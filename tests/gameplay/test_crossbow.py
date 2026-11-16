"""Crossbow runs native F/RPC, ATTACK handlers, Weapon and projectile damage.

Only engine entities/graphics are fixtures. Native methods come from the current
installed scripts.zip and execute in Lua 5.1, including Combat's cooldown/range.
"""
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/python-deps"))
from lupa.lua51 import LuaRuntime
from test_review_regressions import GAME, vanilla
import test_component

MODULE = ROOT / "mods/klbq_kanami/scripts/klbq_kanami/crossbow.lua"
PREFAB = ROOT / "mods/klbq_kanami/scripts/prefabs/klbq_crossbow.lua"


class Crossbow(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.is_file(), "连弩原版攻击桥接尚未实现")
        self.assertTrue(PREFAB.is_file(), "连弩及原版弹射物尚未实现")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME) as archive:
            self.lua.execute(archive.read("scripts/class.lua").decode("utf-8-sig"))
            for module in ("util/sourcemodifierlist", "components/spdamageutil",
                           "components/weapon", "components/planardamage", "components/planardefense"):
                self.lua.execute("package.preload[...] = function() " + archive.read(
                    "scripts/"+module+".lua").decode("utf-8-sig") + " end", module)
            self.native_sg = {}
            for name in ("wilson", "wilson_client"):
                source = archive.read("scripts/stategraphs/SG"+name+".lua").decode("utf-8-sig")
                start = source.index("ActionHandler(ACTIONS.ATTACK,")
                end = source.index("ActionHandler(ACTIONS.TOSS,", start)
                self.native_sg[name] = source[start:end].strip().rstrip(",")
        self.lua.execute("Combat={};Replica={};PlayerController={};Projectile={};ACTIONS={ATTACK={}}")
        for name in ("InCooldown", "CanAttack", "StartAttack", "RestartCooldown", "GetAttackRange",
                     "CalcAttackRangeSq", "DoAttack", "CalcDamage", "ClearAttackTemps"):
            self.lua.execute(vanilla("components/combat.lua", "function Combat:"+name+"("))
        for name in ("MinAttackPeriod", "StartAttack", "CancelAttack", "InCooldown", "GetAttackRangeWithWeapon",
                     "IsValidTarget", "CanTarget"):
            self.lua.execute(vanilla("components/combat_replica.lua", "function Combat:"+name+"(").replace(
                "function Combat:", "function Replica:", 1))
        helper = vanilla("components/playercontroller.lua", "local function ValidateAttackTarget(")
        self.lua.execute(helper + "\n" + vanilla("components/playercontroller.lua", "function PlayerController:GetAttackTarget("))
        for name in ("DoAttackButton", "OnRemoteAttackButton", "RemoteAttackButton", "IsControlPressed",
                     "IsAnyOfControlsPressed", "RemoteStopControl", "OnRemoteStopControl", "OnRemoteStopAllControls"):
            chunk = vanilla("components/playercontroller.lua", "function PlayerController:"+name+"(")
            self.lua.execute("local BUTTON_REPEAT_COOLDOWN=.5\n" + chunk)
        self.lua.execute(vanilla("components/projectile.lua", "function Projectile:Hit("))
        self.lua.execute(vanilla("components/projectile.lua", "function Projectile:Throw("))
        self.lua.execute(vanilla("components/projectile.lua", "function Projectile:SetLaunchOffset("))
        with zipfile.ZipFile(GAME) as archive:
            native_projectile=self.lua.execute(archive.read('scripts/components/projectile.lua').decode('utf-8-sig'))
            self.lua.globals().Projectile.OnUpdate=native_projectile.OnUpdate
        self.lua.execute(vanilla("components/projectile.lua", "function Projectile:Stop("))
        attack = vanilla("actions.lua", "ACTIONS.ATTACK.fn = function(")
        self.lua.execute(attack)
        self.lua.execute("""
          now=0;GetTime=function() return now end;FRAMES=1/30;TUNING={WILSON_ATTACK_PERIOD=.4,DEFAULT_ATTACK_RANGE=2}
          EQUIPSLOTS={HANDS='hands'};CONTROL_ATTACK=1;CONTROL_PRIMARY=2;CONTROL_CONTROLLER_ATTACK=3
          CONTROL_MOVE_UP=4;CONTROL_MOVE_DOWN=5;CONTROL_MOVE_LEFT=6;CONTROL_MOVE_RIGHT=7;CONTROL_FORCE_ATTACK=8
          DEGREES=math.pi/180;COLLISION={LIMITS=1};LAYER_WORLD=1;ANIM_ORIENTATION={OnGround=1}
          FunctionOrValue=function(v,...) if type(v)=='function' then return v(...) end return v end
          CanApplyPlayerDamageMod=function() return 1 end
          SpDamageUtil=require('components/spdamageutil')
          Vector3=function(x,y,z) return {x=x,y=y,z=z} end
          distsq=function(a,b) return (a.x-b.x)^2+(a.y-b.y)^2+(a.z-b.z)^2 end
          IsEntityDead=function(e) return e.components.health and e.components.health:IsDead() end
          CanEntitySeeTarget=function(a,b) return b.visible~=false end
          TargetIsHostile=function(a,b) return not b.friendly end
          TheNet={GetPVPEnabled=function() return false end}
          TheWorld={ismastersim=true};TheSim={FindEntities_Registered=function() return {target} end}
          pressed={};TheInput={IsControlPressed=function(s,c) return pressed[c]==true end}
          State=function(s) return s end;EventHandler=function(n,f) return {name=n,fn=f} end
          ActionHandler=function(a,d) return {action=a,deststate=d} end
          hooks={};classhooks={};sgposts={};states={wilson={},wilson_client={}}
          env={GLOBAL=_G,AddComponentPostInit=function(n,f) hooks[n]=f end,
            AddClassPostConstruct=function(n,f) classhooks[n]=f end,
            AddStategraphPostInit=function(n,f) sgposts[n]=f end,
            AddStategraphState=function(n,s) states[n][s.name]=s end}
          function net(v) return {value=function() return v end} end
          function entity(prefab)
            local e={prefab=prefab,components={},replica={},tags={},events={},tasks={},x=0,z=0}
            e.IsValid=function(s) return not s.removed end;e.IsInLimbo=function(s) return s.tags.INLIMBO end
            e.HasTag=function(s,t) return s.tags[t]==true end
            e.HasAnyTag=function(s,...) for _,t in ipairs({...}) do if s:HasTag(t) then return true end end return false end
            e.HasOneOfTags=function(s,ts) return s:HasAnyTag(unpack(ts)) end
            e.AddTag=function(s,t) s.tags[t]=true end;e.RemoveTag=function(s,t) s.tags[t]=nil end
            e.GetPosition=function(s) return Vector3(s.x,s.y or 0,s.z) end
            e.GetPhysicsRadius=function() return 0 end
            e.GetDistanceSqToInst=function(s,t) return (s.x-t.x)^2+(s.z-t.z)^2 end
            e.GetDistanceSqToPoint=function(s,x,y,z) return (s.x-x)^2+(s.z-z)^2 end
            e.Transform={GetWorldPosition=function() return e.x,e.y or 0,e.z end,
              SetPosition=function(s,x,y,z) e.x=x;e.y=y;e.z=z end,SetScale=function() end,GetRotation=function() return e.rotation or 0 end}
            e.entity={SetCanSleep=function()end,IsValid=function() return not e.removed end,IsVisible=function() return e.visible~=false end,
              AddTransform=function() end,AddAnimState=function() end,AddNetwork=function() end,SetPristine=function() end}
            e.Physics={Stop=function() end,CollidesWith=function() end,ClearCollidesWith=function() end,SetMotorVel=function() end}
            e.AnimState=setmetatable({}, {__index=function() return function() end end})
            e.StartUpdatingComponent=function() end;e.StopUpdatingComponent=function() end
            e.SoundEmitter={PlaySound=function() end};e.FacePoint=function() end;e.ForceFacePoint=function() end
            e.Remove=function(s) s.removed=true end;e.IsAsleep=function() return false end
            e.ListenForEvent=function(s,n,f) s.events[n]=f end
            e.PushEvent=function(s,n,d) if s.events[n] then s.events[n](s,d) end end
            e.DoTaskInTime=function(s,t,f) s.tasks[#s.tasks+1]=f;return {Cancel=function() end} end
            e.AddComponent=function(s,n)
              if n=='weapon' or n=='planardamage' then s.components[n]=require('components/'..n)(s)
              elseif n=='projectile' then
                local p={inst=s,SetSpeed=function(s,n) s.speed=n end,SetHoming=function(s,n) s.homing=n end,
                  SetHitDist=function(s,n) s.hitdist=n end,SetOnHitFn=function(s,f) s.onhit=f end,
                  SetOnMissFn=function(s,f) s.onmiss=f end,SetOnThrownFn=function(s,f) s.onthrown=f end,
                  RotateToTarget=function() end}
                setmetatable(p,{__index=Projectile});s.components[n]=p
              elseif n=='equippable' then s.components[n]={SetOnEquip=function(s,f) s.onequip=f end,SetOnUnequip=function(s,f) s.onunequip=f end}
              else s.components[n]={} end
            end
            return e
          end
          Asset=function() return {} end;Prefab=function(n,f,a,d) return {name=n,fn=f,assets=a,deps=d} end
          MakeInventoryPhysics=function() end;MakeProjectilePhysics=function() end
          MakeInventoryFloatable=function() end;MakeHauntableLaunch=function() end
          CreateEntity=function() return entity('created') end
          player=entity('wilson');player.isplayer=true;player:AddTag('player')
          player.components.health={IsDead=function() return player.dead==true end}
          target=entity('hound');target.x=10
          target.components.health={IsDead=function() return target.dead==true end}
          target.components.combat={ShouldRecoil=function() return false end,CanBeAttacked=function() return true end,
            GetAttacked_Internal=function(s,a,d,w,stim,sp) hits=(hits or 0)+1;hitattacker=a;hitdamage=d;hitplanar=sp and sp.planar end}
          target.replica.combat={CanBeAttacked=function() return true end,GetTarget=function() return player end}
          combat=setmetatable({inst=player,min_attack_period=.4,attackrange=2,hitrange=2,canattack=true,
            externaldamagemultipliers={Get=function() return 1 end},GetWeapon=function() return hand end,
            SetTarget=function(s,t) s.target=t end,IsValidTarget=function(s,t) return player.replica.combat:IsValidTarget(t) end,
            CanTarget=function(s,t) return player.replica.combat:CanTarget(t) end,
            CanHitTarget=function(s,t,w) return t and not t.dead and not t.removed end}, {__index=Combat})
          player.components.combat=combat
          replica=setmetatable({inst=player,_attackrange=net(2),_ispanic=net(false),
            GetWeapon=function() return hand end,CanExtinguishTarget=function() return false end,
            CanLightTarget=function() return false end,IsAlly=function(s,t) return t.friendly end,
            IsRecentTarget=function() return false end}, {__index=Replica})
          player.replica.combat=replica
          player.replica.inventory={GetEquippedItem=function() return hand end,IsHeavyLifting=function() return false end,IsFloaterHeld=function() return false end}
          player.components.inventory={GetEquippedItem=function() return hand end}
          loco={Stop=function(s) s.wantstomoveforward=false end,WantsToMoveForward=function(s) return s.wantstomoveforward==true end}
          player.components.locomotor=loco
          pc=setmetatable({inst=player,ismastersim=true,handler={},locomotor=loco,remote_controls={},remote_vector={y=0},
            IsEnabled=function() return true end,IsOverrideAttack=function() return false end,
            CanLocomote=function() return true end,GetCombatTarget=function() return combat.target end}, {__index=PlayerController})
          player.components.playercontroller=pc
          player.GetBufferedAction=function(s) return s.bufferedaction end
          player.ClearBufferedAction=function(s) s.bufferedaction=nil end
          player.PerformBufferedAction=function(s) local a=s.bufferedaction;s.bufferedaction=nil;if a then return a.action.fn(a) end end
          player.PerformPreviewBufferedAction=function(s) previews=(previews or 0)+1;if s.bufferedaction.preview_cb then s.bufferedaction.preview_cb() end end
          function BufferedAction(d,t,a) return {doer=d,target=t,action=a} end
          function makesg(name)
            local sg={mem={},statemem={},sg={states=states[name]},currentstate={name='idle'},tags={}}
            sg.HasStateTag=function(s,t) return s.tags[t]==true end
            sg.RemoveStateTag=function(s,t) s.tags[t]=nil end;sg.AddStateTag=function(s,t) s.tags[t]=true end
            sg.SetTimeout=function(s,t) s.timeout=t end
            sg.GoToState=function(s,n)
              if s.currentstate.onexit then s.currentstate.onexit(player) end
              s.laststate=s.currentstate;s.currentstate=states[name][n] or {name=n};s.statemem={};s.tags={}
              for _,t in ipairs(s.currentstate.tags or {}) do s.tags[t]=true end
              if s.currentstate.onenter then s.currentstate.onenter(player) end
            end
            return sg
          end
          function begin(a,preview)
            player.bufferedaction=a
            local n=nativehandler.deststate(player,a)
            if n then player.sg:GoToState(n) end
          end
          loco.PushAction=function(s,a) begin(a) end;loco.PreviewAction=function(s,a) begin(a,true) end
          function update(t) now=t;if player.sg.currentstate.onupdate then player.sg.currentstate.onupdate(player,FRAMES) end end
          RPC={AttackButton=1,StopControl=2};rpc_calls={}
          SendRPCToServer=function(id,...) rpc_calls[#rpc_calls+1]={id,...} end
          StopTrackingDelayOwner=function() end
        """)
        self.lua.execute("package.preload['klbq_kanami/crossbow']=function() " + MODULE.read_text(encoding="utf-8-sig")+" end")
        self.lua.execute("require('klbq_kanami/crossbow').Install(env)")
        result = self.lua.execute(PREFAB.read_text(encoding="utf-8-sig"))
        self.lua.globals().gunprefab, self.lua.globals().boltprefab = result
        self.lua.execute("""
          hand=gunprefab.fn();hand.prefab='klbq_crossbow';hand.components.inventoryitem.owner=player
          hand.replica.inventoryitem={IsWeapon=function() return true end,SetAttackRange=function() end,
            AttackRange=function() return hand.components.weapon.attackrange end}
          shots={};bolts={}
          SpawnPrefab=function(n)
            if n=='klbq_crossbow_bolt' then
              local bolt=boltprefab.fn();bolt.prefab=n;shots[#shots+1]=now;bolts[#bolts+1]=bolt;return bolt
            end
          end
          hooks.combat(combat)
          classhooks['components/combat_replica'](replica)
          if hooks.playercontroller then hooks.playercontroller(pc) end
        """)
        self.use_sg("wilson")
        self.lua.execute("if hand.components.equippable.onequip then hand.components.equippable.onequip(hand,player) end")

    def use_sg(self, name):
        self.lua.execute("nativehandler="+self.native_sg[name])
        self.lua.execute("nativegraph={actionhandlers={[ACTIONS.ATTACK]=nativehandler}};sgposts[...](nativegraph)",name)
        self.lua.execute("player.sg=makesg(...)",name)

    def fire(self):
        self.lua.execute("pressed[CONTROL_ATTACK]=true;pc:DoAttackButton()")

    def test_bolt_launches_forward_at_hand_height_in_four_directions(self):
        import math
        for angle in (0,90,180,270):
            with self.subTest(angle=angle):
                self.setUp()
                self.lua.execute('player.rotation=...;player.x=20;player.y=.4;player.z=30;target.x=25;target.z=30',angle)
                self.fire()
                self.assertAlmostEqual(self.lua.eval('bolts[1].y'),1.9)
                self.assertAlmostEqual(self.lua.eval('bolts[1].x'),20+1.2*math.cos(math.radians(angle)))
                self.assertAlmostEqual(self.lua.eval('bolts[1].z'),30-1.2*math.sin(math.radians(angle)))

    def test_elevated_bolt_preserves_ground_hit_radius_for_small_and_large_targets(self):
        for radius in (0,.5,3):
            with self.subTest(radius=radius):
                self.setUp()
                self.lua.execute('target_radius=...;target.GetPhysicsRadius=function()return target_radius end',radius)
                self.fire()
                hitdist=self.lua.eval('bolts[1].components.projectile.hitdist')
                self.assertAlmostEqual((hitdist+radius)**2-1.5**2,(radius+.5)**2)
                self.lua.execute('bolts[1].x=target.x-target_radius-.49;bolts[1].components.projectile:OnUpdate(FRAMES)')
                self.assertTrue(self.lua.eval('bolts[1].removed'))

    def enable_native_locomotor(self):
        self.lua.execute("LocoMotor={};EntityScript={}")
        with zipfile.ZipFile(GAME) as archive:
            source=archive.read("scripts/components/locomotor.lua").decode("utf-8-sig")
            self.lua.execute("package.loaded['class']=Class")
            self.lua.execute(archive.read("scripts/vector3.lua").decode("utf-8-sig"))
            dynamic=archive.read("scripts/util.lua").decode("utf-8-sig")
            self.lua.execute(dynamic[dynamic.index('DynamicPosition = Class('):dynamic.index('-- Class LinkedList')])
            self.lua.execute("TheWorld.Map={GetPlatformAtPoint=function() return nil end}")
            self.lua.execute(archive.read("scripts/bufferedaction.lua").decode("utf-8-sig"))
        self.lua.execute(source[source.index("Dest = Class"):source.index("local function onrunspeed")])
        for method in ("PushAction", "GoToEntity", "GoToPoint", "OnUpdate", "Stop", "Clear", "SetBufferedAction", "PreviewAction"):
            self.lua.execute("local ARRIVE_STEP=.15;local INVALID_PLATFORM_ID='INVALID PLATFORM'\n"+
                             vanilla("components/locomotor.lua","function LocoMotor:"+method+"("))
        self.lua.execute(vanilla("components/combat.lua","function Combat:LocomotorCanAttack("))
        self.lua.execute(vanilla("components/combat_replica.lua","function Combat:LocomotorCanAttack(").replace(
            "function Combat:","function Replica:",1))
        self.lua.execute(vanilla("entityscript.lua","function EntityScript:PushBufferedAction("))
        self.lua.execute(vanilla("entityscript.lua","function EntityScript:PreviewBufferedAction("))
        self.lua.execute("""
          distsq=function(a,b,c,d)
            if type(a)=='table' then return (a.x-b.x)^2+(a.y-b.y)^2+(a.z-b.z)^2 end
            return (a-c)^2+(b-d)^2
          end
          pc.OnRemoteBufferedAction=function() end;pc.OnLocomotorBufferedAction=function() end
          player.PushBufferedAction=EntityScript.PushBufferedAction
          player.sg.StartAction=function(s,a)
            moving_at_start=loco.wantstomoveforward
            local name=nativehandler.deststate(player,a)
            if name then s:GoToState(name);return true end
            return false
          end
          player.sg.PreviewAction=player.sg.StartAction
          player.PreviewBufferedAction=EntityScript.PreviewBufferedAction
          setmetatable(loco,{__index=LocoMotor})
          loco.inst=player;loco.ismastersim=true
          loco.PushAction=LocoMotor.PushAction;loco.PreviewAction=LocoMotor.PreviewAction
          loco.Stop=LocoMotor.Stop
          loco.ResetPath=function() end;loco.StopMoveTimerInternal=function() end
          loco.StopMoving=function() end;loco.StopUpdatingInternal=function() end
          loco.StartUpdatingInternal=function() end;loco.CancelPredictMoveTimer=function() end
          loco.FindPath=function() end;loco.FaceMovePoint=function() end;loco.GetRunSpeed=function() return 6 end
        """)

    def enable_native_remote_prediction(self):
        """Use DST's real last-walk -> buffered-action protocol, not y=0."""
        for method in ("GetRemotePredictPosition", "OnRemoteBufferedAction"):
            self.lua.execute(vanilla("components/playercontroller.lua",
                                     "function PlayerController:"+method+"("))
        self.lua.execute("""
          pc.handler=nil;pc.remote_predicting=true;pc.remote_authority=true
          pc.IsBusy=function() return false end
          pc.OnRemoteBufferedAction=PlayerController.OnRemoteBufferedAction
          pc.remote_vector=Vector3(player.x,3,player.z)
          pc.directwalking=true;pc.predictwalking=true
        """)

    def dispatch_native_remote_attack_buffer(self):
        """Run OnUpdate's real predicted-position/buffer dispatch phase."""
        with zipfile.ZipFile(GAME) as archive:
            source = archive.read('scripts/components/playercontroller.lua').decode('utf-8-sig')
        start = source.index('--Attack controls are buffered and handled here in the update')
        end = source.index('\n    if isenabled then', start)
        self.lua.execute('local self=pc\n' + source[start:end])

    def test_native_remote_predicted_walk_to_f_is_an_action_handoff_not_movement(self):
        self.enable_native_locomotor()
        self.enable_native_remote_prediction()
        self.lua.execute('pc:OnRemoteAttackButton(target,false,false,false,false)')
        self.assertTrue(self.lua.eval('pc.attack_buffer.forced and pc.attack_buffer._predictpos'))
        self.assertIsNone(self.lua.eval('pc.attack_buffer:GetActionPoint()'))
        self.dispatch_native_remote_attack_buffer()
        self.assertEqual(self.lua.eval("pc.remote_vector.y"),5)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"klbq_crossbow_attack")
        self.assertEqual(self.lua.eval("#shots"),1)
        self.lua.execute("update(.125)")
        self.assertEqual(self.lua.eval("#shots"),2)
        # A later movement packet still cancels continuous fire.
        self.lua.execute("pc.remote_vector.y=3;update(.25)")
        self.assertEqual(self.lua.eval("#shots"),2)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def enable_native_client_last_walk_cache(self):
        self.lua.execute(vanilla("components/playercontroller.lua",
                                 "function PlayerController:RemotePredictWalking("))
        self.lua.execute("""
          RPC.PredictWalking='PredictWalking'
          pc.GetPlatformRelativePosition=function(s,x,z) return nil,x,z end
          pc:RemotePredictWalking(player.x,player.z,false,nil,false,true)
        """)

    def test_client_native_stopped_walk_cache_does_not_block_preview_or_target_rpc(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4),canattack=net(true)}")
        self.use_sg("wilson_client");self.enable_native_locomotor()
        self.lua.execute("loco.ismastersim=false")
        self.enable_native_client_last_walk_cache()
        self.assertEqual(self.lua.eval("pc.remote_vector.y"),4)
        self.fire()
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"klbq_crossbow_attack")
        self.assertEqual(self.lua.eval("previews or 0"),1)
        self.assertTrue(self.lua.eval("rpc_calls[#rpc_calls][2]==target"))
        self.assertEqual(self.lua.eval("#shots"),0)

    def test_native_locomotor_f_starts_from_gotoentity_and_onupdate_before_native_stop(self):
        for distance in (10,16):
            with self.subTest(distance=distance):
                self.setUp();self.enable_native_locomotor()
                self.lua.execute("target.x=...",distance)
                self.fire()
                if distance>12:
                    self.assertEqual(self.lua.eval("#shots"),0)
                    self.lua.execute("player.x=4;LocoMotor.OnUpdate(loco,1/30,true)")
                self.assertTrue(self.lua.eval("moving_at_start"))
                self.assertEqual(self.lua.eval("#shots"),1)
                self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"klbq_crossbow_attack")

    def test_continuous_fire_uses_a_stable_aim_pose_instead_of_melee_swing(self):
        self.lua.execute("player.AnimState.PlayAnimation=function(s,n) last_animation=n end")
        self.fire()
        self.assertEqual(self.lua.eval('last_animation'),'kanami_crossbow_shoot')

    def test_client_native_locomotor_preview_arrives_and_sends_original_target_rpc(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4),canattack=net(true)}")
        self.use_sg("wilson_client");self.enable_native_locomotor()
        self.lua.execute("loco.ismastersim=false")
        self.fire()
        self.assertTrue(self.lua.eval("moving_at_start"))
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"klbq_crossbow_attack")
        self.assertEqual(self.lua.eval("previews"),1)
        self.assertEqual(self.lua.eval("#rpc_calls"),2)
        self.assertTrue(self.lua.eval("rpc_calls[2][2]==target"))
        self.assertEqual(self.lua.eval("#shots"),0)

    def test_server_revive_protection_refuses_first_shot_and_stops_hold_even_with_weapon_equipped(self):
        for protection in (
                "player._klbq_protect=net(true)",
                "player.components.klbq_kanami={state={string=false},CanUseHands=function() return false end}"):
            for started in (False,True):
                with self.subTest(protection=protection,started=started):
                    self.setUp()
                    if started:self.fire()
                    self.lua.execute(protection)
                    if started:self.lua.execute("update(.125)")
                    else:self.fire()
                    self.assertTrue(self.lua.eval("hand.prefab=='klbq_crossbow'"))
                    self.assertEqual(self.lua.eval("#shots"),1 if started else 0)
                    self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def test_client_revive_protection_refuses_preview_and_stops_predicted_hold(self):
        for started in (False,True):
            with self.subTest(started=started):
                self.setUp()
                self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4),canattack=net(true)}")
                self.use_sg("wilson_client")
                if started:self.fire()
                self.lua.execute("player._klbq_protect=net(true)")
                if started:self.lua.execute("update(.125)")
                else:self.fire()
                self.assertEqual(self.lua.eval("previews or 0"),1 if started else 0)
                self.assertEqual(self.lua.eval("#shots"),0)
                self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def test_native_f_routes_original_attack_only_for_crossbow_and_fires_first_shot(self):
        self.fire()
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"), "klbq_crossbow_attack")
        self.assertEqual(self.lua.eval("#shots"), 1)
        self.lua.execute("hand=entity('spear');player.sg:GoToState('idle')")
        self.assertEqual(self.lua.eval("nativehandler.deststate(player,BufferedAction(player,target,ACTIONS.ATTACK))"), "attack")

    def test_held_native_f_averages_eight_per_second_in_three_and_four_frame_steps(self):
        self.fire()
        for frame in range(1, 121):
            self.lua.execute("update(...)", frame/30)
        times = list(self.lua.eval("shots").values())
        self.assertEqual(len(times), 33)
        intervals = [round((b-a)*30) for a,b in zip(times,times[1:])]
        self.assertEqual(set(intervals), {3,4})
        self.assertAlmostEqual((times[-1]-times[0])/(len(times)-1), .125)
        self.assertEqual(self.lua.eval("combat.min_attack_period"), .4)

    def test_exact_boundary_no_shot_before_one_eighth_second_and_no_swap_reset(self):
        self.fire()
        self.lua.execute("update(.124999)")
        self.assertEqual(self.lua.eval("#shots"), 1)
        self.lua.execute("update(.125)")
        self.assertEqual(self.lua.eval("#shots"), 2)
        self.lua.execute("player.sg:GoToState('idle');now=.14;pc:DoAttackButton()")
        self.assertEqual(self.lua.eval("#shots"), 2)

    def test_remote_native_hold_rpc_runs_faster_than_native_half_second_repeat(self):
        self.lua.execute("pc.handler=nil;pc:OnRemoteAttackButton(target,false,false,false,false);loco:PushAction(pc.attack_buffer,true);pc.attack_buffer=nil")
        for frame in range(1,16): self.lua.execute("update(...)",frame/30)
        self.assertEqual(self.lua.eval("#shots"),5)
        self.lua.execute("pc:OnRemoteStopControl(CONTROL_ATTACK);update(.6)")
        self.assertEqual(self.lua.eval("#shots"),5)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def test_remote_released_first_rpc_still_fires_once_then_stops(self):
        self.lua.execute("pc.handler=nil;pc:OnRemoteAttackButton(target,false,false,false,true);loco:PushAction(pc.attack_buffer,true);pc.attack_buffer=nil")
        self.assertEqual(self.lua.eval("#shots"),1)
        self.lua.execute("update(.1)")
        self.assertEqual(self.lua.eval("#shots"),1)
        self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def test_client_f_keeps_preview_and_remote_rpc_without_client_doattack(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)}")
        self.use_sg("wilson_client")
        self.fire()
        self.assertEqual(self.lua.eval("previews"),1)
        self.assertEqual(self.lua.eval("#shots"),0)
        self.assertEqual(self.lua.eval("#rpc_calls"),2)
        self.assertEqual(self.lua.eval("rpc_calls[2][2]==target"),True)
        self.lua.execute("pc:RemoteStopControl(CONTROL_ATTACK);pressed[CONTROL_ATTACK]=false;update(.1)")
        self.assertEqual(self.lua.eval("#shots"),0)

    def test_client_hold_keeps_eight_per_second_prediction_without_additional_damage_or_rpc(self):
        self.lua.execute("TheWorld.ismastersim=false;pc.ismastersim=false;player.components.combat=nil;replica.classified={minattackperiod=net(.4)}")
        self.use_sg("wilson_client");self.fire()
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"),.125)
        for frame in range(1,121): self.lua.execute("update(...)",frame/30)
        self.assertEqual(self.lua.eval("#shots"),0)
        self.assertEqual(self.lua.eval("#rpc_calls"),2)
        self.assertAlmostEqual(self.lua.eval("player._klbq_crossbow_nextshot"),4.125)
        self.lua.execute("hand=entity('spear')")
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"),.4)

    def test_release_death_string_move_unequip_and_target_loss_stop(self):
        for stop in ("pressed[CONTROL_ATTACK]=false", "player.dead=true",
                     "player._klbq_string=net(true)", "loco.wantstomoveforward=true",
                     "hand=entity('spear')", "target.dead=true", "target.x=12.001",
                     "target.visible=false", "target:AddTag('notarget')"):
            with self.subTest(stop=stop):
                self.setUp();self.fire();self.lua.execute(stop+";update(.1)")
                self.assertEqual(self.lua.eval("#shots"),1)
                self.assertEqual(self.lua.eval("player.sg.currentstate.name"),"idle")

    def test_native_target_checks_refuse_friendly_ghost_and_invisible_targets(self):
        for invalid in ("target.friendly=true;target.replica.combat.GetTarget=function() return nil end",
                        "target:AddTag('playerghost')", "target.visible=false", "target:AddTag('notarget')"):
            with self.subTest(invalid=invalid):
                self.setUp();self.lua.execute(invalid);self.fire()
                self.assertEqual(self.lua.eval("#shots"),0)

    def test_weapon_is_zero_physical_five_planar_ranged_and_has_no_durability(self):
        self.lua.execute("physical,special=hand.components.weapon:GetDamage(player,target)")
        self.assertEqual(self.lua.eval("physical"),0)
        self.assertEqual(self.lua.eval("special.planar"),5)
        self.assertTrue(self.lua.eval("hand.components.weapon:CanRangedAttack()"))
        self.assertIsNone(self.lua.eval("hand.components.finiteuses"))
        self.assertEqual(self.lua.eval("combat:GetAttackRange()"),12)
        self.assertIsNone(self.lua.eval("hand.components.container"))

    def test_unload_and_other_mod_period_are_preserved(self):
        self.fire()
        self.lua.execute("combat.min_attack_period=.7;hand=entity('spear');now=.1")
        self.assertTrue(self.lua.eval("combat:InCooldown()"))
        self.assertEqual(self.lua.eval("replica:MinAttackPeriod()"),.7)
        self.assertEqual(self.lua.eval("combat.min_attack_period"),.7)

    def test_native_projectile_hit_reenters_native_combat_planar_damage(self):
        self.fire()
        self.lua.execute("bolts[1].components.projectile:Hit(target)")
        self.assertEqual(self.lua.eval("hitdamage"),0)
        self.assertEqual(self.lua.eval("hitplanar"),5)

    def test_in_flight_bolt_keeps_original_attacker_after_crossbow_is_dropped_or_traded(self):
        for ownership in ("hand.components.inventoryitem.owner=nil", "hand.components.inventoryitem.owner=trader"):
            with self.subTest(ownership=ownership):
                self.setUp();self.fire()
                self.lua.execute("""
                  trader=entity('willow')
                  trader.components.combat={DoAttack=function() traded_attack=true end}
                """)
                self.lua.execute(ownership)
                self.assertTrue(self.lua.eval("bolts[1].components.projectile.owner==player"))
                self.lua.execute("bolts[1].components.projectile:Hit(target)")
                self.assertEqual(self.lua.eval("hitplanar"),5)
                self.assertTrue(self.lua.eval("hitattacker==player"))
                self.assertFalse(bool(self.lua.eval("traded_attack")))

    def test_projectile_respects_real_native_planar_defense_health_cap_and_invulnerability(self):
        self.lua.execute("Health={}")
        for name in ("GetPercent", "GetMaxWithPenalty", "IsInvincible", "IsDead", "CanFadeOut", "DoDelta", "SetVal"):
            self.lua.execute(vanilla("components/health.lua", "function Health:"+name+"("))
        self.lua.execute(vanilla("components/combat.lua", "function Combat:GetAttacked_Internal("))
        self.lua.execute("""
          math.clamp=function(v,a,b) return math.max(a,math.min(b,v)) end
          CanEntityBecomeCorpse=function() return false end
          IsRangedWeapon=function(w) return w and w:HasTag('rangedweapon') end
          target.components.combat=setmetatable({inst=target,externaldamagetakenmultipliers={Get=function() return 1 end},
            CanBeAttacked=function() return true end,ShouldRecoil=function(s,a,w,d) return false,d end,
            GetImpactSound=function() return nil end},{__index=Combat})
          target.components.health=setmetatable({inst=target,currenthealth=1000,maxhealth=1000,penalty=0,
            nonlethal_pct=0,absorb=0,playerabsorb=0,nofadeout=true,
            externalabsorbmodifiers={Get=function() return 0 end},externalreductionmodifiers={Get=function() return 0 end}}, {__index=Health})
          target.components.planardefense=require('components/planardefense')(target)
          target.components.planardefense:SetBaseDefense(3)
        """)
        self.fire()
        self.lua.execute("bolts[1].components.projectile:Hit(target)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"),1000-(5-3))
        self.lua.execute("target.components.health.maxdamagetakenperhit=-1;update(.125);bolts[2].components.projectile:Hit(target)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"),1000-(5-3)-1)
        self.lua.execute("target.components.health.invincible=true;update(.25);bolts[3].components.projectile:Hit(target)")
        self.assertEqual(self.lua.eval("target.components.health.currenthealth"),1000-(5-3)-1)


class CrossbowPassive(unittest.TestCase):
    setUp = test_component.Lifecycle.setUp

    def test_s1_uses_crossbow_planar_power_while_other_weapons_remain_unchanged(self):
        self.lua.execute("""
          gun={prefab='klbq_crossbow',components={weapon={GetDamage=function() return 0,{planar=5} end}}}
          other={prefab='other',components={weapon={GetDamage=function() return 34,{planar=10} end}}}
          target={}
          snapshot=require('klbq_kanami/damage').Snapshot(inst,target,gun)
          bolt={prefab='klbq_crossbow_bolt',components=gun.components}
          boltsnapshot=require('klbq_kanami/damage').Snapshot(inst,target,bolt)
          unrelated=require('klbq_kanami/damage').Snapshot(inst,target,other)
        """)
        self.assertEqual(self.lua.eval("snapshot.power"),5)
        self.assertEqual(self.lua.eval("boltsnapshot.power"),5)
        self.assertEqual(self.lua.eval("unrelated.power"),34)

    def test_native_calc_context_does_not_replace_crossbow_snapshot_with_physical_zero(self):
        self.lua.execute("""
          component.attackcontext={power=5,zmult=1.5,weapon={prefab='klbq_crossbow'}}
          for i=1,20 do local n=debug.getupvalue(inst.components.combat.CalcDamage,i)
            if n=='oldcalc' then debug.setupvalue(inst.components.combat.CalcDamage,i,function() return 0,{planar=5} end);break end end
          physical,special=inst.components.combat:CalcDamage({},component.attackcontext.weapon)
        """)
        self.assertEqual(self.lua.eval("component.attackcontext.power"),5)
        self.assertEqual(self.lua.eval("physical"),0)
        self.assertEqual(self.lua.eval("special.planar"),7.5)

    def test_delayed_crossbow_snapshot_keeps_five_power_and_launch_z_after_weapon_swap(self):
        self.lua.execute("""
          gun={prefab='klbq_crossbow',components={weapon={GetDamage=function() return 0,{planar=5} end}}}
          component.state.zenabled=true
          snapshot=require('klbq_kanami/damage').Snapshot(inst,{},gun)
          for i=1,20 do local n=debug.getupvalue(inst.components.combat.CalcDamage,i)
            if n=='oldcalc' then debug.setupvalue(inst.components.combat.CalcDamage,i,function() return 0,{planar=5} end);break end end
          projectile={_klbq_attack_snapshot=snapshot}
          component.state.zenabled=false
          inst.components.combat.GetWeapon=function() return {prefab='spear'} end
          inst.components.combat:DoAttack({},gun,projectile)
        """)
        self.assertEqual(self.lua.eval("captured.power"),5)
        self.assertEqual(self.lua.eval("captured.zmult"),1.5)
        self.assertTrue(self.lua.eval("captured.weapon==gun"))
        self.assertEqual(self.lua.eval("duringattackdamage"),0)

    def test_crossbow_passive_uses_five_or_z_seven_point_five_and_shared_cooldown(self):
        from test_passive import Passive
        for enabled,expected in ((False,950-5-950*.03),(True,950-7.5-950*.03*1.5)):
            with self.subTest(z=enabled):
                self.setUp();Passive.target(self)
                self.lua.globals().enabled=enabled
                self.lua.execute("""
                  gun={prefab='klbq_crossbow',components={weapon={GetDamage=function() return 0,{planar=5} end}}}
                  component.state.zenabled=enabled
                  local d=require('klbq_kanami/damage')
                  component:Echo(target,d.Snapshot(inst,target,gun))
                """)
                self.assertEqual(self.lua.eval("planaramount"),7.5 if enabled else 5)
                self.assertAlmostEqual(self.lua.eval("hp.currenthealth"),expected)
                self.assertFalse(self.lua.eval("component:Echo(target,{power=34,zmult=1,weapon={prefab='spear'}})"))
                self.assertEqual(self.lua.eval("planarhits"),1)


if __name__ == "__main__": unittest.main(verbosity=2)
