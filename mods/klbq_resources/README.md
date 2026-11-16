# 香奈美附属 · 卡拉彼丘资源 0.1.0

已实现的 DST 独立物品包，两端必装。保留 20 项资源及固定 Prefab ID，方便以后合并。支持拾取、普通背包/箱子收纳、每组 40 的同类堆叠、拆分与原生存档；已接入浮水组件。

不添加配方、掉落、赠送、抽卡、兑换、商店、属性或角色技能。战令币、活动凭录、历史活动物品与赛季专用资源仍被排除。

- [运行包](release/klbq_resources-0.1.0.zip)：解压到游戏安装目录的 `mods/klbq_resources/`，使该目录直接含 `modinfo.lua`。所有加入者同版；地面与洞穴均需启用。
- [融合与调用](docs/融合与调用.md)：查询接口、开发查看与合并步骤。
- [验证记录](docs/reports/verification.md)：代码、编译资源、运行 ZIP 及实际隔离专服保存重载证据。
- [物品规格](docs/物品设计.md)、[原作核验](docs/资料核验.md)、[设计比对目录](docs/resource-catalog.json)。

```lua
local Resources = require("klbq_resources/api")
local prefab = Resources.GetPrefab("stringsea_beacon")
-- klbq_resource_stringsea_beacon
```

本轮只改附属模组，没有部署到游戏目录，未写入香奈美、莉莉丝或正式存档；主模组同期出现的 v1.0.0 变动已保留。运行包可独立启用，不要求香奈美模组。合并入口是 `require("klbq_resources/register").Install(env)`。

运行美术由内置 imagegen 重绘；[图集](art/resource-icons.png)、[最终提示词](art/imagegen-prompt.txt)与裁切布局保存在 `art/`。原作参考图仅位于 `docs/references/`，未进入运行包。原作设定及相关权利属于《卡拉彼丘》权利人，本包为非官方同人作品。

已通过无渲染专服加载、物品操作和保存重载；未进行图形客户端、另一台远端客户端、实际海面浮水及洞穴跨分片验收。
