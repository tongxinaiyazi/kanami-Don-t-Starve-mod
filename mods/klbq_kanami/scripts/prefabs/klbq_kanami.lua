local MakePlayerCharacter=require("prefabs/player_common")
local Visual=require("klbq_kanami/visual")
local Chef=require("klbq_kanami/chef")
local Rules=require("klbq_kanami/rules")
local Curse=require("klbq_kanami/curse")
local assets={Asset("ANIM","anim/klbq_kanami.zip"),Asset("ANIM","anim/klbq_kanami_string.zip"),Asset("ANIM","anim/klbq_kanami_actions.zip"),Asset("ANIM","anim/ghost_klbq_kanami_build.zip")}
local prefabs={"klbq_finale","klbq_ammo_heart","klbq_ammo_fate","klbq_ammo_doom","klbq_kanami_domain_fx","klbq_kanami_domain_cast_fx","klbq_kanami_tracer_fx","klbq_kanami_revive_fx","impact"}
local function common(inst)
    inst:AddTag("klbq_kanami")
    Curse.Common(inst)
    Chef.Common(inst)
    Visual.Bind(inst)
    inst.MiniMapEntity:SetIcon("klbq_kanami.tex")
    for _,name in ipairs({"string","z","x","protect","wet","waterwalk"}) do
        inst["_klbq_"..name]=net_bool(inst.GUID,"klbq_kanami."..name,"klbq_statusdirty")
    end
    inst._klbq_memory_sequence = net_bool(inst.GUID, "klbq_kanami.memory_sequence", "klbq_memorysequencedirty")
    for _,name in ipairs({"ztime","xtime","zcd","xcd","revive","passivecd","shotcd","ammo"}) do
        inst["_klbq_"..name]=net_ushortint(inst.GUID,"klbq_kanami."..name,"klbq_statusdirty")
    end
    inst._klbq_hitdamage=net_float(inst.GUID,"klbq_kanami.hitdamage")
    inst._klbq_hittarget=net_entity(inst.GUID,"klbq_kanami.hittarget")
    inst._klbq_hitseq=net_byte(inst.GUID,"klbq_kanami.hitseq","klbq_hitdirty")
    inst:ListenForEvent("klbq_hitdirty",function()
        local target=inst._klbq_hittarget:value()
        local amount=inst._klbq_hitdamage:value()
        if inst==ThePlayer and inst.HUD and target and target:IsValid() and amount>0 then
            inst.HUD:ShowPopupNumber(math.floor(amount*10+.5)/10,32,target:GetPosition(),40,{1,.65,.85,1},false)
        end
    end)
    local laststring,lastprotect,lastwaterwalk,originalmask
    local function ConfigurePrediction(stringed,waterwalk)
        local loco=inst.components.locomotor
        if not loco then return end
        if not loco._klbq_prediction then
            loco._klbq_prediction={}
            Rules.ConfigureCaveGlide(loco)
            local old=loco.GetSpeedMultiplier
            loco.GetSpeedMultiplier=function(self,...)
                local existing=old(self,...)
                if inst:HasTag("playerghost") then return existing end
                Rules.RefreshCaveCollisionMask(inst,inst._klbq_string:value() and inst._klbq_waterwalk:value())
                return Rules.Speed(existing,inst._klbq_string:value(),false,inst._klbq_wet:value())
            end
        end
        local state=loco._klbq_prediction
        if waterwalk and not state.waterwalk then
            state.allowocean=loco.pathcaps and loco.pathcaps.allowocean or false
            loco:AdjustPathCaps(true,"allowocean")
        elseif not waterwalk and state.waterwalk then
            loco:AdjustPathCaps(state.allowocean,"allowocean")
        end
        state.waterwalk=waterwalk
    end
    local function StringVisual()
        local stringed=inst._klbq_string:value() and not inst:HasTag("playerghost")
        local waterwalk=stringed and inst._klbq_waterwalk:value()
        local protect=inst._klbq_protect:value()
        if stringed~=laststring then Visual.StringBuild(inst,stringed);Visual.HideEquipment(inst) end
        if not TheWorld.ismastersim then ConfigurePrediction(stringed,waterwalk) end
        if not TheWorld.ismastersim and stringed and waterwalk and laststring then
            Rules.RefreshCaveCollisionMask(inst,true)
        end
        if not TheWorld.ismastersim and (stringed~=laststring or waterwalk~=lastwaterwalk) then
            if stringed then
                if not laststring then originalmask=inst.Physics:GetCollisionMask() end
                inst.Physics:SetCollisionMask(waterwalk and COLLISION.GROUND or COLLISION.WORLD)
            else
                if laststring and not inst:HasTag("playerghost") then
                    if originalmask then inst.Physics:SetCollisionMask(originalmask) else ChangeToCharacterPhysics(inst) end
                end
            end
        end
        if stringed~=laststring or protect~=lastprotect then
            inst.AnimState:SetMultColour(stringed and .82 or 1,stringed and .66 or 1,1,protect and .3 or (stringed and .55 or 1))
        end
        laststring=stringed;lastprotect=protect;lastwaterwalk=waterwalk
    end
    inst:ListenForEvent("klbq_statusdirty",StringVisual)
    if not TheWorld.ismastersim then
        inst:ListenForEvent("newstate",function()
            Rules.RefreshCaveCollisionMask(inst,inst._klbq_string:value() and inst._klbq_waterwalk:value()
                and not inst:HasTag("playerghost"))
        end)
        local pending
        local function RefreshPrediction()
            if pending then return end
            -- Vanilla emits enablemovementprediction BEFORE creating locomotor.
            pending=inst:DoTaskInTime(0,function() pending=nil;StringVisual() end)
        end
        inst:ListenForEvent("enablemovementprediction",RefreshPrediction)
        inst:ListenForEvent("playeractivated",RefreshPrediction)
        RefreshPrediction()
    end
end
local function master(inst)
    inst.starting_inventory={"klbq_singularity"}
    inst.soundsname="willow"
    inst.components.health:SetMaxHealth(75)
    inst.components.hunger:SetMax(75)
    inst.components.sanity:SetMax(200)
    inst.components.combat:SetDefaultDamage(34)
    inst.ghostbuild="ghost_klbq_kanami_build"
    inst:AddComponent("klbq_kanami")
    Curse.Master(inst)
    inst:ListenForEvent("ms_becameghost",function()
        inst.AnimState:SetBuild("ghost_klbq_kanami_build")
    end)
    inst:ListenForEvent("ms_respawnedfromghost",function()
        inst.AnimState:SetBuild("klbq_kanami")
    end)
end
return MakePlayerCharacter("klbq_kanami",prefabs,assets,common,master,{})
