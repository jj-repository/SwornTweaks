using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(BlessingGenerator), nameof(BlessingGenerator.GenerateBlessings))]
    static class RarityPatch
    {
        private static BlessingGenerator? _lastInstance;

        static void Prefix(BlessingGenerator __instance)
        {
            // Re-apply when we see a new instance (game may recreate between runs)
            if (__instance == _lastInstance) return;
            _lastInstance = __instance;

            __instance.legendaryBlessingBaseChance = Config.LegendaryChance.Value;
            __instance.epicBlessingBaseChance = Config.EpicChance.Value;
            __instance.rareBlessingBaseChance = Config.RareChance.Value;
            __instance.uncommonBlessingBaseChance = Config.UncommonChance.Value;

            MelonLogger.Msg($"[SwornTweaks] Rarity set: L={Config.LegendaryChance.Value} E={Config.EpicChance.Value} R={Config.RareChance.Value} U={Config.UncommonChance.Value}");
        }
    }
}
