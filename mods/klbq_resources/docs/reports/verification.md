# 0.1.0 验证记录

日期：2026-10-30。目标：DST 760178，Windows 本机。

## 结果

- Lua 5.1 运行单元检查 18/18：20 项身份与查询 API、无效输入、同版注册去重、版本冲突、受限 modinfo、可调用 Asset 表、严格全局变量环境、客户端/服务器构造分界。
- 编译资源检查 3/3：20 个地面动画与 Symbol 绑定，库存图集 20 个原生 64×64 区域，KTEX/BILD/ANIM 格式与图标。
- ZIP 检查 2/2：12 个允许的运行文件，文件位于模组根部，无参考图、工具、测试、存档、缓存或日志。
- 隔离测试端口检查 7/7：只选择 LAN 允许的空闲 UDP 端口，跳过默认 10999；配置与启动参数一致，并拒绝端口回落。自动检查合计 30/30。
- 实际无渲染专服创建阶段 24 项通过：20 个实体的生成、原生存档记录往返、背包与箱子转移、堆叠上限、图集/动画名绑定，以及同类合堆、溢出/拆分、异类拒绝混堆、无额外配方。
- 实际保存退出并启动第二个服务器进程，重载阶段 21 项通过：20 种资源各自的独立数量恢复，且没有额外资源身份。
- 两阶段均退出码 0、失败数 0、无 Lua 错误。工具创建新世界后重复运行，两阶段再次通过。
- 最终两阶段实际端口均为 11018，与选择值一致，未出现端口回落；端口解析同时排除了独立的 SteamMasterServerPort 字段。
- 早期核验时香奈美与莉莉丝 104 个文件均与起始 SHA256 一致；最终核对发现香奈美的 modinfo.lua、modmain.lua、README.md 出现同期变动，元信息已为 1.0.0。本任务未写入、覆盖或回退这些主模组文件，其现有变动已保留。详见 [范围核对](scope-audit.json)。

## 证据

- [创建阶段结果](engine-create-result.json)、[创建日志](engine-create.log)。
- [重载阶段结果](engine-reload-result.json)、[重载日志](engine-reload.log)。
- [核心实现 RED/GREEN](../core-report.md)。
- [端口修复 RED/GREEN](../port-fix-report.md)。
- [运行包文件与 SHA256 清单](../../release/manifest.json)。
- 库存与地面运行切图已查看：`art/inventory-atlas.png`、`art/runtime-preview.png`。
- 初次资产检查为预期 3 项失败（未构建）；初次包检查为预期 2 项失败（未打包），构建打包后均通过。

## 运行隔离

服务器在任务自己的 D 盘临时根下运行。只读链接游戏 data，复制本机运行所需二进制和本附属模组到临时主机；不覆盖游戏安装目录中的模组，不读写用户正式存档。只在临时离线测试世界生成资源和测试实体。

临时测试世界与编译中间目录在任务结束时清理；本页关联日志、结果、源码、艺术工程、运行包保留。

## 检查命令

在项目根目录：

```powershell
& 'D:\SOFTWARE\CodexData\runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -m unittest discover -s mods/klbq_resources/tests -p 'test_*.py' -v
py -3 -B mods/klbq_resources/tools/build_assets.py
py -3 -B mods/klbq_resources/tools/package_mod.py
py -3 -B mods/klbq_resources/tools/run_engine.py --seconds 120
```

## 证据边界

无渲染专服的动画名与资源绑定检查不等于实际游戏画面验收。未完成图形客户端的库存/地面画面、另一台远端客户端、实际海面浮水、洞穴跨分片、长期运行、停用模组和未来融合版本的存档迁移验证。

本包没有来源、用途或经济系统。控制台生成与开发查询是测试/集成入口，不是自动资源发放。
