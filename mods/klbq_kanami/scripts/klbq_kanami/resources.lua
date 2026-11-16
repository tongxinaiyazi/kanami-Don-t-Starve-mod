-- Shared, unmodified resource runtime keeps the add-on's IDs and artwork.
-- Its registry also handles both load orders when the same add-on is enabled.
local M={}

local function Pack(...) return {n=select("#",...),...} end

local function InstallMining(env, base_string)
    local G=env.GLOBAL
    local mine=G.ACTIONS and G.ACTIONS.MINE
    if not mine or not mine.fn then return end
    -- Destroy(player) also calls WorkedBy; only the native mining action grants
    -- a reward. A scoped context survives native buffered-action clearing.
    local context
    local oldmine=mine.fn
    mine.fn=function(act,...)
        local previous=context
        context=act
        local result=Pack(pcall(oldmine,act,...))
        context=previous
        if not result[1] then error(result[2],0) end
        return unpack(result,2,result.n)
    end
    local function Rock(inst)
        if not G.TheWorld.ismastersim or inst._klbq_mining_installed then return end
        local workable=inst.components.workable
        local loot=inst.components.lootdropper
        if not workable or not loot then return end
        inst._klbq_mining_installed=true
        local oldwork=workable.onwork
        workable:SetOnWorkCallback(function(rock,worker,workleft,...)
            if not rock._klbq_base_string_mined and workleft<=0
                and workable:GetWorkAction()==mine
                and context and context.target==rock and context.doer==worker
                and worker and worker:IsValid() and worker:HasTag("player")
                and not worker:HasTag("playerghost")
                and worker.components.health and not worker.components.health:IsDead() then
                rock._klbq_base_string_mined=true
                -- Spawn before the original callback removes the mined entity.
                loot:SpawnLootPrefab(base_string)
            end
            if oldwork then return oldwork(rock,worker,workleft,...) end
        end)
        local oldsave,oldload=inst.OnSave,inst.OnLoad
        inst.OnSave=function(rock,data,...)
            data.klbq_base_string_mined=rock._klbq_base_string_mined or nil
            if oldsave then return oldsave(rock,data,...) end
        end
        inst.OnLoad=function(rock,data,...)
            rock._klbq_base_string_mined=data and data.klbq_base_string_mined or nil
            if oldload then return oldload(rock,data,...) end
        end
    end
    env.AddPrefabPostInit("rock1",Rock)
    env.AddPrefabPostInit("rock2",Rock)
end

local function InstallBossLoot(env, ring)
    for prefab,count in pairs({minotaur=6,daywalker=4,daywalker2=4}) do
        -- Keep the native loot setup and stategraph timing, including daywalker's
        -- defeated/looted persistence. No rewards on intermediate health phases.
        env.AddPrefabPostInit(prefab,function(inst)
            if not env.GLOBAL.TheWorld.ismastersim or inst._klbq_ring_loot then return end
            local loot=inst.components.lootdropper
            if loot then
                -- Daywalker's native setup calls SetLoot, clearing chanceloot.
                -- Extend its final result instead of changing shared tables or
                -- setup functions; native phase timing remains authoritative.
                local oldgenerate=loot.GenerateLoot
                loot.GenerateLoot=function(self,...)
                    local result=Pack(oldgenerate(self,...))
                    for i=1,count do table.insert(result[1],ring) end
                    return unpack(result,1,result.n)
                end
                inst._klbq_ring_loot=true
            end
        end)
    end
end
function M.Install(env)
    require("klbq_resources/register").Install(env)
    local api=require("klbq_resources/api")
    InstallMining(env,assert(api.GetPrefab("base_string")))
    InstallBossLoot(env,assert(api.GetPrefab("topology_ring")))
    local terminal=api.GetPrefab("terminal_kanami")
    assert(terminal,"Kanami terminal is missing from the resource catalog")
    env.AddPrefabPostInit("charlie_boss",function(inst)
        if not env.GLOBAL.TheWorld.ismastersim or inst._klbq_terminal_loot then return end
        local loot=inst.components.lootdropper
        if loot then
            -- Native Charlie DropDeathLoot runs at death2 frame 176. Extending
            -- its loot list keeps that timing and the original phase rewards.
            loot:AddChanceLoot(terminal,1)
            inst._klbq_terminal_loot=true
        end
    end)
end
return M
