using System;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class BiomeRepeatPatch
    {
        private static readonly Random _rng = new();

        // Prefix: modify biomes list BEFORE ResetBiomeRunData allocates
        // m_biomeRunDatas array, so the array is sized correctly.
        // (Previous crashes were caused by ChaosModePatch, not this.)
        static void Prefix(ExpeditionManager __instance)
        {
            // Boss Rush handles its own biome structure — skip extra biomes
            if (Config.BossRushMode.Value) return;

            int extra = Config.ExtraBiomes.Value;
            if (extra <= 0) return;

            var biomes = __instance.biomes;
            if (biomes == null || biomes.Count < 5) return;

            // Guard: vanilla has exactly 5 biomes — if already modified, skip
            if (biomes.Count > 5) return;

            // Find the 3 combat biome data objects and Camelot insertion point
            BiomeData? kingswood = null, cornucopia = null, deepHarbor = null;
            int camelotIndex = -1;
            for (int i = 0; i < biomes.Count; i++)
            {
                var bt = biomes[i]?.GetBiomeType();
                switch (bt)
                {
                    case BiomeType.Kingswood: kingswood = biomes[i]; break;
                    case BiomeType.Cornucopia: cornucopia = biomes[i]; break;
                    case BiomeType.DeepHarbor: deepHarbor = biomes[i]; break;
                    case BiomeType.Camelot: camelotIndex = i; break;
                }
            }

            if (kingswood == null || cornucopia == null || deepHarbor == null || camelotIndex < 0)
                return;

            var combat = new[] { kingswood, cornucopia, deepHarbor };

            if (Config.AllBiomesRandom.Value)
            {
                // Replace all 3 combat biomes + add extras, fully randomized
                for (int i = 2; i >= 0; i--)
                    biomes.RemoveAt(i);

                // Insert (3 + extra) random combat biomes before Camelot (now at index 0)
                int total = 3 + extra;
                for (int i = 0; i < total; i++)
                    biomes.Insert(i, combat[_rng.Next(3)]);
            }
            else if (Config.RandomizeRepeats.Value)
            {
                // Insert random extra biomes after DeepHarbor (before Camelot)
                for (int i = 0; i < extra; i++)
                    biomes.Insert(camelotIndex + i, combat[_rng.Next(3)]);
            }
            else
            {
                // Insert ordered extras: cycle Kingswood, Cornucopia, DeepHarbor
                for (int i = 0; i < extra; i++)
                    biomes.Insert(camelotIndex + i, combat[i % 3]);
            }

            // Log the final sequence
            var names = new string[biomes.Count];
            for (int i = 0; i < biomes.Count; i++)
                names[i] = biomes[i]?.GetBiomeType().ToString() ?? "?";
            MelonLogger.Msg($"[SwornTweaks] Biome sequence ({biomes.Count}): {string.Join(" -> ", names)}");
        }
    }
}
