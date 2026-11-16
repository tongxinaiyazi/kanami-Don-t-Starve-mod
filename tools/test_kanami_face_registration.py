"""Pixel-level regression checks for neutral eyes in native idle poses."""
import unittest
import json
import numpy as np
from calibrate_kanami_face import matrix, player_banks
from inspect_dst_assets import read_anim, read_game_zip
from render_kanami_body_v2 import ROOT, load_registration
from build_kanami_body_v2 import make_actions


class FaceRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = load_registration(ROOT/'art/klbq_kanami/body-v2')
        cls.layout=json.loads((ROOT/'art/klbq_kanami/body-v2/registration.json').read_text(encoding='utf8'))['frames']
        cls.idles = make_actions()

    def iris_pixels(self, facing):
        animation = next(a for a in self.idles if a['name'] == 'kanami_idle_loop' and a['facing'] == facing)
        elements = animation['frames'][0]['elements']
        return self.iris_pixels_for_elements(elements)

    def iris_pixels_for_elements(self,elements):
        head = next(e for e in elements if e['symbol'] == 'headbase')
        face = next(e for e in elements if e['symbol'] == 'face')
        entry = self.frames['face', face['frame']]
        pixels = np.asarray(entry['image'], dtype=float)
        red, green, blue, alpha = (pixels[:, :, i] for i in range(4))
        selected = (alpha > 128) & (blue > red*1.3) & (blue > green*1.1) & (blue > 90)
        eye_y=self.layout[f"face/{face['frame']}"]['local_eye_anchor'][1]
        local_y=np.arange(entry['h'])+entry['y']-entry['h']/2
        selected&=np.abs(local_y[:,None]-eye_y)<16
        y, x = np.where(selected)
        self.assertGreater(len(x), 20, 'Missing blue iris artwork')
        local = np.column_stack((x+entry['x']-entry['w']/2, y+entry['y']-entry['h']/2, np.ones(len(x))))
        return (np.linalg.inv(matrix(head)) @ matrix(face) @ local.T).T[:, :2]

    def test_front_eyes_are_larger_and_above_lower_cheeks(self):
        points = self.iris_pixels(8)
        self.assertLess(points[:, 1].mean(), -34)
        self.assertGreater(points[:, 1].mean(), -42)
        self.assertGreaterEqual(np.ptp(points[:, 0]), 49)
        self.assertGreaterEqual(np.ptp(points[:, 1]), 12)

    def test_profile_eye_has_matching_height(self):
        points = self.iris_pixels(5)
        np.testing.assert_allclose(points.mean(axis=0),[20,-45],atol=.8)
        self.assertGreaterEqual(np.ptp(points[:, 1]), 12)
        self.assertGreater(points[:,0].min(),2)
        self.assertLess(points[:,0].max(),35,'Iris must stay inside the profile face, behind the nose contour')

    def test_neutral_mouth_is_present_but_almost_invisible(self):
        for n,point in ((0,[-6,-11]),(4,[27,-25])):
            entry=self.frames['face',n]
            from calibrate_kanami_face import neutral_face_bases
            view=int(n==4)
            registration=self.layout[f'face/{n}']
            point=np.asarray(registration['local_eye_anchor'])+np.linalg.solve(
                neutral_face_bases()[view],np.asarray(point)-registration['head_eye_anchor'])
            x=entry['w']/2-entry['x']+point[0]
            y=entry['h']/2-entry['y']+point[1]
            mask=entry['image'].getchannel('A').crop((round(x-8),round(y-3),round(x+8),round(y+4)))
            box=mask.point(lambda alpha:255 if alpha>40 else 0).getbbox()
            self.assertIsNotNone(box,'A subtle closed mouth must remain in the artwork')
            self.assertLessEqual(box[2]-box[0],4)
            self.assertLessEqual(box[3]-box[1],3)
            self.assertEqual(registration['mouth_mode'],'subtle_closed')

    def test_speech_iris_centres_follow_the_head_through_the_entire_cycle(self):
        speech=next(a for a in self.idles if a['name']=='kanami_dial_loop')
        expressions=set()
        for frame in speech['frames']:
            face=next(e for e in frame['elements']if e['symbol']=='face')
            expressions.add(face['frame'])
            centre=self.iris_pixels_for_elements(frame['elements']).mean(axis=0)
            np.testing.assert_allclose(centre,[-8,-38],atol=.75)
        self.assertEqual(expressions,{0,9,10})

    def test_speech_keeps_a_readable_mouth_below_the_eyes(self):
        speech=next(a for a in self.idles if a['name']=='kanami_dial_loop')
        for frame in speech['frames']:
            elements=frame['elements']
            head=next(e for e in elements if e['symbol']=='headbase')
            face=next(e for e in elements if e['symbol']=='face')
            entry=self.frames['face',face['frame']]
            y,x=np.where(np.asarray(entry['image'])[:,:,3]>(40 if face['frame']==0 else 128))
            local=np.column_stack((x+entry['x']-entry['w']/2,y+entry['y']-entry['h']/2,np.ones(len(x))))
            points=(np.linalg.inv(matrix(head))@matrix(face)@local.T).T[:,:2]
            mouth=points[(points[:,1]>-22)&(points[:,1]<0)]
            self.assertGreater(len(mouth),0,'Speech must retain a visible mouth')
            if face['frame'] in (9,10):
                self.assertGreater(len(mouth),4)
                self.assertLessEqual(np.ptp(mouth[:,0]),8)
                self.assertLessEqual(np.ptp(mouth[:,1]),6)

    def test_speech_does_not_duplicate_the_upper_lip_in_the_eye_cutout(self):
        for n in (9,10):
            alpha=np.asarray(self.frames['face',n]['image'])[:,:,3]
            rows=(alpha>128).sum(axis=1)>1
            groups=int((rows&~np.r_[False,rows[:-1]]).sum())
            self.assertEqual(groups,3,'The eye layer must not contain a duplicate lip')

    def test_calibration_uses_player_assets(self):
        banks = player_banks()
        self.assertIn('player_actions_feast_eat', banks)
        self.assertNotIn('player_hermitcrab_idle', banks)
        self.assertNotIn('player_hermitcrab_look', banks)


if __name__ == '__main__':
    unittest.main()
