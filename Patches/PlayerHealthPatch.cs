using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Apply PlayerHealthMultiplier and PlayerDamageMultiplier to the player character.
    ///
    /// Players use CharacterHealth (same base as mobs), but they are NOT Mob
    /// instances. We hook CharacterHealth.Setup Postfix and filter out Mob
    /// objects, applying multipliers only to player stats.
    /// A per-instance guard prevents stacking if Setup is called multiple times.
    /// </summary>
    [HarmonyPatch(typeof(CharacterHealth), nameof(CharacterHealth.Setup))]
    static class PlayerHealthPatch
    {
        internal static readonly HashSet<int> _applied = new();

        static void Postfix(CharacterHealth __instance)
        {
            var go = __instance.gameObject;
            if (go == null) return;
            if (go.GetComponent<Mob>() != null) return;

            int id = __instance.GetInstanceID();
            if (!_applied.Add(id)) return;

            // Health multiplier
            float hpMult = Config.PlayerHealthMultiplier.Value;
            if (hpMult != 1.0f)
            {
                var hs = __instance.healthStats;
                var healthMod = hs?.HealthMultiplier;
                if (healthMod != null)
                {
                    healthMod.AddMod(hpMult);
                    MelonLogger.Msg($"[SwornTweaks] Player health multiplied by {hpMult}x (Max={hs!.Max:F0})");
                }
            }

            // Damage multiplier — access CombatStats via Player component
            float dmgMult = Config.PlayerDamageMultiplier.Value;
            if (dmgMult != 1.0f)
            {
                var player = go.GetComponent<Player>();
                if (player != null)
                {
                    player.CombatStats?.AttackMultiplier?.AddMod(dmgMult);
                    MelonLogger.Msg($"[SwornTweaks] Player damage multiplied by {dmgMult}x");
                }
            }
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

    /// <summary>
    /// Invincibility: skip all incoming damage for the player when enabled.
    /// </summary>
    [HarmonyPatch(typeof(CharacterHealth), nameof(CharacterHealth.ApplyDamage))]
    static class InvincibilityPatch
    {
        static bool Prefix(CharacterHealth __instance, ref DamageResult __result)
        {
            if (!Config.Invincible.Value) return true;
            var go = __instance.gameObject;
            if (go == null || go.GetComponent<Mob>() != null) return true;
            __result = default;
            return false;
        }
    }

    /// <summary>
    /// Infinite mana: override mana value to max whenever the game tries to set it.
    /// </summary>
    [HarmonyPatch(typeof(Mana), nameof(Mana.SetCurrentInternal))]
    static class InfiniteManaPatch
    {
        static void Prefix(Mana __instance, ref float value)
        {
            if (!Config.InfiniteMana.Value) return;
            if (!__instance.initialized) return;

            var stats = __instance.manaStats;
            if (stats == null) return;

            value = stats.MaxMana;
        }
    }
}
