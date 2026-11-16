"""Original cutout registration. Native pixels are never sampled or published."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'native-contract.json').read_text(encoding='utf8'))['frames']
OUT=ROOT/'sprites'; OUT.mkdir(exist_ok=True)
S=Image.open(ROOT/'joint-art/torso-lap-source.png').convert('RGBA')
P=Image.open(ROOT/'joint-art/pelvis-clothing-source.png').convert('RGBA')
B=Image.open(ROOT/'upper-art/supplement-source.png').convert('RGBA')
T=Image.open(ROOT/'upper-art/skirt-topdown-closed-source.png').convert('RGBA')
D=Image.open(ROOT/'joint-art/bent-neck-source.png').convert('RGBA')
N=Image.open(ROOT/'joint-art/forearm-overlap-source.png').convert('RGBA')
for image,name in [(S,'joint-art/torso-lap-source.png'),(P,'joint-art/pelvis-clothing-source.png'),
                   (B,'upper-art/supplement-source.png'),(T,'upper-art/skirt-topdown-closed-source.png'),
                   (D,'joint-art/bent-neck-source.png'),(N,'joint-art/forearm-overlap-source.png')]:
    image.info['source_art']=name
frames={}

def warp(key,source,box,src,dst,meaning,labels,neck_source=None,shoulder_sources=None,waist_source=None,waist_edge_sources=None):
    e=C[key]; pad=20
    im=source.crop(box)
    p=np.array([[x-box[0],y-box[1],1] for x,y in src],float)
    q=np.array([[x+pad,y+pad] for x,y in dst],float)
    forward=np.linalg.solve(p,q).T
    mat=np.vstack([forward,[0,0,1]])
    inv=np.linalg.inv(mat)
    size=(int(e['w'])+pad*2,int(e['h'])+pad*2)
    rendered=im.transform(size,Image.Transform.AFFINE,tuple(inv[:2,:].flat),Image.Resampling.BICUBIC)
    filename=key.replace('/','_')+'.png';rendered.save(OUT/filename)
    frames[key]={'image':'sprites/'+filename,'canvas':list(size),'centre':[e['x'],e['y']],'duration':e['duration'],'original':True,'semantic':meaning,'source_art':source.info['source_art'],'source_crop':list(box),'registration_method':'three anatomical anchors with open overlap edges; joint-connected animation export; 20 pixel local padding','anchors':{name:{'source_sheet':list(a),'target_canvas':[b[0]+pad,b[1]+pad]} for name,a,b in zip(labels,src,dst)}}
    def local_point(point):
        mapped=forward@np.array([point[0]-box[0],point[1]-box[1],1.])
        return (mapped+np.array([e['x'],e['y']])-np.array(size)/2).tolist()
    if neck_source is not None:
        frames[key]['neck_anchor']=local_point(neck_source)
        frames[key]['neck_source']=list(neck_source)
    if shoulder_sources is not None:
        frames[key]['shoulder_anchors']=[local_point(p) for p in shoulder_sources]
    if waist_source is not None:
        frames[key]['waist_anchor']=local_point(waist_source)
    if waist_edge_sources is not None:
        frames[key]['waist_edges']=[local_point(p) for p in waist_edge_sources]

def local_destination(key,points):
    e=C[key]
    return [[x-e['x']+e['w']/2,y-e['y']+e['h']/2] for x,y in points]

# Neck/shoulder/waist coordinates reviewed against native pose drawings, not bbox fits.
torso_sources=[((40,40,355,380),[(99,147),(307,147),(201,326)]),((450,40,700,390),[(489,143),(593,145),(607,326)]),((760,40,1050,380),[(798,147),(1015,147),(907,323)])]
torso_targets=[[(9,22),(59,22),(34,70)],[(9,18),(60,21),(41,70)],[(16,21),(70,13),(33,70)],[(13,22),(47,22),(35,75)],[(27,22),(61,22),(34,74)],[(10,22),(44,22),(43,75)],[(9,19),(59,19),(34,70)],[(9,19),(59,19),(47,70)],[(23,19),(73,19),(36,70)]]
for n in range(9):
    view=n//3; box,anchors=torso_sources[view]
    # The original torso registration put shoulders below the arm pivots and
    # the waist at the skirt hem. Preserve native sway while joining the bones.
    shift=([(5,-9),(-5,-9),(0,-10)] if view==0 else
           [(5,-12),(-5,-12),(0,-10)] if view==1 else
           [(5,-6),(-5,-6),(0,-10)])
    torso_targets[n]=[[x+dx,y+dy] for (x,y),(dx,dy) in zip(torso_targets[n],shift)]
    warp('torso/'+str(n),S,box,anchors,torso_targets[n],['front','right profile','back'][view]+[' upright',' sway one',' sway opposite'][n%3]+'; neck/collar, shoulders and waist registered as anatomical joints',['shoulder_left','shoulder_right','waist'],neck_source=[(201,95),(545,97),(907,97)][view],waist_edge_sources=[[(143,326),(260,326)],[(552,326),(638,326)],[(854,323),(961,323)]][view])
warp('torso/9',D,(410,0,1250,1150),[(493,171),(493,1018),(1143,574)],[(15,8),(15,62),(77,34)],'Deep forward bend: right collar and shoulder sockets, left curved waist hem; belt belongs to pelvis',['waist_upper','waist_lower','neck'],neck_source=(1143,574),shoulder_sources=[(920,480),(1070,390)],waist_source=(900,574),waist_edge_sources=[(900,420),(900,730)])
warp('torso/10',B,(605,0,1075,510),[(699,84),(976,84),(841,433)],[(15,12),(55,12),(39,55)],'Skeleton death pose: original rib cage and spine, no living costume',['clavicle_left','clavicle_right','spine_base'])

# Upper arms include the bare skin and ruffled band; separate vanilla skin layer omitted.
upper_dst=[[(22,12),(22,54),(35,31)],[(29,12),(24,55),(43,31)],[(19,12),(22,51),(32,30)],[(23,12),(22,55),(36,31)],None,[(22,12),(22,51),(32,31)],[(29,12),(22,52),(36,31)]]
def set_cross_section(anchors,radius):
    """Change thickness only; preserve both anatomical joint control points."""
    a,b,c=np.asarray(anchors,float)
    axis=b-a;axis/=np.linalg.norm(axis)
    normal=np.array([-axis[1],axis[0]])
    along=a+axis*np.dot(c-a,axis)
    side=1 if np.dot(c-a,normal)>=0 else -1
    return [a.tolist(),b.tolist(),(along+normal*side*radius).tolist()]

# The old outer controls used 12–16 units despite a forearm radius near 4.
# Register exposed biceps as skin, not as the wide native shirt-sleeve envelope.
# Shoulder/elbow locations and segment lengths are unchanged.
for n in range(4):upper_dst[n]=set_cross_section(upper_dst[n],7.0 if n==1 else 5.5)
elbows=[(-1.03,36.15),(.81,35.89),(.15,34.48),(-3.49,45.84)]
for n,(ex,ey) in enumerate(elbows):
    upper_dst[n]=local_destination('arm_upper/'+str(n),[(0,0),(ex,ey),(5.2+ex/2,ey/2)])
for n in range(7):
    if n==4:
        warp('arm_upper/4',B,(1110,585,1500,990),[(1289,792),(1289,908),(1400,792)],[(22,23),(22,37),(29,23)],'Upper arm points at camera: foreshortened skin and ruffle; transverse width matches exposed arm',['shoulder_center','elbow_projected','radius'])
    else:
        bone=n>=5
        # Open shoulder/elbow cut edges are inside the smooth skin. The rounded
        # outline of a closed cylinder must never become an internal joint line.
        warp('arm_upper/'+str(n),B if bone else S,(190,525,375,1020) if bone else (845,440,990,655),[(280,590),(291,942),(330,762)] if bone else [(914,451),(911,646),(958,550)],upper_dst[n],('Skeleton humerus' if bone else 'Bare upper arm with black pink ruffle, open shoulder and elbow overlap edges')+'; '+['neutral','splayed','foreshortened','rear','disk','neutral skeleton','splayed skeleton'][n],['shoulder','elbow','outer_midpoint'])
lower_dst=[[(12,8),(12,44),(16,26)],[(14,9),(16,58),(20,33)],[(52,10),(11,23),(32,25)],[(12,9),(12,40),(16,25)],[(14,12),(16,54),(20,32)],[(13,8),(11,48),(17,28)],[(52,11),(11,23),(32,25)]]
lower_dst[2]=set_cross_section(lower_dst[2],4.5)
for n,wrist in [(0,(-.15,29.41)),(1,(1.36,41.74)),(2,(-37.59,16.99)),(5,(-.15,29.41))]:
    axis=np.asarray(wrist,float);normal=np.array([axis[1],-axis[0]])/np.linalg.norm(axis)
    midpoint=axis/2+normal*4.3
    lower_dst[n]=local_destination('arm_lower/'+str(n),[(0,0),wrist,midpoint])
for n in range(7):
    bone=n in (3,4,6)
    warp('arm_lower/'+str(n),B if bone else N,(698,520,867,1020) if bone else (0,250,825,1730),[(779,588),(785,956),(823,766)] if bone else [(354,280),(358,1640),(535,950)],lower_dst[n],('Skeleton radius and ulna' if bone else 'Bare forearm with open elbow/wrist overlaps; wrist garment belongs exclusively to hand')+'; '+['neutral vertical','extended vertical','horizontal leftward','neutral skeleton','extended skeleton','rear vertical','horizontal skeleton'][n],['elbow','wrist','outer_midpoint'])

# Skirt waist is registered to pelvis seam; flared hems intentionally extend past native shorts.
pelvis_sources=[((1070,125,1435,365),[(1183,165),(1318,165),(1249,321)]),((45,465,340,700),[(148,510),(257,510),(205,650)]),((402,465,750,700),[(508,505),(633,505),(572,650)])]
for n in range(9):
    e=C['torso_pelvis/'+str(n)];view=min(n//3,2);box,src=pelvis_sources[view]
    cx=e['w']/2; waist_y=10; hem=43 if n<9 else 59
    skew=[0,2,-2,0,-2,2,0,2,-2,0][n]
    dst=[(cx-20+skew,waist_y),(cx+20+skew,waist_y),(cx,hem)]
    warp('torso_pelvis/'+str(n),P,box,src,dst,['front skirt','profile skirt','back skirt'][view]+'; clothing only, continuous dark shorts panel, independently animated thighs contain all skin',['waist_left','waist_right','hem_center'])
warp('torso_pelvis/9',T,(40,100,1260,1070),[(411,410),(901,410),(653,1008)],local_destination('torso_pelvis/9',[(10,-28),(10,12),(-38,-8)]),'Forward-bending pelvis: radial skirt rotated to native right-side waist opening, closed dark shorts, no thigh skin',['waist_upper','waist_lower','front_hem'],waist_source=(653,260),waist_edge_sources=[(553,260),(753,260)])
warp('torso_pelvis/10',B,(1080,125,1525,500),[(1174,209),(1413,209),(1300,435)],[(15,12),(57,12),(36,43)],'Skeleton death pelvis: dedicated original bone cutout',['iliac_left','iliac_right','pubic_center'])
for n in range(3):
    key='arm_upper_skin/'+str(n); e=C[key]; filename=key.replace('/','_')+'.png'; Image.new('RGBA',(int(e['w']),int(e['h']))).save(OUT/filename)
    frames[key]={'image':'sprites/'+filename,'canvas':[int(e['w']),int(e['h'])],'centre':[e['x'],e['y']],'duration':e['duration'],'original':True,'semantic':'Redundant native under-sleeve overlay intentionally absent; complete skin/bone in arm_upper','intentional_empty':True,'reason':'Original arm_upper includes shoulder-to-elbow skin and ruffle or skeleton humerus, avoiding a double drawn overlay','covered_by':'arm_upper'}
(ROOT/'registration-upper.json').write_text(json.dumps({'frames':frames},ensure_ascii=False,indent=2),encoding='utf8')
sheet=Image.new('RGB',(1200,((len(frames)+7)//8)*180),(65,62,70)); d=ImageDraw.Draw(sheet)
for i,(key,e) in enumerate(frames.items()):
    im=Image.open(ROOT/e['image']);im.thumbnail((140,140));im=im.resize((int(im.width*1.0),int(im.height*1.0)))
    x=(i%8)*150;y=(i//8)*180;sheet.paste(im,(x+(150-im.width)//2,y+28),im);d.text((x+3,y+4),key,fill='white')
sheet.save(ROOT/'upper-art/registered-contact.png')
print('Registered',len(frames),'original frames')
