using HarmonyLib;
using Il2Cpp;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(BlessingGenerator), nameof(BlessingGenerator.GetOddsForClassification))]
    static class DuoBoostPatch
    {
        static void Postfix(BlessingGenerator.BlessingClassification classification, ref float __result)
        {
            float chance = Config.DuoChance.Value;
            if (chance <= 0f) return; // 0 = vanilla behavior
            if (classification == BlessingGenerator.BlessingClassification.Duo)
                __result = chance;
        }
    }
}
