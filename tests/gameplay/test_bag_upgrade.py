"""Run eyeball upgrading through installed DST Trader, GIVE, and gear getters."""
import unittest

import test_bag
from test_review_regressions import vanilla


class SingularityEyeballUpgrade(unittest.TestCase):
    setUp = test_bag.SingularityBag.setUp

    def _trader(self):
        self.assertTrue(self.lua.eval("bag.components.trader ~= nil"),
                        "the bag must accept a deerclops eyeball through native Trader")
        self.lua.execute("""
            function MakeGift(prefab,count)
                local item=MakeEntity();item.prefab=prefab
                item:AddComponent('inventoryitem')
                item:AddComponent('stackable')
                item.components.stackable:SetStackSize(count or 1)
                return item
            end
            SpawnPrefab=function(prefab) return MakeGift(prefab,1) end
            giver=MakeEntity()
            eye=MakeGift('deerclops_eyeball',3)
            eye.components.inventoryitem.owner=giver
        """)

    def _upgrade(self):
        self._trader()
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,eye)"))

    def _native_gear_getters(self):
        for name, component, method in (
            ("components/inventory", "Inventory", "GetWaterproofness"),
            ("components/inventory", "Inventory", "IsInsulated"),
            ("components/temperature", "Temperature", "GetInsulation"),
            ("components/equippable", "Equippable", "IsInsulated"),
        ):
            source = self.native[name]
            start = source.index("function " + component + ":" + method + "(")
            end = source.index("\nfunction ", start + 1)
            self.lua.execute(component + "=" + component + " or {};" + source[start:end])
        self.lua.execute("""
            gear={inst={components={}},equipslots={}}
            gear.isexternallyinsulated={Get=function() return false end}
            gear.GetItemInSlot=function(s,slot) return s.equipslots[slot] end
            bag.components.equippable.IsInsulated=Equippable.IsInsulated
            thermometer={inst={components={inventory=gear}},
                inherentinsulation=0,inherentsummerinsulation=0}
        """)

    def test_unupgraded_network_flag_is_false_on_both_sides_before_server_components(self):
        self.assertTrue(self.lua.eval("bag._klbq_eyeball ~= nil"), "upgrade must have a network flag")
        self.assertFalse(self.lua.eval("bag._klbq_eyeball:value()"))
        self.assertTrue(self.lua.eval("bag:HasTag('trader')"))
        self.assertTrue(self.lua.eval("bag.components.waterproofer == nil and bag.components.insulator == nil"))
        self.lua.execute("TheWorld.ismastersim=false;clientbag=bagprefab.fn()")
        self.assertTrue(self.lua.eval("clientbag._klbq_eyeball ~= nil"))
        self.assertFalse(self.lua.eval("clientbag._klbq_eyeball:value()"))
        self.assertTrue(self.lua.eval("clientbag.pristine and clientbag:HasTag('trader')"))
        self.assertTrue(self.lua.eval("next(clientbag.components)==nil"))

    def test_native_trader_consumes_one_eyeball_and_keeps_hat_upgrade_available(self):
        self._upgrade()
        self.assertEqual(self.lua.eval("eye.components.stackable:StackSize()"), 2)
        self.assertFalse(self.lua.eval("eye.removed == true"))
        self.assertTrue(self.lua.eval("bag._klbq_eyeball:value()"))
        self.assertFalse(self.lua.eval("bag.components.trader:AcceptGift(giver,eye)"))
        self.assertEqual(self.lua.eval("eye.components.stackable:StackSize()"), 2)
        self.assertTrue(self.lua.eval("bag:HasTag('trader') and bag.components.trader.enabled"))

    def test_last_eyeball_is_removed_and_other_items_are_refused_without_consumption(self):
        self._trader()
        self.lua.execute("wrong=MakeGift('meat',4);wrong.components.inventoryitem.owner=giver")
        self.assertFalse(self.lua.eval("bag.components.trader:AcceptGift(giver,wrong)"))
        self.assertEqual(self.lua.eval("wrong.components.stackable:StackSize()"), 4)
        self.assertTrue(self.lua.eval("wrong.components.inventoryitem.owner==giver and not wrong.removed"))
        self.lua.execute("single=MakeGift('deerclops_eyeball',1);single.components.inventoryitem.owner=giver")
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,single)"))
        self.assertTrue(self.lua.eval("single.removed and single.components.inventoryitem.removedfromowner"))

    def test_native_give_action_and_discovery_work_on_ground_and_owned_bag(self):
        self._trader()
        self.lua.execute(vanilla('componentutil.lua','function IsItemInReadOnlyContainer(')+'\n'
                         + vanilla('componentutil.lua','function ShouldItemMimicBeRevealedFor('))
        source = self.native["actions"]
        give = source[source.index("ACTIONS.GIVE.fn ="):source.index("ACTIONS.GIVETOPLAYER.fn =")]
        self.lua.execute("ACTIONS={GIVE={}};local ShouldBlockGiving=function() return false end;" + give)
        source = self.native["componentactions"]
        trade = source[source.index("        tradable = function("):source.index("        treegrowthsolution = function(")]
        self.lua.execute("discover=({" + trade + "}).tradable")
        for owned in (False, True):
            with self.subTest(owned=owned):
                self.lua.execute("""
                    target=bagprefab.fn()
                    target.components.inventoryitem.owner=... and giver or nil
                    available={};discover(eye,giver,target,available,true)
                """, owned)
                self.assertTrue(self.lua.eval("available[1]==ACTIONS.GIVE"))
                self.assertTrue(self.lua.eval("ACTIONS.GIVE.fn({doer=giver,target=target,invobject=eye})"))
                self.assertFalse(self.lua.eval("(ACTIONS.GIVE.fn({doer=giver,target=target,invobject=eye}))"))
        self.assertEqual(self.lua.eval("eye.components.stackable:StackSize()"), 1)

    def test_upgrade_has_exact_eyebrella_rain_and_summer_values_only_while_equipped(self):
        self._native_gear_getters()
        self.assertEqual(self.lua.eval("Inventory.GetWaterproofness(gear)"), 0)
        self._upgrade()
        native_hat = self.native["prefabs/hats"]
        block = native_hat[native_hat.index("    fns.eyebrella = function()"):native_hat.index("    local function balloon_onequip")]
        self.assertIn("SetEffectiveness(TUNING.WATERPROOFNESS_ABSOLUTE)", block)
        self.assertIn("SetInsulation(TUNING.INSULATION_LARGE)", block)
        self.assertIn("inst.components.insulator:SetSummer()", block)
        self.assertEqual(self.lua.eval("bag.components.waterproofer:GetEffectiveness()"), self.lua.eval("TUNING.WATERPROOFNESS_ABSOLUTE"))
        self.assertEqual(self.lua.eval("bag.components.insulator:GetInsulation()"),
                         (self.lua.eval("TUNING.INSULATION_LARGE"), "summer"))
        self.assertEqual(self.lua.eval("Inventory.GetWaterproofness(gear)"), 0)
        self.assertEqual(self.lua.eval("Temperature.GetInsulation(thermometer)"), (0, 0))
        for extra in (False, True):
            with self.subTest(extra_back_slot=extra):
                self.lua.execute("""
                    EQUIPSLOTS.BACK=... and 'extra_slots_back' or nil
                    gear.equipslots[EQUIPSLOTS.BACK or EQUIPSLOTS.BODY]=bag
                """, extra)
                self.assertEqual(self.lua.eval("Inventory.GetWaterproofness(gear)"), 1)
                self.assertEqual(self.lua.eval("Temperature.GetInsulation(thermometer)"), (0, 240))
                self.lua.execute("gear.equipslots={}")
                self.assertEqual(self.lua.eval("Inventory.GetWaterproofness(gear)"), 0)
                self.assertEqual(self.lua.eval("Temperature.GetInsulation(thermometer)"), (0, 0))
        self.assertTrue(self.lua.eval("bag.components.fueled==nil and bag.components.finiteuses==nil"))
        self.assertTrue(self.lua.eval("bag.components.equippable.insulated==true"))

    def test_native_electrical_insulation_matches_eyebrella_only_after_upgrade_when_worn(self):
        self._native_gear_getters()
        self.lua.execute("gear.equipslots[bag.equipslot]=bag")
        self.assertFalse(self.lua.eval("Inventory.IsInsulated(gear)"))
        self._upgrade()
        source = self.native["prefabs/hats"]
        eyebrella = source[source.index("    fns.eyebrella = function()"):source.index("    local function balloon_onequip")]
        self.assertIn("inst.components.equippable.insulated = true", eyebrella)
        self.assertTrue(self.lua.eval("bag.components.equippable:IsInsulated()"))
        self.assertTrue(self.lua.eval("Inventory.IsInsulated(gear)"))
        self.assertFalse(self.lua.eval("bag.components.trader:AcceptGift(giver,eye)"))
        self.assertTrue(self.lua.eval("Inventory.IsInsulated(gear)"))
        self.lua.execute("gear.force_no_insulation=true")
        self.assertFalse(self.lua.eval("Inventory.IsInsulated(gear)"))
        self.lua.execute("gear.force_no_insulation=nil;gear.equipslots={}")
        self.assertFalse(self.lua.eval("Inventory.IsInsulated(gear)"))

    def test_upgrading_an_owned_bag_refreshes_character_ability_immediately(self):
        self._trader()
        self.lua.execute("""
            refreshes=0;syncs=0
            owner=MakeEntity()
            owner.components.klbq_kanami={ApplyString=function(s) refreshes=refreshes+1 end,
                Sync=function(s) assert(refreshes==1);syncs=syncs+1 end}
            bag.components.inventoryitem.owner=owner
        """)
        self.assertTrue(self.lua.eval("bag.components.trader:AcceptGift(giver,eye)"))
        self.assertEqual(self.lua.eval("refreshes"), 1)
        self.assertEqual(self.lua.eval("syncs"), 1)

    def test_save_reload_preserves_upgrade_and_native_container_food(self):
        self._upgrade()
        self.assertTrue(self.lua.eval("type(bag.OnSave)=='function' and type(bag.OnLoad)=='function'"))
        self.lua.execute("""
            food=MakeFood(4800,.25);food.components.perishable:LongUpdate(480)
            food.prefab='food';food.GetSaveRecord=function(s)
                return {prefab='food',perishable=s.components.perishable:OnSave()}
            end
            assert(bag.components.container:GiveItem(food,14))
            data={};bag:OnSave(data)
            containerdata=bag.components.container:OnSave()
            SpawnSaveRecord=function(record)
                local item=MakeFood(4800,1)
                item.components.perishable:OnLoad(record.perishable)
                return item
            end
            restored=bagprefab.fn();restored:OnLoad(data)
            restored.components.container:OnLoad(containerdata,{})
            restoredfood=restored.components.container:GetItemInSlot(14)
            restoredfood.components.perishable:LongUpdate(480)
        """)
        self.assertTrue(self.lua.eval("restored._klbq_eyeball:value()"))
        self.assertFalse(self.lua.eval("restored.components.trader:AcceptGift(giver,eye)"))
        self.assertEqual(self.lua.eval("restored.components.container.numslots"), 14)
        self.assertEqual(self.lua.eval("restored.components.waterproofer:GetEffectiveness()"), 1)
        self.assertEqual(self.lua.eval("restored.components.insulator:GetInsulation()"), (240, "summer"))
        self.assertTrue(self.lua.eval("restored.components.equippable.insulated==true"))
        self.assertAlmostEqual(self.lua.eval("restoredfood.components.perishable:GetPercent()"), .27)
        self.assertTrue(self.lua.eval("restoredfood.components.inventoryitem.owner==restored"))

    def test_loading_legacy_data_does_not_grant_upgrade(self):
        self.assertTrue(self.lua.eval("type(bag.OnLoad)=='function'"))
        self.lua.execute("bag:OnLoad({})")
        self.assertFalse(self.lua.eval("bag._klbq_eyeball:value()"))
        self.assertTrue(self.lua.eval("bag.components.trader.enabled"))
        self.assertTrue(self.lua.eval("bag.components.waterproofer==nil and bag.components.insulator==nil"))
        self.assertFalse(self.lua.eval("bag.components.equippable.insulated==true"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
