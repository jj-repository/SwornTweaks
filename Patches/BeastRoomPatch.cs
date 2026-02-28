using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;

using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Force extra boss/beast encounters via two systems:
    ///   1. Fixed Extra Bosses — selection sampling guarantees exactly N bosses per biome
    ///   2. Random Chance — per-room % roll, respects per-biome cap
    ///
    /// Both systems protect the first 3 rooms (tutorial-ish) and last 2 rooms
    /// (biome boss area). The candidate pool respects SpawnBeastBosses and
    /// ForceBiomeBoss toggles.
    /// </summary>
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class BeastRoomPatch
    {
        private static readonly Random _rng = new();

        // Known biome room counts
        private static readonly Dictionary<BiomeType, int> BiomeRoomCounts = new()
        {
            { BiomeType.Kingswood, 15 },
            { BiomeType.Cornucopia, 13 },
            { BiomeType.DeepHarbor, 13 },
        };

        // Track random beast count per biome to enforce MaxBeastsPerBiome
        internal static readonly Dictionary<BiomeType, int> BeastCounts = new();

        // Track fixed extra bosses placed per biome this run
        internal static readonly Dictionary<BiomeType, int> FixedBossesPlaced = new();

        static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result,
                            int nextRoomIndex, BiomeData biome)
        {
            if (__result == null || __result.Length == 0) return;

            var bt = biome != null ? biome.GetBiomeType() : BiomeType.None;


            if (Config.UseVanillaBeastSettings.Value) return;
            if (Config.BossRushMode.Value) return; // BossRush handles all room assignment
            if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere || bt == BiomeType.None)
                return;

            int totalRooms = BiomeRoomCounts.GetValueOrDefault(bt, 13);

            bool force = false;
            bool isFixed = false;

            // 1. Fixed Extra Bosses — selection sampling algorithm
            int fixedTarget = Math.Clamp(Config.FixedExtraBosses.Value, 0, 3);
            if (fixedTarget > 0)
            {
                int firstEligible = 3;
                int lastEligible = totalRooms - 3; // skip last 2 rooms (index totalRooms-2 and totalRooms-1)

                if (nextRoomIndex >= firstEligible && nextRoomIndex <= lastEligible)
                {
                    int placed = FixedBossesPlaced.GetValueOrDefault(bt, 0);
                    int remainingToPlace = fixedTarget - placed;

                    if (remainingToPlace > 0)
                    {
                        int remainingEligible = lastEligible - nextRoomIndex + 1;
                        double probability = (double)remainingToPlace / remainingEligible;
                        double roll = _rng.NextDouble();

                        if (roll < probability)
                        {
                            force = true;
                            isFixed = true;
                            if (!FixedBossesPlaced.ContainsKey(bt))
                                FixedBossesPlaced[bt] = 0;
                            FixedBossesPlaced[bt]++;
                        }
                    }
                }
            }

            // 2. Random chance — respects max per biome, protects last room
            if (!force)
            {
                float chance = Config.BeastChancePercent.Value;
                if (chance <= 0f) return;

                // Never override the biome boss room (last room)
                if (nextRoomIndex >= totalRooms - 1) return;

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

            // Build candidate pool based on toggles
            bool includeBeast = Config.SpawnBeastBosses.Value;
            bool includeBoss = Config.ForceBiomeBoss.Value;
            var candidates = new List<(RoomType type, LevelData level)>();

            // Mini-boss (beast) levels
            if (includeBeast)
            {
                var mbPool = biome?.MiniBossLevelPool;
                if (mbPool != null)
                    for (int i = 0; i < mbPool.Length; i++)
                        if (mbPool[i] != null) candidates.Add((RoomType.MiniBoss, mbPool[i]));
                var mbFirst = biome?.FirstMiniBossLevel;
                if (mbFirst != null && candidates.Count == 0)
                    candidates.Add((RoomType.MiniBoss, mbFirst));
            }

            // Biome end boss levels
            if (includeBoss)
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
                MelonLogger.Warning($"[SwornTweaks] No boss levels in pool for biome {bt} (Beast={includeBeast}, Boss={includeBoss}) — skipping room {nextRoomIndex}");
                return;
            }

            var pick = candidates[_rng.Next(candidates.Count)];

            if (isFixed)
                MelonLogger.Msg($"[SwornTweaks] Fixed extra {pick.type} room {nextRoomIndex} (biome={bt}, level={pick.level.name})");
            else
                MelonLogger.Msg($"[SwornTweaks] Random {pick.type} room {nextRoomIndex} (biome={bt}, level={pick.level.name})");

            // Convert all paths for this room and clear post-level events
            for (int i = 0; i < __result.Length; i++)
            {
                var path = __result[i];
                if (path == null) continue;
                path.roomType = pick.type;
                path.levelData = pick.level;
                path.postLevelEvents = new Il2CppStructArray<PostLevelEventType>(0);
            }

            // Increment random counter (fixed bosses tracked separately)
            if (!isFixed)
            {
                if (!BeastCounts.ContainsKey(bt))
                    BeastCounts[bt] = 0;
                BeastCounts[bt]++;
            }
        }
    }

    // Reset beast counts at run start
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class BeastCountReset
    {
        static void Prefix()
        {
            BeastRoomPatch.BeastCounts.Clear();
            BeastRoomPatch.FixedBossesPlaced.Clear();
        }
    }
}
