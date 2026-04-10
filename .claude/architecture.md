# Architecture

## Dual-Component Design

**C# DLL** — loaded by MelonLoader into SWORN at runtime
- `Core.cs`: MelonMod entry, initializes config, scene loading
- `Config.cs`: 37 settings via MelonPreferences API
- `Patches/*.cs`: 16 Harmony patches intercepting game methods

**Python Configurator** — standalone settings GUI
- Reads/writes `MelonPreferences.cfg` (INI format)
- Tabs: Player, Enemies, Toggles, Game Modes, Settings, Help
- Auto-detects SWORN installation path
- Self-update + downloads latest DLL to Mods folder

## Harmony Patching
```csharp
[HarmonyPatch(typeof(TargetClass), "TargetMethod")]
class MyPatch {
    static void Prefix(...) { }   // before original
    static void Postfix(...) { }  // after original
}
```

## Config Access
```csharp
Config.BonusRerolls.Value      // int
Config.InfiniteRerolls.Value   // bool
```

## 16 Patch Files (multiple patch classes per file)
BossRushPatch (8 inner classes incl. DragonEndGameRedirect), SaveStatePatch (7 inner classes), HealthBoostPatch, BeastRoomPatch, FaeRealmPatch, PlayerHealthPatch, BiomeRepeatPatch, SkipSomewherePatch, SafeParagonPatch, RerollPatch, DoorRewardPatch, GoldPatch, RarityPatch, GemCostPatch, DuoBoostPatch, IntensityPatch

## SaveStatePatch Architecture (v1.12 redesign)

### Key insight
SWORN generates paths **incrementally** (1-2 rooms at a time via `PathGenerator.GeneratePaths`), NOT as a full biome array. The old path-trimming approach never worked because the "full biome path" never exists.

### GeneratePaths method
Signature: `PathGenerator.GeneratePaths(ExpeditionManager, int, int, BiomeData, PathGenerator.BiomeRunData, BiomeData.Room, int, PathGenerationFlags)` — 8 params. Harmony patches capture named params: `expeditionManager`, `biome`, `biomeRunData`, `nextRoomIndex`.

### Save flow
1. `SaveStateHealthSnapshot` (ConsumePath Prefix, High priority) — snapshots health BEFORE between-room heal
2. `SaveStateRoomCounter` (ConsumePath Prefix, High priority) — increments BiomeRoomsCompleted
3. ConsumePath body runs (game heals player, transitions room)
4. `SaveStateSave.DoSave` (ConsumePath Postfix) — writes JSON with expedition state, player data, path history
5. `SaveStatePathRecorder` (GeneratePaths Postfix, very low priority) — records path data AFTER all other patches modify it, updates save file

### Load flow
1. `SaveStateLoad` Prefix (ResetBiomeRunData) — reads save, sets ReplayActive, builds LevelData lookup
2. `SaveStateBiomeOverride` Prefix (GeneratePaths, High priority) — overrides `ref int nextRoomIndex` to target room, sets expedition indices RIGHT BEFORE path generation. Only during init call (IsInResetBiomeRunData). Gameplay calls pass through and consume replay.
3. `SaveStatePathReplay` Postfix (GeneratePaths, low priority) — replaces generated path entries with saved data (roomType, levelData by name lookup, rewardType, postLevelEvents)
4. `SaveStateLoad` Postfix (ResetBiomeRunData) — sets expedition indices, starts DelayedPlayerRestore coroutine
5. `DelayedPlayerRestore` — waits for player spawn, restores gold/health/blessings
6. `DeferredHealthRestore` — waits for mobs (room loaded), re-applies health if game reset it

### Priority chain for GeneratePaths patches
Prefix: SaveStateBiomeOverride (600/High) → other patches
Postfix: BeastRoomPatch (400) → DoorRewardPatch (400) → FaeRealmPatch (400) → BossRushRoomOverride (200/Low) → SaveStatePathReplay (190) → SaveStatePathRecorder (180)

### Save file
`{SWORN}/UserData/SwornTweaks_SaveState.json` — version 2 format with expedition data, per-player state, and room path history.

### BossRush exclusion
Save/load is disabled when BossRush mode is active (queue-based encounter system needs warmup calls we can't make yet — GeneratePaths has 8 params).
