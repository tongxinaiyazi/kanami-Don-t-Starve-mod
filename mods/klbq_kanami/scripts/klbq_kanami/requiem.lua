-- Native ATTACK keeps F/left-click targeting and native Weapon/Combat damage.
-- Only Requiem receives these states and attack periods.
local M={}
local ATTACK="klbq_requiem_attack"
local SWEEP="klbq_requiem_sweep"
local PERIOD=.8
local WINDUP=.6
local SWEEPPERIOD=2
local RADIUS=4.5
local EPSILON=1e-7
local EXCLUDE={"INLIMBO","NOCLICK","FX","DECOR","player","playerghost","notarget","noattack",
    "invisible","flight","structure","wall","player_aligned","domesticated","companion"}

local function Weapon(inst)
    local combat=inst.replica.combat
    return combat and combat:GetWeapon() or nil
end
local function IsRequiem(weapon)
    return weapon~=nil and weapon.prefab=="klbq_requiem" and weapon:IsValid()
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
    local pc=inst.components.playercontroller
    local loco=inst.components.locomotor
    -- y=5 is DST's buffered-action handoff, not a new movement command.
    -- Its old direct/predict flags settle on the next controller update.
    -- A client's remote_vector caches its last sent packet, including stops.
    local handoff=pc and pc.ismastersim and pc.remote_vector and pc.remote_vector.y==5
    return (loco and loco:WantsToMoveForward()) or (pc and ((not handoff and (pc.directwalking or pc.predictwalking
        or (pc.ismastersim and pc.remote_vector and pc.remote_vector.y~=0)))
        or pc:IsAnyOfControlsPressed(CONTROL_MOVE_UP,CONTROL_MOVE_DOWN,CONTROL_MOVE_LEFT,CONTROL_MOVE_RIGHT)))
end
local function Ready(inst,weapon)
    return Alive(inst) and IsRequiem(weapon) and Weapon(inst)==weapon
end
local function Exit(inst)
    inst.sg:GoToState("idle")
end
local function ClearOwnAction(inst)
    if inst:GetBufferedAction()==inst.sg.statemem.action then inst:ClearBufferedAction() end
end
local function CanSweep(inst)
    local rider=inst.replica.rider
    return Ready(inst,Weapon(inst)) and not (rider and rider:IsRiding())
        and GetTime()+EPSILON>=(inst._klbq_requiem_nextsweep or 0)
end
function M.Cast(inst)
    if not TheWorld.ismastersim or inst == nil or not inst.sg
        or inst.sg:HasStateTag("busy") or not CanSweep(inst) then return false end
    local locomotor = inst.components.locomotor
    if locomotor == nil then return false end
    locomotor:PushAction(BufferedAction(inst,nil,ACTIONS.KLBQ_REQUIEM_SWEEP,Weapon(inst)),true)
    return true
end
local function ValidTarget(inst,target,combat)
    if target==inst or not target:IsValid() or target:IsInLimbo() or target:HasAnyTag(unpack(EXCLUDE))
        -- Native treeguards carry "tree" as well as "plantcreature".
        or (target:HasTag("tree") and not target:HasTag("plantcreature"))
        or not target.components.health or IsEntityDead(target) or not target.components.combat
        -- A self-centered swing does not aim at a lit point. Native sight also
        -- tests ambient light, incorrectly turning night sweeps into FX only.
        or not target.entity:IsVisible() or combat:IsAlly(target) or not combat:CanTarget(target)
        or inst:GetDistanceSqToInst(target)>RADIUS*RADIUS then return false end
    local follower=target.components.follower
    local leader=follower and follower.leader
    return not (leader and (leader==inst or leader.isplayer or leader:HasTag("player") or combat:IsAlly(leader)))
end
local function DoSweep(inst,weapon)
    if not TheWorld.ismastersim or not Ready(inst,weapon) then return false end
    local combat=inst.components.combat
    local uses=weapon.components.finiteuses
    if not combat or not uses or uses:GetUses()<=0 then return false end
    local x,y,z=inst.Transform:GetWorldPosition()
    local targets=TheSim:FindEntities(x,y,z,RADIUS,{"_combat"},EXCLUDE)
    -- Keep native onattack/weapononattack events and per-target Combat damage,
    -- but consume one use for the complete swing, including an empty swing.
    local ignored=uses:IgnoresCombatDurabilityLoss()
    uses:SetIgnoreCombatDurabilityLoss(true)
    local ok,err=pcall(function()
        for _,target in ipairs(targets) do
            if not Ready(inst,weapon) then break end
            if ValidTarget(inst,target,combat) then
                combat:DoAttack(target,weapon,nil,nil,nil,RADIUS)
            end
        end
    end)
    uses:SetIgnoreCombatDurabilityLoss(ignored)
    if weapon:IsValid() then uses:Use(1) end
    if not ok then error(err) end
    local fx=SpawnPrefab("klbq_requiem_sweep")
    if fx then fx.Transform:SetPosition(x,y,z) end
    return true
end

local function MakeAttack(client)
    return State{
        name=ATTACK,tags={"attack","notalking","abouttoattack"},
        onenter=function(inst)
            local action=inst:GetBufferedAction()
            local target=action and action.target
            local weapon=Weapon(inst)
            local combat=client and inst.replica.combat or inst.components.combat
            if not Ready(inst,weapon) or not target or not target:IsValid() or not combat
                or combat:InCooldown() or not inst.replica.combat:CanTarget(target) then
                inst:ClearBufferedAction();Exit(inst);return
            end
            inst.sg.statemem.weapon=weapon;inst.sg.statemem.attacktarget=target;inst.sg.statemem.action=action
            inst.components.locomotor:Stop()
            if Moving(inst) then inst:ClearBufferedAction();Exit(inst);return end
            if not client then
                if not combat:CanAttack(target) then inst:ClearBufferedAction();Exit(inst);return end
                combat:SetTarget(target)
            end
            combat:StartAttack()
            inst._klbq_requiem_nextattack=GetTime()+PERIOD
            inst:FacePoint(target:GetPosition())
            inst.AnimState:PlayAnimation("atk_pre");inst.AnimState:PushAnimation("atk",false)
            inst.sg:SetTimeout(PERIOD)
            if client then inst:PerformPreviewBufferedAction() end
        end,
        timeline={TimeEvent(.3,function(inst)
            local mem=inst.sg.statemem
            if not Ready(inst,mem.weapon) or Moving(inst) then inst:ClearBufferedAction();Exit(inst);return end
            inst.SoundEmitter:PlaySound("dontstarve/wilson/attack_weapon")
            if not client then inst:PerformBufferedAction() end
            inst.sg:RemoveStateTag("abouttoattack")
        end)},
        onupdate=function(inst)
            if not Ready(inst,inst.sg.statemem.weapon) or Moving(inst) then Exit(inst) end
        end,
        ontimeout=Exit,
        events={EventHandler("equip",Exit),EventHandler("unequip",Exit)},
        onexit=function(inst)
            local combat=inst.components.combat
            if combat and combat.target==inst.sg.statemem.attacktarget then combat:SetTarget(nil) end
            ClearOwnAction(inst)
        end,
    }
end
local function MakeSweep(client)
    return State{
        name=SWEEP,tags={"attack","doing","busy","notalking","nomorph"},
        server_states=client and {SWEEP} or nil,
        onenter=function(inst)
            local action=inst:GetBufferedAction()
            local weapon=Weapon(inst)
            if not CanSweep(inst) or not action or action.invobject~=weapon then
                inst:ClearBufferedAction();Exit(inst);return
            end
            inst.sg.statemem.weapon=weapon;inst.sg.statemem.action=action
            inst._klbq_requiem_nextsweep=GetTime()+SWEEPPERIOD
            inst.components.locomotor:Stop()
            inst.AnimState:PlayAnimation("atk_leap_pre")
            inst.AnimState:PushAnimation("atk_leap_lag",true)
            inst.sg:SetTimeout(SWEEPPERIOD)
            if client then inst:PerformPreviewBufferedAction() end
        end,
        timeline={TimeEvent(WINDUP,function(inst)
            if not Ready(inst,inst.sg.statemem.weapon) or Moving(inst) then Exit(inst);return end
            inst.AnimState:PlayAnimation("atk_leap")
            inst.AnimState:PushAnimation("idle_loop",true)
            inst.SoundEmitter:PlaySound("dontstarve/wilson/attack_whoosh")
            if not client then
                inst.sg.statemem.released=true
                inst:PerformBufferedAction()
            end
        end)},
        onupdate=function(inst)
            if not Ready(inst,inst.sg.statemem.weapon) or Moving(inst) then Exit(inst) end
        end,
        ontimeout=Exit,
        events={EventHandler("equip",Exit),EventHandler("unequip",Exit)},
        onexit=ClearOwnAction,
    }
end

function M.Install(env)
    local sweep=Action({distance=math.huge,do_not_locomote=true,mount_valid=false})
    sweep.id="KLBQ_REQUIEM_SWEEP";sweep.str="镇魂歌 · 圆斩"
    sweep.fn=function(act)
        local inst=act.doer
        local mem=inst.sg and inst.sg.statemem
        if not TheWorld.ismastersim or not inst.sg or inst.sg.currentstate.name~=SWEEP
            or not mem.released or mem.completed or mem.weapon~=act.invobject then return false end
        mem.completed=true
        return DoSweep(inst,act.invobject)
    end
    env.AddAction(sweep)
    env.AddComponentPostInit("combat",function(combat)
        local old=combat.InCooldown
        combat.InCooldown=function(self,...)
            if IsRequiem(Weapon(self.inst)) then
                local normal=self.inst._klbq_requiem_nextattack
                    or (self.laststartattacktime and self.laststartattacktime+PERIOD) or 0
                return GetTime()+EPSILON<math.max(normal,self.inst._klbq_requiem_nextsweep or 0)
            end
            return old(self,...)
        end
    end)
    env.AddClassPostConstruct("components/combat_replica",function(combat)
        local oldperiod=combat.MinAttackPeriod
        combat.MinAttackPeriod=function(self,...)
            if IsRequiem(self:GetWeapon()) then return PERIOD end
            return oldperiod(self,...)
        end
        local oldcooldown=combat.InCooldown
        combat.InCooldown=function(self,...)
            if IsRequiem(self:GetWeapon()) and not self.inst.components.combat then
                local normal=self.inst._klbq_requiem_nextattack
                    or (self._laststartattacktime and self._laststartattacktime+PERIOD) or 0
                return GetTime()+EPSILON<math.max(normal,self.inst._klbq_requiem_nextsweep or 0)
            end
            return oldcooldown(self,...)
        end
    end)
    for _,name in ipairs({"wilson","wilson_client"}) do
        env.AddStategraphState(name,MakeAttack(name=="wilson_client"))
        env.AddStategraphState(name,MakeSweep(name=="wilson_client"))
        env.AddStategraphActionHandler(name,ActionHandler(sweep,SWEEP))
        env.AddStategraphPostInit(name,function(sg)
            local handler=sg.actionhandlers[ACTIONS.ATTACK]
            if not handler then return end
            local old=handler.deststate
            handler.deststate=function(inst,action,...)
                if IsRequiem(Weapon(inst)) then
                    if not Alive(inst) then return nil end
                    -- Native ATTACK suppresses repeat clicks through this
                    -- exact statemem field. Preserve the in-flight first hit
                    -- before delegating through another weapon's SG wrapper.
                    if inst.sg.currentstate.name==ATTACK and action.target==inst.sg.statemem.attacktarget then return nil end
                end
                local dest=old
                if type(old)=="function" then dest=old(inst,action,...) end
                if IsRequiem(Weapon(inst)) then
                    if dest=="attack" then return ATTACK end
                end
                return dest
            end
        end)
    end
end
return M
