local M = {}

local function Owner(inst)
    if inst == nil then return nil end
    local item = inst.components.inventoryitem
    local owner = item ~= nil and item:GetGrandOwner() or inst
    if owner == nil or owner.prefab ~= "klbq_kanami" or owner.components.inventory == nil then return nil end
    local health = owner.components.health
    if owner:HasTag("playerghost") or (health ~= nil and health:IsDead()) then return nil end
    return owner
end

local function RefreshItems(inst, seen)
    seen = seen or {}
    if seen[inst] then return end
    seen[inst] = true
    if Owner(inst) ~= nil then
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

local function Blocked(inst)
    local owner = Owner(inst)
    return owner ~= nil and not owner.components.inventory._klbq_allowdrop
end

local function Pack(...) return { n = select("#", ...), ... } end

local function AllowDrops(inventory, fn, ...)
    local previous = inventory._klbq_allowdrop
    inventory._klbq_allowdrop = true
    local result = Pack(pcall(fn, ...))
    inventory._klbq_allowdrop = previous
    if not result[1] then error(result[2], 0) end
    return unpack(result, 2, result.n)
end

local function AllowCapacityDrops(inventory, item, fn, ...)
    local previous = inventory._klbq_capacityitems
    local allowed = {}
    if item ~= nil then
        allowed[item] = true
        -- ReturnActiveItem can split a stack before calling GiveItem. Keep
        -- that incoming split authorized until the outer return completes.
        if previous ~= nil then previous[item] = true end
    end
    inventory._klbq_capacityitems = allowed
    local result = Pack(pcall(fn, ...))
    inventory._klbq_capacityitems = previous
    if not result[1] then error(result[2], 0) end
    return unpack(result, 2, result.n)
end

local function ProtectInventory(inst)
    inst:AddTag("stronggrip")
    local inventory = inst.components.inventory
    if inventory == nil then return end
    inventory.thiefproof = true
    local equip = inventory.Equip
    inventory.Equip = function(self, item, ...)
        -- Hostile living hats must not displace equipment after their drop
        -- attempt is rejected, especially when every storage slot is full.
        if item ~= nil and item.components.combat ~= nil
            and Owner(item) ~= self.inst and Blocked(self.inst) then
            return false
        end
        return equip(self, item, ...)
    end
    local drop = inventory.DropItem
    inventory.DropItem = function(self, item, ...)
        local allowed = self._klbq_capacityitems
        if item ~= nil and not (allowed and allowed[item]) and Blocked(item) then return nil end
        return drop(self, item, ...)
    end
    -- Native capacity handling may drop its incoming item. Keep this allowance
    -- item-specific so pickup callbacks cannot disarm unrelated equipment.
    local give = inventory.GiveItem
    inventory.GiveItem = function(self, item, ...)
        return AllowCapacityDrops(self, item, give, self, item, ...)
    end
    local returnactive = inventory.ReturnActiveItem
    inventory.ReturnActiveItem = function(self, ...)
        return AllowCapacityDrops(self, self.activeitem, returnactive, self, ...)
    end
    local everything = inventory.DropEverything
    inventory.DropEverything = function(self, ondeath, ...)
        -- Death keeps its native drop rules, including active cursor items.
        if ondeath then return AllowDrops(self, everything, self, ondeath, ...) end
        if Blocked(self.inst) then return nil end
        return everything(self, ondeath, ...)
    end
    for _, name in ipairs({"DropEquipped", "DropActiveItem", "DropItemsWithTag", "DropItemsByFilter"}) do
        local original = inventory[name]
        if original ~= nil then
            inventory[name] = function(self, ...)
                if Blocked(self.inst) then return nil end
                return original(self, ...)
            end
        end
    end
    if inventory.ForEachItem ~= nil then inventory:ForEachItem(RefreshItems) end
end

function M.Install(env)
    env.AddPrefabPostInit("klbq_kanami", ProtectInventory)
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
            return Owner(self.inst) ~= nil or thiefproof(self, ...)
        end
        for _, name in ipairs({"DropItem", "DropItemBySlot", "DropEverything", "DropEverythingByFilter", "DropEverythingWithTag"}) do
            local original = component[name]
            if original ~= nil then
                component[name] = function(self, ...)
                    if Blocked(self.inst) then return nil end
                    return original(self, ...)
                end
            end
        end
    end)
    local drop = env.GLOBAL.ACTIONS.DROP.fn
    env.GLOBAL.ACTIONS.DROP.fn = function(action, ...)
        local doer = action.doer
        local inventory = doer ~= nil and doer.components.inventory or nil
        if inventory ~= nil and doer.prefab == "klbq_kanami" then
            return AllowDrops(inventory, drop, action, ...)
        end
        return drop(action, ...)
    end
end

return M
