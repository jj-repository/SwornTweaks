using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(Mob), nameof(Mob.SetMobDifficultyScaling))]
    static class HealthBoostPatch
    {
        // Track which mobs we've already modified to prevent stacking
        // if SetMobDifficultyScaling is called more than once per mob
        internal static readonly HashSet<int> _modified = new();

        // Cached biome lookup
        private static ExpeditionManager _cachedEM;
        private static string GetCurrentBiome()
        {
            try
            {
                if (_cachedEM == null)
                    _cachedEM = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                var biome = _cachedEM?.CurrentBiome;
                return biome != null ? biome.GetBiomeType().ToString() : "?";
            }
            catch { return "?"; }
        }

        static void Postfix(Mob __instance)
        {
            int id = __instance.GetInstanceID();
            if (!_modified.Add(id)) return;

            var health = __instance.HealthStats?.HealthMultiplier;
            var hs = __instance.HealthStats;
            string mobType = __instance.MobStats?.Type.ToString() ?? "Unknown";

            if (__instance.IsBoss)
            {
                if (Config.BossHealthMultiplier.Value != 1.0f && health != null)
                {
                    health.AddMod(Config.BossHealthMultiplier.Value);
                }
                // Debug: log boss HP
                float baseMax = hs?.BaseMax ?? 0;
                float max = hs?.Max ?? 0;
                string biome = GetCurrentBiome();
                MelonLogger.Msg($"[SwornTweaks] [HP] BOSS {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | mult={Config.BossHealthMultiplier.Value}x");
            }
            else if (__instance.IsMajorEnemy)
            {
                if (Config.BeastHealthMultiplier.Value != 1.0f && health != null)
                {
                    health.AddMod(Config.BeastHealthMultiplier.Value);
                }
                // Debug: log beast HP
                float baseMax = hs?.BaseMax ?? 0;
                float max = hs?.Max ?? 0;
                string biome = GetCurrentBiome();
                MelonLogger.Msg($"[SwornTweaks] [HP] BEAST {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | mult={Config.BeastHealthMultiplier.Value}x");
            }
            else
            {
                float hp = Config.EnemyHealthMultiplier.Value;
                float dmg = Config.EnemyDamageMultiplier.Value;
                if (hp != 1.0f && health != null)
                    health.AddMod(hp);
                if (dmg != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(dmg);

                // Debug: log normal enemy HP
                float baseMax = hs?.BaseMax ?? 0;
                float max = hs?.Max ?? 0;
                string biome = GetCurrentBiome();
                MelonLogger.Msg($"[SwornTweaks] [HP] MOB {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0}");
            }
        }
    }

    // Clear tracked mobs at run start to prevent memory leak
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class HealthBoostReset
    {
        static void Prefix()
        {
            HealthBoostPatch._modified.Clear();
        }
    }
}
