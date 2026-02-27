using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(RerollManager), nameof(RerollManager.OnRunStarted))]
    static class RerollPatch
    {
        static void Prefix(RerollManager __instance)
        {
            int bonus = Config.BonusRerolls.Value;
            if (bonus <= 0) return;
            __instance.baseRerolls += bonus;
            MelonLogger.Msg($"[SwornTweaks] Rerolls: +{bonus} (total base: {__instance.baseRerolls})");
        }
    }
}
