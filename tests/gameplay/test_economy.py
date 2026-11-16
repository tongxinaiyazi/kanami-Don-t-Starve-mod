"""Material economy against installed DST action/work/loot implementations."""
import unittest
import zipfile
import re
import test_terminal_integration
from test_review_regressions import vanilla, ROOT, GAME


class Economy(unittest.TestCase):
    def setUp(self):
        test_terminal_integration.TerminalIntegration.setUp(self)
        self.lua.execute("""
          ACTIONS={MINE={id='MINE'},HAMMER={id='HAMMER'}};Workable={}
          EQUIPSLOTS={HANDS='hands'};GetTime=function()return 0 end
          ShouldItemMimicBeRevealedFor=function()return false end
          TUNING={ROCKS_MINE=3};spawned={}
          SpawnPrefab=function()return {Transform={SetPosition=function()end}} end
        """)
        methods=('GetWorkAction','CanBeWorked','ShouldRecoil','WorkedBy_Internal','WorkedBy','Destroy','SetOnWorkCallback')
        for name in methods:
            self.lua.execute(vanilla('components/workable.lua','function Workable:'+name+'('))
        self.lua.execute(vanilla('actions.lua','local function DoToolWork(')+"\n"+
                         vanilla('actions.lua','ACTIONS.MINE.fn = function(act)'))
        self.lua.globals().RockWork=self.lua.execute(vanilla('prefabs/rocks.lua','local function OnWork(')+'\nreturn OnWork')
        self.lua.execute("""
          function worker(player,dead)
            return {components={health={IsDead=function()return dead end}},
              HasTag=function(s,t)return t=='player' and player or t=='playerghost' and dead end,
              IsValid=function()return true end,PushEvent=function()end}
          end
          function rock()
            local r=boss();r.GetPosition=function()return {x=1,y=0,z=2}end
            r.Remove=function(s)s.removed=true end;r.AnimState={PlayAnimation=function()end}
            r.components.workable=setmetatable({inst=r,action=ACTIONS.MINE,workleft=3,workable=true,onwork=RockWork},{__index=Workable})
            r.components.lootdropper.SpawnLootPrefab=function(s,p)spawned[#spawned+1]=p end
            r.components.lootdropper.DropLoot=function(s)s.native=(s.native or 0)+1 end
            return r
          end
          require('klbq_kanami/resources').Install(env)
        """)

    def test_only_native_living_player_mining_completion_rewards(self):
        self.lua.execute("""
          assert(env.hooks.rock1,'missing mining acquisition')
          r=rock();env.hooks.rock1(r);w=worker(true,false)
          for i=1,2 do assert(ACTIONS.MINE.fn({target=r,doer=w})) end
          assert(#spawned==0,'partial work rewarded')
          assert(ACTIONS.MINE.fn({target=r,doer=w}))
          assert(#spawned==1 and spawned[1]=='klbq_resource_base_string')
          assert(r.removed and r.components.lootdropper.native==1)
          r.components.workable.onwork(r,w,0,1)
          assert(#spawned==1,'repeated completion rewarded')
        """)

    def test_destroy_npc_ghost_and_hammer_cannot_reward(self):
        self.lua.execute("""
          assert(env.hooks.rock2,'missing mining acquisition')
          r=rock();env.hooks.rock2(r);r.components.workable:Destroy(worker(true,false))
          for _,w in ipairs({worker(false,false),worker(true,true)})do
            r=rock();env.hooks.rock2(r)
            for i=1,3 do ACTIONS.MINE.fn({target=r,doer=w})end
          end
          r=rock();env.hooks.rock2(r);r.components.workable.action=ACTIONS.HAMMER
          ACTIONS.MINE.fn({target=r,doer=worker(true,false)})
          assert(r.components.workable.workleft==3)
          assert(#spawned==0)
        """)

    def test_boss_native_loot_additions_are_exact_and_idempotent(self):
        for prefab,count in [('minotaur',6),('daywalker',4),('daywalker2',4)]:
            self.lua.execute("""
              local prefab,count=...;assert(env.hooks[prefab],'missing boss acquisition')
              b=boss();env.hooks[prefab](b);env.hooks[prefab](b)
              generated=b.components.lootdropper:GenerateLoot()
            """,prefab,count)
            loot=list(self.lua.globals().generated.values())
            self.assertEqual(loot.count('klbq_resource_topology_ring'),count)
            self.assertIn('dreadstone',loot)

    def test_client_hooks_do_not_change_world_loot_or_callbacks(self):
        self.lua.execute("""
          TheWorld.ismastersim=false
          r=rock();local old=r.components.workable.onwork
          env.hooks.rock1(r);assert(r.components.workable.onwork==old)
          for _,prefab in ipairs({'minotaur','daywalker','daywalker2'})do
            b=boss();env.hooks[prefab](b);assert(b.components.lootdropper.chanceloot==nil)
          end
        """)

    def test_native_boss_loot_setup_keeps_added_rings_and_original_rewards(self):
        for prefab,signature in [('daywalker','local function LootSetupFn('),('daywalker2','local function lootsetfn(')]:
            name='LootSetupFn' if prefab=='daywalker' else 'lootsetfn'
            setup=self.lua.execute(vanilla('prefabs/'+prefab+'.lua',signature)+'\nreturn '+name)
            self.lua.globals().native_setup=setup
            for method in ('SetLoot','SetChanceLootTable','ClearRandomLoot','AddRandomLoot','PickRandomLoot','GetRandomLootTable','GetChance'):
                self.lua.execute(vanilla('components/lootdropper.lua','function LootDropper:'+method+'('))
            self.lua.execute("""
              local prefab=...
              WeightedRandomLootTotal=function()return 1 end
              b=boss();env.hooks[prefab](b)
              b.components.knownlocations={GetLocation=function()return true end}
              TheWorld.components={};AllPlayers={}
              LootTables[prefab]={{'native_reward',1}}
              b.components.lootdropper:SetChanceLootTable(prefab)
              b.components.lootdropper.lootsetupfn=native_setup
              generated=b.components.lootdropper:GenerateLoot()
            """,prefab)
            loot=list(self.lua.globals().generated.values())
            self.assertEqual(loot.count('klbq_resource_topology_ring'),4)
            self.assertIn('native_reward',loot)

    def test_mining_preserves_callbacks_returns_and_saved_award_flag(self):
        self.lua.execute("""
          r=rock();savecalls=0;loadcalls=0
          r.OnSave=function(s,data)data.original=42;savecalls=savecalls+1;return {123},'tail' end
          r.OnLoad=function(s,data)loadcalls=loadcalls+1;s.native_loaded=data.original;return 'loaded' end
          env.hooks.rock1(r);env.hooks.rock1(r)
          local w=worker(true,false)
          for i=1,3 do ACTIONS.MINE.fn({target=r,doer=w})end
          saved={};local refs,tail=r:OnSave(saved)
          assert(refs[1]==123 and tail=='tail' and savecalls==1)
          fresh=rock();env.hooks.rock1(fresh);fresh:OnLoad(saved)
          assert(fresh._klbq_base_string_mined and saved.original==42)
          for i=1,3 do ACTIONS.MINE.fn({target=fresh,doer=w})end
          assert(#spawned==1,'saved award repeated')
          failmine=ACTIONS.MINE.fn
        """)

    def test_daywalker_rewards_wait_for_native_defeat_drop_and_looted_guard(self):
        for prefab in ('daywalker','daywalker2'):
            with zipfile.ZipFile(GAME) as archive:
                source=archive.read('scripts/stategraphs/SG'+prefab+'.lua').decode('utf-8-sig')
            # Execute the installed callback containing the native DropLoot call;
            # all surrounding phase and state names remain source-owned.
            hit=source.index('inst.components.lootdropper:DropLoot')
            start=source.rfind('FrameEvent(',0,hit)
            end=source.index('end),',hit)+len('end)')
            callback=source[start:end]
            self.lua.execute("""
              FrameEvent=function(frame,fn)return fn end
              b=boss();env.hooks[...](b);b.defeated=false;b.looted=false
              b.sg={AddStateTag=function()end};DEGREES=math.pi/180
              b.Transform={GetWorldPosition=function()return 0,0,0 end}
              SpawnPrefab=function()return {Transform={SetPosition=function()end,SetRotation=function()end}}end
              b.AnimState={HideSymbol=function()end,Hide=function()end}
              b.components.timer={ResumeTimer=function()end}
              b.GetPosition=function()return {}end
              b.components.lootdropper.DropLoot=function(s)s.drops=(s.drops or 0)+1;s.generated=s:GenerateLoot()end
            """,prefab)
            fn=self.lua.execute('return '+callback)
            b=self.lua.globals().b
            fn(b)
            self.assertIsNone(b.components.lootdropper.drops)
            b.defeated=True
            fn(b);fn(b)
            self.assertEqual(b.components.lootdropper.drops,1)
            self.assertEqual(list(b.components.lootdropper.generated.values()).count('klbq_resource_topology_ring'),4)
            saved=self.lua.table()
            onsave=self.lua.execute(vanilla('prefabs/'+prefab+'.lua','local function OnSave(')+'\nreturn OnSave')
            onsave(b,saved)
            self.assertTrue(saved.looted)


class Recipes(unittest.TestCase):
    def test_recipe_costs_restriction_atlases_yield_and_private_station(self):
        from lupa.lua51 import LuaRuntime
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute("""
          TECH={SCIENCE_ONE=1,SCIENCE_TWO=2,KLBQ_STRING_ONE=3};GLOBAL=_G;recipes={}
          Ingredient=function(name,n,atlas)return {name=name,n=n,atlas=atlas}end
          env={GLOBAL=_G,AddRecipe2=function(name,ingredients,tech,config,filters)
            assert(not recipes[name]);recipes[name]={ingredients=ingredients,tech=tech,config=config,filters=filters}
          end}
        """)
        path=ROOT/'mods/klbq_kanami/scripts/klbq_kanami/recipes.lua'
        self.assertTrue(path.exists(),'missing economy recipe module')
        module=lua.execute(path.read_text(encoding='utf-8'))
        module.Install(lua.globals().env)
        expected={
          'klbq_resource_base_string':(1,8,{'rocks':4,'nitre':2}),
          'klbq_resource_tracing_plate':(2,1,{'goldnugget':2,'papyrus':1,'transistor':1}),
          'klbq_resource_topology_ring':(2,2,{'thulecite':2,'nightmarefuel':2}),
          'klbq_finale':(2,1,{'redgem':1,'goldnugget':4,'boards':2,'gears':1,'klbq_resource_base_string':4}),
          'klbq_singularity':(1,1,{'silk':6,'goldnugget':2,'rope':2,'klbq_resource_base_string':4}),
          'klbq_crossbow':(2,1,{'boards':2,'silk':4,'goldnugget':2,'purplegem':1,'klbq_resource_base_string':4}),
          'klbq_requiem':(1,1,{'flint':8,'boards':2,'goldnugget':2,'rope':2,'klbq_resource_base_string':6}),
          'klbq_ammo_fate':(2,20,{'klbq_resource_topology_ring':2,'nitre':2}),
          'klbq_crystal':(2,1,{'klbq_resource_terminal_kanami':1,'klbq_resource_topology_ring':2,'moonrocknugget':12,'gears':2}),
          'klbq_imprint_tool':(2,1,{'klbq_resource_tracing_plate':1,'klbq_resource_base_string':4,'goldnugget':2,'rope':2}),
          'klbq_ammo_heart':(1,20,{'rocks':4,'flint':2,'nitre':1}),
          'klbq_blade':(1,1,{'flint':6,'twigs':2,'rope':2}),
          'klbq_ammo_doom':(3,1,{'purebrilliance':2,'horrorfuel':2,'nightmarefuel':6,'opalpreciousgem':1})}
        self.assertEqual(set(lua.globals().recipes.keys()),set(expected))
        for name,(tech,num,cost) in expected.items():
            r=lua.globals().recipes[name]
            self.assertEqual(r.tech,tech,name);self.assertEqual(r.config.numtogive,num,name)
            self.assertEqual(r.config.builder_tag,'klbq_kanami',name)
            atlas='images/klbq_resources_items.xml' if name.startswith('klbq_resource_') else 'images/klbq_kanami_items.xml'
            self.assertEqual(r.config.atlas,atlas,name)
            self.assertEqual({v.name:v.n for v in r.ingredients.values()},cost,name)
            for v in r.ingredients.values():
                if v.name.startswith('klbq_resource_'):self.assertEqual(v.atlas,'images/klbq_resources_items.xml')
        doom=lua.globals().recipes.klbq_ammo_doom
        self.assertTrue(doom.config.nounlock);self.assertEqual(doom.config.station_tag,'klbq_crystal')
        self.assertIn('TOOLS',list(lua.globals().recipes.klbq_imprint_tool.filters.values()))
