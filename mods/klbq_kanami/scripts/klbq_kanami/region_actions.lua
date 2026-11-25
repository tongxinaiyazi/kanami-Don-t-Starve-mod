local Regions = require("klbq_kanami/regions")
local M = {}
local RPC = "KLBQ_REGION_SCORE"
local REACH = 5

local function CanUse(doer)
    return doer ~= nil and doer.prefab == "klbq_kanami" and not doer:HasTag("playerghost")
        and not (doer._klbq_string and doer._klbq_string:value())
        and not (doer._klbq_protect and doer._klbq_protect:value())
end

local function IsOwned(doer, score)
    return CanUse(doer) and score ~= nil and score:IsValid() and score.prefab == "klbq_region_score"
        and score.replica.inventoryitem ~= nil and score.replica.inventoryitem:IsGrandOwner(doer)
end

local function IsInSlot(doer, score)
    local inventory = doer.replica.inventory
    return inventory ~= nil and inventory:GetActiveItem() == nil and IsOwned(doer, score)
end

local function Say(doer, message)
    local talker = doer.components.talker
    if talker then talker:Say(message) end
end

function M.CollectInventoryActions(score, doer, actions, right)
    -- UseItemFromInvTile recomputes the selected action with no right argument.
    if right ~= false and IsInSlot(doer, score) then
        actions[#actions+1] = M.read
    end
end

function M.Install(env)
    local G = env.GLOBAL
    Regions.InstallTrees(env)

    local function OpenScore(score)
        if G.ThePlayer == nil or not G.ThePlayer.HUD or not G.TheFrontEnd
            or not IsInSlot(G.ThePlayer, score) then return end
        local Popup = require("screens/popupdialog")
        local function Request(command, key)
            env.SendModRPCToServer(env.GetModRPC(RPC, "edit"), score, command, key)
        end
        local keys = Regions.List(score._klbq_regions:value())
        local buttons, screen = {}
        buttons[1] = {text="记录脚下",cb=function() screen:Close(); Request("record", "") end}
        if #keys > 0 then
            buttons[#buttons+1] = {text="选择地区",cb=function()
                screen:Close()
                local RegionScreen = require("widgets/klbq_regionscreen")
                G.TheFrontEnd:PushScreen(RegionScreen(keys, score._klbq_region:value(), function(key) Request("select", key) end))
            end}
        end
        buttons[#buttons+1] = {text="关闭",cb=function() screen:Close() end}
        local selected = Regions.Name(score._klbq_region:value())
        local detail = #keys > 0 and ("当前地区："..selected.."\n已记录 "..#keys.." 个地区")
            or "还没记录地区。到达想要记下的地方后，在这里记录脚下地区。"
        screen = Popup("记录初心的乐谱", detail, buttons, nil, 180)
        G.TheFrontEnd:PushScreen(screen)
    end

    env.AddClientModRPCHandler(RPC, "open", OpenScore)
    env.AddModRPCHandler(RPC, "edit", function(doer, score, command, key)
        if not G.TheWorld.ismastersim or type(score) ~= "table" or not G.EntityScript.is_instance(score)
            or not IsInSlot(doer, score) then return end
        local now = G.GetTime()
        if (doer._klbq_next_score_edit or 0) > now then return end
        doer._klbq_next_score_edit = now + .35
        if command == "record" then
            local x,y,z = doer.Transform:GetWorldPosition()
            local map = G.TheWorld.Map
            if not G.TileGroupManager:IsLandTile(map:GetTileAtPoint(x,y,z))
                or (doer.GetCurrentPlatform and doer:GetCurrentPlatform() ~= nil) then
                Say(doer, "站在陆地上，才能记录当地的回响。")
                return
            end
            local region = Regions.AtPoint(map, x,y,z)
            local records, selected = Regions.Record(score._klbq_regions:value(), score._klbq_region:value(), region)
            score._klbq_regions:set(records)
            score._klbq_region:set(selected or "")
            Say(doer, "已记录："..Regions.Name(region))
        elseif command == "select" and Regions.Select(score._klbq_regions:value(), key) then
            score._klbq_region:set(key)
            Say(doer, "当前拓印地区："..Regions.Name(key))
        end
    end)

    local read = G.Action({priority=3,rmb=true,mount_valid=false})
    read.id = "KLBQ_READ_REGION_SCORE"
    read.str = "打开乐谱"
    read.fn = function(act)
        if not G.TheWorld.ismastersim or not IsInSlot(act.doer, act.invobject) then return false end
        if act.doer == G.ThePlayer then
            OpenScore(act.invobject)
        elseif act.doer.userid then
            env.SendModRPCToClient(env.GetClientModRPC(RPC, "open"), act.doer.userid, act.invobject)
        end
        return true
    end
    M.read = read
    env.AddAction(read)

    local imprint = G.Action({priority=3,rmb=true,distance=REACH,do_not_locomote=true,mount_valid=false})
    imprint.id = "KLBQ_IMPRINT_REGION"
    imprint.str = "拓印地区"
    imprint.fn = function(act)
        local doer, score, pt = act.doer, act.invobject, act:GetActionPoint()
        if not G.TheWorld.ismastersim or not pt or not IsOwned(doer, score)
            or doer.components.inventory:GetActiveItem() ~= score or doer:GetDistanceSqToPoint(pt) > REACH*REACH then
            return false
        end
        local key = Regions.Select(score._klbq_regions:value(), score._klbq_region:value())
        if not key then return false end
        local world = G.TheWorld
        local x,y = world.Map:GetTileCoordsAtPoint(pt:Get())
        if not Regions.SetTile(world, world.Map, x, y, key) then return false end
        Say(doer, "已拓印："..Regions.Name(key))
        return true
    end
    env.AddAction(imprint)
    env.AddComponentAction("POINT", "inventoryitem", function(score, doer, pt, actions, right, target)
        if right and target == nil and IsOwned(doer, score) and doer.replica.inventory:GetActiveItem() == score
            and Regions.Valid(score._klbq_region:value()) and doer:GetDistanceSqToPoint(pt) <= REACH*REACH
            and G.WORLD_TILES.KLBQ_IMPRINT ~= nil
            and G.TheWorld.Map:GetTileAtPoint(pt:Get()) == G.WORLD_TILES.KLBQ_IMPRINT then
            actions[#actions+1] = imprint
        end
    end)
    for _, graph in ipairs({"wilson","wilson_client"}) do
        env.AddStategraphActionHandler(graph, G.ActionHandler(read, "doshortaction"))
        env.AddStategraphActionHandler(graph, G.ActionHandler(imprint, "doshortaction"))
    end
end

return M
