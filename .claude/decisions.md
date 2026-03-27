# Decisions & Standards

## Design Decisions
| Decision | Rationale |
|----------|-----------|
| Single DLL | Easier than 7 separate mods for users |
| Python configurator | PyQt6 faster to develop; no game references needed |
| INI config | MelonPreferences uses INI; configurator reads directly |
| DLL in repo | Configurator downloads it; GitHub release assets are source |

## Won't Fix
| Issue | Reason |
|-------|--------|
| No automated tests | Requires actual game running |
| Large configurator.py (1402L) | Single file simpler for PyInstaller |
| DLL in repo | Needed for download feature; small (52KB) |

## Known Issues
1. No automated test suite (C# or configurator)
2. SwornTweaks.dll checked into repo

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
Single DLL consolidation, progressive HP scaling with biome-aware normalization, Boss Rush structured sequences, multiplayer save/resume JSON persistence, auto-update (configurator + DLL) ✓
