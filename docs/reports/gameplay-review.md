# 香奈美玩法独立审阅

审阅日期：2026-10-27。审阅对象为当前 `mods/klbq_kanami` 源码（新目录，无 Git 差异），依据 `AGENTS.md`、`docs/kanami-spec.md` 和 `docs/reports/gameplay-report.md`。本审阅仅写入本报告，未修改玩法实现、游戏文件或存档。

## 结论

- **规格符合性：暂不通过。** 核心结构覆盖了批准规格，但延迟投掷伤害快照、客户端移动预测组件重建、复活后的不可锁定保护存在可复现缺口。
- **代码质量：需要修复后复审。** 服务端权威、计时规则隔离、命名空间、领域共享修饰器和镜头所有权处理方向合理；现有桩测试没有覆盖几个实际引擎生命周期边界，29 项通过不足以证明这些行为正常。
- 本次未启动游戏，不对多人、实际客户端预测、素材或虚空异界 2.3.2 兼容性作通过结论。已知 `modinfo.lua` 的受限环境 `string` 问题由主任务修复，不重复列作本次新发现。

## 需要修复的发现

### 1. P2：投掷自身的武器保存成了空手攻击快照

定位：`mods/klbq_kanami/modmain.lua:120-121`；使用处 `scripts/components/klbq_kanami.lua:224`。

`projectile.Throw` 包装只在 `owner` 本身带 weapon 时使用 owner，否则读取攻击者当前手持武器。原版 `scripts/components/combat.lua:1168-1175` 先 `inventory:DropItem(weapon, false)`，然后 `projectile:Throw(self.inst, targ)`。因此吹箭、回旋镖等自身充当投射物的武器在该钩子执行时已从手上移除，owner 是玩家，`combat:GetWeapon()` 已经不是发出攻击的武器。快照落到 `Damage.Snapshot` 的空手基础 34。原版 `projectile.lua:236-256` 命中时仍以投射物实体为武器执行 `DoAttack`，故普通伤害与追加位面伤害对应不上。

本次定向 Lua 5.1 复现直接执行当前注册钩子：一个发出前 `attackcontext.power=100`、实体带 weapon 的吹箭，模拟原版 DropItem 后手上为空，再调用 `Throw(player,target)`。输出：

```text
THROWN_SNAPSHOT_EXPECTED=100 ACTUAL=34
THROWN_SNAPSHOT_EXPECTED_WEAPON=blowdart_pipe ACTUAL=None
```

这不是攻击后换武器测试能够覆盖的情况：现有 `test_delayed_attack_keeps_launch_weapon_and_z_snapshot_after_swap` 手工构造了已经正确的 `_klbq_attack_snapshot`，没有执行真正创建快照的 Throw 钩子。

建议：优先复用/复制发出该次攻击时的攻击上下文，并明确处理投射物本身是 weapon 的路径，保持对应武器记录与 Z 发出时状态。增加真实 DropItem → Throw → 命中顺序的回归用例；既覆盖吹箭/回旋镖，也覆盖武器生成另一个 projectile 的路径。

### 2. P2：客户端重新开启移动预测后丢失 C 的加速及水面寻路能力

定位：`mods/klbq_kanami/scripts/prefabs/klbq_kanami.lua:38-46`，以及 `:19-29`。

客户端只在创建 prefab 后的单次零延迟任务中包装当时存在的 `locomotor.GetSpeedMultiplier`。原版 `scripts/prefabs/player_common.lua:877-940` 的 `EnableMovementPrediction` 会移除并重新创建 locomotor；首次创建也依赖 `OnSetOwner`（`:1019-1024`）。关闭再开启移动预测后，新组件没有本模组的加速包装；如果 C 一直开启，`StringVisual` 因 `stringed == laststring` 也不会给新组件重新设置 `allowocean`。服务端仍按 C 速度和穿水规则运行，客户端预测失配。

本次定向 Lua 5.1 复现执行当前 prefab 的 common 初始化：先完成 C 开启状态初始化，再按引擎顺序替换 locomotor，并派发 `klbq_statusdirty`。输出：

```text
CLIENT_BEFORE_RECREATE=1.8
CLIENT_AFTER_RECREATE_EXPECTED=1.8 ACTUAL=1.3
CLIENT_AFTER_RECREATE_OCEAN_EXPECTED=true ACTUAL=None
```

建议：以组件实例为单位做幂等安装，在本地玩家激活、移动预测启用/组件重新创建后重建包装并重新应用当前网络状态。注意原版 `enablemovementprediction` 事件在组件创建之前发出，若监听此事件，应在创建完成后再安装。不要只检查 C 的布尔状态有没有改变；还需检查当前 locomotor 是否是已配置实例。相关动作过滤器也仅单次零延迟安装，应同步核查 `playeractionpicker` 的 owner 生命周期。

### 3. P2：复活保护中的主动攻击仍会被生物锁定

定位：`mods/klbq_kanami/scripts/components/klbq_kanami.lua:119-126`。

保护只增加 `notarget`。这个标签能阻止部分主动搜索，但不能阻止原版被攻击后直接 `SetTarget(attacker)`：

- 原版 `scripts/prefabs/spider.lua:306-328` 的 OnAttacked 直接 SetTarget，并共享目标。
- 原版 `scripts/prefabs/hound.lua:243-250` 同样直接 SetTarget 并共享目标。
- `scripts/components/combat.lua:473-481` 的 SetTarget 检查 `IsValidTarget` 与 `ShouldAggro`；`combat_replica.lua:292-309` 的 IsValidTarget 不检查 notarget，`combat.lua:424-452` 的 ShouldAggro 也不检查 notarget。

本次定向复现将游戏包中的上述三个实际方法加载到 Lua 5.1，使用当前 `Protection(true)` 创建的保护标签，再模拟被攻击后 SetTarget。输出：

```text
PROTECTED_HAS_NOTARGET=True
VANILLA_SETTARGET_PROTECTED_EXPECTED=false ACTUAL=True
```

生命伤害仍会被当前 DoDelta 包装归零，但“不被生物锁定、攻击/施法不打断”这部分规格未满足。现有测试只证明攻击事件不会清除保护计时，没有尝试敌方索敌。

建议：补充能覆盖原版直接 SetTarget/ShareTarget 的临时保护机制，并保留外部模组原有状态。当前原版 ShouldAggro 明确拒绝 `stealth` 标签（`:439-441`），也支持目标方 `shouldavoidaggrofn`（该回调的 true/false 语义与名称相反，需按源码处理）。应覆盖主动搜索、受击反击、共享仇恨及保护结束恢复，不应仅证明血量不降。

## 已核对且暂未发现明确缺陷的部分

- C/Z/X 与枪械伤害、随机暴击、弹药消耗及计时均在服务端；技能 RPC 核验玩家 prefab、存活、字符串参数并限流。客户端只发送技能请求、显示 HUD/镜头。
- C 通过 Health.DoDelta 将负数乘 0.2，后续仍走原版吸收；危险解除检查包含地图与实体重叠，边界/洞穴无效地块会退回 lastsafe。实际网络碰撞和移动手感仍需引擎验证。
- Z 的一般 Combat.CalcDamage 包装分别缩放普通与特殊伤害返回值；谢幕曲独立按快照乘一次，追加回响保留原版 planar 通道。回响先预留共享 3 秒 CD 再递归进入 Combat，避免同步 onhitother 再触发。
- 枪械 3 秒 CD 属于玩家状态，换枪不清除；装弹、存量、目标基本合法性检查在扣弹之前。普通 ATTACK 有过滤与服务端 DoAttack 阻断，未装弹不会以 34 伤害进行原版近战。无限距离自定义动作采用 `distance=math.huge` 与 `do_not_locomote`，仍需真实远端 RPC 路径验证。
- 命运弹 true damage 使用当前 Health.DoDelta 的正确参数位置，跳过常规吸收但保留 invincible、redirect、delta modifier、单次伤害上限。普通/暴击及 Z 数值表达式符合规格。
- 处决通过 SetVal(0) 保留 minhealth/death 原版事件与手动击杀归属，没有直接 Remove；这不保证所有第三方 boss 的自定义阶段代理兼容。兼容模块如实保持未适配状态。
- X 共享一份本模组修饰器并记录多个领域 owner，最后退出才恢复；敌对玩家不会吃生物减益，友好玩家是加法速度增益，生物只改伤害和移动倍率。实际客户端外部速度同步尚未运行验证。
- 自动复活遵循原版 respawnfromghost → DoActualRez → ms_respawnedfromghost 事件链。原版无 source 路径进入 reviver_rebirth，其 onexit 会恢复控制、HUD、皮肤与镜头，当前自定义复活动作中断该状态不会静态上漏掉这些清理。复活后的生命/饱食/理智设置、提前复活取消计时、剩余时间存读结构符合规格；实际读档/重连/洞穴仍待验证。
- 镜头保存了原距离/上限/仰角与方法，停止时只恢复仍属自己的值/包装；当前原版 ZoomIn、ZoomOut、ContinuousZoomDelta 直接写 distancetarget，与本模块的缩放追踪方式一致。

## 测试证据与剩余边界

原实现报告给出的 29 项通过为此前执行结果，本次没有重跑完整套件。审阅读取了所有玩法 Lua 模块及测试，针对上述三处疑点单独执行最小复现，三处均观察到预期与实际不符；第 3 项还直接使用当前游戏包方法验证。

核验来源为安装目录 `data/databundles/scripts.zip` 的当前分发脚本，包括 combat、combat_replica、projectile、complexprojectile、weapon、health、locomotor、playeractionpicker、player_common、player_common_extensions、SGwilson、cameras/followcamera、modutil、mods、boomerang、blowdart、spider、hound 等。没有以网上旧版镜像代替当前接口。

修复后应先运行新增的三组回归，再执行真实引擎独立测试：远端预测开关与 C 水面移动、吹箭/回旋镖延迟命中及换装、复活保护中攻击蜘蛛/猎犬并观察目标锁定。完整交付仍需角色动作/美术验收、多人/专用服、重连/洞穴/存档、普通/位面/真伤/处决归属及虚空异界 2.3.2 的已列明场景。
