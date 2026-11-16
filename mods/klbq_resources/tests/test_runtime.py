"""Behavior checks against the real Lua 5.1 runtime modules (engine calls stubbed)."""
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'tools' / 'python-deps'))
from lupa.lua51 import LuaRuntime

FILES = ['modinfo.lua', 'modmain.lua', 'scripts/klbq_resources/catalog.lua',
         'scripts/klbq_resources/api.lua', 'scripts/klbq_resources/register.lua',
         'scripts/prefabs/klbq_resources.lua']
CATEGORIES = {'通用货币': 'currency', '卡池凭证': 'sequence', '外观材料': 'appearance',
              '常驻模式资源': 'mode', '角色序列终端': 'terminal'}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        # Windows Lua 5.1 fopen cannot open the Unicode project path. Python reads
        # source bytes, while Lua's native require/cache still executes each module.
        preload = self.lua.eval('function(name,source) package.preload[name]=assert(loadstring(source,name)) end')
        for name in ('catalog','api','register'):
            file=ROOT / 'scripts/klbq_resources' / (name+'.lua')
            if file.exists():
                preload('klbq_resources/'+name,file.read_text(encoding='utf-8'))
        self.items = json.loads((ROOT / 'docs/resource-catalog.json').read_text(encoding='utf-8-sig'))['items']

    def module(self, name):
        self.assertTrue((ROOT / 'scripts' / (name + '.lua')).exists(), 'Missing runtime module: ' + name)
        return self.lua.eval('require')(name)

    def env(self):
        return self.lua.execute('''
            local g = {STRINGS={NAMES={OTHER="preserve"},CHARACTERS={GENERIC={DESCRIBE={OTHER="keep"}}}}}
            local e = {GLOBAL=g, modname="test_resources", PrefabFiles={"other"}, Assets={{type="ANIM",file="other.zip"}}, icons={}}
            e.Asset=function(kind,path) return {type=kind,file=path} end
            e.RegisterInventoryItemAtlas=function(atlas,image) e.icons[#e.icons+1]={atlas,image} end
            return e
        ''')

    def test_runtime_files_exist(self):
        for file in FILES:
            self.assertTrue((ROOT / file).is_file(), 'Missing runtime file: ' + file)

    def test_lua51_syntax(self):
        compile_lua = self.lua.eval('function(s,n) local f,e=loadstring(s,n); assert(f,e); return true end')
        for file in FILES:
            self.assertTrue((ROOT / file).exists(), 'Missing runtime file: ' + file)
            self.assertTrue(compile_lua((ROOT / file).read_text(encoding='utf-8'), file))

    def test_restricted_modinfo(self):
        self.assertTrue((ROOT / 'modinfo.lua').exists(), 'Missing runtime modinfo')
        e = self.lua.eval('function(s) local e={}; local f=assert(loadstring(s)); setfenv(f,e); f(); return e end')((ROOT / 'modinfo.lua').read_text(encoding='utf-8'))
        for k,v in {'api_version':10,'version':'0.1.0','dst_compatible':True,'dont_starve_compatible':False,
                    'reign_of_giants_compatible':False,'client_only_mod':False,'all_clients_require_mod':True,
                    'icon_atlas':'modicon.xml','icon':'modicon.tex'}.items():
            self.assertEqual(e[k],v,k)
        self.assertIsNone(e.configuration_options)
        self.assertIsNone(e.mod_dependencies)

    def test_exact_catalog_and_indexes(self):
        c = self.module('klbq_resources/catalog')
        for k,v in {'VERSION':'0.1.0','API_VERSION':1,'STACK_SIZE':40,'PREFIX':'klbq_resource_',
                    'ATLAS':'images/klbq_resources_items.xml','TEXTURE':'images/klbq_resources_items.tex',
                    'ANIM':'anim/klbq_resources_items.zip','BANK':'klbq_resources_items',
                    'BUILD':'klbq_resources_items','PREFAB_FILE':'klbq_resources'}.items():
            self.assertEqual(c[k],v,k)
        self.assertEqual(len(c['items']),20)
        equal = self.lua.eval('function(a,b) return rawequal(a,b) end')
        for i,item in enumerate(self.items,1):
            d=c['items'][i]; key=item['prefab'].removeprefix('klbq_resource_')
            self.assertEqual(d.key,key)
            self.assertEqual(d.prefab,item['prefab'])
            self.assertEqual(d.name,item['name'])
            self.assertEqual(d.inspect,item['inspect_text'])
            self.assertEqual(d.category,CATEGORIES[item['category']])
            self.assertTrue(equal(c.by_key[key],d))
            self.assertTrue(equal(c.by_prefab[item['prefab']],d))

    def test_api_all_twenty_identities(self):
        api=self.module('klbq_resources/api')
        self.assertEqual(api.API_VERSION,1)
        for item in self.items:
            full=item['prefab']; key=full.removeprefix('klbq_resource_')
            for value in (key,full):
                self.assertEqual(api.GetDefinition(value).name,item['name'])
                self.assertEqual(api.GetPrefab(value),full)
            self.assertTrue(api.IsResource(full))
            self.assertTrue(api.IsResource(self.lua.table_from({'prefab':full})))
            self.assertFalse(api.IsResource(key))

    def test_api_invalid_values(self):
        api=self.module('klbq_resources/api')
        for value in (None,False,True,0,42,'','unknown','klbq_resource_unknown',self.lua.table(),self.lua.eval('function() end')):
            self.assertIsNone(api.GetDefinition(value))
            self.assertIsNone(api.GetPrefab(value))
            self.assertFalse(api.IsResource(value))
        self.assertFalse(api.IsResource(self.lua.table_from({'prefab':42})))
        self.assertFalse(api.IsResource(self.lua.eval('setmetatable({}, {__index=function() error("invalid field") end})')))

    def test_register_preserves_and_registers_every_identity(self):
        r=self.module('klbq_resources/register'); e=self.env()
        self.assertTrue(r.Install(e))
        self.assertEqual(e.PrefabFiles[1],'other')
        self.assertEqual(e.PrefabFiles[2],'klbq_resources')
        self.assertEqual(len(e.PrefabFiles),2)
        self.assertEqual(e.Assets[1].file,'other.zip')
        self.assertEqual(len(e.Assets),4)
        self.assertEqual({(e.Assets[i].type,e.Assets[i].file) for i in range(2,5)},
                         {('ANIM','anim/klbq_resources_items.zip'),('ATLAS','images/klbq_resources_items.xml'),('IMAGE','images/klbq_resources_items.tex')})
        self.assertEqual(len(e.icons),20)
        self.assertEqual(e.GLOBAL.STRINGS.NAMES.OTHER,'preserve')
        self.assertEqual(e.GLOBAL.STRINGS.CHARACTERS.GENERIC.DESCRIBE.OTHER,'keep')
        for i,item in enumerate(self.items,1):
            self.assertEqual(e.GLOBAL.STRINGS.NAMES[item['prefab'].upper()],item['name'])
            self.assertEqual(e.GLOBAL.STRINGS.CHARACTERS.GENERIC.DESCRIBE[item['prefab'].upper()],item['inspect_text'])
            self.assertEqual(e.icons[i][1],'images/klbq_resources_items.xml')
            self.assertEqual(e.icons[i][2],item['prefab']+'.tex')
        self.assertEqual(e.GLOBAL.KLBQ_RESOURCES_OWNER.version,'0.1.0')
        self.assertEqual(e.GLOBAL.KLBQ_RESOURCES_OWNER.owner,'test_resources')

    def test_repeated_same_host_and_same_version_other_host_are_noops(self):
        r=self.module('klbq_resources/register'); e=self.env(); r.Install(e)
        self.assertFalse(r.Install(e))
        self.assertEqual(len(e.icons),20); self.assertEqual(len(e.Assets),4)
        other=self.env(); other.GLOBAL=e.GLOBAL
        self.assertFalse(r.Install(other))
        self.assertEqual(len(other.PrefabFiles),1); self.assertEqual(len(other.Assets),1)
        self.assertEqual(len(other.icons),0)

    def test_conflicting_version_leaves_second_host_untouched(self):
        r=self.module('klbq_resources/register'); e=self.env()
        e.GLOBAL.KLBQ_RESOURCES_OWNER=self.lua.table_from({'version':'9.9.9','owner':'other_mod'})
        with self.assertRaisesRegex(Exception,'[Vv]ersion.*9.9.9|9.9.9.*[Vv]ersion'):
            r.Install(e)
        self.assertEqual(len(e.PrefabFiles),1); self.assertEqual(len(e.Assets),1)
        self.assertEqual(len(e.icons),0)
        self.assertIsNone(e.GLOBAL.STRINGS.NAMES.KLBQ_RESOURCE_BABLO_CRYSTAL)
        self.assertEqual(e.GLOBAL.KLBQ_RESOURCES_OWNER.version,'9.9.9')

    def test_invalid_environment_does_not_claim_or_mutate(self):
        r=self.module('klbq_resources/register')
        for field in ('Asset','RegisterInventoryItemAtlas','PrefabFiles','Assets'):
            e=self.env(); e[field]=42
            with self.assertRaises(Exception): r.Install(e)
            self.assertIsNone(e.GLOBAL.KLBQ_RESOURCES_OWNER)
            self.assertIsNone(e.GLOBAL.STRINGS.NAMES.KLBQ_RESOURCE_BABLO_CRYSTAL)
            self.assertEqual(len(e.icons),0)
        e=self.env(); e.GLOBAL.STRINGS.CHARACTERS.GENERIC.DESCRIBE=42
        with self.assertRaises(Exception): r.Install(e)
        self.assertIsNone(e.GLOBAL.KLBQ_RESOURCES_OWNER)
        self.assertEqual(len(e.PrefabFiles),1)

    def test_asset_failure_does_not_claim_or_mutate(self):
        r=self.module('klbq_resources/register'); e=self.env()
        e.Asset=self.lua.eval('function() error("cannot construct asset") end')
        with self.assertRaises(Exception): r.Install(e)
        self.assertIsNone(e.GLOBAL.KLBQ_RESOURCES_OWNER)
        self.assertEqual(len(e.PrefabFiles),1); self.assertEqual(len(e.Assets),1)
        self.assertEqual(len(e.icons),0)

    def test_existing_prefab_entry_is_not_duplicated(self):
        r=self.module('klbq_resources/register'); e=self.env()
        e.PrefabFiles[2]='klbq_resources'; r.Install(e)
        self.assertEqual(len(e.PrefabFiles),2)

    def test_asset_callable_class_table_is_accepted(self):
        r=self.module('klbq_resources/register'); e=self.env()
        e.Asset=self.lua.eval('setmetatable({}, {__call=function(_,kind,path) return {type=kind,file=path} end})')
        self.assertTrue(r.Install(e))
        self.assertEqual(len(e.Assets),4)
        self.assertEqual(e.Assets[2].type,'ANIM')

    def test_owner_registration_works_with_strict_globals(self):
        r=self.module('klbq_resources/register'); e=self.env()
        self.lua.eval('''function(g)
            setmetatable(g, {
                __index=function(_,key) error("read undeclared global "..key) end,
                __newindex=function(_,key) error("write undeclared global "..key) end,
            })
        end''')(e.GLOBAL)
        self.assertTrue(r.Install(e))
        self.assertEqual(self.lua.eval('rawget')(e.GLOBAL,'KLBQ_RESOURCES_OWNER').version,'0.1.0')
        self.assertFalse(r.Install(e))

    def test_registration_creates_missing_lists_and_string_tables(self):
        r=self.module('klbq_resources/register'); e=self.env()
        e.PrefabFiles=None; e.Assets=None; e.GLOBAL.STRINGS=self.lua.table()
        r.Install(e)
        self.assertEqual(len(e.PrefabFiles),1); self.assertEqual(len(e.Assets),3)
        self.assertEqual(e.GLOBAL.STRINGS.NAMES.KLBQ_RESOURCE_BABLO_CRYSTAL,self.items[0]['name'])

    def prefab_setup(self, master):
        self.module('klbq_resources/catalog')
        self.lua.globals().test_master=master
        self.lua.execute('''
            TheWorld={ismastersim=test_master}
            TUNING={STACK_SIZE_SMALLITEM=40}
            function Asset(kind,file) return {type=kind,file=file} end
            function Prefab(name,fn,assets) return {name=name,fn=fn,assets=assets} end
            function CreateEntity()
                local i={components={},tags={},events={}}
                local function event(n) i.events[#i.events+1]=n end
                i.entity={}
                function i.entity:AddTransform() i.Transform={}; event("transform") end
                function i.entity:AddAnimState() i.AnimState={}; event("animstate")
                    function i.AnimState:SetBank(v) self.bank=v end
                    function i.AnimState:SetBuild(v) self.build=v end
                    function i.AnimState:PlayAnimation(v) self.animation=v end
                    function i.AnimState:SetRayTestOnBB(v) self.raytest=v; event("raytest") end
                end
                function i.entity:AddNetwork() i.Network={}; event("network") end
                function i.entity:SetPristine() event("pristine") end
                function i:AddTag(t) self.tags[t]=true end
                function i:AddComponent(c)
                    event("component:"..c); self.components[c]={}
                    if c=="inventoryitem" then
                        self.components[c].ChangeImageName=function(component,v) component.imagename=v end
                    end
                end
                return i
            end
            function MakeInventoryPhysics(i) i.physics=true; i.events[#i.events+1]="physics" end
            function MakeInventoryFloatable(i) i:AddComponent("floater") end
        ''')
        self.assertTrue((ROOT / 'scripts/prefabs/klbq_resources.lua').exists(),'Missing prefab module')
        result=self.lua.execute((ROOT / 'scripts/prefabs/klbq_resources.lua').read_text(encoding='utf-8'))
        self.assertIsInstance(result,tuple)
        self.assertEqual(len(result),20)
        return result

    def test_all_master_prefabs_capture_separate_identity(self):
        prefabs=self.prefab_setup(True)
        for prefab,item in zip(prefabs,self.items):
            self.assertEqual(prefab.name,item['prefab'])
            self.assertEqual(len(prefab.assets),3)
            inst=prefab.fn()
            self.assertEqual(set(inst.components.keys()),{'floater','inspectable','inventoryitem','stackable'})
            self.assertEqual(inst.components.stackable.maxsize,40)
            self.assertEqual(inst.components.inventoryitem.atlasname,'images/klbq_resources_items.xml')
            self.assertEqual(inst.components.inventoryitem.imagename,item['prefab'])
            self.assert_common(inst,item)
            events=list(inst.events.values()); pristine=events.index('pristine')
            self.assertLess(events.index('component:floater'),pristine)
            for c in ('inspectable','inventoryitem','stackable'):
                self.assertGreater(events.index('component:'+c),pristine)

    def test_all_client_prefabs_return_before_authoritative_components(self):
        for prefab,item in zip(self.prefab_setup(False),self.items):
            inst=prefab.fn()
            self.assertEqual(set(inst.components.keys()),{'floater'})
            self.assert_common(inst,item)
            self.assertEqual(list(inst.events.values())[-1],'pristine')

    def assert_common(self,inst,item):
        self.assertIsNotNone(inst.Transform); self.assertIsNotNone(inst.Network)
        self.assertTrue(inst.physics)
        self.assertEqual(inst.AnimState.bank,'klbq_resources_items')
        self.assertEqual(inst.AnimState.build,'klbq_resources_items')
        self.assertEqual(inst.AnimState.animation,item['prefab'])
        self.assertTrue(inst.AnimState.raytest)
        self.assertEqual(set(inst.tags.keys()),{'klbq_resource','klbq_resource_'+CATEGORIES[item['category']]})

    def test_modmain_delegates_to_installer(self):
        self.module('klbq_resources/register')
        self.assertTrue((ROOT / 'modmain.lua').exists(),'Missing runtime modmain')
        e=self.env(); self.lua.globals().env=e
        self.lua.execute((ROOT / 'modmain.lua').read_text(encoding='utf-8'))
        self.assertEqual(e.GLOBAL.KLBQ_RESOURCES_OWNER.version,'0.1.0')


if __name__ == '__main__':
    unittest.main(verbosity=2)
