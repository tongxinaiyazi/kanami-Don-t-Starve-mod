"""Pearl uses installed DST prefab, friendship, talk queue, and toss state in Lua 5.1."""
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")
MODULE = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/hermit.lua'


class Hermit(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME) as archive:
            native = {n: archive.read('scripts/' + n + '.lua').decode('utf-8-sig')
                      for n in ('class', 'components/friendlevels', 'components/npc_talker',
                                'prefabs/hermitcrab', 'stategraphs/SGhermitcrab')}
        self.lua.execute(native['class'])
        self.lua.execute('''
          function noop() end
          function AutoTable() return setmetatable({}, {__index=function(t,k) t[k]=k;return k end}) end
          local function Passive() return setmetatable({}, {__index=function() return noop end}) end
          Asset=function() return {} end
          Vector3=function(x,y,z) return {x=x,y=y,z=z} end
          FRAMES=1/30;CHATPRIORITIES=AutoTable();PEARL_DECORATION_TYPES=AutoTable()
          ACTIONS=AutoTable();FOODGROUP=AutoTable();FOODTYPE=AutoTable();EQUIPSLOTS=AutoTable()
          SPECIAL_EVENTS=AutoTable();COLLISION=AutoTable();FACING_DOWN=1
          TUNING={HERMITCRAB={SPEAKTIME=5,COMPLAINTIME=30,RUNSPEED=4,WALKSPEED=2},
            PROTOTYPER_TREES=AutoTable(),OCEAN_FISHING={REEL_ACTION_REPEAT_DELAY=1}}
          LOC={GetTextScale=function() return 1 end};TheNet={IsDedicated=function() return true end}
          MakeCharacterPhysics=noop;MakeHauntablePanic=noop;MakeMediumFreezableCharacter=noop
          net_tinybyte=function() return {set=noop,value=function() return 0 end} end
          IsSpecialEventActive=function() return false end
          weighted_random_choice=function(t) local key=next(t);return key end
          function ConcatArrays(a,b) for _,v in ipairs(b) do table.insert(a,v) end return a end
          function string:split(sep) local r={} for p in self:gmatch('[^'..sep..']+') do r[#r+1]=p end return r end
          STRINGS={HERMITCRAB_INTRODUCE={'intro'},HERMITCRAB_GIVE_PEARL={'pearl'},
            HERMITCRAB_GROUP_REWARD={HIGH={'group'},MED={'group'},LOW={'group'}},
            HERMITCRAB_DEFAULT_REWARD={HIGH={'default'}}}
          package.preload['brains/hermitcrabbrain']=function() return {} end
          package.preload['stategraphs/commonstates']=function() return {} end
          CommonStates=Passive();CommonHandlers=setmetatable({}, {__index=function() return function() return {} end end})
          ActionHandler=function(a,s) return {action=a,state=s} end
          EventHandler=function(n,f) return {name=n,fn=f} end
          TimeEvent=function(t,f) return {time=t,fn=f} end;FrameEvent=function(t,f) return TimeEvent(t*FRAMES,f) end
          State=function(s) return s end
          StateGraph=function(n,ss,ee) local g={states={},events={}}
            for _,s in ipairs(ss) do g.states[s.name]=s end
            for _,e in ipairs(ee) do if e.name then g.events[e.name]=e.fn end end
            return g
          end
          Prefab=function(n,f) return {name=n,fn=f} end
          now=0;spawned={};dropped={};tasks={};closeplayer=false
          GetTime=function() return now end
          function Schedule(inst,delay,fn,period)
            local task={inst=inst,time=now+delay,fn=fn,period=period,Cancel=function(s) s.cancelled=true end}
            tasks[#tasks+1]=task;return task
          end
          function Advance(dt)
            local untiltime=now+dt
            while true do
              local nexttask
              for _,t in ipairs(tasks) do if not t.cancelled and t.time<=untiltime and (not nexttask or t.time<nexttask.time) then nexttask=t end end
              if not nexttask then break end
              now=nexttask.time
              if nexttask.period then nexttask.time=now+nexttask.period else nexttask.cancelled=true end
              nexttask.fn(nexttask.inst)
            end
            now=untiltime
          end
          function Entity(name)
            local e={prefab=name,components={},tags={},listeners={},valid=true,events={}}
            e.IsValid=function(s) return s.valid end
            e.AddTag=function(s,t) s.tags[t]=true end
            e.RemoveTag=function(s,t) s.tags[t]=nil end
            e.HasTag=function(s,t) return s.tags[t] or false end
            e.IsInLimbo=function() return false end
            e.ListenForEvent=function(s,n,f,source)
              source=source or s;source.listeners[n]=source.listeners[n] or {};table.insert(source.listeners[n],{s,f})
            end
            e.PushEvent=function(s,n,d)
              s.events[n]=(s.events[n] or 0)+1
              for _,listener in ipairs(s.listeners[n] or {}) do listener[2](listener[1],d) end
              if s.sg and native_sg.events[n] then native_sg.events[n](s,d) end
            end
            e.DoTaskInTime=function(s,t,f) return Schedule(s,t,f) end
            e.DoPeriodicTask=function(s,t,f) return Schedule(s,t,f,t) end
            e.WatchWorldState=noop;e.SetBrain=noop;e.ForceFacePoint=noop;e.ClearBufferedAction=noop;e.PerformBufferedAction=noop
            e.GetNearestPlayer=function() return owner end
            e.GetPosition=function() return Vector3(0,0,0) end
            e.Transform=Passive();e.Transform.GetWorldPosition=function() return 0,0,0 end
            e.AnimState=Passive();e.DynamicShadow=Passive();e.SoundEmitter=Passive();e.Physics=Passive()
            e.SoundEmitter.PlayingSound=function() return false end
            e.entity=Passive()
            e.SetStateGraph=function(s)
              s.sg={inst=s,tags={idle=true},mem={},statemem={},HasStateTag=function(g,t) return g.tags[t] or false end,
                SetTimeout=noop,RemoveStateTag=function(g,t) g.tags[t]=nil end}
              s.sg.GoToState=function(g,n,d)
                local state=native_sg.states[n];g.currentstate=state;g.statemem={};g.tags={}
                for _,t in ipairs(state.tags or {}) do g.tags[t]=true end
                if state.onenter then state.onenter(s,d) end
              end
            end
            e.AddComponent=function(s,n)
              local c=Passive();c.inst=s;s.components[n]=c
              if n=='friendlevels' then c=Friendlevels(s);s.components[n]=c
              elseif n=='npc_talker' then c=NPCTalker(s);s.components[n]=c
              elseif n=='inventory' then
                c.items={};c.GiveItem=function(i,item) i.items[#i.items+1]=item end
                c.DropItem=function(i,item) for k,v in ipairs(i.items) do if v==item then table.remove(i.items,k);break end end end
                c.GetItemSlot=function(i,item) for k,v in ipairs(i.items) do if v==item then return k end end end
                c.GetEquippedItem=function() return nil end;c.IsHeavyLifting=function() return false end
              elseif n=='lootdropper' then c.FlingItem=function(_,item) dropped[#dropped+1]=item end
              elseif n=='locomotor' then s.components[n]={Stop=noop,Clear=noop}
              elseif n=='timer' then
                c.timers={};c.TimerExists=function(t,k) return t.timers[k]~=nil end
                c.StartTimer=function(t,k,v) t.timers[k]=v end;c.StopTimer=function(t,k) t.timers[k]=nil end
                c.GetTimeLeft=function(t,k) return t.timers[k] end;c.SetTimeLeft=function(t,k,v) t.timers[k]=v end
              elseif n=='craftingstation' then c.learned={};c.LearnItem=function(t,k,v) t.learned[k]=v end
              elseif n=='talker' then c.Chatter=function() s:PushEvent('ontalk') end
              end
            end
            return e
          end
          TheWorld=Entity('world');TheWorld.ismastersim=true;TheWorld.state={isday=true}
          CreateEntity=function() return Entity('hermitcrab') end
          SpawnPrefab=function(n)
            local e=Entity(n);spawned[#spawned+1]=e
            e.Remove=function(s) s.valid=false end
            if n=='hermit_bundle' then e.components.unwrappable={WrapItems=function(_,items) e.wrapped=items end} end
            return e
          end
          FindClosestPlayerToInst=function() return closeplayer and owner or nil end
          FindEntity=function() return nil end
          GetTopologyDataAtInst=function() return {task_id='',layout_id=''} end
          function NativeToss()
            if npc.itemstotoss and not npc.sg:HasStateTag('mandatory') then npc:PushEvent('tossitem') end
            if npc.sg.currentstate==native_sg.states.tossitem then
              for _,event in ipairs(native_sg.states.tossitem.timeline) do event.fn(npc) end
              for _,event in ipairs(native_sg.states.tossitem.events) do if event.name=='animqueueover' then event.fn(npc) end end
            end
          end
        ''')
        self.lua.globals().Friendlevels = self.lua.execute(native['components/friendlevels'])
        self.lua.globals().NPCTalker = self.lua.execute(native['components/npc_talker'])
        self.lua.globals().native_sg = self.lua.execute(native['stategraphs/SGhermitcrab'])
        prefab, *_ = self.lua.execute(native['prefabs/hermitcrab'])
        self.lua.globals().hermit_prefab = prefab
        self.lua.execute("owner=Entity('klbq_kanami');other=Entity('klbq_kanami');npc=hermit_prefab.fn();Advance(0)")

    def module(self):
        self.assertTrue(MODULE.exists(), 'missing native Pearl friendship integration')
        self.lua.globals().hermit = self.lua.execute(MODULE.read_text(encoding='utf-8-sig'))

    def count_spawned(self, name):
        return self.lua.eval('function(name) local n=0 for _,e in ipairs(spawned) do if e.prefab==name then n=n+1 end end return n end')(name)

    def test_native_fixture_repeats_non_onetime_tasks_and_persists_the_queue(self):
        self.lua.execute('npc.components.friendlevels:CompleteTask(1,owner);npc.components.friendlevels:CompleteTask(1,owner)')
        self.assertEqual(self.lua.eval('#npc.components.friendlevels.queuedrewards'), 2)
        self.assertEqual(self.lua.eval('npc.components.friendlevels:OnSave().level'), 1)

    def test_domain_maxes_native_shared_friendship_and_cashes_vanilla_rewards(self):
        self.module()
        self.lua.execute('hermit.Apply(owner,npc)')
        self.assertEqual(self.lua.eval('npc.components.friendlevels:GetLevel()'), 10)
        self.assertEqual(self.lua.eval('#npc.components.friendlevels.queuedrewards'), 0)
        self.assertEqual(self.lua.eval('npc._shop_level'), 5)
        self.assertTrue(self.lua.eval('npc.components.craftingstation.learned.supertacklecontainer~=nil'))
        self.assertEqual(self.count_spawned('hermit_pearl'), 1)
        self.assertEqual(self.count_spawned('hermit_bundle'), 4)
        self.assertEqual(self.lua.eval('#npc.itemstotoss'), 5)
        self.assertIsNone(self.lua.eval('npc.giverewardstask'))
        self.assertEqual(self.lua.eval('#dropped'), 0)
        self.lua.execute('NativeToss()')
        self.assertEqual(self.lua.eval('#dropped'), 5)
        self.assertIsNone(self.lua.eval('npc.itemstotoss'))

    def test_quarter_second_scans_and_two_performers_cannot_farm_rewards(self):
        self.module()
        self.lua.execute('''
          hermit.Apply(owner,npc);NativeToss()
          for i=1,120 do hermit.Apply(owner,npc);hermit.Apply(other,npc);Advance(.25) end
        ''')
        self.assertEqual(self.count_spawned('hermit_pearl'), 1)
        self.assertEqual(self.count_spawned('hermit_bundle'), 4)
        self.assertEqual(self.lua.eval('#npc.components.friendlevels.queuedrewards'), 0)
        self.assertEqual(self.lua.eval('npc.events.friend_task_complete'), 10)

    def test_native_dialog_runs_talkto_then_tossitem_without_mod_forcing_states(self):
        self.module()
        self.lua.execute('hermit.Apply(owner,npc);npc.components.npc_talker:DoNextLine()')
        self.assertEqual(self.lua.eval('npc.sg.currentstate.name'), 'talkto')
        self.assertEqual(self.lua.eval('#dropped'), 0)
        self.lua.execute('native_sg.states.talkto.ontimeout(npc)')
        self.assertEqual(self.lua.eval('npc.sg.currentstate.name'), 'tossitem')
        self.lua.execute('NativeToss()')
        self.assertEqual(self.lua.eval('#dropped'), 5)

    def test_busy_npc_keeps_vanilla_queue_until_safe_and_save_load_preserves_it(self):
        self.module()
        self.lua.execute("npc.sg.tags={busy=true};hermit.Apply(owner,npc);saved=npc.components.friendlevels:OnSave()")
        self.assertEqual(self.lua.eval('saved.level'), 10)
        self.assertEqual(self.lua.eval('#saved.queuedrewards'), 10)
        self.assertEqual(self.count_spawned('hermit_pearl'), 0)
        for tag in ('ishome', 'mandatory', 'teashop', 'soakin'):
            self.lua.execute('npc.sg.tags={[...]=true};hermit.Apply(owner,npc)', tag)
            self.assertEqual(self.lua.eval('#npc.components.friendlevels.queuedrewards'), 10)
            self.assertEqual(self.count_spawned('hermit_pearl'), 0)
        self.lua.execute('npc.components.friendlevels:OnLoad(saved);npc.components.friendlevels:LoadPostPass({},saved);npc.sg.tags={idle=true};hermit.Apply(owner,npc)')
        self.assertEqual(self.count_spawned('hermit_pearl'), 1)
        self.assertEqual(self.lua.eval('#npc.components.friendlevels.queuedrewards'), 0)

    def test_existing_max_friendship_still_completes_pearl_house_gate_once(self):
        self.module()
        self.lua.execute('npc.components.friendlevels.level=10;hermit.Apply(owner,npc);hermit.Apply(other,npc)')
        self.assertTrue(self.lua.eval('npc.components.friendlevels.friendlytasks[3].complete'))
        self.assertEqual(self.count_spawned('hermit_pearl'), 1)
        self.assertEqual(self.lua.eval('npc.events.friend_task_complete'), 3)

    def test_vanilla_pearlgiven_save_gate_prevents_duplicates_after_reload(self):
        self.module()
        self.lua.execute('''
          hermit.Apply(owner,npc);NativeToss();data={};npc.OnSave(npc,data)
          npc.pearlgiven=nil;npc.OnLoad(npc,data)
          -- A later genuine repeatable task retains its normal reward, without another pearl.
          npc.components.friendlevels:CompleteTask(1,owner)
          npc.sg.tags={idle=true}
          hermit.Apply(owner,npc)
        ''')
        self.assertTrue(self.lua.eval('data.pearlgiven'))
        self.assertEqual(self.count_spawned('hermit_pearl'), 1)
        self.assertEqual(self.count_spawned('hermit_bundle'), 5)

    def test_client_invalid_owner_and_other_prefabs_are_ignored(self):
        self.module()
        self.lua.execute('TheWorld.ismastersim=false;hermit.Apply(owner,npc);TheWorld.ismastersim=true;owner.valid=false;hermit.Apply(owner,npc);owner.valid=true;npc.prefab="hermitcrab_marker";hermit.Apply(owner,npc)')
        self.assertEqual(self.lua.eval('npc.components.friendlevels:GetLevel()'), 0)
        self.assertEqual(self.count_spawned('hermit_pearl'), 0)
        self.assertEqual(self.lua.eval('hermit.TAGS[1]'), 'hermitcrab')


if __name__ == '__main__':
    unittest.main(verbosity=2)
