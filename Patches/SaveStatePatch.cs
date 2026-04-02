using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
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
        public int Version { get; set; } = 1;

        [JsonPropertyName("timestamp")]
        public string Timestamp { get; set; } = "";

        [JsonPropertyName("expedition")]
        public ExpeditionData Expedition { get; set; } = new();

        [JsonPropertyName("players")]
        public List<PlayerSaveData> Players { get; set; } = new();
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

    // ── Room counter: track rooms completed per biome ───────────

    internal static class SaveStateTracker
    {
        internal static int BiomeRoomsCompleted;

        internal static void ResetBiomeCounter()
        {
            BiomeRoomsCompleted = 0;
        }
    }

    // Increment counter before each room transition save
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
                    }
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

                MelonLogger.Msg($"[SwornTweaks] [Save] Run state saved — biome={save.Expedition.BiomeIndex} room={save.Expedition.RoomIndex} players={save.Players.Count}");
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

    // ── Load trigger: on fresh run start ─────────────────────────
    //
    // GeneratePaths fires DURING ResetBiomeRunData, but the body
    // likely resets BiomeIndex to 0 before calling it. Strategy:
    //
    //   Prefix  → read save, set biome-override + path-skip flags
    //   Body    → builds m_biomeRunDatas, calls GeneratePaths
    //             (SaveStateBiomeOverride prefix redirects to saved biome)
    //             (SaveStatePathSkip postfix trims completed rooms)
    //   Postfix → set BiomeIndex/RoomIndex/BiomeRoomIndex definitively
    //             (survives whatever the body did to them)

    [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
    [HarmonyPriority(Priority.Low)]
    static class SaveStateLoad
    {
        // Signaling for biome override (consumed by SaveStateBiomeOverride)
        internal static bool ShouldOverrideBiome;
        internal static int TargetBiomeIndex;

        // Signaling for path trimming (consumed by SaveStatePathSkip)
        internal static bool ShouldSkipRooms;
        internal static int RoomsToSkip;

        // Pending save data for the Postfix to consume
        private static SaveData _pendingSave;

        static void Prefix(ExpeditionManager __instance)
        {
            // Reset biome room counter on each biome start
            SaveStateTracker.ResetBiomeCounter();

            try
            {
                if (!Config.AutoSaveEnabled.Value || !Config.LoadSaveOnStart.Value) return;

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

                MelonLogger.Msg($"[SwornTweaks] [Save] Prefix: loading state from {save.Timestamp} — biome={save.Expedition.BiomeIndex} roomsInBiome={save.Expedition.BiomeRoomIndex}");

                // Set biome override flag so SaveStateBiomeOverride redirects
                // PathGenerator.GeneratePaths to the saved biome
                if (save.Expedition.BiomeIndex > 0)
                {
                    ShouldOverrideBiome = true;
                    TargetBiomeIndex = save.Expedition.BiomeIndex;
                    MelonLogger.Msg($"[SwornTweaks] [Save] Will override path generation to biome {save.Expedition.BiomeIndex}");
                }

                // Set skip flags BEFORE GeneratePaths fires (it runs inside ResetBiomeRunData)
                int roomsToSkip = save.Expedition.BiomeRoomIndex;
                if (roomsToSkip > 0)
                {
                    ShouldSkipRooms = true;
                    RoomsToSkip = roomsToSkip;
                    MelonLogger.Msg($"[SwornTweaks] [Save] Will skip {roomsToSkip} rooms on next path generation");
                }

                // Store for Postfix to handle state restore + player restore
                _pendingSave = save;
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Prefix load failed: {ex.Message}");
            }
        }

        static void Postfix(ExpeditionManager __instance)
        {
            if (_pendingSave == null) return;
            var save = _pendingSave;
            _pendingSave = null;

            try
            {
                // Restore expedition state AFTER body ran
                // (body likely reset BiomeIndex/RoomIndex/BiomeRoomIndex to 0)
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
                // (avoids IL2CPP struct equality issues with ContainsKey)
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

    // ── Biome override: redirect path generation to saved biome ──
    //
    // During ResetBiomeRunData the body resets BiomeIndex to 0 and then
    // calls PathGenerator.GeneratePaths with biome-0 data. This prefix
    // swaps the biome + biomeRunData params to the saved biome so the
    // generated path matches where the player actually was.

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    [HarmonyPriority(Priority.High)] // run before all other path patches
    static class SaveStateBiomeOverride
    {
        static void Prefix(ExpeditionManager expeditionManager,
                           ref BiomeData biome,
                           ref PathGenerator.BiomeRunData biomeRunData)
        {
            if (!SaveStateLoad.ShouldOverrideBiome) return;

            try
            {
                int target = SaveStateLoad.TargetBiomeIndex;
                var biomes = expeditionManager.biomes;
                var runDatas = expeditionManager.m_biomeRunDatas;

                if (biomes != null && target < biomes.Count &&
                    runDatas != null && target < runDatas.Length)
                {
                    biome = biomes[target];
                    biomeRunData = runDatas[target];
                    MelonLogger.Msg($"[SwornTweaks] [Save] Biome override: redirected path generation to biome {target}");
                }
                else
                {
                    MelonLogger.Warning($"[SwornTweaks] [Save] Biome override failed: target={target} biomes={biomes?.Count} runDatas={runDatas?.Length}");
                }
            }
            catch (Exception ex)
            {
                MelonLogger.Warning($"[SwornTweaks] [Save] Biome override error: {ex.Message}");
            }
            // Don't clear the flag here — SaveStatePathSkip clears it
            // once the main biome path (long enough to trim) arrives.
        }
    }

    // ── Path trimming: skip completed rooms on load ────────────

    [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
    [HarmonyPriority(Priority.Low - 10)] // run after all other path patches
    static class SaveStatePathSkip
    {
        static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result)
        {
            if (!SaveStateLoad.ShouldSkipRooms) return;

            int skip = SaveStateLoad.RoomsToSkip;
            var paths = __result;

            // If path is too short, this isn't the main biome path (e.g. a 1-entry
            // init path inside ResetBiomeRunData). Keep the flag for the real call.
            if (paths == null || skip >= paths.Length)
            {
                MelonLogger.Msg($"[SwornTweaks] [Save] Path too short ({paths?.Length ?? 0}) to skip {skip} — waiting for biome path");
                return; // do NOT clear flags
            }

            // This is the real biome path — consume all flags and trim
            SaveStateLoad.ShouldSkipRooms = false;
            SaveStateLoad.ShouldOverrideBiome = false;

            int newLen = paths.Length - skip;
            var trimmed = new Il2CppReferenceArray<ExpeditionManager.Path>(newLen);
            for (int i = 0; i < newLen; i++)
                trimmed[i] = paths[i + skip];
            __result = trimmed;

            MelonLogger.Msg($"[SwornTweaks] [Save] Skipped {skip} rooms — path: {paths.Length} → {newLen}");
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
