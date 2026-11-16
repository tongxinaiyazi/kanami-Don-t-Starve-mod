local assets={Asset("ANIM","anim/klbq_kanami_fx.zip"),Asset("ANIM","anim/reticuleaoe.zip")}
local function Make(name,anim,loop,ground,radius)
    local function fn()
        local inst=CreateEntity()
        inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
        inst:AddTag("FX");inst:AddTag("NOCLICK");inst:AddTag("NOBLOCK")
        if loop or ground then
            -- Use the game's calibrated world-space ring. A large hand-drawn
            -- note is not a boundary and cannot establish the real hit radius.
            inst.AnimState:SetBank("reticuleaoe");inst.AnimState:SetBuild("reticuleaoe")
            inst.AnimState:PlayAnimation("idle",true)
            local scale=radius and radius/4 or require("klbq_kanami/rules").DomainScale()
            -- OnGroundFixed applies a uniform Transform scale twice in the
            -- current renderer. Scale the art directly, keeping the entity
            -- transform at one; validated against markers 12 units away.
            inst.AnimState:SetScale(1.5*scale,1.5*scale)
            inst.AnimState:SetLightOverride(1)
            inst.AnimState:SetMultColour(.86,.4,1,.65)
            inst.AnimState:SetOrientation(ANIM_ORIENTATION.OnGroundFixed)
            inst.AnimState:SetLayer(LAYER_WORLD_BACKGROUND)
            inst.AnimState:SetSortOrder(3)
        else
            inst.AnimState:SetBank("klbq_kanami_fx");inst.AnimState:SetBuild("klbq_kanami_fx")
            inst.AnimState:PlayAnimation(anim,loop)
            inst.AnimState:SetLightOverride(.6)
        end
        inst.entity:SetPristine()
        if not TheWorld.ismastersim then return inst end
        inst.persists=false
        if not loop then inst:DoTaskInTime(radius and .5 or 1,inst.Remove) end
        return inst
    end
    return Prefab(name,fn,assets)
end
return Make("klbq_kanami_domain_fx","domain",true),Make("klbq_kanami_tracer_fx","tracer",false),Make("klbq_kanami_revive_fx","revive",false),Make("klbq_kanami_domain_cast_fx","domain_cast",false,true),Make("klbq_requiem_sweep","sweep",false,true,4.5)
