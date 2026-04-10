# Decisions & Standards

## Design Decisions
| Decision | Rationale |
|----------|-----------|
| Single DLL | Easier than 7 separate mods for users |
| Python configurator | PyQt6 faster to develop; no game references needed |
| INI config | MelonPreferences uses INI; configurator reads directly |
| DLL in repo | Configurator downloads it; GitHub release assets are source |
| Pin PyInstaller 6.13.0 | Unpinned version caused Defender false positive (Win32/Contebrew.A!ml) |
| version_info.txt | Windows exe metadata reduces AV heuristic suspicion |
| Pre-transition health snapshot | ConsumePath body heals players; must capture health in Prefix before heal |
| nextRoomIndex override (not path trimming) | SWORN generates paths 1-2 at a time, full biome array never exists |
| BossRush excluded from save/load | BossRush uses encounter queues that need sequential warmup; GeneratePaths has 8 params we can't fully call yet |

## Won't Fix
| Issue | Reason |
|-------|--------|
| No automated tests | Requires actual game running |
| Large configurator.py (~1400L) | Single file simpler for PyInstaller |
| DLL in repo | Needed for download feature; small (~78KB) |

## Known Issues / TODO
1. No automated test suite (C# or configurator)
2. **Multiplayer blessing restore bug**: `bm.RemoveAllBlessings()` nukes ALL players' blessings on each iteration — in 2-player game only P2 keeps blessings. Need per-player removal or restore order fix.
3. **Multiplayer health restore bug**: `DelayedPlayerRestore` finds first non-mob `CharacterHealth` instead of matching per-player. Need to correlate CharacterHealth to specific player IDs.
4. **BossRush warmup**: Can't call `GeneratePaths` directly for warmup (8 params, unknown names for 4 of them). Need to either find param names via IL2CPP decompilation or use reflection/AccessTools.
5. **Room layout vs room position**: Room skip works (loads correct biome room index) but the visual room layout may differ since path generation is randomized. Path replay with saved data should produce same doors but the level geometry within a room type may vary.

## Quality Standards
| Aspect | Standard |
|--------|----------|
| Game Mod | All 37 settings work in-game |
| Configurator | Reads/writes config correctly |
| Update System | Self-update + DLL download |
| Cross-platform | Windows + Linux (Proton) |

Do not optimize: patches game methods directly; no perf bottleneck. Configurator GUI is responsive.

## Review (2026-03-18 — Production Ready)
16 patches functional, configurator handles missing config, auto-update with error handling, SSL bundled, platform path detection ✓

## Completed
Single DLL consolidation, progressive HP scaling with biome-aware normalization, Boss Rush structured sequences, multiplayer save/resume JSON persistence, auto-update (configurator + DLL), save system v2 redesign (nextRoomIndex override + path recording/replay + pre-heal health snapshot) ✓
