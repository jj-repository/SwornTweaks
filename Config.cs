using MelonLoader;

namespace SwornTweaks
{
    internal static class Config
    {
        private static MelonPreferences_Category _cat = null!;

        // Rerolls
        internal static MelonPreferences_Entry<int> BonusRerolls = null!;
        internal static MelonPreferences_Entry<bool> InfiniteRerolls = null!;

        // Blessing rarity
        internal static MelonPreferences_Entry<float> LegendaryChance = null!;
        internal static MelonPreferences_Entry<float> EpicChance = null!;
        internal static MelonPreferences_Entry<float> RareChance = null!;
        internal static MelonPreferences_Entry<float> UncommonChance = null!;

        // Gem cost
        internal static MelonPreferences_Entry<bool> NoGemCost = null!;
        internal static MelonPreferences_Entry<bool> RingOfDispelFree = null!;

        // Gold
        internal static MelonPreferences_Entry<bool> UnlimitedGold = null!;

        // Door rewards
        internal static MelonPreferences_Entry<bool> NoCurrencyDoorRewards = null!;

        // Duo blessings
        internal static MelonPreferences_Entry<float> DuoChance = null!;

        // Round Table
        internal static MelonPreferences_Entry<float> RoundTableChance = null!;

        // Run length / biome sequence
        internal static MelonPreferences_Entry<int> ExtraBiomes = null!;
        internal static MelonPreferences_Entry<bool> RandomizeRepeats = null!;
        internal static MelonPreferences_Entry<bool> AllBiomesRandom = null!;
        internal static MelonPreferences_Entry<bool> ProgressiveScaling = null!;
        internal static MelonPreferences_Entry<float> ProgressiveScalingGrowth = null!;

        // Beast rooms
        internal static MelonPreferences_Entry<bool> UseVanillaBeastSettings = null!;
        internal static MelonPreferences_Entry<bool> SpawnBeastBosses = null!;
        internal static MelonPreferences_Entry<bool> ForceBiomeBoss = null!;
        internal static MelonPreferences_Entry<int> FixedExtraBosses = null!;
        internal static MelonPreferences_Entry<float> BeastChancePercent = null!;
        internal static MelonPreferences_Entry<int> MaxBeastsPerBiome = null!;

        // Player
        internal static MelonPreferences_Entry<float> PlayerHealthMultiplier = null!;
        internal static MelonPreferences_Entry<float> PlayerDamageMultiplier = null!;
        internal static MelonPreferences_Entry<bool> InfiniteMana = null!;
        internal static MelonPreferences_Entry<bool> Invincible = null!;

        // Health multipliers
        internal static MelonPreferences_Entry<float> BossHealthMultiplier = null!;
        internal static MelonPreferences_Entry<float> BeastHealthMultiplier = null!;

        // Damage multipliers (boss/beast)
        internal static MelonPreferences_Entry<float> BossDamageMultiplier = null!;
        internal static MelonPreferences_Entry<float> BeastDamageMultiplier = null!;

        // Intensity
        internal static MelonPreferences_Entry<float> IntensityMultiplier = null!;

        // Enemy scaling (normal enemies only)
        internal static MelonPreferences_Entry<float> EnemyHealthMultiplier = null!;
        internal static MelonPreferences_Entry<float> EnemyDamageMultiplier = null!;

        // Fae Realms
        internal static MelonPreferences_Entry<bool> GuaranteedFaeKiss = null!;
        internal static MelonPreferences_Entry<bool> GuaranteedFaeKissCurse = null!;

        // Sword in the Stone
        internal static MelonPreferences_Entry<int> GuaranteedSwordsBiomes = null!;

        // Skip Somewhere
        internal static MelonPreferences_Entry<bool> SkipSomewhere = null!;

        // Extra Blessings
        internal static MelonPreferences_Entry<int> ExtraBlessings = null!;

        // Boss Rush
        internal static MelonPreferences_Entry<bool> BossRushMode = null!;
        internal static MelonPreferences_Entry<int> BossRushHornRewards = null!;
        internal static MelonPreferences_Entry<int> BossRushHealPerRoom = null!;
        internal static MelonPreferences_Entry<float> BossRushScaling = null!;
        internal static MelonPreferences_Entry<bool> BossRushRandomizer = null!;
        internal static MelonPreferences_Entry<int> BossRushExtraBlessings = null!;

        // Fight a Specific Boss
        internal static MelonPreferences_Entry<bool> FightBossMode = null!;
        internal static MelonPreferences_Entry<string> FightBossSelection = null!;
        internal static MelonPreferences_Entry<int> FightBossRepeat = null!;
        internal static MelonPreferences_Entry<float> FightBossDamageMultiplier = null!;
        internal static MelonPreferences_Entry<int> FightBossHealth = null!;

        internal static void Init()
        {
            _cat = MelonPreferences.CreateCategory("SwornTweaks");

            BonusRerolls = _cat.CreateEntry("BonusRerolls", 0,
                "Extra rerolls added at the start of each run");
            InfiniteRerolls = _cat.CreateEntry("InfiniteRerolls", false,
                "Set rerolls to 500 on every scene load");

            LegendaryChance = _cat.CreateEntry("LegendaryChance", 0.03f,
                "Base chance for legendary blessings");
            EpicChance = _cat.CreateEntry("EpicChance", 0.08f,
                "Base chance for epic blessings");
            RareChance = _cat.CreateEntry("RareChance", 0.20f,
                "Base chance for rare blessings");
            UncommonChance = _cat.CreateEntry("UncommonChance", 0.25f,
                "Base chance for uncommon blessings");

            NoGemCost = _cat.CreateEntry("NoGemCost", false,
                "Skip the 300 gold Lancelot gem socket cost (need 300 gold to see option)");
            RingOfDispelFree = _cat.CreateEntry("RingOfDispelFree", false,
                "Unlock Ring of Dispel without buying gems (skip straight to Somewhere)");

            UnlimitedGold = _cat.CreateEntry("UnlimitedGold", false,
                "Make the game think you always have max gold (everything is free)");

            NoCurrencyDoorRewards = _cat.CreateEntry("NoCurrencyDoorRewards", false,
                "Replace currency door rewards (FairyEmber/Silk/Moonstone) with Paragon rewards");

            DuoChance = _cat.CreateEntry("DuoChance", 0.0f,
                "Duo blessing chance (0.35 = 35%)");

            RoundTableChance = _cat.CreateEntry("RoundTableChance", 0.0f,
                "Round Table blessing chance (0.0 = vanilla)");

            ExtraBiomes = _cat.CreateEntry("ExtraBiomes", 0,
                "Number of extra combat biomes to add (0-3, inserted after DeepHarbor)");
            RandomizeRepeats = _cat.CreateEntry("RandomizeRepeats", false,
                "Randomize which biomes are used for extra slots");
            AllBiomesRandom = _cat.CreateEntry("AllBiomesRandom", false,
                "Completely randomize all combat biome order");
            ProgressiveScaling = _cat.CreateEntry("ProgressiveScaling", false,
                "Normalize mob HP by biome slot position (for AllBiomesRandom/ExtraBiomes)");
            ProgressiveScalingGrowth = _cat.CreateEntry("ProgressiveScalingGrowth", 1.5f,
                "Scales difficulty for extra or random biomes (1.0 = no scaling)");

            UseVanillaBeastSettings = _cat.CreateEntry("UseVanillaBeastSettings", true,
                "Use vanilla beast spawning (ignores all beast room settings below)");

            SpawnBeastBosses = _cat.CreateEntry("SpawnBeastBosses", true,
                "Include legendary beasts (mini-bosses) in extra boss room pool");
            ForceBiomeBoss = _cat.CreateEntry("ForceBiomeBoss", false,
                "Also include biome end bosses in extra boss room pool");
            FixedExtraBosses = _cat.CreateEntry("FixedExtraBosses", 0,
                "Number of guaranteed extra boss rooms per biome (0-3, placed randomly in valid range)");
            BeastChancePercent = _cat.CreateEntry("BeastChancePercent", 0.0f,
                "Percent chance per room for a beast (Legendary Beast) fight (0 = disabled)");
            MaxBeastsPerBiome = _cat.CreateEntry("MaxBeastsPerBiome", 5,
                "Max random beast encounters per biome (fixed rooms don't count)");

            PlayerHealthMultiplier = _cat.CreateEntry("PlayerHealthMultiplier", 1.0f,
                "Health multiplier for the player character (1.0 = no change)");
            PlayerDamageMultiplier = _cat.CreateEntry("PlayerDamageMultiplier", 1.0f,
                "Damage multiplier for the player character (1.0 = no change)");
            InfiniteMana = _cat.CreateEntry("InfiniteMana", false,
                "Infinite mana — mana never decreases");
            Invincible = _cat.CreateEntry("Invincible", false,
                "Player takes no damage");

            BossHealthMultiplier = _cat.CreateEntry("BossHealthMultiplier", 1.0f,
                "Health multiplier for bosses like Gawain, Arthur (1.0 = no change)");
            BeastHealthMultiplier = _cat.CreateEntry("BeastHealthMultiplier", 1.0f,
                "Health multiplier for legendary beasts like Dagonet (1.0 = no change)");

            BossDamageMultiplier = _cat.CreateEntry("BossDamageMultiplier", 1.0f,
                "Damage multiplier for bosses (1.0 = no change)");
            BeastDamageMultiplier = _cat.CreateEntry("BeastDamageMultiplier", 1.0f,
                "Damage multiplier for legendary beasts (1.0 = no change)");

            IntensityMultiplier = _cat.CreateEntry("IntensityMultiplier", 1.0f,
                "Global room intensity multiplier (1.0 = no change, higher = harder spawns)");

            EnemyHealthMultiplier = _cat.CreateEntry("EnemyHealthMultiplier", 1.0f,
                "Health multiplier for normal enemies (not bosses/beasts) (1.0 = no change)");
            EnemyDamageMultiplier = _cat.CreateEntry("EnemyDamageMultiplier", 1.0f,
                "Damage multiplier for normal enemies (not bosses/beasts) (1.0 = no change)");

            GuaranteedFaeKiss = _cat.CreateEntry("GuaranteedFaeKiss", false,
                "Guarantee one Kiss fae portal per run");
            GuaranteedFaeKissCurse = _cat.CreateEntry("GuaranteedFaeKissCurse", false,
                "Guarantee one Kiss Curse fae portal per run");

            GuaranteedSwordsBiomes = _cat.CreateEntry("GuaranteedSwordsBiomes", 0,
                "Number of biomes that get a guaranteed Sword in the Stone (0=disabled, 1-4)");

            SkipSomewhere = _cat.CreateEntry("SkipSomewhere", false,
                "Skip the Somewhere level and go directly to Morgana");

            ExtraBlessings = _cat.CreateEntry("ExtraBlessings", 0,
                "Extra blessing rewards after each room (0-3)");

            BossRushMode = _cat.CreateEntry("BossRushMode", false,
                "Structured boss rush: 1 normal room + unique beasts + unique bosses per biome");
            BossRushHornRewards = _cat.CreateEntry("BossRushHornRewards", 1,
                "Trove (horn) rewards per boss rush room (0-3)");
            BossRushHealPerRoom = _cat.CreateEntry("BossRushHealPerRoom", 15,
                "HP healed after each boss rush room (0 = disabled)");
            BossRushScaling = _cat.CreateEntry("BossRushScaling", 1.25f,
                "HP multiplier compounding per boss rush room (1.0 = no scaling)");
            BossRushRandomizer = _cat.CreateEntry("BossRushRandomizer", false,
                "Randomize all boss/beast order across biomes (Roundtable skipped, Morgana always last)");
            BossRushExtraBlessings = _cat.CreateEntry("BossRushExtraBlessings", 0,
                "Extra blessing rewards per boss rush room (0-3)");

            FightBossMode = _cat.CreateEntry("FightBossMode", false,
                "Enable specific boss fight mode (force-load a chosen boss)");
            FightBossSelection = _cat.CreateEntry("FightBossSelection", "Gawain",
                "Boss identifier to fight (e.g. Gawain, Arthur, Morgana)");
            FightBossRepeat = _cat.CreateEntry("FightBossRepeat", 1,
                "Number of times to repeat the boss fight (1-5)");
            FightBossDamageMultiplier = _cat.CreateEntry("FightBossDamageMultiplier", 1.0f,
                "Damage multiplier for the fight boss (1.0 = no change)");
            FightBossHealth = _cat.CreateEntry("FightBossHealth", 0,
                "Exact HP for the fight boss (0 = use default boss health)");

        }
    }
}
