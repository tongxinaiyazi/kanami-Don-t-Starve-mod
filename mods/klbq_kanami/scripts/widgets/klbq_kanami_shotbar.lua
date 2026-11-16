local Widget=require("widgets/widget")
local Image=require("widgets/image")
local Rules=require("klbq_kanami/rules")
local ShotBar=Class(Widget,function(self,owner)
    Widget._ctor(self,"klbq_kanami_shotbar")
    self.owner=owner
    self.remaining=0
    self:SetClickable(false)
    self:SetScaleMode(SCALEMODE_PROPORTIONAL)
    self.root=self:AddChild(Widget("bar"))
    local border=self.root:AddChild(Image("images/global.xml","square.tex"))
    border:SetSize(94,10);border:SetTint(.12,.09,.15,.96)
    local background=self.root:AddChild(Image("images/global.xml","square.tex"))
    background:SetSize(90,6);background:SetTint(.3,.22,.35,1)
    self.fill=self.root:AddChild(Image("images/global.xml","square.tex"))
    self.fill:SetHRegPoint(ANCHOR_LEFT);self.fill:SetPosition(-45,0)
    self.fill:SetTint(1,.59,.82,1)
    self:Hide();self:StartUpdating()
end)
function ShotBar:OnUpdate(dt)
    local p=self.owner
    if not p or not p:IsValid() or p:HasTag("playerghost") or not p._klbq_shotcd then self:Hide();return end
    if TheNet:IsServerPaused() then return end
    local raw=p._klbq_shotcd:value()
    if raw~=self.last then self.remaining=raw/10;self.last=raw
    else self.remaining=math.max(0,self.remaining-(dt or 0)) end
    if self.remaining<=0 then self:Hide();return end
    self:Show()
    local progress=math.max(0,math.min(1,1-self.remaining/Rules.SHOT_COOLDOWN))
    self.fill:SetSize(math.max(.01,90*progress),6)
    local offset=p._klbq_string:value() and -250 or -190
    self:SetPosition(TheSim:GetScreenPos(p.AnimState:GetSymbolPosition("headbase",0,offset,0)))
end
return ShotBar
