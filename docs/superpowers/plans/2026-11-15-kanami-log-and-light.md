# 香奈美堆叠兼容与矿工帽升级实现计划

> 执行方式：本会话顺序执行，使用 executing-plans；当前目录没有 Git 仓库，不创建提交或工作树。

**Goal:** 修复资源生成崩溃，并让弦能奇点通过矿工帽获得仅穿戴生效的永久照明。

**Architecture:** 资源物品使用原版运行时堆叠分类上限；保留附加资源模组与内嵌副本一致。奇点使用两项独立升级标记、原版 Trader 和 minerhatlight，光源在穿戴时创建并跟随玩家，卸下及移除时清理。

**Tech Stack:** 当前 DST 762172 Lua 5.1、现有 Python/Lupa、独立引擎测试世界。

## Global Constraints

- 矿工帽一次消耗一个，任意剩余燃料均可；重复升级不耗材料。
- 仅穿戴发光；两项升级任意顺序、可保存；旧存档默认无灯。
- 不改用户正式存档或其他 Workshop 模组，不上传 Workshop。

### Task 1: 堆叠崩溃回归

- [x] 新增 `tests/gameplay/test_resource_stack_compat.py`，用原版 stackable 与 stackable_replica 创建全部资源物品，分别检查原版上限与 999。
- [x] 执行 `python -B -m unittest discover -s tests/gameplay -p test_resource_stack_compat.py -v`，确认 999 下复现日志相同错误。
- [x] 修改两个 `mods/*/scripts/prefabs/klbq_resources.lua`：

```lua
inst.components.stackable.maxsize = TUNING.STACK_SIZE_SMALLITEM
```

- [x] 同一回归通过，确认两份共享资源文件相同。

### Task 2: 原版给予和仅穿戴照明

- [x] 新增 `tests/gameplay/test_bag_light.py`，扩展必要引擎边界夹具；验证接受帽子、拒绝重复、双升级顺序、穿戴和卸下、光源清理、存档及客户端结构。
- [x] 先运行该测试并确认因新功能缺失而失败。
- [x] 修改 `mods/klbq_kanami/scripts/prefabs/klbq_singularity.lua`：增加 `_klbq_minerhat` 网络标记；原版 trader 按材料选择升级；仅两项完成后关闭交易；保存 `klbq_minerhat`；穿戴时 `SpawnPrefab("minerhatlight")` 并 `SetParent(owner.entity)`；卸下和移除时 Remove 光源。
- [x] 修改原眼球测试，眼球完成后继续保留矿工帽升级入口。
- [x] 运行矿工帽、眼球、背包及客户端回归。

### Task 3: 引擎与交付

- [x] 扩展 `tests/engine_mod/bag.lua`，用真实帽子和背包验证升级、原版光源、卸下重穿、存档恢复及重复拒绝。
- [x] 运行 `python -B -m unittest discover -s tests/gameplay -q`。
- [x] 运行 `python -B tools/run_kanami_engine.py --seconds 180 --isolated-mod-copy --bag-only --equipment`；检查所有断言、Lua 错误和退出状态。
- [x] 更新模组说明、验证报告及补丁版本，打包运行包；交付说明区分已验证与未验证。
