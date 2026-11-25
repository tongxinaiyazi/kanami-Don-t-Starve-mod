# 香奈美 · 谢幕曲

《饥荒联机版》角色模组，当前发布版本为 **2.4.0**，房主与加入者均需安装。

2.4.0 新增多地区乐谱与拟态拓印地皮、记忆序列、弦能奇点护甲与夜视升级，以及谢幕曲自动锁定。洞穴弦化可踏虚空，X 大招可催熟新种下的树苗且不再补农田养分。完整配方和操作见 [2.4.0 更新清单](发布资料/klbq_kanami_v2_4_0/更新清单.md)，其他玩法见 [模组说明](mods/klbq_kanami/README.md) 与 [玩家介绍](docs/香奈美模组介绍.md)。

## 工程目录

- `mods/klbq_kanami` 为可部署的角色模组，根目录包含 `modinfo.lua` 和 `modmain.lua`。
- `mods/klbq_resources` 为配套资源包源码，供资源集成与回归验证使用。
- `art/klbq_kanami` 包含当前美术工程、Spriter 文件、注册数据和导出资源。
- `tools` 包含资源构建、检查、测试世界和打包工具。
- `tests` 包含 Lua 5.1 玩法回归和引擎测试夹具。
- `发布资料` 包含各版本介绍、更新说明、标题与预览图。
- `dist` 中的 Git 文件记录版本清单和发布校验结果，生成的 ZIP 保存在本机。

## 安装与开发

将 `mods/klbq_kanami` 放入 DST 安装目录的 `mods` 中，在世界的服务器模组菜单启用。地面和洞穴使用相同版本，更新后完整重启游戏与世界。

开发使用 Python 3、Pillow、Lupa 和本机安装的 DST 脚本。资源编译使用 Don't Starve Mod Tools。测试入口如下，其他机器的游戏路径需按 [构建说明](docs/BUILDING.md) 调整。

```powershell
python -m unittest discover -s tests/gameplay -q
```

## 发布与 GitHub 同步

根据版本更新元信息、发布资料并完成相应验证，随后运行打包工具。

```powershell
python tools/package_kanami.py
git add --all
git commit -m "Release X.Y.Z"
git push origin main
```

运行包与工程 ZIP 位于项目 `dist`。工坊上传器使用约定目录 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，发布文案同步到其上级目录。每次用户要求准备发布包，都应完成对应 Git 提交、推送并核对远端提交。具体约定见 [AGENTS.md](AGENTS.md)，当前版本验证见 [2.4.0 发布记录](docs/reports/release-2.4.0.md)。
