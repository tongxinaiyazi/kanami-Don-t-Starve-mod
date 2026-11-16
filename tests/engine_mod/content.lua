-- Development-only real-engine checks. Loaded by the base harness, never by
-- interactive/playtest, void or void_probe modes; no production code imports it.
local G = GLOBAL
local assert, pcall, tostring = G.assert, G.pcall, G.tostring
local ipairs, pairs = G.ipairs, G.pairs

function RunKanamiContentChecks(context)
    if context.mode ~= "base" then return end
    local p, check, eq = context.player, context.check, context.eq
    local x, y, z = p.Transform:GetWorldPosition()

    local function Scoped(name, fn, delay)
        local owned = {}
        local function Track(inst)
            assert(inst ~= nil, "missing native spawned entity")
            owned[#owned + 1] = inst
            return inst
        end
        local function Spawn(name)
            local inst = Track(G.SpawnPrefab(name))
            inst.Transform:SetPosition(x, y, z)
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function Actor(name)
            local inst = Spawn(name)
            if not inst.components.playercontroller then inst:AddComponent("playercontroller") end
            return inst
        end
        local function Finish(action)
          check(name, function()
            local ok, err = pcall(action)
            local cleanupok, cleanuperr = pcall(function()
                -- Items produced by native cooking were not created by Spawn.
                -- Remove every item still belonging to these synthetic actors.
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
            assert(cleanupok, "fixture cleanup: "..tostring(cleanuperr))
          end)
        end
        if delay ~= nil then
            -- EntityScript delivers ordinary Lua event listeners immediately,
            -- but queues SG events for its next real update. Keep actors alive
            -- until a world task verifies that native processing and item drops.
            local ok, verify = pcall(fn, Spawn, Actor, Track)
            if ok then
                G.TheWorld:DoTaskInTime(delay, function() Finish(verify) end)
            else
                Finish(function() G.error(verify, 0) end)
            end
        else
            Finish(function() fn(Spawn, Actor, Track) end)
        end
    end

    Scoped("new content native prefab spawn and animations", function(Spawn)
        for _, name in ipairs({ "klbq_singularity", "klbq_blade", "klbq_crystal", "klbq_omurice",
            "klbq_omurice_spice_garlic", "klbq_omurice_spice_sugar",
            "klbq_omurice_spice_chili", "klbq_omurice_spice_salt" }) do
            local item = Spawn(name)
            assert(item.prefab == name and item.components.inventoryitem, "not an inventory prefab: "..name)
            assert(item.AnimState:IsCurrentAnimation("idle"), "idle animation unavailable: "..name)
        end
    end)

    Scoped("singularity fourteen native slots and real freshness recovery", function(Spawn)
        local bag = Spawn("klbq_singularity")
        local container = bag.components.container
        eq(container.numslots, 14)
        local food = Spawn("berries")
        local perishable = food.components.perishable
        perishable:SetPercent(.5)
        assert(container:GiveItem(food, 1), "bag rejected food")
        assert(food.components.inventoryitem.owner == bag)
        eq(bag.components.preserver:GetPerishRateMultiplier(food), -.1)
        local before = perishable:GetPercent()
        perishable:LongUpdate(480)
        assert(perishable:GetPercent() > before, "native perishable did not recover freshness")
        perishable:SetPercent(.99)
        perishable:LongUpdate(480000)
        eq(perishable:GetPercent(), 1)
        for slot = 2, 14 do assert(container:GiveItem(Spawn("twigs"), slot), "slot rejected: "..slot) end
        assert(container:IsFull(), "native container did not fill fourteen slots")
        assert(not container:CanTakeItemInSlot(Spawn("flint"), 15), "bag exposes a fifteenth slot")
        assert(not container:CanTakeItemInSlot(bag, 1), "bag may nest inside itself")
    end)

    Scoped("singularity native equipment slot and armor coexistence", function(Spawn, Actor)
        local actor,bag,armor=Actor("klbq_kanami"),Spawn("klbq_singularity"),Spawn("armorwood")
        local slot=G.EQUIPSLOTS.BACK or G.EQUIPSLOTS.BODY
        assert(bag.components.equippable.equipslot==slot,"wrong native backpack slot")
        actor.components.inventory:Equip(bag)
        assert(actor.components.inventory:GetEquippedItem(slot)==bag,"backpack equip failed")
        eq(bag.components.container.numslots,14)
        actor.components.inventory:Equip(armor)
        assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.BODY)==armor,"armor equip failed")
        if G.EQUIPSLOTS.BACK then
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.BACK)==bag,"extra slot backpack displaced by armor")
        end
    end)

    Scoped("X native aggro suppression and existing target release", function(Spawn, Actor, Track)
        local actor,victim=Actor("klbq_kanami"),Track(context.target())
        local c=actor.components.klbq_kanami
        victim.components.combat:SetTarget(actor)
        assert(victim.components.combat.target==actor,"fixture did not start with native aggro")
        assert(c:Cast("x"))
        assert(not victim.components.combat:ShouldAggro(actor),"X did not block native aggro")
        assert(victim.components.combat.target==nil,"X retained existing nearby aggro")
        local before=actor.components.health.currenthealth
        actor.components.health:DoDelta(-5);eq(actor.components.health.currenthealth,before-5)
        c.state.deadlines.x_active=nil;c:Tick()
        assert(victim.components.combat:ShouldAggro(actor),"aggro was not restored after X")
    end)

    Scoped("X permits native attacked retaliation and beefalo ShareTarget", function(Spawn, Actor)
        local actor=Actor("klbq_kanami")
        local first,helper=Spawn("beefalo"),Spawn("beefalo")
        first:StopBrain("kanami_retaliation_check");helper:StopBrain("kanami_retaliation_check")
        local c=actor.components.klbq_kanami
        assert(c:Cast("x"))
        assert(not first.components.combat:ShouldAggro(actor),"unprovoked aggro bypassed X")
        first.components.combat:GetAttacked(actor,10)
        assert(first.components.combat.target==actor,"attacked beefalo could not retaliate")
        assert(helper.components.combat.target==actor,"native herd ShareTarget was blocked")
        c:Tick()
        assert(first.components.combat.target==actor and helper.components.combat.target==actor,
            "domain scan cleared attack-induced aggro")
        c.state.deadlines.protect=G.GetTime()+30;c:Protection(true)
        assert(not first.components.combat:ShouldAggro(actor),"revival protection allowed retaliation")
    end)

    Scoped("X native recruitment and other player's follower ownership", function(Spawn, Actor)
        local actor,other=Actor("klbq_kanami"),Actor("wilson")
        local hires={}
        for _,prefab in ipairs({"pigman","bunnyman","rocky"}) do
            local hire=Spawn(prefab);if hire.brain then hire.brain:Stop() end
            hires[#hires+1]=hire
        end
        local reserved=Spawn("pigman");if reserved.brain then reserved.brain:Stop() end
        other.components.leader:AddFollower(reserved)
        assert(actor.components.klbq_kanami:Cast("x"))
        for _,hire in ipairs(hires) do
            assert(hire.components.follower:GetLeader()==actor,"not hired: "..hire.prefab)
            assert(not hire.components.combat:CanTarget(actor),"hire targets its leader: "..hire.prefab)
            eq(hire.components.combat.externaldamagemultipliers:Get(),1)
        end
        assert(reserved.components.follower:GetLeader()==other,"field stole another player's hire")
    end)

    Scoped("blade native damage 51 and two hundred attack uses", function(Spawn, _, Track)
        local blade, victim = Spawn("klbq_blade"), Track(context.target())
        eq(blade.components.weapon:GetDamage(p, victim), 51)
        eq(blade.components.finiteuses.total, 200)
        eq(blade.components.finiteuses:GetUses(), 200)
        blade.components.weapon:OnAttack(p, victim)
        eq(blade.components.finiteuses:GetUses(), 199)
        blade.components.finiteuses:Use(199)
        assert(not blade:IsValid(), "native final use did not remove blade")
    end)

    Scoped("native chef permissions and omurice eaten stats", function(Spawn, Actor)
        for _, tag in ipairs({ "masterchef", "professionalchef", "expertchef" }) do
            assert(p:HasTag(tag), "missing native chef permission: "..tag)
        end
        assert(p.components.foodmemory == nil, "Warly repeat-food penalty leaked into Kanami")
        assert(p.components.eater.preferseatingtags == nil, "Warly cooked-food restriction leaked into Kanami")
        local food = Spawn("klbq_omurice")
        local edible = food.components.edible
        eq(edible.healthvalue, 30); eq(edible.hungervalue, 50); eq(edible.sanityvalue, 70)
        eq(edible:GetHealth(p), 45); eq(edible:GetHunger(p), 75); eq(edible:GetSanity(p), 105)
        -- Native spoilage first, then Kanami's extra positive-gain penalty and
        -- omurice affinity. Spoiled sanity remains the native negative value.
        for _, pair in ipairs({ { .4, 45*G.TUNING.STALE_FOOD_HEALTH*.5, 75*G.TUNING.STALE_FOOD_HUNGER*.5, 0 }, { .1, 0, 3.75, -G.TUNING.SANITY_SMALL } }) do
            food.components.perishable:SetPercent(pair[1])
            eq(edible:GetHealth(p), pair[2])
            eq(edible:GetHunger(p), pair[3])
            eq(edible:GetSanity(p), pair[4])
        end
        food.components.perishable:SetPercent(1)
        local eater = Actor("klbq_kanami")
        eater.components.health:SetVal(1, "kanami_test")
        eater.components.hunger:SetCurrent(0)
        eater.components.sanity:SetCurrent(0)
        assert(eater.components.eater:Eat(food), "native Eater refused omurice")
        eq(eater.components.health.currenthealth, 46)
        eq(eater.components.hunger.current, 75)
        eq(eater.components.sanity.current, 105)
    end)

    for _, cooker in ipairs({ "cookpot", "portablecookpot" }) do
        Scoped(cooker.." native cook save reload and double harvest by another player", function(Spawn, Actor)
            local pot, recipient = Spawn(cooker), Actor("wilson")
            for slot, ingredient in ipairs({ "bird_egg", "bird_egg", "tomato", "potato" }) do
                assert(pot.components.container:GiveItem(Spawn(ingredient), slot), "pot rejected ingredient")
            end
            assert(pot.components.stewer:CanCook(), "native pot did not accept four ingredients")
            pot.components.stewer:StartCooking(p)
            assert(pot.components.stewer:IsCooking(), "native cooking did not start")
            assert(pot.components.stewer.product == "klbq_omurice", "native recipe selected another product")
            local saved = pot.components.stewer:OnSave()
            pot.components.stewer:StopCooking()
            local restored = Spawn(cooker)
            restored.components.stewer:OnLoad(saved)
            restored.components.stewer:LongUpdate(restored.components.stewer:GetTimeToCook() + 1)
            assert(restored.components.stewer:IsDone(), "native LongUpdate did not finish cooking")
            assert(restored.components.stewer:Harvest(recipient), "native Harvest failed")
            local count = 0
            for _, item in ipairs(recipient.components.inventory:FindItems(function(item) return item.prefab == "klbq_omurice" end)) do
                count = count + (item.components.stackable and item.components.stackable:StackSize() or 1)
            end
            eq(count, 2)
            assert(not restored.components.stewer:Harvest(recipient), "empty pot harvested twice")
        end)
    end

    Scoped("ground crystal grants nearby tech and pocketing revokes it", function(Spawn, Actor)
        local actor, crystal = Actor("klbq_kanami"), Spawn("klbq_crystal")
        local builder = actor.components.builder
        local recipe = assert(G.AllRecipes.klbq_ammo_doom)
        builder:EvaluateTechTrees()
        assert(builder.current_prototyper == crystal, "native proximity scan did not select crystal")
        eq(builder.accessible_tech_trees.KLBQ_STRING, 1)
        assert(G.CanPrototypeRecipe(recipe.level, builder.accessible_tech_trees), "nearby crystal did not permit doom tech")
        assert(recipe.nounlock, "doom became permanently learnable")
        builder:UnlockRecipe("klbq_ammo_doom")
        actor.components.inventory:GiveItem(crystal)
        assert(crystal.components.inventoryitem.owner == actor, "crystal pickup failed")
        assert(not crystal:HasTag("prototyper"), "pocket crystal still participates in proximity scan")
        builder:EvaluateTechTrees()
        eq(builder.accessible_tech_trees.KLBQ_STRING, 0)
        assert(not G.CanPrototypeRecipe(recipe.level, builder.accessible_tech_trees), "pocket crystal still provides tech")
        assert(not builder:KnowsRecipe("klbq_ammo_doom"), "doom stayed learned after pickup")
        actor.components.inventory:DropItem(crystal, true)
        crystal.Transform:SetPosition(actor.Transform:GetWorldPosition())
        builder:EvaluateTechTrees()
        eq(builder.accessible_tech_trees.KLBQ_STRING, 1)
        crystal.Transform:SetPosition(x + G.TUNING.RESEARCH_MACHINE_DIST + 2, y, z)
        builder:EvaluateTechTrees()
        eq(builder.accessible_tech_trees.KLBQ_STRING, 0)
    end)

    for _, ammo in ipairs({ "klbq_ammo_heart", "klbq_ammo_fate" }) do
        Scoped(ammo.." non Kanami actual health loss backlash respects native armor", function(Spawn, Actor, Track)
            local actor, gun = Actor("wilson"), Spawn("klbq_finale")
            local armor, victim = Spawn("armorwood"), Track(context.target())
            actor.components.inventory:Equip(gun)
            actor.components.inventory:Equip(armor)
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == gun)
            assert(gun.components.container:GiveItem(Spawn(ammo), 1))
            -- Below 1500 max HP, both normal and critical fate select 300.
            victim.components.health:SetMaxHealth(1000)
            victim.components.health:SetPercent(1)
            local before, targetbefore = actor.components.health.currenthealth, victim.components.health.currenthealth
            local condition, absorption = armor.components.armor.condition, armor.components.armor:GetAbsorption(nil, gun)
            assert(G.require("klbq_kanami/rifle").Shoot(actor, victim), "non Kanami native shot failed")
            local actual = targetbefore - victim.components.health.currenthealth
            eq(actual, ammo == "klbq_ammo_heart" and 50 or 300)
            eq(before - actor.components.health.currenthealth, actual * (1 - absorption))
            assert(armor.components.armor.condition < condition, "backlash bypassed native armor wear")
            assert(not actor.components.health:IsDead(), "armored normal/fate test unexpectedly killed shooter")
        end)
    end

    Scoped("non Kanami doom native death event and normal item drops", function(Spawn, Actor, Track)
        local actor, gun = Actor("wilson"), Spawn("klbq_finale")
        local marker, victim = Spawn("flint"), Track(context.target())
        actor.components.inventory:Equip(gun)
        actor.components.inventory:GiveItem(marker)
        assert(marker.components.inventoryitem.owner == actor)
        assert(gun.components.container:GiveItem(Spawn("klbq_ammo_doom"), 1))
        local deaths = 0
        actor:ListenForEvent("death", function() deaths = deaths + 1 end)
        actor.components.health:SetInvincible(true)
        assert(G.require("klbq_kanami/rifle").Shoot(actor, victim), "non Kanami doom shot failed")
        assert(victim.components.health:IsDead(), "doom target survived")
        assert(actor:IsValid() and actor.components.health:IsDead(), "shooter was removed or survived doom")
        eq(deaths, 1)
        local shotat = G.GetTime()
        G.print("[KANAMI_DEATH_TIMING]", "immediate", "hp", actor.components.health.currenthealth,
            "sg", actor.sg.currentstate.name, "deaths", deaths)
        return function()
            G.print("[KANAMI_DEATH_TIMING]", "after native ticks", "elapsed", G.GetTime() - shotat,
                "valid", actor:IsValid(), "sg", actor.sg and actor.sg.currentstate.name, "deaths", deaths)
            assert(G.GetTime() - shotat >= .2, "death check did not wait for actual engine time")
            assert(actor:IsValid() and actor.components.health:IsDead(), "shooter was removed or resurrected before death validation")
            eq(deaths, 1)
            assert(actor.sg:HasStateTag("dead"), "native death state was not retained after engine ticks")
            assert(gun:IsValid() and gun.components.inventoryitem.owner == nil and not gun:IsInLimbo(), "native death did not drop rifle")
            assert(marker:IsValid() and marker.components.inventoryitem.owner == nil and not marker:IsInLimbo(), "native death did not drop inventory")
        end
    end, .25)
end
