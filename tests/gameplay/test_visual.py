import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class Visual(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  self.m=self.lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/visual.lua').read_text(encoding='utf8'))
  self.lua.execute('''
   local methods={GetBuild=function(s) return build end,SetBuild=function(s,b) build=b end,
     HideSymbol=function(s,k) hidden[k]=true end,ShowSymbol=function(s,k) hidden[k]=nil end,
     Hide=function(s,k) hidden[k]=true end,Show=function(s,k) hidden[k]=nil end,
     ClearOverrideSymbol=function(s,k) cleared[k]=true end}
   local anim=newproxy(true)
   getmetatable(anim).__index=methods
   getmetatable(anim).__newindex=function() error('native AnimState cannot be modified') end
   hidden={};cleared={};build='klbq_kanami';inst={AnimState=anim,armorabsorb=.8}
  ''')
 def test_equipment_hides_hat_body_backpack_and_restores_original_head(self):
  self.lua.execute('hidden.HEAD=true;hidden.HAIR=true')
  self.m.HideEquipment(self.lua.globals().inst)
  for symbol in ['swap_hat','swap_body','swap_body_tall','backpack','HAT','HEAD_HAT']:
   self.assertTrue(self.lua.eval('hidden[...]',symbol))
  self.assertIsNone(self.lua.eval('hidden.HEAD'))
  self.assertIsNone(self.lua.eval('hidden.HAIR'))
  self.assertEqual(self.lua.eval('inst.armorabsorb'),.8)
  self.assertIsNone(self.lua.eval('hidden.swap_object'))
 def test_equipment_hiding_preserves_paper_weapon_hiding_and_ghost_build(self):
  self.m.StringBuild(self.lua.globals().inst,True)
  self.m.HideEquipment(self.lua.globals().inst)
  self.assertTrue(self.lua.eval('hidden.swap_object'))
  self.lua.execute("inst.AnimState:SetBuild('ghost_klbq_kanami_build')")
  self.m.HideEquipment(self.lua.globals().inst)
  self.assertEqual(self.lua.eval('build'),'ghost_klbq_kanami_build')
 def test_complete_paper_build_without_native_scale_mutation(self):
  self.m.StringBuild(self.lua.globals().inst,True)
  self.assertEqual(self.lua.eval('build'),'klbq_kanami_string')
  self.m.StringBuild(self.lua.globals().inst,False)
  self.assertEqual(self.lua.eval('build'),'klbq_kanami')
 def test_keeps_later_ghost_or_external_build(self):
  self.m.StringBuild(self.lua.globals().inst,True)
  self.lua.execute("inst.AnimState:SetBuild('ghost_klbq_kanami_build')")
  self.m.StringBuild(self.lua.globals().inst,False)
  self.assertEqual(self.lua.eval('build'),'ghost_klbq_kanami_build')
 def test_paper_hides_floating_held_weapon_and_restores_it(self):
  self.m.StringBuild(self.lua.globals().inst,True)
  self.assertTrue(self.lua.eval("hidden.swap_object"))
  self.m.StringBuild(self.lua.globals().inst,False)
  self.assertIsNone(self.lua.eval("hidden.swap_object"))
 def test_restores_prior_skin_build_and_is_idempotent(self):
  self.lua.execute("inst.AnimState:SetBuild('compatible_skin')")
  self.m.StringBuild(self.lua.globals().inst,True)
  self.m.StringBuild(self.lua.globals().inst,True)
  self.m.StringBuild(self.lua.globals().inst,False)
  self.assertEqual(self.lua.eval('build'),'compatible_skin')

 def bind_hands(self,prefab,client=False,tool=False):
  self.lua.globals().handprefab=prefab
  self.lua.globals().handtool=tool
  self.lua.execute('''
   EQUIPSLOTS={HANDS='hands'};events={}
   item={prefab=handprefab,HasTag=function(_,tag)return tag==handprefab or (handtool and tag=='tool') end}
   local inventory={GetEquippedItem=function()return item end,equipslots={}}
   inst.components={inventory=inventory};inst.replica={inventory=inventory}
   inst.ListenForEvent=function(_,event,fn) events[event]=fn end
   inst.DoTaskInTime=function()return {Cancel=function()end}end
  ''')
  if client:self.lua.execute('inst.components=nil')
  self.m.Bind(self.lua.globals().inst)

 def test_imprint_projection_stays_visible_during_native_work_on_both_sides(self):
  for client in (False,True):
   self.bind_hands('klbq_imprint_tool',client)
   for state in ('chop_start','chop','mine_start','mine','mine_recoil','dig_start','dig'):
    with self.subTest(client=client,state=state):
     self.lua.execute('events.newstate(inst,{statename=...})',state)
     self.assertIsNone(self.lua.eval('hidden.swap_object'))
     self.assertTrue(self.lua.eval('hidden.ARM_carry'))
     self.assertIsNone(self.lua.eval('hidden.ARM_normal'))

 def test_projector_still_hides_for_food_and_restores_afterwards(self):
  self.bind_hands('klbq_imprint_tool')
  self.lua.execute("events.newstate(inst,{statename='eat'})")
  self.assertTrue(self.lua.eval('hidden.swap_object'))
  self.lua.execute("events.newstate(inst,{statename='idle'})")
  self.assertIsNone(self.lua.eval('hidden.swap_object'))

 def test_existing_weapon_work_hiding_is_preserved(self):
  self.bind_hands('klbq_finale')
  self.lua.execute("events.newstate(inst,{statename='mine'})")
  self.assertTrue(self.lua.eval('hidden.swap_object'))

 def test_regular_tools_remain_visible_during_work_on_server_and_client(self):
  tools={'axe':('chop_start','chop'),'goldenaxe':('chop_start','chop'),
    'pickaxe':('mine_start','mine','mine_recoil'),'goldenpickaxe':('mine_start','mine','mine_recoil'),
    'shovel':('dig_start','dig'),'goldenshovel':('dig_start','dig'),
    'hammer':('hammer_start','hammer'),'bugnet':('bugnet_start','bugnet'),'pitchfork':('terraform',)}
  for client in (False,True):
   for prefab,states in tools.items():
    self.bind_hands(prefab,client,tool=True)
    for state in states:
     with self.subTest(client=client,prefab=prefab,state=state):
      self.lua.execute('events.newstate(inst,{statename=...})',state)
      self.m.HideEquipment(self.lua.globals().inst)
      self.assertIsNone(self.lua.eval('hidden.swap_object'))
      self.assertTrue(self.lua.eval('hidden.ARM_carry'))
      self.assertIsNone(self.lua.eval('hidden.ARM_normal'))
    self.lua.execute("events.newstate(inst,{statename='idle'})")
    self.assertIsNone(self.lua.eval('hidden.swap_object'))

 def test_tool_hides_while_eating_and_reappears_for_work(self):
  self.bind_hands('pickaxe',tool=True)
  self.lua.execute("events.newstate(inst,{statename='eat'})")
  self.assertTrue(self.lua.eval('hidden.swap_object'))
  self.lua.execute("events.newstate(inst,{statename='mine_start'})")
  self.assertIsNone(self.lua.eval('hidden.swap_object'))

if __name__=='__main__':unittest.main(verbosity=2)
