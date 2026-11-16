"""Export native player contracts; copyrighted reference pixels stay in D: temp."""
import hashlib,json,struct,sys
from pathlib import Path
from PIL import Image,ImageDraw
from inspect_dst_assets import Reader,read_anim,read_game_zip,GAME

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'art/klbq_kanami/body-v2'
REFERENCE=Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')
BANKS=['player_idles','player_basic','player_actions_eat','player_actions_axe','player_actions_pickaxe','player_actions_pickaxe_recoil','player_actions_shovel']

def decode_tex(data):
    assert data[:4]==b'KTEX'
    flags,=struct.unpack_from('<I',data,4)
    fmt=(flags>>4)&31;mips=(flags>>13)&31
    width,height,pitch,count=struct.unpack_from('<HHHI',data,8)
    offset=8+10*mips
    assert fmt==2,('expected native DXT5',fmt)
    # Klei stores BC rows bottom-up; PIL decodes them in payload order.
    return Image.frombytes('RGBA',(width,height),data[offset:offset+count],'bcn',(3,'DXT5')).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def build_reference(character='wilson'):
    data=read_game_zip(character,'build.bin');r=Reader(data)
    magic,version,ns,nf=r.unpack('4sIII');assert magic==b'BILD' and version==6
    name=r.string();na,=r.unpack('I');atlases=[r.string() for _ in range(na)]
    symbols=[]
    for _ in range(ns):
        h,n=r.unpack('II');frames=[]
        for _ in range(n):
            f,d,x,y,w,height,start,count=r.unpack('IIffffII')
            frames.append(dict(frame=f,duration=d,x=x,y=y,w=w,h=height,start=start,count=count))
        symbols.append(dict(hash=h,frames=frames))
    n,=r.unpack('I');vertices=[r.unpack('ffffff') for _ in range(n)];names=r.strings()
    assert r.pos==len(data)
    textures=[decode_tex(read_game_zip(character,a)) for a in atlases]
    frames={};REFERENCE.mkdir(parents=True,exist_ok=True)
    for symbol in symbols:
        name=names[symbol['hash']]
        for f in symbol['frames']:
            w,h=round(f['w']),round(f['h']);canvas=Image.new('RGBA',(w,h))
            for i in range(f['start'],f['start']+f['count'],6):
                vs=vertices[i:i+6];atlas=textures[round(vs[0][5])];aw,ah=atlas.size
                x0=min(v[0] for v in vs);y0=min(v[1] for v in vs)
                x1=max(v[0] for v in vs);y1=max(v[1] for v in vs)
                u0=min(v[3] for v in vs);u1=max(v[3] for v in vs)
                v0=min(v[4] for v in vs);v1=max(v[4] for v in vs)
                patch=atlas.crop((round(u0*aw),round((1-v1)*ah),round(u1*aw),round((1-v0)*ah)))
                assert patch.size==(round(x1-x0),round(y1-y0)),(name,f['frame'],patch.size)
                canvas.alpha_composite(patch,(round(x0-f['x']+w/2),round(y0-f['y']+h/2)))
            filename=f'{name}_{f["frame"]}.png';canvas.save(REFERENCE/filename)
            entry={k:v for k,v in f.items() if k not in ('start','count')}
            entry.update(image_origin_pixels=[w/2-f['x'],h/2-f['y']],
                         spriter_pivot=[.5-f['x']/w,.5+f['y']/h],reference_file=filename,
                         alpha_bbox=canvas.getchannel('A').getbbox())
            frames[f'{name}/{f["frame"]}']=entry
    return frames,hashlib.sha256(data).hexdigest()

def main():
    frames,digest=build_reference();references={};missing=[]
    for bank in BANKS:
        try:anims=read_anim(read_game_zip(bank,'anim.bin'))
        except FileNotFoundError:missing.append(bank);continue
        for a in anims:
            used=sorted({f'{e["symbol"]}/{e["frame"]}' for frame in a['frames'] for e in frame['elements']})
            references[f'{bank}:{a["name"]}:{a["facing"]}']={'frames':len(a['frames']),'fps':a['fps'],'symbols':used}
    OUT.mkdir(parents=True,exist_ok=True)
    result={'game_version':(GAME/'version.txt').read_text().strip(),'build_sha256':digest,
            'basis':'Wilson build local coordinates + original player animation matrices; no pixels redistributed',
            'reference_directory':str(REFERENCE),'frames':frames,'animations':references,'missing_banks':missing}
    (OUT/'native-contract.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    wanted=['torso','torso_pelvis','arm_upper','arm_upper_skin','arm_lower','hand','leg','foot','headbase']
    rows=[(key,f) for key,f in frames.items() if key.split('/')[0] in wanted]
    cols=8;cell=170;sheet=Image.new('RGB',(cols*cell,((len(rows)+cols-1)//cols)*cell),(65,65,65));draw=ImageDraw.Draw(sheet)
    for i,(key,f) in enumerate(rows):
        im=Image.open(REFERENCE/f['reference_file']);im.thumbnail((145,135))
        x=i%cols*cell;y=i//cols*cell
        sheet.paste(im,(x+(cell-im.width)//2,y+25),im);draw.text((x+3,y+3),key,fill='white')
    sheet.save(REFERENCE/'native-contact.png')
    print(json.dumps({'symbols_and_frames':len(frames),'animations':len(references),'missing_banks':missing,'reference':str(REFERENCE)}))

if __name__=='__main__':main()
