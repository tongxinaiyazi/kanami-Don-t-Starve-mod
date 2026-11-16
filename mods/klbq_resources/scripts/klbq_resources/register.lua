local catalog = require("klbq_resources/catalog")

local function RequireTable(value, label)
    assert(type(value) == "table", "klbq_resources: " .. label .. " must be a table")
    return value
end

local function OptionalTable(value, label)
    return value == nil and {} or RequireTable(value, label)
end

local function Install(mod_env)
    local env = RequireTable(mod_env, "mod environment")
    local global = RequireTable(env.GLOBAL, "GLOBAL")
    local owner = rawget(global, "KLBQ_RESOURCES_OWNER")
    if owner ~= nil then
        RequireTable(owner, "KLBQ_RESOURCES_OWNER")
        assert(owner.version == catalog.VERSION,
            "klbq_resources: version conflict; installed " .. tostring(owner.version)
            .. " owned by " .. tostring(owner.owner) .. ", requested " .. catalog.VERSION)
        return false
    end

    -- Validate and prepare every local input before changing a host or claiming ownership.
    -- The native Asset constructor is a callable Class table, not a function.
    -- Construct all assets below before any host mutation; invalid constructors fail there.
    assert(type(env.RegisterInventoryItemAtlas) == "function",
        "klbq_resources: RegisterInventoryItemAtlas must be a function")
    local prefabs = OptionalTable(env.PrefabFiles, "PrefabFiles")
    local assets = OptionalTable(env.Assets, "Assets")
    local strings = RequireTable(global.STRINGS, "STRINGS")
    local names = OptionalTable(strings.NAMES, "STRINGS.NAMES")
    local characters = OptionalTable(strings.CHARACTERS, "STRINGS.CHARACTERS")
    local generic = OptionalTable(characters.GENERIC, "STRINGS.CHARACTERS.GENERIC")
    local describe = OptionalTable(generic.DESCRIBE, "STRINGS.CHARACTERS.GENERIC.DESCRIBE")
    local additions = {
        env.Asset("ANIM", catalog.ANIM),
        env.Asset("ATLAS", catalog.ATLAS),
        env.Asset("IMAGE", catalog.TEXTURE),
    }
    assert(#additions == 3, "klbq_resources: Asset did not return all required assets")

    local has_prefab = false
    for _, prefab in ipairs(prefabs) do
        if prefab == catalog.PREFAB_FILE then
            has_prefab = true
            break
        end
    end

    for _, definition in ipairs(catalog.items) do
        env.RegisterInventoryItemAtlas(catalog.ATLAS, definition.prefab .. ".tex")
    end
    if not has_prefab then
        prefabs[#prefabs + 1] = catalog.PREFAB_FILE
    end
    for _, asset in ipairs(additions) do
        assets[#assets + 1] = asset
    end
    for _, definition in ipairs(catalog.items) do
        local key = string.upper(definition.prefab)
        names[key] = definition.name
        describe[key] = definition.inspect
    end
    env.PrefabFiles = prefabs
    env.Assets = assets
    strings.NAMES = names
    strings.CHARACTERS = characters
    characters.GENERIC = generic
    generic.DESCRIBE = describe
    rawset(global, "KLBQ_RESOURCES_OWNER", {
        version = catalog.VERSION,
        owner = type(env.modname) == "string" and env.modname or "klbq_resources",
    })
    return true
end

return { Install = Install }
