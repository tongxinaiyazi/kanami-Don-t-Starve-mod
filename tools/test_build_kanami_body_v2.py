import copy
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from build_kanami_body_v2 import registered_build, make_actions
from inspect_dst_assets import read_anim, read_game_zip


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='D:/SOFTWARE/CodexData/temp')
        self.root = Path(self.temp.name)
        self.contract = {'frames': {'leg/0': {'frame': 0, 'duration': 1}, 'leg/1': {'frame': 1, 'duration': 1}}}
        self.reg = {'frames': {}}
        for n in range(2):
            im = Image.new('RGBA', (40, 30))
            im.putpixel((3+n, 19), (255, 20, 30, 255))
            im.save(self.root / f'leg_{n}.png')
            self.reg['frames'][f'leg/{n}'] = dict(image=f'leg_{n}.png', canvas=[40, 30], centre=[-13.5, 8.25], duration=1, semantic=f'pose {n}', original=True)

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return registered_build(self.root, self.reg, self.contract)

    def test_preserves_offcentre_canvas_and_pixels(self):
        build, images = self.build()
        f = build.find('Symbol/Frame')
        self.assertEqual((f.get('x'), f.get('y'), f.get('w'), f.get('h')), ('-13.5', '8.25', '40', '30'))
        self.assertEqual(images['leg_0.png'].getbbox(), (3,19,4,20))

    def test_rejects_same_drawing_for_distinct_poses(self):
        self.reg['frames']['leg/1']['image'] = 'leg_0.png'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.build()

    def test_rejects_canvas_drift(self):
        self.reg['frames']['leg/0']['canvas'] = [30, 40]
        with self.assertRaisesRegex(ValueError, 'canvas'):
            self.build()

    def test_rejects_missing_native_frame(self):
        del self.reg['frames']['leg/1']
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.build()

    def test_rejects_blank_body(self):
        Image.new('RGBA', (40,30)).save(self.root/'leg_0.png')
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.build()

    def test_rejects_duration_drift(self):
        self.reg['frames']['leg/0']['duration'] = 2
        with self.assertRaisesRegex(ValueError, 'duration'):
            self.build()

    def add_skin_overlay(self):
        Image.new('RGBA', (40,30)).save(self.root/'skin.png')
        self.contract['frames']['arm_upper_skin/0'] = dict(frame=0, duration=1)
        self.contract['frames']['arm_upper/0'] = dict(frame=0, duration=1)
        self.reg['frames']['arm_upper/0'] = dict(self.reg['frames']['leg/0'])
        self.reg['frames']['arm_upper_skin/0'] = dict(self.reg['frames']['leg/0'], image='skin.png', intentional_empty=True, reason='Complete arm drawn in arm_upper', covered_by='arm_upper')

    def test_allows_explicit_skin_overlay_covered_by_main_arm(self):
        self.add_skin_overlay()
        build, images = self.build()
        self.assertIsNone(images['arm_upper_skin_0.png'].getbbox())

    def test_rejects_empty_skin_overlay_without_coverage(self):
        self.add_skin_overlay()
        del self.reg['frames']['arm_upper_skin/0']['covered_by']
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.build()

    def test_rejects_blank_main_arm_despite_coverage_declaration(self):
        self.add_skin_overlay()
        self.reg['frames']['arm_upper/0']['image'] = 'skin.png'
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.build()


class NativeAnimationTests(unittest.TestCase):
    def test_speech_and_refusal_have_complete_bound_clips(self):
        actions=make_actions()
        for name in ('dial_loop','refuseeat'):
            clips=[a for a in actions if a['name']=='kanami_'+name]
            self.assertEqual(len(clips),1,name)
            self.assertEqual(clips[0]['facing'],255)
            self.assertGreater(len(clips[0]['frames']),40)

    def test_each_name_and_facing_has_one_definition(self):
        actions=make_actions()
        self.assertEqual(len(actions),len({(a['name'],a['facing']) for a in actions}))

    def test_ordinary_aliases_retain_native_articulation(self):
        result = make_actions()
        native = [a for bank in ('player_idles', 'player_basic', 'player_actions_eat') for a in read_anim(read_game_zip(bank, 'anim.bin'))]
        checked = 0
        for anim in result:
            original = next((a for a in native if 'kanami_' + a['name'] == anim['name'] and a['facing'] == anim['facing']), None)
            if original:
                expected=copy.deepcopy(original['frames'])
                if anim['name'].startswith(('kanami_eat','kanami_quick_eat','kanami_feast_eat','kanami_refuseeat')):
                    for frame in expected:
                        frame['elements']=[e for e in frame['elements'] if e['symbol']!='swap_object']
                for actual_frame,expected_frame in zip(anim['frames'],expected):
                    identity=lambda e:(e['symbol'],e['frame'],e['layer'],e['tz'])
                    actual_by_id={identity(e):e for e in actual_frame['elements']}
                    for expected_element in expected_frame['elements']:
                        actual_element=actual_by_id[identity(expected_element)]
                        # Joint binding and sole contact own translations.
                        # Limb size and face parenting own their linear basis.
                        for key in ('tx','ty'):
                            expected_element[key]=actual_element[key]
                        if expected_element['symbol'] in ('face','arm_upper','arm_lower','hand','leg','foot','torso','torso_pelvis'):
                            for key in ('a','b','c','d'):
                                expected_element[key]=actual_element[key]
                    self.assertCountEqual(actual_frame['elements'],expected_frame['elements'])
                    self.assertEqual({k:v for k,v in actual_frame.items() if k!='elements'},
                                     {k:v for k,v in expected_frame.items() if k!='elements'})
                checked += 1
        self.assertEqual(checked, 25)  # Includes the native no-facing refusal clip.
        self.assertFalse(any(e['symbol'] == 'klbq_neck' for a in result for f in a['frames'] for e in f['elements']))

    def test_food_clips_cannot_render_a_weapon_without_client_prediction(self):
        food=[a for a in make_actions() if a['name'].startswith(('kanami_eat','kanami_quick_eat','kanami_feast_eat'))]
        self.assertGreaterEqual(len(food),11)
        for animation in food:
            for frame in animation['frames']:
                self.assertFalse(any(e['symbol']=='swap_object' for e in frame['elements']),animation['name'])

    def test_special_pose_body_has_native_matrices(self):
        result = make_actions()
        native = [a for a in result if a['name']=='kanami_idle_loop']
        for anim in result:
            if anim['name'] not in ('kanami_shoot', 'kanami_crossbow_shoot'):
                continue
            idle = next(a for a in native if a['facing'] == anim['facing'])
            expected = [e for e in idle['frames'][0]['elements'] if e['symbol'] not in ('swap_object','face')]
            for frame in anim['frames']:
                self.assertEqual([e for e in frame['elements'] if e['symbol'] not in ('swap_object','face')], expected)

    def test_expression_landmarks_stay_on_the_authored_face(self):
        from build_kanami_body_v2 import ART
        registration=json.loads((ART/'registration.json').read_text(encoding='utf8'))['frames']
        checked=0
        for animation in make_actions():
            for frame in animation['frames']:
                head=next((e for e in frame['elements'] if e['symbol']=='headbase' and e['frame'] in (0,1,4)),None)
                if head is None:
                    continue
                for face in (e for e in frame['elements'] if e['symbol']=='face'):
                    entry=registration[f"face/{face['frame']}"]
                    px,py=entry['local_eye_anchor']
                    hx,hy=entry['head_eye_anchor']
                    actual=(face['a']*px+face['c']*py+face['tx'],face['b']*px+face['d']*py+face['ty'])
                    target=(head['a']*hx+head['c']*hy+head['tx'],head['b']*hx+head['d']*hy+head['ty'])
                    self.assertAlmostEqual(actual[0],target[0],places=5)
                    self.assertAlmostEqual(actual[1],target[1],places=5)
                    checked+=1
        self.assertGreater(checked,500)


if __name__ == '__main__':
    unittest.main()
