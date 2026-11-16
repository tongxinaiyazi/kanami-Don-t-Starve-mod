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
    Work(1)
end
