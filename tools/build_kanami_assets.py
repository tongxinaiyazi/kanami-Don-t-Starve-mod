"""Compile original Kanami artwork using Klei's installed asset compiler.

Game files are read for skeleton/animation metadata only. No game texture is
copied into the mod. Source XML, PNG cutouts and Spriter project are retained.
"""
from __future__ import annotations
import argparse
import copy
import io
import json
import math
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageOps
from inspect_dst_assets import read_anim, read_build, read_game_zip, GAME

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art' / 'klbq_kanami'
MOD = ROOT / 'mods' / 'klbq_kanami'
STAGE = Path('D:/SOFTWARE/CodexData/temp/kanami_assets')
TOOLS = Path("E:/steam/steamapps/common/Don't Starve Mod Tools/mod_tools")
PY27 = TOOLS / 'buildtools/windows/Python27/python.exe'
COMPILER = TOOLS / 'tools/scripts/buildanimation.py'
CONVERTER = TOOLS / 'tools/bin/TextureConverter.exe'
RESAMPLE = Image.Resampling.LANCZOS

def trim(im):
    box = im.getchannel('A').point(lambda a:255 if a > 12 else 0).getbbox()
    return im.crop(box) if box else Image.new('RGBA', (4,4))

def image(name):
    return trim(Image.open(ART / name).convert('RGBA'))

def fit(im, size, pad=0):
    size = tuple(max(4,int(x)) for x in size)
    out = Image.new('RGBA',size)
    fitted = ImageOps.contain(im,(max(1,size[0]-pad*2),max(1,size[1]-pad*2)),RESAMPLE)
    out.alpha_composite(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2))
    return out

def facial_components(im):
    """Import the eye and mouth as separate rig layers; brows sit under bangs."""
    w,h=im.size;alpha=im.getchannel('A').tobytes();seen=bytearray(w*h);groups=[]
    for index,value in enumerate(alpha):
        if value<24 or seen[index]:continue
        todo=[index];seen[index]=1;count=0;x0=w;y0=h;x1=y1=0
        while todo:
            n=todo.pop();x,y=n%w,n//w;count+=1
            x0=min(x0,x);y0=min(y0,y);x1=max(x1,x+1);y1=max(y1,y+1)
            for k in ((n-1 if x else -1),(n+1 if x+1<w else -1),n-w,n+w):
                if 0<=k<w*h and not seen[k] and alpha[k]>=24:seen[k]=1;todo.append(k)
        groups.append((count,(x0,y0,x1,y1)))
    groups.sort(reverse=True)
    eye=groups[0][1]
    mouths=[g for g in groups[1:] if g[1][1]>=eye[3]-5 and g[0]>10]
    def crop(box):return im.crop((max(0,box[0]-2),max(0,box[1]-2),min(w,box[2]+2),min(h,box[3]+2)))
    return crop(eye),crop(max(mouths)[1]) if mouths else Image.new('RGBA',(4,4))

def xml_save(node, path):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(node)
    ET.ElementTree(node).write(path,encoding='utf-8',xml_declaration=True)

def make_parts():
    src=Image.open(ART/'parts-atlas.png').convert('RGBA')
    rois={
        'head_front':(0,0,.264,.285),'head_side':(.264,0,.505,.285),
        'head_back':(.505,0,.765,.285),'features':(.768,.065,1,.25),
        'torso_front':(0,.285,.27,.50),'torso_side':(.28,.285,.495,.50),
        'torso_back':(.50,.285,.75,.50),'pelvis':(.75,.32,1,.50),
        'upper_arm':(.045,.505,.235,.675),'lower_arm':(.28,.505,.48,.675),
        'fist':(.52,.52,.73,.68),'hand':(.78,.52,1,.68),
        'leg':(.045,.68,.225,.985),'boot':(.28,.70,.48,.94),
        'tail_left':(.50,.68,.735,.99),'tail_right':(.76,.68,1,.99),
    }
    parts={}
    folder=ART/'parts';folder.mkdir(exist_ok=True)
    for key,box in rois.items():
        part=trim(src.crop(tuple(round(v*src.width) for v in box)))
        part.save(folder/(key+'.png'))
        parts[key]=part
    src=Image.open(ART/'torso-rig-atlas.png').convert('RGBA')
    for i,direction in enumerate(('front','side','back')):
        key='rig_torso_'+direction
        part=trim(src.crop((round(i*src.width/3),0,round((i+1)*src.width/3),src.height)))
        part.save(folder/(key+'.png'));parts[key]=part
    if (ART/'faces-atlas.png').exists():
        src=Image.open(ART/'faces-atlas.png').convert('RGBA')
        for i in range(12):
            col,row=i%4,i//4
            part=trim(src.crop((round(col*src.width/4),round(row*src.height/3),
                round((col+1)*src.width/4),round((row+1)*src.height/3))))
            part.save(folder/('face_%02d.png'%i));parts['face_%02d'%i]=part
    src=Image.open(ART/'profile-faces.png').convert('RGBA')
    for i,key in enumerate(('profile_neutral','profile_angry','profile_closed','profile_hurt')):
        row,col=divmod(i,2)
        part=trim(src.crop((round(col*src.width/2),round(row*src.height/2),
            round((col+1)*src.width/2),round((row+1)*src.height/2))))
        part.save(folder/(key+'.png'));parts[key]=part
        eye,mouth=facial_components(part)
        for label,feature in (('eye',eye),('mouth',mouth)):
            name=key+'_'+label;feature.save(folder/(name+'.png'));parts[name]=feature
    src=Image.open(ART/'directional-atlas.png').convert('RGBA')
    names=('pelvis_front','pelvis_side','pelvis_back','boot_side',
        'upper_arm_straight','lower_arm_straight','fist_straight','hand_straight',
        'torso_side_clean','torso_back_clean','boot_front','boot_back')
    for i,key in enumerate(names):
        row,col=divmod(i,4)
        cuts=(0,.29,.48,.78,1) if row==0 else (0,.25,.5,.75,1)
        part=trim(src.crop((round(cuts[col]*src.width),round(row*src.height/3),
            round(cuts[col+1]*src.width),round((row+1)*src.height/3))))
        part.save(folder/(key+'.png'));parts[key]=part
    return parts

def add_frame(build,symbol,num,im,box=None,duration=1):
    node=next((s for s in build if s.get('name')==symbol),None)
    if node is None:node=ET.SubElement(build,'Symbol',name=symbol)
    if box is None:box=(0,0,im.width,im.height)
    filename='%s_%s'%(symbol,num)
    attrs=dict(framenum=str(num),duration=str(duration),x=str(box[0]),y=str(box[1]),
        w=str(im.width),h=str(im.height),image=filename)
    ET.SubElement(node,'Frame',**attrs)
    return filename+'.png',im

def compile_build(name,build,images,anims=None):
    folder=ART/'exported'/name;folder.mkdir(parents=True,exist_ok=True)
    if build is not None:xml_save(build,folder/'build.xml')
    if anims is not None:xml_save(anims,folder/'animation.xml')
    for filename,im in images.items():im.save(folder/filename)
    path=STAGE/'source'/(name+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for filename in ['build.xml','animation.xml']:
            if (folder/filename).exists():z.write(folder/filename,filename)
        for filename in images:z.write(folder/filename,filename)
    out=STAGE/'compiled';out.mkdir(exist_ok=True)
    command=[str(PY27),'-B',str(COMPILER),str(path),'--outputdir='+str(out),'--force','--scale=1','--textureformat=bc3','--platform=opengl']
    result=subprocess.run(command,cwd=STAGE,capture_output=True,text=True,errors='replace')
    (folder/'compiler.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(name+' compile failed:\n'+result.stdout[-1500:]+result.stderr[-1500:])
    compiled=out/'anim'/(name+'.zip')
    if not compiled.exists():raise FileNotFoundError(compiled)
    target=MOD/'anim'/(name+'.zip');target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(compiled,target)
    print('COMPILED',name, target.stat().st_size,flush=True)

def make_character(parts):
    original=read_build(read_game_zip('wilson','build.bin'))
    build=ET.Element('Build',name='klbq_kanami');images={}
    rig_folder=ART/'rig'
    registration=json.loads((rig_folder/'registration.json').read_text(encoding='utf-8'))['frames']
    registered_symbols={'torso','torso_pelvis','arm_upper','arm_upper_skin','arm_lower','hand','leg','foot'}
    expressions={0:0,1:2,2:4,3:0,4:1,5:3,6:3,7:1,8:8,9:9,10:11,11:6,12:5,13:11,14:1,15:7,16:0,17:2,18:4,19:8,20:0,21:6,22:0,23:11,24:9,25:11,26:7,27:4,28:8,29:11,30:0,31:5,32:6}
    for symbol in original['symbols']:
        name=symbol['name']
        for f in symbol['frames']:
            f=dict(f)
            n=f['frame'];size=(round(f['w']),round(f['h']))
            blank=Image.new('RGBA',size)
            if name in registered_symbols or name+'/'+str(n) in registration:
                # Authoring PNGs own their canvas and local origin. Never trim
                # or fit them into a vanilla drawing's bounding box: those
                # margins are part of the shoulder/elbow/wrist/ankle binding.
                entry=registration[name+'/'+str(n)]
                im=Image.open(rig_folder/entry['image']).convert('RGBA')
                size=tuple(entry['canvas'])
                if im.size!=size:
                    raise ValueError('Registered canvas changed without updating its pivot: '+name+'/'+str(n))
                f['x'],f['y']=entry['centre']
            elif name in ('headbase','headbase_hat'):
                im=fit(parts['head_side' if n==1 else 'head_back' if n==2 else 'head_front'],size)
            elif name=='face':
                profile={4:'neutral',5:'angry',6:'hurt',7:'closed',14:'closed'}.get(n)
                if profile:
                    im=Image.new('RGBA',size);w,h=size
                    eye=fit(parts['profile_'+profile+'_eye'],(round(w*.72),round(h*.48)))
                    mouth=fit(parts['profile_'+profile+'_mouth'],(max(4,round(w*.14)),max(4,round(h*.08))))
                    im.alpha_composite(eye,(round(w*.04),round(h*.35)))
                    im.alpha_composite(mouth,(round(w*.65),round(h*.80)))
                else:im=fit(parts.get('face_%02d'%expressions[n],parts['features']),size,pad=2)
                # Anime bangs occupy more of the forehead than Wilson's.
                # Place expressions in the clear skin region, below the fringe.
                f['y']+=14 if n in (4,5,6,7,14) else 28
            elif name in ('hair','hair_hat','cheeks'):im=blank
            elif name=='SWAP_ICON':im=fit(image('portrait.png'),size)
            else:im=blank
            key,value=add_frame(build,name,n,im,(f['x'],f['y'],*size),f['duration']);images[key]=value
    # A separate nape joint follows the collar. It sits behind the turning
    # head, avoiding a point-only join when the head tilts during fidgeting.
    neck=registration['klbq_neck/0']
    im=Image.open(rig_folder/neck['image']).convert('RGBA')
    if list(im.size)!=neck['canvas']:raise ValueError('Neck canvas changed without registration')
    key,value=add_frame(build,'klbq_neck',0,im,(*neck['centre'],*neck['canvas']));images[key]=value
    # The original player animation bank includes separate pigtail layers.
    # Use them rather than painting hair over torso/face layers.
    for n in range(8):
        # Keep the tail attachment behind the shoulder and clear of the feet.
        size=(84,154) if n==2 else (92,180)
        x,y=(-24,33) if n==2 else (-18 if n%2==0 else 18,45)
        im=fit(parts['tail_left' if n%2==0 else 'tail_right'],size)
        key,value=add_frame(build,'hairpigtails',n,im,(x,y,*size));images[key]=value
    compile_build('klbq_kanami',build,images)
    return build,images

def anim_xml(anims):
    root=ET.Element('Anims')
    suffix={8:'_down',5:'_side',2:'_up',255:''}
    for a in anims:
        node=ET.SubElement(root,'anim',name=a['name']+suffix.get(a['facing'],''),root=a['root'],framerate=str(int(a['fps'])))
        for f in a['frames']:
            x,y,w,h=f['box']
            frame=ET.SubElement(node,'frame',x=str(x),y=str(y),w=str(w),h=str(h))
            for i,e in enumerate(f['elements']):
                attrs=dict(name=e['symbol'],frame=str(e['frame']),layername=e['layer'],z_index=str(i))
                for k in ['a','b','c','d','tx','ty']:attrs['m_'+k]=str(e[k])
                ET.SubElement(frame,'element',**attrs)
    return root

def make_actions():
    source={name:read_anim(read_game_zip(name,'anim.bin')) for name in
        ['player_actions_slingshot','player_staff','player_revive_to_character','player_idles']}
    result=[]
    for facing in (8,5,2):
        def get(bank,name):
            return next(a for a in source[bank] if a['name']==name and a['facing'] in (facing,255))
        idle=get('player_idles','idle_loop')
        # A rifle shot uses a grounded stance. Slingshot pre/fire/lag lifts
        # the body and throws the free hand beside the face; it is not a
        # suitable body animation for this horizontal, long-barrel weapon.
        shoot=copy.deepcopy(idle);shoot['name']='kanami_shoot'
        shoot['frames']=[copy.deepcopy(idle['frames'][0]) for _ in range(17)]
        result.append(shoot)
        # Keep feet/body in one aiming pose at 8Hz. Only the weapon receives
        # a two-pixel recoil; replaying a melee swing whips the entire rig.
        burst=copy.deepcopy(idle);burst['name']='kanami_crossbow_shoot'
        pose=copy.deepcopy(idle['frames'][0]);burst['frames']=[]
        for offset in (0,-2,-1,0):
            f=copy.deepcopy(pose)
            for e in f['elements']:
                if e['symbol']=='swap_object':
                    e['a'],e['b'],e['c'],e['d']=(-1 if facing==2 else 1),0,0,1
                    e['tx']+=offset
            burst['frames'].append(f)
        result.append(burst)
        for target,count in [('kanami_string_enter',10),('kanami_string_idle',1),('kanami_string_exit',10)]:
            a=copy.deepcopy(idle);a['name']=target;a['frames']=a['frames'][:count]
            for i,f in enumerate(a['frames']):
                for e in f['elements']:
                    if e['symbol']=='hairpigtails':e['tx']+=math.sin(i/count*math.tau)*3
            result.append(a)
        cast=copy.deepcopy(get('player_staff','staff_pre'));cast['name']='kanami_cast'
        for f in cast['frames']:
            f['elements']=[e for e in f['elements'] if not e['symbol'].startswith('FX') and 'staff' not in e['symbol'].lower()]
        result.append(cast)
        revive=copy.deepcopy(get('player_revive_to_character','transform_end'));revive['name']='kanami_revive';revive['facing']=facing
        result.append(revive)
    # Native coat animation moves its broad sleeve roots around the torso.
    # Kanami's sleeveless costume has a visible shoulder socket, so move each
    # COMPLETE arm chain to that socket, preserving its relative articulation.
    # Keep unique animation names: other characters keep native player_basic.
    arm_symbols={'arm_upper','arm_upper_skin','arm_lower','arm_lower_cuff','hand','swap_object'}
    bound_sources=[a for bank,names in [('player_idles',('idle_loop','idle_inaction','idle_inaction_sanity')),('player_basic',('run_pre','run_loop','run_pst')),
                    ('player_actions_eat',('eat_pre','eat','eat_lag','quick_eat_pre','quick_eat','quick_eat_lag'))]
                   for a in read_anim(read_game_zip(bank,'anim.bin')) if a['name'] in names]
    aim_names={'kanami_shoot','kanami_crossbow_shoot'}
    bound_sources.extend(a for a in result if a['name'] in aim_names)
    result=[a for a in result if a['name'] not in aim_names]
    for source_anim in bound_sources:
        a=copy.deepcopy(source_anim)
        if not a['name'].startswith('kanami_'):a['name']='kanami_'+a['name']
        eating=source_anim['name'].startswith(('eat','quick'))
        quick=source_anim['name'].startswith('quick')
        def chain(item):
            layer=item['layer'].lower()
            if eating and not quick and layer in ('layer 221','layer 223'):
                return 'arm_normal'
            return layer if layer in ('arm_normal','arm_carry') else 'far'
        for frame in a['frames']:
            elements=frame['elements'];torso=next(e for e in elements if e['symbol']=='torso')
            roots=[e for e in elements if e['symbol']=='arm_upper'];bindings={}
            det=torso['a']*torso['d']-torso['b']*torso['c']
            for arm in roots:
                dx,dy=arm['tx']-torso['tx'],arm['ty']-torso['ty']
                local_x=(torso['d']*dx-torso['c']*dy)/det
                sx,sy=(-12,-60) if a['facing']==5 else ((-22 if local_x<0 else 22),-61)
                target=(torso['a']*sx+torso['c']*sy+torso['tx'],torso['b']*sx+torso['d']*sy+torso['ty'])
                angle=0
                # Native coat poses raise the bare arm beside this character's
                # large jaw, especially when running with the long rifle.
                # Rotate the complete chain, including its carried weapon;
                # never move only the hand or stretch a limb to hide a seam.
                lean=(math.atan2(arm['d'],arm['c'])-math.atan2(torso['d'],torso['c'])+math.pi)%math.tau-math.pi
                angle=max(-math.radians(35),min(math.radians(35),lean))-lean
                bindings[chain(arm)]=(arm['tx'],arm['ty'],target,math.cos(angle),math.sin(angle))
            for e in elements:
                if e['symbol'] not in arm_symbols:continue
                ox,oy,target,co,si=bindings[chain(e)]
                dx,dy=e['tx']-ox,e['ty']-oy
                e['tx'],e['ty']=target[0]+co*dx-si*dy,target[1]+si*dx+co*dy
                e['a'],e['b']=co*e['a']-si*e['b'],si*e['a']+co*e['b']
                e['c'],e['d']=co*e['c']-si*e['d'],si*e['c']+co*e['d']
        result.append(a)
    for a in result:
        if a['name']!='kanami_shoot':continue
        for i,frame in enumerate(a['frames']):
            recoil=-math.radians(3)*max(0,1-i/6)
            for e in frame['elements']:
                if e['symbol']=='swap_object':
                    # Rotate around the held grip, keeping the muzzle level.
                    sign=-1 if a['facing']==2 else 1
                    e['a'],e['b'],e['c'],e['d']=sign*math.cos(recoil),math.sin(recoil),-sign*math.sin(recoil),math.cos(recoil)
    # The new rear head has a real nape, rather than a hair curtain hiding
    # the neck. Vanilla's independent head bob no longer lands on this
    # costume's collar. Pin its attachment while preserving rotation and
    # moving the complete head assembly, including both animated pigtails.
    head_symbols={'headbase','headbase_hat','face','cheeks','beard','swap_face','swap_hat'}
    for a in result:
        for frame in a['frames']:
            elements=frame['elements']
            head=next((e for e in elements if e['symbol']=='headbase' and e['frame']==2),None)
            torso=next((e for e in elements if e['symbol']=='torso' and e['frame']==6),None)
            if head is None or torso is None:continue
            dx=torso['tx']-81*torso['c']-(head['tx']-5*head['a'])
            dy=torso['ty']-81*torso['d']-(head['ty']-5*head['b'])
            for e in elements:
                if e['symbol'] in head_symbols or e['symbol'].startswith('hair'):
                    e['tx']+=dx;e['ty']+=dy
            neck=dict(torso,symbol='klbq_neck',frame=0,layer='klbq_neck')
            elements.insert(max(elements.index(head),elements.index(torso))+1,neck)
    compile_build('klbq_kanami_actions',None,{},anim_xml(result))
    return result

def simple_animation(bank,symbol,name='idle',frames=1,size=(120,120),transform=None):
    fs=[]
    for i in range(frames):
        e=dict(symbol=symbol,frame=0,layer='object',a=1,b=0,c=0,d=1,tx=0,ty=0,tz=0)
        if transform:e.update(transform(i,frames))
        fs.append(dict(box=(0,0,*size),events=[],elements=[e]))
    return dict(name=name,root=bank,facing=255,fps=30,frames=fs)

def make_items():
    rifle=image('rifle.png')
    for name,file,size in [('klbq_finale','rifle.png',(240,80)),('klbq_ammo_heart','ammo-heart.png',(64,112)),
        ('klbq_ammo_fate','ammo-fate.png',(72,120)),('klbq_ammo_doom','ammo-doom.png',(80,128)),
        ('klbq_singularity','singularity.png',(112,104)),('klbq_crystal','crystal.png',(104,112)),
        ('klbq_blade','blade.png',(195,64)),('klbq_omurice','omurice.png',(112,80)),
        ('klbq_crossbow','crossbow.png',(168,112)),('klbq_requiem','requiem.png',(240,100))]:
        im=fit(image(file),size);build=ET.Element('Build',name=name)
        key,value=add_frame(build,name,0,im,(0,-size[1]/2,*size))
        compile_build(name,build,{key:value},anim_xml([simple_animation(name,name,size=size)]))
    build=ET.Element('Build',name='swap_klbq_finale');images={}
    for n in range(30):
        im=fit(rifle,(240,80));key,value=add_frame(build,'swap_object',n,im,(60,-9,240,80));images[key]=value
    compile_build('swap_klbq_finale',build,images)
    build=ET.Element('Build',name='swap_klbq_blade')
    # Original-design blade reference is horizontal, handle left. Hand bone
    # supplies in-game angles after importing the blade upright, tip above.
    im=fit(trim(image('blade.png').rotate(90,expand=True)),(60,235))
    # Native player idle/eat/attack banks request more than frame zero.
    key,value=add_frame(build,'swap_object',0,im,(0,-90,60,235),duration=30)
    compile_build('swap_klbq_blade',build,{key:value})
    build=ET.Element('Build',name='swap_klbq_crossbow')
    im=fit(image('crossbow.png'),(142,90))
    key,value=add_frame(build,'swap_object',0,im,(35,-8,142,90),duration=30)
    compile_build('swap_klbq_crossbow',build,{key:value})
    build=ET.Element('Build',name='swap_klbq_requiem')
    im=fit(trim(image('requiem.png').rotate(90,expand=True)),(108,285))
    key,value=add_frame(build,'swap_object',0,im,(0,-99,108,285),duration=30)
    compile_build('swap_klbq_requiem',build,{key:value})

def make_imprint():
    # Invariant imagegen hardware + four independent generated hologram layers.
    # Quarter-cropping, registration and state lamps are mechanical compilation.
    hardware=Image.open(ART/'imprint-hardware.png').convert('RGBA').resize((128,128),RESAMPLE)
    sheet=Image.open(ART/'imprint-projections.png').convert('RGBA')
    centers=[(362/1280,744/1280),(426/1280,758/1280),
             (489/1280,772/1280),(549/1280,785/1280)]
    specs=[('idle',0,0,60,(350/640,510/640)),('chop',1,0,90,(260/640,580/640)),
           ('mine',0,1,90,(332/640,560/640)),('dig',1,1,90,(304/640,560/640))]
    forms={};folder=ART/'imprint-forms';folder.mkdir(exist_ok=True)
    for name,col,row,size,anchor in specs:
        layer=sheet.crop((round(col*sheet.width/2),round(row*sheet.height/2),
                          round((col+1)*sheet.width/2),round((row+1)*sheet.height/2)))
        layer=layer.resize((size,size),RESAMPLE)
        canvas=Image.new('RGBA',(128,160));canvas.alpha_composite(hardware,(0,32))
        canvas.alpha_composite(layer,(round(62-anchor[0]*size),round(92-anchor[1]*size)))
        canvas.save(folder/(name+'.png'));forms[name]=canvas
    forms['idle'].save(ART/'imprint-tool.png')
    build=ET.Element('Build',name='klbq_imprint_tool');images={}
    ground=forms['idle'].resize((100,125),RESAMPLE)
    key,value=add_frame(build,'terminal',0,ground,(0,-62.5,100,125));images[key]=value
    anim=simple_animation('klbq_imprint_tool','terminal',size=(100,125))
    elements=anim['frames'][0]['elements']
    for index,name in enumerate(('chop','mine','dig','tough')):
        lamp=Image.new('RGBA',(4,4));ImageDraw.Draw(lamp).ellipse((0,0,3,3),fill='white')
        symbol='imprint_'+name;key,value=add_frame(build,symbol,0,lamp);images[key]=value
        x,y=centers[index]
        elements.append(dict(symbol=symbol,frame=0,layer=symbol,a=1,b=0,c=0,d=1,
                             tx=x*100-50,ty=(y*128+32)*125/160-125,tz=-index-1))
    compile_build('klbq_imprint_tool',build,images,anim_xml([anim]))
    build=ET.Element('Build',name='swap_klbq_imprint_tool');images={}
    for mode,source in forms.items():
        for mask in range(16):
            im=source.copy();d=ImageDraw.Draw(im)
            for index,(x,y) in enumerate(centers):
                x*=128;y=y*128+32;r=2.2
                d.ellipse((x-r,y-r,x+r,y+r),fill=(105,255,216,255) if mask&(1<<index) else (35,35,43,255))
            box=(9,-50,128,160)
            if mode=='dig':
                # Native shovel animations put the working blade below the
                # hand pivot, opposite the axe/pickaxe artwork convention.
                # Turn the complete prop around the same authored grip.
                im=im.transpose(Image.Transpose.ROTATE_180)
                box=(-9,50,128,160)
            key,value=add_frame(build,'swap_'+mode+'_'+str(mask),0,im,box,duration=30)
            images[key]=value
    compile_build('swap_klbq_imprint_tool',build,images)


def make_ghost():
    # The current player_ghost_withhat idle/angry/appear bank draws the visible
    # silhouette through ghost_tail, not the legacy ghost_body symbol.
    path=GAME/'data/anim/ghost_wilson_build.zip'
    metadata=read_build(zipfile.ZipFile(path).read('build.bin'))
    build=ET.Element('Build',name='ghost_klbq_kanami_build');images={}
    art=image('ghost.png')
    for s in metadata['symbols']:
        for f in s['frames']:
            size=(round(f['w']),round(f['h']))
            # Full original ghost art already includes face, hair and wisps.
            im=fit(art,size) if s['name']=='ghost_tail' else Image.new('RGBA',size)
            key,value=add_frame(build,s['name'],f['frame'],im,(f['x'],f['y'],*size),f['duration']);images[key]=value
    compile_build('ghost_klbq_kanami_build',build,images)

def make_paper():
    src=Image.open(ART/'paper-turnaround.png').convert('RGBA')
    cuts=[(0,0,.365,1),(.365,0,.638,1),(.638,0,1,1)]
    views=[]
    for name,cut in zip(('front','side','back'),cuts):
        part=trim(src.crop((round(cut[0]*src.width),0,round(cut[2]*src.width),src.height)))
        part.save(ART/('paper-'+name+'.png'));views.append(part)
    original=read_build(read_game_zip('wilson','build.bin'))
    build=ET.Element('Build',name='klbq_kanami_string');images={}
    for symbol in original['symbols']:
        for f in symbol['frames']:
            if symbol['name']=='torso':
                # Paper form is a front/back cutout; horizontal movement keeps
                # the complete front silhouette instead of a side illustration.
                view=2 if f['frame'] in (6,7,8) else 0
                im=fit(views[view],(230,340))
                box=(0,-130,230,340)
            else:
                im=Image.new('RGBA',(4,4));box=(0,0,4,4)
            key,value=add_frame(build,symbol['name'],f['frame'],im,box,f['duration']);images[key]=value
    for n in range(8):
        key,value=add_frame(build,'hairpigtails',n,Image.new('RGBA',(4,4)));images[key]=value
    compile_build('klbq_kanami_string',build,images)

def make_fx():
    build=ET.Element('Build',name='klbq_kanami_fx');images={}
    for symbol in ('domain','tracer','revive','sweep'):
        im=Image.new('RGBA',(512,512));d=ImageDraw.Draw(im)
        if symbol=='domain':
            # A normal-view field has a clear boundary, not a full-screen tint.
            # The principal ring's radius (236px) matches gameplay's 12 units.
            for inset,alpha,width in [(17,55,8),(20,220,3),(27,95,2)]:
                d.ellipse((inset,inset,512-inset,512-inset),outline=(226,114,228,alpha),width=width)
            d.line((252,264,252,232,274,227,274,254),fill=(255,192,236,185),width=3)
            d.ellipse((245,261,254,268),fill=(255,192,236,185));d.ellipse((267,251,276,258),fill=(255,192,236,185))
            for i in range(16):
                t=i*math.tau/16;x=256+219*math.cos(t);y=256+219*math.sin(t)
                d.polygon([(x,y-7),(x+5,y),(x,y+7),(x-5,y)],fill=(250,183,227,150))
        elif symbol=='tracer':
            d.line((20,256,490,256),fill=(255,174,211,200),width=8)
            d.line((20,256,490,256),fill=(255,248,255,255),width=2)
        elif symbol=='sweep':
            for inset,alpha,width in ((20,190,12),(33,240,5),(48,100,3)):
                d.arc((inset,inset,512-inset,512-inset),-30,285,fill=(244,220,255,alpha),width=width)
            for i in range(7):
                angle=(i*45+12)*math.pi/180;x=256+210*math.cos(angle);y=256+210*math.sin(angle)
                d.polygon([(x,y-14),(x+5,y),(x,y+14),(x-5,y)],fill=(255,199,238,210))
        else:
            for radius in (65,125,190,230):d.ellipse((256-radius,256-radius,256+radius,256+radius),outline=(211,190,255,150),width=3)
            for i in range(8):
                t=i*math.tau/8;x=256+160*math.cos(t);y=256+160*math.sin(t)
                d.polygon([(x,y-24),(x+8,y),(x,y+24),(x-8,y)],fill=(255,212,247,210))
        key,value=add_frame(build,symbol,0,im);images[key]=value
    anims=[simple_animation('klbq_kanami_fx','domain','domain',60,(512,512),lambda i,n:dict(a=1+.01*math.sin(i/n*math.tau),d=1+.01*math.sin(i/n*math.tau))),
        simple_animation('klbq_kanami_fx','tracer','tracer',8,(512,512)),
        simple_animation('klbq_kanami_fx','domain','domain_cast',30,(512,512),lambda i,n:dict(a=.15+.85*i/(n-1),d=.15+.85*i/(n-1))),
        simple_animation('klbq_kanami_fx','revive','revive',30,(512,512),lambda i,n:dict(a=.4+i/n,d=.4+i/n)),
        simple_animation('klbq_kanami_fx','sweep','sweep',15,(512,512),lambda i,n:dict(a=math.cos(i/n*math.tau),b=math.sin(i/n*math.tau),c=-math.sin(i/n*math.tau),d=math.cos(i/n*math.tau)))]
    compile_build('klbq_kanami_fx',build,images,anim_xml(anims))

def convert_tex(im,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=STAGE/'textures';tmp.mkdir(exist_ok=True)
    source=tmp/(path.stem+'.png');target=tmp/(path.stem+'.tex')
    im.save(source)
    r=subprocess.run([str(CONVERTER),'--swizzle','--format','bc3','--platform','opengl','--premultiply','--mipmap','-i',str(source),'-o',str(target)],capture_output=True,text=True,errors='replace')
    if r.returncode or not target.exists():raise RuntimeError('Texture compile failed: '+r.stdout+r.stderr)
    shutil.copy2(target,path)

def atlas(im,path,entries):
    convert_tex(im,path.with_suffix('.tex'))
    node=ET.Element('Atlas');ET.SubElement(node,'Texture',filename=path.with_suffix('.tex').name)
    elements=ET.SubElement(node,'Elements')
    for name,box in entries.items():
        x,y,w,h=box
        ET.SubElement(elements,'Element',name=name,u1=str((x+.5)/im.width),u2=str((x+w-.5)/im.width),v1=str(1-(y+h-.5)/im.height),v2=str(1-(y+.5)/im.height))
    xml_save(node,path.with_suffix('.xml'))

def skill_icon(kind):
    im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im)
    d.ellipse((5,5,123,123),fill=(28,20,39,245),outline=(224,141,206,255),width=3)
    ink=(244,207,234,255)
    if kind=='string':
        d.polygon([(61,25),(77,43),(71,77),(84,101),(48,101),(58,73),(53,47)],fill=ink)
        d.line((42,20,33,107),fill=(180,165,234,255),width=3)
    elif kind=='z':
        d.ellipse((34,24,94,84),outline=ink,width=5);d.line((64,15,64,94),fill=ink,width=3)
        d.line((25,54,103,54),fill=ink,width=3);d.line((78,80,103,105),fill=ink,width=6)
    elif kind=='x':
        d.ellipse((22,38,106,100),outline=ink,width=3);d.ellipse((39,53,89,85),outline=ink,width=2)
        d.line((65,64,65,27,86,23,86,55),fill=ink,width=5);d.ellipse((54,60,67,70),fill=ink);d.ellipse((76,51,88,61),fill=ink)
    elif kind=='echo':
        for radius in (16,30,44):d.arc((64-radius,64-radius,64+radius,64+radius),-55,55,fill=ink,width=4)
        d.polygon([(28,45),(41,64),(28,83),(15,64)],fill=ink)
    else:
        d.arc((25,25,103,103),0,290,fill=ink,width=6);d.polygon([(27,27),(49,28),(30,48)],fill=ink)
        d.line((64,42,64,84),fill=ink,width=5);d.line((43,64,85,64),fill=ink,width=5)
    return im

def make_ui():
    im=Image.new('RGBA',(1024,256));entries={}
    files=[('klbq_finale','rifle.png'),('klbq_ammo_heart','ammo-heart.png'),('klbq_ammo_fate','ammo-fate.png'),('klbq_ammo_doom','ammo-doom.png'),
        ('klbq_singularity','singularity.png'),('klbq_omurice','omurice.png'),('klbq_crystal','crystal.png'),('klbq_blade','blade.png'),('klbq_crossbow','crossbow.png'),('klbq_requiem','requiem.png'),('klbq_imprint_tool','imprint-tool.png')]
    for i,(name,file) in enumerate(files):
        x,y=(i*128,0) if i<8 else ((i-8+5)*128,128)
        # InventoryBar draws atlas regions at native pixel size. Use the same
        # 64px regions as vanilla items while preserving 128px skill icons.
        icon=fit(image(file),(64,64),6);im.alpha_composite(icon,(x+32,y+32));entries[name+'.tex']=(x+32,y+32,64,64)
    for i,key in enumerate(('string','z','x','revive','echo')):
        icon=skill_icon(key);icon.save(ART/('skill-'+key+'.png'));im.alpha_composite(icon,(i*128,128));entries['klbq_skill_'+key+'.tex']=(i*128,128,128,128)
    im.save(ART/'inventory-atlas.png');atlas(im,MOD/'images/klbq_kanami_items',entries)
    portrait=image('portrait.png');ghost=image('ghost.png')
    avatar=trim(Image.open(ART/'portrait.png').convert('RGBA').crop((0,0,1150,700)))
    silhouettes=Image.new('RGBA',portrait.size,(20,14,28,0));silhouettes.putalpha(portrait.getchannel('A'))
    targets=[('modicon',portrait,128),('images/map_icons/klbq_kanami',avatar,64),
        ('images/avatars/avatar_klbq_kanami',avatar,64),('images/avatars/avatar_ghost_klbq_kanami',ghost,64),
        ('images/avatars/self_inspect_klbq_kanami',avatar,128),('images/saveslot_portraits/klbq_kanami',portrait,128),
        ('images/selectscreen_portraits/klbq_kanami',portrait,256),('images/selectscreen_portraits/klbq_kanami_silho',silhouettes,256),
        ('bigportraits/klbq_kanami',portrait,512),('bigportraits/klbq_kanami_none',portrait,512)]
    for path,src,size in targets:
        canvas=fit(src,(size,size),2);name=Path(path).name+'.tex';atlas(canvas,MOD/path,{name:(0,0,size,size)})
    print('COMPILED UI atlases',flush=True)

def make_spriter(build,images,anims):
    root=ET.Element('spriter_data',scml_version='1.0',generator='Kanami original art pipeline',generator_version='1.0')
    folder=ET.SubElement(root,'folder',id='0',name='parts');lookup={};meta={}
    out=ART/'spriter';(out/'parts').mkdir(parents=True,exist_ok=True)
    index=0
    for s in build:
        for f in s:
            key=(s.get('name'),int(f.get('framenum')));filename=f.get('image')+'.png';im=images[filename]
            im.save(out/'parts'/filename);w,h=im.size
            ET.SubElement(folder,'file',id=str(index),name='parts/'+filename,width=str(w),height=str(h),
                pivot_x=str(.5-float(f.get('x'))/w),pivot_y=str(.5+float(f.get('y'))/h))
            lookup[key]=index;meta[key]=(w,h);index+=1
    entity=ET.SubElement(root,'entity',id='0',name='klbq_kanami')
    for ai,a in enumerate(anims):
        anim=ET.SubElement(entity,'animation',id=str(ai),name=a['name']+'_'+str(a['facing']),length=str(round(len(a['frames'])/a['fps']*1000)),looping='true' if 'idle' in a['name'] else 'false')
        main=ET.SubElement(anim,'mainline');timelines={}
        for fi,f in enumerate(a['frames']):
            k=ET.SubElement(main,'key',id=str(fi),time=str(round(fi/a['fps']*1000)));occ={}
            for e in reversed(f['elements']):
                sourcekey=(e['symbol'],e['frame'])
                if sourcekey not in lookup:continue
                ident=e['symbol']+'/'+e['layer'];occ[ident]=occ.get(ident,0)+1;ident+='/'+str(occ[ident])
                if ident not in timelines:
                    tid=len(timelines);tl=ET.SubElement(anim,'timeline',id=str(tid),name=ident,object_type='sprite');timelines[ident]=(tid,tl,0)
                tid,tl,count=timelines[ident]
                keynode=ET.SubElement(tl,'key',id=str(count),time=str(round(fi/a['fps']*1000)),spin='0')
                sx=math.hypot(e['a'],e['b']);sy=(e['a']*e['d']-e['b']*e['c'])/(sx or 1)
                ET.SubElement(keynode,'object',folder='0',file=str(lookup[sourcekey]),x=str(e['tx']),y=str(-e['ty']),angle=str(-math.degrees(math.atan2(e['b'],e['a']))),scale_x=str(sx),scale_y=str(sy))
                ET.SubElement(k,'object_ref',id=str(len(k)),timeline=str(tid),key=str(count),z_index=str(len(k)))
                timelines[ident]=(tid,tl,count+1)
    xml_save(root,out/'klbq_kanami.scml')

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',choices=['character','paper','actions','items','imprint','ghost','fx','ui','all'],default='all')
    p.add_argument('--body-v2',action='store_true',help='Build and promote the registered v2 body into source; no game deployment')
    args=p.parse_args()
    marker=ART/'body-pipeline.json'
    v2=args.body_v2 or (marker.exists() and json.loads(marker.read_text(encoding='utf8')).get('active')=='body-v2')
    STAGE.mkdir(parents=True,exist_ok=True);parts=make_parts() if not v2 and args.only in ('character','all') else None;build=images=anims=None
    if v2 and args.only in ('character','actions','all'):
        import sys
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/build_kanami_body_v2.py')],check=True)
        from promote_kanami_body_v2 import promote
        promote()
    elif args.only in ('character','all'):build,images=make_character(parts)
    if args.only in ('paper','all'):make_paper()
    if not v2 and args.only in ('actions','all'):anims=make_actions()
    if args.only in ('items','all'):make_items()
    if args.only in ('imprint','items','all'):make_imprint()
    if args.only in ('ghost','all'):make_ghost()
    if args.only in ('fx','all'):make_fx()
    if args.only in ('ui','all'):make_ui()
    if build is not None and anims is not None:make_spriter(build,images,anims)
    elif anims is not None:
        folder=ART/'exported/klbq_kanami'
        build=ET.parse(folder/'build.xml').getroot()
        images={f.get('image')+'.png':Image.open(folder/(f.get('image')+'.png')).convert('RGBA') for s in build for f in s}
        make_spriter(build,images,anims)

if __name__=='__main__':main()
