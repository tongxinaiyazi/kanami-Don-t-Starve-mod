-- Development-only checks against the actually enabled HappyPatch Workshop mod.
-- Configure epic_armor_5=5, boss_maxdamagetake=1 and ["Shadow World"]=1.
local G=GLOBAL
local assert,pcall,tostring=G.assert,G.pcall,G.tostring
local ipairs,pairs,math=G.ipairs,G.pairs,G.math

function RunKanamiHappyChecks(context)
    if context.mode~="happy" then return end
    local p,check,eq=context.player,context.check,context.eq
    local owned,targets={},{}
    local x,y,z=p.Transform:GetWorldPosition()
    local c=p.components.klbq_kanami
    modimport("curse.lua")
    RunKanamiCurseChecks({player=p,check=check,eq=eq})
    local Damage=G.require("klbq_kanami/damage")
    local function Track(inst)
        assert(inst,"HappyPatch fixture failed to spawn")
        owned[#owned+1]=inst
        return inst
    end
    local function Spawn(prefab)
        local inst=Track(G.SpawnPrefab(prefab))
        inst.entity:SetCanSleep(false)
        local offset=2+#owned*2
        if not G.TheWorld.Map:IsPassableAtPoint(x+offset,0,z) then offset=0 end
        inst.Transform:SetPosition(x+offset,y,z)
        inst.entity:SetCanSleep(false)
        if inst.brain then inst.brain:Stop() end
        if inst.components.combat then inst.components.combat:SetTarget(nil) end
        return inst
    end
    local function Stop(inst)
        if inst.brain then inst.brain:Stop() end
        if inst.components.locomotor then inst.components.locomotor:StopMoving() end
        inst.components.combat:SetTarget(nil)
        if inst.sg and inst.sg.sg.states.idle then inst.sg:GoToState("idle") end
    end
    local function ContainsSource(fn,tail,seen)
        if G.type(fn)~="function" then return false end
        seen=seen or {};if seen[fn] then return false end;seen[fn]=true
        local info=G.debug.getinfo(fn,"S")
        local source=info and info.source:gsub("\\","/") or ""
        if source:find(tail,1,true) then return true end
        local i=1
        while true do
            local name,value=G.debug.getupvalue(fn,i)
            if name==nil then return false end
            if G.type(value)=="function" and ContainsSource(value,tail,seen) then return true end
            i=i+1
        end
    end
    local gun
    local function Shoot(t,ammo,roll)
        local container=gun.components.container
        local previous=container:RemoveItemBySlot(1)
        if previous then previous:Remove() end
        local item=Spawn(ammo)
        item.components.stackable:SetStackSize(4)
        assert(container:GiveItem(item,1),"native ammo insert failed")
        p._klbq_nextshot=nil;c.state.deadlines.shot=nil
        c.state.deadlines.passive=G.GetTime()+60
        local oldrandom=math.random
        math.random=function(a,b)
            if a~=nil then return b~=nil and oldrandom(a,b) or oldrandom(a) end
            return roll or .5
        end
        local ok,result=pcall(c.Shoot,c,t)
        math.random=oldrandom
        assert(ok,tostring(result));assert(result,"native rifle rejected HappyPatch target")
        eq(container:GetItemInSlot(1).components.stackable:StackSize(),3)
    end
    local function Ready(t)
        assert(t:IsValid(),"HappyPatch fixture target was removed before armor initialization")
        Stop(t)
        G.print('[KANAMI_HAPPY]',t.prefab,t:HasTag('epic'),t:HasTag('swc2hm'),t.epicarmor2hm~=nil)
        assert(t.epicarmor2hm,"HappyPatch EpicArmor was not initialized")
        assert(ContainsSource(t.components.health.SetVal,"epic/epic_armor.lua"),"actual EpicArmor closure missing")
        t.components.health:SetInvincible(false)
        t.components.health:SetPercent(1)
        eq(t.components.health.maxdamagetakenperhit,-1)
        return t.components.health
    end
    local function Pending(t)
        local h=Ready(t)
        -- Charge the actual installed doDeltaList path. Do not fabricate its
        -- armor table or replace its timers/defense callbacks.
        h:SetVal(h.currenthealth-h.maxhealth*.5,"kanami_fixture_charge",p)
        assert(t.epicarmor2hm.timer,"actual EpicArmor energy timer did not start")
        h:SetPercent(1)
        return h
    end
    local function Recovery(t)
        local h=Ready(t)
        assert(not t.epicarmor2hm.timer,"unexpected energy timer before recovery check")
        if not t.components.timer:TimerExists("invincible2hm") then
            t.components.timer:StartTimer("invincible2hm",30)
        end
        return h
    end
    local function Unchanged(t,setval,delta,total)
        assert(t.components.health.SetVal==setval,"temporary SetVal hook leaked")
        assert(t.components.health.DoDelta==delta,"temporary DoDelta hook leaked")
        eq(t.epicarmor2hm.totalDelta,total)
        eq(t.components.health.maxdamagetakenperhit,-1)
    end
    local function StillProtected(t)
        local h=t.components.health
        local before=h.currenthealth
        h:DoDelta(-100,false,"kanami_ordinary_after_bullet",false,p,true)
        assert(h.currenthealth>=before,"ordinary damage lost HappyPatch defense")
    end
    local function Cleanup()
        for i=#owned,1,-1 do if owned[i]:IsValid() then owned[i]:Remove() end end
    end
    check("HappyPatch enabled and test actor ready",function()
        assert(G.ModManager:GetMod("workshop-2886753796"),"real Workshop HappyPatch is not enabled")
        assert(c and not c:IsZ() and not c.state.string,"HappyPatch shooter must begin in ordinary form")
        gun=Spawn("klbq_finale");p.components.inventory:Equip(gun)
        for _,name in ipairs({"heart","fate","crit","doom","nested","error","phase"}) do
            targets[name]=Spawn("bearger")
        end
        targets.parent=Spawn("hound")
    end)
    G.TheWorld:DoTaskInTime(.2,function()
        check("HappyPatch actual shadow spawn and fade initialization",function()
            local parent=targets.parent;Stop(parent)
            local spawner=parent.components.childspawner2hm
            assert(spawner,"Shadow World=1 must be enabled for actual form check")
            local child
            for existing in pairs(spawner.childrenoutside) do child=existing;break end
            child=child or spawner:SpawnChild(nil)
            Track(child);Stop(child);child.entity:SetCanSleep(false)
            assert(child:HasTag("swc2hm") and child.swp2hm==parent,"not an actual HappyPatch shadow child")
            targets.shadow=child
        end)
    end)
    G.TheWorld:DoTaskInTime(1,function()
        check("HappyPatch heart ignores rate cap while native armor absorbs",function()
            local t=targets.heart;local h=Pending(t)
            if not t.components.inventory then t:AddComponent("inventory") end
            local armor=Spawn("armorwood");t.components.inventory:Equip(armor)
            h:SetAbsorptionAmount(.5)
            local before,condition=h.currenthealth,armor.components.armor.condition
            local setval,delta,total=h.SetVal,h.DoDelta,t.epicarmor2hm.totalDelta
            local expected=50*(1-armor.components.armor:GetAbsorption(p,gun))*.5
                *t.components.combat.externaldamagetakenmultipliers:Get()
                *math.max(1-h.externalabsorbmodifiers:Get(),0)
            assert(expected>1,"fixture's expected ordinary damage does not exceed cap")
            Shoot(t,"klbq_ammo_heart")
            eq(before-h.currenthealth,expected)
            assert(armor.components.armor.condition<condition,"normal armor did not lose durability")
            Unchanged(t,setval,delta,total);StillProtected(t)
        end)
        check("HappyPatch fate ignores actual recovery and DoDelta cap",function()
            local t=targets.fate;local h=Recovery(t)
            local before=h.currenthealth
            local setval,delta,total=h.SetVal,h.DoDelta,t.epicarmor2hm.totalDelta
            Shoot(t,"klbq_ammo_fate",.5);eq(before-h.currenthealth,300)
            Unchanged(t,setval,delta,total);StillProtected(t)
        end)
        check("HappyPatch fate critical uses max health through recovery",function()
            local t=targets.crit;local h=Recovery(t)
            local before=h.currenthealth
            local setval,delta,total=h.SetVal,h.DoDelta,t.epicarmor2hm.totalDelta
            Shoot(t,"klbq_ammo_fate",.01);eq(before-h.currenthealth,require("klbq_kanami/rules").Fate(h.maxhealth,true,false))
            Unchanged(t,setval,delta,total);StillProtected(t)
        end)
        check("HappyPatch doom uses native death loot and shooter credit",function()
            local t=targets.doom;local h=Pending(t)
            local deaths,kills,worlddeaths=0,0,0
            local function killed(_,data)if data.victim==t then kills=kills+1;assert(data.attacker==p)end end
            local function world(_,data)if data.inst==t then worlddeaths=worlddeaths+1;assert(data.afflicter==p)end end
            p:ListenForEvent("killed",killed)
            G.TheWorld:ListenForEvent("entity_death",world)
            t:ListenForEvent("death",function(_,data)
                deaths=deaths+1;assert(data.afflicter==p and t.components.combat.lastattacker==p)
            end)
            local setval,delta,total=h.SetVal,h.DoDelta,t.epicarmor2hm.totalDelta
            Shoot(t,"klbq_ammo_doom")
            p:RemoveEventCallback("killed",killed);G.TheWorld:RemoveEventCallback("entity_death",world)
            assert(h:IsDead());eq(deaths,1);eq(kills,1);eq(worlddeaths,1)
            assert(h.causeofdeath==p and t.components.lootdropper:GetLuckyUser()==p)
            Unchanged(t,setval,delta,total)
        end)
        check("HappyPatch nested ordinary same-shooter damage retains defense",function()
            local t=targets.nested;local h=Pending(t)
            local original=h.SetVal;local nesting=false;local total=t.epicarmor2hm.totalDelta
            h.SetVal=function(self,val,cause,afflicter)
                if not nesting then nesting=true;self:SetVal(self.currenthealth-40,cause,afflicter);nesting=false end
                return original(self,val,cause,afflicter)
            end
            local wrapped=h.SetVal;local before=h.currenthealth
            local ok,err=pcall(Damage.BulletTrueDamage,p,t,300,gun)
            assert(h.SetVal==wrapped,"nested SetVal hook leaked");h.SetVal=original
            assert(ok,tostring(err));eq(before-h.currenthealth,300)
            eq(t.epicarmor2hm.totalDelta-total,40);StillProtected(t)
        end)
        check("HappyPatch errors restore native and ancestor wrappers",function()
            local t=targets.error;local h=Pending(t);local original=h.SetVal
            h.SetVal=function(...)original(...);G.error("kanami_expected_happy_error",0)end
            local failing=h.SetVal;local before=h.currenthealth
            local ok,err=pcall(Damage.BulletTrueDamage,p,t,300,gun)
            assert(h.SetVal==failing,"error leaked SetVal dispatcher");h.SetVal=original
            assert(not ok and tostring(err):find("kanami_expected_happy_error",1,true))
            eq(before-h.currenthealth,300);StillProtected(t)
        end)
        check("HappyPatch doom preserves native minhealth phase event",function()
            local t=targets.phase;local h=Pending(t);local phases=0
            h:SetMinHealth(100)
            t:ListenForEvent("minhealth",function()phases=phases+1 end)
            Shoot(t,"klbq_ammo_doom");eq(h.currenthealth,100);eq(phases,1)
            assert(not h:IsDead(),"execution killed a following form")
        end)
        check("HappyPatch actual shadow form follows normal kill callback",function()
            local parent,child=targets.parent,targets.shadow
            assert(child,"actual shadow check did not produce a child")
            Stop(child)
            assert(not child:HasTag("NOCLICK"),"actual shadow fade has not finished")
            assert(ContainsSource(child.components.health.SetVal,"shadowworld.lua"),"actual shadow SetVal wrapper missing")
            local parenthp=parent.components.health.currenthealth
            Shoot(child,"klbq_ammo_doom")
            assert(child.isdead2hm and not child.killself2hm,"Doom bypassed the normal form-death callback")
            assert(child.components.combat.lastattacker==p,"shadow form lost shooter attribution")
            eq(parent.components.health.currenthealth,parenthp)
            assert(not parent.components.health:IsDead(),"Doom killed shadow's parent")
        end)
        G.TheWorld:DoTaskInTime(2,function()
            check("HappyPatch shadow cleanup retains living parent",function()
                assert(targets.shadow,"actual shadow check did not produce a child")
                assert(not targets.shadow:IsValid(),"normal shadow death did not complete native cleanup")
                assert(targets.parent:IsValid() and not targets.parent.components.health:IsDead())
            end)
            check("HappyPatch fixture cleanup",Cleanup)
            G.print("[KANAMI_TEST] COMPLETE")
            G.TheWorld:DoTaskInTime(1,function()G.c_shutdown(false)end)
        end)
    end)
end
