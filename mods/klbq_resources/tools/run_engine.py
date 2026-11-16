"""Run the actual DST server in a task-owned miniature host and offline save.

Original binaries/data are read/copied for local tests only. Installed mods and
normal user storage are never changed. This host is not a redistributable game.
"""
from __future__ import annotations
import argparse, json, os, re, shutil, socket, subprocess, time, uuid
from pathlib import Path

MOD=Path(__file__).resolve().parents[1]
GAME=Path("E:/steam/steamapps/common/Don't Starve Together")
STAGE=Path("D:/SOFTWARE/CodexData/temp/klbq_resources_engine")
REPORT=MOD/"docs/reports"
RUNTIME_FILES=["modinfo.lua","modmain.lua","modicon.xml","modicon.tex"]
PORT_ERROR=re.compile(r"invalid port selection|fall(?:ing)?\s*back[^\r\n]*port", re.IGNORECASE)
ACTUAL_PORT=re.compile(r"(?<!\S)(?:ServerPort:|Lan Server Started on port:)\s*(\d+)", re.IGNORECASE)

def choose_lan_port():
    """Probe the LAN-only range, keeping the normal default port untouched."""
    for port in range(11018,10997,-1):
        if port == 10999:
            continue
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
            try:
                probe.bind(("127.0.0.1",port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available LAN UDP port in 10998..11018 (10999 reserved)")

def runtime_copy(destination):
    destination.mkdir(parents=True,exist_ok=True)
    for name in RUNTIME_FILES: shutil.copy2(MOD/name,destination/name)
    for folder in ["scripts","images","anim"]:
        shutil.copytree(MOD/folder,destination/folder,dirs_exist_ok=True)

def prepare(phase,server_port):
    if STAGE.exists() and not (STAGE/".klbq-resources-owned").is_file():
        raise RuntimeError("Refusing an unowned test directory")
    STAGE.mkdir(parents=True,exist_ok=True)
    (STAGE/".klbq-resources-owned").write_text("isolated klbq_resources engine test\n")
    host=STAGE/"game"
    binary=host/"bin64"
    binary.mkdir(parents=True,exist_ok=True)
    for source in (GAME/"bin64").iterdir():
        if source.suffix.lower()==".dll" or source.name=="dontstarve_dedicated_server_nullrenderer_x64.exe":
            shutil.copy2(source,binary/source.name)
    # Junction target is checked before creation and never modified.
    data=host/"data"
    if not data.exists():
        quote=lambda path: "'"+str(path).replace("'", "''")+"'"
        command="New-Item -ItemType Junction -Path "+quote(data)+" -Target "+quote(GAME/"data")+" | Out-Null"
        subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    if data.resolve()!=(GAME/"data").resolve():
        raise RuntimeError("Unexpected test data junction target")
    mods=host/"mods"
    runtime_copy(mods/"klbq_resources")
    shutil.copytree(MOD/"tests/engine_mod",mods/"klbq_resources_test",dirs_exist_ok=True)
    (mods/"modsettings.lua").write_text("-- isolated resource test only\n",encoding="utf-8")
    last_cluster=STAGE/"last-cluster.json"
    if phase == "reload":
        name=json.loads(last_cluster.read_text(encoding="utf-8"))["cluster"]
        if not re.fullmatch(r"ResourcesSmoke-[0-9a-f]{12}",name):
            raise RuntimeError("Invalid task-owned cluster name")
    else:
        name="ResourcesSmoke-"+uuid.uuid4().hex[:12]
        last_cluster.write_text(json.dumps({"cluster":name}),encoding="utf-8")
    cluster=STAGE/"storage/DoNotStarveTogether"/name
    shard=cluster/"Master"
    shard.mkdir(parents=True,exist_ok=True)
    (cluster/"cluster.ini").write_text("[GAMEPLAY]\ngame_mode=endless\nmax_players=2\npvp=false\npause_when_empty=false\n\n[NETWORK]\ncluster_name=Resource isolated regression\noffline_cluster=true\nlan_only_cluster=true\n\n[MISC]\nconsole_enabled=true\n\n[SHARD]\nshard_enabled=false\n",encoding="utf-8")
    (shard/"server.ini").write_text("[NETWORK]\nserver_port="+str(server_port)+"\n\n[STEAM]\nauthentication_port=8791\nmaster_server_port=27041\n\n[SHARD]\nis_master=true\n",encoding="utf-8")
    (shard/"worldgenoverride.lua").write_text('return {override_enabled=true,preset="SURVIVAL_TOGETHER",overrides={world_size="small",season_start="autumn",start_location="default"}}\n',encoding="utf-8")
    return binary,shard

def phase_run(binary,shard,phase,timeout,server_port):
    (shard/"modoverrides.lua").write_text('return {["klbq_resources"]={enabled=true},["klbq_resources_test"]={enabled=true,configuration_options={phase="'+phase+'"}}}\n',encoding="utf-8")
    REPORT.mkdir(parents=True,exist_ok=True)
    log=REPORT/("engine-"+phase+".log")
    command=[str(binary/"dontstarve_dedicated_server_nullrenderer_x64.exe"),
             "-persistent_storage_root",str(STAGE/"storage"),"-conf_dir","DoNotStarveTogether",
             "-cluster",shard.parent.name,"-shard","Master","-offline","-bind_ip","127.0.0.1",
             "-port",str(server_port),"-skip_update_server_mods"]
    env=os.environ.copy();env["SteamAppId"]="322330"
    with log.open("wb") as out:
        process=subprocess.Popen(command,cwd=binary,env=env,stdin=subprocess.PIPE,stdout=out,
                                 stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        start=time.monotonic();last_update=0
        try:
            while process.poll() is None and time.monotonic()-start<timeout:
                time.sleep(1)
                text=log.read_text(encoding="utf-8",errors="replace")
                elapsed=int(time.monotonic()-start)
                if elapsed-last_update>=15:
                    markers=[line for line in text.splitlines() if "[RESOURCES_TEST]" in line]
                    print(phase,elapsed,"s",markers[-1] if markers else "world startup",flush=True)
                    last_update=elapsed
                if "LUA ERROR" in text or "Error loading prefab" in text or PORT_ERROR.search(text):
                    break
            if process.poll() is None:
                try:
                    process.stdin.write(b"c_shutdown(false)\n");process.stdin.flush()
                    process.wait(timeout=10)
                except (OSError,subprocess.TimeoutExpired):
                    process.terminate();process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=10)
    text=log.read_text(encoding="utf-8",errors="replace")
    markers=[line for line in text.splitlines() if "[RESOURCES_TEST]" in line]
    print("\n".join(markers),flush=True)
    actual_ports=[int(port) for port in ACTUAL_PORT.findall(text)]
    result={"phase":phase,"server_port":server_port,"actual_server_ports":actual_ports,
            "port_error":bool(PORT_ERROR.search(text)) or any(port!=server_port for port in actual_ports),
            "exit_code":process.returncode,"pass":sum("PASS" in line for line in markers),
            "fail":sum("FAIL" in line for line in markers),"complete":any("COMPLETE" in line for line in markers),
            "lua_error":"LUA ERROR" in text,"log":str(log)}
    (REPORT/("engine-"+phase+"-result.json")).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    if result["exit_code"]!=0 or result["lua_error"] or result["port_error"] or result["fail"] or not result["complete"]:
        raise RuntimeError("Engine "+phase+" failed: "+json.dumps(result))
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["both","create","reload"],default="both")
    parser.add_argument("--seconds",type=int,default=120)
    args=parser.parse_args()
    server_port=choose_lan_port()
    binary,shard=prepare(args.phase,server_port)
    phases=["create","reload"] if args.phase=="both" else [args.phase]
    results=[phase_run(binary,shard,p,args.seconds,server_port) for p in phases]
    print(json.dumps(results),flush=True)

if __name__=="__main__":main()
