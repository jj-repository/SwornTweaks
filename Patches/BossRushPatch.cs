using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
namespace SwornTweaks.Patches
{
    /// <summary>
    /// Boss Rush Mode: Structured boss rush per combat biome.
    /// Room 0: normal combat + extra blessings.
    /// Rooms 1..N: unique beasts (shuffled, no repeats).
    /// Rooms N+1..end: unique biome bosses (shuffled, no repeats).
    /// Biomes are shortened to exactly fit the encounters.
    /// Somewhere is shortened to 1 room (direct Morgana fight), no extra rewards.
    /// Camelot: full Roundtable + Arthur (non-randomizer), or Arthur-only (randomizer).
    /// Arthur/Morgana end-game triggers intercepted to continue the run.
    /// Post-room healing applied via ConsumePath hook.
    /// Progressive HP scaling: boss/beast HP compounds per room across biomes.
    /// Randomizer mode: pools all encounters globally, shuffles, redistributes round-robin.
    /// </summary>
    static class BossRushPatch
    {
        private static readonly Random _rng = new();

        private static readonly PostLevelEventType[] _shrineTypes = {
            PostLevelEventType.MabShrine, PostLevelEventType.BabdShrine,
            PostLevelEventType.BeiraShrine, PostLevelEventType.ClionaShrine,
            PostLevelEventType.GogmagogShrine, PostLevelEventType.LughShrine,
            PostLevelEventType.OberonShrine, PostLevelEventType.TitaniaShrine,
        };

        // Saved original rooms for restoration between runs
        private static readonly Dictionary<BiomeType, Il2CppReferenceArray<BiomeData.Room>> _originalRooms = new();
        private static Il2CppReferenceArray<BiomeData.Room>? _originalSomewhereRooms;
        private static BiomeData? _somewhereRef;
        private static Il2CppReferenceArray<BiomeData.Room>? _originalCamelotRooms;
        private static BiomeData? _camelotRef;

        // Per-biome encounter queues (built at run start, consumed during play)
        private static readonly Dictionary<BiomeType, Queue<(RoomType type, LevelData level)>> _beastQueues = new();
        private static readonly Dictionary<BiomeType, Queue<(RoomType type, LevelData level)>> _bossQueues = new();

        // Track beast/boss counts per biome for room index boundaries
        private static readonly Dictionary<BiomeType, int> _beastCounts = new();
        private static readonly Dictionary<BiomeType, int> _bossCounts = new();

        // Global room counter across all biomes for progressive HP scaling
        internal static int GlobalRoomCounter { get; private set; }

        // Re-entry guard for EndRun safety net
        private static bool _endRunHandled;

        private static void Shuffle<T>(List<T> list)
        {
            for (int i = list.Count - 1; i > 0; i--)
            {
                int j = _rng.Next(i + 1);
                (list[i], list[j]) = (list[j], list[i]);
            }
        }

        private static bool IsCombatBiome(BiomeType bt)
            => bt == BiomeType.Kingswood || bt == BiomeType.Cornucopia || bt == BiomeType.DeepHarbor;

        private static void RestoreOriginalRooms(ExpeditionManager instance)
        {
            if (_originalRooms.Count == 0 && _originalSomewhereRooms == null && _originalCamelotRooms == null) return;

            var biomes = instance.biomes;
            if (biomes == null) return;

            for (int i = 0; i < biomes.Count; i++)
            {
                var biome = biomes[i];
                if (biome == null) continue;
                var bt = biome.GetBiomeType();
                if (_originalRooms.TryGetValue(bt, out var origRooms))
                    biome.rooms = origRooms;
            }

            if (_somewhereRef != null && _originalSomewhereRooms != null)
                _somewhereRef.rooms = _originalSomewhereRooms;

            if (_camelotRef != null && _originalCamelotRooms != null)
                _camelotRef.rooms = _originalCamelotRooms;

            _originalRooms.Clear();
            _originalSomewhereRooms = null;
            _somewhereRef = null;
            _originalCamelotRooms = null;
            _camelotRef = null;
        }

        /// <summary>
        /// Add trove (horn) post-level events to all paths.
        /// </summary>
        private static void AddTroveEvents(Il2CppReferenceArray<ExpeditionManager.Path> paths,
                                            int troveCount, int roomIndex)
        {
            if (troveCount <= 0) return;

            for (int i = 0; i < paths.Length; i++)
            {
                var path = paths[i];
                if (path == null) continue;

                var existing = path.postLevelEvents;
                int existingLen = existing?.Length ?? 0;
                var newEvents = new Il2CppStructArray<PostLevelEventType>(existingLen + troveCount);

                if (existing != null)
                    for (int j = 0; j < existingLen; j++)
                        newEvents[j] = existing[j];

                for (int j = 0; j < troveCount; j++)
                    newEvents[existingLen + j] = PostLevelEventType.Trove;

                path.postLevelEvents = newEvents;
            }

            MelonLogger.Msg($"[SwornTweaks] [BossRush] Room {roomIndex}: +{troveCount} trove(s)");
        }

        /// <summary>
        /// Add random god shrine post-level events to all paths.
        /// </summary>
        private static void AddBlessingEvents(Il2CppReferenceArray<ExpeditionManager.Path> paths,
                                               int count, int roomIndex)
        {
            if (count <= 0) return;

            for (int i = 0; i < paths.Length; i++)
            {
                var path = paths[i];
                if (path == null) continue;

                var existing = path.postLevelEvents;
                int existingLen = existing?.Length ?? 0;
                var newEvents = new Il2CppStructArray<PostLevelEventType>(existingLen + count);

                if (existing != null)
                    for (int j = 0; j < existingLen; j++)
                        newEvents[j] = existing[j];

                for (int j = 0; j < count; j++)
                    newEvents[existingLen + j] = _shrineTypes[_rng.Next(_shrineTypes.Length)];

                path.postLevelEvents = newEvents;
            }

            MelonLogger.Msg($"[SwornTweaks] [BossRush] Room {roomIndex}: +{count} blessing shrine(s)");
        }

        /// <summary>
        /// Append a single post-level event to all paths.
        /// </summary>
        private static void AppendPostLevelEvent(Il2CppReferenceArray<ExpeditionManager.Path> paths,
                                                  PostLevelEventType eventType)
        {
            for (int i = 0; i < paths.Length; i++)
            {
                var path = paths[i];
                if (path == null) continue;

                var existing = path.postLevelEvents;
                int existingLen = existing?.Length ?? 0;
                var newEvents = new Il2CppStructArray<PostLevelEventType>(existingLen + 1);

                if (existing != null)
                    for (int j = 0; j < existingLen; j++)
                        newEvents[j] = existing[j];

                newEvents[existingLen] = eventType;
                path.postLevelEvents = newEvents;
            }
        }

        /// <summary>
        /// Collect all unique beasts and bosses from a combat biome.
        /// </summary>
        private static void CollectEncounters(BiomeData biome,
            out List<(RoomType type, LevelData level)> beasts,
            out List<(RoomType type, LevelData level)> bosses)
        {
            beasts = new List<(RoomType type, LevelData level)>();
            var seen = new HashSet<string>();

            var mbPool = biome.MiniBossLevelPool;
            if (mbPool != null)
                for (int j = 0; j < mbPool.Length; j++)
                    if (mbPool[j] != null && seen.Add(mbPool[j].name))
                        beasts.Add((RoomType.MiniBoss, mbPool[j]));
            var mbFirst = biome.FirstMiniBossLevel;
            if (mbFirst != null && seen.Add(mbFirst.name))
                beasts.Add((RoomType.MiniBoss, mbFirst));

            bosses = new List<(RoomType type, LevelData level)>();
            seen.Clear();

            var bPool = biome.bossLevelPool;
            if (bPool != null)
                for (int j = 0; j < bPool.Length; j++)
                    if (bPool[j] != null && seen.Add(bPool[j].name))
                        bosses.Add((RoomType.Boss, bPool[j]));
            var bFirst = biome.firstBossLevel;
            if (bFirst != null && seen.Add(bFirst.name))
                bosses.Add((RoomType.Boss, bFirst));
        }

        /// <summary>
        /// Shorten a biome to exactly rushCount rooms, reusing existing room templates.
        /// </summary>
        private static void ShortenBiome(BiomeData biome, int rushCount)
        {
            var origRooms = biome.rooms;
            int sourceLen = origRooms?.Length ?? 0;
            if (sourceLen > 0)
            {
                var newRooms = new Il2CppReferenceArray<BiomeData.Room>(rushCount);
                for (int r = 0; r < rushCount; r++)
                    newRooms[r] = origRooms![Math.Min(r, sourceLen - 1)];
                biome.rooms = newRooms;
            }
        }

        /// <summary>
        /// Setup: shorten biomes and build encounter queues at run start.
        /// Runs after BiomeRepeatPatch (which may add extra biomes).
        /// </summary>
        [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ResetBiomeRunData))]
        [HarmonyPriority(Priority.Low)]
        static class BossRushSetup
        {
            static void Prefix(ExpeditionManager __instance)
            {
                // Always restore originals from previous run first
                RestoreOriginalRooms(__instance);

                _beastQueues.Clear();
                _bossQueues.Clear();
                _beastCounts.Clear();
                _bossCounts.Clear();
                GlobalRoomCounter = 0;
                _endRunHandled = false;

                if (!Config.BossRushMode.Value) return;

                var biomes = __instance.biomes;
                if (biomes == null) return;

                bool randomizer = Config.BossRushRandomizer.Value;

                if (randomizer)
                    SetupRandomizer(biomes);
                else
                    SetupStandard(biomes);
            }
        }

        /// <summary>
        /// Standard boss rush: per-biome encounter queues, Camelot untouched.
        /// </summary>
        private static void SetupStandard(Il2CppSystem.Collections.Generic.List<BiomeData> biomes)
        {
            for (int i = 0; i < biomes.Count; i++)
            {
                var biome = biomes[i];
                if (biome == null) continue;
                var bt = biome.GetBiomeType();

                if (IsCombatBiome(bt))
                {
                    if (_originalRooms.ContainsKey(bt)) continue;

                    CollectEncounters(biome, out var beasts, out var bosses);
                    Shuffle(beasts);
                    Shuffle(bosses);

                    _beastQueues[bt] = new Queue<(RoomType, LevelData)>(beasts);
                    _bossQueues[bt] = new Queue<(RoomType, LevelData)>(bosses);
                    _beastCounts[bt] = beasts.Count;
                    _bossCounts[bt] = bosses.Count;

                    int rushCount = 1 + beasts.Count + bosses.Count;
                    _originalRooms[bt] = biome.rooms;
                    ShortenBiome(biome, rushCount);

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] {bt}: {beasts.Count} beasts, {bosses.Count} bosses -> {rushCount} rooms");
                    foreach (var b in beasts)
                        MelonLogger.Msg($"[SwornTweaks] [BossRush]   Beast: {b.level.name}");
                    foreach (var b in bosses)
                        MelonLogger.Msg($"[SwornTweaks] [BossRush]   Boss: {b.level.name}");
                }
                else if (bt == BiomeType.Somewhere)
                {
                    var origRooms = biome.rooms;
                    if (origRooms == null || origRooms.Length <= 1) continue;

                    _originalSomewhereRooms = origRooms;
                    _somewhereRef = biome;

                    var newRooms = new Il2CppReferenceArray<BiomeData.Room>(1);
                    newRooms[0] = origRooms[origRooms.Length - 1];
                    biome.rooms = newRooms;

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Somewhere shortened to 1 room (was {origRooms.Length})");
                }
            }
        }

        /// <summary>
        /// Randomizer mode: pool all encounters globally, shuffle, redistribute round-robin.
        /// Camelot shortened to 1 room (Arthur only, no Roundtable).
        /// Biome order shuffled (Somewhere always last).
        /// </summary>
        private static void SetupRandomizer(Il2CppSystem.Collections.Generic.List<BiomeData> biomes)
        {
            // 1. Collect all encounters from all combat biomes into one global pool
            var globalPool = new List<(RoomType type, LevelData level)>();
            var globalSeen = new HashSet<string>();
            var combatBiomes = new List<(int index, BiomeData biome, BiomeType bt)>();

            for (int i = 0; i < biomes.Count; i++)
            {
                var biome = biomes[i];
                if (biome == null) continue;
                var bt = biome.GetBiomeType();

                if (IsCombatBiome(bt))
                {
                    if (_originalRooms.ContainsKey(bt)) continue;
                    combatBiomes.Add((i, biome, bt));

                    CollectEncounters(biome, out var beasts, out var bosses);
                    foreach (var b in beasts)
                        if (globalSeen.Add(b.level.name))
                            globalPool.Add(b);
                    foreach (var b in bosses)
                        if (globalSeen.Add(b.level.name))
                            globalPool.Add(b);

                    _originalRooms[bt] = biome.rooms;
                }
                else if (bt == BiomeType.Somewhere)
                {
                    var origRooms = biome.rooms;
                    if (origRooms != null && origRooms.Length > 1)
                    {
                        _originalSomewhereRooms = origRooms;
                        _somewhereRef = biome;
                        var newRooms = new Il2CppReferenceArray<BiomeData.Room>(1);
                        newRooms[0] = origRooms[origRooms.Length - 1];
                        biome.rooms = newRooms;
                        MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer] Somewhere shortened to 1 room");
                    }
                }
                else if (bt == BiomeType.Camelot)
                {
                    var cRooms = biome.rooms;
                    if (cRooms != null && cRooms.Length > 1)
                    {
                        _camelotRef = biome;
                        _originalCamelotRooms = cRooms;

                        // Extract Roundtable LevelData from rooms and add to global pool
                        try
                        {
                            for (int r = 0; r < cRooms.Length; r++)
                            {
                                var room = cRooms[r];
                                if (room == null) continue;
                                if (room.roomTypeOverride != RoomType.Roundtable) continue;

                                var pool = room.levelPoolOverride;
                                if (pool == null || pool.Length == 0) continue;

                                for (int p = 0; p < pool.Length; p++)
                                {
                                    var ld = pool[p];
                                    if (ld != null && globalSeen.Add("RT_" + ld.name))
                                    {
                                        globalPool.Add((RoomType.Roundtable, ld));
                                        MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer] Added Roundtable level: {ld.name}");
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            MelonLogger.Warning($"[SwornTweaks] [BossRush] [Randomizer] Roundtable extraction failed: {ex.Message}");
                        }

                        // Shorten Camelot to 1 room (Arthur fight only)
                        var newRooms = new Il2CppReferenceArray<BiomeData.Room>(1);
                        newRooms[0] = cRooms[cRooms.Length - 1];
                        biome.rooms = newRooms;
                        MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer] Camelot shortened to 1 room (Arthur only)");
                    }
                }
            }

            if (combatBiomes.Count == 0) return;

            // 2. Shuffle the global pool
            Shuffle(globalPool);

            MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer] Global pool: {globalPool.Count} encounters");
            foreach (var e in globalPool)
                MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer]   {e.type}: {e.level.name}");

            // 3. Redistribute round-robin into per-biome boss queues
            //    (beastCounts = 0, bossCounts = share — reuses GeneratePaths logic unchanged)
            int numBiomes = combatBiomes.Count;
            var perBiome = new List<(RoomType, LevelData)>[numBiomes];
            for (int i = 0; i < numBiomes; i++)
                perBiome[i] = new List<(RoomType, LevelData)>();

            for (int i = 0; i < globalPool.Count; i++)
                perBiome[i % numBiomes].Add(globalPool[i]);

            for (int i = 0; i < numBiomes; i++)
            {
                var bt = combatBiomes[i].bt;
                var biome = combatBiomes[i].biome;
                var share = perBiome[i];

                _beastQueues[bt] = new Queue<(RoomType, LevelData)>();
                _bossQueues[bt] = new Queue<(RoomType, LevelData)>(share);
                _beastCounts[bt] = 0;
                _bossCounts[bt] = share.Count;

                // 4. Re-shorten each combat biome to 1 + share rooms
                int rushCount = 1 + share.Count;
                ShortenBiome(biome, rushCount);

                MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer] {bt}: {share.Count} encounters -> {rushCount} rooms");
                foreach (var e in share)
                    MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer]   {e.Item1}: {e.Item2.name}");
            }

            // 5. Shuffle biome order (Fisher-Yates), keeping Somewhere always last
            //    Find Somewhere index and temporarily remove it
            int somewhereIdx = -1;
            BiomeData? somewhereData = null;
            for (int i = 0; i < biomes.Count; i++)
            {
                if (biomes[i]?.GetBiomeType() == BiomeType.Somewhere)
                {
                    somewhereIdx = i;
                    somewhereData = biomes[i];
                    break;
                }
            }

            if (somewhereIdx >= 0)
                biomes.RemoveAt(somewhereIdx);

            // Fisher-Yates on remaining biomes
            int n = biomes.Count;
            for (int i = n - 1; i > 0; i--)
            {
                int j = _rng.Next(i + 1);
                var tmp = biomes[i];
                biomes[i] = biomes[j];
                biomes[j] = tmp;
            }

            // Put Somewhere back at the end
            if (somewhereData != null)
                biomes.Add(somewhereData);

            MelonLogger.Msg("[SwornTweaks] [BossRush] [Randomizer] Biome order:");
            for (int i = 0; i < biomes.Count; i++)
                MelonLogger.Msg($"[SwornTweaks] [BossRush] [Randomizer]   [{i}] = {biomes[i]?.GetBiomeType()}");
        }

        /// <summary>
        /// GeneratePaths Postfix: override room types and rewards for the boss rush sequence.
        /// </summary>
        [HarmonyPatch(typeof(PathGenerator), nameof(PathGenerator.GeneratePaths))]
        [HarmonyPriority(Priority.Low)] // run after BeastRoomPatch
        static class BossRushRoomOverride
        {
            static void Postfix(ref Il2CppReferenceArray<ExpeditionManager.Path> __result,
                                int nextRoomIndex, BiomeData biome)
            {
                if (!Config.BossRushMode.Value) return;
                if (__result == null || __result.Length == 0) return;

                var bt = biome != null ? biome.GetBiomeType() : BiomeType.None;

                // Somewhere: no extra rewards at all (Morgana ends the game)
                if (bt == BiomeType.Somewhere) return;

                // Camelot: only Arthur gets extra rewards, Roundtable stays vanilla
                if (bt == BiomeType.Camelot)
                {
                    bool isArthur = false;
                    for (int i = 0; i < __result.Length; i++)
                    {
                        var path = __result[i];
                        if (path != null && path.roomType == RoomType.Arthur)
                        { isArthur = true; break; }
                    }
                    if (isArthur)
                    {
                        GlobalRoomCounter++;
                        MelonLogger.Msg($"[SwornTweaks] [BossRush] Camelot Arthur (global #{GlobalRoomCounter})");
                    }
                    return;
                }

                // Skip non-combat biomes
                if (!IsCombatBiome(bt)) return;

                int numBeasts = _beastCounts.GetValueOrDefault(bt, 0);
                int numBosses = _bossCounts.GetValueOrDefault(bt, 0);

                GlobalRoomCounter++;

                int troveCount = Math.Clamp(Config.BossRushHornRewards.Value, 0, 3);
                int blessingCount = Math.Clamp(Config.BossRushExtraBlessings.Value, 0, 3);
                bool isLastBoss = (nextRoomIndex == numBeasts + numBosses) && numBosses > 0;

                if (nextRoomIndex == 0)
                {
                    // Room 0: normal combat with SwordInTheStone paragon reward
                    for (int i = 0; i < __result.Length; i++)
                    {
                        var path = __result[i];
                        if (path == null) continue;
                        path.rewardType = RewardType.SwordInTheStone;
                    }
                    AddTroveEvents(__result, troveCount, nextRoomIndex);
                    AddBlessingEvents(__result, blessingCount, nextRoomIndex);
                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Room 0 (SwordInTheStone) in {bt} (global #{GlobalRoomCounter})");
                }
                else if (nextRoomIndex <= numBeasts)
                {
                    if (_beastQueues.TryGetValue(bt, out var bq) && bq.Count > 0)
                    {
                        var pick = bq.Dequeue();
                        for (int i = 0; i < __result.Length; i++)
                        {
                            var path = __result[i];
                            if (path == null) continue;
                            path.roomType = pick.type;
                            path.levelData = pick.level;
                            // Clear unwanted post-level events (fae portals, Black Knight, etc.)
                            path.postLevelEvents = new Il2CppStructArray<PostLevelEventType>(0);
                        }
                        AddTroveEvents(__result, troveCount, nextRoomIndex);
                        AddBlessingEvents(__result, blessingCount, nextRoomIndex);
                        MelonLogger.Msg($"[SwornTweaks] [BossRush] Room {nextRoomIndex} -> {pick.type} ({pick.level.name}) in {bt} (global #{GlobalRoomCounter})");
                    }
                }
                else if (nextRoomIndex <= numBeasts + numBosses)
                {
                    if (_bossQueues.TryGetValue(bt, out var bq) && bq.Count > 0)
                    {
                        var pick = bq.Dequeue();
                        for (int i = 0; i < __result.Length; i++)
                        {
                            var path = __result[i];
                            if (path == null) continue;
                            path.roomType = pick.type;
                            path.levelData = pick.level;
                            // Clear unwanted post-level events
                            path.postLevelEvents = new Il2CppStructArray<PostLevelEventType>(0);

                            // Last boss per biome gets Healing fountain reward
                            if (isLastBoss)
                                path.rewardType = RewardType.Healing;
                        }

                        if (isLastBoss)
                        {
                            // Fountain room: troves + blessings + fae portal on first two biomes
                            AddTroveEvents(__result, troveCount, nextRoomIndex);
                            AddBlessingEvents(__result, blessingCount, nextRoomIndex);

                            // Inject fae portal on last boss: Kiss on 1st biome, KissCurse on 2nd
                            try
                            {
                                var em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                                int biomeIdx = em?.BiomeIndex ?? -1;
                                PostLevelEventType faeEvent = PostLevelEventType.None;
                                if (biomeIdx == 0)
                                    faeEvent = PostLevelEventType.KissPortal;
                                else if (biomeIdx == 1)
                                    faeEvent = PostLevelEventType.KissCursePortal;

                                if (faeEvent != PostLevelEventType.None)
                                {
                                    AppendPostLevelEvent(__result, faeEvent);
                                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Injected {faeEvent} on last boss of biome {biomeIdx}");
                                }
                            }
                            catch (Exception ex)
                            {
                                MelonLogger.Warning($"[SwornTweaks] [BossRush] Fae portal inject failed: {ex.Message}");
                            }

                            MelonLogger.Msg($"[SwornTweaks] [BossRush] Room {nextRoomIndex} -> {pick.type} ({pick.level.name}) + Healing fountain in {bt} (global #{GlobalRoomCounter})");
                        }
                        else
                        {
                            AddTroveEvents(__result, troveCount, nextRoomIndex);
                            AddBlessingEvents(__result, blessingCount, nextRoomIndex);
                            MelonLogger.Msg($"[SwornTweaks] [BossRush] Room {nextRoomIndex} -> {pick.type} ({pick.level.name}) in {bt} (global #{GlobalRoomCounter})");
                        }
                    }
                }
            }
        }

        /// <summary>
        /// Post-room healing: heal players by configured amount after each room transition.
        /// </summary>
        [HarmonyPatch(typeof(ExpeditionManager), nameof(ExpeditionManager.ConsumePath))]
        static class BossRushPostRoomHeal
        {
            static void Postfix()
            {
                try
                {
                    if (!Config.BossRushMode.Value) return;
                    int healAmount = Config.BossRushHealPerRoom.Value;
                    if (healAmount <= 0) return;

                    var healths = UnityEngine.Object.FindObjectsOfType<CharacterHealth>();
                    if (healths == null) return;
                    foreach (var health in healths)
                    {
                        if (health == null) continue;
                        // Skip mobs — only heal players
                        try { if (health.GetComponent<Mob>() != null) continue; }
                        catch { continue; }
                        health.AddCurrent(healAmount, ActorId.Null);
                    }

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Healed players for {healAmount} HP");
                }
                catch (Exception ex)
                {
                    MelonLogger.Warning($"[SwornTweaks] [BossRush] Heal failed: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Bypass the 3-gem Ring of Dispel requirement to access Somewhere/Morgana in Boss Rush.
        /// </summary>
        [HarmonyPatch(typeof(DialogueStaticData), "get_HasLancelotKeys")]
        static class LancelotKeysBypass
        {
            static bool Prefix(ref bool __result)
            {
                if (!Config.BossRushMode.Value && !Config.SkipSomewhere.Value && !Config.RingOfDispelFree.Value) return true;
                __result = true;
                return false;
            }
        }

        /// <summary>
        /// Intercept Arthur's EndGame: skip the run-ending flow and force level completion
        /// so the game transitions to the next biome.
        /// </summary>
        [HarmonyPatch(typeof(ArthurLevelManager), nameof(ArthurLevelManager.EndGame))]
        static class ArthurEndGameRedirect
        {
            static bool Prefix(ArthurLevelManager __instance)
            {
                if (!Config.BossRushMode.Value) return true;

                try
                {
                    var em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                    if (em == null) return true;
                    int totalBiomes = em.biomes?.Count ?? 0;
                    if (em.BiomeIndex >= totalBiomes - 1) return true; // let final biome end normally

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Intercepting Arthur EndGame at biome {em.BiomeIndex}/{totalBiomes} — calling NextLevel(0)");

                    try
                    {
                        __instance.NextLevel(0);
                        MelonLogger.Msg("[SwornTweaks] [BossRush] NextLevel(0) called for Arthur");
                    }
                    catch (Exception ex)
                    {
                        MelonLogger.Warning($"[SwornTweaks] [BossRush] Arthur NextLevel failed: {ex.Message}");
                    }

                    return false;
                }
                catch { }

                return true;
            }
        }

        /// <summary>
        /// Intercept Morgana's RunEndGameCinematic: skip the cinematic + EndRun flow
        /// and force level completion to advance to the next biome.
        /// </summary>
        [HarmonyPatch(typeof(MorganaLevelManager), nameof(MorganaLevelManager.RunEndGameCinematic))]
        static class MorganaEndGameRedirect
        {
            static bool Prefix(MorganaLevelManager __instance)
            {
                if (!Config.BossRushMode.Value) return true;

                try
                {
                    var em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                    if (em == null) return true;
                    int totalBiomes = em.biomes?.Count ?? 0;
                    if (em.BiomeIndex >= totalBiomes - 1) return true; // let final biome end normally

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] Intercepting Morgana RunEndGameCinematic at biome {em.BiomeIndex}/{totalBiomes} — calling NextLevel(0)");

                    __instance.NextLevel(0);
                    MelonLogger.Msg("[SwornTweaks] [BossRush] NextLevel(0) called for Morgana");

                    return false;
                }
                catch (Exception ex)
                {
                    MelonLogger.Warning($"[SwornTweaks] [BossRush] Morgana redirect failed: {ex.Message}");
                }

                return true;
            }
        }

        /// <summary>
        /// Safety net: intercept EndRun in case EndGame patches miss a path.
        /// Has a re-entry guard to prevent infinite loops.
        /// </summary>
        [HarmonyPatch(typeof(BorealisGamemode), nameof(BorealisGamemode.EndRun))]
        static class EndRunRedirect
        {
            static bool Prefix(bool __0) // __0 = wasVictory
            {
                if (!Config.BossRushMode.Value) return true;

                try
                {
                    if (_endRunHandled) return false;

                    var em = UnityEngine.Object.FindObjectOfType<ExpeditionManager>();
                    if (em == null) return true;

                    int biomeIdx = em.BiomeIndex;
                    int totalBiomes = em.biomes?.Count ?? 0;

                    if (biomeIdx < totalBiomes - 1)
                    {
                        _endRunHandled = true;
                        MelonLogger.Msg($"[SwornTweaks] [BossRush] Intercepting EndRun at biome {biomeIdx}/{totalBiomes} — advancing to next biome");

                        var lm = UnityEngine.Object.FindObjectOfType<LevelManager>();
                        if (lm != null)
                        {
                            lm.NextLevel(0);
                            MelonLogger.Msg("[SwornTweaks] [BossRush] NextLevel(0) called from EndRun redirect");
                        }

                        return false;
                    }

                    MelonLogger.Msg($"[SwornTweaks] [BossRush] At final biome {biomeIdx} — letting EndRun proceed normally");
                }
                catch (Exception ex)
                {
                    MelonLogger.Warning($"[SwornTweaks] [BossRush] EndRun redirect failed: {ex.Message}");
                }

                return true;
            }
        }
    }
}
