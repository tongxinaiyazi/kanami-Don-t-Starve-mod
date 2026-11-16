local assets={Asset("ANIM","anim/klbq_finale.zip"),Asset("ANIM","anim/swap_klbq_finale.zip"),Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex")}
local function equip(inst,owner)
    owner.AnimState:OverrideSymbol("swap_object","swap_klbq_finale","swap_object")
    owner.AnimState:Show("ARM_carry");owner.AnimState:Hide("ARM_normal")
    inst.components.container:Open(owner)
end
local function unequip(inst,owner)
    owner.AnimState:Hide("ARM_carry");owner.AnimState:Show("ARM_normal")
    inst.components.container:Close(owner)
end
local function fn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_finale");inst.AnimState:SetBuild("klbq_finale");inst.AnimState:PlayAnimation("idle")
    inst:AddTag("klbq_finale");inst:AddTag("rangedweapon");inst:AddTag("weapon")
    MakeInventoryFloatable(inst,"med",.1,.65)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
    inst:AddComponent("equippable")
    inst.components.equippable:SetOnEquip(equip);inst.components.equippable:SetOnUnequip(unequip)
    -- Weapon is present for compatibility/snapshot power, but every ordinary
    -- ATTACK path is filtered for this gun, loaded or empty. Shoot is custom.
    inst:AddComponent("weapon");inst.components.weapon:SetDamage(34)
    inst:AddComponent("container");inst.components.container:WidgetSetup("klbq_finale")
    inst.components.container.stay_open_on_hide=true
    MakeHauntableLaunch(inst)
    return inst
end
return Prefab("klbq_finale",fn,assets,{"klbq_ammo_heart","klbq_ammo_fate","klbq_ammo_doom"})
