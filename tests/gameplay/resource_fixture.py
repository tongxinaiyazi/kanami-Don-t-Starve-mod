from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def preload_resources(lua):
    for module in ('klbq_resources/catalog','klbq_resources/api','klbq_resources/register','klbq_kanami/resources','klbq_kanami/recipes','klbq_kanami/imprint'):
        path=ROOT/'mods/klbq_kanami/scripts'/f'{module}.lua'
        lua.execute('package.preload[...] = function() '+path.read_text(encoding='utf-8')+' end',module)
