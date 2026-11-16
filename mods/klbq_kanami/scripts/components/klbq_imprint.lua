local Imprint = require("klbq_kanami/imprint")
local unpack = unpack
local function Pack(...) return {n = select("#", ...), ...} end

local ImprintComponent = Class(function(self, inst)
    self.inst = inst
    self.flags = {}
    local trader = inst.components.trader
    trader.acceptnontradable = true
    trader:SetAbleToAcceptTest(function(_, sample, giver)
        return self:CanAccept(sample, giver)
    end)
    trader:SetOnAccept(function(_, giver, sample)
        -- Native Trader has already split off and consumed precisely one item.
        local key = Imprint.SAMPLES[sample.prefab]
        if key ~= nil then
            self.flags[key] = true
            self:Sync()
        end
    end)
    local accept = trader.AcceptGift
    trader.AcceptGift = function(component, giver, sample)
        if self.accepting or not self:CanAccept(sample, giver) then return false end
        -- Inventory removal emits events. Hold an item-local guard throughout
        -- those callbacks so reentrant or repeated delivery cannot spend twice.
        self.accepting = true
        local result = Pack(pcall(accept, component, giver, sample, 1))
        self.accepting = false
        if not result[1] then error(result[2], 0) end
        return unpack(result, 2, result.n)
    end
    self:Sync()
end)

function ImprintComponent:CanAccept(sample, giver)
    if not TheWorld.ismastersim or sample == nil or not sample:IsValid()
        or not self.inst:IsValid() or not Imprint.CanUseHands(giver)
        or not giver:HasTag("player") then return false end
    local key = Imprint.SAMPLES[sample.prefab]
    local uses = sample.components.finiteuses
    local sampleitem = sample.components.inventoryitem
    if key == nil or self.flags[key]
        or sampleitem == nil or sampleitem:GetGrandOwner() ~= giver then return false end
    if key ~= "speed" and (uses == nil or uses:GetPercent() <= 0) then return false end
    local owner = self.inst.components.inventoryitem:GetGrandOwner()
    if owner ~= nil then return owner == giver end
    return not self.inst:IsInLimbo() and giver:GetDistanceSqToInst(self.inst) <= 16
end

function ImprintComponent:Sync()
    local inst = self.inst
    local tool = inst.components.tool
    for _, key in ipairs(Imprint.KEYS) do
        local enabled = self.flags[key] == true
        inst["_klbq_imprint_"..key]:set(enabled)
        if key ~= "tough" then
            local action = ACTIONS[string.upper(key)]
            if enabled then
                tool:SetAction(action, 1)
            else
                tool.actions[action] = nil
                inst:RemoveTag(action.id.."_tool")
            end
        end
    end
    tool:EnableToughWork(self.flags.tough == true)
    local speed = self.flags.speed == true
    inst._klbq_imprint_speed:set(speed)
    inst.components.equippable.walkspeedmult = speed and Imprint.SPEED_MULT or 1
    Imprint.RefreshVisuals(inst)
end

function ImprintComponent:OnSave()
    local data = {}
    for _, key in ipairs(Imprint.KEYS) do data[key] = self.flags[key] == true end
    data.speed = self.flags.speed == true
    return data
end

function ImprintComponent:OnLoad(data)
    self.flags = {}
    for _, key in ipairs(Imprint.KEYS) do
        self.flags[key] = data ~= nil and data[key] == true
    end
    self.flags.speed = data ~= nil and data.speed == true
    self:Sync()
end

return ImprintComponent
