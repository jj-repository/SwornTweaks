using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

namespace SwornTweaks.Patches
{
    // ── Save data model ──────────────────────────────────────────

    internal class SaveData
    {
        [JsonPropertyName("version")]
        public int Version { get; set; } = 2;

        [JsonPropertyName("timestamp")]
        public string Timestamp { get; set; } = "";

        [JsonPropertyName("expedition")]
        public ExpeditionData Expedition { get; set; } = new();

        [JsonPropertyName("players")]
        public List<PlayerSaveData> Players { get; set; } = new();

        [JsonPropertyName("roomHistory")]
        public List<RoomPathSnapshot> RoomHistory { get; set; } = new();
    }

    internal class ExpeditionData
    {
        [JsonPropertyName("biomeIndex")]
        public int BiomeIndex { get; set; }

        [JsonPropertyName("roomIndex")]
        public int RoomIndex { get; set; }

        [JsonPropertyName("biomeRoomIndex")]
        public int BiomeRoomIndex { get; set; }

        [JsonPropertyName("hasKilledArthur")]
        public bool HasKilledArthur { get; set; }

        [JsonPropertyName("hasKilledMorgana")]
        public bool HasKilledMorgana { get; set; }
    }

    internal class PlayerSaveData
    {
        [JsonPropertyName("playerId")]
        public byte PlayerId { get; set; }

        [JsonPropertyName("gold")]
        public int Gold { get; set; }

        [JsonPropertyName("health")]
        public HealthData Health { get; set; } = new();

        [JsonPropertyName("blessings")]
        public List<BlessingData> Blessings { get; set; } = new();
    }

    internal class HealthData
    {
        [JsonPropertyName("current")]
        public float Current { get; set; }

        [JsonPropertyName("max")]
        public float Max { get; set; }

        [JsonPropertyName("curse")]
        public float Curse { get; set; }

        [JsonPropertyName("reviveTokens")]
        public int ReviveTokens { get; set; }
    }

    internal class BlessingData
    {
        [JsonPropertyName("typeName")]
        public string TypeName { get; set; } = "";

        [JsonPropertyName("level")]
        public int Level { get; set; }

        [JsonPropertyName("rarity")]
        public int Rarity { get; set; }
    }

    // ── Path snapshot models ────────────────────────────────────

    internal class PathEntryData
    {
        [JsonPropertyName("roomType")]
        public int RoomType { get; set; }

        [JsonPropertyName("levelName")]
        public string LevelName { get; set; } = "";

        [JsonPropertyName("rewardType")]
        public int RewardType { get; set; }

        [JsonPropertyName("postLevelEvents")]
        public List<int> PostLevelEvents { get; set; } = new();
    }

    internal class RoomPathSnapshot
    {
        [JsonPropertyName("nextRoomIndex")]
        public int NextRoomIndex { get; set; }

        [JsonPropertyName("biomeType")]
        public string BiomeType { get; set; } = "";

        [JsonPropertyName("paths")]
        public List<PathEntryData> Paths { get; set; } = new();
    }

    // ── State tracker ───────────────────────────────────────────

    internal static class SaveStateTracker
    {
        // Room counter for save indexing
        internal static int BiomeRoomsCompleted;

        // Path history recorded during play
        internal static List<RoomPathSnapshot> RoomHistory = new();

        // True while inside ResetBiomeRunData body (between Prefix/Postfix)
        internal static bool IsInResetBiomeRunData;

        // Suppresses our patches during warmup GeneratePaths calls
        internal static bool IsWarmingUp;

        // ── Replay state (active during load) ──
        internal static bool ReplayActive;
        internal static int ReplayTargetRoom;        // BiomeRoomIndex to skip to
        internal static SaveData? ReplaySaveData;     // full save for replay
        internal static List<RoomPathSnapshot>? SavedRoomHistory; // paths from save

        // LevelData lookup (built once on first replay)
        internal static Dictionary<string, LevelData>? LevelLookup;

        internal static void ResetBiomeCounter()
        {
            BiomeRoomsCompleted = 0;
        }

        internal static void ResetHistory()
        {
            RoomHistory.Clear();
        }

        internal static void ClearReplay()
        {
            ReplayActive = false;
            ReplayTargetRoom = 0;
            ReplaySaveData = null;
            SavedRoomHistory = null;
        }

        internal static void BuildLevelLookup()
        {
            if (LevelLookup != null) return;
            LevelLookup = new Dictionary<string, LevelData>();
            try
            {
                var all = Resources.FindObjectsOfTypeAll<LevelData>();
                if (all != null)
                {
                    foreach (var ld in all)
                    {
                        if (ld == null) continue;
                        string name = ld.name;
                        if (!string.IsNullOrEmpty(name))
                            LevelLookup[name] = ld;
                    }
                }
                MelonLogger.Msg($"[SwornTweaks] [Save] Built LevelData lookup: {LevelLookup.Count} entries");
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] LevelData lookup build failed: {ex.Message}");
            }
        }
    }

    // ── Room counter: track rooms completed per biome ───────────

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ConsumePath))]
    [HarmonyPriority(Priority.High)]
    static class SaveStateRoomCounter
    {
        static void Prefix()
        {
            SaveStateTracker.BiomeRoomsCompleted++;
        }
    }

    // ── Save trigger: after each room transition ─────────────────

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ConsumePath))]
    static class SaveStateSave
    {
        static void Postfix(ExpeditionManager __instance)
        {
            DoSave(__instance);
        }

        internal static void DoSave(ExpeditionManager em = null)
        {
            try
            {
                if (!Config.AutoSaveEnabled.Value) return;
                if (Config.BossRushMode.Value) return; // save/load not supported in BossRush

                if (em == null)
                    em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                if (em == null) return;

                // Don't save before any rooms are completed
                if (em.RoomIndex < 0) return;
                var gm = UnityEngine.Object.FindObjectOfType<BorealisGamemode>();
                if (gm == null || gm.players == null) return;

                var bm = UnityEngine.Object.FindObjectOfType<BlessingManager>();
                var cm = UnityEngine.Object.FindObjectOfType<CurrencyManager>();

                // Pre-collect player CharacterHealth components (non-mob) for fallback health reading
                var playerHealthComps = new List<CharacterHealth>();
                try
                {
                    var allHealth = UnityEngine.Object.FindObjectsOfType<CharacterHealth>();
                    if (allHealth != null)
                    {
                        foreach (var h in allHealth)
                        {
                            if (h == null) continue;
                            try { if (h.gameObject.GetComponent<Mob>() != null) continue; } catch { continue; }
                            playerHealthComps.Add(h);
                        }
                    }
                }
                catch { }

                var save = new SaveData
                {
                    Timestamp = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss"),
                    Expedition = new ExpeditionData
                    {
                        BiomeIndex = em.BiomeIndex,
                        RoomIndex = em.RoomIndex,
                        BiomeRoomIndex = SaveStateTracker.BiomeRoomsCompleted,
                        HasKilledArthur = em.HasKilledArthurThisRun,
                        HasKilledMorgana = em.HasKilledMorganaThisRun,
                    },
                    // Include current path history
                    RoomHistory = new List<RoomPathSnapshot>(SaveStateTracker.RoomHistory),
                };

                int playerIndex = 0;
                foreach (var kvp in gm.players)
                {
                    var playerId = kvp.Key;
                    var playerSave = new PlayerSaveData { PlayerId = playerId.id };

                    // Gold
                    if (cm != null)
                    {
                        try { playerSave.Gold = cm.GetGold(playerId); }
                        catch { playerSave.Gold = 0; }
                    }

                    // Health — try PersistentRunData first, then live CharacterHealth
                    try
                    {
                        bool healthCaptured = false;

                        // Approach 1: PersistentRunData (has curse + reviveTokens)
                        var borealisPlayer = kvp.Value;
                        if (borealisPlayer?.PersistentRunData != null)
                        {
                            var chType = Il2CppType.Of<CharacterHealth>();
                            if (chType != null)
                            {
                                bool hasKey = borealisPlayer.PersistentRunData.ContainsKey(chType);
                                if (hasKey)
                                {
                                    var prd = borealisPlayer.PersistentRunData[chType];
                                    var healthPrd = prd?.Cast<CharacterHealth.HealthPersistentRunData>();
                                    if (healthPrd != null && healthPrd.max > 0)
                                    {
                                        playerSave.Health = new HealthData
                                        {
                                            Current = healthPrd.current,
                                            Max = healthPrd.max,
                                            Curse = healthPrd.curse,
                                            ReviveTokens = healthPrd.reviveTokens,
                                        };
                                        healthCaptured = true;
                                        MelonLogger.Msg($"[SwornTweaks] [Save] Health (PRD) P{playerId.id}: {healthPrd.current:F0}/{healthPrd.max:F0} curse={healthPrd.curse:F0} revives={healthPrd.reviveTokens}");
                                    }
                                }
                                if (!healthCaptured)
                                    MelonLogger.Msg($"[SwornTweaks] [Save] PRD health unavailable for P{playerId.id} (hasKey={hasKey})");
                            }
                        }

                        // Approach 2: Live EntityHealth properties (Current/Max are on EntityHealth base class)
                        if (!healthCaptured && playerIndex < playerHealthComps.Count)
                        {
                            var ch = playerHealthComps[playerIndex];
                            var t = Traverse.Create(ch);
                            float currentHp = t.Property("Current").GetValue<float>();
                            float maxHp = t.Property("Max").GetValue<float>();
                            int revives = t.Property("CurrentReviveTokens").GetValue<int>();

                            if (maxHp > 0)
                            {
                                playerSave.Health = new HealthData
                                {
                                    Current = currentHp,
                                    Max = maxHp,
                                    ReviveTokens = revives,
                                };
                                healthCaptured = true;
                                MelonLogger.Msg($"[SwornTweaks] [Save] Health (live) P{playerId.id}: {currentHp:F0}/{maxHp:F0} revives={revives}");
                            }
                        }

                        if (!healthCaptured)
                            MelonLogger.Warning($"[SwornTweaks] [Save] Could not read health for P{playerId.id}");
                    }
                    catch (Exception ex)
                    {
                        MelonLogger.Warning($"[SwornTweaks] [Save] Health read failed for P{playerId.id}: {ex.Message}");
                    }

                    // Blessings — convert IL2CPP IEnumerable to List for safe iteration
                    if (bm != null)
                    {
                        try
                        {
                            var blessings = bm.GetBlessings(playerId);
                            if (blessings != null)
                            {
                                var blessingList = new Il2CppSystem.Collections.Generic.List<Blessing>(blessings);
                                for (int i = 0; i < blessingList.Count; i++)
                                {
                                    var blessing = blessingList[i];
                                    if (blessing == null) continue;
                                    var type = blessing.GetIl2CppType();
                                    string typeName = type?.Name ?? blessing.Name ?? "Unknown";
                                    int level = bm.GetBlessingLevel(playerId, type);
                                    var rarity = bm.GetBlessingRarity(playerId, type);
                                    playerSave.Blessings.Add(new BlessingData
                                    {
                                        TypeName = typeName,
                                        Level = level,
                                        Rarity = (int)rarity,
                                    });
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            MelonLogger.Warning($"[SwornTweaks] [Save] Failed reading blessings for P{playerId.id}: {ex.Message}");
                        }
                    }

                    save.Players.Add(playerSave);
                    playerIndex++;
                }

                string json = JsonSerializer.Serialize(save, new JsonSerializerOptions { WriteIndented = true });
                string savePath = GetSavePath();
                Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);
                File.WriteAllText(savePath, json);

                MelonLogger.Msg($"[SwornTweaks] [Save] Run state saved — biome={save.Expedition.BiomeIndex} room={save.Expedition.RoomIndex} biomeRoom={save.Expedition.BiomeRoomIndex} paths={save.RoomHistory.Count}");
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Save failed: {ex.Message}");
            }
        }

        internal static string GetSavePath()
        {
            return Path.Combine(MelonEnvironment.UserDataDirectory, "SwornTweaks_SaveState.json");
        }
    }

    // ── Path recorder: capture GeneratePaths results ────────────
    //
    // Runs LAST among all GeneratePaths postfixes to capture the
    // final path state after all other patches have modified it.
    // Also updates the save file so room N+1's path data is persisted
    // even though DoSave fires before GeneratePaths.

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    [HarmonyPriority(Priority.Low - 20)]
    static class SaveStatePathRecorder
    {
        static void Postfix(Il2CppReferenceArray<ExpeditionManager.Path> __result,
                            int nextRoomIndex, BiomeData biome)
        {
            if (!Config.AutoSaveEnabled.Value) return;
            if (SaveStateTracker.IsWarmingUp) return; // don't record warmup calls
            if (__result == null || __result.Length == 0) return;

            try
            {
                var bt = biome?.GetBiomeType().ToString() ?? "Unknown";
                var snapshot = new RoomPathSnapshot
                {
                    NextRoomIndex = nextRoomIndex,
                    BiomeType = bt,
                };

                for (int i = 0; i < __result.Length; i++)
                {
                    var path = __result[i];
                    if (path == null) continue;

                    var entry = new PathEntryData
                    {
                        RoomType = (int)path.roomType,
                        LevelName = path.levelData?.name ?? "",
                        RewardType = (int)path.rewardType,
                    };

                    if (path.postLevelEvents != null)
                    {
                        for (int j = 0; j < path.postLevelEvents.Length; j++)
                            entry.PostLevelEvents.Add((int)path.postLevelEvents[j]);
                    }

                    snapshot.Paths.Add(entry);
                }

                SaveStateTracker.RoomHistory.Add(snapshot);
                MelonLogger.Msg($"[SwornTweaks] [Save] Recorded path: nextRoom={nextRoomIndex} biome={bt} doors={snapshot.Paths.Count}");

                // Update save file with latest path history (GeneratePaths fires
                // AFTER DoSave in ConsumePath, so the save file may be stale)
                try
                {
                    string savePath = SaveStateSave.GetSavePath();
                    if (File.Exists(savePath))
                    {
                        string json = File.ReadAllText(savePath);
                        var save = JsonSerializer.Deserialize<SaveData>(json);
                        if (save != null)
                        {
                            save.RoomHistory = new List<RoomPathSnapshot>(SaveStateTracker.RoomHistory);
                            string updated = JsonSerializer.Serialize(save, new JsonSerializerOptions { WriteIndented = true });
                            File.WriteAllText(savePath, updated);
                        }
                    }
                }
                catch { } // non-critical — next DoSave will include it anyway
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Path recording failed: {ex.Message}");
            }
        }
    }

    // ── Load trigger: on fresh run start ─────────────────────────
    //
    // New approach: instead of path trimming (which doesn't work
    // because SWORN generates paths 1-2 at a time), we override
    // nextRoomIndex in GeneratePaths to jump directly to the
    // saved room. The init path (inside ResetBiomeRunData) is
    // overridden to generate the target room's path, so the game
    // loads the correct scene.
    //
    // Before the override, we run "warmup" GeneratePaths calls for
    // rooms 0..N-1 to advance other patches' internal state (e.g.
    // BossRush encounter queues, FaeRealm portal counters).

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    [HarmonyPriority(Priority.Low)]
    static class SaveStateLoad
    {
        // Pending save data for the Postfix to consume
        private static SaveData? _pendingSave;

        static void Prefix(ExpeditionManager __instance)
        {
            // Track init phase for all GeneratePaths calls
            SaveStateTracker.IsInResetBiomeRunData = true;

            // Reset biome room counter on each biome start
            SaveStateTracker.ResetBiomeCounter();
            SaveStateTracker.ResetHistory();

            try
            {
                if (!Config.AutoSaveEnabled.Value || !Config.LoadSaveOnStart.Value) return;
                if (Config.BossRushMode.Value) return; // save/load not supported in BossRush

                // Only load on fresh run start (BiomeIndex == 0)
                if (__instance.BiomeIndex != 0) return;

                string savePath = SaveStateSave.GetSavePath();
                if (!File.Exists(savePath))
                {
                    MelonLogger.Msg("[SwornTweaks] [Save] No save file found — starting fresh run");
                    return;
                }

                string json = File.ReadAllText(savePath);
                var save = JsonSerializer.Deserialize<SaveData>(json);
                if (save == null)
                {
                    MelonLogger.Warning("[SwornTweaks] [Save] Failed to deserialize save file");
                    return;
                }

                int target = save.Expedition.BiomeRoomIndex;
                MelonLogger.Msg($"[SwornTweaks] [Save] Prefix: loading state from {save.Timestamp} — biome={save.Expedition.BiomeIndex} target room={target} saved paths={save.RoomHistory.Count}");

                if (target <= 0)
                {
                    MelonLogger.Msg("[SwornTweaks] [Save] Target room is 0 — no room skip needed");
                    _pendingSave = save; // still restore player state
                    return;
                }

                // Activate replay system
                SaveStateTracker.ReplayActive = true;
                SaveStateTracker.ReplayTargetRoom = target;
                SaveStateTracker.ReplaySaveData = save;
                SaveStateTracker.SavedRoomHistory = save.RoomHistory;
                SaveStateTracker.BuildLevelLookup();

                // Store for Postfix to handle player restore
                _pendingSave = save;
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Prefix load failed: {ex.Message}");
            }
        }

        static void Postfix(ExpeditionManager __instance)
        {
            SaveStateTracker.IsInResetBiomeRunData = false;

            if (_pendingSave == null) return;
            var save = _pendingSave;
            _pendingSave = null;

            try
            {
                // TODO: warmup — call GeneratePaths for rooms 0..target-1 to
                // advance other patches' internal state (BossRush queues, etc.)
                // Skipped for now because GeneratePaths has 8 params and we
                // don't know them all. BossRush+save/load may have wrong encounters.

                // Restore expedition state
                var t = Traverse.Create(__instance);
                t.Property("BiomeIndex").SetValue(save.Expedition.BiomeIndex);
                t.Property("RoomIndex").SetValue(save.Expedition.RoomIndex);
                t.Property("BiomeRoomIndex").SetValue(save.Expedition.BiomeRoomIndex);
                t.Property("HasKilledArthurThisRun").SetValue(save.Expedition.HasKilledArthur);
                t.Property("HasKilledMorganaThisRun").SetValue(save.Expedition.HasKilledMorgana);

                // Sync biome room counter
                SaveStateTracker.BiomeRoomsCompleted = save.Expedition.BiomeRoomIndex;

                MelonLogger.Msg($"[SwornTweaks] [Save] Postfix: expedition restored — biome={save.Expedition.BiomeIndex} roomIndex={save.Expedition.RoomIndex} biomeRoom={save.Expedition.BiomeRoomIndex}");

                // Auto-reset LoadSaveOnStart so the next fresh run starts clean
                Config.LoadSaveOnStart.Value = false;
                MelonPreferences.Save();
                MelonLogger.Msg("[SwornTweaks] [Save] LoadSaveOnStart auto-reset to false");

                // Delayed player state restore — entities must exist first
                MelonCoroutines.Start(DelayedPlayerRestore(save));
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Postfix load failed: {ex.Message}");
            }
        }

        private static IEnumerator DelayedPlayerRestore(SaveData save)
        {
            // Poll for players to spawn (up to 30s)
            BorealisGamemode gm = null;
            float elapsed = 0f;
            while (elapsed < 30f)
            {
                yield return new WaitForSeconds(0.5f);
                elapsed += 0.5f;
                gm = UnityEngine.Object.FindObjectOfType<BorealisGamemode>();
                if (gm?.players != null && gm.players.Count > 0)
                {
                    MelonLogger.Msg($"[SwornTweaks] [Save] Players found after {elapsed:F1}s ({gm.players.Count} players)");
                    break;
                }
            }

            if (gm == null || gm.players == null || gm.players.Count == 0)
            {
                MelonLogger.Warning("[SwornTweaks] [Save] Timed out waiting for players to spawn");
                yield break;
            }

            try
            {
                var bm = UnityEngine.Object.FindObjectOfType<BlessingManager>();
                var cm = UnityEngine.Object.FindObjectOfType<CurrencyManager>();

                // Build a type lookup for blessing resolution
                Dictionary<string, Il2CppSystem.Type>? blessingTypes = null;
                if (bm != null)
                {
                    blessingTypes = new Dictionary<string, Il2CppSystem.Type>();
                    try
                    {
                        var blessingIl2CppType = Il2CppType.Of<Blessing>();
                        if (blessingIl2CppType != null)
                        {
                            var asm = blessingIl2CppType.Assembly;
                            if (asm != null)
                            {
                                foreach (var type in asm.GetTypes())
                                {
                                    if (type == null) continue;
                                    try
                                    {
                                        if (blessingIl2CppType.IsAssignableFrom(type) && !type.IsAbstract)
                                        {
                                            string name = type.Name;
                                            if (!string.IsNullOrEmpty(name))
                                                blessingTypes[name] = type;
                                        }
                                    }
                                    catch { }
                                }
                            }
                        }
                        MelonLogger.Msg($"[SwornTweaks] [Save] Found {blessingTypes.Count} blessing types for restore");
                    }
                    catch (Exception ex)
                    {
                        MelonLogger.Warning($"[SwornTweaks] [Save] Blessing type scan failed: {ex.Message}");
                        blessingTypes = null;
                    }
                }

                // Iterate session players and match to save data by id byte
                foreach (var kvp in gm.players)
                {
                    var playerId = kvp.Key;
                    var borealisPlayer = kvp.Value;

                    // Find matching save data for this player
                    PlayerSaveData playerSave = null;
                    foreach (var ps in save.Players)
                    {
                        if (ps.PlayerId == playerId.id)
                        {
                            playerSave = ps;
                            break;
                        }
                    }
                    if (playerSave == null)
                    {
                        MelonLogger.Msg($"[SwornTweaks] [Save] No save data for P{playerId.id}");
                        continue;
                    }

                    MelonLogger.Msg($"[SwornTweaks] [Save] Found P{playerId.id} in session, restoring...");

                    // Restore gold
                    if (cm != null)
                    {
                        try
                        {
                            int currentGold = cm.GetGold(playerId);
                            int delta = playerSave.Gold - currentGold;
                            if (delta != 0)
                            {
                                cm.AddGold(playerId, delta);
                                MelonLogger.Msg($"[SwornTweaks] [Save] Restored gold for P{playerId.id}: {playerSave.Gold} (delta={delta})");
                            }
                        }
                        catch (Exception ex)
                        {
                            MelonLogger.Warning($"[SwornTweaks] [Save] Gold restore failed for P{playerId.id}: {ex.Message}");
                        }
                    }

                    // Restore health using CharacterHealth.SetMax/SetCurrent/SetReviveTokens
                    if (playerSave.Health.Max > 0)
                    {
                        try
                        {
                            CharacterHealth playerCh = null;
                            var allHealth = UnityEngine.Object.FindObjectsOfType<CharacterHealth>();
                            if (allHealth != null)
                            {
                                foreach (var ch in allHealth)
                                {
                                    if (ch == null) continue;
                                    try { if (ch.gameObject.GetComponent<Mob>() != null) continue; } catch { continue; }
                                    playerCh = ch;
                                    break;
                                }
                            }

                            if (playerCh != null)
                            {
                                playerCh.SetMax(playerSave.Health.Max, playerSave.Health.Curse);
                                playerCh.SetCurrent(playerSave.Health.Current, ActorId.Null);
                                if (playerSave.Health.ReviveTokens > 0)
                                    playerCh.SetReviveTokens(playerSave.Health.ReviveTokens);
                                MelonLogger.Msg($"[SwornTweaks] [Save] Restored health for P{playerId.id}: {playerSave.Health.Current:F0}/{playerSave.Health.Max:F0} curse={playerSave.Health.Curse:F0} revives={playerSave.Health.ReviveTokens}");
                            }
                            else
                            {
                                MelonLogger.Warning($"[SwornTweaks] [Save] Could not find player CharacterHealth for P{playerId.id}");
                            }
                        }
                        catch (Exception ex)
                        {
                            MelonLogger.Warning($"[SwornTweaks] [Save] Health restore failed for P{playerId.id}: {ex.Message}");
                        }
                    }

                    // Restore blessings
                    if (bm != null && blessingTypes != null && playerSave.Blessings.Count > 0)
                    {
                        try
                        {
                            bm.RemoveAllBlessings();

                            foreach (var bd in playerSave.Blessings)
                            {
                                if (!blessingTypes.TryGetValue(bd.TypeName, out var bType))
                                {
                                    MelonLogger.Warning($"[SwornTweaks] [Save] Unknown blessing type '{bd.TypeName}' — skipping");
                                    continue;
                                }

                                var level = new Il2CppSystem.Nullable<int>(bd.Level);
                                var rarity = new Il2CppSystem.Nullable<BlessingRarity>((BlessingRarity)bd.Rarity);
                                bm.AddBlessing(playerId, bType, level, rarity);
                            }

                            MelonLogger.Msg($"[SwornTweaks] [Save] Restored {playerSave.Blessings.Count} blessings for P{playerId.id}");
                        }
                        catch (Exception ex)
                        {
                            MelonLogger.Warning($"[SwornTweaks] [Save] Blessing restore failed for P{playerId.id}: {ex.Message}");
                        }
                    }
                }

                MelonLogger.Msg("[SwornTweaks] [Save] Player state restore complete — scheduling deferred health restore");

                // The game resets health to full during scene initialization (after players spawn).
                // Wait for the first room to fully load (mobs appear), then re-apply saved health.
                MelonCoroutines.Start(DeferredHealthRestore(save));
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Delayed restore failed: {ex.Message}");
            }
        }

        private static IEnumerator DeferredHealthRestore(SaveData save)
        {
            // Wait for the first room to load — poll for mobs (up to 60s)
            float elapsed = 0f;
            bool roomLoaded = false;
            while (elapsed < 60f)
            {
                yield return new WaitForSeconds(1f);
                elapsed += 1f;
                try
                {
                    var mobs = UnityEngine.Object.FindObjectsOfType<Mob>();
                    if (mobs != null && mobs.Length > 0)
                    {
                        roomLoaded = true;
                        break;
                    }
                }
                catch { }
            }

            if (!roomLoaded)
            {
                MelonLogger.Warning("[SwornTweaks] [Save] Deferred health: timed out waiting for room load");
                yield break;
            }

            // Small extra delay to ensure health initialization is fully complete
            yield return new WaitForSeconds(1f);

            // Re-apply health for each player
            try
            {
                var allHealth = UnityEngine.Object.FindObjectsOfType<CharacterHealth>();
                if (allHealth == null) yield break;

                foreach (var ps in save.Players)
                {
                    if (ps.Health.Max <= 0) continue;

                    foreach (var ch in allHealth)
                    {
                        if (ch == null) continue;
                        try { if (ch.gameObject.GetComponent<Mob>() != null) continue; } catch { continue; }

                        float currentHp = Traverse.Create(ch).Property("Current").GetValue<float>();
                        float maxHp = Traverse.Create(ch).Property("Max").GetValue<float>();

                        // Only re-apply if the game reset health (current is at or near max)
                        if (ps.Health.Current < maxHp && currentHp >= maxHp * 0.95f)
                        {
                            ch.SetMax(ps.Health.Max, ps.Health.Curse);
                            ch.SetCurrent(ps.Health.Current, ActorId.Null);
                            MelonLogger.Msg($"[SwornTweaks] [Save] Deferred health restore for P{ps.PlayerId}: {ps.Health.Current:F0}/{ps.Health.Max:F0} (was {currentHp:F0}/{maxHp:F0})");
                        }
                        else
                        {
                            MelonLogger.Msg($"[SwornTweaks] [Save] Deferred health: P{ps.PlayerId} already at {currentHp:F0}/{maxHp:F0} — no override needed");
                        }
                        break; // first non-mob health component
                    }
                }
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Deferred health restore failed: {ex.Message}");
            }
        }
    }

    // ── GeneratePaths Prefix: override biome + nextRoomIndex ────
    //
    // When replay is active, this redirects path generation to the
    // saved room index and biome. Also sets expedition state on the
    // ExpeditionManager right before path generation, so nothing
    // can overwrite our values between here and the generator.

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    [HarmonyPriority(Priority.High)]
    static class SaveStateBiomeOverride
    {
        static void Prefix(ExpeditionManager expeditionManager,
                           ref BiomeData biome,
                           ref PathGenerator.BiomeRunData biomeRunData,
                           ref int nextRoomIndex)
        {
            // Always log for diagnostics
            if (Config.AutoSaveEnabled.Value && !SaveStateTracker.IsWarmingUp)
            {
                string bt = "?";
                try { bt = biome?.GetBiomeType().ToString() ?? "null"; } catch { }
                MelonLogger.Msg($"[SwornTweaks] [Save] GeneratePaths: nextRoomIndex={nextRoomIndex} biome={bt} inInit={SaveStateTracker.IsInResetBiomeRunData} replay={SaveStateTracker.ReplayActive} warmup={SaveStateTracker.IsWarmingUp}");
            }

            if (!SaveStateTracker.ReplayActive) return;
            if (SaveStateTracker.IsWarmingUp) return;

            var save = SaveStateTracker.ReplaySaveData;
            if (save == null) return;

            int target = SaveStateTracker.ReplayTargetRoom;

            // Override biome if saved biome differs from current
            if (save.Expedition.BiomeIndex > 0)
            {
                var biomes = expeditionManager.biomes;
                var runDatas = expeditionManager.m_biomeRunDatas;
                int targetBiome = save.Expedition.BiomeIndex;

                if (biomes != null && targetBiome < biomes.Count &&
                    runDatas != null && targetBiome < runDatas.Length)
                {
                    biome = biomes[targetBiome];
                    biomeRunData = runDatas[targetBiome];
                    MelonLogger.Msg($"[SwornTweaks] [Save] Replay: overrode biome to {targetBiome}");
                }
            }

            // Override nextRoomIndex to the target room
            int orig = nextRoomIndex;
            nextRoomIndex = target;
            MelonLogger.Msg($"[SwornTweaks] [Save] Replay: nextRoomIndex {orig} → {target}");

            // Set expedition state RIGHT HERE — nothing can overwrite between
            // this point and the path generator reading it
            var t = Traverse.Create(expeditionManager);
            t.Property("BiomeIndex").SetValue(save.Expedition.BiomeIndex);
            t.Property("RoomIndex").SetValue(save.Expedition.RoomIndex);
            t.Property("BiomeRoomIndex").SetValue(target);
            t.Property("HasKilledArthurThisRun").SetValue(save.Expedition.HasKilledArthur);
            t.Property("HasKilledMorganaThisRun").SetValue(save.Expedition.HasKilledMorgana);
        }
    }

    // ── GeneratePaths Postfix: replay saved path data ───────────
    //
    // When replay is active, replaces the generated path entries'
    // fields with saved data from the original run. This ensures
    // the player gets the same room layout.
    //
    // For the init call (inside ResetBiomeRunData), ensures the
    // result has exactly 1 element (the game expects this for init).
    //
    // Consumes the replay after the first non-init call.

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    [HarmonyPriority(Priority.Low - 10)]
    static class SaveStatePathReplay
    {
        static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result,
                            int nextRoomIndex)
        {
            if (!SaveStateTracker.ReplayActive) return;
            if (SaveStateTracker.IsWarmingUp) return;
            if (__result == null || __result.Length == 0) return;

            var history = SaveStateTracker.SavedRoomHistory;
            if (history == null || history.Count == 0)
            {
                MelonLogger.Msg("[SwornTweaks] [Save] Replay: no saved path history — using generated paths");
                ConsumeReplayIfGameplay();
                return;
            }

            // Find saved snapshot matching this nextRoomIndex
            RoomPathSnapshot? snapshot = null;
            foreach (var s in history)
            {
                if (s.NextRoomIndex == nextRoomIndex)
                {
                    snapshot = s;
                    break;
                }
            }

            if (snapshot == null)
            {
                MelonLogger.Msg($"[SwornTweaks] [Save] Replay: no saved data for room {nextRoomIndex} — using generated paths");
                ConsumeReplayIfGameplay();
                return;
            }

            // Overwrite generated path entries with saved data
            var lookup = SaveStateTracker.LevelLookup;
            int overwritten = 0;

            // Match generated paths 1:1 with saved paths (use min of both counts)
            int count = Math.Min(__result.Length, snapshot.Paths.Count);
            for (int i = 0; i < count; i++)
            {
                var path = __result[i];
                var saved = snapshot.Paths[i];
                if (path == null) continue;

                path.roomType = (RoomType)saved.RoomType;
                path.rewardType = (RewardType)saved.RewardType;

                // Restore LevelData by name lookup
                if (lookup != null && !string.IsNullOrEmpty(saved.LevelName) &&
                    lookup.TryGetValue(saved.LevelName, out var ld))
                {
                    path.levelData = ld;
                }

                // Restore post-level events
                if (saved.PostLevelEvents.Count > 0)
                {
                    var events = new Il2CppStructArray<PostLevelEventType>(saved.PostLevelEvents.Count);
                    for (int j = 0; j < saved.PostLevelEvents.Count; j++)
                        events[j] = (PostLevelEventType)saved.PostLevelEvents[j];
                    path.postLevelEvents = events;
                }
                else
                {
                    path.postLevelEvents = new Il2CppStructArray<PostLevelEventType>(0);
                }

                overwritten++;
            }

            // If init call and result has more than 1 element, trim to 1
            // (the game expects exactly 1 path for the initial room setup)
            if (SaveStateTracker.IsInResetBiomeRunData && __result.Length > 1)
            {
                var trimmed = new Il2CppReferenceArray<ExpeditionManager.Path>(1);
                trimmed[0] = __result[0];
                __result = trimmed;
                MelonLogger.Msg($"[SwornTweaks] [Save] Replay: trimmed init result to 1 element");
            }

            MelonLogger.Msg($"[SwornTweaks] [Save] Replay: overwrote {overwritten}/{__result.Length} paths for room {nextRoomIndex} with saved data");

            ConsumeReplayIfGameplay();
        }

        private static void ConsumeReplayIfGameplay()
        {
            // Only consume replay after the first non-init call
            // (the init call inside ResetBiomeRunData should NOT consume)
            if (!SaveStateTracker.IsInResetBiomeRunData)
            {
                SaveStateTracker.ClearReplay();
                MelonLogger.Msg("[SwornTweaks] [Save] Replay consumed (first gameplay GeneratePaths call)");
            }
        }
    }

    // ── Run end cleanup: delete save when run finishes normally ──

    [HarmonyPatch(typeof(BorealisGamemode), nameof(BorealisGamemode.EndRun))]
    static class SaveStateEndRunCleanup
    {
        static void Postfix()
        {
            try
            {
                if (!Config.AutoSaveEnabled.Value) return;

                string savePath = SaveStateSave.GetSavePath();
                if (File.Exists(savePath))
                {
                    File.Delete(savePath);
                    MelonLogger.Msg("[SwornTweaks] [Save] Run ended — save file deleted");
                }
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] EndRun cleanup failed: {ex.Message}");
            }
        }
    }
}
