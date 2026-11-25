local Screen = require("widgets/screen")
local Widget = require("widgets/widget")
local Image = require("widgets/image")
local ImageButton = require("widgets/imagebutton")
local Text = require("widgets/text")
local Selection = require("klbq_kanami/region_selection")
local Regions = require("klbq_kanami/regions")
local ATLAS, SQUARE = "images/global.xml", "square.tex"
local TEXT = {.91,.94,1,1}
local MUTED = {.67,.75,.83,1}
local ACCENT = {.53,.90,.89,1}

local function Rect(parent, w,h,x,y, colour)
    local img = parent:AddChild(Image(ATLAS, SQUARE))
    img:SetSize(w,h)
    img:SetPosition(x,y)
    img:SetTint(unpack(colour))
    img:SetClickable(false)
    return img
end

local function Label(parent, size,x,y, message, colour)
    local text = parent:AddChild(Text(NEWFONT, size, message, colour))
    text:SetPosition(x,y)
    text:SetClickable(false)
    return text
end

local function Button(parent, w,h,x,y, label, fn)
    local b = parent:AddChild(ImageButton(ATLAS, SQUARE, SQUARE, SQUARE, SQUARE, SQUARE))
    b.scale_on_focus = false
    b.move_on_click = false
    b:ForceImageSize(w,h)
    b:SetPosition(x,y)
    b:SetFont(NEWFONT)
    b:SetTextSize(25)
    b:SetTextColour(TEXT)
    b:SetTextFocusColour({1,1,1,1})
    b:SetTextDisabledColour(MUTED)
    b:SetTextSelectedColour({.09,.15,.20,1})
    b:SetImageNormalColour(.16,.22,.32,1)
    b:SetImageFocusColour(.23,.39,.49,1)
    b:SetImageDisabledColour(.12,.15,.22,1)
    b:SetImageSelectedColour(unpack(ACCENT))
    b:SetText(label)
    b:SetOnClick(fn)
    return b
end

local RegionsScreen = Class(Screen, function(self, keys, current, confirm)
    Screen._ctor(self, "KanamiRegionScreen")
    self.selection = Selection.Open(keys, current)
    self.current = current
    self.confirm = confirm
    local shade = self:AddChild(ImageButton(ATLAS, SQUARE, SQUARE, SQUARE))
    shade.scale_on_focus = false
    shade.image:SetScaleMode(SCALEMODE_FILLSCREEN)
    shade:SetImageNormalColour(0,0,0,.56)
    shade:SetImageFocusColour(0,0,0,.56)
    shade:SetOnClick(function() end)
    local root = self:AddChild(Widget("Region score panel"))
    root:SetVAnchor(ANCHOR_MIDDLE)
    root:SetHAnchor(ANCHOR_MIDDLE)
    root:SetScaleMode(SCALEMODE_PROPORTIONAL)
    Rect(root,804,520,0,0,{.28,.43,.53,1})
    Rect(root,800,516,0,0,{.07,.10,.17,1})
    Rect(root,750,2,0,149,{.23,.38,.49,1})
    Label(root,37,0,207,"选择拓印地区",TEXT)
    Label(root,23,0,176,"当前使用："..(Regions.Name(current) or "未选择"),MUTED)
    self.rows = {}
    for i=1,8 do
        local index = i
        local x = i % 2 == 1 and -186 or 186
        local y = 109 - 55*math.floor((i-1)/2)
        self.rows[i] = Button(root,350,46,x,y,"",function()
            self.selection:Choose(index)
            self:Refresh()
        end)
    end
    self.status = Label(root,23,0,-111,"",ACCENT)
    self.page = Label(root,23,0,-157,"",MUTED)
    self.prev = Button(root,118,36,-154,-157,"上一页",function()
        if self.selection:Page(-1) then self:Refresh(true) end
    end)
    self.next = Button(root,118,36,154,-157,"下一页",function()
        if self.selection:Page(1) then self:Refresh(true) end
    end)
    self.back = Button(root,146,45,-91,-214,"返回",function() self:Close() end)
    self.apply = Button(root,176,45,91,-214,"确认地区",function()
        local key = self.selection:Confirm()
        if key ~= nil then self:Close(); self.confirm(key) end
    end)
    self.apply:SetImageNormalColour(.16,.35,.43,1)
    self:Refresh(true)
end)

function RegionsScreen:Refresh(focus)
    local keys = self.selection:Visible()
    local pending = self.selection:Confirm()
    for i,b in ipairs(self.rows) do
        local key = keys[i]
        if key then
            b:Show()
            b:Unselect()
            b:SetText(Regions.Name(key)..(key == self.current and " · 当前" or ""))
            if key == pending then b:Select() end
            local left = i % 2 == 0 and self.rows[i-1] or nil
            local right = i % 2 == 1 and keys[i+1] and self.rows[i+1] or nil
            b:SetFocusChangeDir(MOVE_LEFT,left)
            b:SetFocusChangeDir(MOVE_RIGHT,right)
            b:SetFocusChangeDir(MOVE_UP,i > 2 and self.rows[i-2] or nil)
            local pager = (self.selection.page > 1 and self.prev)
                or (self.selection.page < self.selection.pages and self.next) or self.back
            b:SetFocusChangeDir(MOVE_DOWN,keys[i+2] and self.rows[i+2] or pager)
        else
            b:Hide()
        end
    end
    self.status:SetString(pending and ("待确认："..Regions.Name(pending)) or "点选地区，再确认")
    self.page:SetString(string.format("%d / %d",self.selection.page,self.selection.pages))
    if self.selection.pages == 1 then self.prev:Hide(); self.next:Hide(); self.page:Hide() end
    if self.selection.page > 1 then self.prev:Enable() else self.prev:Disable() end
    if self.selection.page < self.selection.pages then self.next:Enable() else self.next:Disable() end
    if pending then self.apply:Enable() else self.apply:Disable() end
    self.back:SetFocusChangeDir(MOVE_RIGHT,self.apply)
    self.apply:SetFocusChangeDir(MOVE_LEFT,self.back)
    local last = self.rows[#keys]
    self.back:SetFocusChangeDir(MOVE_UP,last)
    self.apply:SetFocusChangeDir(MOVE_UP,last)
    self.back:SetFocusChangeDir(MOVE_LEFT,self.selection.page > 1 and self.prev or nil)
    self.apply:SetFocusChangeDir(MOVE_RIGHT,self.selection.page < self.selection.pages and self.next or nil)
    self.prev:SetFocusChangeDir(MOVE_RIGHT,self.selection.page < self.selection.pages and self.next or nil)
    self.next:SetFocusChangeDir(MOVE_LEFT,self.selection.page > 1 and self.prev or nil)
    for _,control in ipairs({self.prev,self.next}) do
        control:SetFocusChangeDir(MOVE_UP,last)
        control:SetFocusChangeDir(MOVE_DOWN,self.back)
    end
    self.default_focus = #keys > 0 and self.rows[1] or self.back
    if focus and TheInput:ControllerAttached() then self.default_focus:SetFocus() end
end

function RegionsScreen:Close()
    TheFrontEnd:PopScreen(self)
end

function RegionsScreen:OnControl(control, down)
    if RegionsScreen._base.OnControl(self,control,down) then return true end
    if control == CONTROL_CANCEL and not down then self:Close(); return true end
end

return RegionsScreen
