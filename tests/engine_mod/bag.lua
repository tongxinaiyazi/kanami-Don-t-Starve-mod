-- Task-owned regression for crafting/equipping the spatial backpack. Actual
-- remote Replica + ContainerWidget:Open are covered by test_bag_client.py.
local G=GLOBAL
local assert,pcall,tostring,ipairs=G.assert,G.pcall,G.tostring,G.ipairs
modimport("bag_ui.lua")
function RunKanamiBagChecks(context)
    local p,check,eq=context.player,context.check,context.eq
    if not p.components.playercontroller then p:AddComponent("playercontroller") end
    if not p.components.playeractionpicker then p:AddComponent("playeractionpicker") end
    -- The parent harness owns its primary player and normal save/shutdown.
    -- Removing that registered actor immediately before shutdown can invalidate
    -- its pending native save. Only remove items created by this fixture.
    local owned={}
    local function Spawn(name)
        local inst=assert(G.SpawnPrefab(name));owned[#owned+1]=inst
        inst.entity:SetCanSleep(false);inst.Transform:SetPosition(p.Transform:GetWorldPosition())
        return inst
    end
    local inv=p.components.inventory
    local bag,restored
    check("bag actual native Builder consumes materials and auto equips fourteen slots",function()
        local recipe=assert(G.GetValidRecipe("klbq_singularity"))
        for _,ing in ipairs(recipe.ingredients) do
            local item=Spawn(ing.type);item.components.stackable:SetStackSize(ing.amount)
            assert(inv:GiveItem(item))
        end
        p:ListenForEvent("builditem",function(_,data)if data.item.prefab=="klbq_singularity" then bag=data.item;owned[#owned+1]=bag end end)
        assert(p.components.builder:DoBuild("klbq_singularity"),"actual native craft failed")
        assert(bag and inv:GetEquippedItem(bag.components.equippable.equipslot)==bag)
        eq(bag.components.container:GetNumSlots(),14)
        local widget=assert(bag.replica.container:GetWidget(),"native replica widget is nil")
        eq(#widget.slotpos,14)
        assert(widget==G.require("containers").params.klbq_singularity.widget)
        for _,ing in ipairs(recipe.ingredients) do assert(not inv:Has(ing.type,1),"native craft did not consume ingredient") end
        assert(bag.components.container:IsOpenedBy(p),"auto equip did not open native container")
    end)
    check("bag native close reopen and both upgrades preserve its private layout",function()
        assert(bag,"craft failed")
        local slot=bag.components.equippable.equipslot
        bag.components.container:Close(p)
        assert(inv:Unequip(slot)==bag);assert(inv:Equip(bag))
        assert(bag.components.container:IsOpenedBy(p))
        local eye=Spawn("deerclops_eyeball");inv:GiveItem(eye)
        assert(bag.components.trader:AcceptGift(p,eye))
        assert(bag._klbq_eyeball:value());eq(#bag.replica.container:GetWidget().slotpos,14)
        local hat=Spawn("minerhat");hat.components.fueled:SetPercent(0);inv:GiveItem(hat)
        for _,right in ipairs({false,true}) do
            local choices=p.components.playeractionpicker:GetUseItemActions(bag,hat,right)
            assert(choices[1] and choices[1].action==G.ACTIONS.GIVE,"native mouse discovery selected STORE instead of GIVE")
        end
        local give=p.components.playeractionpicker:GetUseItemActions(bag,hat,false)[1]
        assert(G.ACTIONS.GIVE.fn(give))
        assert(not hat:IsValid(),"miner hat was not consumed")
        assert(bag._klbq_minerhat:value())
        assert(bag._klbq_light and bag._klbq_light:IsValid(),"equipped upgrade did not create light")
        assert(bag._klbq_light.prefab=="minerhatlight" and bag._klbq_light.entity:GetParent()==p)
        eq(bag._klbq_light.Light:GetRadius(),2.5)
        assert(not bag.components.fueled,"permanent bag light has a fuel cost")
        local light=bag._klbq_light
        assert(inv:Unequip(slot)==bag)
        assert(not light:IsValid() and bag._klbq_light==nil,"unequipped bag kept its light")
        assert(inv:Equip(bag))
        assert(bag._klbq_light and bag._klbq_light:IsValid())
        local extra=Spawn("minerhat");inv:GiveItem(extra)
        assert(not bag.components.trader:AcceptGift(p,extra))
        assert(extra:IsValid() and extra.components.inventoryitem.owner==p,"repeat upgrade consumed hat")
        local food=Spawn("berries");food.components.perishable:SetPercent(.4)
        assert(bag.components.container:GiveItem(food,14))
        local record=bag:GetSaveRecord()
        restored=assert(G.SpawnSaveRecord(record));owned[#owned+1]=restored
        eq(#restored.replica.container:GetWidget().slotpos,14)
        assert(restored._klbq_eyeball:value())
        assert(restored._klbq_minerhat:value() and restored._klbq_light==nil)
        assert(restored.components.container:GetItemInSlot(14).prefab=="berries")
    end)
    check("bag native miner hat first keeps eye upgrade and does not light on ground",function()
        local target=Spawn("klbq_singularity")
        local hat=Spawn("minerhat");inv:GiveItem(hat)
        assert(target.components.trader:AcceptGift(p,hat))
        assert(target._klbq_minerhat:value() and target._klbq_light==nil)
        local eye=Spawn("deerclops_eyeball");inv:GiveItem(eye)
        assert(target.components.trader:AcceptGift(p,eye))
        assert(target._klbq_eyeball:value() and target.components.trader.enabled)
    end)
    check("bag native gemstone stages, guaranteed Dragonfly core and save migration",function()
        local slot=assert(bag).components.equippable.equipslot
        local function Gift(name)
            local item=Spawn(name)
            assert(inv:GiveItem(item))
            local use=p.components.playeractionpicker:GetUseItemActions(bag,item,true)[1]
            assert(use and use.action==G.ACTIONS.GIVE,name.." native input did not choose GIVE")
            assert(G.ACTIONS.GIVE.fn(use),name.." was refused")
            assert(not item:IsValid(),name.." was not consumed")
        end
        for _=1,45 do Gift("redgem") end
        local red=Spawn("redgem");assert(inv:GiveItem(red))
        assert(not bag.components.trader:AcceptGift(p,red) and red:IsValid())
        eq(bag.components.armor:GetAbsorption(),.9)
        for i=1,5 do
            Gift("bluegem")
            eq(bag._klbq_light.Light:GetRadius(),2.5+i*.5)
        end
        local dragonfly=Spawn("dragonfly")
        local count=0
        for _,prefab in ipairs(dragonfly.components.lootdropper:GenerateLoot()) do
            if prefab=="klbq_ember_core" then count=count+1 end
        end
        eq(count,1)
        Gift("klbq_ember_core")
        eq(bag._klbq_light.Light:GetRadius(),5.5)
        local upgraded=assert(G.SpawnSaveRecord(bag:GetSaveRecord()));owned[#owned+1]=upgraded
        assert(upgraded._klbq_nightvision:value() and not upgraded._klbq_light)
        eq(upgraded.components.armor:GetAbsorption(),.9)
        assert(inv:Unequip(slot)==bag and inv:Equip(upgraded))
        eq(upgraded._klbq_light.Light:GetRadius(),5.5)
        assert(inv:Unequip(slot)==upgraded and inv:Equip(bag))
    end)
    check("memory sequence native inventory action and save roundtrip",function()
        local recipe=assert(G.GetValidRecipe("klbq_resource_memory_sequence"))
        eq(recipe.level.SCIENCE,2)
        local builder=p.components.builder
        local portable=assert(G.GetValidRecipe("icebox"))
        local station=assert(G.GetValidRecipe("klbq_ammo_doom"))
        assert(not builder:KnowsRecipe(portable) and not builder:KnowsRecipe(station))
        local sequence=Spawn("klbq_resource_memory_sequence")
        sequence.components.stackable:SetStackSize(2)
        assert(inv:GiveItem(sequence))
        local use=p.components.playeractionpicker:GetInventoryActions(sequence)[1]
        assert(use and use.action.id=="KLBQ_MEMORY_SEQUENCE","native inventory index did not offer use")
        assert(use.action.fn(use))
        eq(sequence.components.stackable:StackSize(),1)
        assert(not use.action.fn(use),"same player consumed another sequence")
        assert(builder:KnowsRecipe(portable) and not builder:KnowsRecipe(station))
        local saved={};p:OnSave(saved)
        assert(saved.klbq_memory_sequence==true)
        -- Directly reload the same flag on the test actor. Native Builder's
        -- own save format continues to carry its learned recipes.
        p._klbq_memory_sequence:set(false)
        assert(not builder:KnowsRecipe(portable))
        p:OnLoad(saved)
        assert(p._klbq_memory_sequence:value() and builder:KnowsRecipe(portable))
    end)
    G.TheWorld:DoTaskInTime(.25,function()
        check("bag native saved upgraded container opens after deferred loading",function()
            assert(restored,"save/load setup failed")
            local slot=restored.components.equippable.equipslot
            inv:Unequip(slot);assert(inv:Equip(restored))
            assert(restored.components.container:IsOpenedBy(p))
            assert(restored._klbq_light and restored._klbq_light:IsValid())
            assert(restored._klbq_light.entity:GetParent()==p)
            eq(restored.replica.container:GetNumSlots(),14)
            assert(restored.replica.container:GetWidget().animbank=="ui_krampusbag_2x8")
        end)
        RunKanamiBagUIChecks(context)
        check("bag fixture cleanup",function()
            for i=#owned,1,-1 do if owned[i]:IsValid() then owned[i]:Remove() end end
            assert(p:IsValid(),"parent harness player was removed before normal save")
        end)
        G.print("[KANAMI_TEST] COMPLETE")
        G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
    end)
end
