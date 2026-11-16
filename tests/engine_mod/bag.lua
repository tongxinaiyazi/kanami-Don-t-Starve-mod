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
        assert(target._klbq_eyeball:value() and not target.components.trader.enabled)
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
