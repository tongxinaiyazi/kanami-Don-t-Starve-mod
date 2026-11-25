local M = {}
local Selection = {}
Selection.__index = Selection
local PAGE_SIZE = 8

function M.Open(keys, current)
    local page = 1
    for i, key in ipairs(keys) do
        if key == current then page = math.ceil(i/PAGE_SIZE); break end
    end
    return setmetatable({keys=keys, page=page, pages=math.max(1, math.ceil(#keys/PAGE_SIZE))}, Selection)
end

function Selection:Visible()
    local out = {}
    for i=(self.page-1)*PAGE_SIZE+1, math.min(self.page*PAGE_SIZE, #self.keys) do
        out[#out+1] = self.keys[i]
    end
    return out
end

function Selection:Choose(index)
    local key = self:Visible()[index]
    if key ~= nil then self.pending = key end
    return key ~= nil
end

function Selection:Confirm()
    return self.pending
end

function Selection:Page(delta)
    local nextpage = self.page + delta
    if nextpage < 1 or nextpage > self.pages then return false end
    self.page = nextpage
    return true
end

return M
