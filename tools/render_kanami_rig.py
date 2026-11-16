"""Render source cutouts through actual DST animation matrices for asset QA."""
import argparse
import math
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from inspect_dst_assets import read_anim,read_game_zip

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'art/klbq_kanami'

def load_build(folder):
    frames={}
    for symbol in ET.parse(folder/'build.xml').getroot():
        for f in symbol:
            frame={k:float(f.get(k)) for k in ('x','y','w','h')}
            frame['image']=Image.open(folder/(f.get('image')+'.png')).convert('RGBA')
            frames[(symbol.get('name'),int(f.get('framenum')))]=frame
    return frames

def render(frame,frames,carry=False,size=(520,600),scale=1.6):
    out=Image.new('RGBA',size,(38,33,46,255))
    for e in reversed(frame['elements']):
        name=e['layer'].lower()
        if 'hat' in name or 'swap' in name or name=='beard' or name=='lantern_overlay':continue
        if not carry and 'carry' in name:continue
        if carry and 'normal' in name:continue
        f=frames.get((e['symbol'],e['frame']))
        if not f:continue
        im=f['image'];xoff=f['x']-im.width/2;yoff=f['y']-im.height/2
        matrix=np.array([[e['a'],e['c'],e['tx']],[e['b'],e['d'],e['ty']],[0,0,1]],dtype=float)
        offset=np.array([[scale,0,size[0]/2],[0,scale,size[1]-55],[0,0,1]],dtype=float)
        local=np.array([[1,0,xoff],[0,1,yoff],[0,0,1]],dtype=float)
        transform=offset@matrix@local
        inv=np.linalg.inv(transform)
        part=im.transform(size,Image.Transform.AFFINE,tuple(inv[:2,:].flatten()),Image.Resampling.BICUBIC)
        out.alpha_composite(part)
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='rig-preview.png');parser.add_argument('--carry',action='store_true');args=parser.parse_args()
    build=load_build(ART/'exported/klbq_kanami')
    if args.carry:build.update(load_build(ART/'exported/swap_klbq_finale'))
    anims=read_anim(read_game_zip('player_idles','anim.bin'))
    sheet=Image.new('RGBA',(1560,600),(38,33,46,255))
    for i,facing in enumerate((8,5,2)):
        anim=next(a for a in anims if a['name']=='idle_loop' and a['facing']==facing)
        im=render(anim['frames'][0],build,carry=args.carry);sheet.alpha_composite(im,(i*520,0))
    sheet.save(ART/args.output)
