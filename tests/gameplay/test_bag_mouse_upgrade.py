"""Exercise native mouse action discovery before the GIVE implementation."""
import re
import unittest

import test_bag
import test_bag_light


class BagMouseUpgrade(unittest.TestCase):
    def setUp(self):
        test_bag_light.SingularityMinerHatUpgrade.setUp(self)
        source = self.native["componentactions"]
        source = source[source.index("    USEITEM ="):]
        start = source.index("        inventoryitem = function(")
        end = re.search(r"\n        \w+ = function", source[start + 1:]).start() + start + 1
        callback = source[start:end].strip().removeprefix("inventoryitem = ").rstrip(",")
        self.lua.execute("NativeInventoryUse=" + callback)
        imprint = test_bag.ROOT / "mods/klbq_kanami/scripts/klbq_kanami/imprint.lua"
        self.lua.execute("package.preload['klbq_kanami/imprint']=function() "
                         + imprint.read_text(encoding="utf-8") + " end")
        self.lua.execute("""
            ACTIONS={GIVE={},STORE={}}
            Action=function(value)return value end
            ActionHandler=function()return {} end
            registrations=0
            require('klbq_kanami/imprint').Install({GLOBAL=_G,
                AddAction=function()end,AddStategraphActionHandler=function()end,
                AddComponentAction=function(kind,component,fn)
                    assert(kind=='USEITEM' and component=='inventoryitem')
                    registrations=registrations+1;CollectModUse=fn
                end},require('klbq_kanami/bag').CollectUpgradeAction)
            function PrepareTarget(target)
                target.replica.container.CanBeOpened=function()return true end
                target.replica.container.IsReadOnlyContainer=function()return false end
                return target
            end
            PrepareTarget(bag)
            hat.replica.inventoryitem={CanOnlyGoInPocket=function()return false end,
                IsLockedInSlot=function()return false end,
                CanOnlyGoInPocketOrPocketContainers=function()return false end,
                IsGrandOwner=function()return true end}
            function Collect(target,item,right)
                local actions={}
                NativeInventoryUse(item,giver,target,actions,right)
                CollectModUse(item,giver,target,actions,right)
                return actions
            end
        """)

    def test_minerhat_offers_give_instead_of_store_for_both_mouse_buttons(self):
        self.assertTrue(self.lua.eval("hat.components.tradable==nil"))
        for right in (False, True):
            with self.subTest(right=right):
                self.lua.execute("choices=Collect(bag,hat,...)", right)
                self.assertTrue(self.lua.eval("#choices==1 and choices[1]==ACTIONS.GIVE"),
                                "pending minerhat upgrade must replace native container STORE with GIVE")
        self.assertEqual(self.lua.eval("registrations"), 1,
                         "bag and imprint must share the single native inventoryitem action hook")

    def test_client_without_server_components_can_offer_upgrade(self):
        self.lua.execute("TheWorld.ismastersim=false;client=PrepareTarget(bagprefab.fn())")
        self.assertTrue(self.lua.eval("next(client.components)==nil"))
        self.lua.execute("choices=Collect(client,hat,false)")
        self.assertTrue(self.lua.eval("choices[1]==ACTIONS.GIVE"))

    def test_existing_eyeball_upgrade_still_offers_hat_and_completed_hat_can_be_stored(self):
        self.lua.execute("bag:OnLoad({klbq_eyeball=true});choices=Collect(bag,hat,false)")
        self.assertTrue(self.lua.eval("choices[1]==ACTIONS.GIVE"))
        self.lua.execute("assert(bag.components.trader:AcceptGift(giver,hat))")
        self.lua.execute("replacement=MakeGift('minerhat',1);replacement.replica.inventoryitem=hat.replica.inventoryitem")
        self.lua.execute("choices=Collect(bag,replacement,false)")
        self.assertTrue(self.lua.eval("#choices==1 and choices[1]==ACTIONS.STORE"))

    def test_other_items_keep_native_store(self):
        self.lua.execute("food=MakeGift('berries',1);food.replica.inventoryitem=hat.replica.inventoryitem")
        self.lua.execute("choices=Collect(bag,food,false)")
        self.assertTrue(self.lua.eval("#choices==1 and choices[1]==ACTIONS.STORE"))

    def test_trader_tags_keep_pending_gem_upgrades_available(self):
        self.assertTrue(self.lua.eval("bag:HasTag('alltrader') and bag.components.trader.acceptnontradable"))
        self.lua.execute("assert(bag.components.trader:AcceptGift(giver,hat));assert(bag.components.trader:AcceptGift(giver,eye))")
        self.assertTrue(self.lua.eval("bag:HasTag('trader') and bag:HasTag('alltrader')"))
        self.lua.execute("TheWorld.ismastersim=false;client=bagprefab.fn()")
        self.assertTrue(self.lua.eval("client:HasTag('alltrader')"))

    def test_blue_gems_offer_give_only_between_hat_and_five_gems(self):
        self.lua.execute("blue=MakeGift('bluegem',1);blue.replica.inventoryitem=hat.replica.inventoryitem")
        self.assertTrue(self.lua.eval("Collect(bag,blue,true)[1]==ACTIONS.STORE"))
        self.lua.execute("assert(bag.components.trader:AcceptGift(giver,hat))")
        self.assertTrue(self.lua.eval("Collect(bag,blue,true)[1]==ACTIONS.GIVE"))
        self.lua.execute("""
            for i=1,5 do assert(Gift(bag,'bluegem')) end
        """)
        self.assertTrue(self.lua.eval("Collect(bag,blue,true)[1]==ACTIONS.STORE"))


if __name__ == "__main__":
    unittest.main()
