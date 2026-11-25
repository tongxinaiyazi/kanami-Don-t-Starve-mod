-- Native, task-world-only X checks. Every actor, tile edit and scheduled check
-- belongs to this scope; no engine functions or global registries are replaced.
local G = GLOBAL
local assert,pcall,tostring = G.assert,G.pcall,G.tostring
local ipairs,math = G.ipairs,G.math

function RunKanamiGardenChecks(context)
    if context.mode ~= "base" then return end
    local check,eq = context.check,context.eq
    local owned,tasks,restores = {},{},{}
    local finished,problem = false,nil
    local function Cleanup()
        if finished then return end
        finished = true
        for _,task in ipairs(tasks) do task:Cancel() end
        for i=#owned,1,-1 do
            local inst = owned[i]
            if inst:IsValid() then
                local component = inst.components.klbq_kanami
                if component then component:ClearDomain() end
                if inst.components.inventory then
                    for _,item in ipairs(inst.components.inventory:FindItems(function() return true end)) do
                        if item:IsValid() then item:Remove() end
                    end
                end
                inst:Remove()
            end
        end
        for i=#restores,1,-1 do restores[i]() end
    end
    local function After(delay,fn)
        local task = G.TheWorld:DoTaskInTime(delay,function()
            if finished or problem then return end
            local ok,err = pcall(fn)
            if not ok then problem = err end
        end)
        tasks[#tasks+1] = task
    end
    local function Finish()
        local cleanupok,cleanuperr = pcall(Cleanup)
        check("X native garden scope completes and restores fixtures",function()
            assert(not problem,tostring(problem))
            assert(cleanupok,tostring(cleanuperr))
        end)
    end
    local setupok,setuperr = pcall(function()
        local px,_,pz = context.player.Transform:GetWorldPosition()
        local map,manager = G.TheWorld.Map,G.TheWorld.components.farming_manager
        local ax,az
        -- Keep this fixture clear of the other native suites, and avoid touching
        -- pre-existing plants that the actual 12-unit domain would otherwise tend.
        for radius=256,416,16 do
            for step=0,47 do
                local angle=step*math.pi/24
                local x,z=px+radius*math.cos(angle),pz+radius*math.sin(angle)
                local land=true
                for _,offset in ipairs({{0,0},{4,0},{0,4},{-4,0},
                    {-4,-4},{-2,-4},{0,-4},{2,-4},{4,-4},{6,-4},{-4,-2},{-2,-2}}) do
                    local tx,tz=x+offset[1],z+offset[2]
                    if not (map:IsInMapBounds(tx,0,tz) and map:IsVisualGroundAtPoint(tx,0,tz)
                        and map:IsPassableAtPoint(tx,0,tz)) then land=false;break end
                end
                if land then
                    for _,entity in ipairs(G.TheSim:FindEntities(x,0,z,70,nil,{"INLIMBO","FX","DECOR"},
                        {"player","plant","farm_plant","notreadyforharvest","readyforharvest","tree","boulder"})) do
                        local ex,_,ez=entity.Transform:GetWorldPosition()
                        if entity:HasTag("player") or entity.components.farmplanttendable
                            or entity.prefab=="grass" or entity.prefab=="sapling"
                            or entity.prefab=="berrybush" or entity.prefab=="berrybush2"
                            or entity.prefab=="berrybush_juicy" or entity.components.crop
                            or ((entity:HasTag("tree") or entity.prefab=="marbleshrub")
                                and (ex-x)*(ex-x)+(ez-z)*(ez-z)<=16*16) then land=false;break end
                    end
                end
                if land then ax,az=x,z;break end
            end
            if ax then break end
        end
        assert(ax,"no clear native gardening land fixture")
        local function Spawn(prefab,dx,dz)
            local inst=assert(G.SpawnPrefab(prefab),"native gardening prefab missing: "..prefab)
            owned[#owned+1]=inst
            inst.Transform:SetPosition(ax+(dx or 0),0,az+(dz or 0))
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function Player(prefab,dx,dz)
            local inst=Spawn(prefab,dx,dz)
            inst.userid="KANAMI_GARDEN_"..tostring(inst.GUID)
            if not inst.components.playercontroller then inst:AddComponent("playercontroller") end
            return inst
        end
        local tx,tz=map:GetTileCoordsAtPoint(ax,0,az)
        local originaltile=map:GetTile(tx,tz)
        local n1,n2,n3=manager:GetTileNutrients(tx,tz)
        restores[#restores+1]=function()
            map:SetTile(tx,tz,originaltile)
            manager:SetTileNutrients(tx,tz,n1,n2,n3)
        end
        map:SetTile(tx,tz,G.WORLD_TILES.FARMING_SOIL)
        manager:SetTileNutrients(tx,tz,0,0,0)
        local owner,other,ally=Player("klbq_kanami",4,0),Player("klbq_kanami",0,4),Player("wilson",-4,0)
        local c,oc=owner.components.klbq_kanami,other.components.klbq_kanami
        local crop,bush=Spawn("farm_plant_carrot"),Spawn("berrybush",1,0)
        local seed=Spawn("farm_plant_randomseed",0,1)
        local saplings={}
        for _,definition in ipairs({
            {"pinecone_sapling",-4,-4,"evergreen",3},
            {"lumpy_sapling",-2,-4,"evergreen_sparse",3},
            {"acorn_sapling",0,-4,"deciduoustree",3},
            {"twiggy_nut_sapling",2,-4,"twiggytree",3},
            {"marblebean_sapling",4,-4,"marbleshrub",3},
            {"moonbutterfly_sapling",6,-4,"moon_tree",3},
            {"palmcone_sapling",-4,-2,"palmconetree",3},
            {"tree_rock_sapling",-2,-2,nil,2},
        }) do
            local sapling=Spawn(definition[1],definition[2],definition[3])
            saplings[#saplings+1]={inst=sapling,timer=sapling.components.timer,
                x=ax+definition[2],z=az+definition[3],prefab=definition[4],mature=definition[5]}
        end
        -- The ordinary planted-seed prefab must replace itself via native code.
        -- Fix only this fixture's random outcome; the mod leaves randomness intact.
        seed._identified_plant_type="farm_plant_tomato"
        local pickable=assert(bush.components.pickable)
        pickable:MakeEmpty()
        local tended=0
        local tendable=assert(crop.components.farmplanttendable)
        local originaltend=tendable.TendTo
        tendable.TendTo=function(self,doer)
            local result=originaltend(self,doer)
            if result then tended=tended+1 end
            return result
        end
        local function Rate(inst)
            local sanity=inst.components.sanity
            sanity:SetPercent(.5)
            local before=sanity.current
            sanity:Recalc(1)
            return sanity.current-before
        end
        local ownbase,otherbase,allybase=Rate(owner),Rate(other),Rate(ally)
        local ownmod=owner.components.sanity.externalmodifiers:Get()
        local othermod=other.components.sanity.externalmodifiers:Get()
        local allymod=ally.components.sanity.externalmodifiers:Get()
        assert(c:Cast("x"),"real X activation failed")
        for _,sapling in ipairs(saplings) do
            for _,tree in ipairs(G.TheSim:FindEntities(sapling.x,0,sapling.z,.1,nil,{"INLIMBO","FX","DECOR"})) do
                if tree.components.growable then
                    owned[#owned+1]=tree
                    assert(sapling.tree==nil,"sapling produced duplicate trees")
                    sapling.tree=tree
                end
            end
        end
        check("X native planted tree timers preserve original replacements",function()
            for _,sapling in ipairs(saplings) do
                assert(not sapling.inst:IsValid(),sapling.inst.prefab.." did not germinate")
                assert(not sapling.timer:TimerExists("grow"),"native sapling timer was left running")
                local tree=assert(sapling.tree,"native sapling replacement missing")
                if sapling.prefab then assert(tree.prefab==sapling.prefab,"native tree species changed")
                else assert(tree.prefab=="tree_rock1" or tree.prefab=="tree_rock2","native stone tree variation changed") end
            end
        end)
        local seedtended=0
        do
            local plant=assert(seed.grew_into,"ordinary planted seed did not germinate on activation")
            owned[#owned+1]=plant
            local tending=plant.components.farmplanttendable
            local original=tending.TendTo
            tending.TendTo=function(self,doer)
                local result=original(self,doer)
                if result then seedtended=seedtended+1 end
                return result
            end
        end
        check("X native ally sanity plus30 per minute excludes caster",function()
            eq(owner.components.sanity.externalmodifiers:Get(),ownmod)
            eq(other.components.sanity.externalmodifiers:Get(),othermod+.5)
            eq(ally.components.sanity.externalmodifiers:Get(),allymod+.5)
            eq(Rate(owner)-ownbase,0)
            eq(Rate(other)-otherbase,.5)
            eq(Rate(ally)-allybase,.5)
        end)
        assert(oc:Cast("x"),"second real X activation failed")
        check("X native overlapping same-character domains share sanity source",function()
            eq(owner.components.sanity.externalmodifiers:Get(),ownmod+.5)
            eq(other.components.sanity.externalmodifiers:Get(),othermod+.5)
            eq(ally.components.sanity.externalmodifiers:Get(),allymod+.5)
        end)
        oc.state.deadlines.x_active=nil;oc:Tick()
        assert(pickable:CanBePicked(),"native berry bush failed to become harvestable")
        pickable:MakeEmpty() -- no harvest or loot is generated by this fixture.
        local started=G.GetTime()
        After(4.35,function()
            check("X native ordinary planted seed germinates and replacement matures",function()
                assert(not seed:IsValid(),"ordinary planted seed was ignored")
                local plant=assert(seed.grew_into,"native seed did not produce a replacement")
                assert(plant:IsValid() and plant.prefab=="farm_plant_tomato","native seed product changed")
                assert(plant.components.growable:GetCurrentStageData().name=="full","replacement crop did not mature")
                assert(plant.components.pickable:CanBePicked(),"replacement crop is not harvestable")
                -- Season/family still affect native stress. Tending is verified
                -- through actual successful TendTo calls, not a giant-crop claim.
                assert(seedtended>=3,"replacement crop growth stages were not tended")
            end)
            check("X native farm crop tend water and real-time maturity without fertilizer",function()
                assert(G.GetTime()-started>=4.2,"native time did not advance")
                assert(c:IsX(),"domain expired during crop checks")
                assert(crop.components.growable:GetCurrentStageData().name=="full","crop did not mature")
                assert(crop.components.pickable and crop.components.pickable:CanBePicked(),"native crop not harvestable")
                assert(tended>=4,"each native growth stage was not tended")
                assert(not crop:HasTag("farm_plant_killjoy"),"mature crop was advanced into rot")
                assert(manager:IsSoilMoistAtPoint(ax,0,az),"native crop soil was not watered")
                local a,b,d=manager:GetTileNutrients(tx,tz)
                assert(a==0 and b==0 and d==0,"domain replenished depleted soil nutrients")
                assert(not pickable:CanBePicked(),"quarter-second scans refilled harvested bush repeatedly")
                assert(crop._magicgrowthtask==nil,"growth leaked into a deferred magic chain")
            end)
            check("X native planted trees stop at their original mature stages",function()
                for _,sapling in ipairs(saplings) do
                    local tree=assert(sapling.tree,"native sapling replacement missing")
                    assert(tree:IsValid(),"mature tree was removed")
                    eq(tree.components.growable:GetStage(),sapling.mature)
                    assert(not tree:HasTag("magicgrowth"),"domain leaked a native magic growth chain")
                end
            end)
            c.state.deadlines.x_active=nil;c:Tick()
            check("X native last domain exit removes only its sanity source",function()
                eq(owner.components.sanity.externalmodifiers:Get(),ownmod)
                eq(other.components.sanity.externalmodifiers:Get(),othermod)
                eq(ally.components.sanity.externalmodifiers:Get(),allymod)
                assert(owner._klbq_garden==nil and other._klbq_garden==nil,"garden membership leaked after X ended")
            end)
        end)
    end)
    if not setupok then problem=setuperr;Finish();return end
    -- A hard bound also cleans fixtures if a delayed assertion fails.
    G.TheWorld:DoTaskInTime(4.8,Finish)
end
