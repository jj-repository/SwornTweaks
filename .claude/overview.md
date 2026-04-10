# Overview

v1.12 — Single DLL consolidating multiple SWORN mods + PyQt6 configurator GUI. Game: SWORN (Steam 1763250), MelonLoader required.

## Files
- `Core.cs` — MelonMod entry point
- `Config.cs` — 37 MelonPreferences entries
- `Patches/*.cs` — 16 Harmony patch files
- `configurator.py` — PyQt6 configurator (~1400 lines)
- `SwornTweaks.dll` — compiled mod binary (in repo for download feature, ~78KB)
- `docs/MODDING_CONTEXT.md` — game modding reference (56KB)
- `version_info.txt` — Windows exe version metadata (reduces Defender false positives)
