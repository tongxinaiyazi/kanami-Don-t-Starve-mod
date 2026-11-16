"""Exercise the installed HappyPatch curse tracker, not a duplicate counter."""
import unittest
from pathlib import Path
import test_curse
HAPPY=Path('E:/steam/steamapps/workshop/content/322330/2886753796')

class HappySpeechCurse(unittest.TestCase):
 def test_immune_character_never_activates_real_tracker_but_other_players_do(self):
  fixture=test_curse.CurseImmunity();fixture.setUp();lua=fixture.lua
  lua.execute('''
   flags={}; TUNING.util2hm={GetClassified2hm=function(id)
    flags[id]=flags[id] or {take_cursed_item_num={set=function(self,x)self.active=x end}}
    return flags[id]
   end}
   function EntityWatch(self)self.WatchWorldState=function()end;self.RemoveEventCallback=function()end;self.userid=self.prefab;self.components.inventory.equipslots={}end
   EntityWatch(p);p:AddTag('klbq_kanami')
   other=player('wilson');EntityWatch(other)
  ''')
  source=(HAPPY/'scripts/components/haitangcurse2hm.lua').read_text(encoding='utf8')
  lua.execute('package.preload["components/haitangcurse2hm"]=function() '+source+' end')
  lua.execute('''
   p:AddComponent('haitangcurse2hm');other:AddComponent('haitangcurse2hm')
   cursed=entity('happy_test_curse');cursed:AddTag('curse2hm')
   p.components.inventory.itemslots[1]=cursed
   other.components.inventory.itemslots[1]=cursed
   p:RunTasks();other:RunTasks()
  ''')
  self.assertFalse(lua.eval('flags[p.userid].take_cursed_item_num.active'))
  self.assertTrue(lua.eval('flags[other.userid].take_cursed_item_num.active'))
  lua.execute("p:PushEvent('equip',{item=cursed});p:PushEvent('itemget',{slot=2,item=cursed})")
  self.assertFalse(lua.eval('flags[p.userid].take_cursed_item_num.active'))
  self.assertEqual(lua.eval('p.components.haitangcurse2hm.curse_num'),0)
