# SwornTweaks

All-in-one SWORN mod combining rerolls, blessing rarity, gem cost skip, unlimited gold, door reward replacement, duo boost, biome repeat, random beast rooms, boss/beast/player health and damage multipliers, intensity scaling, fae realm guarantees, guaranteed sword in the stone, extra blessings, a structured boss rush mode, and a fight-specific-boss mode. Everything is configurable.

## Installation

See [INSTALL.md](INSTALL.md) for detailed setup instructions (Windows + Linux).

Quick start:
1. Copy `SwornTweaks.dll` to `SWORN/Mods/`
2. Launch the game — config file is created automatically

## Configurator GUI

A visual config editor with auto-update from GitHub:

```bash
python3 configurator.py
```

![SwornTweaks Configurator](screenshots/configurator.png)

See [INSTALL.md](INSTALL.md) for setup. Windows standalone `.exe` available in [Releases](https://github.com/jj-repository/SwornTweaks/releases).

Features:
- Tabbed interface: **Player**, **Enemies**, **Toggles**, **Game Modes**, **Settings**, **Help**
- Save/load config, share config codes, import/export `.cfg` files
- Auto-update check for DLL and GUI from GitHub releases
- Mascot image in Settings tab

## Configuration

Settings are stored in `SWORN/UserData/MelonPreferences.cfg` under the `[SwornTweaks]` section. Changes take effect on the next run start.

### Rerolls

| Setting | Default | Description |
|---------|---------|-------------|
| `BonusRerolls` | `50` | Extra rerolls added at the start of each run |
| `InfiniteRerolls` | `false` | Set rerolls to 500 on every scene load |

### Blessing Rarity

| Setting | Default | Description |
|---------|---------|-------------|
| `LegendaryChance` | `0.03` | Base chance for legendary blessings (3%) |
| `EpicChance` | `0.08` | Base chance for epic blessings (8%) |
| `RareChance` | `0.20` | Base chance for rare blessings (20%) |
| `UncommonChance` | `0.25` | Base chance for uncommon blessings (25%) |

### Extra Blessings

| Setting | Default | Description |
|---------|---------|-------------|
| `ExtraBlessings` | `0` | Extra blessing rewards after each room (0-3) |

### Gem Cost

| Setting | Default | Description |
|---------|---------|-------------|
| `NoGemCost` | `true` | Skip the 300 gold Lancelot gem socket cost (need 300 gold to see option) |
| `RingOfDispelFree` | `false` | Unlock Ring of Dispel without buying gems (skip straight to Somewhere) |

### Gold

| Setting | Default | Description |
|---------|---------|-------------|
| `UnlimitedGold` | `false` | Make the game think you always have max gold (everything is free) |

### Door Rewards

| Setting | Default | Description |
|---------|---------|-------------|
| `NoCurrencyDoorRewards` | `true` | Replace currency rewards (FairyEmber, Silk, Moonstone) with Paragon/ParagonLevelUp |

### Duo Blessings

| Setting | Default | Description |
|---------|---------|-------------|
| `DuoChance` | `0.35` | Duo blessing chance (0.35 = 35%) |

### Player

| Setting | Default | Description |
|---------|---------|-------------|
| `PlayerHealthMultiplier` | `1.0` | Health multiplier for the player character (1.0 = no change) |
| `PlayerDamageMultiplier` | `1.0` | Damage multiplier for the player character (1.0 = no change) |
| `InfiniteMana` | `false` | Infinite mana — mana never decreases |
| `Invincible` | `false` | Player takes no damage |

### Increase Run Length

| Setting | Default | Description |
|---------|---------|-------------|
| `ExtraBiomes` | `0` | Number of extra combat biomes (0-3, inserted after DeepHarbor) |
| `RandomizeRepeats` | `false` | Randomize which biomes fill the extra slots |
| `AllBiomesRandom` | `false` | Completely randomize all combat biome order |
| `ProgressiveScaling` | `false` | Normalize mob HP by biome slot position |
| `ProgressiveScalingGrowth` | `1.5` | Scales difficulty for extra or random biomes (1.0 = no scaling) |

Extra biomes are inserted after the original 3 combat biomes (Kingswood, Cornucopia, DeepHarbor) and before Camelot/Somewhere. By default they cycle in order:

- **+1**: ... → DeepHarbor → **Kingswood** → Camelot → Somewhere
- **+2**: ... → DeepHarbor → **Kingswood** → **Cornucopia** → Camelot → Somewhere
- **+3**: ... → DeepHarbor → **Kingswood** → **Cornucopia** → **DeepHarbor** → Camelot → Somewhere

With `RandomizeRepeats`, each extra slot is randomly picked from the 3 combat biomes. With `AllBiomesRandom`, all combat biome slots (original + extras) are fully randomized — DeepHarbor could be first, Kingswood could appear twice, etc. Camelot and Somewhere always remain at the end.

#### Progressive HP Scaling

When `ProgressiveScaling` is enabled, mob HP is normalized by biome slot position so each slot feels appropriately difficult regardless of which biome fills it. This is especially useful with `AllBiomesRandom` where a hard biome like DeepHarbor could land in slot 0.

The correction formula is: `multiplier = slot_target / native_power`

**Native biome power** (average mob HP relative to Kingswood):

| Biome | Power |
|-------|-------|
| Kingswood | 1.0 |
| Cornucopia | 1.5 |
| DeepHarbor | 4.0 |

**Slot targets** (vanilla order for slots 0-2, then configurable growth per extra slot):

| Slot | Target (at default 1.5x growth) |
|------|--------|
| 0 | 1.0 |
| 1 | 1.5 |
| 2 | 4.0 |
| 3 | 6.0 (4.0 x 1.5) |
| 4 | 9.0 (4.0 x 1.5^2) |
| 5 | 13.5 (4.0 x 1.5^3) |

Slots 3+ use the formula: `4.0 x ProgressiveScalingGrowth ^ (slot - 2)`. Adjust `ProgressiveScalingGrowth` to control how aggressively extra slots scale up.

**Examples:**
- DeepHarbor in slot 0: 1.0/4.0 = **0.25x** (scaled down to feel like Kingswood)
- Kingswood in slot 2: 4.0/1.0 = **4.0x** (scaled up to feel like DeepHarbor)
- Cornucopia in slot 1: 1.5/1.5 = **1.0x** (natural position, no change)
- Kingswood in slot 4: 9.0/1.0 = **9.0x** (extra biome, scaled up)
- DeepHarbor in slot 4: 9.0/4.0 = **2.25x** (extra biome, moderate boost)

With vanilla biome order and no extra biomes, all corrections are 1.0x (no effect). The progressive multiplier stacks multiplicatively with `BossHealthMultiplier`, `BeastHealthMultiplier`, and `EnemyHealthMultiplier`. Does not affect Camelot or Somewhere.

### Extra Boss Rooms

| Setting | Default | Description |
|---------|---------|-------------|
| `UseVanillaBeastSettings` | `true` | Disable extra boss rooms (ignores all settings below) |
| `SpawnBeastBosses` | `true` | Include legendary beasts (mini-bosses) in extra boss room pool |
| `ForceBiomeBoss` | `false` | Also include biome end bosses in the pool |
| `FixedExtraBosses` | `0` | Guaranteed extra boss rooms per biome (0-3) |
| `BeastChancePercent` | `0` | % chance per room for an extra boss fight (0 = disabled) |
| `MaxBeastsPerBiome` | `5` | Max random beast encounters per biome (fixed rooms don't count) |

Room counts: Kingswood=15, Cornucopia=13, DeepHarbor=13. Fixed extra bosses are placed randomly in the eligible range (rooms 3 through totalRooms-3), protecting the early tutorial rooms and the biome boss room. Random chance also protects the last biome room and respects the per-biome cap.

### Health & Damage Multipliers

| Setting | Default | Description |
|---------|---------|-------------|
| `BossHealthMultiplier` | `2.0` | Health multiplier for bosses like Gawain, Arthur (1.0 = no change) |
| `BossDamageMultiplier` | `1.0` | Damage multiplier for bosses (1.0 = no change) |
| `BeastHealthMultiplier` | `2.0` | Health multiplier for legendary beasts like Dagonet (1.0 = no change) |
| `BeastDamageMultiplier` | `1.0` | Damage multiplier for legendary beasts (1.0 = no change) |

### Enemy Scaling

| Setting | Default | Description |
|---------|---------|-------------|
| `EnemyHealthMultiplier` | `1.0` | Health multiplier for normal enemies (1.0 = no change) |
| `EnemyDamageMultiplier` | `1.0` | Damage multiplier for normal enemies (1.0 = no change) |

Affects regular enemies only — bosses and legendary beasts use their own multipliers above.

### Intensity

| Setting | Default | Description |
|---------|---------|-------------|
| `IntensityMultiplier` | `1.0` | Global room intensity multiplier (higher = harder spawns) |

Multiplies the result of `BiomeData.GetRoomIntensity`. Affects enemy spawn density/difficulty across all biomes.

### Fae Realms

| Setting | Default | Description |
|---------|---------|-------------|
| `GuaranteedFaeKiss` | `false` | Guarantee one Kiss fae portal per run |
| `GuaranteedFaeKissCurse` | `false` | Guarantee one Kiss Curse fae portal per run |

### Sword in the Stone

| Setting | Default | Description |
|---------|---------|-------------|
| `GuaranteedSwordsBiomes` | `0` | Number of biomes with a guaranteed Sword in the Stone drop (0-4) |

When set to 1-4, forces one Sword in the Stone reward per biome for that many biomes. Value of 0 disables the feature (vanilla random chance). Setting 4 covers all 3 combat biomes plus Camelot (after Arthur). Somewhere never spawns Sword in the Stone drops.

### Skip Somewhere

| Setting | Default | Description |
|---------|---------|-------------|
| `SkipSomewhere` | `false` | Skip the Somewhere level and go directly to Morgana |

### Boss Rush

| Setting | Default | Description |
|---------|---------|-------------|
| `BossRushMode` | `false` | Structured boss rush — shortened biomes with unique encounters |
| `BossRushHornRewards` | `1` | Trove (horn) rewards per boss rush room (0-3) |
| `BossRushHealPerRoom` | `15` | HP healed after each boss rush room (0 = disabled) |
| `BossRushScaling` | `1.25` | HP multiplier compounding per room (1.0 = no scaling) |
| `BossRushRandomizer` | `false` | Randomize all boss/beast order across biomes |
| `BossRushExtraBlessings` | `0` | Extra blessing rewards per boss rush room (0-3) |

When enabled, each combat biome is shortened to a structured sequence:

- **Room 0**: Normal combat room with SwordInTheStone paragon reward
- **Rooms 1-N**: Each unique beast (legendary beast/mini-boss) in the biome, shuffled, no repeats
- **Rooms N+1-end**: Each unique biome boss, shuffled, no repeats
- **Last boss per biome**: Healing fountain reward + fae portal (Kiss on 1st biome, KissCurse on 2nd)

All rooms receive configurable trove (horn) rewards. Unwanted post-level events (random fae portals, Black Knight, etc.) are cleared from beast/boss rooms to keep the boss rush focused. After each room, players are healed by the configured HP amount. Boss/beast HP scales progressively per room across biomes (configurable multiplier, stacks with Boss/Beast Health Multipliers).

The Somewhere biome is shortened to 1 room (direct Morgana fight) with no extra rewards. The 3-gem Ring of Dispel requirement is automatically bypassed so you can always reach Morgana. In Camelot, the Roundtable knight fights stay vanilla.

When Boss Rush is active, the following GUI sections are disabled (incompatible): Toggles, Spawn Intensity, Fae Realms, Sword in the Stone, Extra Boss Rooms, Increase Run Length, and Fight Boss.

### Fight a Specific Boss

| Setting | Default | Description |
|---------|---------|-------------|
| `FightBossMode` | `false` | Enable specific boss fight mode (force-load a chosen boss) |
| `FightBossSelection` | `Gawain` | Boss identifier to fight |
| `FightBossRepeat` | `1` | Number of times to repeat the boss fight (1-5) |
| `FightBossDamageMultiplier` | `1.0` | Damage multiplier for the fight boss (1.0 = no change) |
| `FightBossHealth` | `0` | Exact HP for the fight boss (0 = use default boss health) |

Available bosses: Questing Beast, Sir Canis, Bedivere, Sirens, Gawain, Lady Kay, Arthur, Arthur Dragon, Morgana.

The GUI shows default vanilla HP (on Squire difficulty) for the selected boss. When Fight Boss is active, the Enemies tab, Toggles tab, and all other Game Modes sections are disabled.

Fight Boss and Boss Rush are mutually exclusive — enabling one disables the other.

## Example Config

```ini
[SwornTweaks]
BonusRerolls = 50
InfiniteRerolls = false
LegendaryChance = 0.03
EpicChance = 0.08
RareChance = 0.2
UncommonChance = 0.25
NoGemCost = true
RingOfDispelFree = false
UnlimitedGold = false
NoCurrencyDoorRewards = true
DuoChance = 0.35
ExtraBiomes = 0
RandomizeRepeats = false
AllBiomesRandom = false
ProgressiveScaling = false
ProgressiveScalingGrowth = 1.5
UseVanillaBeastSettings = true
SpawnBeastBosses = true
ForceBiomeBoss = false
FixedExtraBosses = 0
BeastChancePercent = 0
MaxBeastsPerBiome = 5
PlayerHealthMultiplier = 1
PlayerDamageMultiplier = 1
InfiniteMana = false
Invincible = false
BossHealthMultiplier = 2
BossDamageMultiplier = 1
BeastHealthMultiplier = 2
BeastDamageMultiplier = 1
EnemyHealthMultiplier = 1
EnemyDamageMultiplier = 1
IntensityMultiplier = 1
GuaranteedFaeKiss = false
GuaranteedFaeKissCurse = false
GuaranteedSwordsBiomes = 0
SkipSomewhere = false
ExtraBlessings = 0
BossRushMode = false
BossRushHornRewards = 1
BossRushHealPerRoom = 15
BossRushScaling = 1.25
BossRushRandomizer = false
BossRushExtraBlessings = 0
FightBossMode = false
FightBossSelection = Gawain
FightBossRepeat = 1
FightBossDamageMultiplier = 1
FightBossHealth = 0
```

## Supersedes

This mod replaces the following individual mods:
- SwornRerollMod
- SwornRarityMod
- SwornNoGemCost
- SwornNoCurrencyDoorRewards
- SwornDuoBoost
- SwornMoreRooms
- SwornBossHealthBoost
