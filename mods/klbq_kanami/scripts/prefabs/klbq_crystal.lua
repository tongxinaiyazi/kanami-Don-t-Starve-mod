local assets={Asset("ANIM","anim/klbq_crystal.zip"),Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex")}

local function Pocket(inst)
    -- A carried or stored crystal is inert. This also excludes it from the
    -- native builder's tagged proximity scan before the next tech evaluation.
    inst:RemoveTag("prototyper")
    local prototyper=inst.components.prototyper
    for doer in pairs(prototyper.doers) do prototyper:TurnOff(doer) end
end

local function Ground(inst)
    inst:AddTag("prototyper")
end

local function CanUse(inst,doer)
    return not inst:IsInLimbo() and not inst.components.inventoryitem:IsHeld()
        and doer:HasTag("klbq_kanami") and doer:IsNear(inst,TUNING.RESEARCH_MACHINE_DIST)
end

local function fn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_crystal");inst.AnimState:SetBuild("klbq_crystal");inst.AnimState:PlayAnimation("idle",true)
    inst:AddTag("klbq_crystal");inst:AddTag("prototyper")
    MakeInventoryFloatable(inst,"med",.1,.65)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
    inst:AddComponent("prototyper")
    inst.components.prototyper.trees=TUNING.PROTOTYPER_TREES.KLBQ_STRING
    inst.components.prototyper.restrictedtag="klbq_kanami"
    inst.components.prototyper.overridecanuseprototyper=CanUse
    inst:ListenForEvent("onputininventory",Pocket)
    inst:ListenForEvent("ondropped",Ground)
    MakeHauntableLaunch(inst)
    return inst
end

return Prefab("klbq_crystal",fn,assets)
