using MelonLoader;

namespace SwornTweaks
{
    internal static class Config
    {
        private static MelonPreferences_Category _cat = null!;

        // Rerolls
        internal static MelonPreferences_Entry<int> BonusRerolls = null!;

        // Blessing rarity
        internal static MelonPreferences_Entry<float> LegendaryChance = null!;
        internal static MelonPreferences_Entry<float> EpicChance = null!;
        internal static MelonPreferences_Entry<float> RareChance = null!;
        internal static MelonPreferences_Entry<float> UncommonChance = null!;

        // Gem cost
        internal static MelonPreferences_Entry<bool> NoGemCost = null!;

        // Door rewards
        internal static MelonPreferences_Entry<bool> NoCurrencyDoorRewards = null!;

        // Duo blessings
        internal static MelonPreferences_Entry<float> DuoChance = null!;

        // Biome repeat
        internal static MelonPreferences_Entry<bool> EnableBiomeRepeat = null!;
        internal static MelonPreferences_Entry<string> RepeatBiome = null!;
        internal static MelonPreferences_Entry<string> RepeatAfterBiome = null!;

        // Beast rooms
        internal static MelonPreferences_Entry<float> BeastChancePercent = null!;
        internal static MelonPreferences_Entry<int> BeastRoom1 = null!;
        internal static MelonPreferences_Entry<int> BeastRoom2 = null!;

        // Health multipliers
        internal static MelonPreferences_Entry<float> BossHealthMultiplier = null!;
        internal static MelonPreferences_Entry<float> BeastHealthMultiplier = null!;

        internal static void Init()
        {
            _cat = MelonPreferences.CreateCategory("SwornTweaks");

            BonusRerolls = _cat.CreateEntry("BonusRerolls", 500,
                "Extra rerolls added at the start of each run");

            LegendaryChance = _cat.CreateEntry("LegendaryChance", 0.03f,
                "Base chance for legendary blessings");
            EpicChance = _cat.CreateEntry("EpicChance", 0.08f,
                "Base chance for epic blessings");
            RareChance = _cat.CreateEntry("RareChance", 0.20f,
                "Base chance for rare blessings");
            UncommonChance = _cat.CreateEntry("UncommonChance", 0.25f,
                "Base chance for uncommon blessings");

            NoGemCost = _cat.CreateEntry("NoGemCost", true,
                "Skip the 300 gold gem socket cost");

            NoCurrencyDoorRewards = _cat.CreateEntry("NoCurrencyDoorRewards", true,
                "Replace currency door rewards (FairyEmber/Silk/Moonstone) with Paragon rewards");

            DuoChance = _cat.CreateEntry("DuoChance", 0.35f,
                "Duo blessing chance (0.35 = 35%)");

            EnableBiomeRepeat = _cat.CreateEntry("EnableBiomeRepeat", true,
                "Insert a repeated biome into the expedition sequence");
            RepeatBiome = _cat.CreateEntry("RepeatBiome", "Kingswood",
                "Which biome to repeat (Kingswood, Cornucopia, DeepHarbor)");
            RepeatAfterBiome = _cat.CreateEntry("RepeatAfterBiome", "Cornucopia",
                "Insert the repeat after this biome");

            BeastChancePercent = _cat.CreateEntry("BeastChancePercent", 15.0f,
                "Percent chance per room for a beast (Legendary Beast) fight (0 = disabled)");
            BeastRoom1 = _cat.CreateEntry("BeastRoom1", -1,
                "Force beast at this 0-based room index (-1 = disabled)");
            BeastRoom2 = _cat.CreateEntry("BeastRoom2", -1,
                "Force beast at this 0-based room index (-1 = disabled)");

            BossHealthMultiplier = _cat.CreateEntry("BossHealthMultiplier", 3.0f,
                "Health multiplier for bosses like Gawain, Arthur (1.0 = no change)");
            BeastHealthMultiplier = _cat.CreateEntry("BeastHealthMultiplier", 2.0f,
                "Health multiplier for legendary beasts like Dagonet (1.0 = no change)");
        }
    }
}
