local G=GLOBAL
local pcall,assert,type,tostring,math=G.pcall,G.assert,G.type,G.tostring,G.math
local mode=GetModConfigData("mode") or "base"
if mode=="interactive" then
    -- Owned visual QA only: protect players immediately, including reload,
    -- while the external screenshot driver is waiting for its command hook.
    AddPlayerPostInit(function(inst)
        if not G.TheWorld.ismastersim then return end
        inst:DoTaskInTime(0,function()
            if inst._imprintGod then inst._imprintGod:Cancel() end
            inst._imprintGod=inst:DoPeriodicTask(.2,function(p)
                if p:HasTag("playerghost") then p:PushEvent("respawnfromghost",{source=p})
                elseif p.components.health then
                    p.components.health:SetInvincible(true);p.components.health:SetPercent(1)
                    p.components.hunger:SetPercent(1);p.components.sanity:SetPercent(1)
                    p.components.temperature:SetTemperature(22);p:AddTag("notarget")
                    local k=p.components.klbq_kanami
                    if k then k.state.deadlines.protect=nil;k:Sync() end
                end
            end)
        end)
    end)
end
local function report(name,ok,detail)
    print("[KANAMI_TEST]",ok and "PASS" or "FAIL",name,detail or "")
end
local function check(name,fn)
    local ok,err=pcall(fn)
    report(name,ok,not ok and tostring(err) or "")
    return ok
end
local function eq(a,b) assert(math.abs(a-b)<.01,tostring(a).." ~= "..tostring(b)) end
AddSimPostInit(function()
    if not G.TheWorld.ismastersim then return end
    G.TheWorld:DoTaskInTime(3,function()
        print("[KANAMI_TEST] START",G.APP_VERSION)
        if mode=="interactive" then print("[KANAMI_TEST] INTERACTIVE_READY");return end
        if mode=="void_probe" then
            local mod=G.ModManager:GetMod("workshop-2526778484")
            assert(mod,"Void Realm was not loaded")
            local names={}
            for name,prefab in G.pairs(mod.Prefabs or {}) do
                local info=prefab.fn and G.debug.getinfo(prefab.fn,"S")
                local source=info and info.source or ""
                if G.string.find(name,"slime") or G.string.find(name,"robot") or G.string.find(name,"zhixu")
                    or G.string.find(source,"sishisheng") or G.string.find(source,"lizhanshuangsheng") then
                    names[#names+1]=name
                    print("[KANAMI_VOID_PREFAB]",name,source)
                end
            end
            G.table.sort(names)
            for _,name in G.ipairs(names) do
                local spawned,t=pcall(G.SpawnPrefab,name)
                if spawned and t then
                    if t.brain then t.brain:Stop() end
                    local h=t.components.health
                    if h then
                        print("[KANAMI_VOID_HEALTH]",name,"max",h.maxhealth,"min",h.minhealth,"cap",h.maxdamagetakenperhit,"invincible",h.invincible,"combat",t.components.combat~=nil)
                    end
                    t:Remove()
                else print("[KANAMI_VOID_SPAWN_ERROR]",name,t) end
            end
            print("[KANAMI_TEST] COMPLETE");G.c_shutdown(false);return
        end
        local ok,p=pcall(G.SpawnPrefab,"klbq_kanami")
        if not ok or not p then report("spawn",false,p);return end
        G.rawset(G,"KANAMI_TEST_PLAYER",p)
        p.userid="KANAMI_ENGINE_TEST"
        local startportal=G.c_find("multiplayer_portal")
        if startportal then local px,py,pz=startportal.Transform:GetWorldPosition();p.Transform:SetPosition(px+4,py,pz+4)end
        if mode=="bag" then
            modimport("bag.lua");RunKanamiBagChecks({player=p,check=check,eq=eq})
            return
        end
        if mode=="guard" then
            modimport("inventory_guard.lua");RunKanamiInventoryGuardChecks({player=p,check=check})
            return
        end
        if mode=="resources" then
            modimport("resources.lua");RunKanamiResourceChecks({player=p,check=check,eq=eq})
            return
        end
        if mode=="imprint" then
            modimport("imprint.lua");RunKanamiImprintChecks({player=p,check=check,eq=eq})
            return
        end
        if mode=="audit" then
            modimport("audit_lifecycle.lua")
            RunKanamiLifecycleAuditChecks({player=p,check=check,eq=eq,done=function()
                print("[KANAMI_TEST] COMPLETE")
                G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
            end})
            return
        end
        if mode=="weapon_inputs" then
            modimport("weapon_inputs.lua")
            RunKanamiWeaponInputChecks({player=p,check=check,eq=eq,label="joint installed mods",done=function()
                modimport("character_interactions.lua")
                RunKanamiCharacterInteractionChecks({player=p,check=check,eq=eq,done=function()
                    print("[KANAMI_TEST] COMPLETE")
                    G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
                end})
            end})
            return
        end
        if mode=="weapons" then
            modimport("weapons.lua");RunKanamiWeaponsChecks({mode="base",player=p,check=check,eq=eq})
            modimport("requiem.lua");RunKanamiRequiemChecks({mode="base",player=p,check=check,eq=eq})
            G.TheWorld:DoTaskInTime(6,function()
                modimport("character_interactions.lua")
                RunKanamiCharacterInteractionChecks({player=p,check=check,eq=eq,done=function()
                    print("[KANAMI_TEST] COMPLETE")
                    G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
                end})
            end)
            return
        end
        if mode=="happy" then
            modimport("happy.lua")
            RunKanamiHappyChecks({mode=mode,player=p,check=check,eq=eq})
            return
        end
        -- A synthetic entity has no network join/controller phase. Add the
        -- real server controller, but don't emit portal player-join events.
        if not p.components.playercontroller then p:AddComponent("playercontroller") end
        p.entity:SetCanSleep(false)
        local portal=G.c_find("multiplayer_portal")
        if portal then
            local px,py,pz=portal.Transform:GetWorldPosition()
            p.Transform:SetPosition(px+4,py,pz+4)
        end
        local x,y,z=p.Transform:GetWorldPosition()
        local c=p.components.klbq_kanami
        -- Old test creatures may remain in this task-owned persistent world.
        -- Pick a genuinely clear land point before testing a safe C exit.
        do
            local px,py,pz=p.Transform:GetWorldPosition()
            -- Validate against the same complete character collision mask
            -- ApplyString will save, including other synthetic players.
            c.savedmask=p.Physics:GetCollisionMask()
            local found=false
            for dx=-16,16,4 do
                for dz=-16,16,4 do
                    p.Physics:Teleport(px+dx,0,pz+dz)
                    if c:SafePoint(px+dx,0,pz+dz) then found=true;break end
                end
                if found then break end
            end
            x,y,z=p.Transform:GetWorldPosition()
            assert(found,"no safe synthetic-player land point")
        end
        local function lifecycle(event)
            print("[KANAMI_LIFECYCLE]",event,"ghost",p:HasTag("playerghost"),"hp",p.components.health.currenthealth,
                "sg",p.sg and p.sg.currentstate.name,"dead",c and c.state.dead,"auto",c and c.autoreviving,
                "remaining",c and c:Remaining("revive"),"protected",c and c:IsProtected())
            print("[KANAMI_ANIM]",event,"asleep",p:IsAsleep(),"done",p.AnimState:AnimDone())
        end
        for _,event in G.ipairs({"death","ms_becameghost","respawnfromghost","ms_respawnedfromghost"}) do
            p:ListenForEvent(event,function()
                lifecycle(event)
                if event=="ms_respawnedfromghost" then
                    check("exact revival stats at event",function()
                        eq(p.components.health.currenthealth,1)
                        eq(p.components.hunger.current,37.5)
                        eq(p.components.sanity.current,200)
                    end)
                end
            end)
        end
        check("base stats",function()
            assert(c);eq(p.components.health.maxhealth,75);eq(p.components.hunger.max,75);eq(p.components.sanity.max,200)
        end)
        print("[KANAMI_API] AnimState.GetScale",type(p.AnimState.GetScale))
        local function target()
            local t=G.SpawnPrefab("beefalo")
            t.Transform:SetPosition(x+8,0,z)
            if t.brain then t.brain:Stop() end
            t.components.combat:SetTarget(nil)
            t.components.health:SetMaxHealth(10000)
            return t
        end
        local gun=G.SpawnPrefab("klbq_finale")
        p.components.inventory:Equip(gun)
        local function ammo(prefab)
            local previous=gun.components.container:RemoveItemBySlot(1)
            if previous then previous:Remove() end
            local item=G.SpawnPrefab(prefab);item.components.stackable:SetStackSize(4)
            assert(gun.components.container:GiveItem(item,1))
            c.state.deadlines.shot=nil;c.state.deadlines.passive=nil;p._klbq_nextshot=nil
            return item
        end
        check("heart 50 plus rifle echo34",function()
            local t=target();ammo("klbq_ammo_heart");assert(c:Shoot(t));eq(t.components.health.currenthealth,9617.5)
            eq(gun.components.container:GetItemInSlot(1).components.stackable:StackSize(),3)
            assert(not c:Shoot(t));t:Remove()
        end)
        check("fate bullet bypasses cap and passive retains normal limits",function()
            local t=target();t.components.health:SetMaxHealth(1000);t.components.health:SetPercent(1)
            t.components.health:SetMaxDamageTakenPerHit(20)
            ammo("klbq_ammo_fate");assert(c:Shoot(t));eq(t.components.health.currenthealth,660);t:Remove()
        end)
        check("doom bypass cap invulnerable and death callback",function()
            local t=target();local deaths=0
            t.components.combat.lastattacker=t -- Replace an existing source.
            t:ListenForEvent("death",function(_,data)
                deaths=deaths+1
                assert(data.afflicter==p and data.cause==(p.nameoverride or p.prefab),"death source is not shooter")
                assert(t.components.combat.lastattacker==p,"combat source stale during death")
            end)
            t.components.health:SetInvincible(true);t.components.health:SetMaxDamageTakenPerHit(1)
            ammo("klbq_ammo_doom");assert(c:Shoot(t));assert(t.components.health:IsDead());eq(deaths,1)
            assert(t.components.health.causeofdeath==p)
            assert(t.components.lootdropper:GetLuckyUser()==p,"loot source is not shooter")
        end)
        check("dynamic other weapon echo",function()
            gun.components.container:Close()
            local sword=G.SpawnPrefab("nightsword");p.components.inventory:Equip(sword)
            local t=target();local snap=G.require("klbq_kanami/damage").Snapshot(p,t,sword)
            eq(snap.power,68);c.state.deadlines.passive=nil;assert(c:Echo(t,snap));eq(t.components.health.currenthealth,9632)
            t:Remove();p.components.inventory:Equip(gun)
        end)
        check("fate alone triggers native beefalo retaliation",function()
            local t=target();ammo("klbq_ammo_fate")
            -- Suppress the passive so its Combat:GetAttacked cannot hide
            -- a missing attacked notification in the true-damage path.
            c.state.deadlines.passive=G.GetTime()+3
            assert(c:Shoot(t));assert(t.components.health.currenthealth<=9700)
            assert(t.components.combat.target==p,"true hit did not aggro native beefalo")
            t:Remove()
        end)
        check("Z ordinary planar once",function()
            local t=target();ammo("klbq_ammo_heart");assert(c:Cast("z"));assert(c:Shoot(t));eq(t.components.health.currenthealth,9427.375)
            t:Remove();assert(c:Cast("z"));assert(not c:IsZ())
        end)
        check("string speed additive and damage multiply",function()
            local prior=p.components.locomotor:GetSpeedMultiplier()
            assert(c:ToggleString());eq(p.components.locomotor:GetSpeedMultiplier(),prior+.5)
            local h=p.components.health.currenthealth;p.components.health:DoDelta(-10);eq(p.components.health.currenthealth,h-2)
            local rejected=target();assert(not c:Shoot(rejected));rejected:Remove()
            assert(c:ToggleString(),"C exit unexpectedly unsafe")
        end)
        check("domain enemy debuff exit restore",function()
            local t=target();local mult=t.components.combat.externaldamagemultipliers:Get();local speed=t.components.locomotor:GetSpeedMultiplier()
            assert(c:Cast("x"));c:Tick();eq(t.components.combat.externaldamagemultipliers:Get(),mult*.5)
            eq(t.components.locomotor:GetSpeedMultiplier(),speed*.5)
            c.state.deadlines.x_active=nil;c:Tick();eq(t.components.combat.externaldamagemultipliers:Get(),mult)
            t:Remove()
        end)
        check("save/load keeps remaining deadlines",function()
            c.state.deadlines.x=G.GetTime()+12.5
            local saved=c:OnSave();c:OnLoad(saved);eq(c:Remaining("x"),12.5)
        end)
        if mode=="base" then
            modimport("content.lua")
            RunKanamiContentChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("performance.lua")
            RunKanamiPerformanceChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("balance.lua")
            RunKanamiBalanceChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("weapons.lua")
            RunKanamiWeaponsChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("requiem.lua")
            RunKanamiRequiemChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("garden.lua")
            RunKanamiGardenChecks({mode=mode,player=p,target=target,check=check,eq=eq})
            modimport("curse.lua")
            RunKanamiCurseChecks({player=p,check=check,eq=eq})
        end
        check("begin real60s resurrection",function()
            p.components.health:Kill();assert(c.state.dead);eq(c:Remaining("revive"),60)
        end)
        p:DoTaskInTime(61.5,function()
            lifecycle("check61.5")
            check("real60s revive stats and protection",function()
                assert(not p:HasTag("playerghost"));eq(p.components.health.currenthealth,1)
                -- At this later instant normal hunger drain has resumed.
                assert(p.components.hunger.current<=37.5 and p.components.hunger.current>37)
                assert(p.components.sanity.current<=200 and p.components.sanity.current>198)
                assert(c:IsProtected())
                p.components.health:DoDelta(-1000);eq(p.components.health.currenthealth,1)
            end)
        end)
        p:DoTaskInTime(92,function()
            check("protection expires after real30s",function() assert(not c:IsProtected()) end)
            modimport("character_interactions.lua")
            RunKanamiCharacterInteractionChecks({player=p,check=check,eq=eq,done=function()
                print("[KANAMI_TEST] COMPLETE")
                G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
            end})
        end)
    end)
end)
