using MelonLoader;
using SwornTweaks.Patches;

[assembly: MelonInfo(typeof(SwornTweaks.Core), "SwornTweaks", "1.0.0", "Vercility")]
[assembly: MelonGame("Windwalk Games", "SWORN")]

namespace SwornTweaks
{
    public class Core : MelonMod
    {
        public override void OnInitializeMelon()
        {
            Config.Init();
            LoggerInstance.Msg("SwornTweaks loaded.");
            LoggerInstance.Msg($"  Rerolls: +{Config.BonusRerolls.Value}, Infinite: {Config.InfiniteRerolls.Value}");
            LoggerInstance.Msg($"  Rarity: L={Config.LegendaryChance.Value} E={Config.EpicChance.Value} R={Config.RareChance.Value} U={Config.UncommonChance.Value} RT={Config.RoundTableChance.Value}");
            LoggerInstance.Msg($"  NoGemCost: {Config.NoGemCost.Value}, RingOfDispelFree: {Config.RingOfDispelFree.Value}, UnlimitedGold: {Config.UnlimitedGold.Value}");
            LoggerInstance.Msg($"  NoCurrencyDoorRewards: {Config.NoCurrencyDoorRewards.Value}");
            LoggerInstance.Msg($"  DuoChance: {Config.DuoChance.Value}");
            LoggerInstance.Msg($"  ExtraBiomes: {Config.ExtraBiomes.Value}, RandomRepeats: {Config.RandomizeRepeats.Value}, AllRandom: {Config.AllBiomesRandom.Value}, ProgressiveHP: {Config.ProgressiveScaling.Value} (growth={Config.ProgressiveScalingGrowth.Value}x)");
            LoggerInstance.Msg($"  VanillaBeast: {Config.UseVanillaBeastSettings.Value}, Beast: {Config.SpawnBeastBosses.Value}, MainBoss: {Config.ForceBiomeBoss.Value}, Fixed: {Config.FixedExtraBosses.Value}, Chance: {Config.BeastChancePercent.Value}% (max {Config.MaxBeastsPerBiome.Value}/biome)");
            LoggerInstance.Msg($"  PlayerHP: {Config.PlayerHealthMultiplier.Value}x, PlayerDMG: {Config.PlayerDamageMultiplier.Value}x, InfMana: {Config.InfiniteMana.Value}, Invincible: {Config.Invincible.Value}, BossHP: {Config.BossHealthMultiplier.Value}x, BeastHP: {Config.BeastHealthMultiplier.Value}x, BossDMG: {Config.BossDamageMultiplier.Value}x, BeastDMG: {Config.BeastDamageMultiplier.Value}x");
            LoggerInstance.Msg($"  Intensity: {Config.IntensityMultiplier.Value}x");
            LoggerInstance.Msg($"  EnemyHP: {Config.EnemyHealthMultiplier.Value}x, EnemyDMG: {Config.EnemyDamageMultiplier.Value}x");
            LoggerInstance.Msg($"  FaeKiss: {Config.GuaranteedFaeKiss.Value}, FaeKissCurse: {Config.GuaranteedFaeKissCurse.Value}");
            LoggerInstance.Msg($"  SkipSomewhere: {Config.SkipSomewhere.Value}");
            LoggerInstance.Msg($"  BossRush: {Config.BossRushMode.Value}, Horns: {Config.BossRushHornRewards.Value}, Blessings: {Config.BossRushExtraBlessings.Value}, Heal: {Config.BossRushHealPerRoom.Value}, Scaling: {Config.BossRushScaling.Value}x, Randomizer: {Config.BossRushRandomizer.Value}");
            LoggerInstance.Msg($"  AutoSave: {Config.AutoSaveEnabled.Value}, LoadOnStart: {Config.LoadSaveOnStart.Value}");
        }

        public override void OnApplicationQuit()
        {
            SaveStateSave.DoSave();
        }

        public override void OnSceneWasLoaded(int buildIndex, string sceneName)
        {
            if (!Config.InfiniteRerolls.Value) return;
            try
            {
                Il2Cpp.RerollManager.SetRerolls(500);
                var rm = RerollPatch.Instance;
                if (rm != null) rm.baseRerolls = 500;
            }
            catch { /* RerollManager not ready yet — RerollPatch Postfix handles it */ }
        }
    }
}
