using System;
using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class BiomeRepeatPatch
    {
        static void Prefix(ExpeditionManager __instance)
        {
            if (!Config.EnableBiomeRepeat.Value) return;

            var biomes = __instance.biomes;
            if (biomes == null || biomes.Count < 2) return;

            if (!Enum.TryParse<BiomeType>(Config.RepeatBiome.Value, true, out var repeatType))
            {
                MelonLogger.Warning($"[SwornTweaks] Unknown RepeatBiome: '{Config.RepeatBiome.Value}'");
                return;
            }
            if (!Enum.TryParse<BiomeType>(Config.RepeatAfterBiome.Value, true, out var afterType))
            {
                MelonLogger.Warning($"[SwornTweaks] Unknown RepeatAfterBiome: '{Config.RepeatAfterBiome.Value}'");
                return;
            }

            // Guard: if the repeat biome already appears more than once, skip
            int repeatCount = 0;
            for (int i = 0; i < biomes.Count; i++)
                if (biomes[i]?.GetBiomeType() == repeatType) repeatCount++;
            if (repeatCount > 1)
            {
                MelonLogger.Msg($"[SwornTweaks] Biome repeat already present ({repeatType} x{repeatCount}), skipping");
                return;
            }

            // Find the "after" biome index
            int afterIndex = -1;
            for (int i = 0; i < biomes.Count; i++)
            {
                if (biomes[i]?.GetBiomeType() == afterType)
                {
                    afterIndex = i;
                    break;
                }
            }
            if (afterIndex < 0)
            {
                MelonLogger.Warning($"[SwornTweaks] RepeatAfterBiome '{afterType}' not found in biome list");
                return;
            }

            // Find the BiomeData source for the repeat
            BiomeData? source = null;
            for (int i = 0; i < biomes.Count; i++)
            {
                if (biomes[i]?.GetBiomeType() == repeatType)
                {
                    source = biomes[i];
                    break;
                }
            }
            if (source == null)
            {
                MelonLogger.Warning($"[SwornTweaks] RepeatBiome '{repeatType}' not found in biome list");
                return;
            }

            biomes.Insert(afterIndex + 1, source);

            MelonLogger.Msg($"[SwornTweaks] Inserted {repeatType} repeat after {afterType} (index {afterIndex + 1}, {biomes.Count} biomes total)");

            string seq = "";
            for (int i = 0; i < biomes.Count; i++)
                seq += (i > 0 ? " -> " : "") + biomes[i]?.GetBiomeType().ToString();
            MelonLogger.Msg($"[SwornTweaks] Biome sequence: {seq}");
        }
    }
}
