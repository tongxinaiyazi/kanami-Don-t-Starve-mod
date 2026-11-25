local M = {}
M.MAX_RUBIES = 45
M.MAX_SAPPHIRES = 5
M.CORE = "klbq_ember_core"
M.LIGHT_DIRTY = "klbq_baglightdirty"

local function IsBag(inst)
    return inst ~= nil and (inst.prefab == "klbq_singularity"
        or (inst.HasTag ~= nil and inst:HasTag("klbq_singularity")))
end

function M.CanUpgrade(bag, prefab)
    if prefab == "deerclops_eyeball" then
        return bag._klbq_eyeball ~= nil and not bag._klbq_eyeball:value()
    elseif prefab == "minerhat" then
        return bag._klbq_minerhat ~= nil and not bag._klbq_minerhat:value()
    elseif prefab == "redgem" then
        return bag._klbq_rubies ~= nil and bag._klbq_rubies:value() < M.MAX_RUBIES
    elseif prefab == "bluegem" then
        return bag._klbq_minerhat ~= nil and bag._klbq_minerhat:value()
            and bag._klbq_sapphires:value() < M.MAX_SAPPHIRES
    elseif prefab == M.CORE then
        return bag._klbq_minerhat ~= nil and bag._klbq_minerhat:value()
            and bag._klbq_sapphires:value() == M.MAX_SAPPHIRES and not bag._klbq_nightvision:value()
    end
    return false
end

function M.CollectUpgradeAction(item, doer, target, actions, right)
    if not IsBag(target) or not target:HasTag("trader") or not M.CanUpgrade(target, item.prefab) then
        return
    end
    local inventoryitem = item.replica.inventoryitem
    local rider = doer.replica.rider
    if inventoryitem == nil or inventoryitem:CanOnlyGoInPocket()
        or inventoryitem:IsLockedInSlot()
        or inventoryitem:CanOnlyGoInPocketOrPocketContainers()
        or not inventoryitem:IsGrandOwner(doer)
        or (rider ~= nil and rider:IsRiding()) then
        return
    end
    -- Native inventoryitem chooses STORE for an openable container before
    -- checking alltrader. Override only this pending upgrade, on both mouse
    -- buttons; controller inventory use checks the right button first too.
    local give = false
    for i = #actions, 1, -1 do
        if actions[i] == ACTIONS.STORE then
            table.remove(actions, i)
        elseif actions[i] == ACTIONS.GIVE then
            give = true
        end
    end
    if not give then
        table.insert(actions, ACTIONS.GIVE)
    end
end

local function Owner(inst)
    local item = inst.components ~= nil and inst.components.inventoryitem or nil
    if item ~= nil then
        return item.owner
    end
    -- Clients have no InventoryItem component. Entity parenting follows the
    -- same nested ownership graph without exposing server-only components.
    return inst.entity ~= nil and inst.entity.GetParent ~= nil and inst.entity:GetParent() or nil
end

function M.CanTakeItem(container, item)
    if item == nil then return true end
    local current = container.inst
    local related = IsBag(item)
    local contains = false
    local seen = {}
    while current ~= nil and not seen[current] do
        seen[current] = true
        related = related or IsBag(current)
        contains = contains or current == item
        current = Owner(current)
    end
    -- An ordinary box may contain the singularity, and vice versa. Refuse only
    -- a cycle through our bag; preserve native rules for all other containers.
    return not (related and (contains or current ~= nil))
end

local function InstallAdmission(container)
    if container._klbq_cyclecheck then return end
    container._klbq_cyclecheck = true
    local old = container.CanTakeItemInSlot
    container.CanTakeItemInSlot = function(self, item, ...)
        if not M.CanTakeItem(self, item) then return false end
        return old(self, item, ...)
    end
end

local function SuppressButton(button)
    -- Button's constructor uses "BUTTON"; SetText changes .name to its label.
    -- Identify its public button methods instead of the mutable widget name.
    if not button.SetOnClick or not button.Disable or not button.SetClickable
        or button._klbq_hiddenbagbutton then return end
    button._klbq_hiddenbagbutton = true
    button:Hide()
    button:SetClickable(false)
    button:Disable()
    button.onclick = nil
    -- Third-party Open hooks finish configuring children after AddChild.
    -- Keep a usable child reference for their Close/Kill paths while ensuring
    -- that later Show/Enable/SetOnClick cannot restore these controls.
    button.Show = button.Hide
    button.Enable = button.Disable
    local setclickable = button.SetClickable
    button.SetClickable = function(self) return setclickable(self, false) end
    button.SetOnClick = function() end
    button.OnControl = function() return false end
end

local function GuardButtons(widget, isours)
    if widget._klbq_bagbuttonguard then return end
    widget._klbq_bagbuttonguard = true
    local add = widget.AddChild
    widget.AddChild = function(self, child, ...)
        local result = add(self, child, ...)
        if isours() then SuppressButton(child) end
        return result
    end
    if isours() then
        for child in pairs(widget.children or {}) do SuppressButton(child) end
    end
end

local function Pack(...)
    return {n = select("#", ...), ...}
end

function M.Install(env)
    env.AddComponentPostInit("container", InstallAdmission)
    env.AddClassPostConstruct("components/container_replica", InstallAdmission)
    env.AddClassPostConstruct("widgets/containerwidget", function(self)
        if self._klbq_bagwindowguard then return end
        self._klbq_bagwindowguard = true
        GuardButtons(self, function()
            return IsBag(self._klbq_openingcontainer or self.container)
        end)
        local open = self.Open
        self.Open = function(widget, container, ...)
            widget._klbq_openingcontainer = container
            local result = Pack(open(widget, container, ...))
            widget._klbq_openingcontainer = nil
            return unpack(result, 1, result.n)
        end
    end)
    env.AddClassPostConstruct("widgets/inventorybar", function(self)
        local function IsOurOverflow()
            local inventory = self.owner ~= nil and self.owner.replica.inventory or nil
            local overflow = inventory ~= nil and inventory:GetOverflowContainer() or nil
            return self.integrated_backpack and overflow ~= nil and IsBag(overflow.inst)
        end
        local function GuardRow(row)
            if row ~= nil then GuardButtons(row, IsOurOverflow) end
        end
        GuardRow(self.bottomrow)
        -- Native Rebuild replaces bottomrow every time. Attach before later
        -- mods add controls, whichever order their Rebuild wrappers run in.
        local root = self.root
        if root ~= nil and not root._klbq_bagrowguard then
            root._klbq_bagrowguard = true
            local add = root.AddChild
            root.AddChild = function(widget, child, ...)
                local result = add(widget, child, ...)
                if child.name == "bottomrow" then GuardRow(child) end
                return result
            end
        end
    end)
end

return M
