"""Check genuine compiled formats and artwork on the symbols actually animated."""
import sys, unittest, zipfile, hashlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from inspect_dst_assets import read_anim, read_build, read_game_zip

class Assets(unittest.TestCase):
 def test_imprint_shovel_blade_faces_the_native_working_end_for_every_unlock_mask(self):
  import numpy as np
  from xml.etree import ElementTree as ET
  native=read_build(read_game_zip('swap_shovel','build.bin'))['symbols'][0]['frames'][0]
  self.assertGreater(native['y'],0,'Native shovel artwork extends below its hand pivot')
  folder=ROOT/'art/klbq_kanami/exported/swap_klbq_imprint_tool'
  symbols={s.get('name'):s[0] for s in ET.parse(folder/'build.xml').getroot()}
  compiled=read_build(zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/swap_klbq_imprint_tool.zip').read('build.bin'))
  compiled={s['name']:s['frames'][0] for s in compiled['symbols']}
  for mask in range(16):
   with self.subTest(mask=mask):
    f=symbols['swap_dig_'+str(mask)]
    self.assertGreater(compiled['swap_dig_'+str(mask)]['y'],0)
    pixels=np.asarray(Image.open(folder/(f.get('image')+'.png')).convert('RGBA')).astype(float)
    local_y=np.arange(pixels.shape[0])[:,None]+float(f.get('y'))-float(f.get('h'))/2
    cyan=(pixels[:,:,1]>pixels[:,:,0]*1.15)&(pixels[:,:,2]>pixels[:,:,0]*1.15)&(pixels[:,:,3]>100)
    blade=cyan&(abs(local_y)>60)
    self.assertGreater(int(blade.sum()),10,'Missing visible projected shovel head')
    blade_y=float(np.broadcast_to(local_y,blade.shape)[blade].mean())
    self.assertGreater(blade_y,60,'Projected shovel blade points opposite the native working end')
    # The same held grip must stay at the origin after turning the prop.
    self.assertAlmostEqual(float(f.get('x'))+(128-55)-64,0)
    self.assertAlmostEqual(float(f.get('y'))+(160-130)-80,0)

 def test_rear_skull_layer_has_a_nape_beneath_continuous_hair(self):
  import numpy as np
  from render_kanami_body_v2 import load_exported
  build=load_exported(ROOT/'art/klbq_kanami/exported/klbq_kanami')
  head=build['headbase',2]['image'];pixels=np.asarray(head)
  red,green,blue,alpha=(pixels[:,:,i].astype(int) for i in range(4))
  skin=(alpha>200)&(red>green+15)&(red>blue+15)
  self.assertGreater(int(skin.sum()),20,'Rear head slot needs an anatomical nape')
  box=head.getchannel('A').getbbox()
  self.assertLess(box[3]-box[1],40,'Rear skull/nape slot must not contain a second displaced hair curtain')
  hair=build['hair',2]['image'].getchannel('A').getbbox()
  self.assertGreater(hair[3]-hair[1],200,'Rear foreground layer must contain the continuous skull and loose hair')

 def test_compiled_expression_landmarks_follow_the_head(self):
  import json,math
  registration=json.loads((ROOT/'art/klbq_kanami/body-v2/registration.json').read_text(encoding='utf8'))['frames']
  with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/klbq_kanami_actions.zip') as archive:
   animations=read_anim(archive.read('anim.bin'))
  checked=0
  for animation in animations:
   for frame in animation['frames']:
    head=next((e for e in frame['elements'] if e['symbol']=='headbase' and e['frame'] in (0,1,4)),None)
    if head is None:continue
    for face in (e for e in frame['elements'] if e['symbol']=='face'):
     entry=registration[f"face/{face['frame']}"];px,py=entry['local_eye_anchor'];hx,hy=entry['head_eye_anchor']
     actual=(face['a']*px+face['c']*py+face['tx'],face['b']*px+face['d']*py+face['ty'])
     target=(head['a']*hx+head['c']*hy+head['tx'],head['b']*hx+head['d']*hy+head['ty'])
     self.assertLess(math.dist(actual,target),.0001,(animation['name'],'face drift'))
     checked+=1
  self.assertGreater(checked,500)

 def test_body_joints_retain_native_articulation_in_ordinary_actions(self):
  native=[a for bank in ('player_basic','player_actions_eat','player_idles') for a in read_anim(read_game_zip(bank,'anim.bin'))]
  with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/klbq_kanami_actions.zip') as archive:
   compiled=read_anim(archive.read('anim.bin'))
  checked=0
  for animation in compiled:
   original=next((a for a in native if animation['name']=='kanami_'+a['name'] and animation['facing']==a['facing']),None)
   if original is None:continue
   self.assertEqual(animation['fps'],original['fps']);self.assertEqual(len(animation['frames']),len(original['frames']))
   for actual_frame,source_frame in zip(animation['frames'],original['frames']):
    source_elements=source_frame['elements']
    if animation['name'].startswith(('kanami_eat','kanami_quick_eat','kanami_feast_eat','kanami_refuseeat')):
     source_elements=[e for e in source_elements if e['symbol']!='swap_object']
    self.assertEqual(len(actual_frame['elements']),len(source_elements))
    identity=lambda e:(e['symbol'].lower(),e['frame'],e['layer'].lower())
    self.assertCountEqual([identity(e) for e in actual_frame['elements']],[identity(e) for e in source_elements])
    # Hair and arms have authored depth for the full-length hairstyle. Match
    # source tracks by identity, retaining duplicate occurrences within a track.
    source_groups={}
    for element in source_elements:source_groups.setdefault(identity(element),[]).append(element)
    for actual in actual_frame['elements']:
     source=source_groups[identity(actual)].pop(0)
     self.assertEqual((actual['symbol'].lower(),actual['frame'],actual['layer'].lower()),(source['symbol'].lower(),source['frame'],source['layer'].lower()))
     # Root/garment angular motion remains native. Limb dimensions and the
     # face basis are authored, with connected translations and sole contact.
     fields=() if actual['symbol'] in ('face','arm_upper','arm_lower','hand','leg','foot','torso','torso_pelvis') else ('a','b','c','d')
     for key in fields:self.assertAlmostEqual(actual[key],source[key],places=5,msg=(animation['name'],actual['symbol'],key))
   checked+=1
  self.assertEqual(checked,25)

 def test_registered_body_canvases_are_not_trimmed_or_refitted(self):
  import json
  from render_kanami_rig import load_build
  folder=ROOT/'art/klbq_kanami/body-v2'
  layout=json.loads((folder/'registration.json').read_text(encoding='utf8'))['frames']
  built=load_build(ROOT/'art/klbq_kanami/exported/klbq_kanami')
  for key,entry in layout.items():
   symbol,n=key.split('/');f=built[symbol,int(n)]
   original=Image.open(folder/entry['image']).convert('RGBA')
   self.assertEqual(list(original.size),entry['canvas'],key)
   self.assertEqual(f['image'].tobytes(),original.tobytes(),key)
   self.assertEqual([f['x'],f['y']],entry['centre'],key)

 def test_upper_arm_skin_does_not_duplicate_the_clothed_arm(self):
  from render_kanami_rig import load_build
  build=load_build(ROOT/'art/klbq_kanami/exported/klbq_kanami')
  for (name,n),f in build.items():
   if name=='arm_upper_skin':
    self.assertIsNone(f['image'].getchannel('A').getbbox(),('duplicate upper arm',n))

 def test_survival_poses_have_no_visible_joint_gaps(self):
  import json
  from render_kanami_body_v2 import load_exported
  from check_kanami_joint_poses import audit
  build=load_exported(ROOT/'art/klbq_kanami/exported/klbq_kanami')
  with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/klbq_kanami_actions.zip') as archive:
   animations=read_anim(archive.read('anim.bin'))
  layout=json.loads((ROOT/'art/klbq_kanami/body-v2/registration.json').read_text(encoding='utf8'))['frames']
  report,_=audit(build,layout,animations,all_actions=True)
  self.assertGreater(report['checked'],29000)
  self.assertEqual(set(report['counts']),{'neck','shoulder','elbow','wrist','hip','ankle','waist'})
  self.assertEqual(report['issues'],[],str(report['issues'][:20]))

 def test_boot_cuffs_and_hands_use_their_native_pose_contracts(self):
  import json
  from render_kanami_rig import load_build
  frames=load_build(ROOT/'art/klbq_kanami/exported/klbq_kanami')
  layout=json.loads((ROOT/'art/klbq_kanami/body-v2/registration.json').read_text(encoding='utf8'))['frames']
  for n in range(8):
   entry=layout['foot/'+str(n)];ax,ay=entry['local_anchors'][0]
   frame=frames['foot',n];alpha=frame['image'].getchannel('A')
   x=round(frame['w']/2-frame['x']+ax);y=round(frame['h']/2-frame['y']+ay)
   self.assertTrue(alpha.crop((x-3,y-3,x+4,y+4)).getbbox(),('missing ankle opening',n))
  native=next(s['frames'] for s in read_build(read_game_zip('wilson','build.bin'))['symbols'] if s['name']=='hand')
  for reference in native:
   number=reference['frame'];box=frames['hand',number]['image'].getchannel('A').getbbox()
   self.assertLessEqual(box[3]-box[1],reference['h'],('hand exceeds its native pose envelope',number))

 def test_crossbow_burst_keeps_native_standing_body_and_hand_anchor(self):
  import math
  with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/klbq_kanami_actions.zip') as z:
   bound=read_anim(z.read('anim.bin'))
   bursts=[a for a in bound if a['name']=='kanami_crossbow_shoot']
  self.assertEqual(len(bursts),3)
  for a in bursts:
   idle=next(v for v in bound if v['name']=='kanami_idle_loop' and v['facing']==a['facing'])['frames'][0]
   # Compiled symbol names are case-insensitive hashes; the local reader's
   # reverse-name registry can resolve an uppercase native name in lowercase.
   body=lambda f:[dict(e,symbol=e['symbol'].lower(),layer=e['layer'].lower())
                  for e in f['elements'] if e['symbol']!='swap_object']
   anchor=next(e for e in idle['elements'] if e['symbol']=='swap_object')
   for f in a['frames']:
    self.assertEqual(body(f),body(idle),a['facing'])
    weapon=next(e for e in f['elements'] if e['symbol']=='swap_object')
    self.assertLessEqual(math.dist((weapon['tx'],weapon['ty']),(anchor['tx'],anchor['ty'])),2.001)

 def test_rifle_fire_keeps_a_grounded_pose_and_recoils_about_the_grip(self):
  with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim/klbq_kanami_actions.zip') as z:
   animations=read_anim(z.read('anim.bin'))
  shots=[a for a in animations if a['name']=='kanami_shoot']
  self.assertEqual(len(shots),3)
  for shot in shots:
   idle=next(a for a in animations if a['name']=='kanami_idle_loop' and a['facing']==shot['facing'])['frames'][0]
   self.assertEqual(len(shot['frames']),17)
   for f in shot['frames']:
    for e,standing in zip(f['elements'],idle['elements']):
     if e['symbol']=='swap_object':
      self.assertEqual((e['tx'],e['ty']),(standing['tx'],standing['ty']))
     else:self.assertEqual(e,standing,('shot moves body instead of weapon',shot['facing'],e['symbol']))

 def test_all_held_weapons_cover_native_idle_and_eating_symbol_frames(self):
  needed=set()
  for bank in ('player_idles','player_actions_eat'):
   for a in read_anim(read_game_zip(bank,'anim.bin')):
    if a['name'] not in ('idle_loop','eat','quickeat'):continue
    needed.update(e['frame'] for f in a['frames'] for e in f['elements'] if e['symbol']=='swap_object')
  self.assertTrue(needed)
  for name in ('blade','crossbow','requiem'):
   with zipfile.ZipFile(ROOT/'mods/klbq_kanami/anim'/('swap_klbq_'+name+'.zip')) as z:
    frames=next(s['frames'] for s in read_build(z.read('build.bin'))['symbols'] if s['name']=='swap_object')
   for frame in needed:
    self.assertTrue(any(f['frame']<=frame<f['frame']+f['duration'] for f in frames),(name,frame))
 def test_backpack_and_ammo_inventory_regions_use_native_sixty_four_pixels(self):
  from xml.etree import ElementTree as ET
  atlas=ET.parse(ROOT/'mods/klbq_kanami/images/klbq_kanami_items.xml')
  for key in ('klbq_singularity','klbq_ammo_heart','klbq_ammo_fate','klbq_ammo_doom','klbq_imprint_tool'):
   entry=next(e for e in atlas.findall('.//Element') if e.get('name')==key+'.tex')
   width=(float(entry.get('u2'))-float(entry.get('u1')))*1024+1
   height=(float(entry.get('v2'))-float(entry.get('v1')))*256+1
   self.assertAlmostEqual(width,64);self.assertAlmostEqual(height,64)
 def test_paper_uses_front_for_sides_and_distinct_back(self):
  anims=read_anim(read_game_zip('player_idles','anim.bin'))
  folder=ROOT/'art/klbq_kanami/exported/klbq_kanami_string'
  hashes=[]
  for facing in (8,5,2):
   idle=next(a for a in anims if a['name']=='idle_loop' and a['facing']==facing)
   torso=next(e for e in idle['frames'][0]['elements'] if e['symbol']=='torso')
   im=Image.open(folder/('torso_'+str(torso['frame'])+'.png')).convert('RGBA')
   self.assertTrue(im.getchannel('A').getbbox())
   hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
  self.assertEqual(hashes[0],hashes[1],'Side movement must keep the front paper view')
  self.assertNotEqual(hashes[0],hashes[2],'The rear paper view must remain distinct')
 def test_runtime_animation_archives_contain_compiled_binary(self):
  for path in (ROOT/'mods/klbq_kanami/anim').glob('*.zip'):
   with self.subTest(path=path.name),zipfile.ZipFile(path) as archive:
    for member,magic in [('build.bin',b'BILD'),('anim.bin',b'ANIM')]:
     if member in archive.namelist():self.assertEqual(archive.read(member)[:4],magic)
    self.assertTrue('build.bin' in archive.namelist() or 'anim.bin' in archive.namelist())
 def test_ghost_idle_has_visible_original_art(self):
  idle=next(a for a in read_anim(read_game_zip('player_ghost_withhat','anim.bin')) if a['name']=='idle')
  folder=ROOT/'art/klbq_kanami/exported/ghost_klbq_kanami_build'
  for frame in idle['frames']:
   visible=False
   for element in frame['elements']:
    path=folder/(element['symbol']+'_'+str(element['frame'])+'.png')
    if path.exists() and Image.open(path).convert('RGBA').getchannel('A').getbbox():visible=True
   self.assertTrue(visible,'Every idle frame needs visible artwork on an animated symbol')

if __name__=='__main__':unittest.main(verbosity=2)
