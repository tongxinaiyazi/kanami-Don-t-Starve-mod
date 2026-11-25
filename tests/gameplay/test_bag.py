"""Exercise the singularity against the installed DST container/perishable code.

Only engine entities and networking are substituted. The real Lua 5.1 classes,
14-slot widget definition, container admission, spoilage, and save/load execute.
"""
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/python-deps"))
from lupa.lua51 import LuaRuntime

GAME = Path("E:/steam/steamapps/common/Don't Starve Together")
SLOT_MOD = Path("E:/steam/steamapps/workshop/content/322330/3173431824")
PREFAB = ROOT / "mods/klbq_kanami/scripts/prefabs/klbq_singularity.lua"


class SingularityBag(unittest.TestCase):
    def setUp(self):
        self.assertTrue(PREFAB.is_file(), "弦能奇点 prefab is not implemented")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        with zipfile.ZipFile(GAME / "data/databundles/scripts.zip") as archive:
            native = {
                name: archive.read("scripts/" + name + ".lua").decode("utf-8-sig")
                for name in (
                    "class", "containers", "components/container",
                    "components/preserver", "components/perishable",
                    "components/trader", "components/waterproofer", "components/insulator",
                    "components/stackable", "components/inventory", "components/temperature",
                    "components/equippable", "components/armor", "util/sourcemodifierlist",
                    "componentactions", "actions", "prefabs/hats", "tuning",
                )
            }
        self.lua.execute(native["class"])
        self.lua.execute("""
            FRAMES=1/30
            TUNING={TOTAL_DAY_TIME=480,PERISH_FRESH=.5,PERISH_STALE=.2,
                PERISH_WET_MULT=1.3,PERISH_WINTER_MULT=.75,
                PERISH_FROZEN_FIRE_MULT=.2,PERISH_SUMMER_MULT=1.25,
                PERISH_COLD_FROZEN_MULT=0,PERISH_GLOBAL_MULT=1,
                PERISH_GROUND_MULT=1,OVERHEAT_TEMP=70}
            EQUIPSLOTS={BODY='body'}
            SEASONS={WINTER='winter',SUMMER='summer'}
            MAXUINT=4294967295
            TheWorld={ismastersim=true,state={temperature=20,isacidraining=false}}
            TheWorld.HasTag=function() return false end
            TheSim={ReskinEntity=function() end}
            GetTemperatureAtXZ=function() return TheWorld.state.temperature end
            GetGameModeProperty=function() return false end
            GetTaskRemaining=function() return 0 end
            FunctionOrValue=function(v,...) if type(v)=='function' then return v(...) end return v end
            math.clamp=function(v,a,b) return math.max(a,math.min(b,v)) end
            Vector3=function(x,y,z) return {x=x,y=y,z=z} end
            Asset=function(kind,path) return {type=kind,file=path} end
            Prefab=function(name,fn,assets,deps) return {name=name,fn=fn,assets=assets,deps=deps} end
            MakeInventoryPhysics=function() end
            MakeInventoryFloatable=function() end
            MakeHauntableLaunch=function() end
            MakeHauntableLaunchAndDropFirstItem=function() end
            local entities={}
            bagcomponenthooks={}
            local nextguid=0
            net_bool=function(guid,name,dirty)
                assert(not entities[guid].pristine,'net_bool must be declared before pristine')
                return {current=false,set=function(s,v) s.current=v end,value=function(s) return s.current end}
            end
            net_byte=function(guid,name,dirty)
                local var=net_bool(guid,name,dirty);var.current=0;return var
            end
            function MakeEntity()
                nextguid=nextguid+1
                local inst={GUID=nextguid,components={},tags={},events={},tasks={},replica={},persists=true}
                entities[nextguid]=inst
                inst.entity=setmetatable({}, {__index=function(t,k)
                    if k=='SetPristine' then return function() inst.pristine=true end end
                    return function() end
                end})
                inst.AnimState={SetBank=function() end,SetBuild=function() end,PlayAnimation=function() end}
                inst.Transform={GetWorldPosition=function() return 0,0,0 end}
                inst.SoundEmitter={PlaySound=function() end}
                inst.GetPosition=function() return Vector3(0,0,0) end
                inst.GetIsWet=function() return false end
                inst.IsValid=function() return true end
                inst.Remove=function(s) s.removed=true end
                inst.IsInLimbo=function() return false end
                inst.AddTag=function(s,t) s.tags[t]=true end
                inst.RemoveTag=function(s,t) s.tags[t]=nil end
                inst.HasTag=function(s,t) return s.tags[t]==true end
                inst.HasAnyTag=function(s,...) for _,t in ipairs({...}) do if s:HasTag(t) then return true end end return false end
                inst.ListenForEvent=function(s,n,fn) s.events[n]=fn end
                inst.PushEvent=function(s,n,data) if s.events[n] then s.events[n](s,data) end end
                inst.StartUpdatingComponent=function() end
                inst.StopUpdatingComponent=function() end
                inst.DoPeriodicTask=function(s,dt,fn,delay,arg)
                    local task={Cancel=function(s) s.cancelled=true end}
                    s.tasks[#s.tasks+1]=task;return task
                end
                inst.replica.container=setmetatable({}, {__index=function() return function() end end})
                inst.replica.stackable=setmetatable({}, {__index=function() return function() end end})
                inst.AddComponent=function(s,name)
                    if name=='container' or name=='preserver' or name=='perishable' or name=='trader'
                            or name=='waterproofer' or name=='insulator' or name=='stackable' or name=='armor' then
                        s.components[name]=require('components/'..name)(s)
                    elseif name=='equippable' then
                        s.components[name]={SetOnEquip=function(c,fn) c.onequipfn=fn end,
                            SetOnUnequip=function(c,fn) c.onunequipfn=fn end,
                            SetOnEquipToModel=function(c,fn) c.onequiptomodelfn=fn end,
                            IsEquipped=function(c) return c.equipped==true end}
                    elseif name=='inventoryitem' then
                        s.components[name]={cangoincontainer=true,ChangeImageName=function(c,n) c.imagename=n end,
                            EnableMoisture=function(c,v) c.moistureenabled=v end,
                            RemoveFromOwner=function(c) c.owner=nil;c.removedfromowner=true end,
                            OnPutInInventory=function(c,owner) c.owner=owner end,
                            InheritMoisture=function() end,GetMoisture=function() return 0 end,
                            IsWet=function() return false end,SetTemperature=function() end,
                            GetTemperature=function() return 20 end}
                    else s.components[name]={} end
                    if bagcomponenthooks[name] then bagcomponenthooks[name](s.components[name]) end
                end
                return inst
            end
            CreateEntity=MakeEntity
        """)
        # Execute the unmodified installed widgetsetup and krampus widget block.
        # Other native container definitions require UI systems irrelevant here.
        source = native["containers"]
        widgetsetup = source[source.index("function containers.widgetsetup"):source.index("--[[ backpack ]]")]
        krampus = re.search(r"params\.krampus_sack\s*=.*?(?=--\[\[ piggyback \]\])", source, re.S).group()
        self.lua.execute("package.preload.containers=function() local params={};local containers={params=params};"
                         + widgetsetup + krampus + " return containers end")
        for name in ("components/container", "components/preserver", "components/perishable",
                     "components/trader", "components/waterproofer", "components/insulator", "components/stackable",
                     "components/armor", "util/sourcemodifierlist"):
            self.lua.execute("package.preload[...] = function() " + native[name] + " end", name)
        module = ROOT / "mods/klbq_kanami/scripts/klbq_kanami/bag.lua"
        if module.exists():
            self.lua.execute("package.preload['klbq_kanami/bag']=function() "
                             + module.read_text(encoding="utf-8-sig") + " end")
            self.lua.execute("""
                require('klbq_kanami/bag').Install({GLOBAL=_G,
                    AddComponentPostInit=function(n,fn)bagcomponenthooks[n]=fn end,
                    AddClassPostConstruct=function()end})
            """)
        self.native = native
        # Extract the installed constants used by the eyebrella, not copied values.
        seg_time = re.search(r"local seg_time\s*=\s*([^\r\n]+)", native["tuning"]).group(1)
        for key in ("WATERPROOFNESS_ABSOLUTE", "INSULATION_LARGE", "STACK_SIZE_MEDITEM"):
            value = re.search(r"\b" + key + r"\s*=\s*([^,\r\n]+)", native["tuning"]).group(1)
            self.lua.execute("local seg_time=" + seg_time + ";TUNING." + key + "=" + value)
        self.lua.execute("bagprefab=(function() " + PREFAB.read_text(encoding="utf-8-sig") + " end)()")
        self.lua.execute("bag=bagprefab.fn()")
        self.lua.execute("""
            function MakeFood(lifetime,percent)
                local item=MakeEntity();item:AddComponent('inventoryitem');item:AddComponent('perishable')
                item.components.inventoryitem.owner=bag
                item.components.perishable:SetPerishTime(lifetime)
                item.components.perishable:SetPercent(percent)
                item.components.perishable:StartPerishing()
                return item
            end
        """)

    def test_native_widget_has_exactly_fourteen_slots_and_rejects_fifteenth(self):
        self.assertEqual(self.lua.eval("bag.components.container.numslots"), 14)
        self.lua.execute("food=MakeFood(4800,.5)")
        self.assertTrue(self.lua.eval("bag.components.container:CanTakeItemInSlot(food,14)"))
        self.assertFalse(self.lua.eval("bag.components.container:CanTakeItemInSlot(food,15)"))

    def test_native_admission_prevents_nesting_the_bag(self):
        self.assertFalse(self.lua.eval("bag.components.container:CanTakeItemInSlot(bag,1)"))
        self.assertTrue(self.lua.eval("bag:HasTag('backpack')"))

    def test_bag_can_enter_inventory_and_an_unrelated_container(self):
        source = self.native["components/inventory"]
        start = source.index("function Inventory:CanTakeItemInSlot")
        end = source.index("function Inventory:AcceptsStacks", start)
        self.lua.execute("Inventory={};" + source[start:end])
        self.lua.execute("""
            pocket={maxslots=15,GetItemInSlot=function()end}
            outer=MakeEntity();outer:AddComponent('container');outer.components.container.numslots=8
        """)
        self.assertTrue(self.lua.eval("Inventory.CanTakeItemInSlot(pocket,bag,1)"))
        self.assertTrue(self.lua.eval("outer.components.container:CanTakeItemInSlot(bag,1)"))
        self.assertFalse(self.lua.eval("bag.components.inventoryitem.canonlygoinpocket==true"))

    def test_native_admission_allows_safe_bags_but_blocks_both_cycle_directions(self):
        self.lua.execute("""
            second=bagprefab.fn()
            outer=MakeEntity();outer:AddComponent('inventoryitem');outer:AddComponent('container')
            outer.components.container.numslots=8
        """)
        self.assertTrue(self.lua.eval("bag.components.container:CanTakeItemInSlot(second,1)"))
        self.assertTrue(self.lua.eval("bag.components.container:CanTakeItemInSlot(outer,1)"))
        self.lua.execute("bag.components.inventoryitem.owner=outer")
        self.assertFalse(self.lua.eval("bag.components.container:CanTakeItemInSlot(outer,1)"))
        self.lua.execute("bag.components.inventoryitem.owner=nil;outer.components.inventoryitem.owner=bag")
        self.assertFalse(self.lua.eval("outer.components.container:CanTakeItemInSlot(bag,1)"))
        self.lua.execute("second.components.inventoryitem.owner=bag;bag.components.inventoryitem.owner=nil")
        self.assertFalse(self.lua.eval("second.components.container:CanTakeItemInSlot(bag,1)"))

    def test_native_perishing_reverses_ten_percent_of_base_decay(self):
        for lifetime in (480, 4800, 9600):
            with self.subTest(lifetime=lifetime):
                self.lua.execute("food=MakeFood(...,.25);food.components.perishable:LongUpdate(480)", lifetime)
                self.assertAlmostEqual(self.lua.eval("food.components.perishable:GetPercent()"), .25 + 48 / lifetime)

    def test_restoration_stops_at_fully_fresh_using_native_clamp(self):
        self.lua.execute("food=MakeFood(4800,.99);food.components.perishable:LongUpdate(48000)")
        self.assertEqual(self.lua.eval("food.components.perishable:GetPercent()"), 1)
        self.assertTrue(self.lua.eval("food:HasTag('fresh')"))

    def test_removal_immediately_restores_normal_decay(self):
        self.lua.execute("""
            food=MakeFood(4800,.25);food.components.perishable:LongUpdate(480)
            food.components.inventoryitem.owner=nil
            food.components.perishable:LongUpdate(480)
        """)
        self.assertAlmostEqual(self.lua.eval("food.components.perishable:GetPercent()"), .16)

    def test_native_save_reload_keeps_recovered_freshness(self):
        self.lua.execute("""
            food=MakeFood(4800,.25);food.components.perishable:LongUpdate(480)
            saved=food.components.perishable:OnSave()
            restored=MakeFood(4800,1);restored.components.perishable:OnLoad(saved)
            restored.components.perishable:LongUpdate(480)
        """)
        self.assertAlmostEqual(self.lua.eval("restored.components.perishable:GetPercent()"), .27)

    def test_equip_opens_and_unequip_or_model_closes_without_changing_player_art(self):
        self.lua.execute("""
            opened=0;closed=0;visualwrites=0
            owner={prefab='klbq_kanami',PushEvent=function() end,AnimState=setmetatable({}, {__index=function()
                return function() visualwrites=visualwrites+1 end end})}
            bag.components.container.Open=function(c,w) assert(w==owner);opened=opened+1 end
            bag.components.container.Close=function(c,w) assert(w==owner);closed=closed+1 end
            bag.components.equippable.onequipfn(bag,owner)
            bag.components.equippable.onunequipfn(bag,owner)
            bag.components.equippable.onequiptomodelfn(bag,owner)
        """)
        self.assertEqual(self.lua.eval("opened"), 1)
        self.assertEqual(self.lua.eval("closed"), 2)
        self.assertEqual(self.lua.eval("visualwrites"), 0)

    def test_extra_slot_follows_actual_registered_back_slot_and_disabled_falls_back(self):
        self.assertEqual(self.lua.eval("bag.components.equippable.equipslot"), "body")
        # This is the actual value registered by installed 3173431824/slots.lua.
        self.lua.execute("EQUIPSLOTS.BACK='extra_slots_back';extra=bagprefab.fn()")
        self.assertEqual(self.lua.eval("extra.components.equippable.equipslot"), "extra_slots_back")
        self.assertEqual(self.lua.eval("extra.equipslot"), "extra_slots_back")
        self.lua.execute("EQUIPSLOTS.BACK=nil;disabled=bagprefab.fn()")
        self.assertEqual(self.lua.eval("disabled.components.equippable.equipslot"), "body")

    def test_installed_extra_slot_assignment_recognizes_and_wraps_the_bag(self):
        self.lua.execute("""
            GLOBAL=_G
            EQUIPSLOTS.BACK='extra_slots_back'
            AddPrefabPostInit=function() end
            AddPrefabPostInitAny=function(fn) assign=fn end
            package.preload.symbol_back=function() return {} end
            package.preload.yongbutuoxie=function() return {} end
            modrequire=function(name)
                if name=='modconfig' then return {IsServer=true} end
                if name=='bodylayers' then return {BODY_LAYER_LIST={},BODY_LAYER_DEFS={NECK={},BELLY={}}} end
                if name=='backslot' then return {ApplyBackCallbacks=function(inst) wrapped=inst end} end
            end
            bag.prefab='klbq_singularity'
        """)
        assignment = (SLOT_MOD / "scripts/assign.lua").read_text(encoding="utf-8-sig")
        self.lua.execute("(function() " + assignment + " end)().InitPrefab();assign(bag)")
        self.assertEqual(self.lua.eval("bag.components.equippable.equipslot"), "extra_slots_back")
        self.assertTrue(self.lua.eval("wrapped==bag"))

    def test_client_constructs_pristine_network_entity_without_server_components(self):
        self.lua.execute("TheWorld.ismastersim=false;clientbag=bagprefab.fn()")
        self.assertTrue(self.lua.eval("clientbag.pristine"))
        self.assertTrue(self.lua.eval("clientbag:HasTag('backpack')"))
        self.assertTrue(self.lua.eval("next(clientbag.components)==nil"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
