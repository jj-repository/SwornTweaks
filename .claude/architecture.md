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
SwornTweaksConfig.BonusRerolls.Value      // int
SwornTweaksConfig.InfiniteRerolls.Value   // bool
```

## 16 Patch Files (multiple patch classes per file)
BossRushPatch (8 inner classes incl. DragonEndGameRedirect), SaveStatePatch (5 inner classes), HealthBoostPatch, BeastRoomPatch, FaeRealmPatch, PlayerHealthPatch, BiomeRepeatPatch, SkipSomewherePatch, SafeParagonPatch, RerollPatch, DoorRewardPatch, GoldPatch, RarityPatch, GemCostPatch, DuoBoostPatch, IntensityPatch
