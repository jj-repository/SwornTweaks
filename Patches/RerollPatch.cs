using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(RerollManager), nameof(RerollManager.OnRunStarted))]
    static class RerollPatch
    {
        internal static RerollManager? Instance;
        private static int _vanillaBaseRerolls = -1;

        static void Prefix(RerollManager __instance)
        {
            Instance = __instance;

            int bonus = Config.BonusRerolls.Value;
            if (bonus <= 0) return;

            // Capture the vanilla base once, then always derive from it
            // to prevent accumulation across multiple runs
            if (_vanillaBaseRerolls < 0)
                _vanillaBaseRerolls = __instance.baseRerolls;
            __instance.baseRerolls = _vanillaBaseRerolls + bonus;
            MelonLogger.Msg($"[SwornTweaks] Rerolls: +{bonus} (total base: {__instance.baseRerolls})");
        }

        static void Postfix(RerollManager __instance)
        {
            if (!Config.InfiniteRerolls.Value) return;
            __instance.baseRerolls = 500;
            RerollManager.SetRerolls(500);
            MelonLogger.Msg("[SwornTweaks] Infinite rerolls: set to 500");
        }
    }
}
