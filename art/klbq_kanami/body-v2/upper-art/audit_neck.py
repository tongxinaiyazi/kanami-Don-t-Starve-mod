"""Actual neck skin/head alpha adjacency under unmodified native matrices."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'tools'))
from inspect_dst_assets import read_anim,read_game_zip
from render_kanami_body_v2 import load_registration,render_frame,BANKS
A=Path(__file__).resolve().parents[1];frames=load_registration(A)
probe='--probe-head-down' in sys.argv
if probe:
 for (symbol,number),entry in frames.items():
  if symbol=='headbase' and number in (0,1,4):entry['y']+=(1.5 if number==1 else 2.0)
regs=json.loads((A/'registration.json').read_text(encoding='utf8'))['frames']
O=Path('D:/SOFTWARE/CodexData/temp/kanami_neck_connection_qa');O.mkdir(exist_ok=True)
if probe:
 O=Path('D:/SOFTWARE/CodexData/temp/kanami_neck_connection_probe');O.mkdir(exist_ok=True)
neck={}
# Tight source-space skin strips, independently inspected; no collar/shirt alpha.
polys=[[(168,54),(239,54),(239,94),(168,94)],[(512,50),(583,50),(583,94),(512,76)],[(875,54),(941,54),(941,85),(875,85)]]
for n in range(9):
 e=regs['torso/'+str(n)];src=np.array([[*v['source_sheet'],1] for v in e['anchors'].values()]);dst=np.array([v['target_canvas'] for v in e['anchors'].values()]);M=np.linalg.solve(src,dst);poly=[tuple(np.array([*v,1])@M) for v in polys[n//3]]
 region=Image.new('L',tuple(e['canvas']));ImageDraw.Draw(region).polygon(poly,fill=255);im=frames['torso',n]['image'].getchannel('A');alpha=np.minimum(np.array(im),np.array(region));neck[n]=Image.fromarray(alpha)
def mask(e,alpha):
 f=frames[e['symbol'],e['frame']];m=np.array([[e['a'],e['c'],e['tx']+512],[e['b'],e['d'],e['ty']+700],[0,0,1]])@np.array([[1,0,f['x']-alpha.width/2],[0,1,f['y']-alpha.height/2],[0,0,1]])
 if abs(np.linalg.det(m))<1e-10:return None
 inv=np.linalg.inv(m);return np.array(alpha.transform((1024,1024),Image.Transform.AFFINE,tuple(inv[:2].flat),Image.Resampling.BILINEAR))>80
def distance(n,h):
 ny,nx=np.where(n);hy,hx=np.where(h)
 if not len(nx) or not len(hx):return None
 return float(np.sqrt(min(((nx[k:k+64,None]-hx)**2+(ny[k:k+64,None]-hy)**2).min() for k in range(0,len(nx),64))))
rows=[];saved={};excluded=[]
for name,bank in BANKS.items():
 for anim in read_anim(read_game_zip(bank,'anim.bin')):
  if anim['name']!=name:continue
  for i,f in enumerate(anim['frames']):
   h=next((e for e in f['elements'] if e['symbol']=='headbase'),None);t=next((e for e in f['elements'] if e['symbol']=='torso'),None)
   if not h or not t or h['frame'] not in (0,1):continue
   if t['frame'] not in neck:excluded.append([name,anim['facing'],i,h['frame'],t['frame']]);continue
   hm=mask(h,frames['headbase',h['frame']]['image'].getchannel('A'));nm=mask(t,neck[t['frame']]);overlap=int((hm&nm).sum());gap=0 if overlap else distance(nm,hm)
   row=dict(action=name,facing=anim['facing'],frame=i,head_frame=h['frame'],torso_frame=t['frame'],neck_pixels=int(nm.sum()),overlap=overlap,gap=gap)
   rows.append(row);saved[name,anim['facing'],i]=f
summary={}
for name in BANKS:
 rr=[r for r in rows if r['action']==name];summary[name]=dict(frames=len(rr),overlap_frames=sum(r['overlap']>0 for r in rr),gaps_gt_1_5=[r for r in rr if r['gap'] is not None and r['gap']>1.5],worst=sorted(rr,key=lambda r:r['gap'] or 0,reverse=True)[:4])
(O/'neck-alpha-report.json').write_text(json.dumps(dict(probe_head_down=probe,threshold=80,source_neck_polygons=polys,summary=summary,excluded=excluded,frames=rows),indent=2))
if probe:
 print({n:dict(frames=s['frames'],overlap=s['overlap_frames'],gaps=len(s['gaps_gt_1_5'])) for n,s in summary.items()})
 sys.exit(0) # Face calibration would also need an update; do not render misleading probe faces.
worst=[]
for name,s in summary.items():worst.extend(s['worst'][:2])
sheet=Image.new('RGB',(4*440,3*480))
for k,r in enumerate(worst):
 im=render_frame(saved[r['action'],r['facing'],r['frame']],frames,True,False,size=(440,480),scale=1.5).convert('RGB');ImageDraw.Draw(im).text((4,4),f"{r['action']} {r['facing']} frame{r['frame']} gap{r['gap']:.2f} overlap{r['overlap']}",fill='white');sheet.paste(im,((k%4)*440,(k//4)*480))
sheet.save(O/'worst-neck-frames.png')
print({n:dict(frames=s['frames'],overlap=s['overlap_frames'],gaps=len(s['gaps_gt_1_5']),max_gap=s['worst'][0]['gap'] if s['worst'] else None) for n,s in summary.items()});print('excluded',excluded)
