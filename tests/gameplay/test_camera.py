import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime
class Camera(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  p=ROOT/'mods/klbq_kanami/scripts/klbq_kanami/camera.lua'
  self.assertTrue(p.exists(),'missing camera ownership implementation')
  self.module=self.lua.execute(p.read_text(encoding='utf-8-sig'))
  self.lua.execute('camera={distancetarget=30,maxdist=50,maxdistpitch=60,SetDistance=function(s,v) s.distancetarget=v end,ZoomIn=function(s) s.distancetarget=s.distancetarget-4 end,ZoomOut=function(s) s.distancetarget=s.distancetarget+4 end}')
 def test_restores_prior_camera_after_zoom(self):
  session=self.module.Start(self.lua.globals().camera,80)
  self.lua.execute('camera:ZoomOut()')
  self.module.Stop(session)
  self.assertEqual(self.lua.eval('camera.distancetarget'),30);self.assertEqual(self.lua.eval('camera.maxdist'),50)
 def test_leaves_other_mod_new_camera_distance(self):
  session=self.module.Start(self.lua.globals().camera,80)
  self.lua.execute('camera:SetDistance(99);camera.maxdist=150')
  self.module.Stop(session)
  self.assertEqual(self.lua.eval('camera.distancetarget'),99);self.assertEqual(self.lua.eval('camera.maxdist'),150)
if __name__=='__main__':unittest.main(verbosity=2)
