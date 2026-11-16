"""Chef regressions execute the installed DST eater, edible, stewer and cooking."""
import sys
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")
MOD = ROOT / 'mods/klbq_kanami/scripts'


class Chef(unittest.TestCase):
    def setUp(self):
        path = MOD / 'klbq_kanami/chef.lua'
        self.assertTrue(path.exists(), 'missing chef gameplay implementation')
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME) as archive:
            self.native = {name: archive.read('scripts/' + name + '.lua').decode('utf-8-sig')
                           for name in ('class', 'cooking', 'spicedfoods', 'components/eater',
                                        'components/edible', 'components/stewer')}
            tuning = archive.read('scripts/tuning.lua').decode('utf-8-sig')
            self.stale_health=float(re.search(r'\bSTALE_FOOD_HEALTH\s*=\s*([.0-9]+)',tuning)[1])
            self.stale_hunger=float(re.search(r'\bSTALE_FOOD_HUNGER\s*=\s*([.0-9]+)',tuning)[1])
        self.lua.execute(self.native['class'])
        self.lua.execute('''
          FOODTYPE={GENERIC='GENERIC',MEAT='MEAT',VEGGIE='VEGGIE'}
          FOODGROUP={OMNI='GENERIC'}
          TUNING={STALE_FOOD_HUNGER=2/3,STALE_FOOD_HEALTH=1/3,
            SPOILED_FOOD_HUNGER=.5,SPOILED_FOOD_HEALTH=0,SANITY_SMALL=10,
            BASE_COOK_TIME=20,PERISH_MED=4800,STACK_SIZE_SMALLITEM=40,
            HOT_FOOD_BONUS_TEMP=40,FOOD_TEMP_LONG=480,
            SPICE_MULTIPLIERS={SPICE_SALT={HEALTH=.25},SPICE_CHILI={TEMPERATUREDELTA=.2}}}
          TheWorld={ismastersim=true};now=0;GetTime=function() return now end
          shallowcopy=function(t) local v={} for k,x in pairs(t) do v[k]=x end return v end
          package.preload.tuning=function() return {} end
          package.preload.preparedfoods=function() return {} end
          package.preload.preparedfoods_warly=function() return {} end
          package.preload.preparednonfoods=function() return {} end
          package.preload['prefabs/oceanfishdef']=function() return {fish={}} end
          function Entity(name)
            local e={prefab=name,tags={},components={},events={},tasks={}}
            e.AddTag=function(s,t) s.tags[t]=true end
            e.RemoveTag=function(s,t) s.tags[t]=nil end
            e.HasTag=function(s,t) return s.tags[t]==true end
            e.HasAnyTag=function(s,ts) for _,t in ipairs(ts) do if s:HasTag(t) then return true end end return false end
            e.ListenForEvent=function() end
            e.PushEvent=function(s,t,d) s.events[t]=d end
            e.IsValid=function() return true end
            e.Remove=function(s) s.removed=true end
            e.GetPosition=function() return {x=0,y=0,z=0} end
            e.Transform={SetPosition=function() end,GetWorldPosition=function() return 0,0,0 end}
            e.Physics={Stop=function() end}
            e.DoTaskInTime=function(s,t,f,...)
              local args={...};local task={Cancel=function(s) s.cancelled=true end}
              task.run=function() f(s,unpack(args)) end;table.insert(s.tasks,task);return task
            end
            return e
          end
          hooks={};recipes={}
          env={GLOBAL=_G,AddComponentPostInit=function(n,f) hooks[n]=f end,
            AddCookerRecipe=function(n,r) AddCookerRecipe(n,r,true);recipes[n]=recipes[n] or {};recipes[n][r.name]=r end}
          function Player(kanami)
            local p=Entity(kanami and 'klbq_kanami' or 'wilson')
            p:AddTag('player');if kanami then p:AddTag('klbq_kanami') end
            p.userid=kanami and 'kanami' or 'wilson';p.player_classified={}
            for _,n in ipairs({'health','hunger','sanity'}) do
              p.components[n]={total=0,DoDelta=function(s,v) s.total=s.total+v end}
            end
            p.items={};p.components.inventory={GiveItem=function(s,item) table.insert(p.items,item) end}
            p.components.eater=Eater(p)
            return p
          end
          function Food(name,state,h,u,s)
            local f=Entity(name);f:AddTag('edible_GENERIC')
            f.components.edible=Edible(f)
            f.components.edible.healthvalue=h or 30;f.components.edible.hungervalue=u or 50;f.components.edible.sanityvalue=s or 70
            local perish={state=state,percent=1,IsStale=function(s) return s.state=='stale' end,
              IsSpoiled=function(s) return s.state=='spoiled' end,GetPercent=function(s) return s.percent end,
              SetPercent=function(s,v) s.percent=v end,StartPerishing=function() end}
            f.components.perishable=perish
            f.components.stackable={stacksize=1,SetStackSize=function(s,v) s.stacksize=v end,
              StackSize=function(s) return s.stacksize end,Get=function() return f end}
            if hooks.edible then hooks.edible(f.components.edible) end
            return f
          end
          SpawnPrefab=function(n) return Food(n,'fresh') end
          LaunchAt=function(f) dropped=f end
          function Pot(kind)
            local p=Entity(kind or 'cookpot');p.components.stewer=Stewer(p)
            p.components.container={slots={},Close=function() end,IsFull=function() return true end,
              DestroyContents=function(s) s.slots={} end}
            hooks.stewer(p.components.stewer)
            return p
          end
          function Ingredients(p,names)
            p.components.container.slots={}
            for i,n in ipairs(names) do p.components.container.slots[i]=Food(n,'fresh') end
          end
        ''')
        self.lua.execute('TUNING.STALE_FOOD_HEALTH,TUNING.STALE_FOOD_HUNGER=...',self.stale_health,self.stale_hunger)
        for name in ('spicedfoods', 'cooking', 'components/eater', 'components/edible', 'components/stewer'):
            self.lua.execute('package.preload[...] = function() ' + self.native[name] + ' end', name)
        self.lua.execute("cooking=require('cooking');Eater=require('components/eater');Edible=require('components/edible');Stewer=require('components/stewer')")
        self.lua.globals().chef = self.lua.execute(path.read_text(encoding='utf-8-sig'))
        self.lua.execute('''
          chef.Install(env)
          for _,n in ipairs({'cookpot','portablecookpot'}) do
            env.AddCookerRecipe(n,{name='wetgoop',test=function() return true end,priority=-100,weight=1,perishtime=4800})
          end
          kanami=Player(true);normal=Player(false);chef.Common(kanami)
        ''')

    def assert_stats(self, p, health, hunger, sanity):
        for field, value in zip(('health', 'hunger', 'sanity'), (health, hunger, sanity)):
            self.assertAlmostEqual(self.lua.eval(f'{p}.components.{field}.total'), value)

    def test_native_chef_permissions_without_native_warly_drawbacks(self):
        self.assertTrue(self.lua.eval("kanami:HasTag('masterchef') and kanami:HasTag('professionalchef') and kanami:HasTag('expertchef')"))
        self.assertIsNone(self.lua.eval('kanami.components.foodmemory'))
        self.assertIsNone(self.lua.eval('kanami.components.eater.preferseatingtags'))
        self.lua.execute("raw=Food('berries','fresh');kanami.components.eater:Eat(raw)")
        self.assert_stats('kanami', 30, 50, 70)

    def test_stale_and_spoiled_multiply_native_positive_spoilage_results(self):
        for state, expected in (('stale', (30*self.stale_health*.5, 50*self.stale_hunger*.5, 0)), ('spoiled', (0, 2.5, -10))):
            with self.subTest(state=state):
                self.lua.execute("kanami=Player(true);f=Food('test',...);assert(kanami.components.eater:Eat(f))", state)
                self.assert_stats('kanami', *expected)
        self.lua.execute("f=Food('test','spoiled');normal.components.eater:Eat(f)")
        self.assert_stats('normal', 0, 25, -10)

    def test_freshness_policy_is_configurable_and_negative_stats_are_preserved(self):
        self.lua.execute("chef.Configure({stale=.25,spoiled=.05});f=Food('bad','stale',-20,50,-15);kanami.components.eater:Eat(f)")
        self.assert_stats('kanami', -20, 50 * self.stale_hunger * .25, -15)

    def test_dynamic_native_getters_spices_and_other_eater_hooks_still_run_once(self):
        self.lua.execute('''
          getcalls=0;eatcalls=0;customcalls=0
          f=Food('test','spoiled');f.components.edible.spice='SPICE_SALT'
          f.components.edible:SetGetHealthFn(function(food,eater) getcalls=getcalls+1;assert(food==f and eater==kanami);return 40 end)
          f.components.edible:SetOnEatenFn(function(food,eater) eatcalls=eatcalls+1 end)
          kanami.components.eater.custom_stats_mod_fn=function(i,h,u,s,food) customcalls=customcalls+1;return h*2,u,s end
          kanami.components.eater:Eat(f)
        ''')
        self.assert_stats('kanami', 0, 2.5, -10)
        for n in ('getcalls', 'eatcalls', 'customcalls'):
            self.assertEqual(self.lua.eval(n), 1)
        self.assertTrue(self.lua.eval('f.components.edible.degrades_with_spoilage'))

    def test_getter_failure_keeps_native_spoilage_state(self):
        self.lua.execute("f=Food('test','stale');f.components.edible:SetGetHealthFn(function() error('food hook failed') end);ok,err=pcall(f.components.edible.GetHealth,f.components.edible,kanami)")
        self.assertFalse(self.lua.eval('ok'))
        self.assertIn('food hook failed', self.lua.eval('err'))
        self.assertTrue(self.lua.eval('f.components.edible.degrades_with_spoilage'))

    def test_dynamic_getter_observes_original_spoilage_state_and_runs_once(self):
        self.lua.execute('''
          calls=0;f=Food('test','stale')
          f.components.edible:SetGetHealthFn(function(food,eater)
            calls=calls+1;assert(food.components.edible.degrades_with_spoilage)
            return 60
          end)
          gain=f.components.edible:GetHealth(kanami)
        ''')
        self.assertEqual(self.lua.eval('calls'), 1)
        self.assertAlmostEqual(self.lua.eval('gain'), 60*self.stale_health*.5)

    def test_omurice_recipe_uses_real_ingredient_egg_values_in_both_pots(self):
        for pot in ('cookpot', 'portablecookpot'):
            with self.subTest(pot=pot):
                self.lua.execute("product=cooking.CalculateRecipe(...,{'bird_egg','bird_egg','tomato','potato'})", pot)
                self.assertEqual(self.lua.eval('product'), 'klbq_omurice')
                self.lua.execute("product=cooking.CalculateRecipe(...,{'bird_egg','tomato','potato','twigs'})", pot)
                self.assertEqual(self.lua.eval('product'), 'wetgoop')
                self.lua.execute("product=cooking.CalculateRecipe(...,{'tallbirdegg','tomato_cooked','potato_cooked','berries'})", pot)
                self.assertEqual(self.lua.eval('product'), 'klbq_omurice')

    def test_omurice_rejects_prohibited_fillers_with_real_cooking_tags(self):
        for pot in ('cookpot','portablecookpot'):
            for filler in ('twigs','meat','fish','monstermeat','mandrake'):
                with self.subTest(pot=pot,filler=filler):
                    self.lua.execute("product=cooking.CalculateRecipe(...,{'tallbirdegg','tomato','potato',select(2,...)})", pot,filler)
                    self.assertNotEqual(self.lua.eval('product'),'klbq_omurice')

    def test_omurice_positive_stats_get_one_affinity_multiplier(self):
        self.lua.execute("f=Food('klbq_omurice','fresh');kanami.components.eater:Eat(f);f=Food('klbq_omurice','fresh');normal.components.eater:Eat(f)")
        self.assert_stats('kanami', 45, 75, 105)
        self.assert_stats('normal', 30, 50, 70)

    def test_stale_omurice_combines_freshness_and_affinity_once(self):
        self.lua.execute("f=Food('klbq_omurice','stale');kanami.components.eater:Eat(f)")
        self.assert_stats('kanami', 45*self.stale_health*.5, 75*self.stale_hunger*.5, 0)

    def test_spoiled_omurice_does_not_turn_native_sanity_penalty_into_gain(self):
        self.lua.execute("f=Food('klbq_omurice','spoiled');kanami.components.eater:Eat(f)")
        self.assert_stats('kanami', 0, 3.75, -10)

    def test_original_spice_generation_and_eaten_buff_for_omurice(self):
        self.assertEqual(self.lua.eval("cooking.CalculateRecipe('portablespicer',{'klbq_omurice','spice_garlic'})"), ('klbq_omurice_spice_garlic', .12))
        self.lua.execute("buffs=0;kanami.AddDebuff=function(s,n,p) assert(n=='buff_playerabsorption');buffs=buffs+1 end;recipes.portablespicer.klbq_omurice_spice_garlic.oneatenfn({},kanami)")
        self.assertEqual(self.lua.eval('buffs'), 1)

    def test_double_yield_belongs_to_cook_and_survives_save_load(self):
        for kind in ('cookpot', 'portablecookpot'):
            with self.subTest(kind=kind):
                self.lua.execute('''
                  normal.items={};pot=Pot(...);Ingredients(pot,{'bird_egg','bird_egg','tomato','potato'})
                  pot.components.stewer:StartCooking(kanami)
                  -- A second StartCooking while cooking must not change the owner.
                  pot.components.stewer:StartCooking(normal)
                  data=pot.components.stewer:OnSave();loaded=Pot(pot.prefab)
                  loaded.components.stewer:OnLoad(data);loaded.components.stewer:LongUpdate(100)
                  assert(loaded.components.stewer:Harvest(normal))
                ''', kind)
                self.assertEqual(self.lua.eval('#normal.items'), 2)
                self.lua.execute("assert(not loaded.components.stewer:Harvest(normal))")
                self.assertEqual(self.lua.eval('#normal.items'), 2)

    def test_kanami_harvesting_others_food_does_not_double_and_stop_clears_owner(self):
        self.lua.execute('''
          pot=Pot();Ingredients(pot,{'bird_egg','bird_egg','tomato','potato'})
          pot.components.stewer:StartCooking(kanami);pot.components.stewer:StopCooking()
          Ingredients(pot,{'bird_egg','bird_egg','tomato','potato'})
          pot.components.stewer:StartCooking(normal);pot.components.stewer:LongUpdate(100)
          pot.components.stewer:Harvest(kanami)
        ''')
        self.assertEqual(self.lua.eval('#kanami.items'), 1)

    def test_double_food_has_same_native_spoilage_and_original_harvest_hook(self):
        self.lua.execute('''
          pot=Pot();Ingredients(pot,{'bird_egg','bird_egg','tomato','potato'})
          harvestcalls=0;pot.components.stewer.onharvest=function() harvestcalls=harvestcalls+1 end
          pot.components.stewer:StartCooking(kanami);pot.components.stewer:LongUpdate(100)
          now=480;pot.components.stewer:Harvest(normal)
        ''')
        self.assertEqual(self.lua.eval('harvestcalls'), 1)
        self.assertEqual(self.lua.eval('#normal.items'), 2)
        self.assertAlmostEqual(self.lua.eval('normal.items[1].components.perishable.percent'), self.lua.eval('normal.items[2].components.perishable.percent'))

    def test_old_save_without_owner_never_gets_double_yield(self):
        self.lua.execute('''
          pot=Pot();pot.components.stewer:OnLoad({product='klbq_omurice',done=true,remainingtime=100,spoiltime=4800,product_spoilage=1})
          pot.components.stewer:Harvest(kanami)
        ''')
        self.assertEqual(self.lua.eval('#kanami.items'), 1)

    def test_existing_method_arguments_returns_and_save_references_are_preserved(self):
        self.lua.execute('''
          local old=Edible.GetHunger
          Edible.GetHunger=function(s,e,arg) return old(s,e),arg end
          f=Food('test','stale');h,extra=f.components.edible:GetHunger(kanami,'getter arg')
          local oldsave=Stewer.OnSave
          Stewer.OnSave=function(s,arg) local d=oldsave(s);d.othermod=arg;return d,{100,200} end
          pot=Pot();Ingredients(pot,{'bird_egg','bird_egg','tomato','potato'})
          pot.components.stewer:StartCooking(kanami);saved,refs=pot.components.stewer:OnSave('save arg')
        ''')
        self.assertAlmostEqual(self.lua.eval('h'), 50 * self.stale_hunger * .5)
        self.assertEqual(self.lua.eval('extra'), 'getter arg')
        self.assertEqual(self.lua.eval('saved.othermod'), 'save arg')
        self.assertEqual(self.lua.eval('refs[2]'), 200)
        self.assertTrue(self.lua.eval('saved.klbq_kanami_cooked'))

    def test_food_prefabs_construct_on_both_sides_with_real_stats(self):
        self.lua.execute('''
          package.preload['klbq_kanami/chef']=function() return chef end
          Asset=function(kind,path) return {kind,path} end
          Prefab=function(name,fn,assets,prefabs) return {name=name,fn=fn,assets=assets,prefabs=prefabs} end
          for _,n in ipairs({'MakeInventoryPhysics','MakeInventoryFloatable','MakeSmallBurnable',
            'MakeSmallPropagator','MakeHauntableLaunchAndPerish'}) do _G[n]=function() end end
          function CreateEntity()
            local i=Entity('klbq_omurice')
            i.AnimState={SetBank=function(s,n) s.bank=n end,SetBuild=function(s,n) s.build=n end,
              PlayAnimation=function(s,n) s.anim=n end,OverrideSymbol=function() end}
            i.entity={AddTransform=function() end,AddAnimState=function() end,
              AddNetwork=function() i.networked=true end,SetPristine=function() assert(i.networked);i.pristine=true end}
            i.SetPrefabNameOverride=function() end
            i.AddComponent=function(s,n)
              assert(s.pristine,'server components must follow pristine/client boundary')
              if n=='edible' then s.components.edible=Edible(s);hooks.edible(s.components.edible)
              else s.components[n]={ChangeImageName=function(s,n) s.image=n end,
                SetPerishTime=function(s,v) s.perishtime=v end,StartPerishing=function(s) s.started=true end} end
            end
            return i
          end
        ''')
        data = self.lua.execute((MOD / 'prefabs/klbq_omurice.lua').read_text(encoding='utf-8-sig'))
        self.assertEqual(len(data), 5)
        self.lua.globals().foodprefabs = self.lua.table_from(data)
        self.lua.execute('''
          actual=foodprefabs[1].fn()
          for _,p in ipairs(foodprefabs) do assert(p.fn().components.edible.healthvalue==30) end
          TheWorld.ismastersim=false;replica=foodprefabs[1].fn()
        ''')
        self.assertTrue(self.lua.eval('actual.pristine and replica.pristine'))
        self.assertIsNone(self.lua.eval('replica.components.edible'))
        self.assertEqual(self.lua.eval('actual.components.edible.healthvalue'), 30)
        self.assertEqual(self.lua.eval('actual.components.edible.hungervalue'), 50)
        self.assertEqual(self.lua.eval('actual.components.edible.sanityvalue'), 70)
        self.assertTrue(self.lua.eval('actual.components.perishable.started'))
        self.assertEqual(self.lua.eval('actual.AnimState.bank'), 'klbq_omurice')
        self.assertEqual(self.lua.eval('actual.components.inventoryitem.atlasname'), 'images/klbq_kanami_items.xml')


if __name__ == '__main__':
    unittest.main(verbosity=2)
