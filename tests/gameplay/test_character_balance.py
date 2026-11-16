"""Character balance and prediction regressions, executing Lua 5.1 and native DST methods."""
import re
import unittest
import zipfile
import test_component

ROOT = test_component.ROOT
GAME = r"E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip"


def native(path, signature):
    with zipfile.ZipFile(GAME) as archive:
        source = archive.read('scripts/' + path).decode('utf-8-sig')
    start = source.index(signature)
    end = re.search(r'^end\s*$', source[start:], re.M).end()
    return source[start:start + end]


class CharacterBalance(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute('''
          EQUIPSLOTS.BODY='body';EQUIPSLOTS.BACK='back'
          Vector3=function(x,y,z) return {x=x,y=y,z=z} end
          TheWorld.Map.IsGroundTargetBlocked=function() return false end
          inst.GetPhysicsRadius=function() return .5 end
          inst.Physics.GetCollisionMask=function() return 31 end
          inst.Physics.SetCollisionMask=function(s,n) mask=n end
          inst.Physics.Teleport=function(s,x,y,z) position={x,y,z};teleported=x end
          position={0,0,0};inst.Transform.GetWorldPosition=function() return unpack(position) end
          inst.components.inventory.GetEquippedItem=function(s,slot) return equips and equips[slot] end
          equips={}
          bag={prefab='klbq_singularity',_klbq_eyeball={value=function() return upgraded end}}
          upgraded=true
          inst.components.locomotor.pathcaps=nil
          LocoMotor={}
        ''')
        self.lua.execute(native('components/locomotor.lua', 'function LocoMotor:AdjustPathCaps('))
        self.lua.execute('inst.components.locomotor.AdjustPathCaps=LocoMotor.AdjustPathCaps')

    def native_speed(self):
        self.lua.execute(native('components/locomotor.lua', 'local function ServerGetSpeedMultiplier(') + '\nNativeSpeed=ServerGetSpeedMultiplier')
        self.lua.execute('''
          local l=inst.components.locomotor
          terrain=1;equipment=1;other=1;l.domain=1;l.throttle=1;l.inst=inst
          l.ExternalSpeedMultiplier=function(s) return other*s.domain end
          l.TempGroundSpeedMultiplier=function() return terrain end
          l.RemoveExternalSpeedMultiplier=function(s) s.domain=1 end
          l.SetExternalSpeedMultiplier=function(s,owner,key,n) s.domain=n end
          inst.components.inventory.isopen=true
          inst.components.inventory.equipslots={}
          inst.components.inventory.equipslots.body={components={equippable={GetWalkSpeedMult=function() return equipment end}}}
          for i=1,20 do
            if debug.getupvalue(l.GetSpeedMultiplier,i)=='oldspeed' then debug.setupvalue(l.GetSpeedMultiplier,i,NativeSpeed);break end
          end
        ''')

    def test_native_speed_scales_existing_buffs_then_adds_c_and_x_before_wet_penalty(self):
        self.native_speed()
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.5)
        self.lua.execute('equipment=1.25;terrain=1.3;other=1.1')
        base = 1.25 * 1.3 * 1.1 * 1.5
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), base)
        self.lua.execute('component:ToggleString()')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), base + .5)
        self.lua.execute('''
          inst:AddTag('player');TheNet={GetPVPEnabled=function() return false end}
          inst.components.sanity.SetNegativeAuraImmunity=function() end
          inst.components.combat.externaldamagemultipliers.RemoveModifier=function() end
          -- Isolate speed composition; native domain cleansing is tested separately.
          require('klbq_kanami/cleanse').Apply=function() end
          TheSim.FindEntities=function(s,x,y,z,r) return r==12 and {inst} or {} end
          tracked=require('klbq_kanami/domain').Scan(inst,{})
        ''')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), base + .7)
        self.lua.execute('inst.components.moisture.moisture=.01;inst:PushEvent("moisturedelta");component:Tick()')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), (base + .7) * .5)
        self.lua.execute('require("klbq_kanami/domain").Scan(inst,tracked)')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), (base + .7) * .5)
        self.lua.execute('require("klbq_kanami/domain").Remove(inst,tracked)')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), (base + .5) * .5)

    def test_any_positive_moisture_blocks_entry_but_allows_exit_and_does_not_force_exit(self):
        self.lua.execute('inst.components.moisture.moisture=.01')
        self.assertFalse(self.lua.eval('component:ToggleString()'))
        self.assertFalse(self.lua.eval('component.state.string'))
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), .975)
        self.lua.execute('inst.components.moisture.moisture=0')
        self.assertTrue(self.lua.eval('component:ToggleString()'))
        self.lua.execute('inst.components.moisture.moisture=.01;inst:PushEvent("moisturedelta");component:Tick()')
        self.assertTrue(self.lua.eval('component.state.string'))
        self.assertTrue(self.lua.eval('inst._klbq_wet:value()'))
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.225)
        self.assertTrue(self.lua.eval('component:ToggleString()'))

    def test_plain_string_keeps_native_drowning_and_ocean_pathing(self):
        self.lua.execute('component:ToggleString()')
        self.assertFalse(self.lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean') or False)
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldDrown()'))
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldFallInVoid()'))
        self.assertFalse(self.lua.eval('inst._klbq_waterwalk:value()'))

    def test_upgraded_bag_must_be_equipped_in_body_or_back(self):
        self.lua.execute('component:ToggleString();equips.hands=bag;component:ApplyString();component:Sync()')
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldDrown()'))
        for slot in ('body', 'back'):
            with self.subTest(slot=slot):
                self.lua.execute('equips={};equips[...]=bag;component:ApplyString();component:Sync()', slot)
                self.assertTrue(self.lua.eval('inst._klbq_waterwalk:value()'))
                self.assertTrue(self.lua.eval('inst.components.locomotor.pathcaps.allowocean'))
                self.assertFalse(self.lua.eval('inst.components.drownable:ShouldDrown()'))
        self.lua.execute('upgraded=false;component:ApplyString();component:Sync()')
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldDrown()'))
        self.assertFalse(self.lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean') or False)

    def test_losing_bag_over_water_returns_only_to_still_valid_land(self):
        self.lua.execute('''
          TheWorld.Map.IsVisualGroundAtPoint=function(s,x,y,z) return x<10 end
          equips.body=bag;component:ToggleString();position={20,0,20}
          equips.body=nil;component:ApplyString();component:Sync()
        ''')
        self.assertEqual(self.lua.eval('teleported'), 0)
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldDrown()'))
        self.lua.execute('''
          position={0,0,0};equips.body=bag;component:ApplyString()
          position={20,0,20};component.lastsafe={30,0,30};teleported=nil
          equips.body=nil;component:ApplyString()
        ''')
        self.assertIsNone(self.lua.eval('teleported'))
        self.assertTrue(self.lua.eval('inst.components.drownable:ShouldDrown()'))

    def test_load_drops_a_safety_coordinate_from_another_shard(self):
        self.lua.execute('''
          TheShard={GetShardId=function() return 'Master' end}
          component.lastsafe={4,0,4};data=component:OnSave()
          TheShard.GetShardId=function() return 'Caves' end
          component:OnLoad(data)
        ''')
        self.assertIsNone(self.lua.eval('component.lastsafe'))

    def test_safety_return_rejects_void_nonfinite_and_blocked_saved_points(self):
        self.lua.execute('''
          component.lastsafe={3,0,3}
          TheWorld.Map.IsInvalidTileAtPoint=function() return true end
        ''')
        self.assertFalse(self.lua.eval('component:ReturnToSafeGround()'))
        self.assertIsNone(self.lua.eval('teleported'))
        self.lua.execute('TheWorld.Map.IsInvalidTileAtPoint=function() return false end;component.lastsafe={math.huge,0,3}')
        self.assertFalse(self.lua.eval('component:ReturnToSafeGround()'))
        self.lua.execute('component.lastsafe={3,0,3};TheWorld.Map.IsGroundTargetBlocked=function() return true end')
        self.assertFalse(self.lua.eval('component:ReturnToSafeGround()'))

    def test_temperature_and_burning_cause_multiply_only_damage_preserve_args_and_protection(self):
        for cause, multiplier in [('cold', 2), ('hot', 2), ('fire', 1.5), ('dragonfly', 1), ('hunger', 1)]:
            with self.subTest(cause=cause):
                self.lua.execute('inst.components.health.currenthealth=1000')
                self.assertAlmostEqual(self.lua.eval('inst.components.health:DoDelta(-10,true,...)', cause), -10 * multiplier)
                self.assertEqual(self.lua.eval('inst.components.health:DoDelta(10,true,...)', cause), 10)
        self.lua.execute('component:ToggleString()')
        self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10,true,"cold")'), -4)
        self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10,false,"fire")'), -3)
        self.lua.execute('component.state.deadlines.protect=30')
        self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10,true,"hot")'), 0)
        self.assertEqual(self.lua.eval('inst.components.health:DoDelta(10,true,"hot")'), 10)

    def test_death_and_component_removal_disable_personal_movement_bonuses(self):
        self.lua.execute('equips.body=bag;component:ToggleString();component:OnDeath();inst:AddTag("playerghost")')
        self.assertFalse(self.lua.eval('inst._klbq_waterwalk:value()'))
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.3)
        self.lua.execute('inst:RemoveTag("playerghost");component:OnRespawn()')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.95)
        self.lua.execute('component:OnRemoveFromEntity()')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.3)
        self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10,true,"cold")'), -10)

    def test_damage_wrapper_keeps_nil_arguments_tail_and_all_return_values(self):
        self.lua.execute('''
          local function original(h,n,...) captured={n=select('#',...),...};return n,nil,'last' end
          for i=1,20 do
            if debug.getupvalue(inst.components.health.DoDelta,i)=='olddelta' then
              debug.setupvalue(inst.components.health.DoDelta,i,original);break
            end
          end
          first,middle,last=inst.components.health:DoDelta(-10,nil,'hot',false,nil,true)
        ''')
        self.assertEqual(self.lua.eval('first'), -20)
        self.assertIsNone(self.lua.eval('middle'))
        self.assertEqual(self.lua.eval('last'), 'last')
        self.assertEqual(self.lua.eval('captured.n'), 5)
        self.assertEqual(self.lua.eval('captured[2]'), 'hot')
        self.assertFalse(self.lua.eval('captured[3]'))
        self.assertTrue(self.lua.eval('captured[5]'))
        self.lua.execute('inst.components.health:DoDelta(-10)')
        self.assertEqual(self.lua.eval('captured.n'), 0)


class PredictionBalance(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute('''
          TheWorld.ismastersim=false;Asset=function() return {} end
          package.preload['prefabs/player_common']=function() return function(n,p,a,common) return common end end
          net_bool=function() return {v=false,value=function(s) return s.v end,set=function(s,v) s.v=v end} end
          net_ushortint=net_bool;net_float=net_bool;net_entity=net_bool;net_byte=net_bool
          inst.MiniMapEntity={SetIcon=function() end};inst.Physics.GetCollisionMask=function() return 31 end
          tasks={};inst.DoTaskInTime=function(s,t,f) tasks[#tasks+1]=f;return {Cancel=function() end} end
          function drain() local q=tasks;tasks={};for _,f in ipairs(q) do f(inst) end end
          LocoMotor={}
        ''')
        self.lua.execute(native('components/locomotor.lua', 'function LocoMotor:AdjustPathCaps('))
        self.lua.execute('function newloco() return {GetSpeedMultiplier=function() return 1.3 end,AdjustPathCaps=LocoMotor.AdjustPathCaps} end;inst.components.locomotor=newloco()')
        source = (ROOT/'mods/klbq_kanami/scripts/prefabs/klbq_kanami.lua').read_text(encoding='utf-8-sig')
        self.lua.execute('common=(function() ' + source + ' end)();common(inst);drain()')

    def test_prediction_tracks_wet_and_separate_water_permission_then_recreates_without_stacking(self):
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.95)
        self.lua.execute('inst._klbq_string:set(true);inst:PushEvent("klbq_statusdirty")')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 2.45)
        self.assertFalse(self.lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean') or False)
        self.lua.execute('inst._klbq_wet:set(true);inst._klbq_waterwalk:set(true);inst:PushEvent("klbq_statusdirty")')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.225)
        self.assertTrue(self.lua.eval('inst.components.locomotor.pathcaps.allowocean'))
        self.lua.execute('inst.components.locomotor=newloco();inst:PushEvent("enablemovementprediction");drain()')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.225)
        self.assertTrue(self.lua.eval('inst.components.locomotor.pathcaps.allowocean'))
        self.lua.execute('for i=1,4 do inst:PushEvent("playeractivated");inst:PushEvent("klbq_statusdirty");drain() end')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.225)
        self.lua.execute('inst._klbq_waterwalk:set(false);inst:PushEvent("klbq_statusdirty")')
        self.assertFalse(self.lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean') or False)
        self.lua.execute('inst:AddTag("playerghost");inst:PushEvent("klbq_statusdirty")')
        self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.3)


class ResurrectionHands(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute('Inventory={};Combat={};EQUIPSLOTS.BODY="body";EQUIPSLOTS.HEAD="head";EQUIPSLOTS.BACK="back"')
        for name in ('Equip', 'Unequip', 'GiveItem'):
            self.lua.execute(native('components/inventory.lua', 'function Inventory:'+name+'('))
        self.lua.execute(native('components/combat.lua', 'function Combat:CanAttack('))
        self.lua.execute('''
          inv=inst.components.inventory;inv.inst=inst;inv.equipslots={};inv.itemslots={};inv.maxslots=1
          inv.Equip=inv.Equip
          inv.Unequip=Inventory.Unequip;inv.GiveItem=Inventory.GiveItem
          inv.GetEquippedItem=function(s,slot) return s.equipslots[slot] end
          inv.GetItemSlot=function() return nil end
          inv.GetOverflowContainer=function() return nil end
          inv.GetSpecializedContainers=function() return nil end
          inv.GetNextAvailableSlot=function(s) if not full then return 1,s.itemslots end end
          inv.IsItemEquipped=function(s,item) for slot,v in pairs(s.equipslots) do if v==item then return slot end end end
          inv.DropItem=function(s,item) dropped=item;item.components.inventoryitem.owner=nil;return item end
          function item(slot)
            local i={components={},IsValid=function() return true end,HasTag=function() return false end}
            i.components.equippable={equipslot=slot,IsRestricted=function() return false end,
              IsRestricted_FromLoad=function() return false end,ShouldPreventUnequipping=function() return false end,
              Equip=function() equipped=(equipped or 0)+1 end,Unequip=function() unequipped=(unequipped or 0)+1 end,
              ToPocket=function() pocketed=(pocketed or 0)+1 end}
            i.components.inventoryitem={cangoincontainer=true,IsHeld=function() return false end,
              OnPutInInventory=function(s,owner) s.owner=owner end,OnPickup=function() return false end}
            return i
          end
          for i=1,20 do
            if debug.getupvalue(inv.Equip,i)=='oldequip' then debug.setupvalue(inv.Equip,i,Inventory.Equip);break end
          end
          local c=inst.components.combat;c.inst=inst;c.canattack=true
          c.IsValidTarget=function() return true end;c.InCooldown=function() return false end;c.ignorehitrange=true
          for i=1,20 do
            if debug.getupvalue(c.CanAttack,i)=='oldcan' then debug.setupvalue(c.CanAttack,i,Combat.CanAttack);break end
          end
          weapon=item('hands');armor=item('body');hat=item('head');bag=item('back')
          inv.equipslots.hands=weapon
          function protect()
            component:OnDeath();component.autoreviving=true;component:OnRespawn()
          end
        ''')

    def test_auto_resurrection_returns_existing_hand_item_through_native_inventory(self):
        self.lua.execute('protect()')
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))
        self.assertTrue(self.lua.eval('inv.itemslots[1]==weapon'))
        self.assertEqual(self.lua.eval('unequipped'), 1)
        self.assertEqual(self.lua.eval('pocketed'), 1)
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'), 1)
        self.assertEqual(self.lua.eval('inst.components.hunger.p'), .5)
        self.assertEqual(self.lua.eval('inst.components.sanity.p'), 1)
        self.assertEqual(self.lua.eval('component:Remaining("protect")'), 30)

    def test_full_native_inventory_drops_weapon_without_deleting_it(self):
        self.lua.execute('full=true;inv.activeitem=item("hands");protect()')
        self.assertTrue(self.lua.eval('dropped==weapon'))
        self.assertTrue(self.lua.eval('weapon:IsValid()'))
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))
        self.assertIsNone(self.lua.eval('weapon.components.inventoryitem.owner'))

    def test_protection_locks_only_hand_equipment_until_exact_deadline_without_auto_requip(self):
        self.lua.execute('protect()')
        self.assertFalse(bool(self.lua.eval('inv:Equip(weapon)')))
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))
        for name in ('armor', 'hat', 'bag'):
            self.assertTrue(self.lua.eval('inv:Equip(_G[...])', name))
        self.lua.execute('now=29.999')
        self.assertFalse(bool(self.lua.eval('inv:Equip(weapon)')))
        self.lua.execute('now=30;component:Tick()')
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))
        self.assertTrue(self.lua.eval('inv:Equip(weapon)'))
        self.assertTrue(self.lua.eval('inv.equipslots.hands==weapon'))

    def test_protection_blocks_native_canattack_and_direct_doattack_but_allows_czx(self):
        self.lua.execute('protect()')
        self.assertFalse(self.lua.eval('inst.components.combat:CanAttack({})'))
        self.assertIsNone(self.lua.eval('inst.components.combat:DoAttack({})'))
        self.assertIsNone(self.lua.eval('captured'))
        self.assertTrue(self.lua.eval('component:ToggleString()'))
        self.assertTrue(self.lua.eval('component:ToggleString()'))
        self.assertTrue(self.lua.eval('component:Cast("z")'))
        self.assertTrue(self.lua.eval('component:Cast("x")'))
        self.assertTrue(self.lua.eval('component:IsProtected()'))
        self.lua.execute('now=30;component:Tick()')
        self.assertTrue(self.lua.eval('inst.components.combat:CanAttack({})'))
        self.assertEqual(self.lua.eval('inst.components.combat:DoAttack({})'), ('original', 7))

    def test_retained_equip_wrapper_is_inert_on_removal_and_keeps_a_later_mod(self):
        self.lua.execute('''
          protect();ours=inv.Equip
          later=function(...) return ours(...) end;inv.Equip=later
          component:OnRemoveFromEntity()
        ''')
        self.assertTrue(self.lua.eval('inv.Equip==later'))
        self.assertTrue(self.lua.eval('inv:Equip(weapon)'))
        self.assertTrue(self.lua.eval('inst.components.combat:CanAttack({})'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
