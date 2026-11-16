import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class Gameplay(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  self.lua.execute("package.path = ... .. '/mods/klbq_kanami/scripts/?.lua;' .. package.path",str(ROOT).replace('\\','/'))
  self.rules=self.lua.execute((ROOT/"mods/klbq_kanami/scripts/klbq_kanami/rules.lua").read_text(encoding="utf-8-sig"))
 def test_additive_speed_preserves_existing_final_coefficient(self):
  self.assertAlmostEqual(self.rules.Speed(1.3,True,True),2.65)
  self.assertAlmostEqual(self.rules.Speed(.7,False,True),1.25)
 def test_fate_crit_replaces_and_z_once(self):
  self.assertEqual(self.rules.Fate(20000,True,True),900)
  self.assertEqual(self.rules.Fate(100,True,True),450)
  self.assertEqual(self.rules.Fate(10000,False,False),300)
 def test_fate_configured_percentages_keep_floor_and_apply_z_once(self):
  for fraction in (.03,.05,.1,.2):
   self.rules.ConfigureFate(fraction)
   self.assertEqual(self.rules.Fate(20000,True,False),20000*fraction)
   self.assertEqual(self.rules.Fate(20000,True,True),20000*fraction*1.5)
   self.assertEqual(self.rules.Fate(100,True,False),300)
   self.assertEqual(self.rules.Fate(100,True,True),450)
   self.assertEqual(self.rules.Fate(20000,False,True),450)
 def test_fate_missing_or_invalid_configuration_falls_back_to_three_percent(self):
  for value in (None,False,0,-.03,.01,.04,.3,'0.2'):
   self.rules.ConfigureFate(.2)
   self.rules.ConfigureFate(value)
   self.assertEqual(self.rules.Fate(20000,True,False),600)
 def test_global_cooldown_boundary_and_save_migration(self):
  s=self.rules.New(); self.assertTrue(self.rules.Ready(s,'passive',10))
  self.rules.Start(s,'passive',10,3)
  self.assertFalse(self.rules.Ready(s,'passive',12.999)); self.assertTrue(self.rules.Ready(s,'passive',13))
  saved=self.rules.Save(s,11); restored=self.rules.Load(saved,500)
  self.assertEqual(self.rules.Remaining(restored,'passive',500),2)
 def test_z_is_saved_toggle_without_duration_or_cooldown(self):
  s=self.rules.New(); self.assertTrue(self.rules.Cast(s,'z',100))
  self.assertTrue(s.zenabled)
  self.assertEqual(self.rules.Remaining(s,'z',100),0)
  restored=self.rules.Load(self.rules.Save(s,400),900)
  self.assertTrue(restored.zenabled)
  self.assertTrue(self.rules.Cast(restored,'z',900));self.assertFalse(restored.zenabled)
  self.assertTrue(self.rules.Cast(restored,'z',900.1));self.assertTrue(restored.zenabled)
  self.rules.Death(restored,910);self.assertFalse(restored.zenabled)
 def test_x_keeps_cast_time_duration_and_cooldown(self):
  s=self.rules.New();self.assertTrue(self.rules.Cast(s,'x',100))
  self.assertFalse(self.rules.Cast(s,'x',130));self.assertEqual(self.rules.Remaining(s,'x_active',130),0)
  self.assertTrue(self.rules.Cast(s,'x',160))
 def test_early_revive_cancels_countdown_and_auto_protection(self):
  s=self.rules.New(); self.rules.Death(s,100)
  self.assertFalse(self.rules.AutoReviveDue(s,159.99)); self.assertTrue(self.rules.AutoReviveDue(s,160))
  self.rules.Revive(s,135,False); self.assertFalse(self.rules.AutoReviveDue(s,1000))
  self.assertEqual(self.rules.Remaining(s,'protect',135),0)
  self.rules.Death(s,200); self.rules.Revive(s,260,True)
  self.assertEqual(self.rules.Remaining(s,'protect',260),30)
 def test_snapshot_is_value_and_never_ammo_damage(self):
  a=self.rules.Snapshot(34,2,True); self.assertEqual(a.power,68); self.assertEqual(a.zmult,1.5)
 def test_damage_math_applies_string_and_z_once(self):
  self.assertEqual(self.rules.Incoming(-100,True,False),-20)
  self.assertEqual(self.rules.Incoming(-100,True,True),0)
  self.assertEqual(self.rules.Incoming(10,True,True),10)
 def test_domain_ring_matches_normal_view_twelve_world_units(self):
  self.assertAlmostEqual(self.rules.DomainScale(236)*4,12)
if __name__=='__main__': unittest.main(verbosity=2)
