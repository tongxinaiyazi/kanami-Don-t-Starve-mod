local G = GLOBAL
local assert, ipairs = G.assert, G.ipairs

function RunKanamiInventoryGuardChecks(context)
    local p, check = context.player, context.check
    p.entity:SetCanSleep(false)
    p.sg:GoToState("idle")
    p.components.health:SetInvincible(false)
    p:AddTag("notarget")
    local inventory = p.components.inventory
    local owned = {}
    local function Spawn(name)
        local inst = assert(G.SpawnPrefab(name), name)
        owned[#owned + 1] = inst
        inst.Transform:SetPosition(p.Transform:GetWorldPosition())
        inst.entity:SetCanSleep(false)
        if inst.brain ~= nil then inst:StopBrain() end
        return inst
    end
    local spear, food, bag
    check("native Kanami has strong grip and thief-proof inventory", function()
        assert(p:HasTag("stronggrip") and inventory:IsThiefProof())
        spear = Spawn("spear")
        assert(inventory:GiveItem(spear))
        assert(inventory:Equip(spear))
        assert(spear:HasTag("nosteal"))
    end)
    check("native monkey and otter cannot steal a selected held item", function()
        food = Spawn("meat")
        assert(inventory:GiveItem(food))
        for _, name in ipairs({"monkey", "otter"}) do
            local thief = Spawn(name)
            assert(thief.components.thief ~= nil)
            assert(not thief.components.thief:StealItem(p, food))
            assert(food.components.inventoryitem:GetGrandOwner() == p)
        end
    end)
    check("native carried backpack blocks theft and forced container drops", function()
        bag = Spawn("klbq_singularity")
        assert(inventory:GiveItem(bag))
        assert(inventory:Equip(bag))
        assert(bag.components.container:GiveItem(food, 1))
        assert(bag.components.container:IsThiefProof())
        assert(not Spawn("otter").components.thief:StealItem(bag, food))
        bag.components.container:DropItemBySlot(1)
        bag.components.container:DropEverything()
        assert(bag.components.container:GetItemInSlot(1) == food)
    end)
    check("native forced drop and disarm keep inventory and equipment", function()
        inventory:DropItem(spear, true, true)
        inventory:DropEquipped()
        inventory:DropEverything()
        assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == spear)
        assert(spear.components.inventoryitem.owner == p)
        assert(bag.components.inventoryitem.owner == p)
    end)
    check("native explicit player DROP still works and restores protection", function()
        local action = G.BufferedAction(p, nil, G.ACTIONS.DROP, spear, p:GetPosition())
        action.options.wholestack = true
        assert(G.ACTIONS.DROP.fn(action))
        assert(spear.components.inventoryitem.owner == nil and not spear:HasTag("nosteal"))
        assert(inventory:GiveItem(spear))
        assert(inventory:Equip(spear))
        inventory:DropItem(spear)
        assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == spear)
    end)
    check("native saved inventory restores item protection", function()
        local saved = assert(G.SpawnSaveRecord(spear:GetSaveRecord()))
        owned[#owned + 1] = saved
        assert(inventory:GiveItem(saved))
        assert(saved:HasTag("nosteal") and saved.components.inventoryitem:GetGrandOwner() == p)
    end)
    if G.Prefabs.dst_gi_nahida_weapon_grass then
        local first = #owned + 1
        check("Nahida native giant harvest with free inventory slots keeps every product accessible", function()
            assert(inventory:GetNextAvailableSlot(Spawn("spear")) ~= nil, "fixture has no free inventory slot")
            local scythe = Spawn("dst_gi_nahida_weapon_grass")
            assert(inventory:GiveItem(scythe) and inventory:Equip(scythe))
            local plants, harvested = {}, {}
            for i = 1, 2 do
                local plant = Spawn("farm_plant_carrot")
                local x, y, z = p.Transform:GetWorldPosition()
                plant.Transform:SetPosition(x + i, y, z)
                plant.force_oversized = true
                plant.components.growable:SetStage(4)
                plant.components.growable:DoGrowth()
                plants[i] = plant
            end
            local function Observe(_, data)
                for _, item in ipairs(data.loot or {}) do
                    harvested[#harvested + 1] = item
                    owned[#owned + 1] = item
                end
            end
            p:ListenForEvent("picksomething", Observe)
            assert(G.ACTIONS.NAHIDA_SCYTHE.fn(G.BufferedAction(p, plants[1], G.ACTIONS.NAHIDA_SCYTHE, scythe)))
            p:RemoveEventCallback("picksomething", Observe)
            assert(#harvested == 2 and not plants[1]:IsValid() and not plants[2]:IsValid())
            for _, item in ipairs(harvested) do
                local accessible = item:IsValid() and not item:IsInLimbo()
                inventory:ForEachItem(function(held) if held == item then accessible = true end end)
                assert(accessible, "giant crop became inaccessible after harvesting with free inventory slots")
                if not item:IsInLimbo() then
                    assert(p:GetDistanceSqToInst(item) < 144, "giant crop landed far from the harvesting player")
                end
            end
        end)
        assert(inventory:Equip(spear))
        for i = first, #owned do
            if owned[i]:IsValid() then owned[i]:Remove() end
        end
    end
    local capacitystart = #owned + 1
    check("native full inventory returns cursor item to ground", function()
        for slot = 1, inventory.maxslots do
            if inventory:GetItemInSlot(slot) == nil then
                local filler = Spawn("spear")
                assert(inventory:GiveItem(filler, slot))
            end
        end
        for slot = 1, bag.components.container:GetNumSlots() do
            if bag.components.container:GetItemInSlot(slot) == nil then
                local filler = Spawn("spear")
                assert(bag.components.container:GiveItem(filler, slot))
            end
        end
        local item = Spawn("cutgrass")
        assert(inventory:GiveItem(item))
        assert(inventory:GetActiveItem() == item)
        inventory:ReturnActiveItem()
        assert(inventory:GetActiveItem() == nil)
        assert(item.components.inventoryitem.owner == nil and not item:IsInLimbo())
        local stack = Spawn("cutgrass")
        stack.components.stackable:SetStackSize(3)
        assert(inventory:GiveItem(stack))
        inventory:ReturnActiveItem(nil, true)
        assert(inventory:GetActiveItem() == stack and stack.components.stackable:StackSize() == 3)
        inventory:ReturnActiveItem()
        assert(stack.components.inventoryitem.owner == nil and not stack:IsInLimbo())
        inventory:DropItem(spear)
        assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == spear)
    end)
    check("native oversized harvest survives full inventory and occupied cursor", function()
        local active = Spawn("twigs")
        assert(inventory:GiveItem(active))
        assert(inventory:GetActiveItem() == active)
        local plants = {}
        for i = 1, 2 do
            local plant = Spawn("farm_plant_carrot")
            local x, y, z = p.Transform:GetWorldPosition()
            plant.Transform:SetPosition(x + i, y, z)
            plant.force_oversized = true
            plant.components.growable:SetStage(4)
            plant.components.growable:DoGrowth()
            assert(plant.is_oversized and plant.components.pickable:CanBePicked())
            plants[i] = plant
        end
        local harvested = {}
        local function Observe(_, data)
            for _, item in ipairs(data.loot or {}) do
                harvested[#harvested + 1] = item
                owned[#owned + 1] = item
            end
        end
        p:ListenForEvent("picksomething", Observe)
        if G.Prefabs.dst_gi_nahida_weapon_grass then
            local scythe = Spawn("dst_gi_nahida_weapon_grass")
            scythe.DoScythe(scythe, plants[1], p)
            assert(not plants[2]:IsValid(), "Nahida bulk harvest did not execute")
        end
        if plants[1]:IsValid() then plants[1].components.pickable:Pick(p) end
        if plants[2]:IsValid() then plants[2].components.pickable:Pick(p) end
        p:RemoveEventCallback("picksomething", Observe)
        assert(#harvested == 2, "giant harvest count differs")
        for _, item in ipairs(harvested) do
            assert(item.prefab == "carrot_oversized" and item:IsValid())
            assert(item.components.inventoryitem.owner == nil and not item:IsInLimbo())
        end
        inventory:ReturnActiveItem()
        assert(active.components.inventoryitem.owner == nil and not active:IsInLimbo())
    end)
    check("native trees mature while barren grass stays unfertilized", function()
        local tree, grass = Spawn("evergreen"), Spawn("grass")
        tree.components.growable:SetStage(1)
        grass.components.pickable:MakeBarren()
        local garden = G.require("klbq_kanami/agriculture")
        garden.Remove(p)
        garden.Scan(p)
        assert(tree.components.growable:GetStage() == 2)
        assert(grass.components.pickable:IsBarren() and not grass.components.pickable:CanBePicked())
        garden.Remove(p)
    end)
    check("native giant harvest stays accessible with an empty cursor and full inventory", function()
        local plant = Spawn("farm_plant_carrot")
        plant.force_oversized = true
        plant.components.growable:SetStage(4)
        plant.components.growable:DoGrowth()
        local harvested
        local function Observe(_, data)
            harvested = data.loot and data.loot[1]
        end
        p:ListenForEvent("picksomething", Observe)
        if G.Prefabs.dst_gi_nahida_weapon_grass then
            local scythe = Spawn("dst_gi_nahida_weapon_grass")
            scythe.DoScythe(scythe, plant, p)
        else
            plant.components.pickable:Pick(p)
        end
        p:RemoveEventCallback("picksomething", Observe)
        local giant = assert(harvested, "giant harvest was not produced")
        owned[#owned + 1] = giant
        assert(giant.prefab == "carrot_oversized")
        inventory:ReturnActiveItem()
        assert(giant:IsValid() and not giant:IsInLimbo() and giant.components.inventoryitem.owner == nil)
        assert(inventory:GetActiveItem() == nil)
    end)
    for i = capacitystart, #owned do
        if owned[i]:IsValid() then owned[i]:Remove() end
    end
    if p.components.playercontroller == nil then p:AddComponent("playercontroller") end
    local cases = {
        {"pickaxe", "rock2", G.ACTIONS.MINE, "mine"},
        {"axe", "evergreen", G.ACTIONS.CHOP, "chop"},
        {"shovel", "sapling", G.ACTIONS.DIG, "dig"},
    }
    local function Finish()
        p.components.health:Kill()
        -- Player death is handled by the next stategraph update, after the
        -- health event. Inventory's native death listener is disabled for players.
        G.TheWorld:DoTaskInTime(1, function()
            check("native death drops remain enabled", function()
                assert(p.components.health:IsDead())
                assert(bag.components.inventoryitem.owner == nil)
            end)
            check("inventory guard fixture cleanup", function()
                for i = #owned, 1, -1 do
                    if owned[i]:IsValid() then owned[i]:Remove() end
                end
            end)
            G.print("[KANAMI_TEST] COMPLETE")
            G.TheWorld:DoTaskInTime(1, function() G.c_shutdown(false) end)
        end)
    end
    local function Work(index)
        local case = cases[index]
        if case == nil then Finish();return end
        local tool, target = Spawn(case[1]), Spawn(case[2])
        local workevent, statevisible = false, false
        target.components.workable:SetWorkLeft(10)
        if target.components.pickable ~= nil then target.components.pickable:MakeEmpty() end
        target:ListenForEvent("worked", function() workevent = true end)
        local observe = function(_, data)
            if data ~= nil and data.statename == case[4] then
                statevisible = p._klbq_workarm == true and not p._klbq_hidecarry
            end
        end
        p:ListenForEvent("newstate", observe)
        assert(inventory:GiveItem(tool))
        assert(inventory:Equip(tool))
        local x, y, z = p.Transform:GetWorldPosition()
        target.Transform:SetPosition(x + 1.5, y, z)
        p.sg:GoToState("idle")
        p.components.locomotor:PushAction(G.BufferedAction(p, target, case[3], tool), true)
        G.TheWorld:DoTaskInTime(2, function()
            check("native ordinary " .. case[1] .. " works with visible tool state", function()
                assert(workevent, "native work action did not execute; state=" .. p.sg.currentstate.name
                    .. "; visible=" .. G.tostring(statevisible)
                    .. "; distance=" .. G.tostring(p:GetDistanceSqToInst(target)))
                assert(statevisible, "working tool was hidden")
                assert(inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == tool)
            end)
            p:RemoveEventCallback("newstate", observe)
            p:ClearBufferedAction()
            p.sg:GoToState("idle")
            if target:IsValid() then target:Remove() end
            Work(index + 1)
        end)
    end
    local plant = Spawn("farm_plant_carrot")
    local x, y, z = p.Transform:GetWorldPosition()
    plant.Transform:SetPosition(x + 1.5, y, z)
    plant.force_oversized = true
    plant.components.growable:SetStage(4)
    plant.components.growable:DoGrowth()
    local hand = inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)
    if hand then inventory:Unequip(G.EQUIPSLOTS.HANDS);assert(inventory:GiveItem(hand)) end
    local harvested = {}
    local function Observe(_, data)
        for _, item in ipairs(data.loot or {}) do
            harvested[#harvested + 1] = item
            owned[#owned + 1] = item
        end
    end
    p:ListenForEvent("picksomething", Observe)
    p.components.locomotor:PushAction(G.BufferedAction(p, plant, G.ACTIONS.PICK), true)
    G.TheWorld:DoTaskInTime(2, function()
        p:RemoveEventCallback("picksomething", Observe)
        check("native bare hand giant harvest with free inventory slots preserves nearby product", function()
            assert(not plant:IsValid() and #harvested == 1, "native PICK action did not harvest giant plant")
            local item = harvested[1]
            local accessible = item:IsValid() and not item:IsInLimbo()
            inventory:ForEachItem(function(held) if held == item then accessible = true end end)
            assert(accessible, "manual harvest giant became inaccessible")
            assert(item:IsInLimbo() or p:GetDistanceSqToInst(item) < 144, "manual harvest giant landed far away")
        end)
        for _, item in ipairs(harvested) do if item:IsValid() then item:Remove() end end
        p:ClearBufferedAction()
        p.sg:GoToState("idle")
        Work(1)
    end)
end
