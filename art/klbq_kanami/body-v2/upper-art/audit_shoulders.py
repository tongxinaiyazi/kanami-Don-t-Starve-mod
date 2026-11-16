"""Native versus original shoulder masks and foreground hair occlusion."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'tools'))
from inspect_dst_assets import read_anim,read_game_zip
from render_kanami_body_v2 import visible,load_registration,render_frame
A=Path(__file__).resolve().parents[1];C=json.loads((A/'native-contract.json').read_text(encoding='utf8'))['frames'];REG=json.loads((A/'registration-upper.json').read_text(encoding='utf8'))['frames']
O=Path('D:/SOFTWARE/CodexData/temp/kanami_shoulder_qa');O.mkdir(exist_ok=True)
native={};cand=load_registration(A)
for key,e in C.items():
 s,n=key.split('/');f={k:e[k] for k in ('x','y','w','h')};f['image']=Image.open(Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')/e['reference_file']).convert('RGBA')
 for i in range(int(n),int(n)+e['duration']):native[s,i]=f
# Always use latest upper-part registration even before parent merges it.
for key,e in REG.items():
 s,n=key.split('/');f=dict(x=e['centre'][0],y=e['centre'][1],w=e['canvas'][0],h=e['canvas'][1],image=Image.open(A/e['image']).convert('RGBA'))
 for i in range(int(n),int(n)+e['duration']):cand[s,i]=f
def mask(e,frames):
 f=frames.get((e['symbol'],e['frame']))
 if not f:return None
 im=f['image'];m=np.array([[e['a'],e['c'],e['tx']+320],[e['b'],e['d'],e['ty']+480],[0,0,1]])@np.array([[1,0,f['x']-im.width/2],[0,1,f['y']-im.height/2],[0,0,1]])
 if abs(np.linalg.det(m))<1e-10:return None
 inv=np.linalg.inv(m);return np.array(im.getchannel('A').transform((640,560),Image.Transform.AFFINE,tuple(inv[:2].flat),Image.Resampling.BILINEAR))>80
def nearest(a,b):
 ay,ax=np.where(a);by,bx=np.where(b)
 if not len(ax) or not len(bx):return None
 # nearest squared distance, chunked to limit RAM
 return float(np.sqrt(min(((ax[k:k+128,None]-bx)**2+(ay[k:k+128,None]-by)**2).min() for k in range(0,len(ax),128))))
BANKS=[('player_idles','idle_loop'),('player_basic','run_loop'),('player_actions_eat','eat'),('player_actions_axe','chop_loop'),('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop')]
rows=[];tiles=[]
for bank,name in BANKS:
 for anim in read_anim(read_game_zip(bank,'anim.bin')):
  if anim['name']!=name:continue
  for i,frame in enumerate(anim['frames']):
   for carry in (False,True):
    elements=[e for e in frame['elements'] if visible(e,carry,False)];torso=next((e for e in elements if e['symbol']=='torso'),None)
    if not torso:continue
    tm=mask(torso,cand);tn=mask(torso,native)
    for ai,upper in enumerate(elements):
     if upper['symbol']!='arm_upper':continue
     am=mask(upper,cand);an=mask(upper,native)
     if any(v is None for v in [am,an,tm,tn]):continue
     overlap=am&tm;hairm=[mask(e,cand) for e in elements[:ai] if e['symbol'].startswith('hair') or e['symbol'].startswith('headbase')];hairm=[m for m in hairm if m is not None];hair=np.logical_or.reduce(hairm) if hairm else np.zeros_like(am)
     gap=0 if overlap.any() else nearest(am,tm);ngap=0 if (an&tn).any() else nearest(an,tn)
     rows.append(dict(action=name,facing=anim['facing'],frame=i,carry=carry,layer=upper['layer'],arm_frame=upper['frame'],torso_frame=torso['frame'],gap=gap,native_gap=ngap,overlap=int(overlap.sum()),overlap_covered_by_hair=int((overlap&hair).sum()),upper_pixels=int(am.sum()),upper_covered_by_hair=int((am&hair).sum())))
    if name=='eat' and i in (18,26) and carry:
     for label,frames,hide in [('current hair',cand,False),('current no hair',cand,True),('native no hair',native,True)]:
      render_input=frame if not hide else dict(frame,elements=[e for e in frame['elements'] if not (e['symbol'].startswith('headbase') or e['symbol'].startswith('face') or e['symbol'].startswith('cheek'))])
      im=render_frame(render_input,frames,True,hide,size=(600,650),scale=2).convert('RGB');ImageDraw.Draw(im).text((8,8),f'eat {i} {label}',fill='white');tiles.append(im)
summary={name:dict(checks=len(rr:=[r for r in rows if r['action']==name]),new_gaps=[r for r in rr if r['gap'] is not None and r['gap']>max(1.5,(r['native_gap'] or 0)+1)]) for _,name in BANKS}
(O/'shoulder-relation.json').write_text(json.dumps(dict(summary=summary,all_frames=rows),indent=2));sheet=Image.new('RGB',(1800,1300))
for i,im in enumerate(tiles):sheet.paste(im,((i%3)*600,(i//3)*650))
sheet.save(O/'eat-shoulder-comparison.png');print({k:dict(checks=v['checks'],new_gaps=len(v['new_gaps'])) for k,v in summary.items()})
