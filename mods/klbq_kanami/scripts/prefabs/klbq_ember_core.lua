local catalog = require("klbq_resources/catalog")
local IMAGE = "klbq_resource_stringsea_beacon"
local assets = {
    Asset("ANIM", catalog.ANIM),
    Asset("ATLAS", catalog.ATLAS),
    Asset("IMAGE", catalog.TEXTURE),
}

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank(catalog.BANK)
    inst.AnimState:SetBuild(catalog.BUILD)
    inst.AnimState:PlayAnimation(IMAGE)
    inst.AnimState:SetMultColour(1, .64, .45, 1)
    MakeInventoryFloatable(inst, "small", .05, .65)
    inst.entity:SetPristine()

    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname = catalog.ATLAS
    inst.components.inventoryitem:ChangeImageName(IMAGE)
    inst:AddComponent("stackable")
    inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM
    MakeHauntableLaunch(inst)
    return inst
end

return Prefab("klbq_ember_core", fn, assets)
