"""Register original generated leg/shoe poses using reviewed joint anchors.

No bounding-box fitting; source cap/knee/toe anchors map to native local space.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from compare_kanami_native_body import source_frames,render
from inspect_dst_assets import read_anim,read_game_zip

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'art/klbq_kanami/body-v2'
# Coordinates within each generation cell: cap centres; bend vertices reviewed.
LEGS=[
 ([(235,75),(198,312)],[(0,-5),(-4,40)]),
 ([(190,90),(185,322)],[(-1,-6),(-4,42)]),
 ([(173,94),(174,322)],[(-2,-5),(0,44)]),
 ([(179,91),(156,323)],[(0,-5),(-7,47)]),
 ([(272,90),(241,184),(128,238)],[(1,-2),(-6,27),(-26,24)]),
 ([(186,83),(184,304)],[(-2,-6),(-4,47)]),
 ([(229,103),(114,184),(193,249)],[(-2,-6),(-15,11),(-6,31)]),
 ([(178,113),(119,230),(214,206)],[(1,-4),(-18,19),(0,13)]),
 ([(204,66),(218,193),(181,282)],[(-1,-4),(5,17),(-7,41)]),
 ([(192,56),(192,294)],[(0,-5),(-4,40)]),
 ([(174,53),(169,292)],[(0,-5),(-7,47)]),
]
# Ankle collar centre then toe centre, in corresponding cell coordinates.
FEET=[
 ([(293,130),(169,291),(340,285)],[(-3.74,8.10),(-15,22),(3,23)]),
 ([(174,129),(292,302),(126,299)],[(-3.76,9.65),(10,24),(-8,24)]),
 ([(149,145),(287,289),(128,289)],[(-1.83,8.74),(14,24),(-7,24)]),
 ([(194,140),(101,249),(208,325)],[(-3.41,13.01),(-16,26),(-3,27)]),
 ([(280,129),(156,314),(315,290)],[(-20.84,-3.75),(-40,13),(-11,10)]),
 ([(154,168),(330,241),(137,280)],[(-4.43,12.22),(22,18),(-8,22)]),
 ([(267,176),(120,165),(299,305)],[(-4.41,12.30),(-26,6),(1,24)]),
 ([(103,249),(312,199)],[(-6,10),(23,5)]),
]

def affine(source,target):
    if len(source)==2:
        s0,s1=np.array(source,float);t0,t1=np.array(target,float)
        ds=s1-s0;dt=t1-t0
        a=np.dot(ds,dt)/np.dot(ds,ds);b=(ds[0]*dt[1]-ds[1]*dt[0])/np.dot(ds,ds)
        m=np.array([[a,-b],[b,a]]);return np.column_stack([m,t0-m@s0])
    return np.linalg.solve(np.column_stack([np.array(source),np.ones(3)]),np.array(target)).T


def outline_points(image,left,top):
    opaque=np.asarray(image.getchannel('A'))>128
    padded=np.pad(opaque,1)
    inside=(padded[:-2,1:-1]&padded[2:,1:-1]&padded[1:-1,:-2]&padded[1:-1,2:])
    y,x=np.where(opaque&~inside)
    return np.column_stack((x+left,y+top)).tolist()

def main():
    contract=json.loads((ART/'native-contract.json').read_text(encoding='utf8'))['frames'];entries={}
    folder=ART/'sprites';folder.mkdir(exist_ok=True)
    fit=json.loads((ART/'joint-art/native-joint-fit.json').read_text())['ankle']['points']
    # Match ankle landmarks in the same local coordinate system on both parts.
    # The bent knee remains independently registered, as in the native sprite.
    for n,(source,target) in enumerate(LEGS[:9]):
        target[-1]=fit[f'leg/{n}']['point']
    for symbol,sourcefile,rows,anchors in [('leg','joint-art/legs-overlap-source.png',3,LEGS),('foot','joint-art/boots-overlap-source.png',2,FEET)]:
        sheet=Image.open(ART/sourcefile).convert('RGBA')
        for i,(source,target) in enumerate(anchors):
            x=i%4*sheet.width//4;y=i//4*sheet.height//rows
            im=sheet.crop((x,y,(i%4+1)*sheet.width//4,(i//4+1)*sheet.height//rows))
            part_source=sourcefile
            if symbol=='leg' and i<9:
                # Cut the stocking inside the painted fabric, before its rounded
                # outside contour. The separate boot covers this open cut edge.
                end=np.asarray(source[-1],float)
                previous=np.asarray(source[-2],float)
                yy,xx=np.indices((im.height,im.width))
                beyond=(xx-end[0])*(end[0]-previous[0])+(yy-end[1])*(end[1]-previous[1])>0
                pixels=np.array(im)
                pixels[beyond,3]=0
                im=Image.fromarray(pixels)
                # A joint is inside an overlap, not at the cut edge. Native
                # paper limbs slide slightly during their authored animations.
                direction=end-previous
                source=[list(p) for p in source]
                source[-1]=(end-direction/np.linalg.norm(direction)*24).tolist()
            m=np.vstack([affine(source,target),[0,0,1]])
            # Fixed generous local canvas includes every reviewed joint.
            left,top,width,height=(-48,-20,80,84) if symbol=='leg' else (-56,-24,96,64)
            placement=np.array([[1,0,-left],[0,1,-top],[0,0,1.]])@m
            inv=np.linalg.inv(placement)
            out=im.transform((width,height),Image.Transform.AFFINE,tuple(inv[:2,:].flatten()),Image.Resampling.BICUBIC)
            key=f'{symbol}/{i}';filename=f'sprites/{symbol}_{i}.png';out.save(ART/filename)
            entries[key]={'image':filename,'canvas':[width,height],'centre':[left+width/2,top+height/2],
                'duration':contract[key]['duration'],'original':True,
                'semantic':('ivory skeletal '+symbol if (symbol=='leg' and i>=9) or (symbol=='foot' and i==7) else 'Kanami white/pink '+symbol)+' native pose '+str(i),
                'registration_method':'reviewed hip/ankle/knee caps' if symbol=='leg' else 'reviewed ankle collar/toe axis',
                'source':part_source,'source_cell':None if part_source!=sourcefile else i,'source_anchors':source,'local_anchors':target}
            if symbol=='foot':
                box=out.getchannel('A').point(lambda alpha:255 if alpha>128 else 0).getbbox()
                entries[key]['opaque_bounds']=[left+box[0],top+box[1],left+box[2]-1,top+box[3]-1]
                native=contract[key];box=native['alpha_bbox'];ox,oy=native['image_origin_pixels']
                entries[key]['native_bounds']=[box[0]-ox,box[1]-oy,box[2]-1-ox,box[3]-1-oy]
                entries[key]['support_points']=outline_points(out,left,top)
                reference=Image.open(Path('D:/SOFTWARE/CodexData/temp/kanami_body_native')/native['reference_file']).convert('RGBA')
                entries[key]['native_support_points']=outline_points(reference,-ox,-oy)
    (ART/'registration-legs.json').write_text(json.dumps({'format':1,'frames':entries},ensure_ascii=False,indent=2),encoding='utf8')
    native,current=source_frames()
    for key,e in entries.items():
        s,n=key.split('/');native[s,int(n)]={'image':Image.open(ART/e['image']), 'x':e['centre'][0],'y':e['centre'][1],'duration':e['duration']}
    output=Path('D:/SOFTWARE/CodexData/temp/kanami_body_native');proof=Image.new('RGB',(6*240,4*380),(30,30,34));draw=ImageDraw.Draw(proof)
    for row,(bank,name) in enumerate([('player_idles','idle_loop'),('player_basic','run_loop'),('player_actions_eat','eat'),('player_actions_shovel','shovel_loop')]):
        anims=[a for a in read_anim(read_game_zip(bank,'anim.bin')) if a['name']==name]
        for col,(face,phase) in enumerate([(8,0),(8,.5),(5,0),(5,.5),(2,0),(2,.5)]):
            a=next((a for a in anims if a['facing']==face),None)
            if a is None:
                if face!=8:continue
                a=next(a for a in anims if a['facing']==255)
            idx=round((len(a['frames'])-1)*phase)
            image=render(a['frames'][idx],native,size=(240,350),scale=.7)
            proof.paste(image,(col*240,row*380+25));draw.text((col*240+5,row*380+3),f'{name} {face} frame{idx}',fill='white')
    proof.save(output/'legs-native-animation-proof.png')
    print('Registered',len(entries),'original lower limb poses; proof',output/'legs-native-animation-proof.png')

if __name__=='__main__':main()
