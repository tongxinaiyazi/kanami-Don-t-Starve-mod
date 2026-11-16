import unittest

import test_component


class Passive(unittest.TestCase):
    setUp = test_component.Lifecycle.setUp

    def target(self):
        self.lua.execute('''
          planarhits=0;truehits=0;trueamount=0;kills=0;retaliations=0
          local oldpush=inst.PushEvent
          inst.PushEvent=function(s,n,d)
            if n=='killed' then kills=kills+1 end
            return oldpush(s,n,d)
          end
          hp={currenthealth=950,maxhealth=10000,IsDead=function(s) return s.currenthealth<=0 end,
            DoDelta=function(s,n,ot,cause,ignoreinv,attacker,ignoreabsorb)
              truehits=truehits+1;trueamount=-n;trueweapon=attacker
              assert(ignoreabsorb and not ignoreinv)
              if s.invincible then return 0 end
              n=math.max(n,-(s.cap or math.huge));s.currenthealth=math.max(0,s.currenthealth+n);return n
            end}
          target={components={health=hp,combat={}},IsValid=function() return true end,
            IsInLimbo=function() return false end,PushEvent=function(s,n,d)
              if n=='attacked' then retaliations=retaliations+1;attackedweapon=d.weapon end
            end}
          target.components.combat.onkilledbyother=function() victimcredits=(victimcredits or 0)+1 end
          target.components.combat.GetAttacked=function(s,attacker,damage,weapon,stim,sp)
            planarhits=planarhits+1;planaramount=sp.planar
            local wasalive=not hp:IsDead()
            if not hp.invincible then hp.currenthealth=math.max(0,hp.currenthealth-math.min(sp.planar,hp.cap or math.huge)) end
            inst:PushEvent('onhitother',{target=target,weapon=weapon,spdamage=sp})
            if wasalive and hp:IsDead() then
              inst:PushEvent('killed',{victim=target});s.onkilledbyother(target,attacker)
            end
          end
          weapon={prefab='test_weapon',components={}}
          snap={power=34,zmult=1,weapon=weapon}
        ''')

    def test_adds_current_health_fraction_to_existing_planar_using_entry_snapshot(self):
        self.target()
        self.assertTrue(self.lua.eval('component:Echo(target,snap)'))
        self.assertEqual(self.lua.eval('planaramount'),34)
        self.assertAlmostEqual(self.lua.eval('trueamount'),950*.03)
        self.assertAlmostEqual(self.lua.eval('hp.currenthealth'),950-34-950*.03)
        self.assertEqual(self.lua.eval('retaliations'),1)
        self.assertTrue(self.lua.eval('attackedweapon==weapon'))
        self.assertEqual(self.lua.eval('planarhits'),1)
        self.assertEqual(self.lua.eval('truehits'),1)

    def test_z_amplifies_both_parts_once(self):
        self.target()
        self.lua.execute('snap.zmult=1.5;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('planaramount'),51)
        self.assertAlmostEqual(self.lua.eval('trueamount'),950*.03*1.5)
        self.assertAlmostEqual(self.lua.eval('hp.currenthealth'),950-51-950*.03*1.5)

    def test_cooldown_is_shared_across_targets_and_recursive_events(self):
        self.target()
        self.lua.execute('component:Echo(target,snap);other={components={health=hp},IsValid=target.IsValid,IsInLimbo=target.IsInLimbo}')
        self.assertFalse(self.lua.eval('component:Echo(other,snap)'))
        self.assertEqual(self.lua.eval('planarhits'),1)
        self.lua.execute('now=1.499')
        self.assertFalse(self.lua.eval('component:Echo(target,snap)'))
        self.lua.execute('now=1.5;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('planarhits'),2)
        self.assertAlmostEqual(self.lua.eval('trueamount'),(950-34-950*.03)*.03)

    def test_true_damage_respects_hit_cap_and_invincibility(self):
        self.target()
        self.lua.execute('hp.cap=10;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('hp.currenthealth'),930)
        self.lua.execute('now=3;hp.invincible=true')
        self.assertFalse(self.lua.eval('component:Echo(target,snap)'))
        self.assertEqual(self.lua.eval('hp.currenthealth'),930)
        self.assertEqual(self.lua.eval('retaliations'),1)

    def test_planar_kill_never_gets_duplicate_true_damage_or_kill_credit(self):
        self.target()
        self.lua.execute('hp.currenthealth=20;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('hp.currenthealth'),0)
        self.assertEqual(self.lua.eval('truehits'),0)
        self.assertEqual(self.lua.eval('kills'),1)
        self.assertEqual(self.lua.eval('victimcredits'),1)

    def test_true_part_kill_uses_existing_native_credit(self):
        self.target()
        self.lua.execute('hp.currenthealth=35;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('hp.currenthealth'),0)
        self.assertEqual(self.lua.eval('kills'),1)
        self.assertEqual(self.lua.eval('victimcredits'),1)

    def test_true_part_can_succeed_when_planar_is_fully_absorbed(self):
        self.target()
        self.lua.execute('target.components.combat.GetAttacked=function() planarhits=planarhits+1 end')
        self.assertTrue(self.lua.eval('component:Echo(target,snap)'))
        self.assertEqual(self.lua.eval('hp.currenthealth'),950-950*.03)

    def test_original_weapon_power_is_preserved(self):
        self.target()
        self.lua.execute('snap.power=113;snap.zmult=1.5;component:Echo(target,snap)')
        self.assertEqual(self.lua.eval('planaramount'),169.5)
        self.assertAlmostEqual(self.lua.eval('trueamount'),950*.03*1.5)

    def test_failed_damage_releases_recursion_guard(self):
        self.target()
        self.lua.execute('hp.DoDelta=function() error("damage callback failure") end;ok,err=pcall(component.Echo,component,target,snap)')
        self.assertFalse(self.lua.eval('ok'))
        self.assertIn('damage callback failure',self.lua.eval('err'))
        self.assertFalse(self.lua.eval('component.echoing'))
        self.assertEqual(self.lua.eval("component:Remaining('passive')"),1.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
