using System;
using HarmonyLib;
using Il2Cpp;
using Il2CppSystem.Collections.Generic;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Safety net: the game's SelectParagonType crashes with "Invalid roll: '0'"
    /// when WeightedTable has no entries (can happen with extra biomes or rarely in vanilla).
    /// Return the first available type instead of letting it throw.
    /// </summary>
    [HarmonyPatch(typeof(BlessingGenerator), nameof(BlessingGenerator.SelectParagonType))]
    static class SafeParagonPatch
    {
        static bool Prefix(List<ParagonType> availableTypes, ref ParagonType __result)
        {
            if (availableTypes == null || availableTypes.Count == 0)
            {
                MelonLogger.Warning("[SwornTweaks] SelectParagonType: no available types — returning Courage");
                __result = ParagonType.Courage;
                return false; // skip original
            }
            return true; // run original
        }
    }
}
