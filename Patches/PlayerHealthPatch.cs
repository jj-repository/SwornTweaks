using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace SwornTweaks.Patches
{
    [HarmonyPatch(typeof(CharacterHealth), nameof(CharacterHealth.Setup))]
    static class PlayerHealthPatch
    {
        static void Postfix(CharacterHealth __instance)
        {
            float mult = Config.PlayerHealthMultiplier.Value;
            if (mult == 1.0f) return;

            // Only apply to players, not bosses (BossHealth also extends CharacterHealth)
            var player = __instance.GetComponentInParent<Player>();
            if (player == null) return;

            var healthStats = player.HealthStats;
            if (healthStats?.HealthMultiplier == null) return;

            healthStats.HealthMultiplier.AddMod(mult);
            MelonLogger.Msg($"[SwornTweaks] Player health multiplier applied: {mult}x");
        }
    }
}
