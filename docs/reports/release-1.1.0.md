# 香奈美1.1.0身体整合发布

发布于2026-11-12，目标为饥荒联机版，两端必装。本机游戏版本762172。作者为奈娅子，游戏内简介为“模组交流群：1131263408”。

本次采用另一对话交付的身体V2最终稿，身体源工程位于art/klbq_kanami/body-v2。整合前，当前源码全部91个运行文件与dist/package-check-1.0.1-joints.json一致。身体流水线body-pipeline.json的active为body-v2，已编译角色及动作ZIP的SHA256与该交付记录一致。

身体修订包含完整腰缝、手脚与颈部连接，肢体和躯干比例，头发与持物手掌的遮挡关系，侧眼及嘴部校准，以及原生dial_loop说话和拒食动画。详细美术修订与实测证据见joint-rebind-2026-11-10.md、joint-rebind-readback.json、body-v2-latest.png及joint-rebind-latest.png。

本次将modinfo.lua和运行加载日志升级至1.1.0。打包脚本从modinfo.lua读取版本，并选择对应版本的发布资料。运行包、源码美术包与固定上传目录按当前源文件生成。

本轮回归结果与逐文件校验记录在dist/package-check-1.1.0.json，日志为regression-1.1.0.txt与body-tests-1.1.0.txt。

本次重跑438项玩法回归和46项身体／工具检查，全部通过，耗时分别为107.216秒和102.999秒。当前编译身体及动作资源匹配另一对话最终交付哈希，153组方向与动作、2996帧、45,330次接缝检查沿用该美术交付记录。

美术交付时已在1.0.1对相同身体资源实测说话、正侧面、三方向移动、砍伐、采矿、挖掘与正常食用。本轮进行版本整合和打包校验，未新增1.1.0图形客户端实测。另一台物理机器、洞穴迁移、骑乘与全部特殊表情仍沿用美术报告的验证范围。

运行ZIP为dist/klbq_kanami-1.1.0-dst.zip，源码美术ZIP为dist/klbq_kanami-1.1.0-source-art.zip。固定工坊目录为D:/SOFTWARE/DSTWorkshop/klbq_kanami，本地安装目录为E:/steam/steamapps/common/Don't Starve Together/mods/klbq_kanami。游戏安装由已有部署脚本替换，旧版本运行包和源码保留在项目中。

本地正式安装已替换为1.1.0，91个运行文件与源码、运行ZIP及固定上传目录逐文件SHA256一致。工坊上传由用户通过现有条目完成，更新后重新启动游戏载入。
