"""Operate only the task-owned isolated DST client for visual regression QA."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
import subprocess
import time
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
GAME=Path("E:/steam/steamapps/common/Don't Starve Together")
TEMP=Path('D:/SOFTWARE/CodexData/temp/kanami_client')
STATE=TEMP/'client-process.json'
user=C.WinDLL('user32',use_last_error=True)
user.SetForegroundWindow.argtypes=[W.HWND]
user.GetForegroundWindow.restype=W.HWND
user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
user.GetWindowTextLengthW.argtypes=[W.HWND]
user.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
user.IsWindowVisible.argtypes=[W.HWND]
try:user.SetProcessDpiAwarenessContext(C.c_void_p(-4))
except (AttributeError,OSError):pass

def window():
    state=json.loads(STATE.read_text());found=[]
    callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def visit(hwnd,param):
        pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid))
        if pid.value==state['pid'] and user.IsWindowVisible(hwnd):
            n=user.GetWindowTextLengthW(hwnd);title=C.create_unicode_buffer(n+1);user.GetWindowTextW(hwnd,title,n+1)
            found.append((hwnd,title.value))
        return True
    cb=callback(visit);user.EnumWindows(cb,0)
    if not found:raise RuntimeError('Task-owned client has no visible window yet')
    return found[0]

class KEYBDINPUT(C.Structure):
    _fields_=[('wVk',W.WORD),('wScan',W.WORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class MOUSEINPUT(C.Structure):
    _fields_=[('dx',W.LONG),('dy',W.LONG),('mouseData',W.DWORD),('dwFlags',W.DWORD),('time',W.DWORD),('dwExtraInfo',C.c_size_t)]
class UNION(C.Union):_fields_=[('ki',KEYBDINPUT),('mi',MOUSEINPUT)]
class INPUT(C.Structure):_fields_=[('type',W.DWORD),('u',UNION)]
user.SendInput.argtypes=[W.UINT,C.POINTER(INPUT),C.c_int]
def send_key(vk=0,scan=0,flags=0):
    if vk and not scan:
        # SDL's digital controls can ignore scan-code-only synthetic letters
        # with the active IME. Keep the virtual key alongside its scan code.
        scan=user.MapVirtualKeyW(vk,0)
    value=INPUT(1,UNION(ki=KEYBDINPUT(vk,scan,flags,0,0)))
    if user.SendInput(1,C.byref(value),C.sizeof(value))!=1:raise C.WinError(C.get_last_error())
def focus(hwnd):
    if user.GetForegroundWindow()==hwnd:return
    user.ShowWindow(hwnd,9)
    current=C.WinDLL('kernel32').GetCurrentThreadId()
    foreground=user.GetWindowThreadProcessId(user.GetForegroundWindow(),None)
    attached=bool(foreground and current!=foreground and user.AttachThreadInput(current,foreground,True))
    try:user.BringWindowToTop(hwnd);user.SetForegroundWindow(hwnd)
    finally:
        if attached:user.AttachThreadInput(current,foreground,False)
    time.sleep(.15)
    if user.GetForegroundWindow()!=hwnd:raise RuntimeError('Refusing input: task-owned game is not foreground')

def capture_background(hwnd,path):
    """Read only our window's render surface without taking keyboard focus."""
    g=C.WinDLL('gdi32')
    user.GetDC.argtypes=[W.HWND];user.GetDC.restype=W.HDC
    user.PrintWindow.argtypes=[W.HWND,W.HDC,W.UINT]
    g.CreateCompatibleDC.argtypes=[W.HDC];g.CreateCompatibleDC.restype=W.HDC
    g.CreateCompatibleBitmap.argtypes=[W.HDC,C.c_int,C.c_int];g.CreateCompatibleBitmap.restype=W.HBITMAP
    g.SelectObject.argtypes=[W.HDC,W.HANDLE];g.SelectObject.restype=W.HANDLE
    g.DeleteObject.argtypes=[W.HANDLE];g.DeleteDC.argtypes=[W.HDC]
    user.ReleaseDC.argtypes=[W.HWND,W.HDC]
    class BI(C.Structure):
        _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('image',W.DWORD),('x',W.LONG),('y',W.LONG),('used',W.DWORD),('important',W.DWORD)]
    g.GetDIBits.argtypes=[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.POINTER(BI),W.UINT]
    r=W.RECT();user.GetWindowRect(hwnd,C.byref(r));w=r.right-r.left;h=r.bottom-r.top
    screen=user.GetDC(hwnd);dc=g.CreateCompatibleDC(screen);bitmap=g.CreateCompatibleBitmap(screen,w,h);old=g.SelectObject(dc,bitmap)
    try:
        if not user.PrintWindow(hwnd,dc,2):raise RuntimeError('Cannot capture owned window')
        info=BI(C.sizeof(BI),w,-h,1,32,0,0,0,0,0,0);data=C.create_string_buffer(w*h*4)
        g.GetDIBits(dc,bitmap,0,h,data,C.byref(info),0)
        Image.frombuffer('RGB',(w,h),data,'raw','BGRX',0,1).save(path)
    finally:
        g.SelectObject(dc,old);g.DeleteObject(bitmap);g.DeleteDC(dc);user.ReleaseDC(hwnd,screen)

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['launch','capture','sequence','key','type','click','quit'])
    p.add_argument('value',nargs='?');p.add_argument('--direct',action='store_true');p.add_argument('--file');p.add_argument('--background',action='store_true');p.add_argument('--hold-key',type=lambda s:int(s,0));p.add_argument('--right',action='store_true');args=p.parse_args();TEMP.mkdir(parents=True,exist_ok=True)
    if args.command=='launch':
        if STATE.exists():
            try:
                hwnd,title=window();print(json.dumps({'existing':True,'hwnd':hwnd,'title':title}));return
            except RuntimeError:pass
        storage=TEMP/'storage';storage.mkdir(exist_ok=True)
        arguments=['-persistent_storage_root',str(storage),'-conf_dir','KanamiClientTest','-offline','-windowed','-w','1280','-h','720','-skip_update_server_mods','-ugc_directory','E:/steam/steamapps/workshop']
        if args.direct:
            environment=os.environ.copy();environment.update(SteamAppId='322330',SteamGameId='322330')
            process=subprocess.Popen([str(GAME/'bin64/dontstarve_steam_x64.exe')]+arguments,cwd=GAME/'bin64',env=environment)
            STATE.write_text(json.dumps({'pid':process.pid,'storage':str(storage)}));print('Launched client with Steam application context PID',process.pid);return
        # Steam must provide its application context; direct EXE launch exits
        # with Steam initialization result=1 on this machine.
        subprocess.Popen([str(GAME.parents[2]/'steam.exe'),'-applaunch','322330']+arguments,cwd=GAME/'bin64',creationflags=subprocess.CREATE_NO_WINDOW)
        query="Get-CimInstance Win32_Process -Filter \"Name='dontstarve_steam_x64.exe'\" | Where-Object { $_.CommandLine -like '*kanami_client*' } | Select-Object -ExpandProperty ProcessId"
        for _ in range(20):
            ids=subprocess.run(['powershell.exe','-NoProfile','-Command',query],capture_output=True,text=True).stdout.split()
            if ids:
                pid=int(ids[0]);STATE.write_text(json.dumps({'pid':pid,'storage':str(storage)}));print('Launched isolated client PID',pid);return
            time.sleep(1)
        raise RuntimeError('Steam did not start the isolated client within20seconds')
    hwnd,title=window()
    if args.command in ('capture','sequence'):
        helper=Path('C:/Users/ASUS/.codex/skills/screenshot/scripts/take_screenshot.ps1')
        samples=[(0,args.value or 'client.png')] if args.command=='capture' else [(float(x.split(':',1)[0]),x.split(':',1)[1]) for x in args.value.split(',')]
        started=time.monotonic()
        if args.hold_key:focus(hwnd);send_key(args.hold_key)
        try:
            for delay,filename in samples:
                while time.monotonic()-started<delay:time.sleep(min(.5,delay-(time.monotonic()-started)))
                if args.hold_key and user.GetForegroundWindow()!=hwnd:raise RuntimeError('Input focus changed; releasing held key')
                output=TEMP/filename
                if args.background:
                    capture_background(hwnd,output);print(output)
                else:
                    focus(hwnd)
                    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(helper),'-WindowHandle',str(hwnd),'-Path',str(output)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        finally:
            if args.hold_key:send_key(args.hold_key,flags=2)
        return
    if args.command=='quit':
        user.PostMessageW(hwnd,0x10,0,0);print('Sent close to task-owned client');return
    focus(hwnd)
    if args.command=='key':
        vk=int(args.value,0);send_key(vk);time.sleep(.15);send_key(vk,flags=2);time.sleep(.25)
    elif args.command=='type':
        value=Path(args.file).read_text(encoding='utf-8') if args.file else args.value
        for char in value:
            if user.GetForegroundWindow()!=hwnd:raise RuntimeError('Input focus changed; stopped')
            send_key(scan=ord(char),flags=4);send_key(scan=ord(char),flags=6);time.sleep(.002)
    elif args.command=='click':
        x,y=map(int,args.value.split(','));point=W.POINT(x,y)
        user.ClientToScreen(hwnd,C.byref(point));user.SetCursorPos(point.x,point.y);time.sleep(.2)
        value=INPUT(0,UNION(mi=MOUSEINPUT(0,0,0,8 if args.right else 2,0,0)));user.SendInput(1,C.byref(value),C.sizeof(value))
        time.sleep(.12);value.u.mi.dwFlags=16 if args.right else 4;user.SendInput(1,C.byref(value),C.sizeof(value));time.sleep(.3)

if __name__=='__main__':main()
