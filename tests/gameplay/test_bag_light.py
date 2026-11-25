"""Run miner-hat upgrades through native Trader and bag lifecycle callbacks."""
import unittest

import test_bag
import test_bag_upgrade


class SingularityMinerHatUpgrade(unittest.TestCase):
    def setUp(self):
        test_bag.SingularityBag.setUp(self)
        test_bag_upgrade.SingularityEyeballUpgrade._trader(self)
        self.lua.execute("""
            lights={}
            local spawn=SpawnPrefab
            SpawnPrefab=function(prefab)
                if prefab~='minerhatlight' then return spawn(prefab) end
                local light=MakeEntity();light.prefab=prefab
                light.IsValid=function(s)return not s.removed end
                light.entity.SetParent=function(_,parent)light.parent=parent end
                light.Light={SetRadius=function(_, radius) light.radius=radius end}
                lights[#lights+1]=light
                return light
            end
            function Wear(target,owner)
                target.components.inventoryitem.owner=owner
                target.components.equippable.equipped=true
                target.components.equippable.onequipfn(target,owner)
            end
            function Unwear(target,owner)
                target.components.equippable.equipped=false
                target.components.equippable.onunequipfn(target,owner)
            end
            function Gift(target,name,count)
                local gift=MakeGift(name,count or 1)
                gift.components.inventoryitem.owner=giver
                return target.components.trader:AcceptGift(giver,gift), gift
            end
            hat=MakeGift('minerhat',1)
            hat.components.stackable=nil
            hat.components.fueled={GetPercent=function()return 0 end}
            hat.components.inventoryitem.owner=giver
        """)

    def test_hat_is_consumed_once_without_fuel_requirement_or_ground_light(self):
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,hat)"))
        self.assertTrue(self.lua.eval("hat.removed and hat.components.inventoryitem.removedfromowner"))
        self.assertTrue(self.lua.eval("bag._klbq_minerhat:value()"))
        self.assertEqual(self.lua.eval("#lights"), 0)
        self.lua.execute("again=MakeGift('minerhat',3);again.components.inventoryitem.owner=giver")
        self.assertFalse(self.lua.eval("bag.components.trader:AcceptGift(giver,again)"))
        self.assertEqual(self.lua.eval("again.components.stackable:StackSize()"), 3)
        self.assertTrue(self.lua.eval("not again.removed and again.components.inventoryitem.owner==giver"))

    def test_light_only_exists_while_worn_and_follows_each_owner(self):
        self.lua.execute("assert(bag.components.trader:AcceptGift(giver,hat));Wear(bag,giver)")
        self.assertEqual(self.lua.eval("#lights"), 1)
        self.assertTrue(self.lua.eval("lights[1].parent==giver.entity and not lights[1].removed"))
        self.lua.execute("Wear(bag,giver)")
        self.assertEqual(self.lua.eval("#lights"), 1, "repeated equip must not duplicate light")
        self.lua.execute("Unwear(bag,giver);bag.components.inventoryitem.owner=nil")
        self.assertTrue(self.lua.eval("lights[1].removed"))
        self.lua.execute("other=MakeEntity();Wear(bag,other)")
        self.assertEqual(self.lua.eval("#lights"), 2)
        self.assertTrue(self.lua.eval("lights[2].parent==other.entity and not lights[2].removed"))
        self.lua.execute("bag.components.equippable.onequiptomodelfn(bag,other)")
        self.assertTrue(self.lua.eval("lights[2].removed"))
        self.assertTrue(self.lua.eval("bag.components.fueled==nil and bag.components.finiteuses==nil"))

    def test_upgrade_while_equipped_lights_immediately_and_removal_cleans_it(self):
        self.lua.execute("Wear(bag,giver)")
        self.assertEqual(self.lua.eval("#lights"), 0)
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,hat)"))
        self.assertEqual(self.lua.eval("#lights"), 1)
        self.lua.execute("bag:PushEvent('onremove')")
        self.assertTrue(self.lua.eval("lights[1].removed"))

    def test_eyeball_and_hat_can_be_given_in_either_order(self):
        for first, second in (("hat", "eye"), ("eye", "hat")):
            with self.subTest(first=first):
                self.setUp()
                self.assertTrue(self.lua.eval(f"bag.components.trader:AcceptGift(giver,{first})"))
                self.assertTrue(self.lua.eval("bag.components.trader.enabled and bag:HasTag('trader')"))
                self.assertTrue(self.lua.eval(f"bag.components.trader:AcceptGift(giver,{second})"))
                self.assertTrue(self.lua.eval("bag._klbq_eyeball:value() and bag._klbq_minerhat:value()"))
                self.assertTrue(self.lua.eval("bag.components.trader.enabled"))
                self.assertTrue(self.lua.eval("bag.components.waterproofer:GetEffectiveness()==1"))

    def test_save_reload_restores_both_upgrades_but_only_equipped_lights(self):
        self.lua.execute("""
            assert(bag.components.trader:AcceptGift(giver,hat))
            assert(bag.components.trader:AcceptGift(giver,eye))
            saved={};bag:OnSave(saved)
            restored=bagprefab.fn();restored:OnLoad(saved)
        """)
        self.assertTrue(self.lua.eval("saved.klbq_minerhat and saved.klbq_eyeball"))
        self.assertTrue(self.lua.eval("restored._klbq_minerhat:value() and restored._klbq_eyeball:value()"))
        self.assertEqual(self.lua.eval("#lights"), 0)
        self.lua.execute("Wear(restored,giver)")
        self.assertEqual(self.lua.eval("#lights"), 1)
        self.assertTrue(self.lua.eval("lights[1].parent==giver.entity"))
        self.assertTrue(self.lua.eval("restored.components.trader.enabled"))

    def test_tiers_consume_one_gem_at_a_time_and_survive_save(self):
        self.lua.execute("Wear(bag,giver)")
        self.assertFalse(self.lua.eval("(Gift(bag,'bluegem'))"))
        self.assertFalse(self.lua.eval("(Gift(bag,'klbq_ember_core'))"))
        self.assertTrue(self.lua.eval("(Gift(bag,'redgem'))"))
        self.assertAlmostEqual(self.lua.eval("bag.components.armor.absorb_percent"), .02)
        self.lua.execute("""
            for i=2,45 do assert(Gift(bag,'redgem')) end
            excessRubyOK,excessRuby=Gift(bag,'redgem',2)
            assert(Gift(bag,'minerhat'))
            for i=1,4 do assert(Gift(bag,'bluegem')) end
        """)
        self.assertFalse(self.lua.eval("excessRubyOK"))
        self.assertEqual(self.lua.eval("excessRuby.components.stackable:StackSize()"), 2)
        self.assertAlmostEqual(self.lua.eval("bag.components.armor.absorb_percent"), .9)
        self.assertEqual(self.lua.eval("lights[1].radius"), 4.5)
        self.assertFalse(self.lua.eval("(Gift(bag,'klbq_ember_core'))"))
        self.lua.execute("""
            accepted,blues=Gift(bag,'bluegem',2)
            assert(accepted)
            assert(not Gift(bag,'bluegem'))
        """)
        self.assertEqual(self.lua.eval("blues.components.stackable:StackSize()"), 1)
        self.assertEqual(self.lua.eval("lights[1].radius"), 5)
        self.lua.execute("""
            assert(Gift(bag,'klbq_ember_core'))
            assert(not Gift(bag,'klbq_ember_core'))
            assert(Gift(bag,'deerclops_eyeball'))
            saved={};bag:OnSave(saved)
            restored=bagprefab.fn();restored:OnLoad(saved);Wear(restored,giver)
        """)
        self.assertEqual(self.lua.eval("lights[1].radius"), 5.5)
        self.assertEqual(self.lua.eval("lights[2].radius"), 5.5)
        self.assertAlmostEqual(self.lua.eval("restored.components.armor.absorb_percent"), .9)
        self.assertTrue(self.lua.eval("restored.components.armor:IsIndestructible()"))
        self.assertFalse(self.lua.eval("restored.components.trader.enabled"))

    def test_legacy_eyeball_save_keeps_hat_upgrade_available_without_free_light(self):
        self.lua.execute("bag:OnLoad({klbq_eyeball=true});Wear(bag,giver)")
        self.assertFalse(self.lua.eval("bag._klbq_minerhat:value()"))
        self.assertEqual(self.lua.eval("#lights"), 0)
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,hat)"))
        self.assertEqual(self.lua.eval("#lights"), 1)

    def test_client_has_upgrade_flag_before_pristine_and_no_server_components(self):
        self.lua.execute("TheWorld.ismastersim=false;clientbag=bagprefab.fn()")
        self.assertTrue(self.lua.eval("clientbag.pristine and clientbag._klbq_minerhat~=nil"))
        self.assertFalse(self.lua.eval("clientbag._klbq_minerhat:value()"))
        self.assertTrue(self.lua.eval("next(clientbag.components)==nil"))
        self.assertEqual(self.lua.eval("#lights"), 0)


if __name__ == "__main__":
    unittest.main()
