"""X and resurrection share aggro protection, without sharing invulnerability."""
import unittest
import test_component
from test_review_regressions import vanilla

class DomainAggro(unittest.TestCase):
 def setUp(self):
  fixture=test_component.Lifecycle();fixture.setUp();self.lua=fixture.lua
  self.lua.execute('Combat={}')
  self.lua.execute(vanilla('components/combat.lua','function Combat:ShouldAggro('))
  self.lua.execute('enemy={components={combat={}}};enemy.components.combat.inst=enemy;external=function() return true end;inst.components.combat.shouldavoidaggrofn=external')
 def allowed(self):return self.lua.eval('Combat.ShouldAggro(enemy.components.combat,inst)')
 def test_cast_blocks_native_aggro_without_granting_damage_immunity(self):
  self.assertTrue(self.allowed())
  self.lua.execute("component:Cast('x')")
  self.assertFalse(self.allowed())
  self.assertFalse(self.lua.eval("inst:HasTag('notarget')"))
  self.assertFalse(bool(self.lua.eval("inst:HasTag('klbq_protected')")))
  self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10)'),-10)
  self.lua.execute('now=30;component:Tick()')
  self.assertTrue(self.allowed())
  self.assertTrue(self.lua.eval('inst.components.combat.shouldavoidaggrofn==external'))
 def test_attacking_a_creature_allows_retaliation_until_native_target_is_dropped(self):
  self.lua.execute("component:Cast('x');enemy.components.combat.lastattacker=inst;enemy.components.combat.lastwasattackedtime=now")
  self.assertTrue(self.allowed())
  self.lua.execute('enemy.components.combat.target=inst;now=5')
  self.assertTrue(self.allowed())
  self.lua.execute('enemy.components.combat.target=nil')
  self.assertFalse(self.allowed())
 def test_resurrection_protection_still_blocks_provoked_attackers(self):
  self.lua.execute("component:Cast('x');enemy.components.combat.lastattacker=inst;enemy.components.combat.lastwasattackedtime=now;component.state.deadlines.protect=10;component:Protection(true)")
  self.assertFalse(self.allowed())
  self.assertTrue(self.lua.eval("inst:HasTag('notarget')"))
  self.lua.execute('now=10;enemy.components.combat.target=inst;component:Tick()')
  self.assertFalse(self.lua.eval("inst:HasTag('notarget')"))
 def test_x_outlasts_revive_protection_without_keeping_invulnerability(self):
  self.lua.execute("component.state.deadlines.protect=10;component:Protection(true);component:Cast('x');now=10;component:Tick()")
  self.assertFalse(self.allowed())
  self.assertFalse(self.lua.eval('component:IsProtected()'))
  self.assertFalse(bool(self.lua.eval("inst:HasTag('klbq_protected')")))
  self.lua.execute('now=30;component:Tick()')
  self.assertTrue(self.allowed())
 def test_revive_protection_outlasts_x(self):
  self.lua.execute("component:Cast('x');component.state.deadlines.protect=40;component:Protection(true);now=30;component:Tick()")
  self.assertFalse(self.allowed())
  self.assertTrue(self.lua.eval("inst:HasTag('klbq_protected')"))
  self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10)'),0)
  self.lua.execute('now=40;component:Tick()')
  self.assertTrue(self.allowed())
 def test_removal_cleans_up_active_x_and_death_cleans_up_without_losing_external_tag(self):
  self.lua.execute("inst:AddTag('notarget');component:Cast('x');component:OnRemoveFromEntity()")
  self.assertTrue(self.lua.eval('inst.components.combat.shouldavoidaggrofn==external'))
  self.assertTrue(self.lua.eval("inst:HasTag('notarget')"))
  self.lua.execute("component:Cast('x');component:OnDeath()")
  self.assertTrue(self.allowed())
 def test_component_removal_disables_retained_protection_damage_closure(self):
  self.lua.execute('component.state.deadlines.protect=30;component:Protection(true);component:OnRemoveFromEntity()')
  self.assertFalse(self.lua.eval('component:IsProtected()'))
  self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-10)'),-10)
  self.assertFalse(self.lua.eval('inst._klbq_protect:value()'))

if __name__=='__main__':unittest.main(verbosity=2)
