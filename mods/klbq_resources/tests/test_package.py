"""Check the deliverable archive as installed by another player."""
from pathlib import Path
import json, unittest, zipfile
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'release/klbq_resources-0.1.0.zip'
EXPECTED={'modinfo.lua','modmain.lua','modicon.xml','modicon.tex','README.txt',
          'scripts/klbq_resources/catalog.lua','scripts/klbq_resources/api.lua',
          'scripts/klbq_resources/register.lua','scripts/prefabs/klbq_resources.lua',
          'images/klbq_resources_items.xml','images/klbq_resources_items.tex',
          'anim/klbq_resources_items.zip'}

class RuntimePackage(unittest.TestCase):
    def test_archive_has_only_runtime_files_at_mod_root(self):
        self.assertTrue(ARCHIVE.is_file(),'runtime package has not been created')
        with zipfile.ZipFile(ARCHIVE) as z:
            self.assertEqual(set(z.namelist()),EXPECTED)
            self.assertIsNone(z.testzip())
            for name in z.namelist():
                self.assertNotIn('..',Path(name).parts)
                if name!='README.txt':
                    self.assertEqual(z.read(name),(ROOT/name).read_bytes())
                self.assertFalse(any(p in name for p in ['references/','tests/','art/','reports/','cache','token']))
            self.assertEqual(z.read('images/klbq_resources_items.tex')[:4],b'KTEX')
            self.assertIn(b'all_clients_require_mod = true',z.read('modinfo.lua'))
            self.assertNotIn(b'klbq_kanami',z.read('modmain.lua'))
    def test_install_readme_matches_scope(self):
        self.assertTrue(ARCHIVE.is_file(),'runtime package has not been created')
        with zipfile.ZipFile(ARCHIVE) as z:
            text=z.read('README.txt').decode('utf-8')
        for value in ['0.1.0','klbq_resources','40','两端']:
            self.assertIn(value,text)

if __name__=='__main__':unittest.main(verbosity=2)
