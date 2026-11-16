# 香奈美 2.1.0 发布资料

本版包含矿工帽永久照明、矿工帽给予动作修复和资源堆叠兼容修复。给予弦能奇点一个矿工帽，永久免燃料，仅背着时发光；支持存档，与巨鹿眼球升级兼容。未完成矿工帽升级时优先显示“给予”，升级后恢复普通存放。

## 约定目录

- 待上传目录：`D:\SOFTWARE\DSTWorkshop\klbq_kanami`。目录根直接包含 modinfo.lua 和 modmain.lua，版本为 2.1.0。
- 运行包：`D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.1.0-dst.zip`。
- 工程包：`D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-2.1.0-source-art.zip`。
- 发布文案：`D:\SOFTWARE\项目\饥荒\发布资料\klbq_kanami_v2_1_0`，使用 description.txt、patch-notes.txt、title.txt 和 preview.png。
- 上传目录的上级同步提供 kanami-description.txt、kanami-patch-notes.txt、kanami-preview.png、kanami-upload-guide.md 及 kanami-current-release.json。

## 上传与安装

本次仅生成本地发布文件，没有上传或覆盖工坊条目。用户发布时，在 DST 上传器选择现有条目 3827702076 的 Edit，勾选 Update Data，选择上述待上传目录。

本次未更新游戏中的本地开发副本（仍为 2.0.2）。手动安装新运行包时，将包内文件放到游戏安装目录的 mods/klbq_kanami 中，确保 modinfo.lua 和 modmain.lua 直接位于该目录；使用本地版时关闭同名工坊版。保存退出并完整重启游戏及世界，房主与加入者使用同一版本；启用洞穴时两分片均需更新。

验证及未验证范围见 `docs/reports/release-2.1.0.md`；一致性检查见 `dist/package-check-2.1.0.json`。
