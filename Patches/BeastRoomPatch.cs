using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Force MiniBoss (beast) encounters in specific rooms.
    ///
    /// SelectObjectiveType has CallerCount(0) — it's only called from native
    /// IL2CPP code inside GeneratePaths, so Harmony can never intercept it.
    /// Instead, we hook GeneratePaths Postfix and modify the returned Path
    /// objects to MiniBoss room type with the correct biome beast level.
    /// </summary>
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class BeastRoomPatch
    {
        private static readonly Random _rng = new();

        // Track random beast count per biome to enforce MaxBeastsPerBiome
        internal static readonly Dictionary<BiomeType, int> BeastCounts = new();

        static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result,
                            int nextRoomIndex, BiomeData biome)
        {
            if (__result == null || __result.Length == 0) return;

            var bt = biome != null ? biome.GetBiomeType() : BiomeType.None;

            // Debug: log room intensity for data gathering
            var firstPath = __result[0];
            if (firstPath != null)
                MelonLogger.Msg($"[SwornTweaks] [ROOM] idx={nextRoomIndex} biome={bt} intensity={firstPath.intensity:F2} type={firstPath.roomType}");

            if (Config.UseVanillaBeastSettings.Value) return;
            if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere || bt == BiomeType.None)
                return;

            bool force = false;
            bool isFixed = false;

            // 1. Fixed beast rooms — always force
            int br1 = Config.BeastRoom1.Value;
            int br2 = Config.BeastRoom2.Value;
            if ((br1 >= 0 && nextRoomIndex == br1) || (br2 >= 0 && nextRoomIndex == br2))
            {
                force = true;
                isFixed = true;
            }

            // 2. Random chance — respects max per biome
            if (!force)
            {
                float chance = Config.BeastChancePercent.Value;
                if (chance <= 0f) return;

                // Check per-biome cap
                int max = Config.MaxBeastsPerBiome.Value;
                if (max > 0)
                {
                    int count = BeastCounts.GetValueOrDefault(bt, 0);
                    if (count >= max) return;
                }

                float roll = (float)(_rng.NextDouble() * 100.0);
                if (roll < chance)
                {
                    force = true;
                    MelonLogger.Msg($"[SwornTweaks] Random beast room {nextRoomIndex} (biome={bt}, roll={roll:F1}% < {chance}%)");
                }
            }

            if (!force) return;

            // Build a combined pool of candidate levels
            bool includeBosses = Config.ForceBiomeBoss.Value;
            var candidates = new System.Collections.Generic.List<(RoomType type, LevelData level)>();

            // Always include mini-boss levels
            var mbPool = biome?.MiniBossLevelPool;
            if (mbPool != null)
                for (int i = 0; i < mbPool.Length; i++)
                    if (mbPool[i] != null) candidates.Add((RoomType.MiniBoss, mbPool[i]));
            var mbFirst = biome?.FirstMiniBossLevel;
            if (mbFirst != null && candidates.Count == 0)
                candidates.Add((RoomType.MiniBoss, mbFirst));

            // Optionally include biome end boss levels
            if (includeBosses)
            {
                var bPool = biome?.bossLevelPool;
                if (bPool != null)
                    for (int i = 0; i < bPool.Length; i++)
                        if (bPool[i] != null) candidates.Add((RoomType.Boss, bPool[i]));
                var bFirst = biome?.firstBossLevel;
                if (bFirst != null && (bPool == null || bPool.Length == 0))
                    candidates.Add((RoomType.Boss, bFirst));
            }

            if (candidates.Count == 0)
            {
                MelonLogger.Warning($"[SwornTweaks] No boss levels found for biome {bt} — skipping room {nextRoomIndex}");
                return;
            }

            var pick = candidates[_rng.Next(candidates.Count)];

            if (isFixed)
                MelonLogger.Msg($"[SwornTweaks] Fixed {pick.type} room {nextRoomIndex} (biome={bt}, level={pick.level.name})");
            else
                MelonLogger.Msg($"[SwornTweaks] Random {pick.type} room {nextRoomIndex} (biome={bt}, level={pick.level.name})");

            // Convert all paths for this room
            for (int i = 0; i < __result.Length; i++)
            {
                var path = __result[i];
                if (path == null) continue;
                path.roomType = pick.type;
                path.levelData = pick.level;
            }

            // Increment counter
            if (!BeastCounts.ContainsKey(bt))
                BeastCounts[bt] = 0;
            BeastCounts[bt]++;
        }

    }

    // Reset beast counts at run start
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class BeastCountReset
    {
        static void Prefix()
        {
            BeastRoomPatch.BeastCounts.Clear();
        }
    }
}
