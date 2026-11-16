# 0.2.3 背包窗口崩溃热修复（2026-10-28）

用户实际client_log.txt在本轮21:46测试的00:02:38报错：`scripts/widgets/containerwidget.lua:32: attempt to index local widget (a nil value)`，container为klbq_singularity。完整堆栈经过额外背包、虚空异界及为爽而虐的Open包装，最终在原版ContainerWidget:Open读取nil布局时失败；本记录只保留相关错误信息，不复制含用户连接信息的完整日志。

原因为0.2.2仅服务端调用WidgetSetup(krampus_sack)。原版客户端ContainerReplica构造器按自己的prefab名klbq_singularity查询containers.params，找不到定义，widget=nil/numslots=0。专用服务器中的实际物品/返鲜测试看不到客户端这个缺陷，因此上版通过测试不能证明背包窗口正常。

修复：在Prefab模块两端加载时注册独立的klbq_singularity 2×7布局，早于任何实例及SetPristine；服务端也用同名WidgetSetup。保留14格、返鲜、眼球升级、额外BACK/BODY槽与隐藏外观；不引用或修改其他模组的窗口函数，不依赖原版krampus_sack被其他模组改过后的布局。已有存档的背包下次两端重载后按同prefab重新获得布局，无需清存档或丢弃物品。

新增test_bag_client.py执行安装包原始ContainerReplica完整构造器及ContainerWidget:Open完整方法（图形节点/网络变量为夹具）：旧代码3项先失败，准确出现widget=nil；修复后客户端14格、原生窗口两次打开、服务端/客户端一致且不污染原版背包3项通过。完整Lua回归303项通过，37.462秒。不能将此表述为实际GUI或远端联机实测。

独立真实服务器联合启用四五六格装备栏、为爽而虐2.8.14.84、虚空异界2.3.2：实际Builder消耗配方/自动装备、关闭重开/升级、保存恢复打开和清理共4项通过、0 Lua错误。检查完成后关闭时原生CFileWriterThread断言/C0000409仍出现，属于已在0.2.2记录的独立服务器退出异常，本轮没有当作正常退出；单装备栏对照也出现关闭异常，该结果保留于engine-bag-equipment-result.json。
最终联合复验：四五六格装备栏＋为爽而虐＋虚空异界同时启用，4项全部通过、0 Lua错误、正常退出0。已调整测试夹具，不再提前删除由外层管理的主玩家，并留出正常保存时间。此前单装备栏组合的关闭异常仍保留于engine-bag-equipment-result.json，不将早期异常改写为未发生。实际客户端画面仍待重载复查。


没有控制用户游戏窗口、改用户存档或T键配置。部署前更新运行包/工程包，按用户要求删除游戏中本任务旧版与验证副本，保留D盘源码与历史ZIP。
