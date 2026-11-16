-- All nonstandard boss integration belongs here. Void Realm 2.3.2 has
-- obfuscated logic: standard health support is NOT a compatibility claim.
local M = {}
local bulletscopes = {}

local function Pack(...)
    return {n=select("#",...),...}
end
local function HappyArmorSource(fn)
    local info=debug.getinfo(fn,"S")
    local source=info and info.source and info.source:gsub("\\","/"):lower() or ""
    return source:find("/workshop%-2886753796/epic/epic_armor%.lua$")~=nil
        or source:find("/2886753796/epic/epic_armor%.lua$")~=nil
end
local function FindHappyArmor(root,inst)
    if not inst or type(inst.epicarmor2hm)~="table" or not debug
        or not debug.getinfo or not debug.getupvalue or not debug.setupvalue then return end
    local visited,count={},0
    local function Visit(fn,parent,index)
        if type(fn)~="function" or visited[fn] or count>=64 then return end
        visited[fn]=true;count=count+1
        local values,children={},{}
        local i=1
        while true do
            local name,value=debug.getupvalue(fn,i)
            if name==nil then break end
            values[name]=value
            if type(value)=="function" then children[#children+1]={value,i,name} end
            i=i+1
        end
        -- Match the installed EpicArmor closure, not an arbitrary SetVal
        -- override. Its sibling shadowworld form/death wrapper must survive.
        if HappyArmorSource(fn) and values.inst==inst
            and type(values.oldSetVal)=="function" and type(values.doDeltaList)=="function"
            and HappyArmorSource(values.doDeltaList) and type(values.epic_data)=="table" then
            return {fn=fn,base=values.oldSetVal,parent=parent,index=index}
        end
        -- Prefer the normal delegation chain before inspecting other helpers.
        for _,child in ipairs(children) do
            if child[3]=="oldSetVal" then
                local found=Visit(child[1],fn,child[2]);if found then return found end
            end
        end
        for _,child in ipairs(children) do
            if child[3]~="oldSetVal" then
                local found=Visit(child[1],fn,child[2]);if found then return found end
            end
        end
    end
    return Visit(root)
end
local function InvokeBullet(scope,val,cause,afflicter)
    local tokens=scope.tokens
    tokens[#tokens+1]={depth=scope.depth+1,pending=true,cause=cause,afflicter=afflicter}
    local result=Pack(pcall(scope.dispatch,scope.health,val,cause,afflicter))
    tokens[#tokens]=nil
    if not result[1] then error(result[2],0) end
    return unpack(result,2,result.n)
end

-- One bullet's canonical health transition. HappyPatch 2.8.14.84 places its
-- time gate inside SetVal, below ordinary cap/DoDelta wrappers. Temporarily
-- bypass only that identified closure, preserving native SetVal, minhealth,
-- shadow form transitions and every other wrapper in the delegation chain.
function M.BulletSetVal(health,val,cause,afflicter)
    local running=bulletscopes[health]
    if running then return InvokeBullet(running,val,cause,afflicter) end
    local adapter=FindHappyArmor(health.SetVal,health.inst)
    if not adapter then return health:SetVal(val,cause,afflicter) end
    local scope={health=health,depth=0,tokens={}}
    local function BulletArmor(self,value,why,who,...)
        local token=scope.tokens[#scope.tokens]
        if token and token.pending and scope.depth==token.depth and self==health
            and why==token.cause and who==token.afflicter and value<=self.currenthealth then
            -- Consume before native callbacks: nested ordinary hits, even by
            -- the same attacker, retain their original EpicArmor defense.
            token.pending=false
            return adapter.base(self,value,why,who,...)
        end
        return adapter.fn(self,value,why,who,...)
    end
    local oldslot=rawget(health,"SetVal")
    local root=health.SetVal
    if adapter.parent then
        debug.setupvalue(adapter.parent,adapter.index,BulletArmor)
    else
        root=BulletArmor
    end
    scope.dispatch=function(...)
        scope.depth=scope.depth+1
        local result=Pack(pcall(root,...))
        scope.depth=scope.depth-1
        if not result[1] then error(result[2],0) end
        return unpack(result,2,result.n)
    end
    health.SetVal=scope.dispatch
    bulletscopes[health]=scope
    local result=Pack(pcall(InvokeBullet,scope,val,cause,afflicter))
    bulletscopes[health]=nil
    if health.SetVal==scope.dispatch then health.SetVal=oldslot end
    if adapter.parent then
        local _,current=debug.getupvalue(adapter.parent,adapter.index)
        if current==BulletArmor then debug.setupvalue(adapter.parent,adapter.index,adapter.fn) end
    end
    if not result[1] then error(result[2],0) end
    return unpack(result,2,result.n)
end

function M.Resolve(target)
    -- Arbitrary multipart redirect callbacks may mutate state and must not be
    -- guessed. Vanilla combat follows them for normal/planar damage; true and
    -- execute target the selected health component until an adapter is tested.
    return target
end
function M.Health(target)
    target = M.Resolve(target)
    return target and target.components and target.components.health, target
end
return M
