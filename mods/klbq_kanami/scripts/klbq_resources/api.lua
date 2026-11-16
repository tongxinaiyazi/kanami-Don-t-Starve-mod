local catalog = require("klbq_resources/catalog")

local function GetDefinition(key_or_prefab)
    if type(key_or_prefab) ~= "string" then
        return nil
    end
    return catalog.by_key[key_or_prefab] or catalog.by_prefab[key_or_prefab]
end

local function GetPrefab(key_or_prefab)
    local definition = GetDefinition(key_or_prefab)
    return definition ~= nil and definition.prefab or nil
end

local function IsResource(value)
    local kind = type(value)
    if kind == "table" or kind == "userdata" then
        local ok, prefab = pcall(function() return value.prefab end)
        if not ok then
            return false
        end
        value = prefab
    end
    return type(value) == "string" and catalog.by_prefab[value] ~= nil
end

return {
    API_VERSION = catalog.API_VERSION,
    GetDefinition = GetDefinition,
    GetPrefab = GetPrefab,
    IsResource = IsResource,
}
