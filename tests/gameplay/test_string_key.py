"""The default key and an existing custom key both use the skill RPC."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime


class StringKey(unittest.TestCase):
    def install(self, configured=None, requiem_key=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().configured = configured
        lua.globals().requiem_key = requiem_key
        lua.execute("""
            package.preload['klbq_kanami/camera']=function()return {}end
            handlers={};KEY_R=114;KEY_Z=122;KEY_X=120;KEY_V=118
            TheInput={AddKeyUpHandler=function(self,key,fn)handlers[key]=fn end}
            IsPaused=function()return false end
            ThePlayer={prefab='klbq_kanami',HasTag=function()return false end,
                replica={combat={GetWeapon=function()return {prefab='klbq_requiem'}end}},
                HUD={IsChatInputScreenOpen=function()return false end}}
            TheFrontEnd={GetActiveScreen=function()return {name='HUD'}end}
            env={GLOBAL=_G,GetModConfigData=function(key)if key=='key_string'then return configured elseif key=='key_requiem'then return requiem_key end end,
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
        lua = self.install(116)
        self.assertTrue(lua.eval('handlers[116]~=nil and handlers[114]==nil'))
        lua.execute('handlers[116]()')
        self.assertEqual(lua.eval('sent'), 'c')

    def test_requiem_defaults_to_v_and_supports_another_key(self):
        for configured, key in ((None, 118), (98, 98)):
            lua = self.install(requiem_key=configured)
            self.assertTrue(lua.eval(f'handlers[{key}]~=nil'))
            lua.execute(f'handlers[{key}]()')
            self.assertEqual(lua.eval('sent'), 'v')

    def test_requiem_key_requires_equipped_weapon_and_gameplay_focus(self):
        for change in ("ThePlayer.replica.combat.GetWeapon=function()return {prefab='spear'}end",
                       "ThePlayer.HUD.IsChatInputScreenOpen=function()return true end",
                       "TheFrontEnd.GetActiveScreen=function()return {name='ConsoleScreen'}end",
                       "IsPaused=function()return true end", "ThePlayer.HasTag=function()return true end"):
            with self.subTest(change=change):
                lua = self.install()
                lua.execute(change + ';handlers[118]()')
                self.assertIsNone(lua.eval('sent'))

    def test_other_characters_can_use_equipped_requiem(self):
        lua = self.install()
        lua.execute("ThePlayer.prefab='wilson';handlers[118]()")
        self.assertEqual(lua.eval('sent'), 'v')


if __name__ == '__main__':
    unittest.main()
