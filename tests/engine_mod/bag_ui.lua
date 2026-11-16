-- Native-world checks for carried/nested bags, run by bag.lua before cleanup.
-- The matching UI checks
-- execute the installed ContainerWidget and HappyPatch sources in
-- tests/gameplay/test_bag_ui.py; this file does not claim to render a client.
local G = GLOBAL

function RunKanamiBagUIChecks(context)
    local player, check, eq = context.player, context.check, context.eq
    local owned = {}
    local function Spawn(name)
        local inst = G.assert(G.SpawnPrefab(name))
        owned[#owned + 1] = inst
        inst.Transform:SetPosition(player.Transform:GetWorldPosition())
        return inst
    end
    local bag, inner, outer
    check("bag native inventory accepts an unequipped singularity", function()
        bag = Spawn("klbq_singularity")
        G.assert(player.components.inventory:GiveItem(bag))
        G.assert(bag.components.inventoryitem.owner == player, "carried bag has the wrong owner")
        G.assert(not bag.components.equippable:IsEquipped())
        eq(bag.components.container:GetNumSlots(), 14)
        eq(#bag.replica.container:GetWidget().slotpos, 14)
    end)
    check("bag native container permits storage in another backpack", function()
        outer = Spawn("krampus_sack")
        G.assert(player.components.inventory:RemoveItem(bag, true) == bag)
        G.assert(outer.components.container:GiveItem(bag, 1))
        G.assert(bag.components.inventoryitem.owner == outer, "nested bag has the wrong owner")
        G.assert(outer.components.container:GetItemInSlot(1) == bag, "native container did not retain the bag")
    end)
    check("bag native container rejects self and indirect cycles", function()
        G.assert(not bag.components.container:CanTakeItemInSlot(bag, 1))
        -- Native Krampus sacks cannot normally enter any container. Make only
        -- this task-owned fixture carryable to exercise the ownership guard.
        outer.components.inventoryitem.cangoincontainer = true
        G.assert(not bag.components.container:CanTakeItemInSlot(outer, 1))
        inner = Spawn("klbq_singularity")
        G.assert(bag.components.container:GiveItem(inner, 14))
        G.assert(not inner.components.container:CanTakeItemInSlot(outer, 1))
        G.assert(not inner.components.container:CanTakeItemInSlot(bag, 1))
    end)
    check("bag native safe nesting keeps private layout and permanent upgrade", function()
        local eye = Spawn("deerclops_eyeball")
        G.assert(inner.components.trader:AcceptGift(player, eye))
        G.assert(inner._klbq_eyeball:value())
        eq(inner.components.preserver:GetPerishRateMultiplier(), -.1)
        G.assert(inner.components.equippable.equipslot == (G.EQUIPSLOTS.BACK or G.EQUIPSLOTS.BODY))
        eq(#inner.replica.container:GetWidget().slotpos, 14)
        local saved = inner:GetSaveRecord()
        local restored = G.assert(G.SpawnSaveRecord(saved))
        owned[#owned + 1] = restored
        G.assert(restored._klbq_eyeball:value())
        eq(restored.components.container:GetNumSlots(), 14)
    end)
    check("bag carried fixture cleanup", function()
        for i = #owned, 1, -1 do
            if owned[i]:IsValid() then owned[i]:Remove() end
        end
        G.assert(player:IsValid())
    end)
end
