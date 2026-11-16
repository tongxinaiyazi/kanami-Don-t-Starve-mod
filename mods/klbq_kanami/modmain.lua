local G=GLOBAL
-- The world's mod configuration controls server-authoritative bullet damage.
require("klbq_kanami/rules").ConfigureFate(GetModConfigData("fate_crit_fraction"))
PrefabFiles={"klbq_kanami","klbq_finale","klbq_ammo","klbq_kanami_fx","klbq_singularity","klbq_omurice","klbq_crystal","klbq_blade","klbq_crossbow","klbq_requiem","klbq_imprint_tool"}
Assets={
    Asset("ATLAS","images/klbq_kanami_items.xml"),Asset("IMAGE","images/klbq_kanami_items.tex"),
    Asset("ATLAS","images/map_icons/klbq_kanami.xml"),Asset("IMAGE","images/map_icons/klbq_kanami.tex"),
    Asset("ATLAS","images/avatars/avatar_klbq_kanami.xml"),Asset("IMAGE","images/avatars/avatar_klbq_kanami.tex"),
    Asset("ATLAS","images/avatars/avatar_ghost_klbq_kanami.xml"),Asset("IMAGE","images/avatars/avatar_ghost_klbq_kanami.tex"),
    Asset("ATLAS","images/avatars/self_inspect_klbq_kanami.xml"),Asset("IMAGE","images/avatars/self_inspect_klbq_kanami.tex"),
    Asset("ATLAS","images/saveslot_portraits/klbq_kanami.xml"),Asset("IMAGE","images/saveslot_portraits/klbq_kanami.tex"),
    Asset("ATLAS","images/selectscreen_portraits/klbq_kanami.xml"),Asset("IMAGE","images/selectscreen_portraits/klbq_kanami.tex"),
    Asset("ATLAS","images/selectscreen_portraits/klbq_kanami_silho.xml"),Asset("IMAGE","images/selectscreen_portraits/klbq_kanami_silho.tex"),
    Asset("ATLAS","bigportraits/klbq_kanami.xml"),Asset("IMAGE","bigportraits/klbq_kanami.tex"),
}
AddMinimapAtlas("images/map_icons/klbq_kanami.xml")
AddModCharacter("klbq_kanami","FEMALE")
require("klbq_kanami/technology").Install(env)
require("klbq_kanami/chef").Install(env)
require("klbq_kanami/curse").Install(env)
require("klbq_kanami/domain").Install(env)
require("klbq_kanami/visual").Install(env)
require("klbq_kanami/bag").Install(env)
require("klbq_kanami/inventoryguard").Install(env)
for _,name in ipairs({"klbq_finale","klbq_ammo_heart","klbq_ammo_fate","klbq_ammo_doom","klbq_singularity","klbq_omurice","klbq_crystal","klbq_blade","klbq_crossbow","klbq_requiem","klbq_imprint_tool"}) do
    RegisterInventoryItemAtlas("images/klbq_kanami_items.xml",name..".tex")
end
require("klbq_kanami/resources").Install(env)
local S=G.STRINGS
S.CHARACTER_TITLES.klbq_kanami="弦上的终曲"
S.CHARACTER_NAMES.klbq_kanami="香奈美"
S.CHARACTER_DESCRIPTIONS.klbq_kanami="* 身轻敏捷，弦化穿障；眼球背包解锁踏水\n* 怕冷热与火焰，潮湿时速度减半\n* 旋律回响、交响爆音、演出开始与双生共鸣"
S.CHARACTER_QUOTES.klbq_kanami="让这首曲子，响到最后吧。"
S.CHARACTER_SURVIVABILITY.klbq_kanami="纤细却不屈"
S.NAMES.KLBQ_KANAMI="香奈美"
S.SKIN_NAMES.klbq_kanami_none="香奈美"
local descriptions={
    KLBQ_FINALE={"谢幕曲","灯火渐暗，属于你的最后一拍才刚刚响起。"},
    KLBQ_AMMO_HEART={"心之语","把未说出口的心意，唱进下一声回响。"},
    KLBQ_AMMO_FATE={"支配命运之轮","舞台尚未落幕，命运的节拍由我改写。"},
    KLBQ_AMMO_DOOM={"末日浩劫","最后一个音符落下，便是这场演出的谢幕。"},
    KLBQ_SINGULARITY={"弦能奇点","把旅途的零碎，藏进一枚安静的星点。"},
    KLBQ_OMURICE={"蛋包饭","把一天的疲惫，轻轻裹进金黄的蛋皮里。"},
    KLBQ_CRYSTAL={"精粹弦能晶体","沉寂的序列在晶面深处共振，仿佛仍记得那场未完的演出。"},
    KLBQ_BLADE={"忍锋","银白刃缘掠过，连风也短暂屏住呼吸。"},
    KLBQ_CROSSBOW={"连弩","细密的弦声，把沉默缝成一条直线。"},
    KLBQ_IMPRINT_TOOL={"拓印终端","把陌生的形状，留作下一次重逢的记忆。"},
    KLBQ_REQUIEM={"镇魂歌","为远去的回声，留下一段温柔而锋利的尾奏。"},
}
for name,data in pairs(descriptions) do
    S.NAMES[name]=data[1];S.RECIPE_DESC[name]=data[2];S.CHARACTERS.GENERIC.DESCRIBE[name]=data[2]
end
S.RECIPE_DESC.KLBQ_RESOURCE_BASE_STRING="每一段弦，都在等待属于自己的合奏。"
S.RECIPE_DESC.KLBQ_RESOURCE_TRACING_PLATE="让短暂的形状，在光里留下痕迹。"
S.RECIPE_DESC.KLBQ_RESOURCE_TOPOLOGY_RING="环的两端，在另一重维度相遇。"
-- Ammo descriptions and inspection dialogue share original character flavour.
S.CHARACTERS.GENERIC.DESCRIBE.KLBQ_AMMO_HEART="把未说出口的心意，唱进下一声回响。"
S.CHARACTERS.GENERIC.DESCRIBE.KLBQ_AMMO_FATE="舞台尚未落幕，命运的节拍由我改写。"
S.CHARACTERS.GENERIC.DESCRIBE.KLBQ_AMMO_DOOM="最后一个音符落下，便是这场演出的谢幕。"
require("klbq_kanami/speech").Install(S,env)
-- Crafting registration uses the shared material catalog.
require("klbq_kanami/recipes").Install(env)
require("klbq_kanami/imprint").Install(env, require("klbq_kanami/bag").CollectUpgradeAction)

-- Container definitions must run on clients before container replicas are built.
local containers=require("containers")
containers.params.klbq_finale={
    widget={slotpos={G.Vector3(0,36,0)},animbank="ui_cookpot_1x2",animbuild="ui_cookpot_1x2",pos=G.Vector3(0,15,0)},
    type="hand_inv",excludefromcrafting=true,
    itemtestfn=function(container,item,slot) return item:HasTag("klbq_ammo") end,
}
containers.MAXITEMSLOTS=math.max(containers.MAXITEMSLOTS,1)

local shoot=G.Action({priority=20,distance=math.huge,do_not_locomote=true,mount_valid=false})
shoot.id="KLBQ_SHOOT";shoot.str="谢幕曲 · 射击"
shoot.fn=function(act)
    return require("klbq_kanami/rifle").Shoot(act.doer,act.target)
end
AddAction(shoot)
local function CanSelectShot(doer,target)
    return not doer:HasTag("playerghost") and not (doer._klbq_string and doer._klbq_string:value())
        and not (doer._klbq_protect and doer._klbq_protect:value())
        and target and target~=doer and target.replica and target.replica.health
        and not (target:HasTag("playerghost") or target:HasTag("INLIMBO") or target:HasTag("NOCLICK"))
        and target.entity:IsVisible()
end
AddComponentAction("EQUIPPED","inventoryitem",function(item,doer,target,actions,right)
    if not right and item:HasTag("klbq_finale")
        and CanSelectShot(doer,target) then
        actions[#actions+1]=shoot
    end
end)
for _,sg in ipairs({"wilson","wilson_client"}) do AddStategraphActionHandler(sg,G.ActionHandler(shoot,"klbq_shoot")) end
require("klbq_kanami/states").Install(env)
require("klbq_kanami/crossbow").Install(env)
require("klbq_kanami/requiem").Install(env)

local forbidden={ATTACK=true,CHOP=true,MINE=true,HAMMER=true,DIG=true,NET=true,TERRAFORM=true,SCYTHE=true,SHAVE=true,ROW=true,ROW_CONTROLLER=true,
    FISH=true,FISH_OCEAN=true,REEL=true,OCEAN_FISHING_POND=true,OCEAN_FISHING_CAST=true,OCEAN_FISHING_REEL=true,OCEAN_FISHING_CATCH=true,
    TILL=true,POUR_WATER=true,POUR_WATER_GROUNDTILE=true,WATER_TOSS=true,GRAVEDIG=true,CARVEPUMPKIN=true,
    DRAW=true,FAN=true,BLINK=true,CASTSPELL=true,CASTAOE=true,
    -- Inventory projectiles and tools can bypass combat and need no HANDS item.
    TOSS=true,TOSS_MAP=true,OCEAN_TOSS=true,LIGHT=true,CAST_NET=true,NABBAG=true,
    BRUSH=true,SEW=true,ROTATE_FENCE=true,TERRAFORM_REMOVE=true,MURDER=true,SLAUGHTER=true,INCINERATE=true,
    BOAT_CANNON_LOAD_AMMO=true,BOAT_CANNON_START_AIMING=true,BOAT_CANNON_SHOOT=true,
    GOLF_START_AIMING=true,GOLF_START_CHARGING=true}
local function Allowed(inst,action,item)
    local gun=inst.replica.inventory and inst.replica.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)
    if gun and gun:HasTag("klbq_finale") and action==G.ACTIONS.ATTACK then return false end
    local protected=inst._klbq_protect and inst._klbq_protect:value()
    if protected and action.id=="EQUIP" and item then
        local equip=item.replica and item.replica.equippable
        local slot=equip and equip:EquipSlot() or (item.components and item.components.equippable and item.components.equippable.equipslot)
        if slot==G.EQUIPSLOTS.HANDS then return false end
    end
    local locked=protected or (inst._klbq_string and inst._klbq_string:value())
    -- Native DEPLOY also launches some inventory items directly. Its two
    -- aliases share that body; ordinary planting/buildable placement stays free.
    local projectiledeploy=(action.id=="DEPLOY" or action.id=="DEPLOY_TILEARRIVE" or action.id=="DEPLOY_FLOATING")
        and item~=nil and item:HasTag("complexprojectile")
    return not (locked and (forbidden[action.id] or (G.TOOLACTIONS and G.TOOLACTIONS[action.id])
        or projectiledeploy or action.id=="KLBQ_SHOOT" or action.id=="KLBQ_REQUIEM_SWEEP"))
end
-- Retain native pickup validation, events and full-inventory handling. The
-- temporary scope only changes its implicit HANDS auto-equip during protection.
local pickup=G.ACTIONS and G.ACTIONS.PICKUP
if pickup then
    local oldpickup=pickup.fn
    local function PackPickup(...) return {n=G.select("#",...),...} end
    pickup.fn=function(act,...)
        local c=act.doer and act.doer.components.klbq_kanami
        if not c or c:CanUseHands() then return oldpickup(act,...) end
        local previous=c.pickupitem
        c.pickupitem=act.target
        local result=PackPickup(G.pcall(oldpickup,act,...))
        c.pickupitem=previous
        if not result[1] then G.error(result[2]) end
        return G.unpack(result,2,result.n)
    end
end
local function InstallActionFilter(picker)
    if not picker._klbq_actionfilter then
        picker._klbq_actionfilter=true
        local old=picker.SortActionList
        picker.SortActionList=function(self,actions,target,useitem,...)
            local inst=self.inst
            local gun=inst.replica.inventory and inst.replica.inventory:GetEquippedItem(G.EQUIPSLOTS.HANDS)
            local rifle=gun and gun:HasTag("klbq_finale") and CanSelectShot(inst,target)
            local filtered={}
            for _,action in ipairs(actions) do
                -- Hostile/Ctrl-click routes skip EQUIPPED collection entirely.
                if rifle and action==G.ACTIONS.ATTACK then action=shoot;useitem=gun end
                if Allowed(inst,action,useitem) then filtered[#filtered+1]=action end
            end
            -- Vanilla activates ONLY the top filter. Do not push our own filter:
            -- preserve its living/ghost, mounted, paused and other-mod rules.
            return old(self,filtered,target,useitem,...)
        end
    end
end
-- OnSetOwner can create/recreate the picker after prefab initialization.
AddComponentPostInit("playeractionpicker",function(picker)
    InstallActionFilter(picker)
end)
local function InstallRiflePlayer(inst)
    if inst._klbq_rifle_installed then return end
    inst._klbq_rifle_installed=true
    inst:DoTaskInTime(0,function()
        if inst.components.playeractionpicker then
            InstallActionFilter(inst.components.playeractionpicker)
        end
    end)
    if not G.TheWorld.ismastersim then return end
    local old=inst.PerformBufferedAction
    inst.PerformBufferedAction=function(player,...)
        local act=player:GetBufferedAction()
        if act and not Allowed(player,act.action,act.invobject) then player:ClearBufferedAction();return false end
        return old(player,...)
    end
    local combat=inst.components.combat
    if combat then
        local oldattack=combat.DoAttack
        combat.DoAttack=function(self,target,weapon,...)
            local hand=weapon or self:GetWeapon()
            if hand and hand.prefab=="klbq_finale" then return end
            return oldattack(self,target,weapon,...)
        end
        local oldcan=combat.CanAttack
        combat.CanAttack=function(self,...)
            local hand=self:GetWeapon()
            if hand and hand.prefab=="klbq_finale" then return false end
            return oldcan(self,...)
        end
    end
    inst:ListenForEvent("klbq_shot",function(_,data)
        local fx=G.SpawnPrefab("klbq_kanami_tracer_fx")
        if fx then
            local x,y,z=inst.Transform:GetWorldPosition();fx.Transform:SetPosition(x,y,z)
            fx:ForceFacePoint(data.target.Transform:GetWorldPosition())
        end
        local impact=G.SpawnPrefab("impact")
        if impact and data.target:IsValid() then
            local combat=data.target.components.combat
            if combat and combat.hiteffectsymbol then
                impact.entity:AddFollower():FollowSymbol(data.target.GUID,combat.hiteffectsymbol,0,0,0)
            else impact.Transform:SetPosition(data.target.Transform:GetWorldPosition()) end
            impact:FacePoint(inst.Transform:GetWorldPosition())
        end
    end)
end
AddPlayerPostInit(InstallRiflePlayer)
AddPrefabPostInit("klbq_kanami",function(inst)
    InstallRiflePlayer(inst)
    if not G.TheWorld.ismastersim then return end
    inst:ListenForEvent("klbq_string_changed",function(_,enabled)
        if inst.sg and not inst.sg:HasStateTag("busy") then inst.sg:GoToState(enabled and "klbq_string_enter" or "klbq_string_exit") end
    end)
end)

AddModRPCHandler("KLBQ_KANAMI","skill",function(player,key)
    if not player or player.prefab~="klbq_kanami" or type(key)~="string" then return end
    local c=player.components.klbq_kanami
    if not c or not c:Alive() then return end
    -- C is free, but repeated packets within one tick cannot toggle twice.
    local now=G.GetTime()
    if now<(c.nextinput or 0) then return end
    c.nextinput=now+.15
    if key=="c" then c:ToggleString() elseif key=="z" or key=="x" then c:Cast(key) end
end)

-- Capture a delayed attack at projectile creation, before a player swaps hands.
-- Hooks preserve existing functions/return counts; no target-global changes.
AddComponentPostInit("projectile",function(c)
    local old=c.Throw
    c.Throw=function(self,owner,target,attacker,...)
        local source=attacker or (owner and owner.components.combat and owner) or (owner and owner.components.inventoryitem and owner.components.inventoryitem.owner)
        if source and source.components.klbq_kanami and target then
            local context=source.components.klbq_kanami.attackcontext
            if context then
                -- DoAttack records this before DropItem removes the weapon.
                self.inst._klbq_attack_snapshot={power=context.power,zmult=context.zmult,weapon=context.weapon}
            else
                local w=self.inst.components.weapon and self.inst
                    or (owner and owner.components.weapon and owner) or source.components.combat:GetWeapon()
                self.inst._klbq_attack_snapshot=require("klbq_kanami/damage").Snapshot(source,target,w)
            end
        else
            self.inst._klbq_attack_snapshot=nil
        end
        return old(self,owner,target,attacker,...)
    end
end)
AddComponentPostInit("complexprojectile",function(c)
    local old=c.Launch
    c.Launch=function(self,pos,attacker,weapon,...)
        if attacker and attacker.components.klbq_kanami then
            local context=attacker.components.klbq_kanami.attackcontext
            self.inst._klbq_attack_snapshot=context and {power=context.power,zmult=context.zmult,weapon=context.weapon} or nil
        else
            self.inst._klbq_attack_snapshot=nil
        end
        return old(self,pos,attacker,weapon,...)
    end
end)
if not G.TheNet:IsDedicated() then require("klbq_kanami/client").Install(env) end
print("[KLBQ_KANAMI] 2.1.1 registered (server-authoritative skills)")
