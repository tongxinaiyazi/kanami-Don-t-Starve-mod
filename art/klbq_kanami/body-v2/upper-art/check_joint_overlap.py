"""Alpha-only connection metric, paired native-animation layers; no native exports."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'tools'))
from inspect_dst_assets import read_anim,read_game_zip
from render_kanami_body_v2 import visible
A=Path(__file__).resolve().parents[1];C=json.loads((A/'native-contract.json').read_text(encoding='utf8'))['frames'];REG=json.loads((A/'registration-upper.json').read_text(encoding='utf8'))['frames']
if '--hands' in sys.argv:REG.update(json.loads((A/'registration-hands.json').read_text(encoding='utf8'))['frames'])
F={}
for key,e in C.items():
 s,n=key.split('/'); native=Image.open(Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')/e['reference_file']).convert('RGBA'); f=dict(x=e['x'],y=e['y'],im=native)
 if key in REG and '--native' not in sys.argv:
  v=REG[key];f=dict(x=v['centre'][0],y=v['centre'][1],im=Image.open(A/v['image']).convert('RGBA'))
 for i in range(int(n),int(n)+e['duration']):F[s,i]=f
def mask(e):
 f=F.get((e['symbol'],e['frame']))
 if not f:return None
 im=f['im'];m=np.array([[e['a'],e['c'],e['tx']+320],[e['b'],e['d'],e['ty']+480],[0,0,1]])@np.array([[1,0,f['x']-im.width/2],[0,1,f['y']-im.height/2],[0,0,1]])
 if abs(np.linalg.det(m))<1e-10:return None
 inv=np.linalg.inv(m);return np.array(im.getchannel('A').transform((640,560),Image.Transform.AFFINE,tuple(inv[:2].flat),Image.Resampling.BILINEAR))>80
def nearest(a,b):
 ay,ax=np.where(a);by,bx=np.where(b)
 if not len(ax) or not len(bx):return None
 return float(np.sqrt(((ax[:,None]-bx)**2+(ay[:,None]-by)**2).min()))
issues=[];counts={};worst={}
for bank,name in [('player_idles','idle_loop'),('player_basic','run_loop'),('player_actions_axe','chop_loop'),('player_actions_eat','eat'),('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop')]:
 for anim in read_anim(read_game_zip(bank,'anim.bin')):
  if anim['name']!=name:continue
  for carry in (False,True):
   for i,frame in enumerate(anim['frames']):
    elements=[e for e in frame['elements'] if visible(e,carry,True)]
    for e in elements:
     if e['symbol']!='arm_lower':continue
     layer=e['layer'];group=layer if layer.lower().startswith('arm_') and layer.lower() not in ('arm_upper','arm_lower') else 'default'
     def groupof(v):return v['layer'] if v['layer'].lower().startswith('arm_') and v['layer'].lower() not in ('arm_upper','arm_lower') else 'default'
     for symbol,joint in [('arm_upper','elbow'),('hand','wrist')]:
      others=[v for v in elements if v['symbol']==symbol]
      if not others:continue
      other=others[0]
      m1=mask(e); mm=[mask(v) for v in others]; mm=[m for m in mm if m is not None];m2=np.logical_or.reduce(mm) if mm else None
      if m1 is None or m2 is None:continue
      counts[joint]=counts.get(joint,0)+1
      gap=0 if np.any(m1&m2) else nearest(m1,m2)
      if gap is not None and gap>worst.get(joint,0):worst[joint]=gap
      if gap is not None and gap>1.5:issues.append(dict(action=name,facing=anim['facing'],frame=i,carry=carry,joint=joint,layer=layer,gap_pixels=gap,lower=e['frame'],other=other['frame']))
out=Path('D:/SOFTWARE/CodexData/temp/kanami_upper_qa')/('joint-overlap-native.json' if '--native' in sys.argv else 'joint-overlap-hands.json' if '--hands' in sys.argv else 'joint-overlap.json');out.write_text(json.dumps(dict(counts=counts,worst=worst,issues=issues),indent=2));print(json.dumps(dict(counts=counts,worst=worst,issues=len(issues))))
