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
    /// Camelot: Arthur gets extra rewards, Roundtable stays vanilla.
    /// Post-room healing applied via ConsumePath hook.
    /// Progressive HP scaling: boss/beast HP compounds per room across biomes.
    /// </summary>
    static class BossRushPatch
    {
        private static readonly Random _rng = new();

        // Saved original rooms for restoration between runs
        private static readonly Dictionary<BiomeType, Il2CppReferenceArray<BiomeData.Room>> _originalRooms = new();
        private static Il2CppReferenceArray<BiomeData.Room>? _originalSomewhereRooms;
        private static BiomeData? _somewhereRef;

        // Per-biome encounter queues (built at run start, consumed during play)
        private static readonly Dictionary<BiomeType, Queue<(RoomType type, LevelData level)>> _beastQueues = new();
        private static readonly Dictionary<BiomeType, Queue<(RoomType type, LevelData level)>> _bossQueues = new();

        // Track beast/boss counts per biome for room index boundaries
        private static readonly Dictionary<BiomeType, int> _beastCounts = new();
        private static readonly Dictionary<BiomeType, int> _bossCounts = new();

        // Global room counter across all biomes for progressive HP scaling
        internal static int GlobalRoomCounter { get; private set; }

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
            if (_originalRooms.Count == 0 && _originalSomewhereRooms == null) return;

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

            _originalRooms.Clear();
            _originalSomewhereRooms = null;
            _somewhereRef = null;
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

                if (!Config.BossRushMode.Value) return;

                var biomes = __instance.biomes;
                if (biomes == null) return;

                for (int i = 0; i < biomes.Count; i++)
                {
                    var biome = biomes[i];
                    if (biome == null) continue;
                    var bt = biome.GetBiomeType();

                    if (IsCombatBiome(bt))
                    {
                        // Skip if already processed this BiomeType (duplicate from ExtraBiomes)
                        if (_originalRooms.ContainsKey(bt)) continue;

                        // Collect unique beast levels
                        var beasts = new List<(RoomType type, LevelData level)>();
                        var seen = new HashSet<string>();

                        var mbPool = biome.MiniBossLevelPool;
                        if (mbPool != null)
                            for (int j = 0; j < mbPool.Length; j++)
                                if (mbPool[j] != null && seen.Add(mbPool[j].name))
                                    beasts.Add((RoomType.MiniBoss, mbPool[j]));
                        var mbFirst = biome.FirstMiniBossLevel;
                        if (mbFirst != null && seen.Add(mbFirst.name))
                            beasts.Add((RoomType.MiniBoss, mbFirst));

                        // Collect unique boss levels
                        var bosses = new List<(RoomType type, LevelData level)>();
                        seen.Clear();

                        var bPool = biome.bossLevelPool;
                        if (bPool != null)
                            for (int j = 0; j < bPool.Length; j++)
                                if (bPool[j] != null && seen.Add(bPool[j].name))
                                    bosses.Add((RoomType.Boss, bPool[j]));
                        var bFirst = biome.firstBossLevel;
                        if (bFirst != null && seen.Add(bFirst.name))
                            bosses.Add((RoomType.Boss, bFirst));

                        Shuffle(beasts);
                        Shuffle(bosses);

                        _beastQueues[bt] = new Queue<(RoomType, LevelData)>(beasts);
                        _bossQueues[bt] = new Queue<(RoomType, LevelData)>(bosses);
                        _beastCounts[bt] = beasts.Count;
                        _bossCounts[bt] = bosses.Count;

                        // Shorten rooms: 1 normal + beasts + bosses
                        int rushCount = 1 + beasts.Count + bosses.Count;
                        var origRooms = biome.rooms;
                        _originalRooms[bt] = origRooms;

                        int sourceLen = origRooms?.Length ?? 0;
                        if (sourceLen > 0)
                        {
                            var newRooms = new Il2CppReferenceArray<BiomeData.Room>(rushCount);
                            for (int r = 0; r < rushCount; r++)
                                newRooms[r] = origRooms![Math.Min(r, sourceLen - 1)];
                            biome.rooms = newRooms;
                        }

                        MelonLogger.Msg($"[SwornTweaks] [BossRush] {bt}: {beasts.Count} beasts, {bosses.Count} bosses -> {rushCount} rooms");
                        foreach (var b in beasts)
                            MelonLogger.Msg($"[SwornTweaks] [BossRush]   Beast: {b.level.name}");
                        foreach (var b in bosses)
                            MelonLogger.Msg($"[SwornTweaks] [BossRush]   Boss: {b.level.name}");
                    }
                    else if (bt == BiomeType.Somewhere)
                    {
                        // Shorten Somewhere to 1 room (direct Morgana fight)
                        var origRooms = biome.rooms;
                        if (origRooms == null || origRooms.Length <= 1) continue;

                        _originalSomewhereRooms = origRooms;
                        _somewhereRef = biome;

                        // Take the last room (boss fight) as the only room
                        var newRooms = new Il2CppReferenceArray<BiomeData.Room>(1);
                        newRooms[0] = origRooms[origRooms.Length - 1];
                        biome.rooms = newRooms;

                        MelonLogger.Msg($"[SwornTweaks] [BossRush] Somewhere shortened to 1 room (was {origRooms.Length})");
                    }
                }
            }
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
                            // Fountain room: troves + fae portal on first two biomes
                            AddTroveEvents(__result, troveCount, nextRoomIndex);

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
        /// DialogueStaticData.HasLancelotKeys is a static bool property.
        /// </summary>
        [HarmonyPatch(typeof(DialogueStaticData), "get_HasLancelotKeys")]
        static class LancelotKeysBypass
        {
            static bool Prefix(ref bool __result)
            {
                if (!Config.BossRushMode.Value) return true;
                __result = true;
                return false;
            }
        }
    }
}
