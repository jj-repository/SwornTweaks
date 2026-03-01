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
            {
                float duoChance = Config.DuoChance.Value;
                if (duoChance > 0f) __result = duoChance;
            }
            else if (classification == BlessingGenerator.BlessingClassification.RoundTable)
            {
                float rtChance = Config.RoundTableChance.Value;
                if (rtChance > 0f) __result = rtChance;
            }
        }
    }
}
