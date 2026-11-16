"""Diagnostic colour masks under unmodified native animation matrices.

These are local reference masks, never distributable character artwork.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from inspect_dst_assets import read_anim, read_game_zip
from render_kanami_rig import render

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')
COLOURS={'headbase':(160,150,220),'torso':(80,180,220),
 'torso_pelvis':(120,90,220),'arm_upper':(250,150,70),
 'arm_upper_skin':(250,150,70),'arm_lower':(240,210,70),
 'hand':(100,220,150),'leg':(220,120,180),'foot':(150,210,250)}

def main():
    contract=json.loads((ROOT/'art/klbq_kanami/body-v2/native-contract.json').read_text(encoding='utf8'))
    frames={}
    for key,entry in contract['frames'].items():
        symbol,number=key.split('/')
        if symbol not in COLOURS:continue
        original=Image.open(OUT/entry['reference_file']).convert('RGBA')
        im=Image.new('RGBA',original.size,COLOURS[symbol]+(255,))
        im.putalpha(original.getchannel('A'))
        frame={k:entry[k] for k in ('x','y','w','h')};frame['image']=im
        for index in range(int(number),int(number)+entry['duration']):frames[symbol,index]=frame
    requests=[('player_idles','idle_loop'),('player_basic','run_loop'),
        ('player_actions_eat','eat'),('player_actions_axe','chop_loop'),
        ('player_actions_pickaxe','pickaxe_loop'),('player_actions_shovel','shovel_loop')]
    count=0
    for bank,name in requests:
        for anim in read_anim(read_game_zip(bank,'anim.bin')):
            if anim['name']!=name or anim['facing'] not in (2,5,8):continue
            images=[]
            for frame in anim['frames']:
                im=render(frame,frames,carry=name in ('chop_loop','pickaxe_loop','shovel_loop'),size=(420,600),scale=1.35)
                draw=ImageDraw.Draw(im)
                # Native symbol origins, not guessed skin/cloth landmarks.
                for e in frame['elements']:
                    if e['symbol'] not in COLOURS:continue
                    if 'carry' in e['layer'].lower() and name in ('idle_loop','run_loop','eat'):continue
                    x=e['tx']*1.35+210;y=e['ty']*1.35+545
                    draw.ellipse((x-2,y-2,x+2,y+2),fill='white')
                images.append(im.convert('RGB'))
            images[0].save(OUT/f'joints-{name}-{anim["facing"]}.gif',save_all=True,
                append_images=images[1:],duration=round(1000/anim['fps']),loop=0)
            count+=len(images)
    print('Rendered',count,'native frames with colour-coded symbols and origins; no production files changed')

if __name__=='__main__':main()
