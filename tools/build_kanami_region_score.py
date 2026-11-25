"""Compile the score's original icon and floor sprite with the Kanami asset pipeline."""
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from build_kanami_assets import (
    ART, MOD, RESAMPLE, add_frame, anim_xml, atlas, compile_build, simple_animation,
)


def main():
    sprite = Image.new("RGBA", (384, 384))
    d = ImageDraw.Draw(sprite)
    ink = "#3d3354"
    d.polygon([(48, 127), (249, 82), (341, 243), (133, 315)], fill="#806379", outline=ink, width=10)
    d.polygon([(130, 284), (319, 223), (339, 243), (135, 306)], fill="#f3e0ba", outline=ink, width=7)
    for x in (176, 203, 242, 274):
        d.line((x, 286-(x-176)*.31, x+45, 272-(x-176)*.31), fill="#c7a98c", width=3)
    d.polygon([(45, 122), (237, 71), (313, 219), (121, 292)], fill="#9684bc", outline=ink, width=10)
    d.polygon([(66, 131), (226, 86), (292, 211), (129, 273)], fill="#fff1ca", outline="#ce9f5d", width=7)
    d.line([(76, 129), (137, 259)], fill="#638c82", width=12)
    for offset in range(0, 37, 9):
        d.line((108+offset*.56, 141+offset, 250+offset*.56, 101+offset),
               fill="#b4a18a", width=2)
    for x, y in ((168, 164), (210, 138)):
        d.ellipse((x-11, y-7, x+10, y+7), fill="#856ca8")
        d.line((x+7, y-2, x-1, y-36), fill="#856ca8", width=6)
    d.line((167, 128, 207, 102), fill="#856ca8", width=8)
    d.polygon([(263, 245), (269, 276), (288, 271), (295, 260), (282, 238)], fill="#b98367", outline=ink, width=4)
    d.arc((153, 187, 231, 237), 190, 350, fill="#c58f54", width=6)
    for x, y in ((89, 116), (149, 244), (273, 195)):
        d.ellipse((x-5, y-5, x+5, y+5), fill="#e4b063")
    src = sprite.resize((96, 96), RESAMPLE)
    src.save(ART / "klbq_region_score.png")
    inventory = sprite.resize((64, 64), RESAMPLE)
    atlas(inventory, MOD / "images/klbq_region_score", {"klbq_region_score.tex": (0, 0, 64, 64)})
    build = ET.Element("Build", name="klbq_region_score")
    frame = add_frame(build, "score", 0, src, (0, 0, 96, 96))
    compile_build("klbq_region_score", build, dict([frame]),
                  anim_xml([simple_animation("klbq_region_score", "score", size=(96, 96))]))


if __name__ == "__main__":
    main()
