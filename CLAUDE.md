# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SwornTweaks** is an all-in-one mod for SWORN (Windwalk Games / Team17) using MelonLoader, with a companion PyQt6 configurator GUI. It consolidates multiple individual mods (rerolls, rarity, gem cost, door rewards, duo boost, biome repeat, beast rooms, health multipliers) into a single DLL.

**Version:** 1.8.2

## Files Structure

```
SwornTweaks/
├── .github/
│   ├── ISSUE_TEMPLATE/          # Bug report + feature request forms
│   └── workflows/
│       └── build-exe.yml        # PyInstaller builds (Win/Linux)
├── Patches/                     # 16 Harmony patch files (C#)
│   ├── BossRushPatch.cs         # Boss rush mode (785 lines)
│   ├── SaveStatePatch.cs        # Multiplayer save/resume (743 lines)
│   ├── HealthBoostPatch.cs      # Boss/beast/enemy HP/DMG scaling
│   ├── BeastRoomPatch.cs        # Extra beast encounters
│   ├── FaeRealmPatch.cs         # Guaranteed fae portals
│   ├── PlayerHealthPatch.cs     # Player HP/DMG multipliers + invincibility
│   ├── BiomeRepeatPatch.cs      # Extra biomes cycling
│   ├── SkipSomewherePatch.cs    # Skip Somewhere level
│   ├── SafeParagonPatch.cs      # Paragon reward safety
│   ├── RerollPatch.cs           # Reroll mechanics
│   ├── DoorRewardPatch.cs       # Currency door replacement
│   ├── GoldPatch.cs             # Unlimited gold
│   ├── RarityPatch.cs           # Blessing rarity override
│   ├── GemCostPatch.cs          # Gem cost bypass
│   ├── DuoBoostPatch.cs         # Duo blessing mechanics
│   └── IntensityPatch.cs        # Room intensity multiplier
├── docs/
│   ├── MODDING_CONTEXT.md       # Game modding reference (56KB)
│   └── Modinstall.md            # Installation guide
├── screenshots/
│   └── configurator.png
├── Core.cs                      # MelonMod entry point
├── Config.cs                    # 37 MelonPreferences entries
├── configurator.py              # PyQt6 configurator GUI (1402 lines)
├── SwornTweaks.csproj           # .NET 6.0 project
├── SwornTweaks.dll              # Compiled mod binary
├── README.md
├── INSTALL.md
├── requirements.txt             # PyQt6>=6.5
└── .gitignore
```

## Build and Run Commands

```bash
# Build C# DLL (requires .NET 6.0 SDK + game references)
dotnet build -c Release

# Run configurator
pip install -r requirements.txt
python configurator.py

# Build configurator executable
pip install pyinstaller certifi
pyinstaller --onefile --windowed --name SwornTweaks configurator.py
```

## Architecture Overview

### Dual-Component Design

1. **C# DLL (SwornTweaks.dll)** — MelonLoader mod loaded into SWORN at runtime
   - `Core.cs`: MelonMod entry, initializes config, handles scene loading
   - `Config.cs`: 37 settings via MelonPreferences API
   - `Patches/*.cs`: Harmony patches intercepting game methods

2. **Python Configurator (configurator.py)** — Standalone GUI for editing settings
   - Reads/writes `MelonPreferences.cfg` (INI format)
   - Tabbed interface: Player, Enemies, Toggles, Game Modes, Settings, Help
   - Auto-detects SWORN installation path
   - Self-update from GitHub releases
   - Downloads latest SwornTweaks.dll into Mods folder

### Key Patterns

**Harmony Patching:**
```csharp
[HarmonyPatch(typeof(TargetClass), "TargetMethod")]
class MyPatch {
    static void Prefix(...) { }  // Before original
    static void Postfix(...) { } // After original
}
```

**Config Access:**
```csharp
SwornTweaksConfig.BonusRerolls.Value  // int
SwornTweaksConfig.InfiniteRerolls.Value  // bool
```

## Configuration

**Config Path:** `{SWORN}/UserData/MelonPreferences.cfg` (section `[SwornTweaks]`)

**Configurator Config:**
- Windows: `%APPDATA%\SwornTweaks\configurator.json`
- Linux: `~/.config/SwornTweaks/configurator.json`

**37 Settings** organized into categories:
- Rerolls, Rarity, Gem Cost, Gold, Door Rewards
- Duo/Round Table, Biome Repeat, Beast Rooms
- Player Scaling (HP/DMG/Mana/Invincible)
- Enemy Scaling (Boss/Beast/Enemy HP/DMG)
- Intensity, Fae Realms, Sword in the Stone
- Boss Rush Mode, Fight Specific Boss
- Multiplayer Save/Resume

## Dependencies

### C# Mod
- .NET 6.0 (x64)
- MelonLoader 0.7.1+
- 0Harmony (patching framework)
- Il2CppInterop.Runtime
- Assembly-CSharp.dll (game stubs)

### Python Configurator
- PyQt6 >= 6.5
- certifi (for PyInstaller SSL bundles)

### Game
- SWORN (Steam App ID: 1763250)
- MelonLoader installed
- .NET 6 Desktop Runtime

## Update System

**Configurator self-update:**
- Checks GitHub releases API for latest version
- Downloads new executable, replaces self, restarts
- SSL certificates bundled via certifi for PyInstaller builds

**DLL download:**
- Configurator can download latest SwornTweaks.dll from GitHub releases
- Places it directly in SWORN's Mods folder

**GitHub Integration:**
- Repository: `jj-repository/SwornTweaks`

## Testing

No automated test suite. Testing is manual:
- Install mod in game, verify each setting works
- Test configurator on Windows and Linux

## Security Features

- SSL certificate bundling for PyInstaller builds
- Platform-specific config paths (no hardcoded paths)
- Downloads from GitHub releases only

## Known Issues / Technical Debt

1. No automated tests for C# patches or configurator
2. SwornTweaks.dll binary checked into repo (needed for configurator download feature)
3. configurator.py is a single 1402-line file

---

## Review Status

> **Last Full Review:** 2026-03-18
> **Status:** Production Ready

### Code Quality
- [x] All 16 Harmony patches functional
- [x] Configurator handles missing config gracefully
- [x] Auto-update with error handling
- [x] SSL certificates bundled for PyInstaller
- [x] Platform-specific path detection

## Quality Standards

| Aspect | Standard | Status |
|--------|----------|--------|
| Game Mod | All 37 settings work in-game | Met |
| Configurator | Reads/writes config correctly | Met |
| Update System | Self-update + DLL download | Met |
| Cross-platform | Windows + Linux (Proton) | Met |

## Intentional Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single DLL consolidating multiple mods | Easier for users to install one mod instead of 7 |
| Python configurator (not C#) | PyQt6 is faster to develop; configurator doesn't need game references |
| INI config format | MelonPreferences uses INI; configurator reads it directly |
| DLL checked into repo | Configurator needs to download it; GitHub release assets are the source |

## Won't Fix (Accepted Limitations)

| Issue | Reason |
|-------|--------|
| No automated tests | Game mod testing requires the actual game running |
| Large configurator.py | Single file is simpler for PyInstaller bundling |
| DLL in repo | Needed for download feature; small file (52KB) |

## Completed Optimizations

- Consolidated 7 individual mods into one
- Progressive HP scaling with biome-aware normalization
- Boss Rush mode with structured sequences
- Multiplayer save/resume with JSON persistence
- Auto-update for both configurator and DLL

**DO NOT further optimize:** The mod patches game methods directly; there's no performance bottleneck. The configurator GUI is responsive.
