"""Shared rifle: native Combat/Inventory/Armor/Health paths, no game process."""
import unittest
import zipfile
import test_component
from test_review_regressions import GAME, ROOT, register, vanilla


class Rifle(unittest.TestCase):
    def setUp(self):
        fixture = test_component.Lifecycle(); fixture.setUp(); self.lua = fixture.lua
        path = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/rifle.lua'
        if path.exists():
            self.lua.execute('package.preload[...] = function() ' + path.read_text(encoding='utf-8-sig') + ' end', 'klbq_kanami/rifle')
        register(self.lua)
        self.lua.execute('Health={};Combat={};Inventory={};Armor={}')
        for cls, path, names in [
            ('Health', 'health', ('GetPercent','GetMaxWithPenalty','IsInvincible','IsDead','CanFadeOut','DoDelta','SetVal')),
            ('Combat', 'combat', ('GetAttacked','GetAttacked_Internal')),
            ('Inventory', 'inventory', ('ApplyDamage','DropEverything')),
            ('Armor', 'armor', ('GetAbsorption','GetBonusDamage','TakeDamage')),
        ]:
            for name in names:
                self.lua.execute(vanilla('components/'+path+'.lua', 'function '+cls+':'+name+'('))
        self.lua.execute('''
          math.clamp=function(n,a,b)return math.max(a,math.min(n,b))end
          IsRangedWeapon=function(w)return w and w:HasTag('rangedweapon')end
          CanEntityBecomeCorpse=function()return false end;NotifyPlayerProgress=function()end
          TheWorld.PushEvent=function(s,n,d)worlddeath=(worlddeath or 0)+(n=='entity_death' and 1 or 0)end
          TheWorld.components={charlie_tracker={IsCharlieDefeated=function()return false end}}
          ProfileStatsAdd=function()end
          EquipSlot={Count=function()return 1 end,FromID=function()return 'body' end}
          GetGhostEnabled=function()return true end;GetGameModeProperty=function()return false end
          function modifier()return {Get=function()return 1 end}end
          function makehealth(entity,amount)
            return setmetatable({inst=entity,currenthealth=amount,maxhealth=amount,penalty=0,
              nonlethal_pct=0,absorb=0,playerabsorb=0,nofadeout=true,
              externalabsorbmodifiers={Get=function()return 0 end},
              externalreductionmodifiers={Get=function()return 0 end}}, {__index=Health})
          end
          function makecombat(entity)
            return setmetatable({inst=entity,externaldamagetakenmultipliers=modifier(),
              externaldamagemultipliers=modifier(),ShouldRecoil=function(s,a,w,d)return false,d end,
              GetWeapon=function()return gun end,CanTarget=function()return true end}, {__index=Combat})
          end
          function armor(entity,amount)
            local a=setmetatable({inst=entity,condition=1000,absorb_percent=amount,
              conditionlossmultipliers=modifier(),CanResist=function()return true end,
              SetCondition=function(s,n)s.condition=n end},{__index=Armor})
            return {components={armor=a,inventoryitem={}}},a
          end
          inst.prefab='wilson';inst.components.klbq_kanami=nil;inst._klbq_string=nil;inst.events={}
          inst.components.health=makehealth(inst,150);inst.components.combat=makecombat(inst)
          inst.components.combat.bonusdamagefn=function()return 0 end
          inst.ForceFacePoint=function()end
          inst.components.inventory=setmetatable({inst=inst,equipslots={},itemslots={},maxslots=2,
            GetEquippedItem=function()return gun end,IsItemEquipped=function(s,item)return item==gun end}, {__index=Inventory})
          function equiparmor(who,percent)
            local item,a=armor(who,percent);who.components.inventory.equipslots.body=item;return a
          end
          target={components={},tags={},events={},Transform={GetWorldPosition=function()return 100000,0,100000 end},
            entity={IsVisible=function()return true end},IsValid=inst.IsValid,IsInLimbo=inst.IsInLimbo,
            HasTag=inst.HasTag,PushEvent=inst.PushEvent,AddTag=inst.AddTag,RemoveTag=inst.RemoveTag}
          target.components.health=makehealth(target,1000);target.components.combat=makecombat(target)
          target.components.inventory=setmetatable({inst=target,equipslots={}}, {__index=Inventory})
          count=20;spent=0
          ammo={prefab='klbq_ammo_heart',HasTag=function(s,t)return t=='klbq_ammo' end,
            components={stackable={StackSize=function()return count end,
              Get=function()count=count-1;return {Remove=function()spent=spent+1 end}end}},Remove=function()spent=spent+1 end}
          container={GetItemInSlot=function()return count>0 and ammo or nil end,
            RemoveItemBySlot=function()count=0;return ammo end}
          function newgun()return {prefab='klbq_finale',components={container=container,inventoryitem={},equippable={}},
            HasTag=function(s,t)return t=='klbq_finale' or t=='rangedweapon' end,
            PushEvent=function()end,IsValid=function()return true end}end
          gun=newgun()
          function shoot()return registeredactions.KLBQ_SHOOT.fn({doer=inst,target=target})end
          TheNet.GetPVPEnabled=function()return false end
        ''')

    def test_lock_pauses_without_ammo_or_when_busy_and_releases_when_holstered(self):
        self.lua.execute('''
          inst.components.health:SetVal(10000)
          inst.DoPeriodicTask=function(s,period,fn) tick=fn;return {Cancel=function() canceled=true end} end
          busy=false;inst.sg={HasStateTag=function(s,t) return t=="busy" and busy end}
          count=0
          assert(registeredactions.KLBQ_SHOOT_LOCK.fn({doer=inst,target=target}))
          assert(spent==0 and inst._klbq_rifle_lock)
          count=3;busy=true;now=1;tick();assert(spent==0)
          busy=false;tick();assert(spent==1)
          local old=gun;gun=nil;inst:PushEvent("unequip",{item=old})
          assert(canceled and inst._klbq_rifle_lock==nil)
          now=10;tick();assert(spent==1)
        ''')

    def test_lock_reuses_shot_cooldown_and_clears_on_phase_or_manual_retarget(self):
        self.lua.execute('''
          inst.components.health:SetVal(10000)
          inst.DoPeriodicTask=function(s,period,fn) tick=fn;return {Cancel=function() canceled=true end} end
          subscriptions={}
          inst.ListenForEvent=function(s,event,fn,source)
            if source then subscriptions[event]=fn else s.events[event]=fn end
          end
          inst.RemoveEventCallback=function(s,event,fn,source)
            if source then subscriptions[event]=nil else s.events[event]=nil end
          end
          rifle=require('klbq_kanami/rifle')
          target.prefab='alterguardian_phase1'
          assert(registeredactions.KLBQ_SHOOT_LOCK.fn({doer=inst,target=target}))
          assert(spent==1)
          now=1;tick()
          assert(spent==1)
          now=1.5;tick()
          assert(spent==2)
          subscriptions.phasetransition(target)
          assert(canceled and inst._klbq_rifle_lock==nil)
          now=1.6;registeredactions.KLBQ_SHOOT_LOCK.fn({doer=inst,target=target})
          assert(inst._klbq_rifle_lock and spent==2)
          local second={components=target.components,HasTag=target.HasTag,tags={},IsValid=target.IsValid,
            IsInLimbo=target.IsInLimbo,entity=target.entity}
          registeredactions.KLBQ_SHOOT.fn({doer=inst,target=second})
          assert(inst._klbq_rifle_lock==nil and spent==2)
        ''')

    def test_fate_shot_uses_configured_max_health_fraction(self):
        for fraction in (.03, .05, .1, .2):
            with self.subTest(fraction=fraction):
                self.setUp()
                self.lua.execute('require("klbq_kanami/rules").ConfigureFate(...)', fraction)
                self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .01 end;target.components.health.maxhealth=20000;target.components.health.currenthealth=20000")
                self.assertTrue(self.lua.eval('shoot()'))
                self.assertEqual(self.lua.eval('target.components.health.currenthealth'),20000*(1-fraction))
                self.assertEqual(self.lua.eval('count'),19)

    def test_generic_heart_measures_target_loss_then_uses_native_shooter_armor(self):
        self.lua.execute('enemyarmor=equiparmor(target,.8);selfarmor=equiparmor(inst,.8);target.components.health.absorb=.5')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertAlmostEqual(self.lua.eval('target.components.health.currenthealth'),995)
        self.assertAlmostEqual(self.lua.eval('inst.components.health.currenthealth'),149)
        self.assertAlmostEqual(self.lua.eval('enemyarmor.condition'),960)
        self.assertAlmostEqual(self.lua.eval('selfarmor.condition'),996)
        self.assertEqual(self.lua.eval('spent'),1)

    def test_fate_backlash_uses_uncapped_target_loss_and_shooter_armor(self):
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;selfarmor=equiparmor(inst,.8);target.components.health.maxdamagetakenperhit=-40;target.components.health.absorb=.99")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),700)
        self.assertAlmostEqual(self.lua.eval('inst.components.health.currenthealth'),90)
        self.assertAlmostEqual(self.lua.eval('selfarmor.condition'),760)

    def test_target_cap_bypass_does_not_disable_generic_shooters_backlash_cap(self):
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;selfarmor=equiparmor(inst,.8);target.components.health.maxdamagetakenperhit=-1;inst.components.health.maxdamagetakenperhit=-8;inst.components.health.absorb=.5")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),700)
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),142)
        self.assertAlmostEqual(self.lua.eval('selfarmor.condition'),760)
        self.assertEqual(self.lua.eval('inst.components.health.maxdamagetakenperhit'),-8)
        self.assertIsNone(self.lua.eval('inst.components.health._ignore_maxdamagetakenperhit'))

    def test_actual_rifle_first_two_ammo_bypass_private_time_gates(self):
        self.lua.execute('''
          target.components.combat.GetAttacked=function()return false end
          target.components.combat.GetAttacked_Internal=function()return false end
          target.components.health.DoDelta=function()return 0 end
          target.components.health.deltamodifierfn=function()return 0 end
          target.components.health.maxdamagetakenperhit=-1
        ''')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),950)
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;now=1.5")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),650)
        self.assertEqual(self.lua.eval('spent'),2)

    def test_redirected_receiver_loss_drives_generic_backlash_and_damage_number(self):
        self.lua.execute('''
          receiver={components={},events={},tags={},HasTag=target.HasTag,IsValid=target.IsValid,
            IsInLimbo=target.IsInLimbo,PushEvent=target.PushEvent}
          receiver.components.health=makehealth(receiver,1000)
          receiver.components.combat=makecombat(receiver)
          receiver.components.health.maxdamagetakenperhit=-1
          receiver.components.health.DoDelta=function()return 0 end
          receiver.components.combat.GetAttacked_Internal=function()return false end
          target.components.health.invincible=true
          target.components.combat.redirectdamagefn=function()return receiver end
          selfarmor=equiparmor(inst,.8)
          inst.events.klbq_shot=function(s,data)shotdamage=data.damage end
          inst._klbq_hitseq={set=function(s,v)s.v=v end,value=function(s)return s.v or 0 end}
          inst._klbq_hitdamage={set=function(s,v)hitnumber=v end}
          inst._klbq_hittarget={set=function()end}
        ''')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),1000)
        self.assertEqual(self.lua.eval('receiver.components.health.currenthealth'),950)
        self.assertAlmostEqual(self.lua.eval('inst.components.health.currenthealth'),140)
        self.assertAlmostEqual(self.lua.eval('hitnumber'),50)
        self.assertAlmostEqual(self.lua.eval('shotdamage'),50)

    def test_backlash_does_not_reapply_shooters_outgoing_bonus(self):
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;target.components.health.currenthealth=20;inst.components.combat.bonusdamagefn=function()return 900 end")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),130)

    def test_all_player_hook_blocks_empty_rifle_melee_and_preserves_other_weapons(self):
        self.lua.execute('''
          ACTIONS={ATTACK={id='ATTACK'}}
          inst.replica={inventory=inst.components.inventory}
          inst.GetBufferedAction=function()return {action=ACTIONS.ATTACK}end
          inst.ClearBufferedAction=function()cleared=(cleared or 0)+1 end
          inst.PerformBufferedAction=function()buffered=(buffered or 0)+1;return 'buffered',7 end
          inst.components.combat.DoAttack=function()melee=(melee or 0)+1;return 'melee',8 end
          inst.components.combat.CanAttack=function()return true,'native-reason' end
          count=0;playerpostinit(inst);wrapped=inst.components.combat.DoAttack;playerpostinit(inst)
        ''')
        self.assertFalse(self.lua.eval('inst.components.combat:CanAttack(target)'))
        self.lua.execute('inst.components.combat:DoAttack(target)')
        self.assertIsNone(self.lua.eval('melee'))
        self.assertFalse(self.lua.eval('inst:PerformBufferedAction()'))
        self.assertEqual(self.lua.eval('cleared'),1)
        self.assertIsNone(self.lua.eval('buffered'))
        self.assertTrue(self.lua.eval('wrapped==inst.components.combat.DoAttack'))
        self.lua.execute("gun=nil;a,b=inst.components.combat:DoAttack(target);c,d=inst:PerformBufferedAction();allowed,reason=inst.components.combat:CanAttack(target)")
        self.assertTrue(self.lua.eval('inst.components.combat:CanAttack(target)'))
        self.assertTrue(self.lua.eval('allowed'))
        self.assertEqual(self.lua.eval('reason'),'native-reason')
        self.assertEqual(self.lua.eval('a'),'melee');self.assertEqual(self.lua.eval('b'),8)
        self.assertEqual(self.lua.eval('c'),'buffered');self.assertEqual(self.lua.eval('d'),7)

    def test_overkill_reflects_only_remaining_life_not_requested_damage(self):
        self.lua.execute("ammo.prefab='klbq_ammo_fate';math.random=function()return .5 end;target.components.health.currenthealth=10")
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),0)
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),140)

    def test_invincible_target_costs_ammo_but_has_no_backlash(self):
        self.lua.execute('target.components.health.invincible=true')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),1000)
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),150)
        self.assertEqual(self.lua.eval('spent'),1)

    def test_generic_player_cooldown_survives_gun_swap_and_has_no_range_cap(self):
        self.assertTrue(self.lua.eval('shoot()'))
        self.lua.execute('gun=newgun();now=1.499')
        self.assertFalse(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('spent'),1)
        self.lua.execute('now=1.5')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('spent'),2)

    def test_invisible_ghost_and_empty_cannot_shoot_or_spend(self):
        self.lua.execute('target.entity.IsVisible=function()return false end')
        self.assertFalse(self.lua.eval('shoot()'))
        self.lua.execute("target.entity.IsVisible=function()return true end;inst:AddTag('playerghost')")
        self.assertFalse(self.lua.eval('shoot()'))
        self.lua.execute("inst:RemoveTag('playerghost');count=0")
        self.assertFalse(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('spent'),0)

    def test_protected_kanami_cannot_fire_even_if_rifle_remains_equipped(self):
        self.lua.execute('inst.components.klbq_kanami=component;component.state.deadlines.protect=30;component.state.deadlines.passive=999;inst._klbq_string={set=function()end,value=function()return false end}')
        self.assertFalse(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('spent'),0)
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),1000)
        self.lua.execute('now=30')
        self.assertTrue(self.lua.eval('shoot()'))

    def test_client_cannot_consume_ammo_or_apply_damage(self):
        self.lua.execute('TheWorld.ismastersim=false')
        self.assertFalse(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('spent'),0)
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),1000)

    def test_doom_native_death_state_drops_items_without_removing_shooter(self):
        # Execute the actual native death state and native inventory drop loop.
        with zipfile.ZipFile(GAME) as archive:
            source=archive.read('scripts/stategraphs/SGwilson.lua').decode('utf-8-sig')
        start=source.rfind('    State{',0,source.index('        name = "death",'))
        end=source.index('\n    State{',start+10)
        state=source[start:end].rstrip().removesuffix(',')
        self.lua.execute('''
          State=function(v)return v end;TimeEvent=function()return {}end;FrameEvent=TimeEvent
          EventHandler=function()return {}end;FRAMES=1/30
          ClearStatusAilments=function()end;ForceStopHeavyLifting=function()end
        ''')
        self.lua.execute(vanilla('stategraphs/SGwilson.lua','local function DropAllItemsForDeath(')+'\n_G.DropAllItemsForDeath=DropAllItemsForDeath')
        self.lua.globals().deathstate=self.lua.execute('return '+state)
        self.lua.execute('''
          ammo.prefab='klbq_ammo_doom';target.tags.noattack=true
          inst.components.combat.CanTarget=function()return false end
          selfarmor=equiparmor(inst,.99);inst.components.health.invincible=true
          inst.components.inventory.equipslots.hands=gun
          kept={components={inventoryitem={keepondeath=true}}};dropped={components={inventoryitem={}}}
          inst.components.inventory.itemslots={dropped,kept};drops={}
          inst.components.inventory.DropItem=function(s,item) drops[item]=true end
          inst.ClearBufferedAction=function()end
          inst.components.locomotor.Stop=function()end;inst.components.locomotor.Clear=function()end
          inst.components.rider={IsRiding=function()return false end}
          inst.components.burnable={Extinguish=function()end}
          inst.AnimState.PlayAnimation=function(s,n)deathanimation=n end
          inst.SoundEmitter={PlaySound=function()end}
          inst.sg={statemem={},mem={},HasStateTag=function()return false end,ClearBufferedEvents=function()end}
          inst.Remove=function()error('shooter must not be removed')end
          inst.events.death=function(s,data)s.deathcause=data.cause;shooter_deaths=(shooter_deaths or 0)+1;deathstate.onenter(s,data)end
        ''')
        self.assertTrue(self.lua.eval('shoot()'))
        self.assertEqual(self.lua.eval('target.components.health.currenthealth'),0)
        self.assertEqual(self.lua.eval('inst.components.health.currenthealth'),0)
        self.assertEqual(self.lua.eval('shooter_deaths'),1)
        self.assertEqual(self.lua.eval('deathanimation'),'death')
        self.assertTrue(self.lua.eval('drops[gun] and drops[dropped]'))
        self.assertFalse(bool(self.lua.eval('drops[kept]')))
        self.assertEqual(self.lua.eval('worlddeath'),2)


if __name__=='__main__':unittest.main(verbosity=2)
