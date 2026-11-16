-- Task-world-only native curse checks; caller owns the world and shutdown.
local G = GLOBAL
local assert, pcall, tostring = G.assert, G.pcall, G.tostring
local ipairs = G.ipairs

function RunKanamiCurseChecks(context)
    local check, eq = context.check, context.eq
    local owned = {}
    local x, y, z = context.player.Transform:GetWorldPosition()
    local function Spawn(prefab)
        local inst = G.SpawnPrefab(prefab)
        assert(inst, "curse fixture failed to spawn " .. prefab)
        owned[#owned + 1] = inst
        inst.entity:SetCanSleep(false)
        inst.Transform:SetPosition(x + 4, y, z + 4)
        return inst
    end
    local function Cleanup()
        for _, inst in ipairs(owned) do if inst:IsValid() then inst:Remove() end end
    end
    local function Scenario()
        local player, ordinary = Spawn("klbq_kanami"), Spawn("wilson")
        local token = Spawn("cursed_monkey_token")
        local cursehits = 0
        player:ListenForEvent("monkeycursehit", function() cursehits = cursehits + 1 end)
        check("curse immediate native eligibility and forced inventory rejection", function()
            assert(not player.components.cursable:IsCursable(token))
            assert(ordinary.components.cursable:IsCursable(token))
            player.components.cursable:ForceOntoOwner(token)
            assert(token.components.inventoryitem.owner == nil)
        end)
        check("curse native pending target neither moves nor binds to Kanami", function()
            local tx, ty, tz = token.Transform:GetWorldPosition()
            token.components.curseditem.target = player
            token.components.curseditem.cursed_target = player
            token.components.curseditem:OnUpdate(.1)
            assert(token.components.curseditem.target == nil)
            assert(token.components.curseditem.cursed_target == nil)
            local ax, ay, az = token.Transform:GetWorldPosition()
            eq(ax, tx); eq(ay, ty); eq(az, tz)
            assert(token.components.inventoryitem.owner == nil)
        end)
        check("curse native manual stack pickup never transforms or staggers", function()
            token.components.stackable:SetStackSize(10)
            player.components.inventory:GiveItem(token)
            assert(token.components.inventoryitem.owner == player)
            eq(player.components.cursable.curses.MONKEY or 0, 0)
            eq(cursehits, 0)
            assert(token.components.curseditem.cursed_target == nil)
            assert(not token:HasTag("applied_curse"))
            assert(not token:HasTag("cursed_inventory_item"))
            assert(player._trymonkeychangetask == nil)
        end)
        check("curse native split and drop restore effect for ordinary player", function()
            local split = token.components.stackable:Get(1)
            assert(split ~= token)
            owned[#owned + 1] = split
            assert(G.ACTIONS.DROP.fn(G.BufferedAction(player,nil,G.ACTIONS.DROP,split)))
            assert(split.components.inventoryitem.owner == nil)
            assert(split:HasTag("cursed_inventory_item"))
            ordinary.components.inventory:GiveItem(split)
            eq(ordinary.components.cursable.curses.MONKEY, 1)
            assert(split.components.curseditem.cursed_target == ordinary)
            eq(cursehits, 0)
        end)
        check("curse native reload clears existing appearance and pending transform", function()
            local pending = player:DoPeriodicTask(.1, function() G.error("old curse transformation survived") end)
            player._trymonkeychangetask = pending
            player.components.cursable.curses.MONKEY = 9
            player.monkeyfeet, player.monkeyhands, player.monkeytail = true, true, true
            player:AddTag("MONKEY_CURSE_3")
            player:SetPersistData({ skinner = { monkey_curse = "MONKEY_CURSE_3" } })
            assert(player._trymonkeychangetask == nil)
            assert(player.components.skinner:GetMonkeyCurse() == nil)
            assert(not player:HasTag("MONKEY_CURSE_3"))
            assert(player.monkeyfeet == nil and player.monkeyhands == nil and player.monkeytail == nil)
            eq(player.components.cursable.curses.MONKEY or 0, 0)
            assert(token:IsValid() and token.components.inventoryitem.owner == player)
            eq(cursehits, 0)
        end)
        G.TheWorld:DoTaskInTime(.2, function()
            check("curse next-tick native state remains immune", function()
                assert(player:IsValid())
                assert(not player.components.cursable:IsCursable(token))
                eq(cursehits, 0)
                assert(player._trymonkeychangetask == nil)
                assert(not player:HasTag("MONKEY_CURSE_1") and not player:HasTag("MONKEY_CURSE_3"))
            end)
            check("curse task-world fixture cleanup", Cleanup)
        end)
    end
    local ok, err = pcall(Scenario)
    if not ok then
        check("curse fixture setup", function() G.error(tostring(err)) end)
        check("curse fixture error cleanup", Cleanup)
    end
end
