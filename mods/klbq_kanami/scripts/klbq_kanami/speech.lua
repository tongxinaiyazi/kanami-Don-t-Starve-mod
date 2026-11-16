local M = {}

local function Copy(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, item in pairs(value) do result[key] = Copy(item) end
    return result
end

function M.Bind(inst)
    if inst.prefab~="klbq_kanami" then return end
    local talker=inst.components and inst.components.talker
    if not talker then return end
    -- Native sayfn calls mod_str_fn for each raw line, then the global speech
    -- postprocessor, then speech_override_fn. Preserve our own UTF-8 line at
    -- that final display boundary without changing anyone else's speech.
    talker.mod_str_fn=function(message)
        talker._klbq_original_line=message
        return message
    end
    inst.speech_override_fn=function(_,processed)
        local raw=talker._klbq_original_line
        talker._klbq_original_line=nil
        return raw or processed
    end
end

function M.Install(strings,env)
    -- STRINGS has already been localized before modmain runs. Requiring a
    -- native speech module would return its shared cached table, so copy the
    -- localized generic voice and keep every nested table private to Kanami.
    local speech = Copy(strings.CHARACTERS.GENERIC or {})
    speech.ANNOUNCE_HUNGRY = "肚子饿了，先吃点东西再继续演奏吧。"
    speech.ANNOUNCE_COLD = "好冷……手指都快拨不动弦了。"
    speech.ANNOUNCE_HOT = "太热了，得找个阴凉的地方。"
    speech.ANNOUNCE_DUSK = "暮色到了，准备好今晚的灯火吧。"
    speech.ANNOUNCE_TORCH_OUT = "灯火熄了，得赶快找些光。"
    speech.ANNOUNCE_WET = "衣服湿了，弦也变得沉重了。"
    speech.ANNOUNCE_WETTER = "雨越来越大了。"
    speech.ANNOUNCE_SOAKED = "全身都湿透了，得避避雨。"
    speech.ANNOUNCE_CRAFTING_FAIL = "还少了一些材料。"
    -- Generic intentionally ships these as only_used_by_warly placeholders.
    -- Kanami has the chef tags, so native Eater legitimately requests them.
    speech.ANNOUNCE_EAT = {
        COOKED="热腾腾的，刚刚好。", DRIED="留一点给下一段旅程。",
        PREPARED="这道菜的味道很和谐。", RAW="也许烹饪后更好吃。",
        TASTY="真好吃！", YUCKY="这个味道……有点跑调。",
        GENERIC="补充好力气，继续演奏。",
        SAME_OLD_1="还是熟悉的味道。", SAME_OLD_2="再来一份也不错。",
        SAME_OLD_3="熟悉的旋律。", SAME_OLD_4="吃饱最重要。", SAME_OLD_5="谢谢款待。",
    }
    speech.ANNOUNCE_FOODMEMORY="熟悉的味道，让人安心。"
    speech.ACTIONFAIL_GENERIC = "这次没能合上节拍。"
    speech.DESCRIBE_GENERIC = "一件还没听过它故事的东西。"
    speech.DESCRIBE_TOODARK = "太暗了，什么也看不清。"
    speech.DESCRIBE_SMOLDERING = "快要烧起来了，离远一点。"
    speech.DESCRIBE = speech.DESCRIBE or {}
    speech.DESCRIBE.SKELETON = "一段已经停下的旋律。"
    speech.DESCRIBE.SKELETON_NOTPLAYER = "这里曾经有过一个生命。"
    -- Native GetPlayerDeathDescription formats player name first and cause
    -- second. Preserve both placeholders and leave names/chat untouched.
    local remains = "%s的旋律，被%s暂时打断了。"
    speech.DESCRIBE.SKELETON_PLAYER = {
        MALE = remains,
        FEMALE = remains,
        ROBOT = remains,
        DEFAULT = remains,
    }
    strings.CHARACTERS.KLBQ_KANAMI = speech
    if env and env.AddPrefabPostInit then
        env.AddPrefabPostInit("klbq_kanami",function(inst)
            M.Bind(inst)
            inst:DoTaskInTime(0,function() M.Bind(inst) end)
        end)
    end
    -- Uncovered strings use DST's existing GENERIC fallback in stringutil.lua.
    return speech
end

return M
