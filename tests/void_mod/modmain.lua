local G=GLOBAL
local pcall,assert,tostring,math=G.pcall,G.assert,G.tostring,G.math
local mode=GetModConfigData("mode")
local function report(name,fn)
    local ok,err=pcall(fn)
    print("[VOID_TEST]",ok and "PASS" or "FAIL",name,not ok and tostring(err) or "")
end
local function eq(a,b) assert(math.abs(a-b)<.02,tostring(a).." ~= "..tostring(b)) end
AddSimPostInit(function()
    if not G.TheWorld.ismastersim then return end
    G.TheWorld:DoTaskInTime(3,function()
        print("[VOID_TEST] START",mode,G.APP_VERSION)
        if mode=="control" then
            local ok,t=pcall(G.SpawnPrefab,"ancient_robot_claw")
            print("[VOID_CONTROL] claw",ok,t)
            if ok and t then t:Remove() end
            print("[VOID_TEST] COMPLETE");G.c_shutdown(false);return
        end
        local p=assert(G.SpawnPrefab("klbq_kanami"));p.userid="KANAMI_VOID_TEST"
        if not p.components.playercontroller then p:AddComponent("playercontroller") end
        p.entity:SetCanSleep(false)
        local portal=G.c_find("multiplayer_portal")
        local x,y,z=portal.Transform:GetWorldPosition();p.Physics:Teleport(x+4,0,z+4)
        x,y,z=p.Transform:GetWorldPosition()
        local c=p.components.klbq_kanami
        local gun=assert(G.SpawnPrefab("klbq_finale"));p.components.inventory:Equip(gun)
        local damage=G.require("klbq_kanami/damage")
        local observed={}
        local function target(name)
            local t=assert(G.SpawnPrefab(name));t.Transform:SetPosition(x+8,0,z)
            if t.brain then t.brain:Stop() end
            t.entity:SetCanSleep(false)
            local h=t.components.health
            print("[VOID_TARGET]",name,"hp",h and h.maxhealth,"combat",t.components.combat~=nil,"loco",t.components.locomotor~=nil,"loot",t.components.lootdropper~=nil)
            return t
        end
        local function ammo(name)
            local old=gun.components.container:RemoveItemBySlot(1);if old then old:Remove() end
            local a=assert(G.SpawnPrefab(name));a.components.stackable:SetStackSize(4);assert(gun.components.container:GiveItem(a,1))
            c.state.deadlines.shot=nil;c.state.deadlines.passive=nil;c.state.zenabled=false;p._klbq_nextshot=nil
        end
        report("king heart actual damage",function()
            local t=target("kingslime");local h=t.components.health;local before=h.currenthealth
            ammo("klbq_ammo_heart");assert(c:Shoot(t));print("[VOID_OBS] king heart",before-h.currenthealth,"absorb",h.absorb,"planar",t.components.planardefense~=nil,"armor",t.components.armor~=nil);eq(before-h.currenthealth,517.65);t:Remove()
        end)
        report("king heart defensive paths",function()
            local t=target("kingslime");local h=t.components.health;local before=h.currenthealth
            assert(damage.Normal(p,t,50,gun));local ordinary=before-h.currenthealth;before=h.currenthealth
            assert(damage.Planar(p,t,34,gun));local planar=before-h.currenthealth
            print("[VOID_OBS] king normal",ordinary,"planar",planar);eq(ordinary+planar,68.88);t:Remove()
        end)
        report("king fate fixed and invincible",function()
            local t=target("kingslime");local h=t.components.health;local before=h.currenthealth
            local rules=G.require("klbq_kanami/rules");eq(rules.Fate(h.maxhealth,false,false),300);eq(rules.Fate(h.maxhealth,true,false),3000);eq(rules.Fate(h.maxhealth,false,true),450)
            assert(damage.TrueDamage(p,t,300));eq(before-h.currenthealth,300)
            h:SetInvincible(true);before=h.currenthealth;assert(not damage.TrueDamage(p,t,300));eq(before,h.currenthealth);t:Remove()
        end)
        report("king both bullet types bypass cap and private rate gates",function()
            local t=target("kingslime");local h=t.components.health
            h:SetMaxHealth(1000);h:SetPercent(1);h:SetMaxDamageTakenPerHit(1)
            -- Artificial local gates on the actual mod entity; unrelated
            -- damage must keep these gates, while rifle bullets bypass them.
            h.DoDelta=function() return 0 end
            h.deltamodifierfn=function() return 0 end
            t.components.combat.GetAttacked=function() return false end
            t.components.combat.GetAttacked_Internal=function() return false end
            ammo("klbq_ammo_heart");c.state.deadlines.passive=G.GetTime()+3
            local before=h.currenthealth;assert(c:Shoot(t));eq(before-h.currenthealth,41)
            ammo("klbq_ammo_fate");c.state.deadlines.passive=G.GetTime()+3
            before=h.currenthealth;assert(c:Shoot(t));eq(before-h.currenthealth,300)
            print("[VOID_OBS] rifle cap/rate bypass",41,300)
            t:Remove()
        end)
        report("king fate critical and Z",function()
            local t=target("kingslime");local h=t.components.health;local before=h.currenthealth
            local rules=G.require("klbq_kanami/rules");local amount=rules.Fate(h.maxhealth,true,true)
            eq(amount,4500);assert(damage.TrueDamage(p,t,amount));eq(before-h.currenthealth,4500);t:Remove()
        end)
        report("king domain debuff restore",function()
            local t=target("kingslime");local combat=t.components.combat;local loco=assert(t.components.locomotor)
            local d=combat.externaldamagemultipliers:Get();local s=loco:GetSpeedMultiplier()
            c.state.deadlines.x=nil;assert(c:Cast("x"));c:Tick();eq(combat.externaldamagemultipliers:Get(),d*.5);eq(loco:GetSpeedMultiplier(),s*.5)
            c.state.deadlines.x_active=nil;c:Tick();eq(combat.externaldamagemultipliers:Get(),d);eq(loco:GetSpeedMultiplier(),s);t:Remove()
        end)
        report("king doom death event and attribution",function()
            local t=target("kingslime");local h=t.components.health;local deaths,kills=0,0
            local loot=t.components.lootdropper;local previous=loot.DropLoot
            loot.DropLoot=function(self,...) observed.kingloot=(observed.kingloot or 0)+1;return previous(self,...) end
            observed.king=t
            t.components.combat.lastattacker=t
            t:ListenForEvent("death",function(_,data)
                deaths=deaths+1
                assert(data.afflicter==p and data.cause==(p.nameoverride or p.prefab))
                assert(t.components.combat.lastattacker==p,"stale doom kill source")
            end)
            p:ListenForEvent("killed",function(_,data) if data.victim==t then kills=kills+1 end end)
            h:SetInvincible(true);h:SetMaxDamageTakenPerHit(1)
            ammo("klbq_ammo_doom");assert(c:Shoot(t));assert(h:IsDead());eq(deaths,1);eq(kills,1)
            assert(h.causeofdeath==p and loot:GetLuckyUser()==p)
            print("[VOID_OBS] king death",deaths,"kills",kills,"lootdropper",t.components.lootdropper~=nil)
        end)
        report("order fate and doom",function()
            local t=target("tr_zhixu");local h=t.components.health;local before=h.currenthealth
            local loot=t.components.lootdropper;local previous=loot.DropLoot
            loot.DropLoot=function(self,...) observed.orderloot=(observed.orderloot or 0)+1;return previous(self,...) end
            observed.order=t
            assert(damage.TrueDamage(p,t,300));eq(before-h.currenthealth,300)
            local deaths=0;t:ListenForEvent("death",function() deaths=deaths+1 end)
            h:SetInvincible(true);h:SetMaxDamageTakenPerHit(1);assert(damage.Execute(p,t));assert(h:IsDead());eq(deaths,1)
            print("[VOID_OBS] order death",deaths,"lootdropper",t.components.lootdropper~=nil)
        end)
        G.TheWorld:DoTaskInTime(10,function()
            print("[VOID_OBS] delayed loot calls king",observed.kingloot or 0,"order",observed.orderloot or 0,"king valid",observed.king and observed.king:IsValid(),"order valid",observed.order and observed.order:IsValid())
            print("[VOID_TEST] COMPLETE");G.c_shutdown(false)
        end)
    end)
end)
