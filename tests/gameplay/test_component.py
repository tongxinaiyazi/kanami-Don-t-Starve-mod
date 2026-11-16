import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/python-deps'))
from lupa.lua51 import LuaRuntime

class Lifecycle(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime(unpack_returned_tuples=True)
  for name in ('klbq_kanami/rules','klbq_kanami/compat','klbq_kanami/damage','klbq_kanami/rifle','klbq_kanami/chef','klbq_kanami/curse','klbq_kanami/cleanse','klbq_kanami/recruit','klbq_kanami/hermit','klbq_kanami/agriculture','klbq_kanami/domain','klbq_kanami/visual','klbq_kanami/crossbow','components/klbq_kanami'):
   p=ROOT/'mods/klbq_kanami/scripts'/f'{name}.lua'
   self.assertTrue(p.exists(),f'missing behavior module: {name}')
   self.lua.execute("package.preload[...] = function() "+p.read_text(encoding='utf-8-sig')+" end",name)
  self.lua.execute('''
   now=0;GetTime=function() return now end;EQUIPSLOTS={HANDS='hands'}
   Vector3=function(x,y,z) return {x=x,y=y,z=z} end
   Class=function(ctor) local c={};c.__index=c;setmetatable(c,{__call=function(_,...) local s=setmetatable({},c);ctor(s,...);return s end});return c end
   TheWorld={ismastersim=true,Map={IsInMapBounds=function() return true end,IsAboveGroundAtPoint=function() return true end,IsPassableAtPoint=function() return true end,IsVisualGroundAtPoint=function() return true end,IsGroundTargetBlocked=function() return false end}}
   TheSim={FindEntities=function() return {} end};COLLISION={GROUND=1,WORLD=2}
   ChangeToCharacterPhysics=function() end
   SpawnPrefab=function() return nil end
   local function Net() return {v=0,set=function(self,v) self.v=v end,value=function(self) return self.v end} end
   inst={GUID=1,components={},tags={},events={},tasks={},Transform={GetWorldPosition=function() return 0,0,0 end},Physics={SetCollisionMask=function() end,Teleport=function() end},AnimState={SetMultColour=function() end,GetBuild=function(s) return s.build or 'klbq_kanami' end,SetBuild=function(s,b) s.build=b end},
    IsValid=function() return true end,IsInLimbo=function() return false end,GetCurrentPlatform=function() return nil end,GetPhysicsRadius=function() return .5 end,
    HasTag=function(s,t) return s.tags[t] end,AddTag=function(s,t) s.tags[t]=true end,RemoveTag=function(s,t) s.tags[t]=nil end,
    ListenForEvent=function(s,n,f) s.events[n]=f end,RemoveEventCallback=function() end,
    PushEvent=function(s,n,d) if s.events[n] then s.events[n](s,d) end end,
    updating={},StartUpdatingComponent=function(s,c) s.updating[c]=true end,StopUpdatingComponent=function(s,c) s.updating[c]=nil end,
    DoPeriodicTask=function() return {Cancel=function() end} end,
    DoTaskInTime=function(s,t,f) table.insert(s.tasks,f);return {Cancel=function() end} end}
   for _,k in ipairs({'string','z','x','protect','wet','waterwalk','ztime','xtime','zcd','xcd','revive','passivecd','shotcd','ammo'}) do inst['_klbq_'..k]=Net() end
   inst.components.moisture={moisture=0,GetMoisture=function(s) return s.moisture end}
   inst.components.drownable={ShouldDrown=function() return true end,ShouldFallInVoid=function() return true end}
   inst.components.health={currenthealth=75,IsDead=function(s) return s.currenthealth<=0 end,DoDelta=function(s,n) s.currenthealth=s.currenthealth+n;return n end,SetCurrentHealth=function(s,v) s.currenthealth=v end,ForceUpdateHUD=function() end}
   inst.components.hunger={SetPercent=function(s,v) s.p=v end};inst.components.sanity={SetPercent=function(s,v) s.p=v end}
   inst.components.locomotor={GetSpeedMultiplier=function() return 1.3 end,AdjustPathCaps=function() end,RemoveExternalSpeedMultiplier=function() end,SetExternalSpeedMultiplier=function() end}
   inst.components.combat={CalcDamage=function() return 34,{planar=10} end,DoAttack=function(self) captured=inst.components.klbq_kanami.attackcontext;duringattackdamage=self:CalcDamage(nil,nil);return 'original',7 end,CanAttack=function() return true end,GetWeapon=function() return nil end,externaldamagemultipliers={Get=function() return 1 end}}
   inst.components.inventory={GetEquippedItem=function() return nil end,Equip=function() return true end}
   inst.AnimState.HideSymbol=function() end;inst.AnimState.ShowSymbol=function() end
   inst.AnimState.Hide=function() end;inst.AnimState.Show=function() end;inst.AnimState.ClearOverrideSymbol=function() end
   component=require('components/klbq_kanami')(inst);inst.components.klbq_kanami=component
  ''')
 def test_string_is_free_additive_and_reduces_all_health_damage(self):
  self.assertTrue(self.lua.eval("component:ToggleString()"))
  self.assertAlmostEqual(self.lua.eval('inst.components.locomotor:GetSpeedMultiplier()'),2.45)
  self.assertEqual(self.lua.eval('inst.components.health:DoDelta(-50)'),-10)
 def test_z_scales_normal_and_planar_once_preserves_returns(self):
  self.assertTrue(self.lua.eval("component:Cast('z')"))
  self.lua.execute('normal,sp=inst.components.combat:CalcDamage(nil,nil)')
  self.assertEqual(self.lua.eval('normal'),51);self.assertEqual(self.lua.eval('sp.planar'),15)
 def test_domain_cast_immediately_creates_field_and_activation_feedback(self):
  self.lua.execute('''
   spawned={}
   SpawnPrefab=function(name)
    spawned[name]=true
    return {entity={SetParent=function()end},Transform={SetPosition=function()end},Remove=function()end}
   end
   inst.entity={}
   component:Cast('x')
  ''')
  self.assertTrue(self.lua.eval('spawned.klbq_kanami_domain_fx'))
  self.assertTrue(self.lua.eval('spawned.klbq_kanami_domain_cast_fx'))
 def test_revive_stats_and_protection_block_attacks(self):
  self.lua.execute('inst.components.health.ForceUpdateHUD=function() hud_health=inst.components.health.currenthealth end')
  self.lua.execute('component:OnDeath();now=60;inst:AddTag("playerghost"); component:Tick();inst:RemoveTag("playerghost");component:OnRespawn()')
  self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),1)
  self.assertEqual(self.lua.eval('inst.components.hunger.p'),.5)
  self.assertEqual(self.lua.eval('inst.components.sanity.p'),1)
  self.assertEqual(self.lua.eval('hud_health'),1)
  self.assertTrue(self.lua.eval('component:IsProtected()'))
  self.assertFalse(self.lua.eval('inst.components.combat:CanAttack({})'))
  self.assertIsNone(self.lua.eval('inst.components.combat:DoAttack({})'))
  self.lua.execute('inst:PushEvent("onattackother",{})')
  self.assertTrue(self.lua.eval('component:IsProtected()'))
 def test_saved_deadline_keeps_remaining_across_new_clock(self):
  self.lua.execute("component:Cast('x');now=12;data=component:OnSave();now=100;component:OnLoad(data)")
  self.assertEqual(self.lua.eval("component:Remaining('x_active')"),18)
  self.assertEqual(self.lua.eval("component:Remaining('x')"),48)
 def test_doom_can_execute_visible_phase_that_rejects_ordinary_attacks(self):
  self.lua.execute('''
   target={components={health={currenthealth=1000,IsDead=function(s) return s.currenthealth<=0 end,SetVal=function(s,n) s.currenthealth=n end},combat={}},
     HasTag=function(s,t) return t=='noattack' end,IsValid=function() return true end,IsInLimbo=function() return false end,
     entity={IsVisible=function() return true end},Transform={GetWorldPosition=function() return 1,0,1 end}}
   ammo={prefab='klbq_ammo_doom',HasTag=function() return true end,components={stackable={StackSize=function() return 1 end}},Remove=function() end}
   container={GetItemInSlot=function(s) return s.ammo end,RemoveItemBySlot=function(s) local a=s.ammo;s.ammo=nil;return a end,ammo=ammo}
   gun={prefab='klbq_finale',components={container=container}}
   inst.components.inventory.GetEquippedItem=function() return gun end
   inst.components.combat.CanTarget=function() return false end
   inst.ForceFacePoint=function() end
   TheNet={GetPVPEnabled=function() return false end}
  ''')
  self.assertTrue(self.lua.eval('component:Shoot(target)'))
  self.assertEqual(self.lua.eval('target.components.health.currenthealth'),0)
  self.assertEqual(self.lua.eval("component:Remaining('shot')"),1.5)
 def test_string_refuses_exit_inside_a_physical_obstacle(self):
  self.lua.execute('''
   Vector3=function(x,y,z) return {x=x,y=y,z=z} end
   TheWorld.Map.IsGroundTargetBlocked=function() return false end
   inst.GetPhysicsRadius=function() return .5 end
   inst.Physics.GetCollisionMask=function() return 31 end
   checkbit=function(a,b) return true end
   obstacle={Physics={IsActive=function() return true end,GetCollisionGroup=function() return 2 end},
      GetPhysicsRadius=function() return 1 end,Transform={GetWorldPosition=function() return 0,0,0 end}}
   TheSim.FindEntities=function() return {obstacle} end
   component:ToggleString()
  ''')
  self.assertFalse(self.lua.eval('component:ToggleString()'))
  self.assertTrue(self.lua.eval('component.state.string'))
 def test_rifle_consumes_one_and_swapping_cannot_bypass_player_cooldown(self):
  self.lua.execute('''
   count=20;spent=0;normalhits=0;planarhits=0;lastplanar=0
   ammo={prefab='klbq_ammo_heart',HasTag=function() return true end,components={stackable={StackSize=function() return count end,
      Get=function() count=count-1;return {Remove=function() spent=spent+1 end} end}}}
   container={GetItemInSlot=function() return ammo end}
   gun={prefab='klbq_finale',components={container=container}}
   inst.components.inventory.GetEquippedItem=function() return gun end
   inst.components.combat.CanTarget=function() return true end;inst.ForceFacePoint=function() end
   target={components={health={currenthealth=1000,IsDead=function(s) return s.currenthealth<=0 end,
      DoDelta=function(s,n) s.currenthealth=math.max(0,s.currenthealth+n);return n end},combat={}},
      PushEvent=function() end,HasTag=function() return false end,IsValid=function() return true end,IsInLimbo=function() return false end,
      entity={IsVisible=function() return true end},Transform={GetWorldPosition=function() return 1,0,1 end}}
   target.components.combat.GetAttacked=function(s,attacker,damage,weapon,stim,sp)
      if sp then planarhits=planarhits+1;lastplanar=sp.planar else normalhits=normalhits+1 end
      target.components.health:DoDelta(-damage-(sp and sp.planar or 0))
      inst:PushEvent('onhitother',{target=target,weapon=weapon,damage=damage,damageresolved=damage,spdamage=sp})
      return true
   end
   component:Cast('z')
  ''')
  self.assertTrue(self.lua.eval('component:Shoot(target)'))
  self.assertEqual(self.lua.eval('spent'),1);self.assertEqual(self.lua.eval('count'),19)
  self.assertEqual(self.lua.eval('planarhits'),1);self.assertEqual(self.lua.eval('lastplanar'),51)
  self.assertAlmostEqual(self.lua.eval('target.components.health.currenthealth'),1000-75-51-(1000-75)*.03*1.5)
  self.lua.execute('gun={prefab="klbq_finale",components={container=container}}')
  self.assertFalse(self.lua.eval('component:Shoot(target)'))
  self.assertEqual(self.lua.eval('spent'),1)
  self.lua.execute('now=1.499')
  self.assertFalse(self.lua.eval('component:Shoot(target)'))
  self.lua.execute('now=1.5')
  self.assertTrue(self.lua.eval('component:Shoot(target)'))
  self.assertEqual(self.lua.eval('spent'),2)
 def test_delayed_attack_keeps_launch_weapon_and_z_snapshot_after_swap(self):
  self.lua.execute('''
   oldweapon={prefab='dynamic',components={weapon={GetDamage=function() return 99 end}}}
   newweapon={prefab='different',components={weapon={GetDamage=function() return 10 end}}}
   inst.components.combat.GetWeapon=function() return newweapon end
   projectile={_klbq_attack_snapshot={power=99,zmult=1.5,weapon=oldweapon}}
   captured=nil
   -- The original method is exercised through the installed wrapper and sees
   -- the immutable projectile snapshot, rather than the new hand equipment.
   component.state.deadlines.z_active=nil
  ''')
  self.lua.execute('result,second=inst.components.combat:DoAttack({},oldweapon,projectile)')
  self.assertEqual(self.lua.eval('result'),'original');self.assertEqual(self.lua.eval('second'),7)
  self.assertEqual(self.lua.eval('projectile._klbq_attack_snapshot.power'),99)
  self.assertEqual(self.lua.eval('captured.power'),99)
  self.assertEqual(self.lua.eval('captured.zmult'),1.5)
  self.assertTrue(self.lua.eval('captured.weapon==oldweapon'))
  self.assertEqual(self.lua.eval('duringattackdamage'),51)
  self.assertIsNone(self.lua.eval('component.attackcontext'))
 def test_string_returns_to_last_safe_point_in_cave_void(self):
  self.lua.execute('''
   Vector3=function(x,y,z) return {x=x,y=y,z=z} end
   TheWorld.Map.IsGroundTargetBlocked=function() return false end
   TheWorld.Map.IsInvalidTileAtPoint=function(s,x) return x==20 end
   inst.GetPhysicsRadius=function() return .5 end
   inst.Transform.GetWorldPosition=function() return 20,0,20 end
   inst.Physics.Teleport=function(_,x,y,z) teleported=x end
   component.state.string=true;component.lastsafe={3,0,3};component:Tick()
  ''')
  self.assertEqual(self.lua.eval('teleported'),3)
if __name__=='__main__':unittest.main(verbosity=2)
