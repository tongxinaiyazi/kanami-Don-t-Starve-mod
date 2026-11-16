"""Character speech regressions use the installed DST strings and formatter."""
import ast
import re
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/python-deps'))
from lupa.lua51 import LuaRuntime

GAME = Path(r"E:/steam/steamapps/common/Don't Starve Together/data/databundles/scripts.zip")


def po_strings(source):
    """Read the native PO values without embedding translated game dialogue."""
    values = {}
    context = None
    collecting = False
    text = ''
    for line in source.splitlines() + ['']:
        if line.startswith('msgctxt '):
            context = ast.literal_eval(line[8:])
        elif line.startswith('msgstr '):
            collecting = True
            text = ast.literal_eval(line[7:])
        elif collecting and line.startswith('"'):
            text += ast.literal_eval(line)
        elif collecting:
            if context and text:
                values[context] = text
            collecting = False
    return values


class Speech(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(GAME) as archive:
            cls.native = {
                name: archive.read('scripts/' + name).decode('utf-8-sig')
                for name in ('speech_wilson.lua', 'speech_willow.lua', 'stringutil.lua',
                             'translator.lua', 'componentutil.lua', 'languages/chinese_s.po')
            }
        cls.translations = po_strings(cls.native['languages/chinese_s.po'])

    def setUp(self):
        self.lua = lua = LuaRuntime(unpack_returned_tuples=True)
        from resource_fixture import preload_resources
        preload_resources(lua)
        lua.execute("package.path = ... .. '/mods/klbq_kanami/scripts/?.lua;' .. package.path",
                    ROOT.as_posix())
        lua.execute('''
            STRINGS={CHARACTER_TITLES={},CHARACTER_NAMES={},CHARACTER_DESCRIPTIONS={},
                CHARACTER_QUOTES={},CHARACTER_SURVIVABILITY={},NAMES={},
                CHARACTERS={},SKIN_NAMES={},RECIPE_DESC={}}
            env=setmetatable({GLOBAL=_G},{__index=_G});env.env=env
            GetModConfigData=function() return nil end
            Asset=function() return {} end
            AddMinimapAtlas=function() end;AddModCharacter=function() end
            RegisterInventoryItemAtlas=function() end
            AddPrefabPostInit=function() end
        ''')
        for name, filename in (('GENERIC', 'speech_wilson.lua'), ('WILLOW', 'speech_willow.lua')):
            lua.globals().STRINGS.CHARACTERS[name] = lua.execute(self.native[filename])
        # Run the game's recursive translation function against its installed PO.
        lua.globals().translations = lua.table_from(self.translations)
        lua.execute('LanguageTranslator={GetTranslatedString=function(s,k) return translations[k] end}')
        translator = self.native['translator.lua']
        start = translator.index('local function DoTranslateStringTable(')
        end = translator.index('LanguageTranslator = Translator()', start)
        lua.execute(translator[start:end] + '\nTranslateStringTable(STRINGS)')
        lua.execute('package.loaded.speech_willow=STRINGS.CHARACTERS.WILLOW')
        lua.execute(self.native['stringutil.lua'])
        for name in ('technology', 'chef', 'curse', 'visual', 'bag', 'domain'):
            lua.execute('package.preload[...] = function() return {Install=function() end} end',
                        'klbq_kanami/' + name)
        speech = (ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/speech.lua').read_text(encoding='utf-8-sig')
        rules = (ROOT / 'mods/klbq_kanami/scripts/klbq_kanami/rules.lua').read_text(encoding='utf-8-sig')
        lua.execute("package.preload['klbq_kanami/rules']=function() " + rules + '\nend')
        lua.execute("package.preload['klbq_kanami/speech']=function() " + speech + '\nend')
        # Execute the real registration section, before recipe/gameplay setup.
        source = (ROOT / 'mods/klbq_kanami/modmain.lua').read_text(encoding='utf-8-sig')
        lua.execute('setfenv(assert(loadstring(...)),env)()', source[:source.index('-- Crafting registration')])

    def test_character_speech_is_independent_at_every_table_level(self):
        self.assertFalse(self.lua.eval('STRINGS.CHARACTERS.KLBQ_KANAMI==STRINGS.CHARACTERS.WILLOW'))
        self.assertFalse(self.lua.eval('STRINGS.CHARACTERS.KLBQ_KANAMI==STRINGS.CHARACTERS.GENERIC'))
        self.assertTrue(self.lua.eval('''STRINGS.CHARACTERS.KLBQ_KANAMI.DESCRIBE.EVERGREEN
            ~=STRINGS.CHARACTERS.GENERIC.DESCRIBE.EVERGREEN'''))
        self.lua.execute('''
            before=STRINGS.CHARACTERS.GENERIC.DESCRIBE.EVERGREEN.BURNING
            STRINGS.CHARACTERS.KLBQ_KANAMI.DESCRIBE.EVERGREEN.BURNING='独立检查语'
        ''')
        self.assertEqual(self.lua.eval('STRINGS.CHARACTERS.GENERIC.DESCRIBE.EVERGREEN.BURNING'),
                         self.lua.eval('before'))

    def test_common_speech_and_native_inspection_are_chinese(self):
        self.assertIn('肚子', self.lua.eval('GetString("klbq_kanami","ANNOUNCE_HUNGRY")'))
        self.lua.execute('item={prefab="evergreen",components={inspectable={}}}')
        self.assertEqual(self.lua.eval('GetDescription("klbq_kanami",item,"BURNING")'),
                         self.lua.eval('STRINGS.CHARACTERS.GENERIC.DESCRIBE.EVERGREEN.BURNING'))
        self.assertRegex(self.lua.eval('GetDescription("klbq_kanami",item,"BURNING")'), r'[\u4e00-\u9fff]')
        self.assertEqual(self.lua.eval('GetActionFailString("klbq_kanami","BUILD","BUSY_STATION")'),
                         self.lua.eval('STRINGS.CHARACTERS.GENERIC.ACTIONFAIL.BUILD.BUSY_STATION'))

    def test_missing_new_strings_keep_native_generic_fallback(self):
        self.lua.execute('''
            STRINGS.CHARACTERS.GENERIC.ANNOUNCE_FUTURE_KLBQ_TEST='未来的旋律。'
            STRINGS.CHARACTERS.GENERIC.DESCRIBE.KLBQ_FUTURE_TEST='一件新事物。'
            item={prefab='klbq_future_test',components={inspectable={}}}
        ''')
        self.assertEqual(self.lua.eval('GetString("klbq_kanami","ANNOUNCE_FUTURE_KLBQ_TEST")'), '未来的旋律。')
        self.assertEqual(self.lua.eval('GetDescription("klbq_kanami",item)'), '一件新事物。')

    def test_chef_food_announcements_never_use_native_warly_placeholders(self):
        text=self.lua.eval('GetString("klbq_kanami","ANNOUNCE_EAT","PREPARED")')
        self.assertNotIn('only_used_by_warly',text)
        self.assertRegex(text,r'[\u4e00-\u9fff]')
        self.assertNotIn('only_used_by_warly',self.lua.eval('GetString("klbq_kanami","ANNOUNCE_FOODMEMORY")'))

    def test_character_display_preserves_original_line_after_speech_postprocessing(self):
        self.lua.execute('''
            native_line='最后一个音符落下，便是这场演出的谢幕。'
            actor={prefab='klbq_kanami',components={talker={}}}
            local m=require('klbq_kanami/speech')
            if m.Bind then m.Bind(actor) end
            local t=actor.components.talker
            local first=t.mod_str_fn and t.mod_str_fn(native_line) or native_line
            local garbled='末喔唉日齐齐浩喔唉劫：'..first
            displayed=actor.speech_override_fn and actor.speech_override_fn(actor,garbled) or garbled
        ''')
        self.assertEqual(self.lua.eval('displayed'),self.lua.eval('native_line'))

    def test_player_death_description_preserves_native_name_and_cause_formatting(self):
        source = self.native['componentutil.lua']
        start = source.index('function GetPlayerDeathDescription(')
        end = start + re.search(r'^end\s*$', source[start:], re.M).end()
        self.lua.execute(source[start:end])
        self.lua.execute('''
            CHARACTER_GENDERS={FEMALE={'klbq_kanami'}}
            table.contains=function(t,v) for _,x in ipairs(t) do if x==v then return true end end end
            viewer={prefab='klbq_kanami',components={talker={}},HasTag=function() return false end}
            remains={prefab='skeleton_player',char='klbq_kanami',playername='演奏者_テスト',
                cause='skeleton',components={inspectable={}}}
            STRINGS.NAMES.SKELETON='骷髅'
        ''')
        result = self.lua.eval('GetPlayerDeathDescription(remains,viewer)')
        self.assertIn('演奏者_テスト', result)
        self.assertIn('骷髅', result)
        self.assertIn('旋律', result)
        self.assertNotIn('生命之火', result)
        self.assertNotIn('%s', result)
        for gender in ('MALE', 'FEMALE', 'ROBOT', 'DEFAULT'):
            self.assertEqual(self.lua.globals().STRINGS.CHARACTERS.KLBQ_KANAMI.DESCRIBE.SKELETON_PLAYER[gender].count('%s'), 2)
        self.lua.execute("remains.pkname='玩家%_テスト'")
        self.assertIn('玩家%_テスト', self.lua.eval('GetPlayerDeathDescription(remains,viewer)'))
        self.assertEqual(self.lua.eval('remains.playername'), '演奏者_テスト')
        self.assertEqual(self.lua.eval('remains.cause'), 'skeleton')

    def test_ammo_crafting_and_inspection_use_character_flavour_without_mechanics(self):
        for name in ('KLBQ_AMMO_HEART', 'KLBQ_AMMO_FATE', 'KLBQ_AMMO_DOOM'):
            with self.subTest(prefab=name):
                self.lua.execute('item={prefab=...,components={inspectable={}}}', name.lower())
                text = self.lua.eval('GetDescription("klbq_kanami",item)')
                self.assertRegex(text, r'心意|命运|演出')
                self.assertEqual(text,self.lua.globals().STRINGS.RECIPE_DESC[name])
                self.assertEqual(text,self.lua.globals().STRINGS.CHARACTERS.GENERIC.DESCRIBE[name])
                for hint in ('伤害', '处决', '%', '50', '300', '绕过', '限伤', '限频', '站在', '靠近', '制作', '给予', '放在地上', '流程'):
                    self.assertNotIn(hint, text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
