"""Build the imprint turf's original terrain texture, icon, and dropped item."""
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from build_kanami_assets import (
    ART, MOD, RESAMPLE, add_frame, anim_xml, atlas, compile_build, convert_tex, simple_animation,
)

BLUEPRINT = ART / "imprint-turf"
NAME = "turf_klbq_imprint"


def metal_panel(index):
    panel = Image.new("RGBA", (256, 256), "#171e2e")
    d = ImageDraw.Draw(panel)
    edge = (16, 10, 240, 246)
    d.rounded_rectangle(edge, radius=22, fill="#1b2939", outline="#121927", width=6)
    d.rounded_rectangle((22, 15, 234, 238), radius=18, fill="#2d4053", outline="#4b6274", width=3)
    d.polygon([(39, 29), (201, 29), (219, 47), (219, 202), (199, 222), (55, 222), (36, 203), (36, 49)],
              fill="#29394a", outline="#202d3e", width=5)
    d.line([(37, 54),(54, 37),(200, 37)], fill="#5d7285", width=2)
    d.line([(221, 193),(201, 218),(68, 218)], fill="#192435", width=3)
    d.polygon([(91, 52),(165, 52),(203, 128),(162, 199),(91, 199),(51, 128)], fill="#32445a")
    d.polygon([(99, 66),(155, 66),(189, 128),(154, 181),(101, 181),(68, 128)],
              fill="#263747", outline="#5a7581", width=2)
    for reflect in (False, True):
        def flip(x, y):
            return (256-x, 256-y) if reflect else (x, y)
        d.line([flip(x,y) for x,y in [(40,80),(65,80),(86,59),(109,59)]], fill="#61a3aa", width=5)
        d.line([flip(x,y) for x,y in [(42,92),(63,92),(72,83)]], fill="#345b70", width=3)
        for x in (56,74,92):
            cx,cy=flip(x,205)
            d.line((cx,cy-2,cx+7,cy-2), fill="#8481aa" if index % 3 == 0 else "#507084", width=3)
        for x,y in ((46,43),(208,43)):
            cx,cy=flip(x,y)
            d.ellipse((cx-3,cy-3,cx+3,cy+3), fill="#85909c", outline="#182737")
    port = "#77c3be" if index % 2 == 0 else "#a99ed0"
    d.line([(106,128),(128,103),(150,128),(128,153),(106,128)], fill="#456e79", width=4)
    d.line([(114,128),(128,113),(142,128),(128,143),(114,128)], fill=port, width=3)
    d.polygon([(123,128),(128,122),(133,128),(128,134)], fill="#91bdc5")
    d.line((0,125,18,125),fill="#4e7881",width=4)
    d.line((238,125,255,125),fill="#4e7881",width=4)
    return panel


def item_sprite(panel):
    # An unfolded plate viewed from above, with a visible graphite side wall.
    base = Image.new("RGBA", (256, 256))
    d = ImageDraw.Draw(base)
    d.polygon([(20,103),(149,39),(237,101),(237,129),(108,196),(20,130)],
              fill="#475c6a", outline="#131c2a",width=7)
    d.polygon([(20,103),(108,170),(108,196),(20,130)], fill="#202c3b",outline="#131c2a",width=5)
    d.line((27,128,106,188,232,123),fill="#7296a3",width=4)
    cut = panel.crop((18,11,238,244)).convert("RGBA")
    # Map source corners to the corners of the top parallelogram.
    from PIL import ImageTransform
    # Solve the inverse affine transform directly for the two basis vectors.
    ox,oy = 23,104
    ax,ay,bx,by = 124,-63,87,64
    det = ax*by-ay*bx
    a,b = cut.width*by/det,-cut.width*bx/det
    c,e = -cut.height*ay/det,cut.height*ax/det
    top = cut.transform(base.size,ImageTransform.AffineTransform((a,b,-a*ox-b*oy,c,e,-c*ox-e*oy)),
                        resample=Image.Resampling.BICUBIC)
    base.alpha_composite(top)
    return base.crop((10,28,246,210))


def main():
    BLUEPRINT.mkdir(exist_ok=True)
    ground = Image.new("RGBA", (1024,1024))
    for index in range(16):
        var = metal_panel(index)
        if (index // 4 + index % 4) % 2:
            var = var.transpose(Image.Transpose.ROTATE_180)
        ground.paste(var,((index%4)*256,(index//4)*256))
    ground.save(BLUEPRINT / "ground.png")
    convert_tex(ground, MOD / "levels/textures/klbq_imprint_noise.tex")
    minimap = Image.new("RGBA", (256,256), "#304a60")
    draw = ImageDraw.Draw(minimap)
    for x in (0,64,128,192):
        for y in (0,64,128,192):
            draw.rectangle((x+1,y+1,x+62,y+62),fill="#38556a",outline="#293e53",width=2)
            draw.rectangle((x+22,y+22,x+42,y+42),fill="#457180")
    minimap.save(BLUEPRINT / "minimap.png")
    convert_tex(minimap, MOD / "levels/textures/klbq_imprint_mini_noise.tex")
    art = item_sprite(metal_panel(0))
    art.save(BLUEPRINT / "item.png")
    icon = Image.new("RGBA",(64,64))
    thumb = art.resize((62,48), RESAMPLE)
    icon.alpha_composite(thumb,(1,8))
    atlas(icon, MOD / "images" / NAME, {NAME+".tex": (0,0,64,64)})
    sprite = art.resize((108,84), RESAMPLE)
    build = ET.Element("Build",name=NAME)
    frame = add_frame(build,"plate",0,sprite,(0,0,108,84))
    compile_build(NAME, build, dict([frame]),
                  anim_xml([simple_animation(NAME,"plate",size=(108,84))]))


if __name__ == "__main__":
    main()
