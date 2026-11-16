-- One shared modifier per target, with owner membership. Two domains never
-- multiply each other's penalties; leaving the final domain removes only ours.
local M = {}
local Rules = require("klbq_kanami/rules")
local Cleanse = require("klbq_kanami/cleanse")
local Recruit = require("klbq_kanami/recruit")
local Hermit = require("klbq_kanami/hermit")
local Agriculture
local KEY = "klbq_domain"
local AURA_SOURCE = "klbq_kanami_domain_negative_aura"
local SANITY_KEY = "klbq_domain_sanity_regen"
local retaliation_context=setmetatable({},{__mode="k"})
function M.CanRetaliate(owner,enemy)
    local combat=enemy and enemy.components and enemy.components.combat
    if not combat then return false end
    -- GetAttacked sets these before native attacked/ShareTarget callbacks.
    -- Once engaged, retain that retaliation until native AI drops its target.
    local fresh=combat.lastattacker==owner and (combat.target==owner
        or (combat.lastwasattackedtime~=nil and GetTime()-combat.lastwasattackedtime<=1))
    if retaliation_context[owner] or fresh then
        combat._klbq_retaliation=combat._klbq_retaliation or setmetatable({},{__mode="k"})
        combat._klbq_retaliation[owner]=true
        return true
    end
    return combat._klbq_retaliation and combat._klbq_retaliation[owner] and combat.target==owner or false
end
function M.Install(env)
    env.AddComponentPostInit("combat",function(combat)
        if not env.GLOBAL.TheWorld.ismastersim or not combat.ShareTarget then return end
        local share=combat.ShareTarget
        combat.ShareTarget=function(self,target,...)
            if not target or not target.HasTag or not target:HasTag("klbq_kanami")
                or not M.CanRetaliate(target,self.inst) then return share(self,target,...) end
            local previous=retaliation_context[target]
            retaliation_context[target]=true
            local function Pack(...)return {n=select("#",...),...}end
            local result=Pack(pcall(share,self,target,...))
            retaliation_context[target]=previous
            if not result[1] then error(result[2]) end
            return unpack(result,2,result.n)
        end
    end)
end
local function Friendly(owner,target)
    if target == owner then return true end
    if target:HasTag("player") then
        local combat=owner.components.combat
        return not TheNet:GetPVPEnabled() or (combat and combat.IsAlly and combat:IsAlly(target)) or false
    end
    local f = target.components.follower
    if f and f:GetLeader() then
        local leader=f:GetLeader()
        return leader==owner or (leader:HasTag("player") and Friendly(owner,leader))
    end
    return target:HasTag("companion") or target:HasTag("playerallied")
        or (owner.components.combat.IsAlly and owner.components.combat:IsAlly(target))
end
local function Refresh(target)
    local data=target._klbq_domains
    local friendly,enemy,allied_domain=false,false,false
    if data then
        for owner,ally in pairs(data) do
            if owner:IsValid() then
                if ally then friendly=true;allied_domain=allied_domain or owner~=target else enemy=true end
            else data[owner]=nil end
        end
    end
    local sanity = friendly and target:HasTag("player") and target.components.sanity or nil
    if target._klbq_domain_sanity ~= sanity then
        if target._klbq_domain_sanity then
            target._klbq_domain_sanity:SetNegativeAuraImmunity(false,AURA_SOURCE)
        end
        target._klbq_domain_sanity = sanity
        if sanity then sanity:SetNegativeAuraImmunity(true,AURA_SOURCE) end
    end
    -- Native sanity externalmodifiers are additive sanity/second. Share one
    -- source across all allied domains, excluding this domain's own caster.
    local regen = allied_domain and sanity and sanity.externalmodifiers and sanity or nil
    if target._klbq_domain_regen ~= regen then
        if target._klbq_domain_regen then
            target._klbq_domain_regen.externalmodifiers:RemoveModifier(target,SANITY_KEY)
        end
        target._klbq_domain_regen = regen
        if regen then regen.externalmodifiers:SetModifier(target,.5,SANITY_KEY) end
    end
    -- Also clean friendly followers, without granting them the player speed buff.
    if friendly then Cleanse.Apply(target) end
    local loco=target.components.locomotor
    if loco then
        loco:RemoveExternalSpeedMultiplier(target,KEY)
        if friendly and target:HasTag("player") then
            -- Convert the additive +.2 final coefficient into a synchronized
            -- external ratio, recomputed each scan as equipment/terrain change.
            local base=loco:GetSpeedMultiplier()
            local kanami=target.components.klbq_kanami
            if kanami and kanami:Alive() then
                -- Its personal wet penalty applies after both flat bonuses.
                -- Remove it and C before converting X into a native net ratio.
                if kanami:IsMoist() then base=base*2 end
                if kanami.state.string then base=base-.5 end
            end
            if base>0 then loco:SetExternalSpeedMultiplier(target,KEY,(base+.2)/base) end
        elseif enemy and not friendly then loco:SetExternalSpeedMultiplier(target,KEY,.5) end
    end
    local combat=target.components.combat
    if combat and combat.externaldamagemultipliers then
        combat.externaldamagemultipliers:RemoveModifier(target,KEY)
        if enemy and not friendly then combat.externaldamagemultipliers:SetModifier(target,.5,KEY) end
    end
end
function M.Remove(owner, targets)
    if Agriculture then Agriculture.Remove(owner) end
    for target in pairs(targets or {}) do
        if target:IsValid() and target._klbq_domains then target._klbq_domains[owner]=nil;Refresh(target) end
    end
end
function M.Scan(owner, previous)
    if TheWorld and TheWorld.ismastersim then
        Agriculture = Agriculture or require("klbq_kanami/agriculture")
        Agriculture.Scan(owner)
    end
    local x,y,z=owner.Transform:GetWorldPosition()
    local current={}
    for _,target in ipairs(TheSim:FindEntities(x,y,z,Rules.DOMAIN_RADIUS,nil,{"INLIMBO","playerghost","FX","DECOR"},{"_combat","player","hermitcrab"})) do
        -- Pearl deliberately has no health component in the current game.
        if target:IsValid() then Hermit.Apply(owner,target) end
        if target:IsValid() and target.components.health and not target.components.health:IsDead() then
            Recruit.Apply(owner,target)
            local combat=target.components.combat
            if not target:HasTag("player") and combat and combat.target==owner and combat.DropTarget
                and not M.CanRetaliate(owner,target) then
                combat:DropTarget()
            end
            local ally=Friendly(owner,target)
            if ally or (not target:HasTag("player") and target.components.combat) then
                target._klbq_domains=target._klbq_domains or setmetatable({},{__mode="k"})
                target._klbq_domains[owner]=ally
                current[target]=true
                Refresh(target)
            end
        end
    end
    for target in pairs(previous or {}) do
        if not current[target] and target:IsValid() and target._klbq_domains then target._klbq_domains[owner]=nil;Refresh(target) end
    end
    return current
end
return M
