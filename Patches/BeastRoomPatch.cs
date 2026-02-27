using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class BeastRoomTracker
    {
        internal static int CurrentRoom = -1;
        internal static BiomeType CurrentBiome = BiomeType.None;

        // Track random beast count per biome to enforce MaxBeastsPerBiome
        internal static readonly Dictionary<BiomeType, int> BeastCounts = new();
        private static BiomeType _lastBiome = BiomeType.None;

        static void Prefix(int nextRoomIndex, BiomeData biome)
        {
            CurrentRoom = nextRoomIndex;
            CurrentBiome = biome != null ? biome.GetBiomeType() : BiomeType.None;

            // Reset counter when entering a new biome
            if (CurrentBiome != _lastBiome)
            {
                _lastBiome = CurrentBiome;
                if (!BeastCounts.ContainsKey(CurrentBiome))
                    BeastCounts[CurrentBiome] = 0;
            }
        }
    }

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.SelectObjectiveType))]
    static class BeastRoomPatch
    {
        private static readonly Random _rng = new();

        static void Postfix(ref ObjectiveType __result, BiomeData biome)
        {
            if (Config.UseVanillaBeastSettings.Value) return;

            var bt = biome != null ? biome.GetBiomeType() : BeastRoomTracker.CurrentBiome;
            if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere)
                return;

            int room = BeastRoomTracker.CurrentRoom;

            // 1. Fixed beast rooms — always force
            int br1 = Config.BeastRoom1.Value;
            int br2 = Config.BeastRoom2.Value;
            if (room >= 0 && (room == br1 || room == br2))
            {
                if (__result != ObjectiveType.MajorEnemy)
                {
                    MelonLogger.Msg($"[SwornTweaks] Fixed beast room {room} triggered");
                    __result = ObjectiveType.MajorEnemy;
                }
                return;
            }

            // 2. Random chance — only on normal combat rooms, respects max per biome
            float chance = Config.BeastChancePercent.Value;
            if (chance <= 0f) return;

            if (__result != ObjectiveType.Default && __result != ObjectiveType.Wave
                && __result != ObjectiveType.Horde && __result != ObjectiveType.Onslaught)
                return;

            // Check per-biome cap
            int max = Config.MaxBeastsPerBiome.Value;
            if (max > 0)
            {
                int count = BeastRoomTracker.BeastCounts.GetValueOrDefault(bt, 0);
                if (count >= max) return;
            }

            float roll = (float)(_rng.NextDouble() * 100.0);
            if (roll < chance)
            {
                MelonLogger.Msg($"[SwornTweaks] Random beast room {room} triggered (roll={roll:F1}% < {chance}%)");
                __result = ObjectiveType.MajorEnemy;

                // Increment counter
                if (!BeastRoomTracker.BeastCounts.ContainsKey(bt))
                    BeastRoomTracker.BeastCounts[bt] = 0;
                BeastRoomTracker.BeastCounts[bt]++;
            }
        }
    }

    // Reset beast counts at run start
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class BeastCountReset
    {
        static void Prefix()
        {
            BeastRoomTracker.BeastCounts.Clear();
        }
    }
}
