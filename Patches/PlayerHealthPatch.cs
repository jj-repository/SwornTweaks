using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Apply PlayerHealthMultiplier to the player character.
    ///
    /// Players use CharacterHealth (same base as mobs), but they are NOT Mob
    /// instances. We hook CharacterHealth.Setup Postfix and filter out Mob
    /// objects, applying the multiplier only to player health.
    /// A per-instance guard prevents stacking if Setup is called multiple times.
    /// </summary>
    [HarmonyPatch(typeof(CharacterHealth), nameof(CharacterHealth.Setup))]
    static class PlayerHealthPatch
    {
        internal static readonly HashSet<int> _applied = new();

        static void Postfix(CharacterHealth __instance)
        {
            float mult = Config.PlayerHealthMultiplier.Value;
            if (mult == 1.0f) return;

            // Skip mobs — they have their own multipliers via HealthBoostPatch
            var go = __instance.gameObject;
            if (go == null) return;
            if (go.GetComponent<Mob>() != null) return;

            int id = __instance.GetInstanceID();
            if (!_applied.Add(id)) return;

            var hs = __instance.healthStats;
            if (hs == null) return;

            var healthMult = hs.HealthMultiplier;
            if (healthMult == null) return;

            healthMult.AddMod(mult);
            float maxAfter = hs.Max;
            MelonLogger.Msg($"[SwornTweaks] Player health multiplied by {mult}x (Max={maxAfter:F0})");
        }
    }

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class PlayerHealthReset
    {
        static void Prefix()
        {
            PlayerHealthPatch._applied.Clear();
        }
    }
}
