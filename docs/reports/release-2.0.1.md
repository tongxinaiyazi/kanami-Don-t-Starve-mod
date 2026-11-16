# 香奈美 2.0.1：日志检查与矿工帽升级

日期：2026-11-15。目标 DST 762172，Steam Build 26474873。两端必装。

## 日志结论

本机最新日志为 `C:/Users/ASUS/Documents/Klei/DoNotStarveTogether/client_log.txt`，会话开始于 2026-11-15 21:42:36。第 34875 行、运行时 00:18:16 报错：

```text
[string "scripts/components/stackable_replica.lua"]:99: attempt to perform arithmetic on field '?' (a nil value)
```

调用从原版 Builder.DoBuild 经 SpawnPrefab 进入工坊模组 3827702076 的 `scripts/prefabs/klbq_resources.lua:36`。模组 2.0.0 将资源堆叠上限写死为 catalog.STACK_SIZE=40；本次启用的「防卡好多招」3050607025 在日志第 1642 行配置 STACK_SIZE=999，其 more_stack_size.lua 将原版堆叠分类改成 999。原版副本按分类值建立的 STACK_SIZE_CODES 不包含 40，因此在 SetMaxSize 中发生 nil - 1。

已用当前安装的原版 stackable 与 stackable_replica 精确复现相同行号、相同错误；修复后两份资源实现的全部 20 个物品在默认值和 999 设置下均可创建，服务端与副本读取上限一致。

用户提供的 `D:/QQ/client_log.txt` 为另一台机器 2026-11-13 的会话（以日志正文时间为准，非文件接收时间）。运行时 00:30:28、01:09:49 两次记录 Dedicated server process terminated prematurely，随后断连。该文件没有 Lua 错误堆栈，因此不能确认两次退出与上述堆叠崩溃同源。继续定位需要该机器对应会话的 Master/Caves 服务端日志；本机现有服务端日志是 11 月 14 日，不能替代。

提供的日志另有重复资源路径拒绝、FROMNUM 图集警告和 Unsupported Storage Multi key；当前文件不能证明它们造成上述退出。本机日志的 DSA 时钟同步重复输出来自独行长路；本次不改其他模组。

## 修复与功能

- 内嵌及独立资源 prefab 使用运行时 TUNING.STACK_SIZE_SMALLITEM，保留默认 40，兼容当前 999 堆叠设置；不修改其他 Workshop 模组。
- 奇点接受一个矿工帽，升级后仅穿戴时发光；光源复用原版联网 minerhatlight，半径 2.5，无燃料消耗，原帽燃料不限。
- 矿工帽和巨鹿眼球升级独立，任意顺序均可；重复给予拒绝且不消耗。
- 穿戴时创建并绑定光源；卸下、装到模型、移除时清理。升级存档保留，旧存档无免费照明。
- 新标记在两端 SetPristine 之前声明。版本升至 2.0.1。

## 验证

- 447 项玩法回归全部通过，耗时 81.104 秒。
- 其中背包相关 34 项通过；新增堆叠回归覆盖两份资源实现、默认/999、全部 20 个物品。
- 独立资源模组的 18 项运行期回归通过。
- 独立离线实际引擎世界，启用本机装备栏模组：10 PASS、0 FAIL、0 Lua 错误、进程正常退出 0。覆盖真实制作、原版 GIVE 消耗空燃料帽、仅穿戴光源、卸下重穿、重复拒绝、双升级顺序、存档恢复和原有容器功能。结果见 `engine-bag-equipment-result.json`，日志见 `engine-bag-equipment.log`。
- 初次引擎测试的夹具错误调用 light:GetParent，修正为 light.entity:GetParent 后重跑通过；初次记录保留为 `engine-bag-light-initial-fixture-error.log`，不作为功能通过依据。
- 本次未打开图形客户端，未实测另一台远端客户端、洞穴迁移或长时间游玩。未更改正式存档。

## 交付

运行包为 `dist/klbq_kanami-2.0.1-dst.zip`，源码美术工程包为同目录 `klbq_kanami-2.0.1-source-art.zip`。本地部署和固定待上传目录沿用现有受控脚本并核对 SHA256，最终结果见 `dist/package-check-2.0.1.json`。

实际问题会话加载的是工坊 3827702076，而非本地开发副本；本次没有修改 Steam 的工坊下载副本，也没有上传工坊。使用本地版时关闭同名工坊版，启用本地 2.0.1；房主及加入者版本一致，重启游戏和世界加载更新。
