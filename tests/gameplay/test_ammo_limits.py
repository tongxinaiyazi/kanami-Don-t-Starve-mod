"""Bullet-only cap/rate bypass against the installed native combat pipeline."""
import unittest
import zipfile

import test_rifle
from test_review_regressions import GAME, vanilla


class AmmoLimits(unittest.TestCase):
    def setUp(self):
        test_rifle.Rifle.setUp(self)
        self.lua.execute("Damage=require('klbq_kanami/damage');PlanarEntity={}")
        self.lua.execute(vanilla('components/planarentity.lua', 'function PlanarEntity:AbsorbDamage('))
        self.lua.execute('''
          a=inst;t=target;h=t.components.health;c=t.components.combat;a:AddTag('player')
          -- Both of these are common private per-instance mod wrappers. Merely
          -- removing maxdamagetakenperhit cannot make either accept a hit.
          olddelta=h.DoDelta;oldattack=c.GetAttacked
          oldinternal=c.GetAttacked_Internal
          h.maxdamagetakenperhit=-1
          h.DoDelta=function(...) gated_deltas=(gated_deltas or 0)+1;return 0 end
          h.deltamodifierfn=function(...) gated_modifiers=(gated_modifiers or 0)+1;return 0 end
          c.GetAttacked=function(...) gated_attacks=(gated_attacks or 0)+1;return false end
          c.GetAttacked_Internal=function(...) gated_internal=(gated_internal or 0)+1;return false end
          wrapped_delta=h.DoDelta;wrapped_attack=c.GetAttacked;wrapped_internal=c.GetAttacked_Internal
          health_updates=0;attacked_events=0;hit_events=0;deltas=0;kills=0
          t.events.healthdelta=function(s,data)health_updates=health_updates+1;lastdelta=data end
          t.events.attacked=function(s,data)attacked_events=attacked_events+1;lastattack=data end
          h.ondelta=function(s,old,new,ot,cause,aff,amount)deltas=deltas+1;ondelta_amount=amount end
          a.events.onhitother=function(s,data)hit_events=hit_events+1;lasthit=data end
          a.events.killed=function(s,data)kills=kills+1;killdata=data end
        ''')

    def assert_wrappers_preserved(self):
        self.assertTrue(self.lua.eval('h.DoDelta==wrapped_delta and c.GetAttacked==wrapped_attack and c.GetAttacked_Internal==wrapped_internal'))
        self.assertEqual(self.lua.eval('h.maxdamagetakenperhit'), -1)
        self.assertIsNone(self.lua.eval('h._ignore_maxdamagetakenperhit'))

    def test_heart_ignores_cap_and_private_combat_health_gates_but_keeps_armor(self):
        self.lua.execute('enemyarmor=equiparmor(t,.8);h.absorb=.5')
        for _ in range(2):
            self.assertTrue(self.lua.eval('Damage.BulletNormal(a,t,50,gun)'))
        self.assertEqual(self.lua.eval('h.currenthealth'), 990)
        self.assertEqual(self.lua.eval('enemyarmor.condition'), 920)
        self.assertEqual(self.lua.eval('health_updates'), 2)
        self.assertEqual(self.lua.eval('deltas'), 2)
        self.assertEqual(self.lua.eval('attacked_events'), 2)
        self.assertEqual(self.lua.eval('hit_events'), 2)
        self.assertEqual(self.lua.eval('lastdelta.amount'), -5)
        self.assertEqual(self.lua.eval('lastattack.damageresolved'), 5)
        self.assertAlmostEqual(self.lua.eval('lastdelta.newpercent'), .99)
        self.assertIsNone(self.lua.eval('gated_deltas or gated_attacks or gated_internal or gated_modifiers'))
        self.assert_wrappers_preserved()

    def test_heart_retains_native_planar_damping_and_external_absorption(self):
        self.lua.execute('''
          t.components.planarentity=setmetatable({OnResistNonPlanarAttack=function()resisted=true end},{__index=PlanarEntity})
          c.externaldamagetakenmultipliers.Get=function()return .5 end
          h.absorb=.2;h.playerabsorb=.1
          h.externalabsorbmodifiers.Get=function()return .25 end
          h.externalreductionmodifiers.Get=function()return 1 end
        ''')
        self.assertTrue(self.lua.eval('Damage.BulletNormal(a,t,50,gun)'))
        expected=(25*4+64)**.5*4-32
        expected=expected*.7*.75-1
        self.assertAlmostEqual(self.lua.eval('1000-h.currenthealth'), expected)
        self.assertTrue(self.lua.eval('resisted'))
        self.assert_wrappers_preserved()

    def test_fate_ignores_cap_private_delta_gate_and_all_ordinary_absorption(self):
        self.lua.execute('enemyarmor=equiparmor(t,.99);h.absorb=.99;h.externalreductionmodifiers.Get=function()return 999 end')
        for _ in range(2):
            self.assertTrue(self.lua.eval('Damage.BulletTrueDamage(a,t,300,gun)'))
        self.assertEqual(self.lua.eval('h.currenthealth'), 400)
        self.assertEqual(self.lua.eval('enemyarmor.condition'), 1000)
        self.assertEqual(self.lua.eval('health_updates'), 2)
        self.assertEqual(self.lua.eval('attacked_events'), 2)
        self.assertEqual(self.lua.eval('hit_events'), 2)
        self.assertEqual(self.lua.eval('lastattack.damageresolved'), 300)
        self.assertTrue(self.lua.eval('lastattack.attacker==a and c.lastattacker==a'))
        self.assertIsNone(self.lua.eval('gated_deltas or gated_attacks or gated_internal or gated_modifiers'))
        self.assert_wrappers_preserved()

    def test_first_two_bullets_keep_phase_invincibility_redirect_and_minhealth(self):
        for method in ('BulletNormal', 'BulletTrueDamage'):
            with self.subTest(method=method):
                self.lua.execute('h.currenthealth=1000;h.invincible=true;h.minhealth=nil;h.redirect=nil')
                self.assertFalse(self.lua.eval(f'Damage.{method}(a,t,300,gun)'))
                self.assertEqual(self.lua.eval('h.currenthealth'), 1000)
                self.lua.execute('h.invincible=false;h.redirect=function(...)redirected=true;return true end')
                self.assertFalse(self.lua.eval(f'Damage.{method}(a,t,300,gun)'))
                self.assertEqual(self.lua.eval('h.currenthealth'), 1000)
                self.assertTrue(self.lua.eval('redirected'))
                self.lua.execute('h.redirect=nil;h.currenthealth=50;h.minhealth=1;t.events.minhealth=function()phase_changes=(phase_changes or 0)+1 end')
                self.assertTrue(self.lua.eval(f'Damage.{method}(a,t,300,gun)'))
                self.assertEqual(self.lua.eval('h.currenthealth'), 1)
                self.assertEqual(self.lua.eval('kills'), 0)
                self.assert_wrappers_preserved()

    def test_cap_bypass_keeps_kanami_string_reduction(self):
        self.lua.execute('t.components.klbq_kanami={state={string=true},IsProtected=function() return false end}')
        for method in ('BulletNormal','BulletTrueDamage'):
            with self.subTest(method=method):
                self.lua.execute('h.currenthealth=1000')
                self.assertTrue(self.lua.eval(f'Damage.{method}(a,t,50,gun)'))
                self.assertEqual(self.lua.eval('h.currenthealth'),990)

    def test_cap_bypass_keeps_kanami_resurrection_protection(self):
        self.lua.execute('t.components.klbq_kanami={state={string=false},IsProtected=function() return true end}')
        for method in ('BulletNormal','BulletTrueDamage'):
            with self.subTest(method=method):
                self.assertFalse(self.lua.eval(f'Damage.{method}(a,t,50,gun)'))
                self.assertEqual(self.lua.eval('h.currenthealth'),1000)

    def test_heart_restores_delta_on_error(self):
        self.lua.execute("c.ShouldRecoil=function()error('armor failure')end")
        self.assertFalse(self.lua.eval('(function()local ok=pcall(function()Damage.BulletNormal(a,t,50,gun)end);return ok end)()'))
        self.assert_wrappers_preserved()

    def test_nested_unrelated_damage_still_uses_original_gate(self):
        self.lua.execute('''
          h.redirect=function(s,amount,ot,cause,inv,aff,abs)
            if not nested then nested=true;h:DoDelta(-100,false,'unrelated',false,nil,false)end
            return false
          end
        ''')
        self.assertTrue(self.lua.eval('Damage.BulletNormal(a,t,50,gun)'))
        self.assertEqual(self.lua.eval('h.currenthealth'), 950)
        self.assertEqual(self.lua.eval('gated_deltas'), 1)
        self.assert_wrappers_preserved()

    def test_fate_native_death_credit_and_onhit_fire_once(self):
        self.lua.execute('''
          h.currenthealth=100
          t.events.death=function(s,data)death_afflicter=data.afflicter;death_combat=s.components.combat.lastattacker end
          c.onkilledbyother=function(s,who)killcallbacks=(killcallbacks or 0)+1;callback_attacker=who end
        ''')
        self.assertTrue(self.lua.eval('Damage.BulletTrueDamage(a,t,300,gun)'))
        self.assertEqual(self.lua.eval('h.currenthealth'), 0)
        self.assertEqual(self.lua.eval('kills'), 1)
        self.assertEqual(self.lua.eval('killcallbacks'), 1)
        self.assertEqual(self.lua.eval('attacked_events'), 1)
        self.assertEqual(self.lua.eval('hit_events'), 1)
        self.assertTrue(self.lua.eval('death_afflicter==a and death_combat==a and callback_attacker==a'))
        self.assertFalse(self.lua.eval('Damage.BulletTrueDamage(a,t,300,gun)'))
        self.assertEqual(self.lua.eval('kills'), 1)

    def test_doom_ends_current_form_and_preserves_native_replacement(self):
        self.lua.execute('''
          h.invincible=true
          t.events.death=function(s,data)nextform={health=500,owner=data.afflicter};s.removed_by_native_phase=true end
          t.Remove=function()error('bullet must not Remove a form')end
        ''')
        self.assertTrue(self.lua.eval('Damage.Execute(a,t)'))
        self.assertEqual(self.lua.eval('nextform.health'), 500)
        self.assertTrue(self.lua.eval('nextform.owner==a and t.removed_by_native_phase'))
        self.assertEqual(self.lua.eval('kills'), 1)
        self.assert_wrappers_preserved()

    def test_native_health_property_setters_update_replica_and_hud(self):
        # Native Class properties are what publish SetVal to network replicas;
        # merely changing a mocked currenthealth number cannot prove this.
        with zipfile.ZipFile(GAME) as archive:
            self.lua.execute(archive.read('scripts/class.lua').decode('utf-8-sig'))
            for path in ('util/sourcemodifierlist', 'components/health'):
                source=archive.read('scripts/'+path+'.lua').decode('utf-8-sig')
                self.lua.execute('package.preload[...] = function() '+source+' end', path)
        self.lua.execute('''
          CHEATS_ENABLED=false;TUNING={HEALTH_PENALTY_ENABLED=false,NONLETHAL_PERCENT=0}
          t.replica={health=setmetatable({SetCurrent=function(s,n)replica_current=n end,
            SetIsDead=function(s,v)replica_dead=v end},{__index=function()return function()end end})}
          h=require('components/health')(t);t.components.health=h
          h.maxhealth=1000;h.currenthealth=1000;h.nofadeout=true
          h.maxdamagetakenperhit=-1;h.DoDelta=wrapped_delta
          h.deltamodifierfn=function()return 0 end
        ''')
        self.assertTrue(self.lua.eval('Damage.BulletNormal(a,t,50,gun)'))
        self.assertEqual(self.lua.eval('replica_current'), 950)
        self.assertFalse(self.lua.eval('replica_dead'))
        self.assertAlmostEqual(self.lua.eval('lastdelta.newpercent'), .95)
        self.assertTrue(self.lua.eval('Damage.BulletTrueDamage(a,t,1000,gun)'))
        self.assertEqual(self.lua.eval('replica_current'), 0)
        self.assertTrue(self.lua.eval('replica_dead'))
        self.assertEqual(self.lua.eval('health_updates'), 2)

    def test_native_redirect_chain_bypasses_receiver_limits_and_reports_real_loss(self):
        self.lua.execute('''
          function receiver()
            local r={components={},events={},tags={},IsValid=t.IsValid,IsInLimbo=t.IsInLimbo,
              HasTag=t.HasTag,PushEvent=t.PushEvent}
            r.components.health=makehealth(r,1000);r.components.combat=makecombat(r)
            r.components.inventory=setmetatable({inst=r,equipslots={}},{__index=Inventory})
            r.components.health.maxdamagetakenperhit=-1
            r.components.health.DoDelta=function()receiver_gate_called=true;return 0 end
            r.components.health.deltamodifierfn=function()receiver_modifier_called=true;return 0 end
            r.components.combat.GetAttacked_Internal=function()receiver_attack_gate=true;return false end
            return r
          end
          middle=receiver();last=receiver()
          h.invincible=true;middle.components.health.invincible=true
          c.redirectdamagefn=function()redirect_calls=(redirect_calls or 0)+1;return middle end
          middle.components.combat.redirectdamagefn=function()redirect_calls=redirect_calls+1;return last end
          receiver_delta=last.components.health.DoDelta;receiver_attack=last.components.combat.GetAttacked_Internal
          receiver_armor=equiparmor(last,.8);last.components.health.absorb=.5
          receipt={}
        ''')
        self.assertTrue(self.lua.eval('Damage.BulletNormal(a,t,50,gun,receipt)'))
        self.assertEqual(self.lua.eval('h.currenthealth'),1000)
        self.assertEqual(self.lua.eval('middle.components.health.currenthealth'),1000)
        self.assertEqual(self.lua.eval('last.components.health.currenthealth'),995)
        self.assertEqual(self.lua.eval('receiver_armor.condition'),960)
        self.assertEqual(self.lua.eval('redirect_calls'),2)
        self.assertEqual(self.lua.eval('Damage.ActualDamage(receipt)'),5)
        self.assertIsNone(self.lua.eval('receiver_gate_called or receiver_attack_gate or receiver_modifier_called'))
        self.assertTrue(self.lua.eval('last.components.health.DoDelta==receiver_delta and last.components.combat.GetAttacked_Internal==receiver_attack'))
        self.assertIsNone(self.lua.eval('middle.components.combat.redirected_from or last.components.combat.redirected_from'))
        self.assert_wrappers_preserved()

    def test_native_redirect_chain_restores_receiver_and_source_on_error(self):
        self.lua.execute('''
          receiver={components={},IsValid=t.IsValid,IsInLimbo=t.IsInLimbo,HasTag=t.HasTag,events={},PushEvent=t.PushEvent}
          receiver.components.health=makehealth(receiver,1000);receiver.components.combat=makecombat(receiver)
          receiver.components.combat.ShouldRecoil=function()error('receiver armor failure')end
          receiver_delta=receiver.components.health.DoDelta
          receiver_internal=receiver.components.combat.GetAttacked_Internal
          external_redirect=function()return receiver end;c.redirectdamagefn=external_redirect
        ''')
        self.assertFalse(self.lua.eval('(function()local ok=pcall(function()Damage.BulletNormal(a,t,50,gun)end);return ok end)()'))
        self.assertTrue(self.lua.eval('c.redirectdamagefn==external_redirect and receiver.components.health.DoDelta==receiver_delta and receiver.components.combat.GetAttacked_Internal==receiver_internal'))
        self.assertIsNone(self.lua.eval('receiver.components.combat.redirected_from'))
        self.assert_wrappers_preserved()

    def test_execute_notifies_healthdelta_and_ondelta_without_double_kill(self):
        self.lua.execute("a.nameoverride='test shooter'")
        self.assertTrue(self.lua.eval('Damage.Execute(a,t)'))
        self.assertEqual(self.lua.eval('health_updates'),1)
        self.assertEqual(self.lua.eval('deltas'),1)
        self.assertEqual(self.lua.eval('kills'),1)
        self.assertEqual(self.lua.eval('lastdelta.amount'),-1000)
        self.assertEqual(self.lua.eval('lastdelta.cause'),'test shooter')
        self.assertTrue(self.lua.eval('lastdelta.afflicter==a and h.causeofdeath==a'))

    def test_fate_death_cause_uses_shooter_name_and_keeps_ammo_stimuli(self):
        self.lua.execute("a.nameoverride='fate shooter';h.currenthealth=10;t.events.death=function(s,data)deathcause=data.cause end")
        self.assertTrue(self.lua.eval('Damage.BulletTrueDamage(a,t,300,gun)'))
        self.assertEqual(self.lua.eval('deathcause'),'fate shooter')
        self.assertEqual(self.lua.eval('lastdelta.cause'),'fate shooter')
        self.assertEqual(self.lua.eval('lastattack.stimuli'),'klbq_fate')


if __name__ == '__main__':
    unittest.main(verbosity=2)
