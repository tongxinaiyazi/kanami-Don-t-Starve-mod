"""Register original head/expression cutouts with explicit neck and eye anchors.

This is technical sprite registration, not native-pixel reuse or pose editing.
"""
import json,sys
from pathlib import Path
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]/'tools'))
from calibrate_kanami_face import calibrate,neutral_face_bases
C = json.loads((ROOT/'native-contract.json').read_text(encoding='utf8'))['frames']
OUT = ROOT/'sprites'
OUT.mkdir(exist_ok=True)
frames = {}
FRONT_EYE=(-8,-38)
PROFILE_EYE=(20,-45)
FRONT_MOUTH=(-6,-11)
PROFILE_MOUTH=(27,-25)
FACE_BASES=neutral_face_bases()
SMILE=Image.open(ROOT/'joint-art/neutral-smile-source.png').convert('RGBA')
face_pixels={}

def place(key, source, box, anchor, target, scale, size, centre, semantic):
    im=Image.open(ROOT/source).convert('RGBA').crop(box)
    # Source anatomical anchor maps to specified local build coordinates.
    origin=(size[0]/2-centre[0],size[1]/2-centre[1])
    sx,sy=scale if isinstance(scale,tuple) else (scale,scale)
    dx=origin[0]+target[0]-(anchor[0]-box[0])*sx
    dy=origin[1]+target[1]-(anchor[1]-box[1])*sy
    im=im.transform(size,Image.Transform.AFFINE,(1/sx,0,-dx/sx,0,1/sy,-dy/sy),Image.Resampling.BICUBIC)
    filename=key.replace('/','_')+'.png'
    im.save(OUT/filename)
    frames[key]=dict(image='sprites/'+filename,canvas=list(size),centre=list(centre),duration=C[key]['duration'],original=True,semantic=semantic,source_art=source,source_crop=list(box),source_anchor=list(anchor),local_anchor=list(target),scale=scale)

def omit(key, reason):
    filename=key.replace('/','_')+'.png'
    Image.new('RGBA',(4,4)).save(OUT/filename)
    frames[key]=dict(image='sprites/'+filename,canvas=[4,4],centre=[0,0],duration=C[key]['duration'],original=True,semantic=reason,intentional_empty=True,reason=reason)

# Head slots retain native animation transforms. Neck ends, not alpha bboxes,
# determine registration. Hair belongs to the same continuous skull silhouette.
views=[((0,0,560,515),(260,477),(-6,-3),.38),
       ((560,0,1040,515),(832,474),(-6,-10.5),.38),
       ((1151,0,1716,916),(1436,552),(-6,0),.38)]
for symbol in ('headbase','headbase_hat'):
    for n in (0,1,2,4):
        view=n if n<3 else 0
        box,anchor,target,scale=views[view]
        source='head-hair-source.png' if view<2 else 'head-complete-source.png'
        place(f'{symbol}/{n}',source,box,anchor,target,scale,(340,440),(0,-30),['Front skull, chin and short neck attachment; long hair on rear layer','Profile skull, jaw and short neck attachment; long hair on rear layer','Back skull and continuous loose hair; side lock on viewer left'][view])
        if view<2:
            neck_source=(260,490) if view==0 else (832,491)
            frames[f'{symbol}/{n}']['neck_anchor']=[target[0]+(neck_source[0]-anchor[0])*scale,target[1]+(neck_source[1]-anchor[1])*scale]
        if n==4:frames[f'{symbol}/{n}']['shared_pose_reason']='Puffed-cheek head uses the same skull; animated facial overlay provides expression.'
    place(f'{symbol}/3','skull-source.png',(0,0,1280,1200),(645,1100),(-6,23),.15,(208,208),(-6,-65),'Dedicated original skeleton skull for death and shock frames')
    place(f'{symbol}/2','head-hair-source.png',(1264,443,1330,501),(1294,488),(-6,0),.38,(64,64),(-6,0),'Underlying anatomical nape; rear skull and waterfall are on foreground hair/2, avoiding a second displaced crown')
    frames[f'{symbol}/2']['neck_anchor']=[-6,0]

for s in ('hair','hair_hat'):
    for n in range(4):omit(f'{s}/{n}','Crown and loose hair authored continuously in headbase; omit separate native short-hair overlay to prevent duplicate crowns.')
    place(f'{s}/0','joint-art/front-curtain-source.png',(0,515,565,1024),(260,525),(-6,-43),(.44,.49),(340,440),(-6,30),'Continuous loose front-view back-hair curtain, filled centre behind torso and legs; crown overlaps behind the skull instead of protruding above it')
    place(f'{s}/1','head-hair-no-neck-source.png',(565,515,1030,1024),(800,535),(0,-55),(.44,.55),(340,440),(0,30),'Profile loose hair curtain on native rear hair layer; upper arms remain visible')

# Back-view native headbase is mirrored and sits BEHIND the torso, whereas
# hair/2 is unmirrored and sits IN FRONT of it. Register the back waterfall to
# that native layer: putting it in headbase makes the neck poke out of hair.
for s in ('hair','hair_hat'):
    place(f'{s}/2','head-complete-source.png',(1151,0,1716,916),(1436,552),(-11.3,75.7),.38,(340,440),(0,45),'Back crown and continuous loose waterfall on native foreground hair layer; anatomical left lock remains viewer-left; overlap covers native independent hair stretch')

meanings=['neutral','half blink','closed blink','side glance','profile neutral','profile half blink','profile blink','profile glance','focused neutral','speaking','surprise','calm closed','worried wide','fainted','glowing eyes','delighted','worried frown','asleep','drowsy','concerned','tired speaking','gritted teeth','unhappy','crying shout','gasp','wide shout','teeth clench','closed speaking','side glance','distress','attention speaking','dizzy','closed shout']
# Face decals are registered to the lower face area of the new round skull.
# Keep native per-frame movement; only decal local placement is authored.
calibration=calibrate(front=FRONT_EYE,profile=PROFILE_EYE)


def place_expression(number, source, box, anchor, eye_scale, centre):
    """Register eyes, a very subtle closed mouth and readable open expressions."""
    key=f'face/{number}'
    fallback=4 if number in (4,5,6,7) else 0
    eye_fit=calibration.get(number,calibration[fallback])
    profile=number in (4,5,6,7)
    head_eye=PROFILE_EYE if profile else FRONT_EYE
    head_mouth=PROFILE_MOUTH if profile else FRONT_MOUTH
    mouth_target=(np.asarray(eye_fit['local_eye_anchor'])+
                  np.linalg.solve(FACE_BASES[int(profile)],np.asarray(head_mouth)-head_eye)).tolist()
    size=(160,176)
    origin=(size[0]/2-centre[0],size[1]/2-centre[1])
    atlas=Image.open(ROOT/source).convert('RGBA')
    painted=np.asarray(atlas.crop(box))[:,:,3]>128
    rows=np.flatnonzero(painted.sum(axis=1)>2)
    gaps=np.flatnonzero(np.diff(rows)>1)
    if not len(gaps):
        raise ValueError(f'Expression {number} needs separate eye and mouth artwork')
    gap=gaps[-1]
    split_y=box[1]+round((rows[gap]+rows[gap+1])/2)
    eyes=atlas.crop((box[0],box[1],box[2],split_y))
    pixels=np.asarray(eyes,dtype=float)
    red,green,blue,alpha=(pixels[:,:,i] for i in range(4))
    iris=(alpha>128)&(blue>red*1.3)&(blue>green*1.1)&(blue>90)
    iris_y,iris_x=np.where(iris)
    eye_anchor=anchor
    if len(iris_x)>20:
        eye_anchor=(box[0]+float(iris_x.mean()),box[1]+float(iris_y.mean()))
    target=eye_fit['local_eye_anchor']
    dx=origin[0]+target[0]-(eye_anchor[0]-box[0])*eye_scale
    dy=origin[1]+target[1]-(eye_anchor[1]-box[1])*eye_scale
    result=eyes.transform(size,Image.Transform.AFFINE,
        (1/eye_scale,0,-dx/eye_scale,0,1/eye_scale,-dy/eye_scale),Image.Resampling.BICUBIC)
    neutral=number in (0,1,2,3,4,5,6,7,8,11)
    if neutral:
        mouth=SMILE
        mouth_anchor=(886,467)
        sx,sy=(.006,.025) if profile else (.007,.025)
    else:
        mouth=atlas.crop((box[0],split_y,box[2],box[3]))
        bounds=mouth.getchannel('A').point(lambda a:255 if a>128 else 0).getbbox()
        if bounds is None:raise ValueError(f'Missing mouth expression {number}')
        mouth_anchor=((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2)
        sx=sy=min(.17,7/(bounds[2]-bounds[0]),5/(bounds[3]-bounds[1]))
    dx=origin[0]+mouth_target[0]-mouth_anchor[0]*sx
    dy=origin[1]+mouth_target[1]-mouth_anchor[1]*sy
    result.alpha_composite(mouth.transform(size,Image.Transform.AFFINE,
        (1/sx,0,-dx/sx,0,1/sy,-dy/sy),Image.Resampling.BICUBIC))
    filename=f'face_{number}.png'
    result.save(OUT/filename)
    frames[key]=dict(image='sprites/'+filename,canvas=list(size),centre=list(centre),
        duration=C[key]['duration'],original=True,semantic=meanings[number]+'; subtle closed mouth and independently registered open mouth',
        source_art=source,source_crop=list(box),source_anchor=list(eye_anchor),
        eye_scale=eye_scale,mouth_scale=[sx,sy],mouth_mode='subtle_closed' if neutral else 'expression',split_y=split_y,
        local_eye_anchor=eye_fit['local_eye_anchor'],head_eye_anchor=list(head_eye),
        local_mouth_anchor=mouth_target,head_mouth_anchor=list(head_mouth),
        calibration=eye_fit)
    previous=face_pixels.setdefault(result.tobytes(),number)
    if previous!=number:
        frames[key]['shared_pose_reason']=f'Same authored expression and subtle mouth as face/{previous}.'
eye_rows=[136,334,535,735,932,1134]
for n,meaning in enumerate(meanings):
    row,col=divmod(n,6)
    x0=round(col*1269/6);x1=round((col+1)*1269/6)
    y0=round(row*1240/6);y1=round((row+1)*1240/6)
    profile=n in (4,5,6,7)
    anchor=(x0+106,eye_rows[row])
    place_expression(n,'joint-art/face-heart-source.png',(x0,y0,x1,y1),anchor,
        .43,(-7,32))
for n in (4,5,6,7):
    col=n-4
    place_expression(n,'joint-art/profile-features-source.png',(col*543,0,(col+1)*543,724),
        (col*543+279,375),.15,(-18,25))
for n in (0,1):omit(f'cheeks/{n}','Round face silhouette already includes cheeks; original white puff overlays omitted.')
# Inventory swap icon never appears in body animation; source is original face art.
place('SWAP_ICON/0','head-complete-source.png',(0,0,634,916),(321,450),(0,0),.15,(128,160),(0,0),'Original front head icon')
(ROOT/'registration-head.json').write_text(json.dumps({'frames':frames},ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'face-registration-audit.json').write_text(json.dumps(calibration,ensure_ascii=False,indent=2),encoding='utf8')
print('Registered',len(frames),'head and expression frames')
