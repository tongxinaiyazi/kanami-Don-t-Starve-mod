-- Pure Lua 5.1 rules shared by engine code and executable unit tests.
local M = {}
M.PASSIVE_COOLDOWN = 1.5
M.PASSIVE_HEALTH_FRACTION = .03
M.Z_SANITY_PER_SECOND = 150 / 60
M.SHOT_COOLDOWN = 1.5
local timers = {"passive", "shot", "x", "x_active", "revive", "protect"}
function M.New() return { deadlines = {}, dead = false, string = false, zenabled = false } end
function M.Remaining(s, key, now) return math.max(0, (s.deadlines[key] or 0) - now) end
function M.Ready(s, key, now) return M.Remaining(s, key, now) <= 0 end
function M.Start(s, key, now, seconds) s.deadlines[key] = now + seconds end
function M.Cast(s, key, now)
    if s.dead or (key ~= "z" and key ~= "x") then return false end
    if key == "z" then s.zenabled = not s.zenabled; return true end
    if not M.Ready(s,key,now) then return false end
    M.Start(s, key, now, 60)
    M.Start(s, key.."_active", now, 30)
    return true
end
function M.Death(s, now)
    s.dead = true; s.string = false; s.zenabled = false
    s.deadlines.z_active = nil; s.deadlines.x_active = nil; s.deadlines.protect = nil
    M.Start(s, "revive", now, 60)
end
function M.AutoReviveDue(s, now) return s.dead and s.deadlines.revive ~= nil and M.Ready(s, "revive", now) end
function M.Revive(s, now, automatic)
    s.dead = false; s.deadlines.revive = nil
    if automatic then M.Start(s, "protect", now, 30) else s.deadlines.protect = nil end
end
function M.Save(s, now)
    local data = { version = 2, dead = s.dead, string = s.string, zenabled = s.zenabled, remaining = {} }
    for _, key in ipairs(timers) do
        if s.deadlines[key] ~= nil then data.remaining[key] = M.Remaining(s, key, now) end
    end
    return data
end
function M.Load(data, now)
    local s = M.New()
    if type(data) ~= "table" then return s end
    s.dead = data.dead == true; s.string = data.string == true and not s.dead
    -- Old timed Z buffs expire during this upgrade instead of becoming an
    -- unexpected permanent sanity drain. New toggle saves retain their state.
    s.zenabled = data.version == 2 and data.zenabled == true and not s.dead
    for _, key in ipairs(timers) do
        local n = data.remaining and data.remaining[key]
        if type(n) == "number" and n >= 0 and n < 86400 then M.Start(s,key,now,n) end
    end
    return s
end
function M.Speed(existing, string, allied, wet)
    return (existing * 1.5 + (string and .5 or 0) + (allied and .2 or 0)) * (wet and .5 or 1)
end
M.DOMAIN_RADIUS = 12
-- Native reticuleaoe idle (AnimState scale1.5) has a four-world-unit radius.
function M.DomainScale() return M.DOMAIN_RADIUS/4 end
local fate_fraction = .03
function M.ConfigureFate(value)
    -- Missing settings in existing worlds and invalid overrides use the default.
    fate_fraction = (value == .03 or value == .05 or value == .1 or value == .2) and value or .03
end
function M.Fate(maxhp, crit, z) return (crit and math.max(300,maxhp*fate_fraction) or 300) * (z and 1.5 or 1) end
function M.Snapshot(base, mult, z) return { power = base * mult, zmult = z and 1.5 or 1 } end
function M.Incoming(amount, string, protected, cause)
    if amount >= 0 then return amount end
    if protected then return 0 end
    local environmental = (cause == "cold" or cause == "hot") and 2 or (cause == "fire" and 1.5 or 1)
    return amount * environmental * (string and .2 or 1)
end
return M
