"""Editable SCML and compiled build must place each pixel at the same origin."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_kanami_assets as builder


class SpriterRegistration(unittest.TestCase):
    def test_asymmetric_sprite_pixels_have_same_local_coordinates(self):
        base = Path('D:/SOFTWARE/CodexData/temp')
        with tempfile.TemporaryDirectory(prefix='kanami-pivot-', dir=base) as temp:
            root = ET.Element('Build', name='fixture')
            symbol = ET.SubElement(root, 'Symbol', name='hand')
            ET.SubElement(symbol, 'Frame', framenum='0', x='7', y='13',
                          w='40', h='60', image='hand_0')
            with patch.object(builder, 'ART', Path(temp)):
                builder.make_spriter(root, {'hand_0.png': Image.new('RGBA', (40, 60))}, [])
            file = ET.parse(Path(temp)/'spriter/klbq_kanami.scml').find('./folder/file')
            px, py = float(file.get('pivot_x')), float(file.get('pivot_y'))
            for x, y in [(0, 0), (13, 17), (39, 59)]:
                # Convert Spriter's bottom-origin y to DST's downwards y.
                scml = (x - 40*px, y - 60*(1-py))
                native = (x + 7 - 20, y + 13 - 30)
                self.assertAlmostEqual(scml[0], native[0])
                self.assertAlmostEqual(scml[1], native[1])
