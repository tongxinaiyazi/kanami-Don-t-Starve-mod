"""Execute installed DST Open and HappyPatch's real button hooks in both orders.

Only graphics nodes are fixtures. No game process or deployed mod is touched.
"""
import unittest

import test_bag
import test_bag_client

HAPPY = test_bag.GAME.parents[1] / "workshop/content/322330/2886753796"
MODULE = test_bag.ROOT / "mods/klbq_kanami/scripts/klbq_kanami/bag.lua"


class BagButtons(unittest.TestCase):
    def setUp(self):
        fixture = test_bag_client.BagClient()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute("""
            happyhooks={};ourhooks={}
            AddClassPostConstruct=function(n,fn)happyhooks[n]=fn end
            table.contains=function(list,value)for _,v in pairs(list)do if v==value then return true end end return false end
            BUTTONFONT='button';ANCHOR_MIDDLE=0;CONTROL_SECONDARY=1
            TUNING.DATA2HM={opensort=true};TUNING.TEMP2HM={btnotherdir={}};TUNING.isCh2hm=true
            TheInput={GetLocalizedControl=function()return 'right' end,GetControllerID=function()return 0 end}
            SetButtonRightControl=function()end;SaveTemp2hm=function()end
            clicks=0
            function Node(name)
                local n={name=name,children={},shown=true,clickable=true,enabled=true}
                n.inst={entity={SetParent=function()end},ListenForEvent=function()end}
                n.image=setmetatable({}, {__index=function()return function()end end})
                n.text=setmetatable({}, {__index=function()return function()end end})
                n.AddChild=function(s,c)s.children[c]=c;c.parent=s;return c end
                n.Hide=function(s)s.shown=false end;n.Show=function(s)s.shown=true end
                n.Disable=function(s)s.enabled=false end;n.Enable=function(s)s.enabled=true end
                n.SetClickable=function(s,v)s.clickable=v end
                n.SetOnClick=function(s,fn)s.onclick=fn end
                n.OnControl=function(s)if s.onclick then s.onclick()end;return true end
                n.Kill=function(s)s.killed=true;s.shown=false end
                n.SetText=function(s,text)s.name=text end -- Native Button:SetText renames the widget.
                for _,method in ipairs({'SetPosition','SetFont','SetDisabledFont','SetTextSize','SetTooltip','SetScale'})do
                    n[method]=function()end
                end
                return n
            end
            ImageButton=function()return Node('BUTTON')end -- Native Button ctor ignores ImageButton's name argument.
            Widget=function(n)return Node(n)end
            InvSlot=function()local n=Node('InvSlot');n.SetOnClick=nil;return n end
            screen.children={};screen.Open=ContainerWidget.Open
            screen.name='ContainerWidget';screen.container=nil
            owner.HasTag=function()return false end
            local params=require('containers').params
            params.klbq_singularity.widget.poslist2hm={positions={Vector3(0,0,0),Vector3(0,0,0),Vector3(0,0,0)}}
            plain=MakeEntity();plain.prefab='krampus_sack';plain.replica.container=client.replica.container
            root=Node('root')
            bar={root=root,owner=owner,integrated_backpack=true,backpackinv={}}
            owner.replica={inventory={GetOverflowContainer=function()return overflow end}}
            client.replica.container.IsOpenedBy=function()return true end
            bar.Rebuild=function(s)
                s.bottomrow=s.root:AddChild(Node('bottomrow'))
                for i=1,14 do s.backpackinv[i]=Node('InvSlot');s.backpackinv[i].GetPosition=function()return Vector3(0,0,0)end end
            end
            overflow=client.replica.container
        """)
        source = (HAPPY / "easy_other/containersort.lua").read_text(encoding="utf-8-sig")
        helper_start = source.index("    local function addbutton(self,")
        inventory_start = source.index('    AddClassPostConstruct("widgets/inventorybar",', helper_start)
        container_end = source.index("    -- 妥协衣柜处理", inventory_start)
        self.lua.execute("""
            local meatracklist={};local no_help_text=true
            local haslockbutton=true;local hascollectbutton=true;local hasmultisortbtn=false
            local function rightlockbtnfn()end
            local lockbtninfo={text1='锁定',text2='解锁',helptext1='',helptext2='',fn=function()clicks=clicks+1 end}
            local btnlist={lockbtn=lockbtninfo,
                sortbtn={text='整理',helptext='',fn=function()clicks=clicks+1 end},
                collectbtn={text='收集',helptext='',fn=function()clicks=clicks+1 end}}
        """ + source[helper_start:container_end])
        # Engine AddChild is unmodified; the child entity parent is a graphics fixture.
        import zipfile
        with zipfile.ZipFile(test_bag.GAME / "data/databundles/scripts.zip") as archive:
            widget = archive.read("scripts/widgets/widget.lua").decode("utf-8-sig")
        start = widget.index("function Widget:AddChild(child)")
        end = widget.index("function Widget:Hide()", start)
        self.lua.execute("NativeWidget={};" + widget[start:end].replace("Widget:AddChild", "NativeWidget:AddChild"))
        self.lua.execute("screen.AddChild=NativeWidget.AddChild;root.AddChild=NativeWidget.AddChild")
        if MODULE.exists():
            self.lua.execute("require('klbq_kanami/bag').Install({GLOBAL=_G,AddComponentPostInit=function()end,"
                             "AddClassPostConstruct=function(n,fn)ourhooks[n]=fn end})")

    def hooks(self, widget, order):
        self.lua.execute("""
            function OurHook(path,object)if ourhooks[path]then ourhooks[path](object)end end
        """)
        path, instance = ("widgets/containerwidget", "screen") if widget == "window" else ("widgets/inventorybar", "bar")
        for hook in order:
            self.lua.execute(("OurHook('" + path + "'," + instance + ")") if hook == "ours"
                             else "happyhooks['" + path + "'](" + instance + ")")

    def assert_buttons_suppressed(self, instance):
        for name in ("lockbutton2hm", "sortbutton2hm", "collectbutton2hm"):
            self.lua.execute("current=" + instance + "." + name)
            self.assertTrue(self.lua.eval("current~=nil"), "real HappyPatch did not create " + name)
            self.lua.execute("current:Show();current:Enable();current:OnControl(0,false);if current.onclick then current.onclick()end")
            self.assertFalse(self.lua.eval("current.shown"), name + " became visible")
        self.assertEqual(self.lua.eval("clicks"), 0)

    def test_real_happy_buttons_cannot_appear_or_click_on_own_window_in_either_order(self):
        for order in (("ours", "happy"), ("happy", "ours")):
            with self.subTest(order=order):
                self.setUp()
                self.hooks("window", order)
                self.lua.execute("screen:Open(client,owner)")
                self.assertEqual(self.lua.eval("#screen.inv"), 14)
                self.assert_buttons_suppressed("screen")
                self.lua.execute("screen:Open(plain,owner)")
                self.assertTrue(self.lua.eval("screen.sortbutton2hm.shown"))
                self.lua.execute("screen.sortbutton2hm.onclick()")
                self.assertEqual(self.lua.eval("clicks"), 1)

    def test_real_integrated_backpack_buttons_stay_suppressed_across_rebuilds(self):
        for order in (("ours", "happy"), ("happy", "ours")):
            with self.subTest(order=order):
                self.setUp()
                self.hooks("bar", order)
                for _ in range(2):
                    self.lua.execute("bar:Rebuild()")
                    self.assert_buttons_suppressed("bar.bottomrow")
                self.lua.execute("overflow={inst=plain,IsOpenedBy=function()return true end,GetWidget=function()return client.replica.container:GetWidget()end,GetNumSlots=function()return 14 end};bar:Rebuild()")
                self.assertTrue(self.lua.eval("bar.bottomrow.sortbutton2hm.shown"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
