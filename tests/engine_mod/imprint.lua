local G=GLOBAL
local assert,ipairs=G.assert,G.ipairs
function RunKanamiImprintChecks(context)
    local p,check,eq=context.player,context.check,context.eq
    local x,y,z=p.Transform:GetWorldPosition()
    local owned={}
    local function Spawn(name)
        local t=assert(G.SpawnPrefab(name),name);owned[#owned+1]=t
        t.Transform:SetPosition(x+4,y,z+4);return t
    end
    local function Give(name)
        local t=Spawn(name);assert(p.components.inventory:GiveItem(t));return t
    end
    p.components.health:SetInvincible(true);p:AddTag("notarget")
    p.components.inventory:Open()
    local item=Give("klbq_imprint_tool")
    local c=item.components.klbq_imprint
    local imprint=G.require("klbq_kanami/imprint")
    check("imprint pristine native item has no work actions or finite uses",function()
        assert(item.components.finiteuses==nil)
        eq(item.components.weapon.damage,17)
        for _,a in ipairs({G.ACTIONS.CHOP,G.ACTIONS.MINE,G.ACTIONS.DIG,G.ACTIONS.HAMMER}) do assert(not item.components.tool:CanDoAction(a)) end
        assert(item.AnimState:GetBuild()=="klbq_imprint_tool")
    end)
    check("multitool learns tough only, any remaining durability accepted",function()
        local sample=Give("multitool_axe_pickaxe");sample.components.finiteuses:SetUses(1)
        assert(item.components.trader:AcceptGift(p,sample))
        assert(not sample:IsValid());assert(item.components.tool:CanDoToughWork())
        assert(not item.components.tool:CanDoAction(G.ACTIONS.MINE))
        assert(not item.components.tool:CanDoAction(G.ACTIONS.CHOP))
    end)
    check("inventory imprint native action consumes gold samples once",function()
        for _,name in ipairs({"goldenaxe","goldenpickaxe","goldenshovel"}) do
            local sample=Give(name);sample.components.finiteuses:SetUses(1)
            assert(G.ACTIONS.KLBQ_IMPRINT.fn(G.BufferedAction(p,item,G.ACTIONS.KLBQ_IMPRINT,sample)))
            assert(not sample:IsValid())
            local duplicate=Give(name)
            assert(not G.ACTIONS.KLBQ_IMPRINT.fn(G.BufferedAction(p,item,G.ACTIONS.KLBQ_IMPRINT,duplicate)))
            assert(duplicate:IsValid());duplicate:Remove()
        end
        for _,a in ipairs({G.ACTIONS.CHOP,G.ACTIONS.MINE,G.ACTIONS.DIG}) do eq(item.components.tool:GetEffectiveness(a),1) end
    end)
    check("walrus tusk consumes one and grants cane speed only while held",function()
        assert(p.components.inventory:Equip(item))
        local locomotor=p.components.locomotor
        local normal=locomotor:GetSpeedMultiplier()
        local sample=Give("walrus_tusk")
        sample.components.stackable:SetStackSize(2)
        assert(G.ACTIONS.KLBQ_IMPRINT.fn(G.BufferedAction(p,item,G.ACTIONS.KLBQ_IMPRINT,sample)))
        eq(sample.components.stackable:StackSize(),1)
        eq(item.components.equippable.walkspeedmult,G.TUNING.CANE_SPEED_MULT)
        eq(locomotor:GetSpeedMultiplier(),normal*1.25)
        assert(imprint.Has(item,"speed"))
        assert(not item.components.trader:AcceptGift(p,sample))
        eq(sample.components.stackable:StackSize(),1)
        sample:Remove()
        assert(p.components.inventory:Unequip(G.EQUIPSLOTS.HANDS)==item)
        assert(p.components.inventory:GiveItem(item))
        eq(locomotor:GetSpeedMultiplier(),normal)
    end)
    check("native equip state and independent save record restore flags",function()
        assert(p.components.inventory:Equip(item))
        local copy=assert(G.SpawnSaveRecord(item:GetSaveRecord()));owned[#owned+1]=copy
        for _,key in ipairs(imprint.KEYS) do assert(imprint.Has(copy,key)) end
        assert(imprint.Has(copy,"speed"));eq(copy.components.equippable.walkspeedmult,1.25)
        local fresh=Spawn("klbq_imprint_tool")
        for _,key in ipairs(imprint.KEYS) do assert(not imprint.Has(fresh,key)) end
        copy:Remove();fresh:Remove()
    end)
    check("ground GIVE remains native and distance/hand protection reject without consuming",function()
        local t=Spawn("klbq_imprint_tool");t.Transform:SetPosition(x+1,y,z)
        local sample=Give("goldenaxe")
        assert(G.ACTIONS.GIVE.fn(G.BufferedAction(p,t,G.ACTIONS.GIVE,sample)))
        assert(not sample:IsValid());assert(imprint.Has(t,"chop"))
        local k=p.components.klbq_kanami
        local sample2=Give("goldenpickaxe");k.state.string=true
        assert(not t.components.trader:AcceptGift(p,sample2));assert(sample2:IsValid())
        k.state.string=false;k.state.deadlines.protect=G.GetTime()+30
        assert(not t.components.trader:AcceptGift(p,sample2));assert(sample2:IsValid())
        k.state.deadlines.protect=nil
        t:Remove();sample2:Remove()
    end)
    check("ground terminal accepts native tusk GIVE without tool durability",function()
        local t=Spawn("klbq_imprint_tool");t.Transform:SetPosition(x+1,y,z)
        local sample=Give("walrus_tusk")
        assert(sample.components.finiteuses==nil)
        assert(G.ACTIONS.GIVE.fn(G.BufferedAction(p,t,G.ACTIONS.GIVE,sample)))
        assert(not sample:IsValid() and imprint.Has(t,"speed"))
        t:Remove()
    end)
    check("native chop, dig and mining keep ordinary work and exactly one base reward",function()
        local tree=Spawn("evergreen");tree.components.workable:SetWorkLeft(1)
        assert(G.ACTIONS.CHOP.fn(G.BufferedAction(p,tree,G.ACTIONS.CHOP,item)))
        local sapling=Spawn("sapling")
        assert(G.ACTIONS.DIG.fn(G.BufferedAction(p,sapling,G.ACTIONS.DIG,item)))
        local rock=Spawn("rock1");rock.components.workable:SetWorkLeft(2)
        local drops=0;local old=rock.components.lootdropper.SpawnLootPrefab
        rock.components.lootdropper.SpawnLootPrefab=function(self,name,...)
            local t=old(self,name,...);if t then owned[#owned+1]=t end
            if name=="klbq_resource_base_string" then drops=drops+1 end
            return t
        end
        assert(G.ACTIONS.MINE.fn(G.BufferedAction(p,rock,G.ACTIONS.MINE,item)));eq(drops,0)
        assert(G.ACTIONS.MINE.fn(G.BufferedAction(p,rock,G.ACTIONS.MINE,item)));eq(drops,1)
        assert(item:IsValid())
    end)
    check("native tough-work recoil respects imprint qualification",function()
        local spike=Spawn("charliearena_spike")
        local fresh=Spawn("klbq_imprint_tool")
        assert(spike.components.workable:ShouldRecoil(p,fresh,1))
        assert(not spike.components.workable:ShouldRecoil(p,item,1))
    end)
    check("native boss generation preserves base loot and planned ring quantities",function()
        for _,v in ipairs({{"minotaur",6},{"daywalker",4},{"daywalker2",4}}) do
            local b=Spawn(v[1]);b:StopBrain("klbq_imprint_qa")
            local count=0
            for _,name in ipairs(b.components.lootdropper:GenerateLoot()) do
                if name=="klbq_resource_topology_ring" then count=count+1 end
            end
            eq(count,v[2]);b:Remove()
        end
    end)
    check("native material crafts and terminal craft spend exact ingredients",function()
        for _,v in ipairs({{"klbq_resource_base_string",8},{"klbq_resource_tracing_plate",1},{"klbq_resource_topology_ring",2},{"klbq_imprint_tool",1}}) do
            -- Clear only resources created by this fixture before each recipe.
            for _,t in ipairs(owned) do
                if t:IsValid() and t~=item and t.components.inventoryitem and t.components.inventoryitem:GetGrandOwner()==p then t:Remove() end
            end
            local recipe=G.AllRecipes[v[1]]
            for _,ing in ipairs(recipe.ingredients) do
                local t=Give(ing.type);if t.components.stackable then t.components.stackable:SetStackSize(ing.amount) end
            end
            assert(p.components.builder:DoBuild(v[1]),v[1])
            for _,ing in ipairs(recipe.ingredients) do assert(not p.components.inventory:Has(ing.type,1),ing.type) end
            assert(p.components.inventory:Has(v[1],v[2]),v[1].." wrong output quantity")
            local product=p.components.inventory:FindItem(function(t)return t.prefab==v[1] end)
            owned[#owned+1]=product
        end
    end)
    for _,t in ipairs(owned) do if t:IsValid() then t:Remove() end end
    p.components.health:SetInvincible(false);p:RemoveTag("notarget")
    print("[KANAMI_TEST] COMPLETE")
    G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
end
