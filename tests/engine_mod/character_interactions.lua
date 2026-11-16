-- Dedicated-server diagnostics against real entities/components. These query
-- physics masks and AnimState state; they do not render or verify client art.
-- The parent harness owns its player and shutdown. Optional context.done runs
-- after the delayed appearance check and fixture cleanup (about .2 seconds).
local G = GLOBAL
local assert, ipairs, pairs, type = G.assert, G.ipairs, G.pairs, G.type

function RunKanamiCharacterInteractionChecks(context)
    local player, check, eq = context.player, context.check, context.eq
    local c = assert(player.components.klbq_kanami)
    local inventory, moisture = player.components.inventory, player.components.moisture
    local original_equipment, owned = {}, {}
    local displaced, saved_moisture
    local bag, spear, armor, hat
    local x, y, z = player.Transform:GetWorldPosition()

    local function Spawn(prefab)
        local item = assert(G.SpawnPrefab(prefab), "failed to spawn "..prefab)
        owned[#owned + 1] = item
        item.entity:SetCanSleep(false)
        item.Transform:SetPosition(x, y, z)
        return item
    end
    local function WaterPath()
        local caps = player.components.locomotor.pathcaps
        return caps ~= nil and caps.allowocean == true
    end
    local function OriginalAppearance()
        local anim = player.AnimState
        assert(type(anim.GetSymbolOverride) == "function", "native symbol override query is unavailable")
        assert(anim:GetBuild() == "klbq_kanami", "current build is "..G.tostring(anim:GetBuild()))
        assert(anim:GetSkinBuild() == "", "clothing/base skin overlay remained")
        for _, symbol in ipairs({"swap_hat", "swap_body", "swap_body_tall", "swap_backpack", "backpack", "headbase_hat", "torso"}) do
            local build, source = anim:GetSymbolOverride(symbol)
            assert(build == nil and source == nil, symbol.." override remains: "..G.tostring(build).."/"..G.tostring(source))
        end
        G.print("[KANAMI_CHARACTER_APPEARANCE]", "build", anim:GetBuild(), "skin", anim:GetSkinBuild(),
            "symbol overrides cleared; no client rendering asserted")
    end
    local function Cleanup()
        check("character interaction fixture cleanup preserves parent player and equipment", function()
            -- Bypass the public C-exit safety refusal only for fixture teardown:
            -- no world movement took place, and the parent must resume normally.
            c.state.deadlines.protect = nil
            c.state.string = false
            c:Protection(false)
            c:ApplyString()
            c:Sync()
            for i = #owned, 1, -1 do
                if owned[i]:IsValid() then owned[i]:Remove() end
            end
            if displaced and displaced:IsValid() then
                assert(inventory:GiveItem(displaced, 1), "could not restore original inventory slot")
            end
            for _, entry in ipairs(original_equipment) do
                assert(entry.item:IsValid(), "an original equipped item was removed")
                assert(inventory:Equip(entry.item), "could not restore original equipment slot "..G.tostring(entry.slot))
                assert(inventory:GetEquippedItem(entry.slot) == entry.item)
            end
            if saved_moisture ~= nil then moisture:DoDelta(saved_moisture - moisture:GetMoisture(), true) end
            c:ApplyString()
            c:Sync()
            assert(player:IsValid(), "parent player was removed")
            assert(not c.state.string and not c:IsProtected(), "fixture left C or resurrection protection active")
            assert(not player._klbq_waterwalk:value())
        end)
        if context.done then context.done() end
    end

    local ready = check("character interaction fixture uses intact parent actor", function()
        assert(player:IsValid() and c:Alive(), "parent actor must be alive")
        assert(player:GetCurrentPlatform() == nil and G.TheWorld.Map:IsVisualGroundAtPoint(x, y, z), "fixture needs land")
        c.state.deadlines.protect = nil
        c.state.string = false
        c:Protection(false)
        c:ApplyString()
        c:Sync()
        for slot, item in pairs(inventory.equipslots) do
            original_equipment[#original_equipment + 1] = {slot = slot, item = item}
        end
        for _, entry in ipairs(original_equipment) do
            assert(inventory:Unequip(entry.slot, nil, true) == entry.item)
        end
        assert(inventory:GetNumSlots() > 0, "fixture needs a normal inventory slot")
        local old = inventory:GetItemInSlot(1)
        if old then
            displaced = assert(inventory:RemoveItem(old, true))
            assert(displaced == old, "inventory did not return the displaced item")
        end
        saved_moisture = moisture:GetMoisture()
        moisture:DoDelta(-saved_moisture, true)
        eq(moisture:GetMoisture(), 0)
    end)
    if not ready then Cleanup();return end

    check("character C native mask keeps land ocean shore and removes entity obstacles", function()
        assert(c:ToggleString(), "dry native actor could not enter C")
        eq(player.Physics:GetCollisionMask(), G.COLLISION.WORLD)
        assert(not WaterPath() and not player._klbq_waterwalk:value())
        assert(G.checkbit(player.Physics:GetCollisionMask(), G.COLLISION.LAND_OCEAN_LIMITS))
        G.print("[KANAMI_CHARACTER_MASK]", "C without upgraded worn bag", player.Physics:GetCollisionMask(),
            "WORLD", G.COLLISION.WORLD, "shore", G.COLLISION.LAND_OCEAN_LIMITS)
    end)
    check("character ordinary worn bag retains native shore boundary", function()
        bag = Spawn("klbq_singularity")
        assert(inventory:Equip(bag))
        eq(player.Physics:GetCollisionMask(), G.COLLISION.WORLD)
        assert(not WaterPath() and not player._klbq_waterwalk:value())
    end)
    check("character upgraded worn bag changes actual mask to ground and permits ocean", function()
        assert(bag and c.state.string, "previous C/bag setup failed")
        local eye = Spawn("deerclops_eyeball")
        assert(inventory:GiveItem(eye))
        assert(bag.components.trader:AcceptGift(player, eye))
        assert(bag._klbq_eyeball:value())
        c:Tick()
        eq(player.Physics:GetCollisionMask(), G.COLLISION.GROUND)
        assert(WaterPath() and player._klbq_waterwalk:value())
        G.print("[KANAMI_CHARACTER_MASK]", "C with upgraded worn bag", player.Physics:GetCollisionMask(),
            "GROUND", G.COLLISION.GROUND)
    end)
    check("character removing upgraded bag on land restores shore without moving actor", function()
        assert(bag, "bag setup failed")
        assert(inventory:Unequip(bag.components.equippable.equipslot, nil, true) == bag)
        eq(player.Physics:GetCollisionMask(), G.COLLISION.WORLD)
        assert(not WaterPath() and not player._klbq_waterwalk:value())
        local ax, ay, az = player.Transform:GetWorldPosition()
        eq(ax, x);eq(ay, y);eq(az, z)
        c.state.string = false;c:ApplyString();c:Sync()
    end)
    check("character native protected PICKUP stores spear while HANDS equip remains forbidden", function()
        c.state.deadlines.protect = G.GetTime() + 30
        c:Protection(true);c:Sync()
        assert(c:IsProtected() and player._klbq_protect:value())
        assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == nil)
        spear = Spawn("spear")
        local action = G.BufferedAction(player, spear, G.ACTIONS.PICKUP)
        assert(G.ACTIONS.PICKUP.fn(action), "native PICKUP failed")
        assert(inventory:GetItemSlot(spear) ~= nil, "spear was not put into native inventory")
        assert(spear.components.inventoryitem.owner == player)
        assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == nil)
        assert(not inventory:Equip(spear), "protected actor equipped a hand weapon")
        assert(inventory:GetItemSlot(spear) ~= nil and spear:IsValid())
        assert(c.pickupitem == nil, "native pickup action scope leaked")
        assert(not player.components.combat:CanAttack(nil), "protected native combat allowed attack")
        c.state.deadlines.protect = nil;c:Protection(false);c:Sync()
    end)
    check("character native armor and hat callbacks leave original queried appearance", function()
        c.state.deadlines.protect = nil;c.state.string = false
        c:Protection(false);c:ApplyString();c:Sync()
        armor = Spawn("armorwood");hat = Spawn("strawhat")
        assert(inventory:Equip(armor) and inventory:Equip(hat))
        assert(inventory:GetEquippedItem(armor.components.equippable.equipslot) == armor)
        assert(inventory:GetEquippedItem(hat.components.equippable.equipslot) == hat)
        assert(armor.components.armor and armor.components.armor.absorb_percent > 0, "armor component lost its gameplay effect")
        OriginalAppearance()
    end)

    G.TheWorld:DoTaskInTime(.2, function()
        check("character native deferred equip callbacks retain original queried appearance", function()
            assert(armor and hat and armor:IsValid() and hat:IsValid(), "appearance setup failed")
            OriginalAppearance()
        end)
        Cleanup()
    end)
end
