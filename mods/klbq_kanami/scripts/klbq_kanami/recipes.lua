-- Character crafting and shared resource acquisition. Install after technology.
local M={}
function M.Install(env)
    local G=env.GLOBAL
    local Ingredient=G.Ingredient
    local TECH=G.TECH
    local resource_atlas="images/klbq_resources_items.xml"
    local function Resource(key,count)
        return Ingredient("klbq_resource_"..key,count,resource_atlas)
    end
    local function Recipe(name,ingredients,tech,num,filters,extra)
        local config={numtogive=num or 1,builder_tag="klbq_kanami",
            atlas="images/klbq_kanami_items.xml",image=name..".tex"}
        for k,v in pairs(extra or {}) do config[k]=v end
        env.AddRecipe2(name,ingredients,tech,config,filters)
    end
    Recipe("klbq_resource_base_string",{Ingredient("rocks",4),Ingredient("nitre",2)},TECH.SCIENCE_ONE,8,{"CHARACTER","REFINE"},{atlas=resource_atlas})
    Recipe("klbq_resource_tracing_plate",{Ingredient("goldnugget",2),Ingredient("papyrus",1),Ingredient("transistor",1)},TECH.SCIENCE_TWO,1,{"CHARACTER","REFINE"},{atlas=resource_atlas})
    Recipe("klbq_resource_topology_ring",{Ingredient("thulecite",2),Ingredient("nightmarefuel",2)},TECH.SCIENCE_TWO,2,{"CHARACTER","REFINE"},{atlas=resource_atlas})
    Recipe("klbq_finale",{Ingredient("redgem",1),Ingredient("goldnugget",4),Ingredient("boards",2),Ingredient("gears",1),Resource("base_string",4)},TECH.SCIENCE_TWO,1,{"CHARACTER","WEAPONS"})
    Recipe("klbq_ammo_heart",{Ingredient("rocks",4),Ingredient("flint",2),Ingredient("nitre",1)},TECH.SCIENCE_ONE,20,{"CHARACTER","WEAPONS"})
    Recipe("klbq_ammo_fate",{Resource("topology_ring",2),Ingredient("nitre",2)},TECH.SCIENCE_TWO,20,{"CHARACTER","WEAPONS"})
    Recipe("klbq_ammo_doom",{Ingredient("purebrilliance",2),Ingredient("horrorfuel",2),Ingredient("nightmarefuel",6),Ingredient("opalpreciousgem",1)},TECH.KLBQ_STRING_ONE,1,{"CHARACTER","WEAPONS"},{nounlock=true,station_tag="klbq_crystal"})
    Recipe("klbq_crystal",{Resource("terminal_kanami",1),Resource("topology_ring",2),Ingredient("moonrocknugget",12),Ingredient("gears",2)},TECH.SCIENCE_TWO,1,{"CHARACTER","PROTOTYPERS"})
    Recipe("klbq_singularity",{Ingredient("silk",6),Ingredient("goldnugget",2),Ingredient("rope",2),Resource("base_string",4)},TECH.SCIENCE_ONE,1,{"CHARACTER","CONTAINERS"})
    Recipe("klbq_blade",{Ingredient("flint",6),Ingredient("twigs",2),Ingredient("rope",2)},TECH.SCIENCE_ONE,1,{"CHARACTER","WEAPONS"})
    Recipe("klbq_crossbow",{Ingredient("boards",2),Ingredient("silk",4),Ingredient("goldnugget",2),Ingredient("purplegem",1),Resource("base_string",4)},TECH.SCIENCE_TWO,1,{"CHARACTER","WEAPONS"})
    Recipe("klbq_requiem",{Ingredient("flint",8),Ingredient("boards",2),Ingredient("goldnugget",2),Ingredient("rope",2),Resource("base_string",6)},TECH.SCIENCE_ONE,1,{"CHARACTER","WEAPONS"})
    Recipe("klbq_imprint_tool",{Resource("tracing_plate",1),Resource("base_string",4),Ingredient("goldnugget",2),Ingredient("rope",2)},TECH.SCIENCE_TWO,1,{"CHARACTER","TOOLS"})
    Recipe("klbq_region_score",{Resource("topology_ring",2),Resource("tracing_plate",1)},TECH.SCIENCE_TWO,1,
        {"CHARACTER","TOOLS"},{atlas="images/klbq_region_score.xml"})
    Recipe("turf_klbq_imprint",{Resource("tracing_plate",2),Ingredient("cutstone",2),Ingredient("thulecite",1)},TECH.SCIENCE_TWO,2,
        {"CHARACTER","DECOR"},{atlas="images/turf_klbq_imprint.xml"})
    Recipe("klbq_resource_memory_sequence",{Resource("topology_ring",2),Ingredient("dreadstone",2),Resource("tracing_plate",1),
        Ingredient("purplegem",1)},TECH.SCIENCE_TWO,1,{"CHARACTER","REFINE"},{atlas=resource_atlas})
end
return M
