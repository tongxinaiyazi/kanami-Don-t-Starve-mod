"""Fit each expression's local eye anchor to the skull across native poses.

No animation matrices are rewritten. Each distinct face frame gets its own
registration, including frames whose native origin differs from neutral.
"""
import re
import zipfile
import numpy as np
from inspect_dst_assets import read_anim,read_game_zip,GAME

BANKS=('player_idles','player_basic','player_actions_eat','player_actions_axe','player_actions_pickaxe','player_actions_shovel')

def player_banks():
    """Use assets loaded for ordinary players, not every player-prefixed NPC rig."""
    with zipfile.ZipFile(GAME/'data/databundles/scripts.zip') as archive:
        source=archive.read('scripts/prefabs/player_common.lua').decode('utf8')
    source=re.sub(r'--\[\[.*?\]\]', '', source, flags=re.S)
    source=re.sub(r'--[^\n]*', '', source)
    names=set(re.findall(r'Asset\(\s*"ANIM"\s*,\s*"anim/(player[^"/]+)\.zip"', source))
    return sorted(names | set(BANKS))

def matrix(e):
    return np.array([[e['a'],e['c'],e['tx']],[e['b'],e['d'],e['ty']],[0,0,1.]],float)


def neutral_face_bases(idles=None):
    if idles is None:
        idles=read_anim(read_game_zip('player_idles','anim.bin'))
    result={}
    for facing,view in ((8,0),(5,1)):
        frame=next(a for a in idles if a['name']=='idle_loop' and a['facing']==facing)['frames'][0]
        head=next(e for e in frame['elements'] if e['symbol']=='headbase')
        face=next(e for e in frame['elements'] if e['symbol']=='face')
        result[view]=np.linalg.inv(matrix(head)[:2,:2])@matrix(face)[:2,:2]
    return result


def calibrate(front=(-8,-30),profile=(29,-41.5)):
    groups={}
    extra=[bank for bank in player_banks() if bank not in BANKS]
    core_frames=set()
    for bank in (*BANKS,*extra):
        if extra and bank==extra[0]:core_frames=set(groups)
        for a in read_anim(read_game_zip(bank,'anim.bin')):
            for i,f in enumerate(a['frames']):
                heads=[e for e in f['elements'] if e['symbol']=='headbase' and e['frame'] in (0,1,4)]
                faces=[e for e in f['elements'] if e['symbol']=='face']
                if not heads or not faces:continue
                h,face=heads[0],faces[0]
                if face['frame']>32 or (bank not in BANKS and face['frame'] in core_frames):continue
                relative=np.linalg.inv(matrix(h))@matrix(face)
                target=np.array(profile if h['frame']==1 else front,float)
                groups.setdefault(face['frame'],[]).append((relative,target,bank,a['name'],i))
    result={}
    for n,rows in groups.items():
        A=np.concatenate([r[0][:2,:2] for r in rows])
        b=np.concatenate([r[1]-r[0][:2,2] for r in rows])
        p=np.linalg.lstsq(A,b,rcond=None)[0]
        errors=[float(np.linalg.norm(r[0][:2,:2]@p+r[0][:2,2]-r[1])) for r in rows]
        result[n]=dict(local_eye_anchor=p.tolist(),samples=len(rows),median_residual=float(np.median(errors)),max_residual=max(errors),worst_pose=list(rows[int(np.argmax(errors))][2:]))
    return result
