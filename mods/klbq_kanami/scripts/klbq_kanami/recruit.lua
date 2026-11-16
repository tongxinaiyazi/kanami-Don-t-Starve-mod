-- Free recruitment uses the game's leader/follower lifecycle, without feeding
-- fake items through trader callbacks (which may eat, poop, gift or equip).
-- Verified against the installed scripts.zip, not every entity with follower.
local M = {}
local RECRUITS = {
    pigman=true, bunnyman=true, rocky=true, catcoon=true, gnarwail=true,
    merm=true, mermguard=true,
}
local SPIDERS={spider=true,spider_warrior=true,spider_hider=true,spider_spitter=true,
    spider_dropper=true,spider_moon=true,spider_healer=true,spider_water=true}

local function Alive(inst)
    return inst ~= nil and inst:IsValid()
        and not inst:HasTag("INLIMBO") and not inst:HasTag("playerghost")
        and inst.components.health ~= nil and not inst.components.health:IsDead()
end

function M.Apply(owner, target)
    -- Earlier versions granted these unlimited loyalty. End that legacy hire
    -- when our domain next reaches it, without touching another player's pet
    -- or a character explicitly granted Webber's spider identity by another mod.
    if TheWorld and TheWorld.ismastersim and Alive(owner) and target and SPIDERS[target.prefab] then
        local follower=target.components.follower
        local leader=owner.components.leader
        if follower and follower.leader==owner and leader and not owner:HasTag("spiderwhisperer") then
            leader:RemoveFollower(target)
        end
        return false
    end
    if TheWorld == nil or not TheWorld.ismastersim or not Alive(owner) or not Alive(target)
        or owner == target or owner.components.leader == nil
        or owner.components.minigame_participator ~= nil
        or not RECRUITS[target.prefab] or target:HasTag("player")
        or target:HasTag("epic") or target:HasTag("NPC_contestant")
        or target:HasTag("creaturecorpse") then
        return false
    end

    local follower = target.components.follower
    local trader = target.components.trader
    if follower == nil or trader == nil or not trader.enabled then return false end
    -- GetLeader may resolve a carried leash item to its player owner. Never
    -- redirect the actual item/NPC leader, or reclaim an offline player's hire.
    local leader = follower:GetLeader()
    if (leader ~= nil and leader ~= owner)
        or (follower.leader ~= nil and follower.leader ~= owner)
        or follower.cached_player_leader_userid ~= nil then
        return false
    end

    if target.prefab == "pigman" and (target:HasTag("guard") or target:HasTag("werepig")) then
        return false
    end
    if target.prefab == "merm" or target.prefab == "mermguard" then
        local king = TheWorld.components and TheWorld.components.mermkingmanager
        if target.king ~= nil or (king ~= nil and king:IsCandidate(target)) then return false end
    end

    local maxfollowtime = follower.maxfollowtime
    -- Timed recruits retain their prefab's configured cap and native expiration.
    if not follower.neverexpire
        and (type(maxfollowtime) ~= "number" or maxfollowtime <= 0) then
        return false
    end

    if leader == nil then
        -- Only this recruitment bypasses ordinary merm trader identity
        -- checks. No Webber/Wurt tags, recipes, alignment or skills are granted.
        owner.components.leader:AddFollower(target)
        if follower:GetLeader() ~= owner then return false end
        owner:PushEvent("makefriend")
        local sleeper = target.components.sleeper
        if sleeper ~= nil and sleeper:IsAsleep() then sleeper:WakeUp() end
    end

    -- Each .25-second domain scan may call Apply. Top up only after half of the
    -- native duration has elapsed; never repeat onaccept/startfollowing effects.
    if not follower.neverexpire and type(maxfollowtime) == "number" and maxfollowtime > 0
        and (follower.targettime == nil or follower.targettime - GetTime() <= maxfollowtime * .5) then
        follower:AddLoyaltyTime(maxfollowtime)
    end
    return true
end

return M
