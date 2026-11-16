local Camera=require("klbq_kanami/camera")
local M={}
function M.Install(env)
    local G=env.GLOBAL
    local keys={c=env.GetModConfigData("key_string") or G.KEY_R,z=env.GetModConfigData("key_z") or G.KEY_Z,x=env.GetModConfigData("key_x") or G.KEY_X}
    local function Cast(key)
        local p=G.ThePlayer
        if not p or p.prefab~="klbq_kanami" or p:HasTag("playerghost") or G.IsPaused() then return end
        local screen=G.TheFrontEnd:GetActiveScreen()
        if not p.HUD or p.HUD:IsChatInputScreenOpen() or (screen and screen.name~="HUD") then return end
        env.SendModRPCToServer(env.GetModRPC("KLBQ_KANAMI","skill"),key)
    end
    for key,code in pairs(keys) do G.TheInput:AddKeyUpHandler(code,function() Cast(key) end) end
    env.AddClassPostConstruct("widgets/controls",function(controls)
        if not controls.owner or controls.owner.prefab~="klbq_kanami" then return end
        local HUD=require("widgets/klbq_kanami_hud")
        controls.klbq_kanami=controls:AddChild(HUD(controls.owner,Cast,keys))
        controls.klbq_kanami:SetScaleMode(G.SCALEMODE_PROPORTIONAL)
        controls.klbq_kanami:SetHAnchor(G.ANCHOR_LEFT)
        controls.klbq_kanami:SetVAnchor(G.ANCHOR_BOTTOM)
        controls.klbq_kanami:SetMaxPropUpscale(G.MAX_HUD_SCALE)
        controls.klbq_kanami:SetPosition(92,145)
        controls.klbq_kanami:SetScale(.85)
        local ShotBar=require("widgets/klbq_kanami_shotbar")
        controls.klbq_kanami_shotbar=controls:AddChild(ShotBar(controls.owner))
    end)
    env.AddPrefabPostInit("klbq_kanami",function(inst)
        local session
        local function Stop() Camera.Stop(session);session=nil end
        inst:ListenForEvent("onremove",Stop)
        inst:ListenForEvent("playerdeactivated",Stop)
        inst:DoPeriodicTask(.1,function()
            if inst~=G.ThePlayer then if session then Stop() end;return end
            local enabled=inst._klbq_z:value() and not inst:HasTag("playerghost")
            if enabled and not session then session=Camera.Start(G.TheCamera,env.GetModConfigData("camera_distance") or 80)
            elseif not enabled and session then Stop() end
        end)
    end)
end
return M
