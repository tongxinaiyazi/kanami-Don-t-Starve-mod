"""Rebuild original hand cutouts with reviewed wrist anchors, never bbox centering.

Only mechanical crop, affine registration and resampling. Native textures are
not read or copied; native-contract supplies local coordinate metadata only.
"""
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

ART = Path(__file__).resolve().parents[1]
# source wrist (atlas coordinates), explicit scale, clockwise degrees,
# native wrist (reference canvas coordinates; None means native origin).
# 18/19 have palm pivots: registering their wrist to origin would displace them.
POSES = [
 ((139,117),.25,-14,None,'closed relaxed glove, front'),
 ((378,118),.29,16,None,'side grip with curled fingers'),
 ((628,121),.25,30,None,'angled relaxed fist'),
 ((876,117),.25,17,None,'front knuckles and thumb'),
 ((1117,122),.28,36,None,'large oblique carrying grip'),
 ((1350,145),.23,75,None,'side horizontal fist rotated at wrist into native pose'),
 ((180,357),.28,-5,None,'down-left grasping hand'),
 ((360,363),.28,0,None,'cupped upturned palm'),
 ((609,356),.27,-6,None,'spread fingers oblique down-right'),
 ((847,360),.29,-12,None,'open oblique palm'),
 ((1165,355),.29,-15,None,'spread front fingers'),
 ((1421,365),.25,-23,None,'gloved replacement of alternate closed-hand slot'),
 ((158,611),.29,-34,None,'gloved replacement of alternate grip slot'),
 ((387,590),.34,-6,None,'open frontal palm'),
 ((652,616),.32,-20,None,'closed frontal carrying fist'),
 ((896,584),.80,0,None,'cup prop; rim anchor, not a wrist'),
 ((1095,608),.28,3,None,'gloved replacement of alternate oblique open-hand slot'),
 ((1406,583),.34,-6,None,'gloved replacement of alternate frontal open-hand slot'),
 ((100,929),.43,7,(15,49),'curled grasp; native palm pivot and separate wrist anchor'),
 ((333,928),.42,2,(18,44),'side curled grasp; native palm pivot and separate wrist anchor'),
]


def main():
    source = ART/'hand-poses-source.png'
    atlas = Image.open(source).convert('RGBA')
    contract = json.loads((ART/'native-contract.json').read_text(encoding='utf8'))
    out = ART/'sprites'
    out.mkdir(exist_ok=True)
    registration = {'source':source.name, 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'method':'explicit wrist/rim anchors; source alpha preserved; no bbox centering or native pixels', 'frames':{}}
    sheet = Image.new('RGBA',(1000,800),(64,64,64,255))
    draw = ImageDraw.Draw(sheet)
    for n,(anchor,scale,degrees,native_wrist,semantic) in enumerate(POSES):
        # The atlas palms were still large next to the sleeveless rig, especially
        # when native eating squash magnified an open hand. Keep wrist pivots.
        if n!=15:
            scale*=.75 if n in (7,8,9,10,13,16,17) else .85
        cell = atlas.crop((n%6*256,n//6*256,n%6*256+256,n//6*256+256))
        # Ignore low-alpha background noise only when finding a crop. Do not
        # threshold the pixels inside the actual artwork.
        box = cell.getchannel('A').point(lambda a:255 if a>=24 else 0).getbbox()
        if box is None:
            raise ValueError('Missing original hand artwork: '+str(n))
        box = (max(0,box[0]-3),max(0,box[1]-3),min(256,box[2]+3),min(256,box[3]+3))
        cut = cell.crop(box)
        sx,sy = anchor[0]-n%6*256-box[0],anchor[1]-n//6*256-box[1]
        native = contract['frames'][f'hand/{n}']
        origin = native['image_origin_pixels']
        local_wrist = (0,0) if native_wrist is None else (native_wrist[0]-origin[0],native_wrist[1]-origin[1])
        canvas = (128,224) if n==15 else (128,128)
        pivot = (64,32) if n==15 else (64,48)
        target = (pivot[0]+local_wrist[0],pivot[1]+local_wrist[1])
        theta = math.radians(degrees)
        co,si = math.cos(theta),math.sin(theta)
        # Inverse mapping target canvas -> cropped source, with exact wrist
        # anchor invariant. The alpha channel undergoes the same affine map.
        affine = (co/scale,si/scale,sx-(co*target[0]+si*target[1])/scale,
                  -si/scale,co/scale,sy+(si*target[0]-co*target[1])/scale)
        im = cut.transform(canvas,Image.Transform.AFFINE,affine,Image.Resampling.BICUBIC)
        path = out/f'hand_{n}.png'
        im.save(path)
        registration['frames'][f'hand/{n}'] = dict(image=f'sprites/hand_{n}.png',canvas=list(canvas),centre=[canvas[0]/2-pivot[0],canvas[1]/2-pivot[1]],duration=native['duration'],semantic=semantic,original=True,source_cell=[n%6,n//6],source_crop=list(box),source_wrist_atlas=list(anchor),native_wrist_local=list(local_wrist),canvas_origin=list(pivot),scale=scale,rotation_degrees=degrees,visible_bbox=im.getchannel('A').point(lambda a:255 if a>=24 else 0).getbbox())
        preview = im.resize((canvas[0]*2,canvas[1]*2),Image.Resampling.NEAREST)
        if n==15:
            preview = im # cup is intentionally much larger than normal hands
            factor=1
        else:
            factor=2
        x=n%5*200;y=n//5*200
        sheet.alpha_composite(preview,(x+20-int(pivot[0]*factor)+80,y+25))
        px=x+100;py=y+25+pivot[1]*factor
        draw.line((px-4,py,px+4,py),fill='red');draw.line((px,py-4,px,py+4),fill='red')
        draw.text((x+5,y+5),f'hand/{n}',fill='white')
    (ART/'registration-hands.json').write_text(json.dumps(registration,ensure_ascii=False,indent=2),encoding='utf8')
    qa = Path('D:/SOFTWARE/CodexData/temp/kanami_body_v2_hands')
    qa.mkdir(parents=True,exist_ok=True)
    sheet.convert('RGB').save(qa/'registered-hands-contact.png')
    print('Registered 20 original hand frames:',out)


if __name__ == '__main__':
    main()
