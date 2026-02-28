using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(CurrencyManager), nameof(CurrencyManager.GetGold))]
    static class GoldPatch
    {
        static void Postfix(ref int __result)
        {
            if (!Config.UnlimitedGold.Value) return;
            __result = 999999;
        }
    }

    [HarmonyPatch(typeof(CurrencyManager), nameof(CurrencyManager.AddGold))]
    static class GoldPatchBlock
    {
        static bool Prefix(int amount)
        {
            if (!Config.UnlimitedGold.Value) return true;
            // Block all gold deductions so gold never actually decreases
            if (amount < 0)
            {
                MelonLogger.Msg($"[SwornTweaks] [Gold] Blocked gold deduction: {amount}");
                return false;
            }
            return true;
        }
    }
}
