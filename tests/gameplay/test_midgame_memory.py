"""Exercise the memory sequence against the installed game's recipe and Archive rules."""
import sys
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'mods/klbq_kanami/scripts'
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime


class MidgameMemory(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")) as z:
            src = z.read('scripts/components/builder.lua').decode()
            replica = z.read('scripts/components/builder_replica.lua').decode()
            self.dispenser = z.read('scripts/prefabs/archive_lockbox.lua').decode()
            self.actions = z.read('scripts/actions.lua').decode()
        self.lua.execute('''
            function noop() end
            table.contains=function(t,k) for _,v in ipairs(t) do if v==k then return true end end return false end
            TechTree={AVAILABLE_TECH={'SCIENCE','MAGIC'}, AVAILABLE_TECH_BONUS={},AVAILABLE_TECH_TEMPBONUS={},
                AVAILABLE_TECH_BONUS_CLASSIFIED={},AVAILABLE_TECH_TEMPBONUS_CLASSIFIED={}}
            GetTime=function() return 0 end
            TUNING={HUNGRY_BUILDER_RESET_TIME=10};TheWorld={ismastersim=true};TECH={SCIENCE_TWO={SCIENCE=2}}
            recipes={}
            function Recipe(name, science, magic)
                local recipe={name=name,product=name,level={SCIENCE=science,MAGIC=magic or 0}};recipes[name]=recipe;return recipe
            end
            function GetValidRecipe(name) return recipes[name] end
            function IsRecipeValid(name) return recipes[name]~=nil end
            function Net(v)return {set=function(s,x)s.v=x end,value=function(s)return s.v end,v=v}end
            function Player(name)
                local p={prefab=name,components={},replica={},_klbq_memory_sequence=Net(false),events={}}
                p.IsValid=function()return true end
                p.HasTag=function(s,t)return t==name end
                p.ListenForEvent=function(s,k,f)s.events[k]=f end
                p.PushEvent=noop
                local b=setmetatable({inst=p,recipes={},station_recipes={},science_bonus=0,magic_bonus=0}, {__index=RealBuilder})
                b.AddRecipe=function(s,r)table.insert(s.recipes,r)end
                b.GetTempTechBonuses=noop
                p.components.builder=b
                p.replica.builder=setmetatable({inst=p}, {__index=RealReplica})
                p.replica.builder.classified={isfreebuildmode=Net(false),sciencebonus=Net(0),magicbonus=Net(0),recipes={}}
                p.OnSave=function(_,data) data.builder=b:OnSave() end
                p.OnLoad=function(_,data) if data.builder~=nil then b:OnLoad(data.builder) end end
                prefabinit.klbq_kanami(p)
                return p,b
            end
            prefabinit={}
            STRINGS={NAMES={},RECIPE_DESC={},CHARACTERS={GENERIC={DESCRIBE={}}}}
            Action=function(t)return t end;ActionHandler=function()end
            api={GLOBAL=_G,AddAction=function(a)use=a end,AddStategraphActionHandler=noop,
                AddPrefabPostInit=function(n,fn)prefabinit[n]=fn end,AddPlayerPostInit=noop}
        ''')
        self.lua.execute('RealBuilder={}; local Builder=RealBuilder; '
                         + src[src.index('function Builder:OnSave'):src.index('function Builder:IsBuildBuffered')]
                         + src[src.index('function Builder:KnowsRecipe'):src.index('function Builder:HasIngredients')])
        self.lua.execute('RealReplica={}; local Builder=RealReplica; '
                         + replica[replica.index('function Builder:KnowsRecipe'):replica.index('function Builder:HasIngredients')])
        module = SCRIPTS / 'klbq_kanami/midgame.lua'
        self.assertTrue(module.exists(), 'memory sequence use and portable science are missing')
        self.lua.execute('package.preload["klbq_kanami/bag"]=function() '
                         + (SCRIPTS / 'klbq_kanami/bag.lua').read_text(encoding='utf-8-sig') + ' end')
        self.lua.globals().midgame = self.lua.execute(module.read_text(encoding='utf-8-sig'))
        self.lua.execute('''
            midgame.Install(api)
            p,b=Player('klbq_kanami')
            boards=Recipe('boards',2);postgame=Recipe('postgame',3);magic=Recipe('magic',0,1)
            separate=Recipe('machine',2);separate.station_tag='workshop'
            exclusive=Recipe('limited',2);exclusive.nounlock=true
            learned=Recipe('learned',3);b:AddRecipe('learned')
            item={prefab='klbq_resource_memory_sequence',components={},replica={},count=2}
            item.IsValid=function()return item.count>0 end
            item.components.inventoryitem={GetGrandOwner=function()return item.owner end,
                RemoveFromOwner=function()return {Remove=function()item.count=item.count-1 end} end}
            item.replica.inventoryitem={IsGrandOwner=function(_,who)return item.owner==who end}
            item.owner=p
            function Use(who)return use.fn({doer=who,invobject=item})end
        ''')

    def test_uses_once_retains_native_learned_recipes_and_excludes_separate_stations(self):
        self.assertFalse(self.lua.eval('b:KnowsRecipe(boards)'))
        self.assertTrue(self.lua.eval('Use(p)'))
        self.assertFalse(self.lua.eval('Use(p)'))
        self.assertEqual(self.lua.eval('item.count'), 1)
        for recipe in ('boards', 'learned'):
            self.assertTrue(self.lua.eval(f'b:KnowsRecipe({recipe})'))
        for recipe in ('postgame', 'magic', 'separate', 'exclusive'):
            self.assertFalse(self.lua.eval(f'b:KnowsRecipe({recipe})'))
        self.lua.execute('b:AddRecipe("magic");saved={};p:OnSave(saved);q,qbuilder=Player("klbq_kanami");q:OnLoad(saved)')
        for recipe in ('boards', 'learned', 'magic'):
            self.assertTrue(self.lua.eval(f'qbuilder:KnowsRecipe({recipe})'))
        self.assertEqual(self.lua.eval('qbuilder.science_bonus'), 0)

    def test_remote_recipe_check_reads_replicated_flag_without_rewriting_the_recipe(self):
        self.lua.execute('p.components.builder=nil')
        self.assertFalse(self.lua.eval('p.replica.builder:KnowsRecipe(boards)'))
        self.lua.execute('p._klbq_memory_sequence:set(true)')
        self.assertTrue(self.lua.eval('p.replica.builder:KnowsRecipe(boards)'))
        self.assertFalse(self.lua.eval('p.replica.builder:KnowsRecipe(postgame)'))
        self.assertEqual(self.lua.eval('boards.level.SCIENCE'), 2)

    def test_other_characters_and_nonowned_items_cannot_be_consumed(self):
        self.lua.execute('other={prefab="wilson"};item.owner=other')
        self.assertFalse(self.lua.eval('Use(other)'))
        self.assertFalse(self.lua.eval('Use(p)'))
        self.assertEqual(self.lua.eval('item.count'), 2)

    def install_fountain(self):
        self.lua.execute(self.dispenser[self.dispenser.index('local function OnActivate(inst, doer)'):
                                       self.dispenser.index('local function getstatus(inst)')]
                         + '\nNativeActivate=OnActivate')
        self.lua.execute('ACTIONS={ACTIVATE={}};'+self.actions[self.actions.index('ACTIONS.ACTIVATE.fn = function(act)'):
                                                            self.actions.index('ACTIONS.ACTIVATE.strfn = function(act)')])
        self.lua.execute('''
            TheWorld.components={archivemanager={GetPowerSetting=function() return archivepowered end}}
            archivepowered=false;PI2=2*math.pi;PI=math.pi
            Vector3=function() return {} end
            movesound=noop
            function GetString() return "ANNOUNCE_ARCHIVE_NO_POWER" end
            function SpawnPrefab(name)
                assert(name=="archive_dispencer_sfx")
                starts=(starts or 0)+1
                return {SoundEmitter={PlaySound=noop},DoTaskInTime=noop}
            end
            function Fountain()
                local f={prefab="archive_lockbox_dispencer",components={},Transform={GetWorldPosition=noop}}
                f.AnimState={anim="idle",IsCurrentAnimation=function(self,n) return self.anim==n end,
                    PlayAnimation=function(self,n) self.anim=n end}
                f.components.activatable={inactive=true,OnActivate=NativeActivate,
                    CanActivate=function(self) return self.inactive end,
                    DoActivate=function(self,who) self.inactive=false; return self.OnActivate(f,who) end}
                if prefabinit.archive_lockbox_dispencer then prefabinit.archive_lockbox_dispencer(f) end
                return f
            end
            function ReadFountain(f,who)
                return ACTIONS.ACTIVATE.fn({target=f,doer=who})
            end
            function Observe(who)
                who.components.talker={Say=function(self,msg) self.message=msg end}
            end
            Observe(p)
        ''')

    def test_learned_kanami_activates_unpowered_fountain_without_powering_archive(self):
        self.install_fountain()
        self.lua.execute('''
            fountain=Fountain()
            ReadFountain(fountain,p)
            assert(fountain.AnimState.anim=="idle" and fountain.components.activatable.inactive)
            assert(p.components.talker.message=="ANNOUNCE_ARCHIVE_NO_POWER")
            assert(Use(p))
            ReadFountain(fountain,p)
            assert(fountain.AnimState.anim=="use_pre" and not fountain.components.activatable.inactive)
            assert(starts==1 and not fountain.vaultpowered and not archivepowered)
            ReadFountain(fountain,p)
            assert(starts==1)
        ''')

    def test_old_saved_entitlement_applies_only_to_living_kanami(self):
        self.install_fountain()
        self.lua.execute('''
            q=Player("klbq_kanami")
            q:OnLoad({klbq_memory_sequence=true})
            other={prefab="wilson",components={},_klbq_memory_sequence=Net(true)}
            Observe(q);Observe(other)
            local normal=q.HasTag
            q.HasTag=function(self,tag) return tag=="playerghost" or normal(self,tag) end
            local fountain=Fountain()
            ReadFountain(fountain,q)
            assert(fountain.AnimState.anim=="idle")
            q.HasTag=normal
            ReadFountain(fountain,q)
            assert(fountain.AnimState.anim=="use_pre")
            local unpowered=Fountain()
            ReadFountain(unpowered,other)
            assert(unpowered.AnimState.anim=="idle")
            archivepowered=true
            ReadFountain(unpowered,other)
            assert(unpowered.AnimState.anim=="use_pre" and archivepowered)
        ''')
