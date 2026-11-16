"""Infer sprite-local joint points from installed native animation transforms.

This is diagnostic metadata. It never rewrites character art or animations.
Joint endpoints are fitted together rather than inferred from sprite bounds.
"""
import itertools
import json
from pathlib import Path
import numpy as np
from calibrate_kanami_face import matrix
from inspect_dst_assets import read_anim, read_game_zip
from render_kanami_body_v2 import ROOT, visible

ART=ROOT/'art/klbq_kanami/body-v2'
OUTPUT=Path('D:/SOFTWARE/CodexData/temp/kanami_joint_contract')
BANKS={'player_idles':('idle_loop','idle_inaction','idle_inaction_sanity'),
       'player_basic':('run_pre','run_loop','run_pst'),
       'player_actions_eat':('eat_pre','eat','eat_lag','quick_eat_pre','quick_eat','quick_eat_lag'),
       'player_actions_axe':('chop_pre','chop_loop','chop_pst'),
       'player_actions_pickaxe':('pickaxe_pre','pickaxe_loop','pickaxe_pst'),
       'player_actions_shovel':('shovel_pre','shovel_loop','shovel_pst')}


def robust_fit(A,b,prior):
    weights=np.ones(len(b))
    for _ in range(8):
        w=np.sqrt(weights)
        solution=np.linalg.lstsq(np.vstack((A*w[:,None],np.eye(len(prior))*.2)),
            np.concatenate((b*w,prior*.2)),rcond=None)[0]
        error=np.linalg.norm((A@solution-b).reshape(-1,2),axis=1)
        weights=np.repeat(np.minimum(1.,2./np.maximum(error,1e-6)),2)
    return solution


def point(element,local):
    return (matrix(element)@np.array([*local,1.]))[:2]


def fixed_child_points(animations,parent,child,parent_initial,child_points):
    """Keep native child pivots fixed, avoiding the free two-endpoint gauge."""
    estimates={n:[] for n in parent_initial}
    for animation in animations:
        for carry in (False,True):
            for frame in animation['frames']:
                elements=[e for e in frame['elements'] if visible(e,carry,True)]
                parents=[e for e in elements if e['symbol']==parent and e['frame'] in parent_initial]
                children=[e for e in elements if e['symbol']==child and e['frame'] in child_points]
                parents=list({tuple(e[k] for k in ('frame','a','b','c','d','tx','ty')):e for e in parents}.values())
                if not parents or not children:continue
                count=min(len(parents),len(children))
                choices=[list(zip(p,c)) for p in itertools.permutations(range(len(parents)),count)
                         for c in itertools.permutations(range(len(children)),count)]
                pairs=min(choices,key=lambda pairs:sum(np.linalg.norm(point(parents[i],parent_initial[parents[i]['frame']])-
                    point(children[j],child_points[children[j]['frame']])) for i,j in pairs))
                for i,j in pairs:
                    p,c=parents[i],children[j]
                    local=np.linalg.inv(matrix(p))@np.r_[point(c,child_points[c['frame']]),1.]
                    estimates[p['frame']].append(local[:2])
    return {str(n):dict(point=np.median(values,axis=0).tolist() if values else parent_initial[n],samples=len(values))
            for n,values in estimates.items()}


def fit_chain(animations,parent,child,parent_initial,child_initial):
    keys=[(parent,n) for n in parent_initial]+[(child,n) for n in child_initial]
    indices={key:2*i for i,key in enumerate(keys)}
    initial={**{(parent,n):np.array(p,float) for n,p in parent_initial.items()},
             **{(child,n):np.array(p,float) for n,p in child_initial.items()}}
    solution=initial.copy()
    for iteration in range(4):
        equations=[]
        values=[]
        samples=[]
        for animation in animations:
            for carry in (False,True):
                for frame_number,frame in enumerate(animation['frames']):
                    elements=[e for e in frame['elements'] if visible(e,carry,True)]
                    parents=[e for e in elements if (e['symbol'],e['frame']) in solution and e['symbol']==parent]
                    children=[e for e in elements if (e['symbol'],e['frame']) in solution and e['symbol']==child]
                    # Repeated native elements can be on the same visible track.
                    parents=list({tuple((k,str(v)) for k,v in e.items()):e for e in parents}.values())
                    if not parents or not children:
                        continue
                    if len(parents)>=len(children):
                        pairings=[list(zip(choice,range(len(children)))) for choice in itertools.permutations(range(len(parents)),len(children))]
                    else:
                        pairings=[list(zip(range(len(parents)),choice)) for choice in itertools.permutations(range(len(children)),len(parents))]
                    def cost(pairs):
                        return sum(np.linalg.norm(point(parents[i],solution[parent,parents[i]['frame']])-point(children[j],solution[child,children[j]['frame']])) for i,j in pairs)
                    selected=min(pairings,key=cost)
                    for pi,ci in selected:
                        p,c=parents[pi],children[ci]
                        pm,cm=matrix(p),matrix(c)
                        equation=np.zeros((2,len(keys)*2))
                        ip,ic=indices[parent,p['frame']],indices[child,c['frame']]
                        equation[:,ip:ip+2]=pm[:2,:2]
                        equation[:,ic:ic+2]=-cm[:2,:2]
                        equations.extend(equation)
                        values.extend(cm[:2,2]-pm[:2,2])
                        samples.append((animation['name'],animation['facing'],frame_number,p['frame'],c['frame']))
        A=np.array(equations)
        b=np.array(values)
        prior=np.concatenate([initial[key] for key in keys])
        # A weak prior selects a local solution when a pose is undersampled.
        fitted=robust_fit(A,b,prior)
        solution={key:fitted[index:index+2] for key,index in indices.items()}
    errors=np.linalg.norm((A@fitted-b).reshape(-1,2),axis=1)
    details={}
    for key,p in solution.items():
        position=3 if key[0]==parent else 4
        selected=[i for i,s in enumerate(samples) if s[position]==key[1]]
        relevant=errors[selected]
        details[f'{key[0]}/{key[1]}']=dict(point=p.tolist(),samples=len(selected),
            median_error=float(np.median(relevant)) if len(relevant) else None,
            max_error=float(relevant.max()) if len(relevant) else None)
    return dict(points=details,samples=len(samples),median_error=float(np.median(errors)),
        max_error=float(errors.max()),worst=[dict(pose=list(samples[i]),error=float(errors[i])) for i in np.argsort(errors)[-12:][::-1]])


def fit_shoulders(animations):
    initial={**{('torso',n,side):np.array([20*side,-67 if n<3 else -74 if n<6 else -63],float)
                 for n in range(10) for side in (-1,1)},
             **{('arm_upper',n):np.zeros(2) for n in range(5)}}
    keys=list(initial)
    indices={key:2*i for i,key in enumerate(keys)}
    equations=[];values=[];samples=[]
    for animation in animations:
        for carry in (False,True):
            for frame_number,frame in enumerate(animation['frames']):
                elements=[e for e in frame['elements'] if visible(e,carry,True)]
                torsos=[e for e in elements if e['symbol']=='torso' and e['frame']<10]
                if len(torsos)!=1:continue
                torso=torsos[0];tm=matrix(torso)
                arms=[e for e in elements if e['symbol']=='arm_upper' and e['frame']<5]
                # Some rear clips repeat the carrying arm on two depth tracks.
                arms=list({tuple(e[k] for k in ('frame','a','b','c','d','tx','ty')):e for e in arms}.values())
                arms.sort(key=lambda e:(np.linalg.inv(tm)@matrix(e))[0,2])
                for i,arm in enumerate(arms):
                    local=np.linalg.inv(tm)@matrix(arm)
                    side=(-1 if i==0 else 1) if len(arms)==2 else (-1 if local[0,2]<0 else 1)
                    tk=('torso',torso['frame'],side);ak=('arm_upper',arm['frame'])
                    am=matrix(arm);equation=np.zeros((2,len(keys)*2))
                    equation[:,indices[tk]:indices[tk]+2]=tm[:2,:2]
                    equation[:,indices[ak]:indices[ak]+2]=-am[:2,:2]
                    equations.extend(equation);values.extend(am[:2,2]-tm[:2,2])
                    samples.append((animation['name'],animation['facing'],frame_number,tk,ak))
    A=np.array(equations);b=np.array(values);prior=np.concatenate(list(initial.values()))
    fitted=robust_fit(A,b,prior);errors=np.linalg.norm((A@fitted-b).reshape(-1,2),axis=1)
    details={}
    for key,index in indices.items():
        relevant=errors[[i for i,s in enumerate(samples) if key in s[3:]]]
        details['/'.join(map(str,key))]=dict(point=fitted[index:index+2].tolist(),samples=len(relevant),
            median_error=float(np.median(relevant)) if len(relevant) else None,
            max_error=float(relevant.max()) if len(relevant) else None)
    return dict(points=details,samples=len(samples),median_error=float(np.median(errors)),max_error=float(errors.max()))


def main():
    animations=[a for bank,names in BANKS.items() for a in read_anim(read_game_zip(bank,'anim.bin')) if a['name'] in names]
    legs={0:[0,30],1:[0,30],2:[0,30],3:[0,30],4:[-22,20],5:[0,30],6:[-6,24],7:[0,10],8:[-5,30]}
    feet={n:[0,0] for n in range(7)}
    upper={0:[0,30],1:[0,32],2:[0,30],3:[0,30],4:[0,14]}
    lower={0:[0,0],1:[0,0],2:[0,0],5:[0,0]}
    wrists={0:[0,30],1:[0,40],2:[-36,12],5:[0,30]}
    hands={n:[0,0] for n in range(20) if n!=15}
    results={'shoulder':fit_shoulders(animations),
             'ankle':fit_chain(animations,'leg','foot',legs,feet),
             'elbow':fit_chain(animations,'arm_upper','arm_lower',upper,lower),
             'wrist':fit_chain(animations,'arm_lower','hand',wrists,hands)}
    results['fixed_native_pivots']={
        'ankle':fixed_child_points(animations,'leg','foot',legs,feet),
        'elbow':fixed_child_points(animations,'arm_upper','arm_lower',upper,lower),
        'wrist':fixed_child_points(animations,'arm_lower','hand',wrists,hands)}
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT/'derived.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    for joint,data in results.items():
        if joint=='fixed_native_pivots':
            print(joint,json.dumps(data));continue
        print(joint,data['samples'],data['median_error'],data['max_error'])
        for name,entry in data['points'].items():
            print(name,np.round(entry['point'],3).tolist(),entry['samples'],entry['median_error'])


if __name__=='__main__':
    main()
