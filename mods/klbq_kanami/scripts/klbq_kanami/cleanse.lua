-- Server-side, explicit negative-state adapters. "debuffable" also stores food,
-- skill and potion BUFFS: neither its name nor a *_debuff suffix is a polarity API.
-- Verified against local DST scripts and Void Realm 2.3.2. Unknown effects and
-- mixed tradeoff buffs are intentionally preserved until a safe adapter exists.
local M = {}
local NEGATIVE_PREFABS = {
    -- Native DST: toxins, miasma, vines, damaging purgative, mind-control source,
    -- and the slingshot vulnerability mark. Detachment runs native cleanup.
    firenettle_toxin = true,
    mitegland_debuff = true,
    miasmadebuff = true,
    wormwood_vined_debuff = true,
    ipecacsyrup_buff = true,
    mindcontroller = true,
    slingshotammo_purebrilliance_debuff = true,
    -- Void Realm: poison/DOT, healing lock and broken-armor state.
    tr_shihua_judu = true,
    tr_eguai_poison_buff = true,
    tr_void_rending_wound_debuff = true,
    tr_yexingyaoshi_buff = true,
    tr_zuzhouyan_buff = true,
    tr_kuijiaposun_buff = true,
}

local function CleanDebuffs(target)
    local debuffable = target.components.debuffable
    if not debuffable then return end
    local remove = {}
    for key, entry in pairs(debuffable.debuffs) do
        local inst = entry.inst
        if inst and NEGATIVE_PREFABS[inst.prefab] then
            remove[#remove + 1] = key
        elseif inst and inst.prefab == "sporebomb" then
            -- Native sporebomb's detached callback EXPLODES. Replace only this
            -- bomb's callback, retaining EntityScript:Remove/OnRemoveEntity FX
            -- cleanup, before detaching through the debuffable public API.
            local debuff = inst.components.debuff
            if debuff and debuff.SetDetachedFn then
                debuff:SetDetachedFn(inst.Remove)
                remove[#remove + 1] = key
            end
        end
    end
    -- Detach callbacks may mutate the collection; never delete while traversing.
    for _, key in ipairs(remove) do debuffable:RemoveDebuff(key) end
end

function M.Apply(target)
    local c = target.components
    CleanDebuffs(target)

    local freezable = c.freezable
    if freezable and (freezable:IsFrozen() or freezable.coldness > 0) then
        -- Unfreeze publishes the SG/brain recovery event, including THAWING;
        -- Reset alone silently changes fields and can leave the actor stuck.
        freezable:Unfreeze()
        freezable:Reset()
    end

    local grogginess = c.grogginess
    if grogginess and (grogginess.isgroggy or grogginess:IsKnockedOut()
        or grogginess.grog_amount > 0 or grogginess.speedmod ~= nil) then
        if grogginess:IsKnockedOut() then grogginess:ComeTo() end
        grogginess:ResetGrogginess()
        -- Finish native wear-off through its own lifecycle, clearing its tag,
        -- speed modifier and task without clearing other sources' modifiers.
        -- OnUpdate also handles an existing positive sleep-immunity source.
        grogginess:OnUpdate(grogginess.wearoffduration)
    end

    local sleeper = c.sleeper
    if sleeper then
        -- Native players' voluntary tent/bedroll sleep is managed by their SG,
        -- not sleeper. Wake friendly sleeper creatures even at zero sleepiness:
        -- AddSleepiness can already have scheduled an untracked GoToSleep task.
        if sleeper:IsAsleep() then sleeper:WakeUp()
        elseif sleeper.sleepiness > 0 then sleeper:AddSleepiness(-sleeper.sleepiness) end
    end

    local burnable = c.burnable
    if burnable and (burnable:IsBurning() or burnable:IsSmoldering()) then
        burnable:Extinguish(true)
    end
    local pinnable = c.pinnable
    if pinnable and pinnable:IsStuck() then pinnable:Unstick() end

    local inkable = c.inkable
    if inkable and inkable.inked then
        -- Native expiry publishes deinked to both the SG and client overlay;
        -- removing only squid_ink_player_fx does not clear the ink state.
        inkable:OnUpdate(inkable.inktime)
    end
    local moisture = c.moisture
    if moisture and moisture:GetMoisture() > 0 then
        moisture:DoDelta(-moisture:GetMoisture())
    end
    local temperature = c.temperature
    if temperature and (temperature:IsFreezing() or temperature:IsOverheating()) then
        -- Change only harmful extremes. Do not use SetTemp (persistent lock),
        -- alter insulation or overwrite a comfortable positive temperature buff.
        temperature:SetTemperature(math.min(20, temperature.overheattemp))
    end
end

return M
