"""Validate real runtime assets and their bindings, not source-code patterns."""
from pathlib import Path
import json, struct, sys, unittest, zipfile
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
sys.path.insert(0,str(PROJECT/'tools'))
from inspect_dst_assets import read_anim,read_build
DATA=json.loads((ROOT/'docs/resource-catalog.json').read_text(encoding='utf-8'))
NAMES={item['prefab'] for item in DATA['items']}

class CompiledAssets(unittest.TestCase):
    def test_20_ground_clips_and_symbols_are_compiled_and_bound(self):
        target=ROOT/'anim/klbq_resources_items.zip'
        self.assertTrue(target.is_file(),'shared resource animation has not been built')
        with zipfile.ZipFile(target) as z:
            build=read_build(z.read('build.bin'));anims=read_anim(z.read('anim.bin'))
            self.assertTrue(all(z.read(name)[:4]==b'KTEX' for name in z.namelist() if name.endswith('.tex')))
        self.assertEqual(build['name'],'klbq_resources_items')
        self.assertEqual({symbol['name'] for symbol in build['symbols']},NAMES)
        self.assertEqual({clip['name'] for clip in anims},NAMES)
        for clip in anims:
            self.assertEqual(clip['root'],'klbq_resources_items')
            self.assertGreater(len(clip['frames']),0)
            for frame in clip['frames']:
                self.assertEqual({e['symbol'] for e in frame['elements']},{clip['name']})
                self.assertGreater(frame['box'][2],0)

    def test_native_inventory_atlas_regions_cover_exactly_20_items(self):
        target=ROOT/'images/klbq_resources_items.xml'
        self.assertTrue(target.is_file(),'inventory atlas has not been built')
        atlas=ET.parse(target)
        self.assertEqual(atlas.find('Texture').get('filename'),'klbq_resources_items.tex')
        entries=atlas.findall('Elements/Element')
        self.assertEqual({e.get('name') for e in entries},{n+'.tex' for n in NAMES})
        self.assertEqual(len(entries),20)
        self.assertEqual((ROOT/'images/klbq_resources_items.tex').read_bytes()[:4],b'KTEX')
        rects=[]
        for e in entries:
            x1,x2,y1,y2=[float(e.get(k)) for k in ('u1','u2','v1','v2')]
            self.assertTrue(0<=x1<x2<=1 and 0<=y1<y2<=1)
            self.assertAlmostEqual((x2-x1)*512+1,64)
            self.assertAlmostEqual((y2-y1)*512+1,64)
            rects.append((x1,x2,y1,y2))
        for i,a in enumerate(rects):
            for b in rects[i+1:]:
                self.assertFalse(min(a[1],b[1])>max(a[0],b[0]) and min(a[3],b[3])>max(a[2],b[2]))

    def test_mod_icon_is_compiled(self):
        self.assertTrue((ROOT/'modicon.xml').is_file(),'mod icon has not been built')
        self.assertEqual((ROOT/'modicon.tex').read_bytes()[:4],b'KTEX')
        self.assertIsNotNone(ET.parse(ROOT/'modicon.xml').find("Elements/Element[@name='modicon.tex']"))

if __name__=='__main__':unittest.main(verbosity=2)
