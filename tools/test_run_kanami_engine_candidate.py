import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from run_kanami_engine import prepare_body_candidate


class CandidatePreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='D:/SOFTWARE/CodexData/temp')
        self.root=Path(self.tmp.name)
        self.source=self.root/'candidate/compiled/anim'
        self.source.mkdir(parents=True)
        self.mods=self.root/'game/mods'
        self.target=self.mods/'klbq_kanami_verify'
        self.target.mkdir(parents=True)
        (self.target/'.kanami-task-owned').write_text('test fixture')
        for name,member,magic in [('klbq_kanami.zip','build.bin',b'BILD'),('klbq_kanami_actions.zip','anim.bin',b'ANIM')]:
            with zipfile.ZipFile(self.source/name,'w') as z:
                z.writestr(member,magic+b'test')

    def tearDown(self):self.tmp.cleanup()

    def prepare(self,target=None):
        return prepare_body_candidate(self.source,target or self.target,allowed_source_root=self.root/'candidate',mods_root=self.mods)

    def test_copies_both_and_reports_matching_hashes(self):
        result=self.prepare()
        for name,record in result['files'].items():
            self.assertEqual((self.target/'anim'/name).read_bytes(),(self.source/name).read_bytes())
            self.assertEqual(record['source_sha256'],record['installed_sha256'])
        self.assertFalse((self.mods/'klbq_kanami').exists())

    def test_rejects_ordinary_install(self):
        with self.assertRaisesRegex(ValueError,'verify'):
            self.prepare(self.mods/'klbq_kanami')

    def test_rejects_unowned_destination(self):
        (self.target/'.kanami-task-owned').unlink()
        with self.assertRaisesRegex(ValueError,'owned'):self.prepare()

    def test_missing_second_zip_does_not_copy_first(self):
        (self.source/'klbq_kanami_actions.zip').unlink()
        with self.assertRaises(FileNotFoundError):self.prepare()
        self.assertFalse((self.target/'anim').exists())

    def test_rejects_non_candidate_source(self):
        with self.assertRaisesRegex(ValueError,'source'):
            prepare_body_candidate(self.source,self.target,allowed_source_root=self.root/'elsewhere',mods_root=self.mods)

    def test_rejects_wrong_binary_before_copy(self):
        with zipfile.ZipFile(self.source/'klbq_kanami_actions.zip','w') as z:z.writestr('anim.bin',b'WRONG')
        with self.assertRaisesRegex(ValueError,'anim.bin'):self.prepare()
        self.assertFalse((self.target/'anim').exists())

    def test_rejects_invalid_zip_before_copy(self):
        (self.source/'klbq_kanami_actions.zip').write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile):self.prepare()
        self.assertFalse((self.target/'anim').exists())


if __name__=='__main__':unittest.main()
