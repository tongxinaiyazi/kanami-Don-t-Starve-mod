"""Isolated offline Void tests. Never reads or writes the user's saves."""
import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = Path("E:/steam/steamapps/common/Don't Starve Together")
STORAGE = Path('D:/SOFTWARE/CodexData/temp/kanami_void_test')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['control', 'combat'])
    parser.add_argument('--kanami-mod',default='klbq_kanami')
    parser.add_argument('--report-suffix',default='')
    args = parser.parse_args()
    if not re.fullmatch(r'klbq_kanami(?:_verify)?',args.kanami_mod) or not re.fullmatch(r'[a-zA-Z0-9_-]*',args.report_suffix):
        parser.error('Invalid task-owned mod key or report suffix')
    fixture = GAME/'mods/klbq_kanami_void_test'
    if fixture.exists() and not (fixture/'.kanami-void-task-owned').exists():
        raise RuntimeError('Refusing unowned fixture directory')
    shutil.copytree(ROOT/'tests/void_mod', fixture, dirs_exist_ok=True)
    (fixture/'.kanami-void-task-owned').write_text('isolated Void test fixture')
    if not (GAME/'mods/workshop-2526778484').exists() and not Path('E:/steam/steamapps/workshop/content/322330/2526778484/modinfo.lua').is_file():
        raise RuntimeError('Installed Void Realm source missing')
    if args.mode == 'combat' and not (GAME/'mods'/args.kanami_mod/'.kanami-task-owned').exists():
        raise RuntimeError('Task-owned Kanami installation missing')
    cluster = STORAGE/'DoNotStarveTogether'/('VoidControl' if args.mode=='control' else 'VoidCombat')
    if args.mode == 'combat' and not cluster.exists():
        control = STORAGE/'DoNotStarveTogether/VoidControl'
        if control.exists(): shutil.copytree(control, cluster)
    shard = cluster/'Master'; shard.mkdir(parents=True,exist_ok=True)
    (cluster/'cluster.ini').write_text('[GAMEPLAY]\ngame_mode=endless\nmax_players=2\npvp=false\npause_when_empty=false\n[NETWORK]\ncluster_name=Void isolated regression\noffline_cluster=true\nlan_only_cluster=true\n[MISC]\nconsole_enabled=true\n[SHARD]\nshard_enabled=false\n')
    (shard/'server.ini').write_text('[NETWORK]\nserver_port=11015\n[SHARD]\nis_master=true\n')
    (shard/'worldgenoverride.lua').write_text('return {override_enabled=true,preset="SURVIVAL_TOGETHER",overrides={world_size="small",season_start="autumn",autumn="verylongseason",start_location="default"}}\n')
    kanami = ',["'+args.kanami_mod+'"]={enabled=true}' if args.mode=='combat' else ''
    (shard/'modoverrides.lua').write_text('return {["workshop-2526778484"]={enabled=true},["klbq_kanami_void_test"]={enabled=true,configuration_options={mode="'+args.mode+'"}}'+kanami+'}\n')
    log=ROOT/('docs/reports/void-'+args.mode+args.report_suffix+'.log')
    command=[str(GAME/'bin64/dontstarve_dedicated_server_nullrenderer_x64.exe'),'-persistent_storage_root',str(STORAGE),'-conf_dir','DoNotStarveTogether','-cluster',cluster.name,'-shard','Master','-offline','-bind_ip','127.0.0.1','-port','11015','-skip_update_server_mods','-ugc_directory','E:/steam/steamapps/workshop']
    with log.open('wb') as out:
        p=subprocess.Popen(command,cwd=GAME/'bin64',stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            p.wait(timeout=180)
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=10)
    result=log.read_text(encoding='utf-8',errors='replace')
    for line in result.splitlines():
        if '[VOID_' in line or 'LUA ERROR' in line: print(line)
    markers=[line for line in result.splitlines() if '[VOID_TEST]' in line]
    summary={'exit_code':p.returncode,'complete':'[VOID_TEST] COMPLETE' in result,
             'pass':sum('\tPASS\t' in line for line in markers),
             'fail':sum('\tFAIL\t' in line for line in markers),
             'lua_error':'LUA ERROR' in result,'log':str(log)}
    log.with_name(log.stem+'-result.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))
    if (not summary['complete'] or summary['fail'] or summary['lua_error'] or p.returncode!=0):
        raise SystemExit(1)

if __name__=='__main__': main()
