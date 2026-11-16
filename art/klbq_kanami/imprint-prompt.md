# 拓印终端美术生成记录

当前方案由用户后续要求确定：轻薄蓝白底座、小型投影、短握柄；闲置只保留一个全息圆盘。原生CHOP／MINE／DIG自动投影对应的全息斧头／镐／铲，停止作业返回圆盘，无手动模式切换。

- 工具：内置 `image_gen`，生成硬件与投影图集，再以机械编译注册、组合。
- 最初参考：`mods/klbq_resources/art/items/klbq_resource_tracing_plate.png`。
- 当前硬件原图：`art/klbq_kanami/imprint-hardware.png`。
- 当前投影图集：`art/klbq_kanami/imprint-projections.png`。
- 合成闲置图：`art/klbq_kanami/imprint-tool.png`。
- 各形态合成图：`art/klbq_kanami/imprint-forms/idle.png`、`chop.png`、`mine.png`、`dig.png`。
- 用途：`klbq_imprint_tool` 的落地、手持与64像素物品栏图标；不替换资源包拓印基板或角色本体。

## 当前两次生成要求摘要

以下记录画面要求，不声称是工具调用完整提示词的逐字导出；完整调用提示词可由主任务另行补录。

第一步，编辑v2图获得稳定硬件：保持用户选择的轻薄蓝白底座、小型结构与短握柄，移除所有悬浮全息圆盘，仅留下机械底座和握柄，四个LED插槽未点亮。维持原来的近侧三分之四视角、清晰黑色墨线、平涂与克制纸感阴影，透明背景，不含文字、人物、手或水印。硬件的轮廓与握柄不随投影变化。

第二步，生成独立2×2透明全息图集：四格分别是idle单个青蓝色全息圆盘、chop青蓝色能量斧头、mine青蓝色能量镐、dig青蓝色能量铲。四格只包含全息投影，不含机械底座和握柄；风格、朝向、色温和投影连接逻辑一致，形状在游戏小尺寸下仍可辨认。采用《饥荒联机版》风格的原创墨线和清晰剪影，无文字、数字、人物或水印。

## 机械注册与编译

编译流程从独立全息图集注册idle／chop／mine／dig四种形态，使用同一份硬件原图合成，保持底座、握柄、手部锚点稳定。四灯表示砍伐、采矿、挖掘、坚硬作业能力，初始全部关闭；4种形态各覆盖16种灯状态组合，生成可加载落地／手持动画与64像素物品栏图标。运行期沿原生作业状态自动切换投影并在停止后复原，不增加玩家模式按钮，不改变角色其他贴图、骨骼或动作。

## 历史草案（已覆盖）

初稿v1采用双青蓝全息圆盘、灰白／海军蓝底座与底部握柄；用户评价不佳后选择轻薄蓝白底座、小型双圆盘、短握柄的v2。用户再明确要求闲置单圆盘和原生动作投影工具，因此双圆盘要求只保留作美术工程历史，不再是当前外观标准。v1／v2留在drafts，不混入当前运行资源。

## 历史v2提示词（已覆盖）

用户否决v1，选择“贴近原作：轻薄蓝白底座、小型双圆盘、短握柄”。当时生成的双圆盘v2与v1均保留在drafts作为工程历史，现有imprint-tool.png已改为单圆盘机械合成结果。v2同样由内置image_gen基于原资源图制作，当时编译锚点与四枚状态灯随v2重新注册；当前方案以本文前半部分为准。完整生成要求：

Create a beautiful compact handheld Imprint Terminal sprite for DST, faithful to the provided Strinova tracing-plate reference. Two small cyan concentric discs stacked diagonally over a pale grey-white/navy thin base, short grip about one quarter of object height, four tiny unlit indicator sockets on the front bezel. Clean near-side three-quarter view, confident black ink, flatter anime color blocks, restrained paper-textured shading, readable at64px, transparent background. No letters, digits, hands, people, watermark, tall projection column or giant halo. Keep original blue-white double-disc identity while making the prop lighter and sleeker.
