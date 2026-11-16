"""Promote a verified body-v2 candidate into SOURCE only, retaining a backup.

This does not install into the game, refresh the upload folder, or publish.
"""
import argparse,datetime,hashlib,json,shutil
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
from build_kanami_body_v2 import ROOT,ART,STAGE,make_actions,registered_build
import build_kanami_assets as legacy

NAMES=('klbq_kanami','klbq_kanami_actions')

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source_hashes(art):
    registration=json.loads((art/'registration.json').read_text(encoding='utf8'))
    files={'registration.json','native-contract.json'}|{e['image'] for e in registration['frames'].values()}
    result={}
    for name in files:
        p=(art/name).resolve()
        if not p.is_relative_to(art.resolve()):raise ValueError('source escapes art folder')
        result[name]=digest(p)
    # Animation binding logic is an input just as much as the PNG registration.
    # A rebuilt picture must not promote actions from an earlier rig exporter.
    for name in ('build_kanami_body_v2.py','retarget_kanami_body.py','render_kanami_body_v2.py','calibrate_kanami_face.py'):
        result['@tool/'+name]=digest(ROOT/'tools'/name)
    return result

def record_candidate(stage,art):
    files={}
    for name in NAMES:
        targets=[stage/'compiled/anim'/f'{name}.zip',*list((stage/'exported'/name).glob('*'))]
        for p in targets:
            if p.is_file() and p.suffix in ('.zip','.xml','.png'):files[p.relative_to(stage).as_posix()]=digest(p)
    if not all(f'compiled/anim/{name}.zip' in files for name in NAMES):return
    (stage/'body-v2-candidate.json').write_text(json.dumps({'format':1,'art':str(art.resolve()),'sources':source_hashes(art),'candidate_files':files},indent=2),encoding='utf8')

def promote(stage=STAGE,art=ART):
    stage=stage.resolve();art=art.resolve()
    manifest=json.loads((stage/'body-v2-candidate.json').read_text(encoding='utf8'))
    if manifest['art']!=str(art) or manifest['sources']!=source_hashes(art):raise ValueError('stale candidate: rebuild after source changes')
    for name,expected in manifest['candidate_files'].items():
        p=(stage/name).resolve()
        if not p.is_relative_to(stage) or digest(p)!=expected:raise ValueError('candidate hash mismatch: '+name)
    registration=json.loads((art/'registration.json').read_text(encoding='utf8'))
    contract=json.loads((art/'native-contract.json').read_text(encoding='utf8'))
    build,images=registered_build(art,registration,contract)
    rootart=ROOT/'art/klbq_kanami';mod=ROOT/'mods/klbq_kanami'
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    backup=rootart/'history'/('before-body-v2-'+stamp);backup.mkdir(parents=True)
    targets=[(mod/'anim'/f'{n}.zip',Path('anim')/f'{n}.zip') for n in NAMES]
    targets += [(rootart/'exported'/n,Path('exported')/n) for n in NAMES]
    targets += [(rootart/'spriter',Path('spriter')),(rootart/'body-pipeline.json',Path('body-pipeline.json'))]
    for source,relative in targets:
        if source.exists():
            destination=backup/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            if source.is_dir():shutil.copytree(source,destination)
            else:shutil.copy2(source,destination)
    # Verify exact owned source targets before replacing recursive directories.
    for name in NAMES:
        target=rootart/'exported'/name
        if target.resolve()!=rootart.resolve()/'exported'/name or target.is_symlink():raise ValueError('linked source export')
        if target.exists():shutil.rmtree(target)
        shutil.copytree(stage/'exported'/name,target,ignore=shutil.ignore_patterns('*.log'))
        shutil.copy2(stage/'compiled/anim'/f'{name}.zip',mod/'anim'/f'{name}.zip')
    # XML retains native matrices; SCML is an editable approximation for shear.
    legacy.make_spriter(build,images,make_actions())
    state={'format':1,'active':'body-v2','source':'body-v2/registration.json','backup':str(backup),
           'runtime_sha256':{n:digest(mod/'anim'/f'{n}.zip') for n in NAMES}}
    (rootart/'body-pipeline.json').write_text(json.dumps(state,indent=2),encoding='utf8')
    print('Promoted body-v2 into project source only. Backup:',backup)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',type=Path,default=STAGE)
    parser.add_argument('--art',type=Path,default=ART);args=parser.parse_args();promote(args.stage,args.art)
