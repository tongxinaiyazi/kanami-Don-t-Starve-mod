local assets={Asset("ANIM","anim/klbq_crossbow.zip"),Asset("ANIM","anim/swap_klbq_crossbow.zip"),
    Asset("ANIM","anim/klbq_kanami_actions.zip"),
    Asset("ANIM","anim/klbq_kanami_fx.zip"),Asset("ATLAS","images/klbq_kanami_items.xml"),
    Asset("IMAGE","images/klbq_kanami_items.tex")}

local function equip(inst,owner)
    owner.AnimState:OverrideSymbol("swap_object","swap_klbq_crossbow","swap_object")
    owner.AnimState:Show("ARM_carry");owner.AnimState:Hide("ARM_normal")
    local combat=owner.components.combat
    if combat then
        -- Weapon ranges are offsets added to the current character's base
        -- range in native Combat/GetAttackRange (DEFAULT_ATTACK_RANGE is 2).
        inst.components.weapon:SetRange(12-combat.attackrange,12-combat.hitrange)
    end
end
local function unequip(inst,owner)
    owner.AnimState:Hide("ARM_carry");owner.AnimState:Show("ARM_normal")
end
local function fn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeInventoryPhysics(inst)
    inst.AnimState:SetBank("klbq_crossbow");inst.AnimState:SetBuild("klbq_crossbow");inst.AnimState:PlayAnimation("idle")
    inst:AddTag("klbq_crossbow");inst:AddTag("rangedweapon");inst:AddTag("weapon")
    MakeInventoryFloatable(inst,"med",.1,.65)
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst:AddComponent("inspectable")
    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.atlasname="images/klbq_kanami_items.xml"
    inst:AddComponent("equippable")
    inst.components.equippable:SetOnEquip(equip);inst.components.equippable:SetOnUnequip(unequip)
    inst:AddComponent("weapon")
    inst.components.weapon:SetDamage(0)
    inst.components.weapon:SetRange(12-TUNING.DEFAULT_ATTACK_RANGE)
    inst.components.weapon:SetProjectile("klbq_crossbow_bolt")
    inst:AddComponent("planardamage");inst.components.planardamage:SetBaseDamage(5)
    MakeHauntableLaunch(inst)
    return inst
end

local function hit(inst)
    local fx=SpawnPrefab("impact")
    if fx then fx.Transform:SetPosition(inst.Transform:GetWorldPosition()) end
    inst:Remove()
end
local function UpdateHitHeight(inst,target)
    if target and target:IsValid() then
        local _,y=inst.Transform:GetWorldPosition()
        local _,ty=target.Transform:GetWorldPosition()
        local radius=target:GetPhysicsRadius(0)
        -- Native projectiles test 3D distance. Keep the original .5-unit
        -- horizontal tolerance when the bolt is raised to the weapon's height.
        local horizontal=radius+.5
        inst.components.projectile:SetHitDist(math.sqrt(horizontal*horizontal+(y-ty)*(y-ty))-radius)
    end
end
local function thrown(inst,owner,target,attacker)
    -- Native Projectile:Hit normally recovers a ranged weapon's attacker from
    -- its *current* inventory owner. A fired bolt must retain its real shooter
    -- when the crossbow is dropped, destroyed, or traded during flight.
    inst.components.projectile.owner=attacker
        or (owner and owner.components.combat and owner)
        or (owner and owner.components.inventoryitem and owner.components.inventoryitem.owner)
        or owner
    UpdateHitHeight(inst,target)
end
local function boltfn()
    local inst=CreateEntity()
    inst.entity:AddTransform();inst.entity:AddAnimState();inst.entity:AddNetwork()
    MakeProjectilePhysics(inst)
    inst.AnimState:SetBank("klbq_kanami_fx");inst.AnimState:SetBuild("klbq_kanami_fx")
    inst.AnimState:PlayAnimation("tracer",true);inst.AnimState:SetLightOverride(.6)
    inst.Transform:SetScale(.28,.28,.28)
    inst:AddTag("projectile");inst:AddTag("weapon");inst:AddTag("NOCLICK")
    inst.entity:SetPristine()
    if not TheWorld.ismastersim then return inst end
    inst.persists=false
    -- Its entire bounded flight is authoritative, including a dedicated
    -- server without a nearby awake human (the projectile expires in 3s).
    inst.entity:SetCanSleep(false)
    -- Projectile:Hit uses this bolt as its native weapon and the captured
    -- player as owner. Planar defense/armor/health limits remain native.
    inst:AddComponent("weapon");inst.components.weapon:SetDamage(0)
    inst:AddComponent("planardamage");inst.components.planardamage:SetBaseDamage(5)
    inst:AddComponent("projectile")
    inst.components.projectile:SetSpeed(45)
    inst.components.projectile:SetHoming(true)
    inst.components.projectile:SetLaunchOffset(Vector3(1.2,1.5,0))
    inst.components.projectile:SetHitDist(.5)
    inst.components.projectile:SetOnHitFn(hit)
    inst.components.projectile:SetOnThrownFn(thrown)
    inst.components.projectile:SetOnMissFn(inst.Remove)
    local onupdate=inst.components.projectile.OnUpdate
    inst.components.projectile.OnUpdate=function(self,dt)
        UpdateHitHeight(self.inst,self.target)
        return onupdate(self,dt)
    end
    inst:DoTaskInTime(3,inst.Remove)
    return inst
end
return Prefab("klbq_crossbow",fn,assets,{"klbq_crossbow_bolt"}),
    Prefab("klbq_crossbow_bolt",boltfn,assets,{"impact"})
