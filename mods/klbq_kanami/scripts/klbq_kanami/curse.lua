-- Native cursed_monkey_token immunity belongs to Kanami, never to the world.
-- Verified against the installed cursable/curseditem and HappyPatch Wonkey util.
local M = {}

local function IsImmune(inst)
    -- Character common/master constructors can run before SpawnPrefab assigns
    -- .prefab; the character's own common constructor already adds this tag.
    return inst ~= nil and (inst.prefab == "klbq_kanami" or inst:HasTag("klbq_kanami"))
end

local function ClearBinding(cursed)
    cursed.cursed_target = nil
    cursed.target = nil
    cursed.inst:RemoveTag("applied_curse")
end

local function RefreshItem(cursed, owner)
    if IsImmune(owner) then
        if not cursed._klbq_inert then
            cursed._klbq_inert = true
            cursed._klbq_previous_active = cursed.active
        end
        cursed.active = false -- native setter updates the inventory restriction tag
        ClearBinding(cursed)
    else
        if IsImmune(cursed.cursed_target) then ClearBinding(cursed) end
        if IsImmune(cursed.target) then cursed.target = nil end
        if cursed._klbq_inert then
            cursed.active = cursed._klbq_previous_active
            cursed._klbq_previous_active = nil
            cursed._klbq_inert = nil
        end
    end
end

local function ClearExisting(inst)
    local cursable = inst.components.cursable
    if cursable then cursable.curses.MONKEY = nil end
    for _, field in ipairs({ "_trymonkeychangetask", "_trymonkeyannouncetask" }) do
        if inst[field] then inst[field]:Cancel(); inst[field] = nil end
    end
    inst.monkeyfeet, inst.monkeyhands, inst.monkeytail = nil, nil, nil
    for i = 1, 3 do inst:RemoveTag("MONKEY_CURSE_" .. i) end
    local skinner = inst.components.skinner
    if skinner and skinner:GetMonkeyCurse() ~= nil then skinner:ClearMonkeyCurse() end
    local inventory = inst.components.inventory
    if inventory then
        inventory:ForEachItem(function(item)
            if item.components.curseditem then RefreshItem(item.components.curseditem, inst) end
        end)
    end
end

function M.Common(inst)
    if IsImmune(inst) then inst:AddTag("klbq_curseimmune") end
end

function M.Master(inst)
    if not IsImmune(inst) or inst._klbq_curseimmune then return end
    inst._klbq_curseimmune = true
    local cursable = inst.components.cursable
    if cursable then
        -- Native lookforplayer and OnUpdate both consult this before movement.
        cursable.IsCursable = function() return false end
        -- Given bypasses IsCursable on manual pickup. Block its authoritative
        -- entry point too, including HappyPatch's shared docurse replacement.
        cursable.ApplyCurse = function(_, item)
            if item and item.components.curseditem then RefreshItem(item.components.curseditem, inst) end
        end
        cursable.ForceOntoOwner = function() end
        local remove = cursable.RemoveCurse
        cursable.RemoveCurse = function(self, curse, ...)
            if curse == "MONKEY" then ClearExisting(inst); return end
            return remove(self, curse, ...)
        end
        -- Native Died consumes/spawns all cursed items. Immune inventory items
        -- have no curse to remove and must not be recreated on death.
        cursable.Died = function() ClearExisting(inst) end
    end
    ClearExisting(inst)
    local onload = inst.OnLoad
    local function Loaded(self, ...)
        ClearExisting(self)
        return ...
    end
    -- In character master_postinit, player_common captures this in _OnLoad;
    -- its public OnLoad invokes it after component save data has been restored.
    inst.OnLoad = function(self, ...)
        if onload then return Loaded(self, onload(self, ...)) end
        ClearExisting(self)
    end
    inst:ListenForEvent("ms_respawnedfromghost", ClearExisting)
    -- Covers late skin/inventory restoration without polling every frame.
    inst:DoTaskInTime(0, function() ClearExisting(inst) end)
end

function M.Install(env)
    -- HappyPatch's own cursed-equipment tracker enables its server-side
    -- Talker:Say and chat gibberish. Stop that character-local curse source;
    -- preserving a line only after transmission cannot undo its mutation.
    env.AddComponentPostInit("haitangcurse2hm",function(tracker)
        if not env.GLOBAL.TheWorld.ismastersim or not IsImmune(tracker.inst) then return end
        tracker.DoInit=function(self)
            self.curse_num=0
            local util=env.GLOBAL.TUNING and env.GLOBAL.TUNING.util2hm
            local classified=util and util.GetClassified2hm and util.GetClassified2hm(self.inst.userid)
            if classified and classified.take_cursed_item_num then
                classified.take_cursed_item_num:set(false)
            end
        end
        tracker:DoInit()
    end)
    env.AddComponentPostInit("curseditem", function(cursed)
        if not env.GLOBAL.TheWorld.ismastersim then return end
        local given, update, copy = cursed.Given, cursed.OnUpdate, cursed.CopyCursedFields
        cursed.Given = function(self, item, data, ...)
            if data and IsImmune(data.owner) then
                RefreshItem(self, data.owner)
                return
            end
            RefreshItem(self, data and data.owner)
            return given(self, item, data, ...)
        end
        cursed.OnUpdate = function(self, ...)
            local inventoryitem = self.inst.components.inventoryitem
            RefreshItem(self, inventoryitem and inventoryitem.owner)
            return update(self, ...)
        end
        cursed.CopyCursedFields = function(self, to, ...)
            local function Copied(...)
                if self._klbq_inert then
                    to._klbq_inert = true
                    to._klbq_previous_active = self._klbq_previous_active
                end
                return ...
            end
            return Copied(copy(self, to, ...))
        end
        cursed.inst:ListenForEvent("onputininventory", function(_, owner) RefreshItem(cursed, owner) end)
        cursed.inst:ListenForEvent("ondropped", function() RefreshItem(cursed, nil) end)
    end)
    -- Normal players retain their actual original component and utility calls.
    env.AddPlayerPostInit(function(inst)
        if IsImmune(inst) then
            M.Common(inst)
            if env.GLOBAL.TheWorld.ismastersim then M.Master(inst) end
        end
    end)
end

return M
