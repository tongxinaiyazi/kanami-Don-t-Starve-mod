local Regions = require("klbq_kanami/regions")
local atlas = "images/klbq_region_score.xml"
local assets = {
    Asset("ANIM", "anim/klbq_region_score.zip"),
    Asset("ATLAS", atlas),
    Asset("IMAGE", "images/klbq_region_score.tex"),
}

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_region_score")
    inst.AnimState:SetBuild("klbq_region_score")
    inst.AnimState:PlayAnimation("idle")
    MakeInventoryFloatable(inst, "small", .12)

    inst._klbq_regions = net_string(inst.GUID, "klbq_region_score.regions")
    inst._klbq_region = net_string(inst.GUID, "klbq_region_score.selected")
    inst.displaynamefn = function(self)
        local selected = Regions.Name(self._klbq_region:value())
        local name = STRINGS.NAMES.KLBQ_REGION_SCORE
        return selected ~= "" and (name.."【"..selected.."】") or name
    end

    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname = atlas
    inst.components.inventoryitem.imagename = "klbq_region_score"
    inst.OnSave = function(self, data)
        data.regions = self._klbq_regions:value()
        data.selected = self._klbq_region:value()
    end
    inst.OnLoad = function(self, data)
        if not data or type(data.regions) ~= "string" then return end
        local records, selected = Regions.Record(data.regions, data.selected)
        self._klbq_regions:set(records)
        self._klbq_region:set(selected or "")
    end
    return inst
end

return Prefab("klbq_region_score", fn, assets)
