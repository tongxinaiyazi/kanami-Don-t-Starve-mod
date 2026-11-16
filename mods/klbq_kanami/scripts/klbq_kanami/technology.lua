local M={}
local KEY="KLBQ_STRING"

local function DefaultZero(tree)
    if type(tree)=="table" and tree[KEY]==nil then tree[KEY]=0 end
end

function M.Install(env)
    local G=env.GLOBAL
    local TechTree=require("techtree")
    local found=false
    for _,key in ipairs(TechTree.AVAILABLE_TECH) do if key==KEY then found=true;break end end
    if not found then table.insert(TechTree.AVAILABLE_TECH,KEY) end
    -- Current native builder/classified code also supports lowercase fallbacks.
    -- Fill the exported caches so the new tree follows their normal fast path.
    for cache,suffix in pairs({AVAILABLE_TECH_BONUS="_bonus",AVAILABLE_TECH_TEMPBONUS="_tempbonus",
        AVAILABLE_TECH_BONUS_CLASSIFIED="bonus",AVAILABLE_TECH_TEMPBONUS_CLASSIFIED="tempbonus",
        AVAILABLE_TECH_LEVEL_CLASSIFIED="level"}) do
        if TechTree[cache] then TechTree[cache][KEY]=string.lower(KEY)..suffix end
    end
    -- Recipe construction and player_classified registration use AVAILABLE_TECH
    -- dynamically. Backfill existing tables without changing their native levels.
    for _,tree in pairs(G.TECH) do DefaultZero(tree) end
    for _,tree in pairs(G.TUNING.PROTOTYPER_TREES) do DefaultZero(tree) end
    for _,recipe in pairs(G.AllRecipes) do DefaultZero(recipe.level) end
    G.TECH.KLBQ_STRING_ONE=G.TECH.KLBQ_STRING_ONE or TechTree.Create({KLBQ_STRING=1})
    G.TUNING.PROTOTYPER_TREES.KLBQ_STRING=G.TUNING.PROTOTYPER_TREES.KLBQ_STRING or TechTree.Create({KLBQ_STRING=1})
    G.STRINGS.UI.CRAFTING_STATION_FILTERS.KLBQ_STRING="精粹弦能"
    env.AddPrototyperDef("klbq_crystal",{
        icon_atlas="images/klbq_kanami_items.xml",icon_image="klbq_crystal.tex",
        is_crafting_station=true,filter_text=G.STRINGS.UI.CRAFTING_STATION_FILTERS.KLBQ_STRING,
    })
    return G.TECH.KLBQ_STRING_ONE
end

return M
