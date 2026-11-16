"""Create shared resources with the installed stackable network encoding."""
import zipfile
import unittest

import test_bag


class ResourceStackCompatibility(unittest.TestCase):
    def test_all_resources_use_a_supported_runtime_stack_size(self):
        for mod in ("klbq_kanami", "klbq_resources"):
            for size in (40, 999):
                with self.subTest(mod=mod, small_item_stack=size):
                    fixture = test_bag.SingularityBag()
                    fixture.setUp()
                    lua = fixture.lua
                    with zipfile.ZipFile(test_bag.GAME / "data/databundles/scripts.zip") as archive:
                        replica = archive.read("scripts/components/stackable_replica.lua").decode("utf-8-sig")
                    lua.execute("""
                        TUNING.STACK_SIZE_LARGEITEM=10
                        TUNING.STACK_SIZE_MEDITEM=20
                        TUNING.STACK_SIZE_SMALLITEM=...
                        TUNING.STACK_SIZE_TINYITEM=60
                        TUNING.STACK_SIZE_PELLET=120
                        if ...==999 then
                            for k in pairs(TUNING) do
                                if string.find(k,'STACK_SIZE_') then TUNING[k]=999 end
                            end
                        end
                        table.invert=function(values)
                            local inverse={}
                            for k,v in pairs(values) do inverse[v]=k end
                            return inverse
                        end
                        local function netvar()
                            return {current=0,set=function(s,v)s.current=v end,
                                value=function(s)return s.current end}
                        end
                        net_smallbyte=netvar;net_tinybyte=netvar
                    """, size)
                    lua.execute("NativeStackableReplica=(function() " + replica + " end)()")
                    lua.execute("""
                        local create=CreateEntity
                        CreateEntity=function()
                            local inst=create()
                            inst.AnimState.SetRayTestOnBB=function()end
                            inst.replica.stackable=NativeStackableReplica(inst)
                            return inst
                        end
                    """)
                    root = test_bag.ROOT / "mods" / mod / "scripts"
                    lua.execute("package.preload['klbq_resources/catalog']=function() "
                                + (root / "klbq_resources/catalog.lua").read_text(encoding="utf-8") + " end")
                    source = (root / "prefabs/klbq_resources.lua").read_text(encoding="utf-8")
                    lua.execute("prefabs={(function() " + source + " end)()}")
                    lua.execute("""
                        for _,prefab in ipairs(prefabs) do
                            local item=prefab.fn()
                            assert(item.components.stackable.maxsize==TUNING.STACK_SIZE_SMALLITEM)
                            assert(item.replica.stackable:MaxSize()==TUNING.STACK_SIZE_SMALLITEM)
                            assert(item.replica.stackable:StackSize()==1)
                        end
                    """)
                    self.assertEqual(lua.eval("#prefabs"), 20)


if __name__ == "__main__":
    unittest.main()
