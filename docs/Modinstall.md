# SWORN Mods

## Game Info
- **Game:** SWORN by Windwalk Games / Team17
- **Steam App ID:** 1763250
- **Platform:** Windows-only game, runs via Proton on Linux
- **Install path:** `/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/`

---

## Setup: MelonLoader (required for all mods)

MelonLoader is the mod loader that injects mods into the game at runtime.

### One-time install steps

1. **Install protontricks** (needed for .NET runtime in Proton prefix):
   ```
   paru -S protontricks
   ```

2. **Download MelonLoader** (Windows x64 zip — NOT the Linux zip, SWORN runs via Proton):
   ```
   gh release download v0.7.1 --repo LavaGang/MelonLoader -p "MelonLoader.x64.zip" -D /tmp/
   ```

3. **Extract into SWORN game folder:**
   ```
   unzip /tmp/MelonLoader.x64.zip -d /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/
   ```

4. **Install .NET 6 Desktop Runtime into the Proton prefix:**
   ```
   protontricks 1763250 dotnetdesktop6
   ```
   A Windows installer dialog will pop up — click through it.

5. **Set Steam launch option** (Steam → SWORN → Properties → Launch Options):
   ```
   WINEDLLOVERRIDES="version=n,b" gamemoderun %command%
   ```

6. **Launch SWORN once** and wait for the main menu, then close it. MelonLoader will generate the `Mods/` folder and the Il2Cpp assemblies on first boot.

### MelonLoader reference
- GitHub: https://github.com/LavaGang/MelonLoader
- Use `MelonLoader.x64.zip` (Windows) for Proton games, NOT `MelonLoader.Linux.x64.zip`

---

## Installing / Uninstalling Mods

- **Enable a mod:** Copy the `.dll` from `Mods_Disabled/` into the game's `Mods/` folder:
  ```
  cp /mnt/ext4gamedrive/modding/Sworn/Mods_Disabled/SomeMod.dll \
     /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods/
  ```

- **Disable a mod:** Move the `.dll` out of the game's `Mods/` folder:
  ```
  mv /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods/SomeMod.dll \
     /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods_Disabled/
  ```

- **Game mod folders:**
  - Enabled:  `/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods/`
  - Disabled: `/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods_Disabled/`

---

## Mods

### [Enabled] SwornRerollMod
- **File:** `Mods/SwornRerollMod.dll`
- **GitHub:** https://github.com/CxVercility/Sworn_RerollMod
- **Description:** Adds extra rerolls at the start of each run.
- **Custom change:** Value modified from the default **5** to **22** rerolls.
- **Built from source:** Yes (value edited in `Core.cs` before building)

---

### [Enabled] SwornRarityMod
- **File:** `Mods/SwornRarityMod.dll`
- **GitHub:** https://github.com/CxVercility/Sworn_RarityMod
- **Description:** Modifies blessing rarity distribution.
- **Built from source:** Yes, no changes from upstream

---

### [Enabled] SwornNoGemCost (DisableLancelotGemCost)
- **File:** `Mods/SwornNoGemCost.dll`
- **GitHub:** https://github.com/CxVercility/Sworn_DisableLancelotGemCost
- **Description:** Disables the gem cost for Lancelot abilities.
- **Note:** Built as `SwornMod2.dll`, renamed to `SwornNoGemCost.dll` for clarity.
- **Built from source:** Yes, no changes from upstream

---

### [Disabled] SwornNoCurrencyDoorRewards
- **File:** `Mods_Disabled/SwornNoCurrencyDoorRewards.dll`
- **GitHub:** https://github.com/CxVercility/Sworn_NoCurrencyDoorRewards
- **Description:** Replaces currency door rewards (FairyEmber, Silk, Moonstone) with Paragon or ParagonLevelUp rewards instead. CrystalShards are intentionally left untouched (used for HP regen passive). Gold is also not affected.
- **Built from source:** Yes, no changes from upstream

---

### [Enabled] SwornMoreRooms
- **File:** `Mods/SwornMoreRooms.dll`
- **Source:** `/mnt/ext4gamedrive/modding/Sworn/SwornMoreRooms/`
- **Description:** Extends each run with a repeated Kingswood biome (as biome 4, before Camelot/Arthur), adds a second legendary beast fight per biome, and boosts intensity on the repeated biome.
- **Run layout per biome (biomes 1–4, skipping Camelot/Somewhere):**
  - Room 3 (index 2): first beast fight (MajorEnemy — naturally vanilla, kept as-is)
  - Room 4 (index 3, 0-based): **forced** beast fight (MajorEnemy override)
  - Room 8 (index 7, 0-based): **forced** second beast fight (MajorEnemy override)
  - Last room (index 9): knight boss (MiniBoss — Gawain, Percival, etc., naturally vanilla)
  - Biome 4 = repeated Kingswood at 1.5× intensity before Arthur
- **Config:** Edit `UserData/MelonPreferences.cfg` in the SWORN game folder after first run:
  - `BeastRoom1 = 3` — 0-based index of first forced beast room (default 3 = 4th room)
  - `BeastRoom2 = 7` — 0-based index of second forced beast room (default 7 = 8th room)
  - `RepeatBiomeIntensity = 1.5` — intensity multiplier for the repeated Kingswood (1.0 = vanilla)
- **Build:**
  ```bash
  cd /mnt/ext4gamedrive/modding/Sworn/SwornMoreRooms
  dotnet build -c Release
  cp bin/Release/net6.0/SwornMoreRooms.dll \
     /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods/
  ```

---

## Rebuilding Mods from Source

All mods follow the same build process. The `.csproj` files have hardcoded Windows paths that need fixing for Linux builds:

```bash
# 1. Clone
gh repo clone CxVercility/REPO_NAME /tmp/mod_src

# 2. Fix Windows reference paths
sed \
  -e 's|C:\\Program Files (x86)\\Steam\\steamapps\\common\\SWORN\\MelonLoader\\Il2CppAssemblies\\|/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/MelonLoader/Il2CppAssemblies/|g' \
  -e 's|C:\\Program Files (x86)\\Steam\\steamapps\\common\\SWORN\\MelonLoader\\net6\\|/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/MelonLoader/net6/|g' \
  /tmp/mod_src/PROJECT/PROJECT.csproj > /tmp/mod_src/PROJECT/PROJECT.csproj.tmp \
  && mv /tmp/mod_src/PROJECT/PROJECT.csproj.tmp /tmp/mod_src/PROJECT/PROJECT.csproj

# 3. Remove the Windows PostBuild COPY step from the .csproj (edit manually or with sed)

# 4. Build
cd /tmp/mod_src/PROJECT && dotnet build -c Release

# 5. Copy output DLL to game Mods folder
cp /tmp/mod_src/PROJECT/bin/Release/net6.0/OUTPUT.dll \
   /mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/Mods/
```

> The Il2Cpp assemblies required for building are generated by MelonLoader on first game launch and live at:
> `/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/MelonLoader/Il2CppAssemblies/`
