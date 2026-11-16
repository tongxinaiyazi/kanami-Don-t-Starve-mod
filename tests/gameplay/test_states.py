import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class States(unittest.TestCase):
 def test_work_binding_preserves_native_action_and_client_lag(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   inst={prefab='klbq_kanami',sg={},AnimState={
    PlayAnimation=function(s,n)played=n;queue={} end,
    PushAnimation=function(s,n,l)table.insert(queue,n) end,
    IsCurrentAnimation=function(s,n)return played==n end}}
   function graph(client)
    return {states={mine_start={onenter=function(p)
     effects=effects+1;p.AnimState:PlayAnimation('pickaxe_pre')
     if client then p.AnimState:PushAnimation('pickaxe_lag',false) end
     if transition then p.sg.currentstate={} end
     return 12,'native'
    end,timeline={'native worked event'}}}}
   end
  ''')
  mod.Install(lua.globals().env)
  for graph in ['wilson','wilson_client']:
   lua.globals().graphname=graph
   lua.execute("g=graph(graphname=='wilson_client');callbacks[graphname](g);effects=0;transition=false;inst.prefab='klbq_kanami';inst.sg.currentstate=g.states.mine_start;a,b=g.states.mine_start.onenter(inst)")
   self.assertEqual(lua.eval('effects'),1)
   self.assertEqual(lua.eval('a'),12);self.assertEqual(lua.eval('b'),'native')
   self.assertEqual(lua.eval('played'),'kanami_pickaxe_pre')
   self.assertEqual(lua.eval('queue[1]'),'kanami_pickaxe_lag' if graph=='wilson_client' else None)
   self.assertEqual(lua.eval('g.states.mine_start.timeline[1]'),'native worked event')
   lua.execute("inst.prefab='wilson';g.states.mine_start.onenter(inst)")
   self.assertEqual(lua.eval('played'),'pickaxe_pre')
   lua.execute("inst.prefab='klbq_kanami';transition=true;g.states.mine_start.onenter(inst)")
   self.assertEqual(lua.eval('played'),'pickaxe_pre')

 def test_work_post_animation_keeps_queued_idle(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   inst={prefab='klbq_kanami',AnimState={
    PlayAnimation=function(s,n,l)played=n;queued=nil end,
    PushAnimation=function(s,n,l)queued=n;loop=l end,
    IsCurrentAnimation=function(s,n)return played==n end}}
   function graph()return {states={idle={onenter=function(p)
    p.AnimState:PlayAnimation(requested);p.AnimState:PushAnimation('idle_loop',true)
   end}}}end
  ''')
  mod.Install(lua.globals().env)
  for graph in ['wilson','wilson_client']:
   lua.globals().graphname=graph
   lua.execute('g=graph();callbacks[graphname](g)')
   for clip in ['pickaxe_pst','shovel_pst']:
    lua.globals().requested=clip
    lua.execute('g.states.idle.onenter(inst)')
    self.assertEqual(lua.eval('played'),'kanami_'+clip)
    self.assertEqual(lua.eval('queued'),'kanami_idle_loop');self.assertTrue(lua.eval('loop'))

 def test_feast_keeps_native_effects_and_prediction_queue(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   function graph(client)
    return {states={winters_feast_eat={onenter=function(inst)
     effects=effects+1
     inst.AnimState:PlayAnimation('feast_eat_pre_pre')
     if client then inst.AnimState:PushAnimation('feast_eat_lag',false)
     else for _,name in ipairs({'pre','loop','loop','pst'}) do inst.AnimState:PushAnimation('feast_eat_'..name,false) end end
     if changed then inst.sg.currentstate={} end
     return 7,'preserved'
    end}}}
   end
   inst={prefab='klbq_kanami',sg={},AnimState={
    IsCurrentAnimation=function(s,n)return played==n end,
    PlayAnimation=function(s,n)played=n;queue={} end,
    PushAnimation=function(s,n,loop)table.insert(queue,n);assert(loop==false) end}}
  ''')
  mod.Install(lua.globals().env)
  for graphname in ['wilson','wilson_client']:
   lua.globals().graphname=graphname
   lua.execute("g=graph(graphname=='wilson_client');callbacks[graphname](g);effects=0;changed=false;inst.prefab='klbq_kanami';inst.sg.currentstate=g.states.winters_feast_eat;r1,r2=g.states.winters_feast_eat.onenter(inst)")
   self.assertEqual(lua.eval('effects'),1)
   self.assertEqual(lua.eval('r1'),7);self.assertEqual(lua.eval('r2'),'preserved')
   self.assertEqual(lua.eval('played'),'kanami_feast_eat_pre_pre')
   expected=['lag'] if graphname=='wilson_client' else ['pre','loop','loop','pst']
   self.assertEqual([lua.eval(f'queue[{i+1}]') for i in range(len(expected))],['kanami_feast_eat_'+name for name in expected])
   lua.execute("inst.prefab='wilson';g.states.winters_feast_eat.onenter(inst)")
   self.assertEqual(lua.eval('played'),'feast_eat_pre_pre')
   lua.execute("inst.prefab='klbq_kanami';changed=true;g.states.winters_feast_eat.onenter(inst)")
   self.assertEqual(lua.eval('played'),'feast_eat_pre_pre')

 def test_fidget_idle_uses_bound_neck_and_keeps_animqueueover(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)if n=='wilson' then post=f end end}
   inst={prefab='klbq_kanami',AnimState={IsCurrentAnimation=function(s,n)return played==n end,
    PlayAnimation=function(s,n,l)played=n;looped=l end}}
   g={states={funnyidle={onenter=function()played=requested end,events={'native queueover'}}}}
  ''')
  mod.Install(lua.globals().env)
  lua.execute('post(g)')
  for clip in ['idle_inaction','idle_inaction_sanity']:
   lua.globals().requested=clip
   lua.execute('g.states.funnyidle.onenter(inst)')
   self.assertEqual(lua.eval('played'),'kanami_'+clip)
   self.assertFalse(lua.eval('looped'))
  self.assertEqual(lua.eval('g.states.funnyidle.events[1]'),'native queueover')

 def test_queued_idle_is_bound_after_transition_without_erasing_the_queue(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   played='';changes=0;inst={prefab='klbq_kanami',replica={rider={IsRiding=function()return riding end}},
    AnimState={IsCurrentAnimation=function(s,n)return played==n end,
     PlayAnimation=function(s,n)played=n;changes=changes+1 end}}
   function graph()return {states={idle={onenter=function()played='run_pst' end}}}end
  ''')
  mod.Install(lua.globals().env)
  for name in ['wilson','wilson_client']:
   lua.globals().graphname=name
   lua.execute("g=graph();callbacks[graphname](g);g.states.idle.onenter(inst)")
   self.assertEqual(lua.eval('played'),'run_pst')
   lua.execute("played='idle_loop';g.states.idle.onupdate(inst)")
   self.assertEqual(lua.eval('played'),'kanami_idle_loop')
   lua.execute("riding=true;played='idle_loop';g.states.idle.onupdate(inst)")
   self.assertEqual(lua.eval('played'),'idle_loop')
   lua.execute('riding=false')

 def test_bound_run_only_replaces_kanami_ground_run_on_both_sides(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   played='';requested='run_loop';looping=false
   inst={prefab='klbq_kanami',_klbq_string={value=function()return false end},
    AnimState={PlayAnimation=function(s,n,l)played=n;looping=l end,
    IsCurrentAnimation=function(s,n)return played==n end}}
   function graph()return {states={run={onenter=function()played=requested;return 7 end}}}end
  ''')
  mod.Install(lua.globals().env)
  for name in ['wilson','wilson_client']:
   lua.globals().graphname=name
   lua.execute("g=graph();callbacks[graphname](g);inst.prefab='klbq_kanami';requested='run_loop';result=g.states.run.onenter(inst)")
   self.assertEqual(lua.eval('played'),'kanami_run_loop');self.assertTrue(lua.eval('looping'));self.assertEqual(lua.eval('result'),7)
   for clip in ['careful_walk','idle_walk']:
    lua.globals().requested=clip
    lua.execute('g.states.run.onenter(inst)')
    self.assertEqual(lua.eval('played'),'kanami_'+clip)
    self.assertTrue(lua.eval('looping'))
   lua.execute("requested='run_woby_loop';g.states.run.onenter(inst)")
   self.assertEqual(lua.eval('played'),'run_woby_loop')
   lua.execute("inst.prefab='wilson';requested='run_loop';g.states.run.onenter(inst)")
   self.assertEqual(lua.eval('played'),'run_loop')

 def test_bound_attacks_and_pickup_preserve_native_prediction_queue(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   inst={prefab='klbq_kanami',AnimState={PlayAnimation=function(s,n)played=n;queued=nil end,
    PushAnimation=function(s,n,l)queued=n;loop=l end,IsCurrentAnimation=function(s,n)return played==n end}}
   function graph()return {states={attack={onenter=function(p)p.AnimState:PlayAnimation(pre);return 7 end},
    doshortaction={onenter=function(p)p.AnimState:PlayAnimation('pickup');return 9 end}}}end
  ''')
  mod.Install(lua.globals().env)
  for name in ['wilson','wilson_client']:
   lua.globals().graphname=name
   lua.execute('g=graph();callbacks[graphname](g)')
   for pre in ['atk_pre','spearjab_pre']:
    lua.globals().pre=pre
    lua.execute('result=g.states.attack.onenter(inst)')
    self.assertEqual(lua.eval('played'),'kanami_'+pre)
    tail=pre.removesuffix('_pre')+('_lag' if name=='wilson_client' else '')
    self.assertEqual(lua.eval('queued'),'kanami_'+tail)
    self.assertEqual(lua.eval('result'),7)
   lua.execute('result=g.states.doshortaction.onenter(inst)')
   self.assertEqual(lua.eval('played'),'kanami_pickup')
   self.assertEqual(lua.eval('queued'),'kanami_pickup_'+('lag' if name=='wilson_client' else 'pst'))
   self.assertEqual(lua.eval('result'),9)

 def test_native_speech_uses_bound_face_and_preserves_special_modes(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)if n=='wilson'then post=f end end}
   inst={prefab='klbq_kanami',AnimState={IsCurrentAnimation=function(s,n)return played==n end,
    PlayAnimation=function(s,n,l)played=n;loop=l end}}
   g={states={talk={onenter=function(p,noanim)if not noanim then p.AnimState:PlayAnimation(requested,true)end;return 7 end}}}
  ''')
  mod.Install(lua.globals().env)
  lua.execute("post(g);requested='dial_loop';result=g.states.talk.onenter(inst)")
  self.assertEqual(lua.eval('played'),'kanami_dial_loop')
  self.assertTrue(lua.eval('loop'));self.assertEqual(lua.eval('result'),7)
  lua.execute("requested='heavy_dial_loop';g.states.talk.onenter(inst)")
  self.assertEqual(lua.eval('played'),'heavy_dial_loop')
  lua.execute("played='kanami_idle_loop';g.states.talk.onenter(inst,true)")
  self.assertEqual(lua.eval('played'),'kanami_idle_loop')

 def test_bound_eating_preserves_native_queue_and_timeline_on_both_sides(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute("""
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   inst={prefab='klbq_kanami',AnimState={
    PlayAnimation=function(s,n)played=n;queued=nil end,
    PushAnimation=function(s,n,l)queued=n;loop=l end,
    IsCurrentAnimation=function(s,n)return played==n end}}
   function graph()
    return {states={eat={onenter=function(p)p.AnimState:PlayAnimation('eat_pre');p.AnimState:PushAnimation(tail,false);return 9 end,timeline={'native event'}},
      quickeat={onenter=function(p)p.AnimState:PlayAnimation(pre);p.AnimState:PushAnimation(tail,false) end}}}
   end
  """)
  mod.Install(lua.globals().env)
  for name in ['wilson','wilson_client']:
   lua.globals().graphname=name
   tail='eat_lag' if name=='wilson_client' else 'eat'
   lua.globals().tail=tail
   lua.execute("g=graph();callbacks[graphname](g);result=g.states.eat.onenter(inst)")
   self.assertEqual(lua.eval('played'),'kanami_eat_pre');self.assertEqual(lua.eval('queued'),'kanami_'+tail)
   self.assertEqual(lua.eval('result'),9);self.assertEqual(lua.eval('g.states.eat.timeline[1]'),'native event')
   lua.execute("pre='quick_drink_pre';tail='quick_drink';g.states.quickeat.onenter(inst)")
   self.assertEqual(lua.eval('played'),'quick_drink_pre');self.assertEqual(lua.eval('queued'),'quick_drink')

 def test_generic_shot_uses_native_animation_and_keeps_death_state_timeout(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   states={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function(graph,state)if graph=='wilson' then states[state.name]=state end end,
    AddStategraphPostInit=function()end}
   before={};dead={};timeouts=0
   inst={prefab='wilson',components={locomotor={Stop=function()end}},
    AnimState={PlayAnimation=function(s,name)played=name end},
    sg={currentstate=before,SetTimeout=function()timeouts=timeouts+1 end},
    PerformBufferedAction=function(s)s.sg.currentstate=dead end}
  ''')
  mod.Install(lua.globals().env)
  lua.execute('states.klbq_shoot.onenter(inst)')
  self.assertEqual(lua.eval('played'),'dart')
  self.assertTrue(lua.eval('inst.sg.currentstate==dead'))
  self.assertEqual(lua.eval('timeouts'),0)

 def test_old_state_cannot_override_animation_after_native_transition(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   env={GLOBAL={State=function(v)return v end,EventHandler=function()end},AddStategraphState=function()end,
     AddStategraphPostInit=function(n,f)post=f end}
   oldstate={};nextstate={};animation='';inst={prefab='klbq_kanami',_klbq_string={value=function()return true end},
     sg={currentstate=oldstate},AnimState={IsCurrentAnimation=function()return false end,
       PlayAnimation=function(s,n,loop)animation=n end}}
   g={states={run={onupdate=function(p)p.sg.currentstate=nextstate;animation='native_transition' end}}}
  ''')
  mod.Install(lua.globals().env)
  lua.execute('post(g);g.states.run.onupdate(inst)')
  self.assertEqual(lua.eval('animation'),'native_transition')
 def test_string_glides_with_static_pose_and_no_footstep_timeline(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  mod=lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/states.lua').read_text(encoding='utf8'))
  lua.execute('''
   callbacks={};env={GLOBAL={State=function(v)return v end,EventHandler=function()end},
    AddStategraphState=function()end,AddStategraphPostInit=function(n,f)callbacks[n]=f end}
   enabled=true;original=0;steps=0;played=''
   inst={prefab='klbq_kanami',_klbq_string={value=function()return enabled end},
     AnimState={PlayAnimation=function(s,n,l)played=n end,IsCurrentAnimation=function(s,n)return played==n end}}
   function graph()
    local g={states={}}
    for _,n in ipairs({'idle','run_start','run','run_stop'})do
     g.states[n]={onenter=function()original=original+1;played='original';return 'preserved',7 end,
       timeline={{fn=function()steps=steps+1 end}}}
    end
    return g
   end
  ''')
  mod.Install(lua.globals().env)
  for name in ['wilson','wilson_client']:
   lua.globals().graphname=name
   lua.execute("g=graph();callbacks[graphname](g)")
   for state in ['idle','run_start','run','run_stop']:
    lua.globals().statename=state
    lua.execute("r1,r2=g.states[statename].onenter(inst);g.states[statename].timeline[1].fn(inst)")
    self.assertEqual(lua.eval('played'),'kanami_string_idle')
    self.assertEqual(lua.eval('r1'),'preserved');self.assertEqual(lua.eval('r2'),7)
   self.assertEqual(lua.eval('steps'),0)
   lua.execute("enabled=false;g.states.run.onenter(inst);g.states.run.timeline[1].fn(inst)")
   self.assertEqual(lua.eval('played'),'original');self.assertEqual(lua.eval('steps'),1)
   lua.execute('enabled=true;steps=0')

if __name__=='__main__':unittest.main(verbosity=2)
