"""Use only the owned isolated DST server/client to verify imprint visuals/RPC."""
import argparse,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import kanami_client_qa as qa
from prepare_kanami_client import STORAGE,write_klei,select_profile
TEMP=Path('D:/SOFTWARE/CodexData/temp/kanami_client')
REPORT=ROOT/'docs/reports/engine-interactive-addon-equipment.log'

def server(code):
    token='IMPRINT_ACK_'+str(time.time_ns())
    # Dedicated-server stdin evaluates one line at a time.
    code=code.replace('\n',' ')
    (Path('D:/SOFTWARE/CodexData/temp/kanami_engine')/'interactive-command.lua').write_text(code+';print("'+token+'")',encoding='utf8')
    for _ in range(100):
        if ']: '+token in REPORT.read_text(encoding='utf8',errors='replace'):return
        time.sleep(.1)
    raise RuntimeError('Owned server did not acknowledge command')

def client(code):
    token='IMPRINT_CLIENT_ACK_'+str(time.time_ns())
    profile=select_profile()
    write_klei(profile/'kanami_qa_command',code+';print("'+token+'")')
    for _ in range(100):
        if ']: '+token in (STORAGE/'client_log.txt').read_text(encoding='utf8',errors='replace'):return
        time.sleep(.1)
    raise RuntimeError('Owned client did not acknowledge command')

def capture(name):
    folder=TEMP/'imprint-visual';folder.mkdir(exist_ok=True)
    hwnd,_=qa.window()
    path=folder/(name+'.png')
    from PIL import Image,ImageStat,ImageGrab
    for _ in range(8):
        if qa.user.GetForegroundWindow()==hwnd:
            rect=qa.W.RECT();qa.user.GetWindowRect(hwnd,qa.C.byref(rect))
            ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom),all_screens=True).save(path)
        else:qa.capture_background(hwnd,path)
        with Image.open(path) as im:
            w,h=im.size
            if max(ImageStat.Stat(im.crop((w//2-120,h//2-120,w//2+120,h//2+120))).mean)>5:break
        time.sleep(.25)
    else:raise RuntimeError('Owned render surface returned an empty frame')
    return path

def setup():
    server('''local p=AllPlayers[1];assert(p,"no owned QA player");
      if p._imprintGod then p._imprintGod:Cancel() end;
      p._imprintGod=p:DoPeriodicTask(.2,function()
        if p:HasTag("playerghost") then p:PushEvent("respawnfromghost",{source=p})
        else p.components.health:SetInvincible(true);p.components.health:SetPercent(1);
          p.components.hunger:SetPercent(1);p.components.sanity:SetPercent(1);
          p.components.temperature:SetTemperature(22);p:AddTag("notarget");
          local k=p.components.klbq_kanami;k.state.deadlines.protect=nil;k.state.string=false;k:Sync()
        end
      end);TheWorld:PushEvent("ms_setclocksegs",{day=16,dusk=0,night=0})''')
    time.sleep(3)
    server('''local p=AllPlayers[1];p.components.locomotor:Stop();p:ClearBufferedAction();
      p.sg:GoToState("idle");local x,y,z=p.Transform:GetWorldPosition();
      for _,e in ipairs(TheSim:FindEntities(x,y,z,18,nil,{"player","INLIMBO"})) do
        if e.components.inventoryitem or e.components.combat or e.prefab=="skeleton_player" then e:Remove() end
      end;
      for _,t in pairs(p.components.inventory.itemslots) do t:Remove() end;
      local w=SpawnPrefab("klbq_imprint_tool");p.components.inventory:GiveItem(w);p._imprintTool=w;
      for _,n in ipairs({"goldenaxe","goldenpickaxe","goldenshovel","multitool_axe_pickaxe"}) do
        local s=SpawnPrefab(n);s.components.finiteuses:SetUses(1);p.components.inventory:GiveItem(s)
      end;print("IMPRINT_VISUAL_SETUP",p.AnimState:GetBuild())''')
    client('TheCamera:SetDistance(14);TheCamera:SetHeadingTarget(180);ThePlayer.AnimState:Resume()')
    time.sleep(1);print(capture('blank-inventory'))

def rpc():
    for name in ('goldenaxe','goldenpickaxe','goldenshovel','multitool_axe_pickaxe'):
        client('''local inv=ThePlayer.replica.inventory;local w,s;
          for _,t in pairs(inv:GetItems()) do
            if t.prefab=="klbq_imprint_tool" then w=t elseif t.prefab=="'''+name+'''" then s=t end
          end;assert(w and s,"QA samples missing");
          local action=ThePlayer.components.playercontroller:GetItemUseAction(s,w);
          print("IMPRINT_RPC_DISCOVERY","'''+name+'''",action and action.action.id);
          assert(action and action.action==ACTIONS.KLBQ_IMPRINT);
          inv:ControllerUseItemOnItemFromInvTile(w,s)''')
        time.sleep(1.5)
        server('local p=AllPlayers[1];print("IMPRINT_RPC_RESULT","'+name+'",require("klbq_kanami/imprint").Mask(p._imprintTool))')
    server('local p=AllPlayers[1];assert(require("klbq_kanami/imprint").Mask(p._imprintTool)==15);p.components.inventory:Equip(p._imprintTool);p.sg:GoToState("idle")')
    time.sleep(.4);print(capture('unlocked-held'))

def persist():
    server('''local p=AllPlayers[1];local I=require("klbq_kanami/imprint");
      local w=p.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS);assert(w and I.Mask(w)==15);
      local t=SpawnPrefab("klbq_imprint_tool");p.components.inventory:GiveItem(t);
      local s=SpawnPrefab("multitool_axe_pickaxe");p.components.inventory:GiveItem(s);
      assert(t.components.trader:AcceptGift(p,s));assert(I.Mask(t)==8);
      local b=SpawnPrefab("klbq_resource_base_string");b.components.stackable:SetStackSize(8);p.components.inventory:GiveItem(b);
      c_save();print("IMPRINT_PERSIST_SAVED",I.Mask(w),I.Mask(t))''')
    time.sleep(4)

def restored():
    server('''local p=AllPlayers[1];assert(p);local I=require("klbq_kanami/imprint");
      local w=p.components.inventory:GetEquippedItem(EQUIPSLOTS.HANDS);assert(w and I.Mask(w)==15);
      local other=p.components.inventory:FindItem(function(t)return t.prefab=="klbq_imprint_tool" and I.Mask(t)==8 end);
      assert(other and not other.components.tool:CanDoAction(ACTIONS.MINE));p._imprintTool=w;
      if p._imprintGod then p._imprintGod:Cancel() end;
      p._imprintGod=p:DoPeriodicTask(.2,function()p.components.health:SetInvincible(true);p.components.health:SetPercent(1);
        p.components.hunger:SetPercent(1);p.components.sanity:SetPercent(1);p.components.temperature:SetTemperature(22);p:AddTag("notarget") end);
      p.components.klbq_kanami.state.deadlines.protect=nil;p.components.klbq_kanami:Sync();
      local portal=c_find("multiplayer_portal");if portal then local x,y,z=portal.Transform:GetWorldPosition();p.Physics:Teleport(x+4,y,z+4) end;
      TheWorld:PushEvent("ms_setseason","autumn");TheWorld:PushEvent("ms_setclocksegs",{day=16,dusk=0,night=0});
      print("IMPRINT_RELOAD_SERVER",I.Mask(w),I.Mask(other),p.components.inventory:Has("klbq_resource_base_string",8))''')
    client('''local I=require("klbq_kanami/imprint");local w=ThePlayer.replica.inventory:GetEquippedItem(EQUIPSLOTS.HANDS);
      assert(w and I.Mask(w)==15);print("IMPRINT_RELOAD_CLIENT",I.Mask(w));TheCamera:SetDistance(14);TheCamera:SetHeadingTarget(180);
      ThePlayer.AnimState:SetScale(1.5,1.5)''')
    time.sleep(.5);print(capture('restored-idle-projection'))

def poses():
    server('''local p=AllPlayers[1];local portal=c_find("multiplayer_portal");local x,y,z=portal.Transform:GetWorldPosition();
      for dx=16,32,4 do if TheWorld.Map:IsPassableAtPoint(x+dx,y,z+12) then x=x+dx;z=z+12;break end end;
      p.Physics:Teleport(x,y,z);p.components.locomotor:Stop();p:ClearBufferedAction();p.sg:GoToState("idle");
      for _,e in ipairs(TheSim:FindEntities(x,y,z,14,nil,{"player","INLIMBO"})) do
        if e~=TheWorld and e.prefab~="multiplayer_portal" then e:Remove() end
      end;TheWorld:PushEvent("ms_nextphase")''')
    client('''TheCamera:SetDistance(14);ThePlayer.AnimState:SetScale(1.5,1.5);
      if not ThePlayer._imprintQALight then local e=CreateEntity();e.entity:AddTransform();e.entity:AddLight();
        e.entity:SetParent(ThePlayer.entity);e.Light:SetRadius(18);e.Light:SetIntensity(.9);e.Light:SetFalloff(.3);
        e.Light:SetColour(1,1,1);e.Light:Enable(true);ThePlayer._imprintQALight=e end''')
    time.sleep(1)
    names=[]
    for angle,direction in [(90,'side'),(0,'back'),(180,'front')]:
        for action,prefab,mode in [('CHOP','evergreen','chop'),('MINE','rock2','mine'),('DIG','sapling','dig')]:
            server('''local p=AllPlayers[1];p.components.locomotor:Stop();p:ClearBufferedAction();p.sg:GoToState("idle");
              if p._imprintTarget and p._imprintTarget:IsValid() then p._imprintTarget:Remove() end;
              local t=SpawnPrefab("'''+prefab+'''");local x,y,z=p.Transform:GetWorldPosition();
              local a='''+str(angle)+'''*DEGREES;t.Transform:SetPosition(x+1.8*math.cos(a),y,z-1.8*math.sin(a));p._imprintTarget=t;
              if t.components.workable then t.components.workable:SetWorkLeft(10) end;
              t:ListenForEvent("worked",function()print("IMPRINT_WORK_EXECUTED","'''+direction+' '+mode+'''")end);
              if t.components.pickable then t.components.pickable:MakeEmpty() end;
              print("IMPRINT_VISUAL_TARGET","'''+direction+' '+mode+'''")''')
            time.sleep(.8)
            client('''local p=ThePlayer;p:ClearBufferedAction();local c=p.components.playercontroller;
              c:RemoteStopControl(CONTROL_ACTION);
              local target=FindEntity(p,5,function(t)return t.prefab=="'''+prefab+'''" end);
              local action=c:GetActionButtonAction(target);
              print("IMPRINT_VISUAL_CLIENT_ACTION","'''+direction+' '+mode+'''",action and action.action.id);
              assert(action and action.action==ACTIONS.'''+action+''');
              if c.locomotor then action.preview_cb=function()c:RemoteActionButton(action,true)end;
                c.locomotor:PreviewAction(action,true) else c:RemoteActionButton(action,true) end;
              target.AnimState:SetMultColour(1,1,1,.12)''')
            time.sleep(.05)
            name=direction+'-'+mode;names.append((name,capture(name)))
            client('ThePlayer.components.playercontroller:RemoteStopControl(CONTROL_ACTION)')
            time.sleep(.7)
    server('local p=AllPlayers[1];p.components.locomotor:Stop();p:ClearBufferedAction();p.sg:GoToState("idle");if p._imprintTarget and p._imprintTarget:IsValid() then p._imprintTarget:Remove() end')
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(1080,1080),(30,30,35));draw=ImageDraw.Draw(sheet)
    for i,(name,path) in enumerate(names):
        im=Image.open(path);w,h=im.size
        # The in-game player is below centre because the HUD occupies the floor.
        im=im.crop((w//2-450,h//2-350,w//2+450,h//2+550)).resize((340,340))
        sheet.paste(im,((i%3)*360,(i//3)*360+20));draw.text(((i%3)*360+5,(i//3)*360+3),name,fill='white')
    sheet.save(ROOT/'docs/reports/imprint-work-views.png');print('Saved nine actual native work poses')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['setup','rpc','persist','restored','poses','slow','status']);a=parser.parse_args()
    if a.stage=='setup':setup()
    elif a.stage=='rpc':rpc()
    elif a.stage=='persist':persist()
    elif a.stage=='restored':restored()
    elif a.stage=='poses':poses()
    elif a.stage=='slow':slow()
    else:
        client('print("IMPRINT_CLIENT_STATUS",ThePlayer.prefab,ThePlayer.AnimState:GetBuild(),ThePlayer:HasTag("playerghost"))')
        print(capture('status'))
def slow():
    # Native slow motion keeps the brief DIG projection observable. It changes
    # neither stategraphs nor the tool's projection selection/render methods.
    server('''local p=AllPlayers[1];local portal=c_find("multiplayer_portal");local x,y,z=portal.Transform:GetWorldPosition();
      for dx=16,32,4 do if TheWorld.Map:IsPassableAtPoint(x+dx,y,z+12) then x=x+dx;z=z+12;break end end;
      p.Physics:Teleport(x,y,z);for _,e in ipairs(TheSim:FindEntities(x,y,z,14,nil,{"player","INLIMBO"})) do
        if e~=TheWorld and e.prefab~="multiplayer_portal" then e:Remove() end end;TheSim:SetTimeScale(.15)''')
    client('''TheSim:SetTimeScale(.15);if not ThePlayer._imprintQALight then
      local e=CreateEntity();e.entity:AddTransform();e.entity:AddLight();e.entity:SetParent(ThePlayer.entity);
      e.Light:SetRadius(18);e.Light:SetIntensity(.9);e.Light:SetFalloff(.3);e.Light:SetColour(1,1,1);e.Light:Enable(true);
      ThePlayer._imprintQALight=e end''')
    frames=[]
    for mode,prefab in [('chop','evergreen'),('mine','rock2'),('dig','sapling')]:
        server('''local p=AllPlayers[1];p.components.locomotor:Stop();p:ClearBufferedAction();p.sg:GoToState("idle");
          if p._imprintTarget and p._imprintTarget:IsValid() then p._imprintTarget:Remove() end;
          local t=SpawnPrefab("'''+prefab+'''");local x,y,z=p.Transform:GetWorldPosition();
          t.Transform:SetPosition(x-(t.prefab=="sapling" and .5 or 1.6),y,z);
          if t.components.pickable then t.components.pickable:MakeEmpty() end;p._imprintTarget=t;
          t:ListenForEvent("worked",function()print("IMPRINT_SLOW_WORKED","'''+mode+'''")end)''')
        client('''local p=ThePlayer;local c=p.components.playercontroller;c:RemoteStopAllControls();p:ClearBufferedAction();
          p.sg:GoToState("idle");local t=FindEntity(p,5,function(e)return e.prefab=="'''+prefab+'''"end);
          local a=c:GetActionButtonAction(t);assert(a and a.action==ACTIONS.'''+mode.upper()+''');
          a.preview_cb=function()c:RemoteActionButton(a,true)end;c.locomotor:PreviewAction(a,true);
          t.AnimState:SetMultColour(1,1,1,.12)''')
        time.sleep(.5)
        for _ in range(8):
            server('local p=AllPlayers[1];print("IMPRINT_SLOW_FORM","'+mode+'",p.sg.currentstate.name,require("klbq_kanami/imprint").HeldForm(p))')
            lines=[l for l in REPORT.read_text(encoding='utf8',errors='replace').splitlines()
                   if ']: IMPRINT_SLOW_FORM\t'+mode+'\t' in l]
            if lines and lines[-1].strip().endswith('\t'+mode):break
            time.sleep(.4)
        else:raise RuntimeError('Native state never selected '+mode+' projection')
        frames.append((mode,capture('slow-'+mode)))
        time.sleep(5)
    client('TheSim:SetTimeScale(1);ThePlayer.components.playercontroller:RemoteStopAllControls()')
    server('''TheSim:SetTimeScale(1);local p=AllPlayers[1];p.components.locomotor:Stop();p:ClearBufferedAction();
      p.sg:GoToState("idle");if p._imprintTarget and p._imprintTarget:IsValid() then p._imprintTarget:Remove() end;
      print("IMPRINT_FINAL_IDLE",require("klbq_kanami/imprint").HeldForm(p))''')
    time.sleep(.5);frames.append(('idle',capture('final-idle-disc')))
    from PIL import Image,ImageDraw
    sheet=Image.new('RGB',(1440,380),(30,30,35));d=ImageDraw.Draw(sheet)
    for i,(name,path) in enumerate(frames):
        im=Image.open(path);w,h=im.size;im=im.crop((w//2-450,h//2-350,w//2+450,h//2+550)).resize((350,350))
        sheet.paste(im,(i*360,24));d.text((i*360+6,6),name,fill='white')
    sheet.save(ROOT/'docs/reports/imprint-work-confirmed.png')
    print('Saved native slow-motion work and restored idle')

if __name__=='__main__':main()
