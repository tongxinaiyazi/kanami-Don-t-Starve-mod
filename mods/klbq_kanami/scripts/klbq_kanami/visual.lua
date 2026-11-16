local M={}
local unpack=unpack
local function Pack(...) return {n=select("#",...),...} end
local function IsKanami(inst)
    return inst and (inst.prefab=="klbq_kanami" or (inst.HasTag and inst:HasTag("klbq_kanami")))
end
local equipment_symbols={"swap_hat","swap_body","swap_body_tall","swap_backpack","backpack"}
local body_symbols={"torso","torso_pelvis","skirt","arm_upper","arm_upper_skin","arm_lower","arm_lower_cuff","hand","leg","foot"}
local no_carry_states={eat=true,quickeat=true,refuseeat=true,mount_eat=true,float_eat=true,float_quickeat=true,winters_feast_eat=true,
    chop_start=true,chop=true,mine_start=true,mine=true,mine_recoil=true,hammer_start=true,hammer=true,
    dig_start=true,dig=true,bugnet_start=true,bugnet=true,terraform=true}
local projection_states={chop_start=true,chop=true,mine_start=true,mine=true,mine_recoil=true,dig_start=true,dig=true}
local function UpdateCarry(inst)
    local anim=inst.AnimState
    if inst._klbq_hidecarry or inst._klbq_stringbuild then
        anim:HideSymbol("swap_object");anim:Hide("ARM_carry");anim:Show("ARM_normal")
    elseif inst._klbq_workarm then
        anim:ShowSymbol("swap_object");anim:Hide("ARM_carry");anim:Show("ARM_normal")
    else
        anim:ShowSymbol("swap_object")
        local inventory=inst.components and inst.components.inventory or inst.replica and inst.replica.inventory
        if inventory and inventory:GetEquippedItem(EQUIPSLOTS.HANDS) then anim:Show("ARM_carry");anim:Hide("ARM_normal")
        else anim:Hide("ARM_carry");anim:Show("ARM_normal") end
    end
end
local function HideFx(fx)
    if not fx then return end
    if fx.Hide then fx:Hide() end
    -- Native hat/armor controllers create local follower entities in .fx.
    -- Keep their lifetime/callbacks intact; only suppress their rendering.
    if fx.fx then
        if fx.fx.Hide then HideFx(fx.fx)
        else for _,child in pairs(fx.fx) do HideFx(child) end end
    end
end
local function HideWornFx(inst)
    local inventory=inst.components and inst.components.inventory
    for slot,item in pairs(inventory and inventory.equipslots or {}) do
        if slot~=EQUIPSLOTS.HANDS then
            HideFx(item.fx)
            for _,fx in pairs(item.swapfx or {}) do HideFx(fx) end
        end
    end
end
function M.HideEquipment(inst)
    local anim=inst.AnimState
    -- Clear native and skinned substitutions before hiding swaps: OnEquip and
    -- SetSkinsOnAnim may show those symbols again later in their call chain.
    for _,name in ipairs(equipment_symbols) do
        anim:ClearOverrideSymbol(name)
        anim:HideSymbol(name)
    end
    for _,name in ipairs(body_symbols) do anim:ClearOverrideSymbol(name);anim:ShowSymbol(name) end
    for name in pairs(CLOTHING_SYMBOLS or {}) do
        if name~="swap_object" then anim:ClearOverrideSymbol(name);anim:ShowSymbol(name) end
    end
    anim:ClearOverrideSymbol("headbase_hat")
    if anim.ClearSymbolExchanges then anim:ClearSymbolExchanges() end
    if anim.UseHeadHatExchange then anim:UseHeadHatExchange(false) end
    for _,name in ipairs({"HAT","HAT_HAIR","HAIR_HAT","HEAD_HAT","HEAD_HAT_NOHELM","HEAD_HAT_HELM"}) do anim:Hide(name) end
    for _,name in ipairs({"HEAD","HAIR","HAIR_NOHAT","HAIR_pigtails"}) do anim:Show(name) end
    for _,name in ipairs({"face","swap_face","beard","cheeks"}) do anim:ShowSymbol(name) end
    local skinner=inst.components and inst.components.skinner
    local ghost=inst.HasTag and inst:HasTag("playerghost") or (skinner and skinner.skintype=="ghost_skin")
        or anim:GetBuild()=="ghost_klbq_kanami_build"
    if IsKanami(inst) and not ghost then
        local build=inst._klbq_stringbuild and "klbq_kanami_string" or "klbq_kanami"
        if anim.GetSkinBuild and anim.SetSkin and anim:GetSkinBuild()~="" then anim:SetSkin("",build) end
        if anim:GetBuild()~=build then anim:SetBuild(build) end
    end
    HideWornFx(inst)
    if inst._klbq_hidecarry or inst._klbq_stringbuild or inst._klbq_workarm then UpdateCarry(inst) end
end
function M.Refresh(inst)
    M.HideEquipment(inst)
    if inst._klbq_appearance_pending then return end
    -- Inventory equip and clothing events can be emitted before another mod's
    -- outer wrapper or the remaining native skin callback finishes. One queued
    -- repair chain settles those plus extra-slot mods' own 0-tick visual replay.
    -- It ends after two callbacks; no update or periodic polling is installed.
    inst._klbq_appearance_pending=inst:DoTaskInTime(0,function()
        M.HideEquipment(inst)
        inst._klbq_appearance_pending=inst:DoTaskInTime(0,function()
            inst._klbq_appearance_pending=nil
            M.HideEquipment(inst)
        end)
    end)
end
function M.Bind(inst)
    local function Refresh() M.Refresh(inst) end
    for _,event in ipairs({"equip","unequip","equipskinneditem","unequipskinneditem","playeractivated","ms_respawnedfromghost"}) do
        inst:ListenForEvent(event,Refresh)
    end
    -- Keep weapons hidden during food/work animations, but the imprint's
    -- projected head is the working tool itself and must stay on swap_object.
    -- This runs on both server and predicted client, which can each hide it.
    inst:ListenForEvent("newstate",function(_,data)
        local name=data and data.statename
        if no_carry_states[name] or inst._klbq_hidecarry or inst._klbq_workarm then
            inst._klbq_workarm=nil
            local hide=no_carry_states[name]
            if hide and projection_states[name] then
                local inventory=inst.components and inst.components.inventory or inst.replica and inst.replica.inventory
                local item=inventory and inventory:GetEquippedItem(EQUIPSLOTS.HANDS)
                hide=not (item and item:HasTag("klbq_imprint_tool"))
                inst._klbq_workarm=not hide and true or nil
            end
            inst._klbq_hidecarry=hide and true or nil
            UpdateCarry(inst)
        end
    end)
    inst:ListenForEvent("onremove",function()
        if inst._klbq_appearance_pending then inst._klbq_appearance_pending:Cancel();inst._klbq_appearance_pending=nil end
        inst._klbq_hidecarry=nil
        inst._klbq_workarm=nil
    end)
    M.Refresh(inst)
end
local function WrapAppearance(component,names)
    if not IsKanami(component.inst) then return end
    for _,name in ipairs(names) do
        local old=component[name]
        if old then
            component[name]=function(self,...)
                local result=Pack(old(self,...))
                M.Refresh(self.inst)
                return unpack(result,1,result.n)
            end
        end
    end
end
local function InstallFollowFx(fx)
    local function Suppress(owner)
        if IsKanami(owner) then HideFx(fx) end
    end
    local oldattach=fx.AttachToOwner
    if oldattach then
        fx.AttachToOwner=function(self,owner,...)
            local result=Pack(oldattach(self,owner,...))
            Suppress(owner)
            return unpack(result,1,result.n)
        end
    end
    local oldreplicated=fx.OnEntityReplicated
    fx.OnEntityReplicated=function(self,...)
        local result=oldreplicated and Pack(oldreplicated(self,...)) or {n=0}
        Suppress(self.entity:GetParent())
        return unpack(result,1,result.n)
    end
    -- Backpack skin followers acquire their parent after prefab postinit.
    fx:DoTaskInTime(0,function() Suppress(fx.entity:GetParent()) end)
end
function M.Install(env)
    env.AddComponentPostInit("inventory",function(c) WrapAppearance(c,{"Equip","Unequip","OnLoad"}) end)
    env.AddComponentPostInit("skinner",function(c)
        WrapAppearance(c,{"SetSkinMode","SetSkinOverrides","OnLoad","CopySkinsFromPlayer","SwapCopiedPlayerSkins"})
    end)
    for _,prefab in ipairs({"backpack_swap_fx","mask_halfwit_fx","shadow_thrall_parasitehat_fx","lunarplanthat_fx","voidclothhat_fx",
        "wagpunkhat_fx","inspectacleshat_fx","rabbithat_fx","pumpkinhat_fx","bat_bosscorpsehat_fx",
        "armor_voidcloth_fx","armorwagpunk_fx","armor_lunarplant_glow_fx","armor_lunarplant_husk_glow_fx"}) do
        env.AddPrefabPostInit(prefab,InstallFollowFx)
    end
end
function M.StringBuild(inst,enabled)
    local anim=inst.AnimState
    if enabled and not inst._klbq_stringbuild then
        inst._klbq_stringbuild=anim:GetBuild() or "klbq_kanami"
        -- A complete, separately drawn paper silhouette. Do not squash the
        -- human rig or mutate methods on the native AnimState userdata.
        anim:SetBuild("klbq_kanami_string")
        UpdateCarry(inst)
    elseif not enabled and inst._klbq_stringbuild then
        if anim:GetBuild()=="klbq_kanami_string" then
            anim:SetBuild(inst._klbq_stringbuild)
        end
        inst._klbq_stringbuild=nil
        UpdateCarry(inst)
    end
end
return M
