# 香奈美1.1.0发布资料

1.1.0整合另一对话完成的身体V2最终修订，身体与动作资源采用2026-11-12交付版。

在DST上传器选择现有工坊条目并打开Edit。勾选Update Data，目录选择 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`。该目录直接包含modinfo.lua和modmain.lua。

需要更新工坊介绍时，勾选Update Details。名称使用title.txt，Description使用description.txt，Patch Notes使用patch-notes.txt。标签选择character和item。预览图使用 `D:\SOFTWARE\DSTWorkshop\kanami-preview.png`，更新预览图时勾选Update Preview Image。

固定目录旁的kanami-description.txt、kanami-patch-notes.txt与kanami-upload-guide.md也会同步为当前发布资料。由用户在上传器点击Publish完成工坊更新。

运行包位于 `D:\SOFTWARE\项目\饥荒\dist\klbq_kanami-1.1.0-dst.zip`，源码和美术工程包位于同目录的klbq_kanami-1.1.0-source-art.zip。

本机安装位于 `E:\steam\steamapps\common\Don't Starve Together\mods\klbq_kanami`。更新后完整退出并重新启动游戏，在服务器模组中确认版本1.1.0。房主及加入者使用相同版本。

验证记录见docs/reports/release-1.1.0.md，逐文件校验见dist/package-check-1.1.0.json。
