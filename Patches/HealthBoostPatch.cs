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
            var health = __instance.HealthStats?.HealthMultiplier;

            if (__instance.IsBoss)
            {
                if (Config.BossHealthMultiplier.Value != 1.0f && health != null)
                {
                    health.AddMod(Config.BossHealthMultiplier.Value);
                    MelonLogger.Msg($"[SwornTweaks] {__instance.MobStats?.Type} — {Config.BossHealthMultiplier.Value}x boss HP");
                }
            }
            else if (__instance.IsMajorEnemy)
            {
                if (Config.BeastHealthMultiplier.Value != 1.0f && health != null)
                {
                    health.AddMod(Config.BeastHealthMultiplier.Value);
                    MelonLogger.Msg($"[SwornTweaks] {__instance.MobStats?.Type} — {Config.BeastHealthMultiplier.Value}x beast HP");
                }
            }
            else
            {
                float hp = Config.EnemyHealthMultiplier.Value;
                float dmg = Config.EnemyDamageMultiplier.Value;
                if (hp != 1.0f && health != null)
                    health.AddMod(hp);
                if (dmg != 1.0f)
                    __instance.CombatStats?.AttackMultiplier?.AddMod(dmg);
            }
        }
    }
}
