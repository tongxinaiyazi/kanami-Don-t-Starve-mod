"""Build an allowlisted, deterministic runtime ZIP without development data."""
from pathlib import Path
import hashlib, json, re, zipfile

MOD=Path(__file__).resolve().parents[1]
FILES=["modinfo.lua","modmain.lua","modicon.xml","modicon.tex",
       "scripts/klbq_resources/catalog.lua","scripts/klbq_resources/api.lua",
       "scripts/klbq_resources/register.lua","scripts/prefabs/klbq_resources.lua",
       "images/klbq_resources_items.xml","images/klbq_resources_items.tex",
       "anim/klbq_resources_items.zip"]

def main():
    text=(MOD/"modinfo.lua").read_text(encoding="utf-8")
    version=re.search(r'version\s*=\s*"([^"]+)"',text).group(1)
    readme=("卡拉彼丘资源 "+version+"\n\n"
            "DST 两端必装的独立物品包，20 种资源，每组 40。\n"
            "没有配方、掉落、开局赠送、抽卡、商店或使用效果。\n"
            "不包含战令币、活动凭录、历史活动与赛季专用资源。\n\n"
            "安装：在游戏安装目录 mods 下新建 klbq_resources 文件夹，\n"
            "把本 ZIP 内容直接解压进去，modinfo.lua 位于该文件夹根部。\n"
            "重启游戏，在世界的服务器模组列表启用“卡拉彼丘资源”。\n"
            "所有加入者使用同一版本；启用洞穴时两片均需启用。\n"
            "本包可独立启用，不要求香奈美角色模组，也不修改其文件。\n\n"
            "当前物品暂没有自然来源和主动用途。开发测试世界可通过\n"
            'c_spawn("klbq_resource_stringsea_beacon") 等原版控制台命令查看。\n'
            "开发接口与融合说明在项目源码 docs/融合与调用.md。\n\n"
            "原作设定来源《卡拉彼丘》，本包为非官方同人作品。\n"
            "运行美术经 image_gen 重新绘制；未打包原作参考图。\n"
            "不要在仍含这些物品的正式存档中随意停用物品包。\n")
    output=MOD/"release"
    output.mkdir(exist_ok=True)
    target=output/("klbq_resources-"+version+".zip")
    payload={name:(MOD/name).read_bytes() for name in FILES}
    payload["README.txt"]=readme.encode("utf-8")
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(payload.items()):
            info=zipfile.ZipInfo(name,(2026,10,30,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            z.writestr(info,data)
    manifest={"version":version,"archive":target.name,"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
              "bytes":target.stat().st_size,"files":sorted(payload)}
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=="__main__":main()
