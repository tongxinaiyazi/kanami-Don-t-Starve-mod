"""Check actual joint regions, excluding hair and unrelated covering sprites.

This deliberately does not use whole-silhouette distance or a native-gap
allowance. A foot touching the wrong part of a calf cannot satisfy an ankle.
"""
import argparse
import itertools
import json
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from build_kanami_body_v2 import make_actions
from calibrate_kanami_face import matrix
from render_kanami_body_v2 import ROOT, load_registration, load_exported, render_frame, visible
from inspect_dst_assets import read_anim
from retarget_kanami_body import local_anchor,anchor,shoulder_anchor,waist_anchor

ART=ROOT/'art/klbq_kanami/body-v2'
OUTPUT=Path('D:/SOFTWARE/CodexData/temp/kanami_joint_poses')


def joint_pairs(elements,layout):
    def select(symbol):
        selected=[e for e in elements if e['symbol']==symbol and not(symbol=='hand' and e['frame']==15)]
        return list({tuple(e[k] for k in ('frame','a','b','c','d','tx','ty')):e for e in selected}.values())
    for parent,child,joint in [('torso','headbase','neck'),('torso','arm_upper','shoulder'),('arm_upper','arm_lower','elbow'),
                              ('arm_lower','hand','wrist'),('torso_pelvis','leg','hip'),
                              ('leg','foot','ankle'),('torso','torso_pelvis','waist')]:
        parents,children=select(parent),select(child)
        if not parents or not children:continue
        if joint in ('neck','shoulder','hip','waist'):
            p=parents[0]
            for c in children:
                if joint=='neck':
                    pe=layout[f"{p['symbol']}/{p['frame']}"]
                    ce=layout[f"{c['symbol']}/{c['frame']}"]
                    if 'neck_anchor' not in pe or 'neck_anchor' not in ce:continue
                    pp=(matrix(p)@np.r_[pe['neck_anchor'],1.])[:2]
                    cp=(matrix(c)@np.r_[ce['neck_anchor'],1.])[:2]
                elif joint=='shoulder':
                    cp=anchor(c,layout,0)
                    pp=min((shoulder_anchor(p,layout,n) for n in (0,1)),key=lambda a:np.linalg.norm(a-cp))
                elif joint=='hip':
                    # The actual thigh-root landmark is also the test window.
                    # Only pelvis and this leg contribute opaque pixels.
                    cp=anchor(c,layout,0);pp=cp
                else:
                    pp=waist_anchor(p,layout)
                    cp=waist_anchor(c,layout)
                yield joint,p,c,pp,cp
            continue
        count=min(len(parents),len(children))
        choices=[list(zip(p,c)) for p in itertools.permutations(range(len(parents)),count)
                 for c in itertools.permutations(range(len(children)),count)]
        pairs=min(choices,key=lambda pairs:sum(np.linalg.norm(anchor(parents[i],layout,1)-anchor(children[j],layout,0)) for i,j in pairs))
        for i,j in pairs:
            p,c=parents[i],children[j]
            yield joint,p,c,anchor(p,layout,1),anchor(c,layout,0)


def region_mask(element,frames,centre,radius=10,scale=2):
    entry=frames[element['symbol'],element['frame']]
    im=entry['image'];size=round(radius*4)
    local=np.array([[1,0,entry['x']-im.width/2],[0,1,entry['y']-im.height/2],[0,0,1.]])
    screen=np.array([[scale,0,size/2-centre[0]*scale],[0,scale,size/2-centre[1]*scale],[0,0,1.]])
    transform=screen@matrix(element)@local
    if abs(np.linalg.det(transform))<1e-10:return np.zeros((size,size),bool)
    inverse=np.linalg.inv(transform)
    alpha=im.getchannel('A').transform((size,size),Image.Transform.AFFINE,tuple(inverse[:2].flat),Image.Resampling.BILINEAR)
    yy,xx=np.indices((size,size))
    return (np.asarray(alpha)>100)&((xx-size/2)**2+(yy-size/2)**2<=(radius*scale)**2)


def check_pair(p,c,pp,cp,frames,joint,layout=None):
    if joint in ('neck','shoulder','elbow','wrist','ankle','waist') and np.linalg.norm(pp-cp)>.1:
        return f'joint landmark drift {np.linalg.norm(pp-cp):.2f}',0.
    centre=(pp+cp)/2
    radius=12 if joint in ('waist','shoulder','hip') else 9
    a=region_mask(p,frames,centre,radius)
    b=region_mask(c,frames,centre,radius)
    overlap=int((a&b).sum())/4
    if overlap>= (12 if joint=='waist' else 1.5):
        if joint=='waist' and layout is not None:
            entry=layout[f"{p['symbol']}/{p['frame']}"]
            edges=entry.get('waist_edges')
            if edges:
                for fraction in np.linspace(0,1,9):
                    point=np.asarray(edges[0])*(1-fraction)+np.asarray(edges[1])*fraction
                    centre=(matrix(p)@np.r_[point,1.])[:2]
                    first=region_mask(p,frames,centre,2)
                    second=region_mask(c,frames,centre,2)
                    if int((first&second).sum())<4:return 'waist seam is open',overlap
        return None,overlap
    ya,xa=np.where(a);yb,xb=np.where(b)
    if not len(xa) or not len(xb):return 'missing joint surface',overlap
    distance=np.sqrt(min(((xa[i:i+32,None]-xb)**2+(ya[i:i+32,None]-yb)**2).min() for i in range(0,len(xa),32)))/2
    if distance>1 or joint=='waist':return f'gap {distance:.2f}',overlap
    return None,overlap


def audit(frames,layout,animations,all_actions=False):
    checked=0;issues=[];counts={};examples={}
    wanted=('idle_loop','idle_inaction','run_pre','run_loop','run_pst','eat','quick_eat',
            'chop_loop','pickaxe_loop','shovel_loop','feast_eat_loop')
    for animation in animations:
        name=animation['name'].removeprefix('kanami_')
        if name.startswith('string_'):continue
        if not all_actions and name not in wanted:continue
        modes=((False,True) if name in ('idle_loop','idle_inaction','idle_inaction_sanity','dial_loop','run_pre','run_loop','run_pst','careful_walk_pre','careful_walk','careful_walk_pst','idle_walk_pre','idle_walk','idle_walk_pst')
               else (name in ('shoot','crossbow_shoot','cast','atk_pre','atk','atk_lag','atk_recoil','toolpunch','spearjab_pre','spearjab','spearjab_lag'),))
        for carry in modes:
            for index,frame in enumerate(animation['frames']):
                elements=[e for e in frame['elements'] if visible(e,carry,True) and
                          (e['symbol'],e['frame']) in frames]
                for joint,p,c,pp,cp in joint_pairs(elements,layout):
                    error,overlap=check_pair(p,c,pp,cp,frames,joint,layout)
                    checked+=1;counts[joint]=counts.get(joint,0)+1
                    if error:
                        issue=dict(action=name,facing=animation['facing'],frame=index,carry=carry,
                            joint=joint,parent=p['frame'],child=c['frame'],reason=error,
                            landmark_distance=float(np.linalg.norm(pp-cp)),overlap=overlap)
                        issues.append(issue)
                        examples.setdefault((name,animation['facing'],carry,joint),(frame,issue))
    return dict(checked=checked,counts=counts,issues=issues),examples


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--exported',type=Path)
    parser.add_argument('--action-zip',type=Path)
    parser.add_argument('--all-actions',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    layout=json.loads((ART/'registration.json').read_text(encoding='utf8'))['frames']
    frames=load_exported(args.exported) if args.exported else load_registration(ART)
    if args.action_zip:
        with zipfile.ZipFile(args.action_zip) as archive:animations=read_anim(archive.read('anim.bin'))
    else:animations=make_actions()
    report,examples=audit(frames,layout,animations,all_actions=args.all_actions)
    report['source']=str(args.exported or ART)
    report['actions']=str(args.action_zip) if args.action_zip else 'fresh joint export'
    (args.output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    selected=list(examples.values())[:30]
    if selected:
        sheet=Image.new('RGB',(6*320,((len(selected)+5)//6)*440),(38,33,46));draw=ImageDraw.Draw(sheet)
        for n,(frame,issue) in enumerate(selected):
            x=n%6*320;y=n//6*440
            image=render_frame(frame,frames,issue['carry'],True,size=(320,420),scale=2)
            sheet.paste(image,(x,y+20))
            draw.text((x+3,y+3),f"{issue['action']} {issue['facing']}/{issue['frame']} {issue['joint']}",fill='white')
        sheet.save(args.output/'issues.png')
    print(json.dumps(dict(checked=report['checked'],counts=report['counts'],issues=len(report['issues']),
        examples=[issue for _,issue in selected[:8]]),indent=2))


if __name__=='__main__':main()
