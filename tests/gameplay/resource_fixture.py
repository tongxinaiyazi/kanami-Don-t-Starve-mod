from pathlib import Path
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]

def preload_resources(lua):
    for module in ('klbq_resources/catalog','klbq_resources/api','klbq_resources/register','klbq_kanami/resources','klbq_kanami/recipes','klbq_kanami/imprint','klbq_kanami/inventoryguard'):
        path=ROOT/'mods/klbq_kanami/scripts'/f'{module}.lua'
        lua.execute('package.preload[...] = function() '+path.read_text(encoding='utf-8')+' end',module)

def preload_midgame(lua):
    for name in ('region_actions','regions','midgame'):
        module='klbq_kanami/'+name
        path=ROOT/'mods/klbq_kanami/scripts'/f'{module}.lua'
        lua.execute('package.preload[...] = function() '+path.read_text(encoding='utf-8')+' end',module)
    with ZipFile(r"E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip") as source:
        native=source.read('scripts/prefabs/tree_rock_data.lua').decode('utf-8-sig')
    lua.execute('package.preload["prefabs/tree_rock_data"] = function() '+native+'\nend')
