"""Validate ground prefabs at their real client/server construction boundary."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class GroundFx(unittest.TestCase):
 def test_ground_radius_uses_anim_scale_without_double_transform_projection(self):
  for master in (False,True):
   lua=LuaRuntime(unpack_returned_tuples=True)
   lua.execute('''
    TheWorld={}; ANIM_ORIENTATION={OnGroundFixed=1}; LAYER_WORLD_BACKGROUND=2
    Asset=function()end; Prefab=function(name,fn)return {name=name,fn=fn}end
    package.preload['klbq_kanami/rules']=function()return {DomainScale=function()return 3 end}end
    function CreateEntity()
     local e={plays={},scale={1,1,1},tags={}}
     e.entity={AddTransform=function()end,AddAnimState=function()end,AddNetwork=function()end,SetPristine=function()end}
     e.Transform={SetScale=function(_,x,y,z)e.scale={x,y,z}end}
     e.AnimState=setmetatable({
      SetBank=function(_,b)e.bank=b end,SetBuild=function(_,b)e.build=b end,
      PlayAnimation=function(_,a,loop)table.insert(e.plays,{bank=e.bank,anim=a})end,
      SetScale=function(_,x,y)e.animscale={x,y}end,
     },{__index=function()return function()end end})
     e.AddTag=function()end;e.DoTaskInTime=function()end;e.Remove=function()end
     return e
    end
   ''')
   lua.globals().TheWorld.ismastersim=master
   prefabs=lua.execute((ROOT/'mods/klbq_kanami/scripts/prefabs/klbq_kanami_fx.lua').read_text(encoding='utf8'))
   for prefab,radius in [(prefabs[0],12),(prefabs[3],12),(prefabs[4],4.5)]:
    with self.subTest(master=master,prefab=prefab.name):
     inst=prefab.fn()
     self.assertEqual(list(inst.scale.values()),[1,1,1],
       'OnGroundFixed uniformly scaled transforms apply scale twice in the current renderer')
     self.assertAlmostEqual(inst.animscale[1],1.5*radius/4)
     self.assertAlmostEqual(inst.animscale[2],1.5*radius/4)
     self.assertEqual(len(inst.plays),1,'Do not queue an obsolete animation before changing banks')
     self.assertEqual(inst.plays[1].bank,'reticuleaoe')
     self.assertEqual(inst.plays[1].anim,'idle')
