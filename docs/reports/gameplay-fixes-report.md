# 香奈美玩法审阅修复报告

日期：2026-10-27。范围：`docs/reports/gameplay-review.md` 的三项已确认缺陷及直接相关的动作过滤器 owner 生命周期。当前安装 `version.txt` 再读取为 **759671**。没有部署到游戏、启动客户端、修改原版脚本或用户存档；主任务的真实引擎验证结果另行记录。

## 修复内容

1. **延迟投掷攻击快照**（`mods/klbq_kanami/modmain.lua`）：`projectile.Throw` 优先复制玩家当前 `DoAttack` 上下文的攻击力、Z 倍率和武器引用。上下文已经在原版 `DropItem` 之前生成，因此吹箭、回旋镖移出手持槽后仍保留发出时数值。没有上下文时先使用投射物自身的 weapon，再使用 owner 武器或当前装备；独立投射物仍支持武器 owner。复制数值表而非共享可变上下文，complexprojectile 同样复制；其他角色重新使用实体时清除旧快照。原方法参数与返回值保留。
2. **客户端移动预测重建**（`scripts/prefabs/klbq_kanami.lua`）：按 locomotor 实例幂等安装加法速度包装，重复网络事件不会重复加 0.5。监听 `enablemovementprediction` 和 `playeractivated`，合并为零延迟刷新，避开原版“先事件、后创建组件”的顺序。刷新检查当前组件，C 布尔状态不变也能为新组件设置 `allowocean`。退出时恢复该组件原先的 ocean pathcap；幽灵不增加 C 速度。碰撞掩码仍按原有状态转换恢复。
3. **动作过滤器的同类 owner 生命周期**（`modmain.lua`）：通过 `AddComponentPostInit("playeractionpicker")` 给晚创建或重建的香奈美 picker 注册过滤器，保留 prefab 的初始兜底，每实例只注册一次。
4. **复活期间不可锁定**（`scripts/components/klbq_kanami.lua`）：保护期间临时包装目标方 combat 的 `shouldavoidaggrofn`。当前 vanilla `ShouldAggro` 明确以该回调返回 **false** 为拒绝索敌，故可同时阻断受击后的直接 `SetTarget` 和 `ShareTarget`。保留 `notarget` 的主动搜索保护；不新增或改动共享 `stealth` 标签。保护结束、死亡或组件移除时，只恢复仍由本模组持有的回调；保留预先存在的标签/回调及其他模组后来替换的回调。如果后来的包装持有本模组旧回调，保护结束后旧回调自动透传先前行为，不残留永久禁止索敌。

## RED / GREEN 证据

先新增 `tests/gameplay/test_review_regressions.py` 并运行，再修改实现。首轮修正测试夹具缺少 `combat.inst` 后，未修复代码产生预期断言失败：

- 原版 `Combat.DoAttack → DropItem → projectile.Throw`：吹箭快照 **34 ≠ 100**，回旋镖 **34 ≠ 27**。
- locomotor 重建：倍率 **1.3 ≠ 1.8**。
- 当前游戏原版 `Combat.SetTarget / ShouldAggro`：保护玩家仍成为目标。
- 独立投射物：重新计算得到 **60 ≠ 上下文记录 61**，证明没有沿用发出时上下文。

实现修改后最初 5 项测试全部通过；随后补充直接 Throw 无上下文、旧快照清除、complexprojectile 独立副本、晚创建/重建 actionpicker、第三方回调链清理等边界。最终 **9 项新回归通过；完整 gameplay 套件 39/39 通过**，其中包括全部 Lua 文件的 Lua 5.1 语法加载检查。

最终执行命令：

```powershell
& 'D:/SOFTWARE/CodexData/runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest discover -s tests/gameplay -v
```

运行时：项目已有 `tools/python-deps` 中的 Lupa `lua51`；Unicode 路径源码在 Python 侧读取后 preload，没有要求 Lua 文件 API 解析中文路径。正常输出包含原版移动预测开/关日志及 Mod 注册日志，没有失败或异常。

## 原版证据与验证范围

测试运行时直接从安装目录 `data/databundles/scripts.zip` 读取原版函数，不复制完整游戏源码到交付包：

- `components/combat.lua`：`DoAttack`、`SetTarget`、`ShouldAggro`、`ShareTarget`。
- `components/projectile.lua`：`Hit`。
- `components/combat_replica.lua`：`IsValidTarget`。
- `prefabs/player_common.lua`：`EnableMovementPrediction`（实际执行关闭、移除、重新创建及事件顺序）。
- `components/locomotor.lua`：`AdjustPathCaps`。

吹箭/回旋镖测试执行真实原版发射顺序，命中通过原版 `Projectile.Hit` 回到实际 Mod 的 `DoAttack` 包装，并在最终伤害接收点检查记录；没有手工预置一个正确快照来替代待测 Throw 钩子。索敌测试执行原版有效目标判断、直接锁定及共享仇恨，确认保护中攻击不解除保护、30 秒后恢复原行为。引擎实体、网络、物理、任务调度和最终扣血仍由轻量夹具提供。

因此本报告证明上述 Lua 行为及回归成立，**不等同于真实远端客户端预测、多人同步或实际游戏视觉验收**。仍须在独立游戏世界检查 C 水面移动和预测开关、投掷延迟命中、复活后主动攻击蜘蛛/猎犬的反击与共享仇恨、存档/重连/洞穴生命周期。虚空异界 2.3.2 的兼容性没有因此获得运行验证。第三方直接赋值 combat.target 或完全绕过 vanilla ShouldAggro 的自定义 AI 也不在本次已验证范围内。

## 真实引擎回传后的追加修复

主任务首次引擎烟测产生 9 PASS / 3 FAIL、无 Lua 异常，日志为 `docs/reports/engine-console.log`。此结果揭示轻量夹具未真实模拟的两项 API 行为，本子任务据此追加以下修复：

- **GetAttacked 没有返回值**：当前原版公共 `Combat:GetAttacked` 调用 `GetAttacked_Internal` 后不返回其结果。`damage.lua` 的 Normal/Planar 改为比较调用前后的目标 health.currenthealth，返回是否实际扣血，继续走原版 Combat 的护甲/位面/无敌结算。新增测试直接加载真实公共方法，内部伤害接收端模拟扣血或不扣血；RED 为 `nil != true`，修复后实际扣血为 true、没有生命下降为 false。
- **AnimState.GetScale 缺失**：当前引擎确实没有该 getter。`visual.lua` 在角色 common 初始化安装单实例 `SetScale` 透传包装，记录后续缩放值和写入版本；C 结束只在写入仍属本模组时恢复，保留外部后续改动和外部替换的方法。初始原版未写入的 AnimState 采用默认 (1,1)。新增缺少 getter 的测试：C 期间外部改为 (0.7,0.9)，退出不覆盖，下一轮 C 以此为基础缩放和恢复；RED 为 1 != 0.7，修复后通过。直接绕开实例 setter 调用底层原始 C 函数的第三方行为无法由此跟踪。

追加修复后的相同完整命令结果为 **41/41 通过**。引擎可否对 AnimState 单实例覆盖 SetScale 仍由主任务下一轮真实运行验证，不能用 Lua table 夹具替代引擎 userdata 结论。

复活烟测当时观察到“非 ghost 且 HP=0”。源码确认 `DoActualRez` 在完成原版恢复及移除 playerghost 后才发送 `ms_respawnedfromghost`，之后没有同函数内的血量覆盖。本子任务没有基于该现象猜测修改 OnRespawn；已要求主任务记录死亡、成为 ghost、开始复活、实际复活事件、状态图及睡眠状态，区分合成玩家从未进入 ghost 与真正复活后血量覆盖。后续真实运行结果以主任务引擎报告为准。
