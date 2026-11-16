local M = { TAGS = { "hermitcrab" } }

-- Current vanilla hermitcrab TASKS.FIX_HOUSE_1/2/3. The third task is
-- createbundle's pearl prerequisite; completing friendship tasks does not
-- replace, upgrade, or remove the actual house.
local HOUSE_TASKS = { 1, 2, 3 }

local function CompleteMissing(friendlevels, task, owner)
    local data = friendlevels.friendlytasks[task]
    if data ~= nil and not data.complete then
        friendlevels:CompleteTask(task, owner)
    end
end

function M.Apply(owner, npc)
    if TheWorld == nil or not TheWorld.ismastersim
        or owner == nil or not owner:IsValid()
        or npc == nil or not npc:IsValid() or npc.prefab ~= "hermitcrab" then
        return false
    end

    local friendlevels = npc.components and npc.components.friendlevels
    if friendlevels == nil or npc.rewardcheck == nil then
        return false
    end

    -- Preserve vanilla task records, level-change events, reward queue, shop
    -- unlocks and save data. Never repeat a completed repeatable task: vanilla
    -- would award a fresh default gift on every quarter-second domain scan.
    for _, task in ipairs(HOUSE_TASKS) do
        CompleteMissing(friendlevels, task, owner)
    end
    if friendlevels:GetLevel() < friendlevels:GetMaxLevel() then
        local tasks = {}
        for task in pairs(friendlevels.friendlytasks) do
            tasks[#tasks + 1] = task
        end
        table.sort(tasks)
        for _, task in ipairs(tasks) do
            if friendlevels:GetLevel() >= friendlevels:GetMaxLevel() then
                break
            end
            CompleteMissing(friendlevels, task, owner)
        end
    end

    -- Vanilla's periodic reward check requires a player within 8 units. The
    -- performance reaches 32, so use the prefab's exposed rewardcheck here;
    -- it puts the original rewards into inventory/itemstotoss and persists
    -- pearlgiven. The vanilla brain and SG then talk and toss them normally.
    local sg = npc.sg
    if #friendlevels.queuedrewards > 0 and sg ~= nil
        and not sg:HasStateTag("ishome") and not sg:HasStateTag("busy")
        and not sg:HasStateTag("mandatory") and not sg:HasStateTag("teashop")
        and not sg:HasStateTag("soakin")
        and npc.components.npc_talker ~= nil then
        local speech = npc:rewardcheck()
        if speech ~= nil then
            if npc.giverewardstask ~= nil then
                npc.giverewardstask:Cancel()
                npc.giverewardstask = nil
            end
            npc.components.npc_talker:Chatter(speech)
        end
    end
    return true
end

return M
