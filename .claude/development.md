# Development

## Commands
```bash
# Build C# DLL (requires .NET 6.0 SDK + game references)
dotnet build -c Release

# Deploy DLL to game + repo root
cp bin/Release/net6.0/SwornTweaks.dll "/mnt/c/Program Files (x86)/Steam/steamapps/common/SWORN/Mods/SwornTweaks.dll"
cp bin/Release/net6.0/SwornTweaks.dll SwornTweaks.dll

# Configurator
pip install -r requirements.txt  # PyQt6>=6.5, certifi
python configurator.py

# Build configurator exe (pinned version)
pip install pyinstaller==6.13.0
pyinstaller --onefile --windowed --name SwornTweaks --version-file version_info.txt configurator.py
```

## Dependencies
**C# mod:** .NET 6.0 x64, MelonLoader 0.7.1+, 0Harmony, Il2CppInterop.Runtime, Assembly-CSharp.dll (game stubs)
**Configurator:** PyQt6 >= 6.5, certifi (PyInstaller SSL)
**Game:** SWORN (Steam 1763250), MelonLoader, .NET 6 Desktop Runtime

## Paths
- MelonLoader log: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\MelonLoader\Latest.log`
- Save file: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\UserData\SwornTweaks_SaveState.json`
- Mod DLL: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\Mods\SwornTweaks.dll`
- Config: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\UserData\MelonPreferences.cfg`

## Testing
No automated tests. Manual: install mod in game, verify each setting; test configurator on Windows and Linux.

### Save/Load test procedure
1. Enable AutoSave + LoadOnStart in configurator
2. Play N rooms, note health/blessings/gold/room
3. Exit game
4. Re-launch, enter elevator
5. Check log for `[Save] Replay:` and `[Save] Restored` messages
6. Verify: correct room (not room 0), health preserved (pre-heal value), blessings present, gold correct

## Version Bumping
Update VERSION in **both** places:
- `configurator.py` line 47: `VERSION = "X.YY"`
- `version_info.txt`: `filevers` and `prodvers` tuples + `FileVersion`/`ProductVersion` strings
