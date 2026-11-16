import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime
class Damage(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  for module in ('rules','compat','damage'):
   path=ROOT/'mods/klbq_kanami/scripts/klbq_kanami'/f'{module}.lua'
   self.assertTrue(path.exists(),f'missing behavior module: {module}')
   self.lua.execute("package.preload[...] = function() " + path.read_text(encoding='utf-8-sig') + " end",'klbq_kanami/'+module)
  self.lua.execute('''
   GetTime=function() return 10 end
   require=function(name) local f=package.preload[name]; if f then local v=f(); package.preload[name]=function() return v end; return v end; error(name) end
   attacker={components={},PushEvent=function(self,n,d) self.last=n end,IsValid=function() return true end}
   hp={currenthealth=1000,maxhealth=1000,IsDead=function(self) return self.currenthealth<=0 end,
       DoDelta=function(self,n,ot,cause,inv,aff,abs) self.lastignore=abs; self.currenthealth=self.currenthealth+math.max(n,-100); return math.max(n,-100) end,
       SetVal=function(self,n,cause,aff) self.currenthealth=n; self.afflicter=aff end}
   target={components={health=hp,combat={}},PushEvent=function(s,n,d) s.event=n;s.eventdata=d end,IsValid=function() return true end,IsInLimbo=function() return false end,HasTag=function() return false end,entity={IsVisible=function() return true end}}
   target.components.combat.GetAttacked=function(self,att,dmg,w,stim,sp) self.normal=dmg; self.planar=sp and sp.planar; return true end
  ''')
  self.damage=self.lua.eval("require('klbq_kanami/damage')")
 def test_true_damage_uses_health_and_respects_hit_cap(self):
  a,t=self.lua.eval('attacker,target');self.damage.TrueDamage(a,t,300);self.assertEqual(self.lua.eval('hp.currenthealth'),900);self.assertTrue(self.lua.eval('hp.lastignore'))
 def test_execute_preserves_entity_and_credits_attacker(self):
  a,t=self.lua.eval('attacker,target');self.damage.Execute(a,t);self.assertEqual(self.lua.eval('hp.currenthealth'),0);self.assertTrue(self.lua.eval('hp.afflicter==attacker'));self.assertEqual(self.lua.eval('attacker.last'),'killed')
 def test_execute_replaces_stale_combat_attacker_before_death_callback(self):
  self.lua.execute('''
   stale={};target.components.combat.lastattacker=stale
   hp.SetVal=function(self,n,cause,aff)
    source_at_death=target.components.combat.lastattacker
    time_at_death=target.components.combat.lastwasattackedtime
    self.currenthealth=n;self.afflicter=aff
   end
  ''')
  a,t=self.lua.eval('attacker,target');self.damage.Execute(a,t)
  self.assertTrue(self.lua.eval('source_at_death==attacker'))
  self.assertEqual(self.lua.eval('time_at_death'),10)
 def test_execute_native_death_world_event_loot_and_kill_credit_share_shooter(self):
  from test_review_regressions import vanilla
  self.lua.execute('Health={};LootDropper={}')
  self.lua.execute(vanilla('components/health.lua','function Health:SetVal('))
  self.lua.execute(vanilla('components/lootdropper.lua','function LootDropper:GetLuckyUser('))
  self.lua.execute('''
   CanEntityBecomeCorpse=function() return false end
   NotifyPlayerProgress=function(n,count,who) progress_source=who end
   TheWorld={PushEvent=function(s,n,data) world_death=data end}
   hp.inst=target;hp.GetMaxWithPenalty=function(s) return s.maxhealth end
   hp.CanFadeOut=function() return false end;hp.SetVal=Health.SetVal
   attacker.prefab='klbq_kanami'
   kills=0;callbacks=0
   attacker.PushEvent=function(s,n,data) if n=='killed' then kills=kills+1;kill_data=data end end
   target.components.combat.lastattacker={}
   target.components.combat.onkilledbyother=function(victim,who)
    callbacks=callbacks+1;callback_source=who
   end
   target.PushEvent=function(s,n,data)
    if n=='death' then death_data=data;combat_source_at_death=s.components.combat.lastattacker end
   end
   target.Remove=function() error('execution must use normal death') end
  ''')
  a,t=self.lua.eval('attacker,target');self.damage.Execute(a,t)
  for check in ('death_data.afflicter==attacker','world_death.afflicter==attacker',
                'hp.causeofdeath==attacker','combat_source_at_death==attacker',
                'progress_source==attacker','callback_source==attacker',
                'kill_data.attacker==attacker and kill_data.victim==target',
                'LootDropper.GetLuckyUser({inst=target})==attacker'):
   with self.subTest(check=check):self.assertTrue(self.lua.eval(check))
  self.assertEqual(self.lua.eval('kills'),1);self.assertEqual(self.lua.eval('callbacks'),1)
  self.assertEqual(self.lua.eval('death_data.cause'),'klbq_kanami')
 def test_planar_uses_vanilla_combat_channel(self):
  a,t=self.lua.eval('attacker,target');self.damage.Planar(a,t,51,None);self.assertEqual(self.lua.eval('target.components.combat.planar'),51);self.assertEqual(self.lua.eval('target.components.combat.normal'),0)
 def test_true_hit_notifies_victim_for_native_retaliation(self):
  a,t=self.lua.eval('attacker,target');self.damage.TrueDamage(a,t,300)
  self.assertEqual(self.lua.eval('target.event'),'attacked')
  self.assertEqual(self.lua.eval('target.eventdata.damageresolved'),100)
  self.assertTrue(self.lua.eval('target.eventdata.attacker==attacker'))
 def test_blocked_true_hit_does_not_notify_retaliation(self):
  self.lua.execute('hp.DoDelta=function() return 0 end')
  a,t=self.lua.eval('attacker,target');self.damage.TrueDamage(a,t,300)
  self.assertIsNone(self.lua.eval('target.event'))
if __name__=='__main__':unittest.main(verbosity=2)

