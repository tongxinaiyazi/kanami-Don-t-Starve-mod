"""Launch only an isolated offline DST regression world, preserving user saves."""
import argparse
import ctypes
import hashlib
import io
import json
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GAME=Path("E:/steam/steamapps/common/Don't Starve Together")
STORAGE=Path('D:/SOFTWARE/CodexData/temp/kanami_engine')
CANDIDATE_ROOT=Path('D:/SOFTWARE/CodexData/temp')


def read_body_candidate(source, allowed_source_root=CANDIDATE_ROOT):
    source=Path(source).resolve(strict=True)
    if not source.is_relative_to(Path(allowed_source_root).resolve()) or source==Path(allowed_source_root).resolve():
        raise ValueError('Body candidate source must be a dedicated directory under D: temp')
    payloads={}
    for name,member,magic in [('klbq_kanami.zip','build.bin',b'BILD'),('klbq_kanami_actions.zip','anim.bin',b'ANIM')]:
        path=source/name
        if not path.resolve(strict=True).is_relative_to(source):
            raise ValueError('Candidate source file escapes its directory: '+name)
        data=path.read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if archive.testzip() is not None:
                raise ValueError('Corrupt candidate zip: '+name)
            if member not in archive.namelist() or not archive.read(member).startswith(magic):
                raise ValueError('Candidate lacks valid '+member+': '+name)
        payloads[name]=data
    return source,payloads


def prepare_body_candidate(source,destination,*,allowed_source_root=CANDIDATE_ROOT,mods_root=None):
    """Prepare only task-owned verify assets. Independently callable; no game launch."""
    mods_root=Path(mods_root) if mods_root is not None else GAME/'mods'
    expected=mods_root.resolve()/'klbq_kanami_verify'
    destination=Path(destination)
    if destination.resolve()!=expected:
        raise ValueError('Body candidate destination must be the direct klbq_kanami_verify directory')
    if not (destination/'.kanami-task-owned').is_file():
        raise ValueError('Body candidate destination is not task-owned')
    source,payloads=read_body_candidate(source,allowed_source_root)
    anim=destination/'anim'
    if anim.resolve()!=expected/'anim':
        raise ValueError('Refusing redirected verify anim directory')
    anim.mkdir(exist_ok=True)
    report={'source':str(source),'destination':str(destination.resolve()),'files':{}}
    for name,data in payloads.items():
        target=anim/name
        temporary=anim/(name+'.candidate-tmp')
        if temporary.exists():
            raise ValueError('Stale candidate staging file: '+str(temporary))
        temporary.write_bytes(data)
        temporary.replace(target)
        source_hash=hashlib.sha256(data).hexdigest()
        installed_hash=hashlib.sha256(target.read_bytes()).hexdigest()
        if source_hash!=installed_hash:
            raise RuntimeError('Candidate copied hash mismatch: '+name)
        report['files'][name]={'source_sha256':source_hash,'installed_sha256':installed_hash,'bytes':len(data)}
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=140)
    parser.add_argument('--isolated-mod-copy',action='store_true',help='Test a separate mod copy without overwriting the user installed mod')
    parser.add_argument('--workshop-runtime',action='store_true',help='Load the installed Kanami Workshop copy and its native file manifest in the isolated test world')
    parser.add_argument('--body-candidate',type=Path,help='Candidate compiled/anim directory under D: temp; forces isolated-mod-copy and forbids happy')
    parser.add_argument('--prepare-only',action='store_true',help='With body-candidate, prepare and hash the verify copy without launching any process')
    parser.add_argument('--equipment',action='store_true',help='Enable the installed four/five/six equipment slots mod only in this test world')
    parser.add_argument('--void-probe',action='store_true');parser.add_argument('--void',action='store_true');parser.add_argument('--interactive',action='store_true')
    parser.add_argument('--happy',action='store_true',help='Test installed HappyPatch cap/rate and shadow forms in an isolated cluster')
    parser.add_argument('--weapons-only',action='store_true',help='Run native weapon checks without the resurrection timer')
    parser.add_argument('--bag-only',action='store_true',help='Target actual backpack crafting, auto equip and save/load')
    parser.add_argument('--inventory-guard-only',action='store_true',help='Test native theft, forced drops, death drops and ordinary work tools')
    parser.add_argument('--nahida',action='store_true',help='Enable the installed Nahida mod in the isolated compatibility test world')
    parser.add_argument('--audit-only',action='store_true',help='Run post-review native lifecycle and gameplay checks')
    parser.add_argument('--resources-only',action='store_true',help='Test terminal item, crafting and native Charlie death loot')
    parser.add_argument('--imprint-only',action='store_true',help='Test native imprint, work, save and material recipes')
    parser.add_argument('--resource-addon',action='store_true',help='Also enable the task-owned copy of the unchanged resource add-on')
    parser.add_argument('--test-admin',help='Grant admin only inside the isolated test cluster')
    parser.add_argument('--until-client-exits',type=int,help='Keep the interactive world until this task-owned client exits')
    parser.add_argument('--playtest',action='store_true',help='A clean interactive world for the user, without regression-world leftovers')
    parser.add_argument('--user-visual-mods',action='store_true',help='Load the locally observed user mod combination only in the isolated interactive world')
    args=parser.parse_args()
    if args.workshop_runtime and (args.isolated_mod_copy or args.body_candidate):
        parser.error('workshop-runtime uses the installed Workshop copy; choose one mod source')
    if args.prepare_only and not args.body_candidate:parser.error('prepare-only requires body-candidate')
    if args.body_candidate:
        if args.happy:parser.error('body-candidate tests must not enable happy')
        args.isolated_mod_copy=True
        # Validate both archives before touching even the isolated mod copy.
        read_body_candidate(args.body_candidate)
    if args.playtest and not args.interactive:parser.error('playtest requires interactive')
    if args.user_visual_mods and not args.interactive:parser.error('user-visual-mods requires interactive')
    if args.test_admin and (not args.interactive or not re.fullmatch(r'(OU_\d+|KU_[A-Za-z0-9_-]+)',args.test_admin)):
        parser.error('test-admin requires an interactive test and a valid DST userid')
    client_handle=None
    if args.until_client_exits:
        state=json.loads((Path('D:/SOFTWARE/CodexData/temp/kanami_client')/'client-process.json').read_text())
        if not args.interactive or state['pid']!=args.until_client_exits:parser.error('Only the task-owned client may be watched')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        client_handle=kernel.OpenProcess(0x100000,False,args.until_client_exits)
        if not client_handle:raise ctypes.WinError(ctypes.get_last_error())
    # These are new task-owned paths. No existing mod or world is replaced.
    modkey='workshop-3827702076' if args.workshop_runtime else 'klbq_kanami_verify' if args.isolated_mod_copy else 'klbq_kanami'
    copies=[('klbq_kanami_test',ROOT/'tests/engine_mod')]
    if not args.workshop_runtime:copies.insert(0,(modkey,ROOT/'mods/klbq_kanami'))
    for name,source in copies:
        destination=GAME/'mods'/name
        if args.body_candidate:
            expected=(GAME/'mods').resolve()/name
            if destination.resolve()!=expected or (destination/'anim').resolve()!=expected/'anim':
                raise ValueError('Refusing redirected candidate test mod directory '+str(destination))
        if destination.exists() and not (destination/'.kanami-task-owned').exists():
            raise RuntimeError('Refusing to overwrite unowned mod directory '+str(destination))
        shutil.copytree(source,destination,dirs_exist_ok=True)
        (destination/'.kanami-task-owned').write_text('Created by Kanami development on 2026-10-27\n')
        if args.isolated_mod_copy and name==modkey:
            info=destination/'modinfo.lua'
            info.write_text(info.read_text(encoding='utf-8').replace('name="香奈美 · 谢幕曲"','name="[开发验证副本] 香奈美 · 谢幕曲"'),encoding='utf-8')
    candidate_report=None
    if args.body_candidate:
        candidate_report=prepare_body_candidate(args.body_candidate,GAME/'mods'/modkey)
        report_dir=ROOT/'docs/reports';report_dir.mkdir(parents=True,exist_ok=True)
        (report_dir/'engine-body-candidate-preparation.json').write_text(json.dumps(candidate_report,indent=2),encoding='utf-8')
        print(json.dumps({'body_candidate':candidate_report,'prepared_only':args.prepare_only}),flush=True)
        if args.prepare_only:return
    bag_cluster='KanamiBag023'+('-happy' if args.happy else '')+('-void' if args.void else '')+('-equipment' if args.equipment else '')
    cluster_name='KanamiPlaytest' if args.playtest else bag_cluster if args.bag_only else 'KanamiHappy022' if args.happy else 'KanamiVoid' if args.void or args.void_probe else 'KanamiVisual' if args.interactive else 'KanamiSmoke'
    if args.workshop_runtime:cluster_name='KanamiWorkshopLoad'
    cluster=STORAGE/'DoNotStarveTogether'/cluster_name
    if not args.playtest and not args.happy and not cluster.exists() and cluster_name!='KanamiSmoke':
        base=STORAGE/'DoNotStarveTogether/KanamiSmoke'
        if base.exists():shutil.copytree(base,cluster)
    shard=cluster/'Master';shard.mkdir(parents=True,exist_ok=True)
    if args.test_admin:(cluster/'adminlist.txt').write_text(args.test_admin+'\n',encoding='utf-8')
    port=11016 if args.interactive else 11015
    (cluster/'cluster.ini').write_text('[GAMEPLAY]\ngame_mode=endless\nmax_players=2\npvp=false\npause_when_empty='+('true' if args.playtest else 'false')+'\n\n[NETWORK]\ncluster_name='+('Kanami Playtest' if args.playtest else 'Kanami isolated regression')+'\noffline_cluster=true\nlan_only_cluster=true\n\n[MISC]\nconsole_enabled=true\n\n[SHARD]\nshard_enabled=false\n')
    (shard/'server.ini').write_text('[NETWORK]\nserver_port='+str(port)+'\n\n[STEAM]\nauthentication_port=8767\nmaster_server_port=27017\n\n[SHARD]\nis_master=true\n')
    # worldgenoverride is the preset+overrides format; leveldataoverride instead
    # requires a complete level (id/name/desc/location). Do not conflate them.
    obsolete=shard/'leveldataoverride.lua'
    if obsolete.exists():obsolete.unlink()
    (shard/'worldgenoverride.lua').write_text('return {override_enabled=true,preset="SURVIVAL_TOGETHER",overrides={world_size="small",season_start="autumn",autumn="verylongseason",start_location="default"}}\n')
    mode='audit' if args.audit_only else 'bag' if args.bag_only else 'weapon_inputs' if args.weapons_only and (args.happy or args.void) else 'weapons' if args.weapons_only else 'happy' if args.happy else 'void_probe' if args.void_probe else 'void' if args.void else 'interactive' if args.interactive else 'base'
    if args.resources_only:mode='resources'
    if args.imprint_only:mode='imprint'
    if args.inventory_guard_only:mode='guard'
    if args.interactive:mode='interactive'
    extra=''
    if args.resource_addon:
        destination=GAME/'mods/klbq_kanami_resource_test'
        if destination.exists() and not (destination/'.kanami-task-owned').exists():
            raise RuntimeError('Refusing to replace unowned resource test mod')
        shutil.copytree(ROOT/'mods/klbq_resources',destination,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('art','docs','tests','tools','release','__pycache__'))
        (destination/'.kanami-task-owned').write_text('Task-owned resource coexistence fixture\n')
        extra+=', ["klbq_kanami_resource_test"]={enabled=true}'
    if args.equipment:
        reference=Path('E:/steam/steamapps/workshop/content/322330/3173431824/modinfo.lua')
        if not reference.is_file():raise RuntimeError('Installed equipment mod not found')
        extra+=', ["workshop-3173431824"]={enabled=true}'
    if args.happy:
        reference=Path('E:/steam/steamapps/workshop/content/322330/2886753796')
        junction=GAME/'mods/workshop-2886753796'
        if not reference.is_dir():raise RuntimeError('Installed HappyPatch not found')
        if not junction.exists():
            quote=lambda p:"'"+str(p).replace("'","''")+"'"
            subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(junction)+' -Target '+quote(reference)+' | Out-Null'],check=True)
        extra+=', ["workshop-2886753796"]={enabled=true,configuration_options={epic_armor_5=5,extra_change=true,boss_maxdamagetake=1,notboss_maxdamagetake=1,["Shadow World"]=1}}'
    if args.void or args.void_probe:
        reference=Path('E:/steam/steamapps/workshop/content/322330/2526778484')
        junction=GAME/'mods/workshop-2526778484'
        if not junction.exists():
            quote=lambda p:"'"+str(p).replace("'","''")+"'"
            subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(junction)+' -Target '+quote(reference)+' | Out-Null'],check=True)
            (ROOT/'docs/reports/void-junction-owned.txt').write_text(str(junction),encoding='utf-8')
        extra+=', ["workshop-2526778484"]={enabled=true}'
    if args.user_visual_mods:
        for name in ['workshop-661253977','workshop-1207269058','workshop-3750536829',
                     'workshop-2287303119','workshop-2941527805','klbq_lilith']:
            extra+=', ["'+name+'"]={enabled=true}'
    if args.nahida:
        if not Path('E:/steam/steamapps/workshop/content/322330/3520190450/modinfo.lua').is_file():
            raise RuntimeError('Installed Nahida mod not found')
        extra+=', ["workshop-3520190450"]={enabled=true}'
    (shard/'modoverrides.lua').write_text('return { ["'+modkey+'"]={enabled=true}, ["klbq_kanami_test"]={enabled=true,configuration_options={mode="'+mode+'"}}'+extra+' }\n')
    report=ROOT/'docs/reports';report.mkdir(parents=True,exist_ok=True)
    report_mode=mode+('-addon' if args.resource_addon else '')+('-happy' if (args.bag_only or args.weapons_only) and args.happy else '')+('-void' if (args.bag_only or args.weapons_only) and args.void else '')+('-equipment' if args.equipment else '')
    if args.workshop_runtime:report_mode+='-workshop'
    if args.nahida:report_mode+='-nahida'
    log=report/('engine-'+report_mode+'.log')
    command=[str(GAME/'bin64/dontstarve_dedicated_server_nullrenderer_x64.exe'),
        '-persistent_storage_root',str(STORAGE),'-conf_dir','DoNotStarveTogether',
        '-cluster',cluster_name,'-shard','Master','-offline','-bind_ip','0.0.0.0' if args.interactive else '127.0.0.1',
        '-port',str(port),'-skip_update_server_mods','-ugc_directory','E:/steam/steamapps/workshop']
    print('Starting isolated offline test world',flush=True)
    inbox=STORAGE/'interactive-command.lua'
    stop=STORAGE/'interactive-stop'
    if args.interactive:
        # Commands are read only from this isolated test harness, never from
        # game files or a user's normal save/profile.
        inbox.unlink(missing_ok=True);stop.unlink(missing_ok=True)
    with log.open('wb') as out:
        p=subprocess.Popen(command,cwd=GAME/'bin64',stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        started=time.monotonic();last_print=0;sent=False
        while p.poll() is None and (client_handle or time.monotonic()-started<args.seconds):
            time.sleep(1)
            if client_handle and kernel.WaitForSingleObject(client_handle,0)!=0x102:
                print('Task-owned client exited; closing its isolated test world',flush=True);break
            text=log.read_text(encoding='utf-8',errors='replace')
            if args.interactive and inbox.exists():
                command_text=inbox.read_text(encoding='utf-8').strip()
                inbox.unlink()
                if command_text:
                    p.stdin.write((command_text+'\n').encode('utf-8'));p.stdin.flush()
                    print('Executed isolated QA command',flush=True)
            if args.interactive and stop.exists():
                stop.unlink();break
            if '[KANAMI_TEST]' in text and not sent:
                try:p.stdin.write(b'print("KANAMI_CONSOLE_OK")\n');p.stdin.flush();sent=True
                except OSError:pass
            elapsed=int(time.monotonic()-started)
            if elapsed-last_print>=15:
                markers=[l for l in text.splitlines() if '[KANAMI_' in l]
                print('Elapsed',elapsed,'s; recent:', '\n'.join(markers[-3:]) or 'world starting',flush=True);last_print=elapsed
            if 'LUA ERROR' in text or 'Error loading prefab' in text:
                print('Engine Lua error detected; shutting down isolated process',flush=True)
                try:p.stdin.write(b'c_shutdown(false)\n');p.stdin.flush()
                except OSError:pass
                break
        if p.poll() is None:
            try:p.stdin.write(b'c_shutdown(false)\n');p.stdin.flush();p.wait(timeout=12)
            except (OSError,subprocess.TimeoutExpired):p.terminate();p.wait(timeout=10)
    text=log.read_text(encoding='utf-8',errors='replace')
    markers=[l for l in text.splitlines() if '[KANAMI_' in l]
    print('\n'.join(markers),flush=True)
    result={'exit_code':p.returncode,'complete':'[KANAMI_TEST] COMPLETE' in text or (args.interactive and ('INTERACTIVE_READY' in text or (args.playtest and 'Sim paused' in text))),
        'pass':sum('PASS' in l for l in markers),'fail':sum('FAIL' in l for l in markers),
        'lua_error':'LUA ERROR' in text,'log':str(log)}
    if candidate_report:result['body_candidate']=candidate_report
    (report/('engine-'+report_mode+'-result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    if client_handle:kernel.CloseHandle(client_handle)
    if not result['complete'] or result['fail'] or result['lua_error'] or result['exit_code']!=0:raise SystemExit(1)

if __name__=='__main__':main()
