local catalog = require("klbq_resources/catalog")

local assets = {
    Asset("ANIM", catalog.ANIM),
    Asset("ATLAS", catalog.ATLAS),
    Asset("IMAGE", catalog.TEXTURE),
}

local function MakeResource(definition)
    local function fn()
        local inst = CreateEntity()
        inst.entity:AddTransform()
        inst.entity:AddAnimState()
        inst.entity:AddNetwork()

        MakeInventoryPhysics(inst)
        inst.AnimState:SetBank(catalog.BANK)
        inst.AnimState:SetBuild(catalog.BUILD)
        inst.AnimState:PlayAnimation(definition.prefab)
        inst.AnimState:SetRayTestOnBB(true)

        inst:AddTag("klbq_resource")
        inst:AddTag("klbq_resource_" .. definition.category)
        MakeInventoryFloatable(inst, "small", 0.05, 0.65)

        inst.entity:SetPristine()
        if not TheWorld.ismastersim then
            return inst
        end

        inst:AddComponent("inspectable")
        inst:AddComponent("inventoryitem")
        inst.components.inventoryitem.atlasname = catalog.ATLAS
        inst.components.inventoryitem:ChangeImageName(definition.prefab)
        inst:AddComponent("stackable")
        -- Replica max-size encoding follows the current tuning categories.
        -- Stack mods can replace their default values before replicas load.
        inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM
        return inst
    end

    return Prefab(definition.prefab, fn, assets)
end

local prefabs = {}
for _, definition in ipairs(catalog.items) do
    prefabs[#prefabs + 1] = MakeResource(definition)
end
return unpack(prefabs)
