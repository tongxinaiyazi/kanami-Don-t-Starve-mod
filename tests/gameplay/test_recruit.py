import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime


class Recruit(unittest.TestCase):
    """Exercise the installed game's real leader/follower lifecycle in Lua 5.1."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            now = 0
            GetTime = function() return now end
            math.clamp = function(v,lo,hi) return math.max(lo,math.min(v,hi)) end
            IsTableEmpty = function(t) return next(t) == nil end
            NotifyPlayerProgress = function() end
            ProfileStatsAdd = function() end
            AwardPlayerAchievement = function() end
            TheWorld = {ismastersim=true, components={}}
            TheNet = {GetPVPEnabled=function() return false end}
            IsEntityDead = function(inst) return inst.components.health:IsDead() end
            local function Net() return {set=function(self,v) self.v=v end,value=function(self) return self.v end} end
            net_entity=Net;net_bool=Net;net_float=Net
            TUNING = {ACHIEVEMENT_PIG_POSSE_SIZE=1000,ACHIEVEMENT_ROCKY_POSSE_SIZE=1000,FOLLOWER_REFOLLOW_DIST_SQ=1600}
            EntityScript = {is_instance=function() return false end}
            SpawnPrefab = function() error('recruitment must not spawn food or rewards') end
        ''')
        with zipfile.ZipFile("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip") as source:
            self.lua.execute(source.read('scripts/class.lua').decode())
            self.lua.globals().package.loaded['util/sourcemodifierlist'] = self.lua.execute(
                source.read('scripts/util/sourcemodifierlist.lua').decode())
            for name in ('leader', 'follower'):
                self.lua.globals()['Native' + name.title()] = self.lua.execute(
                    source.read('scripts/components/' + name + '.lua').decode())
            self.lua.globals().package.loaded['components/spdamageutil'] = self.lua.execute(
                source.read('scripts/components/spdamageutil.lua').decode())
            self.lua.globals().NativeCombat = self.lua.execute(source.read('scripts/components/combat.lua').decode())
            self.lua.globals().NativeCombatReplica = self.lua.execute(source.read('scripts/components/combat_replica.lua').decode())
            spider = source.read('scripts/prefabs/spider.lua').decode()
            self.spider_ai = self.lua.execute(spider[spider.index('local function IsSpiderAlly'):spider.index('local function BasicWakeCheck')] + '\nreturn {Retarget=NormalRetarget,Keep=keeptargetfn}')
            merm = source.read('scripts/prefabs/merm.lua').decode()
            self.merm_ai = self.lua.execute(merm[merm.index('local function FindInvaderFn'):merm.index('local DECIDROOTTARGET_MUST_TAGS')] + '\nreturn {Retarget=RetargetFn,Keep=KeepTargetFn}')
        self.lua.execute('''
            function Entity(prefab, tags)
                local s = {prefab=prefab,tags=tags or {},components={},events={},tasks={},counts={},valid=true,userid='KU_'..prefab}
                s.IsValid=function(self) return self.valid end
                s.IsInLimbo=function(self) return self.tags.INLIMBO or false end
                s.HasTag=function(self,tag) return self.tags[tag] or false end
                s.HasAnyTag=function(self,...) for _,tag in ipairs({...}) do if self:HasTag(tag) then return true end end;return false end
                s.GetPosition=function() return {x=0,y=0,z=0} end
                s.entity={IsValid=function() return true end,IsVisible=function() return true end}
                s.IsAsleep=function() return false end
                s.GetDistanceSqToInst=function() return 0 end
                s.ListenForEvent=function(self,event,fn,source)
                    if not source then self.events[event]=self.events[event] or {};self.events[event][fn]=true end
                end
                s.RemoveEventCallback=function(self,event,fn,source)
                    if not source and self.events[event] then self.events[event][fn]=nil end
                end
                s.PushEvent=function(self,event,data)
                    self.counts[event]=(self.counts[event] or 0)+1
                    for fn in pairs(self.events[event] or {}) do fn(self,data) end
                end
                s.DoTaskInTime=function(self,delay,fn,...)
                    local task={delay=delay,fn=fn,args={...},cancelled=false}
                    task.Cancel=function(t) t.cancelled=true end
                    table.insert(self.tasks,task)
                    return task
                end
                s.replica={follower={SetLeader=function() end,SetItemOwner=function() end,GetLeader=function() return s.components.follower and s.components.follower:GetLeader() end}}
                s.components.health={IsDead=function() return s.dead or false end}
                s.replica.combat=NativeCombatReplica(s)
                s.replica.combat._attackrange:set(3)
                s.replica.combat._ispanic:set(false)
                s.components.combat=setmetatable({inst=s,DropTarget=function(self) self.target=nil;s.replica.combat:SetTarget(nil) end},{__index=NativeCombat})
                return s
            end
            function Owner(name)
                local s=Entity(name or 'kanami',{player=true,character=true});s.isplayer=true
                s.components.leader=NativeLeader(s)
                return s
            end
            function Target(name)
                local s=Entity(name or 'pigman')
                s.components.follower=NativeFollower(s)
                if not string.match(s.prefab,'^spider') then s.components.follower.maxfollowtime=480 end
                s.components.trader={enabled=true,onaccept=function() error('never replay food/trade side effects') end}
                return s
            end
            owner=Owner();target=Target()
        ''')
        path = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/recruit.lua'
        # A missing module is deliberately represented as an inert capability so
        # the red run fails on missing gameplay behavior, rather than import IO.
        self.module = self.lua.execute(path.read_text(encoding='utf-8-sig')) if path.exists() else self.lua.eval('{Apply=function() return false end}')
        self.lua.globals().Recruit = self.module

    def runlua(self, expression):
        return self.lua.eval(expression)

    def test_hires_native_food_recruits_without_materials_or_trade_side_effects(self):
        for name in ('pigman', 'bunnyman', 'rocky', 'catcoon', 'gnarwail', 'merm', 'mermguard'):
            with self.subTest(prefab=name):
                self.lua.execute('target=Target(...)', name)
                self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
                self.assertTrue(self.runlua('target.components.follower:GetLeader()==owner'))
                self.assertTrue(self.runlua('owner.components.leader:IsFollower(target)'))
                self.assertEqual(self.runlua('target.components.follower.targettime'), 480)

    def test_spiders_are_never_recruited_by_the_domain(self):
        for name in ('spider', 'spider_warrior', 'spider_hider', 'spider_spitter', 'spider_dropper', 'spider_moon', 'spider_healer', 'spider_water'):
            with self.subTest(prefab=name):
                self.lua.execute('target=Target(...)', name)
                self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
                self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))
                self.assertIsNone(self.runlua('target.components.follower.targettime'))
                self.assertIsNone(self.runlua('target.components.follower.maxfollowtime'))
                self.assertIsNone(self.runlua('target.components.follower.neverexpire'))
        self.assertFalse(self.runlua("owner:HasTag('spiderwhisperer')"))
        self.assertFalse(self.runlua("owner:HasTag('merm')"))

    def test_quarter_second_scans_do_not_repeat_recruitment_or_loyalty_events(self):
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.lua.execute('for i=1,120 do now=i*.25;Recruit.Apply(owner,target) end')
        self.assertEqual(self.runlua('target.counts.startfollowing'), 1)
        self.assertEqual(self.runlua('target.counts.gainloyalty'), 1)
        self.assertEqual(self.runlua('owner.counts.makefriend'), 1)
        self.assertEqual(self.runlua('target.components.follower.targettime'), 480)
        self.lua.execute('now=240;Recruit.Apply(owner,target)')
        self.assertEqual(self.runlua('target.components.follower.targettime'), 720)
        self.assertEqual(self.runlua('target.counts.gainloyalty'), 2)
        self.assertEqual(self.runlua('target.counts.startfollowing'), 1)

    def test_legacy_domain_spiders_are_released_without_taking_another_players_followers(self):
        self.lua.execute("target=Target('spider');owner.components.leader:AddFollower(target)")
        self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
        self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))
        self.lua.execute("other=Owner('webber');target=Target('spider');other.components.leader:AddFollower(target)")
        self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
        self.assertTrue(self.runlua('target.components.follower:GetLeader()==other'))

    def test_after_domain_stops_native_loyalty_expires_without_removing_creature(self):
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.lua.execute('''
            now=480
            local task=target.components.follower.task
            task.fn(target,unpack(task.args))
        ''')
        self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))
        self.assertEqual(self.runlua('owner.components.leader.numfollowers'), 0)
        self.assertTrue(self.runlua('target:IsValid()'))
        self.assertEqual(self.runlua('target.counts.loseloyalty'), 1)

    def test_native_save_and_cached_player_rejoin_preserve_ordinary_follower(self):
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.lua.execute('''
            now=12;data=target.components.follower:OnSave()
            restored=Target('pigman');restored.components.follower:OnLoad(data)
            restored.components.follower.cached_player_join_fn(TheWorld,owner)
        ''')
        self.assertEqual(self.runlua('data.time'), 468)
        self.assertTrue(self.runlua('restored.components.follower:GetLeader()==owner'))
        self.assertEqual(self.runlua('restored.components.follower.targettime'), 480)

    def test_never_steals_existing_player_npc_or_item_leaders(self):
        for code in ("other=Owner('wilson')", "other=Entity('spiderqueen')", "other=Entity('beefalobell')"):
            with self.subTest(leader=code):
                self.lua.execute(code + ';target=Target();target.components.follower:SetLeader(other)')
                self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
                self.assertTrue(self.runlua('target.components.follower.leader==other'))
        self.lua.execute("target=Target();target.components.follower:CachePlayerLeader('KU_offline',300)")
        self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
        self.assertIsNone(self.runlua('target.components.follower.leader'))
        self.lua.execute("target=Target();target.components.follower.leader=Entity('leash_item');target.components.follower.itemowner=owner")
        self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))

    def test_generic_followers_boss_parts_pets_cattle_and_unverified_mod_units_are_not_hireable(self):
        for name in ('spiderqueen', 'beequeen', 'bee', 'shadowtentacle', 'shadowworker', 'beefalo', 'babybeefalo', 'smallbird', 'abigail', 'merm_lunar', 'mermguard_lunar', 'merm_shadow', 'mermguard_shadow', 'mod_mercenary'):
            with self.subTest(prefab=name):
                self.lua.execute("target=Target(...);target.tags.hireable=true", name)
                self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
                self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))

    def test_guard_werepig_disabled_trader_and_royal_candidates_are_not_hired(self):
        cases = (
            "target=Target('pigguard')",
            "target=Target('pigman');target.tags.guard=true",
            "target=Target('pigman');target.tags.werepig=true",
            "target=Target('pigman');target.components.trader.enabled=false",
            "target=Target('pigman');target.components.trader=nil",
            "target=Target('mermguard');target.king=Entity('mermking')",
            "target=Target('merm');TheWorld.components.mermkingmanager={IsCandidate=function() return true end}",
        )
        for code in cases:
            with self.subTest(condition=code):
                self.lua.execute('TheWorld.components={};' + code)
                self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
                self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))

    def test_ordinary_merm_does_not_grant_wurt_skills_or_overwrite_native_fields(self):
        self.lua.execute("target=Target('merm');target.components.follower.maxfollowtime=960;owner.components.leader.loyaltyeffectiveness=2")
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.assertEqual(self.runlua('target.components.follower.maxfollowtime'), 960)
        self.assertEqual(self.runlua('target.components.follower.targettime'), 960)
        self.assertFalse(self.runlua("owner:HasTag('merm')"))
        self.assertIsNone(self.runlua('owner.components.skilltreeupdater'))

    def test_native_leader_change_clears_hostility_toward_new_leader(self):
        self.lua.execute('target.components.combat.target=owner')
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.assertIsNone(self.runlua('target.components.combat.target'))

    def test_wakes_new_recruit_once_without_overriding_later_sleep_cycles(self):
        self.lua.execute('''
            wakes=0
            target.components.sleeper={asleep=true,IsAsleep=function(self) return self.asleep end,
                WakeUp=function(self) self.asleep=false;wakes=wakes+1 end}
        ''')
        self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
        self.assertEqual(self.runlua('wakes'), 1)
        self.lua.execute('target.components.sleeper.asleep=true;now=.25;Recruit.Apply(owner,target)')
        self.assertTrue(self.runlua('target.components.sleeper:IsAsleep()'))
        self.assertEqual(self.runlua('wakes'), 1)

    def test_native_spider_and_merm_ai_cannot_retarget_kanami_after_recruitment(self):
        self.lua.execute('''
            TUNING.SPIDER_TARGET_DIST=10;TUNING.SPIDER_INVESTIGATETARGET_DIST=10
            TUNING.MERM_DEFEND_DIST=10;TUNING.MERM_GUARD_DEFEND_DIST=10;TUNING.MERM_TARGET_DIST=10
            SpringCombatMod=function(n) return n end
            FindEntity=function(inst,radius,fn) if fn(owner,inst) then return owner end end
        ''')
        for name, ai in (('merm', self.merm_ai), ('mermguard', self.merm_ai)):
            with self.subTest(prefab=name):
                self.lua.execute("target=Target(...);target.components.knownlocations={GetLocation=function() return nil end}", name)
                self.assertTrue(self.runlua('target.components.combat:CanTarget(owner)'))
                self.assertIsNotNone(ai.Retarget(self.lua.globals().target))
                self.assertTrue(self.runlua('Recruit.Apply(owner,target)'))
                self.assertTrue(self.runlua('target.components.combat:IsAlly(owner)'))
                self.assertFalse(self.runlua('target.components.combat:CanTarget(owner)'))
                self.assertIsNone(ai.Retarget(self.lua.globals().target))
                self.assertFalse(ai.Keep(self.lua.globals().target, self.lua.globals().owner))

    def test_authority_liveness_and_minigame_boundaries(self):
        for code in ('TheWorld.ismastersim=false', 'owner.dead=true', 'target.dead=true', 'target.valid=false', 'target.tags.INLIMBO=true', 'owner.tags.playerghost=true', 'owner.components.minigame_participator={}'):
            with self.subTest(condition=code):
                self.lua.execute('TheWorld.ismastersim=true;owner=Owner();target=Target();' + code)
                self.assertFalse(self.runlua('Recruit.Apply(owner,target)'))
                self.assertIsNone(self.runlua('target.components.follower:GetLeader()'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
