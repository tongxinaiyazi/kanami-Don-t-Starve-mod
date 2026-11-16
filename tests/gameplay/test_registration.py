import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime
class Registration(unittest.TestCase):
 def test_modinfo_does_not_require_absent_string_library(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  lua.execute('info={}')
  source=(ROOT/'mods/klbq_kanami/modinfo.lua').read_text(encoding='utf-8-sig')
  lua.execute('setfenv(assert(loadstring(...)),info)()',source)
  self.assertEqual(lua.eval('info.configuration_options[1].default'),114)
  self.assertEqual(lua.eval('#info.configuration_options[1].options'),26)
  option=next(v for _,v in lua.globals().info.configuration_options.items() if v.name=='fate_crit_fraction')
  self.assertEqual(option.default,.03)
  self.assertEqual([v.data for _,v in option.options.items()],[.03,.05,.1,.2])
 def test_modmain_registers_in_restricted_game_mod_environment(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  from resource_fixture import preload_resources
  preload_resources(lua)
  lua.execute('''
   STRINGS={CHARACTER_TITLES={},CHARACTER_NAMES={},CHARACTER_DESCRIPTIONS={},CHARACTER_QUOTES={},CHARACTER_SURVIVABILITY={},NAMES={},CHARACTERS={GENERIC={DESCRIBE={}}},SKIN_NAMES={},RECIPE_DESC={}}
   TheNet={IsDedicated=function() return true end};TECH={SCIENCE_ONE=1,SCIENCE_TWO=2}
   Action=function(v) return v end;ActionHandler=function() return {} end;ACTIONS={DROP={fn=function()end}}
   Ingredient=function(name,num,atlas) return {name=name,num=num,atlas=atlas} end
   Vector3=function(x,y,z) return {x=x,y=y,z=z} end
   State=function(v) return v end;EventHandler=function() return {} end;TimeEvent=function()return {}end
   TUNING={WILSON_ATTACK_PERIOD=.4}
   package.preload.containers=function() return {params={},MAXITEMSLOTS=0} end
   package.preload.speech_willow=function() return {} end
   package.preload['klbq_kanami/technology']=function() return {Install=function() TECH.KLBQ_STRING_ONE={KLBQ_STRING=1} end} end
   package.preload['klbq_kanami/chef']=function() return {Install=function() end} end
   env={GLOBAL=_G,env=nil,pairs=pairs,ipairs=ipairs,math=math,type=type,string=string,table=table,require=require,print=function() end}
   env.env=env;recipes={};postinits={}
   env.Asset=function() return {} end
   env.GetModConfigData=function(key) if key=='fate_crit_fraction' then return .1 end end
   env.RegisterInventoryItemAtlas=function() end
   for _,n in ipairs({'AddMinimapAtlas','AddModCharacter','AddAction','AddComponentAction','AddStategraphActionHandler','AddStategraphState','AddStategraphPostInit','AddModRPCHandler','AddComponentPostInit','AddClassPostConstruct'}) do env[n]=function() end end
   env.AddPrefabPostInit=function(name,fn) postinits[name]=fn end
   env.AddPlayerPostInit=function() end
   env.AddRecipe2=function(name,ingredients,tech,config) recipes[name]={ingredients=ingredients,tech=tech,config=config} end
  ''')
  for name in ('klbq_kanami/rules','klbq_kanami/cleanse','klbq_kanami/recruit','klbq_kanami/hermit','klbq_kanami/domain','klbq_kanami/states','klbq_kanami/crossbow','klbq_kanami/requiem','klbq_kanami/curse','klbq_kanami/visual','klbq_kanami/bag','klbq_kanami/speech'):
   p=ROOT/'mods/klbq_kanami/scripts'/f'{name}.lua'
   lua.execute('package.preload[...] = function() '+p.read_text(encoding='utf8')+' end',name)
  source=(ROOT/'mods/klbq_kanami/modmain.lua').read_text(encoding='utf-8-sig')
  lua.execute('setfenv(assert(loadstring(...)),env)()',source)
  self.assertEqual(lua.eval('require("klbq_kanami/rules").Fate(20000,true,false)'),2000)
  self.assertEqual(lua.eval("recipes.klbq_ammo_fate.ingredients[1].name"),'klbq_resource_topology_ring')
  self.assertEqual(lua.eval("recipes.klbq_ammo_heart.config.numtogive"),20)
  self.assertEqual(lua.eval("recipes.klbq_crystal.ingredients[1].name"),'klbq_resource_terminal_kanami')
  self.assertEqual(lua.eval("recipes.klbq_crystal.ingredients[1].num"),1)
  self.assertEqual(lua.eval("recipes.klbq_crystal.ingredients[1].atlas"),'images/klbq_resources_items.xml')
  self.assertNotIn('靠近',lua.eval('STRINGS.RECIPE_DESC.KLBQ_CRYSTAL'))
  self.assertNotIn('制作',lua.eval('STRINGS.RECIPE_DESC.KLBQ_CRYSTAL'))
  self.assertEqual(lua.eval("recipes.klbq_ammo_doom.tech.KLBQ_STRING"),1)
  self.assertTrue(lua.eval("recipes.klbq_ammo_doom.config.nounlock"))
  self.assertTrue(lua.eval("recipes.klbq_ammo_doom.ingredients[1].name~='opalpreciousgem'"))
  self.assertTrue(lua.eval("recipes.klbq_ammo_doom.ingredients[4].name=='opalpreciousgem' and recipes.klbq_ammo_doom.ingredients[4].num==1"))
  lua.execute('''
   TheWorld={ismastersim=false};EQUIPSLOTS={HANDS='hands'}
   p={components={playeractionpicker={SortActionList=function(s,a) return a end}},
      replica={inventory={GetEquippedItem=function() return nil end}},_klbq_string={value=function() return true end},
      DoTaskInTime=function(s,t,f) f() end}
   p.components.playeractionpicker.inst=p
   postinits.klbq_kanami(p)
   function actionfilter(i,a) return #i.components.playeractionpicker:SortActionList({a})>0 end
  ''')
  for name in ('FISH','REEL','OCEAN_FISHING_CAST','OCEAN_FISHING_REEL','OCEAN_FISHING_POND','OCEAN_FISHING_CATCH'):
   with self.subTest(action=name):self.assertFalse(lua.eval('actionfilter(p,{id=...})',name))
  self.assertTrue(lua.eval('actionfilter(p,{id="EAT"})'))
 def test_every_lua_file_parses_in_lua51(self):
  lua=LuaRuntime(unpack_returned_tuples=True)
  for p in (ROOT/'mods/klbq_kanami').rglob('*.lua'):
   with self.subTest(file=p.name):lua.execute('assert(loadstring(...))',p.read_text(encoding='utf-8-sig'))
if __name__=='__main__':unittest.main(verbosity=2)
