# 香奈美 · 谢幕曲

《饥荒联机版》角色模组，当前发布版本为 **2.2.0**，房主与加入者均需安装。

包含弦化、旋律回响、交响爆音、演出开始、双生共鸣、专属武器与拓印终端。弦化默认按键为R，角色存活时可抵抗偷取与强制掉落。弦能奇点接受巨鹿眼球和矿工帽升级，矿工帽升级后永久免燃料，仅背着时发光。镇魂歌圆斩默认使用 V，可配置。拓印终端接受海象牙后永久解锁手持 25% 移速加成。领域支持树木催熟，草与浆果丛等取消自动施肥，并修复收纳失败时吞物品及巨大作物消失。角色规则、装备和配方见 [模组说明](mods/klbq_kanami/README.md) 与 [玩家介绍](docs/香奈美模组介绍.md)。

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

运行包与工程 ZIP 位于项目 `dist`。工坊上传器使用约定目录 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，发布文案同步到其上级目录。每次用户要求准备发布包，都应完成对应 Git 提交、推送并核对远端提交。具体约定见 [AGENTS.md](AGENTS.md)，当前版本验证见 [2.2.0 发布记录](docs/reports/release-2.2.0.md)。
