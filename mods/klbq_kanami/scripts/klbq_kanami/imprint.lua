-- Client-visible imprint state and the inventory-to-item action. Ground
-- offerings use DST's original GIVE/Trader path, including normal RPCs.
local M = {}
M.KEYS = {"chop", "mine", "dig", "tough"}
M.SAMPLES = {goldenaxe = "chop", goldenpickaxe = "mine",
    goldenshovel = "dig", multitool_axe_pickaxe = "tough"}
local LABELS = {chop = "砍伐", mine = "采矿", dig = "挖掘", tough = "坚硬作业"}
-- Verified against SGwilson in the installed scripts.zip. The preparation
-- state already needs the projected tool, before its first work timeline hit.
local WORKFORMS = {chop_start = "chop", chop = "chop", mine_start = "mine",
    mine = "mine", mine_recoil = "mine", dig_start = "dig", dig = "dig"}

function M.Has(inst, key)
    local flag = inst ~= nil and inst["_klbq_imprint_"..key] or nil
    return flag ~= nil and flag:value() == true
end

function M.Mask(inst)
    local mask, bit = 0, 1
    for _, key in ipairs(M.KEYS) do
        if M.Has(inst, key) then mask = mask + bit end
        bit = bit * 2
    end
    return mask
end

function M.CanUseHands(doer)
    if doer == nil or not doer:IsValid() or doer:HasTag("playerghost") then return false end
    local components = doer.components
    local health = components ~= nil and components.health or nil
    local kanami = components ~= nil and components.klbq_kanami or nil
    return not (health ~= nil and health:IsDead())
        and not (kanami ~= nil and (not kanami:Alive() or not kanami:CanUseHands() or kanami.state.string))
        and not (doer._klbq_string ~= nil and doer._klbq_string:value())
        and not (doer._klbq_protect ~= nil and doer._klbq_protect:value())
end

function M.Status(inst)
    local parts = {}
    for _, key in ipairs(M.KEYS) do
        parts[#parts + 1] = LABELS[key]..(M.Has(inst, key) and "●" or "○")
    end
    return table.concat(parts, " · ")
end

function M.HeldForm(owner)
    if not M.CanUseHands(owner) then return "idle" end
    local state = owner.sg ~= nil and owner.sg.currentstate or nil
    return state ~= nil and WORKFORMS[state.name] or "idle"
end

local function IsCurrentHands(inst, owner)
    local inventory = owner ~= nil and owner.components ~= nil and owner.components.inventory or nil
    return inventory ~= nil and inventory:GetEquippedItem(EQUIPSLOTS.HANDS) == inst
end

local function ApplyHeld(inst, owner, form)
    owner.AnimState:OverrideSymbol("swap_object", "swap_klbq_imprint_tool",
        "swap_"..form.."_"..M.Mask(inst))
end

function M.UnbindHeld(inst, reset)
    local owner = inst._klbq_imprint_owner
    if owner == nil then return end
    if reset and IsCurrentHands(inst, owner) then ApplyHeld(inst, owner, "idle") end
    for event, callback in pairs(inst._klbq_imprint_observers) do
        owner:RemoveEventCallback(event, callback)
    end
    inst._klbq_imprint_owner = nil
    inst._klbq_imprint_observers = nil
end

function M.BindHeld(inst, owner)
    M.UnbindHeld(inst)
    if not TheWorld.ismastersim then return end
    inst._klbq_imprint_owner = owner
    inst._klbq_imprint_observers = {
        newstate = function() M.RefreshVisuals(inst) end,
        death = function() M.UnbindHeld(inst, true) end,
        onremove = function() M.UnbindHeld(inst) end,
    }
    for event, callback in pairs(inst._klbq_imprint_observers) do
        owner:ListenForEvent(event, callback)
    end
    ApplyHeld(inst, owner, M.HeldForm(owner))
end

function M.RefreshVisuals(inst)
    -- Each LED is an independent symbol in the ground item's animation build.
    -- Its actual work tags are owned by the server Tool component.
    if inst.AnimState.SetSymbolMultColour ~= nil then
        for _, key in ipairs(M.KEYS) do
            local on = M.Has(inst, key)
            inst.AnimState:SetSymbolMultColour("imprint_"..key,
                on and .42 or .18, on and 1 or .18, on and .84 or .22, 1)
        end
    end
    -- Server AnimState symbol overrides replicate to every client. Predicted
    -- SGwilson_client returns to idle while the matching server work continues;
    -- letting that client idle overwrite the symbol would erase the projection.
    if not TheWorld.ismastersim then return end
    local item = inst.components ~= nil and inst.components.inventoryitem or nil
    local owner = item ~= nil and item.owner or nil
    if IsCurrentHands(inst, owner) then
        ApplyHeld(inst, owner, M.HeldForm(owner))
    end
end

function M.Install(env, collectuseitem)
    local G = env.GLOBAL
    local action = G.Action({priority = 3, rmb = true, mount_valid = false})
    action.id = "KLBQ_IMPRINT"
    action.str = "印刻"
    action.fn = function(act)
        local target = act.target
        local imprint = target ~= nil and target.components.klbq_imprint or nil
        if not G.TheWorld.ismastersim or imprint == nil then return false end
        return target.components.trader:AcceptGift(act.doer, act.invobject)
    end
    env.AddAction(action)
    env.AddComponentAction("USEITEM", "inventoryitem", function(sample, doer, target, actions, right)
        -- A mod can register only one callback per component/action type.
        -- Share this entry with bag upgrades instead of replacing imprinting.
        if collectuseitem ~= nil then
            collectuseitem(sample, doer, target, actions, right)
        end
        local key = M.SAMPLES[sample.prefab]
        local inventoryitem = target ~= nil and target.replica.inventoryitem or nil
        -- Native GIVE covers ground targets. This additional action also works
        -- when the target is in one's own pockets or nested backpack.
        if key ~= nil and target ~= nil and target:HasTag("klbq_imprint_tool")
            and not M.Has(target, key) and not sample:HasTag("usesdepleted")
            and inventoryitem ~= nil and inventoryitem:IsGrandOwner(doer)
            and M.CanUseHands(doer) then
            table.insert(actions, action)
        end
    end)
    env.AddStategraphActionHandler("wilson", G.ActionHandler(action, "doshortaction"))
    env.AddStategraphActionHandler("wilson_client", G.ActionHandler(action, "doshortaction"))
end

return M
