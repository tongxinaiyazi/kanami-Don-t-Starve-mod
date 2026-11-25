"""The score lists several regions and only commits an explicit confirmation."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/python-deps"))
from lupa.lua51 import LuaRuntime


class ScoreSelection(unittest.TestCase):
    def test_selection_survives_page_change_and_requires_confirm(self):
        lua = LuaRuntime()
        src = ROOT / "mods/klbq_kanami/scripts/klbq_kanami/region_selection.lua"
        self.assertTrue(src.is_file(), "missing multi-region selector")
        lua.globals().selection = lua.execute(src.read_text(encoding="utf-8"))
        lua.execute('''
            keys={"grass","forest","rock","marsh","desert","moon","ruins","day","night"}
            local picker=selection.Open(keys,"forest")
            assert(#picker:Visible()==8 and picker:Visible()[2]=="forest")
            assert(picker:Confirm()==nil)
            picker:Choose(5)
            assert(picker:Page(1) and #picker:Visible()==1 and picker:Visible()[1]=="night")
            assert(picker:Confirm()=="desert")
            assert(not picker:Page(1) and not picker:Choose(2))
            picker:Choose(1)
            assert(picker:Confirm()=="night")
            assert(picker:Page(-1) and #picker:Visible()==8)
            local last=selection.Open(keys,"night")
            assert(last.page==2 and #last:Visible()==1)
            assert(#selection.Open({},nil):Visible()==0)
        ''')

    def test_widget_lists_multiple_entries_and_commits_only_via_confirm_button(self):
        lua = LuaRuntime()
        scripts = ROOT / "mods/klbq_kanami/scripts"
        lua.globals().package.loaded["klbq_kanami/region_selection"] = lua.execute(
            (scripts / "klbq_kanami/region_selection.lua").read_text(encoding="utf-8"))
        lua.execute('''
            package.loaded["klbq_kanami/regions"]={Name=function(key) return key end}
            local methods={
                SetClickable=function() end,SetFocusChangeDir=function() end,SetFocus=function() end,
                AddChild=function(_, child) return child end, SetSize=function() end, SetScaleMode=function() end,
                SetPosition=function() end, SetVAnchor=function() end, SetHAnchor=function() end,
                SetTint=function() end, ForceImageSize=function() end, SetFont=function() end, SetTextSize=function() end,
                SetImageNormalColour=function() end, SetImageFocusColour=function() end,
                SetImageDisabledColour=function() end,SetImageSelectedColour=function() end,
                SetTextColour=function() end,SetTextFocusColour=function() end,
                SetTextDisabledColour=function() end, SetTextSelectedColour=function() end,
                SetText=function(s,text) s.label=text end, SetString=function(s,text) s.label=text end,
                SetOnClick=function(s,fn) s.click=fn end,
                Show=function(s) s.visible=true end, Hide=function(s) s.visible=false end,
                Enable=function(s) s.enabled=true end, Disable=function(s) s.enabled=false end,
                Select=function(s) s.selected=true end, Unselect=function(s) s.selected=false end,
            }
            local function Widget()
                local w=setmetatable({},{__index=methods})
                w.image=setmetatable({},{__index=methods})
                return w
            end
            local Screen=setmetatable({_ctor=function() end,OnControl=function() return false end},{__index=methods})
            function Class(base, ctor)
                local cls=setmetatable({_base=base},{__index=base})
                cls.__index=cls
                return setmetatable(cls,{__index=base,__call=function(c,...)
                    local obj=setmetatable({},c); ctor(obj,...);return obj
                end})
            end
            for _,key in ipairs({"widget","image","imagebutton","text"}) do package.loaded["widgets/"..key]=Widget end
            package.loaded["widgets/screen"]=Screen
            MOVE_UP,MOVE_DOWN,MOVE_LEFT,MOVE_RIGHT=1,2,3,4
            TheInput={ControllerAttached=function() return false end}
            TheFrontEnd={PopScreen=function(_,screen) screen.closed=true end}
        ''')
        lua.globals().screen = lua.execute(
            (scripts / "widgets/klbq_regionscreen.lua").read_text(encoding="utf-8"))
        lua.execute('''
            local result
            local picker=screen({"蒸汽喷口","暗影喷口","沙漠","森林","洞穴"},"蒸汽喷口",function(key) result=key end)
            assert(picker.rows[1].label=="蒸汽喷口 · 当前" and picker.rows[5].visible)
            assert(picker.rows[6].visible==false and picker.apply.enabled==false)
            picker.rows[2].click()
            assert(picker.rows[2].selected and picker.status.label=="待确认：暗影喷口")
            assert(not result and not picker.closed and picker.apply.enabled)
            picker.apply.click()
            assert(result=="暗影喷口" and picker.closed)
        ''')
