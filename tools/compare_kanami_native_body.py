"""Diagnostic only: same original matrices, native build versus current Kanami."""
import json,math
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from audit_kanami_body import ROOT,REFERENCE,OUT
from inspect_dst_assets import read_anim,read_game_zip

def source_frames():
    contract=json.loads((OUT/'native-contract.json').read_text(encoding='utf8'))
    native={}
    for key,f in contract['frames'].items():
        name,num=key.split('/');native[name.lower(),int(num)]=dict(f,image=Image.open(REFERENCE/f['reference_file']).convert('RGBA'))
    current={}
    folder=ROOT/'art/klbq_kanami/exported/klbq_kanami'
    for symbol in ET.parse(folder/'build.xml').getroot():
        for f in symbol:
            current[symbol.get('name').lower(),int(f.get('framenum'))]={**{k:float(f.get(k)) for k in ['x','y','w','h']},'duration':int(f.get('duration')),'image':Image.open(folder/(f.get('image')+'.png')).convert('RGBA')}
    return native,current

def lookup(frames,symbol,number):
    return next((f for (name,n),f in frames.items() if name==symbol.lower() and n<=number<n+f['duration']),None)

def render(frame,frames,carry=False,size=(320,520),scale=.7):
    out=Image.new('RGBA',size,(53,54,61,255))
    for e in sorted(frame['elements'],key=lambda e:e['tz'],reverse=True):
        layer=e['layer'].lower();symbol=e['symbol'].lower()
        if 'hat' in layer or layer.startswith('swap') or symbol.startswith('swap') or layer in ['beard','lantern_overlay']:continue
        if layer=='arm_carry' and not carry or layer=='arm_normal' and carry:continue
        f=lookup(frames,symbol,e['frame'])
        if f is None:continue
        im=f['image'];matrix=np.array([[e['a'],e['c'],e['tx']],[e['b'],e['d'],e['ty']],[0,0,1.]])
        origin=np.array([[1,0,f['x']-im.width/2],[0,1,f['y']-im.height/2],[0,0,1.]])
        screen=np.array([[scale,0,size[0]/2],[0,scale,size[1]-25],[0,0,1.]])
        inv=np.linalg.inv(screen@matrix@origin)
        out.alpha_composite(im.transform(size,Image.Transform.AFFINE,tuple(inv[:2,:].flatten()),Image.Resampling.BICUBIC))
    return out

def main():
    native,current=source_frames()
    specs=[('idle','player_idles','idle_loop',False),('run','player_basic','run_loop',False),('eat','player_actions_eat','eat',False),('chop','player_actions_axe','chop_loop',True),('mine','player_actions_pickaxe','pickaxe_loop',True),('dig','player_actions_shovel','shovel_loop',True)]
    overview=Image.new('RGB',(1920,6*545),(30,30,36));od=ImageDraw.Draw(overview)
    for row,(label,bank,name,carry) in enumerate(specs):
        anims=[a for a in read_anim(read_game_zip(bank,'anim.bin')) if a['name']==name]
        sheet=Image.new('RGB',(1920,3*545),(30,30,36));d=ImageDraw.Draw(sheet)
        for col,face in enumerate([8,5,2]):
            a=next((a for a in anims if a['facing']==face),None)
            if a is None:
                if col:continue
                a=next(a for a in anims if a['facing']==255)
            for sample in range(3):
                number=round((len(a['frames'])-1)*sample/2);frame=a['frames'][number]
                for side,build in enumerate([native,current]):
                    img=render(frame,build,carry);x=col*640+side*320;y=sample*545
                    sheet.paste(img,(x,y+25));d.text((x+5,y+5),f'{label} f{a["facing"]} frame{number} '+('Wilson' if side==0 else 'Kanami-native'),fill='white')
                    if sample==1:
                        overview.paste(img,(x,row*545+25));od.text((x+5,row*545+5),f'{label} f{a["facing"]} '+('Wilson' if side==0 else 'Kanami-native'),fill='white')
        sheet.save(REFERENCE/(label+'-native-comparison.png'))
    overview.save(REFERENCE/'native-comparison-overview.png')
    print(REFERENCE/'native-comparison-overview.png')

if __name__=='__main__':main()
