"""Render native and current builds through identical unmodified native poses.

Original reference pixels and their renders stay outside the distributable art.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from inspect_dst_assets import read_anim, read_game_zip
from render_kanami_rig import load_build, render

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')

def main():
    contract=json.loads((ROOT/'art/klbq_kanami/body-v2/native-contract.json').read_text(encoding='utf8'))
    native={}
    for key,f in contract['frames'].items():
        symbol,number=key.split('/')
        frame={k:f[k] for k in ('x','y','w','h')}
        frame['image']=Image.open(OUT/f['reference_file']).convert('RGBA')
        for index in range(int(number),int(number)+f['duration']):
            native[symbol,index]=frame
    current=load_build(ROOT/'art/klbq_kanami/exported/klbq_kanami')
    banks={bank:read_anim(read_game_zip(bank,'anim.bin')) for bank in (
        'player_idles','player_basic','player_actions_eat',
        'player_actions_axe','player_actions_pickaxe','player_actions_shovel')}
    requests=[('player_idles','idle_loop'),('player_basic','run_loop'),
        ('player_actions_eat','eat'),('player_actions_axe','chop_loop'),
        ('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop')]
    manifest=[]
    for bank,name in requests:
        candidates=[a for a in banks[bank] if a['name']==name]
        if not candidates:
            print('Animation names for',bank,sorted({a['name'] for a in banks[bank]}))
            continue
        for a in candidates:
            if a['facing'] not in (2,5,8):continue
            indices=sorted({0,len(a['frames'])//3,len(a['frames'])*2//3,len(a['frames'])-1})
            sheet=Image.new('RGB',(800,560*len(indices)),(38,33,46))
            draw=ImageDraw.Draw(sheet)
            for row,index in enumerate(indices):
                frame=a['frames'][index]
                for column,(label,build) in enumerate((('NATIVE',native),('CURRENT / NATIVE ANIMATION',current))):
                    im=render(frame,build,carry=name.endswith('_loop') and name!='idle_loop' and name!='run_loop',size=(400,540),scale=1.5)
                    sheet.paste(im,(column*400,row*560+20))
                    draw.text((column*400+8,row*560+4),f'{label} {name} facing={a["facing"]} frame={index}',fill='white')
            path=OUT/f'compare-{name}-{a["facing"]}.png';sheet.save(path)
            manifest.append(str(path))
    (OUT/'comparisons.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('Wrote',len(manifest),'same-scale comparison sheets to',OUT)

if __name__=='__main__':main()
