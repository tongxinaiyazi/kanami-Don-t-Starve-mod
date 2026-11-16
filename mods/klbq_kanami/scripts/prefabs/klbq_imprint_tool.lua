local Imprint = require("klbq_kanami/imprint")
local assets = {
    Asset("ANIM", "anim/klbq_imprint_tool.zip"),
    Asset("ANIM", "anim/swap_klbq_imprint_tool.zip"),
    Asset("ATLAS", "images/klbq_kanami_items.xml"),
    Asset("IMAGE", "images/klbq_kanami_items.tex"),
}

local function OnEquip(inst, owner)
    Imprint.BindHeld(inst, owner)
    owner.AnimState:Show("ARM_carry")
    owner.AnimState:Hide("ARM_normal")
end

local function OnUnequip(inst, owner)
    Imprint.UnbindHeld(inst, true)
    owner.AnimState:Hide("ARM_carry")
    owner.AnimState:Show("ARM_normal")
end

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_imprint_tool")
    inst.AnimState:SetBuild("klbq_imprint_tool")
    inst.AnimState:PlayAnimation("idle")
    for _, tag in ipairs({"klbq_imprint_tool", "tool", "weapon", "sharp", "trader", "alltrader"}) do
        inst:AddTag(tag)
    end
    for _, key in ipairs(Imprint.KEYS) do
        inst["_klbq_imprint_"..key] = net_bool(inst.GUID, "klbq_imprint."..key, "klbq_imprintdirty")
    end
    inst._klbq_imprint_speed = net_bool(inst.GUID, "klbq_imprint.speed", "klbq_imprintdirty")
    inst:ListenForEvent("klbq_imprintdirty", Imprint.RefreshVisuals)
    Imprint.RefreshVisuals(inst)
    local displayname = inst.GetDisplayName
    inst.GetDisplayName = function(self, ...)
        return displayname(self, ...).."\n"..Imprint.Status(self)
    end
    MakeInventoryFloatable(inst, "med", .05, .7)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end

    inst:AddComponent("inspectable")
    inst.components.inspectable.descriptionfn = function(item)
        return "手中的回响，会记住每一次劳作。\n"..Imprint.Status(item)
    end
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname = "images/klbq_kanami_items.xml"
    inst.components.inventoryitem:ChangeImageName("klbq_imprint_tool")
    inst:AddComponent("equippable")
    inst.components.equippable.equipslot = EQUIPSLOTS.HANDS
    inst.components.equippable:SetOnEquip(OnEquip)
    inst.components.equippable:SetOnUnequip(OnUnequip)
    inst:AddComponent("weapon")
    inst.components.weapon:SetDamage(17)
    inst:AddComponent("tool")
    inst:AddComponent("trader")
    inst:AddComponent("klbq_imprint")
    inst:ListenForEvent("onremove", function() Imprint.UnbindHeld(inst, true) end)
    MakeHauntableLaunch(inst)
    return inst
end

return Prefab("klbq_imprint_tool", fn, assets)
