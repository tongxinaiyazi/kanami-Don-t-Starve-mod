# 重建与验证

工程为Lua角色模组，不需要BepInEx、C#或Harmony。本轮核验本机DST 761239／Steam Build26335394，Lua5.1。

当前验证约束（用户于2026-10-30确认）：之后实际验证关闭“为爽而虐”Workshop2886753796，保留T键模组。下面历史兼容复现中的`--happy`不再执行，除非用户重新要求。保留现有兼容代码与历史结果，不能把关闭后的测试说成重新验证了该模组。

1. 安装Steam版DST与官方Don't Starve Mod Tools。当前路径分别为 `E:/steam/steamapps/common/Don't Starve Together` 与 `E:/steam/steamapps/common/Don't Starve Mod Tools/mod_tools`。其他机器调整工具脚本中的GAME／TOOLS路径。
2. 使用Python3（Pillow用于裁剪、资源排版和离线预览；Lupa用于Lua5.1测试）。依赖不随工程包打包，可安装到D盘虚拟环境。当前Lupa位于 `tools/python-deps`；测试会把它加入搜索路径，也能使用环境内的Lupa。
3. 执行 `python tools/build_kanami_assets.py --only all`。官方捆绑Python2.7负责动画编译，TextureConverter负责TEX；ASCII暂存路径固定为 `D:/SOFTWARE/CodexData/temp/kanami_assets`，可按本机情况调整。
4. 执行 `python -m unittest discover -s tests/gameplay -v`。部分回归直接从当前游戏scripts.zip读取实际函数；测试和工具不属于运行包。
5. 执行 `python tools/run_kanami_engine.py --seconds 240 --isolated-mod-copy`，会部署单独的开发验证副本并创建独立离线测试世界，保留用户已安装版本，不接触正式存档。加 `--equipment` 在该测试世界启用本机“四五六格装备栏”默认配置。只运行一个测试服务器可避免Steam query端口竞争。脚本拒绝覆盖无所有权标记的同名部署目录。
6. 虚空异界探测见 `docs/reports/void-compatibility.md`。需要本机已有的2.3.2目录（优先经Steam UGC路径访问），不自动下载第三方模组。
7. 执行 `python tools/package_kanami.py` 产生运行包及源码／美术工程包，并检查ZIP完整性、输出SHA256。运行包根目录直接包含modinfo.lua／modmain.lua。
8. 每次用户要求准备发布包，都要将本次源码、版本和发布资料提交并推送到 `https://github.com/tongxinaiyazi/kanami-Don-t-Starve-mod.git` 的 `main` 分支。执行 `git add --all`，审查暂存内容后提交，再执行 `git push origin main`。通过 `git ls-remote origin refs/heads/main` 与 `git rev-parse HEAD` 核对提交号。该同步已获用户长期授权，适用的发布步骤见根目录 `AGENTS.md` 第12节。

`kanami_client_qa.py` 是仅限本机任务所有窗口的Win32截图／按键工具；其截图入口依赖本机Codex screenshot技能的脚本。它不是游戏模组，也不作为通用桌面自动化工具发布。

测试世界与中间文件均位于D盘。不得把测试夹具中的赠送物品、无敌、强制昼夜等设置加入正式角色。完整验证证据与尚未验证范围见 `docs/reports/verification.md`。

0.2.2可用 `python tools/run_kanami_engine.py --isolated-mod-copy --happy --seconds 180` 验证本机为爽而虐2.8.14.84，隔离开启巨兽装甲5、额外cap1、影分身；默认只复制自己工程，不改第三方源码。`--weapons-only --equipment` 可单独测试真实F连射和圆斩。每次本地修改验证通过后运行 `powershell -File tools/deploy_kanami.ps1`，同步本地开发副本与已订阅的工坊 3827702076。先加 `-ValidateOnly` 可列出实际目标。部署工具备份差异文件、更新工坊加载清单并逐文件核对 SHA256，结果见 `docs/reports/local-deploy-latest.json`。本地部署独立于发布打包。


0.2.4增加原版64像素物品栏图集区域和手持swap_object帧持续区间；只改尺寸／帧时，执行`--only items`、`--only ui`，领域环改动执行`--only fx`。角色PNG无需随之重绘。

`--bag-only --happy --void --equipment`在同一独立世界验证四五六格、为爽而虐、虚空异界下的制作、收纳、循环拒绝与升级读档。`--weapons-only --equipment`验证实际Controller／Locomotor／状态图武器动作与角色岸边mask／保护拾取；无渲染专服不会验证画面观感。原生远程ATTACK必须由Controller.OnUpdate补齐_predictpos后提交，不能在夹具中直接PushAction丢失坐标；StopBrain应使用EntityScript公开方法以覆盖首次唤醒时建脑。


0.2.5目标已重核为DST760178。`--audit-only --equipment`执行真实海面SpawnSaveRecord、外部复活竞争、睡眠独立收费、零伤回响、旧蜘蛛解除，以及黑夜开启领域后的熊獾圆斩。私有世界仅推进原生环境光渐变到全黑；不改视线或伤害函数。`test_bag_ui.py`模拟原版Button的可变name，不能再假定ImageButton.name恒定。图形显示仍须独立客户端验收。


1.0.1手脚切片／枢轴修订后须重建`--only character`和`--only actions`，并同步工程SCML。`test_assets.py`逐帧腕踝重叠检测仅是连接必要条件；仍需重新载入真实客户端检查站立、跑步、进食和持物。直接对玩家SetPercent可能被状态机覆盖，不能把实际仍为idle的截图标作跑步或进食。

### 固定工坊更新路径

本机临时更新已下载的工坊副本时，原版 `mod.manifest` 也需覆盖新增文件路径。游戏的工坊加载会按清单筛选路径，新增脚本已复制到磁盘后仍需核对清单并完整重启游戏。可执行 `python tools/run_kanami_engine.py --workshop-runtime --inventory-guard-only --equipment --seconds 180`，该模式在独立测试世界中读取已安装的工坊 3827702076 及其文件清单。

运行tools/package_kanami.py会自动同步纯运行文件到 `D:\SOFTWARE\DSTWorkshop\klbq_kanami` 并逐文件核对哈希。上传器以后始终选此目录；不要再创建新的版本化上传目录。旁边的kanami-current-release.json记录发布来源及文件清单，供下次同步识别旧文件。ZIP历史归档和本地源码仍保留。


1.0.1拓印终端：执行`python tools/build_kanami_assets.py --only imprint`重建四种投影形态、16种状态的手持图集及落地动画；执行`--only ui`重建64像素物品图标。`python tools/run_kanami_engine.py --isolated-mod-copy --imprint-only --equipment --resource-addon --seconds 100`运行9项原生工具和材料检查。图形验证辅助脚本qa_imprint_visual.py仅操作D盘独立QA配置，不能用于正式世界。独立资源包源码保持不变。
