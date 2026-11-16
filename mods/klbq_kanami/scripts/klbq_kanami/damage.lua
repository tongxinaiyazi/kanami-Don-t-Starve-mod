local Compat = require("klbq_kanami/compat")
local Rules = require("klbq_kanami/rules")
local M = {}
function M.Valid(target)
    return target ~= nil and target:IsValid() and not target:IsInLimbo()
        and target.components.health ~= nil and not target.components.health:IsDead()
end
local function Credit(attacker, target, wasalive)
    if wasalive and target.components.health:IsDead() then
        attacker:PushEvent("killed", { victim=target, attacker=attacker, from_doattack=true })
        local c = target.components.combat
        if c and c.onkilledbyother then c.onkilledbyother(target,attacker) end
    end
end
function M.Normal(attacker, target, amount, weapon)
    if not M.Valid(target) or not target.components.combat then return false end
    local health=target.components.health
    local before=health.currenthealth
    -- Current vanilla GetAttacked discards GetAttacked_Internal's return value.
    target.components.combat:GetAttacked(attacker,amount,weapon,"klbq_bullet")
    return health.currenthealth<before
end
-- The three ammunition effects use their own health transition. Passive echo
-- damage intentionally keeps Normal/Planar/TrueDamage and their normal limits.
-- Mirrored from this installation's Health:DoDelta, with per-hit caps and
-- deltamodifierfn omitted: either may implement private damage/time gates.
-- Explicit phase invulnerability, native HP redirects, SetVal/minhealth and
-- normal absorption still belong to the target. A mod that combines a private
-- HP system or rate gate with redirect/SetVal needs a tested Compat adapter.
local function HealthPercent(health)
    return health.GetPercent and health:GetPercent()
        or (health.maxhealth and health.currenthealth/health.maxhealth or 0)
end
local function NotifyHealthDelta(health,oldpercent,amount,overtime,cause,afflicter,entity)
    entity=health.inst or entity
    if entity and entity.PushEvent then
        entity:PushEvent("healthdelta",{oldpercent=oldpercent,newpercent=HealthPercent(health),
            overtime=overtime,cause=cause,afflicter=afflicter,amount=amount})
    end
    if health.ondelta then
        health.ondelta(entity,oldpercent,HealthPercent(health),overtime,cause,afflicter,amount)
    end
end
local function TrackHealth(receipt,health)
    receipt.health=receipt.health or {}
    if health and receipt.health[health]==nil then receipt.health[health]=health.currenthealth end
end
local function TrackNativeHealthRedirect(receipt,health)
    local inst=health.inst
    -- Wendy's native callback explicitly transfers this delta to her bonded
    -- ghost. Observe that known recipient without wrapping its DoDelta: the
    -- redirect intentionally retains Abigail's absorption, caps and phases.
    -- Private/wrapped redirect functions need their own tested adapter.
    if not inst or inst.prefab~="wendy" or not inst:HasTag("ghostlybond_redirect")
        or type(health.redirect)~="function" or not debug or not debug.getinfo then return end
    local info=debug.getinfo(health.redirect,"S")
    local source=info and info.source and info.source:gsub("\\","/") or ""
    if not source:find("/prefabs/wendy%.lua$") then return end
    local bond=inst.components.ghostlybond
    local ghost=bond and bond.ghost
    if ghost and not ghost:IsInLimbo() then TrackHealth(receipt,ghost.components.health) end
end
local function BulletDelta(health, amount, overtime, cause, ignore_invincible, afflicter, ignore_absorb,receipt)
    local oldpercent=HealthPercent(health)
    -- These are this character's documented defenses, not a target hit cap.
    -- They normally live in DoDelta's wrapper, which bullets intentionally skip.
    local kanami=health.inst and health.inst.components.klbq_kanami
    if kanami and amount<0 then
        amount=Rules.Incoming(amount,kanami.state.string,kanami:IsProtected())
        if amount==0 then return 0 end
    end
    if receipt and health.redirect then TrackNativeHealthRedirect(receipt,health) end
    if health.redirect and health.redirect(health.inst,amount,overtime,cause,ignore_invincible,afflicter,ignore_absorb) then
        return 0
    elseif not ignore_invincible and (health:IsInvincible() or health.inst.is_teleporting) then
        return 0
    elseif amount<0 and not ignore_absorb then
        local absorb=health.absorb
        if health.playerabsorb~=0 and afflicter and afflicter:HasTag("player") then
            absorb=absorb+health.playerabsorb
        end
        amount=amount*math.clamp(1-absorb,0,1)*math.max(1-health.externalabsorbmodifiers:Get(),0)
        if afflicter then amount=math.min(0,amount+health.externalreductionmodifiers:Get()) end
    end
    Compat.BulletSetVal(health,health.currenthealth+amount,cause,afflicter)
    NotifyHealthDelta(health,oldpercent,amount,overtime,cause,afflicter)
    return amount
end
local function MarkBullet(combat, attacker, stimuli)
    if combat then
        combat.lastattacker=attacker;combat.lastwasattackedtime=GetTime()
        combat.lastattacktype="projectile";combat.laststimuli=stimuli
    end
end
local function CombatClassMethod(combat, name)
    local class=getmetatable(combat)
    if not class then return nil end
    if class[name] then return class[name] end
    local index=class.__index
    return type(index)=="table" and index[name] or nil
end
function M.ActualDamage(receipt)
    local actual=0
    for health,before in pairs(receipt.health or {}) do
        actual=actual+math.max(0,before-health.currenthealth)
    end
    return actual
end
function M.BulletNormal(attacker, target, amount, weapon, receipt)
    if not M.Valid(target) or not target.components.combat then return false end
    receipt=receipt or {}
    local function Track(health)
        TrackHealth(receipt,health)
    end
    local combat=target.components.combat
    local nativeattack=CombatClassMethod(combat,"GetAttacked_Internal")
    Track(target.components.health)
    -- A replacement component without the native class contract must retain
    -- its own damage implementation. It is not a standard-HP bypass claim.
    if not nativeattack then return M.Normal(attacker,target,amount,weapon) end
    local restores={}
    local active={}
    local function Swap(object,key,value)
        local oldslot=rawget(object,key)
        object[key]=value
        restores[#restores+1]=function()
            if object[key]==value then object[key]=oldslot end
        end
    end
    local Attack
    Attack=function(receiver,who,damage,hitweapon,stimuli,spdamage,from_doattack)
        if active[receiver] then return false end -- Malformed cyclic redirect.
        active[receiver]=true
        local health=receiver.inst.components.health
        Track(health)
        local pending=true
        if health then
            local olddelta=health.DoDelta
            Swap(health,"DoDelta",function(self,delta,overtime,cause,ignore_invincible,afflicter,ignore_absorb)
                if pending and self==health and afflicter==attacker and delta<=0 then
                    -- Consume before SetVal/events; passive or nested unrelated
                    -- damage retains the receiver's ordinary limitations.
                    pending=false
                    return BulletDelta(self,delta,overtime,cause,ignore_invincible,afflicter,ignore_absorb,receipt)
                end
                return olddelta(self,delta,overtime,cause,ignore_invincible,afflicter,ignore_absorb)
            end)
        end
        local redirect=receiver.redirectdamagefn
        if redirect then
            Swap(receiver,"redirectdamagefn",function(...)
                -- Evaluate the actual native redirect once, at its original
                -- point in Combat. Do not infer owners or invoke it in advance.
                local entity=redirect(...)
                local nextcombat=entity and entity.components.combat
                if active[receiver] and nextcombat and not active[nextcombat]
                    and CombatClassMethod(nextcombat,"GetAttacked_Internal") then
                    local oldinternal=nextcombat.GetAttacked_Internal
                    local previous_from=nextcombat.redirected_from
                    local nextpending=true
                    Swap(nextcombat,"GetAttacked_Internal",function(self,a,d,w,s,sp,from)
                        if nextpending and self.redirected_from==receiver.inst and a==attacker and s=="klbq_bullet" then
                            nextpending=false
                            return Attack(self,a,d,w,s,sp,from)
                        end
                        return oldinternal(self,a,d,w,s,sp,from)
                    end)
                    restores[#restores+1]=function()
                        -- Native Combat clears this after recursion, but an
                        -- error must also release its temporary source field.
                        if nextcombat.redirected_from==nil or nextcombat.redirected_from==receiver.inst then
                            nextcombat.redirected_from=previous_from
                        end
                    end
                end
                return entity
            end)
        end
        local result=CombatClassMethod(receiver,"GetAttacked_Internal")(
            receiver,who,damage,hitweapon,stimuli,spdamage,from_doattack)
        pending=false
        active[receiver]=nil
        return result
    end
    -- Native Combat retains recoil/dodge, armor durability, saddle defenses,
    -- type resistance, planar damping, health events and exact kill attribution.
    -- Native redirected body parts (centipede/worm boss) carry the same sink
    -- through their explicit Combat redirect chain. Every scope is restored.
    local ok,err=pcall(Attack,combat,attacker,amount,weapon,"klbq_bullet",nil,true)
    for i=#restores,1,-1 do restores[i]() end
    if not ok then error(err,0) end
    return M.ActualDamage(receipt)>0
end
function M.BulletTrueDamage(attacker, target, amount, weapon,receipt)
    local health,resolved=Compat.Health(target)
    if not health or health:IsDead() then return false end
    receipt=receipt or {}
    TrackHealth(receipt,health)
    local before=health.currenthealth
    local combat=resolved.components.combat
    MarkBullet(combat,attacker,"klbq_fate")
    BulletDelta(health,-amount,false,attacker.nameoverride or attacker.prefab or "klbq_fate",false,attacker,true,receipt)
    local dealt=math.max(0,before-health.currenthealth)
    Credit(attacker,resolved,true)
    if dealt>0 then
        resolved:PushEvent("attacked",{attacker=attacker,damage=amount,damageresolved=dealt,
            original_damage=amount,weapon=weapon,stimuli="klbq_fate",from_doattack=true})
        if combat and combat.onhitfn then combat.onhitfn(resolved,attacker,amount,nil) end
        attacker:PushEvent("onhitother",{target=resolved,damage=amount,damageresolved=dealt,
            weapon=weapon,stimuli="klbq_fate",from_doattack=true})
        local attackercombat=attacker.components.combat
        if attackercombat and attackercombat.onhitotherfn then
            attackercombat.onhitotherfn(attacker,resolved,amount,"klbq_fate",weapon,dealt,nil,nil)
        end
        if combat and (combat.target==nil or combat.target==attacker) then
            combat.lastwasattackedbytargettime=combat.lastwasattackedtime
        end
    end
    return dealt>0
end
function M.Planar(attacker, target, amount, weapon)
    if not M.Valid(target) or not target.components.combat then return false end
    -- This path deliberately retains planarentity/planardefense/armor handling.
    local health=target.components.health
    local before=health.currenthealth
    target.components.combat:GetAttacked(attacker,0,weapon,"klbq_echo",{planar=amount})
    return health.currenthealth<before
end
function M.TrueDamage(attacker, target, amount, weapon)
    local health, resolved = Compat.Health(target)
    if not health or health:IsDead() then return false end
    -- ignore_absorb bypasses regular reduction. Invincibility, redirects,
    -- delta modifiers and maxdamagetakenperhit remain authoritative.
    local before = health.currenthealth
    local result = health:DoDelta(-amount,false,"klbq_fate",false,attacker,true)
    local dealt=math.max(0,before-health.currenthealth)
    if dealt>0 and not health:IsDead() and resolved:IsValid() then
        -- Direct health loss bypasses Combat:GetAttacked. Still notify the
        -- native victim AI (beefalo herd retaliation, hit reactions, etc.).
        local combat=resolved.components.combat
        if combat then
            combat.lastattacker=attacker;combat.lastwasattackedtime=GetTime()
            combat.lastattacktype="projectile";combat.laststimuli="klbq_fate"
        end
        resolved:PushEvent("attacked",{attacker=attacker,damage=amount,damageresolved=dealt,
            original_damage=amount,weapon=weapon,stimuli="klbq_fate",from_doattack=true})
    end
    Credit(attacker,resolved,true)
    return health.currenthealth < before, result
end
function M.Execute(attacker, target)
    local health, resolved = Compat.Health(target)
    if not health or health:IsDead() then return false end
    -- Death listeners in other mods may read Combat instead of afflicter.
    -- Record the shooter BEFORE SetVal emits synchronous death callbacks.
    local combat=resolved.components.combat
    if combat then
        combat.lastattacker=attacker;combat.lastwasattackedtime=GetTime()
        combat.lastattacktype="projectile";combat.laststimuli="klbq_doom"
    end
    -- SetVal is the canonical health transition (minhealth/death/world event/
    -- loot/phase callbacks). Do not Remove, kill subsequent forms, or disable
    -- a third party's defenses. Bypasses DoDelta's invulnerability and cap.
    local before=health.currenthealth
    local oldpercent=HealthPercent(health)
    local cause=attacker.nameoverride or attacker.prefab or "klbq_doom"
    Compat.BulletSetVal(health,0,cause,attacker)
    -- SetVal publishes native death/phase/replica changes, while DoDelta owns
    -- these HUD notifications. Execution supplies them once without re-killing.
    NotifyHealthDelta(health,oldpercent,-before,false,cause,attacker,resolved)
    Credit(attacker,resolved,true)
    return true
end
function M.Snapshot(attacker, target, weapon)
    local c = attacker.components.combat
    local k = attacker.components.klbq_kanami
    local base = 34
    if weapon and weapon.prefab ~= "klbq_finale" and weapon.components.weapon then
        local physical,special=weapon.components.weapon:GetDamage(attacker,target)
        -- Use this pure-planar weapon's actual special damage, although native
        -- Weapon:GetDamage deliberately returns zero physical damage first.
        base = (weapon.prefab=="klbq_crossbow" or weapon.prefab=="klbq_crossbow_bolt")
            and special and special.planar or physical or 0
    end
    local mult = (c.damagemultiplier or 1) * c.externaldamagemultipliers:Get()
    if attacker.components.damagetypebonus then mult=mult*attacker.components.damagetypebonus:GetBonus(target) end
    if c.customdamagemultfn then mult=mult*(c.customdamagemultfn(attacker,target,weapon,1,nil) or 1) end
    return {power=base*mult+(c.damagebonus or 0), zmult=k and k:IsZ() and 1.5 or 1,weapon=weapon}
end
return M
