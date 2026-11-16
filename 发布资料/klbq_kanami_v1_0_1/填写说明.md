# 香奈美 v1.0.1 上传器填写说明

本次为2026-11-02拓印终端与材料体系修订包：新增可学习金工具的拓印终端，闲置单圆盘、作业自动投影斧／镐／铲；新增基弦／拓印基板／拓扑晶环加工与原生掉落，调整相关装备配方；保留连弩发射位置修订，修复脚下出箭，保留弹药配置修订：新增支配命运之轮暴击比例3%／5%／10%／20%（默认3%），并保留后颈修复；修复后脑/后颈结构、闲置歪头断层和持枪动作，并保留普通种子催熟及弹药文案更新。旧包的美术验收结论已撤回，以后固定选择下方上传目录，每次打包自动更新内容。运行包与美术工程分开，旧ZIP保留；不自动上传。

2026-10-30作者修订：游戏内作者为“奈娅子”，游戏内简介只有“模组交流群：1131263408”。两项来自modinfo.lua；已有工坊条目需要勾选Update Data重新上传才能更新订阅文件，只改Update Details不会替换游戏内作者和简介。下方Description是工坊页面介绍，与游戏内简介分别填写。

先在上传器主窗口确认 **Target Game's Workshop = Don't Starve Together**。更新现有条目用Edit，首次创建用Add；不要误选单机版Don't Starve。

按Edit Mod窗口从上到下填写：

1. **Update Data**：勾选，Browse选择 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`。这是纯运行文件目录，直接包含modinfo.lua和modmain.lua；不要选择ZIP、工程包、dist或整个项目目录。
2. **Update Preview Image**：勾选，选择 `D:\SOFTWARE\DSTWorkshop\kanami-preview.png`。使用现有角色立绘512×512 PNG，未重新绘制。
3. **Update Details**：勾选。
4. **Name**：`【卡拉彼丘】香奈美 · 谢幕曲`。版本已经写入modinfo.lua，不必每次把版本号放进标题。
5. **Description**：完整复制 `D:\SOFTWARE\DSTWorkshop\kanami-description.txt` 中的文字。已沿用现有简介的八个栏目，转换为工坊BBCode；不要填文件路径。
6. **Upload redundant files**：不勾选。
7. **Tags**：勾选 `character` 和 `item`。
8. **Visibility**：要让其他人搜索、订阅就选 `Public`；只给自己检查上传结果可选 `Private`。
9. **Patch Notes**：复制 `D:\SOFTWARE\DSTWorkshop\kanami-patch-notes.txt` 的内容。
10. 检查上述字段后，由你点击 **Publish!**。看到完成提示后，再打开工坊页面核对版本和文件；本地打包成功不表示已经上传。

本地完整发布资料保留在 `D:\SOFTWARE\项目\饥荒\发布资料\klbq_kanami_v1_0_1`。预览图和文本放在Data目录外，避免一起变成模组运行数据。

运行包：`dist/klbq_kanami-1.0.1-dst.zip`。源码／美术／构建及发布资料：`dist/klbq_kanami-1.0.1-source-art.zip`。

验证记录见 docs/reports/verification.md；后续实测关闭为爽而虐，保留T键模组。

## 后续每次更新

Update Data始终使用 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，不再选择带版本号的历史目录。每次执行tools/package_kanami.py都会刷新并核对该目录；预览图、介绍和更新说明也输出到固定文件名。仅更新模组文件时，勾选Update Data即可；封面没改不必勾Update Preview Image，标题／介绍没改不必勾Update Details。Patch Notes可填写本次更新内容，最后由用户点击Publish。
