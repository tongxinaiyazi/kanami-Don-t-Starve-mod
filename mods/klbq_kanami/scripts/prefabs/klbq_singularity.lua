-- Remote replicas call containers.widgetsetup(self) using inst.prefab, before
-- any server-only components exist. Register the same private 14-slot layout
-- on both ends when this prefab module loads, not only via server WidgetSetup.
local containers = require("containers")
local Bag = require("klbq_kanami/bag")
local slotpos = {}
for y = 0, 6 do
    slotpos[#slotpos + 1] = Vector3(-162, -75 * y + 240, 0)
    slotpos[#slotpos + 1] = Vector3(-87, -75 * y + 240, 0)
end
containers.params.klbq_singularity = {
    widget = {
        slotpos = slotpos,
        animbank = "ui_krampusbag_2x8",
        animbuild = "ui_krampusbag_2x8",
        pos = Vector3(-5, -130, 0),
    },
    issidewidget = true,
    type = "pack",
    openlimit = 1,
    itemtestfn = Bag.CanTakeItem,
}
containers.MAXITEMSLOTS = math.max(containers.MAXITEMSLOTS or 0, 14)

local assets =
{
    Asset("ANIM", "anim/klbq_singularity.zip"),
    Asset("ANIM", "anim/ui_krampusbag_2x8.zip"),
    Asset("ATLAS", "images/klbq_kanami_items.xml"),
    Asset("IMAGE", "images/klbq_kanami_items.tex"),
}

local function RemoveLight(inst)
    if inst._klbq_light ~= nil then
        if inst._klbq_light:IsValid() then
            inst._klbq_light:Remove()
        end
        inst._klbq_light = nil
    end
end

local function LightOwner(inst, owner)
    if not inst._klbq_minerhat:value() or owner == nil then
        return
    end
    if inst._klbq_light == nil or not inst._klbq_light:IsValid() then
        inst._klbq_light = SpawnPrefab("minerhatlight")
    end
    if inst._klbq_light ~= nil then
        inst._klbq_light.Light:SetRadius(2.5 + .5 * (inst._klbq_sapphires:value()
            + (inst._klbq_nightvision:value() and 1 or 0)))
        inst._klbq_light.entity:SetParent(owner.entity)
    end
end

local function OnEquip(inst, owner)
    -- A spatial pocket has no worn model. Do not clear any armour symbols.
    inst.components.container:Open(owner)
    LightOwner(inst, owner)
    owner:PushEvent(Bag.LIGHT_DIRTY)
end

local function OnUnequip(inst, owner)
    inst.components.container:Close(owner)
    RemoveLight(inst)
    owner:PushEvent(Bag.LIGHT_DIRTY)
end

local function CanAcceptUpgrade(inst, item)
    return item ~= nil and Bag.CanUpgrade(inst, item.prefab)
end

local function RefreshTrader(inst)
    if inst._klbq_eyeball:value() and inst._klbq_rubies:value() == Bag.MAX_RUBIES
        and inst._klbq_nightvision:value() then
        inst.components.trader:Disable()
    else
        inst.components.trader:Enable()
    end
end

local function UpgradeEyeball(inst)
    if inst._klbq_eyeball:value() then
        return
    end

    inst._klbq_eyeball:set(true)
    RefreshTrader(inst)

    -- Match the installed eyebrella's rain and summer insulation components.
    -- Keep its electrical insulation too, without a fuel cost or worn hat model.
    inst:AddComponent("waterproofer")
    inst.components.waterproofer:SetEffectiveness(TUNING.WATERPROOFNESS_ABSOLUTE)
    inst:AddComponent("insulator")
    inst.components.insulator:SetInsulation(TUNING.INSULATION_LARGE)
    inst.components.insulator:SetSummer()
    inst.components.equippable.insulated = true

    local owner = inst.components.inventoryitem.owner
    local kanami = owner ~= nil and owner.components.klbq_kanami or nil
    if kanami ~= nil then
        -- This also covers upgrading an already equipped bag. Equip/unequip
        -- are recalculated by the character after the native slot changes.
        kanami:ApplyString()
        kanami:Sync()
    end
end

local function UpgradeMinerhat(inst)
    if inst._klbq_minerhat:value() then
        return
    end
    inst._klbq_minerhat:set(true)
    RefreshTrader(inst)
    if inst.components.equippable:IsEquipped() then
        LightOwner(inst, inst.components.inventoryitem.owner)
    end
end

local function SetArmor(inst, count)
    inst._klbq_rubies:set(count)
    if count > 0 then
        if inst.components.armor == nil then
            inst:AddComponent("armor")
            inst.components.armor:InitIndestructible(count / 50)
        else
            inst.components.armor:SetAbsorption(count / 50)
        end
    end
end

local function RefreshWornLight(inst)
    local owner = inst.components.inventoryitem.owner
    if owner ~= nil and inst.components.equippable:IsEquipped() then
        LightOwner(inst, owner)
        owner:PushEvent(Bag.LIGHT_DIRTY)
    end
end

local function OnAcceptUpgrade(inst, giver, item)
    if item.prefab == "deerclops_eyeball" then
        UpgradeEyeball(inst)
    elseif item.prefab == "minerhat" then
        UpgradeMinerhat(inst)
    elseif item.prefab == "redgem" then
        SetArmor(inst, inst._klbq_rubies:value() + 1)
        RefreshTrader(inst)
    elseif item.prefab == "bluegem" then
        inst._klbq_sapphires:set(inst._klbq_sapphires:value() + 1)
        RefreshWornLight(inst)
    elseif item.prefab == Bag.CORE then
        inst._klbq_nightvision:set(true)
        RefreshWornLight(inst)
        RefreshTrader(inst)
    end
end

local function OnSave(inst, data)
    data.klbq_eyeball = inst._klbq_eyeball:value() or nil
    data.klbq_minerhat = inst._klbq_minerhat:value() or nil
    data.klbq_rubies = inst._klbq_rubies:value()
    data.klbq_sapphires = inst._klbq_sapphires:value()
    data.klbq_nightvision = inst._klbq_nightvision:value() or nil
end

local function OnLoad(inst, data)
    if data ~= nil and data.klbq_eyeball == true then
        UpgradeEyeball(inst)
    end
    if data ~= nil and data.klbq_minerhat == true then
        UpgradeMinerhat(inst)
        inst._klbq_sapphires:set(math.clamp(math.floor(tonumber(data.klbq_sapphires) or 0), 0, Bag.MAX_SAPPHIRES))
        inst._klbq_nightvision:set(data.klbq_nightvision == true and inst._klbq_sapphires:value() == Bag.MAX_SAPPHIRES)
        RefreshWornLight(inst)
    end
    if data ~= nil then
        SetArmor(inst, math.clamp(math.floor(tonumber(data.klbq_rubies) or 0), 0, Bag.MAX_RUBIES))
        RefreshTrader(inst)
    end
end

local function fn()
    local inst = CreateEntity()
    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)

    inst.AnimState:SetBank("klbq_singularity")
    inst.AnimState:SetBuild("klbq_singularity")
    inst.AnimState:PlayAnimation("idle")
    inst:AddTag("backpack")
    inst:AddTag("klbq_singularity")
    -- Native tradable/GIVE discovery runs on clients before server components.
    inst:AddTag("trader")
    inst:AddTag("alltrader")
    inst._klbq_eyeball = net_bool(inst.GUID, "klbq_singularity.eyeball", "klbq_eyeballdirty")
    inst._klbq_minerhat = net_bool(inst.GUID, "klbq_singularity.minerhat", "klbq_minerhatdirty")
    inst._klbq_rubies = net_byte(inst.GUID, "klbq_singularity.rubies")
    inst._klbq_sapphires = net_byte(inst.GUID, "klbq_singularity.sapphires")
    inst._klbq_nightvision = net_bool(inst.GUID, "klbq_singularity.nightvision", Bag.LIGHT_DIRTY)

    local oldname = inst.GetDisplayName
    if oldname ~= nil then
        inst.GetDisplayName = function(self, ...)
            local name = oldname(self, ...)
            if name == nil then return nil end
            local armor = 2 * self._klbq_rubies:value()
            local light = self._klbq_minerhat:value() and (self._klbq_sapphires:value() + 1) or 0
            return name..string.format("\n护甲 %d%% · 光源 %s", armor,
                self._klbq_nightvision:value() and "夜视" or light > 0 and string.format("%.1f", 2 + .5 * light) or "未解锁")
        end
    end
    MakeInventoryFloatable(inst, "small", .15, .7)

    inst.entity:SetPristine()
    if not TheWorld.ismastersim then
        inst:ListenForEvent(Bag.LIGHT_DIRTY, function()
            local owner = ThePlayer
            if owner ~= nil then owner:PushEvent(Bag.LIGHT_DIRTY) end
        end)
        return inst
    end

    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname = "images/klbq_kanami_items.xml"
    inst.components.inventoryitem:ChangeImageName("klbq_singularity")
    -- A carried spatial pocket remains an ordinary inventory item, including
    -- inside another bag. Admission guards reject only ownership cycles.
    inst.components.inventoryitem.cangoincontainer = true
    inst.components.inventoryitem.canonlygoinpocket = false

    inst:AddComponent("equippable")
    -- 3173431824 registers BACK only when its backpack slot is enabled.
    -- Its existing backpack assignment/callbacks recognize our public tag.
    inst.equipslot = EQUIPSLOTS.BACK or EQUIPSLOTS.BODY
    inst.components.equippable.equipslot = inst.equipslot
    inst.components.equippable:SetOnEquip(OnEquip)
    inst.components.equippable:SetOnUnequip(OnUnequip)
    inst.components.equippable:SetOnEquipToModel(OnUnequip)

    inst:AddComponent("container")
    -- Native Krampus sack is a 2 x 7 pack, including client replica support.
    inst.components.container:WidgetSetup("klbq_singularity")

    inst:AddComponent("preserver")
    -- Native perishable accepts negative rates, clamps at full freshness,
    -- and handles elapsed time/save data. Restore 10% of normal decay speed;
    -- the native temperature/wetness/frozen-item rules continue to apply.
    inst.components.preserver:SetPerishRateMultiplier(-.1)

    inst:AddComponent("trader")
    inst.components.trader.acceptnontradable = true
    -- Native Trader defaults to one item per GIVE, including stacked eyes.
    inst.components.trader:SetAbleToAcceptTest(CanAcceptUpgrade)
    inst.components.trader:SetOnAccept(OnAcceptUpgrade)
    inst:ListenForEvent("onremove", RemoveLight)
    inst.OnSave = OnSave
    inst.OnLoad = OnLoad

    MakeHauntableLaunchAndDropFirstItem(inst)
    return inst
end

return Prefab("klbq_singularity", fn, assets, {"minerhatlight"})
