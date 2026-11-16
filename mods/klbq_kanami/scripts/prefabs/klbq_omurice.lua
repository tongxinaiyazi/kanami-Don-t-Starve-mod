local Chef = require("klbq_kanami/chef")
local atlas = "images/klbq_kanami_items.xml"
local assets = {
    Asset("ANIM", "anim/klbq_omurice.zip"),
    Asset("ANIM", "anim/plate_food.zip"), Asset("ANIM", "anim/spices.zip"),
    Asset("ATLAS", atlas), Asset("IMAGE", "images/klbq_kanami_items.tex"),
}

local function MakeFood(data)
    local prefabs = { "spoiled_food" }
    for _, name in ipairs(data.prefabs or {}) do prefabs[#prefabs + 1] = name end
    local spice = data.spice ~= nil and string.lower(data.spice) or nil
    local function fn()
        local inst = CreateEntity()
        inst.entity:AddTransform()
        inst.entity:AddAnimState()
        inst.entity:AddNetwork()
        MakeInventoryPhysics(inst)
        inst.AnimState:SetBank(spice ~= nil and "plate_food" or "klbq_omurice")
        inst.AnimState:SetBuild(spice ~= nil and "plate_food" or "klbq_omurice")
        inst.AnimState:PlayAnimation("idle")
        if spice ~= nil then
            inst.AnimState:OverrideSymbol("swap_food", "klbq_omurice", "klbq_omurice")
            inst.AnimState:OverrideSymbol("swap_garnish", "spices", spice)
            inst:AddTag("spicedfood")
            inst.inv_image_bg = { atlas = atlas, image = "klbq_omurice.tex" }
            inst:SetPrefabNameOverride("klbq_omurice")
            inst.displaynamefn = function()
                return subfmt(STRINGS.NAMES[data.spice.."_FOOD"], { food = STRINGS.NAMES.KLBQ_OMURICE })
            end
        end
        inst:AddTag("preparedfood")
        MakeInventoryFloatable(inst, "small", .1, .7)
        inst.entity:SetPristine()
        if not TheWorld.ismastersim then return inst end

        inst.food_symbol_build = "klbq_omurice"
        inst.food_basename = data.basename
        inst:AddComponent("edible")
        inst.components.edible.foodtype = data.foodtype
        inst.components.edible.healthvalue = data.health
        inst.components.edible.hungervalue = data.hunger
        inst.components.edible.sanityvalue = data.sanity
        inst.components.edible.spice = data.spice
        inst.components.edible.temperaturedelta = data.temperature or 0
        inst.components.edible.temperatureduration = data.temperatureduration or 0
        inst.components.edible.nochill = data.nochill
        inst.components.edible:SetOnEatenFn(data.oneatenfn)
        inst:AddComponent("inspectable")
        inst:AddComponent("inventoryitem")
        if spice ~= nil then
            inst.components.inventoryitem:ChangeImageName(spice.."_over")
        else
            inst.components.inventoryitem.atlasname = atlas
            inst.components.inventoryitem:ChangeImageName("klbq_omurice")
        end
        inst:AddComponent("stackable")
        inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM
        inst:AddComponent("perishable")
        inst.components.perishable:SetPerishTime(data.perishtime)
        inst.components.perishable.onperishreplacement = "spoiled_food"
        inst.components.perishable:StartPerishing()
        inst:AddComponent("bait")
        inst:AddComponent("tradable")
        MakeSmallBurnable(inst)
        MakeSmallPropagator(inst)
        MakeHauntableLaunchAndPerish(inst)
        return inst
    end
    return Prefab(data.name, fn, assets, prefabs)
end

local prefabs = {}
for _, data in ipairs(Chef.GetRecipes()) do prefabs[#prefabs + 1] = MakeFood(data) end
return unpack(prefabs)
