"""Native sanity-cost and weapon-durability regressions for the new equipment.

Reuse the existing entity fixtures; execute installed DST SourceModifierList,
Sanity:Recalc, Weapon and FiniteUses rather than replacing their
calculations with test formulas.
"""
import unittest
import zipfile

import test_bag
import test_component
from test_review_regressions import GAME, ROOT, vanilla


class ZCost(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        with zipfile.ZipFile(GAME) as archive:
            self.lua.execute(archive.read("scripts/util/sourcemodifierlist.lua").decode("utf-8-sig"))
            self.lua.globals().easing = self.lua.execute(archive.read("scripts/easing.lua").decode("latin-1"))
        self.lua.execute("Sanity={};EntityScript={is_instance=function() return false end}")
        for method in ("SetNegativeAuraImmunity", "Recalc", "OnUpdate"):
            self.lua.execute(vanilla("components/sanity.lua", "function Sanity:" + method + "("))
        self.lua.execute("""
            -- Current installed tuning: one segment is 30 seconds.
            TUNING={SANITYAURA_HUGE=100/(30*.5),SANITYAURA_LARGE=100/(30*2),
                SANITY_GHOST_PLAYER_DRAIN=0,SANITY_AURA_SEACH_RANGE=10}
            -- Disable unrelated ambient contributions; keep aura processing and
            -- external skill modifiers active in the unmodified native method.
            LIGHT_SANITY_DRAINS={[1]={}};RATE_SCALE={}
            SCRATCHPAD_AURANAMES_HasBaseAuraNameBeenUsed=function() return false end
            sanity=inst.components.sanity;sanity.inst=inst
            sanity.externalmodifiers=SourceModifierList(inst,0,SourceModifierList.additive)
            sanity.neg_aura_immune_sources=SourceModifierList(inst,false,SourceModifierList.boolean)
            sanity.sanity_aura_immune_sources=SourceModifierList(inst,false,SourceModifierList.boolean)
            sanity.light_drain_immune_sources=SourceModifierList(inst,true,SourceModifierList.boolean)
            sanity.no_moisture_penalty=true
            sanity.SetNegativeAuraImmunity=Sanity.SetNegativeAuraImmunity
            sanity.dapperness_mult=0;sanity.mode=1;sanity.neg_aura_absorb=0;sanity.rate_modifier=1
            sanity.GetAuraMultipliers=function() return 1 end
            sanity.RecalcGhostDrain=function(s) s.ghost_drain_mult=0 end
            sanity.DoDelta=function(s,n) s.total=(s.total or 0)+n end
            sanity.UpdateMode_Internal=function() end;sanity.Recalc=Sanity.Recalc
            inst.components.health.IsInvincible=function() return invincible or false end
            sleeping=false;inst.sg={HasStateTag=function(_,tag) return tag=='sleeping' and sleeping or tag=='busy' end}
            RATE_SCALE.NEUTRAL=0
            function frame(dt)
                now=now+dt;Sanity.OnUpdate(sanity,dt)
                for c in pairs(inst.updating) do c:OnUpdate(dt) end
            end
            inst.components.combat.externaldamagemultipliers=SourceModifierList(inst)
            inst:AddTag('player');TheNet={GetPVPEnabled=function() return false end}
            aura={components={sanityaura={GetAura=function() return -10 end}}}
        """)

    def test_z_cost_is_150_per_real_minute_through_native_onupdate(self):
        self.assertTrue(self.lua.eval("component:Cast('z')"))
        self.lua.execute("TheSim.FindEntities=function() return {} end;for i=1,60 do frame(1) end")
        self.assertEqual(self.lua.eval("sanity.total"), -150)

    def test_z_cost_continues_during_native_sleep_invincibility_and_spawn_protection(self):
        for state in ('sleeping=true', 'invincible=true', "inst:AddTag('spawnprotection')", 'inst.is_teleporting=true'):
            with self.subTest(state=state):
                self.setUp()
                self.lua.execute("component:Cast('z');TheSim.FindEntities=function() return {} end;"+state)
                self.lua.execute('for i=1,60 do frame(1) end')
                self.assertTrue(self.lua.eval('component:IsZ()'))
                self.assertEqual(self.lua.eval('sanity.total or 0'), -150)

    def test_z_cost_is_not_scaled_by_native_rate_modifier_or_charged_twice(self):
        self.lua.execute("component:Cast('z');sanity.rate_modifier=.1;TheSim.FindEntities=function() return {} end")
        self.lua.execute('for i=1,240 do frame(.25) end')
        self.assertAlmostEqual(self.lua.eval('sanity.total or 0'), -150)

    def test_domain_blocks_enemy_aura_but_native_sanity_still_charges_z(self):
        self.lua.execute("TheSim.FindEntities=function() return {aura} end;Sanity.Recalc(sanity,1)")
        self.assertEqual(self.lua.eval("sanity.total"), -10)
        self.lua.execute("""
            TheSim.FindEntities=function() return {inst} end
            component:Cast('z');component:Cast('x')
            TheSim.FindEntities=function() return {aura} end
            sanity.total=0;frame(1)
        """)
        self.assertTrue(self.lua.eval("sanity.neg_aura_immune_sources:Get()"))
        self.assertAlmostEqual(self.lua.eval("sanity.total"), -2.5)

    def test_z_off_stops_cost_and_preserves_other_sanity_sources(self):
        self.lua.execute("sanity.externalmodifiers:SetModifier(inst,2,'other_buff');component:Cast('z')")
        self.lua.execute('TheSim.FindEntities=function() return {} end;frame(1)')
        self.assertAlmostEqual(self.lua.eval('sanity.total'), -.5)
        self.assertTrue(self.lua.eval("component:Cast('z')"))
        self.assertFalse(self.lua.eval("component:IsZ()"))
        self.assertEqual(self.lua.eval("sanity.externalmodifiers:Get()"), 2)
        self.lua.execute('sanity.total=0;frame(1)')
        self.assertEqual(self.lua.eval('sanity.total'), 2)

    def test_save_load_restores_z_toggle_and_cost_after_deferred_initialization(self):
        self.lua.execute("component:Cast('z');saved=component:OnSave();component:Cast('z')")
        self.assertEqual(self.lua.eval("sanity.externalmodifiers:Get()"), 0)
        self.lua.execute("component:OnLoad(saved);for _,fn in ipairs(inst.tasks) do fn() end")
        self.assertTrue(self.lua.eval("component:IsZ()"))
        self.assertTrue(self.lua.eval("inst._klbq_z:value()"))
        self.lua.execute('TheSim.FindEntities=function() return {} end;frame(1)')
        self.assertAlmostEqual(self.lua.eval('sanity.total'), -2.5)

    def test_death_clears_z_and_respawn_keeps_it_off(self):
        self.lua.execute("component:Cast('z');component:OnDeath()")
        self.assertFalse(self.lua.eval("component:IsZ()"))
        self.assertFalse(self.lua.eval("inst._klbq_z:value()"))
        self.assertEqual(self.lua.eval("sanity.externalmodifiers:Get()"), 0)
        self.lua.execute("component:OnRespawn();component:Tick()")
        self.assertFalse(self.lua.eval("component:IsZ()"))
        self.assertEqual(self.lua.eval("sanity.externalmodifiers:Get()"), 0)
        self.lua.execute('TheSim.FindEntities=function() return {} end;frame(1)')
        self.assertEqual(self.lua.eval('sanity.total or 0'), 0)

    def test_entity_removal_clears_z_cost_without_touching_other_modifiers(self):
        self.lua.execute("""
            sanity.externalmodifiers:SetModifier(inst,2,'other_buff')
            component:Cast('z');component:OnRemoveEntity()
        """)
        self.assertEqual(self.lua.eval("sanity.externalmodifiers:Get()"), 2)
        self.lua.execute('TheSim.FindEntities=function() return {} end;frame(1)')
        self.assertEqual(self.lua.eval('sanity.total'), 2)


class BladeDurability(unittest.TestCase):
    def setUp(self):
        fixture = test_bag.SingularityBag()
        fixture.setUp()
        self.lua = fixture.lua
        with zipfile.ZipFile(GAME) as archive:
            for module in ("util/sourcemodifierlist", "components/spdamageutil",
                           "components/weapon", "components/finiteuses"):
                source = archive.read("scripts/" + module + ".lua").decode("utf-8-sig")
                self.lua.execute("package.preload[...] = function() " + source + " end", module)
        self.lua.execute("""
            local old=CreateEntity
            CreateEntity=function()
                local inst=old();inst.Remove=function(s) s.removed=true end
                local add=inst.AddComponent
                inst.AddComponent=function(s,name)
                    if name=='weapon' or name=='finiteuses' then
                        s.components[name]=require('components/'..name)(s)
                    else add(s,name) end
                end
                return inst
            end
            attacker={IsValid=function() return true end,components={}}
        """)
        source = (ROOT / "mods/klbq_kanami/scripts/prefabs/klbq_blade.lua").read_text(encoding="utf-8-sig")
        self.lua.globals().bladeprefab = self.lua.execute(source)
        self.lua.execute("blade=bladeprefab.fn()")

    def test_native_weapon_damage_and_initial_durability(self):
        self.assertEqual(self.lua.eval("blade.components.weapon:GetDamage(attacker,{})"), (51, None))
        self.assertEqual(self.lua.eval("blade.components.finiteuses:GetUses()"), 200)

    def test_native_weapon_attack_exhausts_only_on_two_hundredth_hit(self):
        self.lua.execute("for i=1,199 do blade.components.weapon:OnAttack(attacker,{}) end")
        self.assertEqual(self.lua.eval("blade.components.finiteuses:GetUses()"), 1)
        self.assertFalse(bool(self.lua.eval("blade.removed")))
        self.lua.execute("blade.components.weapon:OnAttack(attacker,{})")
        self.assertEqual(self.lua.eval("blade.components.finiteuses:GetUses()"), 0)
        self.assertTrue(self.lua.eval("blade.removed"))

    def test_native_save_reload_preserves_remaining_uses_and_final_break(self):
        self.lua.execute("""
            for i=1,199 do blade.components.weapon:OnAttack(attacker,{}) end
            saved=blade.components.finiteuses:OnSave()
            restored=bladeprefab.fn();restored.components.finiteuses:OnLoad(saved)
        """)
        self.assertEqual(self.lua.eval("restored.components.finiteuses:GetUses()"), 1)
        self.assertFalse(bool(self.lua.eval("restored.removed")))
        self.lua.execute("restored.components.weapon:OnAttack(attacker,{})")
        self.assertTrue(self.lua.eval("restored.removed"))
        self.assertEqual(self.lua.eval("restored.components.finiteuses:GetUses()"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
