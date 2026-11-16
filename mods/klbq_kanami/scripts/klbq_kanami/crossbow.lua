-- Native F/controller ATTACK remains responsible for targeting and the first
-- buffered action/RPC. Only this weapon replaces the slow melee stategraph.
local M={}
local STATE="klbq_crossbow_attack"
local PERIOD=1/8
local EPSILON=1e-7

local function Weapon(inst)
    local combat=inst.replica.combat
    return combat and combat:GetWeapon() or nil
end
local function IsCrossbow(weapon)
    return weapon~=nil and weapon.prefab=="klbq_crossbow"
end
local function Alive(inst)
    local k=inst.components.klbq_kanami
    return not inst:HasTag("playerghost") and not IsEntityDead(inst)
        and not (k and k.state.string)
        and not (k and not k:CanUseHands())
        and not (inst._klbq_string and inst._klbq_string:value())
        and not (inst._klbq_protect and inst._klbq_protect:value())
end
local function Moving(inst)
    local controller=inst.components.playercontroller
    local locomotor=inst.components.locomotor
    -- Native OnRemoteBufferedAction changes the last predicted walk to y=5.
    -- That flag suspends walking for the action; directwalking/predictwalking
    -- may still hold the previous tick's values until DoPredictWalking runs.
    -- On clients remote_vector is only the last SENT packet, even after stop.
    local handoff=controller and controller.ismastersim and controller.remote_vector
        and controller.remote_vector.y==5
    return (locomotor and locomotor:WantsToMoveForward())
        or (controller and ((not handoff and (controller.directwalking or controller.predictwalking
            or (controller.ismastersim and controller.remote_vector and controller.remote_vector.y~=0)))
            or controller:IsAnyOfControlsPressed(CONTROL_MOVE_UP,CONTROL_MOVE_DOWN,CONTROL_MOVE_LEFT,CONTROL_MOVE_RIGHT)))
end
local function Valid(inst,target,weapon)
    if not Alive(inst) or Weapon(inst)~=weapon or not IsCrossbow(weapon)
        or not target or not target:IsValid() or target:IsInLimbo()
        or not CanEntitySeeTarget(inst,target) then return false end
    local combat=inst.replica.combat
    local range=combat:GetAttackRangeWithWeapon()+target:GetPhysicsRadius(0)
    return combat:CanTarget(target) and inst:GetDistanceSqToInst(target)<=range*range
end
local function Held(inst)
    local controller=inst.components.playercontroller
    return controller and controller:IsEnabled()
        and controller:IsAnyOfControlsPressed(CONTROL_ATTACK,CONTROL_CONTROLLER_ATTACK,CONTROL_PRIMARY)
end
local function Animate(inst)
    local rider=inst.replica.rider
    inst.AnimState:PlayAnimation(rider and rider:IsRiding() and "player_atk" or "kanami_crossbow_shoot")
    -- Start at the release pose; no global animation-speed override to leak
    -- into walking, another weapon, transformations, or another mod's buff.
    inst.AnimState:SetFrame(0)
end
local function Exit(inst)
    inst.sg:GoToState("idle")
end
local function Advance(inst,initial)
    local now=GetTime()
    local previous=inst._klbq_crossbow_nextshot
    -- Carry the fractional tick remainder while held. At 30 Hz .125 seconds
    -- needs alternating three/four-frame gaps instead of rounding every gap up.
    -- A long stall never produces a catch-up burst in a single simulation tick.
    inst._klbq_crossbow_nextshot=(initial or previous==nil or now-previous>PERIOD)
        and now+PERIOD or previous+PERIOD
end

local function MakeState(client)
    return State{
        name=STATE,
        tags={"attack","notalking","abouttoattack"},
        onenter=function(inst)
            local action=inst:GetBufferedAction()
            local weapon=Weapon(inst)
            local target=action and action.target
            local combat=client and inst.replica.combat or inst.components.combat
            if not combat or not Valid(inst,target,weapon)
                or combat:InCooldown() then
                inst:ClearBufferedAction();Exit(inst);return
            end
            inst.sg.statemem.weapon=weapon
            inst.sg.statemem.attacktarget=target
            -- Native GoToEntity/OnUpdate dispatch the action before their own
            -- Stop, so WantsToMoveForward is still true even after arrival.
            -- Clear that approach motion before checking held movement input.
            inst.components.locomotor:Stop()
            if Moving(inst) then inst:ClearBufferedAction();Exit(inst);return end
            if not client then
                if not combat:CanAttack(target) then inst:ClearBufferedAction();Exit(inst);return end
                combat:SetTarget(target)
            end
            combat:StartAttack()
            Advance(inst,true)
            inst:FacePoint(target:GetPosition())
            Animate(inst)
            if client then
                -- The original DoAttackButton preview_cb sends the original
                -- AttackButton RPC, including force/released flags.
                inst:PerformPreviewBufferedAction()
                inst:ClearBufferedAction()
            else
                inst:PerformBufferedAction()
            end
            inst.sg:RemoveStateTag("abouttoattack")
        end,
        onupdate=function(inst)
            local mem=inst.sg.statemem
            if not Valid(inst,mem.attacktarget,mem.weapon) or Moving(inst) or not Held(inst) then Exit(inst);return end
            if GetTime()+EPSILON<(inst._klbq_crossbow_nextshot or 0) then return end
            local combat=client and inst.replica.combat or inst.components.combat
            if not client and not combat:CanAttack(mem.attacktarget) then Exit(inst);return end
            combat:StartAttack()
            Advance(inst,false)
            inst:FacePoint(mem.attacktarget:GetPosition())
            Animate(inst)
            if not client then
                -- Server only, after native CanTarget/CanAttack and range checks.
                -- Native Weapon/Projectile/Combat retain planar defense, PvP,
                -- damage caps, invulnerability, hit events and kill attribution.
                combat:DoAttack(mem.attacktarget,mem.weapon)
            end
        end,
        events={
            EventHandler("equip",Exit),EventHandler("unequip",Exit),
        },
        onexit=function(inst)
            local combat=inst.components.combat
            if combat and combat.target==inst.sg.statemem.attacktarget then combat:SetTarget(nil) end
            local action=inst:GetBufferedAction()
            if action and action.action==ACTIONS.ATTACK and action.target==inst.sg.statemem.attacktarget then
                inst:ClearBufferedAction()
            end
        end,
    }
end

function M.Install(env)
    env.AddComponentPostInit("combat",function(combat)
        local old=combat.InCooldown
        combat.InCooldown=function(self,...)
            if IsCrossbow(Weapon(self.inst)) then
                local deadline=self.inst._klbq_crossbow_nextshot
                    or (self.laststartattacktime and self.laststartattacktime+PERIOD)
                return deadline~=nil and GetTime()+EPSILON<deadline
            end
            return old(self,...)
        end
    end)
    env.AddClassPostConstruct("components/combat_replica",function(combat)
        local oldperiod=combat.MinAttackPeriod
        combat.MinAttackPeriod=function(self,...)
            if IsCrossbow(self:GetWeapon()) then return PERIOD end
            return oldperiod(self,...)
        end
        local oldcooldown=combat.InCooldown
        combat.InCooldown=function(self,...)
            if IsCrossbow(self:GetWeapon()) and self.inst.components.combat==nil then
                local deadline=self.inst._klbq_crossbow_nextshot
                    or (self._laststartattacktime and self._laststartattacktime+PERIOD)
                return deadline~=nil and GetTime()+EPSILON<deadline
            end
            return oldcooldown(self,...)
        end
    end)
    for _,name in ipairs({"wilson","wilson_client"}) do
        env.AddStategraphState(name,MakeState(name=="wilson_client"))
        env.AddStategraphPostInit(name,function(sg)
            local handler=sg.actionhandlers[ACTIONS.ATTACK]
            if not handler then return end
            local old=handler.deststate
            handler.deststate=function(inst,action,...)
                local destination=old
                if type(old)=="function" then destination=old(inst,action,...) end
                if IsCrossbow(Weapon(inst)) then
                    if not Alive(inst) or inst.sg.currentstate.name==STATE then return nil end
                    if destination=="attack" then return STATE end
                end
                return destination
            end
        end)
    end
end
return M
