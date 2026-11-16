"""Compile registered artwork, joint-connected poses and head-attached expressions.

All outputs are candidates in D: temp. This tool never deploys to a mod folder.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
import numpy as np
from calibrate_kanami_face import matrix,neutral_face_bases
from inspect_dst_assets import read_anim, read_game_zip
from build_kanami_assets import anim_xml, xml_save, PY27, COMPILER
from retarget_kanami_body import attach_body_joints

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art/klbq_kanami/body-v2'
STAGE = Path('D:/SOFTWARE/CodexData/temp/kanami_body_v2_candidate')
BODY = {'torso', 'torso_pelvis', 'arm_upper', 'arm_upper_skin', 'arm_lower', 'hand', 'leg', 'foot', 'headbase', 'headbase_hat'}


def registered_build(folder, registration, contract):
    entries = registration['frames']
    missing = set(contract['frames']) - set(entries)
    if missing:
        raise ValueError('missing native frames: ' + ', '.join(sorted(missing)))
    build = ET.Element('Build', name='klbq_kanami')
    images, nodes, seen = {}, {}, {}
    for key, entry in entries.items():
        symbol, number = key.rsplit('/', 1)
        number = int(number)
        if not symbol.replace('_', '').isalnum() or number < 0:
            raise ValueError('invalid symbol/frame: ' + key)
        native = contract['frames'].get(key)
        duration = entry['duration']
        if not isinstance(duration, int) or duration < 1 or (native and duration != native['duration']):
            raise ValueError('duration differs from native contract: ' + key)
        if entry.get('original') is not True or not entry.get('semantic', '').strip():
            raise ValueError('original artwork and explicit semantic required: ' + key)
        path = (folder / entry['image']).resolve()
        if not path.is_relative_to(folder.resolve()) or path.suffix.lower() != '.png':
            raise ValueError('PNG must be inside body-v2: ' + key)
        with Image.open(path) as source:
            im = source.convert('RGBA')
        if list(im.size) != entry['canvas']:
            raise ValueError('canvas mismatch: ' + key)
        centre = entry['centre']
        if len(centre) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in centre):
            raise ValueError('invalid centre: ' + key)
        empty = im.getchannel('A').getbbox() is None
        covered_skin = (symbol == 'arm_upper_skin' and entry.get('covered_by') == 'arm_upper'
                        and any(k.startswith('arm_upper/') for k in entries))
        if empty and ((symbol in BODY and not covered_skin) or not entry.get('intentional_empty') or not entry.get('reason')):
            raise ValueError('empty artwork without allowed explicit omission: ' + key)
        digest = hashlib.sha256(im.tobytes() + str(im.size).encode()).hexdigest()
        # Distinct poses require independent art unless a reviewed reason is recorded.
        if not empty and digest in seen and seen[digest].split('/')[0] == symbol and not entry.get('shared_pose_reason'):
            raise ValueError('duplicate pose artwork: ' + key + ' and ' + seen[digest])
        seen[digest] = key
        node = nodes.get(symbol)
        if node is None:
            node = nodes[symbol] = ET.SubElement(build, 'Symbol', name=symbol)
        filename = f'{symbol}_{number}'
        ET.SubElement(node, 'Frame', framenum=str(number), duration=str(duration), x=str(centre[0]), y=str(centre[1]), w=str(im.width), h=str(im.height), image=filename)
        images[filename + '.png'] = im
    return build, images


def attach_face_to_head(frame, registration, face_bases=None):
    """Parent the authored eye landmark to the shorter anime face opening."""
    head=next((e for e in frame['elements'] if e['symbol']=='headbase' and e['frame'] in (0,1,4)),None)
    if head is None:
        return
    for element in frame['elements']:
        if element['symbol']!='face':
            continue
        entry=registration[f"face/{element['frame']}"]
        view=1 if head['frame']==1 else 0
        if face_bases and view in face_bases:
            linear=matrix(head)[:2,:2]@face_bases[view]
            element['a'],element['c']=map(float,linear[0])
            element['b'],element['d']=map(float,linear[1])
        px,py=entry['local_eye_anchor']
        hx,hy=entry['head_eye_anchor']
        element['tx']=head['a']*hx+head['c']*hy+head['tx']-element['a']*px-element['c']*py
        element['ty']=head['b']*hx+head['d']*hy+head['ty']-element['b']*px-element['d']*py


def make_actions(loader=None, registration=None):
    """Retain native articulation and bind the replacement's anatomical joints."""
    if loader is None:
        loader = lambda bank: read_anim(read_game_zip(bank, 'anim.bin'))
    sources = {bank: loader(bank) for bank in ('player_idles', 'player_basic', 'player_actions_eat', 'player_actions_feast_eat', 'player_staff', 'player_revive_to_character',
        'player_actions_axe','player_actions_pickaxe','player_actions_pickaxe_recoil','player_actions_shovel',
        'player_tiptoe','player_groggy','player_attacks','player_attacks_recoil','player_actions_item','player_actions')}
    result = []
    wanted = {'player_idles': ('idle_loop', 'idle_inaction', 'idle_inaction_sanity'), 'player_basic': ('run_pre', 'run_loop', 'run_pst'), 'player_actions_eat': ('eat_pre', 'eat', 'eat_lag', 'quick_eat_pre', 'quick_eat', 'quick_eat_lag','refuseeat'),
        'player_actions_feast_eat': ('feast_eat_pre_pre','feast_eat_pre','feast_eat_loop','feast_eat_pst','feast_eat_lag'),
        'player_actions_axe':('chop_pre','chop_loop','chop_lag'),
        'player_actions_pickaxe':('pickaxe_pre','pickaxe_loop','pickaxe_lag','pickaxe_pst'),
        'player_actions_pickaxe_recoil':('pickaxe_recoil',),
        'player_actions_shovel':('shovel_pre','shovel_loop','shovel_lag','shovel_pst'),
        'player_tiptoe':('careful_walk_pre','careful_walk','careful_walk_pst'),
        'player_groggy':('idle_walk_pre','idle_walk','idle_walk_pst'),
        'player_actions_item':('pickup','pickup_lag','pickup_pst'),
        'player_actions':('hit','dial_loop'),
        'player_attacks':('atk_pre','atk','atk_lag','punch','toolpunch','spearjab_pre','spearjab','spearjab_lag'),
        'player_attacks_recoil':('atk_recoil',)}
    for bank, names in wanted.items():
        for native in sources[bank]:
            if native['name'] in names:
                anim = copy.deepcopy(native)
                anim['name'] = 'kanami_' + anim['name']
                result.append(anim)
    for facing in (8, 5, 2):
        def get(bank, name):
            return copy.deepcopy(next(a for a in sources[bank] if a['name'] == name and a['facing'] in (facing, 255)))
        idle = get('player_idles', 'idle_loop')
        for name, count in (('kanami_shoot', 17), ('kanami_crossbow_shoot', 4), ('kanami_string_enter', 10), ('kanami_string_idle', 1), ('kanami_string_exit', 10)):
            anim = copy.deepcopy(idle)
            anim['name'] = name
            anim['frames'] = [copy.deepcopy(idle['frames'][i % len(idle['frames'])] if 'string' in name else idle['frames'][0]) for i in range(count)]
            for i, frame in enumerate(anim['frames']):
                for e in frame['elements']:
                    if e['symbol'] != 'swap_object' or 'string' in name:
                        continue
                    sign = -1 if facing == 2 else 1
                    recoil = -math.radians(3) * max(0, 1-i/6) if name == 'kanami_shoot' else 0
                    e['a'], e['b'], e['c'], e['d'] = sign*math.cos(recoil), math.sin(recoil), -sign*math.sin(recoil), math.cos(recoil)
                    if name == 'kanami_crossbow_shoot':
                        e['tx'] += (0, -2, -1, 0)[i]
            result.append(anim)
        cast = get('player_staff', 'staff_pre')
        cast['name'] = 'kanami_cast'
        for frame in cast['frames']:
            frame['elements'] = [e for e in frame['elements'] if not e['symbol'].startswith('FX') and 'staff' not in e['symbol'].lower()]
        if not any(a['name']==cast['name'] and a['facing']==cast['facing'] for a in result):
            result.append(cast)
        revive = get('player_revive_to_character', 'transform_end')
        revive['name'], revive['facing'] = 'kanami_revive', facing
        result.append(revive)
    if registration is None:
        registration=json.loads((ART/'registration.json').read_text(encoding='utf8'))['frames']
    face_bases=neutral_face_bases(sources['player_idles'])
    for animation in result:
        for frame in animation['frames']:
            if animation['name'].startswith(('kanami_eat','kanami_quick_eat','kanami_feast_eat','kanami_refuseeat')):
                # Inventory food use may be server-driven while the owning
                # client's SG stays idle. An absent weapon track also covers
                # that path, independent of local visibility/prediction flags.
                frame['elements']=[e for e in frame['elements'] if e['symbol']!='swap_object']
            normal_arms=animation['name'].startswith(('kanami_chop_','kanami_pickaxe_','kanami_shovel_',
                'kanami_eat','kanami_quick_eat','kanami_feast_eat','kanami_refuseeat','kanami_revive','kanami_punch','kanami_pickup','kanami_hit'))
            attach_body_joints(frame,registration,weapon_carry=not normal_arms)
            attach_face_to_head(frame,registration,face_bases)
    return result


def compile_candidate(stage, name, build=None, images=None, animations=None):
    folder = stage / 'exported' / name
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for filename, node in (('build.xml', build), ('animation.xml', animations)):
        if node is not None:
            xml_save(node, folder / filename)
            files.append(filename)
    for filename, im in (images or {}).items():
        im.save(folder / filename)
        files.append(filename)
    source = stage / 'source' / (name + '.zip')
    source.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename in files:
            archive.write(folder / filename, filename)
    output = stage / 'compiled'
    output.mkdir(exist_ok=True)
    run = subprocess.run([str(PY27), '-B', str(COMPILER), str(source), '--outputdir=' + str(output), '--force', '--scale=1', '--textureformat=bc3', '--platform=opengl'], cwd=stage, capture_output=True, text=True, errors='replace')
    (folder / 'compiler.log').write_text(run.stdout + run.stderr, encoding='utf8')
    target = output / 'anim' / (name + '.zip')
    if run.returncode or not target.exists():
        raise RuntimeError('candidate compiler failed; see ' + str(folder / 'compiler.log'))
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art', type=Path, default=ART)
    parser.add_argument('--stage', type=Path, default=STAGE)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--actions-only', action='store_true')
    args = parser.parse_args()
    stage = args.stage.resolve()
    if stage.is_relative_to(ROOT / 'mods') or stage.is_relative_to(ROOT / 'art'):
        raise ValueError('candidate stage must be separate from production and artwork')
    outputs = []
    if not args.actions_only:
        contract = json.loads((args.art / 'native-contract.json').read_text(encoding='utf8'))
        registration = json.loads((args.art / 'registration.json').read_text(encoding='utf8'))
        build, images = registered_build(args.art, registration, contract)
        if not args.validate_only:
            outputs.append(str(compile_candidate(stage, 'klbq_kanami', build, images)))
    if not args.validate_only:
        outputs.append(str(compile_candidate(stage, 'klbq_kanami_actions', animations=anim_xml(make_actions()))))
        if not args.actions_only:
            from promote_kanami_body_v2 import record_candidate
            record_candidate(stage, args.art)
    print(json.dumps({'validated': True, 'candidate_outputs': outputs}, ensure_ascii=False))


if __name__ == '__main__':
    main()
