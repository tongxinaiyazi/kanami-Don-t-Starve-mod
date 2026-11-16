"""Lifecycle regressions run the installed game's load/resurrection callbacks."""
import unittest
import zipfile

import test_character_balance as balance
import test_component
from test_review_regressions import vanilla
import test_rifle


class ResurrectionRace(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute("""
            FRAMES=1/30;STRINGS={NAMES={SHENANIGANS='unknown'}}
            inst.ShowHUD=function() end
            inst.sg={currentstate={name='haunt'},statemem={},AddStateTag=function() end}
            inst.components.playercontroller={Enable=function() end}
            scheduled={};requests=0
            inst.DoTaskInTime=function(s,delay,fn,...)
                local args={...};local task={at=now+delay,fn=fn,args=args}
                task.Cancel=function(t) t.cancelled=true end
                table.insert(scheduled,task);return task
            end
            function due()
                local previous=scheduled;scheduled={}
                for _,task in ipairs(previous) do
                    if not task.cancelled and task.at<=now then task.fn(inst,unpack(task.args))
                    else table.insert(scheduled,task) end
                end
            end
            source={prefab='resurrectionstone',valid=true,
                IsValid=function(s) return s.valid end,IsInLimbo=function() return false end,
                HasTag=function() return false end,GetBasicDisplayName=function() return 'stone' end,
                components={}}
        """)
        self.lua.execute(vanilla('prefabs/player_common_extensions.lua', 'local function DoMoveToRezSource(')
                         + '\nNativeMoveToRezSource=DoMoveToRezSource')
        self.lua.execute('DoMoveToRezSource=NativeMoveToRezSource')
        self.lua.execute(vanilla('prefabs/player_common_extensions.lua', 'local function OnRespawnFromGhost(')
                         + '\nNativeRespawnFromGhost=OnRespawnFromGhost')
        self.lua.execute("""
            inst.events.respawnfromghost=function(s,data)
                requests=requests+1;NativeRespawnFromGhost(s,data)
            end
            component:OnDeath();inst:AddTag('playerghost');now=59
            inst:PushEvent('respawnfromghost',{source=source})
        """)

    def test_native_delayed_external_revival_does_not_start_second_automatic_revival(self):
        self.lua.execute('now=60;component:Tick()')
        self.assertEqual(self.lua.eval('requests'), 1)
        self.assertIsNone(self.lua.eval('component.autoreviving'))
        self.assertFalse(self.lua.eval('component:IsProtected()'))

    def test_invalid_native_revival_source_keeps_original_automatic_deadline(self):
        self.lua.execute('source.valid=false;now=59.4;due()')
        self.assertIsNone(self.lua.eval('inst.rezsource'))
        self.assertTrue(self.lua.eval('inst:HasTag("reviving")'))
        self.lua.execute('now=59.9;component:Tick()')
        self.assertEqual(self.lua.eval('requests'), 1)
        self.lua.execute('now=60;component:Tick()')
        self.assertEqual(self.lua.eval('requests'), 2)
        self.assertTrue(self.lua.eval('component.autoreviving'))

    def test_completed_external_revival_cancels_timer_and_protection(self):
        self.lua.execute("inst:RemoveTag('playerghost');component:OnRespawn();now=61;component:Tick()")
        self.assertEqual(self.lua.eval('requests'), 1)
        self.assertIsNone(self.lua.eval('component.state.deadlines.revive'))
        self.assertFalse(self.lua.eval('component:IsProtected()'))


class NativeOceanLoad(unittest.TestCase):
    def setUp(self):
        fixture = balance.CharacterBalance()
        fixture.setUp()
        self.lua = fixture.lua
        self.lua.execute("""
            position={20,0,20};equips.body=bag
            TheWorld.Map.IsVisualGroundAtPoint=function(_,x) return x<10 end
            TheWorld.Map.IsPassableAtPoint=function(_,x) return x<10 end
            TheWorld.Map.IsOceanTileAtPoint=function(_,x) return x>=10 end
            TheWorld.Map.IsInvalidTileAtPoint=function() return false end
            inst.Transform.SetPosition=function(_,x,y,z) position={x,y,z};portalteleports=(portalteleports or 0)+1 end
            inst.SnapCamera=function() end;IsConsole=function() return false end
            Ents={{HasTag=function(_,tag) return tag=='multiplayer_portal' end,
                Transform={GetWorldPosition=function() return 3,0,3 end}}}
            -- MakePlayerCharacter captures the mod's master-init OnLoad before
            -- installing its own native wrapper; EntityScript loads components first.
            inst._OnLoad=inst.OnLoad
            function taskframe(reverse)
                local previous=inst.tasks;inst.tasks={}
                if reverse then for i=#previous,1,-1 do previous[i](inst) end
                else for _,fn in ipairs(previous) do fn(inst) end end
            end
        """)
        self.lua.globals().NativeLoad = self.lua.execute(
            vanilla('prefabs/player_common.lua', 'local function OnLoad(') + '\nreturn OnLoad')

    def load(self, stringed=True):
        self.lua.execute('component:OnLoad({version=2,string=...,remaining={}})', stringed)
        self.lua.execute('NativeLoad(inst,{})')

    def test_upgraded_bag_ocean_load_keeps_position_in_either_native_task_order(self):
        self.load()
        self.lua.execute('taskframe(true);taskframe(false);taskframe(true)')
        self.assertEqual(self.lua.eval('position[1]'), 20)
        self.assertIsNone(self.lua.eval('portalteleports'))
        self.assertTrue(self.lua.eval('component:CanStringWaterWalk()'))
        self.assertIsNone(self.lua.eval('inst.components.drownable.enabled'))

    def test_native_non_string_ocean_rescue_is_unchanged(self):
        self.load(False)
        self.lua.execute('taskframe(true);taskframe(false);taskframe(true)')
        self.assertEqual(self.lua.eval('position[1]'), 3)
        self.assertEqual(self.lua.eval('portalteleports'), 1)
        self.assertIsNone(self.lua.eval('inst.components.drownable.enabled'))

    def test_ocean_guard_restores_existing_disabled_drownable_and_cleans_component_removal(self):
        self.lua.execute('inst.components.drownable.enabled=false')
        self.load()
        self.lua.execute('taskframe(true);taskframe(false);taskframe(true)')
        self.assertFalse(self.lua.eval('inst.components.drownable.enabled'))
        self.lua.execute('inst.components.drownable.enabled=true')
        self.load()
        self.lua.execute('component:OnRemoveFromEntity()')
        self.assertTrue(self.lua.eval('inst.components.drownable.enabled'))


class NativeResolvedHit(unittest.TestCase):
    def setUp(self):
        fixture = test_rifle.Rifle()
        fixture.setUp()
        self.lua = fixture.lua
        with zipfile.ZipFile(balance.GAME) as archive:
            source = archive.read('scripts/components/spdamageutil.lua').decode('utf-8-sig')
        self.lua.execute("package.preload['components/spdamageutil']=function() " + source + ' end')
        self.lua.execute("""
            SpDamageUtil=require('components/spdamageutil')
            inst.components.klbq_kanami=component;inst.prefab='klbq_kanami';inst:AddTag('player')
            inst.events.onhitother=function(s,data) initialresolved=data.damageresolved;component:OnHit(data) end
            component.attackcontext={power=5,zmult=1,weapon=gun}
        """)

    def test_native_full_absorption_does_not_trigger_true_damage_or_passive_cooldown(self):
        self.lua.execute("target.components.health.absorb=1;target.components.combat:GetAttacked(inst,0,gun,nil,{planar=5})")
        self.assertEqual(self.lua.eval('initialresolved'), 0)
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'), 1000)
        self.assertEqual(self.lua.eval('component:Remaining("passive")'), 0)

    def test_native_positive_planar_damage_still_triggers_passive(self):
        self.lua.execute('target.components.combat:GetAttacked(inst,0,gun,nil,{planar=5})')
        self.assertGreater(self.lua.eval('initialresolved'), 0)
        self.assertLess(self.lua.eval('target.components.health.currenthealth'), 995)
        self.assertEqual(self.lua.eval('component:Remaining("passive")'), 1.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
