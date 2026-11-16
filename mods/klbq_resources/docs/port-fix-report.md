# LAN port isolation fix — 2026-10-30

## Scope and cause

Only `tools/run_engine.py`, `tests/test_engine_runner.py`, and this report were changed.
The runner previously configured/requested 11041, outside the current LAN-only
10998..11018 range. The engine warned `Invalid port selection: 11041` and used
10999, defeating test isolation. Existing success checks ignored that warning.

## Change

- `choose_lan_port()` probes real UDP binds on 127.0.0.1, preferring 11018
  down through 10998 while skipping normal default 10999. Context managers
  close both successful and failed probe sockets; exhaustion raises a clear
  RuntimeError naming the allowed range.
- `main()` chooses once, passing the same port into `prepare()` and both
  `phase_run()` calls. `server.ini` and executable `-port` use that value.
- Logs containing invalid-port/fallback warnings fail validation. Parsed
  `ServerPort:` and `Lan Server Started on port:` values must match the chosen
  port; a silent fallback therefore also fails. The earlier
  `SteamGameServer_Init(10999,27041)` message is intentionally excluded.
- Result JSON records `server_port`, `actual_server_ports`, and `port_error`.
- No dependencies were added. No server process was launched or another process
  modified/terminated. Real engine reruns remain the parent task's responsibility.

The bind probe is a point-in-time availability check: another process may claim
the port after the probe closes. Engine failures or logged fallback then fail
the run; the helper never evicts another process.

## RED: missing helper, before production edits

Working directory for all commands below:
`D:\SOFTWARE\项目\饥荒\mods\klbq_resources`.

The initial `python -B ...` invocation resolved to the Windows Store alias,
returned exit 1 with no output, and was not treated as test evidence. The
installed Python launcher was then used.

Command:

```powershell
py -3 -B -m unittest discover -s tests -p test_engine_runner.py -k helper_exists -v
```

Output (exit 1):

```text
test_helper_exists (test_engine_runner.LanPortTests.test_helper_exists) ... FAIL

======================================================================
FAIL: test_helper_exists (test_engine_runner.LanPortTests.test_helper_exists)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py", line 18, in test_helper_exists
    self.assertTrue(callable(getattr(runner, "choose_lan_port", None)),
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    "Missing choose_lan_port helper")
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: False is not true : Missing choose_lan_port helper

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (failures=1)
```

The full seven-test pre-implementation run used
`py -3 -B -m unittest discover -s tests -p test_engine_runner.py -v` and ended
`FAILED (failures=1, errors=7)`: missing helper/socket import and the old
prepare/phase_run argument counts. This was expected missing-API evidence.
During the first GREEN attempts, the configuration fixture itself required its
ownership marker and empty mods directory; these were added to the fixture.
No production behavior was relaxed to satisfy those setup errors.

## RED: silent fallback, before mismatch detection

After the parent supplied real log formats, added both mismatch cases to the
existing fallback test and observed the expected behavioral failures.

Command:

```powershell
py -3 -B -m unittest discover -s tests -p test_engine_runner.py -k invalid_port -v
```

Output (exit 1):

```text
test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) ...
  test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) (warning='ServerPort: 10999') ... FAIL
  test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) (warning='Lan Server Started on port: 10999') ... FAIL

======================================================================
FAIL: test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) (warning='ServerPort: 10999')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py", line 100, in test_invalid_port_or_fallback_fails_even_with_complete_marker
    with self.assertRaisesRegex(RuntimeError, "Engine create failed"):
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: RuntimeError not raised

======================================================================
FAIL: test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) (warning='Lan Server Started on port: 10999')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py", line 100, in test_invalid_port_or_fallback_fails_even_with_complete_marker
    with self.assertRaisesRegex(RuntimeError, "Engine create failed"):
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: RuntimeError not raised

----------------------------------------------------------------------
Ran 1 test in 0.022s

FAILED (failures=2)
```

## GREEN: final targeted regression suite

Command:

```powershell
py -3 -B -m unittest discover -s tests -p test_engine_runner.py -v
```

Output (exit 0):

```text
test_exhaustion_is_clear_and_every_probe_is_closed (test_engine_runner.LanPortTests.test_exhaustion_is_clear_and_every_probe_is_closed) ... ok
test_helper_exists (test_engine_runner.LanPortTests.test_helper_exists) ... ok
test_occupied_port_is_skipped_and_probe_is_closed (test_engine_runner.LanPortTests.test_occupied_port_is_skipped_and_probe_is_closed) ... ok
test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) ... ok
test_main_passes_selected_port_to_configuration_and_both_phases (test_engine_runner.RunnerPortTests.test_main_passes_selected_port_to_configuration_and_both_phases) ... ok
test_port_is_in_executable_arguments_and_result_json (test_engine_runner.RunnerPortTests.test_port_is_in_executable_arguments_and_result_json) ... ok
test_prepare_writes_selected_port_to_server_ini (test_engine_runner.RunnerPortTests.test_prepare_writes_selected_port_to_server_ini) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.048s

OK
```

The occupied-port test calls the actual helper, holds an actual UDP socket on
its first selected port, and confirms a lower allowed port is selected. It
immediately binds that second port to verify the successful probe was closed.
Exhaustion/order/reserved-port/failed-close behavior uses a deterministic busy
socket fixture. Fake-process tests exercise the real runner command construction,
result JSON serialization, warning/fallback rejection and normal success without
starting the engine. The configuration test exercises real `prepare()` file
writing in a disposable D-drive fixture while replacing installed-game copying
and junction resolution. Temporary fixtures are removed by context managers.

## Follow-up: distinguish complete port labels from SteamMasterServerPort

The parent's real create run passed 24 engine checks and exited 0 on 11018,
but the first parser matched the `ServerPort:` suffix inside
`SteamMasterServerPort: 27041`. That falsely produced
`actual_server_ports: [11018, 27041, 11018]`. The parser now requires whitespace
or start-of-input immediately before the complete label. This accepts timestamped
game-port labels and excludes the Steam master port. No server was started by
this subtask.

First extended the successful fake-process fixture with timestamped
`ServerPort: 11017`, `SteamMasterServerPort: 27041`, and
`Lan Server Started on port: 11017`, and asserted the serialized actual ports
are exactly `[11017, 11017]`.

RED command:

```powershell
py -3 -B -m unittest discover -s tests -p test_engine_runner.py -k port_is_in_executable -v
```

Output (exit 1; the RuntimeError is the observed false-rejection bug):

```text
test_port_is_in_executable_arguments_and_result_json (test_engine_runner.RunnerPortTests.test_port_is_in_executable_arguments_and_result_json) ... ERROR

======================================================================
ERROR: test_port_is_in_executable_arguments_and_result_json (test_engine_runner.RunnerPortTests.test_port_is_in_executable_arguments_and_result_json)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py", line 90, in test_port_is_in_executable_arguments_and_result_json
    result = self.run_fake_phase(root, "SteamGameServer_Init(10999,27041)\n[00:00:01]: ServerPort: 11017\n[00:00:01]: SteamMasterServerPort: 27041\n[00:00:01]: Lan Server Started on port: 11017\n[RESOURCES_TEST] PASS\n[RESOURCES_TEST] COMPLETE\n")
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py", line 85, in run_fake_phase
    return runner.phase_run(root / "binary", shard, "create", 1, 11017)
           ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tools\run_engine.py", line 121, in phase_run
    raise RuntimeError("Engine "+phase+" failed: "+json.dumps(result))
RuntimeError: Engine create failed: {"phase": "create", "server_port": 11017, "actual_server_ports": [11017, 27041, 11017], "port_error": true, "exit_code": 0, "pass": 1, "fail": 0, "complete": true, "lua_error": false, "log": "D:\\SOFTWARE\\CodexData\\temp\\tmp_docfqkj\\reports\\engine-create.log"}

----------------------------------------------------------------------
Ran 1 test in 0.010s

FAILED (errors=1)
```

Then changed only the port regex to require the complete-label boundary.

GREEN command:

```powershell
py -3 -B -m unittest discover -s tests -p test_engine_runner.py -v
```

Output (exit 0):

```text
test_exhaustion_is_clear_and_every_probe_is_closed (test_engine_runner.LanPortTests.test_exhaustion_is_clear_and_every_probe_is_closed) ... ok
test_helper_exists (test_engine_runner.LanPortTests.test_helper_exists) ... ok
test_occupied_port_is_skipped_and_probe_is_closed (test_engine_runner.LanPortTests.test_occupied_port_is_skipped_and_probe_is_closed) ... ok
test_invalid_port_or_fallback_fails_even_with_complete_marker (test_engine_runner.RunnerPortTests.test_invalid_port_or_fallback_fails_even_with_complete_marker) ... ok
test_main_passes_selected_port_to_configuration_and_both_phases (test_engine_runner.RunnerPortTests.test_main_passes_selected_port_to_configuration_and_both_phases) ... ok
test_port_is_in_executable_arguments_and_result_json (test_engine_runner.RunnerPortTests.test_port_is_in_executable_arguments_and_result_json) ... ok
test_prepare_writes_selected_port_to_server_ini (test_engine_runner.RunnerPortTests.test_prepare_writes_selected_port_to_server_ini) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.038s

OK
```
