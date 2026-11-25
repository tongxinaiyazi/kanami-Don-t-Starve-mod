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
local TREE_SAPLINGS = {pinecone_sapling=true,lumpy_sapling=true,acorn_sapling=true,
    twiggy_nut_sapling=true,marblebean_sapling=true,moonbutterfly_sapling=true,
    palmcone_sapling=true,tree_rock_sapling=true}
local OTHER_TREES = {marbleshrub=true,tree_rock1=true,tree_rock2=true}
local EXCLUDE = {"INLIMBO","FX","DECOR","burnt","stump"}
local TAGS = {"plant","farm_plant","notreadyforharvest","readyforharvest","tree","marbleshrub","boulder"}
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
    for _,plant in ipairs(TheSim:FindEntities(x,y,z,Rules.DOMAIN_RADIUS,nil,EXCLUDE,TAGS)) do
        local prefab = plant.prefab
        local components = plant.components
        local growable = components.growable
        local tree_stage
        if plant:HasTag("tree") and components.simplemagicgrower then
            tree_stage = components.simplemagicgrower.last_stage
        elseif OTHER_TREES[prefab] and growable and growable.stages then
            tree_stage = #growable.stages
        end
        if plant:IsValid() and (FARM_PLANTS[prefab] or PICKABLES[prefab] or LEGACY_CROPS[prefab]
            or TREE_SAPLINGS[prefab] or tree_stage) then
            current[plant] = true
            local record = Record(owner,state,plant)
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
                elseif TREE_SAPLINGS[prefab] then
                    local timer = components.timer
                    if not record.complete and timer and timer:TimerExists("grow") then
                        record.complete = true
                        -- planted_tree.lua owns the replacement and its seed-growth
                        -- callbacks. Match Timer's native completion event sequence.
                        timer:StopTimer("grow")
                        plant:PushEvent("timerdone",{name="grow"})
                    end
                elseif tree_stage then
                    if growable and growable.magicgrowable ~= false and not record.complete then
                        if growable:GetStage() < tree_stage and now >= record.nextgrowth then
                            record.nextgrowth = now+1
                            growable:DoGrowth()
                        end
                        -- Native magic-growth limits exclude a tree's old/dead stage.
                        record.complete = growable:GetStage() >= tree_stage
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
                        elseif not pickable:CanBeFertilized() then
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
    for plant in pairs(state.plants) do
        if not current[plant] then Release(owner,plant) end
    end
    state.plants = current
end
return M
