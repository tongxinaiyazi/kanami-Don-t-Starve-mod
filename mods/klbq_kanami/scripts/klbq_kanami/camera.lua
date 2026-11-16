local M={}
local function Pack(...) return {n=select("#",...),...} end
function M.Start(camera,distance)
    if not camera or not camera.SetDistance then return nil end
    local s={camera=camera,before=camera.distancetarget,maxdist=camera.maxdist,pitch=camera.maxdistpitch,own=true,methods={}}
    s.appliedmax=math.max(camera.maxdist or 50,120)
    camera.maxdist=s.appliedmax
    s.appliedpitch=75;camera.maxdistpitch=75
    camera:SetDistance(distance or 80)
    s.last=camera.distancetarget
    for _,name in ipairs({"SetDistance","ZoomIn","ZoomOut","ContinuousZoomDelta"}) do
        if type(camera[name])=="function" then
            local old=camera[name]
            local wrapper=function(self,...)
                if name=="SetDistance" then s.own=false end
                local result=Pack(old(self,...))
                s.last=self.distancetarget
                return unpack(result,1,result.n)
            end
            s.methods[name]={old=old,wrapper=wrapper}
            camera[name]=wrapper
        end
    end
    return s
end
function M.Stop(s)
    if not s then return end
    local c=s.camera
    -- Direct writes and subsequently installed wrappers belong to other mods.
    local distance_owned=s.own and c.distancetarget==s.last
        and (not s.methods.SetDistance or c.SetDistance==s.methods.SetDistance.wrapper)
    for name,method in pairs(s.methods) do if c[name]==method.wrapper then c[name]=method.old end end
    if distance_owned then c:SetDistance(s.before) end
    if c.maxdist==s.appliedmax then c.maxdist=s.maxdist end
    if c.maxdistpitch==s.appliedpitch then c.maxdistpitch=s.pitch end
end
return M
