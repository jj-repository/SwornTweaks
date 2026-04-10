
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
using UnityEngine;

namespace SwornTweaks.Patches
{
    /// <summary>
    /// Guarantee one KissPortal (fae realm) and one KissCursePortal per run.
    ///
    /// Hooks PathGenerator.GeneratePaths Postfix to:
    ///   1. Track whether each portal type has naturally spawned
    ///   2. At a deadline room (8+) in the appropriate biome, inject the portal
    ///      if it hasn't appeared yet
    ///
    /// Kiss is guaranteed in biome 0 (first combat biome).
    /// KissCurse is guaranteed in biome 1 (second combat biome).
    /// </summary>
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class FaeRealmPatch
    {
        internal static bool KissSpawned;
        internal static bool KissCurseSpawned;

        private const int DEADLINE_ROOM = 8;

        static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result,
                            int nextRoomIndex, BiomeData biome)
        {
            if (!Config.GuaranteedFaeKiss.Value && !Config.GuaranteedFaeKissCurse.Value) return;
            if (__result == null || __result.Length == 0) return;

            var bt = biome != null ? biome.GetBiomeType() : BiomeType.None;
            if (bt == BiomeType.Camelot || bt == BiomeType.Somewhere || bt == BiomeType.None)
                return;

            // Scan existing post-level events to track natural spawns
            for (int i = 0; i < __result.Length; i++)
            {
                var path = __result[i];
                if (path?.postLevelEvents == null) continue;
                for (int j = 0; j < path.postLevelEvents.Length; j++)
                {
                    if (path.postLevelEvents[j] == PostLevelEventType.KissPortal)
                        KissSpawned = true;
                    if (path.postLevelEvents[j] == PostLevelEventType.KissCursePortal)
                        KissCurseSpawned = true;
                }
            }

            bool kissDone = KissSpawned || !Config.GuaranteedFaeKiss.Value;
            bool curseDone = KissCurseSpawned || !Config.GuaranteedFaeKissCurse.Value;
            if (kissDone && curseDone) return;
            if (nextRoomIndex < DEADLINE_ROOM) return;

            // Skip boss/beast rooms — don't inject portals there
            var firstPath = __result[0];
            if (firstPath != null &&
                (firstPath.roomType == RoomType.Boss || firstPath.roomType == RoomType.MiniBoss))
                return;

            // Get current biome index to decide which portal to inject
            int biomeIndex = -1;
            try
            {
                var em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                if (em != null) biomeIndex = em.BiomeIndex;
            }
            catch { } // FindObjectOfType not available outside of gameplay scenes

            PostLevelEventType toInject = PostLevelEventType.None;

            if (!KissSpawned && Config.GuaranteedFaeKiss.Value && biomeIndex <= 0)
            {
                toInject = PostLevelEventType.KissPortal;
                KissSpawned = true;
            }
            else if (!KissCurseSpawned && Config.GuaranteedFaeKissCurse.Value && biomeIndex >= 1)
            {
                toInject = PostLevelEventType.KissCursePortal;
                KissCurseSpawned = true;
            }

            if (toInject == PostLevelEventType.None) return;

            // Inject into the first path's post-level events
            for (int i = 0; i < __result.Length; i++)
            {
                var path = __result[i];
                if (path == null) continue;

                var existing = path.postLevelEvents;
                int oldLen = existing?.Length ?? 0;
                var newEvents = new Il2CppStructArray<PostLevelEventType>(oldLen + 1);
                for (int j = 0; j < oldLen; j++)
                    newEvents[j] = existing![j];
                newEvents[oldLen] = toInject;
                path.postLevelEvents = newEvents;
            }

            MelonLogger.Msg($"[SwornTweaks] Injected {toInject} at room {nextRoomIndex} (biome={bt}, biomeIdx={biomeIndex})");
        }
    }

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    static class FaeRealmReset
    {
        static void Prefix()
        {
            FaeRealmPatch.KissSpawned = false;
            FaeRealmPatch.KissCurseSpawned = false;
        }
    }
}
