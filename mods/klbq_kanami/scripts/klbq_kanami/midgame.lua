local Bag = require("klbq_kanami/bag")
local M = {}
local MEMORY = "klbq_resource_memory_sequence"
local VISION = "klbq_singularity"
local use

local function InstallArchiveAccess(inst)
    if not TheWorld.ismastersim then return end
    local activatable = inst.components.activatable
    local activate = activatable ~= nil and activatable.OnActivate or nil
    if activate == nil then return end
    activatable.OnActivate = function(dispenser, doer, ...)
        local memory = doer ~= nil and doer.prefab == "klbq_kanami" and doer._klbq_memory_sequence or nil
        local health = memory ~= nil and doer.components.health or nil
        if memory == nil or not memory:value() or doer:HasTag("playerghost")
            or (health ~= nil and health:IsDead()) or dispenser.vaultpowered then
            return activate(dispenser, doer, ...)
        end
        -- The native callback checks vaultpowered before archive power.
        -- Only bypass that check for this activation, not for the whole Archive.
        local previous = dispenser.vaultpowered
        dispenser.vaultpowered = true
        local ok, result, reason = pcall(activate, dispenser, doer, ...)
        dispenser.vaultpowered = previous
        if not ok then error(result, 0) end
        return result, reason
    end
end

local function CanLearnMemory(doer, item)
    return doer ~= nil and doer.prefab == "klbq_kanami" and doer:HasTag("klbq_kanami")
        and not doer:HasTag("playerghost") and doer._klbq_memory_sequence ~= nil
        and not doer._klbq_memory_sequence:value() and item ~= nil and item.prefab == MEMORY
end

local function Remember(act)
    local doer, item = act.doer, act.invobject
    if not TheWorld.ismastersim or not CanLearnMemory(doer, item)
        or not doer:IsValid() or not item:IsValid() or doer.components.builder == nil then
        return false
    end
    local inventoryitem = item.components.inventoryitem
    if inventoryitem == nil or inventoryitem:GetGrandOwner() ~= doer then return false end
    local consumed = inventoryitem:RemoveFromOwner(false)
    if consumed == nil then return false end
    consumed:Remove()
    doer._klbq_memory_sequence:set(true)
    doer:PushEvent("unlockrecipe")
    return true
end

function M.CollectInventoryActions(item, doer, actions)
    if use ~= nil and CanLearnMemory(doer, item) and item.replica.inventoryitem ~= nil
        and item.replica.inventoryitem:IsGrandOwner(doer) then
        actions[#actions + 1] = use
    end
end

local portable_levels = setmetatable({}, {__mode = "k"})
local function EnablePortableScience(builder)
    if builder == nil then return end
    local knows = builder.KnowsRecipe
    builder.KnowsRecipe = function(self, recipe, ...)
        local memory = self.inst._klbq_memory_sequence
        if memory == nil or not memory:value() then return knows(self, recipe, ...) end
        if type(recipe) == "string" then recipe = GetValidRecipe(recipe) end
        if recipe ~= nil and not recipe.nounlock and not recipe.manufactured and recipe.station_tag == nil
            and not recipe.unlocks_from_skin and (recipe.level.SCIENCE or 0) > 0
            and recipe.level.SCIENCE <= TECH.SCIENCE_TWO.SCIENCE then
            -- Treat ordinary science recipes as known. Do not add to science_bonus:
            -- native prototyper evaluation sums that bonus with nearby station tech.
            local virtual_level = portable_levels[recipe.level]
            if virtual_level == nil then
                virtual_level = {}
                for key, level in pairs(recipe.level) do virtual_level[key] = level end
                virtual_level.SCIENCE = 0
                portable_levels[recipe.level] = virtual_level
            end
            local virtual_recipe = setmetatable({level = virtual_level}, {__index = recipe})
            return knows(self, virtual_recipe, ...)
        end
        return knows(self, recipe, ...)
    end
end

local function RefineMemory(inst)
    local memory = inst._klbq_memory_sequence
    if memory == nil then return end
    EnablePortableScience(inst.replica.builder)
    inst:ListenForEvent("klbq_memorysequencedirty", function() inst:PushEvent("unlockrecipe") end)
    if not TheWorld.ismastersim then return end
    EnablePortableScience(inst.components.builder)

    -- Native Builder owns learned recipes, including ones learned before the
    -- upgrade. Persist only the additional portable-science entitlement here.
    local onsave, onload = inst.OnSave, inst.OnLoad
    inst.OnSave = function(self, data, ...)
        local refs = onsave ~= nil and onsave(self, data, ...) or nil
        data.klbq_memory_sequence = memory:value() or nil
        return refs
    end
    inst.OnLoad = function(self, data, ...)
        local result = onload ~= nil and onload(self, data, ...) or nil
        if data ~= nil and data.klbq_memory_sequence == true then
            memory:set(true)
            self:PushEvent("unlockrecipe")
        end
        return result
    end
end

local function FindNightBag(inv)
    for _, slot in ipairs({EQUIPSLOTS.BACK or EQUIPSLOTS.BODY, EQUIPSLOTS.BODY}) do
        local item = inv:GetEquippedItem(slot)
        if item ~= nil and item.prefab == "klbq_singularity" and item._klbq_nightvision ~= nil
            and item._klbq_nightvision:value() then return item end
    end
end

local function InstallVision(inst)
    local vision = inst.components.playervision
    if vision == nil then return end
    local enabled = false
    local function Disable()
        if enabled then
            enabled = false
            vision:PopForcedNightVision(VISION)
        end
    end
    local ambient
    local function Refresh()
        if ThePlayer ~= inst then return end
        local inv = inst.replica.inventory
        local dark = TheWorld:HasTag("cave") or TheWorld.state.isnight
        if dark and not vision:HasGhostVision() and inv ~= nil and FindNightBag(inv) ~= nil
            and not inv:EquipHasTag("nightvision") then
            if not enabled then
                enabled = true
                if ambient == nil then
                    local bright = {colour = Point(.73, .73, .73), time = .25}
                    ambient = {CAVE_COLOUR = bright, FULL_MOON_COLOUR = bright, default = bright}
                end
                -- The last argument suppresses the mole-hat colour cube, so
                -- only ambient light changes and normal world grading remains.
                vision:PushForcedNightVision(VISION, -10, nil, false, ambient, true)
            end
        else
            Disable()
        end
    end
    local function QueueRefresh() inst:DoTaskInTime(0, Refresh) end
    for _, event in ipairs({"playeractivated", "equip", "unequip", "inventoryclosed", "ghostvision", Bag.LIGHT_DIRTY}) do
        inst:ListenForEvent(event, QueueRefresh)
    end
    inst:WatchWorldState("isnight", Refresh)
    inst:ListenForEvent("playerdeactivated", Disable)
    inst:ListenForEvent("onremove", Disable)
end

function M.Install(env)
    local G = env.GLOBAL
    local strings = G.STRINGS
    strings.NAMES.KLBQ_EMBER_CORE = "弦海信标·余烬核心"
    strings.CHARACTERS.GENERIC.DESCRIBE.KLBQ_EMBER_CORE = "龙蝇的余热仍在弦海信标中跳动。"
    strings.RECIPE_DESC.KLBQ_RESOURCE_MEMORY_SEQUENCE = "记下学过的配方，随身携带炼金引擎级科技。可使用未通电的知识饮水机。"

    use = G.Action({priority = 2, mount_valid = true})
    use.id, use.str, use.fn = "KLBQ_MEMORY_SEQUENCE", "铭记配方", Remember
    env.AddAction(use)
    for _, sg in ipairs({"wilson", "wilson_client"}) do
        env.AddStategraphActionHandler(sg, G.ActionHandler(use, "doshortaction"))
    end
    env.AddPrefabPostInit("klbq_kanami", RefineMemory)
    env.AddPrefabPostInit("archive_lockbox_dispencer", InstallArchiveAccess)
    env.AddPlayerPostInit(InstallVision)
    env.AddPrefabPostInit("dragonfly", function(inst)
        if TheWorld.ismastersim and inst.components.lootdropper ~= nil then
            inst.components.lootdropper:AddChanceLoot(Bag.CORE, 1)
        end
    end)
end

return M
