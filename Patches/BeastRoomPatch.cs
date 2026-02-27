using System;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.SelectObjectiveType))]
    static class BeastRoomPatch
    {
        private static readonly Random _rng = new();

        static void Postfix(ref ObjectiveType __result, BiomeData biome)
        {
            float chance = Config.BeastChancePercent.Value;
            if (chance <= 0f) return;

            // Only override normal combat rooms (Default, Wave, Horde, Onslaught)
            // Don't touch special objectives like MajorEnemy, Roundtable, Arena, etc.
            if (__result != ObjectiveType.Default && __result != ObjectiveType.Wave
                && __result != ObjectiveType.Horde && __result != ObjectiveType.Onslaught)
                return;

            // Skip Camelot and Somewhere (boss zones)
            if (biome != null)
            {
                var bt = biome.GetBiomeType();
                if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere)
                    return;
            }

            float roll = (float)(_rng.NextDouble() * 100.0);
            if (roll < chance)
            {
                MelonLogger.Msg($"[SwornTweaks] Beast room triggered (roll={roll:F1}% < {chance}%)");
                __result = ObjectiveType.MajorEnemy;
            }
        }
    }
}
