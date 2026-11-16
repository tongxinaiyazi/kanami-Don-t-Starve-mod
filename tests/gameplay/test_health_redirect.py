"""Native Wendy health redirection keeps Abigail's defenses and shot receipts."""
import unittest

import test_rifle
from test_review_regressions import vanilla


class HealthRedirect(unittest.TestCase):
    def setUp(self):
        fixture = test_rifle.Rifle(); fixture.setUp(); self.lua = fixture.lua
        self.lua.execute('''
          inst.components.health.currenthealth=1000;inst.components.health.maxhealth=1000
          target.prefab='wendy';target:AddTag('player');target:AddTag('ghostlybond_redirect')
          receiver={prefab='abigail',components={},events={},tags={},
            HasTag=target.HasTag,IsValid=target.IsValid,IsInLimbo=target.IsInLimbo,
            PushEvent=target.PushEvent,AddTag=target.AddTag,RemoveTag=target.RemoveTag}
          receiver.components.health=makehealth(receiver,1000)
          target.components.ghostlybond={ghost=receiver}
          TheNet.GetPVPEnabled=function()return true end;math.random=function()return .5 end
          inst.events.klbq_shot=function(s,data)shotdamage=data.damage end
          inst._klbq_hitseq={set=function(s,v)s.v=v end,value=function(s)return s.v or 0 end}
          inst._klbq_hitdamage={set=function(s,v)hitnumber=v end}
          inst._klbq_hittarget={set=function(s,v)hitentity=v end}
        ''')
        # Execute the installed native callback, including its actual source
        # identity. The adapter must decline unrelated private HP callbacks.
        source = vanilla('prefabs/wendy.lua', 'local function redirect_to_abigail(')
        callback = self.lua.execute('local src=...;return assert(loadstring(src, "@scripts/prefabs/wendy.lua"))()',
                                    source+'\nreturn redirect_to_abigail')
        self.lua.globals().target.components.health.redirect = callback
        self.lua.execute('Replica={}')
        self.lua.execute(vanilla('components/combat.lua', 'function Combat:CanTarget('))
        for name in ['IsValidTarget', 'CanTarget']:
            self.lua.execute(vanilla('components/combat_replica.lua', 'function Combat:'+name+'(').replace(
                'function Combat:', 'function Replica:', 1))
        self.lua.execute('''
          function anytag(s,...)for _,tag in ipairs({...})do if s:HasTag(tag)then return true end end;return false end
          target.HasAnyTag=anytag;gun.HasAnyTag=anytag
          inst.isplayer=true;target.isplayer=true
          target.entity.IsValid=function()return true end
          target.GetPosition=function()return {x=100000,y=0,z=100000}end
          target.replica={combat={CanBeAttacked=function()return true end}}
          IsEntityDead=function(entity)return entity.components.health:IsDead()end
          inst.replica={combat=setmetatable({inst=inst,
            _attackrange={value=function()return 2 end},_ispanic={value=function()return false end},
            GetWeapon=function()return gun end,CanExtinguishTarget=function()return false end,
            CanLightTarget=function()return false end},{__index=Replica})}
          inst.components.combat.CanTarget=nil
        ''')
        self.lua.execute('original_redirect=target.components.health.redirect;original_target_delta=target.components.health.DoDelta;original_receiver_delta=receiver.components.health.DoDelta')

    def shoot(self, ammo):
        self.lua.globals().ammo.prefab = ammo
        return self.lua.eval('shoot()')

    def assert_receipt(self, loss):
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 1000)
        self.assertAlmostEqual(self.lua.eval('inst.components.health.currenthealth'), 1000-loss)
        self.assertAlmostEqual(self.lua.eval('hitnumber'), loss)
        self.assertAlmostEqual(self.lua.eval('shotdamage'), loss)
        self.assertTrue(self.lua.eval('hitentity==target'))
        self.assertTrue(self.lua.eval('target.components.health.redirect==original_redirect'))
        self.assertTrue(self.lua.eval('target.components.health.DoDelta==original_target_delta'))
        self.assertTrue(self.lua.eval('receiver.components.health.DoDelta==original_receiver_delta'))

    def test_both_bullets_reflect_and_display_real_native_receiver_loss(self):
        for ammo, loss in [('klbq_ammo_heart', 50), ('klbq_ammo_fate', 300)]:
            with self.subTest(ammo=ammo):
                self.setUp()
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 1000-loss)
                self.assert_receipt(loss)

    def test_receiver_damage_still_uses_native_absorption(self):
        for ammo, loss in [('klbq_ammo_heart', 25), ('klbq_ammo_fate', 150)]:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('receiver.components.health.absorb=.5')
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 1000-loss)
                self.assert_receipt(loss)

    def test_receiver_cap_is_retained_for_both_bullets(self):
        for ammo in ['klbq_ammo_heart', 'klbq_ammo_fate']:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('receiver.components.health.maxdamagetakenperhit=-12')
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 988)
                self.assert_receipt(12)
                self.assertEqual(self.lua.eval('receiver.components.health.maxdamagetakenperhit'), -12)

    def test_shooter_armor_applies_after_actual_receiver_loss(self):
        for ammo, loss in [('klbq_ammo_heart', 50), ('klbq_ammo_fate', 300)]:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('selfarmor=equiparmor(inst,.8)')
                self.assertTrue(self.shoot(ammo))
                self.assertAlmostEqual(self.lua.eval('inst.components.health.currenthealth'), 1000-loss*.2)
                self.assertAlmostEqual(self.lua.eval('hitnumber'), loss)
                self.assertAlmostEqual(self.lua.eval('selfarmor.condition'), 1000-loss*.8)

    def test_receiver_minhealth_limits_measured_damage_and_preserves_phase_event(self):
        for ammo in ['klbq_ammo_heart', 'klbq_ammo_fate']:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('''
                  receiver.components.health.currenthealth=20;receiver.components.health.minhealth=10
                  receiver.events.minhealth=function()phasechanges=(phasechanges or 0)+1 end
                ''')
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 10)
                self.assertEqual(self.lua.eval('phasechanges'), 1)
                self.assert_receipt(10)

    def test_lethal_damage_measures_remaining_health_and_preserves_native_death(self):
        for ammo in ['klbq_ammo_heart', 'klbq_ammo_fate']:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('''
                  receiver.components.health.currenthealth=20
                  receiver.events.death=function()receiverdeaths=(receiverdeaths or 0)+1 end
                ''')
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 0)
                self.assertEqual(self.lua.eval('receiverdeaths'), 1)
                self.assert_receipt(20)

    def test_receiver_invincibility_keeps_zero_damage_and_zero_backlash(self):
        for ammo in ['klbq_ammo_heart', 'klbq_ammo_fate']:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('receiver.components.health.invincible=true')
                self.assertTrue(self.shoot(ammo))
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 1000)
                self.assert_receipt(0)

    def test_native_redirect_is_called_once_without_tracking_unrelated_nested_damage(self):
        self.lua.execute('''
          unrelated={components={},events={},tags={},PushEvent=target.PushEvent}
          unrelated.components.health=makehealth(unrelated,1000)
          receiver.components.health.ondelta=function()
            redirects=(redirects or 0)+1;unrelated.components.health:DoDelta(-75)
          end
        ''')
        self.assertTrue(self.shoot('klbq_ammo_heart'))
        self.assertEqual(self.lua.eval('redirects'), 1)
        self.assertEqual(self.lua.eval('unrelated.components.health.currenthealth'), 925)
        self.assert_receipt(50)

    def test_receiver_error_restores_scopes_and_next_shot_still_works(self):
        self.lua.execute('receiver.components.health.ondelta=function()error("receiver health event failure")end')
        self.assertFalse(self.lua.eval('(function()local ok=pcall(shoot);return ok end)()'))
        self.assertTrue(self.lua.eval('target.components.health.DoDelta==original_target_delta and target.components.health.redirect==original_redirect and receiver.components.health.DoDelta==original_receiver_delta'))
        self.lua.execute('receiver.components.health.ondelta=nil;now=1.5')
        self.assertTrue(self.shoot('klbq_ammo_heart'))
        self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 900)
        self.assert_receipt(50)

    def test_unrecognized_health_redirect_retains_its_private_behavior(self):
        self.lua.execute('''
          local native=target.components.health.redirect
          target.components.health.redirect=function(...)return native(...)end
          original_redirect=target.components.health.redirect
        ''')
        self.assertTrue(self.shoot('klbq_ammo_heart'))
        self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 950)
        self.assert_receipt(0)

    def test_all_ammo_retains_native_pvp_off_target_rejection_without_spending_ammo(self):
        for ammo in ['klbq_ammo_heart', 'klbq_ammo_fate', 'klbq_ammo_doom']:
            with self.subTest(ammo=ammo):
                self.setUp();self.lua.execute('TheNet.GetPVPEnabled=function()return false end')
                self.assertFalse(self.shoot(ammo))
                self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 1000)
                self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'), 1000)
                self.assertEqual(self.lua.eval('inst.components.health.currenthealth'), 1000)
                self.assertEqual(self.lua.eval('count'), 20)
                self.assertEqual(self.lua.eval('spent'), 0)
                self.assertIsNone(self.lua.eval('inst._klbq_nextshot'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
