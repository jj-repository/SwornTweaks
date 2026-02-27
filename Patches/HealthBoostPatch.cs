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

        // Cached lookups for debug logging
        private static ExpeditionManager _cachedEM;
        private static DifficultyManager _cachedDM;
        private static BorealisGamemode _cachedGM;
        internal static bool _headerLogged;

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

        private static string GetSessionInfo()
        {
            try
            {
                if (_cachedDM == null)
                    _cachedDM = UnityEngine.Object.FindObjectOfType<DifficultyManager>();
                if (_cachedGM == null)
                    _cachedGM = UnityEngine.Object.FindObjectOfType<BorealisGamemode>();

                string diff = _cachedDM?.CurrentDifficultyLevel.ToString() ?? "?";
                int players = 1;
                try { players = _cachedGM?.players?.Count ?? 1; } catch { }
                return $"diff={diff} players={players}";
            }
            catch { return "diff=? players=?"; }
        }

        static void Postfix(Mob __instance)
        {
            int id = __instance.GetInstanceID();
            if (!_modified.Add(id)) return;

            // Log session header once per run
            if (!_headerLogged)
            {
                _headerLogged = true;
                MelonLogger.Msg($"[SwornTweaks] [HP] === SESSION: {GetSessionInfo()} ===");
            }

            var health = __instance.HealthStats?.HealthMultiplier;
            var hs = __instance.HealthStats;
            string mobType = __instance.MobStats?.Type.ToString() ?? "Unknown";
            string biome = GetCurrentBiome();
            float baseMax = hs?.BaseMax ?? 0;
            float max = hs?.Max ?? 0;

            if (__instance.IsBoss)
            {
                if (Config.BossHealthMultiplier.Value != 1.0f && health != null)
                    health.AddMod(Config.BossHealthMultiplier.Value);
                float maxAfter = hs?.Max ?? 0;
                MelonLogger.Msg($"[SwornTweaks] [HP] BOSS {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | AfterMod={maxAfter:F0} | mult={Config.BossHealthMultiplier.Value}x");
            }
            else if (__instance.IsMajorEnemy)
            {
                if (Config.BeastHealthMultiplier.Value != 1.0f && health != null)
                    health.AddMod(Config.BeastHealthMultiplier.Value);
                float maxAfter = hs?.Max ?? 0;
                MelonLogger.Msg($"[SwornTweaks] [HP] BEAST {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | AfterMod={maxAfter:F0} | mult={Config.BeastHealthMultiplier.Value}x");
            }
            else
            {
                float hp = Config.EnemyHealthMultiplier.Value;
                float dmg = Config.EnemyDamageMultiplier.Value;
                if (hp != 1.0f && health != null)
                    health.AddMod(hp);
                if (dmg != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(dmg);
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
            HealthBoostPatch._headerLogged = false;
        }
    }
}
