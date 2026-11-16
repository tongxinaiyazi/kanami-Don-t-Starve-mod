"""Character immunity against installed native curse and real HappyPatch wrappers."""
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")
HAPPY = Path('E:/steam/steamapps/workshop/content/322330/2886753796/easy_role/wonkey_easy.lua')


class CurseImmunity(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME) as archive:
            for name in ('class', 'curse_monkey_util', 'components/cursable', 'components/curseditem'):
                source = archive.read('scripts/' + name + '.lua').decode('utf-8-sig')
                if name == 'class':
                    self.lua.execute(source)
                else:
                    self.lua.execute('package.preload[...] = function() ' + source + ' end', name)
            source = archive.read('scripts/entityscript.lua').decode('utf-8-sig')
            start = source.index('function EntityScript:SetPersistData(')
            end = source.index('\nend', start) + 4
            self.lua.execute('EntityScript={};' + source[start:end])
        self.lua.execute('''
          GLOBAL=_G;TheWorld={ismastersim=true};TUNING={MONKEY_TOKEN_COUNTS={LEVEL_1=0,LEVEL_2=2,LEVEL_3=5,LEVEL_4=10}}
          GetTime=function()return 0 end;Vector3=function(x,y,z)return{x=x,y=y,z=z}end
          SpawnPrefab=function()return {entity={SetParent=function()end}}end
          GetString=function()return 'curse' end
          hooks={};playerhooks={}
          AddComponentPostInit=function(name,fn)hooks[name]=fn end
          AddPlayerPostInit=function(fn)playerhooks[#playerhooks+1]=fn end
          function entity(prefab)
            local e={prefab=prefab,components={},tags={},events={},tasks={},hits=0,moves=0,
              Transform={GetWorldPosition=function()return 0,0,0 end},entity={IsVisible=function()return true end}}
            e.Transform.SetPosition=function()e.moves=e.moves+1 end
            function e:IsValid()return true end
            function e:AddTag(t)self.tags[t]=true end
            function e:RemoveTag(t)self.tags[t]=nil end
            function e:HasTag(t)return self.tags[t] or false end
            function e:ListenForEvent(n,fn)self.events[n]=self.events[n] or {};table.insert(self.events[n],fn)end
            function e:PushEvent(n,d)
              if n=='monkeycursehit' then self.hits=self.hits+1 end
              for _,fn in ipairs(self.events[n] or {})do fn(self,d)end
            end
            function e:DoTaskInTime(t,fn,...)
              local task={fn=fn,args={...},Cancel=function(s)s.cancelled=true end};table.insert(self.tasks,task);return task
            end
            e.DoPeriodicTask=e.DoTaskInTime
            function e:RunTasks()local tasks=self.tasks;self.tasks={};for _,t in ipairs(tasks)do if not t.cancelled then t.fn(self,unpack(t.args))end end end
            function e:StartUpdatingComponent()end
            function e:StopUpdatingComponent()end
            function e:GetDistanceSqToInst()return 1 end
            function e:AddComponent(name)
              self.components[name]=require('components/'..name)(self)
              if hooks[name]then hooks[name](self.components[name])end
            end
            return e
          end
          function player(prefab,skip)
            local p=entity(prefab)
            p.components.health={IsDead=function()return false end}
            p.components.debuffable={HasDebuff=function()return false end}
            p.components.talker={Say=function()p.speeches=(p.speeches or 0)+1 end}
            p.components.skinner={monkey_curse=nil,SetMonkeyCurse=function(s,v)s.monkey_curse=v end,
              GetMonkeyCurse=function(s)return s.monkey_curse end,ClearMonkeyCurse=function(s)s.monkey_curse=nil end,
              OnLoad=function(s,data)s.monkey_curse=data.monkey_curse end}
            p.components.inventory={inst=p,items={},itemslots={},maxslots=15,
              IsFull=function(s)return s.full end,
              FindItems=function(s,fn)local r={};for _,v in ipairs(s.items)do if fn(v)then r[#r+1]=v end end;return r end,
              FindItem=function(s,fn)for _,v in ipairs(s.items)do if fn(v)then return v end end end,
              ForEachItem=function(s,fn)for _,v in ipairs(s.items)do fn(v)end end,
              DropItem=function()p.ejections=(p.ejections or 0)+1 end,
              ConsumeByName=function()p.consumed=(p.consumed or 0)+1 end,
              GiveItem=function(s,item)
                item:PushEvent('onpickup',{owner=p});item.components.inventoryitem.owner=p
                s.items[#s.items+1]=item;item:AddTag('INLIMBO');item:PushEvent('onputininventory',p)
              end}
            p.sg={HasStateTag=function()return false end,GoToState=function()p.transformed=true end}
            p:AddComponent('cursable')
            if not skip then M.Common(p);M.Master(p);for _,fn in ipairs(playerhooks)do fn(p)end end
            return p
          end
          function token()
            local t=entity('cursed_monkey_token');t:AddTag('monkey_token')
            t.components.inventoryitem={RemoveFromOwner=function()end}
            t:AddComponent('curseditem');t.components.curseditem.curse='MONKEY'
            return t
          end
          closest=nil;FindClosestPlayerInRangeSq=function()return closest end
          function give(p,t)p.components.inventory:GiveItem(t)end
          function drop(t)t.components.inventoryitem.owner=nil;t:RemoveTag('INLIMBO');t:PushEvent('ondropped')end
        ''')
        path = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/curse.lua'
        if path.exists():
            self.lua.execute('M=(function()' + path.read_text(encoding='utf-8-sig') + ' end)()')
        else:
            self.lua.execute('M={Common=function()end,Master=function()end,Install=function()end}')
        self.lua.execute("M.Install(_G);p=player('klbq_kanami');q=player('wilson');t=token()")

    def test_native_zero_time_and_later_autopull_reject_character(self):
        self.assertFalse(self.lua.eval('p.components.cursable:IsCursable(t)'))
        self.lua.execute('closest=p;t.components.curseditem:lookforplayer();t:RunTasks();t.components.curseditem:OnUpdate(.1)')
        self.assertTrue(self.lua.eval('t.components.curseditem.target==nil'))
        self.assertEqual(self.lua.eval('t.moves'), 0)
        self.assertEqual(self.lua.eval('#p.components.inventory.items'), 0)

    def test_character_construction_before_prefab_name_exists(self):
        self.lua.execute("p=player(nil,true);p:AddTag('klbq_kanami');M.Common(p);M.Master(p)")
        self.assertFalse(self.lua.eval('p.components.cursable:IsCursable(t)'))
        self.lua.execute('give(p,t)')
        self.assertEqual(self.lua.eval('p.hits'), 0)
        self.assertEqual(self.lua.eval('p.components.cursable.curses.MONKEY or 0'), 0)

    def test_manual_pickup_is_harmless_and_does_not_stick(self):
        self.lua.execute('give(p,t);p:RunTasks()')
        self.assertEqual(self.lua.eval('p.components.cursable.curses.MONKEY or 0'), 0)
        self.assertEqual(self.lua.eval('p.hits'), 0)
        self.assertTrue(self.lua.eval('t.components.curseditem.cursed_target==nil'))
        self.assertFalse(self.lua.eval("t:HasTag('applied_curse')"))
        self.assertFalse(self.lua.eval("t:HasTag('cursed_inventory_item')"))
        self.lua.execute('drop(t);t.components.curseditem:OnUpdate(.1)')
        self.assertEqual(self.lua.eval('p.ejections or 0'), 0)
        self.assertTrue(self.lua.eval('t.components.inventoryitem.owner==nil'))

    def test_forced_pickup_never_ejects_an_existing_item(self):
        self.lua.execute('p.components.inventory.full=true;p.components.cursable:ForceOntoOwner(t)')
        self.assertEqual(self.lua.eval('p.ejections or 0'), 0)
        self.assertEqual(self.lua.eval('#p.components.inventory.items'), 0)

    def test_dropped_or_transferred_token_still_curses_other_players(self):
        self.lua.execute('give(p,t);drop(t);closest=q;t.components.curseditem:lookforplayer();t:RunTasks()')
        self.assertTrue(self.lua.eval('t.components.curseditem.target==q'))
        self.lua.execute('give(q,t)')
        self.assertEqual(self.lua.eval('q.components.cursable.curses.MONKEY'), 1)
        self.assertTrue(self.lua.eval('t.components.curseditem.cursed_target==q'))
        self.assertTrue(self.lua.eval("t:HasTag('cursed_inventory_item')"))
        self.assertEqual(self.lua.eval('q.hits'), 1)

    def test_already_applied_pickup_becomes_inert_without_escape_speech(self):
        self.lua.execute("t:AddTag('applied_curse');t.components.curseditem.cursed_target=q;give(p,t);p:RunTasks()")
        self.assertTrue(self.lua.eval('t.components.curseditem.cursed_target==nil'))
        self.assertFalse(self.lua.eval("t:HasTag('applied_curse')"))
        self.assertEqual(self.lua.eval('p.speeches or 0'), 0)
        self.assertEqual(self.lua.eval('p.hits'), 0)

    def test_old_pending_target_and_binding_cannot_pull(self):
        self.lua.execute('t.components.curseditem.target=p;t.components.curseditem.cursed_target=p;t.components.curseditem:OnUpdate(.1)')
        self.assertTrue(self.lua.eval('t.components.curseditem.target==nil and t.components.curseditem.cursed_target==nil'))
        self.assertEqual(self.lua.eval('#p.components.inventory.items'), 0)

    def test_split_stack_restores_effect_on_leaving_immune_owner(self):
        self.lua.execute('give(p,t);u=token();t.components.curseditem:CopyCursedFields(u.components.curseditem);drop(u);give(q,u)')
        self.assertTrue(self.lua.eval("u:HasTag('cursed_inventory_item')"))
        self.assertEqual(self.lua.eval('q.components.cursable.curses.MONKEY'), 1)

    def test_real_persist_load_cleans_existing_monkey_state_and_tasks(self):
        self.lua.execute('''
          p=player('klbq_kanami',true)
          local curse=require('curse_monkey_util');p.components.cursable:ApplyCurse(t)
          t.components.inventoryitem.owner=p;p.components.inventory.items={t}
          p._trymonkeychangetask=p:DoPeriodicTask(.1,function()p.transformed=true end)
          pending=p._trymonkeychangetask;p:AddTag('MONKEY_CURSE_3');p.monkeyhands=true;p.monkeytail=true
          M.Common(p);M.Master(p)
          EntityScript.SetPersistData(p,{skinner={monkey_curse='MONKEY_CURSE_3'}})
          p:RunTasks()
        ''')
        self.assertTrue(self.lua.eval('pending.cancelled'))
        self.assertFalse(self.lua.eval('p.transformed or false'))
        self.assertTrue(self.lua.eval('p.components.skinner.monkey_curse==nil'))
        self.assertTrue(self.lua.eval('p.monkeyfeet==nil and p.monkeyhands==nil and p.monkeytail==nil'))
        self.assertFalse(self.lua.eval("p:HasTag('MONKEY_CURSE_3')"))
        self.assertEqual(self.lua.eval('p.components.cursable.curses.MONKEY or 0'), 0)
        self.assertEqual(self.lua.eval('#p.components.inventory.items'), 1)
        self.assertFalse(self.lua.eval("t:HasTag('cursed_inventory_item')"))

    def test_real_happy_curse_override_has_no_hit_for_immune_character(self):
        source = HAPPY.read_text(encoding='utf-8-sig')
        # Execute the actual installed first block, including its shared utility
        # overrides; unrelated Wonkey features are outside this regression.
        source = source[:source.index('-- 芜猴助跑时间缩短')]
        self.lua.execute("GetModConfigData=function(k)return k=='Start With Wonkey Disable Transform' end;AddStategraphPostInit=function()end")
        self.lua.execute(source)
        self.lua.execute('give(p,t);u=token();give(q,u);p.components.cursable:RemoveCurse("MONKEY",1)')
        self.assertEqual(self.lua.eval('p.hits'), 0)
        self.assertEqual(self.lua.eval('p.consumed or 0'), 0)
        self.assertEqual(self.lua.eval('q.hits'), 1)
        self.assertEqual(self.lua.eval('q.components.cursable.curses.MONKEY'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
