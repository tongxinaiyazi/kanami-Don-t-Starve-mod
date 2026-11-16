-- Combo-safe native input diagnostics. Damage/defense/healing stay owned by
-- the enabled mods. Assertions concern controller -> SG -> weapon/projectile
-- execution, attribution, durability and cadence; actual HP is only logged.
-- Own actors/items are cleaned up before optional context.done is called.
local G = GLOBAL
local assert, pcall, tostring = G.assert, G.pcall, G.tostring
local ipairs, pairs, math = G.ipairs, G.pairs, G.math

function RunKanamiWeaponInputChecks(context)
    local parent, check, eq = context.player, context.check, context.eq
    local px, _, pz = parent.Transform:GetWorldPosition()
    local centers, pending = {}, 3
    local label = context.label or context.mode or "native combination"

    local function Center()
        local map = G.TheWorld.Map
        for radius = 48, 256, 16 do
            for step = 0, 31 do
                local angle = step * math.pi / 16
                local x, z = px + radius * math.cos(angle), pz + radius * math.sin(angle)
                local clear = #G.TheSim:FindEntities(x, 0, z, 18, {"_combat"}, {"INLIMBO"}) == 0
                for _, prior in ipairs(centers) do
                    if (x - prior[1])^2 + (z - prior[2])^2 < 40^2 then clear = false;break end
                end
                if clear then
                    for _, offset in ipairs({{0,0},{1.5,0},{2.5,0},{-2.5,0},{0,4.2},{0,-4.2},{4.8,0},{8,0},{12,0}}) do
                        local tx, tz = x + offset[1], z + offset[2]
                        if not (map:IsInMapBounds(tx,0,tz) and map:IsVisualGroundAtPoint(tx,0,tz)
                            and map:IsPassableAtPoint(tx,0,tz) and not map:IsGroundTargetBlocked(G.Vector3(tx,0,tz))) then
                            clear = false;break
                        end
                    end
                end
                if clear then centers[#centers + 1] = {x,z};return x,z end
            end
        end
        G.error("no isolated native weapon input land fixture", 0)
    end

    local function Scoped(name, setup, duration)
        local owned, seen, tasks = {}, {}, {}
        local problem, actor, pc, ax, az
        local function Guard(fn)
            return function(...)
                if problem then return end
                local ok, err = pcall(fn, ...)
                if not ok then problem = err end
            end
        end
        local function Track(inst)
            assert(inst, "native input fixture failed to spawn")
            if not seen[inst] then seen[inst] = true;owned[#owned + 1] = inst end
            return inst
        end
        local function Spawn(prefab, dx, dz)
            if ax == nil then ax, az = Center() end
            local inst = Track(G.SpawnPrefab(prefab))
            inst.Transform:SetPosition(ax + (dx or 0), 0, az + (dz or 0))
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function After(delay, fn)
            local task = G.TheWorld:DoTaskInTime(delay, Guard(fn))
            tasks[#tasks + 1] = task
            return task
        end
        local function Actor(weapon_prefab)
            actor = Spawn("klbq_kanami")
            actor.userid = "KANAMI_INPUT_"..tostring(actor.GUID)
            if not actor.components.playercontroller then actor:AddComponent("playercontroller") end
            if not actor.components.playeractionpicker then actor:AddComponent("playeractionpicker") end
            -- Synthetic actors have no OnSetOwner/keyboard phase. Restore the
            -- native living-player action-filter baseline, then use remote RPC
            -- entrypoints: they populate native remote_controls themselves.
            actor.components.playeractionpicker:PushActionFilter(function(_, action)
                return not action.ghost_exclusive
            end, G.ACTION_FILTER_PRIORITIES.default)
            pc = actor.components.playercontroller
            assert(pc.handler == nil and pc.locomotor == actor.components.locomotor,
                "synthetic actor did not get an authority-side native controller")
            assert(pc.classified and pc.classified.iscontrollerenabled, "native classified missing")
            pc.classified.iscontrollerenabled:set(true)
            local weapon = Spawn(weapon_prefab)
            assert(actor.components.inventory:Equip(weapon), "native weapon Equip failed")
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS) == weapon)
            assert(actor.components.klbq_kanami:CanUseHands() and not actor.components.klbq_kanami.state.string)
            return actor, weapon, pc
        end
        local function Victim(dx, dz)
            local target = Spawn("hound", dx, dz)
            -- StopBrain's named reason survives the prefab's first wake and
            -- deferred brain creation. Do not replace damage, aggro, armor,
            -- planar defense, hit callbacks, healing or combat methods.
            target:StopBrain("klbq_native_input_target")
            target.components.combat:SetTarget(nil)
            target.components.locomotor:Stop()
            -- Keep an ordinary native target alive for the full input sequence;
            -- max HP is fixture capacity, not an expected damage calculation.
            target.components.health:SetMaxHealth(10000)
            target.components.health:SetPercent(1)
            return target
        end
        local function PredictWalking()
            local x, _, z = actor.Transform:GetWorldPosition()
            pc.classified.iscontrollerenabled:set(true)
            assert(pc:IsEnabled(), "native controller remained disabled")
            pc.remote_authority = true;pc.remote_predicting = true
            pc:OnRemotePredictWalking(x, z, true, true, nil, nil, false)
            -- Model a previous tick of predicted direct walking, as real F or
            -- mouse attack packets can arrive before these flags have settled.
            pc.directwalking = true;pc.predictwalking = true
        end
        local function RemoteAttack(target, isleftmouse, released)
            PredictWalking()
            pc:OnRemoteAttackButton(target, false, false, isleftmouse or false, released or false)
            assert(pc.attack_buffer and pc.attack_buffer.forced and pc.attack_buffer._predictpos,
                "native attack packet lost its forced predicted-position contract")
            -- Native OnUpdate supplies the action point before PushAction. A
            -- forced action with no point must never be pushed by the fixture.
            pc:OnUpdate(0)
            assert(pc.attack_buffer == nil, "native OnUpdate did not dispatch attack buffer")
            assert(pc.remote_vector.y == 0 or pc.remote_vector.y == 5,
                "predicted walk did not hand off to native action")
        end
        local function LogHP(stage, target)
            G.print("[KANAMI_INPUT_HP]", label, name, stage, target.prefab, target.GUID,
                "hp", target.components.health.currenthealth, "max", target.components.health.maxhealth)
        end
        local function Cleanup()
            for _, task in ipairs(tasks) do task:Cancel() end
            if pc then
                pc.remote_controls[G.CONTROL_ATTACK] = nil
                pc.remote_controls[G.CONTROL_PRIMARY] = nil
                pc.remote_controls[G.CONTROL_SECONDARY] = nil
            end
            if actor and actor:IsValid() then
                actor.components.locomotor:Stop();actor.components.locomotor:Clear()
                local c = actor.components.klbq_kanami
                c.state.deadlines.protect = nil;c.state.string = false
                c:Protection(false);c:ApplyString();c:Sync()
            end
            -- Remove fixture-owned inventory items before their actor. The
            -- parent actor and all of its equipment remain outside this set.
            for _, inst in ipairs(owned) do
                if inst:IsValid() and inst.components.inventory then
                    for _, item in ipairs(inst.components.inventory:FindItems(function() return true end)) do
                        if item:IsValid() then item:Remove() end
                    end
                    local active = inst.components.inventory:GetActiveItem()
                    if active and active:IsValid() then active:Remove() end
                end
            end
            for i = #owned, 1, -1 do if owned[i]:IsValid() then owned[i]:Remove() end end
            assert(parent:IsValid(), "native input fixture removed the parent player")
        end
        local function Finish(verify)
            check(name, function()
                assert(problem == nil, "async native input fixture: "..tostring(problem))
                verify()
            end)
            check(name.." fixture cleanup", Cleanup)
            pending = pending - 1
            if pending == 0 and context.done then context.done() end
        end
        local ok, verify = pcall(setup, Spawn, Actor, Victim, PredictWalking, RemoteAttack, After, Guard, Track, LogHP)
        if not ok then
            Finish(function() G.error(verify, 0) end)
        else
            G.TheWorld:DoTaskInTime(duration, function() Finish(verify) end)
        end
    end

    Scoped("combination crossbow native predicted F continuous launches and release", function(_, Actor, Victim, _, RemoteAttack, After, Guard, Track, LogHP)
        local actor, weapon, pc = Actor("klbq_crossbow")
        local target = Victim(8, 0)
        local launches, hits = {}, 0
        local released, start
        weapon:ListenForEvent("weapononprojectilelaunched", Guard(function(_, data)
            assert(data and data.attacker == actor and data.target == target, "native launch source/target changed")
            local bolt = Track(assert(data.projectile, "native launch omitted its projectile"))
            assert(bolt.prefab == "klbq_crossbow_bolt" and bolt.components.projectile, "native weapon launched the wrong projectile")
            assert(bolt.components.projectile.owner == actor, "native bolt did not retain its shooter")
            launches[#launches + 1] = G.GetTime()
        end))
        target:ListenForEvent("attacked", Guard(function(_, data)
            if data.attacker == actor then
                -- Kanami S1 can emit another native attacked event using the
                -- launch weapon; count actual bolt hits independently of it.
                if data.weapon and data.weapon.prefab == "klbq_crossbow_bolt" then hits = hits + 1 end
            end
        end))
        After(.25, function()
            start = G.GetTime();LogHP("before F", target)
            RemoteAttack(target, false, false)
            assert(actor.sg.currentstate.name == "klbq_crossbow_attack", "predicted F did not enter custom crossbow state")
            eq(#launches, 1)
        end)
        After(1.75, function()
            assert(#launches >= 10, "held native F did not continue launching")
            released = #launches
            pc:OnRemoteAttackButton(nil, false, true, false, true)
            assert(not pc:IsControlPressed(G.CONTROL_ATTACK), "native release retained attack control")
            LogHP("release F", target)
        end)
        return function()
            assert(start and released and #launches == released, "native release did not stop projectile launches")
            assert(actor.sg.currentstate.name ~= "klbq_crossbow_attack", "release retained custom firing state")
            assert(hits > 0, "launched native projectiles never reached the native target")
            for i = 2, #launches do
                local frames = (launches[i] - launches[i - 1]) / G.FRAMES
                assert(frames >= 2.95 and frames <= 4.05, "native launch gap is not three/four frames: "..tostring(frames))
            end
            local mean = (launches[#launches] - launches[1]) / (#launches - 1)
            assert(math.abs(mean - .125) < G.FRAMES / (#launches - 1) + .003, "native stream did not average eight launches/second")
            G.print("[KANAMI_INPUT_CADENCE]", label, #launches, "launches", hits, "native target hits", mean, "mean seconds")
            LogHP("after F release", target)
        end
    end, 2.2)

    Scoped("combination Requiem native predicted F and real remote left click", function(_, Actor, Victim, PredictWalking, RemoteAttack, After, Guard, _, LogHP)
        local actor, sword, pc = Actor("klbq_requiem")
        local target = Victim(1.5, 0)
        local hits, starts = {}, {}
        local initial_uses, after_f
        sword:ListenForEvent("weapononattack", Guard(function(_, data)
            assert(data and data.attacker == actor and data.target == target, "native sword hit source/target changed")
            hits[#hits + 1] = G.GetTime()
        end))
        After(.25, function()
            initial_uses = sword.components.finiteuses:GetUses();starts[1] = G.GetTime()
            LogHP("before F", target)
            RemoteAttack(target, false, true)
            assert(actor.sg.currentstate.name == "klbq_requiem_attack", "native F did not enter Requiem attack")
            assert(actor.sg.statemem.attacktarget == target, "native F lost its attack target")
        end)
        After(.75, function()
            eq(#hits, 1)
            after_f = sword.components.finiteuses:GetUses()
            assert(after_f < initial_uses, "native F weapononattack did not consume durability")
            assert(hits[1] - starts[1] >= .3 - G.FRAMES, "native F hit preceded the attack timeline")
            LogHP("after F", target)
        end)
        After(1.4, function()
            PredictWalking()
            local action
            for _, candidate in ipairs(actor.components.playeractionpicker:GetLeftClickActions(target:GetPosition(), target)) do
                if candidate.action == G.ACTIONS.ATTACK then action = candidate;break end
            end
            assert(action and action.target == target, "native left picker did not offer target ATTACK")
            starts[2] = G.GetTime()
            pc:OnRemoteLeftClick(action.action.code, target:GetPosition(), target, true, 0, false, action.action.mod_name)
            pc:OnUpdate(0)
            assert(actor.sg.currentstate.name == "klbq_requiem_attack", "native remote left click did not enter Requiem attack")
            assert(actor.sg.statemem.attacktarget == target, "native remote left click lost its target")
        end)
        return function()
            eq(#hits, 2)
            assert(after_f and sword.components.finiteuses:GetUses() < after_f, "native left hit did not consume durability")
            assert(starts[2] - starts[1] >= .8, "fixture retried before the normal attack period")
            assert(hits[2] - starts[2] >= .3 - G.FRAMES, "native left hit preceded the attack timeline")
            G.print("[KANAMI_INPUT_DURABILITY]", label, "Requiem F/left", initial_uses, after_f, sword.components.finiteuses:GetUses())
            LogHP("after remote left click", target)
        end
    end, 2.5)

    Scoped("combination Requiem native remote RMB self centered ring", function(_, Actor, Victim, PredictWalking, _, After, Guard, _, LogHP)
        local actor, sword, pc = Actor("klbq_requiem")
        local inside = {Victim(2.5,0), Victim(-2.5,0), Victim(0,4.2), Victim(0,-4.2)}
        local outside, cursor = Victim(4.8,0), Victim(12,0)
        local expected, counts = {}, {}
        for i, target in ipairs(inside) do expected[target] = "inside"..tostring(i) end
        local start, before, after
        sword:ListenForEvent("weapononattack", Guard(function(_, data)
            assert(data and data.attacker == actor, "native sweep changed attacker")
            local target = assert(data.target, "native sweep omitted target")
            assert(expected[target], "native sweep hit a target outside the intended ring: "..tostring(target.prefab))
            assert(actor:GetDistanceSqToInst(target) <= 4.5^2 + .001, "sweep target was outside its radius at release")
            assert(actor.sg.currentstate.name == "klbq_requiem_sweep" and actor.sg.statemem.released,
                "native sweep weapon hit occurred before its release phase")
            counts[target] = (counts[target] or 0) + 1
            G.print("[KANAMI_INPUT_SWEEP_TARGET]", label, expected[target], target.GUID, math.sqrt(actor:GetDistanceSqToInst(target)))
        end))
        local excluded_hits = 0
        for _, target in ipairs({outside, cursor}) do
            target:ListenForEvent("attacked", Guard(function(_, data)
                if data.attacker == actor then excluded_hits = excluded_hits + 1 end
            end))
        end
        After(.25, function()
            PredictWalking()
            local action
            for _, candidate in ipairs(actor.components.playeractionpicker:GetRightClickActions(cursor:GetPosition(), cursor)) do
                if candidate.action == G.ACTIONS.KLBQ_REQUIEM_SWEEP then action = candidate;break end
            end
            assert(action and action.target == nil and action.invobject == sword, "native RMB did not offer self-centered sweep")
            start, before = G.GetTime(), sword.components.finiteuses:GetUses()
            pc:OnRemoteRightClick(action.action.code, cursor:GetPosition(), cursor, 0, true, 0, true, action.action.mod_name)
            pc:OnUpdate(0)
            assert(actor.sg.currentstate.name == "klbq_requiem_sweep", "native RMB did not enter custom sweep state")
            assert(pc.remote_vector.y == 0 or pc.remote_vector.y == 5, "native RMB did not settle predicted walking")
        end)
        After(.75, function()
            assert(G.next(counts) == nil, "native sweep hit before its .6-second windup")
            eq(sword.components.finiteuses:GetUses(), before)
        end)
        After(1.1, function()
            for _, target in ipairs(inside) do
                eq(counts[target] or 0, 1)
                LogHP(expected[target].." after RMB", target)
            end
            eq(excluded_hits, 0)
            after = sword.components.finiteuses:GetUses()
            assert(after < before, "released native sweep did not consume durability")
            LogHP("outside4.8 after RMB", outside);LogHP("cursor12 after RMB", cursor)
        end)
        return function()
            assert(start and after, "native sweep release observation did not complete")
            for _, target in ipairs(inside) do eq(counts[target] or 0, 1) end
            eq(excluded_hits, 0)
            eq(sword.components.finiteuses:GetUses(), after)
            G.print("[KANAMI_INPUT_DURABILITY]", label, "Requiem RMB", before, after,
                "four target weapon events; outside/cursor zero events; actual HP only recorded")
        end
    end, 2.7)
end
