# SwornTweaks

All-in-one SWORN mod combining rerolls, blessing rarity, gem cost skip, door reward replacement, duo boost, biome repeat, random beast rooms, and boss/beast health multipliers. Everything is configurable.

## Installation

1. Build: `dotnet build -c Release`
2. Copy `bin/Release/net6.0/SwornTweaks.dll` to `SWORN/Mods/`
3. Remove any old individual mod DLLs (SwornRerollMod, SwornRarityMod, SwornNoGemCost, SwornNoCurrencyDoorRewards, SwornDuoBoost, SwornMoreRooms)
4. Launch the game — config file is created automatically

## Configurator GUI

A visual config editor is included — no need to edit the cfg file by hand:

```bash
python3 configurator.py
```

All settings can be adjusted with spinboxes, checkboxes, and dropdowns. Click **Save** to write to the cfg file.

## Configuration

Settings are stored in `SWORN/UserData/MelonPreferences.cfg` under the `[SwornTweaks]` section. Changes take effect on the next run start (no game restart needed for most settings).

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

### Gem Cost

| Setting | Default | Description |
|---------|---------|-------------|
| `NoGemCost` | `true` | Skip the 300 gold gem socket cost |

### Door Rewards

| Setting | Default | Description |
|---------|---------|-------------|
| `NoCurrencyDoorRewards` | `true` | Replace currency rewards (FairyEmber, Silk, Moonstone) with Paragon/ParagonLevelUp |

### Duo Blessings

| Setting | Default | Description |
|---------|---------|-------------|
| `DuoChance` | `0.35` | Duo blessing chance (0.35 = 35%) |

### Biome Repeat

| Setting | Default | Description |
|---------|---------|-------------|
| `EnableBiomeRepeat` | `true` | Insert a repeated biome into the expedition |
| `RepeatBiome` | `Kingswood` | Which biome to repeat |
| `RepeatAfterBiome` | `Cornucopia` | Insert the repeat after this biome |

Default sequence: Kingswood → Cornucopia → **Kingswood (repeat)** → DeepHarbor → Camelot → Somewhere

Valid biome names: `Kingswood`, `Cornucopia`, `DeepHarbor`, `Camelot`, `Somewhere`

### Beast Rooms

| Setting | Default | Description |
|---------|---------|-------------|
| `BeastChancePercent` | `0` | % chance per room for a Legendary Beast fight (0 = disabled) |
| `BeastRoom1` | `4` | Force beast at this 0-based room index (-1 = disabled) |
| `BeastRoom2` | `8` | Force beast at this 0-based room index (-1 = disabled) |

Beast rooms spawn randomly in Kingswood, Cornucopia, and DeepHarbor. They are skipped in Camelot and Somewhere. Only normal combat rooms (Default, Wave, Horde, Onslaught) can be replaced by random chance. Hardset rooms always trigger regardless of objective type.

### Health Multipliers

| Setting | Default | Description |
|---------|---------|-------------|
| `BossHealthMultiplier` | `2.0` | Health multiplier for bosses like Gawain, Arthur (1.0 = no change) |
| `BeastHealthMultiplier` | `2.0` | Health multiplier for legendary beasts like Dagonet (1.0 = no change) |

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
NoCurrencyDoorRewards = true
DuoChance = 0.35
EnableBiomeRepeat = true
RepeatBiome = Kingswood
RepeatAfterBiome = Cornucopia
BeastChancePercent = 0
BeastRoom1 = 4
BeastRoom2 = 8
BossHealthMultiplier = 2
BeastHealthMultiplier = 2
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
