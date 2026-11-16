name = "[本地测试] 卡拉彼丘资源验证"
description = "仅供隔离离线测试世界使用，不发布。"
author = "本地开发"
version = "0.1.0"
api_version = 10
dst_compatible = true
client_only_mod = false
all_clients_require_mod = true
configuration_options = {
    {name="phase", label="测试阶段", default="create",
     options={{description="创建",data="create"},{description="重载",data="reload"}}},
}
