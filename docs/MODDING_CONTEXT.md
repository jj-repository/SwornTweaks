# Sworn Modding Context

Complete reference for modding Sworn with MelonLoader. Covers game architecture, code structure, and mod hook points.

---

## Setup & Environment

### Paths
- **Game install**: `/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/`
- **Steam App ID**: 1763250
- **IL2CPP stubs**: `.../SWORN/MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll` (181 assemblies total)
- **Mod folder**: `.../SWORN/Mods/` (enabled), `.../SWORN/Mods_Disabled/` (disabled)
- **Modding workspace**: `/home/ungj/SwornTweaks/`

### Existing Mods

**Active:**
- `SwornTweaks.dll` — unified all-in-one mod (configurable via MelonPreferences). Source: `SwornTweaks/`. Combines:
  - Rerolls (+500 base), blessing rarity boosts, gem cost skip, currency door reward replacement, duo boost (35%)
  - Biome repeat (Kingswood after Cornucopia by default), random beast rooms (15% chance) + hardset beast room indices
  - Boss/beast health multipliers (3x boss, 2x beast by default)
  - Includes `configurator.py` — PyQt6 GUI for editing all settings visually
  - Patches: `RerollManager.OnRunStarted`, `BlessingGenerator.GenerateBlessings`, `BlessingGenerator.GetOddsForClassification`, `CurrencyManager.AddGold/GetGold`, `PathGenerator.GeneratePaths`, `PathGenerator.SelectObjectiveType`, `ExpeditionManager.ResetBiomeRunData`, `Mob.SetMobDifficultyScaling`

**Superseded by SwornTweaks (old source folders deleted, DLLs in `Mods_Disabled/`):**
- `SwornMoreRooms.dll`, `SwornDuoBoost.dll`, `SwornRarityMod.dll`, `SwornNoGemCost.dll`, `SwornNoCurrencyDoorRewards.dll`, `SwornRerollMod.dll`, `SwornBossHealthBoost.dll`

### Running with Proton (Linux)
```
WINEDLLOVERRIDES="version=n,b" %command%
```
MelonLoader intercepts via the Windows `version.dll` hook.

### Build Process
1. Create project folder under `/home/ungj/SwornTweaks/<ModName>/`
2. Write `Core.cs` + `<ModName>.csproj` using template below
3. `cd <ModName> && dotnet build -c Release`
4. Copy `bin/Release/net6.0/<ModName>.dll` to both the project folder and game `Mods/` folder (keep a copy in each)

### .csproj Template
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Library</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <Nullable>enable</Nullable>
    <Platforms>x64</Platforms>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>
  <ItemGroup>
    <!-- MelonLoader + Harmony -->
    <Reference Include="MelonLoader">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/net6/MelonLoader.dll</HintPath>
    </Reference>
    <Reference Include="0Harmony">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/net6/0Harmony.dll</HintPath>
    </Reference>
    <Reference Include="Il2CppInterop.Runtime">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/net6/Il2CppInterop.Runtime.dll</HintPath>
    </Reference>
    <!-- IL2CPP game stubs -->
    <Reference Include="Assembly-CSharp">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll</HintPath>
    </Reference>
    <Reference Include="Il2Cppmscorlib">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/Il2CppAssemblies/Il2Cppmscorlib.dll</HintPath>
    </Reference>
    <Reference Include="UnityEngine.CoreModule">
      <HintPath>/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/MelonLoader/Il2CppAssemblies/UnityEngine.CoreModule.dll</HintPath>
    </Reference>
    <!-- Add Il2CppWindwalk.Core.dll if referencing EntityBase/CurrencyManager etc. -->
  </ItemGroup>
</Project>
```

---

## MelonLoader & IL2CPP Concepts

### What MelonLoader Does
- Hooks into Unity at startup, loads mods from `/Mods/`
- For IL2CPP games: generates C# stub DLLs from the IL2CPP metadata so you can reference game types
- Provides **Harmony** for method patching (prefix/postfix/transpiler)
- Provides **Il2CppInterop** for type bridging between managed C# and IL2CPP native code

### IL2CPP vs Mono
- **Mono**: C# runs as bytecode (IL), easy to patch, ILSpy shows full source
- **IL2CPP** (Sworn uses this): C# compiled to C++ then native binary. Stubs exist for type info but actual method bodies are native — you can't transpile, only prefix/postfix patch.

### Harmony Patching Pattern
```csharp
using HarmonyLib;
using MelonLoader;

[assembly: MelonInfo(typeof(MyMod.Core), "MyMod", "1.0.0", "Author")]
[assembly: MelonGame("Developer", "SWORN")]

namespace MyMod {
    public class Core : MelonMod {
        public override void OnInitializeMelon() {
            HarmonyInstance.PatchAll();
        }
    }

    [HarmonyPatch(typeof(TargetClass), nameof(TargetClass.TargetMethod))]
    public static class MyPatch {
        // Return false to skip original, return true to run original
        static bool Prefix(TargetClass __instance, ref int roomIndex) {
            roomIndex = roomIndex / 3; // modify arg before original runs
            return true;
        }
        // __result holds return value (postfix only)
        static void Postfix(ref float __result) {
            __result *= 2f;
        }
    }
}
```

### IL2CPP Type Gotchas
- Unity types like `AnimationCurve`, `ScriptableObject` need `Il2CppInterop` wrappers
- Static fields on IL2CPP types: access via `Il2CppType.Field` or just use the static directly if stubbed
- Nested types: e.g. `PathGenerator.BiomeRunData`, `PathGenerator.BiomePathGenerationParameters`

### Code Inspection (Linux, .NET 10)
- **ilspycmd** does NOT work with .NET 10 (requires .NET 8) — use Mono.Cecil instead
- Custom inspector at `/tmp/sworn-inspect/` (Mono.Cecil, .NET 10 console app)
- Run: `cd /tmp/sworn-inspect && dotnet run`

---

## Game Architecture Overview

Sworn is a co-op roguelike with a fixed biome structure. Each run progresses through **4 biomes** (Kingswood → Cornucopia → DeepHarbor → Camelot), each biome being a sequence of rooms. Room content is determined by `PathGenerator` using `RoomGroup` arrays indexed by room position within the biome.

### Key Systems
1. **ExpeditionManager** — run-level state machine (which biome, which room)
2. **PathGenerator** (ScriptableObject) — generates the room sequence for a biome
3. **BiomeData** (ScriptableObject) — per-biome config: intensity curve, room pools, events
4. **DifficultyManager** — 6 difficulty levels affecting enemy health/damage/corruptions
5. **BlessingManager** — upgrade/blessing system
6. **RerollManager** — reroll currency
7. **MetaCurrencyManager** — currencies (gold, gems, etc.)
8. **PostLevelEventsInfoList** — post-level event registry (Black Knight, Architect, etc.)
9. **RoundTableLevelManager** — Roundtable knight boss fights
10. **MajorEnemyCombatRunner** — legendary beast boss fights (async combat runner)
11. **ArthurLevelManager / MorganaLevelManager / DragonLevelManager** — final bosses (call `EndGame()`)

### Room Flow
```
ExpeditionManager.ConsumePath()
  → advances BiomeRoomIndex (room within biome) and RoomIndex (global)
  → checks if biome complete → advances BiomeIndex
  → calls GeneratePaths() for next biome if needed

PathGenerator.GeneratePaths(BiomeData, BiomeRunData, PathGenerationFlags)
  → for each room slot: SelectRoomGroup() → picks RoomGroup
  → for each room slot: SelectIntensity() → picks intensity float
  → CheckForBlackKnight() → sets biomeRunData.blackKnightIndex
  → returns List<Room> (the path)
```

---

## Enums

### BiomeType
```
None = 0
Kingswood = 1
Cornucopia = 2
DeepHarbor = 3
Camelot = 4
Somewhere = 5
```

### DifficultyLevel
```
Squire = 0, Knight = 1, Baron = 2, Duke = 3, Sovereign = 4
```
DifficultyManager has 6 slots (difficulty0–difficulty5) but only 5 named levels are known. Slot 5 may be unused or a hidden/future level.

### RoomType
```
None = -1
Default = 0
Combat = 1
MiniBoss = 2
Boss = 3
Shop = 4
Event = 5
Rest = 6
BlockedPath = 7
Lobby = 8
Roundtable = 9
Arthur = 10
Portal = 11
ScriptedRoom = 12
Morgana = 13
Bridge = 14
```

### ObjectiveType (complete)
```
None = -1, Default = 0, Wave = 1, Horde = 2, MajorEnemy = 3,
Onslaught = 4, MerlinShrines = 5, SetPiece = 6, SpawnCrystals = 7,
ObstacleCourse = 8, LunaBlossom = 9, CapturePoints = 10, TileMatching = 11,
QuizMaster = 12, Totems = 13, Arena = 14, TutorialWave = 15,
Roundtable = 16, Kiss = 17, KissCurse = 18,
AreaCaptureSequential = 19, AreaCaptureAnyOrder = 20,
DestroyTargetsSequential = 21, DestroyTargetsAnyOrder = 22, ScriptedRoom = 23
```

### PostLevelEventType (complete)
```
None = 0, Trove = 1, GoldShop = 2, MidasShrine = 3,
VampireShrine = 5, MushroomShrine = 6, EtherealShrine = 7,
MabShrine = 8, BabdShrine = 9, BeiraShrine = 10, ClionaShrine = 11,
GogmagogShrine = 12, LughShrine = 13, OberonShrine = 14, TitaniaShrine = 15,
KissPortal = 16, KissCursePortal = 17, SeedSpot = 18,
MetaCurrencyTrove = 19, BlackKnightCombat = 20, CorruptionShrine = 21
```

### ParagonType
```
None = 0, Courage = 1, Flame = 2, Frost = 3, Venom = 4,
Shadow = 5, Wind = 6, Death = 7, Crit = 8,
LevelUp = 11, SwordInTheStone = 12
```

### BlessingRarity
```
Common = 0, Uncommon = 1, Rare = 2, Epic = 3, Legendary = 4, DUO = 5, RoundTable = 6
```

### BlessingType (flags/bitfield)
```
None = 0, Paragon = 1, Character = 2, Weapon = 4, Health = 8,
Gold = 16, BlessingLevel = 32, GrailWater = 64, FairyEmber = 128,
CrystalShard = 256, Event = 512, Kiss = 1024, KissCurse = 2048,
Obsidian = 4096, Ability = 6
```

### RewardType (complete)
```
None = 0, Paragon = 1, ParagonLevelUp = 2, Gold = 3, Health = 4,
CrystalShard = 5, FairyEmber = 6, GrailWater = 7, Obsidian = 8,
OLD_WeaponBlessing = 9, MetaCurrency = 10, Healing = 11,
SingleBlessing = 12, SwordInTheStone = 13, Emerald = 14, Silk = 15,
Moonstone = 16, TestPortalReward = 17, Kiss = 18, KissCurse = 19,
WarStone = 23, TreasureStone = 24, WealthStone = 25, DevotionStone = 26,
TitaniaBlessing = 28, EndingKeyCombat = 30, EndingKeyGold = 31,
EndingKeyHealth = 32, HealthCost = 98, CurseCost = 99
```

### MetaCurrencyType (complete)
```
None = -1, CrystalShard = 0, FairyEmber = 1, GrailWater = 2,
Ink = 3, Emerald = 4, Silk = 5, Moonstone = 6, Scryingstone = 7,
WarStone = 8, TreasureStone = 9, WealthStone = 10,
DevotionStone = 11, Obsidian = 12
```

### EventBlessingType
```
None = 0, VampireShrine = 2, MysteriousMushroom = 3, EtherealShrine = 4,
MabShrine = 5, PostShop = 6, BabdShrine = 7, BeiraShrine = 8,
ClionaShrine = 9, GogmagogShrine = 10, LughShrine = 11,
OberonShrine = 12, TitaniaShrine = 13
```

### LevelState
```
7 states (e.g. Loading, Running, Complete, etc.)
```

### TrueEndingKeys (flags)
```
CombatKey = 1, GoldKey = 2, HealthKey = 4
```

### RoomGroup (partial — many values)
Used by PathGenerator to categorize rooms into pools. Each biome has a series of RoomGroupRange entries that say "rooms 0–4 pick from group X, rooms 5–9 pick from group Y," etc.

---

## Key Classes & Fields

### ExpeditionManager
```csharp
// Run-level state
int BiomeIndex          // which biome (0–3)
int BiomeRoomIndex      // room within current biome
int RoomIndex           // global room index across whole run
List<BiomeData> SerializedBiomes   // the 4 biomes in order
List<Room> nextPaths    // upcoming rooms (generated ahead)

// Methods
void GeneratePaths(BiomeData biome, BiomeRunData runData, PathGenerationFlags flags)
void ConsumePath()      // advance to next room
void ResetBiomeRunData()
```

### PathGenerator (ScriptableObject)
```csharp
// Config (set per-biome in Unity editor)
BiomePathGenerationParameters[] pathGenerationParameters

// Runtime
List<Room> GeneratePaths(BiomeData biome, BiomeRunData runData, PathGenerationFlags flags)
RoomGroup SelectRoomGroup(int roomIndex, BiomeRunData runData, ...)
float SelectIntensity(int roomIndex, BiomeData biome, ...)
void CheckForBlackKnight(int totalRooms, BiomeRunData runData, ...)
```

### PathGenerator.BiomePathGenerationParameters (nested type)
```csharp
int minBlackKnightIndex         // earliest room Black Knight can appear
int maxBlackKnightIndex         // latest room Black Knight can appear
RoomGroup fillerRoomGroup       // fallback group when no range matches
RoomGroupRange[] roomGroups     // array of (startIndex, endIndex, group) ranges
```

### PathGenerator.BiomeRunData (nested type)
```csharp
// Constructed per biome-visit
BiomeRunData(BiomeData biome, int seed)
void Init(int seed)

// State
int blackKnightIndex            // which room Black Knight appears as post-level event
List<int> usedLevels            // which level assets have been used (dedup)
List<int> usedEvents            // which events have fired
Dictionary<EventType, int> remainingEventCounts
RoomGroup[] roomGroups          // resolved groups for this run
```

### PathGenerationFlags (struct)
```csharp
bool isTutorialRun
bool hasEncounteredArchitect
bool canEncounterArchitect
bool hasEncounteredFisherKing
bool canEncounterFisherKing
bool canEncounterLancelot
```

### BiomeData (ScriptableObject)
```csharp
AnimationCurve intensityCurve   // maps room index (0..N) → intensity float
PathGenerator pathGenerator
BiomePathGenerationParameters pathGenerationParameters  // (may be on PathGenerator)

// Combat data arrays
MajorEnemyCombatData[] majorEnemyCombatData
// ... other combat pool arrays

float GetRoomIntensity(int roomIndex)   // evaluates intensityCurve at roomIndex

// Nested type: PostLevelEventPool
class PostLevelEventPool {
    PostLevelEventType[] events
    int max
    int startRun
    int startRoom
}

// Nested type: Room
class Room {
    RoomType roomTypeOverride
    ObjectiveType objectiveTypeOverride
    bool hasRewardTypeOverride
    RewardType rewardTypeOverride
    LevelPool levelPoolOverride
}
```

### BiomeData.MajorEnemyCombatData
```csharp
float majorEnemySelectionCoefficient
float probability
float totalMinorEnemyIntensityCoefficient
float waveEnemiesCoefficient
```

### DifficultyManager
```csharp
void SetDifficultyLevel(DifficultyLevel level)
DifficultySettings GetDifficultySettings()
// 6 difficulty slots (0–5)
```

### DifficultySettings
```csharp
float EnemyHealth
float EnemyDamage
int Corruptions
int BossCorruptions
float MetaCurrencyMultiplier
```

### RoundTableLevelManager
```csharp
int currentRound
int startingRoundsCompleted
CombatData[] combatData         // knight fight data pool
// Each round: selects a knight pair, tracks usedLevels within session
// No cross-run persistence — fully repeatable
```

### RoundtableSerializedData
```csharp
int numberOfRounds
float intensityCoefficient
float additionalIntensityPerWave
KnightPair[] knightPairs
RewardPair[] rewardPairs
```

### MajorEnemyCombatRunner
```csharp
// Async runner: UniTask-based, uses CancellationToken
// Handles legendary beast fights (Dagonet etc.)
// NO persistent state — fully repeatable without patches
// Phases (e.g. Dagonet): ChaseAndSlash, Barrels, Lasso, WildSpin
```

### ArthurLevelManager / MorganaLevelManager / DragonLevelManager
```csharp
// All call EndGame() on completion → ends the run
// To make repeatable: intercept EndGame() or the completion callback
```

### MiniBossLevelManager
```csharp
// Completely empty class — inherits LevelManager with no overrides
```

### RerollManager
```csharp
static int Rerolls           // current reroll count
static void AddRerolls(int amount)
static void SetRerolls(int amount)
```

### BlessingManager
```csharp
// extends EntityBase (networked — all changes sync via RPC)
BlessingGeneratedTable blessingTable          // lookup table: all Blessing ScriptableObjects
BlessingCategoryGeneratedTable blessingCategoryTable  // all BlessingCategory ScriptableObjects
int runsRequiredForCompanions                 // run count gate for companion blessings
int runsRequiredForUltimates                  // run count gate for ultimate blessings
Dictionary<Type, Blessing> blessings          // master blessing registry
Dictionary<PlayerId, HashSet<Type>> playerBlessings     // per-player owned blessings
Dictionary<(PlayerId,Type), int> playerBlessingLevel    // per-player blessing levels
Dictionary<(PlayerId,Type), BlessingRarity> playerBlessingRarity  // per-player blessing rarities
Dictionary<(PlayerId,Type), float> playerBlessingIntegrity
Dictionary<(PlayerId,Type), int> playerBlessingDuration
PlayerId playerEligibleForRoundTableBlessing

// Events (Action<PlayerId, Blessing, int?, BlessingRarity?>)
Action BlessingAdded, BlessingRemoved, BlessingIntegrityChanged, BlessingDurationChanged

// Key methods
bool AddOrOverrideBlessing<T>(PlayerId, level?, rarity?)  // add or upgrade
bool AddBlessing<T>(PlayerId, level?, rarity?)             // add only if not present
bool RemoveBlessing<T>(PlayerId)
bool HasBlessing<T>(PlayerId)
int GetBlessingLevel<T>(PlayerId)
BlessingRarity GetBlessingRarity<T>(PlayerId)
float GetBlessingIntegrity<T>(PlayerId)
int GetBlessingDuration<T>(PlayerId)
Blessing GetBlessing<T>()
IEnumerable<Blessing> GetBlessings(PlayerId)
BlessingCategory GetBlessingCategoryForType(BlessingType)
int GetRoundTableBlessingRequirement()        // how many blessings needed to unlock RT
bool AnyPlayerHasARoundtable()
bool AnyPlayerHasBlessing<T>()

// RPC sync methods (called internally)
void SyncAddBlessing(PlayerId, string typeName, int? level, BlessingRarity? rarity, RpcInfo)
void SyncRemoveBlessing(PlayerId, string typeName, RpcInfo)
void SyncAddOrOverrideBlessing(...)
void SyncRemoveAllBlessings(RpcInfo)
```

### CurrencyManager (networked entity)
```csharp
// In-run gold system (NOT meta currencies)
Dictionary<PlayerId, int> playerGoldCount    // per-player gold
Dictionary<PlayerId, int> playerGoldSpent    // per-player gold spent
Action<PlayerId, int, int> GoldCountChanged  // (playerId, prevAmount, newAmount)

void AddGold(PlayerId playerId, int amount)  // positive to add, negative to subtract
int GetGold(PlayerId playerId)               // current gold
int GetGoldSpent(PlayerId playerId)
void ClearAll()
// Synced via RPC (SyncAddGold, SyncClearAll)
```
Gem slot purchase flow: game checks `GetGold() >= 300` → calls `AddGold(playerId, -300)`.

### PostLevelShopUI
```csharp
// Post-level blessing shop (appears after rooms)
Boolean TryPurchase(int index)    // validates gold + purchases item
int GetGoldCost(int originalCost) // applies cost modifiers
void OnReroll()                   // rerolls shop offerings
// Key props: currencyManager, blessingManager, shopItems, buttons
```

### PostLevelEventsInfoList
```csharp
// Static singleton
// Provides accessor for each PostLevelEventType
// Used by PathGenerator/ExpeditionManager to schedule post-level events
```

---

## Intensity System

### How Intensity Works
- `BiomeData.intensityCurve`: an `AnimationCurve` asset that maps `roomIndex` (0 to N) → a float intensity value
- `GetRoomIntensity(int roomIndex)` evaluates this curve
- Intensity is a **budget**: enemy spawners use it to pick how many/what type of enemies to spawn
- There are spawn caps per room so extremely high intensity just hits the cap (safe to multiply)
- The curve is defined in the Unity editor per biome — you can't edit it at runtime without mods, but you CAN postfix `GetRoomIntensity` to multiply the return value

### Intensity Scaling
- Current curve: roughly linear, max ~1.0 at end of biome
- Modding: postfix `GetRoomIntensity` to return `result * multiplier` → more enemies per room
- Safe approach: cap at 3–4x, hits spawn cap above that

### Boss Intensity
- `DifficultySettings.BossCorruptions`: extra corruptions added to boss fights at higher difficulty
- `RoundtableSerializedData.intensityCoefficient` + `additionalIntensityPerWave`: scales Roundtable knight intensity per round

---

## Room Structure & More Rooms Strategy

### Current Biome Layout (approximate)
Each biome has ~10 rooms following this pattern:
```
[combat] [combat] [combat] [MajorEnemy/beast] [combat] [combat] [combat] [combat] [Roundtable/knight] [Boss/Arthur|Morgana]
```
Plus Black Knight appears as a post-level event at `blackKnightIndex` (typically room 3–6 range within biome, configured via `minBlackKnightIndex`/`maxBlackKnightIndex`).

### How PathGenerator Selects Rooms
`SelectRoomGroup(roomIndex, ...)` looks up `roomGroups` array: each entry has `(startIndex, endIndex, RoomGroup)`. If `roomIndex` falls in range, that group is used. The group then has a pool of room assets to pick from.

### Strategy: Room Count Multiplier
Patch `SelectRoomGroup` and `CheckForBlackKnight` with a Harmony **prefix** that divides `roomIndex` by a multiplier before the original method sees it:

```csharp
[HarmonyPatch(typeof(PathGenerator), "SelectRoomGroup")]
static class PatchSelectRoomGroup {
    static void Prefix(ref int roomIndex) {
        roomIndex = roomIndex / MULTIPLIER;
    }
}

[HarmonyPatch(typeof(PathGenerator), "CheckForBlackKnight")]
static class PatchCheckForBlackKnight {
    static void Prefix(ref int totalRooms, ref int roomIndex) {
        roomIndex = roomIndex / MULTIPLIER;
        // Optionally scale totalRooms too
    }
}
```

This makes the existing room group ranges cover `MULTIPLIER` times as many rooms. A multiplier of 3 gives ~30 rooms per biome instead of ~10, with the same room type progression just stretched out.

**Black Knight scaling**: `minBlackKnightIndex` and `maxBlackKnightIndex` in `BiomePathGenerationParameters` should be scaled proportionally, otherwise the Knight will appear in the first few rooms. Options:
- Patch `BiomePathGenerationParameters` fields after load (postfix constructor or `Init`)
- Or patch `CheckForBlackKnight` to also multiply the thresholds: `if (roomIndex >= min * MULTIPLIER && roomIndex <= max * MULTIPLIER)`

### Strategy: Loop-Back After Biome 3
To extend the run past the 4th biome:
1. Intercept `BiomeIndex` increment in `ExpeditionManager`
2. When it would advance past index 3, reset to index 2 (DeepHarbor) or 0 (Kingswood)
3. Re-init `BiomeRunData` with a new seed
4. Keep intensity values from where they left off (manual offset or multiply `GetRoomIntensity` argument)

---

## Boss Repeatability

### Legendary Beasts (MajorEnemyCombatRunner)
- **Fully repeatable with zero patches**
- No persistent state between runs or within a run
- Each MajorEnemy room spawns a fresh `MajorEnemyCombatRunner` via UniTask
- Safe to appear multiple times per biome

### Roundtable Knights (RoundTableLevelManager)
- **Repeatable**, but tracks `usedLevels` to avoid repeating the same knight pair within a session
- To force repeat: patch `RoundTableLevelManager` to clear `usedLevels` before each fight, or ignore dedup
- No cross-run persistence

### Arthur / Morgana / Dragon (Final Bosses)
- Call `EndGame()` on completion → **ends the run**
- To make repeatable: patch the completion handler or intercept `EndGame()`
- Could redirect to a "victory room" instead of ending, then allow continuation

### Black Knight (PostLevelEventType.BlackKnightCombat)
- Appears as a **post-level event** (not a room type) at the room indexed by `biomeRunData.blackKnightIndex`
- Triggered by `PostLevelEventsInfoList` after the room at that index completes
- To repeat: patch `CheckForBlackKnight` to set `blackKnightIndex` to a recurring value, or manually re-trigger the event

---

## Difficulty Modding

### DifficultySettings Fields
All float/int multipliers applied game-wide:
```
EnemyHealth            — HP multiplier for enemies
EnemyDamage            — damage multiplier for enemies
Corruptions            — number of corruptions in standard rooms
BossCorruptions        — number of corruptions in boss rooms
MetaCurrencyMultiplier — currency gain multiplier
```

### Patching Difficulty
Postfix `DifficultyManager.GetDifficultySettings()` to multiply fields:
```csharp
static void Postfix(ref DifficultySettings __result) {
    __result.EnemyHealth *= 2f;
    __result.EnemyDamage *= 1.5f;
}
```

---

## Blessing Generation System (RNG)

The blessing offering/RNG system is handled by `BlessingGenerator` (ScriptableObject, set in Unity editor). This is the core class that determines what blessings appear when you pick a paragon after a room.

### BlessingGenerator
```csharp
// === Rarity base chances (float, set in Unity editor) ===
float uncommonBlessingBaseChance    // base % to roll Uncommon instead of Common
float rareBlessingBaseChance        // base % to roll Rare
float epicBlessingBaseChance        // base % to roll Epic
float legendaryBlessingBaseChance   // base % to roll Legendary
// Rarity roll: for each blessing, roll against these thresholds (highest first).
// If none hit, result is Common. The `rarityIncrease` parameter shifts rolls up.

// === Generation pipeline ===
// Two phases: Roll (pick classification slots) then Fill (fill remaining slots)
// Different step arrays depending on whether the player already has blessings:
RollStep[] blessingGenerationRollStepsWithNoBlessings
FillStep[] blessingGenerationFillStepsWithNoBlessings
RollStep[] blessingGenerationRollStepsWithBlessings
FillStep[] blessingGenerationFillStepsWithBlessings

// === Classification odds (flat chances) ===
float chanceOfPrioritizingCoreSlotBlessing      // % for "core slot" (main paragon ability)
float chanceOfPrioritizingNonCoreSlotBlessing   // % for non-core slot blessing
float chanceOfPrioritizingUpgradeBlessing       // % for upgrade to existing blessing
float chanceOfPrioritizingAlaCarteBlessing      // % for "a la carte" generic blessing

// === Curve-based chances (AnimationCurve, evaluated at runtime) ===
AnimationCurve chanceOfRollingRoundTableByBlessingCountAboveRequirement
    // X = (player blessing count - RT requirement), Y = chance to include RT blessing
AnimationCurve chanceOfRollingDuoByTotalBlessingCount
    // X = total blessings, Y = chance to include a DUO blessing
AnimationCurve chanceOfPrioritizingNewMechanicByCurrentMechanicCountFromThisParagon
    // X = mechanics from this paragon, Y = chance to offer a new mechanic

// === Paragon weighting ===
AnimationCurve repeatParagonWeightsByCurrentParagonCount
    // How likely to re-offer a paragon you already have blessings from
float newParagonWeight              // weight for offering a never-seen paragon
bool weightParagonsOnReroll         // whether rerolls also use paragon weighting

// === Other ===
bool allowDuosAndRoundTablesInSameRoll
Blessing[] backupBlessings          // fallback pool if nothing valid is found

// === Key methods ===
GeneratedBlessing[] GenerateBlessings(BlessingCategory, PlayerId, BlessingManager, int rarityIncrease, IEnumerable<Blessing> lowPriority)
GeneratedBlessing[] GenerateLeveledBlessings(PlayerId, BlessingManager, int levelIncrease, ...)
GeneratedBlessing[] GenerateSwordInTheStoneBlessings(PlayerId, BlessingManager, ...)
GeneratedBlessing[] GenerateKissCurseBlessings(PlayerId, BlessingManager, bool hasCurse, int count, int rarityIncrease, ...)
ParagonType SelectParagonType(List<ParagonType> available, List<PlayerId> playersToWeight, bool isReroll, BlessingManager)

// Internal pipeline:
GeneratedBlessing[] GenerateBlessingsInternal(BlessingCategory, PlayerId, BlessingManager, int levelIncrease, int rarityIncrease, GenerationOptions, List<Blessing> lowPriority)
Blessing[] SelectBlessings(IEnumerable<Blessing> valid, BlessingCategory, PlayerId, BlessingManager, List<Blessing> lowPriority)
int GenerateBlessingLevel(IBlessingLevel, PlayerId, BlessingManager, int levelIncrease)
BlessingRarity GenerateBlessingRarity(IBlessingRarity, PlayerId, BlessingManager, int rarityIncrease)
List<Blessing> SelectBlessingsFromContext(BlessingSelectionContext, BlessingManager)
float GetOddsForClassification(BlessingClassification, BlessingSelectionContext, BlessingManager)
BlessingSelectionContext BuildBlessingSelectionContext(IEnumerable<Blessing> valid, BlessingCategory, PlayerId, BlessingManager, List<Blessing> lowPriority, bool canShowRT)
float GetChanceToIncludeRoundTableBlessing(BlessingManager)
float GetParagonTypeWeight(ParagonType, HashSet<ParagonType> current, bool isReroll)
```

### How Blessing Generation Works (Flow)

1. **Player completes a room** → reward entity spawns (e.g. `BlessingRewardEntity`)
2. Entity calls `BlessingGenerator.GenerateBlessings(category, playerId, manager, rarityIncrease, lowPriority)`
3. **BuildBlessingSelectionContext()**: classifies all valid blessings into buckets:
   - `CoreSlotBlessings` — main paragon ability upgrades
   - `NonCoreSlotBlessings` — secondary paragon blessings
   - `NewMechanicBlessings` — mechanics player doesn't have yet
   - `MechanicUpgrade` — upgrades to existing mechanics
   - `AlaCarteBlessings` — generic utility blessings
   - `DuoBlessings` — cross-paragon synergy blessings
   - `RoundTableBlessings` — knight blessings (gated by blessing count)
   - `PreviouslyRerolledBlessings` — blessings from prior reroll
   - `BackupBlessings` — fallback pool
4. **Roll phase**: iterate `RollStep[]` — each step has a `BlessingClassification`. For each step, call `GetOddsForClassification()` using the flat chance fields, then probabilistically pick from that bucket.
5. **Fill phase**: iterate `FillStep[]` — each step has a `BlessingClassification[]` priority list. Try to fill remaining slots from those classifications in order.
6. **Rarity assignment**: for each selected blessing, call `GenerateBlessingRarity()` which rolls against `uncommonBlessingBaseChance`, `rareBlessingBaseChance`, `epicBlessingBaseChance`, `legendaryBlessingBaseChance` (highest tier first). The `rarityIncrease` param shifts everything up.
7. **Level assignment**: `GenerateBlessingLevel()` determines the level for the offered blessing.
8. Result = array of `GeneratedBlessing` objects, each with `.Blessing`, `.Level`, `.Rarity`, `.SacrificeReward`, `.SacrificeAmount`.

### BlessingClassification (enum, used internally by generator)
```
Unset = 0, CoreSlot, NonCoreSlots, NewMechanic, MechanicUpgrade,
AlaCarte, Duo, RoundTable, PreviouslyRerolled, BackUp
```

### Mechanic (enum, used for "new mechanic" tracking)
```
Unset, Stun, Quake, Vulnerable, DamageShield, Crit, Fortune,
Javelin, Coin, Mark, Weak, SoulMissile, SpiritCharge, Urn,
Ignite, Immolate, Scorch, Eruption, Chill, FrostNova, Freeze,
Backstab, Shade, Bleed, Invisibility, Venom, Spiderling, Bile,
Fury, Flow, ChainLightning, Whirlwind
```

### GenerationOptions (flags)
```
None = 0, CheckValid = 1, GiveBonusReward = 2
```

### GeneratedBlessing (the offering object)
```csharp
Blessing Blessing           // the blessing ScriptableObject
int? Level                  // level offered (null = no level system)
BlessingRarity? Rarity      // rarity offered
SacrificeType SacrificeReward  // if kiss/curse: sacrifice type
int SacrificeAmount         // sacrifice cost
```

### BlessingRarityValues<T>
Generic container for per-rarity values. Many blessings use this for scaling:
```csharp
T common, uncommon, rare, epic, legendary
T GetValue(BlessingRarity rarity)  // returns the value for that rarity
```

### Rarity Boost System
- `BlessingRarityBoostRoundtable` — a Roundtable blessing that increases rarity chance
  - Has `float rarityChanceIncrease` field
  - On add: applies `BlessingRarityBoostStatus` to player
- `BlessingRarityBoostStatus` (extends Status) — tracks `float chanceBoost`
- `BlessingRarityUtils.IncreaseRarity(BlessingRarity?)` — bumps rarity up one tier

### Modding the Blessing RNG

| Goal | Patch Target | Notes |
|---|---|---|
| Force all Legendary | `BlessingGenerator.GenerateBlessingRarity` | Postfix: `__result = BlessingRarity.Legendary` |
| Increase rarity odds | `BlessingGenerator.uncommonBlessingBaseChance` etc. | Postfix `OnInitializeMelon` to find and set fields |
| Always offer DUO | `BlessingGenerator.GenerateBlessings` | Postfix or patch `BuildBlessingSelectionContext` |
| Force specific blessings | `BlessingGenerator.SelectBlessings` | Postfix to replace result array |
| More offerings per room | `BlessingGenerator.GenerateBlessingsInternal` | Patch `DesiredBlessingCount` in context |

### Blessing Hierarchy (inheritance)
```
Blessing (base ScriptableObject)
  ├── CharacterBlessing (paragon-specific base)
  │     ├── CourageBlessing
  │     ├── FlameBlessing
  │     ├── FrostBlessing
  │     ├── VenomBlessing
  │     ├── ShadowBlessing
  │     ├── WindBlessing
  │     ├── DeathBlessing
  │     └── CritBlessing
  ├── DuoBlessing (cross-paragon synergy)
  ├── RoundTableBlessing (from knight fights)
  ├── ShopBlessing (from shops)
  ├── EventBlessing (from shrine events)
  ├── ParagonBlessing (generic paragon)
  └── (many concrete subclasses per mechanic)
```

Each concrete blessing (e.g. `AdrenalineCounterBlessing`, `BackstabApplicationBlessing`) defines its own stat bonuses, `OnAdd`/`OnRemove` hooks, and `GetBlessingStatDescriptionInternal()`.

### BlessingCategory (ScriptableObject)
Groups blessings by paragon type. Each category has:
```csharp
string Name
BlessingType blessingType             // which BlessingType flag this category covers
Blessing[] Blessings                  // all blessings in this category
BlessingBannerWorldChoiceItem worldChoiceItem  // the banner/visual shown to player
bool exclude                          // whether to exclude from generated tables
```
Subcategory variant: `AbilityBlessingCategory` has `List<BlessingCategory> subCategories`.

---

## Corruption System

Corruptions are room modifiers that make combat harder. Added by `DifficultySettings.Corruptions` per room.

### Corruption (ScriptableObject)
```csharp
LocalizedString Description
Sprite Icon
Corruption[] ConflictingCorruptions   // can't appear together
bool MultiplayerOnly                  // only in co-op
float affinity                        // selection weight
bool exclude                          // exclude from generation
bool AllowedInBossRooms

// Lifecycle hooks
void OnLevelStarted(CorruptionManager)
void OnLevelCompleted(CorruptionManager)
void OnPlayerSpawned(PlayerId, CorruptionManager)
void OnPlayerDespawned(PlayerId, CorruptionManager)
void OnMobSpawned(Mob, CorruptionManager)
void OnMobKilled(Mob, CorruptionManager)
float GetAffinity(BorealisGamemode)
bool IsValid(BorealisGamemode)
```

### CorruptionManager (networked entity)
```csharp
CorruptionGeneratedTable corruptionTable    // all corruption ScriptableObjects
TrueBossCorruption trueBossCorruption       // special boss corruption
Dictionary<Type, Corruption> corruptions    // master registry
HashSet<Type> currentCorruptions            // active this level

bool AddCorruption<T>()
bool RemoveCorruption<T>()
void RemoveAllCorruptions()
bool HasCorruption<T>()
T GetCorruption<T>()
IEnumerable<Corruption> GetCurrentCorruptions()

// Synced via RPC (SyncAddCorruption, SyncRemoveCorruption, SyncRemoveAllCorruptions)
```

### CorruptionShrine (PostRoomShrine)
Post-level event where players can interact with corruption orbs to gain/remove corruptions.

### Modding Corruptions
| Goal | Patch Target | Notes |
|---|---|---|
| Remove all corruptions | `CorruptionManager.AddCorruptionInternal` | Prefix returning false |
| Force specific corruption | `CorruptionManager.OnLevelStarted` | Postfix to add corruption |
| Modify corruption weights | `Corruption.GetAffinity` | Postfix to change return value |

---

## Mod Ideas & Hook Points

| Goal | Patch Target | Type | Notes |
|---|---|---|---|
| More rooms per biome | `PathGenerator.SelectRoomGroup` | Prefix (div roomIndex) | Also patch CheckForBlackKnight |
| Scale Black Knight index | `PathGenerator.CheckForBlackKnight` | Prefix | Scale min/max thresholds |
| More intensity | `BiomeData.GetRoomIntensity` | Postfix (multiply result) | Safe, caps at spawn limit |
| More rerolls | `RerollManager.SetRerolls` | OnSceneWasInitialized | Already done in RerollMod500 |
| Custom difficulty | `DifficultyManager.GetDifficultySettings` | Postfix | Multiply returned settings |
| Repeat Roundtable knights | `RoundTableLevelManager.usedLevels` | Prefix (clear list) | Before level selection |
| Repeat Arthur/Morgana | `ArthurLevelManager.EndGame` (or similar) | Prefix (skip/redirect) | Complex — run ends |
| Loop biomes | `ExpeditionManager.ConsumePath` | Postfix | Reset BiomeIndex + RunData |
| Free gems/currency | `MetaCurrencyManager.Spend` | Prefix (return false) | Skip original |
| All Legendary blessings | `BlessingGenerator.GenerateBlessingRarity` | Postfix | `__result = BlessingRarity.Legendary` |
| Boost rarity chances | `BlessingGenerator` fields | Runtime field set | Set `uncommonBlessingBaseChance` etc. |
| Force DUO offerings | `BlessingGenerator.BuildBlessingSelectionContext` | Postfix | Inject DUO blessings into context |
| No corruptions | `CorruptionManager.AddCorruptionInternal` | Prefix (return false) | Skip all corruption adds |
| Custom corruption weights | `Corruption.GetAffinity` | Postfix | Multiply/set return value |
| Grant blessing directly | `BlessingManager.AddBlessing<T>` | Direct call | Needs PlayerId + Type |
| Remove all blessings | `BlessingManager.RemoveAllBlessings` | Direct call | Networked (syncs via RPC) |

---

## Health System Architecture

### Inheritance Hierarchy
```
EntityHealth (base — has Current, Max, CurrentShields, MaxShields, CurrentReviveTokens)
  ├── BasicHealth (simple: destructibles, non-character objects)
  ├── DestructibleHealth (breakable objects)
  ├── DummyHealth (training dummy)
  └── CharacterHealth (adds Statsheet, HealthStats, CurseMultiplier, statusManager)
        ├── BossHealth (single-phase bosses: despawnAbility, death animation, BossUI bar)
        │     └── ArthurDragonHealth (phase 2 of Arthur fight)
        └── TwoPhaseBossHealth (two-phase bosses: revivalAbility, hasDiedOnce)
              ├── ArthurHealth (phase 1 → transitions to dragon via deathToDragonAbility)
              └── MorganaHealth (morganaStatueInteractable on death)
```
Regular mobs also use `CharacterHealth` — same class as bosses, just different prefab stats.

### HealthStats (StatCollection on every mob/boss/player)
```csharp
Single BaseMax                  // base HP set per prefab in Unity editor
ModList ExtraHealth             // additive HP modifiers
ModList HealthIncreaseModifier  // additive increase modifiers
ModList HealthMultiplier        // multiplicative HP modifiers
Single BaseShields              // base shield value
ModList ExtraShield             // additive shield modifiers
ModList ShieldMultiplier        // multiplicative shield modifiers
Int32 BaseReviveTokens          // number of revive tokens
ModList ExtraReviveTokens       // additive token modifiers
// Computed:
Single Max                      // final max HP (BaseMax * HealthMultiplier + ExtraHealth, roughly)
Single ShieldsMax               // final max shields
Int32 MaxReviveTokens           // final revive token count
```

### ModList (modifier stack)
Each ModList is an ordered list of float mods. `Value` property resolves the stack (typically additive: sum of all mods, or multiplicative depending on the `resolve` func).
```csharp
int AddMod(float value)         // add a modifier, returns modId
bool RemoveMod(int modId)       // remove by id
void ClearMods()                // clear all
Single Value { get; }           // resolved final value
```

### DifficultySettings (nested struct in DifficultyManager)
```csharp
float EnemyHealth               // HP multiplier for ALL enemies (no boss-specific field)
float EnemyDamage               // damage multiplier for ALL enemies
int Corruptions                 // corruption count for standard rooms
int BossCorruptions             // corruption count for boss rooms (NOT health-related)
float MetaCurrencyMultiplier    // currency gain multiplier
```
6 difficulty slots (0–5) on `DifficultyManager`, each with its own `DifficultySettings`.
Method: `DifficultySettings GetDifficultySettings(DifficultyLevel level)`

### How Health Gets Set
1. Mob prefab has `MobStatsheet` → `HealthStats` → `BaseMax` (baked in Unity editor per mob type)
2. `Mob.Setup()` → wires up references
3. `Mob.SetMobDifficultyScaling()` → applies `DifficultySettings.EnemyHealth` as a multiplier to `HealthStats.HealthMultiplier.AddMod()`
4. `CharacterHealth.Setup()` → reads final `HealthStats.Max` → sets `EntityHealth.Max`
5. **Boss and normal enemies share the same path** — no separate boss health scaling

### Three Mob Categories (Important Distinction)

| Game label | Code flag | `MobTypeFlags` value | MobType examples | Detection |
|---|---|---|---|---|
| **Regular enemy** | neither IsBoss nor IsMajorEnemy | `MinorMobs = 0` | Zombie, Snake, Boar, AxeThrower | default |
| **"Major Foe"** (door label) | `MobInfo.MobTypeFlags == MajorMobs` | `MajorMobs = 1` | MajorHammerMob, MajorBoar, MajorBerserker, MajorPiker, etc. | `MobStats.Type` name starts with "Major" |
| **Legendary Beast** | `Mob.IsMajorEnemy == true` | set at runtime by `MajorEnemyCombatRunner` | Dagonet, HarpyBoss, BaneOfCrows, Talos | `Mob.IsMajorEnemy` property |
| **Boss** | `Mob.IsBoss == true` (`BossMob` class) | `BossMobs = 2` | Gawain, Percival, Kay, Arthur, Morgana, ArthurDragon | `Mob.IsBoss` property |

- **"Major Foe"** at doors = normal `WaveCombatRunner` room that happens to spawn `MajorMobs` (elite variants — bigger, more HP baked in prefab). They're distinct `MobType` enum entries (MajorHammerMob=17, MajorBoar=19, etc.)
- **Legendary Beast** = `ObjectiveType.MajorEnemy` room, handled by `MajorEnemyCombatRunner`. The `isMajorEnemy` field is set at spawn time.
- **Boss** = `BossMob` class instances. Use `BossHealth` or `TwoPhaseBossHealth` for death mechanics + `BossUI` for the big health bar.

### MobTypeFlags Enum
```
MinorMobs = 0
MajorMobs = 1
BossMobs = 2
```

### MobType Enum (complete)
```
Empty = -1, PracticeDummy = 0, AxeThrower = 1, Boar = 2, HammerMob = 3,
Mortoad = 4, QuestingBeast = 5, Snake = 6, SnakeSpawner = 7, Canis = 8,
BombCaster = 9, GooMortar = 10, Necromancer = 11, Reaper = 12, Scarecrow = 13,
ExplodingRat = 14, MaulerRat = 15, Zombie = 16,
MajorHammerMob = 17, MajorAxeThrower = 18, MajorBoar = 19, MajorMortoad = 20,
Trapper = 21, MajorTrapper = 22, Gawain = 23, LootGoblin = 24,
CrystalSpawner = 25, Shielder = 26, BuffTotem = 27, Berserker = 28,
Bastion = 29, Piker = 30, Pixie = 31, SporeShroom = 32, Shaman = 33,
Pouncer = 34, MajorPiker = 35, Rollerhog = 36, DarkCleric = 37, Zapper = 38,
Boomer = 39, Belcher = 40, Ghost = 41, BoundGhost = 42, ShielderScarecrow = 43,
Talos = 44, Percival = 45, Mosquito = 46, BaneOfCrows = 47,
IslandMortar = 48, IslandSpitter = 49, IslandBeamShooter = 50, IslandSwarmer = 51,
IslandAbomination = 52, LadyBedivere = 53, TheSirensMace = 54, TheSirensStaff = 55,
SwooperGull = 56, WaveWaller = 57, HarpoonShooter = 58, OceanBiter = 59, Farris = 60,
MajorBombCaster = 61, MajorZombie = 62, MajorMosquito = 63, MajorBerserker = 64,
MajorGooMortar = 65, InkSpitter = 66, MajorAbomination = 67,
LightningMage = 72, BeamHorror = 73, SwordKnight = 74, HammerKnight = 75,
BowKnight = 76, MageKnight = 77, CrystalTurret = 78, CorruptedCrystalTurret = 79,
CrystalTarget = 80, CrystalImp = 81, Seedling = 82, Wolf = 83, SnakePlant = 84,
WildwoodSlasher = 85, CrystalPiker = 86, MajorSunCaster = 87,
TrueGawain = 90, GawainsKnights = 91, KingArthur = 99, Morgana = 100,
SunCaster = 101, Shocker = 102, Slicer = 103, ArmThrower = 104, SomewhereBat = 105,
MorganaClone = 106, ArthurDragon = 107, Kay = 108, Dagonet = 109, HarpyBoss = 110
```

### BossMob (extends Mob)
```csharp
LocalizedString bossName            // display name for BossUI bar
AssetReference levelStartupAbility  // cinematic intro ability
AbilityRunner abilityRunner
Boolean IsBoss { get; }             // overrides Mob.IsBoss → always true
LocalizedString BossName { get; }
```
No separate health scaling logic — uses same `Mob.SetMobDifficultyScaling()`.

### Modding Health Per Category
Patch `Mob.SetMobDifficultyScaling()` postfix to add per-category multipliers:
```csharp
[HarmonyPatch(typeof(Mob), "SetMobDifficultyScaling")]
static class HealthBoostPatch {
    static void Postfix(Mob __instance) {
        if (__instance.IsBoss)
            __instance.HealthStats.HealthMultiplier.AddMod(BOSS_HP_MULT);
        else if (__instance.IsMajorEnemy)
            __instance.HealthStats.HealthMultiplier.AddMod(BEAST_HP_MULT);
        else if (__instance.MobStats?.Type.ToString().StartsWith("Major") == true)
            __instance.HealthStats.HealthMultiplier.AddMod(MAJOR_FOE_HP_MULT);
    }
}
```

### Key Health Classes Reference

| Class | Extends | Used By | Key Feature |
|---|---|---|---|
| `EntityHealth` | EntityBase | — | Base: Current, Max, Shields, events |
| `BasicHealth` | EntityHealth | Simple objects | Statsheet, despawnOnDeath, DamageNumbers |
| `CharacterHealth` | EntityHealth | All characters | HealthStats, CurseMultiplier, StatusManager, SyncRPC |
| `BossHealth` | CharacterHealth | Single-phase bosses | despawnAbility, DeathAbilityStarted, BossUI binding |
| `TwoPhaseBossHealth` | CharacterHealth | Two-phase bosses | revivalAbility, hasDiedOnce, hasRevived |
| `HealthStats` | StatCollection | All entities | BaseMax, HealthMultiplier, ExtraHealth modlists |
| `MobStatsheet` | Statsheet | Mobs | HealthStats + MovementStats + CombatStats + MobStats |
| `BossUI` | VisualElement | Boss health bar | HealthBar, poiseBar, frostBar, bossNameLabel |
| `OverheadUI` | MonoBehaviour | Overhead bars | BindMob(isBoss), BindMajorEnemy(), healthBar |

### Existing Health Corruptions
```csharp
EnemyHealthCorruption : Corruption     // multiplies ALL mob health via OnMobSpawned
  Single healthMultiplier              // the multiplier value (set in Unity editor)

EnemyHealthBossCorruption : BossCorruption  // multiplies boss-only health
  Single healthMultiplier
```
Both call `OnMobSpawned(Mob mob, CorruptionManager manager)` — likely does `mob.HealthStats.HealthMultiplier.AddMod(healthMultiplier)`.

### CombatRunner Subclasses (room fight types)
```
CombatRunner (base — RunCombat, ForceEndCombat)
  ├── WaveCombatRunner (standard wave rooms — where Major Foes appear)
  ├── HordeCombatRunner (horde mode)
  ├── MajorEnemyCombatRunner (legendary beast fights)
  ├── RoundtableCombatRunner (Roundtable knight fights)
  ├── BossRushCombatRunner (native Boss Rush arena — v1.2.0.0+)
  ├── OnslaughtCombatRunner
  ├── ArenaCombatRunner
  ├── CapturePointCombatRunner / AreaCaptureCombatRunner
  ├── DestroyTargetsCombatRunner
  ├── ShrineCombatRunner
  ├── LunaBlossomCombatRunner
  ├── ObstacleCourseCombatRunner
  ├── QuizMasterCombatRunner
  ├── SetPieceCombatRunner
  ├── SpawnerEventCombatRunner
  ├── TotemEventCombatRunner
  └── KissCurseCombatRunner
```

---

## v1.2.0.0 Update Changes (2026-04-02)

SWORN 1.0 Update #2 — key changes affecting modding.

### Native Boss Rush Mode
The game now has an official Boss Rush arena in Camelot. Separate from our custom boss rush (which restructures the biome sequence).

**New types:**
- `BossRushLevelManager` (extends `PortalLevelManager`) — manages the arena encounter, generates random corruptions, tracks rounds
- `BossRushCombatRunner` (extends `CombatRunner`) — spawns bosses in waves
- `BossRushPortal` — portal interaction to start/continue boss rush
- `BossRushLevelManager.BossRushWaveData` — per-wave spawn data + reward type

**ExpeditionManager boss rush state:**
- `LevelData BossRushArena` — the arena level asset
- `bool BeatBossRush` (property) — whether player completed native boss rush this run
- `List<BossRushWaveData> BossRushInfo` — wave configuration
- `void StartBossRush()` — initiates native boss rush
- `void SetBossRushAsBeaten()` — marks completion

**BorealisGamemode:**
- `void StartBossRushMode()` / `StartBossRushInternal()` — triggers native boss rush from gamemode

**SwornTweaks guard:** `BossRushSetup.Prefix` checks `ExpeditionManager.BossRushInfo` to skip our custom boss rush if native is active.

### Dragon Arthur (New Final Boss Variant)
Dragon Arthur is a second-phase boss form, restricted to the native Boss Rush mode.

**New types:**
- `DragonLevelManager` (extends `LevelManager`) — has its own `EndGame() → UniTaskVoid`
- `DragonMob` — dragon-specific mob logic
- `ArthurDragonHealth` (extends `BossHealth`) — phase 2 health bar
- Multiple ability classes: `ArthurDragonRingSlamAbility`, `ArthurDragonBeamFanAbility`, `ArthurDragonBiteAbility`, `ArthurDragonSlashAbility`, `ArthurDragonSpiralLinearProjectilesAbility`
- `DragonPhaseStageController` — manages phase transitions
- `DragonLevelManager.PlayDragonPhaseCinematicInternal()`, `PlayEndGameCinematicInternal()`, `PlaySecretBiomeCinematicInternal()`

**MobType:** `ArthurDragon = 107`

**SwornTweaks patch:** `DragonEndGameRedirect` intercepts `DragonLevelManager.EndGame()` (same logic as `ArthurEndGameRedirect`).

### Corruption System Rework
Expanded corruption system with new corruption types and a shrine post-level event. See the Corruption System section above for full API. Key additions in v1.2.0.0:
- `PostLevelEventType.CorruptionShrine = 21` — players can interact with corruption orbs
- `ExpeditionManager.m_corruptionManager`, `corruptionWeights`, `usedCorruptionMultiplier`, `unusedCorruptionMultiplier`
- `ExpeditionManager.NextPathCorruptionAdded` event
- `TrueBossCorruption` subclass for boss-specific corruptions
- `EnemyDamageBossCorruption`, `EnemyHealthBossCorruption` — boss-only damage/health modifiers

**Impact on SwornTweaks:** Corruption health/damage modifiers stack with our HealthBoostPatch and PlayerHealthPatch multipliers. Combined effect may be stronger than intended.

### True Ending Keys (New Progression System)
New collectible system for a "true ending" path.

**Enum: `TrueEndingKeys` (flags)**
```
None = 0, CombatKey = 1, GoldKey = 2, HealthKey = 4, AllKeys = 7
```

**New types:**
- `EndingKeyRewardEntity` — reward pickup entity for keys
- `EndingKeyRewardInfo` — key reward metadata
- `EndingKeyOverlayUI` — HUD indicator

**ExpeditionManager:**
- `TrueEndingKeys` property/field
- `MarkTrueEndingKeyAsSeen()` method
- `SyncSetTrueEndingKeys` RPC

**New RewardTypes:** `EndingKeyCombat = 30`, `EndingKeyGold = 31`, `EndingKeyHealth = 32`

### New Reward Types (TODO: Investigate)
These new `RewardType` values were added. Need to determine what they are and whether DoorRewardPatch should handle them:

| Value | Name | Notes |
|---|---|---|
| 23 | `WarStone` | New stone currency? Related to `MetaCurrencyType.WarStone = 8` |
| 24 | `TreasureStone` | Related to `MetaCurrencyType.TreasureStone = 9` |
| 25 | `WealthStone` | Related to `MetaCurrencyType.WealthStone = 10` |
| 26 | `DevotionStone` | Related to `MetaCurrencyType.DevotionStone = 11` |
| 28 | `TitaniaBlessing` | Blessing reward from Titania? |
| 30 | `EndingKeyCombat` | True ending key (combat variant) |
| 31 | `EndingKeyGold` | True ending key (gold variant) |
| 32 | `EndingKeyHealth` | True ending key (health variant) |
| 98 | `HealthCost` | Door that costs health to enter? |
| 99 | `CurseCost` | Door that costs curse to enter? |

**Action items:**
- Check in-game what Stone rewards look like and whether they're currency door rewards like FairyEmber/Silk/Moonstone
- Decide if DoorRewardPatch should replace Stone rewards with Paragon rewards too
- HealthCost/CurseCost may be door penalties, not rewards — do NOT replace these blindly

### New Room Types
- `RoomType.Morgana = 13` — dedicated Morgana room type (was previously just `Boss` in Somewhere)
- `RoomType.Bridge = 14` — new bridge level connecting areas

**Impact:** BossRushRoomOverride now treats `RoomType.Morgana` as a boss-like room for reward purposes.

### New PostLevelEventTypes
- `SeedSpot = 18` — seed planting spot
- `MetaCurrencyTrove = 19` — meta-currency trove
- `BlackKnightCombat = 20` — Black Knight encounter (was previously a different mechanic)
- `CorruptionShrine = 21` — corruption orb interaction shrine

### BlessingClassification Update
- New value: `BackUp = 10` — fallback blessing classification slot

---

## Notes & Gotchas

- **Networked game**: Many state changes go through `SyncXxx` RPC methods. If a patch only runs on the host, clients may desync. Test in solo mode first.
- **ScriptableObjects**: BiomeData and PathGenerator are Unity assets. You can't easily replace them at runtime; patching methods that read from them is safer.
- **AnimationCurve**: `intensityCurve` is a Unity `AnimationCurve`. Evaluating it returns a float. You can't easily add keyframes at runtime from a mod without IL2CPP interop for the Unity type.
- **UniTask**: All combat runners use UniTask for async flow. Don't block the async context with synchronous heavy work.
- **CancellationToken**: Combat runners pass a `CancellationToken`. If you patch mid-fight, don't break cancellation.
- **Mono.Cecil for code reading**: Use `/tmp/sworn-inspect/` (Mono.Cecil + .NET 8) to read Assembly-CSharp.dll. Cpp2IL at `/tmp/cpp2il/` can regenerate stubs from GameAssembly.dll + global-metadata.dat when MelonLoader stubs are stale.
- **WINEDLLOVERRIDES**: Required to activate MelonLoader under Proton. Set in Steam launch options.
- **`m_biomeRunDatas` is a fixed-size array**: `ExpeditionManager.m_biomeRunDatas` is `Il2CppReferenceArray` created by `ResetBiomeRunData()` matching the original biome count. If you insert into `biomes` after this array is built, the array won't match — the game uses `m_biomeRunDatas[BiomeIndex].BiomeData` to determine the actual biome for path generation, not `biomes[BiomeIndex]`. Any biome insertion must also resize/rebuild `m_biomeRunDatas`.
- **`remainingEventCounts` doesn't track MajorEnemy**: `BiomeRunData.remainingEventCounts` (keyed by `ObjectiveType`) does NOT contain an `ObjectiveType.MajorEnemy` entry. Beast fights are likely controlled by `BiomeData.majorEnemyCombatData` arrays on the ScriptableObject or hardcoded room slots, not the event count system.
- **`biomes` vs `SerializedBiomes`**: Both are `List<BiomeData>` properties on `ExpeditionManager`. `SerializedBiomes` is likely just a wrapper around `biomes` — modifying `biomes` affects both.
- **ExpeditionManager.OnRunStart timing**: `ResetBiomeRunData()` is called during initialization (well before `OnRunStart`), meaning postfixing `OnRunStart` to insert biomes is too late — the run data array is already sized.

---

## SwornMoreRooms v1.3.0-dbg — Known Issues (from Latest.log analysis)

### Issue: Repeated Kingswood biome skipped
- **Symptom**: After DeepHarbor, game goes to Camelot instead of the inserted Kingswood
- **Root cause**: `m_biomeRunDatas` (fixed-size `Il2CppReferenceArray`) created by `ResetBiomeRunData()` before the `OnRunStart` postfix inserts the extra biome. Array stays at 5 entries while `biomes` list grows to 6. `m_biomeRunDatas[3]` still points to Camelot's BiomeRunData.
- **Fix approach**: Either (a) patch `ResetBiomeRunData` to insert the biome first and build the array with the right size, or (b) after insertion, manually resize `m_biomeRunDatas` by creating a new array with 6 entries, copying old data and inserting new Kingswood BiomeRunData at index 3.

### Issue: `remainingEventCounts` MajorEnemy key not found
- **Symptom**: `[SMR] BiomeRunData.Init: MajorEnemy key NOT found in remainingEventCounts` (5-6 times per run start)
- **Root cause**: Game doesn't put `ObjectiveType.MajorEnemy` in the event count dictionary. Beast spawning uses a different mechanism.
- **Impact**: Low — the beast override via `GeneratePaths` postfix (setting `roomObjectiveType = MajorEnemy`) works regardless.

### Issue: SwornRerollModInfinite NullReferenceException
- **Symptom**: `RerollManager.SetRerolls` throws NullRef repeatedly in `OnSceneWasInitialized`
- **Root cause**: `RerollManager` singleton not yet initialized when early scenes load
- **Fix approach**: Guard with null check or use a later callback
