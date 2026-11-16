"""Reproduce the reported client crash with native Replica + Widget:Open.

The old server-only test stubs replica.WidgetSetup and cannot exercise remote
clients. These tests execute the installed replica constructor and complete
container window Open method; only graphics nodes/netvars are fixtures.
"""
import re
import unittest
import zipfile
import test_bag


class BagClient(unittest.TestCase):
    def setUp(self):
        fixture = test_bag.SingularityBag()
        fixture.setUp()
        self.lua = fixture.lua
        with zipfile.ZipFile(test_bag.GAME / 'data/databundles/scripts.zip') as z:
            replica = z.read('scripts/components/container_replica.lua').decode('utf8')
            widget = z.read('scripts/widgets/containerwidget.lua').decode('utf8')
        start = widget.index('function ContainerWidget:Open(')
        end = start + re.search(r'^end\s*$', widget[start:], re.M).end()
        self.lua.execute('package.preload[...] = function() '+replica+' end', 'components/container_replica')
        self.lua.execute('ContainerWidget={};'+widget[start:end])
        self.lua.execute('''
            TheWorld.ismastersim=false
            -- Engine normally creates replica netvars during entity assembly.
            net_bool=function()return {value=function()return false end}end
            client=bagprefab.fn();client.prefab='klbq_singularity'
            client.replica.container=require('components/container_replica')(client)
            owner={components={}}
            local function Node()
                return {SetPosition=function()end,SetBank=function(s,n)s.bank=n end,
                    SetBuild=function(s,n)s.build=n end,PlayAnimation=function(s,n)s.anim=n end,
                    GetAnimState=function(s)return s end}
            end
            InvSlot=function(index,atlas,texture,doer,container)
                local n=Node();n.index=index;n.container=container;return n
            end
            screen={inv={},owner=owner,bgimage={},bganim=Node(),inst={ListenForEvent=function()end},
                Close=function(s)s.inv={};s.isopen=false end,
                Show=function(s)s.shown=true end,SetPosition=function(s,p)s.position=p end,
                AddChild=function(s,c)return c end,Refresh=function(s)s.refreshed=true end}
        ''')

    def test_remote_constructor_resolves_fourteen_slots_without_server_components(self):
        self.assertIsNone(self.lua.eval('client.components.container'))
        self.assertEqual(self.lua.eval('client.replica.container:GetNumSlots()'), 14)
        self.assertTrue(self.lua.eval('client.replica.container:GetWidget()~=nil'))
        self.assertTrue(self.lua.eval('client.replica.container:IsSideWidget()'))

    def test_native_client_open_builds_all_slots_and_can_reopen_existing_bag(self):
        for _ in range(2):
            self.lua.execute('ContainerWidget.Open(screen,client,owner)')
            self.assertEqual(self.lua.eval('#screen.inv'), 14)
            self.assertTrue(self.lua.eval('screen.shown and screen.isopen and screen.refreshed'))
            self.assertEqual(self.lua.eval('screen.bganim.bank'), 'ui_krampusbag_2x8')
            self.assertTrue(self.lua.eval('screen.inv[14].container==client.replica.container'))

    def test_server_and_remote_use_same_private_layout_without_changing_vanilla_pack(self):
        self.assertTrue(self.lua.eval('bag.components.container:GetWidget()==client.replica.container:GetWidget()'))
        self.assertTrue(self.lua.eval("require('containers').params.klbq_singularity~=require('containers').params.krampus_sack"))
        self.lua.execute("table.remove(require('containers').params.krampus_sack.widget.slotpos)")
        self.assertEqual(self.lua.eval('#client.replica.container:GetWidget().slotpos'), 14)

    def test_native_remote_admission_allows_safe_bags_and_rejects_ownership_cycles(self):
        self.lua.execute('''
            function RemoteItem(inst)
                inst.replica.inventoryitem={CanGoInContainer=function()return true end,
                    CanOnlyGoInPocket=function()return false end,
                    CanOnlyGoInPocketOrPocketContainers=function()return false end,
                    IsLockedInSlot=function()return false end}
                return inst
            end
            RemoteItem(client)
            other=RemoteItem(bagprefab.fn());other.prefab='klbq_singularity'
            other.replica.container=require('components/container_replica')(other)
            hooks={}
            require('klbq_kanami/bag').Install({GLOBAL=_G,AddComponentPostInit=function()end,
                AddClassPostConstruct=function(n,fn)hooks[n]=fn end})
            outer=RemoteItem(MakeEntity());outer.prefab='krampus_sack'
            outer.replica.container=require('components/container_replica')(outer)
            hooks['components/container_replica'](outer.replica.container)
        ''')
        self.assertTrue(self.lua.eval('client.replica.container:CanTakeItemInSlot(other,1)'))
        self.assertTrue(self.lua.eval('outer.replica.container:CanTakeItemInSlot(client,1)'))
        self.assertFalse(self.lua.eval('client.replica.container:CanTakeItemInSlot(client,1)'))
        self.lua.execute('client.entity.GetParent=function()return outer end')
        self.assertFalse(self.lua.eval('client.replica.container:CanTakeItemInSlot(outer,1)'))
        self.lua.execute('client.entity.GetParent=function()end;outer.entity.GetParent=function()return client end')
        self.assertFalse(self.lua.eval('outer.replica.container:CanTakeItemInSlot(client,1)'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
