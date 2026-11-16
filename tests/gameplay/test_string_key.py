"""The default key and an existing custom key both use the skill RPC."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime


class StringKey(unittest.TestCase):
    def install(self, configured=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().configured = configured
        lua.execute("""
            package.preload['klbq_kanami/camera']=function()return {}end
            handlers={};KEY_R=114;KEY_Z=122;KEY_X=120
            TheInput={AddKeyUpHandler=function(self,key,fn)handlers[key]=fn end}
            IsPaused=function()return false end
            ThePlayer={prefab='klbq_kanami',HasTag=function()return false end,
                HUD={IsChatInputScreenOpen=function()return false end}}
            TheFrontEnd={GetActiveScreen=function()return {name='HUD'}end}
            env={GLOBAL=_G,GetModConfigData=function(key)if key=='key_string'then return configured end end,
                SendModRPCToServer=function(rpc,key)sent=key end,GetModRPC=function()return {}end,
                AddClassPostConstruct=function()end,AddPrefabPostInit=function()end}
        """)
        module = ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/client.lua'
        lua.execute('(function() ' + module.read_text(encoding='utf-8') + ' end)().Install(env)')
        return lua

    def test_missing_configuration_uses_r_and_the_existing_skill_rpc(self):
        lua = self.install()
        self.assertTrue(lua.eval('handlers[114]~=nil and handlers[99]==nil'))
        lua.execute('handlers[114]()')
        self.assertEqual(lua.eval('sent'), 'c')

    def test_custom_configuration_still_uses_its_selected_key(self):
        lua = self.install(118)
        self.assertTrue(lua.eval('handlers[118]~=nil and handlers[114]==nil'))
        lua.execute('handlers[118]()')
        self.assertEqual(lua.eval('sent'), 'c')


if __name__ == '__main__':
    unittest.main()
