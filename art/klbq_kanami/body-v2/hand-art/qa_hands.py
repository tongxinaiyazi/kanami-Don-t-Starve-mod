"""Local-only mixed native reference plus new upper/hands; NEVER distribute."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ART=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ART.parents[2]/'tools'))
from render_kanami_body_v2 import render_frame, add_frame
from inspect_dst_assets import read_anim,read_game_zip

frames={}
contract=json.loads((ART/'native-contract.json').read_text(encoding='utf8'))
for key,e in contract['frames'].items():
    symbol,num=key.split('/')
    f={k:e[k] for k in ('x','y','w','h')}
    f['image']=Image.open(Path(contract['reference_directory'])/e['reference_file']).convert('RGBA')
    add_frame(frames,symbol,int(num),e['duration'],f)
for filename in ('registration-upper.json','registration-hands.json'):
    for key,e in json.loads((ART/filename).read_text(encoding='utf8'))['frames'].items():
        symbol,num=key.split('/')
        f=dict(x=e['centre'][0],y=e['centre'][1],w=e['canvas'][0],h=e['canvas'][1],image=Image.open(ART/e['image']).convert('RGBA'))
        for n in range(int(num),int(num)+e['duration']):frames[symbol,n]=f
out=Path('D:/SOFTWARE/CodexData/temp/kanami_body_v2_hands')
out.mkdir(exist_ok=True)
tiles=[]
for bank,name in [('player_idles','idle_loop'),('player_basic','run_loop'),('player_actions_eat','eat'),('player_actions_axe','chop_loop'),('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop')]:
    for anim in read_anim(read_game_zip(bank,'anim.bin')):
        if anim['name']!=name:continue
        for carry in (False,True):
            stem=f'{name}-{anim["facing"]}-'+('carry' if carry else 'empty')
            images=[]
            for i,frame in enumerate(anim['frames']):
                im=render_frame(frame,frames,carry=carry,hide_hair=True,size=(440,480),scale=1.5).convert('RGB')
                ImageDraw.Draw(im).text((4,4),f'{stem} {i}',fill='white')
                images.append(im)
            images[0].save(out/(stem+'.gif'),save_all=True,append_images=images[1:],duration=33,loop=0)
            if name in ('idle_loop','run_loop','eat'):
                tiles.extend(images[i] for i in (0,len(images)//3,2*len(images)//3))
sheet=Image.new('RGB',(9*440,((len(tiles)+8)//9)*480),(38,33,46))
for i,im in enumerate(tiles):sheet.paste(im,((i%9)*440,(i//9)*480))
sheet.save(out/'mixed-upper-hand-contact.png')
print(out)
