"""Compile the generated resource atlas with the locally installed Klei tools.

Image handling here is mechanical sprite slicing, sizing and texture packing.
The painted source was produced with image_gen; reference artwork is not used.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageOps

MOD=Path(__file__).resolve().parents[1]
TOOLS=Path("E:/steam/steamapps/common/Don't Starve Mod Tools/mod_tools")
DEFAULT_STAGE=Path("D:/SOFTWARE/CodexData/temp/klbq_resources_assets")
RESAMPLE=Image.Resampling.LANCZOS

def xml_write(node,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    ET.indent(node)
    ET.ElementTree(node).write(path,encoding="utf-8",xml_declaration=True)

def fitted(image,size,pad=0):
    box=image.getchannel("A").point(lambda v:255 if v>24 else 0).getbbox()
    if box is None:
        raise ValueError("Empty source sprite")
    image=image.crop(box)
    image=ImageOps.contain(image,(size[0]-2*pad,size[1]-2*pad),RESAMPLE)
    canvas=Image.new("RGBA",size)
    canvas.alpha_composite(image,((size[0]-image.width)//2,(size[1]-image.height)//2))
    return canvas

def run(command,cwd,log):
    result=subprocess.run([str(x) for x in command],cwd=cwd,capture_output=True,text=True,errors="replace")
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(result.stdout+result.stderr,encoding="utf-8")
    if result.returncode:
        raise RuntimeError("Klei tool failed: "+str(command[0])+"\n"+result.stdout[-2000:]+result.stderr[-2000:])

def texture(image,path,entries,stage):
    folder=stage/"textures"
    folder.mkdir(parents=True,exist_ok=True)
    png=folder/(path.stem+".png")
    tex=folder/(path.stem+".tex")
    image.save(png)
    run([TOOLS/"tools/bin/TextureConverter.exe","--swizzle","--format","bc3","--platform","opengl",
         "--premultiply","--mipmap","-i",png,"-o",tex],stage,MOD/"art/build-logs"/(path.stem+".log"))
    path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(tex,path.with_suffix(".tex"))
    atlas=ET.Element("Atlas")
    ET.SubElement(atlas,"Texture",filename=path.with_suffix(".tex").name)
    elements=ET.SubElement(atlas,"Elements")
    for name,(x,y,w,h) in entries.items():
        ET.SubElement(elements,"Element",name=name,
                      u1=str((x+.5)/image.width),u2=str((x+w-.5)/image.width),
                      v1=str(1-(y+h-.5)/image.height),v2=str(1-(y+.5)/image.height))
    xml_write(atlas,path.with_suffix(".xml"))

def build(stage):
    if not TOOLS.is_dir():
        raise FileNotFoundError("Installed Don't Starve Mod Tools not found: "+str(TOOLS))
    if stage.exists() and not (stage/".klbq-resources-owned").is_file():
        raise RuntimeError("Refusing an unowned build directory: "+str(stage))
    stage.mkdir(parents=True,exist_ok=True)
    (stage/".klbq-resources-owned").write_text("klbq_resources asset build\n",encoding="utf-8")
    items=json.loads((MOD/"docs/resource-catalog.json").read_text(encoding="utf-8"))["items"]
    source=Image.open(MOD/"art/resource-icons.png").convert("RGBA")
    layout=json.loads((MOD/"art/asset-layout.json").read_text(encoding="utf-8"))
    if list(source.size)!=layout["source_size"]:
        raise ValueError("Source size changed; inspect and update art/asset-layout.json first")
    xs,ys=layout["x_edges"],layout["y_edges"]
    art=MOD/"art/items"
    art.mkdir(parents=True,exist_ok=True)
    inventory=Image.new("RGBA",(512,512));entries={}
    build_xml=ET.Element("Build",name="klbq_resources_items")
    anims=ET.Element("Anims")
    exported=MOD/"art/exported/klbq_resources_items"
    exported.mkdir(parents=True,exist_ok=True)
    frames={}
    for index,item in enumerate(items):
        row,col=divmod(index,4)
        region=(xs[col],ys[row],xs[col+1],ys[row+1])
        cutout=source.crop(region)
        sprite=fitted(cutout,(256,256),8)
        name=item["prefab"]
        sprite.save(art/(name+".png"))
        frames[name]=sprite
        icon=fitted(sprite,(64,64),5)
        x,y=18+(index%5)*100,28+(index//5)*120
        inventory.alpha_composite(icon,(x,y))
        entries[name+".tex"]=(x,y,64,64)

        ground=fitted(sprite,(80,80),2)
        ground.save(exported/(name+".png"))
        symbol=ET.SubElement(build_xml,"Symbol",name=name)
        ET.SubElement(symbol,"Frame",framenum="0",duration="1",x="0",y="-40",w="80",h="80",image=name)
        animation=ET.SubElement(anims,"anim",name=name,root="klbq_resources_items",framerate="30")
        frame=ET.SubElement(animation,"frame",x="-45",y="-85",w="90",h="90")
        ET.SubElement(frame,"element",name=name,frame="0",layername="object",z_index="0",
                      m_a="1",m_b="0",m_c="0",m_d="1",m_tx="0",m_ty="0")
    xml_write(build_xml,exported/"build.xml")
    xml_write(anims,exported/"animation.xml")
    archive=stage/"klbq_resources_items.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as output:
        for path in sorted(exported.iterdir()):
            if path.suffix in (".xml",".png"):
                output.write(path,path.name)
    compiled=stage/"compiled"
    compiled.mkdir(exist_ok=True)
    run([TOOLS/"buildtools/windows/Python27/python.exe","-B",TOOLS/"tools/scripts/buildanimation.py",
         archive,"--outputdir="+str(compiled),"--force","--scale=1","--textureformat=bc3","--platform=opengl"],
        stage,MOD/"art/build-logs/animation.log")
    target=MOD/"anim/klbq_resources_items.zip"
    target.parent.mkdir(exist_ok=True)
    shutil.copy2(compiled/"anim/klbq_resources_items.zip",target)
    texture(inventory,MOD/"images/klbq_resources_items",entries,stage)
    inventory.save(MOD/"art/inventory-atlas.png")
    icon=fitted(frames["klbq_resource_stringsea_beacon"],(128,128),10)
    texture(icon,MOD/"modicon",{"modicon.tex":(0,0,128,128)},stage)
    icon.save(MOD/"art/modicon.png")
    # Grid preview of exactly the cropped runtime sprites; labels stay in docs.
    preview=Image.new("RGBA",(960,1200))
    for index,item in enumerate(items):
        row,col=divmod(index,4)
        preview.alpha_composite(fitted(frames[item["prefab"]],(220,220),8),(col*240+10,row*240+10))
    preview.save(MOD/"art/runtime-preview.png")
    print(json.dumps({"items":len(items),"inventory_size":[512,512],
                      "compiled_animation_bytes":target.stat().st_size,
                      "stage":str(stage)},ensure_ascii=False))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",type=Path,default=DEFAULT_STAGE)
    args=parser.parse_args()
    build(args.stage.resolve())
