# 香奈美 2.1.1 发布资料

本版将弦化默认按键改为 R，加入存活时的防偷取与强制掉落保护，并修复普通工具工作时的手持贴图消失。死亡按原世界规则掉落，玩家可以主动丢弃、给予与存放物品。

## 发布文件

- 固定待上传目录为 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，根目录直接包含 modinfo.lua 和 modmain.lua，版本为 2.1.1。
- 运行包为 `D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.1.1-dst.zip`。
- 源码美术工程包为 `D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.1.1-source-art.zip`。
- 发布文案位于 `D:\SOFTWARE\项目\饥荒\发布资料\klbq_kanami_v2_1_1`，包括 description.txt、patch-notes.txt、title.txt 和 preview.png。
- 待上传目录的上级同步提供 kanami-description.txt、kanami-patch-notes.txt、kanami-preview.png、kanami-upload-guide.md 和 kanami-current-release.json。

## 工坊更新与安装

更新现有工坊条目 3827702076 时，在 DST 上传器选择 Edit，勾选 Update Data，使用上述固定待上传目录。发布文案采用本版对应文件。

手动安装时，将运行包解压到游戏安装目录的 mods/klbq_kanami，确保 modinfo.lua 和 modmain.lua 直接位于该目录。保存退出并完整重启游戏与世界，房主与加入者均使用 2.1.1，地面与洞穴同时更新。已有世界若保存过其他键位，可在模组配置中将“弦化按键”选为 R。

本版源码、测试和发布资料同步到 `https://github.com/tongxinaiyazi/kanami-Don-t-Starve-mod` 的 main 分支。验证范围见 `docs/reports/release-2.1.1.md`，文件一致性记录见 `dist/package-check-2.1.1.json`。
