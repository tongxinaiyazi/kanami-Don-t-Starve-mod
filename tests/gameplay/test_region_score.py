"""The score remembers visited regions while each tile and sapling keeps its own imprint."""
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/python-deps"))
from lupa.lua51 import LuaRuntime


class RegionScore(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute('''
            package.loaded["prefabs/tree_rock_data"] = {
                WEIGHTED_VINE_LOOT={DEFAULT={rocks=1},FOREST_AREA={flint=1},DESERT_AREA={goldnugget=1}},
                STATIC_LAYOUTS_TO_LOOT_KEY={},
                ROOMS_TO_LOOT_KEY={Forest="FOREST_AREA",Desert="DESERT_AREA"},
                TASKS_TO_LOOT_KEY={},
                CheckModifyLootArea=function(key) return key end,
            }
            function ConvertTopologyIdToData(id) return {room_id=id} end
            map={
                topology="Forest",tile=9,
                GetTopologyIDAtPoint=function(self) return self.topology end,
                GetTile=function(self) return self.tile end,
            }
            WORLD_TILES={KLBQ_IMPRINT=9}
        ''')
        source = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/regions.lua'
        self.assertTrue(source.is_file(), 'no region score implementation')
        self.lua.globals().regions = self.lua.execute(source.read_text(encoding='utf-8'))

    def test_only_the_owners_score_can_record_and_select_visited_regions(self):
        self.lua.execute('''
            package.loaded["klbq_kanami/regions"] = regions
            TheWorld={ismastersim=true,Map=map}
            map.GetTileAtPoint=function() return 9 end
            TileGroupManager={IsLandTile=function() return true end}
            t=0; GetTime=function() return t end
            EntityScript={is_instance=function(item) return item==score end}
            function Net()
                return {data="",value=function(s) return s.data end,set=function(s,v) s.data=v end}
            end
            local function Player()
                return {prefab="klbq_kanami",components={}, HasTag=function() return false end,
                    Transform={GetWorldPosition=function() return 0,0,0 end},
                    replica={inventory={GetActiveItem=function() return nil end}}}
            end
            owner, stranger=Player(),Player()
            score={prefab="klbq_region_score",IsValid=function() return true end,
                _klbq_region=Net(),_klbq_regions=Net(),replica={inventoryitem={IsGrandOwner=function(_,p) return p==owner end}}}
            function Action() return {} end
            function ActionHandler() end
            local function noop() end
            env={GLOBAL=_G,AddPrefabPostInit=noop,AddClientModRPCHandler=noop,
                AddAction=noop,AddComponentAction=noop,AddStategraphActionHandler=noop,
                AddModRPCHandler=function(_,_,fn) edit=fn end}
        ''')
        actions = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/region_actions.lua'
        self.lua.execute(actions.read_text(encoding='utf-8')).Install(self.lua.globals().env)
        self.lua.execute('''
            edit(stranger,score,"record","DESERT_AREA")
            assert(score._klbq_regions:value()=="")
            edit(owner,score,"record","DESERT_AREA")
            assert(score._klbq_region:value()=="FOREST_AREA")
            t=1; edit(owner,score,"select","DESERT_AREA")
            assert(score._klbq_region:value()=="FOREST_AREA")
            t=2; map.topology="Desert"; edit(owner,score,"record","")
            assert(score._klbq_region:value()=="DESERT_AREA")
            t=3; edit(owner,score,"select","FOREST_AREA")
            assert(score._klbq_region:value()=="FOREST_AREA")
            assert(#regions.List(score._klbq_regions:value())==2)
        ''')

    def test_score_retains_both_visited_regions_and_rejects_unknown_selection(self):
        self.lua.execute('''
            records, selected = regions.Record("", nil, regions.AtPoint(map, 0, 0, 0))
            map.topology="Desert"
            records, selected = regions.Record(records, selected, regions.AtPoint(map, 0, 0, 0))
            assert(selected=="DESERT_AREA")
            assert(regions.Select(records, "UNKNOWN")==nil)
            assert(regions.Select(records, "DEFAULT")==nil)
            assert(regions.Select(records, "FOREST_AREA")=="FOREST_AREA")
            records, selected = regions.Record(records, "FOREST_AREA", "DESERT_AREA")
            assert(selected=="FOREST_AREA")
            keys=regions.List(records)
            assert(#keys==2)
        ''')

    def test_tile_imprints_are_independent_saved_and_cleared_on_replacement(self):
        self.lua.execute('''
            world={}
            regions.SetTile(world,map,0,0,"FOREST_AREA")
            regions.SetTile(world,map,1,0,"DESERT_AREA")
            assert(regions.GetTile(world,map,0,0)=="FOREST_AREA")
            assert(regions.GetTile(world,map,1,0)=="DESERT_AREA")
            copy={_klbq_region_tiles=regions.SaveTiles(world)}
            regions.OnTerraform(copy,{x=0,y=0,original_tile=9,tile=2})
            assert(regions.GetTile(copy,map,0,0)==nil)
            assert(regions.GetTile(copy,map,1,0)=="DESERT_AREA")
            map.tile=2
            assert(regions.GetTile(copy,map,1,0)==nil)
            assert(not regions.SetTile(copy,map,1,0,"FOREST_AREA"))
        ''')

    def test_steam_vents_keep_the_rift_status_at_recording_and_revisit_unlocks_both(self):
        game = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")
        with zipfile.ZipFile(game) as archive:
            source = archive.read('scripts/prefabs/tree_rock_data.lua').decode('utf-8-sig')
        self.lua.globals().native = self.lua.execute(source)
        self.lua.execute('package.loaded["prefabs/tree_rock_data"] = native')
        module = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/regions.lua'
        self.lua.globals().regions = self.lua.execute(module.read_text(encoding='utf-8'))
        self.lua.execute('''
            function ConvertTopologyIdToData(id) return {task_id=id} end
            map.topology="CentipedeCaveTask"
            local active=false
            local source={ismastersim=true,components={riftspawner={
                IsShadowPortalActive=function()return active end}}}
            TheWorld=source
            local ordinary=regions.AtPoint(map,0,0,0)
            assert(ordinary=="VENT_AREA",ordinary)
            local records,selected=regions.Record("",nil,ordinary)
            assert(regions.Select(records,"VENT_AREA_SHADOW_RIFT")==nil)
            active=true
            local dark=regions.AtPoint(map,0,0,0)
            assert(dark=="VENT_AREA_SHADOW_RIFT",dark)
            records,selected=regions.Record(records,selected,dark)
            assert(#regions.List(records)==2 and selected==dark)
            assert(regions.Select(records,ordinary)==ordinary)

            local postinit={}
            regions.InstallTrees({GLOBAL=_G,AddPrefabPostInit=function(name,fn)postinit[name]=fn end})
            local rolls=0
            weighted_random_choices=function(weights,n)
                rolls=rolls+1
                assert(n==5)
                return {gold=weights.goldnugget,red=weights.redgem}
            end
            local function GrowOnOtherShard(recorded, destinationActive)
                TheWorld={ismastersim=true,_klbq_growing_region=recorded,
                    GroundCreep={OnCreep=function()return false end},
                    HasTag=function()return false end,
                    components={riftspawner={IsShadowPortalActive=function()return destinationActive end}}}
                local tree={growfromseed=function()end,OnLoad=function(self,data)self.vine_loot=data.vine_loot end,
                    Transform={GetWorldPosition=function()return 0,0,0 end}}
                postinit.tree_rock1_short(tree)
                tree:growfromseed()
                return tree
            end
            local darkTree=GrowOnOtherShard(dark,false)
            local bonus=native.WEIGHTED_VINE_LOOT.VENT_AREA_SHADOW_RIFT
            assert(darkTree.vine_loot.gold==bonus.goldnugget and darkTree.vine_loot.red==bonus.redgem)
            local ordinaryTree=GrowOnOtherShard(ordinary,true)
            local base=native.WEIGHTED_VINE_LOOT.VENT_AREA
            assert(ordinaryTree.vine_loot.gold==base.goldnugget and ordinaryTree.vine_loot.red==base.redgem)
            TheWorld._klbq_growing_region=dark
            ordinaryTree:growfromseed()
            assert(ordinaryTree.vine_loot.gold==base.goldnugget and rolls==2)
        ''')
