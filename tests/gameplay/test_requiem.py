"""Requiem uses current DST Combat/Weapon/finiteuses and native F ATTACK.

Fixtures replace only engine entities, input, and SG scheduling. Damage remains
the current installed Lua 5.1 Combat path, including native range and health caps.
"""
import sys
import unittest
import zipfile
from pathlib import Path

import test_crossbow
from test_review_regressions import GAME, vanilla

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "mods/klbq_kanami/scripts/klbq_kanami/requiem.lua"
PREFAB = ROOT / "mods/klbq_kanami/scripts/prefabs/klbq_requiem.lua"


class Requiem(unittest.TestCase):
    def use_sg(self, name):
        test_crossbow.Crossbow.use_sg(self, name)
        self.lua.execute("if extrahandlers and extrahandlers[...] then for a,h in pairs(extrahandlers[...]) do nativegraph.actionhandlers[a]=h end end", name, name)

    def setUp(self):
        self.assertTrue(MODULE.is_file(), "镇魂歌攻击与圆斩模块尚未实现")
        self.assertTrue(PREFAB.is_file(), "镇魂歌成品尚未实现")
        test_crossbow.Crossbow.setUp(self)
        with zipfile.ZipFile(GAME) as z:
            self.lua.execute("package.preload['components/finiteuses']=function() " +
                             z.read("scripts/components/finiteuses.lua").decode("utf-8-sig") + " end")
        for method in ("GetHitRange", "CalcHitRangeSq", "CanHitTarget"):
            self.lua.execute(vanilla("components/combat.lua", "function Combat:" + method + "("))
        self.lua.execute("""
          TimeEvent=function(t,f) return {time=t,fn=f} end
          env.AddAction=function(a)
            ACTIONS[a.id]=a;return a
          end
          Action=function(t) return t or {} end
          extrahandlers={wilson={},wilson_client={}}
          env.AddStategraphActionHandler=function(n,h) extrahandlers[n][h.action]=h end
          env.AddComponentAction=function() end
          env.AddStategraphPostInit=function(n,fn)
            local old=sgposts[n]
            sgposts[n]=function(sg) if old then old(sg) end;fn(sg) end
          end
          local oldadd=player.AddComponent
          CreateEntity=function()
            local e=entity('created');local old=e.AddComponent
            e.AddComponent=function(s,n)
              if n=='finiteuses' then s.components[n]=require('components/finiteuses')(s)
              else old(s,n) end
            end
            return e
          end
          combat.CalcReflectedDamage=function() return 0 end
          combat.CanExtinguishTarget=function() return false end
          combat.CanLightTarget=function() return false end
          combat.IsAlly=function(s,t) return t.friendly==true end
          target.x=1.5;target:AddTag('_combat')
          targets={target};TheSim.FindEntities=function() return targets end
          effects=0;SpawnPrefab=function() effects=effects+1;return entity('fx') end
          player.AnimState.PlayAnimation=function(s,n) currentanim=n end
          player.AnimState.PushAnimation=function(s,n) queuedanim=n end
          player.components.rider={IsRiding=function() return false end}
          player.replica.inventory.GetActiveItem=function() return activeitem end
          function BufferedAction(d,t,a,item,pos)
            return {doer=d,target=t,action=a,invobject=item,pos=pos,
              GetActionPoint=function(s) return s.pos end}
          end
          picker={inst=player,containers={},GetRightClickActions=function() return originalactions or {} end}
          player.components.playeractionpicker=picker
        """)
        self.lua.execute("requiem=(function() " + MODULE.read_text(encoding="utf-8-sig") + " end)();requiem.Install(env)")
        self.lua.globals().swordprefab = self.lua.execute(PREFAB.read_text(encoding="utf-8-sig"))
        self.lua.execute("""
          hand=swordprefab.fn();hand.prefab='klbq_requiem';hand.components.inventoryitem.owner=player
          hand.replica.inventoryitem={IsWeapon=function() return true end,SetAttackRange=function() end,
            AttackRange=function() return hand.components.weapon.attackrange or 0 end}
          hooks.combat(combat);classhooks['components/combat_replica'](replica)
          if classhooks['components/playeractionpicker'] then classhooks['components/playeractionpicker'](picker) end
          hits=0
          function tick(t)
            local previous=now;now=t;local state=player.sg.currentstate
            if state.onupdate then state.onupdate(player, t-previous) end
            if player.sg.currentstate~=state then return end
            for i,event in ipairs(state.timeline or {}) do
              if not player.sg.statemem['event'..i] and t+1e-7>=player.sg.entered+event.time then
                player.sg.statemem['event'..i]=true;event.fn(player)
              end
            end
            if player.sg.currentstate==state and player.sg.timeout and t+1e-7>=player.sg.entered+player.sg.timeout then
              if state.ontimeout then state.ontimeout(player) end
            end
          end
          local oldmake=makesg
          makesg=function(n)
            local sg=oldmake(n);local oldgo=sg.GoToState
            sg.GoToState=function(s,n) s.entered=now;s.timeout=nil;return oldgo(s,n) end
            return sg
          end
          function sweep()
            local actions=picker:GetRightClickActions(Vector3(100,0,100),nil)
            if not actions[1] then return false end
            player.bufferedaction=actions[1]
            local h=nativegraph.actionhandlers[ACTIONS.KLBQ_REQUIEM_SWEEP]
            assert(h,'missing sweep handler')
            local d=type(h.deststate)=='function' and h.deststate(player,actions[1]) or h.deststate
            if d then player.sg:GoToState(d) end
          end
        """)
        self.use_sg("wilson")

    def fire(self):
        test_crossbow.Crossbow.fire(self)

    def test_native_radius_fixture_keeps_target_brain_stopped_after_deferred_wake(self):
        self.lua.execute('EntityScript={}')
        for method in ('StopBrain', '_EnableBrain_Internal'):
            self.lua.execute(vanilla('entityscript.lua', 'function EntityScript:' + method + '('))
        source = (ROOT / 'tests/engine_mod/requiem.lua').read_text(encoding='utf-8-sig')
        start = source.index('        local function Victim(dx,dz)')
        end = source.index('        local function SweepAction(', start)
        self.lua.execute('''
            brainstarts=0
            target._braindisabled=true;target.brain=nil
            target.brainfn=function() return {_Start_Internal=function() brainstarts=brainstarts+1 end} end
            target.StopBrain=EntityScript.StopBrain
            target.components.combat.SetTarget=function() end
            target.components.locomotor={Stop=function() end}
            target.components.health.SetMaxHealth=function() end
            target.components.health.SetPercent=function() end
            Spawn=function() return target end
        ''' + source[start:end] + '\nVictim(0,0);EntityScript._EnableBrain_Internal(target)')
        self.assertEqual(self.lua.eval('brainstarts'), 0,
                         'radius fixture resumed AI after the pending engine wake')

    def test_native_remote_predicted_walk_handoff_preserves_normal_hit(self):
        test_crossbow.Crossbow.enable_native_locomotor(self)
        test_crossbow.Crossbow.enable_native_remote_prediction(self)
        self.lua.execute('pc:OnRemoteAttackButton(target,false,false,false,false)')
        self.assertTrue(self.lua.eval('pc.attack_buffer.forced and pc.attack_buffer._predictpos'))
        test_crossbow.Crossbow.dispatch_native_remote_attack_buffer(self)
        self.assertEqual(self.lua.eval("pc.remote_vector.y"),5)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"klbq_requiem_attack")
        self.lua.execute("tick(.3)")
        self.assertEqual(self.lua.eval("hits"),1)
        self.assertEqual(self.lua.eval("hitdamage"),51)

    def test_native_remote_predicted_walk_handoff_preserves_sweep_windup(self):
        test_crossbow.Crossbow.enable_native_remote_prediction(self)
        self.lua.execute("pc:OnRemoteBufferedAction();sweep();tick(.6)")
        self.assertEqual(self.lua.eval("pc.remote_vector.y"),5)
        self.assertEqual(self.lua.eval("hits"),1)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"),599)

    def test_new_remote_movement_after_handoff_cancels_sweep(self):
        test_crossbow.Crossbow.enable_native_remote_prediction(self)
        self.lua.execute("pc:OnRemoteBufferedAction();sweep();pc.remote_vector.y=3;tick(.6)")
        self.assertEqual(self.lua.eval("hits"),0)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"),600)

    def test_client_native_stopped_walk_cache_keeps_normal_and_sweep_previews(self):
        for start,release,state in (("pc:DoAttackButton()",.3,"klbq_requiem_attack"),
                                    ("sweep()",.6,"klbq_requiem_sweep")):
            with self.subTest(state=state):
                self.setUp()
                self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4),canattack=net(true)}")
                self.use_sg("wilson_client")
                test_crossbow.Crossbow.enable_native_client_last_walk_cache(self)
                self.lua.execute(start)
                self.lua.execute("tick(...)",release)
                self.assertEqual(self.lua.eval("player.sg.currentstate.name"),state)
                self.assertEqual(self.lua.eval("previews or 0"),1)
                self.assertEqual(self.lua.eval("hits"),0)

    def test_f_and_leftclick_use_native_attack_with_point_eight_second_period(self):
        self.fire()
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_requiem_attack")
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"), .8)
        self.lua.execute("tick(.3)")
        self.assertEqual(self.lua.eval("hits"), 1)
        self.assertEqual(self.lua.eval("hitdamage"), 51)
        self.lua.execute("now=.799")
        self.assertTrue(self.lua.eval("combat:InCooldown()"))
        self.lua.execute("tick(.8)")
        self.assertFalse(self.lua.eval("combat:InCooldown()"))
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)
        self.lua.execute("begin(BufferedAction(player,target,ACTIONS.ATTACK));tick(1.1)")
        self.assertEqual(self.lua.eval("hits"), 2)

    def test_repeated_leftclick_before_hit_keeps_native_attacktarget_and_first_hit(self):
        self.fire()
        self.lua.execute("tick(.1);begin(BufferedAction(player,target,ACTIONS.ATTACK));tick(.2);begin(BufferedAction(player,target,ACTIONS.ATTACK));tick(.3)")
        self.assertEqual(self.lua.eval("hits"), 1)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_requiem_attack")

    def test_repeated_client_leftclick_before_hit_does_not_restart_prediction(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)}")
        self.use_sg("wilson_client")
        self.fire()
        self.lua.execute("tick(.1);begin(BufferedAction(player,target,ACTIONS.ATTACK));tick(.3)")
        self.assertEqual(self.lua.eval("previews"), 1)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_requiem_attack")
        self.assertEqual(self.lua.eval("hits"), 0)

    def test_sweep_has_point_six_second_windup_and_two_second_recovery(self):
        self.lua.execute("sweep();tick(.599)")
        self.assertEqual(self.lua.eval("hits"), 0)
        self.lua.execute("tick(.6)")
        self.assertEqual(self.lua.eval("hits"), 1)
        self.assertEqual(self.lua.eval("hitdamage"), 51)
        self.lua.execute("tick(1.999)")
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_requiem_sweep")
        self.lua.execute("tick(2)")
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "idle")

    def test_sweep_is_360_degrees_centered_on_player_with_four_point_five_radius(self):
        self.lua.execute("""
          targets={}
          for _,pos in ipairs({{4.5,0},{-4.5,0},{0,4.5},{0,-4.5},{4.501,0}}) do
            local t=entity('hound');t.x=pos[1];t.z=pos[2];t:AddTag('_combat')
            t.components.health=target.components.health;t.components.combat=target.components.combat
            t.replica.combat=target.replica.combat;targets[#targets+1]=t
          end
          sweep();tick(.6)
        """)
        self.assertEqual(self.lua.eval("hits"), 4)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)

    def test_sweep_filters_players_followers_noncombat_dead_limbo_and_hidden(self):
        for change in ("target.friendly=true", "target:AddTag('player')", "target:AddTag('structure')",
                       "target:AddTag('wall')", "target:AddTag('tree')", "target.dead=true",
                       "target:AddTag('INLIMBO')", "target.visible=false", "target:AddTag('notarget')",
                       "target.components.combat=nil", "target.components.health=nil",
                       "target.components.follower={leader=player}"):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change + ";sweep();tick(.6)")
                self.assertEqual(self.lua.eval("hits"), 0)
                self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)

    def test_treeguard_is_a_legal_living_target_even_with_native_tree_tag(self):
        self.lua.execute("target:AddTag('tree');target:AddTag('plantcreature');target:AddTag('monster');sweep();tick(.6)")
        self.assertEqual(self.lua.eval("hits"), 1)

    def test_self_centered_sweep_hits_visible_entities_even_in_native_darkness(self):
        self.lua.execute(vanilla('simutil.lua','function CanEntitySeePoint(')+'\n'
                         +vanilla('simutil.lua','function CanEntitySeeTarget('))
        self.lua.execute('''
            TUNING.DARK_CUTOFF=.2
            TheSim.GetLightAtPoint=function()return 0 end
            _CanEntitySeeInDark=function()return false end
            sweep();tick(.6)
        ''')
        self.assertEqual(self.lua.eval('hits'),1)

    def test_swap_death_string_move_or_equip_event_cancel_before_release(self):
        for change in ("hand=entity('spear')", "player.dead=true", "player._klbq_string=net(true)",
                       "loco.wantstomoveforward=true", "pc.directwalking=true"):
            with self.subTest(change=change):
                self.setUp();self.lua.execute("sword=hand;sweep();" + change + ";tick(.6)")
                self.assertEqual(self.lua.eval("hits"), 0)
                self.assertEqual(self.lua.eval("sword.components.finiteuses:GetUses()"), 600)
                self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "idle")

    def test_sweep_cooldown_is_player_scoped_after_swap_and_interruption(self):
        self.lua.execute("sweep();tick(.1);sword=hand;hand=entity('spear');tick(.2);hand=sword;sweep();tick(.8)")
        self.assertEqual(self.lua.eval("hits"), 0)
        self.lua.execute("now=2;sweep();tick(2.6)")
        self.assertEqual(self.lua.eval("hits"), 1)

    def test_transition_preserves_new_buffered_action_during_previous_state_exit(self):
        self.fire()
        self.lua.execute("tick(.1);sweep();tick(.7)")
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_requiem_sweep")
        self.assertEqual(self.lua.eval("hits"), 1)

    def test_string_blocks_both_attack_and_sweep_before_enter(self):
        self.lua.execute("player._klbq_string=net(true)")
        self.fire()
        self.assertEqual(self.lua.eval("hits"), 0)
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)

    def test_server_revive_protection_refuses_f_and_forced_sweep_while_still_equipped(self):
        self.lua.execute("""
          player.components.klbq_kanami={state={string=false},CanUseHands=function() return false end}
        """)
        self.fire()
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "idle")
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)
        self.lua.execute("""
          player.bufferedaction=BufferedAction(player,nil,ACTIONS.KLBQ_REQUIEM_SWEEP,hand,Vector3(0,0,0))
          player.sg:GoToState('klbq_requiem_sweep');tick(.6)
        """)
        self.assertEqual(self.lua.eval("hits"), 0)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)
        self.lua.execute("player.components.klbq_kanami.CanUseHands=function() return true end;now=3")
        self.fire();self.lua.execute("tick(3.3)")
        self.assertEqual(self.lua.eval("hits"), 1)

    def test_client_revive_protection_blocks_f_preview_and_sweep_while_still_equipped(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)};player._klbq_protect=net(true)")
        self.use_sg("wilson_client")
        self.fire()
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "idle")
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)
        self.assertIsNone(self.lua.eval("previews"))
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)

    def test_revive_protection_starting_during_either_windup_cancels_before_damage(self):
        for start, release in (("sweep()", .6), ("pressed[CONTROL_ATTACK]=true;pc:DoAttackButton()", .3)):
            for protect in ("player._klbq_protect=net(true)",
                            "player.components.klbq_kanami={state={string=false},CanUseHands=function() return false end}"):
                with self.subTest(start=start, protect=protect):
                    self.setUp();self.lua.execute(start + ";tick(.1);" + protect)
                    self.lua.execute("tick(...)", release)
                    self.assertEqual(self.lua.eval("hits"), 0)
                    self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)
                    self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "idle")

    def test_rightclick_entity_sweeps_but_preserves_container_and_active_item_actions(self):
        self.assertTrue(self.lua.eval("picker:GetRightClickActions(Vector3(10,0,10),target)[1].action==ACTIONS.KLBQ_REQUIEM_SWEEP"))
        self.assertIsNone(self.lua.eval("picker:GetRightClickActions(Vector3(10,0,10),target)[1].target"))
        self.lua.execute("ACTIONS.OPEN={};originalactions={{action=ACTIONS.OPEN}}")
        self.assertTrue(self.lua.eval("picker:GetRightClickActions(Vector3(0,0,0),target)[1].action==ACTIONS.OPEN"))
        self.lua.execute("originalactions={};activeitem=entity('twigs')")
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)
        self.lua.execute("activeitem=nil;picker.containers[target]=true")
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)

    def test_client_predicts_without_damage_or_durability_use(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)}")
        self.use_sg("wilson_client")
        self.lua.execute("sweep();tick(.6)")
        self.assertEqual(self.lua.eval("hits"), 0)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)
        self.assertEqual(self.lua.eval("previews"), 1)

    def test_client_native_f_previews_once_without_damage_or_durability_use(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)}")
        self.use_sg("wilson_client")
        self.fire();self.lua.execute("tick(.3)")
        self.assertEqual(self.lua.eval("hits"), 0)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)
        self.assertEqual(self.lua.eval("previews"), 1)

    def test_normal_windup_cancels_on_death_move_swap_and_string(self):
        for change in ("player.dead=true", "pc.directwalking=true", "hand=entity('spear')", "player._klbq_string=net(true)"):
            with self.subTest(change=change):
                self.setUp();self.fire();self.lua.execute(change + ";tick(.3)")
                self.assertEqual(self.lua.eval("hits"), 0)

    def test_equipment_event_cancels_sweep_without_spending_durability(self):
        self.lua.execute("""
          sweep()
          for _,ev in ipairs(player.sg.currentstate.events) do if ev.name=='unequip' then ev.fn(player);break end end
          tick(.6)
        """)
        self.assertEqual(self.lua.eval("hits"), 0)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)

    def test_finished_sword_is_a_sharp_unrestricted_600_use_51_physical_weapon(self):
        self.lua.execute("physical,special=hand.components.weapon:GetDamage(player,target)")
        self.assertEqual(self.lua.eval("physical"), 51)
        self.assertIsNone(self.lua.eval("special"))
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 600)
        self.assertTrue(self.lua.eval("hand:HasTag('sharp')"))
        self.assertIsNone(self.lua.eval("hand.components.equippable.restrictedtag"))

    def test_other_weapon_period_and_native_attack_are_untouched(self):
        self.lua.execute("combat.min_attack_period=.7;hand=entity('spear')")
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"), .7)
        self.assertEqual(self.lua.eval("nativehandler.deststate(player,BufferedAction(player,target,ACTIONS.ATTACK))"), "attack")
        self.assertEqual(self.lua.eval("#picker:GetRightClickActions(Vector3(0,0,0),target)"), 0)
        self.lua.execute("hand=entity('klbq_crossbow')")
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"), .125)
        self.assertEqual(self.lua.eval("nativehandler.deststate(player,BufferedAction(player,target,ACTIONS.ATTACK))"), "klbq_crossbow_attack")

    def test_authoritative_sweep_action_cannot_be_replayed_in_same_state(self):
        self.lua.execute("sweep();savedaction=player.bufferedaction;tick(.6);ACTIONS.KLBQ_REQUIEM_SWEEP.fn(savedaction)")
        self.assertEqual(self.lua.eval("hits"), 1)
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)

    def test_native_onattack_failure_restores_original_durability_policy(self):
        self.lua.execute("""
          hand.components.weapon.onattack=function() error('other mod onattack failed') end
          sweep();ok,err=pcall(tick,.6)
        """)
        self.assertFalse(self.lua.eval("ok"))
        self.assertIn("other mod onattack failed", self.lua.eval("err"))
        self.assertFalse(self.lua.eval("hand.components.finiteuses:IgnoresCombatDurabilityLoss()"))

    def test_empty_sweep_costs_one_use_and_last_use_removes_only_after_all_targets(self):
        self.lua.execute("targets={};sweep();tick(.6)")
        self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)
        self.lua.execute("""
          tick(2);hand.components.finiteuses:SetUses(1)
          second=entity('hound');second.x=-2;second.components=target.components;second.replica=target.replica
          targets={target,second};sweep();tick(2.6)
        """)
        self.assertEqual(self.lua.eval("hits"), 2)
        self.assertTrue(self.lua.eval("hand.removed"))

    def native_target(self):
        self.lua.execute("Health={}")
        for method in ("GetPercent", "GetMaxWithPenalty", "IsInvincible", "IsDead", "CanFadeOut", "DoDelta", "SetVal"):
            self.lua.execute(vanilla("components/health.lua", "function Health:" + method + "("))
        self.lua.execute(vanilla("components/combat.lua", "function Combat:GetAttacked_Internal("))
        self.lua.execute(vanilla("components/combat.lua", "function Combat:GetAttacked("))
        self.lua.execute("""
          math.clamp=function(v,a,b) return math.max(a,math.min(b,v)) end
          CanEntityBecomeCorpse=function() return false end;IsRangedWeapon=function() return false end
          target.components.combat=setmetatable({inst=target,externaldamagetakenmultipliers={Get=function() return 1 end},
            CanBeAttacked=function() return true end,ShouldRecoil=function(s,a,w,d) return false,d end,
            GetImpactSound=function() return nil end},{__index=Combat})
          target.components.health=setmetatable({inst=target,currenthealth=1000,maxhealth=1000,penalty=0,
            nonlethal_pct=0,absorb=.5,playerabsorb=0,nofadeout=true,
            externalabsorbmodifiers={Get=function() return 0 end},externalreductionmodifiers={Get=function() return 0 end}}, {__index=Health})
        """)

    def test_native_damage_caps_invulnerability_and_absorption_apply_to_circle(self):
        self.native_target()
        self.lua.execute("sweep();tick(.6)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"), 974.5)
        self.lua.execute("tick(2);target.components.health.maxdamagetakenperhit=-1;sweep();tick(2.6)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"), 973.5)
        self.lua.execute("tick(4);target.components.health.invincible=true;sweep();tick(4.6)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"), 973.5)

    def test_native_armor_and_planar_entity_reduce_physical_sweep_normally(self):
        self.native_target()
        self.lua.execute("Armor={};Inventory={};PlanarEntity={};EquipSlot={Count=function() return 1 end,FromID=function() return 'body' end}")
        self.lua.execute("ProfileStatsAdd=function() end")
        for method in ("CanResist", "GetAbsorption", "GetBonusDamage", "TakeDamage", "SetCondition", "GetPercent"):
            self.lua.execute(vanilla("components/armor.lua", "function Armor:" + method + "("))
        self.lua.execute(vanilla("components/inventory.lua", "function Inventory:ApplyDamage("))
        self.lua.execute(vanilla("components/planarentity.lua", "function PlanarEntity:AbsorbDamage("))
        self.lua.execute("""
          armoritem=entity('armorwood')
          armor=setmetatable({inst=armoritem,condition=1000,maxcondition=1000,absorb_percent=.8,
            conditionlossmultipliers={Get=function() return 1 end}},{__index=Armor})
          armoritem.components.armor=armor
          target.components.inventory=setmetatable({equipslots={body=armoritem}},{__index=Inventory})
          target.components.planarentity=setmetatable({OnResistNonPlanarAttack=function() planarresisted=true end},{__index=PlanarEntity})
          target.components.health.absorb=0;sweep();tick(.6)
        """)
        expected = ((51 * .2 * 4 + 64) ** .5 - 8) * 4
        self.assertAlmostEqual(self.lua.eval("target.components.health.currenthealth"), 1000 - expected)
        self.assertAlmostEqual(self.lua.eval("armor.condition"), 1000 - 51 * .8)
        self.assertTrue(self.lua.eval("planarresisted"))

    def test_native_remote_rightclick_validates_same_sweep_and_does_not_attack_cursor_target(self):
        self.lua.execute(vanilla("components/playercontroller.lua", "function PlayerController:OnRemoteRightClick("))
        self.lua.execute("""
          SetClientRequestedAction=function() end;ClearClientRequestedAction=function() end
          CONTROL_SECONDARY=9
          pc.DecodeControlMods=function() end;pc.ClearControlMods=function() end;pc.handler=nil
          ACTIONS.KLBQ_REQUIEM_SWEEP.code=777;ACTIONS.KLBQ_REQUIEM_SWEEP.mod_name='klbq_test'
          picker.DoGetMouseActions=function(s,pos,target) return nil,s:GetRightClickActions(pos,target)[1] end
          pc.DoAction=function(s,act)
            player.bufferedaction=act
            player.sg:GoToState(nativegraph.actionhandlers[act.action].deststate)
          end
          distant=entity('hound');distant.x=100
          pc:OnRemoteRightClick(777,Vector3(100,0,0),distant,0,false,0,false,'klbq_test')
          tick(.6)
        """)
        self.assertEqual(self.lua.eval("hits"), 1)
        self.assertTrue(self.lua.eval("hitattacker==player"))

    def test_native_circle_triggers_kanami_passive_once_globally_and_z_once(self):
        for z, first, second in ((False, 1000-51-51-(1000-51)*.03, 949),
                                (True, 1000-76.5-76.5-(1000-76.5)*.03*1.5, 923.5)):
            with self.subTest(z=z):
                self.setUp();self.native_target()
                for name in ("klbq_kanami/rules", "klbq_kanami/compat", "klbq_kanami/damage",
                             "klbq_kanami/domain", "klbq_kanami/visual", "klbq_kanami/cleanse",
                             "klbq_kanami/chef", "klbq_kanami/recruit", "klbq_kanami/hermit", "components/klbq_kanami"):
                    path = ROOT / "mods/klbq_kanami/scripts" / (name + ".lua")
                    self.lua.execute("package.preload[...] = function() " + path.read_text(encoding="utf-8-sig") + " end", name)
                self.lua.execute("""
                  player.DoPeriodicTask=function() return {Cancel=function() end} end
                  for _,key in ipairs({'string','z','x','protect','wet','waterwalk','ztime','xtime','zcd','xcd','revive','passivecd','shotcd','ammo'}) do
                    player['_klbq_'..key]={v=false,set=function(s,v) s.v=v end,value=function(s) return s.v end}
                  end
                  k=require('components/klbq_kanami')(player);player.components.klbq_kanami=k
                  target.components.health.absorb=0
                  second=entity('hound');second.x=-2
                  second.components.health={};for key,v in pairs(target.components.health) do second.components.health[key]=v end
                  setmetatable(second.components.health,{__index=Health});second.components.health.inst=second
                  second.components.combat={};for key,v in pairs(target.components.combat) do second.components.combat[key]=v end
                  setmetatable(second.components.combat,{__index=Combat});second.components.combat.inst=second
                  second.replica=target.replica;targets={target,second}
                """)
                self.lua.globals().enabled = z
                self.lua.execute("k.state.zenabled=enabled;sweep();tick(.6)")
                self.assertAlmostEqual(self.lua.eval("target.components.health.currenthealth"), first)
                self.assertAlmostEqual(self.lua.eval("second.components.health.currenthealth"), second)
                self.assertAlmostEqual(self.lua.eval("k:Remaining('passive')"), 1.5)
                self.assertEqual(self.lua.eval("hand.components.finiteuses:GetUses()"), 599)


if __name__ == "__main__":
    unittest.main(verbosity=2)
