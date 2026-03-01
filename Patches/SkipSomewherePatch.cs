using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Skip Somewhere: shorten Somewhere biome to 1 room (last room = Morgana)
    /// so the player goes directly from Arthur to Morgana.
    /// Restores original rooms on next run start.
    /// </summary>
    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    [HarmonyPriority(Priority.LowerThanNormal)]
    static class SkipSomewherePatch
    {
        private static Il2CppReferenceArray<BiomeData.Room>? _originalSomewhereRooms;
        private static BiomeData? _somewhereRef;

        static void Prefix(ExpeditionManager __instance)
        {
            // Always restore originals from previous run first
            if (_somewhereRef != null && _originalSomewhereRooms != null)
            {
                _somewhereRef.rooms = _originalSomewhereRooms;
                _originalSomewhereRooms = null;
                _somewhereRef = null;
            }

            if (!Config.SkipSomewhere.Value || Config.BossRushMode.Value) return;

            var biomes = __instance.biomes;
            if (biomes == null) return;

            for (int i = 0; i < biomes.Count; i++)
            {
                var biome = biomes[i];
                if (biome == null) continue;
                var bt = biome.GetBiomeType();

                if (bt == BiomeType.Somewhere)
                {
                    var origRooms = biome.rooms;
                    if (origRooms == null || origRooms.Length <= 1) return;

                    _originalSomewhereRooms = origRooms;
                    _somewhereRef = biome;

                    var newRooms = new Il2CppReferenceArray<BiomeData.Room>(1);
                    newRooms[0] = origRooms[origRooms.Length - 1];
                    biome.rooms = newRooms;

                    MelonLogger.Msg($"[SwornTweaks] [SkipSomewhere] Somewhere shortened to 1 room (was {origRooms.Length})");
                    return;
                }
            }
        }
    }
}
