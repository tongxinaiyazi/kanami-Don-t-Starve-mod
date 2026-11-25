local Rules=require("klbq_kanami/rules")
local Damage=require("klbq_kanami/damage")
local M={}

local function ShooterAlive(inst)
    local health=inst.components.health
    return health and not health:IsDead() and not inst:HasTag("playerghost")
end
local function TargetVisible(inst,target)
    return target~=inst and Damage.Valid(target)
        and not (target:HasTag("playerghost") or target:HasTag("INLIMBO") or target:HasTag("NOCLICK"))
        and target.entity:IsVisible()
end
local function EquippedRifle(inst)
    local inventory=inst.components.inventory
    local rifle=inventory and inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
    return rifle and rifle.prefab=="klbq_finale" and rifle or nil
end

function M.Shoot(inst,target)
    if not TheWorld.ismastersim then return false end
    local health=inst.components.health
    local kanami=inst.components.klbq_kanami
    local now=GetTime()
    if not ShooterAlive(inst)
        or (kanami and (not kanami:Alive() or not kanami:CanUseHands() or kanami.state.string
            or not Rules.Ready(kanami.state,"shot",now)))
        or now<(inst._klbq_nextshot or 0) or not TargetVisible(inst,target) then return false end
    local rifle=EquippedRifle(inst)
    if not rifle then return false end
    local container=rifle.components.container
    local ammo=container and container:GetItemInSlot(1)
    if not ammo or not ammo:HasTag("klbq_ammo") then return false end
    local name=ammo.prefab
    if name~="klbq_ammo_heart" and name~="klbq_ammo_fate" and name~="klbq_ammo_doom" then return false end
    if name=="klbq_ammo_doom" then
        -- Execute only the selected visible phase, retaining the world's PvP rule.
        if target:HasTag("player") and not TheNet:GetPVPEnabled() then return false end
    elseif not inst.components.combat:CanTarget(target) then return false end
    local snapshot=Damage.Snapshot(inst,target,rifle)
    -- A player owns the deadline: swapping rifles cannot reset the 1.5s interval.
    inst._klbq_nextshot=now+Rules.SHOT_COOLDOWN
    if kanami then Rules.Start(kanami.state,"shot",now,Rules.SHOT_COOLDOWN) end
    if ammo.components.stackable:StackSize()>1 then ammo.components.stackable:Get(1):Remove()
    else container:RemoveItemBySlot(1):Remove() end
    local dealt=false
    local targethealth=target.components.health
    local before=targethealth.currenthealth
    local receipt
    if name=="klbq_ammo_heart" then
        receipt={}
        dealt=Damage.BulletNormal(inst,target,50*snapshot.zmult,rifle,receipt)
    elseif name=="klbq_ammo_fate" then
        receipt={}
        dealt=Damage.BulletTrueDamage(inst,target,Rules.Fate(targethealth.maxhealth,math.random()<.1,snapshot.zmult>1),rifle,receipt)
    else dealt=Damage.Execute(inst,target) end
    if dealt and kanami then kanami:Echo(target,snapshot) end
    local actual=receipt and Damage.ActualDamage(receipt) or math.max(0,before-targethealth.currenthealth)
    if not kanami then
        if name=="klbq_ammo_doom" then
            -- Native death events/stategraph own drops, ghosts and resurrection.
            -- Never Remove the shooter or drop their inventory manually.
            health:SetVal(0,"klbq_doom_backlash",rifle)
        elseif actual>0 then
            -- Environmental physical damage avoids outgoing character bonuses.
            -- An equipped-item attacker would bypass native armor (isequipped),
            -- so keep the rifle as weapon and let native combat apply defenses.
            inst.components.combat:GetAttacked(nil,actual,rifle,"klbq_backlash")
        end
    end
    if name~="klbq_ammo_doom" and inst._klbq_hitseq then
        inst._klbq_hittarget:set(target);inst._klbq_hitdamage:set(actual)
        inst._klbq_hitseq:set((inst._klbq_hitseq:value()+1)%256)
    end
    inst:ForceFacePoint(target.Transform:GetWorldPosition())
    inst:PushEvent("klbq_shot",{target=target,damage=actual})
    if kanami then kanami:Sync() end
    return true
end

local HEALTH_TRIGGER_PHASES={beequeen=true,dragonfly=true,daywalker=true,daywalker2=true,
    toadstool=true,toadstool_dark=true,stalker=true}
local STATE_PHASES={
    dragonfly={transform_fire=true,transform_normal=true},
    klaus={transition_enrage=true},
}

function M.ClearLock(inst)
    local lock=inst._klbq_rifle_lock
    if not lock then return end
    inst._klbq_rifle_lock=nil
    if lock.task then lock.task:Cancel() end
    for _,watch in ipairs(lock.watches) do
        inst:RemoveEventCallback(watch[1],watch[2],watch[3])
    end
end

local function StartLock(inst,target,gun)
    local lock={target=target,gun=gun,watches={},level=target.level}
    inst._klbq_rifle_lock=lock
    local function Watch(event,fn,source)
        lock.watches[#lock.watches+1]={event,fn,source}
        inst:ListenForEvent(event,fn,source)
    end
    local function Finish()
        if inst._klbq_rifle_lock==lock then M.ClearLock(inst) end
    end
    Watch("death",Finish)
    Watch("onremove",Finish)
    Watch("unequip",function(_,data) if data and data.item==gun then Finish() end end)
    Watch("death",Finish,target)
    Watch("onremove",Finish,target)
    Watch("phasetransition",Finish,target)
    local states=STATE_PHASES[target.prefab]
    if states then
        Watch("newstate",function(_,data)
            if data and states[data.statename] then Finish() end
        end,target)
    end
    local trigger=target.components.healthtrigger
    if trigger and HEALTH_TRIGGER_PHASES[target.prefab] then
        Watch("healthdelta",function(_,data)
            if not data or not data.newpercent or not data.oldpercent or data.newpercent>=data.oldpercent then return end
            for threshold in pairs(trigger.triggers) do
                if data.oldpercent>threshold and data.newpercent<=threshold then Finish();return end
            end
        end,target)
    end
    lock.task=inst:DoPeriodicTask(.1,function()
        if inst._klbq_rifle_lock~=lock then return end
        if not ShooterAlive(inst) or not TargetVisible(inst,target) or EquippedRifle(inst)~=gun
            or target.level~=lock.level then
            Finish()
        elseif not (inst.sg and inst.sg:HasStateTag("busy"))
            and not (inst.components.rider and inst.components.rider:IsRiding()) then
            -- Retain the exact damage/cooldown/loaded ammo checks of manual fire.
            -- No state change here: firing must not interrupt the player's work
            -- or repeatedly pull them out of movement.
            M.Shoot(inst,target)
        end
    end)
end

function M.Click(inst,target,locking)
    if not TheWorld.ismastersim or not ShooterAlive(inst) then return false end
    local gun=EquippedRifle(inst)
    if not gun or not TargetVisible(inst,target) then return false end
    local lock=inst._klbq_rifle_lock
    if lock and (lock.target~=target or lock.gun~=gun) then
        M.ClearLock(inst)
        lock=nil
    end
    if locking then
        if target:HasTag("player") and not TheNet:GetPVPEnabled() then return false end
        local ammo=gun.components.container and gun.components.container:GetItemInSlot(1)
        if not inst.components.combat:CanTarget(target) and not (ammo and ammo.prefab=="klbq_ammo_doom") then
            return false
        end
        if not lock then StartLock(inst,target,gun) end
        M.Shoot(inst,target)
        return true -- acquiring a target also works while reloading/on cooldown
    end
    return M.Shoot(inst,target)
end

return M
