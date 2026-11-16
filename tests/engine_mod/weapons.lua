-- Development-only integration checks in the task-owned native test world.
-- Real PlayerController -> Locomotor -> ATTACK handler -> SG -> Weapon ->
-- Projectile -> Combat paths run across actual engine ticks. Only held input
-- on synthetic server controllers is supplied by this fixture.
local G=GLOBAL
local assert,pcall,tostring=G.assert,G.pcall,G.tostring
local ipairs,pairs=G.ipairs,G.pairs

function RunKanamiWeaponsChecks(context)
    if context.mode~="base" then return end
    local p,check,eq=context.player,context.check,context.eq
    local x,y,z=p.Transform:GetWorldPosition()
    local scopeindex=0

    local function Scoped(name,setup,duration)
        scopeindex=scopeindex+1
        local offset=(scopeindex-1)*2
        local owned,seen,tasks={},{},{}
        local problem
        local function Track(inst)
            assert(inst~=nil,"native weapon fixture failed to spawn")
            if not seen[inst] then seen[inst]=true;owned[#owned+1]=inst end
            return inst
        end
        local function Spawn(prefab)
            local inst=Track(G.SpawnPrefab(prefab))
            inst.Transform:SetPosition(x,y,z+offset)
            inst.entity:SetCanSleep(false)
            return inst
        end
        local function After(delay,fn)
            local task=G.TheWorld:DoTaskInTime(delay,function()
                if problem then return end
                local ok,err=pcall(fn)
                if not ok then problem=err end
            end)
            tasks[#tasks+1]=task
            return task
        end
        local function Actor(prefab)
            local actor=Spawn(prefab or "wilson")
            actor.userid="KANAMI_WEAPONS_"..tostring(actor.GUID)
            if not actor.components.playercontroller then actor:AddComponent("playercontroller") end
            local pc=actor.components.playercontroller
            assert(pc.locomotor==actor.components.locomotor,"synthetic native controller has no locomotor")
            -- Fresh synthetic players bypass the connection/activation phase.
            -- Set the native classified permission rather than replacing
            -- IsEnabled, ATTACK actions, combat or the native stategraph.
            assert(pc.classified and pc.classified.iscontrollerenabled,"native controller classified missing")
            pc.classified.iscontrollerenabled:set(true)
            local held=false
            local oldpressed=pc.IsControlPressed
            pc.IsControlPressed=function(self,control)
                if control==G.CONTROL_ATTACK then return held end
                return oldpressed(self,control)
            end
            pc.IsAnyOfControlsPressed=function(self,...)
                for _,control in ipairs({...}) do if self:IsControlPressed(control) then return true end end
                return false
            end
            return actor,function(value) held=value end
        end
        local function Victim(actor,defense,armor)
            local victim=Spawn("hound")
            local ax,ay,az=actor.Transform:GetWorldPosition()
            victim.Transform:SetPosition(ax+8,ay,az)
            victim:StopBrain("klbq_engine_target")
            victim.components.combat:SetTarget(nil)
            victim.components.locomotor:Stop()
            victim.components.health:SetMaxHealth(10000)
            victim.components.health:SetPercent(1)
            if defense then
                if not victim.components.planardefense then victim:AddComponent("planardefense") end
                victim.components.planardefense:SetBaseDefense(defense)
            end
            if armor then
                if not victim.components.inventory then victim:AddComponent("inventory") end
                victim.components.inventory:Equip(armor)
                assert(victim.components.inventory:GetEquippedItem(G.EQUIPSLOTS.BODY)==armor,"native victim armor equip failed")
            end
            return victim
        end
        local function Observe(weapon)
            local launches={}
            weapon:ListenForEvent("weapononprojectilelaunched",function(_,data)
                launches[#launches+1]=G.GetTime()
                if data and data.projectile then Track(data.projectile) end

            end)
            return launches
        end
        local function Fire(actor,victim,held)
            actor.components.playercontroller.classified.iscontrollerenabled:set(true)
            assert(actor.components.playercontroller:IsEnabled(),"native controller disabled before F")
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS).prefab=="klbq_crossbow","native crossbow was not equipped")
            actor.components.locomotor:Stop()
            held(true)

            -- This is the real native F-button method. It must route through
            -- GoToEntity/OnUpdate and PushBufferedAction before entering SG.
            actor.components.playercontroller:DoAttackButton(victim)

        end
        local function Cleanup()
            for _,task in ipairs(tasks) do task:Cancel() end
            for _,inst in ipairs(owned) do
                if inst:IsValid() and inst.components.inventory then
                    for _,item in ipairs(inst.components.inventory:FindItems(function() return true end)) do
                        if item:IsValid() then item:Remove() end
                    end
                end
            end
            for i=#owned,1,-1 do if owned[i]:IsValid() then owned[i]:Remove() end end
        end
        local function Finish(verify)
            check(name,function()
                local ok,err=pcall(function()
                    assert(problem==nil,"async native fixture: "..tostring(problem))
                    verify()
                end)
                local cleanupok,cleanerr=pcall(Cleanup)
                assert(ok,tostring(err))
                assert(cleanupok,"weapon fixture cleanup: "..tostring(cleanerr))
            end)
        end
        local ok,verify=pcall(setup,Spawn,Actor,Victim,Observe,Fire,After,Track)
        if not ok then
            Finish(function() G.error(verify,0) end)
        else
            G.TheWorld:DoTaskInTime(duration,function() Finish(verify) end)
        end
    end

    Scoped("crossbow native predicted walk handoff permits remote F and new movement stops fire",function(Spawn,Actor,Victim,Observe,_,After)
        local actor,held=Actor("wilson")
        local crossbow=Spawn("klbq_crossbow")
        local victim=Victim(actor)
        actor.components.inventory:Equip(crossbow)
        local launches=Observe(crossbow)
        local stopped
        After(.25,function()
            local pc=actor.components.playercontroller
            local ax,_,az=actor.Transform:GetWorldPosition()
            pc.remote_authority=true;pc.remote_predicting=true
            pc:OnRemotePredictWalking(ax,az,true,true,nil,nil,false)
            pc.directwalking=true;pc.predictwalking=true
            held(true)
            pc:OnRemoteAttackButton(victim,false,false,false,false)
            assert(pc.attack_buffer,"native remote F did not create its buffered action")
            assert(pc.attack_buffer.forced and pc.attack_buffer._predictpos,"native predicted F lost its forced position contract")
            -- Native OnUpdate supplies _predictpos before PushAction. A forced
            -- action pushed without that point never reaches the stategraph.
            pc:OnUpdate(0)
            assert(pc.remote_vector.y==0 or pc.remote_vector.y==5,"native action did not settle the predicted walk")
            assert(actor.sg.currentstate.name=="klbq_crossbow_attack","native predicted walk cancelled remote F handoff: state="
                ..actor.sg.currentstate.name.." vector="..tostring(pc.remote_vector.y)
                .." forward="..tostring(pc.locomotor:WantsToMoveForward())
                .." direct="..tostring(pc.directwalking).." predict="..tostring(pc.predictwalking))
            eq(#launches,1)
        end)
        After(.9,function()
            assert(#launches>=5,"native remote handoff interrupted held shots")
            stopped=#launches
            local pc=actor.components.playercontroller
            local ax,_,az=actor.Transform:GetWorldPosition()
            pc:OnRemotePredictWalking(ax+3,az,true,false,nil,nil,false)
        end)
        return function()
            assert(stopped,"native remote movement stage did not run")
            eq(#launches,stopped)
            assert(actor.sg.currentstate.name~="klbq_crossbow_attack","new remote movement did not cancel held fire")
            held(false)
        end
    end,1.3)

    for direction=0,3 do
        local angle=direction*G.math.pi/2
        Scoped("crossbow elevated launch and hit direction "..direction,function(Spawn,Actor,Victim,Observe,Fire,After)
            local actor,held=Actor("klbq_kanami")
            local crossbow=Spawn("klbq_crossbow")
            local victim=Victim(actor)
            actor.components.inventory:Equip(crossbow)
            local ax,ay,az=actor.Transform:GetWorldPosition()
            victim.Transform:SetPosition(ax+8*G.math.cos(angle),ay,az-8*G.math.sin(angle))
            local launches=Observe(crossbow)
            local origin
            crossbow:ListenForEvent("weapononprojectilelaunched",function(_,data)
                if not origin and data and data.projectile then
                    local px,py,pz=data.projectile.Transform:GetWorldPosition()
                    local x0,y0,z0=actor.Transform:GetWorldPosition()
                    origin={px-x0,py-y0,pz-z0,actor.Transform:GetRotation()*G.DEGREES}
                end
            end)
            After(.25,function() Fire(actor,victim,held) end)
            After(.3,function() held(false) end)
            return function()
                assert(origin,"no native projectile launch")
                assert(G.math.abs(origin[2]-1.5)<.001,"bolt spawned at feet")
                -- Other simultaneous fixtures can push the target slightly;
                -- compare against the actor's actual facing at release.
                assert(G.math.abs(origin[1]-1.2*G.math.cos(origin[4]))<.01,"incorrect muzzle x")
                assert(G.math.abs(origin[3]+1.2*G.math.sin(origin[4]))<.01,"incorrect muzzle z")
                assert(#launches>0 and victim.components.health.currenthealth<10000,"raised bolt did not hit")
            end
        end,1.4)
    end

    Scoped("crossbow native F holds eight per second and release stops launching",function(Spawn,Actor,Victim,Observe,Fire,After)
        local actor,held=Actor("wilson")
        local crossbow=Spawn("klbq_crossbow")
        local victim=Victim(actor)
        actor.components.inventory:Equip(crossbow)
        local launches=Observe(crossbow)
        local start,released
        After(.25,function()
            start=G.GetTime()
            Fire(actor,victim,held)
        end)
        -- Allow equip/initialization events to settle before pressing F, then
        -- leave it held for four real seconds. A task and SG update can share
        -- the endpoint tick, so the observed endpoint is 32 or 33 launches.
        After(4.25,function() held(false);released=#launches end)
        return function()
            assert(start and G.GetTime()-start>=4.5,"cadence check did not span real engine time")
            assert(released and released>=32 and released<=33,"expected about 33 real F launches, observed "..tostring(released))
            eq(#launches,released)
            assert(actor.sg.currentstate.name~="klbq_crossbow_attack","release retained firing state")
            for i=2,#launches do
                local frames=(launches[i]-launches[i-1])/G.FRAMES
                assert(frames>=2.95 and frames<=4.05,"launch gap is not a three/four-frame cadence: "..tostring(frames))
            end
            local mean=(launches[#launches]-launches[1])/(#launches-1)
            assert(G.math.abs(mean-.125)<G.FRAMES/(#launches-1)+.001,"native average is not eight rounds per second")
            eq(10000-victim.components.health.currenthealth,#launches*5)
            eq(actor.components.combat.min_attack_period,G.TUNING.WILSON_ATTACK_PERIOD)
            G.print("[KANAMI_WEAPONS_CADENCE]",#launches,"shots",G.GetTime()-start,"elapsed",mean,"mean interval")
        end
    end,5)

    Scoped("crossbow native zero physical armor planar defense and weapon swap",function(Spawn,Actor,Victim,Observe,Fire,After)
        local actor,held=Actor("wilson")
        local crossbow,armor,spear=Spawn("klbq_crossbow"),Spawn("armorwood"),Spawn("spear")
        local victim=Victim(actor,3,armor)
        local condition=armor.components.armor.condition
        actor.components.inventory:Equip(crossbow)
        local launches=Observe(crossbow)
        local swapped
        After(.25,function() Fire(actor,victim,held) end)
        After(1.25,function()
            actor.components.inventory:Equip(spear)
            swapped=#launches
            assert(swapped>0,"native F never launched before weapon swap")
            -- Keep F held briefly; losing the weapon must end this stream.
        end)
        After(1.5,function() held(false) end)
        return function()
            assert(swapped,"weapon-swap stage did not run")
            eq(#launches,swapped)
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)==spear,"native spear equip failed")
            assert(actor.sg.currentstate.name~="klbq_crossbow_attack","weapon swap retained firing state")
            eq(10000-victim.components.health.currenthealth,#launches*(5-3))
            eq(armor.components.armor.condition,condition)
            eq(actor.components.combat.min_attack_period,G.TUNING.WILSON_ATTACK_PERIOD)
        end
    end,1.8)

    Scoped("crossbow native protected hands stop and reject further F",function(Spawn,Actor,Victim,Observe,Fire,After)
        local actor,held=Actor("klbq_kanami")
        local crossbow=Spawn("klbq_crossbow")
        local victim=Victim(actor)
        local k=assert(actor.components.klbq_kanami)
        actor.components.inventory:Equip(crossbow)
        local launches=Observe(crossbow)
        local protected
        After(.25,function() Fire(actor,victim,held) end)
        After(.9,function()
            protected=#launches
            assert(protected>0,"native F never fired before protection")
            -- Activate the actual component deadline and replicated flag while
            -- the crossbow is still equipped; the regular quarter-second Tick
            -- may subsequently unequip it through its own native hand guard.
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)==crossbow,"fixture lost weapon before protection")
            k.state.deadlines.protect=G.GetTime()+30
            actor._klbq_protect:set(true)
            assert(not k:CanUseHands(),"native protected component allows hands")
            actor.components.playercontroller:DoAttackButton(victim)
        end)
        return function()
            assert(protected,"protection stage did not run")
            eq(#launches,protected)
            assert(k:IsProtected(),"native protection expired too early")
            assert(actor.sg.currentstate.name~="klbq_crossbow_attack","protection retained firing state")
            assert(not actor.components.inventory:Equip(crossbow),"native protected inventory equipped hands")
            held(false)
        end
    end,1.8)

    Scoped("crossbow native Z projectile and S1 keep launch snapshot after swap",function(Spawn,Actor,Victim,Observe,Fire,After)
        local actor,held=Actor("klbq_kanami")
        local crossbow,spear=Spawn("klbq_crossbow"),Spawn("spear")
        local victim=Victim(actor)
        victim.components.health:SetMaxHealth(1000);victim.components.health:SetPercent(1)
        local k=assert(actor.components.klbq_kanami)
        actor.components.inventory:Equip(crossbow)
        local launches=Observe(crossbow)
        local changed=false
        crossbow:ListenForEvent("weapononprojectilelaunched",function()
            held(false)
            if not changed then
                changed=true
                assert(k:IsZ(),"Z was not active at native launch")
                assert(k:Cast("z"),"native Z toggle off failed")
                actor.components.inventory:Equip(spear)
            end
        end)
        After(.05,function() assert(k:Cast("z"),"native Z toggle on failed") end)
        After(.8,function()
            k.state.deadlines.passive=nil
            Fire(actor,victim,held)
        end)
        return function()
            eq(#launches,1)
            assert(changed and not k:IsZ(),"snapshot fixture did not change Z after launch")
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)==spear,"snapshot fixture did not swap weapon")
            -- Native main hit 7.5; S1 launch power5*1.5=7.5, then 3% of
            -- post-main-hit HP992.5*1.5=44.6625. No extra physical damage.
            eq(victim.components.health.currenthealth,1000-7.5-7.5-(1000-7.5)*.03*1.5)
            assert(k:Remaining("passive")>0,"native projectile did not trigger shared S1 cooldown")
        end
    end,1.5)
end
