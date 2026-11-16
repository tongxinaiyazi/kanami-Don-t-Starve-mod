# 饥荒模组开发约定

适用目录：`D:\SOFTWARE\项目\饥荒` 及其子目录。资料核验日期：2026-10-26。

## 1. 开发范围与证据优先级

- 本项目用于饥荒模组开发。本机已安装《饥荒联机版》Don't Starve Together，以下默认以 **DST** 为主要参考；这不代表用户已决定所有模组都面向 DST。
- 每个新模组开始前，结合需求明确目标：单机版 Don't Starve（DS）及对应 DLC，或联机版 DST；同时明确客户端模组、服务端模组或两端必装模组。已有上下文足以判断时直接推进。
- DS 与 DST 的接口、配方、玩家获取方式和联网机制不可直接混用。未经分别验证，不声明兼容单机、巨人国、海难或哈姆雷特。
- 饥荒模组主要使用 Lua 和游戏资源格式；不要套用其他游戏的 BepInEx、Harmony 或 C# 插件结构。
- 接口实现以**目标版本随游戏分发的脚本**为准；开发与发布政策以 Klei 官方说明为准。GitHub 镜像和教程用于检索、理解和交叉核对，不能替代当前版本验证。
- 本文件中的代码组织、命名、测试流程属于项目约定；文末分别标明官方政策、社区教程和非官方脚本镜像，不能把社区帖子当作官方 API 保证。

## 2. 本机已核验的开发入口

- DST 安装目录：`E:\steam\steamapps\common\Don't Starve Together`。
- Steam App ID：`322330`；核验时 `appmanifest_322330.acf` 的 Build ID 为 `26148036`，游戏 `version.txt` 为 `759671`。这两个编号不是同一种版本号，游戏更新后重新读取。
- 当前游戏脚本包：`E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip`，包内路径以 `scripts/` 开头。
- 先读安装目录中的 `data\scripts_readme.txt`、`mods\MAKING_MODS.txt` 和 `mods\modsettings.lua`。官方随包说明允许查看解压后的脚本，并说明正常运行仍优先加载 `scripts.zip`。
- 查看源码时优先直接读取压缩包，或解压到项目中的参考目录；保持安装目录原始脚本不变，通过 Mod 扩展游戏。
- 本地开发模组放到 `<游戏安装目录>\mods\<模组目录名>\`，再在游戏模组菜单启用。不要误放到 `Documents\Klei\DoNotStarveTogether\mods` 并假设客户端会发现它。
- 用户文档目录要通过 Windows 已知文件夹或真实日志确认，不能假定必在 C 盘。核验时该目录的 `Klei\DoNotStarveTogether` 下存在 `client_log.txt`、`master_server_log.txt`、`caves_server_log.txt`。
- 当前模组源码：`mods/workshop_publish_test`，为 DST 纯客户端发布测试空壳，仅输出加载日志；上传路径和测试步骤见 `发布测试说明.md`。其他建议结构不代表已经实现的功能。

## 3. 目录与入口文件

- 每个独立模组使用独立目录；按需建立 `mods/<mod_id>/` 作为项目源码目录，部署时复制该目录的内容到游戏的模组目录。交付包根目录应直接包含 `modinfo.lua`、`modmain.lua`，避免多套一层目录。
- `modinfo.lua`：名称、描述、作者、版本、兼容标记、客户端要求、配置选项和图标信息。它有独立加载环境，不在里面访问游戏世界或实现玩法。
- `modmain.lua`：运行期入口，负责注册钩子、Prefab、资源、配方等；运行位置取决于模组类型，不能假定它只在服务器执行。
- `modworldgenmain.lua`：需要修改世界生成时才添加。世界生成环境与运行期环境分开，不能假定 `TheWorld`、玩家或运行期组件可用；相关改动通常要用新建世界验证。
- `scripts/prefabs/<prefab_id>.lua` 定义实体，`scripts/components/<component_id>.lua` 定义组件，`scripts/replicas/<component_id>.lua` 定义需要的客户端副本；界面可放到 `scripts/widgets/`，状态机可放到 `scripts/stategraphs/`。
- 资源按需使用 `anim/`、`images/`、`sound/`、`bigportraits/` 等目录；只创建当前功能需要的文件。
- 源码、参考脚本、资源工程文件、发布包和部署副本分开。参考代码不是发布内容；除获准复用的必要资源外，不打包游戏原始脚本或整份游戏素材。

## 4. modinfo.lua 与模组类型

DST 的基础元信息可从下面开始；替换名称、作者和描述，客户端要求必须按实际功能选择：

```lua
name = "模组名称"
description = "说明模组的实际功能"
author = "作者"
version = "0.1.0"

api_version = 10
dst_compatible = true
dont_starve_compatible = false
reign_of_giants_compatible = false

client_only_mod = false
all_clients_require_mod = true
```

- 上述模板适用于需要两端安装的 DST 模组，不是所有模组的固定配置；`api_version = 10` 是 DST 的模组 API 标记，不是游戏 Build ID。
- 纯客户端功能：`client_only_mod = true`、`all_clients_require_mod = false`，例如只修改本地界面。客户端模组不能直接改变服务器权威状态。
- 无需客户端代码或新增资源的服务端功能：两项都为 `false`；是否能仅服务端运行，必须结合实际实现验证。
- 两端必装功能：`client_only_mod = false`、`all_clients_require_mod = true`。新增联网 Prefab、自定义网络变量或客户端必需素材时，通常属于这一类。
- `client_only_mod` 与 `all_clients_require_mod` 不可同时为 `true`；本机 `scripts/modindex.lua` 对此有明确警告。
- 不把 `server_only_mod = true` 当作替代上述两项的必需加载开关；Klei 开发者帖说明 Workshop 的服务端分类可由两项均为 `false` 得出。
- 配置写在 `configuration_options` 中，确保 `name`、选项 `data` 和 `default` 一致；运行期用 `GetModConfigData("选项名")` 读取。缺失值用 `value == nil` 判断，不要用 `value or default` 覆盖合法的 `false`；Lua 中 `0` 是真值。
- 菜单图标使用匹配的 `.xml` 图集与 `.tex` 文件，在 `icon_atlas`、`icon` 中声明；不要填写尚未制作的资源路径。

## 5. Lua 环境与扩展方式

- 使用目标游戏 Lua/LuaJIT 支持的语法与标准库；不要默认支持 Lua 5.3/5.4 的语法、库函数或系统 Lua 的运行环境。
- `modmain.lua` 处于 Mod 环境。游戏全局对象显式通过 `GLOBAL` 获取，例如 `local TheWorld = GLOBAL.TheWorld`；但不要在世界尚未建立时缓存一个 `nil`，可在实际回调内取值。
- `modimport("scripts/xxx.lua")` 在当前 Mod 环境中加载文件；`require("components/xxx")` 等按游戏模块规则加载。二者的环境、返回值与缓存行为不同，按用途选择。
- `modname`、`MODROOT` 来自 Mod 环境。独立组件、Prefab 或普通 `require` 模块不要假定能直接取得这些 Mod 专用变量；按需显式传入。
- 优先使用公开扩展钩子，避免直接替换整份游戏文件：
  - `AddPrefabPostInit(prefab, fn)`：扩展某类实体，回调收到实例。
  - `AddComponentPostInit(component, fn)`：扩展组件，回调收到组件实例；实体通常是 `self.inst`。
  - `AddPlayerPostInit(fn)`：扩展玩家实体，但不保证此时客户端玩家、HUD 和所有关联对象均已就绪。
  - `AddClassPostConstruct(package, fn)`：扩展界面或类；使用当前游戏存在的模块路径。
  - 动作、状态机和世界生成分别查看 `AddAction`、`AddStategraphActionHandler`、`AddStategraphPostInit`、`AddRoomPreInit`、`AddTaskPreInit` 等实际定义。
- 仅在确需处理所有实体时使用 `AddPrefabPostInitAny`，尽早过滤；原版 `modutil.lua` 明确提示其性能成本。
- 包装已有方法时保留原方法、`self`、参数、返回值和调用顺序；尽量使用组件公开方法，避免无条件覆写其他模组的修改。
- 文件名、Prefab、组件、标签、事件、RPC 命名空间及存档字段使用模组专属前缀，路径大小写保持一致，兼顾 Linux 专用服务器。

## 6. DST 联机必须遵守的边界

- 伤害、物品增减、生产、掉落和世界状态修改等权威逻辑放到服务器端；访问前判断 `TheWorld.ismastersim`，并确认所需组件存在。
- 客户端经常没有对应的 `inst.components.xxx`；通过现有 `inst.replica.xxx`、同步状态或规范的 RPC 获取所需信息。`ThePlayer` 是本地客户端概念，专用服务器不能依赖它。
- 自建联网实体先参考同类原版 Prefab。典型初始化次序为：创建实体 → 添加 Transform/AnimState/Network 等 → 设置两端共有的外观、标签与网络变量 → `SetPristine()` → 客户端提前返回 → 添加服务端玩法组件。
- 典型分界如下，仅是联网 Prefab 构造中的片段，不能作为独立完整文件运行：

```lua
-- 两端共有的实体结构、外观与网络变量已在上方初始化。
inst.entity:SetPristine()
if not TheWorld.ismastersim then
    return inst
end
-- 以下添加服务端玩法组件。
```

- `SetPristine()` 必须在客户端返回之前执行；不要把所有实体初始化都放进服务器分支。已存在实体的 PostInit 扩展则按该实体的原始构造和生命周期判断，不能机械插入这段代码。
- 自定义 `net_bool`、`net_byte`、`net_float`、`net_string` 等必须在两端以一致结构创建，通常在 `SetPristine()` 前完成；原版 `netvars.lua` 明确说明不一致会导致实体反序列化失败。
- 网络状态通常由服务器 `:set(value)`、两端 `:value()` 读取，客户端根据 dirty 事件更新显示。网络同步不会自动变成存档持久化。
- 需要客户端副本的自定义组件查看 `AddReplicableComponent(name)` 与 `scripts/replicas/`；仅仅新增一个组件文件不会自动同步其全部字段。
- 自定义操作查看 `AddModRPCHandler(namespace, name, fn)`、`GetModRPC(namespace, name)`、`SendModRPCToServer(id_table, ...)`；按接口要求注册双方需要的 RPC，服务器校验调用者、参数、距离、权限及必要的调用频率。
- 跨分片通信使用对应 shard RPC；不能假定地面与洞穴共享 Lua 进程、全局表、实体引用或计时任务。

## 7. Prefab、配方与资源

- 新增 Prefab 在 `PrefabFiles` 中列出文件名，不带 `.lua`；文件内返回 `Prefab(...)`，依赖和资源按原版同类实体声明。运行期全局资源通过 `Assets` 等适当入口注册。
- 当前 DST 新配方使用 `AddRecipe2(name, ingredients, tech, config, filters)`；材料使用 `Ingredient`，科技使用 `TECH`，数量、图集、图片等进入 `config`，分类为 `filters` 列表。
- `AddRecipe`、`Recipe`、`AddRecipeTab` 的旧教程不能直接套用到当前 DST；本机 `modutil.lua` 仍有兼容入口及弃用警告。需要调整已有配方时先查看 `AddRecipePostInit`，已有配方添加分类可查看 `AddRecipeToFilter(recipe_name, filter_name)`。
- 名称与描述按需写入 `STRINGS.NAMES`、`STRINGS.RECIPE_DESC`、`STRINGS.CHARACTERS.GENERIC.DESCRIBE`；键名通常使用对应 Prefab 的大写形式。
- 界面和物品贴图通常需要 `.tex` 配合 `.xml` 图集；动画需使用游戏可加载的编译资源并匹配 Bank、Build、动画名。不能仅改扩展名把 PNG 或普通 ZIP 变成游戏资源。
- 需要美术编译或上传时再核对 Steam 中可用的 Don't Starve Mod Tools 及其实际版本。本次未安装、启动或验证 Mod Tools，不承诺旧教程中的工具名称、菜单和外部下载链接仍有效。

## 8. 生命周期、性能与存档

- 优先事件驱动，使用 `ListenForEvent`；定时任务使用 `DoTaskInTime`、`DoPeriodicTask`。保存回调或任务句柄，在功能关闭、重新绑定或对象生命周期变化时按需移除回调、取消任务，防止重复注册和重复执行。
- 不在每帧或短周期内扫描全世界实体；使用合理范围、标签过滤和较低频率，先测量再优化。对成批生成的实体尤其注意初始化和轮询成本。
- 需要持久保存的状态通过组件或实体的 `OnSave`、`OnLoad` 实现；读取旧存档允许字段缺失并提供合理默认值。实体关联按游戏的保存引用机制处理，不直接序列化完整实例。
- 在独立测试世界验证保存、退出、重载和版本升级；新增实体或组件时记录停用模组对存档的影响。保护用户正式存档，涉及迁移先备份。

## 9. 调试与验收

1. 记录目标游戏版本、Mod 版本、配置和启用列表；定位当前真实日志，先看首个 Lua 错误及完整堆栈，再追踪源码。不要把旧日志中的游戏版本当作当前安装版本。
2. 使用独立测试世界，仅启用待测模组及必要依赖，验证加载与核心功能；与无模组结果对照。
3. 按功能覆盖房主、另一台远端客户端、专用服务器，以及启用洞穴后的地面/洞穴切换、重连、死亡复活和存档重载。界面功能重点看客户端；权威玩法重点核对服务器结果。
4. 仅在测试世界按需使用 `c_spawn("prefab")`、`c_give("prefab")`、`c_save()` 等原版调试命令，明确本地/远程控制台的执行侧；这些命令会改变测试状态。
5. 日志查看客户端 `client_log.txt`，以及实际启动配置对应的 Master/Caves 服务器日志；专用服常在 `<cluster_root>\Master\server_log.txt`、`<cluster_root>\Caves\server_log.txt`，以真实路径为准。
6. `mods/modsettings.lua` 中的 `ForceEnableMod`、`EnableModDebugPrint`、`EnableModError` 仅用于按需调试。修改前保存原内容，结束后恢复；不要默认关闭崩溃后的 Mod 禁用机制。
7. 语法检查只说明语法可解析，静态源码检查只说明调用与结构有依据；“已加载”“已进入世界”“多人功能正常”“长时间稳定”必须分别取得证据。未进游戏测试时明确说明。

## 10. 部署、发布与交付

- 每次修改香奈美的运行代码、配置或资源并通过验证后，自动同步本机实际加载的模组副本。交付前核对源码、安装目录和加载版本，并确认本机安装包含本次改动。
- 专用服的 `mods/dedicated_server_mods_setup.lua` 中，`ServerModSetup("WorkshopID")` 负责下载；每个分片的 `modoverrides.lua` 负责启用与配置，这是两个不同步骤。
- 地面与洞穴都需要的模组要分别核对 Master/Caves 的启用状态、配置和版本；不能仅凭下载成功或大厅可见宣布模组正常。
- Workshop 发布前准备清楚的功能说明、版本、依赖、配置说明、兼容范围和必要截图；更新时同步元信息与实际文件。发布或覆盖已有 Workshop 条目需要用户明确授权。
- 按 Klei 官方政策处理代码与素材许可：引用他人内容需有相应许可和署名，第三方美术应附许可链接；不要绕过皮肤、DLC 或产品所有权。镜像公开可读不代表可任意重新分发。
- 最终只打包运行必需内容；不包含日志、个人存档、令牌、下载缓存或整份游戏源码。交付时说明改动、安装位置、测试范围和未验证项。
- 临时解压、依赖缓存和构建产物优先放到项目所在 D 盘或 `D:\SOFTWARE\CodexData\temp`，遵守环境中的缓存路径；结束时仅清理本次创建且已废弃的临时产物。

## 11. 已查阅来源与后续查证入口

以下链接于 2026-10-26 检索或读取。论坛部分页面直接抓取返回 403，本次只采用能从检索正文确认的内容，并对关键接口交叉核对实际源码；不能声称已完整读过所有论坛附件和回复。

- [Klei 官方：Modding Don't Starve and Don't Starve Together](https://support.klei.com/hc/en-us/articles/360029555992-Modding-Don-t-Starve-and-Don-t-Starve-Together)：可修改范围、素材授权及公开发布政策。
- [Klei 论坛：Introduction to Modding](https://kleiforums.com/forums/topic/50773-guide-modding-practices-introduction-to-modding/)：社区入门资料，入口文件和目录结构；2015 年教程，示例要按当前版本复核。
- [Klei 论坛：Getting started with modding DST](https://kleiforums.com/forums/topic/47353-guide-getting-started-with-modding-dst-and-some-general-tips-for-ds-as-well/)：rezecib 的社区教程，阅读源码和 DS/DST 差异；旧教程不能直接作为当前接口契约。
- [Klei 开发者帖：Updated Mod Tools](https://kleiforums.com/forums/topic/52008-updated-mod-tools/)：Workshop 客户端/服务端分类，以及由现有 `modinfo` 标记推导服务端分类的说明。
- [Klei 论坛：Crafting help](https://kleiforums.com/forums/topic/138981-crafting-help/)：新配方接口 `AddRecipe2` 和筛选分类的社区示例，已与本机实现交叉核对。
- [Klei 论坛：Dedicated Server Mod Setup Guide](https://kleiforums.com/forums/topic/96433-dedicated-server-mod-setup-guide/)：社区专用服教程；区分下载文件与每个分片的启用文件，具体路径以当前启动参数为准。
- [GitHub：taichunmin/dont-starve-together-game-scripts](https://github.com/taichunmin/dont-starve-together-game-scripts)：**非官方原版脚本镜像**。本次查到的默认分支最新提交为 `0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64`，提交日期为 2024-09-09；明显早于本机版本，以下固定提交链接用于可追溯参考。
- [镜像 modutil.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/modutil.lua)：钩子、配置、配方、资源和 RPC 扩展入口。
- [镜像 mods.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/mods.lua)：Mod 环境、`GLOBAL`、`modimport` 和加载流程。
- [镜像 modindex.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/modindex.lua)：元信息、兼容字段、配置和客户端要求。
- [镜像 prefabs/spear.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/prefabs/spear.lua)：可核对的联网物品构造例子，`SetPristine()` 和服务端分界已与本机脚本确认。
- [镜像 netvars.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/netvars.lua)：网络变量类型、两端声明一致性、读写与 dirty 事件说明。
- [镜像 networkclientrpc.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/networkclientrpc.lua)：Mod RPC 的注册、编号查找和发送实现。
- [镜像 entityscript.lua](https://github.com/taichunmin/dont-starve-together-game-scripts/blob/0dea2f76e0321ecc6c9faa8e1e5bdd80a5fc1b64/entityscript.lua)：事件、任务和实体/组件保存加载流程。

后续开发先按待改对象定位本机脚本：实体查 `scripts/prefabs/`，玩法查 `scripts/components/`，客户端读取查 `scripts/replicas/`，制造查 `scripts/recipe.lua` 与 `scripts/recipes.lua`，动作查 `scripts/actions.lua`、`scripts/componentactions.lua` 与 `scripts/stategraphs/`，世界生成查 `scripts/map/`。游戏更新后重新核对具体签名和调用处。

## 12. 香奈美 GitHub 与发布同步

- 用户于 2026-11-16 指定 GitHub 仓库 `https://github.com/tongxinaiyazi/kanami-Don-t-Starve-mod.git`，本地 Git 根目录为 `D:\SOFTWARE\项目\饥荒`，默认分支为 `main`，远端名为 `origin`。
- 该仓库跟踪香奈美角色模组、配套资源包源码、当前美术工程、工具、测试、发布资料和版本校验清单。按 `.gitignore` 管理共享工作区中的其他项目、历史副本、依赖缓存、日志及生成 ZIP。
- 以后每次用户要求“准备发布包”“打包发布”或同义操作，都要在完成版本更新、相应验证和打包后，提交本次相关变化并推送到此 GitHub。用户已授权此后每次发布准备时同步推送，无需重复请求确认。
- 打包继续使用 `tools/package_kanami.py`，工坊待上传目录继续采用 `D:\SOFTWARE\DSTWorkshop\klbq_kanami`，ZIP 位于项目 `dist`，文案位于对应版本的 `发布资料` 目录。
- 临时同步本机工坊下载副本时，同时核对 `mod.manifest` 的路径哈希是否覆盖当前运行文件。新增 Lua 路径需要纳入该清单，并完整重启游戏加载。可使用 `tools/run_kanami_engine.py --workshop-runtime --inventory-guard-only --equipment` 在隔离世界验证实际工坊副本及清单。
- 提交前检查暂存文件及差异，排除凭据和本地运行数据。使用普通 `git push origin main`，保留远端已有提交。内容无变化时可直接核对并推送当前提交。
- 推送后读取远端 `main` 的提交号，与本地 `HEAD` 核对。网络或鉴权失败时保留已生成的发布包，排查并重试，交付时准确说明打包与推送各自的完成状态。

## 13. 香奈美每次修改后的本地安装

- 用户于 2026-11-16 明确要求每次修改后更新替换本地 Mod。开发验证通过后，执行 `powershell -File tools/deploy_kanami.ps1`，同步本地开发副本与已订阅的工坊 3827702076 实际运行目录。
- 本地部署独立于发布打包。默认更新 `E:\steam\steamapps\common\Don't Starve Together\mods\klbq_kanami` 和 `E:\steam\steamapps\workshop\content\322330\3827702076`，以实际安装及加载日志核对目录。
- 部署工具备份被替换文件、更新工坊 `mod.manifest`，并逐文件核对 SHA256。检查结果写入 `docs/reports/local-deploy-latest.json`。
- 运行代码、配置结构、资源或新增路径需要完整退出游戏后替换，随后重载 Lua 和网络变量。仅版本标记、加载日志版本与说明文档变化时，部署工具先验证其余内容完全一致，再同步文件并提示完整重启后加载新版本信息。
- 交付前验证实际工坊副本的加载及本次功能。可以执行 `tools/run_kanami_engine.py --workshop-runtime` 的对应专项检查，明确客户端实际操作的验证范围。
