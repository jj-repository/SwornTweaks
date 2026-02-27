using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(Mob), nameof(Mob.SetMobDifficultyScaling))]
    static class HealthBoostPatch
    {
        static void Postfix(Mob __instance)
        {
            if (__instance.IsBoss && Config.BossHealthMultiplier.Value != 1.0f)
            {
                __instance.HealthStats.HealthMultiplier.AddMod(Config.BossHealthMultiplier.Value);
                MelonLogger.Msg($"[SwornTweaks] {__instance.MobStats?.Type} — applied {Config.BossHealthMultiplier.Value}x boss HP");
            }
            else if (__instance.IsMajorEnemy && Config.BeastHealthMultiplier.Value != 1.0f)
            {
                __instance.HealthStats.HealthMultiplier.AddMod(Config.BeastHealthMultiplier.Value);
                MelonLogger.Msg($"[SwornTweaks] {__instance.MobStats?.Type} — applied {Config.BeastHealthMultiplier.Value}x beast HP");
            }
        }
    }
}
