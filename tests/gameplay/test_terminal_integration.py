"""Reuse the resource add-on identity and native Charlie loot generation."""
import hashlib,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime
from resource_fixture import preload_resources
from test_review_regressions import vanilla

class TerminalIntegration(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        preload_resources(self.lua)
        self.lua.execute('''
          TheWorld={ismastersim=true}; LootDropper={}
          LootTables={charlie_boss={{'dreadstone',1}}}
          function makeenv(name)
            STRINGS=STRINGS or {NAMES={},CHARACTERS={GENERIC={DESCRIBE={}}}}
            local e={GLOBAL=_G,modname=name,PrefabFiles={'existing'},Assets={},icons={},hooks={}}
            e.Asset=function(kind,file)return {kind=kind,file=file}end
            e.RegisterInventoryItemAtlas=function(a,i)e.icons[#e.icons+1]=i end
            e.AddPrefabPostInit=function(n,f)e.hooks[n]=f end
            return e
          end
          env=makeenv('klbq_kanami')
          function boss()
            local b={components={},HasTag=function()return false end,PushEvent=function()end}
            b.components.lootdropper=setmetatable({inst=b,chanceloottable='charlie_boss'}, {__index=LootDropper})
            return b
          end
        ''')
        for method in ('AddChanceLoot','GenerateLoot'):
            self.lua.execute(vanilla('components/lootdropper.lua','function LootDropper:'+method+'('))

    def test_embedded_resource_runtime_is_the_addon_original(self):
        for rel in ('scripts/klbq_resources/catalog.lua','scripts/klbq_resources/api.lua','scripts/klbq_resources/register.lua','scripts/prefabs/klbq_resources.lua','anim/klbq_resources_items.zip','images/klbq_resources_items.xml','images/klbq_resources_items.tex'):
            self.assertEqual(hashlib.sha256((ROOT/'mods/klbq_resources'/rel).read_bytes()).digest(),hashlib.sha256((ROOT/'mods/klbq_kanami'/rel).read_bytes()).digest(),rel)
        self.lua.execute('d=require("klbq_resources/api").GetDefinition("terminal_kanami")')
        self.assertEqual(self.lua.eval('d.prefab'),'klbq_resource_terminal_kanami')
        self.assertEqual(self.lua.eval('d.name'),'香奈美序列因子终端')

    def test_addon_and_main_share_registration_in_either_load_order(self):
        for first in ('klbq_kanami','klbq_resources'):
            self.setUp()
            self.lua.execute('''
              first=makeenv(...);second=makeenv('second')
              local register=require('klbq_resources/register')
              assert(register.Install(first));assert(not register.Install(second))
            ''',first)
            self.assertEqual(self.lua.eval('#first.PrefabFiles'),2)
            self.assertEqual(self.lua.eval('#second.PrefabFiles'),1)
            self.assertEqual(self.lua.eval('#first.icons'),20)

    def test_charlie_native_loot_preserves_existing_and_adds_exactly_one_terminal(self):
        self.lua.execute('''
          require('klbq_kanami/resources').Install(env)
          b=boss();env.hooks.charlie_boss(b);env.hooks.charlie_boss(b)
          loot=b.components.lootdropper:GenerateLoot()
        ''')
        self.assertEqual(sorted(self.lua.globals().loot.values()),['dreadstone','klbq_resource_terminal_kanami'])
        self.assertEqual(self.lua.eval('#b.components.lootdropper.chanceloot'),1)
        self.assertIsNone(self.lua.eval('env.hooks.charlie_npc'))
        self.assertIsNone(self.lua.eval('env.hooks.charlie_hand'))

    def test_client_does_not_change_loot_and_reload_gets_one_new_registration(self):
        self.lua.execute('''
          require('klbq_kanami/resources').Install(env)
          TheWorld.ismastersim=false;b=boss();env.hooks.charlie_boss(b)
        ''')
        self.assertIsNone(self.lua.eval('b.components.lootdropper.chanceloot'))
        self.lua.execute('''
          TheWorld.ismastersim=true;b=boss();env.hooks.charlie_boss(b)
          saved=b.components.lootdropper:GenerateLoot()
        ''')
        self.assertEqual(list(self.lua.globals().saved.values()).count('klbq_resource_terminal_kanami'),1)

if __name__=='__main__':unittest.main()
