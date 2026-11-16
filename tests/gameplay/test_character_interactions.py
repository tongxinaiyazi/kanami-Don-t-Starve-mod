"""Regressions across installed DST actions, inventory, skins and native FX callbacks."""
import re
import unittest
import zipfile
from pathlib import Path

import test_character_balance as balance
import test_component
from test_review_regressions import register


def source(path):
    with zipfile.ZipFile(balance.GAME) as archive:
        return archive.read('scripts/' + path).decode('utf-8-sig')


def native_collision(lua):
    text = source('constants.lua')
    lua.execute(re.search(r'COLLISION\s*=\s*\{.*?\n\}', text, re.S)[0])


class ShoreBoundary(unittest.TestCase):
    def setUp(self):
        fixture = balance.CharacterBalance()
        fixture.setUp()
        self.lua = fixture.lua
        native_collision(self.lua)

    def test_phase_keeps_native_world_shore_without_obstacles_and_updates_when_bag_changes(self):
        self.lua.execute('component:ToggleString()')
        self.assertEqual(self.lua.eval('mask'), self.lua.eval('COLLISION.WORLD'))
        self.lua.execute('equips.body=bag;component:ApplyString();component:Sync()')
        self.assertEqual(self.lua.eval('mask'), self.lua.eval('COLLISION.GROUND'))
        self.lua.execute('equips.body=nil;component:ApplyString();component:Sync()')
        self.assertEqual(self.lua.eval('mask'), self.lua.eval('COLLISION.WORLD'))
        self.assertIsNone(self.lua.eval('teleported'))

    def test_client_prediction_updates_shore_mask_without_reentering_c(self):
        fixture = balance.PredictionBalance()
        fixture.setUp()
        lua = fixture.lua
        native_collision(lua)
        lua.execute('inst.Physics.SetCollisionMask=function(s,n) mask=n end;inst._klbq_string:set(true);inst:PushEvent("klbq_statusdirty")')
        self.assertEqual(lua.eval('mask'), lua.eval('COLLISION.WORLD'))
        lua.execute('inst._klbq_waterwalk:set(true);inst:PushEvent("klbq_statusdirty")')
        self.assertEqual(lua.eval('mask'), lua.eval('COLLISION.GROUND'))
        lua.execute('inst._klbq_waterwalk:set(false);inst:PushEvent("klbq_statusdirty")')
        self.assertEqual(lua.eval('mask'), lua.eval('COLLISION.WORLD'))


class ProtectedNativePickup(unittest.TestCase):
    def setUp(self):
        fixture = balance.ResurrectionHands()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute('ACTIONS={PICKUP={}}')
        self.lua.execute(balance.native('actions.lua', 'ACTIONS.PICKUP.fn ='))
        register(self.lua)
        self.lua.execute('''
          inst:AddTag('player');inv.GetNumSlots=function(s) return s.maxslots end
          weapon.IsInLimbo=function() return false end
          weapon.GetPosition=function() return Vector3(3,0,4) end
          weapon.components.inventoryitem.canbepickedup=true
          act={doer=inst,target=weapon};protect();inv.itemslots={}
          equipped=0;pocketed=0;dropped=nil
        ''')

    def test_native_pickup_pockets_weapon_while_direct_hand_equip_stays_blocked(self):
        self.assertTrue(self.lua.eval('ACTIONS.PICKUP.fn(act)'))
        self.assertTrue(self.lua.eval('inv.itemslots[1]==weapon'))
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))
        self.assertEqual(self.lua.eval('equipped'), 0)
        self.assertFalse(bool(self.lua.eval('inv:Equip(weapon)')))
        self.assertIsNone(self.lua.eval('component.pickupitem'))

    def test_native_pickup_uses_overflow_and_full_inventory_keeps_normal_drop(self):
        self.lua.execute('''
          overflow={GetItemInSlot=function() return nil end,
            GiveItem=function(s,item) received=item;return true end}
          inv.GetOverflowContainer=function() return overflow end
          inv.GetNextAvailableSlot=function() return 1,overflow end
        ''')
        self.assertTrue(self.lua.eval('ACTIONS.PICKUP.fn(act)'))
        self.assertTrue(self.lua.eval('received==weapon'))
        self.lua.execute('''
          inv.GetNextAvailableSlot=function() end
          inv.GetOverflowContainer=function() end
          inv.activeitem=item('hands')
        ''')
        self.assertTrue(self.lua.eval('ACTIONS.PICKUP.fn(act)'))
        self.assertTrue(self.lua.eval('dropped==weapon'))
        self.assertTrue(self.lua.eval('weapon:IsValid()'))
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))

    def test_native_pickup_still_checks_pickup_restrictions(self):
        self.lua.execute('weapon.components.inventoryitem.canbepickedup=false')
        self.assertFalse(bool(self.lua.eval('ACTIONS.PICKUP.fn(act)')))
        self.assertIsNone(self.lua.eval('inv.itemslots[1]'))

    def test_full_native_inventory_can_keep_the_pickup_as_active_item(self):
        self.lua.execute(balance.native('components/inventory.lua', 'local function ValidateItemForOverflow(') + '\nNativeValidateItemForOverflow=ValidateItemForOverflow')
        self.lua.execute('''
          ValidateItemForOverflow=NativeValidateItemForOverflow
          full=true;inv.SetActiveItem=function(s,item) s.activeitem=item end
        ''')
        self.assertTrue(self.lua.eval('ACTIONS.PICKUP.fn(act)'))
        self.assertTrue(self.lua.eval('inv.activeitem==weapon'))
        self.assertIsNone(self.lua.eval('dropped'))
        self.assertIsNone(self.lua.eval('inv.equipslots.hands'))

    def test_native_pickup_resumes_autoequip_at_protection_deadline(self):
        self.lua.execute('now=30;component:Tick()')
        self.assertTrue(self.lua.eval('ACTIONS.PICKUP.fn(act)'))
        self.assertTrue(self.lua.eval('inv.equipslots.hands==weapon'))
        self.assertEqual(self.lua.eval('equipped'), 1)

    def test_pickup_scope_clears_after_native_inventory_callback_errors(self):
        self.lua.execute('''
          weapon.components.inventoryitem.OnPickup=function() error('pickup callback failed') end
          ok,err=pcall(ACTIONS.PICKUP.fn,act)
        ''')
        self.assertFalse(self.lua.eval('ok'))
        self.assertIn('pickup callback failed', self.lua.eval('err'))
        self.assertIsNone(self.lua.eval('component.pickupitem'))
        self.assertFalse(bool(self.lua.eval('inv:Equip(weapon)')))


class NativeAppearance(unittest.TestCase):
    def setUp(self):
        fixture = balance.ResurrectionHands()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute('''
          inst.prefab='klbq_kanami';inst:AddTag('klbq_kanami');inst.isplayer=true
          hidden={};overrides={};build='klbq_kanami';skin='';fxhidden=0
          local methods={
            GetBuild=function() return build end,SetBuild=function(s,b) build=b end,
            GetSkinBuild=function() return skin end,SetSkin=function(s,b,default) skin=b;build=default end,
            HideSymbol=function(s,k) hidden[k]=true end,ShowSymbol=function(s,k) hidden[k]=nil end,
            Hide=function(s,k) hidden[k]=true end,Show=function(s,k) hidden[k]=nil end,
            ClearOverrideSymbol=function(s,k) overrides[k]=nil end,
            OverrideSymbol=function(s,k,b,v) overrides[k]=b;hidden[k]=nil end,
            OverrideItemSkinSymbol=function(s,k,b,v) overrides[k]=b;hidden[k]=nil end,
            OverrideSkinSymbol=function(s,k,b,v) overrides[k]=b;hidden[k]=nil end,
            ClearSymbolExchanges=function() exchanged=false end,
            UseHeadHatExchange=function(s,b) exchanged=b end,
            SetMultColour=function() end}
          local anim=newproxy(true);getmetatable(anim).__index=methods
          getmetatable(anim).__newindex=function() error('native AnimState cannot be modified') end
          inst.AnimState=anim
          function drain() local q=inst.tasks;inst.tasks={};for _,fn in ipairs(q) do fn(inst) end end
          function lateequipment()
            inst.AnimState:OverrideSkinSymbol('torso','clothing','torso')
            inst.AnimState:OverrideSymbol('swap_body','armor','swap_body')
            inst.AnimState:OverrideSymbol('swap_hat','hat','swap_hat')
            inst.AnimState:Hide('HEAD');inst.AnimState:Show('HEAD_HAT_HELM')
            inst.AnimState:HideSymbol('face');inst.AnimState:UseHeadHatExchange(true)
          end
        ''')
        register(self.lua)

    def test_native_equip_then_later_mod_skin_overrides_are_removed_after_call_chain(self):
        self.assertIsNotNone(self.lua.eval('hooks.inventory'), 'missing inventory post-call appearance repair')
        # The native wood armor callback runs inside the native Inventory:Equip.
        native = balance.native('prefabs/armor_wood.lua', 'local function onequip(')
        self.lua.execute('OnBlocked=function() end\n' + native + '\nwood_equip=onequip')
        self.lua.execute('''
          hooks.inventory(inv)
          armor.GetSkinBuild=function() return 'armor_wood_skin' end
          armor.GetSkinName=function() return 'armor_wood_skin' end
          armor.ListenForEvent=function() end
          armor.components.equippable.Equip=function(s,owner) wood_equip(armor,owner) end
          local old=inv.Equip
          inv.Equip=function(...) local r=old(...);lateequipment();return r end
          inv:Equip(armor);drain()
        ''')
        for name in ('swap_hat', 'swap_body'):
            self.assertTrue(self.lua.eval('hidden[...]', name))
            self.assertIsNone(self.lua.eval('overrides[...]', name))
        self.assertIsNone(self.lua.eval('overrides.torso'))
        self.assertIsNone(self.lua.eval('hidden.HEAD'))
        self.assertIsNone(self.lua.eval('hidden.face'))
        self.assertFalse(self.lua.eval('exchanged'))
        self.assertIsNone(self.lua.eval('hidden.swap_object'))

    def test_skinner_native_setskinmode_repairs_clothing_after_base_change_callback(self):
        self.assertIsNotNone(self.lua.eval('hooks.skinner'), 'missing native skin callback appearance repair')
        self.lua.execute('Skinner={};SetSkinsOnAnim=function() lateequipment() end')
        self.lua.execute(balance.native('components/skinner.lua', 'function Skinner:SetSkinMode('))
        self.lua.execute('''
          inst.Network={SetPlayerSkin=function() end}
          skinner={inst=inst,skin_data={normal_skin='klbq_kanami'},skintype='normal_skin',
            clothing={},SetSkinMode=Skinner.SetSkinMode,base_change_cb=lateequipment}
          inst.components.skinner=skinner;hooks.skinner(skinner);skinner:SetSkinMode()
        ''')
        self.assertIsNone(self.lua.eval('overrides.torso'))
        self.assertIsNone(self.lua.eval('overrides.swap_hat'))
        self.assertIsNone(self.lua.eval('hidden.face'))
        self.assertFalse(self.lua.eval('exchanged'))

    def test_native_ghost_skin_transition_keeps_ghost_build_before_ghost_tag(self):
        self.lua.execute('''
          build='ghost_klbq_kanami_build'
          inst.components.skinner={skintype='ghost_skin'}
          require('klbq_kanami/visual').HideEquipment(inst)
        ''')
        self.assertEqual(self.lua.eval('build'), 'ghost_klbq_kanami_build')

    def test_native_follower_fx_spawned_on_replication_is_hidden_after_children_exist(self):
        self.assertIsNotNone(self.lua.eval('postinits.armor_lunarplant_glow_fx'), 'missing follower FX callback repair')
        # Exact native callback: it parents first and creates local children next.
        block = balance.native('prefabs/armor_lunarplant.lua', 'local function glow_OnEntityReplicated(')
        self.lua.execute('''
          function glow_SpawnFxForOwner(fx,owner)
            fx.fx={{Hide=function() fxhidden=fxhidden+1 end,IsValid=function() return true end}}
          end
          fx={entity={GetParent=function() return inst end},
            Hide=function() parenthidden=true end,IsValid=function() return true end,
            DoTaskInTime=function(s,t,fn) inst.tasks[#inst.tasks+1]=function() fn(s) end end}
        ''' + block + '\nfx.OnEntityReplicated=glow_OnEntityReplicated')
        self.lua.execute('postinits.armor_lunarplant_glow_fx(fx);fx:OnEntityReplicated()')
        self.assertTrue(self.lua.eval('parenthidden'))
        self.assertEqual(self.lua.eval('fxhidden'), 1)

    def test_extraequip_native_deferred_replay_cannot_restore_worn_body(self):
        external = Path(r'E:/steam/steamapps/workshop/content/322330/3173431824/scripts/bodylayers.lua').read_text(encoding='utf-8-sig')
        def function(signature):
            start = external.index(signature)
            end = re.search(r'^end\s*$', external[start:], re.M).end()
            return external[start:start + end]
        self.lua.execute('''
          GLOBAL=_G;refresh_tasks={};inst:AddTag('player')
          BODY_LAYER_LIST={{def={key='BODY',visual=true}}}
          GetEquippedItemsByPriority=function(inv) return {BODY=armor} end
          armor._body_visual_ops={{method='OverrideSymbol',symbol='swap_body',args={n=2,'armor_wood','swap_body'}}}
        ''' + function('local function ApplyCachedVisual(') + '\n' + function('local function RefreshBodyVisual(') + '\nexternalrefresh=RefreshBodyVisual')
        self.lua.execute('''
          require('klbq_kanami/visual').Bind(inst);drain();drain()
          -- Native clothing event precedes the extra slot mod's queued replay.
          inst:PushEvent('equipskinneditem','armor_wood_skin')
          externalrefresh(inst);hooks.inventory(inv)
          armor.components.equippable.Equip=function() end
          inv:Equip(armor);drain();drain()
        ''')
        self.assertTrue(self.lua.eval('hidden.swap_body'))
        self.assertIsNone(self.lua.eval('overrides.swap_body'))

    def test_native_state_transitions_hide_carry_for_food_and_tool_actions_then_restore(self):
        self.lua.execute('StateGraphInstance={};SGTagsToEntTags={};SGManager={OnEnterNewState=function() end}')
        self.lua.execute(balance.native('stategraph.lua', 'function StateGraphInstance:GoToState('))
        self.lua.execute('''
          require('klbq_kanami/visual').Bind(inst)
          sg={inst=inst,sg={states={idle={}}},GoToState=StateGraphInstance.GoToState}
        ''')
        native_states = source('stategraphs/SGwilson.lua')
        for state in ('eat', 'quickeat', 'mount_eat', 'float_eat', 'float_quickeat', 'winters_feast_eat',
                      'chop_start', 'mine_recoil', 'hammer', 'dig_start', 'bugnet', 'terraform'):
            with self.subTest(state=state):
                self.assertRegex(native_states, r'name\s*=\s*"' + state + '"')
                self.lua.execute('sg.sg.states[...]={};sg:GoToState(...)', state, state)
                self.assertTrue(self.lua.eval('hidden.swap_object'))
                self.assertTrue(self.lua.eval('hidden.ARM_carry'))
                self.lua.execute('sg:GoToState("idle")')
                self.assertIsNone(self.lua.eval('hidden.swap_object'))
                self.assertIsNone(self.lua.eval('hidden.ARM_carry'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
