-- Server-only, bounded care for known vanilla plants. Growth goes through the
-- native stage callbacks, so harvest products, stress and spoil timers survive.
local M = {}
local Rules = require("klbq_kanami/rules")
local FARM_PLANTS = {farm_plant_randomseed=true}
for _,name in ipairs({"carrot","corn","potato","tomato","asparagus","eggplant","pumpkin",
    "watermelon","dragonfruit","durian","garlic","onion","pepper","pomegranate"}) do
    FARM_PLANTS["farm_plant_"..name] = true
end
local PICKABLES = {berrybush=true,berrybush2=true,berrybush_juicy=true,grass=true,sapling=true}
local LEGACY_CROPS = {plant_normal=true,plant_normal_ground=true}
local EXCLUDE = {"INLIMBO","FX","DECOR","burnt"}
local TAGS = {"plant","farm_plant","notreadyforharvest","readyforharvest"}
local records = setmetatable({}, {__mode="k"})
local function WeakKeys() return setmetatable({}, {__mode="k"}) end
local function Release(owner, plant)
    local record = records[plant]
    if record then
        record.owners[owner] = nil
        if next(record.owners) == nil then records[plant] = nil end
    end
end
function M.Remove(owner)
    local state = owner._klbq_garden
    if state then
        for plant in pairs(state.plants) do Release(owner,plant) end
        owner._klbq_garden = nil
    end
end
local function Soil(plant, watered)
    local manager = TheWorld.components.farming_manager
    local map = TheWorld.Map
    if not manager or not map then return end
    local x,y,z = plant.Transform:GetWorldPosition()
    local tx,tz = map:GetTileCoordsAtPoint(x,y,z)
    local key = tx..":"..tz
    if watered[key] then return end
    watered[key] = true
    manager:AddSoilMoistureAtPoint(x,y,z,100)
    local n1,n2,n3 = manager:GetTileNutrients(tx,tz)
    manager:AddTileNutrients(tx,tz,100-n1,100-n2,100-n3)
end
local function Record(owner, state, plant)
    local record = records[plant]
    if record then
        for source,token in pairs(record.owners) do
            if not source:IsValid() or source._klbq_garden ~= token then record.owners[source] = nil end
        end
        if next(record.owners) == nil then record = nil end
    end
    if not record then
        record = {owners=WeakKeys(),complete=false,nextgrowth=0}
        records[plant] = record
    end
    record.owners[owner] = state
    record.complete = record.complete or state.done[plant] == true
    return record
end
function M.Scan(owner)
    if not TheWorld or not TheWorld.ismastersim or not owner:IsValid() then return end
    local now = GetTime()
    local state = owner._klbq_garden
    if not state then
        state = {plants=WeakKeys(),done=WeakKeys(),nextscan=0}
        owner._klbq_garden = state
    end
    if now < state.nextscan then return end
    state.nextscan = now+1
    local x,y,z = owner.Transform:GetWorldPosition()
    local current,watered = WeakKeys(),{}
    local fertilizer
    for _,plant in ipairs(TheSim:FindEntities(x,y,z,Rules.DOMAIN_RADIUS,nil,EXCLUDE,TAGS)) do
        local prefab = plant.prefab
        if plant:IsValid() and (FARM_PLANTS[prefab] or PICKABLES[prefab] or LEGACY_CROPS[prefab]) then
            current[plant] = true
            local record = Record(owner,state,plant)
            local components = plant.components
            local burning = components.burnable and components.burnable:IsBurning()
            if not burning then
                if FARM_PLANTS[prefab] then
                    Soil(plant,watered)
                    local tendable = components.farmplanttendable
                    if tendable then tendable:TendTo(owner) end
                    local growable = components.growable
                    local stage = growable and growable:GetCurrentStageData()
                    if stage and (stage.name == "full" or stage.name == "rotten") then record.complete = true end
                    if not record.complete and growable and stage and now >= record.nextgrowth
                        and (stage.name == "seed" or stage.name == "sprout" or stage.name == "small" or stage.name == "med") then
                        record.nextgrowth = now+1
                        -- Night pausing is lifted just for this native growth step;
                        -- the plant's normal day/night watcher remains in charge.
                        growable:Resume()
                        growable:DoGrowth()
                        -- Ordinary planted seeds replace their entity at germination.
                        -- Let the next bounded scan care for the native replacement;
                        -- do not touch components that the old seed has removed.
                        if plant:IsValid() then
                            stage = growable:GetCurrentStageData()
                            record.complete = stage and (stage.name == "full" or stage.name == "rotten") or false
                        end
                    end
                elseif LEGACY_CROPS[prefab] then
                    local crop = components.crop
                    if crop and not record.complete then
                        crop:Mature()
                        record.complete = crop:IsReadyForHarvest()
                    end
                else
                    local pickable = components.pickable
                    if pickable and not record.complete then
                        if pickable:CanBePicked() then
                            record.complete = true
                        else
                            if pickable:CanBeFertilized() then
                                fertilizer = fertilizer or SpawnPrefab("poop")
                                if fertilizer then pickable:Fertilize(fertilizer,owner) end
                            end
                            -- A paused winter plant has no active timer. Resume
                            -- only to complete this one native regrowth cycle.
                            if pickable.paused then pickable:Resume() end
                            record.complete = pickable:FinishGrowing() or pickable:CanBePicked() or false
                        end
                    end
                end
            end
            if record.complete then state.done[plant] = true end
        end
    end
    if fertilizer and fertilizer:IsValid() then fertilizer:Remove() end
    for plant in pairs(state.plants) do
        if not current[plant] then Release(owner,plant) end
    end
    state.plants = current
end
return M
