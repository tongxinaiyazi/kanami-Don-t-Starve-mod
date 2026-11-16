# 香奈美玩法实现报告

日期：2026-10-26。依据 `docs/kanami-spec.md`、`docs/kanami-assets.json`、项目 AGENTS.md；目标 DST 759671 / Build 26148036。只编写项目源码与测试，未部署、未修改原版脚本、未触及存档。

## 实现

- `mods/klbq_kanami/modinfo.lua`：两端必装、0.1.0、C/Z/X 可配置及 Z 镜头距离。
- `modmain.lua`：角色/图集/配方、单槽装弹容器、无距离上限的原生自定义射击动作、服务端技能 RPC、动作过滤、延迟投射物快照、客户端入口。
- `scripts/prefabs/klbq_kanami.lua`：75/75/200，基础空手34，所有自定义网络变量在共同初始化中创建，默认/幽灵资源对接。
- `scripts/components/klbq_kanami.lua`：C、Z、X、复活与保护、计时持久化、枪械3秒玩家级冷却、消耗1弹、伤害回响与防递归。
- `scripts/klbq_kanami/rules.lua`：纯 Lua 数值/截止时间规则；存档保存剩余时间，切片新进程时重建截止时间。
- `damage.lua`：普通伤害走 Combat；位面走 `{planar=...}` 通道保留原版位面防御；真伤用 `Health:DoDelta(..., false, attacker, true)` 保留无敌/限伤；处决用 `Health:SetVal(0,cause,attacker)` 触发 minhealth/死亡/掉落/后续形态，另补 combat 击杀归属，不 Remove。
- `compat.lua`：集中第三方适配边界，不猜测混淆代码的内部对象，不永久改防御。当前只标准 health 路径。
- `domain.lua`：0.25秒/半径32；一个目标共享一份本模组倍率，最后一个领域离开才解除；所有玩家不吃生物减益，友好随从不减益；友方玩家最终速度系数加0.2并经原生外部倍率同步客户端。
- `camera.lua` / `client.lua` / `widgets/klbq_kanami_hud.lua`：本地按键、可点击技能图标、持续/CD/弹数/复活倒计时；镜头默认80、允许缩放；停止时只恢复仍由本功能持有的值和方法，保留之后其他模组的新值。
- `states.lua`：服务端与预测端射击/弦化进入退出/施法/复活动作，弦化 idle；使用约定的自定义动画，没有全部回退为原版动作。
- `scripts/prefabs/klbq_finale.lua` / `klbq_ammo.lua` / `klbq_kanami_fx.lua`：专属长枪、三种堆叠弹药、领域/示踪/复活特效。

## 接口核验

直接读取安装包 `E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip`，没有解压覆盖游戏：`player_common.lua`、`player_common_extensions.lua`、`combat.lua`、`combat_replica.lua`、`weapon.lua`、`health.lua`、`locomotor.lua`、`drownable.lua`、`map.lua`、`stackable.lua`、`container.lua`、`containers.lua`、`modutil.lua`、`mods.lua`、`networkclientrpc.lua`、`SGwilson.lua`、`followcamera.lua`、`playeractionpicker.lua`、`standardcomponents.lua`。读过随包 `scripts_readme.txt` / `MAKING_MODS.txt` / `modsettings.lua`。

特别核对：当前容器模块导出名是 `MAXITEMSLOTS`；Mod 环境无普通全局回退；`Health:ForceKill()` 也通过 DoDelta，处决采用 SetVal 跳过其限伤/吸收/无敌，同时保留 canonical minhealth/death 事件。

## RED / GREEN

运行命令（项目根）：

```powershell
& 'D:\SOFTWARE\CodexData\runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests\gameplay -v
```

依赖限定在 `tools/python-deps`，测试使用 `lupa.lua51`。Lua 5.1 的 Windows 文件加载不能正确打开本项目 Unicode 路径，因此测试由 Python 读取 UTF-8 源码并预载入 Lua；没有把该环境限制误判为游戏模组失败。所有 Lua 文件 UTF-8 无 BOM。

RED 已实际运行并观察：规则模块缺失；伤害/生命周期/镜头模块缺失；注册测试捕获 `MAXITEMS` nil；领域测试捕获敌对玩家误吃0.5倍率；C 测试捕获障碍内错误解除；末日弹测试捕获 noattack 形态误拒绝；洞穴 void 测试捕获未退回安全点。随后实现或修复并复测。

最新 GREEN：29 tests / 0 failures，包含全部 Lua 文件 Lua5.1 语法解析、受限 Mod 环境注册、配方材料和20发数量、C 叠加速度和生命伤害、物理障碍拒绝解除、洞穴 void 回退、Z 普通/位面仅1.5倍、命运暴击替换公式、跨时钟保存剩余时间、技能从施放算CD、早复活取消倒计时、自动复活1生命/半饱食/满理智/保护持续攻击不取消、枪单发消耗/换枪不能绕过冷却/回响不递归、延迟武器/Z快照与原返回值、普通限伤真伤/处决归属/位面通道、领域不叠加与最后退出恢复、镜头恢复和第三方新值保留、钓鱼与海钓工具动作过滤、C 几何压缩前后原有美术scale恢复及不覆盖其他模组后续scale。

## 尚需实际引擎验收

测试通过仅表示 Lua 数值/约束/生命周期桩场景和注册检查通过。本子任务没有启动真实游戏；未宣称已进入世界、远端联机、专用服、洞穴切片或长时间稳定。

必须实际验证：角色骨骼/所有自定义动作、客户端预测穿水及边界纠正、HUD桌面/窄窗口遮挡、原生无限距动作网络验证、自动复活后控制恢复及正常掉落、Save/Load/重连/洞穴、原版位面防御、特殊Boss minhealth阶段事件和多部件伤害。

虚空异界 Workshop2526778484 / 本机2.3.2 明确待测。其混淆实现如果把阶段存活逻辑置于自定义 DoDelta/SetVal/多部件代理里，标准 health 适配不等于已经兼容；需要独立世界覆盖普通/限伤/无敌/多部件后才能声明。

美术 contract：`klbq_kanami` build + wilson bank，自定义动作动画名见 assets JSON；物品共享 atlas `images/klbq_kanami_items.xml`；C仅用 AnimState x方向0.22倍，不缩放物理模型。领域FX源主环半径236px，运行时 Transform scale=`32*150/236`=20.33898305；native150px/world-unit已用当前原版 `penguin_ice.lua` 的 GetVisualBB 默认值和 `penguin_ice/anim.bin` 原始box逐个坐标核对，四个边界均精确吻合。领域动画1%轻微呼吸不改变权威扫描32半径。
