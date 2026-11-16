# 香奈美 2.0.2：矿工帽无法给予

日期：2026-11-15。目标 DST 762172，Steam Build 26474873。两端必装。

## 问题与证据

用户截图显示拿着矿工帽指向弦能奇点时只有“存放”。本机 client_log.txt 最近会话开始于 2026-11-15 22:42:16，确实加载本地 klbq_kanami 2.0.1；本次问题并非运行了旧工坊副本。

当前安装的 scripts.zip 中，componentactions.lua 的 inventoryitem USEITEM 回调先为可打开的容器加入 STORE，之后才判断 alltrader。矿工帽在原版 hats.lua 中已有 tradable，仍可能同时出现 GIVE 与 STORE，由后续动作排序选中存放。上一版仅直接调用 GIVE.fn 验证服务端升级，漏测了鼠标动作生成及排序，这是本次测试缺口。

## 修复

- 仅针对未完成矿工帽升级的奇点：矿工帽动作列表移除 STORE，保留或加入原版 GIVE。左右键和客户端读取均使用这一规则。
- 完成矿工帽升级后恢复普通存放；其他物品继续使用原版存放行为。沿用服务端 Trader 校验和单件消耗。
- 补齐两端 alltrader 标签及服务端 acceptnontradable 设置。
- 原版 AddComponentAction 对同一模组、动作类型和组件只保留一个回调。因此与已有拓印共用 inventoryitem USEITEM 入口，避免相互覆盖。
- 版本升至 2.0.2。保留 2.0.1 的永久免燃料、仅穿戴发光、眼球升级兼容和堆叠修复。

## 验证

- 452 项玩法回归通过，耗时 110.423 秒，退出码 0。新增 5 项覆盖原版 inventoryitem 动作入口、左右键、客户端无服务端组件、先眼球后矿工帽、已升级恢复存放及其他物品存放。
- 新增动作测试在旧实现上失败，修复后通过。完整输出：regression-2.0.2.txt。
- 独立离线实际引擎世界启用本机装备栏模组：10 PASS、0 FAIL、0 Lua 错误，最终进程退出码 0。用原版 PlayerActionPicker:GetUseItemActions 生成并排序左右键动作，再执行首个 GIVE；覆盖空燃料帽消耗、穿戴照明、卸下熄灭、重穿、重复拒绝、双升级顺序、存档恢复与容器行为。记录：engine-bag-mouse-2.0.2.log 及对应 result.json。
- 一次测试先完成 10 项检查，随后在原生关服阶段出现 CFileWriterThread 终止断言，退出码 3221226505；保留于 engine-bag-mouse-shutdown-assertion.log。未改产品代码，重跑正常退出。不能据此判定断言成因。
- 初次鼠标夹具错误假定原版矿工帽没有 tradable，记录保留于 engine-bag-mouse-initial-fixture-error.log；修正夹具后以上述最终原版动作测试为通过依据。
- 本次未操作图形客户端，未实测远端多人、洞穴切换或长时间游玩；未更改正式存档。

## 交付

运行包：dist/klbq_kanami-2.0.2-dst.zip；源码美术工程包：dist/klbq_kanami-2.0.2-source-art.zip。

本地安装 E:/steam/steamapps/common/Don't Starve Together/mods/klbq_kanami，以 2.0.1 文件清单校验基线后仅更新已改变文件，不删除整目录。固定待上传目录为 D:/SOFTWARE/DSTWorkshop/klbq_kanami。源码、安装副本、待上传目录及运行 ZIP 的逐文件 SHA256 一致，见 dist/package-check-2.0.2.json。

没有修改工坊下载副本，没有上传工坊。保存退出并完整重启客户端及世界，确认模组版本 2.0.2；房主与加入者需保持同一版本。旧包和旧存档保留。
