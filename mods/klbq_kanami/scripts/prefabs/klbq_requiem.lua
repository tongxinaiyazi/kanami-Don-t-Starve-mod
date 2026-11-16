local assets={Asset("ANIM","anim/klbq_requiem.zip"),Asset("ANIM","anim/swap_klbq_requiem.zip"),
    Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex")}

local function equip(inst,owner)
    owner.AnimState:OverrideSymbol("swap_object","swap_klbq_requiem","swap_object")
    owner.AnimState:Show("ARM_carry");owner.AnimState:Hide("ARM_normal")
end
local function unequip(inst,owner)
    owner.AnimState:Hide("ARM_carry");owner.AnimState:Show("ARM_normal")
end
local function fn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_requiem");inst.AnimState:SetBuild("klbq_requiem")
    inst.AnimState:PlayAnimation("idle")
    inst:AddTag("weapon");inst:AddTag("sharp");inst:AddTag("klbq_requiem")
    MakeInventoryFloatable(inst,"med",.1,.7)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
    inst:AddComponent("equippable")
    inst.components.equippable:SetOnEquip(equip);inst.components.equippable:SetOnUnequip(unequip)
    inst:AddComponent("weapon");inst.components.weapon:SetDamage(51)
    inst:AddComponent("finiteuses")
    inst.components.finiteuses:SetMaxUses(600);inst.components.finiteuses:SetUses(600)
    inst.components.finiteuses:SetOnFinished(inst.Remove)
    MakeHauntableLaunch(inst)
    return inst
end
return Prefab("klbq_requiem",fn,assets,{"klbq_requiem_sweep"})
