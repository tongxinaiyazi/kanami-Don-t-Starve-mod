local names={"klbq_ammo_heart","klbq_ammo_fate","klbq_ammo_doom"}
local function Make(name)
    local assets={Asset("ANIM","anim/"..name..".zip"),Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex")}
    local function fn()
        local inst=CreateEntity()
        inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
        MakeInventoryPhysics(inst)
        inst.AnimState:SetBank(name);inst.AnimState:SetBuild(name);inst.AnimState:PlayAnimation("idle")
        inst:AddTag("klbq_ammo")
        MakeInventoryFloatable(inst,"small",.05,.7)
        inst.entity:SetPristine()
        if not TheWorld.ismastersim then return inst end
        inst:AddComponent("inspectable");inst:AddComponent("inventoryitem")
        inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
        inst:AddComponent("stackable");inst.components.stackable.maxsize=TUNING.STACK_SIZE_SMALLITEM
        MakeHauntableLaunch(inst)
        return inst
    end
    return Prefab(name,fn,assets)
end
return Make(names[1]),Make(names[2]),Make(names[3])
