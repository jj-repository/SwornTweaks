using MelonLoader;

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
            LoggerInstance.Msg($"  Rerolls: +{Config.BonusRerolls.Value}");
            LoggerInstance.Msg($"  Rarity: L={Config.LegendaryChance.Value} E={Config.EpicChance.Value} R={Config.RareChance.Value} U={Config.UncommonChance.Value}");
            LoggerInstance.Msg($"  NoGemCost: {Config.NoGemCost.Value}");
            LoggerInstance.Msg($"  NoCurrencyDoorRewards: {Config.NoCurrencyDoorRewards.Value}");
            LoggerInstance.Msg($"  DuoChance: {Config.DuoChance.Value}");
            LoggerInstance.Msg($"  BiomeRepeat: {Config.EnableBiomeRepeat.Value} ({Config.RepeatBiome.Value} after {Config.RepeatAfterBiome.Value})");
            LoggerInstance.Msg($"  BeastChance: {Config.BeastChancePercent.Value}%");
            LoggerInstance.Msg($"  BossHP: {Config.BossHealthMultiplier.Value}x, BeastHP: {Config.BeastHealthMultiplier.Value}x");
        }
    }
}
