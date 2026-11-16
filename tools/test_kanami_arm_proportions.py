"""Anatomical cross-section checks, independent of registration implementation."""
import json,unittest
from pathlib import Path
import numpy as np
from PIL import Image

ART=Path(__file__).resolve().parents[1]/'art/klbq_kanami/body-v2'

def section_width(entry,t):
    with Image.open(ART/entry['image']) as image:a=np.asarray(image.convert('RGBA'))[:,:,3]
    anchors=list(entry['anchors'].values())
    p,q=(np.array(e['target_canvas'],float) for e in anchors[:2])
    v=q-p;v/=np.linalg.norm(v);normal=np.array([-v[1],v[0]])
    samples=np.arange(-50,50,.25)
    coords=np.rint(p+(q-p)*t+samples[:,None]*normal).astype(int)
    valid=(coords[:,0]>=0)&(coords[:,0]<a.shape[1])&(coords[:,1]>=0)&(coords[:,1]<a.shape[0])
    selected=samples[valid][a[coords[valid,1],coords[valid,0]]>128]
    return float(selected.max()-selected.min()) if len(selected) else 0.

class ArmProportions(unittest.TestCase):
    def test_elbow_diameter_is_continuous(self):
        entries=json.loads((ART/'registration-upper.json').read_text(encoding='utf8'))['frames']
        for upper,lower in ((0,0),(1,1),(2,0),(3,5)):
            with self.subTest(upper=upper,lower=lower):
                u=section_width(entries[f'arm_upper/{upper}'],.8)
                l=section_width(entries[f'arm_lower/{lower}'],.2)
                self.assertGreater(u,0)
                self.assertGreater(l,0)
                self.assertLessEqual(max(u,l)/min(u,l),1.65,'Elbow contour steps between thick and thin segments')

    def test_horizontal_forearm_keeps_same_anatomical_thickness(self):
        e=json.loads((ART/'registration-upper.json').read_text(encoding='utf8'))['frames']
        normal=section_width(e['arm_lower/0'],.2)
        horizontal=section_width(e['arm_lower/2'],.2)
        self.assertLessEqual(max(normal,horizontal)/min(normal,horizontal),1.5)

if __name__=='__main__':unittest.main()
