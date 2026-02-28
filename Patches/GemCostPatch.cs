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

    // GetGold postfix removed — it inflated gold for ALL checks (shops, etc.),
    // not just the Lancelot gem socket. The AddGold(-300) prefix above is sufficient:
    // gems are free as long as you have 300 gold for the UI to show the option.
}
