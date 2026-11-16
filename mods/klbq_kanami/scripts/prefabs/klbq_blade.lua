local assets={Asset("ANIM","anim/klbq_blade.zip"),Asset("ANIM","anim/swap_klbq_blade.zip"),
    Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex")}
local function OnEquip(inst,owner)
    owner.AnimState:OverrideSymbol("swap_object","swap_klbq_blade","swap_object")
    owner.AnimState:Show("ARM_carry");owner.AnimState:Hide("ARM_normal")
end
local function OnUnequip(inst,owner)
    owner.AnimState:Hide("ARM_carry");owner.AnimState:Show("ARM_normal")
end
local function fn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_blade");inst.AnimState:SetBuild("klbq_blade");inst.AnimState:PlayAnimation("idle")
    inst:AddTag("sharp");inst:AddTag("pointy");inst:AddTag("weapon")
    MakeInventoryFloatable(inst,"med",.05,.7)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("weapon");inst.components.weapon:SetDamage(51)
    inst:AddComponent("finiteuses")
    inst.components.finiteuses:SetMaxUses(200);inst.components.finiteuses:SetUses(200)
    inst.components.finiteuses:SetOnFinished(inst.Remove)
    inst:AddComponent("inspectable");inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
    inst:AddComponent("equippable")
    inst.components.equippable:SetOnEquip(OnEquip);inst.components.equippable:SetOnUnequip(OnUnequip)
    MakeHauntableLaunch(inst)
    return inst
end
return Prefab("klbq_blade",fn,assets)
