-- Native Warly's three common tags grant cookware, recipes and fast cooking.
-- His dietary restrictions, foodmemory and hunger rate are deliberately absent.
local M = {}
local policy = { stale = .5, spoiled = .1 }
local foodname = "klbq_omurice"
local recipes

local function Pack(...)
    return { n = select("#", ...), ... }
end

local function IsKanami(inst)
    return inst ~= nil and inst:HasTag("klbq_kanami")
end

function M.Common(inst)
    inst:AddTag("masterchef")
    inst:AddTag("professionalchef")
    inst:AddTag("expertchef")
end

-- Apply an additional penalty after native spoilage. Zero and negative native
-- results stay unchanged; omurice's bonus only scales positive gains.
function M.Configure(config)
    for _, name in ipairs({ "stale", "spoiled" }) do
        if config[name] ~= nil then
            assert(type(config[name]) == "number" and config[name] >= 0 and config[name] <= 1,
                "Invalid Kanami food freshness multiplier: "..name)
            policy[name] = config[name]
        end
    end
end

local function Freshness(food)
    local perish = food.components.perishable
    if perish ~= nil then
        if perish:IsSpoiled() then return policy.spoiled end
        if perish:IsStale() then return policy.stale end
    end
    return 1
end

local function IsOmurice(food)
    return food.prefab == foodname or food.food_basename == foodname
        or string.sub(food.prefab, 1, #foodname + 7) == foodname.."_spice_"
end

local function InstallEdible(edible)
    if edible._klbq_chef_wrapped then return end
    edible._klbq_chef_wrapped = true
    for _, method in ipairs({ "GetHealth", "GetHunger", "GetSanity" }) do
        local old = edible[method]
        edible[method] = function(self, eater, ...)
            if not IsKanami(eater) then return old(self, eater, ...) end
            local freshness = Freshness(self.inst)
            local result = Pack(old(self, eater, ...))
            if type(result[1]) == "number" and result[1] > 0 then
                result[1] = result[1] * freshness * (IsOmurice(self.inst) and 1.5 or 1)
            end
            return unpack(result, 1, result.n)
        end
    end
end

local function InstallStewer(stewer)
    if stewer._klbq_chef_wrapped then return end
    stewer._klbq_chef_wrapped = true
    local start = stewer.StartCooking
    stewer.StartCooking = function(self, doer, ...)
        local idle = self.targettime == nil and self.inst.components.container ~= nil
        local result = Pack(start(self, doer, ...))
        if idle and self.targettime ~= nil then
            self._klbq_kanami_cooked = IsKanami(doer) and self.product == foodname or nil
        end
        return unpack(result, 1, result.n)
    end

    local save = stewer.OnSave
    stewer.OnSave = function(self, ...)
        local result = Pack(save(self, ...))
        if result[1] ~= nil then
            result[1].klbq_kanami_cooked = self._klbq_kanami_cooked or nil
        end
        return unpack(result, 1, result.n)
    end
    local load = stewer.OnLoad
    stewer.OnLoad = function(self, data, ...)
        self._klbq_kanami_cooked = data ~= nil and data.klbq_kanami_cooked == true or nil
        local result = Pack(load(self, data, ...))
        if self.product ~= foodname then self._klbq_kanami_cooked = nil end
        return unpack(result, 1, result.n)
    end
    local stop = stewer.StopCooking
    stewer.StopCooking = function(self, ...)
        local result = Pack(stop(self, ...))
        self._klbq_kanami_cooked = nil
        return unpack(result, 1, result.n)
    end

    local harvest = stewer.Harvest
    stewer.Harvest = function(self, harvester, ...)
        local bonus = self.done and self.product == foodname and self._klbq_kanami_cooked
        local percent = bonus and self.spoiltime ~= nil
            and self.product_spoilage * self:GetTimeToSpoil() / self.spoiltime or nil
        if bonus then self._klbq_kanami_cooked = nil end
        local result = Pack(harvest(self, harvester, ...))
        if bonus and result[1] and self.product == nil then
            -- Preserve native Harvest, cookbook learning and other mod hooks.
            -- Give the second serving separately, avoiding shared recipe edits.
            local loot = SpawnPrefab(foodname)
            if loot ~= nil then
                if percent ~= nil and loot.components.perishable ~= nil then
                    loot.components.perishable:SetPercent(percent)
                    loot.components.perishable:StartPerishing()
                end
                if harvester ~= nil and harvester.components.inventory ~= nil then
                    harvester.components.inventory:GiveItem(loot, nil, self.inst:GetPosition())
                else
                    LaunchAt(loot, self.inst, nil, 1, 1)
                end
            end
        end
        return unpack(result, 1, result.n)
    end
end

function M.GetRecipes()
    if recipes == nil then
        local base = {
            name = foodname,
            test = function(cooker, names, tags)
                return (tags.egg or 0) >= 2
                    and (tags.inedible or 0) <= 0 and (tags.meat or 0) <= 0
                    and (tags.magic or 0) <= 0 and (tags.fish or 0) <= 0 and (tags.monster or 0) <= 0
                    and (names.tomato or 0) + (names.tomato_cooked or 0) >= 1
                    and (names.potato or 0) + (names.potato_cooked or 0) >= 1
            end,
            priority = 60, weight = 1, foodtype = FOODTYPE.MEAT,
            hunger = 50, sanity = 70, health = 30,
            perishtime = TUNING.PERISH_MED, cooktime = 1, potlevel = "high",
            overridebuild = foodname, overridesymbolname = foodname,
            cookbook_atlas = "images/klbq_kanami_items.xml",
            cookbook_tex = foodname..".tex",
        }
        local spiced = require("spicedfoods")
        -- Reuse original garlic/sugar/chili buffs, salt multipliers and heat.
        GenerateSpicedFoods({ [foodname] = base })
        recipes = { base }
        for _, spice in ipairs({ "garlic", "sugar", "chili", "salt" }) do
            local key = foodname.."_spice_"..spice
            local data = spiced[key]
            -- Our food prefab factory owns these definitions. Leaving them in
            -- the vanilla factory's global table would register them twice.
            spiced[key] = nil
            data.official = nil
            recipes[#recipes + 1] = data
        end
    end
    return recipes
end

function M.Install(env)
    local data = M.GetRecipes()
    for _, cooker in ipairs({ "cookpot", "portablecookpot" }) do
        env.AddCookerRecipe(cooker, data[1])
    end
    for i = 2, #data do env.AddCookerRecipe("portablespicer", data[i]) end
    env.AddComponentPostInit("edible", InstallEdible)
    env.AddComponentPostInit("stewer", InstallStewer)
end

return M
