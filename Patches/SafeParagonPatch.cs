using System;
using HarmonyLib;
using Il2Cpp;
using Il2CppSystem.Collections.Generic;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Safety net: the game's SelectParagonType crashes with "Invalid roll: '0'"
    /// when WeightedTable total weight is zero (can happen with extra biomes).
    /// The Prefix catches empty lists; the Finalizer catches zero-weight tables.
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

        static Exception? Finalizer(Exception __exception, ref ParagonType __result)
        {
            if (__exception != null)
            {
                MelonLogger.Warning($"[SwornTweaks] SelectParagonType threw: {__exception.Message} — returning Courage");
                __result = ParagonType.Courage;
                return null; // swallow exception
            }
            return null;
        }
    }
}
