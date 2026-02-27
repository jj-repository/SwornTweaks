using HarmonyLib;
using Il2Cpp;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(BlessingGenerator), nameof(BlessingGenerator.GetOddsForClassification))]
    static class DuoBoostPatch
    {
        static void Postfix(BlessingGenerator.BlessingClassification classification, ref float __result)
        {
            if (classification == BlessingGenerator.BlessingClassification.Duo)
                __result = Config.DuoChance.Value;
        }
    }
}
