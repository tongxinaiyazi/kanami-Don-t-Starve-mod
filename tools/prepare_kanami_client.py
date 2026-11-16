"""Configure only the task-owned QA profile, or submit a command to that client."""
from pathlib import Path
import argparse,base64,json,re,shutil,struct,zlib
ROOT=Path(__file__).resolve().parents[1]
GAME=Path("E:/steam/steamapps/common/Don't Starve Together")
STORAGE=Path('D:/SOFTWARE/CodexData/temp/kanami_client/storage/KanamiClientTest')
ACTIVE=STORAGE.parent.parent/'active-profile.json'

def select_profile(profile_id=None):
    if profile_id is None and ACTIVE.exists():
        profile_id=json.loads(ACTIVE.read_text())['profile_id']
    if profile_id is not None:
        if not str(profile_id).isdigit():raise ValueError('QA profile id must be numeric')
        folder=STORAGE/str(profile_id)/'client_save'
        if not folder.is_dir():raise ValueError('QA profile does not exist: '+str(folder))
        return folder
    folders=list(STORAGE.glob('*/client_save'))
    if len(folders)!=1:raise ValueError('Multiple QA profiles; specify --profile-id explicitly')
    return folders[0]
def read_klei(path):
    b=path.read_bytes();assert b.startswith(b'KLEI     1D')
    d=base64.b64decode(b[11:]);assert struct.unpack('<II',d[:8])==(1,16)
    return zlib.decompress(d[16:]).decode('utf-8')
def write_klei(path,text):
    data=text.encode('utf-8');compressed=zlib.compress(data,9)
    path.write_bytes(b'KLEI     1D'+base64.b64encode(struct.pack('<IIII',1,16,len(data),len(compressed))+compressed))
def main():
    p=argparse.ArgumentParser();p.add_argument('--command-file',type=Path);p.add_argument('--profile-id');args=p.parse_args()
    folder=select_profile(args.profile_id)
    if args.profile_id:ACTIVE.write_text(json.dumps({'profile_id':args.profile_id}),encoding='utf8')
    if args.command_file:
        write_klei(folder/'kanami_qa_command',args.command_file.read_text(encoding='utf-8'))
        print('Submitted command to isolated Kanami client');return
    dst=GAME/'mods/klbq_kanami_client_qa'
    if dst.exists() and not (dst/'.kanami-task-owned').is_file():raise RuntimeError('Unowned destination')
    shutil.copytree(ROOT/'tests/client_mod',dst,dirs_exist_ok=True)
    (dst/'.kanami-task-owned').write_text('Kanami graphical QA, 2026-10-29',encoding='utf-8')
    path=folder/'modindex';text=read_klei(path)
    backup=path.with_name('modindex-before-visual-025')
    if not backup.exists():backup.write_bytes(path.read_bytes())
    # A previous failed QA launch can leave temporary server mods disabled.
    # Reset only the three known test entries when explicitly preparing a new
    # run. Leave the game's general crash-disable mechanism and other mods alone.
    for key in ('klbq_kanami_verify=', 'klbq_kanami_resource_test=', '["workshop-3173431824"]='):
        start=text.find(key)
        if start<0:continue
        end=text.find('seen_api_version=10}',start)
        if end<0:raise ValueError('Unexpected QA mod-index entry: '+key)
        end+=len('seen_api_version=10}')
        entry=text[start:end].replace('temp_disabled=true','temp_disabled=false').replace('disabled_bad=true','disabled_bad=false')
        text=text[:start]+entry+text[end:]
    name='klbq_kanami_client_qa'
    text=re.sub(r'\b'+name+r'=\{[^}]*\},?', '',text)
    text=text.replace('known_mods={','known_mods={'+name+'={enabled=true,seen_api_version=10},',1)
    write_klei(path,text);(folder/'boot_modindex').write_bytes(b'KLEI     1 done')
    (folder/'kanami_qa_command').write_bytes(b'KLEI     1 ')
    print(json.dumps({'profile':str(folder),'enabled':name,'T_mods_preserved':True}))
if __name__=='__main__':main()
