"""Native inventory attacks and tools must obey both Kanami hand locks.

Use the installed BufferedAction, EntityScript execution and action picker, plus
the real ACTIONS implementations. Only their item/world component endpoints are
fixtures; neither the admission filter nor the native action body is replaced.
"""
import re
import unittest
import zipfile

import test_component
from test_review_regressions import GAME, register, vanilla


BLOCKED = (
    "TOSS", "TOSS_MAP", "OCEAN_TOSS", "LIGHT",
    "BOAT_CANNON_LOAD_AMMO", "BOAT_CANNON_START_AIMING", "BOAT_CANNON_SHOOT",
    "CAST_NET", "NABBAG", "BRUSH", "SEW", "ROTATE_FENCE", "TERRAFORM_REMOVE",
    "MURDER", "SLAUGHTER", "INCINERATE", "GOLF_START_AIMING", "GOLF_START_CHARGING",
)
DEPLOY = ("DEPLOY", "DEPLOY_TILEARRIVE", "DEPLOY_FLOATING")
ALLOWED = ("EAT", "PICKUP", "BUILD", "BOAT_CANNON_STOP_AIMING", "GOLF_STOP_AIMING")


class HandsAudit(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        with zipfile.ZipFile(GAME) as archive:
            constants = archive.read("scripts/constants.lua").decode("utf-8-sig")
            picker = archive.read("scripts/components/playeractionpicker.lua").decode("utf-8-sig")
            buffered = archive.read("scripts/bufferedaction.lua").decode("utf-8-sig")
            componentactions = archive.read("scripts/componentactions.lua").decode("utf-8-sig")
        # These native entries already cover PLAY/UNSADDLE. Omitting the table
        # would turn previously protected tools into false-positive findings.
        toolactions = re.search(r"TOOLACTIONS\s*=\s*\{[^}]+\}", constants).group()
        self.lua.execute(toolactions)
        self.lua.execute("ACTIONS={}")
        for name in BLOCKED + DEPLOY + ALLOWED + ("ATTACK", "PLAY", "UNSADDLE"):
            self.lua.execute("ACTIONS[...]= {id=...,priority=1}", name, name)
        self.lua.execute(vanilla("actions.lua", "local function ActionCanMapToss(") +
                         "\n_G.ActionCanMapToss=ActionCanMapToss")
        self.lua.execute(vanilla("actions.lua", "local function IsBoatCannonAmmo(") +
                         "\n_G.IsBoatCannonAmmo=IsBoatCannonAmmo")
        for name in BLOCKED + ALLOWED + ("DEPLOY", "PLAY"):
            self.lua.execute(vanilla("actions.lua", "ACTIONS." + name + ".fn = function("))
        self.lua.execute("ACTIONS.DEPLOY_TILEARRIVE.fn=ACTIONS.DEPLOY.fn;ACTIONS.DEPLOY_FLOATING.fn=ACTIONS.DEPLOY.fn")
        self.lua.execute("EntityScript={}")
        for method in ("PerformBufferedAction", "GetBufferedAction", "ClearBufferedAction"):
            self.lua.execute(vanilla("entityscript.lua", "function EntityScript:" + method + "("))
        self.lua.execute(buffered)
        self.lua.globals().Picker = self.lua.execute(picker)
        register(self.lua)
        self.lua.execute("Discover={}")
        for key, signature in (
            ("toss", "complexprojectile = function(inst, doer, pos, actions, right, target)"),
            ("light", "lighter = function(inst, doer, target, actions)"),
            ("cannon", "boatcannon = function(inst, doer, actions, right)"),
        ):
            start = componentactions.index(signature)
            end = start + re.search(r"^        end,", componentactions[start:], re.M).end()
            body = componentactions[start:end].rstrip(",")
            field = signature.split(" =", 1)[0]
            self.lua.execute("Discover[...]=({" + body + "})." + field, key)
        self.lua.execute("""
            EQUIPSLOTS={HANDS='hands',BODY='body'}
            ShouldItemMimicBeRevealedFor=function()return false end
            DynamicPosition=function(pt)return {GetPosition=function()return pt end}end
            TUNING.FENCE_DEFAULT_ROTATION=90
            GetDescription=function()return 'ready' end
            effects=0;hand=nil
            function Effect()effects=effects+1;return true end
            function Entity()
                local e={tags={},components={},replica={},Transform={SetPosition=function()end,
                    GetWorldPosition=function()return 1,0,1 end}}
                function e:HasTag(t)return self.tags[t] or false end
                function e:HasAnyTag(...)
                    for i=1,select('#',...)do if self:HasTag(select(i,...))then return true end end
                    return false
                end
                function e:IsValid()return true end
                function e:IsInLimbo()return false end
                function e:is_a(t)return t==EntityScript end
                function e:GetPosition()return {x=1,y=0,z=1}end
                function e:Remove()return Effect()end
                e.OnUsedAsItem=function()end
                e.FacePoint=function()end
                e.sg={GoToState=Effect}
                return e
            end
            inst.prefab='klbq_kanami';inst:AddTag('player')
            inst._klbq_string:set(false);inst._klbq_protect:set(false)
            inst.replica={inventory={GetEquippedItem=function()return hand end,
                GetActiveItem=function()return item end}}
            inst.components.inventory.GetEquippedItem=function()return hand end
            inst.components.inventory.GetActiveItem=function()return item end
            inst.components.inventory.FindItem=function()return item end
            inst.components.inventory.DropItem=function(_,i)return i end
            inst.components.inventory.RemoveItem=function(_,i)return i end
            inst.components.inventory.GiveItem=Effect
            inst.components.inventory.IsOpenedBy=function()return true end
            inst.components.talker={Say=function()end}
            inst.components.builder={DoBuild=Effect}
            inst.components.eater={Eat=Effect}
            inst.components.boatcannonuser={SetCannon=Effect,GetCannon=function()return target end}
            inst.PerformBufferedAction=EntityScript.PerformBufferedAction
            inst.GetBufferedAction=EntityScript.GetBufferedAction
            inst.ClearBufferedAction=EntityScript.ClearBufferedAction
            inst.FacePoint=function()end
            playerpostinit(inst)
            p=Picker(inst);hooks.playeractionpicker(p)
            function Prepare()
                effects=0;hand=nil
                item=Entity();target=Entity()
                item.tags.complexprojectile=true;item.tags.projectile=true
                item.tags.boatcannon_ammo=true;item.projectileprefab='cannonball_rock'
                item.CanTossOnMap=function()return true end
                item.replica.inventoryitem={IsHeldBy=function()return true end}
                item.components.inventoryitem={IsHeldBy=function()return true end,
                    RemoveFromOwner=function()return item end}
                item.components.complexprojectile={Launch=Effect}
                item.components.oceanthrowable={AddProjectile=function()end}
                item.components.deployable={CanDeploy=function()return true end,Deploy=Effect}
                item.components.lighter={Light=Effect}
                item.components.fishingnet={CastNet=Effect}
                item.components.nabbag={DoNabFromAct=Effect}
                item.components.sewing={DoSewing=Effect}
                item.components.fencerotator={Rotate=Effect}
                item.components.terraformer={}
                item.components.quagmire_slaughtertool={Slaughter=Effect}
                item.components.instrument={Play=Effect}
                item.components.golfclub={StartAiming=Effect,StopAiming=Effect}
                item.components.equippable={IsRestricted=function()return false end,
                    ShouldPreventUnequipping=function()return false end,IsEquipped=function()return hand==item end}
                item.components.health={IsDead=function()return false end}
                target.tags.canbeslaughtered=true
                target.components.inventoryitem={canbepickedup=true,RemoveFromOwner=function()return target end}
                target.components.health={IsDead=function()return false end}
                target.components.burnable={IsBurning=function()return false end}
                target.components.boatcannon={operator=nil,IsAmmoLoaded=function()return false end,LoadAmmo=Effect}
                target.components.brushable={Brush=Effect}
                target.components.terraformerremoveable={TryToRemove=Effect}
                target.components.fueled={}
                target.components.incinerator={Incinerate=Effect}
                target.components.edible={}
            end
            inst.IsNear=function()return true end
            function SetLock(mode)
                inst._klbq_string:set(mode=='string')
                inst._klbq_protect:set(mode=='protect')
                component.state.string=mode=='string'
                component.state.deadlines.protect=mode=='protect' and 30 or nil
            end
            function Perform(name)
                inst.bufferedaction=BufferedAction(inst,target,ACTIONS[name],item,{x=1,y=0,z=1})
                return inst:PerformBufferedAction()
            end
            function Offered(name)
                return #p:SortActionList({ACTIONS[name]},target,item)>0
            end
        """)

    def test_unlocked_inventory_attacks_and_equipped_golf_actions_keep_native_behavior(self):
        for name in BLOCKED:
            with self.subTest(action=name):
                self.lua.execute("Prepare();SetLock('normal')")
                if name.startswith("GOLF_"):
                    self.lua.execute("hand=item")
                else:
                    self.assertTrue(self.lua.eval("hand==nil"))
                self.assertTrue(self.lua.eval("Perform(...)", name))
                if name != "GOLF_START_CHARGING":  # native fn returns true; SG does the swing
                    self.assertGreater(self.lua.eval("effects"), 0)
                self.assertTrue(self.lua.eval("Offered(...)", name))

    def test_server_rejects_inventory_attacks_and_tools_before_native_side_effects(self):
        for mode in ("string", "protect"):
            for name in BLOCKED:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("Prepare();SetLock(...)", mode)
                    if mode == "string" and name.startswith("GOLF_"):
                        self.lua.execute("hand=item")
                    self.assertFalse(self.lua.eval("Perform(...)", name))
                    self.assertEqual(self.lua.eval("effects"), 0)
                    self.assertTrue(self.lua.eval("inst.bufferedaction==nil"))

    def test_client_picker_filters_the_same_inventory_attacks_without_server_components(self):
        for mode in ("string", "protect"):
            for name in BLOCKED:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("Prepare();SetLock(...);item.components={};TheWorld.ismastersim=false", mode)
                    self.assertFalse(self.lua.eval("Offered(...)", name))

    def test_native_client_discovery_is_filtered_before_buffered_actions_are_offered(self):
        for mode in ("normal", "string", "protect"):
            with self.subTest(mode=mode):
                self.lua.execute("""
                    Prepare();SetLock(...);item.components={};target.components={}
                    TheWorld.ismastersim=false;target.tags.canlight=true;target.tags.ammoloaded=true
                    discovered={}
                    Discover.toss(item,inst,{x=1,y=0,z=1},discovered,true)
                    Discover.light(item,inst,target,discovered)
                    Discover.cannon(target,inst,discovered,true)
                    filtered=p:SortActionList(discovered,target,item)
                """, mode)
                self.assertEqual(self.lua.eval("#discovered"), 3)
                self.assertEqual(self.lua.eval("#filtered"), 3 if mode == "normal" else 0)

    def test_projectile_deploy_aliases_cannot_bypass_toss_lock_on_server(self):
        for mode in ("string", "protect"):
            for name in DEPLOY:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("Prepare();SetLock(...)", mode)
                    self.assertFalse(self.lua.eval("Perform(...)", name))
                    self.assertEqual(self.lua.eval("effects"), 0)

    def test_projectile_deploy_aliases_are_filtered_by_client_tag(self):
        for mode in ("string", "protect"):
            for name in DEPLOY:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("Prepare();SetLock(...);item.components={};TheWorld.ismastersim=false", mode)
                    self.assertFalse(self.lua.eval("Offered(...)", name))

    def test_ordinary_deploy_is_still_allowed_in_both_locks(self):
        for mode in ("normal", "string", "protect"):
            for name in DEPLOY:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("""
                        Prepare();SetLock(...);item.components.complexprojectile=nil
                        item.tags.complexprojectile=nil;item.tags.projectile=nil
                    """, mode)
                    self.assertTrue(self.lua.eval("Offered(...)", name))
                    self.assertTrue(self.lua.eval("Perform(...)", name))
                    self.assertGreater(self.lua.eval("effects"), 0)

    def test_unlock_restores_native_projectile_deploy(self):
        for name in DEPLOY:
            with self.subTest(action=name):
                self.lua.execute("Prepare();SetLock('normal')")
                self.assertTrue(self.lua.eval("Offered(...)", name))
                self.assertTrue(self.lua.eval("Perform(...)", name))
                self.assertEqual(self.lua.eval("effects"), 1)

    def test_pickup_eating_building_and_cancelling_tools_are_preserved(self):
        for mode in ("string", "protect"):
            for name in ALLOWED:
                with self.subTest(mode=mode, action=name):
                    self.lua.execute("Prepare();SetLock(...)", mode)
                    self.assertTrue(self.lua.eval("Offered(...)", name))
                    self.assertTrue(self.lua.eval("Perform(...)", name))

    def test_native_toolactions_and_existing_action_filters_still_apply(self):
        self.lua.execute("Prepare();SetLock('string')")
        for name in ("PLAY", "UNSADDLE"):
            with self.subTest(action=name):
                self.assertFalse(self.lua.eval("Offered(...)", name))
        self.lua.execute("SetLock('normal');p:PushActionFilter(function()return false end,999)")
        self.assertFalse(self.lua.eval("Offered('TOSS')"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
