local M = {}

local function IsProtected(inst)
    if inst == nil or inst.prefab ~= "klbq_kanami" or inst.components.inventory == nil
        or inst:HasTag("playerghost") then return false end
    local health = inst.components.health
    return health == nil or not health:IsDead()
end

local function HasProtectedOwner(inst)
    local item = inst.components.inventoryitem
    return IsProtected(item ~= nil and item:GetGrandOwner() or inst)
end

local function RefreshItems(inst, seen)
    seen = seen or {}
    if seen[inst] then return end
    seen[inst] = true
    if HasProtectedOwner(inst) then
        if not inst:HasTag("nosteal") then
            inst:AddTag("nosteal")
            inst._klbq_addednosteal = true
        end
    elseif inst._klbq_addednosteal then
        inst:RemoveTag("nosteal")
        inst._klbq_addednosteal = nil
    end
    local container = inst.components.container
    if container ~= nil then
        for _, item in pairs(container.slots) do RefreshItems(item, seen) end
    end
end

local function Pack(...) return { n = select("#", ...), ... } end
local function WithField(object, key, value, fn, ...)
    local previous = object[key]
    object[key] = value
    local result = Pack(pcall(fn, ...))
    object[key] = previous
    if not result[1] then error(result[2], 0) end
    return unpack(result, 2, result.n)
end

local function ProtectInventory(inst)
    -- Native wet-tool slip, Moose/Goose, Bearger, gel and drowning logic.
    inst:AddTag("stronggrip")
    local inventory = inst.components.inventory
    if inventory == nil then return end
    local thiefproof = inventory.IsThiefProof
    inventory.IsThiefProof = function(self, ...)
        return IsProtected(self.inst) or thiefproof(self, ...)
    end
    if inventory.ForEachItem ~= nil then inventory:ForEachItem(RefreshItems) end
end

local function ProtectDrowning(component)
    local fall = component.OnFallInOcean
    component.OnFallInOcean = function(self, ...)
        if IsProtected(self.inst) then
            local active = self.inst.components.inventory:GetActiveItem()
            local item = active ~= nil and active.components.inventoryitem or nil
            if item ~= nil then
                -- The initial fall only checks keepondrown for the cursor item.
                return WithField(item, "keepondrown", true, fall, self, ...)
            end
        end
        return fall(self, ...)
    end
end

local function ProtectKnockback(sg)
    for _, name in ipairs({"knockback", "knockbacklanded"}) do
        local state = sg.states[name]
        if state ~= nil then
            local enter = state.onenter
            state.onenter = function(inst, data, ...)
                if data ~= nil and data.propsmashed and IsProtected(inst) then
                    local safe = {}
                    for key, value in pairs(data) do safe[key] = value end
                    safe.propsmashed = nil
                    data = safe
                end
                return enter(inst, data, ...)
            end
        end
    end
end

local function ProtectBatChomp(sg)
    local attack = sg.states.chomp_attack
    if attack ~= nil then
        local update = attack.onupdate
        attack.onupdate = function(inst, ...)
            local mem = inst.sg.statemem
            if mem.canattach and IsProtected(mem.target) then
                -- Keep the attack's movement and tracking; skip only TryHat.
                return WithField(mem, "canattach", false, update, inst, ...)
            end
            return update(inst, ...)
        end
    end
    local fail = sg.states.chomp_fail
    if fail ~= nil then
        local update = fail.onupdate
        fail.onupdate = function(inst, ...)
            local target = inst.sg.statemem.target
            -- The fail state's update only retries the hat grab.
            if IsProtected(target) and target:IsValid() then return end
            return update(inst, ...)
        end
    end
end

function M.Install(env)
    -- Leave general inventory and container APIs native. Manual unequip,
    -- full inventories, world transitions and death all share those APIs.
    env.AddPrefabPostInit("klbq_kanami", ProtectInventory)
    env.AddComponentPostInit("drownable", ProtectDrowning)
    env.AddPrefabPostInit("slurper", function(inst)
        local test = inst.HatTest
        if test ~= nil then
            inst.HatTest = function(self, target, ...)
                if IsProtected(target) then return false end
                return test(self, target, ...)
            end
        end
    end)
    env.AddStategraphPostInit("wilson", ProtectKnockback)
    env.AddStategraphPostInit("bat", ProtectBatChomp)
    env.AddComponentPostInit("inventoryitem", function(component)
        for _, name in ipairs({"SetOwner", "ClearOwner"}) do
            local original = component[name]
            component[name] = function(self, ...)
                local result = Pack(original(self, ...))
                RefreshItems(self.inst)
                return unpack(result, 1, result.n)
            end
        end
    end)
    env.AddComponentPostInit("container", function(component)
        local thiefproof = component.IsThiefProof
        component.IsThiefProof = function(self, ...)
            return HasProtectedOwner(self.inst) or thiefproof(self, ...)
        end
    end)
end

return M
