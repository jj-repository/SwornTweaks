# SwornTweaks Installation Guide

## 1. Install MelonLoader (required first)

MelonLoader is the mod framework that loads SwornTweaks into SWORN. You need to install it before using any mods.

### Windows

1. Go to the [MelonLoader Releases](https://github.com/LavaGang/MelonLoader/releases) page
2. Download `MelonLoader.Installer.exe`
3. Run the installer:
   - Click **Select** and browse to your SWORN executable:
     `C:\Program Files (x86)\Steam\steamapps\common\SWORN\SWORN.exe`
     (or wherever Steam installed the game)
   - Make sure **Latest** version is selected
   - Click **Install**
4. Launch SWORN once — MelonLoader will set up its folders (`Mods/`, `UserData/`, etc.) on first run. The game may take longer to start the first time. You can close it after you see the main menu.

### Linux (Steam Proton)

MelonLoader works through Proton but requires a DLL override:

1. Download `MelonLoader.x64.zip` from the [MelonLoader Releases](https://github.com/LavaGang/MelonLoader/releases) page
2. Find your SWORN game folder:
   - Default: `~/.steam/steam/steamapps/common/SWORN/`
   - Custom library: check your Steam library path, e.g. `/mnt/<drive>/SteamLibrary/steamapps/common/SWORN/`
3. Extract the zip into the SWORN game folder — you should see a `MelonLoader/` folder and `version.dll` next to `SWORN.exe`
4. In Steam, right-click SWORN → **Properties** → **General** → **Launch Options** and add:
   ```
   WINEDLLOVERRIDES="version=n,b" %command%
   ```
5. Launch SWORN once to let MelonLoader create its folders (`Mods/`, `UserData/`). Close after the main menu appears.

---

## 2. Install SwornTweaks

1. Download `SwornTweaks.dll` from the [latest release](https://github.com/jj-repository/SwornTweaks/releases) or the repo root
2. Copy `SwornTweaks.dll` into your SWORN game's `Mods/` folder:
   - **Windows**: `C:\Program Files (x86)\Steam\steamapps\common\SWORN\Mods\`
   - **Linux**: `~/.steam/steam/steamapps/common/SWORN/Mods/` (or your custom Steam library path)
3. Launch the game — the config file is created automatically at `SWORN/UserData/MelonPreferences.cfg`

---

## 3. Configurator GUI (optional)

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
