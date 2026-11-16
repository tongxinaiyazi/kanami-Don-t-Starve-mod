# Runtime task: independent 20-item resource package

Read this file first. It is the implementation contract. User approved implementation on 2026-10-30.

## Scope and ownership

You may modify only these files under `D:\SOFTWARE\项目\饥荒\mods\klbq_resources`:
- modinfo.lua
- modmain.lua
- scripts/klbq_resources/catalog.lua
- scripts/klbq_resources/api.lua
- scripts/klbq_resources/register.lua
- scripts/prefabs/klbq_resources.lua
- tests/test_runtime.py
- docs/core-report.md

No Git repository exists. Do not initialize Git or write outside the add-on. Do not edit art, build tools, design JSON or README; parent handles those and the actual engine/art validation. The parent is working concurrently.

Inputs: docs/resource-catalog.json (exact 20 names, Prefab IDs, inspect strings and order), docs/物品设计.md (approved item scope), project AGENTS.md. Game current version: 760178; current scripts are in E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip. Inspect exact used component APIs from local scripts.

## Runtime contract

Version 0.1.0. modinfo uses api_version=10, dst_compatible=true, dont_starve_compatible=false, reign_of_giants_compatible=false, client_only_mod=false, all_clients_require_mod=true. Declare existing-to-be-built modicon.xml/modicon.tex. No configurations or dependencies.

Use Lua 5.1 syntax. modinfo must run without string/ipairs libraries, as the game uses a restricted environment.

Catalog is a pure require module with no game globals:
- VERSION = "0.1.0", API_VERSION = 1, STACK_SIZE = 40
- PREFIX = "klbq_resource_"
- ATLAS = "images/klbq_resources_items.xml"
- TEXTURE = "images/klbq_resources_items.tex"
- ANIM = "anim/klbq_resources_items.zip"
- BANK = BUILD = "klbq_resources_items"
- PREFAB_FILE = "klbq_resources"
- items: ordered 20-entry list, each {key, prefab, name, inspect, category}; key is the full prefab minus PREFIX. category is currency/sequence/appearance/mode/terminal matching the design groups.
- by_key and by_prefab indexes; IDs, names, descriptions and order must match design JSON exactly.

api.lua exports API_VERSION, GetDefinition(key_or_prefab) returning a definition or nil, GetPrefab(key_or_prefab) returning the full prefab string or nil, IsResource(value) accepting a full prefab string or entity.prefab and returning a boolean. Invalid values return nil/false without crashing. No spawn, economy or mutation helpers. No dependency on GLOBAL or Mod-specific variables at module load.

register.lua exports Install(mod_env). It consumes env.GLOBAL, env.Asset and env.RegisterInventoryItemAtlas; it appends to env.PrefabFiles and env.Assets preserving existing entries. It registers 20 names at GLOBAL.STRINGS.NAMES and matching GENERIC.DESCRIBE strings and all 20 icon names <prefab>.tex at the atlas. Scope all additions to resource-prefixed names.

Idempotency: two calls on the same environment or two hosts with this same version register once. Keep one GLOBAL.KLBQ_RESOURCES_OWNER record with version and owner name. On a conflicting version, fail with a clear message before mutating the second host. Do not silently append a duplicate prefab file or override another version. Set ownership only after input validation and successful installation. Expose no global gameplay hooks.

modmain.lua delegates registration:
```lua
require("klbq_resources/register").Install(env)
```

Prefab factory returns all 20 Prefab objects. Each has the shared compiled anim/atlas/image assets. The ground clip name is the full prefab string; bank/build are klbq_resources_items. Create Transform, AnimState and Network; use MakeInventoryPhysics, SetRayTestOnBB, then tags klbq_resource and klbq_resource_<category>. Add MakeInventoryFloatable before SetPristine. Client return occurs after common visual/physics/network setup and before server-only components. Server adds only standard inspectable, inventoryitem, stackable (plus native floater from floatable setup); atlas and image names correspond to the entry, maxsize=40. All closures capture each definition separately.

No custom netvars, save schema, periodic tasks, recipes, RPC, edible, tradable, loot, fuel, durability, combat, buffs, prototyper, equipment or player restrictions. Let native inventory/stack persistence work.

## Tests and RED/GREEN

Use meaningful behavior tests for API invalid inputs and exact 20 identity mapping, owner idempotency and conflict/no-partial-change behavior, restricted modinfo, Lua 5.1 parsing, per-entry prefab construction and master/client boundary. Test actual module code, not regex-only implementation mirrors. Engine APIs can be stubbed for boundary/unit tests; parent separately validates real engine behavior.

Existing Lua 5.1 module is at D:\SOFTWARE\项目\饥荒\tools\python-deps\lupa. Use Python 3.12:
D:\SOFTWARE\CodexData\runtimes\codex-primary-runtime\dependencies\python\python.exe
Set sys.dont_write_bytecode=True or use -B and avoid __pycache__ outside your add-on.

Before runtime code, create tests and record an expected failing assertion for absent runtime; then implement and run GREEN. Do not add tests solely to mirror every private helper.

## Report

Write docs/core-report.md with RED and GREEN commands/output, changed file list and concerns. Final response to parent: DONE or DONE_WITH_CONCERNS, test count and any material limitation. Do not claim game loading or graphical verification; parent owns it.
