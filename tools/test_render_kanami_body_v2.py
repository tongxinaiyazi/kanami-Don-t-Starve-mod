import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from render_kanami_body_v2 import load_registration, load_exported, render_frame, visible, export_cycle


class CandidateRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='D:/SOFTWARE/CodexData/temp')
        self.root = Path(self.temp.name)
        Image.new('RGBA', (8, 6), (255, 0, 0, 255)).save(self.root/'candidate.png')
        data = {'frames': {'hand/3': dict(image='candidate.png', canvas=[8,6], centre=[10,-4], duration=3)}}
        (self.root/'registration.json').write_text(json.dumps(data))

    def tearDown(self):
        self.temp.cleanup()

    def test_reads_candidate_pixels_and_expands_duration(self):
        frames = load_registration(self.root)
        self.assertEqual(set(frames), {('hand',3),('hand',4),('hand',5)})
        self.assertEqual(frames['hand',4]['image'].getpixel((0,0)), (255,0,0,255))
        element = dict(symbol='hand', frame=4, layer='arm_normal', a=1,b=0,c=0,d=1,tx=0,ty=0)
        im = render_frame({'elements':[element]}, frames, size=(100,100), scale=1)
        self.assertEqual(im.getpixel((60,41)), (255,0,0,255))

    def test_exported_duration_and_case_insensitive_symbols(self):
        (self.root/'build.xml').write_text('<Build><Symbol name="HAND"><Frame framenum="3" duration="2" x="10" y="-4" w="8" h="6" image="candidate"/></Symbol></Build>')
        self.assertEqual(set(load_exported(self.root)), {('hand',3),('hand',4)})

    def test_carry_keeps_weapon_and_excludes_empty_arm(self):
        def e(symbol, layer): return dict(symbol=symbol,layer=layer)
        self.assertTrue(visible(e('swap_object','swap_object'), True, False))
        self.assertFalse(visible(e('swap_object','swap_object'), False, False))
        self.assertFalse(visible(e('hand','arm_normal'), True, False))
        self.assertTrue(visible(e('hair','hair'), False, False))
        self.assertFalse(visible(e('hair','hair'), False, True))
        self.assertTrue(visible(e('headbase','head'), False, True))

    def test_gif_contains_every_frame_and_contact(self):
        frames = load_registration(self.root)
        elements = [dict(symbol='hand',frame=4,layer='arm_normal',a=1,b=0,c=0,d=1,tx=n*12,ty=0) for n in range(3)]
        anim = dict(name='test',facing=8,fps=30,frames=[{'elements':[e]} for e in elements])
        report = export_cycle(anim, frames, self.root, False, False, (100,100), 1, 3)
        with Image.open(self.root/report['file']) as gif:
            self.assertEqual(gif.n_frames,3)
            total = 0
            for n in range(3):
                gif.seek(n)
                total += gif.info['duration']
            self.assertEqual(total,100)
        self.assertEqual(report['contact_frames'],[0,1,2])
        self.assertEqual(report['missing_visible_symbols'],[])


if __name__ == '__main__': unittest.main()
