# 卡拉彼丘资源物品包 Implementation Plan

> **For agentic workers:** Use subagent-driven-development for the Lua runtime task and requesting-code-review for the complete deliverable. No Git repository is present; use file snapshots and read-only reviews instead of commits.

**Goal:** 将已设计的 20 项资源实现为独立 DST 物品包，并保留稳定的查询、注册与融合入口。

**Architecture:** 纯 Lua 目录定义物品，统一 Prefab 工厂提供原生库存、堆叠和存档行为。独立注册模块负责资源和字符串，公开查询 API 不产生物品或经济行为。重绘图集由 Klei 本地工具编译，交付包只包含运行所需文件。

**Tech Stack:** DST 760178 bundled Lua, Lua 5.1, Python 3, Klei Mod Tools, image_gen.

## Global Constraints

- 只修改 `D:\SOFTWARE\项目\饥荒\mods\klbq_resources` 内的项目文件。
- 保持设计目录中的全部 20 个 `klbq_resource_` Prefab ID。
- 排除战令币、活动凭录、历史活动物品、赛季专用资源。
- 不添加来源、配方、掉落、赠送、商店、抽卡、兑换、属性或角色技能。
- DST 两端必装，不直接依赖或修改香奈美/莉莉丝组件、配方和存档。
- 每组 40，同种可堆叠，不同资源和终端不可混堆，数量保存采用原生 stackable。
- 艺术工程、测试、报告、参考图不得进入运行 ZIP。
- 使用现有工具链，不更改游戏原始文件或用户正式存档。
- 临时编译与隔离世界仅写入任务独有的 D 盘临时目录；结束清理废弃中间文件。
- 不在无 GUI 专服验证后声称图形客户端、另一台客户端、洞穴或真机验收通过。

## Task 1: Lua runtime and reusable integration API

Requirements and exact interfaces are in [runtime-task.md](runtime-task.md). The implementer owns only the runtime Lua files, runtime unit test and core report specified there.

- [x] Write runtime behavior tests and record an expected RED for missing runtime.
- [x] Implement pure Lua catalog, API, idempotent registration and common Prefab factory.
- [x] Verify Lua 5.1 parsing, restricted modinfo environment, registration ownership, all 20 item identities, client/server boundary and no gameplay systems.
- [x] Report GREEN and inspect the final code with read-only review.

Unit command:
```powershell
& 'D:\SOFTWARE\CodexData\runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s mods/klbq_resources/tests -p test_runtime.py -v
```

Required integration calls:
```lua
local resources = require("klbq_resources/api")
local prefab = resources.GetPrefab("stringsea_beacon")
local definition = resources.GetDefinition(prefab)
local is_resource = resources.IsResource(existing_entity)
require("klbq_resources/register").Install(env)
```

## Task 2: Original art and compiled resources

Files: `art/resource-icons.png`, `art/imagegen-prompt.txt`, `art/items/*.png`, `tools/build_assets.py`, `tests/test_assets.py`, `images/klbq_resources_items.{xml,tex}`, `anim/klbq_resources_items.zip`, `modicon.{xml,tex}`.

- [x] Add an asset test requiring the compiled 20 inventory entries, animation bank/build and all 20 ground clips; observe RED before building.
- [x] Generate one transparent 4-column × 5-row sprite atlas, ordered exactly as resource-catalog.json, using the original icons only as references.
- [x] Inspect all slots and transparent margins; split and resize only as mechanical asset processing.
- [x] Compile a 512×512 inventory atlas with 20 native 64×64 regions, plus ground build/animations and mod icon through installed Klei tools.
- [x] Re-run binary/atlas binding tests and visually inspect inventory/ground preview.

Asset command:
```powershell
py -3 -B mods/klbq_resources/tools/build_assets.py
py -3 -B -m unittest discover -s mods/klbq_resources/tests -p test_assets.py -v
```

## Task 3: Engine validation, docs and package

Files: `tests/engine_mod/{modinfo,modmain}.lua`, `tools/run_engine.py`, `tools/package_mod.py`, `docs/融合与调用.md`, `docs/reports/*`, `release/klbq_resources-0.1.0.zip`, README and previous design-status fields.

- [x] Launch only a task-owned offline server with an isolated storage root and mod root; never overwrite installed mods.
- [x] Spawn all 20 resources in that test world. Check animation build/clip binding, inventory atlas, stack split/merge/overflow, container behavior, save records and reloading resource entities.
- [x] Compare the current main-mod file hashes with the pre-implementation snapshot.
- [x] Document lookup API, merge entry and retained Prefab IDs with copyable examples and test commands.
- [x] Package only allowlisted runtime files; inspect the archive for reference artwork, logs, saves, dependencies or tools.
- [x] Run complete checks once after fixes; record evidence and unverified GUI/multiplayer/shard cases.
- [x] Request a read-only final review; resolve material findings before delivery.
