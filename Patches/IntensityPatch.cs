using HarmonyLib;
using Il2Cpp;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(BiomeData), nameof(BiomeData.GetRoomIntensity))]
    static class IntensityPatch
    {
        static void Postfix(ref float __result)
        {
            float mult = Config.IntensityMultiplier.Value;
            if (mult != 1.0f)
                __result *= mult;
        }
    }
}
