"""Compare actual limb silhouettes under the same installed native animations.

Pair limbs using native art before measuring the replacement. Native layer
names are not anatomy: several back-facing actions name a forearm swap_object.
"""
import itertools
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from render_kanami_body_v2 import ROOT, BANKS, DEFAULT_ACTIONS, add_frame, load_registration, render_frame, visible
from inspect_dst_assets import read_anim, read_game_zip
from calibrate_kanami_face import matrix

ART = ROOT/'art/klbq_kanami/body-v2'
OUTPUT = Path('D:/SOFTWARE/CodexData/temp/kanami_connections')
PAIRS = [('arm_lower', 'arm_upper', 'elbow'), ('arm_lower', 'hand', 'wrist'),
         ('foot', 'leg', 'ankle'), ('leg', 'torso_pelvis', 'hip')]


def mask(element, frames):
    entry = frames.get((element['symbol'], element['frame']))
    if entry is None:
        return np.zeros((560, 640), dtype=bool)
    image = entry['image']
    matrix = np.array([[element['a'], element['c'], element['tx']+320],
                       [element['b'], element['d'], element['ty']+480], [0, 0, 1.]])
    matrix = matrix @ np.array([[1, 0, entry['x']-image.width/2],
                                [0, 1, entry['y']-image.height/2], [0, 0, 1.]])
    if abs(np.linalg.det(matrix)) < 1e-10:
        return np.zeros((560, 640), dtype=bool)
    inverse = np.linalg.inv(matrix)
    alpha = image.getchannel('A').transform((640, 560), Image.Transform.AFFINE,
        tuple(inverse[:2].flat), Image.Resampling.BILINEAR)
    return np.asarray(alpha) > 80


def gap(first, second):
    if np.any(first & second):
        return 0.
    y1, x1 = np.where(first)
    y2, x2 = np.where(second)
    if not len(x1) or not len(x2):
        return None
    return float(np.sqrt(min(
        ((x1[start:start+64, None]-x2)**2+(y1[start:start+64, None]-y2)**2).min()
        for start in range(0, len(x1), 64))))


def joint_point(element, distal, registration):
    entry=registration[f"{element['symbol']}/{element['frame']}"]
    if 'anchors' in entry:
        anchors=list(entry['anchors'].values())
        point=np.array(anchors[1 if distal else 0]['target_canvas'],float)
        point+=np.array(entry['centre'])-np.array(entry['canvas'])/2
    elif 'local_anchors' in entry:
        point=np.array(entry['local_anchors'][-1 if distal else 0],float)
    elif 'native_wrist_local' in entry:
        point=np.array(entry['native_wrist_local'],float)
    else:
        return None
    return (matrix(element)@np.array([*point,1]))[:2]


def gap_coverage(first,second,frame,candidate,carry):
    y1,x1=np.where(first)
    y2,x2=np.where(second)
    closest=None
    for start in range(0,len(x1),64):
        distances=(x1[start:start+64,None]-x2)**2+(y1[start:start+64,None]-y2)**2
        i,j=np.unravel_index(distances.argmin(),distances.shape)
        item=(int(distances[i,j]),start+i,j)
        if closest is None or item[0]<closest[0]:
            closest=item
    if closest is None:
        return 0.
    distance,i,j=closest
    steps=max(3,int(np.sqrt(distance)*2)+1)
    x=np.rint(np.linspace(x1[i],x2[j],steps)[1:-1]).astype(int)
    y=np.rint(np.linspace(y1[i],y2[j],steps)[1:-1]).astype(int)
    covering=np.zeros_like(first)
    for element in frame['elements']:
        if visible(element,carry,False) and element['symbol'] in ('hair','headbase','torso','torso_pelvis'):
            covering|=mask(element,candidate)
    return float(covering[y,x].mean())


def main():
    OUTPUT.mkdir(exist_ok=True)
    candidate = load_registration(ART)
    registration=json.loads((ART/'registration.json').read_text(encoding='utf8'))['frames']
    contract = json.loads((ART/'native-contract.json').read_text(encoding='utf8'))
    native = {}
    for key, entry in contract['frames'].items():
        symbol, number = key.split('/')
        image = Image.open(Path(contract['reference_directory'])/entry['reference_file']).convert('RGBA')
        add_frame(native, symbol, int(number), entry['duration'], dict(entry, image=image))
    checks, issues, examples, excluded = [], [], [], []
    for name in DEFAULT_ACTIONS:
        bank=BANKS[name]
        for animation in read_anim(read_game_zip(bank, 'anim.bin')):
            if animation['name'] != name:
                continue
            carrying_modes=(False,True) if name in ('idle_loop','run_loop') else (name!='eat',)
            for carry in carrying_modes:
                for number, frame in enumerate(animation['frames']):
                    elements = [e for e in frame['elements'] if visible(e, carry, True)]
                    relevant = set(s for pair in PAIRS for s in pair[:2])
                    silhouettes = [(e, mask(e, native), mask(e, candidate)) for e in elements if e['symbol'] in relevant]
                    for first_symbol, second_symbol, joint in PAIRS:
                        first = [s for s in silhouettes if s[0]['symbol'] == first_symbol]
                        second = [s for s in silhouettes if s[0]['symbol'] == second_symbol]
                        if not first or not second:
                            continue
                        choices = list(itertools.permutations(range(len(second)), len(first)))
                        if len(second) == 1:
                            choices = [tuple(0 for _ in first)]
                        costs = [[gap(a[1], b[1]) for b in second] for a in first]
                        choices = [choice for choice in choices if all(costs[i][j] is not None for i, j in enumerate(choice))]
                        if not choices:
                            continue
                        anatomical_costs=costs
                        if joint!='hip':
                            anatomical_costs=[]
                            for a in first:
                                end=joint_point(a[0],joint=='wrist',registration)
                                distances=[]
                                for b in second:
                                    start=joint_point(b[0],joint in ('elbow','ankle'),registration)
                                    distances.append(float(np.linalg.norm(end-start)))
                                anatomical_costs.append(distances)
                        pairing = min(choices, key=lambda choice: sum(anatomical_costs[i][j] for i, j in enumerate(choice)))
                        for i, j in enumerate(pairing):
                            a, b = first[i], second[j]
                            row = dict(action=name, facing=animation['facing'], frame=number, carry=carry,
                                joint=joint, first=[a[0]['symbol'], a[0]['frame'], a[0]['layer']],
                                second=[b[0]['symbol'], b[0]['frame'], b[0]['layer']], native_gap=costs[i][j])
                            if b[0]['symbol'] == 'hand' and b[0]['frame'] == 15:
                                excluded.append(dict(row, reason='Native cup prop slot has no wrist'))
                                continue
                            row['candidate_gap'] = gap(a[2], b[2])
                            checks.append(row)
                            if row['candidate_gap'] is None or row['candidate_gap'] > row['native_gap']+1.5:
                                row['gap_coverage']=gap_coverage(a[2],b[2],frame,candidate,carry)
                                issues.append(row)
                                examples.append((row, frame))
        print(name, 'checked', len(checks), 'regressions', len(issues), flush=True)
    report = dict(checks=len(checks), regressions=len(issues),
        visible_regressions=sum(row['gap_coverage']<1 for row in issues),
        occluded_alerts=sum(row['gap_coverage']==1 for row in issues), excluded=excluded, issues=issues,
        joints={joint: sum(r['joint'] == joint for r in checks) for _, _, joint in PAIRS})
    (OUTPUT/'report.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    chosen = sorted(examples, key=lambda row: row[0]['candidate_gap'] or 0, reverse=True)[:12]
    sheet = Image.new('RGB', (4*400, 3*440), (38, 33, 46))
    for index, (row, frame) in enumerate(chosen):
        image = render_frame(frame, candidate, row['carry'], True, size=(400, 440), scale=1.3)
        ImageDraw.Draw(image).text((4, 4), f"{row['action']} {row['facing']} f{row['frame']} {row['joint']} gap {row['candidate_gap']}", fill='white')
        sheet.paste(image, (index % 4*400, index // 4*440))
    sheet.save(OUTPUT/'regressions.png')
    print(json.dumps({k: v for k, v in report.items() if k not in ('issues', 'excluded')}))


if __name__ == '__main__':
    main()
