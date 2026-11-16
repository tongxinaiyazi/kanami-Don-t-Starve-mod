-- Development-only checks against real DST entities and components. The base
-- harness imports this file; production code and interactive modes do not.
local G = GLOBAL
local assert, pcall, tostring = G.assert, G.pcall, G.tostring
local ipairs, pairs, math = G.ipairs, G.pairs, G.math

function RunKanamiBalanceChecks(context)
    if context.mode ~= "base" then return end
    local p, check, eq = context.player, context.check, context.eq
    local x, y, z = p.Transform:GetWorldPosition()

    local function Scoped(name, fn, delay)
        local owned, seen = {}, {}
        local function Track(inst)
            assert(inst ~= nil, "native balance fixture failed to spawn")
            if not seen[inst] then seen[inst] = true;owned[#owned + 1] = inst end
            return inst
        end
        local function Spawn(prefab)
            local inst = Track(G.SpawnPrefab(prefab))
            inst.Transform:SetPosition(x, y, z)
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function Actor()
            local actor = Spawn("klbq_kanami")
            if not actor.components.playercontroller then actor:AddComponent("playercontroller") end
            local c = assert(actor.components.klbq_kanami)
            c.savedmask = actor.Physics:GetCollisionMask()
            -- Every assertion uses its own clear land point: other synthetic
            -- players at the harness origin must not invalidate a safe C exit.
            for dx = -24, 24, 4 do
                for dz = -24, 24, 4 do
                    local ax, az = x + dx, z + dz
                    actor.Physics:Teleport(ax, 0, az)
                    if c:SafePoint(ax, 0, az) then return actor end
                end
            end
            G.error("no clear land point for native balance actor", 0)
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
                            local active = inst.components.inventory:GetActiveItem()
                            if active and active:IsValid() then active:Remove() end
                        end
                    end
                    for i = #owned, 1, -1 do
                        if owned[i]:IsValid() then owned[i]:Remove() end
                    end
                end)
                assert(ok, tostring(err))
                assert(cleanupok, "balance fixture cleanup: "..tostring(cleanuperr))
            end)
        end
        if delay == nil then
            Finish(function() fn(Spawn, Actor, Track) end)
        else
            local ok, verify = pcall(fn, Spawn, Actor, Track)
            if ok then G.TheWorld:DoTaskInTime(delay, function() Finish(verify) end)
            else Finish(function() G.error(verify, 0) end) end
        end
    end

    local function Dry(actor)
        local moisture = actor.components.moisture
        moisture:DoDelta(-moisture:GetMoisture())
        eq(moisture:GetMoisture(), 0)
    end
    local function NormalizeTerrain(actor)
        -- Set native fixture coefficients; never replace the locomotor getter.
        local loco = actor.components.locomotor
        loco.groundspeedmultiplier = 1
        loco.tempgroundspeedmultiplier = nil
        loco.throttle = 1
    end
    local function Upgrade(Spawn, actor, bag)
        local eye = Spawn("deerclops_eyeball")
        eye.components.stackable:SetStackSize(2)
        actor.components.inventory:GiveItem(eye)
        assert(bag.components.trader:AcceptGift(actor, eye), "native Trader refused eyeball")
        eq(eye.components.stackable:StackSize(), 1)
        assert(bag._klbq_eyeball:value(), "upgrade net_bool stayed false")
        assert(not bag.components.trader:AcceptGift(actor, eye), "upgrade accepted a second eye")
        eq(eye.components.stackable:StackSize(), 1)
    end
    local function OceanPoint(actor)
        local ax, _, az = actor.Transform:GetWorldPosition()
        local map = G.TheWorld.Map
        for radius = 8, 2048, 8 do
            for step = 0, 15 do
                local angle = step * math.pi / 8
                local ox, oz = ax + radius * math.cos(angle), az + radius * math.sin(angle)
                if map:IsInMapBounds(ox, 0, oz) and map:IsOceanTileAtPoint(ox, 0, oz)
                    and not map:IsInvalidTileAtPoint(ox, 0, oz) then return ox, 0, oz end
            end
        end
        G.error("base test world has no accessible ocean fixture within 2048 units", 0)
    end
    local function HasOceanPath(actor)
        local caps = actor.components.locomotor.pathcaps
        return caps ~= nil and caps.allowocean == true
    end

    Scoped("balance native base 150 percent C flat fifty and X flat twenty", function(_, Actor)
        local actor = Actor()
        local c, loco = actor.components.klbq_kanami, actor.components.locomotor
        Dry(actor);NormalizeTerrain(actor)
        eq(loco:GetSpeedMultiplier(), 1.5)
        assert(c:ToggleString());eq(loco:GetSpeedMultiplier(), 2)
        assert(c:Cast("x"));eq(loco:GetSpeedMultiplier(), 2.2)
        loco:SetExternalSpeedMultiplier(actor, "klbq_balance_existing", 1.3)
        c:Tick();eq(loco:GetSpeedMultiplier(), 2.65)
        -- Repeated field refreshes must not stack the synchronized +.2 ratio.
        for _ = 1, 4 do c:Tick();eq(loco:GetSpeedMultiplier(), 2.65) end
        c.state.deadlines.x_active = nil;c:Tick()
        eq(loco:GetSpeedMultiplier(), 2.45)
        assert(c:ToggleString());eq(loco:GetSpeedMultiplier(), 1.95)
        loco:RemoveExternalSpeedMultiplier(actor, "klbq_balance_existing")
        eq(loco:GetSpeedMultiplier(), 1.5)
    end)

    Scoped("balance native tiny moisture blocks C and halves the complete speed", function(_, Actor)
        local actor = Actor()
        local c, m, loco = actor.components.klbq_kanami, actor.components.moisture, actor.components.locomotor
        Dry(actor);NormalizeTerrain(actor)
        m:DoDelta(.01)
        assert(m:GetMoisture() > 0 and m:GetMoisture() < .02, "native tiny moisture was lost")
        assert(not c:ToggleString(), "positive moisture allowed C entry")
        eq(loco:GetSpeedMultiplier(), .75)
        assert(actor._klbq_wet:value(), "native moisturedelta did not synchronize wetness")
        Dry(actor);assert(c:ToggleString());eq(loco:GetSpeedMultiplier(), 2)
        m:DoDelta(.01)
        assert(c.state.string, "getting wet forcibly ended an existing C")
        eq(loco:GetSpeedMultiplier(), 1)
        assert(c:ToggleString(), "wetness prevented a safe C exit")
        eq(loco:GetSpeedMultiplier(), .75)
        Dry(actor);eq(loco:GetSpeedMultiplier(), 1.5)
    end)

    Scoped("balance Z independent cost retains one hundred fifty per real minute", function(_, Actor)
        local actor = Actor()
        local c, modifiers = actor.components.klbq_kanami, actor.components.sanity.externalmodifiers
        local before = modifiers:Get()
        assert(c:Cast("z"))
        eq(modifiers:Get(), before)
        local initial=actor.components.sanity.current
        c:OnUpdate(60);eq(initial-actor.components.sanity.current,150)
        c:Tick();eq(modifiers:Get(), before)
        assert(c:Cast("z"));eq(modifiers:Get(), before)
    end)

    Scoped("balance native temperature cold hot times two and burning times one point five", function(_, Actor)
        local actor = Actor()
        local c, h, t = actor.components.klbq_kanami, actor.components.health, actor.components.temperature
        Dry(actor)
        h:SetCurrentHealth(75);t:SetTemperature(-20)
        t:OnUpdate(1)
        assert(t.current < 0, "temperature fixture thawed before its native damage tick")
        eq(75 - h.currenthealth, t.hurtrate * 2)
        h:SetCurrentHealth(75);t:SetTemperature(t.overheattemp + 20)
        t:OnUpdate(1)
        assert(t.current > t.overheattemp, "temperature fixture cooled before its native damage tick")
        eq(75 - h.currenthealth, (t.overheathurtrate or t.hurtrate) * 2)
        t:SetTemperature(20);h:SetCurrentHealth(75)
        eq(h:GetFireDamageScale(), 1)
        h:DoFireDamage(4, nil, true)
        eq(h.currenthealth, 69)
        h:DoDelta(-4, false, "dragonfly");eq(h.currenthealth, 65)
        h:DoDelta(4, true, "hot");eq(h.currenthealth, 69)
        assert(c:ToggleString())
        h:DoDelta(-10, true, "cold");eq(h.currenthealth, 65)
        h:DoFireDamage(4, nil, true);eq(h.currenthealth, 63.8)
        c.state.deadlines.protect = G.GetTime() + 30;c:Protection(true)
        h:DoDelta(-100, true, "hot");eq(h.currenthealth, 63.8)
        h:DoDelta(1, true, "fire");eq(h.currenthealth, 64.8)
    end)

    Scoped("balance native ordinary bag no immunity upgrade rain heat electricity and ocean", function(Spawn, Actor)
        local actor, bag = Actor(), Spawn("klbq_singularity")
        -- Native Drownable intentionally starts enabled=nil and schedules its
        -- first enable with DoTaskInTime(0), after character setup. Verify the
        -- actual post-setup component rather than testing its loading grace.
        return function()
        assert(actor.components.drownable.enabled == true, "native drownable post-setup enable did not run")
        assert(not actor.components.health:IsInvincible(), "ocean fixture has native invincibility")
        local c, inv, t = actor.components.klbq_kanami, actor.components.inventory, actor.components.temperature
        Dry(actor)
        local winter, summer = t:GetInsulation()
        eq(inv:GetWaterproofness(), 0);assert(not inv:IsInsulated())
        assert(inv:Equip(bag));assert(c:ToggleString())
        assert(not c:CanStringWaterWalk() and not HasOceanPath(actor))
        assert(not actor._klbq_waterwalk:value())
        local sx, sy, sz = actor.Transform:GetWorldPosition()
        local ox, oy, oz = OceanPoint(actor)
        actor.Physics:Teleport(ox, oy, oz)
        assert(actor.components.drownable:IsOverWater(), "ocean fixture is safe native land/platform")
        assert(actor.components.drownable:ShouldDrown(), "ordinary string/bag suppressed native drowning")
        actor.Physics:Teleport(sx, sy, sz)
        Upgrade(Spawn, actor, bag)
        eq(bag.components.waterproofer:GetEffectiveness(), 1)
        local value, kind = bag.components.insulator:GetInsulation()
        eq(value, 240);assert(kind == G.SEASONS.SUMMER)
        eq(inv:GetWaterproofness(), 1);assert(inv:IsInsulated())
        local upgradedwinter, upgradedsummer = t:GetInsulation()
        eq(upgradedwinter, winter);eq(upgradedsummer, summer + 240)
        assert(c:CanStringWaterWalk() and HasOceanPath(actor))
        assert(actor._klbq_waterwalk:value(), "worn upgrade did not immediately synchronize water walking")
        actor.Physics:Teleport(ox, oy, oz)
        assert(actor.components.drownable:IsOverWater())
        assert(not actor.components.drownable:ShouldDrown(), "upgraded equipped C did not suppress ocean drowning")
        assert(inv:Unequip(bag.components.equippable.equipslot) == bag)
        local rx, ry, rz = actor.Transform:GetWorldPosition()
        eq(rx, sx);eq(ry, sy);eq(rz, sz)
        assert(not c:CanStringWaterWalk() and not HasOceanPath(actor))
        assert(not actor._klbq_waterwalk:value())
        eq(inv:GetWaterproofness(), 0);assert(not inv:IsInsulated())
        local finalwinter, finalsummer = t:GetInsulation()
        eq(finalwinter, winter);eq(finalsummer, summer)
        actor.Physics:Teleport(ox, oy, oz)
        assert(actor.components.drownable:ShouldDrown(), "unequipping left permanent native drowning immunity")
        actor.Physics:Teleport(sx, sy, sz)
        end
    end, .1)

    Scoped("balance native upgraded bag save record and loaded C equipment synchronization", function(Spawn, Actor, Track)
        local actor, bag = Actor(), Spawn("klbq_singularity")
        Dry(actor);Upgrade(Spawn, actor, bag)
        local food = Spawn("berries")
        food.components.perishable:SetPercent(.4)
        assert(bag.components.container:GiveItem(food, 14))
        assert(actor.components.inventory:Equip(bag))
        assert(actor.components.klbq_kanami:ToggleString())
        local state = actor.components.klbq_kanami:OnSave()
        local record = bag:GetSaveRecord()
        local restored = Track(G.SpawnSaveRecord(record))
        for _, item in pairs(restored.components.container.slots) do Track(item) end
        local loaded = Actor()
        loaded.components.klbq_kanami:OnLoad(state)
        assert(loaded.components.inventory:Equip(restored))
        return function()
            local c = loaded.components.klbq_kanami
            assert(c.state.string and c:CanStringWaterWalk())
            assert(loaded._klbq_waterwalk:value() and HasOceanPath(loaded))
            assert(restored._klbq_eyeball:value())
            assert(not restored.components.trader:AbleToAccept(Spawn("deerclops_eyeball"),loaded),
                "reloaded upgrade accepted another eye")
            eq(loaded.components.inventory:GetWaterproofness(), 1)
            assert(loaded.components.inventory:IsInsulated())
            local value, kind = restored.components.insulator:GetInsulation()
            eq(value, 240);assert(kind == G.SEASONS.SUMMER)
            local restoredfood = assert(restored.components.container:GetItemInSlot(14))
            assert(restoredfood.prefab == "berries", "native save record lost container content")
            assert(restoredfood.components.perishable:GetPercent() >= .399, "save load lost food freshness")
            assert(restoredfood.components.inventoryitem.owner == restored)
        end
    end, .25)

    Scoped("balance native automatic respawn protection empties and locks only hands", function(Spawn, Actor, Track)
        local actor, weapon = Actor(), Spawn("klbq_blade")
        local c, inv = actor.components.klbq_kanami, actor.components.inventory
        assert(inv:Equip(weapon))
        c:OnDeath();c.autoreviving = true;c:OnRespawn()
        eq(actor.components.health.currenthealth, 1)
        eq(actor.components.hunger.current, 37.5);eq(actor.components.sanity.current, 200)
        eq(c:Remaining("protect"), 30)
        assert(c:IsProtected() and not c:CanUseHands())
        assert(inv:GetEquippedItem(G.EQUIPSLOTS.HANDS) == nil)
        assert(weapon:IsValid() and weapon.components.inventoryitem.owner == actor)
        assert(inv:GetItemSlot(weapon) ~= nil, "native respawn did not pocket hand equipment")
        assert(not inv:Equip(weapon), "protection allowed HANDS equip")
        assert(inv:Equip(Spawn("armorwood")), "protection blocked BODY equipment")
        assert(inv:Equip(Spawn("footballhat")), "protection blocked HEAD equipment")
        assert(inv:Equip(Spawn("klbq_singularity")), "protection blocked backpack equipment")
        Dry(actor);assert(c:ToggleString());assert(c:ToggleString())
        assert(c:Cast("z") and c:Cast("x"), "hand lock disabled non-hand skills")
        local victim = Track(context.target())
        local ax, ay, az = actor.Transform:GetWorldPosition()
        victim.Physics:Teleport(ax + 1, ay, az)
        actor.sg:GoToState("idle")
        local before = victim.components.health.currenthealth
        assert(not actor.components.combat:CanAttack(victim), "native Combat.CanAttack escaped protection guard")
        actor.components.combat:DoAttack(victim)
        eq(victim.components.health.currenthealth, before)
        c.state.deadlines.protect = G.GetTime() - 1;c:Tick()
        assert(c:CanUseHands() and inv:GetEquippedItem(G.EQUIPSLOTS.HANDS) == nil,
            "expiry failed to unlock hands or automatically re-equipped weapon")
        assert(inv:Equip(weapon), "expired protection still blocked native hand equip")
        actor.sg:GoToState("idle")
        assert(actor.components.combat:CanAttack(victim), "native combat did not recover after protection")
    end)

    Scoped("balance native full inventory keeps respawn weapon equipped and locked", function(Spawn, Actor)
        local actor, weapon = Actor(), Spawn("klbq_blade")
        local c, inv = actor.components.klbq_kanami, actor.components.inventory
        assert(inv:Equip(weapon))
        for slot = 1, inv.maxslots do assert(inv:GiveItem(Spawn("spear"), slot), "could not fill native slot "..slot) end
        -- Occupy the real mouse cursor too, so GiveItem reaches its original
        -- ground-drop branch instead of using the otherwise legitimate cursor.
        assert(inv:GiveItem(Spawn("flint")))
        assert(inv:GetActiveItem() ~= nil and inv:GetOverflowContainer() == nil)
        c:OnDeath();c.autoreviving = true;c:OnRespawn()
        assert(c:IsProtected() and not c:CanUseHands())
        assert(weapon:IsValid() and inv:GetEquippedItem(G.EQUIPSLOTS.HANDS) == weapon
            and weapon.components.inventoryitem.owner == actor,
            "full native inventory lost the protected hand item")
        eq(weapon.components.finiteuses:GetUses(), 200)
    end)
end
