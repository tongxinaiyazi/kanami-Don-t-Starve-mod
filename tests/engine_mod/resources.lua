local G=GLOBAL
local assert=G.assert
function RunKanamiResourceChecks(context)
    local p,check,eq=context.player,context.check,context.eq
    local x,y,z=p.Transform:GetWorldPosition()
    local owned={}
    local function Spawn(name)
        local item=assert(G.SpawnPrefab(name),name)
        owned[#owned+1]=item;item.Transform:SetPosition(x+15,y,z+15)
        return item
    end
    p.components.health:SetInvincible(true);p:AddTag("notarget")
    local boss,spawned,originalLoot= nil,{},nil
    check("terminal shares original identity, stack, art, inventory and save record",function()
        local d=assert(G.require("klbq_resources/api").GetDefinition("terminal_kanami"))
        assert(d.prefab=="klbq_resource_terminal_kanami")
        local t=Spawn(d.prefab)
        assert(t.AnimState:GetBuild()=="klbq_resources_items")
        assert(t.AnimState:IsCurrentAnimation(d.prefab))
        assert(t.components.inventoryitem.atlasname=="images/klbq_resources_items.xml")
        eq(t.components.stackable.maxsize,40)
        t.components.stackable:SetStackSize(3)
        local copy=assert(G.SpawnSaveRecord(t:GetSaveRecord()));owned[#owned+1]=copy
        eq(copy.components.stackable:StackSize(),3)
        assert(p.components.inventory:GiveItem(copy))
        assert(copy.components.inventoryitem.owner==p)
        copy:Remove();t:Remove()
    end)
    check("native crystal craft consumes one terminal and no lunar seed",function()
        local recipe=assert(G.AllRecipes.klbq_crystal)
        assert(recipe.ingredients[1].type=="klbq_resource_terminal_kanami")
        eq(recipe.ingredients[1].amount,1)
        for _,ing in G.ipairs(recipe.ingredients) do
            assert(ing.type~="lunar_seed")
            local item=Spawn(ing.type);item.components.stackable:SetStackSize(ing.amount)
            assert(p.components.inventory:GiveItem(item))
        end
        assert(p.components.builder:DoBuild("klbq_crystal"),"native crystal crafting failed")
        for _,ing in G.ipairs(recipe.ingredients) do assert(not p.components.inventory:Has(ing.type,1),"ingredient not consumed") end
        assert(p.components.inventory:FindItem(function(t)return t.prefab=="klbq_crystal" end))
        assert(not G.string.find(G.STRINGS.RECIPE_DESC.KLBQ_CRYSTAL,"制作",1,true))
    end)
    check("Charlie native generated loot keeps base table and one guaranteed terminal",function()
        boss=Spawn("charlie_boss");boss:StopBrain("klbq_resource_qa");boss.entity:SetCanSleep(false)
        local loot=boss.components.lootdropper
        assert(loot.chanceloottable=="charlie_boss")
        local n=0
        for _,name in G.ipairs(loot:GenerateLoot()) do if name=="klbq_resource_terminal_kanami" then n=n+1 end end
        eq(n,1)
        originalLoot=loot.SpawnLootPrefab
        loot.SpawnLootPrefab=function(self,name,...)
            local item=originalLoot(self,name,...)
            if item then spawned[#spawned+1]=item;owned[#owned+1]=item end
            return item
        end
        G.TheWorld:DoTaskInTime(.5,function()
            -- Finish prefab zero-delay spawn initialization before the test
            -- kills it; otherwise native spawn resets health after the kill.
            boss.sg:GoToState("idle")
            boss.components.health:SetInvincible(false)
            boss.components.health:Kill()
            print("[KANAMI_RESOURCE_DEATH]",boss.sg.currentstate.name,boss.components.health.currenthealth)
        end)
    end)
    G.TheWorld:DoTaskInTime(27,function()
        check("native Charlie death timeline drops exactly one terminal with base rewards",function()
            local terminals,other=0,0
            for _,item in G.ipairs(spawned) do
                if item.prefab=="klbq_resource_terminal_kanami" then terminals=terminals+1 else other=other+1 end
            end
            assert(boss and (not boss:IsValid() or boss.looted),"Charlie native death loot did not run")
            eq(terminals,1);assert(other>0,"original loot was replaced")
        end)
        for _,item in G.ipairs(owned) do if item:IsValid() then item:Remove() end end
        p.components.health:SetInvincible(false);p:RemoveTag("notarget")
        print("[KANAMI_TEST] COMPLETE")
        G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
    end)
end
