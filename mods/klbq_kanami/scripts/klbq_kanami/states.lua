local M={}
local function Pack(...) return {n=select("#",...),...} end
local function Stringed(inst)
    return inst.prefab=="klbq_kanami" and inst._klbq_string and inst._klbq_string:value()
end
local function OrdinaryBody(inst)
    local rider=inst.replica and inst.replica.rider or inst.components and inst.components.rider
    return not (rider and rider:IsRiding()) and not (inst.HasTag and inst:HasTag("wereplayer"))
end
function M.Install(env)
    local G=env.GLOBAL
    for _,graph in ipairs({"wilson","wilson_client"}) do
        local client=graph=="wilson_client"
        for _,entry in ipairs({{"klbq_shoot","kanami_shoot",.55},{"klbq_string_enter","kanami_string_enter",.3},{"klbq_string_exit","kanami_string_exit",.3},{"klbq_cast","kanami_cast",.5},{"klbq_revive","kanami_revive",.8}}) do
            local name,anim,duration=unpack(entry)
            env.AddStategraphState(graph,G.State{
                name=name,tags={"busy","nopredict"},
                onenter=function(inst)
                    inst.components.locomotor:Stop()
                    inst.AnimState:PlayAnimation(name=="klbq_shoot" and inst.prefab~="klbq_kanami" and "dart" or anim)
                    if name=="klbq_shoot" then
                        local state=inst.sg.currentstate
                        if client then inst:PerformPreviewBufferedAction() else inst:PerformBufferedAction() end
                        -- Backlash can synchronously enter native death. Keep
                        -- that state's timing and drop/ghost transition intact.
                        if inst.sg.currentstate~=state then return end
                    elseif name=="klbq_revive" and not client then
                        local fx=G.SpawnPrefab("klbq_kanami_revive_fx")
                        if fx then fx.entity:SetParent(inst.entity) end
                    end
                    inst.sg:SetTimeout(duration)
                end,
                ontimeout=function(inst) inst.sg:GoToState("idle") end,
                events={G.EventHandler("animover",function(inst) inst.sg:GoToState("idle") end)},
            })
        end
        env.AddStategraphPostInit(graph,function(sg)
            for _,name in ipairs({"attack","attack_recoil","doshortaction","doshortaction_fast","hit","hit_souloverload"}) do
                local state=sg.states[name]
                if state and state.onenter then
                    local old=state.onenter
                    state.onenter=function(inst,...)
                        local before=inst.sg and inst.sg.currentstate
                        local result=Pack(old(inst,...))
                        if inst.prefab=="klbq_kanami" and OrdinaryBody(inst)
                            and (not inst.sg or inst.sg.currentstate==before) then
                            for _,anim in ipairs({"atk_pre","spearjab_pre","punch","toolpunch","atk_recoil","pickup","pickup_pst","hit"}) do
                                if inst.AnimState:IsCurrentAnimation(anim) then
                                    inst.AnimState:PlayAnimation("kanami_"..anim)
                                    if string.sub(anim,-4)=="_pre" then
                                        local tail=string.sub(anim,1,-5)..(client and "_lag" or "")
                                        inst.AnimState:PushAnimation("kanami_"..tail,false)
                                    elseif anim=="pickup" then
                                        inst.AnimState:PushAnimation(client and "kanami_pickup_lag" or "kanami_pickup_pst",false)
                                    end
                                    break
                                end
                            end
                        end
                        return unpack(result,1,result.n)
                    end
                end
            end
            for _,name in ipairs({"chop_start","chop","mine_start","mine","mine_recoil","dig_start","dig"}) do
                local state=sg.states[name]
                if state and state.onenter then
                    local old=state.onenter
                    state.onenter=function(inst,...)
                        local before=inst.sg and inst.sg.currentstate
                        local result=Pack(old(inst,...))
                        if inst.prefab=="klbq_kanami" and OrdinaryBody(inst)
                            and (not inst.sg or inst.sg.currentstate==before) then
                            for _,anim in ipairs({"chop_pre","chop_loop","pickaxe_pre","pickaxe_loop","pickaxe_recoil","shovel_pre","shovel_loop"}) do
                                if inst.AnimState:IsCurrentAnimation(anim) then
                                    inst.AnimState:PlayAnimation("kanami_"..anim)
                                    if client and string.sub(anim,-4)=="_pre" then
                                        inst.AnimState:PushAnimation("kanami_"..string.sub(anim,1,-5).."_lag",false)
                                    end
                                    break
                                end
                            end
                        end
                        return unpack(result,1,result.n)
                    end
                end
            end
            local feast=sg.states.winters_feast_eat
            if feast and feast.onenter then
                local old=feast.onenter
                feast.onenter=function(inst,...)
                    local before=inst.sg and inst.sg.currentstate
                    local result=Pack(old(inst,...))
                    if inst.prefab=="klbq_kanami" and OrdinaryBody(inst)
                        and (not inst.sg or inst.sg.currentstate==before)
                        and inst.AnimState:IsCurrentAnimation("feast_eat_pre_pre") then
                        inst.AnimState:PlayAnimation("kanami_feast_eat_pre_pre")
                        if client then
                            inst.AnimState:PushAnimation("kanami_feast_eat_lag",false)
                        else
                            for _,anim in ipairs({"pre","loop","loop","pst"}) do
                                inst.AnimState:PushAnimation("kanami_feast_eat_"..anim,false)
                            end
                        end
                    end
                    return unpack(result,1,result.n)
                end
            end
            -- Preserve the native meal timing and prediction queue while
            -- binding lifted arms to the costume shoulders, not beside the head.
            for _,name in ipairs({"eat","quickeat","refuseeat"}) do
                local state=sg.states[name]
                if state and state.onenter then
                    local old=state.onenter
                    state.onenter=function(inst,...)
                        local before=inst.sg and inst.sg.currentstate
                        local result=Pack(old(inst,...))
                        if inst.prefab=="klbq_kanami" and OrdinaryBody(inst) and (not inst.sg or inst.sg.currentstate==before) then
                            local prefix=inst.AnimState:IsCurrentAnimation("eat_pre") and "eat"
                                or (inst.AnimState:IsCurrentAnimation("quick_eat_pre") and "quick_eat" or nil)
                            if prefix then
                                inst.AnimState:PlayAnimation("kanami_"..prefix.."_pre")
                                inst.AnimState:PushAnimation("kanami_"..prefix..(client and "_lag" or ""),false)
                            elseif inst.AnimState:IsCurrentAnimation("refuseeat") then
                                inst.AnimState:PlayAnimation("kanami_refuseeat")
                            end
                        end
                        return unpack(result,1,result.n)
                    end
                end
            end
            for _,name in ipairs({"idle","funnyidle","talk","run_start","run","run_stop","run_gallop_start","run_gallop","run_monkey_start","run_monkey"}) do
                local state=sg.states[name]
                if state then
                    local loop=name=="idle" or name=="talk" or name=="run" or name=="run_gallop" or name=="run_monkey"
                    for _,callback in ipairs({"onenter","onupdate"}) do
                        local old=state[callback]
                        if old or (callback=="onupdate" and name=="idle") then state[callback]=function(inst,...)
                            local before=inst.sg and inst.sg.currentstate
                            local result=old and Pack(old(inst,...)) or {n=0}
                            if (not inst.sg or inst.sg.currentstate==before) and Stringed(inst)
                                and not inst.AnimState:IsCurrentAnimation("kanami_string_idle") then
                                inst.AnimState:PlayAnimation("kanami_string_idle",loop)
                            elseif (callback=="onenter" or name=="idle") and inst.prefab=="klbq_kanami"
                                and OrdinaryBody(inst) and not Stringed(inst) and (not inst.sg or inst.sg.currentstate==before) then
                                -- The costume shoulder is narrower than the
                                -- native coat. Only replace ordinary on-foot
                                -- run clips; preserve riding/other forms.
                                -- idle(pushanim) has queued a loop after the
                                -- current transition. Do not clear that queue.
                                -- Bind it when the loop actually begins.
                                local clips=name=="idle" and {"idle_loop","pickaxe_pst","shovel_pst"}
                                    or name=="funnyidle" and {"idle_inaction","idle_inaction_sanity"}
                                    or name=="talk" and {"dial_loop"}
                                    or {"run_pre","run_loop","run_pst","careful_walk_pre","careful_walk","careful_walk_pst","idle_walk_pre","idle_walk","idle_walk_pst"}
                                for _,anim in ipairs(clips) do
                                    if inst.AnimState:IsCurrentAnimation(anim) then
                                        inst.AnimState:PlayAnimation("kanami_"..anim,anim=="run_loop" or anim=="idle_loop" or anim=="dial_loop" or anim=="careful_walk" or anim=="idle_walk")
                                        if anim=="pickaxe_pst" or anim=="shovel_pst" then
                                            inst.AnimState:PushAnimation("kanami_idle_loop",true)
                                        end
                                        break
                                    end
                                end
                            end
                            return unpack(result,1,result.n)
                        end end
                    end
                    -- Gliding paper has no footfalls or humanoid gait events.
                    for _,event in ipairs(state.timeline or {}) do
                        local old=event.fn
                        if old then event.fn=function(inst,...)
                            if not Stringed(inst) then return old(inst,...) end
                        end end
                    end
                end
            end
        end)
    end
end
return M
