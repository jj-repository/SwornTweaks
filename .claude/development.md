# Development

## Commands
```bash
# Build C# DLL (requires .NET 6.0 SDK + game references)
dotnet build -c Release

# Configurator
pip install -r requirements.txt  # PyQt6>=6.5, certifi
python configurator.py

# Build configurator exe
pyinstaller --onefile --windowed --name SwornTweaks configurator.py
```

## Dependencies
**C# mod:** .NET 6.0 x64, MelonLoader 0.7.1+, 0Harmony, Il2CppInterop.Runtime, Assembly-CSharp.dll (game stubs)
**Configurator:** PyQt6 >= 6.5, certifi (PyInstaller SSL)
**Game:** SWORN (Steam 1763250), MelonLoader, .NET 6 Desktop Runtime

## Testing
No automated tests. Manual: install mod in game, verify each setting; test configurator on Windows and Linux.
