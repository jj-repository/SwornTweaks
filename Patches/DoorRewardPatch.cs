using System;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    static class DoorRewardPatch
    {
        static void Postfix(Il2CppReferenceArray<ExpeditionManager.Path> __result)
        {
            if (!Config.NoCurrencyDoorRewards.Value) return;
            if (__result == null) return;

            var rng = new Random();
            for (int i = 0; i < __result.Length; i++)
            {
                var path = __result[i];
                if (path == null) continue;

                var reward = path.rewardType;
                if (reward == RewardType.FairyEmber || reward == RewardType.Silk || reward == RewardType.Moonstone)
                {
                    path.rewardType = rng.Next(2) == 0 ? RewardType.ParagonLevelUp : RewardType.Paragon;
                }
            }
        }
    }
}
