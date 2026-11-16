"""Run the cleanser against current native component classes, with a tiny entity host."""
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME_SCRIPTS = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")


class Cleanse(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            EntityScript={is_instance=function() return false end}
            Vector3=function(x,y,z) return {x=x,y=y,z=z} end
            GetTime=function() return 0 end
            TUNING={GROGGINESS_WEAR_OFF_DURATION=2, GROGGINESS_DECAY_RATE=.1}
            t={components={},tags={},events={}}
            function t:IsValid() return true end
            function t:AddTag(k) self.tags[k]=true end
            function t:RemoveTag(k) self.tags[k]=nil end
            function t:HasTag(k) return self.tags[k] end
            function t:ListenForEvent() end
            function t:RemoveEventCallback() end
            function t:StartUpdatingComponent() end
            function t:StopUpdatingComponent() end
            function t:RestartBrain() end
            function t:PushEvent(name)
                self.events[name]=(self.events[name] or 0)+1
                if name=='cometo' then self.knockedout=false end
            end
            t.sg={HasStateTag=function(_,tag) return tag=='knockout' and t.knockedout end}
            t.components.health={IsDead=function() return false end}
            t.components.locomotor={slow=true,RemoveExternalSpeedMultiplier=function(s) s.slow=false end}
        ''')
        with zipfile.ZipFile(GAME_SCRIPTS) as source:
            self.lua.execute(source.read('scripts/class.lua').decode())
            self.lua.execute("package.preload['easing']=function() return {} end")
            modifiers = self.lua.execute(source.read('scripts/util/sourcemodifierlist.lua').decode())
            self.lua.globals().SourceModifierList = modifiers
            self.lua.globals().native_classes = self.lua.table()
            for name in ['debuffable', 'grogginess', 'freezable', 'inkable']:
                self.lua.globals().native_classes[name] = self.lua.execute(
                    source.read(f'scripts/components/{name}.lua').decode())
        self.lua.execute('''
            t.components.debuffable=native_classes.debuffable(t)
            function AddEffect(key,prefab)
                local inst={prefab=prefab,components={},removed=false}
                function inst:Remove() self.removed=true end
                inst.components.debuff={
                    SetDetachedFn=function(s,fn) s.detach=fn end,
                    OnDetach=function(s) if s.detach then s.detach(inst,t) else inst:Remove() end end}
                t.components.debuffable.debuffs[key]={inst=inst,onremove=function() end}
                return inst
            end
        ''')
        self.m = self.lua.execute((ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/cleanse.lua').read_text(encoding='utf8'))

    def apply(self):
        self.m.Apply(self.lua.globals().t)

    def test_only_evidenced_negative_prefabs_removed_even_with_custom_keys(self):
        names = ['firenettle_toxin', 'mitegland_debuff', 'miasmadebuff',
                 'wormwood_vined_debuff', 'ipecacsyrup_buff', 'mindcontroller',
                 'slingshotammo_purebrilliance_debuff', 'tr_shihua_judu',
                 'tr_eguai_poison_buff', 'tr_void_rending_wound_debuff',
                 'tr_yexingyaoshi_buff', 'tr_zuzhouyan_buff', 'tr_kuijiaposun_buff']
        for name in names:
            with self.subTest(name=name):
                inst = self.lua.globals().AddEffect('custom_' + name, name)
                self.apply()
                self.assertTrue(inst.removed)
                self.assertFalse(self.lua.globals().t.components.debuffable.HasDebuff(
                    self.lua.globals().t.components.debuffable, 'custom_' + name))

    def test_positive_mixed_unknown_and_own_effects_are_preserved(self):
        names = ['buff_attack', 'buff_sleepimmunity', 'healthregenbuff', 'nightvision_buff',
                 'wx78_shadow_fuel_debuff', 'tr_mingjie_buff', 'buff_xinghong',
                 'tr_chaoweibengjie_buff', 'unknown_poison_debuff', 'klbq_domain']
        effects = [self.lua.globals().AddEffect(name, name) for name in names]
        self.apply()
        self.assertTrue(all(not effect.removed for effect in effects))

    def test_known_key_does_not_misclassify_unknown_prefab(self):
        effect = self.lua.globals().AddEffect('miasmadebuff', 'other_mod_positive_buff')
        self.apply()
        self.assertFalse(effect.removed)

    def test_sporebomb_cleansing_does_not_detonate_cloud(self):
        self.lua.execute('''bomb=AddEffect('sporebomb','sporebomb');clouds=0
            bomb.components.debuff:SetDetachedFn(function(inst) clouds=clouds+1;inst:Remove() end)''')
        self.apply()
        self.assertEqual(self.lua.globals().clouds, 0)
        self.assertTrue(self.lua.globals().bomb.removed)

    def test_frozen_and_thawing_states_emit_native_unfreeze_and_clear_coldness(self):
        for state in ['FROZEN', 'THAWING', 'NORMAL']:
            self.lua.execute("t.components.freezable=native_classes.freezable(t)")
            component = self.lua.globals().t.components.freezable
            component.state = state
            component.coldness = 4
            self.apply()
            self.assertEqual(component.state, 'NORMAL')
            self.assertEqual(component.coldness, 0)
        self.assertEqual(self.lua.globals().t.events.unfreeze, 2)

    def test_forced_knockout_and_residual_groggy_speed_use_native_recovery(self):
        self.lua.execute('''t.components.grogginess=native_classes.grogginess(t)
            t.components.grogginess.grog_amount=4;t.components.grogginess.isgroggy=true
            t.components.grogginess.wearofftime=0;t.components.locomotor.slow=true;t.knockedout=true''')
        self.apply()
        g = self.lua.globals().t.components.grogginess
        self.assertEqual(g.grog_amount, 0)
        self.assertFalse(g.isgroggy)
        self.assertFalse(self.lua.globals().t.knockedout)
        self.assertFalse(self.lua.globals().t.components.locomotor.slow)
        self.assertEqual(self.lua.globals().t.events.cometo, 1)

    def test_sleep_immunity_buff_is_preserved_when_native_grogginess_already_immune(self):
        self.lua.execute('''t.components.grogginess=native_classes.grogginess(t)
            t.components.grogginess:AddImmunitySource('positive_buff')
            t.components.grogginess.grog_amount=4;t.components.grogginess.isgroggy=true''')
        self.apply()
        self.assertEqual(self.lua.globals().t.components.grogginess.grog_amount, 0)
        self.assertTrue(self.lua.eval("t.components.grogginess._immunity_sources:CalculateModifierFromKey('groggyimmunity')"))

    def test_ink_uses_native_deinked_event_and_fx_removal(self):
        self.lua.execute('''t.components.inkable=native_classes.inkable(t)
            t.components.inkable.inked=true;t.components.inkable.inktime=2
            ink=AddEffect('squid_ink_player_fx','squid_ink_player_fx')
            function t:RemoveDebuff(key) self.components.debuffable:RemoveDebuff(key) end''')
        self.apply()
        self.assertFalse(self.lua.globals().t.components.inkable.inked)
        self.assertEqual(self.lua.globals().t.events.deinked, 1)
        self.assertTrue(self.lua.globals().ink.removed)

    def test_extinguish_dry_temperature_and_pin(self):
        self.lua.execute('''
            t.components.burnable={IsBurning=function() return true end,IsSmoldering=function() return true end,Extinguish=function(s) s.cleared=true end}
            t.components.moisture={GetMoisture=function() return 40 end,DoDelta=function(s,delta) s.delta=delta end}
            t.components.temperature={current=-10,overheattemp=70,IsFreezing=function(s) return s.current<0 end,IsOverheating=function(s) return s.current>s.overheattemp end,SetTemperature=function(s,v) s.current=v end}
            t.components.pinnable={IsStuck=function() return true end,Unstick=function(s) s.cleared=true end}
        ''')
        self.apply()
        components = self.lua.globals().t.components
        self.assertTrue(components.burnable.cleared)
        self.assertTrue(components.pinnable.cleared)
        self.assertEqual(components.moisture.delta, -40)
        self.assertGreaterEqual(components.temperature.current, 0)
        components.temperature.current = 90
        self.apply()
        self.assertLessEqual(components.temperature.current, 70)
        components.temperature.current = 15
        self.apply()
        self.assertEqual(components.temperature.current, 15)

    def test_sleeper_sleepiness_and_already_scheduled_sleep_are_cleared(self):
        self.lua.execute('''t.components.sleeper={sleepiness=4,asleep=true,IsAsleep=function(s) return s.asleep end,WakeUp=function(s) s.asleep=false;s.sleepiness=0 end,AddSleepiness=function(s,v) s.sleepiness=s.sleepiness+v end}''')
        self.apply()
        self.assertFalse(self.lua.globals().t.components.sleeper.asleep)
        self.lua.execute('t.components.sleeper.sleepiness=0;t.components.sleeper.asleep=true')
        self.apply()
        self.assertFalse(self.lua.globals().t.components.sleeper.asleep)
        self.lua.execute('t.components.sleeper.sleepiness=1;t.components.sleeper.asleep=false')
        self.apply()
        self.assertEqual(self.lua.globals().t.components.sleeper.sleepiness, 0)

    def test_voluntary_player_sleep_without_grogginess_is_retained(self):
        self.lua.execute('''t.components.grogginess=native_classes.grogginess(t)
            t.sleeping=true;t.sg.HasStateTag=function(_,tag) return tag=='sleeping' end''')
        self.apply()
        self.assertTrue(self.lua.globals().t.sleeping)
        self.assertIsNone(self.lua.globals().t.events.cometo)


if __name__ == '__main__':
    unittest.main(verbosity=2)
