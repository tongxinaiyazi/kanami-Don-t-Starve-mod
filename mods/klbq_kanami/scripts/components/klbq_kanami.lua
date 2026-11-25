local Rules=require("klbq_kanami/rules")
local Damage=require("klbq_kanami/damage")
local Domain=require("klbq_kanami/domain")
local Visual=require("klbq_kanami/visual")
local unpack=unpack
local function Pack(...) return {n=select("#",...),...} end
local Kanami=Class(function(self,inst)
    self.inst=inst
    self.state=Rules.New()
    self.targets={}
    self:InstallHooks()
    self._death=function() self:OnDeath() end
    self._respawn=function() self:OnRespawn() end
    self._hit=function(_,data) self:OnHit(data) end
    self._moisture=function() self:Sync() end
    self._equipment=function() self:ApplyString();self:Sync() end
    self._movementstate=function() Rules.RefreshCaveCollisionMask(inst,self:CanStringWaterWalk()) end
    inst:ListenForEvent("death",self._death)
    inst:ListenForEvent("ms_respawnedfromghost",self._respawn)
    inst:ListenForEvent("onhitother",self._hit)
    inst:ListenForEvent("moisturedelta",self._moisture)
    inst:ListenForEvent("equip",self._equipment)
    inst:ListenForEvent("unequip",self._equipment)
    inst:ListenForEvent("newstate",self._movementstate)
    self.task=inst:DoPeriodicTask(.25,function() self:Tick() end)
    self:Sync()
end)
function Kanami:Remaining(key) return Rules.Remaining(self.state,key,GetTime()) end
function Kanami:IsZ() return self.state.zenabled==true and not self.state.dead end
function Kanami:IsX() return self:Remaining("x_active")>0 and not self.state.dead end
function Kanami:IsProtected() return self:Remaining("protect")>0 and not self.state.dead end
function Kanami:CanUseHands() return self.removed or not self:IsProtected() end
function Kanami:Alive() return not self.state.dead and not self.inst:HasTag("playerghost") and not self.inst.components.health:IsDead() end
function Kanami:IsMoist()
    local moisture=self.inst.components.moisture
    -- Native IsWet waits for the second wetness segment; any moisture blocks entry.
    return moisture~=nil and moisture:GetMoisture()>0
end
function Kanami:CanStringWaterWalk()
    if not self.state.string or not self:Alive() then return false end
    local inventory=self.inst.components.inventory
    for _,slot in pairs({EQUIPSLOTS.BACK,EQUIPSLOTS.BODY}) do
        local bag=inventory and inventory:GetEquippedItem(slot)
        if bag and bag.prefab=="klbq_singularity" and bag._klbq_eyeball and bag._klbq_eyeball:value() then return true end
    end
    return false
end
function Kanami:Sync()
    local inst=self.inst
    inst._klbq_string:set(self.state.string)
    inst._klbq_z:set(self:IsZ());inst._klbq_x:set(self:IsX());inst._klbq_protect:set(self:IsProtected())
    inst._klbq_wet:set(self:IsMoist())
    inst._klbq_waterwalk:set(self:CanStringWaterWalk())
    for field,key in pairs({ztime="z_active",xtime="x_active",zcd="z",xcd="x",revive="revive",passivecd="passive",shotcd="shot"}) do
        inst["_klbq_"..field]:set(math.ceil(self:Remaining(key)*10))
    end
    local weapon=inst.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
    local ammo=weapon and weapon.prefab=="klbq_finale" and weapon.components.container:GetItemInSlot(1)
    inst._klbq_ammo:set(ammo and ammo.components.stackable:StackSize() or 0)
end
function Kanami:SafePoint(x,y,z)
    local map=TheWorld.Map
    if not (map:IsInMapBounds(x,y,z) and not Rules.IsCaveVoid(map,x,y,z)
        and (self.inst:GetCurrentPlatform()~=nil or map:IsVisualGroundAtPoint(x,y,z))
        and map:IsPassableAtPoint(x,y,z) and not map:IsGroundTargetBlocked(Vector3(x,y,z))) then return false end
    local radius=self.inst:GetPhysicsRadius(.5)
    for _,obstacle in ipairs(TheSim:FindEntities(x,y,z,radius+(MAX_PHYSICS_RADIUS or 4),nil,{"INLIMBO","FX","DECOR","NOBLOCK"})) do
        if obstacle~=self.inst and obstacle.Physics and obstacle.Physics:IsActive()
            and checkbit(self.savedmask or COLLISION.OBSTACLES,obstacle.Physics:GetCollisionGroup()) then
            local ox,oy,oz=obstacle.Transform:GetWorldPosition()
            local r=radius+obstacle:GetPhysicsRadius(0)
            if (x-ox)^2+(z-oz)^2<r*r then return false end
        end
    end
    return true
end
function Kanami:SafeGroundPoint(point)
    if type(point)~="table" then return false end
    for i=1,3 do
        local n=point[i]
        if type(n)~="number" or n~=n or n<=-math.huge or n>=math.huge then return false end
    end
    local map=TheWorld.Map
    return not (map.IsInvalidTileAtPoint and map:IsInvalidTileAtPoint(unpack(point)))
        and map:IsVisualGroundAtPoint(unpack(point)) and self:SafePoint(unpack(point))
end
function Kanami:ReturnToSafeGround()
    if self:SafeGroundPoint(self.lastsafe) then
        local loco=self.inst.components.locomotor
        if loco.Stop then loco:Stop() end
        self.inst.Physics:Teleport(unpack(self.lastsafe))
        return true
    end
    return false
end
function Kanami:ApplyString()
    local inst=self.inst
    local enabled=self.state.string and self:Alive()
    local waterwalk=self:CanStringWaterWalk()
    local loco=inst.components.locomotor
    if enabled then
        if not self.stringapplied then self.savedmask=inst.Physics.GetCollisionMask and inst.Physics:GetCollisionMask() end
        -- WORLD includes the native land/ocean and boat walls; GROUND alone
        -- lets direct movement leave shore even with allowocean=false.
        -- Both masks omit entity obstacles so C still passes through walls.
        inst.Physics:SetCollisionMask(waterwalk and COLLISION.GROUND or COLLISION.WORLD)
        inst:AddTag("klbq_string")
    else
        if not inst:HasTag("playerghost") and self.stringapplied then
            if self.savedmask then inst.Physics:SetCollisionMask(self.savedmask) else ChangeToCharacterPhysics(inst) end
        end
        inst:RemoveTag("klbq_string")
    end
    if waterwalk and not self.waterwalkapplied then
        self.savedallowocean=loco.pathcaps and loco.pathcaps.allowocean or false
        loco:AdjustPathCaps(true,"allowocean")
    elseif not waterwalk and self.waterwalkapplied then
        loco:AdjustPathCaps(self.savedallowocean,"allowocean")
    end
    self.waterwalkapplied=waterwalk
    -- Equipment loss must not leave a player suspended over water or a cave gap.
    -- A loaded/shard-migrated string state also needs this check before drowning.
    if enabled and not waterwalk then
        local x,y,z=inst.Transform:GetWorldPosition()
        local map=TheWorld.Map
        if Rules.IsCaveVoid(map,x,y,z) or (inst:GetCurrentPlatform()==nil and not map:IsVisualGroundAtPoint(x,y,z)) then
            self:ReturnToSafeGround()
        end
    end
    self.stringapplied=enabled
    Visual.StringBuild(inst,enabled)
    self:UpdateColour()
end
function Kanami:UpdateColour()
    local stringed=self.state.string and self:Alive()
    self.inst.AnimState:SetMultColour(stringed and .82 or 1,stringed and .66 or 1,1,self:IsProtected() and .3 or (stringed and .55 or 1))
end
function Kanami:ToggleString()
    if not self:Alive() then return false end
    if not self.state.string and self:IsMoist() then
        if self.inst.components.talker then self.inst.components.talker:Say("身上还有潮湿度，无法进入弦化。") end
        return false
    end
    local x,y,z=self.inst.Transform:GetWorldPosition()
    if self.state.string and not self:SafePoint(x,y,z) then
        if self.inst.components.talker then self.inst.components.talker:Say("这里无法解除弦化。请先回到安全陆地。") end
        return false
    end
    if not self.state.string then
        if self:SafeGroundPoint({x,y,z}) then self.lastsafe={x,y,z} end
        local hand=self.inst.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
        local rod=hand and (hand.components.fishingrod or hand.components.oceanfishingrod)
        if rod then rod:StopFishing() end
        if self.inst.ClearBufferedAction then self.inst:ClearBufferedAction() end
    end
    self.state.string=not self.state.string
    self:ApplyString();self:Sync()
    self.inst:PushEvent("klbq_string_changed",self.state.string)
    return true
end
function Kanami:Cast(key)
    if not self:Alive() or not Rules.Cast(self.state,key,GetTime()) then return false end
    if key=="z" then self:SetZCost(self:IsZ()) end
    self:Sync()
    if key=="x" then
        -- Cleanse and field membership take effect on activation, then .25s scans.
        self:Tick()
        local fx=SpawnPrefab("klbq_kanami_domain_cast_fx")
        if fx then fx.entity:SetParent(self.inst.entity);fx.Transform:SetPosition(0,.04,0) end
    end
    if self.inst.sg and not self.inst.sg:HasStateTag("busy") then self.inst.sg:GoToState("klbq_cast") end
    return true
end
function Kanami:SetZCost(enabled)
    enabled=enabled and not self.removed and self:Alive() or false
    local sanity=self.inst.components.sanity
    -- Older builds put the cost in Recalc's rate. Remove that source so the
    -- independent update below never charges twice or inherits rate modifiers.
    if sanity and sanity.externalmodifiers then
        sanity.externalmodifiers:RemoveModifier(self.inst,"klbq_blast")
    end
    if self.zcostenabled~=enabled then
        self.zcostenabled=enabled
        if enabled then self.inst:StartUpdatingComponent(self)
        else self.inst:StopUpdatingComponent(self) end
    end
end
function Kanami:OnUpdate(dt)
    if not self:IsZ() or not self:Alive() then self:SetZCost(false);return end
    -- Native Sanity.OnUpdate skips Recalc while sleeping/invincible/teleporting.
    -- A skill cost continues there, without changing ordinary sanity sources.
    local sanity=self.inst.components.sanity
    if sanity and dt>0 then sanity:DoDelta(-Rules.Z_SANITY_PER_SECOND*dt,true) end
end
function Kanami:OnDeath()
    if self.state.dead then return end
    Rules.Death(self.state,GetTime())
    self:SetZCost(false)
    self:ApplyString();self:ClearDomain();self:Protection(false);self:Sync()
end
function Kanami:OnRespawn()
    local automatic=self.autoreviving==true
    self.autoreviving=nil
    Rules.Revive(self.state,GetTime(),automatic)
    self:ApplyString()
    if automatic then
        self.inst.components.health:SetCurrentHealth(1)
        self.inst.components.health:ForceUpdateHUD()
        self.inst.components.hunger:SetPercent(.5)
        self.inst.components.sanity:SetPercent(1)
        if self.inst.sg and self.inst.sg.sg.states.klbq_revive then self.inst.sg:GoToState("klbq_revive") end
    end
    self:Protection(automatic);self:Sync()
end
function Kanami:Protection(enabled,forceclear)
    if enabled and not forceclear then
        local inventory=self.inst.components.inventory
        local held = inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
        if held ~= nil and inventory:CanAcceptCount(held, 1) > 0 then
            -- Force removal also handles native equipment that resists ordinary
            -- unequipping. Check storage first so a full inventory cannot
            -- force the existing weapon onto the ground during resurrection.
            local hand=inventory:Unequip(EQUIPSLOTS.HANDS,nil,true)
            if hand then inventory:GiveItem(hand) end
        end
    end
    -- X blocks aggro; only resurrection blocks damage and changes opacity.
    -- One shared hook/tag owner lets either effect outlast the other safely.
    local avoid=not forceclear and (enabled or self:IsX())
    if avoid and not self.protection then
        local combat=self.inst.components.combat
        local previous=combat.shouldavoidaggrofn
        local protection={notarget=self.inst:HasTag("notarget"),tag=self.inst:HasTag("klbq_protected"),previous=previous}
        self.protection=protection
        protection.avoid=function(enemy,...)
            -- Vanilla ShouldAggro's target callback returns FALSE to refuse.
            -- A later mod may retain this wrapper; it becomes inert on expiry.
            if self.protection==protection then
                if self:IsProtected() then return false end
                if self:IsX() and not Domain.CanRetaliate(self.inst,enemy) then return false end
            end
            if previous then return previous(enemy,...) end
            return true
        end
        combat.shouldavoidaggrofn=protection.avoid
    elseif not avoid and self.protection then
        local combat=self.inst.components.combat
        if combat.shouldavoidaggrofn==self.protection.avoid then combat.shouldavoidaggrofn=self.protection.previous end
        if not self.protection.notarget then self.inst:RemoveTag("notarget") end
        if not self.protection.tag then self.inst:RemoveTag("klbq_protected") end
        self.protection=nil
        self:UpdateColour()
    end
    local protection=self.protection
    if protection and not protection.notarget then
        if enabled then self.inst:AddTag("notarget") else self.inst:RemoveTag("notarget") end
    end
    if protection and protection.enabled~=enabled then
        protection.enabled=enabled
        if enabled then self.inst:AddTag("klbq_protected")
        elseif not protection.tag then self.inst:RemoveTag("klbq_protected") end
        self:UpdateColour()
    end
end
function Kanami:ClearDomain()
    Domain.Remove(self.inst,self.targets);self.targets={}
    if self.domainfx and self.domainfx:IsValid() then self.domainfx:Remove() end
    self.domainfx=nil
end
function Kanami:Tick()
    local inst=self.inst
    self:SetZCost(self:IsZ())
    -- Native source resurrection keeps playerghost throughout its delayed
    -- animation. It clears rezsource if that source vanishes, but may retain
    -- the reviving tag; the original automatic deadline then remains usable.
    if Rules.AutoReviveDue(self.state,GetTime()) and inst:HasTag("playerghost")
        and inst.rezsource==nil and not self.autoreviving then
        self.autoreviving=true
        inst:PushEvent("respawnfromghost")
    end
    if self.state.string then
        local x,y,z=inst.Transform:GetWorldPosition()
        local map=TheWorld.Map
        if not map:IsInMapBounds(x,y,z) or
            (map.IsInvalidTileAtPoint and map:IsInvalidTileAtPoint(x,y,z)
                and not (self:CanStringWaterWalk() and Rules.IsCaveVoid(map,x,y,z))) then
            self:ReturnToSafeGround()
        elseif self:SafeGroundPoint({x,y,z}) then self.lastsafe={x,y,z} end
    end
    local waterwalk=self:CanStringWaterWalk()
    if self.waterwalkapplied~=waterwalk then self:ApplyString() end
    Rules.RefreshCaveCollisionMask(inst,waterwalk)
    self:Protection(self:IsProtected())
    if self:IsX() then
        self.targets=Domain.Scan(inst,self.targets)
        if not self.domainfx then
            self.domainfx=SpawnPrefab("klbq_kanami_domain_fx")
            if self.domainfx then self.domainfx.entity:SetParent(inst.entity);self.domainfx.Transform:SetPosition(0,.02,0) end
        end
    elseif next(self.targets) or self.domainfx then self:ClearDomain() end
    self:Sync()
end
function Kanami:OnHit(data)
    if self.echoing or not data or not data.target or not self:Alive() then return end
    -- Native onhitother may contain positive spdamage even when health absorbs
    -- it all. Its resolved amount is authoritative, including an explicit zero.
    if (data.damageresolved or data.damage or 0)<=0 then return end
    self:Echo(data.target,self.attackcontext or Damage.Snapshot(self.inst,data.target,data.weapon))
end
function Kanami:Echo(target,snapshot)
    if self.echoing or not Rules.Ready(self.state,"passive",GetTime()) or not Damage.Valid(target) then return false end
    -- Snapshot after the triggering hit, before either passive damage channel.
    local trueamount=target.components.health.currenthealth*Rules.PASSIVE_HEALTH_FRACTION*snapshot.zmult
    -- Reserve before damage: GetAttacked synchronously emits onhitother.
    Rules.Start(self.state,"passive",GetTime(),Rules.PASSIVE_COOLDOWN)
    self.echoing=true
    local ok,result=pcall(function()
        local planar=Damage.Planar(self.inst,target,snapshot.power*snapshot.zmult,snapshot.weapon)
        -- A planar kill already receives native Combat credit. Do not hit or
        -- credit that corpse again; surviving phases retain their own defenses.
        local truehit=false
        if Damage.Valid(target) then
            truehit=Damage.TrueDamage(self.inst,target,trueamount,snapshot.weapon)
        end
        return planar or truehit
    end)
    self.echoing=false
    if not ok then error(result) end
    return result
end
function Kanami:Shoot(target)
    return require("klbq_kanami/rifle").Shoot(self.inst,target)
end
function Kanami:InstallHooks()
    local inst=self.inst
    -- MakePlayerCharacter captures this callback as _OnLoad after master init,
    -- then invokes it synchronously after every component has loaded.
    local oldload=inst.OnLoad
    inst.OnLoad=function(player,...)
        local result=oldload and Pack(oldload(player,...)) or {n=0}
        self:GuardOceanLoad()
        return unpack(result,1,result.n)
    end
    local c=inst.components.combat
    local oldcalc=c.CalcDamage
    c.CalcDamage=function(combat,...)
        local result=Pack(oldcalc(combat,...))
        if self.attackcontext and not self.context_isprojectile then
            local weapon=self.attackcontext.weapon
            self.attackcontext.power=weapon and (weapon.prefab=="klbq_crossbow" or weapon.prefab=="klbq_crossbow_bolt")
                and result[2] and result[2].planar or result[1] or 0
        end
        local mult=self.attackcontext and self.attackcontext.zmult or (self:IsZ() and 1.5 or 1)
        if mult~=1 then
            result[1]=(result[1] or 0)*mult
            if result[2] then local copy={};for k,v in pairs(result[2]) do copy[k]=v*mult end;result[2]=copy end
        end
        return unpack(result,1,result.n)
    end
    local oldattack=c.DoAttack
    c.DoAttack=function(combat,target,weapon,projectile,...)
        if not self:CanUseHands() then return end
        weapon=weapon or combat:GetWeapon()
        if self.state.string or (weapon and weapon.prefab=="klbq_finale") then return end
        if target==nil and combat.target==nil then return oldattack(combat,target,weapon,projectile,...) end
        local prior=self.attackcontext
        local priorprojectile=self.context_isprojectile
        self.context_isprojectile=projectile~=nil
        self.attackcontext=projectile and projectile._klbq_attack_snapshot or Damage.Snapshot(inst,target or combat.target,weapon)
        local result=Pack(pcall(oldattack,combat,target,weapon,projectile,...))
        self.attackcontext=prior
        self.context_isprojectile=priorprojectile
        if not result[1] then error(result[2]) end
        return unpack(result,2,result.n)
    end
    local oldcan=c.CanAttack
    c.CanAttack=function(combat,...)
        if not self:CanUseHands() then return false end
        local w=combat:GetWeapon()
        if self.state.string or (w and w.prefab=="klbq_finale") then return false end
        return oldcan(combat,...)
    end
    local inventory=inst.components.inventory
    local oldequip=inventory.Equip
    inventory.Equip=function(inv,item,...)
        local equippable=item and item.components and item.components.equippable
        if equippable and equippable.equipslot==EQUIPSLOTS.HANDS and not self:CanUseHands() then
            -- Native PICKUP auto-equips an empty hand and ignores Equip's
            -- return value. Redirect only that validated action's own item.
            if self.pickupitem==item then return inv:GiveItem(item,nil,item:GetPosition()) end
            return false
        end
        return oldequip(inv,item,...)
    end
    local health=inst.components.health
    local olddelta=health.DoDelta
    health.DoDelta=function(h,amount,...)
        if not self.removed then amount=Rules.Incoming(amount,self.state.string,self:IsProtected(),select(2,...)) end
        return olddelta(h,amount,...)
    end
    local loco=inst.components.locomotor
    Rules.ConfigureCaveGlide(loco)
    local oldspeed=loco.GetSpeedMultiplier
    loco.GetSpeedMultiplier=function(l,...)
        local result=Pack(oldspeed(l,...))
        if not self.removed and self:Alive() then result[1]=Rules.Speed(result[1],self.state.string,false,self:IsMoist()) end
        return unpack(result,1,result.n)
    end
    local drown=inst.components.drownable
    if drown then
        local old=drown.ShouldDrown
        drown.ShouldDrown=function(d,...) if self:CanStringWaterWalk() then return false end;return old(d,...) end
        local oldvoid=drown.ShouldFallInVoid
        drown.ShouldFallInVoid=function(d,...)
            if self:CanStringWaterWalk() then
                if not (TheWorld.HasTag and TheWorld:HasTag("cave"))
                    or Rules.IsCaveVoid(TheWorld.Map,inst.Transform:GetWorldPosition()) then return false end
            end
            return oldvoid(d,...)
        end
    end
end
function Kanami:FinishOceanLoad()
    local guard=self.oceanloadguard
    if not guard then return end
    self.oceanloadguard=nil
    if guard.task then guard.task:Cancel() end
    if self.inst.components.drownable==guard.drownable and guard.drownable.enabled==false then
        guard.drownable.enabled=guard.enabled
    end
end
function Kanami:GuardOceanLoad()
    if self.removed or not self:CanStringWaterWalk() then return end
    local inst=self.inst
    local drown=inst.components.drownable
    local x,y,z=inst.Transform:GetWorldPosition()
    local map=TheWorld.Map
    if not drown or drown.enabled==false or
        (not Rules.IsCaveVoid(map,x,y,z) and
            (not map:IsOceanTileAtPoint(x,y,z) or map:IsVisualGroundAtPoint(x,y,z))) then return end
    self:FinishOceanLoad()
    local guard={drownable=drown,enabled=drown.enabled}
    self.oceanloadguard=guard
    drown.enabled=false
    -- Native player_common's next-tick OnLoad rescue ignores ShouldDrown and
    -- tests land passability directly. Skip only when the saved location is traversable.
    -- Scheduler iterates same-tick tasks with pairs, so restore one tick later.
    guard.task=inst:DoTaskInTime(0,function()
        guard.task=inst:DoTaskInTime(0,function()
            if self.oceanloadguard==guard then
                self:FinishOceanLoad()
                self:ApplyString();self:Sync()
            end
        end)
    end)
end
function Kanami:OnSave()
    local data=Rules.Save(self.state,GetTime());data.lastsafe=self.lastsafe
    data.lastsafe_shard=TheShard and TheShard:GetShardId() or nil
    return data
end
function Kanami:OnLoad(data)
    self.state=Rules.Load(data,GetTime())
    local shard=TheShard and TheShard:GetShardId() or nil
    self.lastsafe=data and data.lastsafe_shard==shard and data.lastsafe or nil
    self.inst:DoTaskInTime(0,function()
        if self.inst:HasTag("playerghost") then
            self.state.dead=true
            if self.state.deadlines.revive==nil then Rules.Start(self.state,"revive",GetTime(),60) end
        end
        self:ApplyString();self:Tick()
    end)
end
function Kanami:OnRemoveFromEntity()
    if self.task then self.task:Cancel() end
    self.removed=true
    self:FinishOceanLoad()
    -- Other mods may retain our wrapped methods after RemoveComponent.
    -- Make their captured state inert before restoring tags and appearance.
    self.state=Rules.New();self.state.dead=true
    self:ApplyString()
    self:SetZCost(false)
    self:Protection(false,true)
    self:ClearDomain()
    self.inst:RemoveEventCallback("death",self._death)
    self.inst:RemoveEventCallback("ms_respawnedfromghost",self._respawn)
    self.inst:RemoveEventCallback("onhitother",self._hit)
    self.inst:RemoveEventCallback("moisturedelta",self._moisture)
    self.inst:RemoveEventCallback("equip",self._equipment)
    self.inst:RemoveEventCallback("unequip",self._equipment)
    self.inst:RemoveEventCallback("newstate",self._movementstate)
    if self.inst:IsValid() then self:Sync() end
end
-- Disconnects and shard migration remove the entire EntityScript; that path
-- invokes OnRemoveEntity, rather than RemoveComponent's OnRemoveFromEntity.
Kanami.OnRemoveEntity=Kanami.OnRemoveFromEntity
return Kanami
