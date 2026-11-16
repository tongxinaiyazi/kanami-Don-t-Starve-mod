local G = GLOBAL
local catalog
local phase = GetModConfigData("phase")
local failed = 0

local function check(label, fn)
    local ok, err = G.pcall(fn)
    print("[RESOURCES_TEST]", ok and "PASS" or "FAIL", label, ok and "" or G.tostring(err))
    if not ok then failed = failed + 1 end
end

local function spawn(definition, quantity, x, z)
    local inst = G.SpawnPrefab(definition.prefab)
    G.assert(inst ~= nil, "spawn failed: " .. definition.prefab)
    inst.Transform:SetPosition(x, 0, z)
    inst.components.stackable:SetStackSize(quantity or 1)
    return inst
end

AddSimPostInit(function()
    if not G.TheWorld.ismastersim then return end
    G.TheWorld:DoTaskInTime(3, function()
        catalog = require("klbq_resources/catalog")
        print("[RESOURCES_TEST] START", phase, G.APP_VERSION)
        local api = require("klbq_resources/api")
        if phase == "reload" then
            local found = {}
            for _, inst in G.pairs(G.Ents) do
                if api.IsResource(inst) then
                    found[inst.prefab] = (found[inst.prefab] or 0) + inst.components.stackable:StackSize()
                end
            end
            for i, definition in G.ipairs(catalog.items) do
                check("world reload " .. definition.key, function()
                    G.assert(found[definition.prefab] == i, definition.prefab .. " count " .. G.tostring(found[definition.prefab]))
                end)
            end
            check("only 20 persistent resource identities", function()
                local count = 0
                for _ in G.pairs(found) do count = count + 1 end
                G.assert(count == 20)
            end)
            print("[RESOURCES_TEST] COMPLETE", phase, failed)
            G.TheWorld:DoTaskInTime(1, function() G.c_shutdown(false) end)
            return
        end

        local portal = G.c_find("multiplayer_portal")
        local x, y, z = 0, 0, 0
        if portal then x, y, z = portal.Transform:GetWorldPosition() end
        local player = G.SpawnPrefab("wilson")
        player.Transform:SetPosition(x+3,0,z+3)
        local chest = G.SpawnPrefab("treasurechest")
        chest.Transform:SetPosition(x+4,0,z+4)
        local forbidden = {"edible","tradable","fuel","finiteuses","equippable","weapon","armor",
                           "perishable","lootdropper","prototyper","combat"}
        for i, definition in G.ipairs(catalog.items) do
            check("native item " .. definition.key, function()
                local item = spawn(definition, 7, x+5, z+5)
                G.assert(item.AnimState:GetBuild() == catalog.BUILD)
                G.assert(item.AnimState:IsCurrentAnimation(definition.prefab))
                G.assert(item.components.stackable.maxsize == 40)
                G.assert(item.components.inventoryitem.atlasname == catalog.ATLAS)
                G.assert(item.components.inventoryitem.imagename == definition.prefab)
                G.assert(item:HasTag("klbq_resource"))
                for _, name in G.ipairs(forbidden) do G.assert(item.components[name] == nil, name) end
                local copy = G.SpawnSaveRecord(item:GetSaveRecord())
                G.assert(copy ~= nil and copy.prefab == item.prefab)
                G.assert(copy.components.stackable:StackSize() == 7)
                G.assert(copy.AnimState:IsCurrentAnimation(definition.prefab))
                copy:Remove()
                player.components.inventory:GiveItem(item)
                G.assert(item.components.inventoryitem.owner == player)
                G.assert(player.components.inventory:RemoveItem(item,true) == item)
                G.assert(chest.components.container:GiveItem(item))
                G.assert(item.components.inventoryitem.owner == chest)
                G.assert(chest.components.container:RemoveItem(item,true) == item)
                G.assert(item.components.inventoryitem.owner == nil)
                item:Remove()
            end)
            -- Persist fixtures with distinct quantities for the second process.
            spawn(definition, i, x+6+(i%5)*1.2, z+6+G.math.floor((i-1)/5)*1.2)
        end

        local definition = catalog.items[1]
        check("same-kind merge", function()
            local a,b=spawn(definition,7,x,z),spawn(definition,5,x,z)
            G.assert(a.components.stackable:Put(b)==nil)
            G.assert(a.components.stackable:StackSize()==12 and not b:IsValid())
            a:Remove()
        end)
        check("overflow and split", function()
            local a,b=spawn(definition,39,x,z),spawn(definition,6,x,z)
            G.assert(a.components.stackable:Put(b)==b)
            G.assert(a.components.stackable:StackSize()==40 and b.components.stackable:StackSize()==5)
            local part=a.components.stackable:Get(9)
            G.assert(part~=a and part.prefab==a.prefab)
            G.assert(part.components.stackable:StackSize()==9 and a.components.stackable:StackSize()==31)
            a:Remove();b:Remove();part:Remove()
        end)
        check("all different identities refuse mixing", function()
            local a=spawn(catalog.items[1],1,x,z)
            for i=2,#catalog.items do
                local b=spawn(catalog.items[i],1,x,z)
                G.assert(not a.components.stackable:CanStackWith(b))
                b:Remove()
            end
            a:Remove()
        end)
        check("no unwanted resources or recipes", function()
            G.assert(G.Prefabs.klbq_resource_battlepass_coin==nil)
            G.assert(G.Prefabs.klbq_resource_activity_record==nil)
            for _, d in G.ipairs(catalog.items) do G.assert(G.AllRecipes[d.prefab]==nil) end
        end)
        player:Remove()
        chest:Remove()
        print("[RESOURCES_TEST] COMPLETE", phase, failed)
        if failed == 0 then
            G.c_save()
            G.TheWorld:DoTaskInTime(3, function() G.c_shutdown(false) end)
        else
            G.TheWorld:DoTaskInTime(1, function() G.c_shutdown(false) end)
        end
    end)
end)
