import sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class HUD(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  with zipfile.ZipFile("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip") as z:
   self.lua.execute(z.read('scripts/class.lua').decode('utf-8-sig'))
  self.lua.execute('package.preload["klbq_kanami/rules"]=function() '+(ROOT/'mods/klbq_kanami/scripts/klbq_kanami/rules.lua').read_text(encoding='utf8')+' end')
  self.lua.execute('''
   ANCHOR_LEFT=0;SCALEMODE_PROPORTIONAL=1;BODYTEXTFONT='body';EQUIPSLOTS={HANDS='hands'}
   Widget=Class(function(self,name) self.name=name;self.children={} end)
   function Widget:AddChild(w)table.insert(self.children,w);return w end
   function Widget:SetPosition(x,y,z)self.position={x,y,z} end
   function Widget:SetScale(...)end
   function Widget:SetClickable(...)end
   function Widget:SetScaleMode(...)end
   function Widget:StartUpdating()end
   function Widget:Show()self.shown=true end
   function Widget:Hide()self.shown=false end
   Text=Class(Widget,function(self,f,s,t)Widget._ctor(self);self.text=t end)
   function Text:SetString(t)self.text=t end
   function Text:SetRegionSize(...)end
   function Text:SetColour(...)end
   Image=Class(Widget,function(self)Widget._ctor(self)end)
   function Image:SetSize(w,h)self.width=w;self.height=h end
   function Image:SetTint(...)end
   function Image:SetHRegPoint(...)end
   ImageButton=Class(Widget,function(self)Widget._ctor(self)end)
   function ImageButton:SetOnClick(fn)self.click=fn end
   function ImageButton:SetHoverText(...)end
   function ImageButton:SetTextures(a,n)self.texture=n end
   function ImageButton:SetImageNormalColour(...)end
   package.preload['widgets/widget']=function()return Widget end
   package.preload['widgets/text']=function()return Text end
   package.preload['widgets/image']=function()return Image end
   package.preload['widgets/imagebutton']=function()return ImageButton end
   function Net(v)return {v=v,value=function(s)return s.v end}end
   p={IsValid=function()return true end,HasTag=function(s,t)return t=='playerghost' and ghost end,
    replica={inventory={GetEquippedItem=function()return nil end}},
    AnimState={GetSymbolPosition=function(s,n,x,y,z)return 100,y,0 end}}
   for _,n in ipairs({'ztime','xtime','zcd','xcd','passivecd','revive','ammo','shotcd'})do p['_klbq_'..n]=Net(0)end
   p._klbq_string=Net(false);p._klbq_protect=Net(false);p._klbq_z=Net(false)
   TheNet={IsServerPaused=function()return paused end};TheSim={GetScreenPos=function(s,x,y,z)return x,y end}
  ''')
 def load(self,name):
  return self.lua.execute((ROOT/'mods/klbq_kanami/scripts/widgets'/name).read_text(encoding='utf-8'))
 def test_skill_strip_has_horizontal_icons_and_numeric_cooldowns(self):
  self.lua.globals().HUD=self.load('klbq_kanami_hud.lua')
  self.lua.execute('h=HUD(p,function()end,{c=99,z=122,x=120});p._klbq_z.v=true;h:OnUpdate()')
  self.assertEqual(self.lua.eval('h.cells.z.number.text'),'∞')
  self.assertEqual(self.lua.eval('h.cells.x.number.text'),'0')
  self.assertGreater(self.lua.eval('h.children[2].position[1]'),self.lua.eval('h.children[1].position[1]'))
  self.assertEqual(self.lua.eval('h.children[2].position[2]'),self.lua.eval('h.children[1].position[2]'))
  self.lua.execute('ghost=true;p._klbq_revive.v=431;h:OnUpdate()')
  self.assertEqual(self.lua.eval('h.cells.revive.number.text'),'44')
 def test_strip_contains_only_z_x_echo_and_revive_without_hidden_updates(self):
  self.lua.globals().HUD=self.load('klbq_kanami_hud.lua')
  self.lua.execute('''
   casts={};h=HUD(p,function(k)casts[#casts+1]=k end,{c=99,z=122,x=120})
   -- Omitted cells must not require either string or ammo state to update.
   p._klbq_string=nil;p._klbq_ammo=nil;p.replica.inventory=nil
   p._klbq_z.v=true;p._klbq_xtime.v=123;p._klbq_passivecd.v=12
   h:OnUpdate()
  ''')
  self.assertEqual(self.lua.eval('#h.children'),4)
  self.assertIsNone(self.lua.eval('h.cells.c'))
  self.assertIsNone(self.lua.eval('h.cells.ammo'))
  self.assertEqual(self.lua.eval('h.children[1].name'),'skill_z')
  self.assertEqual(self.lua.eval('h.children[4].name'),'skill_revive')
  self.assertEqual(self.lua.eval('h.cells.z.number.text'),'∞')
  self.assertEqual(self.lua.eval('h.cells.x.number.text'),'13')
  self.assertEqual(self.lua.eval('h.cells.passive.number.text'),'1.2')
  self.lua.execute('h.cells.z.button.click();h.cells.x.button.click()')
  self.assertEqual(self.lua.eval('casts[1]'),'z')
  self.assertEqual(self.lua.eval('casts[2]'),'x')
 def test_shotbar_follows_owner_interpolates_and_stops_when_paused_or_ready(self):
  self.lua.globals().Bar=self.load('klbq_kanami_shotbar.lua')
  self.lua.execute('b=Bar(p);b:OnUpdate(0)')
  self.assertFalse(self.lua.eval('b.shown'))
  self.lua.execute('p._klbq_shotcd.v=15;b:OnUpdate(0);b:OnUpdate(.75)')
  self.assertTrue(self.lua.eval('b.shown'))
  self.assertAlmostEqual(self.lua.eval('b.fill.width'),45)
  self.assertEqual(self.lua.eval('b.position[1]'),100)
  self.lua.execute('paused=true;b:OnUpdate(1)')
  self.assertAlmostEqual(self.lua.eval('b.remaining'),.75)
  self.lua.execute('paused=false;p._klbq_shotcd.v=0;b:OnUpdate(.1)')
  self.assertFalse(self.lua.eval('b.shown'))
  self.lua.execute('p._klbq_shotcd.v=30;ghost=true;b:OnUpdate(0)')
  self.assertFalse(self.lua.eval('b.shown'))

if __name__=='__main__':unittest.main(verbosity=2)
