local M = {}
local native = require("prefabs/tree_rock_data")

local names = {
    DEFAULT="其他地区", FOREST_AREA="森林", SAVANNA_AREA="草原", DECIDUOUS_AREA="桦树林",
    MARSH_AREA="沼泽", GRASS_AREA="草地", ROCKY_AREA="矿区", DESERT_AREA="沙漠",
    MOON_AREA="月岛", HERMIT_AREA="寄居蟹岛", GRAVE_AREA="墓地", MOONQUAY_AREA="月码头",
    MUD_AREA="洞穴泥地", CAVERN_AREA="洞穴岩地", GUANO_AREA="蝙蝠洞", ROCKYLAND_AREA="石虾区",
    RUINS_ENTRANCE_AREA="远古遗迹入口", RUINS_AREA="远古遗迹", RUINS_EXTRA_AREA="远古遗迹深处",
    MOON_GROTTO_AREA="月亮洞窟", VENT_AREA="蒸汽喷口", VENT_AREA_SHADOW_RIFT="暗影喷口",
    MUSHROOM_AREA="蘑菇林", SINKHOLE_AREA="落水洞", MUD_MARSH_AREA="地下沼泽", EMPTY_AREA="贫瘠区",
}

function M.Valid(key)
    return type(key) == "string" and native.WEIGHTED_VINE_LOOT[key] ~= nil
end

function M.Name(key)
    return names[key] or key
end

function M.AtPoint(map, x, y, z)
    local id = map:GetTopologyIDAtPoint(x, y, z)
    if not id then return "DEFAULT" end
    local data = ConvertTopologyIdToData(id)
    local key = native.STATIC_LAYOUTS_TO_LOOT_KEY[data.layout_id]
        or native.ROOMS_TO_LOOT_KEY[data.room_id]
        or native.TASKS_TO_LOOT_KEY[data.task_id]
        or "DEFAULT"
    -- Resolve dynamic variants against the source shard, while recording the
    -- region. Growth on an imprinted tile must use this saved variant.
    return native.CheckModifyLootArea(key)
end

function M.List(records)
    local keys, seen = {}, {}
    for key in string.gmatch(records or "", "[A-Z0-9_]+") do
        if M.Valid(key) and not seen[key] then
            keys[#keys+1] = key
            seen[key] = true
        end
    end
    return keys
end

function M.Select(records, key)
    if M.Valid(key) then
        for _, entry in ipairs(M.List(records)) do
            if entry == key then return key end
        end
    end
end

function M.Record(records, selected, key)
    local keys = M.List(records)
    if M.Valid(key) and not M.Select(records, key) then
        keys[#keys+1] = key
        selected = key
    end
    records = table.concat(keys, ",")
    return records, M.Select(records, selected) or keys[1]
end

function M.IsImprintTile(map, x, y)
    return WORLD_TILES.KLBQ_IMPRINT ~= nil and map:GetTile(x, y) == WORLD_TILES.KLBQ_IMPRINT
end

local function TileKey(x, y)
    return x..":"..y
end

function M.GetTile(world, map, x, y)
    return world._klbq_region_tiles ~= nil and M.IsImprintTile(map, x, y)
        and world._klbq_region_tiles[TileKey(x, y)] or nil
end

function M.SetTile(world, map, x, y, key)
    if not M.Valid(key) or not M.IsImprintTile(map, x, y) then return false end
    world._klbq_region_tiles = world._klbq_region_tiles or {}
    world._klbq_region_tiles[TileKey(x, y)] = key
    return true
end

function M.OnTerraform(world, data)
    if world._klbq_region_tiles and data.original_tile ~= data.tile then
        world._klbq_region_tiles[TileKey(data.x, data.y)] = nil
    end
end

function M.SaveTiles(world)
    local copy = {}
    for pos, key in pairs(world._klbq_region_tiles or {}) do
        if type(pos) == "string" and pos:match("^%d+:%d+$") and M.Valid(key) then
            copy[pos] = key
        end
    end
    return next(copy) and copy or nil
end

local function Roll(inst, key)
    local weights = native.WEIGHTED_VINE_LOOT[key]
    if key ~= "DEFAULT" then
        local total = 0
        for _, weight in pairs(weights) do total = total + weight end
        for _, modifier in pairs(native.EXTRA_LOOT_MODIFIERS) do
            if modifier.test_fn(inst) then
                weights = MergeMapsAdditively(FunctionOrValue(modifier.loot, inst, total), weights)
            end
        end
    end
    return weighted_random_choices(weights, 5)
end

local function WithRegion(world, field, region, fn, ...)
    local previous = world[field]
    world[field] = region
    local ok, result = pcall(fn, ...)
    world[field] = previous
    if not ok then error(result, 0) end
    return result
end

function M.InstallTrees(env)
    local G = env.GLOBAL
    env.AddPrefabPostInit("world", function(world)
        if not world.ismastersim then return end
        world:AddComponent("klbq_regiontiles")
    end)
    env.AddPrefabPostInit("tree_rock_seed", function(seed)
        if not G.TheWorld.ismastersim then return end
        local deploy = seed.components.deployable
        local old = deploy.ondeploy
        deploy.ondeploy = function(inst, pt, ...)
            local world = G.TheWorld
            local map = world.Map
            local tx, ty = map:GetTileCoordsAtPoint(pt:Get())
            return WithRegion(world, "_klbq_planting_region", M.GetTile(world, map, tx, ty), old, inst, pt, ...)
        end
    end)
    env.AddPrefabPostInit("tree_rock_sapling", function(inst)
        if not G.TheWorld.ismastersim then return end
        inst._klbq_planted_region = G.TheWorld._klbq_planting_region
        local push = inst.PushEvent
        inst.PushEvent = function(self, event, data, ...)
            if event == "timerdone" and data and data.name == "grow" and self._klbq_planted_region then
                -- Keep the sapling's snapshot available only during native
                -- growth, which spawns the new tree and calls growfromseed.
                return WithRegion(G.TheWorld, "_klbq_growing_region", self._klbq_planted_region, push, self, event, data, ...)
            end
            return push(self, event, data, ...)
        end
        local save, load = inst.OnSave, inst.OnLoad
        inst.OnSave = function(self, data, ...)
            data.klbq_planted_region = self._klbq_planted_region
            if save then return save(self, data, ...) end
        end
        inst.OnLoad = function(self, data, ...)
            self._klbq_planted_region = data and M.Valid(data.klbq_planted_region) and data.klbq_planted_region or nil
            if load then return load(self, data, ...) end
        end
    end)
    for _, prefab in ipairs({"tree_rock1_short", "tree_rock2_short"}) do
        env.AddPrefabPostInit(prefab, function(inst)
            if not G.TheWorld.ismastersim then return end
            local old = inst.growfromseed
            inst.growfromseed = function(self)
                old(self)
                local key = G.TheWorld._klbq_growing_region
                if key and not self.vine_loot then
                    -- Native one-time vine initialization, before the next-tick fallback.
                    self:OnLoad({vine_loot=Roll(self, key)})
                end
            end
        end)
    end
end

return M
