"""Candidate-only native animation QA; never falls back to production artwork."""
import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
from inspect_dst_assets import read_anim, read_game_zip

ROOT = Path(__file__).resolve().parents[1]
BANKS = {'idle_loop':'player_idles', 'run_loop':'player_basic', 'eat':'player_actions_eat', 'chop_loop':'player_actions_axe', 'pickaxe_loop':'player_actions_pickaxe', 'shovel_loop':'player_actions_shovel'}
DEFAULT_ACTIONS=tuple(BANKS)
BANKS.update({name:'player_actions_feast_eat' for name in ('feast_eat_pre','feast_eat_loop','feast_eat_pst')})
BANKS.update({'dial_loop':'player_actions','refuseeat':'player_actions_eat'})
BACKGROUND = (38,33,46,255)


def add_frame(frames, symbol, number, duration, entry):
    if duration < 1:
        raise ValueError('Invalid duration')
    for n in range(number, number + duration):
        key = (symbol.lower(), n)
        if key in frames:
            raise ValueError('Overlapping sprite duration: ' + str(key))
        frames[key] = entry


def load_registration(folder):
    frames = {}
    for key, entry in json.loads((folder/'registration.json').read_text(encoding='utf8'))['frames'].items():
        symbol, number = key.rsplit('/',1)
        path = (folder/entry['image']).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError('Candidate PNG escapes source folder')
        with Image.open(path) as source:
            im = source.convert('RGBA')
        if list(im.size) != entry['canvas']:
            raise ValueError('Candidate canvas mismatch: ' + key)
        f = dict(x=entry['centre'][0], y=entry['centre'][1], w=im.width, h=im.height, image=im)
        add_frame(frames, symbol, int(number), entry['duration'], f)
    return frames


def load_exported(folder):
    frames = {}
    for symbol in ET.parse(folder/'build.xml').getroot():
        for f in symbol:
            entry = {k:float(f.get(k)) for k in ('x','y','w','h')}
            path = (folder/(f.get('image')+'.png')).resolve()
            if not path.is_relative_to(folder.resolve()):
                raise ValueError('Candidate PNG escapes source folder')
            with Image.open(path) as im:
                entry['image'] = im.convert('RGBA')
            if entry['image'].size != (entry['w'],entry['h']):
                raise ValueError('Candidate exported canvas mismatch')
            add_frame(frames, symbol.get('name'), int(f.get('framenum')), int(f.get('duration')), entry)
    return frames


def visible(element, carry, hide_hair):
    symbol, layer = element['symbol'].lower(), element['layer'].lower()
    if hide_hair and (symbol.startswith('hair') or layer.startswith('hair')):
        return False
    if symbol == 'swap_object':
        return carry
    if symbol in ('headbase_hat','hair_hat','swap_hat','beard','lantern_overlay') or symbol.startswith('swap_'):
        return False
    if 'hat' in layer or layer in ('beard','lantern_overlay'):
        return False
    if not carry and 'carry' in layer:
        return False
    if carry and 'normal' in layer:
        return False
    return True


def render_frame(frame, frames, carry=False, hide_hair=False, size=(440,480), scale=1.35, missing=None):
    out = Image.new('RGBA',size,BACKGROUND)
    offset = np.array([[scale,0,size[0]/2],[0,scale,size[1]-55],[0,0,1]],float)
    for e in reversed(frame['elements']):
        if not visible(e, carry, hide_hair):
            continue
        key = (e['symbol'].lower(),e['frame'])
        f = frames.get(key)
        if f is None:
            if missing is not None:
                missing.add(f'{key[0]}/{key[1]}')
            continue
        im = f['image']
        matrix = np.array([[e['a'],e['c'],e['tx']],[e['b'],e['d'],e['ty']],[0,0,1]],float)
        local = np.array([[1,0,f['x']-im.width/2],[0,1,f['y']-im.height/2],[0,0,1]],float)
        transform = offset @ matrix @ local
        if abs(np.linalg.det(transform)) < 1e-12:
            continue
        inv = np.linalg.inv(transform)
        out.alpha_composite(im.transform(size,Image.Transform.AFFINE,tuple(inv[:2,:].flatten()),Image.Resampling.BICUBIC))
    return out


def export_cycle(anim, frames, output, carry, hide_hair, size, scale, samples):
    facing = {8:'front',5:'side',2:'back',255:'nofaced'}.get(anim['facing'],str(anim['facing']))
    stem = f"{anim['name']}_{facing}_{'carry' if carry else 'empty'}_{'nohair' if hide_hair else 'hair'}"
    missing, rendered = set(), []
    for index, frame in enumerate(anim['frames']):
        im = render_frame(frame,frames,carry,hide_hair,size,scale,missing)
        ImageDraw.Draw(im).text((8,8),f'{stem}  {index+1}/{len(anim["frames"])}',fill='white')
        rendered.append(im.convert('RGB'))
    # GIF timing is centisecond-based; distribute rounding rather than changing FPS.
    duration = [max(10,round((i+1)*100/anim['fps'])*10-round(i*100/anim['fps'])*10) for i in range(len(rendered))]
    rendered[0].save(output/(stem+'.gif'),save_all=True,append_images=rendered[1:],duration=duration,loop=0,disposal=2,optimize=False)
    indices = sorted(set(round(i*(len(rendered)-1)/max(1,samples-1)) for i in range(samples)))
    columns = min(6,len(indices))
    sheet = Image.new('RGB',(columns*size[0],math.ceil(len(indices)/columns)*size[1]),BACKGROUND[:3])
    for n,index in enumerate(indices):
        sheet.paste(rendered[index],((n%columns)*size[0],(n//columns)*size[1]))
    sheet.save(output/(stem+'_contact.png'))
    return dict(file=stem+'.gif',frames=len(rendered),fps=anim['fps'],facing=anim['facing'],missing_visible_symbols=sorted(missing),contact_frames=indices)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--art',type=Path)
    source.add_argument('--exported',type=Path)
    parser.add_argument('--weapon-exported',type=Path,help='Explicit optional weapon; never loads an implicit production build')
    parser.add_argument('--action-zip',type=Path,help='Read the compiled candidate action bank, including head-attached expressions')
    parser.add_argument('--output',type=Path,default=Path('D:/SOFTWARE/CodexData/temp/kanami_body_v2_preview'))
    parser.add_argument('--actions',nargs='+',choices=BANKS,default=list(DEFAULT_ACTIONS))
    parser.add_argument('--mode',choices=('empty','carry','both'),default='both')
    parser.add_argument('--hair',choices=('show','hide','both'),default='both')
    parser.add_argument('--scale',type=float,default=1.35)
    parser.add_argument('--size',nargs=2,type=int,default=(440,480))
    parser.add_argument('--samples',type=int,default=12)
    args = parser.parse_args()
    folder = (args.exported or args.art or ROOT/'art/klbq_kanami/body-v2').resolve()
    metadata = folder/('build.xml' if args.exported else 'registration.json')
    frames = load_exported(folder) if args.exported else load_registration(folder)
    if args.weapon_exported:
        weapon = load_exported(args.weapon_exported.resolve())
        if any(k[0] != 'swap_object' for k in weapon):
            raise ValueError('Weapon build must contain only swap_object; cannot override body artwork')
        frames.update(weapon)
    output = args.output.resolve()
    if output.is_relative_to(ROOT/'mods') or output.is_relative_to(ROOT/'art'):
        raise ValueError('Previews must stay outside production/art source')
    output.mkdir(parents=True,exist_ok=True)
    candidate_actions=[]
    if args.action_zip:
        with zipfile.ZipFile(args.action_zip) as archive:
            candidate_actions=read_anim(archive.read('anim.bin'))
    report = dict(source=str(folder),metadata_sha256=hashlib.sha256(metadata.read_bytes()).hexdigest(),weapon=str(args.weapon_exported) if args.weapon_exported else None,
        action_zip=str(args.action_zip) if args.action_zip else None,
        action_sha256=hashlib.sha256(args.action_zip.read_bytes()).hexdigest() if args.action_zip else None,
        notes=['Native timing and pose identities retained. Connected limb dimensions, garment seams, hair depth and facial landmarks are authored.','Eat, speech and refusal have only facing=255 in the current game.','Carry without weapon-exported shows carrying pose only. Missing optional native layers are listed for review.'],cycles=[])
    for name in args.actions:
        animations = [a for a in candidate_actions if a['name']=='kanami_'+name]
        animation_source='compiled candidate' if animations else 'installed native bank'
        if not animations:
            animations = [a for a in read_anim(read_game_zip(BANKS[name],'anim.bin')) if a['name']==name]
        if not animations:
            raise ValueError('Native action missing: '+name)
        for anim in animations:
            for carry in ([False,True] if args.mode=='both' else [args.mode=='carry']):
                for hide_hair in ([False,True] if args.hair=='both' else [args.hair=='hide']):
                    result = export_cycle(anim,frames,output,carry,hide_hair,tuple(args.size),args.scale,args.samples)
                    result['animation_source']=animation_source
                    report['cycles'].append(result)
                    print(result['file'],flush=True)
    (output/'render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')


if __name__ == '__main__': main()
