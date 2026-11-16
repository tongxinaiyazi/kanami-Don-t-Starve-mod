"""Exercise the installed game's actual action picker, including hostile routing."""
import unittest
import zipfile
import test_component
from test_review_regressions import register, vanilla, GAME


class Actions(unittest.TestCase):
    def setUp(self):
        fixture=test_component.Lifecycle();fixture.setUp();self.lua=fixture.lua
        register(self.lua)
        self.lua.execute('''
          EQUIPSLOTS={HANDS='hands'};CONTROL_FORCE_INSPECT=1;CONTROL_FORCE_ATTACK=2
          ACTIONS={ATTACK={id='ATTACK',priority=2},LOOKAT={id='LOOKAT',priority=-3,ghost_valid=true},
            HAUNT={id='HAUNT',priority=0,ghost_valid=true,ghost_exclusive=true}}
          EntityScript={};Vector3={};inst.prefab='klbq_kanami';inst:AddTag('idle')
          inst._klbq_string:set(false)
          inst.components.playercontroller={IsControlPressed=function(s,c)return control==c end}
          gun={HasTag=function(s,t)return t=='klbq_finale' end,IsValid=function()return true end}
          inst.replica={inventory={GetActiveItem=function()return active end,
              GetEquippedItem=function()return gun end},combat={CanTarget=function()return true end}}
          target={replica={health={},combat={}},entity={IsVisible=function()return true end},
            HasTag=function(s,t)return t=='inspectable' or t=='hostile' and hostile end,
            is_a=function(s,t)return t==EntityScript end}
          target.CollectActions=function(s,kind,doer,actions,right)
            if kind=='SCENE' then actions[#actions+1]=ACTIONS.HAUNT;actions[#actions+1]=ACTIONS.LOOKAT end
          end
          gun.CollectActions=function(s,kind,doer,t,actions,right)
            componentactions.EQUIPPEDinventoryitem(s,doer,t,actions,right)
          end
          BufferedAction=function(doer,t,action,item)return {action=action,invobject=item,target=t} end
        ''')
        with zipfile.ZipFile(GAME) as z:
            picker=self.lua.execute(z.read('scripts/components/playeractionpicker.lua').decode('utf-8-sig'))
        self.lua.globals().Picker=picker
        self.lua.globals().defaultfilter=self.lua.execute(
            vanilla('prefabs/player_common.lua','local function PlayerActionFilter(')+'\nreturn PlayerActionFilter')
        self.lua.execute('p=Picker(inst);hooks.playeractionpicker(p);p:PushActionFilter(defaultfilter,-99)')

    def test_hostile_mouse_route_converts_native_attack_to_rifle_shot(self):
        self.lua.execute('hostile=true;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'KLBQ_SHOOT')
        self.assertTrue(self.lua.eval('result[1].invobject==gun'))

    def test_force_attack_route_uses_rifle_without_melee(self):
        self.lua.execute('control=CONTROL_FORCE_ATTACK;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'KLBQ_SHOOT')
        self.assertTrue(self.lua.eval('result[1].invobject==gun'))

    def test_non_kanami_native_hostile_and_equipped_routes_use_rifle(self):
        self.lua.execute("inst.prefab='wilson';inst._klbq_string=nil;hooks.playeractionpicker(p);hostile=true")
        self.lua.execute('result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'KLBQ_SHOOT')
        self.lua.execute('hostile=false;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'KLBQ_SHOOT')

    def test_non_kanami_living_and_ghost_keep_native_filters(self):
        self.lua.execute("inst.prefab='wilson';inst._klbq_string=nil;hooks.playeractionpicker(p)")
        self.lua.execute('target.replica.health=nil;target.replica.combat=nil;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'LOOKAT')
        self.lua.execute('inst:AddTag("playerghost");p:PushActionFilter(function(i,a)return a.ghost_valid end,99);result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'HAUNT')

    def test_living_player_never_gets_haunt_on_rocks(self):
        self.lua.execute('target.replica.health=nil;target.replica.combat=nil;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'LOOKAT')

    def test_ghost_retains_native_haunt_and_cannot_shoot(self):
        self.lua.execute('inst:AddTag("playerghost");p:PushActionFilter(function(i,a)return a.ghost_valid end,99);result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'HAUNT')

    def test_inspect_and_pause_filters_remain_authoritative(self):
        self.lua.execute('hostile=true;control=CONTROL_FORCE_INSPECT;result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('result[1].action.id'),'LOOKAT')
        self.lua.execute('control=nil;p:PushActionFilter(function()return false end,999);result=p:GetLeftClickActions({},target)')
        self.assertEqual(self.lua.eval('#result'),0)


if __name__=='__main__':unittest.main(verbosity=2)
