"""Mixed native REFERENCE-only joint checks; output is never distributable."""
import sys,json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'tools'))
from render_kanami_body_v2 import render_frame,add_frame
from inspect_dst_assets import read_anim,read_game_zip
A=Path(__file__).resolve().parents[1]; F={}
C=json.loads((A/'native-contract.json').read_text(encoding='utf8'))['frames']
for key,e in C.items():
 s,n=key.split('/'); f={k:e[k] for k in ('x','y','w','h')};f['image']=Image.open(Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')/e['reference_file']).convert('RGBA')
 add_frame(F,s,int(n),e['duration'],f)
reg=json.loads((A/'registration-upper.json').read_text(encoding='utf8'))['frames']
for key,e in reg.items():
 s,n=key.split('/');f=dict(x=e['centre'][0],y=e['centre'][1],w=e['canvas'][0],h=e['canvas'][1],image=Image.open(A/e['image']).convert('RGBA'))
 for number in range(int(n),int(n)+e['duration']):F[s,number]=f
O=Path('D:/SOFTWARE/CodexData/temp/kanami_upper_qa');O.mkdir(exist_ok=True)
tiles=[]
for bank,name in [('player_idles','idle_loop'),('player_basic','run_loop'),('player_actions_axe','chop_loop'),('player_actions_eat','eat'),('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop'),('player_actions_bugnet','bugnet'),('player_mount_shock','shock')]:
 for anim in read_anim(read_game_zip(bank,'anim.bin')):
  if anim['name']!=name:continue
  imgs=[render_frame(f,F,carry=name=='chop_loop',hide_hair=True,size=(250,380),scale=1.5).convert('RGB') for f in anim['frames']]
  imgs[0].save(O/(name+'-'+str(anim['facing'])+'.gif'),save_all=True,append_images=imgs[1:],duration=33,loop=0)
  for i in [0,len(imgs)//3,2*len(imgs)//3]:
   im=imgs[i].copy();ImageDraw.Draw(im).text((4,4),f'{name}-{anim["facing"]}-{i}',fill='white');tiles.append(im)
o=Image.new('RGB',(9*250,((len(tiles)+8)//9)*380))
for i,im in enumerate(tiles):o.paste(im,((i%9)*250,(i//9)*380))
o.save(O/'contact.png');print(O)
