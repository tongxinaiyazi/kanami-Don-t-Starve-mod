"""Run installed HappyPatch wrappers and native DST health/combat, without a game process."""
import unittest
from pathlib import Path

import test_rifle
from test_review_regressions import vanilla


HAPPY = Path(r"E:\steam\steamapps\workshop\content\322330\2886753796")


class HappyCompat(unittest.TestCase):
    def load_happy(self, relative, source=None):
        path = HAPPY / relative
        if source is None:
            source = path.read_text(encoding='utf-8-sig')
        # Keep the actual source path: the production adapter must identify the
        # installed mod, rather than accept an imitation of its field names.
        return self.lua.execute('local src,name=...;return assert(loadstring(src,name))()',
                                source, '@' + path.as_posix())

    def setUp(self):
        fixture = test_rifle.Rifle(); fixture.setUp(); self.lua = fixture.lua
        self.lua.execute(vanilla('components/health.lua', 'function Health:SetMaxDamageTakenPerHit('))
        self.lua.execute('''
          happyconfigs={epic_armor_5=5,boss_maxdamagetake=7,boss_damagetake2=.9}
          GetModConfigData=function(key)return happyconfigs[key]end
          happyany={};happycomponents={}
          AddPrefabPostInit=function()end
          AddPrefabPostInitAny=function(fn)happyany[#happyany+1]=fn end
          AddComponentPostInit=function(name,fn)happycomponents[name]=fn end
          target.prefab='dragonfly';target.tags.epic=true;target.tasks={}
          target.HasAnyTag=function(s,tags)for _,tag in ipairs(tags)do if s:HasTag(tag)then return true end end;return false end
          inst.HasAnyTag=target.HasAnyTag
          target.IsAsleep=function()return false end
          target.DoTaskInTime=inst.DoTaskInTime;target.ListenForEvent=inst.ListenForEvent
          target.AddComponent=function(s,name)
            if name=='timer' then s.components.timer={TimerExists=function()return timer_invincible or false end}
            elseif name=='persistent2hm' then s.components.persistent2hm={data={}}
            else error(name)end
          end
          target.DoPeriodicTask=function()return {Cancel=function()end}end
          target.WatchWorldState=function()end
          TheWorld.state={cycles=0}
          kills=0;death_callbacks=0
          inst.events.killed=function(s,data)kills=kills+1;killdata=data end
          target.components.combat.onkilledbyother=function(victim,who)death_callbacks=death_callbacks+1;callbacksource=who end
          target.Remove=function()error('bullets must use normal death or form callbacks')end
          target.events.death=function(s,data)deathdata=data;sourceatdeath=s.components.combat.lastattacker end
          Damage=require('klbq_kanami/damage');Compat=require('klbq_kanami/compat')
        ''')
        # These are the actual installed cap/DoDelta registrations. The later
        # unrelated freeze/fire/boss feature registrations are outside this test.
        extra = (HAPPY / 'extra/extra.lua').read_text(encoding='utf-8-sig')
        self.load_happy('extra/extra.lua', extra[:extra.index('if modconfigs("boss_notfreezable") then')])
        self.lua.execute('happycomponents.health(target.components.health);happyany[1](target);happyany={}')
        self.load_happy('epic/epic_armor.lua')
        self.lua.execute('''
          happyany[1](target);target.tasks[1]();target.tasks={}
          epicwrapper=target.components.health.SetVal
          originaldelta=target.components.health.DoDelta
          target.epicarmor2hm.timer={Cancel=function()end}
        ''')

    def assert_restored(self, expected_health):
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), expected_health)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))
        self.assertTrue(self.lua.eval('target.components.health.DoDelta==originaldelta'))
        self.assertEqual(self.lua.eval('target.components.health.maxdamagetakenperhit'), -7)
        self.assertTrue(self.lua.eval('target.epicarmor2hm.timer~=nil'))
        self.assertEqual(self.lua.eval('#target.epicarmor2hm.deltaList'), 0)
        self.lua.execute("target.components.health:DoDelta(-100,false,'ordinary',false,inst,true)")
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), expected_health)

    def test_heart_bypasses_real_timer_and_extra_caps_but_keeps_native_armor(self):
        self.lua.execute('enemyarmor=equiparmor(target,.8);target.components.health.absorb=.5')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertAlmostEqual(self.lua.eval('enemyarmor.condition'), 960)
        self.assert_restored(995)

    def test_fate_bypasses_actual_recovery_timer_do_delta_reduction_and_cap(self):
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;target.epicarmor2hm.timer=nil;timer_invincible=true")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 700)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))
        self.assertEqual(self.lua.eval('#target.epicarmor2hm.deltaList'), 0)
        self.lua.execute("target.components.health:DoDelta(-100,false,'ordinary',false,inst,true)")
        self.assertGreater(self.lua.eval('target.components.health.currenthealth'), 700)
        self.assertTrue(self.lua.eval('timer_invincible'))

    def test_fate_critical_and_doom_keep_native_death_credit(self):
        for ammo in ('klbq_ammo_fate', 'klbq_ammo_doom'):
            with self.subTest(ammo=ammo):
                self.setUp()
                self.lua.globals().ammoname=ammo
                self.lua.execute("ammo.prefab=ammoname;math.random=function()return .01 end")
                if ammo=='klbq_ammo_fate':
                    self.lua.execute('target.components.health.maxhealth=100000')
                self.assertTrue(self.lua.eval('shoot()'))
                self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 0)
                self.assertEqual(self.lua.eval('kills'), 1)
                self.assertEqual(self.lua.eval('death_callbacks'), 1)
                for expr in ('deathdata.afflicter==inst', 'sourceatdeath==inst',
                             'callbacksource==inst', 'killdata.attacker==inst',
                             'killdata.victim==target', 'target.components.health.SetVal==epicwrapper'):
                    self.assertTrue(self.lua.eval(expr), expr)

    def test_doom_preserves_real_shadowworld_form_wrapper_without_self_kill_flag(self):
        source=(HAPPY / 'shadowworld.lua').read_text(encoding='utf-8-sig')
        start=source.index('        local oldSetVal = child.components.health.SetVal')
        end=source.index('\n    end\n    child:ListenForEvent', start)
        self.lua.execute('''
          formdeaths=0;selfkills=0
          onchildbekilled=function(child)formdeaths=formdeaths+1;formsource=child.components.combat.lastattacker end
          onchildkillself=function()selfkills=selfkills+1 end
        ''')
        self.load_happy('shadowworld.lua', 'local child=target\n'+source[start:end])
        self.lua.execute("epicwrapper=target.components.health.SetVal;ammo.prefab='klbq_ammo_doom'")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('formdeaths'), 1)
        self.assertEqual(self.lua.eval('selfkills'), 0)
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), .01)
        self.assertTrue(self.lua.eval('formsource==inst'))
        self.assertEqual(self.lua.eval('kills'), 0)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))

    def test_doom_respects_native_minhealth_phase_and_does_not_credit_a_living_form(self):
        self.lua.execute('''
          target.components.health.minhealth=100;phases=0
          target.events.minhealth=function()phases=phases+1 end
          Damage.Execute(inst,target)
        ''')
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 100)
        self.assertEqual(self.lua.eval('phases'), 1)
        self.assertEqual(self.lua.eval('kills'), 0)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))

    def test_outer_epic_ruin_damage_tracking_and_other_wrappers_are_preserved(self):
        source=(HAPPY / 'epic/epic_ruin.lua').read_text(encoding='utf-8-sig')
        source=source[:source.index('AddPrefabPostInitAny(function(inst)')]
        install=self.load_happy('epic/epic_ruin.lua',source+'\nreturn ModifyHealthComponent')
        install(self.lua.globals().target)
        self.lua.execute('''
          inst.tags.epic=true
          local old=target.components.health.SetVal
          target.components.health.SetVal=function(...)outercalls=(outercalls or 0)+1;return old(...)end
          epicwrapper=target.components.health.SetVal
          Damage.BulletTrueDamage(inst,target,300,gun)
        ''')
        self.assertEqual(self.lua.eval('outercalls'),1)
        self.assertEqual(self.lua.eval('target.components.persistent2hm.data.epicruin2hm.totalEpicDamage'),300)
        self.assert_restored(700)

    def test_nested_same_attacker_ordinary_hit_keeps_real_defense(self):
        self.lua.execute('''
          local old=target.components.health.SetVal
          target.components.health.SetVal=function(self,val,cause,afflicter)
            if not nesting then
              nesting=true;self:SetVal(self.currenthealth-40,cause,afflicter);nesting=false
            end
            return old(self,val,cause,afflicter)
          end
          epicwrapper=target.components.health.SetVal
          Damage.BulletTrueDamage(inst,target,300,gun)
        ''')
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),700)
        # Only the nested ordinary hit goes into HappyPatch's damage accumulator.
        self.assertEqual(self.lua.eval('target.epicarmor2hm.totalDelta'),40)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))

    def test_error_restores_root_ancestor_and_future_defenses(self):
        self.lua.execute('''
          local old=target.components.health.SetVal
          target.components.health.SetVal=function(...)
            old(...);error('deliberate outer callback failure')
          end
          failingroot=target.components.health.SetVal
          success,failure=pcall(Damage.BulletTrueDamage,inst,target,300,gun)
        ''')
        self.assertFalse(self.lua.eval('success'))
        self.assertIn('deliberate outer callback failure',self.lua.eval('failure'))
        self.assertTrue(self.lua.eval('target.components.health.SetVal==failingroot'))
        self.lua.execute('target.components.health.SetVal=epicwrapper')
        self.assert_restored(700)

    def test_passive_true_damage_keeps_happy_timer_defense(self):
        self.lua.execute('Damage.TrueDamage(inst,target,300,gun)')
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),1000)
        self.assertTrue(self.lua.eval('target.components.health.SetVal==epicwrapper'))


if __name__=='__main__':unittest.main(verbosity=2)
