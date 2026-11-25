"""Lifecycle regressions use methods read from the installed DST scripts.zip."""
import re
import unittest
import zipfile
import test_component

ROOT = test_component.ROOT
GAME = r"E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip"


def vanilla(path, signature):
    with zipfile.ZipFile(GAME) as archive:
        source = archive.read('scripts/' + path).decode('utf-8-sig')
    start = source.index(signature)
    # Vanilla top-level functions end at column zero; nested blocks are indented.
    end = re.search(r'^end\s*$', source[start:], re.M).end()
    return source[start:start + end]


def register(lua):
    from resource_fixture import preload_resources, preload_midgame
    preload_resources(lua)
    preload_midgame(lua)
    lua.execute('''
      STRINGS={CHARACTER_TITLES={},CHARACTER_NAMES={},CHARACTER_DESCRIPTIONS={},CHARACTER_QUOTES={},CHARACTER_SURVIVABILITY={},NAMES={},CHARACTERS={GENERIC={DESCRIBE={}}},SKIN_NAMES={},RECIPE_DESC={}}
      TheNet={IsDedicated=function() return true end};TECH={SCIENCE_ONE=1,SCIENCE_TWO=2}
      ACTIONS=ACTIONS or {};ACTIONS.DROP=ACTIONS.DROP or {fn=function()end}
      Action=function(v) return v end;ActionHandler=function() return {} end
      Ingredient=function() return {} end;Vector3=function(x,y,z) return {x=x,y=y,z=z} end
      State=function(v) return v end;EventHandler=function() return {} end;TimeEvent=function()return {}end
      TUNING=TUNING or {};TUNING.WILSON_ATTACK_PERIOD=.4
      package.preload.containers=function() return {params={},MAXITEMSLOTS=0} end
      package.preload.speech_willow=function() return {} end
      package.preload['klbq_kanami/technology']=function() return {Install=function() TECH.KLBQ_STRING_ONE={KLBQ_STRING=1} end} end
      require('klbq_kanami/chef').Install=function() end -- independently covered by native chef tests
      env=setmetatable({GLOBAL=_G},{__index=_G});env.env=env
      env.GetModConfigData=function(key) return nil end -- existing world without overrides
      env.Asset=function() return {} end;hooks={};postinits={}
      env.RegisterInventoryItemAtlas=function() end
      for _,n in ipairs({'AddMinimapAtlas','AddModCharacter','AddAction','AddComponentAction','AddStategraphActionHandler','AddStategraphState','AddStategraphPostInit','AddModRPCHandler','AddClientModRPCHandler','AddRecipe2','AddClassPostConstruct'}) do env[n]=function() end end
      env.AddComponentPostInit=function(name,fn) hooks[name]=fn end
      env.AddPlayerPostInit=function(fn) playerpostinit=fn end
      env.AddPrefabPostInit=function(name,fn) postinits[name]=fn end
      registeredactions={};componentactions={}
      env.AddAction=function(action) registeredactions[action.id]=action end
      env.AddComponentAction=function(kind,name,fn) componentactions[kind..name]=fn end
    ''')
    for name in ('klbq_kanami/states','klbq_kanami/requiem','klbq_kanami/bag','klbq_kanami/speech'):
        lua.execute('package.preload[...] = function() ' + (ROOT/'mods/klbq_kanami/scripts'/f'{name}.lua').read_text(encoding='utf-8-sig') + ' end', name)
    lua.execute('setfenv(assert(loadstring(...)),env)()', (ROOT/'mods/klbq_kanami/modmain.lua').read_text(encoding='utf-8-sig'))


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua

    def test_vanilla_entity_remove_clears_domain_modifiers(self):
        lua=self.lua
        lua.execute('''EntityScript={};Ents={};ScriptManager={};TheSim={UnregisterComponentUpdates=function() end};
          OnRemoveEntity=function() end;NewUpdatingEnts={};NewStaticUpdatingEnts={};NewWallUpdatingEnts={}
          UpdatingEnts={};StaticUpdatingEnts={};WallUpdatingEnts={}
          Ents={};numEnts=1;TheNet={UnregisterChatColor=function() end}
        ''')
        lua.execute(vanilla('entityscript.lua','function EntityScript:Remove()'))
        lua.execute('''
          enemy={components={health={IsDead=function() return false end}},
            IsValid=function() return true end,HasTag=function() return false end}
          enemy.components.locomotor={RemoveExternalSpeedMultiplier=function() speed=1 end,
            SetExternalSpeedMultiplier=function(s,o,k,v) speed=v end}
          enemy.components.combat={externaldamagemultipliers={RemoveModifier=function() damage=1 end,
            SetModifier=function(s,o,v,k) damage=v end}}
          inst.IsValid=function() return true end
          inst.HasTag=function(s,t) return t=='player' end
          inst.StopUpdatingComponent=function() end;inst.StopWallUpdatingComponent=function() end
          inst.StopStaticUpdatingComponent=function() end
          inst.StopAllWatchingWorldStates=function() end;inst.RemoveAllEventCallbacks=function() end
          inst.CancelAllPendingTasks=function() end;inst.replica={_={}}
          inst.event_listeners={};inst.event_listening={};inst.pendingtasks={}
          inst.entity={Retire=function() end};ScriptManager.RemoveInstance=function() end
          inst.components.klbq_kanami.targets={[enemy]=true}
          enemy._klbq_domains={[inst]=false};speed=.5;damage=.5
          EntityScript.Remove(inst)
        ''')
        self.assertEqual(lua.eval('speed'),1)
        self.assertEqual(lua.eval('damage'),1)

    def test_dropped_projectile_preserves_launch_weapon_and_z(self):
        lua = self.lua
        register(lua)
        lua.execute('Combat={};Projectile={};StopTrackingDelayOwner=function() end')
        lua.execute(vanilla('components/combat.lua', 'function Combat:DoAttack('))
        lua.execute(vanilla('components/projectile.lua', 'function Projectile:Hit('))
        lua.execute('''
          originalattack=nil
          for i=1,20 do
            local name,value=debug.getupvalue(inst.components.combat.DoAttack,i)
            if name=='oldattack' then originalattack=value;debug.setupvalue(inst.components.combat.DoAttack,i,Combat.DoAttack);break end
          end
          inst.components.combat.inst=inst
          inst.components.combat.CanHitTarget=function() return true end
          inst.components.combat.ClearAttackTemps=function() end
          target={components={}}
          inst.components.inventory.DropItem=function(s,w) hand=nil;return w end
          inst.components.combat.GetWeapon=function() return hand end
        ''')
        for name, power in [('blowdart_pipe', 100), ('boomerang', 27)]:
            with self.subTest(weapon=name):
                lua.globals().power = power
                lua.globals().weaponname = name
                lua.execute('''
                  component.state.zenabled=true
                  launched={prefab=weaponname,components={weapon={GetDamage=function() return power end}},
                    Physics={Stop=function() end},IsValid=function() return true end}
                  p={inst=launched,Throw=function(s,owner,t) s.owner=owner;return 'thrown',7 end,Stop=function() end}
                  launched.components.projectile=p;hooks.projectile(p);hand=launched
                  inst.components.combat:DoAttack(target)
                ''')
                self.assertEqual(lua.eval('launched._klbq_attack_snapshot.power'), power)
                self.assertTrue(lua.eval('launched._klbq_attack_snapshot.weapon==launched'))
                lua.execute('''
                  component.state.zenabled=false;hand={prefab='newweapon',components={}}
                  -- Use vanilla projectile Hit and the real mod DoAttack wrapper;
                  -- replace only the final damage sink, after the launch under test.
                  for i=1,20 do local n=debug.getupvalue(inst.components.combat.DoAttack,i)
                    if n=='oldattack' then debug.setupvalue(inst.components.combat.DoAttack,i,originalattack);break end end
                  Projectile.Hit(p,target)
                ''')
                self.assertEqual(lua.eval('captured.power'), power)
                self.assertEqual(lua.eval('captured.zmult'), 1.5)
                lua.execute('for i=1,20 do local n=debug.getupvalue(inst.components.combat.DoAttack,i);if n=="oldattack" then debug.setupvalue(inst.components.combat.DoAttack,i,Combat.DoAttack);break end end')

    def test_separate_projectile_uses_weapon_owner_and_copies_context(self):
        register(self.lua)
        self.lua.execute('''
          weapon={prefab='staff',components={weapon={GetDamage=function() return 60 end},inventoryitem={owner=inst}}}
          target={};context={power=61,zmult=1.5,weapon=weapon};component.attackcontext=context
          p={inst={components={}},Throw=function() return 'ok',7 end};hooks.projectile(p)
          first,second=p:Throw(weapon,target,inst)
          context.power=0
        ''')
        self.assertEqual(self.lua.eval('p.inst._klbq_attack_snapshot.power'), 61)
        self.assertEqual(self.lua.eval('first'), 'ok')
        self.assertEqual(self.lua.eval('second'), 7)

    def test_direct_throw_falls_back_to_projectile_weapon_and_clears_stale_owner(self):
        register(self.lua)
        self.lua.execute('''
          p={inst={components={weapon={GetDamage=function() return 27 end}}},Throw=function() end}
          hooks.projectile(p);p:Throw(inst,{})
        ''')
        self.assertEqual(self.lua.eval('p.inst._klbq_attack_snapshot.power'), 27)
        self.assertTrue(self.lua.eval('p.inst._klbq_attack_snapshot.weapon==p.inst'))
        self.lua.execute('p:Throw({components={combat={}}},{})')
        self.assertIsNone(self.lua.eval('p.inst._klbq_attack_snapshot'))

    def test_complex_projectile_snapshot_is_independent(self):
        register(self.lua)
        self.lua.execute('''
          component.attackcontext={power=100,zmult=1.5,weapon={}}
          p={inst={},Launch=function() return 'launched',7 end};hooks.complexprojectile(p)
          first,second=p:Launch({},inst);component.attackcontext.power=0
        ''')
        self.assertEqual(self.lua.eval('p.inst._klbq_attack_snapshot.power'), 100)
        self.assertEqual(self.lua.eval('second'), 7)

    def test_actionpicker_late_owner_creation_and_recreation_are_idempotent(self):
        register(self.lua)
        self.lua.execute('''
          inst.prefab='klbq_kanami';TheWorld.ismastersim=false
          postinits.klbq_kanami(inst)
          for _,f in ipairs(inst.tasks) do f(inst) end
          function picker() return {inst=inst,count=0,SortActionList=function(s,actions) s.count=s.count+1;return actions,7 end} end
          a=picker();hooks.playeractionpicker(a);wrapped=a.SortActionList;hooks.playeractionpicker(a)
          b=picker();hooks.playeractionpicker(b)
          inst.replica={};inst._klbq_string:set(true)
          result,second=b:SortActionList({{id='ATTACK'},{id='EAT'}})
        ''')
        self.assertTrue(self.lua.eval('a.SortActionList==wrapped'))
        self.assertEqual(self.lua.eval('a.count'), 0)
        self.assertEqual(self.lua.eval('b.count'), 1)
        self.assertEqual(self.lua.eval('#result'),1)
        self.assertEqual(self.lua.eval('result[1].id'),'EAT')
        self.assertEqual(self.lua.eval('second'),7)

    def test_protection_filters_attack_tools_and_hand_equipping_only(self):
        register(self.lua)
        self.lua.execute('''
          inst.replica={inventory={GetEquippedItem=function() return nil end}}
          picker={inst=inst,SortActionList=function(s,a)return a end};hooks.playeractionpicker(picker)
          inst._klbq_protect:set(true)
          ACTIONS={EQUIP={id='EQUIP'}}
          hand={replica={equippable={EquipSlot=function()return EQUIPSLOTS.HANDS end}}}
          body={replica={equippable={EquipSlot=function()return 'body' end}}}
        ''')
        for action in ('ATTACK','CHOP','MINE','HAMMER','KLBQ_SHOOT','KLBQ_SHOOT_LOCK','KLBQ_REQUIEM_SWEEP'):
            self.assertEqual(self.lua.eval('#picker:SortActionList({{id=...}})',action),0)
        for action in ('PICKUP','EAT','LOOKAT'):
            self.assertEqual(self.lua.eval('#picker:SortActionList({{id=...}})',action),1)
        self.assertEqual(self.lua.eval('#picker:SortActionList({ACTIONS.EQUIP},nil,hand)'),0)
        self.assertEqual(self.lua.eval('#picker:SortActionList({ACTIONS.EQUIP},nil,body)'),1)
        self.lua.execute('inst._klbq_protect:set(false)')
        self.assertEqual(self.lua.eval('#picker:SortActionList({{id="CHOP"}})'),1)

    def test_prediction_recreation_reapplies_speed_and_ocean_without_stacking(self):
        lua = self.lua
        lua.execute('''
          TheWorld.ismastersim=false
          Asset=function() return {} end
          package.preload['prefabs/player_common']=function() return function(n,p,a,common) return common end end
          net_bool=function() return {v=false,value=function(s) return s.v end,set=function(s,v) s.v=v end} end
          net_ushortint=net_bool
          net_float=net_bool;net_entity=net_bool;net_byte=net_bool
          inst.MiniMapEntity={SetIcon=function() end};inst.Physics.GetCollisionMask=function() return 31 end
          tasks={};inst.DoTaskInTime=function(s,t,f) tasks[#tasks+1]=f;return {Cancel=function() end} end
          function drain() local pending=tasks;tasks={};for _,f in ipairs(pending) do f(inst) end end
          LocoMotor={}
        ''')
        lua.execute(vanilla('components/locomotor.lua', 'function LocoMotor:AdjustPathCaps('))
        lua.execute('function newloco() return {GetSpeedMultiplier=function() return 1.3 end,AdjustPathCaps=LocoMotor.AdjustPathCaps} end;inst.components.locomotor=newloco()')
        lua.execute('common=(function() ' + (ROOT/'mods/klbq_kanami/scripts/prefabs/klbq_kanami.lua').read_text(encoding='utf-8-sig') + ' end)();common(inst);inst._klbq_string:set(true);inst._klbq_waterwalk:set(true);drain()')
        self.assertAlmostEqual(lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 2.45)
        lua.execute('''
          USE_MOVEMENT_PREDICTION=true;TUNING={WILSON_RUN_SPEED=6};RPC={};SendRPCToServer=function() end
          ex_fns={ConfigurePlayerLocomotor=function() end,ConfigureGhostLocomotor=function() end}
          inst.Physics.Stop=function() end;inst.SetStateGraph=function() end
          inst.entity={EnableMovementPrediction=function() end}
          inst.AddComponent=function(s,name) s.components[name]=name=='locomotor' and newloco() or {} end
          inst.RemoveComponent=function(s,name) s.components[name]=nil end
          inst.ClearBufferedAction=function() end;inst.ClearStateGraph=function() end
        ''')
        source = vanilla('prefabs/player_common.lua', 'local function EnableMovementPrediction(')
        lua.execute(source + '\nEnablePrediction=EnableMovementPrediction')
        lua.execute('EnablePrediction(inst,false);drain();EnablePrediction(inst,true);drain()')
        self.assertAlmostEqual(lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 2.45)
        self.assertTrue(lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean'))
        lua.execute('for i=1,4 do inst:PushEvent("playeractivated");inst:PushEvent("klbq_statusdirty");drain() end')
        self.assertAlmostEqual(lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 2.45)
        lua.execute('inst._klbq_string:set(false);inst:PushEvent("klbq_statusdirty")')
        self.assertAlmostEqual(lua.eval('inst.components.locomotor:GetSpeedMultiplier()'), 1.95)
        self.assertFalse(lua.eval('inst.components.locomotor.pathcaps and inst.components.locomotor.pathcaps.allowocean') or False)

    def test_protection_rejects_vanilla_retaliation_and_shared_aggro(self):
        lua = self.lua
        lua.execute('Combat={};Replica={};IsEntityDead=function() return false end;TheNet={GetPVPEnabled=function() return false end}')
        for name in ('ShouldAggro', 'SetTarget', 'ShareTarget'):
            lua.execute(vanilla('components/combat.lua', 'function Combat:'+name+'('))
        lua.execute(vanilla('components/combat_replica.lua', 'function Combat:IsValidTarget(').replace('Combat:', 'Replica:', 1))
        lua.execute('''
          inst.replica={combat={}};inst.entity={IsValid=function() return true end,IsVisible=function() return true end}
          inst.GetPosition=function() return {y=0} end;inst.isplayer=true
          enemy={tags={},replica={},HasTag=inst.HasTag,Transform=inst.Transform}
          rival={inst=enemy,GetWeapon=function() end,CanExtinguishTarget=function() return false end,CanLightTarget=function() return false end,
            _attackrange={value=function() return 10 end},IsValidTarget=Replica.IsValidTarget,ShouldAggro=Combat.ShouldAggro,
            DropTarget=function(s) s.target=nil end,EngageTarget=function(s,t) s.target=t end}
          helper={components={combat={SuggestTarget=function() shared=true;return true end}}}
          SpringCombatMod=function(r) return r end;TheSim.FindEntities=function() return {helper} end
          external=function() return true end;inst.components.combat.shouldavoidaggrofn=external
          component.state.deadlines.protect=30;component:Protection(true)
          inst:PushEvent('onattackother',{})
          Combat.SetTarget(rival,inst);Combat.ShareTarget(rival,inst,30,nil,5)
        ''')
        self.assertIsNone(lua.eval('rival.target'))
        self.assertIsNone(lua.eval('shared'))
        self.assertFalse(lua.eval('rival:ShouldAggro(inst)'))
        lua.execute('now=30;component:Tick();Combat.SetTarget(rival,inst)')
        self.assertTrue(lua.eval('rival.target==inst'))
        self.assertTrue(lua.eval('inst.components.combat.shouldavoidaggrofn==external'))

    def test_protection_preserves_external_tags_and_later_override(self):
        self.lua.execute('''
          inst:AddTag('notarget');inst:AddTag('stealth')
          component.state.deadlines.protect=30;component:Protection(true)
          later=function() return false end;inst.components.combat.shouldavoidaggrofn=later
          component:Protection(false)
        ''')
        self.assertTrue(self.lua.eval('inst:HasTag("notarget") and inst:HasTag("stealth")'))
        self.assertTrue(self.lua.eval('inst.components.combat.shouldavoidaggrofn==later'))

    def test_protection_leaves_later_wrapper_chain_inert_after_expiry(self):
        self.lua.execute('''
          previous=function() return 'external' end;inst.components.combat.shouldavoidaggrofn=previous
          component.state.deadlines.protect=30;component:Protection(true)
          ours=inst.components.combat.shouldavoidaggrofn
          later=function(...) return ours(...) end;inst.components.combat.shouldavoidaggrofn=later
        ''')
        self.assertFalse(self.lua.eval('later()'))
        self.lua.execute('now=30;component:Protection(false)')
        self.assertEqual(self.lua.eval('later()'), 'external')
        self.assertTrue(self.lua.eval('inst.components.combat.shouldavoidaggrofn==later'))

    def test_damage_helpers_measure_vanilla_getattacked_without_return(self):
        lua=self.lua
        lua.execute('Combat={}')
        lua.execute(vanilla('components/combat.lua','function Combat:GetAttacked('))
        lua.execute('''
          target={components={health={currenthealth=100,IsDead=function(s) return s.currenthealth<=0 end}},
            IsValid=function() return true end,IsInLimbo=function() return false end}
          target.components.combat={GetAttacked=Combat.GetAttacked,GetAttacked_Internal=function(s,a,d,w,stim,sp)
            target.components.health.currenthealth=target.components.health.currenthealth-d-(sp and sp.planar or 0)
            return true
          end}
          Damage=require('klbq_kanami/damage')
        ''')
        self.assertTrue(lua.eval('Damage.Normal(inst,target,20,nil)'))
        self.assertTrue(lua.eval('Damage.Planar(inst,target,30,nil)'))
        self.assertEqual(lua.eval('target.components.health.currenthealth'),50)
        lua.execute('target.components.combat.GetAttacked_Internal=function() return true end')
        self.assertFalse(lua.eval('Damage.Normal(inst,target,20,nil)'))
        self.assertFalse(lua.eval('Damage.Planar(inst,target,30,nil)'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
