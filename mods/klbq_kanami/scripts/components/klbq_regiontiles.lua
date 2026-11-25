local Regions = require("klbq_kanami/regions")

local RegionTiles = Class(function(self, inst)
    self.inst = inst
    self.onterraform = function(_, data) Regions.OnTerraform(inst, data) end
    inst:ListenForEvent("onterraform", self.onterraform)
end)

function RegionTiles:OnSave()
    return Regions.SaveTiles(self.inst)
end

function RegionTiles:OnLoad(data)
    self.inst._klbq_region_tiles = data
end

function RegionTiles:OnRemoveFromEntity()
    self.inst:RemoveEventCallback("onterraform", self.onterraform)
end

return RegionTiles
