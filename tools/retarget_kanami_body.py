"""Bind replacement paper cutouts through anatomical joints before export.

Native angular motion, pose identity and depth are retained. Limb dimensions
have physical limits instead of inheriting coat-sleeve stretch. The pelvis is
the root of a connected waist-neck and shoulder-elbow-wrist chain. This is
offline rig export, with no Lua polling or per-frame Lua limb correction.
"""
import copy
import itertools
import numpy as np

from calibrate_kanami_face import matrix
from render_kanami_body_v2 import visible


def local_anchor(entry,which):
    if 'anchors' in entry:
        values=list(entry['anchors'].values())
        point=np.array(values[which]['target_canvas'],float)
        return point+np.array(entry['centre'])-np.array(entry['canvas'])/2
    if 'local_anchors' in entry:
        index=-1 if which==1 and entry['image'].startswith('sprites/leg_') else which
        return np.array(entry['local_anchors'][index],float)
    return np.array(entry['native_wrist_local'],float)


def anchor(element,layout,which):
    entry=layout[f"{element['symbol']}/{element['frame']}"]
    return (matrix(element)@np.r_[local_anchor(entry,which),1.])[:2]


def shoulder_anchor(element,layout,which):
    entry=layout[f"{element['symbol']}/{element['frame']}"]
    if 'shoulder_anchors' not in entry:return anchor(element,layout,which)
    return (matrix(element)@np.r_[entry['shoulder_anchors'][which],1.])[:2]


def waist_anchor(element,layout):
    entry=layout[f"{element['symbol']}/{element['frame']}"]
    if 'waist_edges' in entry:
        point=np.asarray(entry['waist_edges'],float).mean(axis=0)
    elif 'waist_anchor' in entry:
        point=np.asarray(entry['waist_anchor'])
    elif element['symbol']=='torso_pelvis':
        point=(local_anchor(entry,0)+local_anchor(entry,1))/2
    else:
        point=local_anchor(entry,2)
    return (matrix(element)@np.r_[point,1.])[:2]


def bind_waist_seam(torso,pelvis,layout):
    """Match both painted waist edges while retaining native skirt depth."""
    shirt=layout[f"torso/{torso['frame']}"]
    skirt=layout[f"torso_pelvis/{pelvis['frame']}"]
    if 'waist_edges' not in shirt:
        return
    target=np.asarray([(matrix(torso)@np.r_[p,1.])[:2] for p in shirt['waist_edges']])
    source=np.asarray(skirt.get('waist_edges',[local_anchor(skirt,0),local_anchor(skirt,1)]))
    local_vector=source[1]-source[0]
    world_vector=target[1]-target[0]
    local_length=np.linalg.norm(local_vector)
    world_length=np.linalg.norm(world_vector)
    along=local_vector/local_length
    across=np.array([-along[1],along[0]])
    direction=world_vector/world_length
    old_linear=matrix(pelvis)[:2,:2]
    normal=np.array([-direction[1],direction[0]])*np.sign(np.linalg.det(old_linear))
    depth=abs(np.linalg.det(old_linear))/np.linalg.norm(old_linear@along)
    linear=np.outer(direction,along)*(world_length/local_length)+np.outer(normal,across)*depth
    pelvis['a'],pelvis['c']=map(float,linear[0])
    pelvis['b'],pelvis['d']=map(float,linear[1])
    pelvis['tx'],pelvis['ty']=map(float,target[0]-linear@source[0])


def normalize_limb(element,entry):
    """Preserve bone direction and mirroring while bounding length and width."""
    symbol=element['symbol']
    transform=matrix(element)[:2,:2]
    if abs(np.linalg.det(transform))<1e-9:return
    if symbol=='hand':
        u,_,vt=np.linalg.svd(transform)
        box=entry.get('visible_bbox')
        span=max(box[2]-box[0],box[3]-box[1]) if box else 22
        size=.82*min(1.,22/max(1,span))
        fixed=(u@vt)*size
    else:
        start=local_anchor(entry,0)
        end=np.asarray(entry['local_anchors'][1]) if symbol=='foot' else local_anchor(entry,1)
        vector=end-start
        length=np.linalg.norm(vector)
        if length<1e-6:return
        along=vector/length
        across=np.array([-along[1],along[0]])
        world_axis=transform@along
        projection=np.linalg.norm(world_axis)
        direction=world_axis/projection
        normal=np.array([-direction[1],direction[0]])*np.sign(np.linalg.det(transform))
        if symbol=='arm_upper':
            desired=11 if element['frame']==4 else 26
            parallel=desired/length
            transverse=.9
        elif symbol=='arm_lower':
            parallel=21/length
            transverse=.9
        elif symbol=='leg':
            points=np.asarray(entry['local_anchors'])
            shape=np.outer(along,along)+np.outer(across,across)*1.15
            shaped_points=points@shape.T
            path=sum(np.linalg.norm(b-a) for a,b in zip(shaped_points,shaped_points[1:]))
            parallel=38/path
            transverse=parallel*1.15
        else:
            parallel=transverse=14/length
        fixed=np.outer(direction,along)*parallel+np.outer(normal,across)*transverse
    element['a'],element['c']=map(float,fixed[0])
    element['b'],element['d']=map(float,fixed[1])


def normalize_torso(element,entry):
    """Use a shorter spine and broader chest around the garment's own axes."""
    if 'neck_anchor' not in entry:
        return
    waist=np.asarray(entry['waist_edges']).mean(axis=0)
    spine=np.asarray(entry['neck_anchor'])-waist
    along=spine/np.linalg.norm(spine)
    across=np.array([-along[1],along[0]])
    proportions=np.outer(along,along)*.94+np.outer(across,across)*1.15
    linear=matrix(element)[:2,:2]@proportions
    element['a'],element['c']=map(float,linear[0])
    element['b'],element['d']=map(float,linear[1])


def support_height(element,outline):
    points=np.column_stack((np.asarray(outline,float),np.ones(len(outline))))
    return float((matrix(element)@points.T)[1].max())


def attach_body_joints(frame,layout,weapon_carry=True):
    elements=frame['elements'];original=copy.deepcopy(elements)
    aliases={};signatures=[]
    for index,e in enumerate(original):
        signature=tuple(e[k] for k in ('symbol','frame','a','b','c','d','tx','ty'))
        signatures.append(signature);aliases.setdefault(signature,[]).append(index)

    def select(symbol,carry):
        indices=[i for i,e in enumerate(original) if e['symbol']==symbol and
                 visible(e,carry,True) and f"{symbol}/{e['frame']}" in layout and
                 not (symbol=='hand' and e['frame']==15)]
        return list({signatures[i]:i for i in indices}.values())

    def translate(index,target,which):
        e=elements[index]
        delta=target-anchor(e,layout,which)
        tx,ty=float(e['tx']+delta[0]),float(e['ty']+delta[1])
        for alias in aliases[signatures[index]]:
            elements[alias]['tx']=tx
            elements[alias]['ty']=ty

    for index,element in enumerate(elements):
        key=f"{element['symbol']}/{element['frame']}"
        if key in layout and element['symbol']=='torso':
            normalize_torso(element,layout[key])
        if key not in layout or element['symbol'] not in ('arm_upper','arm_lower','hand','leg','foot'):continue
        if element['symbol']=='hand' and element['frame']==15:continue
        normalize_limb(element,layout[key])
        if element['symbol']=='leg':
            # Keep the native hip trajectory in the pelvis while normalizing
            # the combined thigh/calf drawing's physical path length.
            translate(index,anchor(original[index],layout,0),0)

    torsos=select('torso',False)
    pelvis=select('torso_pelvis',False)
    if len(torsos)==1 and len(pelvis)==1:
        torso,pelvis_index=torsos[0],pelvis[0]
        delta=waist_anchor(elements[pelvis_index],layout)-waist_anchor(elements[torso],layout)
        elements[torso]['tx']=float(elements[torso]['tx']+delta[0])
        elements[torso]['ty']=float(elements[torso]['ty']+delta[1])
        bind_waist_seam(elements[torso],elements[pelvis_index],layout)
        pelvis_motion=matrix(elements[pelvis_index])@np.linalg.inv(matrix(original[pelvis_index]))
        for leg in select('leg',False):
            target=(pelvis_motion@np.r_[anchor(original[leg],layout,0),1.])[:2]
            translate(leg,target,0)

    torsos=select('torso',False)
    heads=select('headbase',False)
    if len(torsos)==1 and len(heads)==1:
        torso,head=torsos[0],heads[0]
        torso_entry=layout[f"torso/{original[torso]['frame']}"]
        head_entry=layout[f"headbase/{original[head]['frame']}"]
        if 'neck_anchor' in torso_entry and 'neck_anchor' in head_entry:
            target=(matrix(elements[torso])@np.r_[torso_entry['neck_anchor'],1.])[:2]
            actual=(matrix(elements[head])@np.r_[head_entry['neck_anchor'],1.])[:2]
            delta=target-actual
            for element in elements:
                if element['symbol'] in ('headbase','headbase_hat','hair','hair_hat','face','cheeks'):
                    element['tx']=float(element['tx']+delta[0])
                    element['ty']=float(element['ty']+delta[1])

    # Shared tracks are resolved last for the arm mode actually used by the
    # action. Food and work use normal arms, held attacks use carrying arms.
    for carry in ((False,True) if weapon_carry else (True,False)):
        torsos=select('torso',carry);arms=select('arm_upper',carry)
        if len(torsos)==1 and arms:
            torso=torsos[0]
            # Match native proximal positions before retargeting. Crossing hands
            # cannot swap the two shoulder sockets.
            sockets=(0,1)
            if len(arms)<=2:
                assignment=min(itertools.permutations(sockets,len(arms)),key=lambda slots:
                    sum(np.linalg.norm(shoulder_anchor(original[torso],layout,slot)-anchor(original[arm],layout,0))
                        for arm,slot in zip(arms,slots)))
                for arm,slot in zip(arms,assignment):
                    translate(arm,shoulder_anchor(elements[torso],layout,slot),0)
            else:
                # Native work clips contain a few extra motion-smear arms.
                # Keep their authored count/depth and bind each at a shoulder.
                for arm in arms:
                    slot=min(sockets,key=lambda n:np.linalg.norm(shoulder_anchor(original[torso],layout,n)-anchor(original[arm],layout,0)))
                    translate(arm,shoulder_anchor(elements[torso],layout,slot),0)
        for parent,child in [('arm_upper','arm_lower'),('arm_lower','hand'),('leg','foot')]:
            parents,children=select(parent,carry),select(child,carry)
            count=min(len(parents),len(children))
            if not count:continue
            choices=[list(zip(p,c)) for p in itertools.permutations(parents,count)
                     for c in itertools.permutations(children,count)]
            pairs=min(choices,key=lambda pairs:sum(np.linalg.norm(anchor(original[p],layout,1)-
                anchor(original[c],layout,0)) for p,c in pairs))
            for p,c in pairs:
                translate(c,anchor(elements[p],layout,1),0)

    # Props and weapon grip follow the physical hand, retaining their native
    # relative offset and the weapon's independently authored recoil matrix.
    for i,e in enumerate(original):
        if e['symbol']!='swap_object' and not (e['symbol']=='hand' and e['frame']==15):continue
        hands=select('hand',weapon_carry if e['symbol']=='swap_object' else False)
        if not hands:continue
        hand=min(hands,key=lambda j:np.linalg.norm(np.array([original[j]['tx'],original[j]['ty']])-
                                                   np.array([e['tx'],e['ty']])))
        old_hand=matrix(original[hand])
        local_grip=np.linalg.solve(old_hand,np.array([e['tx'],e['ty'],1.]))
        target=matrix(elements[hand])@local_grip
        elements[i]['tx'],elements[i]['ty']=map(float,target[:2])

    feet=select('foot',False)
    if feet and all('native_support_points' in layout[f"foot/{original[i]['frame']}"] for i in feet):
        native_ground=max(support_height(original[i],layout[f"foot/{original[i]['frame']}"]['native_support_points']) for i in feet)
        current_ground=max(support_height(elements[i],layout[f"foot/{original[i]['frame']}"]['support_points']) for i in feet)
        offset=native_ground-current_ground
        for element in elements:
            element['ty']=float(element['ty']+offset)

    # Native short hair sits between the empty and carrying arms. A long
    # curtain on that layer completely covers the carrying hand. Front/profile
    # rear hair belongs behind both arm modes and the held weapon.
    rear_hair=[e for e in elements if e['symbol'] in ('hair','hair_hat') and e['frame'] in (0,1)]
    frame['elements']=[e for e in elements if not (e['symbol'] in ('hair','hair_hat') and e['frame'] in (0,1))]+rear_hair
