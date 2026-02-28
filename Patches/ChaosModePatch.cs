using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Chaos Mode: bypass all blessing prerequisite checks.
    ///
    /// Previous approach (hooking IsValid on blessing subtypes) caused native IL2CPP
    /// crashes because IsValid is a virtual method — Harmony trampolines corrupt the
    /// native vtable. This approach hooks the non-virtual filter lambdas in
    /// BlessingGenerator that call IsValid, forcing them to return true.
    ///
    /// Four filter paths covered:
    ///   1. GenerateBlessingsInternal — main blessing generation
    ///   2. GenerateLeveledBlessings — leveled blessing filter
    ///   3. GenerateSwordInTheStoneBlessings — paragon blessing filter
    ///   4. GenerateKissCurseBlessings — kiss curse blessing filter
    /// </summary>
    static class ChaosModePatch
    {
        /// <summary>Main blessing filter: GenerateBlessingsInternal uses this to check IsValid.</summary>
        [HarmonyPatch(typeof(BlessingGenerator.__c__DisplayClass33_0),
            nameof(BlessingGenerator.__c__DisplayClass33_0._GenerateBlessingsInternal_b__0))]
        static class MainFilter
        {
            static void Postfix(Blessing b, ref bool __result)
            {
                if (!Config.ChaosMode.Value) return;
                if (!__result)
                {
                    MelonLogger.Msg($"[SwornTweaks] [Chaos] Bypassed prerequisite for: {b?.name ?? "?"}");
                    __result = true;
                }
            }
        }

        /// <summary>Leveled blessing filter (stateless lambda on __c).</summary>
        [HarmonyPatch(typeof(BlessingGenerator.__c),
            nameof(BlessingGenerator.__c._GenerateLeveledBlessings_b__29_0))]
        static class LeveledFilter
        {
            static void Postfix(Blessing b, ref bool __result)
            {
                if (!Config.ChaosMode.Value) return;
                if (!__result)
                    __result = true;
            }
        }

        /// <summary>SwordInTheStone blessing filter.</summary>
        [HarmonyPatch(typeof(BlessingGenerator.__c__DisplayClass30_0),
            nameof(BlessingGenerator.__c__DisplayClass30_0._GenerateSwordInTheStoneBlessings_b__0))]
        static class SwordInTheStoneFilter
        {
            static void Postfix(Blessing b, ref bool __result)
            {
                if (!Config.ChaosMode.Value) return;
                if (!__result)
                    __result = true;
            }
        }

        /// <summary>KissCurse blessing filter.</summary>
        [HarmonyPatch(typeof(BlessingGenerator.__c__DisplayClass31_0),
            nameof(BlessingGenerator.__c__DisplayClass31_0._GenerateKissCurseBlessings_b__0))]
        static class KissCurseFilter
        {
            static void Postfix(Blessing b, ref bool __result)
            {
                if (!Config.ChaosMode.Value) return;
                if (!__result)
                    __result = true;
            }
        }
    }
}
