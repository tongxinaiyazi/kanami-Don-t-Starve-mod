# 2026-11-12 2.0.0整合发布

当前版本2.0.0，纳入另一对话最新身体、侧眼、细小常态嘴型和工作弯腿修订，以及拓印终端铲头朝向修复。完整交付见docs/reports/release-2.0.0.md，安装和文件校验见dist/package-check-2.0.0.json。

---

# 2026-11-12 侧眼、细小常态嘴与工作弯腿修订

沿用当前 1.1.0。侧眼缩放从 0.11 提高到 0.15，中心调整到头部坐标 (20, -45)，已包含用户最后的右移反馈。常态保留约 3 单位宽的极细闭口线，张嘴说话及其他张嘴表情继续显示嘴型，开口限制在宽 7、高 5 内。眼和嘴分别随头部定位。

工作时腿部过短来自 leg/6 过紧的膝部折叠，38 单位腿部路径的髋踝跨度原本只有约 19.15。膝点调整为 (-15, 11) 后，髋踝跨度保持在 30 以上，腿部总长保持 38。原生动作时序、帧身份和脚底接地、跳跃轨迹通过回归校验。

当前编译资源通过 439 项玩法回归、47 项身体及工具专项、44 份 Lua 语法，153 个方向与动作、2996 帧，共 45,330 次接缝检查未检出问题。独立客户端已载入相同哈希的最终资源，复核正面及侧面待机、原生说话、砍伐、采矿与挖掘。三个工作目标均记录真实 worked，原生说话进入 talk 并播放 kanami_dial_loop。T 键模组保留，为爽而虐关闭。

当前截图为 body-v2-latest.png 与 joint-rebind-latest.png。后者为实际客户端截帧，临时隐藏周围景物并保留原生白天光照。数据与资源哈希见 joint-rebind-readback.json。本轮交付美术工程及源码中的编译运行资源，职责与交接见 docs/reports/profile-work-2026-11-12.md。本轮未新增第二台远端客户端、洞穴迁移、骑乘及全部特殊表情的游戏内验收。

---
以下保留为历史记录。

# 2026-11-12 1.1.0身体整合发布

采用身体V2最终交付稿，版本升级至1.1.0。当前身体与动作SHA256匹配joint-rebind-readback.json。发布与本地安装校验见docs/reports/release-1.1.0.md和dist/package-check-1.1.0.json。相同美术的游戏实测范围保留在下方修订记录中。

---

# 2026-11-12 腰部、手部与说话表情修订

本轮记录见 docs/reports/joint-rebind-2026-11-10.md 与 joint-rebind-readback.json。缩小嘴型，按实际虹膜校准侧眼，分离误入眼层的上嘴唇，并接入原生说话 dial_loop。腰部按整条接缝绑定，正侧面后发位于手臂后方，身体采用适度缩短的比例。

438 项玩法回归、39 项身体专项及 44 份 Lua 语法通过。153 个动作组合、2996 帧回读后执行 45,330 次接缝检查。实际客户端复核连续说话、正侧面、三方向移动、三种工作及正常食用。当前离线三视图为 body-v2-latest.png，实际说话截帧为 joint-rebind-latest.png。未重测第二台远端客户端、洞穴迁移及骑乘。安装一致性见 dist/package-check-1.0.1-joints.json。

---
以下保留为历史记录。

# 当前交付 1.0.1 身体 V2（2026-11-10）

已完成本次身体、五官与实际客户端复核，运行包已安装，固定上传目录同步完成。详细证据见 reports/body-v2-2026-11-10.md、reports/body-v2-compiled-readback.json 和 dist/package-check-1.0.1-body-v2.json。

- 当前身体权威源为 art/klbq_kanami/body-v2，132帧原创部件。body-pipeline.json 标记 active=body-v2，普通构建会使用该流水线。旧美术保存在 art/klbq_kanami/history。
- 正面眼线上移8、眼部放大约13%，侧面同步调整。眼睛与嘴部独立注册，自定义动作的面部锚点跟随头部面区。身体关节矩阵保留原版，宴席使用原生服务端及客户端队列。
- 434项玩法回归、23项身体专项、44份Lua语法通过。编译58动作、1263帧，935个五官锚点误差不超过0.0000082。
- 六类生存动作6614次关节检查，可见间隙告警0。五处被完整遮挡的几何间隙仍保留记录，不宣称所有关节的几何轮廓重叠。560个正侧头颈帧中559重叠，另一帧距离1.414，背面由披发覆盖单独评估。
- 实际客户端完成待机、正常食用肉丸、控制事件触发的移动、九组工具操作、慢动作三投影及恢复圆盘、三把武器正侧背握持。T模组保留，为爽而虐关闭。真实输入使用发往已验证拥有窗口的 WM_KEYDOWN/WM_KEYUP，SendInput 在本次 SDL/IME 环境中未被游戏接收。取移动截图用现有PowerShell窗口截图，PrintWindow前台可能全黑。
- 已清理无敌、notarget、临时灯光、缩放与输入，测试客户端和专服均已退出。界面只保留最新三视预览 reports/body-v2-latest.png 作为优先参考，不携带大量旧图片。
- 源码、运行ZIP、固定目录 D:/SOFTWARE/DSTWorkshop/klbq_kanami 与游戏 mods/klbq_kanami 共91个运行文件逐一SHA256一致。仅清理本任务游戏安装副本，源码和旧包保留，未上传工坊。
- 全部特殊表情、骑乘、远端第二台客户端、洞穴迁移和长期生存继续按计划补充验证。资源终端计划仍保留清晰地面四灯对照图的待补记录。

---
以下为历史记录，不作为当前候选的验收结果。

# 当前：1.0.1肩肘分层修订（2026-10-31）

已完成最终386项回归、实际空手/持枪跑步与普通进食复查，截图/日志与边界见docs/reports/verification.md。用户要求参考其他模组，已对照本机纳西妲和符玄，结论见docs/reports/rig-reference-review-2026-10-31.md；不复制第三方美术。

78个原创身体PNG和registration.json现为权威输入，编译禁止自动裁边或套原版框。跑步整链平移、进食整链限抬肘；编译前后角色build/atlas与实测资源完全相同。先前1.0.1结论已撤回，旧包保留superseded目录。部署/包完整性以dist/package-check-1.0.1-rigfix.json为准。最终GUI测试已经关闭，恢复测试无敌/照明/镜头；无为爽而虐，T保留。未测第二机/洞穴/全动作，不携带大量旧图片，只记最新rigfix截图路径。

---
下方均为历史记录，不作为当前结论。

# 2026-10-31 用户否定1.0.1美术验收，本轮正在修正

撤回下文“部件已连接”的整体美术结论。旧测试只覆盖腕踝，漏了肩肘；新增检查在旧资源复现170处断接和重复上臂。已新增torso-rig-atlas.png并只绘制arm_upper，修订原生肘跨度，9项资源与382全量回归通过。目前还在真实客户端复查，不将新资源当作已正式部署。

---

# 当前交付：v1.0.1（2026-10-31）

普通随机种子照料催熟、手脚切片枢轴与弯腿帧、三弹角色文案均已修订。最终381自动回归通过，原生基础＋装备栏69项通过；真实客户端重新加载最终资源，复查正侧背站姿、谢幕曲持武、实际按键跑步和原生EAT。局部姿势还用本地临时实体固定帧检查，不能把它算成实际玩家输入。查看到的腕踝已连接，尚未覆盖全部动作／装备组合。

已打包并部署1.0.1；77运行文件在源码、ZIP、英文上传目录和游戏安装逐文件SHA256一致，工程ZIP CRC通过。游戏中本任务旧canonical／verify／test／client_qa已移除并安装唯一canonical；本地源码、历史包和其他模组保留。详情dist/package-check-1.0.1.json。上传目录D:/SOFTWARE/DSTWorkshop/klbq_kanami_v1_0_1，填表docs/kanami-workshop-v1.0.1.md，未自动发布。

独立QA客户端与服务端已退出；用户允许的临时无敌／补满状态任务、照明、镜头缩放均清理。测试后关闭为爽而虐，保留两个T模组。远端第二机、洞穴、长测、全Boss阶段和全动作仍未覆盖，不宣称原始计划全量完成。证据只需记住docs/reports/verification.md、visual-1.0.1.png和两份1.0.1日志，不把旧图片带入上下文。

---
以下为历史记录，旧待办和旧版本状态不作为当前事实。

# 1.0.1 仍在修复，禁止宣称美术已完成（2026-10-30）

用户明确否定上轮手脚连接。当前未打包/未部署正式目录。普通随机种子白名单和实体替换修复、三弹角色文案、源码1.0.1已改。380自动回归和69原生基础+装备栏通过，原生记录docs/reports/engine-base-equipment-result.json。随后美术仍改动，不把旧测试等同最终美术验收。

新发现：横向arm_lower 2/6原生腕点约(-40,15)，之前错误按(-30,0)处理；run/eat大量手腕断开。新tests/gameplay/test_assets.py::test_animated_wrist_and_ankle_layers_touch_in_survival_poses实际投影idle/run/eat各帧alpha检查，起初159处断开，修订后只剩2处，刚调整前臂0长度44与弯腿6踝端(-14,25)并重编译，最终测试输出见本轮工具返回，需核实再记录。校验重叠仅是必要条件，仍须真实客户端看外观和持物遮挡；手臂袖口/躯干重复等也需看。

工具临时目录D:/SOFTWARE/CodexData/temp/kanami_assets。inbox真正路径为D:/SOFTWARE/CodexData/temp/kanami_engine/interactive-command.lua，不在Master目录！旧备注错了。QA当前实际加载verify1.0.1，但之后改动还没重载。正式klbq_kanami仍1.0.0。保持关闭为爽而虐、保留两个T模组。不要携带大量旧图片，只保留路径及结论。

下一步：最终资源重启独立GUI，固定健康安全actor，检查前侧背空手/持物、跑步和进食，不以部件像素重叠当成美术完成。成功后更新规格、计划、验证文档和release1.0.1目录，再打包部署。所有1.0.1发布资料/包目前尚未生成。

---

作者修订已验证：1.0.0作者为奈娅子，游戏内简介仅“模组交流群：1131263408”。源码／上传目录／包／本地部署77文件一致，旧游戏副本已清理；工坊须用户Update Data重新上传，本轮未操作发布。以下旧的“未部署1.0.0”说明已由本次部署结果取代。

# 当前交付：v1.0.0版本打包（2026-10-30）

基于0.2.6，只更新版本标识与交付说明；运行源码modinfo／加载日志为1.0.0，美术及玩法与0.2.6一致。英文上传目录D:/SOFTWARE/DSTWorkshop/klbq_kanami_v1_0_0，完整填写见docs/kanami-workshop-v1.0.0.md。包CRC与哈希见dist/package-check.json；旧包和0.2.6清单保留。未操作上传器、未Publish，当前运行游戏安装副本仍是0.2.6，不误称已部署1.0.0。

本次入口与Lua语法3项检查；此前378回归和GUI实测保留0.2.6归属，不新增覆盖声明。后续实际验证不得开启为爽而虐，T模组保留。以下是历史记录。

---

# 当前状态：0.2.6实测修订（2026-10-30）

最新依据：docs/reports/verification.md、docs/kanami-spec.md、dist/package-check.json。378回归通过；本轮原生基础68与关闭为爽而虐后的实际F连续射击／X内蜘蛛和熊獾圆斩已验证。圈、中文发言和无背包按钮实际可见。连弩又发现弹弓姿势锚点问题，已改站立锚点、重编译并完整重启复查正背面。后续实际验证不得启用为爽而虐，保留两个T键模组；先前兼容证据作为历史保留。

独立QA客户端和服务器已清理临时状态、保存并正常退出；不操作正式存档和其他任务模组。最终包／部署以当前manifest与package-check为准。远端第二台机器、洞穴、长测、全部美术动作及Boss阶段仍待验收；不能宣布整个计划全量通过。不要携带旧截图压缩上下文，只保留结论和必要路径。

---

以下为历史记录，旧版本号、PID、待办与进程状态不作为当前事实。

# 2026-10-29 actual visual follow-up - IN PROGRESS

User requests real verification; do not carry screenshots into context. Keep paths and conclusions only.

Current source version 0.2.6; installed/package 0.2.6 is an EARLIER test snapshot (only FX fix), so REPACKAGE AND REDEPLOY after final checks. Source changed afterwards for Happy curse and X retaliation.

Verified native UI: 0.2.5 bag lock/sort/collect gone. 0.2.6 actual ring visible with 12-unit flint markers. Root: uniform Transform scale on OnGroundFixed has non-linear/doubled scaling; use unit Transform, AnimState scale 1.5*radius/4. Also no obsolete domain animation before bank switch. Tests test_ground_fx RED 6 subcases -> GREEN.

Speech reappeared after cursed equipment: installed HappyPatch role/haitang_curse_2.lua mutates Talker:Say before broadcasting when classified.take_cursed_item_num true (net_bool). Prior display guard cannot undo. New curse.lua AddComponentPostInit haitangcurse2hm disables only Kanami DoInit tracking and resets character flag, leaving other players intact. test_happy_speech_curse uses real installed tracker RED -> GREEN. Needs native GUI cursed-item recheck after reload.

User NEW requirement: X blocks passive aggro only; own attacks may cause retaliation/herd assist. Implemented domain.CanRetaliate + scoped native ShareTarget context, leave notarget only for revive protection. Scan preserves provoked targets. tests/test_domain_aggro 7 pass; added native content.lua beefalo hit + herd + scan test. No final native result yet.

Full unit run failed 8 because new domain.Install not preloaded by restricted registration/speech fixtures, fixed those fixtures; targeted registration3 and speech7 now pass. Last completed full run 377 tests had these fixture errors; rerun full suite before claiming green. stdout Lua logging flushes after unittest summary so search entire log, not just tail.

Native base+equipment is RUNNING via exec session 8231, --seconds210, --isolated-mod-copy. Inspect docs/reports/engine-base-equipment.log/result.json. Old interactive server stopped. No GUI client currently open; own launch helpers installed client QA removed by deploy then prepare recreates. Native actual GUI still needed for crossbow F pose + Requiem RMB with X/Boss/spider + cured speech.

Tools new: tests/client_mod, tools/prepare_kanami_client.py configure ONLY own profile D:/SOFTWARE/CodexData/temp/kanami_client/storage/KanamiClientTest/1764465191/client_save. Both T mods1365141672 and2763963752 preserved. Client QA autojoins127.0.0.1:11016; autoaccepts ONLY mod warning; removes residual LobbyScreen after direct spawn. KANAMI_QA.After wraps scheduled QA in pcall. Do not assign undeclared global in commands (strict.lua); use actor fields/rawset. One earlier own diagnostic did so and raised error overlay, not mod bug; log preserved.

kanami_client_qa.py now PrintWindow --background, --hold-key for sequence (finally releases keys), click --right, brief Win32 focus. Only own PID from client-process.json. Need cleanup/release key state at end.

run_kanami_engine --interactive --playtest --equipment --happy --void --user-visual-mods --seconds7200 uses own existing test world, matching9 user mods+Lilith. Priority fixed so interactive wins Happy mode. Query/auth ports27017/8767 avoid other task. User/all other task have been closing own test client occasionally; use only own process, never kill others. Lilith canonical updated during test0.1.2 ->0.2.0 caused SERVER_MODS_NOT_ON_WORKSHOP on rejoin until own server reload.

No modifications to Lilith source or .lilith-task-owned installs. Deployer now cleans OWN klbq_kanami_client_qa too. Source packager includes own QA tools/tests, no Lilith files.

Next: native base result -> full units -> package/deploy fresh source0.2.6, start interactive and own client for final visual+input checks, then reports/spec/plan/manifest hashes final package rebuild+deploy cleanup test folders. Preserve C/D formal saves. Do NOT claim whole task complete from prior static counts.

---

# 当前继续点：0.2.5（2026-10-29）

最新事实以docs/reports/verification.md、规格、实施计划与dist/package-check.json为准，优先于下方历史交接。此次用户明确新增：发言仍坏、领域视觉巨大、连弩动画、圆斩只特效（蜘蛛开X，Boss也无伤）、背包按钮未消失、移除蜘蛛招募。均已修代码并补验证，夜间圆斩光照门为新增确定根因。

373回归通过，原生海面载入、外部复活、Z睡眠费用、夜间开领域熊獾圆斩已验证。游戏已更新760178，Happy2.8.14.90，不能套用旧759671结果。不得控制用户游戏，沿用先部署自行重载，保留T；另线程的.lilith-task-owned测试副本在用，不删。最终部署由verification.md和package-check记录。

---

以下为旧版本历史，不作为当前进程事实。

# 当前继续点：0.2.4（2026-10-29）

当前规格、计划、验证优先于本文件下方历史记录。已部署0.2.4，77运行文件与源码一致，工程包788项；游戏旧副本已清除。最新生产代码和资源已经修订，337回归、49语法、67基础引擎、18武器、9组合背包、15组合武器输入、19Happy通过，退出0。图形窗口未操作，用户最后授权先部署自行重载；保留T模组。不要引用下方0.1.0 PID或进程状态，它们是历史记录。

新需求已写docs/kanami-spec.md及docs/superpowers/plans/2026-10-28-kanami-implementation.md。晶体首材料是lunar_seed，不是moonrockseed。最终包和安装结果以dist/package-check.json和verification.md为准。

---

以下均为历史交接信息，不作为当前环境与进程事实。

# 香奈美任务继续点（2026-10-27，压缩用）

## 用户最新指令

继续完成已批准的DST香奈美角色模组。用户此刻要求准备上下文压缩，避免携带大量中间截图。只保留文字事实和必要路径，后续按需重新截图。

- 死亡使用饥荒原版轮廓的香奈美幽灵；C为完整有腿纸片人。
- 最新反馈：C不要怪异迈腿，改为静态纸片平移；夜里角色异常置顶；谢幕曲像没伤害、牛不反击。
- 已解释夜里突出和部分不反击是本任务GUI测试强制提亮、无敌、停止牛AI造成，已在旧测试场撤掉。复活保护本身30秒不可锁定，保留。
- 又查到真实伤害通道独立漏洞：直接扣血没有attacked事件，已修复并真实专服验证，不能仅归咎测试设置。
- 下次启动实测要有T键模组，结束保留游戏给用户继续测试；用户已经亲自启用。日志确认task profile的Too Many Items Plus（Workshop1365141672、1.1.3）已加载，不要再改其配置。用户正在同时操作桌面，窗口聚焦曾被系统拒绝；不要反复抢占其窗口。

## 源码与环境

工作区 `D:/SOFTWARE/项目/饥荒`，无Git。源码 `mods/klbq_kanami`，版本0.1.0，两端必装；完整数值规则见 `docs/kanami-spec.md` 和模组README。游戏DST759671，Build26148036，游戏 `E:/steam/steamapps/common/Don't Starve Together`，scripts.zip是当前API依据。临时目录D盘，不改正式存档、不上传Workshop。

Python：`D:/SOFTWARE/CodexData/runtimes/codex-primary-runtime/dependencies/python/python.exe`。Lupa Lua51在tools/python-deps，Pillow可用。官方Mod Tools已安装，构建器内部路径可用。

本轮已读相关技能：执行计划、子代理开发、代码审查、TDD、验证、imagegen、系统调试、截图等。requesting-code-review明确要求子代理，故已有只读final_review代理，其他旧代理已结束或额度用尽。没有使用相关memory内容，不需memory citation。

## 已实现和最新修改

基础机制、三弹、全部技能、复活、配方、HUD及镜头已实现。普通武器动态攻击快照，枪被动34，Z一次倍率；真伤遵循无敌／限伤；末日当前形态标准SetVal死亡而非Remove。

最新反馈后：
- `states.lua` 对idle/run_start/run/run_stop及gallop/monkey移动状态使用单帧kanami_string_idle，抑制弦化移动timeline脚步。构建器相应idle缩为1帧，all已重建，SCML已同步。
- 审查发现原移动回调GoToState后包装会覆盖新状态循环动画，已加currentstate前后身份判断；新增回归，**49/49通过**。最后这个P2修复后尚未重新跑真实GUI／完整引擎，但部署由刚启动的playtest launcher复制。
- `damage.TrueDamage` 新增存活目标实际受伤后的attacked通知及lastattacker等记录，保持原版牛群反击；没有强制绕过复活保护锁定。
- `Shoot` 记录实际生命损失，新增共同网络变量net_float/net_entity/net_byte序号，客户端HUD原版ShowPopupNumber显示实际扣血；modmain增加原版impact命中特效。原有tracer仍为简单视觉线，尚未精修到准确端点。
- visual.StringBuild隐藏swap_object避免C悬浮枪；恢复原build及符号；原生AnimState是userdata，没有GetScale，不可覆盖SetScale。
- OnRemoveEntity接到OnRemoveFromEntity清理，修复断线／迁移后领域残留。

## 验证

- 最新单元／真实脚本函数／资源检查 **49通过**。最后命令 `python -m unittest discover -s tests/gameplay -v`。
- 真实专服最新 **14通过、0失败、0Lua错误、退出0**，`docs/reports/engine-base-result.json` 和engine-base.log。包含真实等待60秒复活1/37.5/200与30秒保护；新增测试关闭被动后命运弹独立令牛combat.target==player。
- 最新虚空异界2.3.2复跑 **8通过、无Lua错误**，`void-combat.log`；发生在最新状态机P2小修之前（只改视觉状态）。史莱姆王及人工秩序目标；机械多部件直接生成错误在关闭香奈美对照下复现。不得宣称全Boss／自然阶段／多部件兼容。
- GUI此前已见普通／纸片／幽灵、选角、持枪、20弹槽、HUD、Z高空与恢复；用户也在交互。**新静态平移／飘字尚无最新GUI证据**。不要把旧截图当新版本证据。
- 一次临时控制台探针误用不存在GetCurrentAnimationName造成Lua错误，保留gui-probe-failed.log，非模组代码；后续已不使用。并行专服曾端口竞争退出断言，最终单服14项退出0。
- 跨机器双人、真实洞穴迁移／跨分片恢复、长测、所有装备动作及Boss自然流程未验证。

## 当前进程与交接环境

图形客户端任务PID **35672**（重新核验），T模组已由用户启用。辅助状态 `D:/SOFTWARE/CodexData/temp/kanami_client/client-process.json`；客户端独立日志在storage/KanamiClientTest/client_log.txt。

刚启动命令：`run_kanami_engine.py --interactive --playtest --test-admin <从新测试cluster/adminlist.txt读取> --until-client-exits 35672`，外层exec session **需查看最近工具返回的session ID**。工具监听任务客户端进程，用户关闭客户端时关闭专服；只授管理员给独立测试档的该玩家，让T键命令可用。

新干净测试世界 **KanamiPlaytest**，LAN名 **Kanami Playtest**，端口11016；不复制旧有大量测试尸体／停AI牛的KanamiVisual；pause_when_empty=true，没人时暂停，所有光照/AI/无敌为普通游戏默认。未保证用户已经加入；当前不宜抢桌面。

server存储 `D:/SOFTWARE/CodexData/temp/kanami_engine/DoNotStarveTogether/KanamiPlaytest`。world已生成，本次是重载，等待启动日志Sim paused／无Lua错即可判断可加入。脚本刚改playtest的Sim paused也算ready，因为空服暂停时3秒测试定时器不会运行。

## 美术与工具

完整工程 `art/klbq_kanami`。无需携带旧图，仅按需读最终 `ghost.png`、`paper-turnaround.png`、`portrait.png`、`rifle.png`。普通分层与Spriter工程在parts/和spriter/；exported/含build.xml、帧PNG、动作XML。官方参考文件只在references/，不得放运行／工程发布包。

`tools/build_kanami_assets.py --only all`：所有PNG通过官方Python27 buildanimation／TextureConverter编译，真实BILD/ANIM/TEX，不是伪ZIP。

幽灵重要：当前player_ghost_withhat的idle真正画ghost_tail，原先仅ghost_body不可见；已改为ghost_tail带完整原创幽灵图，其他层透明，实际GUI已确认。

领域原生单位150px/世界单位，有官方Units.py与range FX标尺；保留32*150/236≈20.339，不能凭屏幕边缘改小。层上已加SetSortOrder(3)。

## 尚待完成

1. 查看新playtest服务器启动／用户T配置存在即可，不强行控制桌面。新C平移／飘字如无前台访问，诚实注明尚未GUI重验；可交用户继续试。
2. 文档数字更新：verification.md刚把45/13替为49/14；kanami-progress.md首段仍45/13，应同步；将最新反馈修复、T环境、P2状态判定加入验证边界。
3. 最后部署哈希对比，确认完整源与游戏副本相同。刚启动launcher会copytree复制当前P2后的全部源码。
4. `tools/package_kanami.py` 已写但**还未运行**。运行生成dist/klbq_kanami-0.1.0-dst.zip（根modinfo/modmain）和source-art.zip及manifest。检查排除官方参考、依赖、旧稿、测试存档/日志；当前工具会把历史报告MD及必要测试代码放工程包，不会运行包携带测试。
5. 如继续改代码，按影响测试，别无限重复。编译all刚完成，最后P2只Lua修改无需重新编译。
6. 最终给简洁中文说明、运行包／源码美术包／README路径，区分49/14/8与未测试项目；保留用户游戏与T配置。

补充最后状态：当前playtest外层exec session为 **22256**；服务器最新日志已到 **Sim paused**，无玩家时暂停待加入。最新P2修正后的states.lua与游戏部署副本SHA256一致。

## 清理限制

旧void代理曾收到自动安全审批拒绝删除它的临时测试目录，未给具体原因，未重试绕过。目录为D:/SOFTWARE/CodexData/temp/kanami_void_test以及game/mods/klbq_kanami_void_test。不要换方式绕过删除；保留且排除交付包。如最终仍保留，开发者要求commentary和final末尾单独短段说明“自动审批拒绝了临时测试目录清理，未给出具体原因；这些目录已保留且不在交付包中”。不要反复要求用户批准。

Workshop2526778484的任务联接本轮曾消失（可能客户端刷新），已确认源目录仍存在后重建同名junction供本轮8测试；不修改第三方源。不要广泛清理用户mods、资源运行时或生成工具原件。

## 压缩后继续完成的交付（2026-10-27）

- 最新49项回归已重新执行通过，编译anim.bin中kanami_string_idle各方向确认为单帧。
- 已生成并复核dist/klbq_kanami-0.1.0-dst.zip（49文件，约1.76MB）、source-art.zip（655文件，约23.07MB）。manifest.json记录SHA256，package-check.json记录独立完整性检查。
- 源码、部署副本、两个包内的49个运行文件哈希全部一致；部署目录额外只有任务所有权标记。
- 工程包排除官方参考、依赖、日志、存档、旧稿、内部交接和过期报告；包含SCML全部分层图片、构建工具、测试源码及当前文档。
- 当前无新增玩法修改。14项真实引擎和8项虚空测试记录已再次读取确认，但未重新运行，之前的验证范围及时间界限保持。
- 本轮再次尝试聚焦游戏，系统拒绝，未发送游戏输入。最新静态平移／飘字GUI复验仍未完成。客户端35672与专服7600维持运行，任务服务器在空服暂停状态等待用户加入“Kanami Playtest”；T模组加载记录存在。
- 不要再次运行打包除非交付内容有修改；不要关闭用户测试客户端或专服。

## 用户要求清理临时文件后的状态

用户于2026-10-27明确要求删除临时文件。只读确认约149 MiB任务废弃产物，64张中间截图；发现用户已在独立客户端的Cluster_1运行Master/Caves，必须保留该存档与配置，以及仍活动的KanamiPlaytest与测试夹具。原生PowerShell删除命令（显式路径、解析路径校验、禁止联接遍历、保留在用内容）在创建进程之前被自动审批以blocked by policy拒绝，没有更具体原因，本轮未删除任何文件。没有换工具绕过。候选清单与拒绝结果见reports/cleanup-2026-10-27.json。不要把待清理清单当作已删除记录。

## 0.1.1最新交付（以本节为准）

用户反馈敌对目标无法射击、活人作祟、侧面异常、枪弹落地太小，新增头顶射击CD条及左下角图标数字横栏。已实现并部署至实际游戏mods目录，版本0.1.1，50个运行文件SHA256与源码、两个交付包一致。dist/manifest.json与package-check.json已更新；运行包约1.70MB，工程包约24.78MB，673文件，SCML引用完整。

原版PlayerActionPicker过滤栈只激活最高优先级，旧PushActionFilter(Allowed,1)压过活人ghost_exclusive过滤；敌对/Ctrl路径直接生成ATTACK并绕过EQUIPPED。改为包装SortActionList，在保留原过滤栈的前提下将持枪ATTACK替换KLBQ_SHOOT、绑定gun invobject并施加C/枪托限制。原版真实动作函数新增测试已先复现后修复。

原版idle_loop躯干方向0/3/6，不是0/1/2循环。普通及纸片方向均修复；补充directional-atlas.png及12个部件，通过内置image_gen生成，提示词在directional-prompt.txt，普通角色四肢改用垂直部件、方向裙摆和靴子，缩短并偏移长发避免遮脚；官方编译器已重新编译角色、纸片、枪弹、UI并同步SCML。落地画布枪240x80、弹64x112/72x120/80x128；背包及手持不放大。

HUD现左下角六图标横排，C/Z/X/回响/复活/弹药，常显数字；新增klbq_skill_echo图集项。new widgets/klbq_kanami_shotbar.lua用原版square.tex绘制跟随头顶的冷却条，客户端根据服务器shotcd插值、暂停时停止，准备和幽灵时隐藏。API应使用ImageButton:SetImageNormalColour，没有ImageButton:SetTint。

最新57项回归通过，两次独立只读审查完成。审查发现的纸片方向映射已修复，新增实际native-facing回归。0.1.0原生引擎14和虚空8记录属于历史，不冒充新版GUI验证。

用户先允许“现在保存并重载继续实测”，已通过其独立客户端向Cluster_1发送c_save并观察地面/Caves写入，后打开断开确认对话框但没有确认。用户期间自行继续了游戏、报告依然旧bug；当时游戏目录确实尚未复制新版，已明确解释。后来Windows拒绝切前台，用户最新明确选择“先部署，我稍后自行重载”。从该答复后没有再操作GUI，不应继续尝试接管窗口。T配置、存档及在用进程保留。当前内存运行的仍可能是0.1.0，已告知完整退出并重启游戏（同时重载服务器）；不能声称0.1.1已在GUI实测。

清理临时目录被策略拒绝的事实仍见cleanup-2026-10-27.json，本轮没有删除或绕过清理。新方向补图保留工程，旧版交付ZIP保留，勿当垃圾删除。此后继续应先读取本节，勿重做已完成打包。


## 0.2.0 当前接续（2026-10-28，以本节为准）
源码现已含最新全部6项：弦能奇点14格出生/反鲜-.1/真实BACK兼容，沃利三正面标签与蛋包饭双产、黄红新鲜收益50%/10%，外国枪反噬、晶体落地私有科技、忍锋51/600，Z改toggle无CD时限/400san每分钟。前轮S1位面+当前5%真伤/1.5CD、枪1.5CD、新侧眼/装备隐藏/领域清理与填充FX全部合并。新增PNG内置imagegen生成并保存本项目，全部官方资源编译已完成SCML同步。
145项Lua回归通过；真实引擎+四五六格装备栏2.4.0默认配置25通过/0Lua错误/退出0，engine-base-equipment-result.json。首轮24有一项末日SG同步检查过早，改为真实.25s异步后通过，无生产死亡改动。最新虚空2.3.2抽测8过/退出0，void-combat-020.log。Z成本与blade使用已固化9项test_z_blade。
尚未最终打包/部署0.2.0，应完成docs后package_kanami.py再校验runtime/source-art/deployed全SHA，更新package-check。现游戏正式目录仍0.1.1，验证副本是game/mods/klbq_kanami_verify（显示开发验证副本），不要启用为正式mod。保持用户最新“先部署稍后自行重载”偏好，不接管GUI，不改T配置/存档。0.2GUI未复验。当前engine/void任务均已正常退出，无任务native服务器待关。旧临时清理拒绝仍未绕过。

0.2.0最终交付已完成：dist/klbq_kanami-0.2.0-dst.zip=63文件1801069字节；source-art.zip=730文件32368408字节。运行源码、实际游戏mods/klbq_kanami、两ZIP内运行文件SHA256逐项一致；SCML引用完整，额外部署文件仅.kanami-task-owned。manifest/package-check当前均0.2.0。README/spec/verification/BUILDING/assets索引已同步145/25/8及GUI未复验。没有接管用户GUI或修改T配置/存档；需用户手动完整退出重启游戏让两端加载。145回归最后一轮通过，无后续生产代码更改。测试native服务器均正常退出。新PNG提示词存于art，工程/包保留，历史ZIP保留用于回退。自动化工具搜索automation_update为空，不得声称已删除提醒。


## 0.2.1本轮仍在实施（最新用户追加范围）
尚未打包/部署0.2.1！实际部署仍0.2.0。用户确认黄红食物须在原版腐败收益上再乘.5/.1，chef已简化保留原版getter；原版STALE_HUNGER=.667 HEALTH=.333，从native读取测试。末日归属修正已做：combat.lastattacker在SetVal之前，cause使用射手nameoverride/prefab，afflicter/loot/killed均射手；Execute现补healthdelta和ondelta。
用户又增加X：免仇恨、不额外免伤；自动免费招募原版可雇生物、保护已有/离线归属；领域内Pearl满10级并原版发奖不刷。新增hermit.lua/recruit.lua，真实原版NPC没有health，domain已独立调用Hermit再过滤健康生物。Protection合并X/复活tagownership而免伤只复活；移除组件先清state使capturedhooks惰性。新增unit和engine performance.lua，真实X/招募/pearl投出+反复扫描已见PASS。root native当前session32013，--seconds240 --isolated-mod-copy --equipment；启动耗131秒，完整结束预计223秒。
用户最新三弹都要绕限伤限频。ammo_limits代理已做damage.BulletNormal/BulletTrueDamage/BulletDelta绕实例combat/health函数与deltamodifierfn/cap，保留明确阶段invincible/redirect/minhealth及普通护甲吸收。物理弹沿原版Combat实际redirect链接入，对实际受伤体receipt累计，rifle反噬/HUD正确；所有临时方法/redirected_from异常恢复。S1与外国反噬不额外绕限。review两个P2(重定向伤害/第三弹健康回调)已修，26项ammo/rifle独立复核通过。代理报全套192，root最终完整复跑待统一确认。
engine fate cap改HP1000/cap20，子弹300+原被动cap20+cap20=>剩660。void kingcap新测实际枪心弹41+命弹300绕cap1/private gates，已写待跑。当前首轮0.2.1 food/doom曾149+native25+void8通过，但不是最新X/全弹绕限验收；必须以新native/void复跑为准。源码version/package_VERSION均0.2.1，dist0.2.1尚无包。README/spec已更新最新X/三弹，先暂写192/29待实测校准。最终verification/void记录/包/部署/manifest/hashes还待完成。保留T配置及手动重载偏好，不GUI、不接管正式世界、不删旧包/旧拒绝清理目录。

0.2.1最终已完成打包与本地部署。194项回归、29真实引擎+四五六装备栏、8虚空抽测通过；最后自身C/复活防御守护由原生函数增量回归通过，未重跑整PvP场景。源码、部署、运行包与工程包运行文件SHA全部一致；manifest与package-check已更新0.2.1，额外部署仅所有权marker。无需再打包/测试，除非又改代码。GUI未接管，正式存档/T配置未改，用户须完整退出重启加载新版。所有任务native服务器已退出，旧ZIP保留，勿上传Workshop。

2026-10-28 用户要求更新计划：正式汇总计划已写docs/superpowers/plans/2026-10-28-kanami-implementation.md，完整归并所有追加需求与完成勾选/待验收项；详细spec与progress同步。已将计划加入工程包allowlist并更新0.2.1源码美术ZIP（738文件）；运行ZIP SHA不变，源码/部署/两包65运行文件仍一致。dist/plan-check.json记录文档检查和原194/29/8证据引用，本次没有新增玩法或重跑游戏，不要将文档更新误报为新测试。


## 0.2.2最终交付（2026-10-28，以本节为准）
全部本轮追加已完成并部署：连弩F8Hz/5位面无弹药；镇魂歌51/.8、右键4.5半径.6前摇/2s一轮1/600耐久；忍锋51/200，按用户原版黑黄刃机械白柄、羽翼镇魂歌重绘并编译；纸片左右front背面back。基础速度1.5、C+.5/X+.2、任意湿度总速*.5且禁止入C，hot/cold2/fire1.5。眼球升级袋防雨1、夏隔热240、电绝缘，穿戴C解锁踏水，卸下海上安全回退。复活protect30禁止手部和攻击，收纳/满包落地，CZX等保留。
最新回响3%/Z4.5%；Z150san/min。X新增农业与队友30san/min，不回本人/同源不叠；真实农田4秒成熟，原生照料、水肥，普通采集植物一次领域催熟一轮。蛋包饭禁inedible/meat/magic/fish/monster；晶体用moonrockseed，doom增加opal。curse.lua免原版和Happy猴子诅咒吸附/手捡/僵直/变身/绑定，丢弃转交恢复活性，旧存档安全清理。
Happy2886753796版本2.8.14.84 Compat按source+闭包签名单次跳过EpicArmor SetVal门，不跳过影分身阶段回调；所有三弹均接入，保留正常死亡/射手来源、原生护甲、普通回调防御、错误恢复。native19最终通过且退出0。早期复制旧测试世界C++崩溃及中间关闭C0000409记入verification，不能删除或改写为从未失败。
最终300 Lua回归、56base+四五六装备栏原生、19Happy原生+诅咒、8Void抽测均通过。root已读日志/退出。base56含真实60+30秒、农田、双新武器、诅咒；Void最新3%心弹517.65，log void-combat-022.log。GUI、远端、洞穴切片、长期未复验，T与用户正式世界不动，继续用户先部署稍后自行重载偏好。
两个0.2.2ZIP在dist，最终manifest/package-check为准，运行文件75个（新武器Lua/资源/农业/诅咒等）。本轮用户明确每次部署删除游戏旧mod，新增tools/deploy_kanami.ps1已实际成功：精确校验后删除正式旧文件夹并重新复制，清除游戏mods里startup_old、verify、test、void_test，只剩正式klbq_kanami。新授权下游戏旧测试目录清理成功；Dtemp里历史清理被拒绝的文件未绕过处理。源码、美术、历史ZIP和测试世界全部保留。任务native服务器均已结束。不要重复打包/测试/部署，除非又改代码；不自动上传Workshop。


## 0.2.3背包客户端崩溃热修复（2026-10-28）
用户制作背包后客户端崩溃，实际日志ContainerWidget.Open:32 widget=nil，服务端无相应Lua异常。根因0.2.2仅server WidgetSetup(krampus_sack)，remoteContainerReplica_ctor默认按klbq_singularity找params失败。已在prefab模块两端加载时注册独立14格params.klbq_singularity，server也改同名WidgetSetup，不改原生/第三方UI钩子。新test_bag_client.py用完整原版Replica ctor和Widget.Open复现3失败，修复后全GREEN；完整303case通过。
新增tests/engine_mod/bag.lua与--bag-only，仅测试所需原生制作自动装备/重开/眼球升级/存读档。--happy --void --equipment同开最终4PASS0Lua0退出；早期清理把外层主玩家p一起Remove导致/相关原生退出CFileWriterThread异常，已由夹具保留主玩家正常保存并延迟1s后退出；不要把旧失败说没发生，docs/reports/verification-023.json和verification.md准确记录。用户正式世界/GUI/T配置不动。
source/modinfo/modmain/package版本0.2.3；deploy.ps1改为读modinfo动态版本。将更新0.2.3两包并按之前授权清理游戏旧副本、部署，完成状态以dist/manifest.json/package-check为准。D盘源码和历史ZIP保留。用户提问“两端与服务器模组菜单”为何相关已解释：两端必装，服务器逻辑客户端UI各自运行，这次是客户端定义遗漏，不是用户启用错误。

0.2.3最终已部署并清除游戏旧正式/verify/test副本，只剩正式klbq_kanami。75运行文件与源及两包SHA一致，dist/manifest、package-check、plan-check均已更新版本。303unit与联合bag4native为本轮实测，旧56/19/8不冒充本轮重跑。无需重复打包部署，除非又改动。
