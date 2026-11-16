"""Held-prop reference QA only, with no edits to weapon or native transforms."""
import json,sys
from pathlib import Path
from PIL import Image,ImageDraw
ART=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ART.parents[2]/'tools'))
from render_kanami_body_v2 import load_exported,render_frame,add_frame
from inspect_dst_assets import read_anim,read_game_zip
contract=json.loads((ART/'native-contract.json').read_text(encoding='utf8'))
frames={}
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
anims=read_anim(read_game_zip('player_idles','anim.bin'))
sheet=Image.new('RGB',(1800,1000),(38,33,46))
for row,weapon in enumerate(('swap_klbq_finale','swap_klbq_crossbow')):
    combined=dict(frames)
    combined.update(load_exported(ART.parent/'exported'/weapon))
    for col,facing in enumerate((8,5,2)):
        a=next(a for a in anims if a['name']=='idle_loop' and a['facing']==facing)
        im=render_frame(a['frames'][0],combined,carry=True,hide_hair=True,size=(600,500),scale=1.5).convert('RGB')
        ImageDraw.Draw(im).text((8,8),f'{weapon} / native idle {facing} / no compensation',fill='white')
        sheet.paste(im,(col*600,row*500))
out=Path('D:/SOFTWARE/CodexData/temp/kanami_body_v2_hands')/'weapon-grips-contact.png'
sheet.save(out)
print(out)
