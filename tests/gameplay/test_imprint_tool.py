"""Imprint item behavior against installed DST Tool, Trader and finite uses.

Only engine entities/rendering/network transports are substituted; upgrades run
through the native Trader and, where relevant, native GIVE/BufferedAction.
"""
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/python-deps"))
from lupa.lua51 import LuaRuntime

SCRIPTS = ROOT / "mods/klbq_kanami/scripts"
GAMEZIP = Path("E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")


class ImprintTool(unittest.TestCase):
    def setUp(self):
        paths = ("components/klbq_imprint.lua", "klbq_kanami/imprint.lua", "prefabs/klbq_imprint_tool.lua")
        self.assertTrue(all((SCRIPTS / p).is_file() for p in paths), "印刻工具实现尚不存在")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAMEZIP) as archive:
            self.native = {p: archive.read("scripts/" + p + ".lua").decode("utf-8-sig")
                           for p in ("class", "components/tool", "components/trader", "components/finiteuses",
                                     "components/stackable", "components/workable", "bufferedaction", "actions",
                                     "componentactions", "stategraphs/SGwilson", "stategraphs/SGwilson_client")}
        self.lua.execute(self.native["class"])
        self.lua.execute("""
            TUNING={STACK_SIZE_MEDITEM=20}; EQUIPSLOTS={HANDS='hands'};MAXUINT=4294967295
            TheWorld={ismastersim=true}; TheNet={IsDedicated=function()return false end}
            TOOLACTIONS={CHOP=true,MINE=true,DIG=true,HAMMER=true}
            ACTIONS={}; for _,id in ipairs({'CHOP','MINE','DIG','HAMMER','GIVE'}) do ACTIONS[id]={id=id} end
            Action=function(v) return v end
            ActionHandler=function(action,state) return {action=action,state=state} end
            Asset=function(t,p)return {type=t,file=p}end
            Prefab=function(n,f,a)return {name=n,fn=f,assets=a}end
            MakeInventoryPhysics=function()end; MakeInventoryFloatable=function()end; MakeHauntableLaunch=function()end
            local entities={};local guid=0
            net_bool=function(id,name,dirty)
                assert(not entities[id].pristine, 'network flag created after pristine')
                return {current=false,set=function(s,v)s.current=v end,value=function(s)return s.current end}
            end
            function MakeEntity()
                guid=guid+1
                local e={GUID=guid,components={},replica={},tags={},events={},x=0,leds={}}
                entities[guid]=e
                e.entity=setmetatable({GetParent=function()return e.parent end}, {__index=function(_,k)
                    if k=='SetPristine' then return function()e.pristine=true end end
                    return function()end
                end})
                e.AnimState=setmetatable({
                    OverrideMultColour=function(_,r,g,b,a,...)
                        assert(type(r)=='number' and type(g)=='number' and type(b)=='number' and type(a)=='number'
                            and select('#',...)==0,'OverrideMultColour accepts only four numbers')
                    end,
                    SetSymbolMultColour=function(_,name,r,g,b,a,...)
                        assert(type(name)=='string' and type(r)=='number' and type(g)=='number'
                            and type(b)=='number' and type(a)=='number' and select('#',...)==0,
                            'SetSymbolMultColour requires a symbol and four numbers')
                        e.leds[name]={r,g,b,a}
                    end,
                    OverrideSymbol=function(_,target,build,source)e.swapsymbol={target,build,source}end},
                    {__index=function()return function()end end})
                e.Transform={GetWorldPosition=function()return e.x,0,0 end}
                e.IsValid=function(s)return not s.removed end
                e.IsInLimbo=function(s)return s:HasTag('INLIMBO') end
                e.Remove=function(s)s.removed=true;s:PushEvent('onremove')end
                e.GetPosition=function(s)return {x=s.x,y=0,z=0}end
                e.GetDistanceSqToInst=function(s,t)return (s.x-t.x)^2 end
                e.GetDisplayName=function()return '印刻工具' end
                e.OnUsedAsItem=function()end
                e.AddTag=function(s,t)s.tags[t]=true end
                e.RemoveTag=function(s,t)s.tags[t]=nil end
                e.HasTag=function(s,t)return s.tags[t]==true end
                e.HasAnyTag=function(s,...)for _,t in ipairs({...})do if s:HasTag(t)then return true end end return false end
                e.ListenForEvent=function(s,n,f)
                    s.events[n]=s.events[n] or {};table.insert(s.events[n],f)
                end
                e.RemoveEventCallback=function(s,n,f)
                    for i=#(s.events[n]or{}),1,-1 do
                        if s.events[n][i]==f then table.remove(s.events[n],i)end
                    end
                end
                e.PushEvent=function(s,n,d)
                    local pending={};for _,f in ipairs(s.events[n]or{})do pending[#pending+1]=f end
                    for _,f in ipairs(pending)do f(s,d)end
                end
                e.DoTaskInTime=function(s,delay,f) return {Cancel=function()end}end
                e.replica.stackable=setmetatable({}, {__index=function()return function()end end})
                e.replica.inventoryitem={IsGrandOwner=function(_,p)
                    return e.components.inventoryitem and e.components.inventoryitem:GetGrandOwner()==p end,
                    IsHeldBy=function(_,p)return e.components.inventoryitem and e.components.inventoryitem.owner==p end,
                    IsHeld=function()return e.components.inventoryitem and e.components.inventoryitem.owner~=nil end,
                    SetPickupPos=function()end}
                e.AddComponent=function(s,n)
                    if n=='inventoryitem' then
                        s.components[n]={inst=s,ChangeImageName=function(c,v)c.imagename=v end,
                            GetGrandOwner=function(c)
                                local owner=c.owner
                                return owner and owner.components.inventoryitem and owner.components.inventoryitem:GetGrandOwner() or owner
                            end,
                            RemoveFromOwner=function(c)
                                c.owner=nil;c.removedfromowner=true
                                if c.onremoveowner then c.onremoveowner()end
                            end,GetMoisture=function()return 0 end,IsWet=function()return false end,
                            OnPutInInventory=function(c,o)c.owner=o end,
                            GetTemperature=function()return 20 end,SetTemperature=function()end,
                            InheritMoisture=function()end}
                    elseif n=='equippable' then
                        s.components[n]={SetOnEquip=function(c,f)c.onequipfn=f end,
                            SetOnUnequip=function(c,f)c.onunequipfn=f end}
                    elseif n=='weapon' then
                        s.components[n]={SetDamage=function(c,v)c.damage=v end}
                    elseif n=='inspectable' then s.components[n]={}
                    else s.components[n]=require('components/'..n)(s)end
                end
                return e
            end
            CreateEntity=MakeEntity
            function Sample(prefab,uses,count)
                local e=MakeEntity();e.prefab=prefab;e:AddComponent('inventoryitem')
                e:AddComponent('finiteuses');e.components.finiteuses:SetUses(uses or 100)
                if count then e:AddComponent('stackable');e.components.stackable:SetStackSize(count)end
                e.components.inventoryitem.owner=giver
                return e
            end
            SpawnPrefab=function(n)return Sample(n,100,1)end
        """)
        for name in ("components/tool", "components/trader", "components/finiteuses", "components/stackable"):
            self.lua.execute("package.preload[...] = function() " + self.native[name] + " end", name)
        for path in paths[:2]:
            self.lua.execute("package.preload[...] = function() " + (SCRIPTS/path).read_text(encoding="utf-8-sig") + " end", path[:-4])
        self.lua.execute("""
            installedactions={}; discoveries={}; handlers={}
            env={GLOBAL=_G, AddAction=function(a)installedactions[a.id]=a end,
                AddComponentAction=function(k,n,f)discoveries[k..':'..n]=f end,
                AddStategraphActionHandler=function(n,h)handlers[n]=h end}
            Imprint=require('klbq_kanami/imprint');Imprint.Install(env)
        """)
        self.lua.execute("toolprefab=(function() " + (SCRIPTS / paths[2]).read_text(encoding="utf-8-sig") + " end)()")
        self.lua.execute("tool=toolprefab.fn();tool.prefab='klbq_imprint_tool';giver=MakeEntity();giver:AddTag('player')")

    def test_fresh_item_has_no_work_actions_or_durability_and_damage_seventeen(self):
        self.assertEqual(self.lua.eval("tool.components.weapon.damage"), 17)
        self.assertEqual(self.lua.eval("tool.components.equippable.equipslot"), "hands")
        self.assertTrue(self.lua.eval("tool.components.finiteuses==nil and tool.components.fueled==nil"))
        self.assertFalse(self.lua.eval("tool.components.tool:CanDoToughWork()"))
        for action in ("CHOP", "MINE", "DIG", "HAMMER"):
            self.assertFalse(self.lua.eval("tool.components.tool:CanDoAction(ACTIONS[...])", action))

    def test_walrus_tusk_consumes_one_for_permanent_handheld_cane_speed(self):
        self.lua.execute("sample=Sample('walrus_tusk',100,2);sample.components.finiteuses=nil")
        self.assertTrue(self.lua.eval('tool.components.trader:AcceptGift(giver,sample)'))
        self.assertEqual(self.lua.eval('sample.components.stackable:StackSize()'), 1)
        self.assertEqual(self.lua.eval('tool.components.equippable.walkspeedmult'), 1.25)
        self.assertTrue(self.lua.eval('Imprint.Has(tool,"speed")'))
        self.assertEqual(self.lua.eval('Imprint.Mask(tool)'), 0)
        self.assertIn('手持加速', self.lua.eval('tool:GetDisplayName()'))
        self.assertFalse(self.lua.eval('tool.components.trader:AcceptGift(giver,sample)'))
        self.assertEqual(self.lua.eval('sample.components.stackable:StackSize()'), 1)

    def test_speed_upgrade_saves_and_old_saves_default_to_normal_speed(self):
        self.lua.execute('''
            sample=Sample('walrus_tusk');sample.components.finiteuses=nil
            assert(tool.components.trader:AcceptGift(giver,sample))
            saved=tool.components.klbq_imprint:OnSave()
            restored=toolprefab.fn();restored.components.klbq_imprint:OnLoad(saved)
            old=toolprefab.fn();old.components.klbq_imprint:OnLoad({chop=true})
        ''')
        self.assertTrue(self.lua.eval('saved.speed and Imprint.Has(restored,"speed")'))
        self.assertEqual(self.lua.eval('restored.components.equippable.walkspeedmult'), 1.25)
        self.assertFalse(self.lua.eval('Imprint.Has(old,"speed")'))
        self.assertEqual(self.lua.eval('old.components.equippable.walkspeedmult'), 1)

    def test_tusk_uses_existing_inventory_imprint_action(self):
        self.lua.execute('''
            sample=Sample('walrus_tusk');sample.components.finiteuses=nil
            tool.components.inventoryitem.owner=giver;actions={}
            discoveries['USEITEM:inventoryitem'](sample,giver,tool,actions,true)
        ''')
        self.assertTrue(self.lua.eval('actions[1]==installedactions.KLBQ_IMPRINT'))
        self.assertTrue(self.lua.eval('actions[1].fn({doer=giver,target=tool,invobject=sample})'))
        self.assertTrue(self.lua.eval('Imprint.Has(tool,"speed") and not sample:IsValid()'))

    def test_three_gold_samples_permanently_unlock_only_their_action_at_efficiency_one(self):
        for sample, action in (("goldenaxe", "CHOP"), ("goldenpickaxe", "MINE"), ("goldenshovel", "DIG")):
            with self.subTest(sample=sample):
                self.lua.execute("sample=Sample(...,1)", sample)
                self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
                self.assertTrue(self.lua.eval("sample.removed and sample.components.inventoryitem.removedfromowner"))
                self.assertEqual(self.lua.eval("tool.components.tool:GetEffectiveness(ACTIONS[...])", action), 1)
                self.assertTrue(self.lua.eval("tool:HasTag(...)", action + "_tool"))
        self.assertFalse(self.lua.eval("tool.components.tool:CanDoToughWork()"))
        self.assertFalse(self.lua.eval("tool.components.tool:CanDoAction(ACTIONS.HAMMER)"))

    def test_multitool_first_grants_only_tough_then_gold_is_still_required(self):
        self.lua.execute("sample=Sample('multitool_axe_pickaxe',20)")
        self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
        self.assertTrue(self.lua.eval("tool.components.tool:CanDoToughWork()"))
        self.assertFalse(self.lua.eval("tool.components.tool:CanDoAction(ACTIONS.CHOP) or tool.components.tool:CanDoAction(ACTIONS.MINE)"))
        self.lua.execute("sample=Sample('goldenpickaxe',20)")
        self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
        self.assertEqual(self.lua.eval("tool.components.tool:GetEffectiveness(ACTIONS.MINE)"), 1)

    def test_duplicate_invalid_depleted_missing_durability_do_not_consume(self):
        self.lua.execute("sample=Sample('goldenaxe',100);assert(tool.components.trader:AcceptGift(giver,sample))")
        for prefab, uses in (("goldenaxe",100),("axe",100),("goldenpickaxe",0),("goldenshovel",-1),("multitool_axe_pickaxe",0)):
            self.lua.execute("sample=Sample(...)", prefab)
            self.lua.execute("sample.components.finiteuses:SetUses(...)", uses)
            self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
            self.assertTrue(self.lua.eval("sample:IsValid() and sample.components.inventoryitem.owner==giver"))
        self.lua.execute("sample=Sample('goldenshovel',100);sample.components.finiteuses=nil")
        self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))

    def test_partial_and_full_samples_each_consume_one_whole_item_not_remaining_uses(self):
        for uses in (1, 100):
            self.lua.execute("tool=toolprefab.fn();sample=Sample('goldenaxe',...,3)", uses)
            self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
            self.assertEqual(self.lua.eval("sample.components.stackable:StackSize()"), 2)
            self.assertEqual(self.lua.eval("sample.components.finiteuses.current"), uses)
            self.assertTrue(self.lua.eval("sample:IsValid() and sample.components.inventoryitem.owner==giver"))
            self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
            self.assertEqual(self.lua.eval("sample.components.stackable:StackSize()"), 2)

    def test_foreign_tool_foreign_sample_ground_sample_and_distant_tool_are_refused(self):
        self.lua.execute("sample=Sample('goldenaxe');other=MakeEntity();other:AddTag('player')")
        for setup in ("tool.components.inventoryitem.owner=other", "sample.components.inventoryitem.owner=other",
                      "sample.components.inventoryitem.owner=nil", "tool.x=99"):
            self.lua.execute("tool.components.inventoryitem.owner=nil;sample.components.inventoryitem.owner=giver;tool.x=0;" + setup)
            self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
            self.assertTrue(self.lua.eval("sample:IsValid()"))

    def test_string_ghost_dead_and_revival_protection_block_even_hand_held_samples(self):
        for state in ("string", "dead", "protected"):
            self.lua.execute("""
                tool=toolprefab.fn();sample=Sample('goldenaxe')
                giver.components.klbq_kanami={state={string=false},Alive=function()return true end,CanUseHands=function()return true end}
            """)
            self.lua.execute({"string":"giver.components.klbq_kanami.state.string=true",
                              "dead":"giver.components.klbq_kanami.Alive=function()return false end",
                              "protected":"giver.components.klbq_kanami.CanUseHands=function()return false end"}[state])
            self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
            self.assertTrue(self.lua.eval("sample:IsValid()"))
        self.lua.execute("giver.components.klbq_kanami=nil;giver:AddTag('playerghost')")
        self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))

    def test_reentrant_and_repeated_delivery_cannot_consume_twice(self):
        self.lua.execute("""
            sample=Sample('goldenaxe');second=Sample('goldenaxe')
            sample.components.inventoryitem.onremoveowner=function()
                reentered=tool.components.trader:AcceptGift(giver,second)
            end
        """)
        self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))
        self.assertFalse(self.lua.eval("reentered"))
        self.assertTrue(self.lua.eval("second:IsValid() and second.components.inventoryitem.owner==giver"))
        self.assertFalse(self.lua.eval("tool.components.trader:AcceptGift(giver,sample)"))

    def test_save_reload_exact_flags_instance_isolation_and_transfer(self):
        self.lua.execute("""
            sample=Sample('goldenaxe');assert(tool.components.trader:AcceptGift(giver,sample))
            sample=Sample('multitool_axe_pickaxe');assert(tool.components.trader:AcceptGift(giver,sample))
            saved=tool.components.klbq_imprint:OnSave();second=toolprefab.fn()
            restored=toolprefab.fn();restored.components.klbq_imprint:OnLoad(saved)
            other=MakeEntity();other:AddTag('player');tool.components.inventoryitem.owner=other
        """)
        for name, value in (("chop",True),("mine",False),("dig",False),("tough",True)):
            self.assertEqual(self.lua.eval("restored['_klbq_imprint_'.. ...]:value()", name), value)
            self.assertFalse(self.lua.eval("second['_klbq_imprint_'.. ...]:value()", name))
            self.assertEqual(self.lua.eval("tool['_klbq_imprint_'.. ...]:value()", name), value)
        self.lua.execute("restored.components.klbq_imprint:OnLoad({chop='true',mine=1})")
        self.assertFalse(self.lua.eval("restored._klbq_imprint_chop:value() or restored._klbq_imprint_mine:value() or restored._klbq_imprint_tough:value()"))

    def test_client_has_network_flags_status_and_leds_without_server_components(self):
        self.lua.execute("TheWorld.ismastersim=false;client=toolprefab.fn()")
        self.assertTrue(self.lua.eval("client.pristine and next(client.components)==nil"))
        for name in ("chop", "mine", "dig", "tough", "speed"):
            self.assertFalse(self.lua.eval("client['_klbq_imprint_'.. ...]:value()", name))
        self.lua.execute("client._klbq_imprint_mine:set(true);client:PushEvent('klbq_imprintdirty')")
        self.assertIn("采矿", self.lua.eval("client:GetDisplayName()"))
        self.assertTrue(self.lua.eval("client.leds.imprint_mine~=nil"))

    def test_native_give_and_inventory_useitem_discovery_and_execution(self):
        self.lua.execute("sample=Sample('goldenaxe');tool.components.inventoryitem.owner=giver")
        self.lua.execute("available={};discoveries['USEITEM:inventoryitem'](sample,giver,tool,available,true)")
        self.assertTrue(self.lua.eval("available[1]==installedactions.KLBQ_IMPRINT"))
        self.assertEqual(self.lua.eval("handlers.wilson.state"), "doshortaction")
        self.assertEqual(self.lua.eval("handlers.wilson_client.state"), "doshortaction")
        self.lua.execute("""
            act={doer=giver,target=tool,invobject=sample}
            result=installedactions.KLBQ_IMPRINT.fn(act)
        """)
        self.assertTrue(self.lua.eval("result"))
        self.assertFalse(self.lua.eval("installedactions.KLBQ_IMPRINT.fn(act)"))
        give = self.native["actions"].split("ACTIONS.GIVE.fn =",1)[1].split("ACTIONS.GIVETOPLAYER.fn =",1)[0]
        self.lua.execute("local ShouldBlockGiving=function()return false end;ShouldItemMimicBeRevealedFor=function()return false end;ACTIONS.GIVE.fn="+give)
        self.lua.execute("tool.components.inventoryitem.owner=nil;sample=Sample('goldenshovel')")
        self.assertTrue(self.lua.eval("ACTIONS.GIVE.fn({doer=giver,target=tool,invobject=sample})"))
        self.assertTrue(self.lua.eval("tool._klbq_imprint_dig:value()"))

    def test_native_tough_recoil_respects_independent_tough_flag(self):
        src=self.native["components/workable"]
        start=src.index("function Workable:ShouldRecoil(")
        self.lua.execute("Workable={};" + src[start:src.index("\nreturn Workable",start)])
        self.assertEqual(self.lua.eval("Workable.ShouldRecoil({tough=true},giver,tool,1)"), (True,0))
        self.lua.execute("sample=Sample('multitool_axe_pickaxe');assert(tool.components.trader:AcceptGift(giver,sample))")
        self.assertEqual(self.lua.eval("Workable.ShouldRecoil({tough=true},giver,tool,1)"), (False,1))

    def test_inventory_target_supports_left_and_right_item_application(self):
        self.lua.execute("sample=Sample('goldenaxe');tool.components.inventoryitem.owner=giver")
        for right in (False, True):
            self.lua.execute("available={};discoveries['USEITEM:inventoryitem'](sample,giver,tool,available,...)", right)
            self.assertTrue(self.lua.eval("available[1]==installedactions.KLBQ_IMPRINT"))

    def test_native_buffered_action_rechecks_ownership_and_protection_at_execution(self):
        self.lua.execute(self.native['bufferedaction'])
        self.lua.execute("""
            sample=Sample('goldenaxe');tool.components.inventoryitem.owner=giver
            action=BufferedAction(giver,tool,installedactions.KLBQ_IMPRINT,sample)
            other=MakeEntity();other:AddTag('player')
            tool.components.inventoryitem.owner=other
        """)
        self.assertFalse(self.lua.eval("(action:Do())"))
        self.lua.execute("""
            tool.components.inventoryitem.owner=giver
            action=BufferedAction(giver,tool,installedactions.KLBQ_IMPRINT,sample)
            giver._klbq_protect={value=function()return true end}
        """)
        self.assertFalse(self.lua.eval("(action:Do())"))
        self.assertTrue(self.lua.eval("sample:IsValid() and sample.components.inventoryitem.owner==giver"))
        self.lua.execute("giver._klbq_protect=nil")
        self.assertTrue(self.lua.eval("(action:Do())"))
        self.assertFalse(self.lua.eval("(action:Do())"))

    def test_nested_owned_inventory_and_forged_stack_count_still_spend_exactly_one(self):
        self.lua.execute("""
            bag=MakeEntity();bag:AddComponent('inventoryitem');bag.components.inventoryitem.owner=giver
            tool.components.inventoryitem.owner=bag;sample=Sample('goldenaxe',20,4)
            sample.components.inventoryitem.owner=bag
        """)
        self.assertTrue(self.lua.eval("tool.components.trader:AcceptGift(giver,sample,99)"))
        self.assertEqual(self.lua.eval("sample.components.stackable:StackSize()"), 3)
        self.assertTrue(self.lua.eval("sample.components.inventoryitem.owner==bag"))

    def test_all_sixteen_masks_select_the_corresponding_held_led_symbol_on_equip(self):
        for mask in range(16):
            self.lua.execute("""
                local mask=...
                for i,key in ipairs(Imprint.KEYS)do
                    tool['_klbq_imprint_'..key]:set(math.floor(mask/2^(i-1))%2==1)
                end
                tool.components.equippable.onequipfn(tool,giver)
            """, mask)
            self.assertEqual(self.lua.eval("Imprint.Mask(tool)"), mask)
            self.assertEqual(self.lua.eval("giver.swapsymbol[1]"), "swap_object")
            self.assertEqual(self.lua.eval("giver.swapsymbol[2]"), "swap_klbq_imprint_tool")
            self.assertEqual(self.lua.eval("giver.swapsymbol[3]"), "swap_idle_"+str(mask))

    def test_live_led_upgrade_refreshes_only_this_current_hands_item(self):
        self.lua.execute("""
            tool.components.inventoryitem.owner=giver
            giver.components.inventory={GetEquippedItem=function()return tool end}
            sample=Sample('goldenaxe');assert(tool.components.trader:AcceptGift(giver,sample))
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"), "swap_idle_1")
        self.lua.execute("""
            other=MakeEntity();giver.components.inventory.GetEquippedItem=function()return other end
            giver.swapsymbol={'swap_object','other_weapon','keep_this'}
            sample=Sample('goldenpickaxe');assert(tool.components.trader:AcceptGift(giver,sample))
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"), "keep_this")

    def test_client_dirty_does_not_overwrite_server_authoritative_work_projection(self):
        self.lua.execute("""
            TheWorld.ismastersim=false;client=toolprefab.fn();client.parent=giver
            giver.replica.inventory={GetEquippedItem=function()return client end}
            giver.swapsymbol={'swap_object','swap_klbq_imprint_tool','swap_mine_8'}
            client._klbq_imprint_tough:set(true);client:PushEvent('klbq_imprintdirty')
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"), "swap_mine_8")
        self.assertEqual(self.lua.eval("client.leds.imprint_tough[2]"), 1)

    def test_native_newstate_projects_matching_tool_from_windup_then_resets_on_stop(self):
        self.lua.execute("""
            tool.components.inventoryitem.owner=giver
            giver.components.inventory={GetEquippedItem=function()return tool end}
            giver.sg={currentstate={name='idle'}}
            tool.components.equippable.onequipfn(tool,giver)
        """)
        forms={'chop_start':'chop','chop':'chop','mine_start':'mine','mine':'mine',
               'mine_recoil':'mine','dig_start':'dig','dig':'dig', 'idle':'idle',
               'run_start':'idle','death':'idle'}
        for state,form in forms.items():
            # These are actual states in the currently installed authoritative SG.
            self.assertRegex(self.native['stategraphs/SGwilson'],r'name\s*=\s*"'+state+'"')
            self.lua.execute("giver.sg.currentstate.name=...;giver:PushEvent('newstate',{statename=...})",state)
            self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'swap_'+form+'_0')

    def test_dirty_unlock_retains_current_projection_and_unequip_removes_observers(self):
        self.lua.execute("""
            tool.components.inventoryitem.owner=giver
            giver.components.inventory={GetEquippedItem=function()return tool end}
            giver.sg={currentstate={name='mine_start'}}
            tool.components.equippable.onequipfn(tool,giver)
            sample=Sample('goldenpickaxe');assert(tool.components.trader:AcceptGift(giver,sample))
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'swap_mine_2')
        self.lua.execute("tool.components.equippable.onunequipfn(tool,giver)")
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'swap_idle_2')
        self.assertEqual(self.lua.eval("#giver.events.newstate"),0)
        self.assertEqual(self.lua.eval("#giver.events.death"),0)
        self.lua.execute("giver.sg.currentstate.name='dig_start';giver:PushEvent('newstate',{statename='dig_start'})")
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'swap_idle_2')

    def test_death_and_item_removal_cleanup_do_not_touch_another_equipped_item(self):
        self.lua.execute("""
            tool.components.inventoryitem.owner=giver
            giver.components.inventory={GetEquippedItem=function()return tool end}
            giver.sg={currentstate={name='chop_start'}}
            tool.components.equippable.onequipfn(tool,giver)
            giver:PushEvent('death')
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'swap_idle_0')
        self.assertEqual(self.lua.eval("#giver.events.newstate"),0)
        self.lua.execute("""
            tool.components.equippable.onequipfn(tool,giver)
            other=MakeEntity();giver.components.inventory.GetEquippedItem=function()return other end
            giver.swapsymbol={'swap_object','other_weapon','keep_this'}
            giver.sg.currentstate.name='mine_start';giver:PushEvent('newstate',{statename='mine_start'})
            tool:Remove()
        """)
        self.assertEqual(self.lua.eval("giver.swapsymbol[3]"),'keep_this')
        self.assertEqual(self.lua.eval("#giver.events.newstate"),0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
