"""Run native theft/drop code through Kanami's protection and ownership hooks."""
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path(r"E:\steam\steamapps\common\Don't Starve Together\data\databundles\scripts.zip")


def native_method(path, signature):
    with zipfile.ZipFile(GAME) as archive:
        source = archive.read('scripts/' + path).decode('utf-8-sig')
    start = source.index(signature)
    end = re.search(r'^end\s*$', source[start:], re.M).end()
    return source[start:start + end]


class InventoryGuard(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            TheWorld={ismastersim=true};EQUIPSLOTS={HANDS='hands',HEAD='head'}
            Inventory={};InventoryItem={};Container={}
            Class=function(ctor)
                local cls={};cls.__index=cls
                return setmetatable(cls,{__call=function(_,...)local s=setmetatable({},cls);ctor(s,...);return s end})
            end
            function Entity(prefab)
                local inst={prefab=prefab,components={},tags={},events={},Transform={SetPosition=function()end,GetWorldPosition=function()return 0,0,0 end}}
                function inst:AddTag(tag)self.tags[tag]=true end
                function inst:RemoveTag(tag)self.tags[tag]=nil end
                function inst:HasTag(tag)return self.tags[tag]==true end
                function inst:IsValid()return true end
                function inst:PushEvent(name,data)self.events[name]=data end
                function inst:GetPosition()return setmetatable({},{__sub=function()return {GetNormalized=function()return {} end}end})end
                return inst
            end
            hooks={};prefabhooks={}
            ACTIONS={DROP={fn=function(act)
                return act.doer.components.inventory:DropItem(act.invobject,true)
            end}}
            env={GLOBAL=_G,AddComponentPostInit=function(name,fn)hooks[name]=fn end,
                AddPrefabPostInit=function(name,fn)prefabhooks[name]=fn end}
            function Item(name,owner,originalnosteal)
                local item=Entity(name)
                local c=setmetatable({inst=item},{__index=InventoryItem});item.components.inventoryitem=c
                if originalnosteal then item:AddTag('nosteal') end
                if hooks.inventoryitem then hooks.inventoryitem(c) end
                c:SetOwner(owner)
                c.RemoveFromOwner=function(self)
                    local previous=self.owner
                    if previous.components.inventory then
                        local inv=previous.components.inventory
                        for slot,held in pairs(inv.equipslots)do if held==item then inv.equipslots[slot]=nil end end
                        for slot,held in pairs(inv.itemslots)do if held==item then inv.itemslots[slot]=nil end end
                        if inv.activeitem==item then inv.activeitem=nil end
                    elseif previous.components.container then
                        for slot,held in pairs(previous.components.container.slots)do
                            if held==item then previous.components.container.slots[slot]=nil end
                        end
                    end
                    self:ClearOwner();return item
                end
                c.OnDropped=function()item.dropped=true end
                return item
            end
            function Player(name)
                local p=Entity(name);p:AddTag('player')
                p.components.health={IsDead=function()return p.dead==true end}
                p.components.inventory=setmetatable({inst=p,itemslots={},equipslots={},maxslots=4},{__index=Inventory})
                p.components.inventory.FindItem=function(self,fn)
                    for _,item in pairs(self.itemslots)do if fn(item)then return item end end
                end
                p.components.inventory.Equip=function(self,item)self.equipslots.head=item;return true end
                if prefabhooks[name]then prefabhooks[name](p)end
                return p
            end
        """)
        for name in ('GetGrandOwner', 'SetOwner', 'ClearOwner'):
            self.lua.execute(native_method('components/inventoryitem.lua', 'function InventoryItem:' + name + '('))
        for name in ('IsThiefProof', 'DropItem', 'DropEverything', 'DropEquipped', 'DropActiveItem', 'SetActiveItem', 'ReturnActiveItem', 'GiveItem'):
            self.lua.execute(native_method('components/inventory.lua', 'function Inventory:' + name + '('))
        self.lua.execute(native_method('components/inventory.lua', 'local function ValidateItemForOverflow(').replace('local function', 'function', 1))
        self.lua.execute("GetGhostEnabled=function()return true end;GetGameModeProperty=function()return false end")
        self.lua.execute(native_method('components/container.lua', 'function Container:IsThiefProof('))
        module = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/inventoryguard.lua'
        if module.exists():
            self.lua.execute("Guard=(function() " + module.read_text(encoding='utf-8') + " end)();Guard.Install(env)")
        self.lua.execute("""
            p=Player('klbq_kanami');other=Player('wilson')
            hat=Item('minerhat',p);weapon=Item('spear',p)
            p.components.inventory.itemslots[1]=hat;p.components.inventory.equipslots.hands=weapon
            thief=Entity('otter');thief.components.combat={DoAttack=function()end}
        """)
        with zipfile.ZipFile(GAME) as archive:
            self.lua.execute("NativeThief=(function() " + archive.read('scripts/components/thief.lua').decode('utf-8-sig') + " end)()")
        self.lua.execute('thief.components.thief=NativeThief(thief)')

    def test_native_thief_cannot_take_a_selected_item_from_kanami(self):
        self.assertFalse(self.lua.eval('thief.components.thief:StealItem(p,hat)'))
        self.assertTrue(self.lua.eval('hat.components.inventoryitem.owner==p and not hat.dropped'))

    def test_force_drop_and_disarm_keep_hand_and_inventory_items(self):
        self.lua.execute('p.components.inventory:DropItem(weapon);p.components.inventory:DropEquipped()')
        self.assertTrue(self.lua.eval('p.components.inventory.equipslots.hands==weapon and not weapon.dropped'))
        self.lua.execute('p.components.inventory:DropEverything()')
        self.assertTrue(self.lua.eval('p.components.inventory.itemslots[1]==hat'))

    def test_forced_drop_preserves_active_cursor_item(self):
        self.lua.execute('p.components.inventory.activeitem=hat;p.components.inventory.itemslots[1]=nil')
        self.lua.execute('p.components.inventory:DropActiveItem();p.components.inventory:DropEverything()')
        self.assertTrue(self.lua.eval('p.components.inventory.activeitem==hat and hat.components.inventoryitem.owner==p'))

    def full_inventory(self):
        self.lua.execute('''
            local inv=p.components.inventory
            inv.IsItemEquipped=function()return nil end
            inv.GetOverflowContainer=function()return nil end
            inv.GetSpecializedContainers=function()return nil end
            inv.GetNextAvailableSlot=function()return nil end
            for _,item in ipairs({hat,weapon})do
                item.components.inventoryitem.OnPickup=function()return false end
                item.components.inventoryitem.OnPutInInventory=function(self,owner)self:SetOwner(owner)end
            end
        ''')

    def test_full_inventory_return_active_item_drops_it_and_clears_cursor(self):
        self.full_inventory()
        self.lua.execute('''
            p.components.inventory.itemslots[1]=nil;p.components.inventory.activeitem=hat
            p.components.inventory:ReturnActiveItem()
        ''')
        self.assertTrue(self.lua.eval('hat.dropped and hat.components.inventoryitem.owner==nil'))
        self.assertIsNone(self.lua.eval('p.components.inventory.activeitem'))
        self.lua.execute('p.components.inventory:DropItem(weapon)')
        self.assertFalse(self.lua.eval('weapon.dropped==true'))

    def test_full_inventory_give_item_returns_overflow_to_ground(self):
        self.full_inventory()
        self.lua.execute('''
            p.components.inventory.activeitem=hat;p.components.inventory.itemslots[1]=nil
            -- A harvested item may already have a player owner from a pickup hook.
            crop=Item('carrot_oversized',p)
            crop.components.inventoryitem.OnPickup=function()return false end
            p.components.inventory:GiveItem(crop)
        ''')
        self.assertTrue(self.lua.eval('crop.dropped and crop.components.inventoryitem.owner==nil'))
        self.assertTrue(self.lua.eval('p.components.inventory.activeitem==hat'))

    def test_return_active_item_callbacks_cannot_disarm_another_item(self):
        self.full_inventory()
        self.lua.execute('''
            p.components.inventory.activeitem=hat;p.components.inventory.itemslots[1]=nil
            hat.components.inventoryitem.OnPickup=function()
                p.components.inventory:DropItem(weapon,true)
                return false
            end
            p.components.inventory:ReturnActiveItem()
        ''')
        self.assertFalse(self.lua.eval('weapon.dropped==true'))
        self.assertTrue(self.lua.eval('hat.dropped and p.components.inventory.equipslots.hands==weapon'))

    def test_capacity_error_restores_drop_protection(self):
        self.full_inventory()
        self.lua.execute('''
            p.components.inventory.activeitem=hat
            hat.components.inventoryitem.OnPickup=function()error('pickup failed')end
            ok=pcall(function()p.components.inventory:ReturnActiveItem()end)
            p.components.inventory:DropItem(weapon)
        ''')
        self.assertFalse(self.lua.eval('ok'))
        self.assertIsNone(self.lua.eval('p.components.inventory._klbq_capacityitems'))
        self.assertFalse(self.lua.eval('weapon.dropped==true'))

    def test_native_death_drop_still_drops_items(self):
        self.lua.execute('p.dead=true;p.components.inventory:DropEverything(true)')
        self.assertTrue(self.lua.eval('weapon.dropped and hat.dropped'))
        self.assertTrue(self.lua.eval('weapon.components.inventoryitem.owner==nil and hat.components.inventoryitem.owner==nil'))

    def test_player_drop_action_is_allowed_and_protection_resumes_afterward(self):
        self.lua.execute('result=ACTIONS.DROP.fn({doer=p,invobject=hat})')
        self.assertTrue(self.lua.eval('result==hat and hat.dropped and not hat:HasTag("nosteal")'))
        self.lua.execute('p.components.inventory:DropItem(weapon)')
        self.assertTrue(self.lua.eval('p.components.inventory.equipslots.hands==weapon'))

    def test_nested_container_is_protected_until_transferred(self):
        self.lua.execute("""
            bag=Item('backpack',p);food=Item('meat',bag)
            local c=setmetatable({inst=bag,slots={food}},{__index=Container});bag.components.container=c
            hooks.container(c)
        """)
        self.assertTrue(self.lua.eval('bag.components.container:IsThiefProof()'))
        self.assertFalse(self.lua.eval('thief.components.thief:StealItem(bag,food)'))
        self.lua.execute('bag.components.inventoryitem:SetOwner(other)')
        self.assertFalse(self.lua.eval('bag.components.container:IsThiefProof()'))
        self.assertFalse(self.lua.eval('food:HasTag("nosteal")'))

    def test_transfer_removes_only_tags_added_by_kanami(self):
        self.assertTrue(self.lua.eval('weapon:HasTag("nosteal") and p:HasTag("stronggrip")'))
        self.lua.execute('weapon.components.inventoryitem:SetOwner(other)')
        self.assertFalse(self.lua.eval('weapon:HasTag("nosteal")'))
        self.lua.execute("special=Item('pocketwatch',p,true);special.components.inventoryitem:ClearOwner()")
        self.assertTrue(self.lua.eval('special:HasTag("nosteal")'))

    def test_hostile_living_hat_cannot_force_an_equipment_swap(self):
        self.lua.execute("attacker=Item('slurper');attacker.components.combat={};p.components.inventory.equipslots.head=hat")
        self.assertFalse(self.lua.eval('p.components.inventory:Equip(attacker)'))
        self.assertTrue(self.lua.eval('p.components.inventory.equipslots.head==hat'))

    def test_drop_error_restores_guard(self):
        if not self.lua.eval('Guard~=nil'):
            self.fail('inventory guard is not installed')
        self.lua.execute("""
            p.components.inventory.DropItem=function()error('fixture drop failure')end
            ok,err=pcall(ACTIONS.DROP.fn,{doer=p,invobject=hat})
        """)
        self.assertFalse(self.lua.eval('ok'))
        self.assertIsNone(self.lua.eval('p.components.inventory._klbq_allowdrop'))

    def test_other_characters_retain_native_drop_behavior(self):
        self.lua.execute("item=Item('spear',other);other.components.inventory.equipslots.hands=item;other.components.inventory:DropEquipped()")
        self.assertTrue(self.lua.eval('item.dropped'))


if __name__ == '__main__':
    unittest.main()
