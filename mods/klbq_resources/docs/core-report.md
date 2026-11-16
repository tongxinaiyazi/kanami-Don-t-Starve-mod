# Resource runtime implementation report

Date: 2026-10-30. Version: 0.1.0. Scope follows `runtime-task.md`; no Git repository was initialized.

## Changed files

- `modinfo.lua`: DST API 10, both clients required, restricted-environment-safe literal metadata, icon declaration, no configurations or dependencies.
- `modmain.lua`: delegates to `require("klbq_resources/register").Install(env)`.
- `scripts/klbq_resources/catalog.lua`: exact ordered 20-item identity mapping from the approved JSON, indexes, names, inspect texts, category tags, resource paths and version constants.
- `scripts/klbq_resources/api.lua`: pure identity lookup API, full-prefab/entity membership, safe invalid-value handling. No economy, spawning or mutation helpers.
- `scripts/klbq_resources/register.lua`: input validation, shared owner version conflict detection, same-version idempotency, preserving append registration, strings and all inventory atlas elements. Ownership is claimed only after successful installation.
- `scripts/prefabs/klbq_resources.lua`: twenty separately captured constructors sharing animation/atlas/image assets. Common physics/visual/network/floater initialization precedes pristine; inspectable/inventoryitem/stackable are master-only; max stack size 40.
- `tests/test_runtime.py`: 16 behavior tests executing actual module code through Lua 5.1; Python reads source for `package.preload` to avoid Windows Lua 5.1 ANSI fopen limitations on this Unicode project path.
- `docs/core-report.md`: this report.

No artwork, design JSON, README, build tools, main character mods, game installation, or saves were modified by this task.

## Local source evidence

Read directly from the current installed `E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip`, supplied target version 760178:

- `scripts/prefabs/twigs.lua` / `cutstone.lua`: Transform/AnimState/Network and physics initialization, floatable before pristine, client/master boundary, native inspectable/inventoryitem/stackable.
- `scripts/standardcomponents.lua`: exact `MakeInventoryPhysics(inst, mass, rad)` and `MakeInventoryFloatable(inst, size, offset, scale, swap_bank, float_index, swap_data)` signatures. Floatable adds the native `floater` component on the common side.
- `scripts/components/inventoryitem.lua`: `ChangeImageName(newname)` assigns `imagename` and emits `imagechange`.
- `scripts/components/stackable.lua`: `CanStackWith` first rejects differing prefab IDs; native `OnSave` / `OnLoad` persist stack counts. No custom persistence was added.
- `scripts/simutil.lua`: `RegisterInventoryItemAtlas(atlas, imagename)` registers exact `<prefab>.tex` elements.
- `scripts/prefabs/balloonparty.lua`: `AnimState:SetRayTestOnBB(true)` current native use.
- `scripts/components/floater.lua`: default non-bank-swapping float behavior preserves the item animation; no separate `idle` animation was assumed by this package.
- `scripts/mods.lua`: Mod environment exposes `GLOBAL`, `modname` and `env.env = env`.

## RED

Created all 16 tests before writing the runtime files. Command:

```powershell
& 'D:\SOFTWARE\CodexData\runtimes\codex-primary-runtime\dependencies\python\python.exe' -B 'D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_runtime.py'
```

Actual initial output excerpt:

```text
test_all_client_prefabs_return_before_authoritative_components ... FAIL
test_all_master_prefabs_capture_separate_identity ... FAIL
test_api_all_twenty_identities ... FAIL
test_api_invalid_values ... FAIL
test_asset_failure_does_not_claim_or_mutate ... FAIL
test_conflicting_version_leaves_second_host_untouched ... FAIL
test_exact_catalog_and_indexes ... FAIL
test_existing_prefab_entry_is_not_duplicated ... FAIL
test_invalid_environment_does_not_claim_or_mutate ... FAIL
test_lua51_syntax ... FAIL
test_modmain_delegates_to_installer ... FAIL
test_register_preserves_and_registers_every_identity ... FAIL
test_registration_creates_missing_lists_and_string_tables ... FAIL
test_repeated_same_host_and_same_version_other_host_are_noops ... FAIL
test_restricted_modinfo ... FAIL
test_runtime_files_exist ... FAIL
AssertionError: False is not true : Missing runtime module: klbq_resources/catalog
AssertionError: False is not true : Missing runtime file: modinfo.lua
Ran 16 tests in 0.009s
FAILED (failures=16)
```

Exit code 1. These were expected missing-runtime assertions. After implementation, two harness issues were corrected: Lua 5.1 cannot fopen the UTF-8 Windows project path (fixed through Python-read source/preload), and one engine stub used an invalid Lua bracket method declaration (fixed to function assignment). Neither required changing production behavior to fit a stub.

## GREEN

Same command, actual successful output:

```text
test_all_client_prefabs_return_before_authoritative_components ... ok
test_all_master_prefabs_capture_separate_identity ... ok
test_api_all_twenty_identities ... ok
test_api_invalid_values ... ok
test_asset_failure_does_not_claim_or_mutate ... ok
test_conflicting_version_leaves_second_host_untouched ... ok
test_exact_catalog_and_indexes ... ok
test_existing_prefab_entry_is_not_duplicated ... ok
test_invalid_environment_does_not_claim_or_mutate ... ok
test_lua51_syntax ... ok
test_modmain_delegates_to_installer ... ok
test_register_preserves_and_registers_every_identity ... ok
test_registration_creates_missing_lists_and_string_tables ... ok
test_repeated_same_host_and_same_version_other_host_are_noops ... ok
test_restricted_modinfo ... ok
test_runtime_files_exist ... ok
Ran 16 tests in 0.019s
OK
```

Exit code 0. The constructor tests iterate all 20 definitions independently on both master and client; this is 40 constructed stub entities, not 40 separately counted test cases. All six production Lua files parse with Lua 5.1. `modinfo.lua` also executes in an entirely empty environment, with no string/ipairs libraries.

## Boundaries and concerns

- These are Lua module/boundary tests using stubbed engine calls. They do not prove game loading, compilation validity, graphical appearance, remote multiplayer, cave migration, inventory/container behavior or save/reload in the engine. Parent owns actual engine and art acceptance.
- No gameplay effects, recipes, generation, distribution, RPC, netvars, custom saves, restrictions or task loops were added.
- Same-version ownership makes a second host a complete no-op; it relies on the first successfully installed host remaining active in the shared game process. A conflicting version fails before changing the second host.
- The shared owner guard checks the loaded catalog version. Future mergers shipping another copy under these identical `require` names must account for DST module caching; use versioned module names or a clear owning entry point when introducing a different catalog version.
- Inventory atlas registration is a native global lookup operation without an unregister API. Validation and all asset construction finish before any registrations; a hypothetical externally replaced atlas function throwing mid-loop can leave its own external registrations partially applied, while ownership remains unclaimed. Normal native registration and version-conflict paths are covered by current source/test evidence.

## Review correction: callable Asset and strict globals

The reviewer identified two engine mismatches missed by the original stubs. Verified current `scripts/prefabs.lua` defines `Asset = Class(...)`; `scripts/class.lua` makes that Class a callable table. Verified `scripts/strict.lua` errors on undeclared global reads and function-scoped writes.

Added `test_asset_callable_class_table_is_accepted` using a table with the native `__call` constructor pattern, and `test_owner_registration_works_with_strict_globals` using rejecting global `__index`/`__newindex` metamethods. Ran the same full test command before fixing production:

```text
test_asset_callable_class_table_is_accepted ... ERROR
LuaError: klbq_resources: Asset must be a function
test_owner_registration_works_with_strict_globals ... ERROR
LuaError: read undeclared global KLBQ_RESOURCES_OWNER
Ran 18 tests in 0.020s
FAILED (errors=2)
```

The other 16 tests passed. Removed the function-only Asset type assertion: the constructor is now exercised while preparing the asset list before any installation mutation, so invalid/non-callable input still fails without claiming ownership. Replaced owner access with native `rawget` / `rawset`, avoiding the strict global metamethods.

Fresh full GREEN with the same command:

```text
test_asset_callable_class_table_is_accepted ... ok
test_owner_registration_works_with_strict_globals ... ok
Ran 18 tests in 0.022s
OK
```

Exit code 0. Current suite count is 18; the earlier 16-test output above remains the original implementation history.
