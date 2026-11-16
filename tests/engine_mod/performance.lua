-- Development-only integration checks. This file operates only on synthetic
-- actors in the task-owned base engine test world, never the user's live game.
local G = GLOBAL
local assert, pcall, tostring = G.assert, G.pcall, G.tostring
local ipairs, pairs = G.ipairs, G.pairs

function RunKanamiPerformanceChecks(context)
    if context.mode ~= "base" then return end
    local p, check, eq = context.player, context.check, context.eq
    local x, y, z = p.Transform:GetWorldPosition()

    local function Scoped(name, fn, delay)
        local owned, seen = {}, {}
        local function Track(inst)
            assert(inst ~= nil, "native fixture entity failed to spawn")
            if not seen[inst] then
                seen[inst] = true
                owned[#owned + 1] = inst
            end
            return inst
        end
        local function Spawn(prefab)
            local inst = Track(G.SpawnPrefab(prefab))
            inst.Transform:SetPosition(x, y, z)
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function ActorKanami()
            local actor = Spawn("klbq_kanami")
            if not actor.components.playercontroller then actor:AddComponent("playercontroller") end
            return actor
        end
        local function Finish(action)
            check(name, function()
                local ok, err = pcall(action)
                local cleanupok, cleanuperr = pcall(function()
                    for _, inst in ipairs(owned) do
                        if inst:IsValid() and inst.components.inventory then
                            for _, item in ipairs(inst.components.inventory:FindItems(function() return true end)) do
                                if item:IsValid() then item:Remove() end
                            end
                        end
                    end
                    for i = #owned, 1, -1 do
                        if owned[i]:IsValid() then owned[i]:Remove() end
                    end
                end)
                assert(ok, tostring(err))
                assert(cleanupok, "performance fixture cleanup: "..tostring(cleanuperr))
            end)
        end
        local ok, verify = pcall(fn, Spawn, ActorKanami, Track)
        if not ok then
            Finish(function() G.error(verify, 0) end)
        else
            -- The original brain schedules its own toss action, and the SG
            -- drops rewards at animation frame 12. Keep every fixture alive
            -- across actual engine ticks; do not call these callbacks by hand.
            G.TheWorld:DoTaskInTime(delay, function() Finish(verify) end)
        end
    end

    Scoped("X Pearl native brain SG reward toss and repeated scan limits", function(Spawn, ActorKanami, Track)
        local actor, pearl = ActorKanami(), Spawn("hermitcrab")
        local c = assert(actor.components.klbq_kanami)
        pearl.Transform:SetPosition(x + 8, y, z)
        assert(pearl.brain ~= nil and pearl.sg ~= nil, "native Pearl brain/stategraph missing")
        assert(pearl.components.health == nil, "fixture must preserve vanilla Pearl's lack of health component")
        assert(pearl.components.friendlevels:GetLevel() == 0, "expected a fresh native Pearl")
        -- Native hermitcrab shares task records across instances; a loaded
        -- world's Pearl may have already mutated them. Isolate this synthetic
        -- NPC without changing the world's canonical friendship state.
        local private={}
        for id,task in G.pairs(pearl.components.friendlevels.friendlytasks) do
            local copy={}
            for k,v in G.pairs(task) do copy[k]=v end
            copy.complete=nil;private[id]=copy
        end
        pearl.components.friendlevels:SetFriendlyTasks(private)

        local rewards, rewardseen, tossstates, completions = {}, {}, 0, 0
        local inventory = assert(pearl.components.inventory)
        local nativeGiveItem = inventory.GiveItem
        inventory.GiveItem = function(self, item, ...)
            if item ~= nil and (item.prefab == "hermit_pearl" or item.prefab == "hermit_bundle")
                and not rewardseen[item] then
                rewardseen[item] = true
                rewards[#rewards + 1] = Track(item)
            end
            return nativeGiveItem(self, item, ...)
        end
        pearl:ListenForEvent("newstate", function(_, data)
            if data and data.statename == "tossitem" then tossstates = tossstates + 1 end
        end)
        pearl:ListenForEvent("friend_task_complete", function() completions = completions + 1 end)

        assert(c:Cast("x"), "fresh Kanami could not start the real X ability")
        local started = G.GetTime()
        eq(pearl.components.friendlevels:GetLevel(), 10)
        assert(pearl.components.friendlevels.friendlytasks[3].complete, "native pearl house-task gate was not completed")
        eq(completions, 10)

        G.TheWorld:DoTaskInTime(.5, function()
            check("X Pearl native reward queue survives actual half second", function()
                assert(actor:IsValid() and pearl:IsValid(), "fixture removed before native updates")
                assert(G.GetTime() - started >= .45, "did not advance real engine time")
                eq(pearl.components.friendlevels:GetLevel(), 10)
                local saved = pearl.components.friendlevels:OnSave()
                eq(saved.level, 10)
                assert(pearl.pearlgiven or #saved.queuedrewards > 0, "rewards neither queued nor settled")
            end)
        end)

        return function()
            assert(G.GetTime() - started >= 2.9, "toss check ran before real brain and SG updates")
            eq(pearl.components.friendlevels:GetLevel(), 10)
            eq(pearl._shop_level, 5)
            eq(#pearl.components.friendlevels.queuedrewards, 0)
            assert(pearl.pearlgiven == true, "native reward function did not persist pearlgiven")
            local saved = {}
            pearl.OnSave(pearl, saved)
            assert(saved.pearlgiven == true, "native prefab save omitted pearl limit")
            assert(tossstates > 0, "original brain never entered the original tossitem state")

            local pearls, bundles = 0, 0
            for _, item in ipairs(rewards) do
                assert(item:IsValid(), "native reward vanished")
                assert(item.components.inventoryitem.owner == nil and not item:IsInLimbo(),
                    "reward remained in NPC inventory instead of native SG dropping it")
                if item.prefab == "hermit_pearl" then pearls = pearls + 1 else bundles = bundles + 1 end
            end
            eq(pearls, 1)
            -- Winter's Feast can legitimately add a house reward bundle.
            assert(bundles >= 4, "missing original friendship reward bundles")
            local count = #rewards
            for _ = 1, 120 do c:Tick() end
            eq(#rewards, count)
            eq(completions, 10)
            eq(#pearl.components.friendlevels.queuedrewards, 0)
            assert(pearl.pearlgiven == true, "repeated scans reset vanilla pearl limit")
        end
    end, 12)
end
