using HarmonyLib;
using Il2Cpp;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Chaos Mode: bypass all blessing prerequisite checks.
    /// Each blessing subclass overrides IsValid() to check RequiredBlessingsAny/All/None.
    /// We patch each override to always return true when ChaosMode is enabled.
    /// </summary>
    static class ChaosModePatch
    {
        private static bool BypassIsValid(ref bool __result)
        {
            if (!Config.ChaosMode.Value) return true;
            __result = true;
            return false; // skip original
        }

        [HarmonyPatch(typeof(Blessing), nameof(Blessing.IsValid))]
        static class Base { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(ParagonBlessing), nameof(ParagonBlessing.IsValid))]
        static class Paragon { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(CharacterBlessing), nameof(CharacterBlessing.IsValid))]
        static class Character { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(EventBlessing), nameof(EventBlessing.IsValid))]
        static class Event { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(WeaponBlessing), nameof(WeaponBlessing.IsValid))]
        static class Weapon { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(DuoBlessing), nameof(DuoBlessing.IsValid))]
        static class Duo { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(KissCurseBlessing), nameof(KissCurseBlessing.IsValid))]
        static class KissCurse { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }

        [HarmonyPatch(typeof(RoundTableBlessing), nameof(RoundTableBlessing.IsValid))]
        static class RoundTable { static bool Prefix(ref bool __result) => BypassIsValid(ref __result); }
    }
}
