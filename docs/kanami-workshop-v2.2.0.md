# 香奈美 2.2.0 发布资料

本版修复树木催熟、收纳失败吞物品和巨大作物采集消失，取消草与浆果丛等自动施肥，将镇魂歌圆斩改为可配置的 V 键，并新增拓印终端海象牙手持加速升级。

## 上传与交付文件

- 固定待上传目录为 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，根目录直接包含 `modinfo.lua` 与 `modmain.lua`。
- 运行包为 `D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.2.0-dst.zip`。
- 工程包为 `D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.2.0-source-art.zip`。
- 发布文案位于 `D:\SOFTWARE\项目\饥荒\发布资料\klbq_kanami_v2_2_0`。
- 待上传目录上级提供 `kanami-description.txt`、`kanami-patch-notes.txt`、`kanami-preview.png`、`kanami-upload-guide.md` 与 `kanami-current-release.json`。

更新现有工坊条目 3827702076 时，在 DST 上传器中选择 Edit，勾选 Update Data，选择固定待上传目录，并使用本版文案。

## 安装与验证

本机部署使用 `powershell -File tools/deploy_kanami.ps1`，同步本地开发副本与实际订阅的工坊副本。手动安装时将运行包解压到游戏安装目录的 `mods/klbq_kanami`，两个入口 Lua 文件直接位于该目录。

更新后完整退出并重启游戏与世界，房主与加入者使用同一版本，地面与洞穴同步更新。镇魂歌圆斩默认 V，可在模组配置中选择其他按键。拓印终端接受一根海象牙后，手持移速增加 25%，状态说明会显示“手持加速”。

源码与本版发布资料同步到 GitHub 仓库的 main 分支。验证记录见 `docs/reports/release-2.2.0.md`，包校验见 `dist/package-check-2.2.0.json`。
