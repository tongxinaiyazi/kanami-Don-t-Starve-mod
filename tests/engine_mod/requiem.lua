-- Task-owned native checks. Input fixtures supply control state only; native
-- PlayerController, ActionPicker, Locomotor, SG, Weapon and Combat do the work.
local G=GLOBAL
local assert,pcall,tostring=G.assert,G.pcall,G.tostring
local ipairs,pairs,math=G.ipairs,G.pairs,G.math

function RunKanamiRequiemChecks(context)
    if context.mode~="base" then return end
    local p,check,eq=context.player,context.check,context.eq
    local x,_,z=p.Transform:GetWorldPosition()
    local centers={}

    local function Center()
        local map=G.TheWorld.Map
        for radius=64,192,16 do
            for step=0,31 do
                local angle=step*math.pi/16
                local ax,az=x+radius*math.cos(angle),z+radius*math.sin(angle)
                local valid=true
                if #G.TheSim:FindEntities(ax,0,az,20,{"_combat"},{"INLIMBO"})>0 then valid=false end
                for _,center in ipairs(centers) do
                    if (ax-center[1])^2+(az-center[2])^2<24*24 then valid=false;break end
                end
                if valid then
                    for _,offset in ipairs({{0,0},{6,0},{-6,0},{0,6},{0,-6},{12,0}}) do
                        local tx,tz=ax+offset[1],az+offset[2]
                        if not (map:IsInMapBounds(tx,0,tz) and map:IsVisualGroundAtPoint(tx,0,tz)
                            and map:IsPassableAtPoint(tx,0,tz)
                            and not map:IsGroundTargetBlocked(G.Vector3(tx,0,tz))) then valid=false;break end
                    end
                end
                if valid then centers[#centers+1]={ax,az};return ax,az end
            end
        end
        G.error("no isolated native Requiem land fixture",0)
    end

    local function Scoped(name,setup,duration)
        assert(duration<=5,"native Requiem scope must clean up within five seconds")
        local owned,seen,tasks={},{},{}
        local problem
        local function Track(inst)
            assert(inst,"native Requiem fixture failed to spawn")
            if not seen[inst] then seen[inst]=true;owned[#owned+1]=inst end
            return inst
        end
        local ax,az
        local function Spawn(prefab,dx,dz)
            if ax==nil then ax,az=Center() end
            local inst=Track(G.SpawnPrefab(prefab))
            inst.Transform:SetPosition(ax+(dx or 0),0,az+(dz or 0))
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
        local function Actor()
            local actor=Spawn("wilson")
            actor.userid="KANAMI_REQUIEM_"..tostring(actor.GUID)
            if not actor.components.playercontroller then actor:AddComponent("playercontroller") end
            if not actor.components.playeractionpicker then actor:AddComponent("playeractionpicker") end
            -- Synthetic actors never run player_common's OnSetOwner. Supply
            -- its exact living-player baseline filter so HAUNT cannot become
            -- a spurious meaningful RMB action in this connectionless fixture.
            actor.components.playeractionpicker:PushActionFilter(function(_,action)return not action.ghost_exclusive end,G.ACTION_FILTER_PRIORITIES.default)
            local pc=actor.components.playercontroller
            assert(pc.locomotor==actor.components.locomotor,"native Requiem controller lacks locomotor")
            assert(pc.classified and pc.classified.iscontrollerenabled,"native Requiem classified missing")
            pc.classified.iscontrollerenabled:set(true)
            -- Synthetic controllers have no physical key input. Supplying an
            -- unheld attack prevents unintended auto-repeat between test clicks.
            local oldpressed=pc.IsControlPressed
            pc.IsControlPressed=function(self,control)
                if control==G.CONTROL_ATTACK then return false end
                return oldpressed(self,control)
            end
            local sword=Spawn("klbq_requiem")
            actor.components.inventory:Equip(sword)
            assert(actor.components.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)==sword,"native Requiem equip failed")
            return actor,sword,pc
        end
        local function Victim(dx,dz)
            local victim=Spawn("hound",dx,dz)
            -- Fresh prefabs can still be awaiting their first engine wake and
            -- have no brain yet. Preserve the public stop reason across that
            -- deferred creation so radius targets cannot later walk inward.
            victim:StopBrain("klbq_engine_target")
            victim.components.combat:SetTarget(nil)
            victim.components.locomotor:Stop()
            victim.components.health:SetMaxHealth(1000)
            victim.components.health:SetPercent(1)
            return victim
        end
        local function SweepAction(actor,pos,target)
            local actions=actor.components.playeractionpicker:GetRightClickActions(pos,target)
            for _,act in ipairs(actions) do
                if act.action==G.ACTIONS.KLBQ_REQUIEM_SWEEP then return act end
            end

        end
        local function Cleanup()
            for _,task in ipairs(tasks) do task:Cancel() end
            for _,inst in ipairs(owned) do
                if inst:IsValid() and inst.components.inventory then
                    for _,item in ipairs(inst.components.inventory:FindItems(function() return true end)) do
                        if item:IsValid() then item:Remove() end
                    end
                    local active=inst.components.inventory:GetActiveItem()
                    if active and active:IsValid() then active:Remove() end
                end
            end
            for i=#owned,1,-1 do if owned[i]:IsValid() then owned[i]:Remove() end end
        end
        local function Finish(verify)
            check(name,function()
                local ok,err=pcall(function()
                    assert(problem==nil,"async native Requiem fixture: "..tostring(problem))
                    verify()
                end)
                local cleanok,cleanerr=pcall(Cleanup)
                assert(ok,tostring(err))
                assert(cleanok,"native Requiem cleanup: "..tostring(cleanerr))
            end)
        end
        local ok,verify=pcall(setup,Spawn,Actor,Victim,SweepAction,After,Track)
        if not ok then Finish(function() G.error(verify,0) end)
        else G.TheWorld:DoTaskInTime(duration,function() Finish(verify) end) end
    end

    Scoped("requiem native predicted walk handoff preserves remote normal attack",function(_,Actor,Victim,_,After)
        local actor,sword,pc=Actor()
        local victim=Victim(1.5,0)
        local hits=0
        sword:ListenForEvent("weapononattack",function() hits=hits+1 end)
        After(.25,function()
            local ax,_,az=actor.Transform:GetWorldPosition()
            pc.remote_authority=true;pc.remote_predicting=true
            pc:OnRemotePredictWalking(ax,az,true,true,nil,nil,false)
            pc.directwalking=true;pc.predictwalking=true
            pc:OnRemoteAttackButton(victim,false,false,false,true)
            assert(pc.attack_buffer,"native remote normal attack has no buffered action")
            assert(pc.attack_buffer.forced and pc.attack_buffer._predictpos,"native normal attack lost its forced position contract")
            pc:OnUpdate(0)
            assert(pc.remote_vector.y==0 or pc.remote_vector.y==5,"native normal action did not settle the predicted walk")
            assert(actor.sg.currentstate.name=="klbq_requiem_attack","native predicted walk cancelled remote normal attack: state="
                ..actor.sg.currentstate.name.." vector="..tostring(pc.remote_vector.y)
                .." forward="..tostring(pc.locomotor:WantsToMoveForward())
                .." direct="..tostring(pc.directwalking).." predict="..tostring(pc.predictwalking))
        end)
        return function()
            eq(hits,1);eq(victim.components.health.currenthealth,949)
            eq(sword.components.finiteuses:GetUses(),599)
        end
    end,1.2)

    Scoped("requiem native F and repeated left clicks preserve first hit and .8s cooldown",function(_,Actor,Victim,_,After)
        local actor,sword,pc=Actor()
        local victim=Victim(1.5,0)
        local starts,hits={},{}
        sword:ListenForEvent("weapononattack",function(_,data)
            assert(data.attacker==actor and data.target==victim,"native normal attack source changed")
            hits[#hits+1]=G.GetTime()
        end)
        After(.25,function()
            starts[1]=G.GetTime()
            actor.components.locomotor:Stop()
            pc:DoAttackButton(victim)
            assert(actor.sg.currentstate.name=="klbq_requiem_attack","native F did not enter Requiem attack")
            assert(actor.sg.statemem.attacktarget==victim,"native ATTACK repeat suppression lost attacktarget")
            eq(actor._klbq_requiem_nextattack-starts[1],.8)
            eq(actor.replica.combat:MinAttackPeriod(),.8)
        end)
        After(.35,function()
            local action
            for _,act in ipairs(actor.components.playeractionpicker:GetLeftClickActions(victim:GetPosition(),victim)) do
                if act.action==G.ACTIONS.ATTACK then action=act;break end
            end
            assert(action,"native left picker did not offer ATTACK")
            pc:DoAction(action)
        end)
        After(.62,function()
            eq(#hits,1);eq(victim.components.health.currenthealth,949)
            eq(sword.components.finiteuses:GetUses(),599)
            assert(hits[1]-starts[1]>=.3-G.FRAMES/2,"normal hit preceded native timeline")
        end)
        After(1,function()
            assert(actor.components.combat:InCooldown(),"normal cooldown ended before .8s")
            pc:DoAttackButton(victim)
        end)
        After(1.55,function()
            assert(not actor.components.combat:InCooldown(),"normal cooldown exceeded .8s")
            starts[2]=G.GetTime();pc:DoAttackButton(victim)
        end)
        return function()
            eq(#hits,2);eq(victim.components.health.currenthealth,898)
            eq(sword.components.finiteuses:GetUses(),598)
            assert(starts[2]-starts[1]>=.8,"native normal starts ignored .8s period")
            assert(actor.sg.currentstate.name~="klbq_requiem_attack","normal recovery did not finish")
        end
    end,2.6)

    Scoped("requiem native remote right click is self centered 360 degrees with .6s windup and 2s period",function(Spawn,Actor,Victim,SweepAction,After)
        local actor,sword,pc=Actor()
        local victims={Victim(2.5,0),Victim(-2.5,0),Victim(0,4.2),Victim(0,-4.2)}
        local outside,distant=Victim(4.8,0),Victim(12,0)
        local follower=Victim(0,-2.5)
        if not follower.components.follower then follower:AddComponent("follower") end
        follower.components.follower:SetLeader(actor)
        local friend=Spawn("wilson",-1.5,1.5)
        friend.components.health:SetMaxHealth(1000);friend.components.health:SetPercent(1)
        local hits=0
        local labels={[outside]="outside",[distant]="distant",[follower]="follower",[friend]="friend"}
        for index,victim in ipairs(victims) do labels[victim]="ring"..tostring(index) end
        sword:ListenForEvent("weapononattack",function(_,data)
            hits=hits+1
            local target=data and data.target
            local px,_,pz=actor.Transform:GetWorldPosition()
            G.print("[KANAMI_REQUIEM_TARGET]",hits,target and (labels[target] or target.prefab),
                target and math.sqrt(actor:GetDistanceSqToInst(target)),"actor",px,pz)
        end)
        local start
        local function RemoteSweep()
            local pos=distant:GetPosition()
            local action=assert(SweepAction(actor,pos,distant),"native right picker did not offer self-centered sweep")
            assert(action.target==nil,"cursor target still anchors the sweep")
            assert(pc.handler==nil,"remote fixture unexpectedly owns a local input handler")
            pc:OnRemoteRightClick(action.action.code,pos,distant,0,true,0,true,action.action.mod_name)
            assert(actor.sg.currentstate.name=="klbq_requiem_sweep","remote right click did not enter Requiem sweep")
        end
        After(.25,function()
            local ax,_,az=actor.Transform:GetWorldPosition()
            pc.remote_authority=true;pc.remote_predicting=true
            pc:OnRemotePredictWalking(ax,az,true,true,nil,nil,false)
            pc.directwalking=true;pc.predictwalking=true
            start=G.GetTime();RemoteSweep()
            eq(pc.remote_vector.y,5)
            eq(actor._klbq_requiem_nextsweep-start,2)
        end)
        After(.75,function()
            eq(hits,0);eq(sword.components.finiteuses:GetUses(),600)
            for _,victim in ipairs(victims) do eq(victim.components.health.currenthealth,1000) end
        end)
        After(.98,function()
            eq(hits,4);eq(sword.components.finiteuses:GetUses(),599)
            for _,victim in ipairs(victims) do eq(victim.components.health.currenthealth,949) end
            eq(outside.components.health.currenthealth,1000);eq(distant.components.health.currenthealth,1000)
            eq(follower.components.health.currenthealth,1000);eq(friend.components.health.currenthealth,1000)
        end)
        After(1.3,function()
            assert(SweepAction(actor,distant:GetPosition(),distant)==nil,"right click bypassed 2s cooldown")
            local action=G.ACTIONS.KLBQ_REQUIEM_SWEEP
            pc:OnRemoteRightClick(action.code,distant:GetPosition(),distant,0,true,0,true,action.mod_name)
            eq(hits,4);eq(sword.components.finiteuses:GetUses(),599)
            -- Native RMB may fall back to walking when sweep is unavailable.
            -- Cancel that fixture input before the second centered swing;
            -- movement can cancel recovery but must retain its deadline.
            actor.components.locomotor:Stop();actor.components.locomotor:Clear()
        end)
        After(2.15,function()
            assert(G.GetTime()<actor._klbq_requiem_nextsweep,"remote sweep cooldown ended before two seconds")
            assert(SweepAction(actor,distant:GetPosition(),distant)==nil,"interrupted recovery reset sweep cooldown")
        end)
        After(2.4,function()
            assert(G.GetTime()-start>=2,"second remote sweep started early")
            RemoteSweep()
        end)
        return function()
            eq(hits,8);eq(sword.components.finiteuses:GetUses(),598)
            for _,victim in ipairs(victims) do eq(victim.components.health.currenthealth,898) end
            eq(outside.components.health.currenthealth,1000);eq(distant.components.health.currenthealth,1000)
            eq(follower.components.health.currenthealth,1000);eq(friend.components.health.currenthealth,1000)
        end
    end,3.3)

    Scoped("requiem native ground right click PushAction enters delayed sweep",function(_,Actor,Victim,SweepAction,After)
        local actor,sword=Actor()
        local victim=Victim(-3,0)
        local start
        After(.25,function()
            local pos=actor:GetPosition()
            local action=assert(SweepAction(actor,pos,nil),"native ground right picker did not offer sweep")
            start=G.GetTime()
            actor.components.locomotor:PushAction(action,true)
            assert(actor.sg.currentstate.name=="klbq_requiem_sweep","native PushAction did not enter Requiem sweep")
        end)
        After(.75,function() eq(victim.components.health.currenthealth,1000) end)
        After(1,function()
            eq(victim.components.health.currenthealth,949);eq(sword.components.finiteuses:GetUses(),599)
        end)
        return function()
            assert(start and G.GetTime()-start>=2,"local ground sweep did not span full recovery")
            assert(actor.sg.currentstate.name=="idle","native local sweep recovery did not end")
            eq(victim.components.health.currenthealth,949);eq(sword.components.finiteuses:GetUses(),599)
        end
    end,2.5)
end
