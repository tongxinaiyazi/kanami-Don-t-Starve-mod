-- Reuse the native terrain edge masks; the surface and inventory art are original.
AddTile("KLBQ_IMPRINT", "LAND", {ground_name="拟态拓印地皮"},
    {name="blocky", noise_texture="levels/textures/klbq_imprint_noise"},
    {name="map_edge", noise_texture="levels/textures/klbq_imprint_mini_noise"},
    {name="klbq_imprint", anim="idle", bank_build="turf_klbq_imprint",
        invicon_override="mosaic_blue", pickupsound="rock"})
