"""Domain gardening runs installed DST grow/tend/pick/crop code in Lua 5.1."""
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")
SCRIPTS = ROOT / 'mods/klbq_kanami/scripts'


class Garden(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().package.loaded['klbq_kanami/rules'] = self.lua.execute((SCRIPTS/'klbq_kanami/rules.lua').read_text(encoding='utf-8-sig'))
        with zipfile.ZipFile(GAME) as archive:
            native = {name: archive.read('scripts/' + name + '.lua').decode('utf-8-sig')
                      for name in ('class', 'util/sourcemodifierlist', 'components/growable',
                                   'components/farmplanttendable', 'components/farmplantstress',
                                   'components/farmsoildrinker', 'components/pickable',
                                   'components/crop', 'prefabs/farm_plants')}
        self.lua.execute(native['class'])
        modifiers = self.lua.execute(native['util/sourcemodifierlist'])
        self.lua.globals().package.loaded['util/sourcemodifierlist'] = modifiers
        self.lua.globals().SourceModifierList = modifiers
        self.lua.execute('''
          function noop() end
          EntityScript={is_instance=function() return false end}
          function Passive() return setmetatable({}, {__index=function() return noop end}) end
          now=0;GetTime=function() return now end
          function Task() return {Cancel=noop} end
          GetRandomMinMax=function(a,b) return a end
          SpringGrowthMod=function(t) return t end
          math.clamp=function(n,a,b) return math.max(a,math.min(n,b)) end
          c_sel=function() end
          Asset=function() return {} end
          Prefab=function(n,fn) return {name=n,fn=fn} end
          net_tinybyte=function() return {set=function(s,n) s.n=n end,value=function(s) return s.n end} end
          MakeSmallBurnable=noop;MakeSmallPropagator=noop;MakeWaxablePlant=noop
          ACTIONS={DIG={}};WORLD_TILES={FARMING_SOIL=1}
          FARM_PLANT_STRESS={NONE=1,LOW=2,MODERATE=3,HIGH=4}
          TUNING={FARM_PLANT_KILLJOY_RADIUS=5,FARM_PANT_OVERCROWDING_MAX_PLANTS=9,FARM_PLANT_LONG_LIFE_MULT=1}
          plantdef={prefab='farm_plant_carrot',bank='farm_plant_carrot',build='farm_plant_carrot',
            product='carrot',seed='carrot_seeds',fireproof=true,moisture={drink_rate=1,min_percent=.35},
            grow_time={seed={100,100},sprout={100,100},small={100,100},med={100,100},full=1000,oversized=1000},
            nutrient_consumption={2,0,0},nutrient_restoration={false,true,true},
            good_seasons={autumn=true},family_min_count=0,max_killjoys_tolerance=0}
          randomdef={};for k,v in pairs(plantdef) do randomdef[k]=v end
          randomdef.prefab='farm_plant_randomseed';randomdef.is_randomseed=true
          package.loaded['prefabs/farm_plant_defs']={PLANT_DEFS={carrot=plantdef,randomseed=randomdef}}
          package.loaded['prefabs/weed_defs']={WEED_DEFS={},weighted_seed_table={}}
          package.loaded['prefabs/veggies']={}
          nativecomponents={};entities={};spawned={}
          function Entity(name)
            local e={prefab=name,components={},tags={},valid=true,x=0,z=0}
            e.IsValid=function(s) return s.valid end
            e.IsAsleep=function() return false end
            e.AddTag=function(s,t) s.tags[t]=true end
            e.RemoveTag=function(s,t) s.tags[t]=nil end
            e.HasTag=function(s,t) return s.tags[t] or false end
            e.DoTaskInTime=function() return Task() end;e.DoPeriodicTask=e.DoTaskInTime
            e.SetDeploySmartRadius=noop;e.SetPhysicsRadiusOverride=noop
            e.WatchWorldState=noop;e.ListenForEvent=noop;e.PushEvent=noop
            e.Remove=function(s) s.valid=false end
            e.Transform=Passive();e.Transform.GetWorldPosition=function() return e.x,0,e.z end
            e.Transform.SetPosition=function(_,x,y,z) e.x=x;e.z=z end
            e.AnimState=Passive();e.SoundEmitter=Passive();e.entity=Passive()
            e.AddComponent=function(s,n)
              s.components[n]=nativecomponents[n] and nativecomponents[n](s) or Passive()
              s.components[n].inst=s
            end
            e.RemoveComponent=function(s,n) s.components[n]=nil end
            return e
          end
          TheWorld=Entity('world');TheWorld.ismastersim=true;TheWorld.state={isnight=false,season='autumn'}
          TheWorld.Map={GetTileCoordsAtPoint=function() return 1,2 end,
            GetEntitiesOnTileAtPoint=function() return {} end}
          TheWorld.components.farming_manager={water=0,nutrients={0,0,0},
            AddSoilMoistureAtPoint=function(s,x,y,z,n) s.water=s.water+n end,
            IsSoilMoistAtPoint=function(s) return s.water>0 end,
            GetTileNutrients=function(s) return unpack(s.nutrients) end,
            AddTileNutrients=function(s,x,z,a,b,c) s.nutrients={s.nutrients[1]+a,s.nutrients[2]+b,s.nutrients[3]+c} end,
            CycleNutrientsAtPoint=function(s,x,y,z,n,r,test)
              if s.nutrients[1]<n[1] then return true end
              if not test then s.nutrients[1]=s.nutrients[1]-n[1] end
              return false
            end}
          TheNet={GetPVPEnabled=function() return false end}
          TheSim={FindEntities=function(_,x,y,z,r,must,cant,oneof)
            if r~=12 then return {} end
            local found={}
            for _,e in ipairs(entities) do if e:IsValid() then
              local included=oneof==nil
              for _,tag in ipairs(oneof or {}) do if e:HasTag(tag) then included=true end end
              if included then found[#found+1]=e end
            end end
            return found
          end}
          CreateEntity=function() return Entity('farm_plant_carrot') end
          SpawnPrefab=function(name)
            local e
            if prefabs and prefabs[name] then e=prefabs[name].fn();e.prefab=name;entities[#entities+1]=e
            else e=Entity(name);e.components.fertilizer={withered_cycles=0} end
            spawned[#spawned+1]=e;return e
          end
          function Player(name)
            local p=Entity(name);p:AddTag('player')
            p.components.health={IsDead=function() return false end}
            p.components.combat={IsAlly=function() return true end}
            p.components.sanity={SetNegativeAuraImmunity=noop,
              externalmodifiers=SourceModifierList(p,0,SourceModifierList.additive)}
            return p
          end
          owner=Player('klbq_kanami');other=Player('klbq_kanami');ally=Player('wilson')
        ''')
        for name in ('growable', 'farmplanttendable', 'farmplantstress', 'farmsoildrinker', 'pickable', 'crop'):
            self.lua.globals().nativecomponents[name] = self.lua.execute(native['components/' + name])
        self.lua.globals().prefab_list = self.lua.table_from(self.lua.execute(native['prefabs/farm_plants']))
        self.lua.execute('prefabs={};for _,p in ipairs(prefab_list) do prefabs[p.name]=p end;carrotprefab=prefabs.farm_plant_carrot')
        self.lua.execute('crop=carrotprefab.fn();entities={crop,owner,other,ally};now=10')
        # Lua 5.1's Windows C stdio cannot open this Unicode workspace path.
        for name in ('cleanse', 'recruit', 'hermit', 'agriculture', 'domain'):
            path = SCRIPTS / 'klbq_kanami' / (name + '.lua')
            if path.exists():
                module = self.lua.execute(path.read_text(encoding='utf-8-sig'))
                self.lua.globals().package.loaded['klbq_kanami/' + name] = module
                if name == 'domain':
                    self.lua.globals().domain = module

    def module(self):
        path = SCRIPTS / 'klbq_kanami/agriculture.lua'
        self.assertTrue(path.exists(), 'domain must implement automatic native plant care and maturation')
        self.lua.globals().garden = self.lua.eval("require('klbq_kanami/agriculture')")

    def test_native_crop_gets_tended_watered_fertilized_and_matures_without_rotting(self):
        self.module()
        self.lua.execute('''
          local original=crop.components.farmplanttendable.ontendtofn
          crop.components.farmplanttendable.ontendtofn=function(inst,doer)
            crop.tend_count=(crop.tend_count or 0)+1;return original(inst,doer)
          end
          for i=1,8 do garden.Scan(owner);now=now+1 end
        ''')
        self.assertEqual(self.lua.eval('crop.components.growable:GetCurrentStageData().name'), 'full')
        self.assertTrue(self.lua.eval('crop.components.pickable:CanBePicked()'))
        self.assertGreater(self.lua.eval('TheWorld.components.farming_manager.water'), 0)
        self.assertGreater(self.lua.eval('TheWorld.components.farming_manager.nutrients[1]'), 0)
        self.assertEqual(self.lua.eval('crop.tend_count'), 4)
        self.assertEqual(self.lua.eval('crop.components.farmplantstress:GetFinalStressState()'), 1)
        self.assertFalse(self.lua.eval("crop:HasTag('farm_plant_killjoy')"))
        self.assertIsNone(self.lua.eval('crop._magicgrowthtask'))

    def test_common_pickables_get_one_harvest_per_activation_not_quarter_second_refills(self):
        self.module()
        self.lua.execute('''
          bushes={}
          for _,name in ipairs({'berrybush','grass','sapling'}) do
            local b=Entity(name);b:AddTag('plant');b:AddComponent('pickable')
            b.components.pickable:SetUp('twigs',100);b.components.pickable:MakeEmpty()
            bushes[#bushes+1]=b
          end
          entities=bushes;garden.Scan(owner)
        ''')
        self.assertTrue(self.lua.eval('bushes[1].components.pickable:CanBePicked()'))

        self.assertTrue(self.lua.eval('bushes[2].components.pickable:CanBePicked()'))
        self.assertTrue(self.lua.eval('bushes[3].components.pickable:CanBePicked()'))
        self.lua.execute('''
          bushes[1].components.pickable:MakeEmpty()
          for i=1,120 do now=now+.25;garden.Scan(owner) end
        ''')
        self.assertFalse(self.lua.eval('bushes[1].components.pickable:CanBePicked()'))
        self.lua.execute('garden.Remove(owner);now=now+1;garden.Scan(owner)')
        self.assertTrue(self.lua.eval('bushes[1].components.pickable:CanBePicked()'))

    def test_ordinary_planted_seed_replacement_is_tended_and_matures(self):
        self.module()
        self.lua.execute('''
          seed=SpawnPrefab('farm_plant_randomseed');entities={seed}
          -- Native replacement is deterministic here; production keeps random crops/weeds.
          seed._identified_plant_type='farm_plant_carrot'
          for i=1,8 do garden.Scan(owner);now=now+1 end
        ''')
        self.assertFalse(self.lua.eval('seed:IsValid()'), 'ordinary planted seed must germinate')
        self.assertEqual(self.lua.eval('seed.grew_into.prefab'), 'farm_plant_carrot')
        self.assertEqual(self.lua.eval('seed.grew_into.components.growable:GetCurrentStageData().name'), 'full')
        self.assertTrue(self.lua.eval('seed.grew_into.components.pickable:CanBePicked()'))
        self.assertEqual(self.lua.eval('seed.grew_into.components.farmplantstress:GetFinalStressState()'), 1)

    def test_native_tree_growth_stops_at_magic_mature_stage(self):
        self.module()
        self.lua.execute('''
          tree=Entity('evergreen');tree:AddTag('tree');tree:AddComponent('growable')
          tree.components.growable.stages={
            {name='short',time=function()return 100 end},
            {name='normal',time=function()return 100 end},
            {name='tall',time=function()return 100 end},
            {name='old',time=function()return 100 end}}
          tree.components.growable:SetStage(1);tree.components.growable:StartGrowing()
          tree.components.simplemagicgrower={last_stage=3}
          entities={tree}
          for i=1,8 do garden.Scan(owner);garden.Scan(other);now=now+1 end
        ''')
        self.assertEqual(self.lua.eval('tree.components.growable:GetStage()'), 3)
        self.assertFalse(self.lua.eval("tree:HasTag('magicgrowth')"))

    def test_barren_pickables_are_not_fertilized_or_revived(self):
        self.module()
        self.lua.execute('''
          entities={}
          for _,name in ipairs({'grass','berrybush','berrybush2','berrybush_juicy','sapling'})do
            local b=Entity(name);b:AddTag('plant');b:AddComponent('pickable')
            b.components.pickable:SetUp('twigs',100);b.components.pickable:MakeBarren()
            entities[#entities+1]=b
          end
          for i=1,4 do garden.Scan(owner);now=now+1 end
        ''')
        self.assertEqual(self.lua.eval('#spawned'), 0)
        self.assertTrue(self.lua.eval('function()for _,b in ipairs(entities)do if not b.components.pickable:IsBarren() then return false end end return true end')())

    def test_unknown_weeds_loose_seeds_and_growing_entities_are_never_changed(self):
        self.module()
        self.lua.execute('''
          entities={}
          for _,name in ipairs({'mod_berrybush','weed_forgetmelots','seeds','evergreen'}) do
            local t=Entity(name);t:AddTag('plant');t.components.growable={DoGrowth=function() error('unknown grew') end}
            t.components.pickable={FinishGrowing=function() error('unknown regenerated') end}
            entities[#entities+1]=t
          end
          for i=1,8 do garden.Scan(owner);now=now+1 end
        ''')
        self.assertTrue(self.lua.eval('function() for _,e in ipairs(entities) do if not e:IsValid() then return false end end return true end')())
        self.assertEqual(self.lua.eval('#spawned'), 0)

    def test_legacy_native_crop_matures_without_harvesting_or_changing_its_product(self):
        self.module()
        self.lua.execute('''
          old=Entity('plant_normal');old:AddTag('notreadyforharvest');old:AddComponent('crop')
          old.components.crop.product_prefab='corn';entities={old};garden.Scan(owner)
        ''')
        self.assertTrue(self.lua.eval('old.components.crop:IsReadyForHarvest()'))
        self.assertEqual(self.lua.eval('old.components.crop.product_prefab'), 'corn')
        self.assertTrue(self.lua.eval('old:IsValid()'))

    def test_overlapping_domains_share_one_growth_step_and_cannot_refill_a_picked_bush(self):
        self.module()
        self.lua.execute('''
          garden.Scan(owner);first=crop.components.growable:GetStage();garden.Scan(other)
          bush=Entity('berrybush');bush:AddTag('plant');bush:AddComponent('pickable')
          bush.components.pickable:SetUp('berries',100);bush.components.pickable:MakeEmpty()
          entities={bush};now=now+1;garden.Scan(owner)
          bush.components.pickable:MakeEmpty();garden.Scan(other)
        ''')
        self.assertEqual(self.lua.eval('first'), 2)
        self.assertEqual(self.lua.eval('crop.components.growable:GetStage()'), 2)
        self.assertFalse(self.lua.eval('bush.components.pickable:CanBePicked()'))

    def test_domain_exit_stops_growth_and_releases_only_its_plant_membership(self):
        self.module()
        self.lua.execute('''
          tracked=domain.Scan(owner);domain.Scan(other);first=crop.components.growable:GetStage()
          domain.Remove(owner,tracked);now=now+1;garden.Scan(other)
        ''')
        self.assertIsNone(self.lua.eval('owner._klbq_garden'))
        self.assertGreater(self.lua.eval('crop.components.growable:GetStage()'), self.lua.eval('first'))
        self.lua.execute('''
          garden.Remove(other);stopped=crop.components.growable:GetStage();now=now+10
        ''')
        self.assertEqual(self.lua.eval('crop.components.growable:GetStage()'), self.lua.eval('stopped'))
        self.assertIsNone(self.lua.eval('crop._magicgrowthtask'))

    def test_domain_scan_integrates_gardening_but_never_runs_on_clients(self):
        self.module()
        self.lua.execute('first=crop.components.growable:GetStage();TheWorld.ismastersim=false;domain.Scan(owner)')
        self.assertEqual(self.lua.eval('crop.components.growable:GetStage()'), self.lua.eval('first'))
        self.lua.execute('TheWorld.ismastersim=true;domain.Scan(owner)')
        self.assertGreater(self.lua.eval('crop.components.growable:GetStage()'), self.lua.eval('first'))

    def test_allies_gain_exact_half_sanity_per_second_owner_excluded_and_domains_do_not_stack(self):
        # The native modifier list is the exact additive channel used by sanity:Recalc.
        self.lua.execute('entities={owner,other,ally};oa=domain.Scan(owner)')
        self.assertEqual(self.lua.eval('owner.components.sanity.externalmodifiers:Get()'), 0)
        self.assertEqual(self.lua.eval('other.components.sanity.externalmodifiers:Get()'), .5)
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), .5)
        self.lua.execute('ob=domain.Scan(other)')
        self.assertEqual(self.lua.eval('owner.components.sanity.externalmodifiers:Get()'), .5)
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), .5)
        self.lua.execute('domain.Remove(owner,oa)')
        self.assertEqual(self.lua.eval('other.components.sanity.externalmodifiers:Get()'), 0)
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), .5)
        self.lua.execute('domain.Remove(other,ob)')
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), 0)

    def test_component_replacement_and_pvp_leave_other_sanity_modifiers_intact(self):
        self.lua.execute('''
          entities={ally};ally.components.sanity.externalmodifiers:SetModifier('equipment',-.2)
          tracked=domain.Scan(owner)
          oldsanity=ally.components.sanity
          ally.components.sanity={SetNegativeAuraImmunity=noop,
            externalmodifiers=SourceModifierList(ally,0,SourceModifierList.additive)}
          domain.Scan(owner,tracked)
        ''')
        self.assertAlmostEqual(self.lua.eval('oldsanity.externalmodifiers:Get()'), -.2)
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), .5)
        self.lua.execute('''
          TheNet.GetPVPEnabled=function() return true end
          owner.components.combat.IsAlly=function() return false end
          domain.Scan(owner,tracked)
        ''')
        self.assertEqual(self.lua.eval('ally.components.sanity.externalmodifiers:Get()'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
