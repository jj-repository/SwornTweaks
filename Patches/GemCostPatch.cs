using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(CurrencyManager), nameof(CurrencyManager.AddGold))]
    static class GemCostPatchAddGold
    {
        static bool Prefix(int amount)
        {
            if (!Config.NoGemCost.Value) return true;
            if (amount == -300)
            {
                MelonLogger.Msg("[SwornTweaks] Blocked 300 gold gem cost");
                return false;
            }
            return true;
        }
    }

    [HarmonyPatch(typeof(CurrencyManager), nameof(CurrencyManager.GetGold))]
    static class GemCostPatchGetGold
    {
        static void Postfix(ref int __result)
        {
            if (!Config.NoGemCost.Value) return;
            if (__result < 300)
                __result = 300;
        }
    }
}
