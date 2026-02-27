# SwornTweaks Installation Guide

## Mod Installation (required)

1. Download `SwornTweaks.dll` from the [latest release](https://github.com/jj-repository/SwornTweaks/releases) or the repo root
2. Copy `SwornTweaks.dll` into your SWORN game's `Mods/` folder:
   - **Windows**: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\Mods\`
   - **Linux**: `~/.steam/steam/steamapps/common/SWORN/Mods/` (or your custom Steam library path)
3. Make sure [MelonLoader](https://melonwiki.xyz/) is installed for SWORN
4. Launch the game — the config file is created automatically at `SWORN/UserData/MelonPreferences.cfg`

**Linux (Proton)**: Add this to SWORN's Steam launch options:
```
WINEDLLOVERRIDES="version=n,b" %command%
```

---

## Configurator GUI Installation

The configurator is a visual editor for the mod's settings. It's optional — you can also edit `MelonPreferences.cfg` by hand.

---

### Windows

**Option A: Standalone .exe (no Python needed)**

1. Download `SwornTweaks-Configurator.exe` from the [latest release](https://github.com/jj-repository/SwornTweaks/releases)
2. Place it anywhere (Desktop, game folder, wherever you like)
3. Double-click to run

The app auto-detects your SWORN installation. If it can't find it, it will ask you to browse to the SWORN folder.

**Option B: Run from source**

1. Install [Python 3.10+](https://www.python.org/downloads/) (check "Add to PATH" during install)
2. Open a terminal (cmd or PowerShell) and run:
   ```
   pip install PyQt6
   ```
3. Download `configurator.py` from the repo
4. Run it:
   ```
   python configurator.py
   ```

---

### CachyOS / Arch Linux

PyQt6 is likely already installed. If not:

```bash
# Option 1: System package (recommended on Arch/CachyOS)
sudo pacman -S python-pyqt6

# Option 2: pip
pip install PyQt6
```

Then run:
```bash
python3 configurator.py
```

**Tip**: You can place `configurator.py` anywhere. It auto-detects your SWORN install by scanning common Steam library paths including `/mnt/*/SteamLibrary/`. The detected path is cached so it only asks once.

---

### Other Linux Distros

```bash
# Ubuntu/Debian
sudo apt install python3-pyqt6
# or
pip install PyQt6

# Fedora
sudo dnf install python3-qt6
# or
pip install PyQt6
```

Then: `python3 configurator.py`

---

## Building the Windows .exe Yourself

If you want to build the standalone Windows executable:

1. Install Python 3.10+ and PyQt6:
   ```
   pip install PyQt6 pyinstaller
   ```
2. Run:
   ```
   pyinstaller --onefile --windowed --name SwornTweaks-Configurator configurator.py
   ```
3. The `.exe` is in the `dist/` folder

---

## How It Works

- The configurator reads and writes `SWORN/UserData/MelonPreferences.cfg`
- The game path is auto-detected and cached in:
  - **Windows**: `%APPDATA%\SwornTweaks\configurator.json`
  - **Linux**: `~/.config/SwornTweaks/configurator.json`
- Click **Save** to write your changes
- Click **Reset Defaults** to restore all values to defaults
- Click **Update from GitHub** to download the latest `SwornTweaks.dll` directly into your Mods folder
