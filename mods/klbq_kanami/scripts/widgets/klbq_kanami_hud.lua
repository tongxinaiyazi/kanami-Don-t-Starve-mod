local Widget=require("widgets/widget")
local Text=require("widgets/text")
local ImageButton=require("widgets/imagebutton")
local HUD=Class(Widget,function(self,owner,cast,keys)
    Widget._ctor(self,"klbq_kanami_skills")
    self.owner=owner
    self.cells={}
    local names={z="交响爆音",x="演出开始",passive="旋律回响",revive="双生共鸣"}
    local entries={{"z","klbq_skill_z"},{"x","klbq_skill_x"},
        {"passive","klbq_skill_echo"},{"revive","klbq_skill_revive"}}
    for i,row in ipairs(entries) do
        local w=self:AddChild(Widget("skill_"..row[1]));w:SetPosition((i-1)*58,0)
        local button=w:AddChild(ImageButton("images/klbq_kanami_items.xml",row[2]..".tex"))
        button:SetScale(.38)
        if keys[row[1]] then
            button:SetOnClick(function() cast(row[1]) end)
            button:SetHoverText(names[row[1]].." · "..string.upper(string.char(keys[row[1]])))
        else
            button:SetClickable(false)
            if names[row[1]] then button:SetHoverText(names[row[1]]) end
        end
        local number=w:AddChild(Text(BODYTEXTFONT,26,""));number:SetPosition(0,-33)
        number:SetRegionSize(62,30);number:SetColour(1,.92,.98,1)
        self.cells[row[1]]={button=button,number=number}
    end
    self:StartUpdating()
end)
local function Seconds(owner,name)
    local field=owner["_klbq_"..name]
    return field and math.ceil(field:value()/10) or 0
end
function HUD:OnUpdate()
    local p=self.owner
    if not p or not p:IsValid() or not p._klbq_z then return end
    local zactive=p._klbq_z:value()
    self.cells.z.number:SetString(zactive and "∞" or "0")
    self.cells.z.button:SetImageNormalColour(zactive and 1 or .6,zactive and .65 or .6,1,1)
    for _,key in ipairs({"x"}) do
        local active=Seconds(p,key.."time");local cd=Seconds(p,key.."cd")
        self.cells[key].number:SetString(tostring(active>0 and active or cd))
        self.cells[key].number:SetColour(active>0 and 1 or .9,active>0 and .6 or .85,1,1)
        self.cells[key].button:SetImageNormalColour(cd>0 and active==0 and .5 or 1,cd>0 and active==0 and .5 or .8,1,1)
    end
    local passive=p._klbq_passivecd:value()/10
    self.cells.passive.number:SetString(passive>0 and string.format("%.1f",passive) or "0")
    self.cells.revive.number:SetString(p:HasTag("playerghost") and tostring(Seconds(p,"revive")) or "0")
    self.cells.revive.button:SetImageNormalColour(p._klbq_protect:value() and 1 or .65,.65,1,1)
end
return HUD
