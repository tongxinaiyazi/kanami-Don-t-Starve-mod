"""Crystal technology through installed native prototyper/builder/replica code."""
import unittest
import zipfile
from test_component import LuaRuntime
from test_review_regressions import GAME, ROOT, vanilla


SCRIPTS=ROOT/'mods/klbq_kanami/scripts'


class Technology(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME) as archive:
            self.techsource=archive.read('scripts/techtree.lua').decode('utf-8-sig')
            self.protosource=archive.read('scripts/components/prototyper.lua').decode('utf-8-sig')
            self.classifiedsource=archive.read('scripts/prefabs/player_classified.lua').decode('utf-8-sig')
        self.lua.execute('package.preload.techtree=function() '+self.techsource+' end')
        self.lua.execute('''
          TechTree=require('techtree')
          Class=function(ctor)local c={};c.__index=c;return setmetatable(c,{__call=function(_,...)local s=setmetatable({},c);ctor(s,...);return s end})end
          table.contains=function(t,v)for _,a in pairs(t)do if a==v then return true end end;return false end
          TECH={NONE=TechTree.Create(),SCIENCE_ONE=TechTree.Create({SCIENCE=1}),SCIENCE_TWO=TechTree.Create({SCIENCE=2})}
          TUNING={RESEARCH_MACHINE_DIST=4,PROTOTYPER_TREES={SCIENCEMACHINE=TechTree.Create({SCIENCE=1}),ALCHEMYMACHINE=TechTree.Create({SCIENCE=2})}}
          AllRecipes={spear={name='spear',product='spear',level=TechTree.Create({SCIENCE=1})}}
          nativelevel=AllRecipes.spear.level;nativealchemy=TUNING.PROTOTYPER_TREES.ALCHEMYMACHINE
          GetValidRecipe=function(name)return AllRecipes[name]end;PREFAB_SKINS_SHOULD_NOT_SELECT={}
          protodefs={};env={GLOBAL=_G,AddPrototyperDef=function(name,def)protodefs[name]=def end}
          STRINGS={UI={CRAFTING_STATION_FILTERS={}}}
          TheWorld={ismastersim=true};TheNet={IsDedicated=function()return true end}
          function net(v)return {v=v,set=function(s,n)s.v=n end,value=function(s)return s.v end}end
          net_tinybyte=function()return net(0)end
          function entity()
            local s={components={},tags={},events={},x=0,z=0,removed=false}
            s.HasTag=function(s,t)return s.tags[t]end
            s.HasTags=function(s,ts)for _,t in ipairs(ts)do if not s:HasTag(t)then return false end end;return true end
            s.HasOneOfTags=function(s,ts)for _,t in ipairs(ts)do if s:HasTag(t)then return true end end;return false end
            s.AddTag=function(s,t)s.tags[t]=true end;s.RemoveTag=function(s,t)s.tags[t]=nil end
            s.ListenForEvent=function(s,n,f,src)if not src then s.events[n]=f end end;s.RemoveEventCallback=function()end
            s.PushEvent=function(s,n,d)if s.events[n]then s.events[n](s,d)end end
            s.IsValid=function(s)return not s.removed end;s.IsInLimbo=function(s)return s:HasTag('INLIMBO')end
            s.GetPosition=function(s)return {x=s.x,y=0,z=s.z}end
            s.IsNear=function(s,other,range)return (s.x-other.x)^2+(s.z-other.z)^2<range^2 end
            s.entity={IsValid=function()return true end,AddTransform=function()end,AddAnimState=function()end,
              AddNetwork=function()end,SetPristine=function()s.pristine=true end}
            s.AnimState={SetBank=function(_,v)s.bank=v end,SetBuild=function(_,v)s.build=v end,PlayAnimation=function(_,v)s.anim=v end}
            s.AddComponent=function(s,name)
              if name=='prototyper'then s.components[name]=Prototyper(s)
              elseif name=='inventoryitem'then s.components[name]={IsHeld=function()return s.held==true end}
              else s.components[name]={}end
            end
            return s
          end
          Asset=function()return {}end;Prefab=function(name,fn)return fn end
          CreateEntity=entity;MakeInventoryPhysics=function()end;MakeInventoryFloatable=function()end;MakeHauntableLaunch=function()end
          Builder={};Replica={}
        ''')
        for name in ('technology',):
            path=SCRIPTS/'klbq_kanami'/f'{name}.lua'
            self.assertTrue(path.exists(),f'missing technology implementation: {name}')
            self.lua.execute('package.preload[...] = function() '+path.read_text(encoding='utf-8-sig')+' end','klbq_kanami/'+name)
        self.lua.execute("technology=require('klbq_kanami/technology');technology.Install(env)")
        self.lua.globals().Prototyper=self.lua.execute(self.protosource)
        crystal=SCRIPTS/'prefabs/klbq_crystal.lua'
        self.assertTrue(crystal.exists(),'missing crystal station prefab')
        self.lua.globals().crystalfn=self.lua.execute(crystal.read_text(encoding='utf-8-sig'))
        self.lua.execute(vanilla('components/builder.lua','local function CopyTechTrees(')+'\n_G.CopyTechTrees=CopyTechTrees')
        self.lua.execute('PROTOTYPER_TAGS={"prototyper"}')
        for name in ('EvaluateTechTrees','KnowsRecipe','UnlockRecipe','AddRecipe','CanLearn'):
            self.lua.execute(vanilla('components/builder.lua','function Builder:'+name+'('))
        for name in ('SetTechTrees','GetTechTrees','KnowsRecipe','CanLearn'):
            self.lua.execute(vanilla('components/builder_replica.lua','function Builder:'+name+'(').replace('function Builder:','function Replica:',1))
        self.lua.execute(vanilla('prefabs/player_classified.lua','local function OnTechTreesDirty(')+'\n_G.OnTechTreesDirty=OnTechTreesDirty')
        self.lua.execute('''
          player=entity();player:AddTag('klbq_kanami')
          classified={GUID=1,techtrees=TechTree.Create(),techtrees_no_temp=TechTree.Create(),recipes={},isfreebuildmode=net(false)}
          serverreplica=setmetatable({inst=player,classified=classified},{__index=Replica})
          player.replica={builder=serverreplica}
          builder=setmetatable({inst=player,recipes={},station_recipes={},exclude_tags={'INLIMBO'},
            accessible_tech_trees=TechTree.Create(),accessible_tech_trees_no_temp=TechTree.Create(),old_accessible_tech_trees={}}, {__index=Builder})
          player.components.builder=builder
          clientplayer=entity();clientplayer:AddTag('klbq_kanami')
          clientreplica=setmetatable({inst=clientplayer,classified=classified},{__index=Replica})
          station=crystalfn();stations={station}
          TheSim={FindEntities=function(_,x,y,z,range,tags,exclude)
            local result={}
            for _,e in ipairs(stations)do
              if (x-e.x)^2+(z-e.z)^2<range^2 and e:HasTags(tags) and not e:HasOneOfTags(exclude)then result[#result+1]=e end
            end
            return result
          end}
          AllRecipes.doom={name='doom',product='klbq_ammo_doom',level=TECH.KLBQ_STRING_ONE,nounlock=true,builder_tag='klbq_kanami'}
        ''')
        # Execute the installed game's actual network-variable registration loop.
        start=self.classifiedsource.index('for i, v in ipairs(TechTree.AVAILABLE_TECH) do',self.classifiedsource.index('local function OnTechTreesDirty(')+1200)
        end=self.classifiedsource.index('    inst.isfreebuildmode',start)
        self.lua.execute('(function(inst) '+self.classifiedsource[start:end]+' end)(classified)')

    def evaluate(self):
        self.lua.execute('builder:EvaluateTechTrees();OnTechTreesDirty(classified)')

    def test_custom_tree_defaults_do_not_change_other_recipes_or_native_levels(self):
        self.assertEqual(self.lua.eval('TECH.KLBQ_STRING_ONE.KLBQ_STRING'),1)
        self.assertEqual(self.lua.eval('TUNING.PROTOTYPER_TREES.KLBQ_STRING.KLBQ_STRING'),1)
        self.assertEqual(self.lua.eval('TECH.SCIENCE_TWO.SCIENCE'),2)
        self.assertEqual(self.lua.eval('TECH.SCIENCE_TWO.KLBQ_STRING'),0)
        self.assertEqual(self.lua.eval('AllRecipes.spear.level.SCIENCE'),1)
        self.assertEqual(self.lua.eval('AllRecipes.spear.level.KLBQ_STRING'),0)
        self.assertTrue(self.lua.eval('nativelevel==AllRecipes.spear.level and nativealchemy==TUNING.PROTOTYPER_TREES.ALCHEMYMACHINE'))
        self.lua.execute('before=#TechTree.AVAILABLE_TECH;technology.Install(env)')
        self.assertEqual(self.lua.eval('#TechTree.AVAILABLE_TECH'),self.lua.eval('before'))

    def test_independent_client_registers_same_network_tree_order(self):
        client=LuaRuntime(unpack_returned_tuples=True)
        client.execute('package.preload.techtree=function() '+self.techsource+' end')
        client.execute('''
          TheWorld={ismastersim=false};TECH={NONE=require('techtree').Create()}
          TUNING={PROTOTYPER_TREES={}};AllRecipes={}
          STRINGS={UI={CRAFTING_STATION_FILTERS={}}}
          env={GLOBAL=_G,AddPrototyperDef=function()end}
        ''')
        client.globals().technology=client.execute((SCRIPTS/'klbq_kanami/technology.lua').read_text(encoding='utf-8-sig'))
        client.execute('technology.Install(env);technology.Install(env)')
        self.assertEqual(client.eval("table.concat(require('techtree').AVAILABLE_TECH,',')"),self.lua.eval("table.concat(TechTree.AVAILABLE_TECH,',')"))
        self.assertEqual(client.eval('TECH.KLBQ_STRING_ONE.KLBQ_STRING'),1)
        self.assertEqual(client.eval('TECH.NONE.KLBQ_STRING'),0)

    def test_native_builder_and_classified_replica_receive_only_nearby_private_tech(self):
        self.lua.execute('station.x=3.9')
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.KLBQ_STRING'),1)
        self.assertEqual(self.lua.eval('clientreplica:GetTechTrees().KLBQ_STRING'),1)
        self.assertEqual(self.lua.eval('clientreplica:GetTechTrees().SCIENCE'),0)
        self.assertTrue(self.lua.eval('builder.current_prototyper==station'))
        self.lua.execute('station.x=4.1')
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.KLBQ_STRING'),0)
        self.assertEqual(self.lua.eval('clientreplica:GetTechTrees().KLBQ_STRING'),0)

    def test_native_station_cannot_unlock_private_tree_and_crystal_does_not_supply_science(self):
        self.lua.execute('other=entity();other:AddComponent("prototyper");other.components.prototyper.trees=TUNING.PROTOTYPER_TREES.ALCHEMYMACHINE;stations={other}')
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.SCIENCE'),2)
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.KLBQ_STRING'),0)
        self.lua.execute('stations={station}')
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.SCIENCE'),0)

    def test_native_unlockrecipe_never_learns_doom_permanently(self):
        self.evaluate()
        self.lua.execute("builder:UnlockRecipe('doom');stations={}")
        self.evaluate()
        self.assertEqual(self.lua.eval('#builder.recipes'),0)
        self.assertFalse(self.lua.eval("builder:KnowsRecipe('doom')"))
        self.assertFalse(self.lua.eval("clientreplica:KnowsRecipe('doom')"))

    def test_only_kanami_can_use_or_learn_crystal_recipe(self):
        self.lua.execute("player:RemoveTag('klbq_kanami');clientplayer:RemoveTag('klbq_kanami')")
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.KLBQ_STRING'),0)
        self.assertFalse(self.lua.eval("builder:CanLearn('doom')"))
        self.assertFalse(self.lua.eval("clientreplica:CanLearn('doom')"))

    def test_pocketing_crystal_revokes_tech_and_dropping_restores_it(self):
        self.evaluate()
        self.lua.execute("station.held=true;station:PushEvent('onputininventory',player)")
        self.evaluate()
        self.assertEqual(self.lua.eval('builder.accessible_tech_trees.KLBQ_STRING'),0)
        self.assertFalse(bool(self.lua.eval('station:HasTag("prototyper")')))
        self.assertFalse(self.lua.eval('station.components.prototyper:CanUsePrototyper(player)'))
        self.lua.execute("station.held=false;station:PushEvent('ondropped')")
        self.evaluate()
        self.assertEqual(self.lua.eval('clientreplica:GetTechTrees().KLBQ_STRING'),1)

    def test_native_activate_does_not_consume_or_remove_crystal(self):
        self.evaluate()
        self.lua.execute("station.Remove=function()error('crystal must remain')end;station.components.prototyper:Activate(player,AllRecipes.doom)")
        self.assertTrue(self.lua.eval('station:IsValid()'))
        self.assertEqual(self.lua.eval('station.components.prototyper.trees.KLBQ_STRING'),1)

    def test_client_prefab_has_shared_pristine_tags_without_server_components(self):
        self.lua.execute('TheWorld.ismastersim=false;clientcrystal=crystalfn()')
        self.assertTrue(self.lua.eval('clientcrystal.pristine'))
        self.assertTrue(self.lua.eval('clientcrystal:HasTag("prototyper")'))
        self.assertEqual(self.lua.eval('clientcrystal.bank'),'klbq_crystal')
        self.assertEqual(self.lua.eval('clientcrystal.build'),'klbq_crystal')
        self.assertIsNone(self.lua.eval('clientcrystal.components.prototyper'))


if __name__=='__main__':unittest.main(verbosity=2)
