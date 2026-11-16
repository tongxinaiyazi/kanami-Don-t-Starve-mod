import sys,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime
class Domain(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  self.lua.globals().package.loaded['klbq_kanami/rules']=self.lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/rules.lua').read_text(encoding='utf8'))
  self.lua.globals().package.loaded['klbq_kanami/cleanse']=self.lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/cleanse.lua').read_text(encoding='utf8'))
  for name in ('recruit','hermit','agriculture'):
   self.lua.globals().package.loaded['klbq_kanami/'+name]=self.lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami'/f'{name}.lua').read_text(encoding='utf8'))
  self.m=self.lua.execute((ROOT/'mods/klbq_kanami/scripts/klbq_kanami/domain.lua').read_text(encoding='utf8'))
  self.lua.execute('''
   TheNet={GetPVPEnabled=function() return true end}
   function Owner() return {components={combat={IsAlly=function() return false end}},IsValid=function() return true end,Transform={GetWorldPosition=function() return 0,0,0 end}} end
   function Target(player)
    local s={components={health={IsDead=function() return false end}},IsValid=function() return true end,HasTag=function(_,tag) return player and tag=='player' end}
    s.components.combat={externaldamagemultipliers={m=1,RemoveModifier=function(s) s.m=1 end,SetModifier=function(s,owner,m) s.m=m end}}
    s.components.locomotor={m=1,GetSpeedMultiplier=function(s) return s.m*1.3 end,RemoveExternalSpeedMultiplier=function(s) s.m=1 end,SetExternalSpeedMultiplier=function(s,owner,key,m) s.m=m end}
    return s
   end
   a=Owner();b=Owner();target=Target(false);TheSim={FindEntities=function() return {target} end}
  ''')
 def test_two_domains_do_not_stack_and_last_exit_restores(self):
  a,b,t=self.lua.eval('a,b,target')
  aa=self.m.Scan(a,None);bb=self.m.Scan(b,None)
  self.assertEqual(t.components.combat.externaldamagemultipliers.m,.5)
  self.assertEqual(t.components.locomotor.m,.5)
  self.m.Remove(a,aa);self.assertEqual(t.components.locomotor.m,.5)
  self.m.Remove(b,bb);self.assertEqual(t.components.locomotor.m,1)
 def test_hostile_players_never_receive_creature_debuff(self):
  self.lua.execute('target=Target(true)')
  self.m.Scan(self.lua.globals().a,None)
  self.assertEqual(self.lua.eval('target.components.locomotor.m'),1)
  self.assertEqual(self.lua.eval('target.components.combat.externaldamagemultipliers.m'),1)
 def test_healthless_hermit_is_in_query_and_reaches_interaction(self):
  self.lua.execute('''
   target={prefab='hermitcrab',components={},IsValid=function() return true end}
   require('klbq_kanami/hermit').Apply=function(owner,npc) called=npc end
   TheSim.FindEntities=function(s,x,y,z,r,must,cant,oneof)
    for _,tag in ipairs(oneof) do if tag=='hermitcrab' then hermit_query=true end end
    return {target}
   end
  ''')
  self.m.Scan(self.lua.globals().a,None)
  self.assertTrue(self.lua.eval('called==target'))
  self.assertTrue(self.lua.eval('hermit_query'))
 def test_allied_players_get_addition_on_existing_speed(self):
  self.lua.execute('target=Target(true);TheNet.GetPVPEnabled=function() return false end')
  self.m.Scan(self.lua.globals().a,None)
  self.assertAlmostEqual(self.lua.eval('target.components.locomotor:GetSpeedMultiplier()'),1.5)
 def sanity_target(self):
  self.lua.execute('''target=Target(true);TheNet.GetPVPEnabled=function() return false end
   target.components.sanity={sources={other=true},SetNegativeAuraImmunity=function(s,v,source) assert(source~=nil);s.sources[source]=v or nil end}
   target.components.burnable={burning=true,IsBurning=function(s) return s.burning end,IsSmoldering=function() return false end,Extinguish=function(s) s.burning=false end}
  ''')
 def test_aura_immunity_stays_until_last_domain_and_preserves_other_source(self):
  self.sanity_target();a,b=self.lua.eval('a,b')
  aa=self.m.Scan(a,None);bb=self.m.Scan(b,None)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),2)
  self.m.Remove(a,aa)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),2)
  self.m.Remove(b,bb)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),1)
  self.assertTrue(self.lua.eval('target.components.sanity.sources.other'))
 def test_continual_cleanse_and_exit_stops_cleansing(self):
  self.sanity_target();a=self.lua.globals().a
  tracked=self.m.Scan(a,None)
  self.assertFalse(self.lua.eval('target.components.burnable.burning'))
  self.lua.execute('target.components.burnable.burning=true')
  tracked=self.m.Scan(a,tracked)
  self.assertFalse(self.lua.eval('target.components.burnable.burning'))
  self.lua.execute('TheSim.FindEntities=function() return {} end;target.components.burnable.burning=true')
  self.m.Scan(a,tracked)
  self.assertTrue(self.lua.eval('target.components.burnable.burning'))
  self.assertTrue(self.lua.eval('target.components.sanity.sources.other'))
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),1)
 def test_enemy_is_never_cleansed(self):
  self.lua.execute('target.components.burnable={burning=true,IsBurning=function(s) return s.burning end,IsSmoldering=function() return false end,Extinguish=function(s) s.burning=false end}')
  self.m.Scan(self.lua.globals().a,None)
  self.assertTrue(self.lua.eval('target.components.burnable.burning'))
 def test_friendly_follower_is_cleansed_without_player_speed_bonus(self):
  self.lua.execute('''target.components.follower={GetLeader=function() return a end}
   target.components.burnable={burning=true,IsBurning=function(s) return s.burning end,IsSmoldering=function() return false end,Extinguish=function(s) s.burning=false end}''')
  self.m.Scan(self.lua.globals().a,None)
  self.assertFalse(self.lua.eval('target.components.burnable.burning'))
  self.assertEqual(self.lua.eval('target.components.locomotor.m'),1)
 def test_hostile_players_follower_is_not_cleansed_in_pvp(self):
  self.lua.execute('''leader=Target(true);target.components.follower={GetLeader=function() return leader end}
   target.components.burnable={burning=true,IsBurning=function(s) return s.burning end,IsSmoldering=function() return false end,Extinguish=function(s) s.burning=false end}''')
  self.m.Scan(self.lua.globals().a,None)
  self.assertTrue(self.lua.eval('target.components.burnable.burning'))
  self.assertEqual(self.lua.eval('target.components.locomotor.m'),.5)
 def test_sanity_component_replacement_releases_only_our_old_source(self):
  self.sanity_target();a=self.lua.globals().a
  tracked=self.m.Scan(a,None)
  self.lua.execute('old=target.components.sanity;target.components.sanity={sources={},SetNegativeAuraImmunity=old.SetNegativeAuraImmunity}')
  self.m.Scan(a,tracked)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(old.sources) do n=n+1 end;return n end')(),1)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),1)
 def test_invalid_owner_membership_is_pruned_without_losing_remaining_domain(self):
  self.sanity_target();a,b=self.lua.eval('a,b')
  self.m.Scan(a,None);bb=self.m.Scan(b,None)
  self.lua.execute('a.IsValid=function() return false end')
  self.m.Scan(b,bb)
  self.assertTrue(self.lua.eval('target._klbq_domains[a]==nil'))
  self.m.Remove(b,bb)
  self.assertEqual(self.lua.eval('function() local n=0;for k in pairs(target.components.sanity.sources) do n=n+1 end;return n end')(),1)
 def test_native_sanity_filters_negative_aura_preserves_positive_night_and_other_sources(self):
  with zipfile.ZipFile("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip") as source:
   self.lua.execute(source.read('scripts/class.lua').decode())
   self.lua.execute("package.preload.easing=function() return {} end;EntityScript={is_instance=function() return false end};SANITY_MODE_INSANITY=1;SANITY_MODE_LUNACY=2;TUNING={SANITY_NIGHT_DARK=-2,SANITY_LUNACY_NIGHT_DARK=-2,SANITY_HIGH_LIGHT=.8,SANITY_LOW_LIGHT=.2,SANITY_GHOST_PLAYER_DRAIN=-1,SANITY_AURA_SEACH_RANGE=20}")
   modifiers=self.lua.execute(source.read('scripts/util/sourcemodifierlist.lua').decode())
   self.lua.globals().package.loaded['util/sourcemodifierlist']=modifiers
   self.lua.globals().SourceModifierList=modifiers
   self.lua.globals().NativeSanity=self.lua.execute(source.read('scripts/components/sanity.lua').decode())
  self.lua.execute('''
   target=Target(true);TheNet.GetPVPEnabled=function() return false end
   TheNet.GetServerGameMode=function() return 'survival' end
   target.Transform={GetWorldPosition=function() return 0,0,0 end}
   target.LightWatcher={GetLightValue=function() return 0 end}
   CanEntitySeeInDark=function() return false end;GetGhostSanityDrain=function() return false end
   RATE_SCALE={};TheWorld={state={isday=false},HasTag=function() return false end}
   negative={components={sanityaura={GetAura=function() return -5 end}}}
   positive={components={sanityaura={GetAura=function() return 1 end}}}
   TheSim.FindEntities=function(_,x,y,z,radius) if radius==12 then return {target} else return {negative,positive} end end
   local function bools() return SourceModifierList(target,false,SourceModifierList.boolean) end
   local s=setmetatable({inst=target,neg_aura_immune_sources=bools(),sanity_aura_immune_sources=bools(),light_drain_immune_sources=bools(),player_ghost_immune_sources=bools(),
     dapperness_mult=0,mode=1,night_drain_mult=1,neg_aura_absorb=0,neg_aura_mult=1,rate_modifier=1,
     neg_aura_modifiers=SourceModifierList(target),externalmodifiers=SourceModifierList(target,0,SourceModifierList.additive),DoDelta=function(s,delta) s.lastdelta=delta end}, {__index=NativeSanity})
   s.externalmodifiers:SetModifier('ordinary_drain',-.5)
   target.components.sanity=s
   s:Recalc(1)
  ''')
  self.assertEqual(self.lua.eval('target.components.sanity.lastdelta'),-6.5)
  a=self.lua.globals().a;tracked=self.m.Scan(a,None)
  self.lua.execute('target.components.sanity:Recalc(1)')
  self.assertEqual(self.lua.eval('target.components.sanity.lastdelta'),-1)
  self.lua.execute("target.components.sanity:SetNegativeAuraImmunity(true,'another_mod')")
  self.m.Remove(a,tracked)
  self.lua.execute('target.components.sanity:Recalc(1)')
  self.assertEqual(self.lua.eval('target.components.sanity.lastdelta'),-1.5)
  self.lua.execute("target.components.sanity:SetNegativeAuraImmunity(false,'another_mod');target.components.sanity:Recalc(1)")
  self.assertEqual(self.lua.eval('target.components.sanity.lastdelta'),-6.5)
if __name__=='__main__':unittest.main(verbosity=2)
