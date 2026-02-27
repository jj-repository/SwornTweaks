using System;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    // Track the current room index so SelectObjectiveType knows where we are
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class BeastRoomTracker
    {
        internal static int CurrentRoom = -1;
        internal static BiomeType CurrentBiome = BiomeType.None;

        static void Prefix(int nextRoomIndex, BiomeData biome)
        {
            CurrentRoom = nextRoomIndex;
            CurrentBiome = biome != null ? biome.GetBiomeType() : BiomeType.None;
        }
    }

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.SelectObjectiveType))]
    static class BeastRoomPatch
    {
        private static readonly Random _rng = new();

        static void Postfix(ref ObjectiveType __result, BiomeData biome)
        {
            // Skip Camelot and Somewhere (boss zones)
            var bt = biome != null ? biome.GetBiomeType() : BeastRoomTracker.CurrentBiome;
            if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere)
                return;

            int room = BeastRoomTracker.CurrentRoom;

            // 1. Hardset beast rooms — always force regardless of current objective
            int br1 = Config.BeastRoom1.Value;
            int br2 = Config.BeastRoom2.Value;
            if (room >= 0 && (room == br1 || room == br2))
            {
                if (__result != ObjectiveType.MajorEnemy)
                {
                    MelonLogger.Msg($"[SwornTweaks] Hardset beast room {room} triggered");
                    __result = ObjectiveType.MajorEnemy;
                }
                return;
            }

            // 2. Random chance — only on normal combat rooms
            float chance = Config.BeastChancePercent.Value;
            if (chance <= 0f) return;

            if (__result != ObjectiveType.Default && __result != ObjectiveType.Wave
                && __result != ObjectiveType.Horde && __result != ObjectiveType.Onslaught)
                return;

            float roll = (float)(_rng.NextDouble() * 100.0);
            if (roll < chance)
            {
                MelonLogger.Msg($"[SwornTweaks] Random beast room {room} triggered (roll={roll:F1}% < {chance}%)");
                __result = ObjectiveType.MajorEnemy;
            }
        }
    }
}
