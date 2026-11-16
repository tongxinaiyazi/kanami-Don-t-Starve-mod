local Rules=require("klbq_kanami/rules")
local Damage=require("klbq_kanami/damage")
local M={}

function M.Shoot(inst,target)
    if not TheWorld.ismastersim then return false end
    local health=inst.components.health
    local kanami=inst.components.klbq_kanami
    local now=GetTime()
    if not health or health:IsDead() or inst:HasTag("playerghost")
        or (kanami and (not kanami:Alive() or not kanami:CanUseHands() or kanami.state.string
            or not Rules.Ready(kanami.state,"shot",now)))
        or now<(inst._klbq_nextshot or 0) or not Damage.Valid(target) then return false end
    if target==inst or target:HasTag("playerghost") or target:HasTag("INLIMBO")
        or target:HasTag("NOCLICK") or not target.entity:IsVisible() then return false end
    local rifle=inst.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
    if not rifle or rifle.prefab~="klbq_finale" then return false end
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

return M
