# 2026-11-01 后颈原画修订

使用内置 imagegen，透明输出；没有使用第三方模组美术。原始生成图保存在本工程head-back-nape-v2.png与neck-connector.png，运行切片在rig/parts。双马尾切片及坐标保持原样。

## 后脑编辑提示

Edit target: the existing Kanami back-of-head sprite. Front head is a proportion reference only. Keep silver-lilac hair, pink highlights, black/pink heart ornament, cowlick and hand-painted chibi styling. Replace the long central back-hair curtain with a short gathered nape hairline and a visible slender skin neck. Do not draw pigtails; they are separate rig sprites. Preserve the upper skull silhouette. Canvas aspect 172:188; nape hairline around 73% height, narrow skin neck around 73–82%, central lower canvas transparent. No face, torso, collar or text. Transparent background.

## 独立颈部连接层提示

Create only a short bare BACK NECK connector sprite matching the corrected rear head. Pale warm peach skin, restrained rosy side shading, narrow dark purple side outlines. Short concave-sided neck section, relative width24 height22. Open flat top and bottom edges hidden by head and collar. Solid skin without holes. No head, hair, face, shoulders, clothes, ornaments or text. Transparent background. This is a rig attachment cutout, not a full illustration.

## 定位

后脑全画布缩放到172×188，保留透明定位空间。颈部连接图裁取有效alpha区域，作为24×22独立注册切片，局部中心(0,-88)，不会随构建自动变更。具体关节偏移和全帧连接测试在构建器及test_assets.py中。
