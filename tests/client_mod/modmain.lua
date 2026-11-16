local G=GLOBAL
local lastcommand
G.rawset(G,"KANAMI_QA",{After=function(delay,fn)
    return G.ThePlayer:DoTaskInTime(delay,function()
        local ok,err=G.pcall(fn)
        print("[KANAMI_CLIENT_QA] AFTER",ok,G.tostring(err))
    end)
end})
local function poll()
    G.TheSim:GetPersistentString("kanami_qa_command",function(ok,s)
        if not ok or s==lastcommand or s=="" then return end
        lastcommand=s
        local fn,err=G.loadstring(s,"Kanami isolated visual QA")
        if not fn then print("[KANAMI_CLIENT_QA] ERROR",G.tostring(err));return end
        G.setfenv(fn,G)
        local success,result=G.pcall(fn)
        print("[KANAMI_CLIENT_QA] COMMAND",success,G.tostring(result))
    end)
end
AddClassPostConstruct("screens/redux/popupdialog",function(self)
    self.inst:DoTaskInTime(.5,function()
        local body=self.dialog and self.dialog.body
        if body and body:GetString()==G.STRINGS.UI.SERVERLISTINGSCREEN.MOD_WARNING_BODY then
            for _,button in G.ipairs(self.buttons) do
                if button.text==G.STRINGS.UI.SERVERLISTINGSCREEN.CONTINUE and button.cb then
                    button.cb();break
                end
            end
        end
    end)
end)
for _,package in G.ipairs({"screens/redux/multiplayermainscreen","screens/redux/mainscreen"}) do
    AddClassPostConstruct(package,function(self)
        self.inst:DoPeriodicTask(.4,poll)
        self.inst:DoTaskInTime(5,function()
            if G.rawget(G,"KANAMI_QA_CONNECTING") or G.TheNet:GetIsClient() then return end
            G.rawset(G,"KANAMI_QA_CONNECTING",true)
            print("[KANAMI_CLIENT_QA] CONNECT",G.c_connect("127.0.0.1",11016))
        end)
    end)
end
AddClassPostConstruct("screens/redux/lobbyscreen",function(self)
    self.inst:DoPeriodicTask(.4,poll)
    self.inst:DoTaskInTime(3,function()
        G.TheNet:SendSpawnRequestToServer("klbq_kanami","klbq_kanami_none","","","","",{},nil,{})
    end)
end)
AddPlayerPostInit(function(inst)
    inst:DoTaskInTime(1,function()
        if inst==G.ThePlayer then
            for _,screen in G.ipairs(G.TheFrontEnd.screenstack) do
                if screen.name=="LobbyScreen" then G.TheFrontEnd:PopScreen(screen);break end
            end
            print("[KANAMI_CLIENT_QA] PLAYER_READY",inst.prefab)
            inst:DoPeriodicTask(.3,poll)
        end
    end)
end)
