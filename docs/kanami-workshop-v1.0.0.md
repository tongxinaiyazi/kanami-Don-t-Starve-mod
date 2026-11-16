# 香奈美 v1.0.0 上传器填写说明

本次将0.2.6打包为1.0.0，只调整元信息和说明。运行包与美术工程包分开，旧ZIP保留；本地安装状态以dist/package-check.json为准，不自动操作上传器或点击Publish。

2026-10-30作者修订：游戏内作者为“奈娅子”，游戏内简介只有“模组交流群：1131263408”。两项来自modinfo.lua；已有工坊条目需要勾选Update Data重新上传才能更新订阅文件，只改Update Details不会替换游戏内作者和简介。下方Description是工坊页面介绍，与游戏内简介分别填写。

先在上传器主窗口确认 **Target Game's Workshop = Don't Starve Together**。更新现有条目用Edit，首次创建用Add；不要误选单机版Don't Starve。

按Edit Mod窗口从上到下填写：

1. **Update Data**：勾选，Browse选择 `D:\SOFTWARE\DSTWorkshop\klbq_kanami_v1_0_0`。这是纯运行文件目录，直接包含modinfo.lua和modmain.lua；不要选择ZIP、工程包、dist或整个项目目录。
2. **Update Preview Image**：勾选，选择 `D:\SOFTWARE\DSTWorkshop\kanami-preview-v1.0.0.png`。使用现有角色立绘512×512 PNG，未重新绘制。
3. **Update Details**：勾选。
4. **Name**：`【卡拉彼丘】香奈美 · 谢幕曲`。版本已经写入modinfo.lua，不必每次把版本号放进标题。
5. **Description**：完整复制 `D:\SOFTWARE\DSTWorkshop\kanami-description-v1.0.0.txt` 中的文字。已沿用现有简介的八个栏目，转换为工坊BBCode；不要填文件路径。
6. **Upload redundant files**：不勾选。
7. **Tags**：勾选 `character` 和 `item`。
8. **Visibility**：要让其他人搜索、订阅就选 `Public`；只给自己检查上传结果可选 `Private`。
9. **Patch Notes**：复制 `D:\SOFTWARE\DSTWorkshop\kanami-patch-notes-v1.0.0.txt` 的内容。
10. 检查上述字段后，由你点击 **Publish!**。看到完成提示后，再打开工坊页面核对版本和文件；本地打包成功不表示已经上传。

本地完整发布资料保留在 `D:\SOFTWARE\项目\饥荒\发布资料\klbq_kanami_v1_0_0`。预览图和文本放在Data目录外，避免一起变成模组运行数据。

运行包：`dist/klbq_kanami-1.0.0-dst.zip`。源码／美术／构建及发布资料：`dist/klbq_kanami-1.0.0-source-art.zip`。

验证记录：本次核对版本、Lua夹具中的受限环境入口注册、Lua5.1语法、包CRC及上传目录哈希。此前378项回归与游戏实测属于0.2.6；没有新增远端多人、洞穴或全部Boss阶段的验证声明。后续实际验证仍关闭为爽而虐，保留T键模组。
