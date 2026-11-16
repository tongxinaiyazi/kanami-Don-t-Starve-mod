-- Review regression scenarios on real server entities. No GUI rendering claim.
local G=GLOBAL
local assert,ipairs,pairs,pcall=G.assert,G.ipairs,G.pairs,G.pcall
function RunKanamiLifecycleAuditChecks(context)
    local p,check,eq=context.player,context.check,context.eq
    local x,_,z=p.Transform:GetWorldPosition()
    local owned,tasks={},{}
    local function Spawn(name,dx,dz)
        local item=assert(G.SpawnPrefab(name));owned[#owned+1]=item
        item.Transform:SetPosition(x+(dx or 0),0,z+(dz or 0));item.entity:SetCanSleep(false)
        return item
    end
    local function After(t,fn)
        tasks[#tasks+1]=G.TheWorld:DoTaskInTime(t,fn)
    end
    local sleeping,initial,started,restored,ocean,external,requests= nil,nil,nil,nil,nil,nil,0
    local nightactor,nightsword,boss,bosshp,nightreleased
    local oldphase,oldmoon,oldwaxing=G.TheWorld.state.phase,G.TheWorld.state.moonphase,G.TheWorld.state.iswaxingmoon
    check("audit native zero resolved planar hit does not trigger echo",function()
        local actor,target=Spawn("klbq_kanami"),Spawn("hound",3)
        target:StopBrain("klbq_audit");target.components.health:SetMaxHealth(1000)
        target.components.health:SetAbsorptionAmount(1)
        target.components.combat:GetAttacked(actor,0,nil,nil,{planar=5})
        eq(target.components.health.currenthealth,1000)
        eq(actor.components.klbq_kanami:Remaining("passive"),0)
    end)
    check("audit native field does not hire spiders and releases legacy hire",function()
        local actor,spider=Spawn("klbq_kanami"),Spawn("spider",2)
        spider:StopBrain("klbq_audit")
        actor.components.leader:AddFollower(spider)
        assert(spider.components.follower:GetLeader()==actor)
        assert(actor.components.klbq_kanami:Cast("x"))
        assert(spider.components.follower:GetLeader()==nil)
    end)
    check("audit original Chinese line reaches native speech display guard",function()
        local actor=Spawn("klbq_kanami")
        G.require("klbq_kanami/speech").Bind(actor)
        local t=actor.components.talker
        local original="末日浩劫：处决眼前敌人的当前形态。"
        t.mod_str_fn(original)
        assert(actor.speech_override_fn(actor,"display postprocessor output")==original)
        assert(not G.GetString(actor,"ANNOUNCE_EAT","PREPARED"):find("only_used_by_warly",1,true))
    end)
    check("audit Z native sleeping update begins",function()
        sleeping=Spawn("klbq_kanami",-4)
        assert(sleeping.components.klbq_kanami:Cast("z"))
        -- The real native SG and Sanity.OnUpdate branch are used; only the
        -- sleeping input tag is supplied without needing to craft a tent.
        sleeping.sg:GoToState("idle");sleeping.sg:AddStateTag("sleeping")
        assert(sleeping.sg:HasStateTag("sleeping"))
        sleeping.components.sanity:SetPercent(.9)
        initial,started=sleeping.components.sanity.current,G.GetTime()
    end)
    check("audit upgraded paper ocean actual save load begins",function()
        local map=G.TheWorld.Map
        for r=16,256,8 do
            for n=0,31 do
                local a=n*G.math.pi/16;local ox,oz=x+r*G.math.cos(a),z+r*G.math.sin(a)
                if map:IsInMapBounds(ox,0,oz) and map:IsOceanTileAtPoint(ox,0,oz)
                    and not map:IsVisualGroundAtPoint(ox,0,oz) then ocean={ox,oz};break end
            end
            if ocean then break end
        end
        assert(ocean,"no task-world ocean point")
        local actor,bag=Spawn("klbq_kanami"),Spawn("klbq_singularity")
        assert(actor.components.inventory:Equip(bag))
        local eye=Spawn("deerclops_eyeball")
        assert(bag.components.trader:AcceptGift(actor,eye))
        local c=actor.components.klbq_kanami
        c.state.string=true;c:ApplyString();c:Sync()
        assert(c:CanStringWaterWalk())
        actor.Physics:Teleport(ocean[1],0,ocean[2])
        local record=actor:GetSaveRecord()
        restored=assert(G.SpawnSaveRecord(record));owned[#owned+1]=restored
        restored.entity:SetCanSleep(false)
    end)
    check("audit external native resurrection begins from actual death",function()
        external=Spawn("klbq_kanami",-8)
        external:ListenForEvent("respawnfromghost",function()requests=requests+1 end)
        external.components.health:Kill()
    end)
    check("audit unlit native Boss circle setup",function()
        local ax,az
        for r=24,128,12 do
            for i=0,15 do
                local a=i*G.math.pi/8;local tx,tz=x+r*G.math.cos(a),z+r*G.math.sin(a)
                if G.TheWorld.Map:IsPassableAtPoint(tx,0,tz) and G.TheWorld.Map:IsPassableAtPoint(tx+2.5,0,tz)
                    and #G.TheSim:FindEntities(tx,0,tz,10,{"_combat"},{"INLIMBO"})==0 then ax,az=tx,tz;break end
            end
            if ax then break end
        end
        assert(ax,"no clear native Boss circle point")
        nightactor=Spawn("klbq_kanami",ax-x,az-z)
        nightsword=Spawn("klbq_requiem",ax-x,az-z)
        assert(nightactor.components.inventory:Equip(nightsword))
        if not nightactor.components.playercontroller then nightactor:AddComponent("playercontroller") end
        if not nightactor.components.playeractionpicker then nightactor:AddComponent("playeractionpicker") end
        nightactor.components.playeractionpicker:PushActionFilter(function(_,action)return not action.ghost_exclusive end,G.ACTION_FILTER_PRIORITIES.default)
        nightactor.components.playercontroller.classified.iscontrollerenabled:set(true)
        boss=Spawn("bearger",ax-x+2.5,az-z)
        boss:StopBrain("klbq_audit");boss.components.locomotor:Stop();boss.components.combat:SetTarget(nil)
        bosshp=boss.components.health.currenthealth
        G.TheWorld:PushEvent("ms_setphase","night")
        G.TheWorld:PushEvent("ms_setmoonphase",{moonphase="new",iswaxing=true})
    end)
    After(1.25,function()
        check("audit Z pays real time cost during native sleeping without Recalc",function()
            assert(sleeping and sleeping:IsValid() and sleeping.sg:HasStateTag("sleeping"))
            local elapsed=G.GetTime()-started
            local delta=initial-sleeping.components.sanity.current
            assert(G.math.abs(delta-elapsed*2.5)<.2,"cost="..G.tostring(delta)..", elapsed="..G.tostring(elapsed))
            assert(sleeping.components.klbq_kanami:Cast("z"))
        end)
        check("audit upgraded paper ocean loaded position and drowning permission",function()
            assert(restored and restored:IsValid())
            local rx,_,rz=restored.Transform:GetWorldPosition()
            assert((rx-ocean[1])^2+(rz-ocean[2])^2<.1,"loaded water walker was rescued to portal")
            assert(restored.components.klbq_kanami:CanStringWaterWalk())
            assert(restored.components.drownable.enabled~=false,"temporary load guard leaked")
        end)
    end)
    After(2.5,function()
        check("audit native source revival pauses the automatic deadline",function()
            assert(external and external:IsValid() and external:HasTag("playerghost"))
            local source=Spawn("resurrectionstone",-10)
            external:PushEvent("respawnfromghost",{source=source})
            assert(external.rezsource~=nil,"native external resurrection did not start")
            local c=external.components.klbq_kanami
            c.state.deadlines.revive=G.GetTime()
            c:Tick()
            assert(not c.autoreviving and requests==1,"duplicate automatic revival request")
        end)
    end)
    After(3.25,function()
        check("audit native remote Boss circle releases despite no target illumination",function()
            -- Finish only the native ambient-light transition. Gameplay time,
            -- damage and the actor's sight remain the engine's real methods.
            G.TheWorld.components.ambientlighting:OnUpdate(30)
            local light=G.TheSim:GetLightAtPoint(boss.Transform:GetWorldPosition())
            assert(light<=G.TUNING.DARK_CUTOFF,"night target remained illuminated: "..G.tostring(light))
            assert(not G.CanEntitySeeTarget(nightactor,boss),"native dark sight did not reproduce")
            assert(nightactor.components.klbq_kanami:Cast("x"))
            nightactor.sg:GoToState("idle")
            local picker=nightactor.components.playeractionpicker
            local action
            for _,a in ipairs(picker:GetRightClickActions(boss:GetPosition(),boss)) do
                if a.action==G.ACTIONS.KLBQ_REQUIEM_SWEEP then action=a;break end
            end
            assert(action,"native Boss right click did not select circle")
            local pc=nightactor.components.playercontroller
            pc.remote_authority=true;pc.remote_predicting=true
            pc:OnRemoteRightClick(action.action.code,boss:GetPosition(),boss,0,true,0,true,action.action.mod_name)
            pc:OnUpdate(0)
            assert(nightactor.sg.currentstate.name=="klbq_requiem_sweep")
            nightreleased=true
        end)
    end)
    After(4.25,function()
        check("audit night Boss circle deals actual HP loss with field active",function()
            assert(nightreleased,"native circle was not dispatched")
            assert(boss.components.health.currenthealth<bosshp,"native Boss HP did not fall")
            G.print("[KANAMI_AUDIT_BOSS]","night with field",bosshp,boss.components.health.currenthealth)
        end)
    end)
    After(5.5,function()
        check("audit native external revival finishes without automatic protection",function()
            assert(external and external:IsValid() and not external:HasTag("playerghost"))
            assert(requests==1 and not external.components.klbq_kanami:IsProtected())
        end)
        check("audit fixture cleanup preserves parent",function()
            G.TheWorld:PushEvent("ms_setphase",oldphase)
            G.TheWorld:PushEvent("ms_setmoonphase",{moonphase=oldmoon,iswaxing=oldwaxing})
            for _,task in ipairs(tasks) do task:Cancel() end
            for i=#owned,1,-1 do
                local inst=owned[i]
                if inst:IsValid() then
                    if inst.components.inventory then
                        for _,item in ipairs(inst.components.inventory:FindItems(function()return true end)) do item:Remove() end
                    end
                    inst:Remove()
                end
            end
            assert(p:IsValid())
        end)
        context.done()
    end)
end
