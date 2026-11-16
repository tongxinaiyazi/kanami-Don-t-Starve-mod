"""Exercise deployment in private fixtures with simulated game process state."""
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = Path('D:/SOFTWARE/CodexData/temp')


class Deployment(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='kanami-deploy-test-', dir=TEMP_ROOT)
        self.workspace = Path(self.temporary.name)
        self.assertTrue(self.workspace.resolve().is_relative_to(TEMP_ROOT.resolve()))
        self.addCleanup(self.temporary.cleanup)
        self.source = self.workspace / 'mods/klbq_kanami'
        self.local = self.workspace / 'game/mods/klbq_kanami'
        self.workshop = self.workspace / 'workshop/3827702076'
        payloads = {'modinfo.lua': 'version="2.1.1"\n',
                    'modmain.lua': 'print("[KLBQ_KANAMI] 2.1.1 registered")\n',
                    'README.md': 'old release\n', 'scripts/prefabs/klbq_kanami.lua': 'return {}\n'}
        for name, text in payloads.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf8')
        for target in (self.local, self.workshop):
            shutil.copytree(self.source, target)
        (self.local / '.kanami-task-owned').write_text('fixture')
        for name in ('modinfo.lua', 'modmain.lua'):
            path = self.source / name
            path.write_text(path.read_text().replace('2.1.1', '2.2.0'), encoding='utf8')
        (self.source / 'README.md').write_text('new release\n')
        (self.workspace / 'docs/reports').mkdir(parents=True)
        self.script = self.workspace / 'tools/deploy_kanami.ps1'
        self.script.parent.mkdir()
        code = (ROOT / 'tools/deploy_kanami.ps1').read_text(encoding='utf8')
        code = code.replace("E:\\steam\\steamapps\\common\\Don't Starve Together\\mods", str(self.local.parent))
        code = code.replace('E:\\steam\\steamapps\\workshop\\content\\322330\\3827702076', str(self.workshop))
        code = code.replace('D:\\SOFTWARE\\CodexData\\temp\\kanami-local-deploy', str(self.workspace / 'backups'))
        self.script.write_text(code, encoding='utf8')

    def deploy(self, running=True):
        process = '[pscustomobject]@{ Id=123 }' if running else 'return'
        command = ("Import-Module (Join-Path $PSHOME 'Modules/Microsoft.PowerShell.Utility'); "
                   f"function Get-Process {{ param($Name,$ErrorAction) {process} }}; & '{self.script}'")
        return subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                               'Bypass', '-Command', command], capture_output=True, text=True, timeout=20)

    def test_metadata_update_while_running_writes_both_copies_and_manifest(self):
        result = self.deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        for target in (self.local, self.workshop):
            self.assertEqual((target / 'modinfo.lua').read_bytes(), (self.source / 'modinfo.lua').read_bytes())
        report = json.loads((self.workspace / 'docs/reports/local-deploy-latest.json').read_text(encoding='utf8'))
        self.assertTrue(report['restart_required'])
        self.assertEqual(struct.unpack_from('<4sII', (self.workshop / 'mod.manifest').read_bytes()), (b'MNFS', 1, 4))

    def test_retired_runtime_path_requires_exit_before_metadata_update(self):
        (self.workshop / 'retired.lua').write_text('return {}')
        result = self.deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('2.1.1', (self.local / 'modinfo.lua').read_text())
        self.assertFalse((self.workshop / 'mod.manifest').exists())

    def test_changed_runtime_code_requires_exit(self):
        (self.source / 'scripts/prefabs/klbq_kanami.lua').write_text('return {changed=true}')
        result = self.deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('2.1.1', (self.local / 'modinfo.lua').read_text())

    def test_stopped_game_allows_runtime_update(self):
        changed = self.source / 'scripts/prefabs/klbq_kanami.lua'
        changed.write_text('return {changed=true}')
        result = self.deploy(running=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.workshop / changed.relative_to(self.source)).read_bytes(), changed.read_bytes())


if __name__ == '__main__':
    unittest.main()
