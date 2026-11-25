local G=GLOBAL
local assert,ipairs,math=G.assert,G.ipairs,G.math

function RunKanamiCaveRifleChecks(p,check,done)
    local world=G.TheWorld
    local map=world.Map
    local inv=p.components.inventory
    local c=p.components.klbq_kanami
    local loco=p.components.locomotor
    local bag,gun,target,second
    local sx,sz,vx,vz,angle
    local ready=check("locate native cave land beside an in-bounds gap",function()
        assert(world:HasTag("cave"))
        local width,height=map:GetSize()
        for i=2,width-3 do
            if sx then break end
            for j=2,height-3 do
                if G.TileGroupManager:IsLandTile(map:GetTile(i,j)) then
                    local x,_,z=map:GetTileCenterPoint(i,j)
                    if c:SafeGroundPoint({x,0,z}) then
                        for _,d in ipairs({{4,0,0},{-4,0,180},{0,4,270},{0,-4,90}}) do
                            local dx,dz=x+d[1],z+d[2]
                            if G.WORLD_TILES.IMPASSABLE==map:GetTileAtPoint(dx,0,dz) and map:IsInMapBounds(dx,0,dz)
                                and G.WORLD_TILES.IMPASSABLE==map:GetTileAtPoint(x+d[1]*2,0,z+d[2]*2) then
                                sx,sz,vx,vz,angle=x,z,dx,dz,d[3]
                                break
                            end
                        end
                    end
                end
                if sx then break end
            end
        end
        assert(sx,"no clear land and adjacent gap")
        p.Physics:Teleport(sx,0,sz);p.entity:SetCanSleep(false)
        bag=assert(G.SpawnPrefab("klbq_singularity"))
        assert(inv:Equip(bag))
        local eye=assert(G.SpawnPrefab("deerclops_eyeball"))
        assert(inv:GiveItem(eye) and bag.components.trader:AcceptGift(p,eye))
        assert(c:ToggleString())
        c:Tick()
        assert(p.Physics:GetCollisionMask()==G.COLLISION.GROUND)
        assert(not p.components.drownable:ShouldFallInVoid())
    end)
    if not ready then done();return end
    world:DoTaskInTime(.4,function()
        check("native cave left click destination across void",function()
            loco:PushAction(G.BufferedAction(p,nil,G.ACTIONS.WALKTO,nil,G.Vector3(vx,0,vz)),true)
        end)
    end)
    world:DoTaskInTime(1.9,function()
        check("native mouse walk enters gap and remains there across safety ticks",function()
            local x,y,z=p.Transform:GetWorldPosition()
            assert(map:GetTileAtPoint(x,y,z)==G.WORLD_TILES.IMPASSABLE,"left click stayed on land")
            assert(not p.components.drownable:ShouldFallInVoid())
            assert(not c:ToggleString(),"string exit allowed over gap")
        end)
        p.Physics:Teleport(sx,0,sz)
        loco:Stop()
        c:Tick()
        loco:RunInDirection(angle)
    end)
    world:DoTaskInTime(2.43,function()
        check("direct cave movement and loss of bag return to last solid ground",function()
            local x,y,z=p.Transform:GetWorldPosition()
            assert(map:GetTileAtPoint(x,y,z)==G.WORLD_TILES.IMPASSABLE,"direct movement stayed on land")
            assert(inv:Unequip(bag.components.equippable.equipslot,nil,true)==bag)
            assert(c:SafeGroundPoint({p.Transform:GetWorldPosition()}),"bag loss did not return to land")
            assert(not p._klbq_waterwalk:value())
            assert(c:ToggleString())
        end)
        if bag:IsValid() then bag:Remove() end
    end)
    local pc
    local actions=G.ACTIONS
    local function Fire(action,entity,mods)
        pc:OnRemoteLeftClick(action.code,entity:GetPosition(),entity,nil,mods,nil,action.mod_name)
    end
    world:DoTaskInTime(3.2,function()
        check("native remote Ctrl-click acquires Finale target",function()
            p.Physics:Teleport(sx,0,sz)
            if not p.components.playercontroller then p:AddComponent("playercontroller") end
            if not p.components.playeractionpicker then p:AddComponent("playeractionpicker") end
            p.components.playeractionpicker:PushActionFilter(function(_,action)
                return not action.ghost_exclusive
            end,G.ACTION_FILTER_PRIORITIES.default)
            pc=p.components.playercontroller
            pc.classified.iscontrollerenabled:set(true)
            gun=assert(G.SpawnPrefab("klbq_finale"))
            assert(inv:Equip(gun))
            local ammo=assert(G.SpawnPrefab("klbq_ammo_heart"))
            ammo.components.stackable:SetStackSize(8)
            assert(gun.components.container:GiveItem(ammo,1))
            target=assert(G.SpawnPrefab("hound"))
            target.Physics:Teleport(sx,0,sz)
            target:StopBrain("klbq_cave_rifle_test")
            target.components.locomotor:Stop()
            target.components.health:SetMaxHealth(10000);target.components.health:SetPercent(1)
            local moonlight=assert(G.SpawnPrefab("lantern"))
            moonlight.Physics:Teleport(sx,0,sz);moonlight.components.machine:TurnOn()
            Fire(actions.KLBQ_SHOOT_LOCK,target,2)
            assert(p._klbq_rifle_lock and p._klbq_rifle_lock.target==target,"remote click did not lock")
            assert(ammo.components.stackable:StackSize()==7)
        end)
    end)
    world:DoTaskInTime(5.1,function()
        check("automatic fire spends one at existing cooldown and releases on phase change",function()
            local ammo=assert(gun.components.container:GetItemInSlot(1))
            assert(ammo.components.stackable:StackSize()==6,"unexpected rounds left: "..G.tostring(ammo.components.stackable:StackSize())
                ..", lock: "..G.tostring(p._klbq_rifle_lock~=nil)..", state: "..p.sg.currentstate.name)
            target:PushEvent("phasetransition")
            assert(p._klbq_rifle_lock==nil)
            second=assert(G.SpawnPrefab("hound"));second.Physics:Teleport(sx,0,sz)
            second:StopBrain("klbq_cave_rifle_test");second.components.locomotor:Stop()
            -- The test clicks again outside a firing animation while still
            -- on cooldown; switching targets must not spend a round early.
            Fire(actions.KLBQ_SHOOT_LOCK,second,2)
            assert(p._klbq_rifle_lock and p._klbq_rifle_lock.target==second)
        end)
    end)
    world:DoTaskInTime(5.8,function()
        check("holstering Finale drops the target",function()
            assert(inv:Unequip(G.EQUIPSLOTS.HANDS,nil,true)==gun)
            assert(p._klbq_rifle_lock==nil)
        end)
        if target and target:IsValid() then target:Remove() end
        if second and second:IsValid() then second:Remove() end
        done()
    end)
end
