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

        // Cached lookups for debug logging (internal so HealthBoostReset can clear them)
        internal static ExpeditionManager? _cachedEM;
        internal static DifficultyManager? _cachedDM;
        internal static BorealisGamemode? _cachedGM;
        internal static bool _headerLogged;

        // Progressive HP scaling data
        private static readonly Dictionary<BiomeType, float> NativePower = new()
        {
            { BiomeType.Kingswood, 1.0f },
            { BiomeType.Cornucopia, 1.5f },
            { BiomeType.DeepHarbor, 4.0f },
        };

        // Vanilla biome power targets for slots 0-2 (hardcoded, not affected by growth)
        private static readonly float[] VanillaSlotTargets = { 1.0f, 1.5f, 4.0f };

        private static float GetBossRushScaling()
        {
            if (!Config.BossRushMode.Value) return 1.0f;
            float scale = Config.BossRushScaling.Value;
            if (scale <= 1.0f) return 1.0f;
            int room = BossRushPatch.GlobalRoomCounter;
            if (room <= 1) return 1.0f; // first room is baseline
            return MathF.Pow(scale, room - 1);
        }

        private static float GetProgressiveMultiplier()
        {
            if (!Config.ProgressiveScaling.Value) return 1.0f;
            try
            {
                if (_cachedEM == null)
                    _cachedEM = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                if (_cachedEM == null) return 1.0f;

                var biome = _cachedEM.CurrentBiome;
                if (biome == null) return 1.0f;
                BiomeType bt = biome.GetBiomeType();
                if (!NativePower.TryGetValue(bt, out float native)) return 1.0f;

                int slot = _cachedEM.BiomeIndex;
                float target;
                if (slot < VanillaSlotTargets.Length)
                    target = VanillaSlotTargets[slot];
                else
                {
                    // Extra slots: grow from DeepHarbor baseline using configurable growth
                    float growth = Config.ProgressiveScalingGrowth.Value;
                    target = VanillaSlotTargets[^1] * MathF.Pow(growth, slot - VanillaSlotTargets.Length + 1);
                }

                return target / native;
            }
            catch { return 1.0f; }
        }

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

            var hs = __instance.HealthStats;
            var health = hs?.HealthMultiplier;
            string mobType = __instance.MobStats?.Type.ToString() ?? "Unknown";
            string biome = GetCurrentBiome();
            float baseMax = hs?.BaseMax ?? 0;
            float max = hs?.Max ?? 0;

            // Progressive HP scaling — applied to all mob types before category multipliers
            float progMult = GetProgressiveMultiplier();
            if (progMult != 1.0f && health != null)
                health.AddMod(progMult);

            // Boss Rush progressive scaling — compounds per room, stacks with all other multipliers
            float rushMult = GetBossRushScaling();
            if (rushMult != 1.0f && health != null)
                health.AddMod(rushMult);

            if (__instance.IsBoss)
            {
                if (Config.BossHealthMultiplier.Value != 1.0f && health != null)
                    health.AddMod(Config.BossHealthMultiplier.Value);
                if (Config.BossDamageMultiplier.Value != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(Config.BossDamageMultiplier.Value);
                float maxAfter = hs?.Max ?? 0;
                MelonLogger.Msg($"[SwornTweaks] [HP] BOSS {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | AfterMod={maxAfter:F0} | prog={progMult:F2}x | rush={rushMult:F2}x | hpMult={Config.BossHealthMultiplier.Value}x | dmgMult={Config.BossDamageMultiplier.Value}x");
            }
            else if (__instance.IsMajorEnemy)
            {
                if (Config.BeastHealthMultiplier.Value != 1.0f && health != null)
                    health.AddMod(Config.BeastHealthMultiplier.Value);
                if (Config.BeastDamageMultiplier.Value != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(Config.BeastDamageMultiplier.Value);
                float maxAfter = hs?.Max ?? 0;
                MelonLogger.Msg($"[SwornTweaks] [HP] BEAST {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | AfterMod={maxAfter:F0} | prog={progMult:F2}x | rush={rushMult:F2}x | hpMult={Config.BeastHealthMultiplier.Value}x | dmgMult={Config.BeastDamageMultiplier.Value}x");
            }
            else
            {
                float hp = Config.EnemyHealthMultiplier.Value;
                float dmg = Config.EnemyDamageMultiplier.Value;
                if (hp != 1.0f && health != null)
                    health.AddMod(hp);
                if (dmg != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(dmg);
                MelonLogger.Msg($"[SwornTweaks] [HP] MOB {mobType} | biome={biome} | BaseMax={baseMax:F0} | Max={max:F0} | prog={progMult:F2}x | rush={rushMult:F2}x");
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
            HealthBoostPatch._cachedEM = null;
            HealthBoostPatch._cachedDM = null;
            HealthBoostPatch._cachedGM = null;
        }
    }
}
