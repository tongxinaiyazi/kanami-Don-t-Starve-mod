"""Regression gates for anatomical joints, independent of hair occlusion."""
import copy
import json
import unittest
import numpy as np
from calibrate_kanami_face import matrix
from retarget_kanami_body import anchor, local_anchor, support_height
from check_kanami_joint_poses import region_mask

from build_kanami_body_v2 import make_actions
from check_kanami_joint_poses import ART, audit, joint_pairs, check_pair
from inspect_dst_assets import read_anim, read_game_zip
from render_kanami_body_v2 import load_registration, visible


class JointRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout=json.loads((ART/'registration.json').read_text(encoding='utf8'))['frames']
        cls.frames=load_registration(ART)
        cls.actions=make_actions()
        cls.idle=next(a for a in cls.actions if a['name']=='kanami_idle_loop' and a['facing']==8)['frames'][0]

    def test_all_seven_joint_types_through_complete_cycles(self):
        report,_=audit(self.frames,self.layout,self.actions,all_actions=True)
        self.assertGreater(report['checked'],29000)
        self.assertEqual(set(report['counts']),{'neck','shoulder','elbow','wrist','waist','hip','ankle'})
        self.assertEqual(report['issues'],[],str(report['issues'][:10]))

    def assert_hands_visible(self,frame):
        elements=frame['elements']
        hands=[(i,e) for i,e in enumerate(elements) if e['symbol']=='hand' and visible(e,True,False)]
        self.assertEqual(len(hands),2)
        for index,hand in hands:
            entry=self.frames['hand',hand['frame']]
            box=entry['image'].getchannel('A').getbbox()
            local=[(box[0]+box[2])/2+entry['x']-entry['w']/2,
                   (box[1]+box[3])/2+entry['y']-entry['h']/2,1.]
            centre=(matrix(hand)@local)[:2]
            painted=region_mask(hand,self.frames,centre,20)
            covering=np.zeros(painted.shape,bool)
            for other in elements[:index]:
                if visible(other,True,False) and (other['symbol'],other['frame']) in self.frames:
                    covering|=region_mask(other,self.frames,centre,20)
            ratio=float((painted&~covering).sum())/max(1,int(painted.sum()))
            self.assertGreater(ratio,.3,('hand hidden behind hair or costume',hand['layer'],ratio))

    def test_front_carrying_hands_remain_visible_with_full_hair(self):
        self.assert_hands_visible(self.idle)

    def test_waist_edges_share_the_same_complete_attachment_line(self):
        for animation in self.actions:
            for frame in animation['frames']:
                torso=next((e for e in frame['elements'] if e['symbol']=='torso'),None)
                pelvis=next((e for e in frame['elements'] if e['symbol']=='torso_pelvis'),None)
                if not torso or not pelvis:continue
                entry=self.layout[f"torso/{torso['frame']}"]
                if 'waist_edges' not in entry:continue
                skirt=self.layout[f"torso_pelvis/{pelvis['frame']}"]
                skirt_edges=skirt.get('waist_edges',[local_anchor(skirt,0),local_anchor(skirt,1)])
                for i,point in enumerate(entry['waist_edges']):
                    actual=(matrix(pelvis)@np.r_[skirt_edges[i],1.])[:2]
                    expected=(matrix(torso)@np.r_[point,1.])[:2]
                    self.assertLess(np.linalg.norm(actual-expected),.1,(animation['name'],torso['frame'],i))

    def test_actual_joint_gap_is_detected_despite_full_hair(self):
        for symbol,joint in [('headbase','neck'),('foot','ankle'),('arm_upper','shoulder'),('leg','hip'),('torso_pelvis','waist')]:
            with self.subTest(joint=joint):
                frame=copy.deepcopy(self.idle)
                child=next(e for e in frame['elements'] if e['symbol']==symbol)
                child['ty']+=22
                elements=[e for e in frame['elements'] if visible(e,False,True)]
                matches=[pair for pair in joint_pairs(elements,self.layout) if pair[0]==joint and pair[2] is child]
                self.assertTrue(matches)
                for name,p,c,pp,cp in matches:
                    error,_=check_pair(p,c,pp,cp,self.frames,name)
                    self.assertIsNotNone(error,'An unrelated silhouette must not hide a broken joint')

    def test_skirt_contains_clothing_and_no_thigh_skin(self):
        import numpy as np
        for n in range(10):
            with self.subTest(pelvis=n):
                pixels=np.asarray(self.frames['torso_pelvis',n]['image']).astype(int)
                red,green,blue,alpha=(pixels[:,:,i] for i in range(4))
                skin=(alpha>200)&(red>150)&(green>100)&(red-green>15)&(red-green<90)&(green-blue>5)&(green-blue<60)
                self.assertLessEqual(int(skin.sum()),2,'Thigh skin belongs to the separately animated leg')

    def test_bent_torso_shoulders_are_registered_beside_the_neck(self):
        import numpy as np
        entry=self.layout['torso/9']
        neck=np.asarray(entry['neck_anchor'])
        self.assertEqual(len(entry['shoulder_anchors']),2)
        for shoulder in entry['shoulder_anchors']:
            self.assertLess(np.linalg.norm(np.asarray(shoulder)-neck),30,
                'Crescent waist tips must not become shoulder sockets')
        self.assertLess(self.layout['torso_pelvis/9']['waist_anchor'][0],neck[0])

    def test_weapon_follows_hand_without_changing_its_grip_offset(self):
        native=next(a for a in read_anim(read_game_zip('player_idles','anim.bin')) if a['name']=='idle_loop' and a['facing']==8)['frames'][0]
        old_hand=next(e for e in native['elements'] if e['symbol']=='hand' and e['layer'].lower()=='arm_carry')
        new_hand=next(e for e in self.idle['elements'] if e['symbol']=='hand' and e['layer'].lower()=='arm_carry')
        old_weapon=next(e for e in native['elements'] if e['symbol']=='swap_object')
        new_weapon=next(e for e in self.idle['elements'] if e['symbol']=='swap_object')
        old_grip=np.linalg.solve(matrix(old_hand),[old_weapon['tx'],old_weapon['ty'],1])
        new_grip=np.linalg.solve(matrix(new_hand),[new_weapon['tx'],new_weapon['ty'],1])
        np.testing.assert_allclose(old_grip,new_grip,atol=1e-5)

    def test_limb_dimensions_remain_fixed_across_every_action(self):
        checked=0
        for animation in self.actions:
            for frame in animation['frames']:
                for element in frame['elements']:
                    symbol=element['symbol']
                    if symbol not in ('arm_upper','arm_lower','hand','leg','foot'):continue
                    if symbol=='hand' and element['frame']==15:continue
                    entry=self.layout[f"{symbol}/{element['frame']}"]
                    linear=matrix(element)[:2,:2]
                    if symbol=='hand':
                        values=np.linalg.svd(linear,compute_uv=False)
                        self.assertAlmostEqual(values[0],values[1],places=6)
                        self.assertLessEqual(values[0],.820001)
                        box=entry['visible_bbox']
                        self.assertLessEqual(values[0]*max(box[2]-box[0],box[3]-box[1]),18.04001)
                    elif symbol=='leg':
                        points=np.asarray(entry['local_anchors'])@linear.T
                        length=sum(np.linalg.norm(b-a) for a,b in zip(points,points[1:]))
                        self.assertAlmostEqual(length,38,places=5)
                    else:
                        start=local_anchor(entry,0)
                        end=np.asarray(entry['local_anchors'][1]) if symbol=='foot' else local_anchor(entry,1)
                        expected=14 if symbol=='foot' else 21 if symbol=='arm_lower' else 11 if element['frame']==4 else 26
                        self.assertAlmostEqual(np.linalg.norm(linear@(end-start)),expected,places=5)
                    checked+=1
        self.assertGreater(checked,10000)

    def test_working_bent_leg_keeps_a_readable_hip_to_ankle_span(self):
        checked=0
        for animation in self.actions:
            if not animation['name'].startswith(('kanami_chop_','kanami_pickaxe_','kanami_shovel_')):
                continue
            for frame in animation['frames']:
                for leg in (e for e in frame['elements'] if e['symbol']=='leg' and e['frame']==6):
                    distance=np.linalg.norm(anchor(leg,self.layout,1)-anchor(leg,self.layout,0))
                    self.assertGreaterEqual(distance,30,'Bent work knees must not fold the stocking away beneath the skirt')
                    checked+=1
        self.assertGreater(checked,100)

    def test_native_sole_trajectory_is_preserved_after_resizing(self):
        native=[a for bank in ('player_basic','player_actions_axe','player_actions_pickaxe','player_actions_shovel')
                for a in read_anim(read_game_zip(bank,'anim.bin'))]
        checked=0
        for animation in self.actions:
            original=next((a for a in native if 'kanami_'+a['name']==animation['name'] and a['facing']==animation['facing']),None)
            if original is None:continue
            for frame,old in zip(animation['frames'],original['frames']):
                feet=[e for e in frame['elements'] if e['symbol']=='foot']
                old_feet=[e for e in old['elements'] if e['symbol']=='foot']
                if not feet:continue
                current=max(support_height(e,self.layout[f"foot/{e['frame']}"]['support_points']) for e in feet)
                expected=max(support_height(e,self.layout[f"foot/{e['frame']}"]['native_support_points']) for e in old_feet)
                self.assertAlmostEqual(current,expected,places=5)
                checked+=1
        self.assertGreater(checked,500)

    def test_front_hair_has_a_continuous_centre_curtain(self):
        entry=self.frames['hair',0]
        alpha=np.asarray(entry['image'])[:,:,3]
        x=round(entry['w']/2-entry['x']-6)
        # Lower central locks remain behind the waist, rather than two
        # disconnected lateral ponytail silhouettes.
        for y_local in (20,50,80,110):
            y=round(entry['h']/2-entry['y']+y_local)
            self.assertGreater(int((alpha[y-2:y+3,x-4:x+5]>128).sum()),20)

    def test_duplicate_rear_depth_tracks_keep_the_same_pose(self):
        frame=next(a for a in self.actions if a['name']=='kanami_idle_loop' and a['facing']==2)['frames'][0]
        arms=[e for e in frame['elements'] if e['symbol']=='arm_upper' and e['layer'].lower()=='arm_carry']
        self.assertEqual(len(arms),2)
        for field in ('a','b','c','d','tx','ty'):
            self.assertAlmostEqual(arms[0][field],arms[1][field],places=5)


if __name__=='__main__':unittest.main()
