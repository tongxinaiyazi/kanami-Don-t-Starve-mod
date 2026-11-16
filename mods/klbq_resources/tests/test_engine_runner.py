"""Exercise the isolated runner without starting the game executable."""
import importlib.util
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "resource_engine_runner", Path(__file__).parents[1] / "tools/run_engine.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LanPortTests(unittest.TestCase):
    def test_helper_exists(self):
        self.assertTrue(callable(getattr(runner, "choose_lan_port", None)),
                        "Missing choose_lan_port helper")

    def test_occupied_port_is_skipped_and_probe_is_closed(self):
        # Holding the actual preferred available UDP port proves the helper
        # checks the OS, rather than merely returning a different constant.
        first = runner.choose_lan_port()
        self.assertIn(first, range(10998, 11019))
        self.assertNotEqual(first, 10999)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as held:
            held.bind(("127.0.0.1", first))
            second = runner.choose_lan_port()
            self.assertLess(second, first)
            self.assertNotEqual(second, 10999)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.bind(("127.0.0.1", second))

    def test_exhaustion_is_clear_and_every_probe_is_closed(self):
        probes = []

        class BusySocket:
            def __enter__(self):
                probes.append(self)
                self.closed = False
                return self

            def bind(self, address):
                self.address = address
                raise OSError("occupied")

            def __exit__(self, *_):
                self.closed = True

        with mock.patch.object(runner.socket, "socket", side_effect=lambda *_: BusySocket()):
            with self.assertRaisesRegex(RuntimeError, "10998.*11018"):
                runner.choose_lan_port()
        self.assertEqual([p.address for p in probes],
                         [("127.0.0.1", p) for p in range(11018, 10997, -1) if p != 10999])
        self.assertTrue(all(p.closed for p in probes))


class RunnerPortTests(unittest.TestCase):
    def test_main_passes_selected_port_to_configuration_and_both_phases(self):
        with mock.patch.object(runner, "choose_lan_port", return_value=11017), \
             mock.patch.object(runner, "prepare", return_value=("binary", "shard")) as prepare, \
             mock.patch.object(runner, "phase_run", return_value={}) as phase_run, \
             mock.patch("sys.argv", ["run_engine.py"]), mock.patch("builtins.print"):
            runner.main()
        prepare.assert_called_once_with("both", 11017)
        self.assertEqual(phase_run.call_args_list,
                         [mock.call("binary", "shard", "create", 120, 11017),
                          mock.call("binary", "shard", "reload", 120, 11017)])

    def run_fake_phase(self, root, log_text):
        shard = root / "cluster/Master"
        shard.mkdir(parents=True)
        report = root / "reports"

        def start_process(command, **kwargs):
            self.assertEqual(command[command.index("-port") + 1], "11017")
            kwargs["stdout"].write(log_text.encode())
            kwargs["stdout"].flush()
            return mock.Mock(poll=lambda: 0, returncode=0)

        with mock.patch.object(runner, "REPORT", report), \
             mock.patch.object(runner.subprocess, "Popen", side_effect=start_process), \
             mock.patch("builtins.print"):
            return runner.phase_run(root / "binary", shard, "create", 1, 11017)

    def test_port_is_in_executable_arguments_and_result_json(self):
        with tempfile.TemporaryDirectory(dir="D:/SOFTWARE/CodexData/temp") as folder:
            root = Path(folder)
            result = self.run_fake_phase(root, "SteamGameServer_Init(10999,27041)\n[00:00:01]: ServerPort: 11017\n[00:00:01]: SteamMasterServerPort: 27041\n[00:00:01]: Lan Server Started on port: 11017\n[RESOURCES_TEST] PASS\n[RESOURCES_TEST] COMPLETE\n")
            saved = json.loads((root / "reports/engine-create-result.json").read_text())
        self.assertEqual(result["server_port"], 11017)
        self.assertEqual(saved["server_port"], 11017)
        self.assertEqual(saved["actual_server_ports"], [11017, 11017])

    def test_invalid_port_or_fallback_fails_even_with_complete_marker(self):
        for warning in ("Invalid port selection", "Falling back to default port 10999",
                        "ServerPort: 10999", "Lan Server Started on port: 10999"):
            with self.subTest(warning=warning), \
                 tempfile.TemporaryDirectory(dir="D:/SOFTWARE/CodexData/temp") as folder:
                with self.assertRaisesRegex(RuntimeError, "Engine create failed"):
                    self.run_fake_phase(Path(folder), warning + "\n[RESOURCES_TEST] COMPLETE\n")

    def test_prepare_writes_selected_port_to_server_ini(self):
        with tempfile.TemporaryDirectory(dir="D:/SOFTWARE/CodexData/temp") as folder:
            root = Path(folder)
            game = root / "installed"
            (game / "bin64").mkdir(parents=True)
            (game / "data").mkdir()
            stage = root / "stage"
            data = stage / "game/data"
            data.mkdir(parents=True)
            (stage / "game/mods").mkdir()
            (stage / ".klbq-resources-owned").write_text("test fixture\n")
            original_resolve = Path.resolve

            def resolve(path, *args, **kwargs):
                return game / "data" if path == data else original_resolve(path, *args, **kwargs)

            with mock.patch.object(runner, "GAME", game), mock.patch.object(runner, "STAGE", stage), \
                 mock.patch.object(runner, "runtime_copy"), mock.patch.object(runner.shutil, "copytree"), \
                 mock.patch.object(Path, "resolve", resolve):
                _, shard = runner.prepare("create", 11017)
            self.assertIn("server_port=11017\n", (shard / "server.ini").read_text())


if __name__ == "__main__":
    unittest.main()
