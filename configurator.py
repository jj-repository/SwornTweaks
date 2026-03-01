#!/usr/bin/env python3
"""SwornTweaks Configurator — lightweight PyQt6 GUI for editing MelonPreferences.cfg"""
from __future__ import annotations

import base64
import json
import os
import platform
import sys
import urllib.request
from configparser import ConfigParser
from io import StringIO
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap, QFont, QPen
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget,
)

VERSION = "1.7.0"
GITHUB_REPO = "jj-repository/SwornTweaks"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_DLL = f"{GITHUB_RAW}/SwornTweaks.dll"
GITHUB_CONFIGURATOR = f"{GITHUB_RAW}/configurator.py"
SECTION = "SwornTweaks"

# Vanilla game defaults — unmodded behavior (used by "Reset to Vanilla" button)
VANILLA_DEFAULTS = {
    "BonusRerolls": 0,
    "InfiniteRerolls": False,
    "LegendaryChance": 0.03,
    "EpicChance": 0.08,
    "RareChance": 0.20,
    "UncommonChance": 0.25,
    "NoGemCost": False,
    "RingOfDispelFree": False,
    "UnlimitedGold": False,
    "NoCurrencyDoorRewards": False,
    "DuoChance": 0.0,
    "ExtraBiomes": 0,
    "RandomizeRepeats": False,
    "AllBiomesRandom": False,
    "ProgressiveScaling": False,
    "ProgressiveScalingGrowth": 1.5,
    "UseVanillaBeastSettings": True,
    "SpawnBeastBosses": True,
    "ForceBiomeBoss": False,
    "FixedExtraBosses": 0,
    "BeastChancePercent": 0.0,
    "MaxBeastsPerBiome": 5,
    "PlayerHealthMultiplier": 1.0,
    "PlayerDamageMultiplier": 1.0,
    "InfiniteMana": False,
    "Invincible": False,
    "BossHealthMultiplier": 1.0,
    "BossDamageMultiplier": 1.0,
    "BeastHealthMultiplier": 1.0,
    "BeastDamageMultiplier": 1.0,
    "IntensityMultiplier": 1.0,
    "EnemyHealthMultiplier": 1.0,
    "EnemyDamageMultiplier": 1.0,
    "GuaranteedFaeKiss": False,
    "GuaranteedFaeKissCurse": False,
    "GuaranteedSwordsBiomes": 0,
    "SkipSomewhere": False,
    "BossRushMode": False,
    "BossRushHornRewards": 1,
    "BossRushHealPerRoom": 15,
    "BossRushScaling": 1.25,
    "BossRushRandomizer": False,
    "BossRushRandomizeArthur": False,
    "BossRushRandomizeRoundTable": False,
    "BossRushExtraBlessings": 0,
    "ExtraBlessings": 0,
    "FightBossMode": False,
    "FightBossSelection": "Gawain",
    "FightBossRepeat": 1,
    "FightBossDamageMultiplier": 1.0,
    "FightBossHealth": 0,
}

_DECIMAL_PCT_KEYS = {"LegendaryChance", "EpicChance", "RareChance", "UncommonChance", "DuoChance"}

_FIGHT_BOSS_LIST = [
    ("Questing Beast", "QuestingBeast"),
    ("Sir Canis", "SirCanis"),
    ("Bedivere", "Bedivere"),
    ("Sirens", "Sirens"),
    ("Gawain", "Gawain"),
    ("Lady Kay", "LadyKay"),
    ("Arthur", "Arthur"),
    ("Arthur Dragon", "ArthurDragon"),
    ("Morgana", "Morgana"),
]

# Default boss HP on Squire difficulty
_BOSS_DEFAULT_HP = {
    "QuestingBeast": 3000,
    "SirCanis": 2000,
    "Bedivere": 10000,
    "Sirens": 7000,
    "Gawain": 6000,
    "LadyKay": 8000,
    "Arthur": 18000,
    "ArthurDragon": 22000,
    "Morgana": 20000,
}

# Embedded mascot image (base64-encoded JPEG, 250x250)
_MASCOT_B64 = (
    "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"
)


def make_icon() -> QIcon:
    """Create a simple app icon programmatically."""
    size = 128
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background circle — dark blue-gray
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(35, 45, 65))
    p.drawEllipse(4, 4, size - 8, size - 8)

    # Border ring — gold accent
    pen = QPen(QColor(218, 165, 32))
    pen.setWidth(3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(6, 6, size - 12, size - 12)

    # "ST" text
    p.setPen(QColor(218, 165, 32))
    font = QFont("Arial", 42, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "ST")

    p.end()
    return QIcon(pix)


def find_game_path() -> Path | None:
    """Auto-detect SWORN install directory."""
    candidates: list[str] = []
    if platform.system() == "Windows":
        for drive in "CDEFGH":
            candidates.append(rf"{drive}:\Program Files (x86)\Steam\steamapps\common\SWORN")
            candidates.append(rf"{drive}:\SteamLibrary\steamapps\common\SWORN")
            candidates.append(rf"{drive}:\Games\SteamLibrary\steamapps\common\SWORN")
            candidates.append(rf"{drive}:\Games\Steam\steamapps\common\SWORN")
    else:
        home = os.path.expanduser("~")
        candidates.append(f"{home}/.steam/steam/steamapps/common/SWORN")
        candidates.append(f"{home}/.local/share/Steam/steamapps/common/SWORN")
        for mount in ("/mnt", "/media", "/run/media"):
            if os.path.isdir(mount):
                try:
                    for entry in os.listdir(mount):
                        base = os.path.join(mount, entry)
                        candidates.append(f"{base}/SteamLibrary/steamapps/common/SWORN")
                        candidates.append(f"{base}/steamapps/common/SWORN")
                except PermissionError:
                    pass
    for c in candidates:
        if os.path.isdir(c):
            return Path(c)
    return None


def settings_path() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "SwornTweaks" / "configurator.json"


def _load_settings() -> dict:
    sp = settings_path()
    if sp.exists():
        try:
            return json.loads(sp.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _save_settings(data: dict):
    sp = settings_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(data))


def load_game_path() -> Path | None:
    data = _load_settings()
    gp = data.get("game_path")
    if gp:
        p = Path(gp)
        if p.is_dir():
            return p
    return None


def save_game_path(path: Path):
    data = _load_settings()
    data["game_path"] = str(path)
    _save_settings(data)


class DownloadWorker(QThread):
    """Background thread for downloading files from GitHub."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url: str, dest: Path):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            self.dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.dest.with_suffix(self.dest.suffix + ".tmp")
            urllib.request.urlretrieve(self.url, str(tmp))
            # On Windows, you can't overwrite a running exe, but you CAN
            # rename it. Move the old file aside, put the new one in place.
            # Use a unique .old name to avoid conflicts with locked files
            # from previous updates (WinError 5).
            import time
            old = self.dest.with_suffix(f".old{int(time.time())}")
            if self.dest.exists():
                self.dest.rename(old)
            tmp.rename(self.dest)
            # Best-effort cleanup of .old files — don't fail if locked
            for stale in self.dest.parent.glob(self.dest.stem + ".old*"):
                try:
                    stale.unlink()
                except OSError:
                    pass  # locked by OS — will be cleaned up next time
            self.finished.emit(str(self.dest))
        except Exception as e:
            self.error.emit(str(e))


class UpdateChecker(QThread):
    """Background thread to check GitHub for a newer version."""
    update_available = pyqtSignal(str)  # emits the remote version string

    def run(self):
        try:
            import re
            req = urllib.request.Request(GITHUB_CONFIGURATOR, headers={"User-Agent": "SwornTweaks"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                # Only read first 2KB — VERSION is near the top
                head = resp.read(2048).decode("utf-8", errors="ignore")
            m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', head)
            if m:
                remote = m.group(1)
                if remote != VERSION:
                    self.update_available.emit(remote)
        except Exception:
            pass  # silently ignore — don't pester the user if offline


class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SwornTweaks Configurator v{VERSION}")
        self.setWindowIcon(make_icon())
        self.resize(540, 740)
        self.widgets: dict[str, QWidget] = {}
        self._workers: list[DownloadWorker] = []

        # Resolve game path
        self.game_path = load_game_path() or find_game_path()
        if self.game_path is None:
            self.game_path = self._ask_game_path()
        if self.game_path:
            save_game_path(self.game_path)

        central = QWidget()
        outer = QVBoxLayout(central)

        # ── Build all groups ────────────────────────────────────────

        # Blessings groups
        self._rerolls_group = self._group("Rerolls", [
            self._int_row("BonusRerolls", "Rerolls", 0, 9999),
            self._bool_row("InfiniteRerolls", "Infinite Rerolls"),
        ], "Bonus blessing rerolls per room.\nInfinite gives unlimited rerolls.")

        self._rarity_group = self._group("Blessing Rarity", [
            self._pct_row("LegendaryChance", "Legendary Chance", 0, 100),
            self._pct_row("EpicChance", "Epic Chance", 0, 100),
            self._pct_row("RareChance", "Rare Chance", 0, 100),
            self._pct_row("UncommonChance", "Uncommon Chance", 0, 100),
            self._pct_row("DuoChance", "Duo Chance", 0, 100),
        ], "Adjust the chance of each blessing rarity.\nValues are percentages.")

        self._extra_blessings_group = self._group("Extra Blessings", [
            self._int_row("ExtraBlessings", "Extra Blessings per Room", 0, 3),
            self._label_row("Additional blessing rewards after each room."),
        ], "Grant extra blessing choices after every room.")

        # Toggles groups
        self._toggles_group = self._group("General", [
            self._bool_row("NoGemCost", "No Gem Cost (Lancelot)"),
            self._bool_row("RingOfDispelFree", "Ring of Dispel Free"),
            self._label_row("Unlocks Ring of Dispel without buying gems."),
            self._bool_row("UnlimitedGold", "Unlimited Gold"),
            self._bool_row("NoCurrencyDoorRewards", "No Currency Door Rewards"),
            self._label_row("Except gold and shards."),
        ], "General gameplay toggles.\nRing of Dispel Free auto-disables No Gem Cost.")

        self._skip_group = self._group("Skip to Morgana", [
            self._bool_row("SkipSomewhere", "Skip from Arthur to Morgana"),
            self._label_row("Skips the Somewhere level pre-Morgana."),
        ], "Skip the Somewhere transition level.")

        self._fae_group = self._group("Guaranteed Fae Realms", [
            self._bool_row("GuaranteedFaeKiss", "Guaranteed Kiss Portal"),
            self._bool_row("GuaranteedFaeKissCurse", "Guaranteed Kiss Curse Portal"),
        ], "Force Fae Realm portals to always appear.")

        sword_row = QHBoxLayout()
        self._sword_cb = QCheckBox("Guaranteed Swords")
        self._sword_cb.stateChanged.connect(self._update_sword_enables)
        sword_row.addWidget(self._sword_cb)
        self._sword_group = self._group("Guaranteed Sword in the Stone", [
            sword_row,
            self._int_row("GuaranteedSwordsBiomes", "Total Swords in the Stone", 0, 4),
        ], "Force a Sword in the Stone reward once per biome.\n"
           "0 = disabled (vanilla chance), 1-3 = that many combat biomes,\n"
           "4 = all combat biomes + after Arthur in Camelot.\n"
           "Somewhere never spawns a Sword in the Stone.")

        self.widgets["RingOfDispelFree"].stateChanged.connect(self._on_dispel_toggled)

        # Player group
        self._player_group = self._group("Player Scaling", [
            self._float_row("PlayerHealthMultiplier", "Player Health", 0.1, 50.0, "x"),
            self._float_row("PlayerDamageMultiplier", "Player Damage", 0.1, 50.0, "x"),
            self._bool_row("InfiniteMana", "Infinite Mana"),
            self._bool_row("Invincible", "Invincible"),
        ], "Scale player health/damage.\nInfinite Mana and Invincible are cheat toggles.")

        # Enemies groups
        self._boss_scaling_group = self._group("Boss Scaling", [
            self._float_row("BossHealthMultiplier", "Boss Health", 0.1, 50.0, "x"),
            self._float_row("BossDamageMultiplier", "Boss Damage", 0.1, 50.0, "x"),
            self._float_row("BeastHealthMultiplier", "Beast Health", 0.1, 50.0, "x"),
            self._float_row("BeastDamageMultiplier", "Beast Damage", 0.1, 50.0, "x"),
        ], "Scale boss and beast health/damage multipliers.")

        self._enemy_scaling_group = self._group("Enemy Scaling", [
            self._float_row("EnemyHealthMultiplier", "Enemy Health", 0.1, 50.0, "x"),
            self._float_row("EnemyDamageMultiplier", "Enemy Damage", 0.1, 50.0, "x"),
            self._label_row("Affects normal enemies only.\nBoss/beast health has its own multipliers."),
        ], "Scale normal enemy health/damage.\nDoes not affect bosses or beasts.")

        self._intensity_group = self._group("Spawn Intensity", [
            self._float_row("IntensityMultiplier", "Enemy Spawn Rate", 0.1, 10.0, "x"),
            self._label_row("Scales enemy spawn count per room."),
        ], "Multiply the number of enemies that spawn per room.")

        # Extra Boss Rooms — enable checkbox + sub-controls wrapped for show/hide
        enable_boss_row = QHBoxLayout()
        self._enable_bosses_cb = QCheckBox("Enable Extra Boss Rooms")
        enable_boss_row.addWidget(self._enable_bosses_cb)

        self._beast_details = QWidget()
        bd_lay = QVBoxLayout(self._beast_details)
        bd_lay.setContentsMargins(0, 0, 0, 0)
        bd_lay.addLayout(self._bool_row("SpawnBeastBosses", "Spawn Beast Bosses"))
        bd_lay.addWidget(self._label_row("Include legendary beasts in extra boss room pool."))
        bd_lay.addLayout(self._bool_row("ForceBiomeBoss", "Also Spawn Main Bosses"))
        bd_lay.addWidget(self._label_row("Also include biome end bosses in the pool."))

        # Fixed Extra Bosses: enable checkbox + spinbox
        fixed_row = QHBoxLayout()
        self._fixed_bosses_cb = QCheckBox("Fixed Extra Bosses")
        fixed_row.addWidget(self._fixed_bosses_cb)
        fixed_row.addStretch()
        fixed_spin = QSpinBox()
        fixed_spin.setRange(1, 3)
        fixed_spin.setFixedWidth(90)
        self.widgets["FixedExtraBosses"] = fixed_spin
        fixed_row.addWidget(fixed_spin)
        bd_lay.addLayout(fixed_row)
        bd_lay.addWidget(self._label_row("Guaranteed extra boss rooms per biome.\n"
                            "Placed randomly, avoiding first 3 and last 2 rooms."))

        # Random chance: enable checkbox + spinbox on same row
        random_row = QHBoxLayout()
        self._random_cb = QCheckBox("Random Chance")
        random_row.addWidget(self._random_cb)
        random_row.addStretch()
        beast_chance_spin = QDoubleSpinBox()
        beast_chance_spin.setRange(0, 100)
        beast_chance_spin.setDecimals(1)
        beast_chance_spin.setSingleStep(1.0)
        beast_chance_spin.setSuffix(" %")
        beast_chance_spin.setFixedWidth(100)
        self.widgets["BeastChancePercent"] = beast_chance_spin
        random_row.addWidget(beast_chance_spin)
        bd_lay.addLayout(random_row)

        bd_lay.addLayout(self._int_row("MaxBeastsPerBiome", "Max per Biome", 0, 15))
        bd_lay.addWidget(self._label_row("Max random beasts per biome (excludes fixed)."))
        self._beast_details.setVisible(False)

        self._extra_boss_group = self._group("Extra Bosses", [enable_boss_row, self._beast_details],
            "Add extra beast/boss encounters per biome.\n"
            "Enable to customize boss room settings.\n"
            "Fixed bosses guaranteed; random chance rolls per room.")

        self._random_cb.stateChanged.connect(lambda _: self._update_beast_enables())
        self._fixed_bosses_cb.stateChanged.connect(lambda _: self._update_beast_enables())

        # Fight a Specific Boss — enable checkbox + sub-controls wrapped for show/hide
        fight_boss_row = QHBoxLayout()
        self._fight_boss_cb = QCheckBox("Fight Boss")
        fight_boss_row.addWidget(self._fight_boss_cb)

        self._fight_boss_details = QWidget()
        fb_lay = QVBoxLayout(self._fight_boss_details)
        fb_lay.setContentsMargins(0, 0, 0, 0)

        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("Select Boss"))
        combo_row.addStretch()
        self._fight_boss_combo = QComboBox()
        self._fight_boss_combo.setFixedWidth(160)
        for display, data in _FIGHT_BOSS_LIST:
            self._fight_boss_combo.addItem(display, data)
        combo_row.addWidget(self._fight_boss_combo)
        fb_lay.addLayout(combo_row)

        fb_lay.addLayout(self._int_row("FightBossRepeat", "Repeat Fight", 1, 5))
        fb_lay.addLayout(self._float_row("FightBossDamageMultiplier", "Boss Damage", 0.1, 10.0, "x"))
        fb_lay.addLayout(self._int_row("FightBossHealth", "Boss Health", 0, 999999))
        self._fight_boss_hp_hint = QLabel()
        self._fight_boss_hp_hint.setStyleSheet("color: gray; font-size: 11px;")
        self._fight_boss_hp_hint.setWordWrap(True)
        fb_lay.addWidget(self._fight_boss_hp_hint)
        self._fight_boss_combo.currentIndexChanged.connect(lambda _: self._update_boss_hp_hint())
        self._update_boss_hp_hint()
        self._fight_boss_details.setVisible(False)

        self._fight_boss_group = self._group("Fight a Specific Boss", [fight_boss_row, self._fight_boss_details],
            "Force-load a specific boss as room 0.\n"
            "Optionally repeat the fight and set custom stats.\n"
            "Disables Enemies tab scaling when active.")

        self._fight_boss_cb.stateChanged.connect(lambda _: self._update_fight_boss_enables())

        # Game Modes groups
        extra_row = QHBoxLayout()
        self._extra_cb = QCheckBox("Extra Biomes")
        extra_row.addWidget(self._extra_cb)
        extra_row.addStretch()
        extra_spin = QSpinBox()
        extra_spin.setRange(1, 3)
        extra_spin.setFixedWidth(90)
        self.widgets["ExtraBiomes"] = extra_spin
        extra_row.addWidget(extra_spin)

        run_rows = [extra_row]
        run_rows.append(self._label_row("1 Biome \u2248 12 Rooms"))
        run_rows.append(self._label_row("Adds more biomes before camelot.\n"
                            "In order if not randomized."))
        run_rows.append(self._bool_row("RandomizeRepeats", "Randomize Repeated Biomes Order"))
        run_rows.append(self._bool_row("AllBiomesRandom", "All Biomes Random Order"))
        run_rows.append(self._label_row("Randomizes all 3 combat biome slots\n"
                            "plus extras. Camelot/Somewhere stay last."))
        run_rows.append(self._bool_row("ProgressiveScaling", "Progressive HP Scaling"))
        growth_row = self._float_row("ProgressiveScalingGrowth", "HP Scaling Growth", 1.0, 3.0, "x")
        self._growth_label = growth_row.itemAt(0).widget()
        run_rows.append(growth_row)
        run_rows.append(self._label_row("Scales difficulty for extra or random biomes.\n"
                            "1.0 = no scaling."))
        self._run_length_group = self._group("More Biomes/Rooms", run_rows,
            "Add extra combat biomes before Camelot.\n"
            "Randomize biome order for variety.\n"
            "Progressive scaling adjusts difficulty.")

        self._extra_cb.stateChanged.connect(lambda _: self._update_extra_enables())
        self.widgets["AllBiomesRandom"].stateChanged.connect(lambda _: self._update_extra_enables())
        self.widgets["ProgressiveScaling"].stateChanged.connect(lambda _: self._update_extra_enables())

        # Boss Rush — enable row with status label, sub-controls wrapped for show/hide
        rush_top = QHBoxLayout()
        rush_cb = QCheckBox("Enable Boss Rush")
        self.widgets["BossRushMode"] = rush_cb
        rush_top.addWidget(rush_cb)
        rush_top.addStretch()
        self._rush_status = QLabel("Deactivated")
        self._rush_status.setStyleSheet("color: #c62828; font-weight: bold;")
        rush_top.addWidget(self._rush_status)
        rush_top.addStretch()

        self._rush_details = QWidget()
        rd_lay = QVBoxLayout(self._rush_details)
        rd_lay.setContentsMargins(0, 0, 0, 0)
        rd_lay.addLayout(self._bool_row("BossRushRandomizer", "Randomize all boss/beast order"))
        # Sub-toggles for randomizer — only visible when randomizer is checked
        self._rush_rand_details = QWidget()
        rrd_lay = QVBoxLayout(self._rush_rand_details)
        rrd_lay.setContentsMargins(20, 0, 0, 0)
        rrd_lay.addLayout(self._bool_row("BossRushRandomizeArthur", "Randomize Arthur Spawn"))
        rrd_lay.addLayout(self._bool_row("BossRushRandomizeRoundTable", "Randomize RoundTable Spawn"))
        self._rush_rand_details.setVisible(False)
        rd_lay.addWidget(self._rush_rand_details)
        rd_lay.addLayout(self._int_row("BossRushHornRewards", "Extra Horns per Room", 0, 3))
        rd_lay.addLayout(self._int_row("BossRushExtraBlessings", "Extra Blessings per Room", 0, 3))
        rd_lay.addLayout(self._int_row("BossRushHealPerRoom", "Player HP Heal per Room", 0, 100))
        rd_lay.addLayout(self._float_row("BossRushScaling", "Boss HP Scaling per Room", 1.0, 3.0, "x"))
        self._boss_rush_group = self._group("Boss Rush Mode", [rush_top, self._rush_details],
            "Fight all bosses and beasts back-to-back.\n"
            "Disables most other settings when active.\n"
            "Randomizer shuffles encounters across biomes.")

        self.widgets["BossRushMode"].stateChanged.connect(lambda _: self._update_rush_enables())
        self.widgets["BossRushRandomizer"].stateChanged.connect(
            lambda _: self._rush_rand_details.setVisible(self.widgets["BossRushRandomizer"].isChecked()))

        # ── Assemble tabs ───────────────────────────────────────────

        self._tabs = QTabWidget()

        def _scroll_tab(page: QWidget) -> QScrollArea:
            sa = QScrollArea()
            sa.setWidget(page)
            sa.setWidgetResizable(True)
            sa.setFrameShape(QScrollArea.Shape.NoFrame)
            return sa

        player_page = QWidget()
        play = QVBoxLayout(player_page)
        play.addWidget(self._player_group)
        play.addWidget(self._rerolls_group)
        play.addWidget(self._rarity_group)
        play.addWidget(self._extra_blessings_group)
        play.addStretch()
        self._tabs.addTab(_scroll_tab(player_page), "Player")

        enemies_page = QWidget()
        elay = QVBoxLayout(enemies_page)
        elay.addWidget(self._boss_scaling_group)
        elay.addWidget(self._enemy_scaling_group)
        elay.addWidget(self._intensity_group)
        elay.addStretch()
        self._tabs.addTab(_scroll_tab(enemies_page), "Enemies")

        toggles_page = QWidget()
        tlay = QVBoxLayout(toggles_page)
        tlay.addWidget(self._toggles_group)
        tlay.addWidget(self._skip_group)
        tlay.addWidget(self._fae_group)
        tlay.addWidget(self._sword_group)
        tlay.addStretch()
        self._tabs.addTab(_scroll_tab(toggles_page), "Toggles")

        modes_page = QWidget()
        mlay = QVBoxLayout(modes_page)
        mlay.addWidget(self._boss_rush_group)
        mlay.addWidget(self._run_length_group)
        mlay.addWidget(self._extra_boss_group)
        mlay.addWidget(self._fight_boss_group)
        mlay.addStretch()
        self._tabs.addTab(_scroll_tab(modes_page), "Game Modes")

        settings_page = QWidget()
        slay = QVBoxLayout(settings_page)
        version_label = QLabel(f"SwornTweaks Configurator v{VERSION}")
        version_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        slay.addWidget(version_label)
        slay.addSpacing(4)
        if self.cfg_path:
            cfg_label = QLabel(f"Config: {self.cfg_path}")
            cfg_label.setStyleSheet("color: gray; font-size: 11px;")
            cfg_label.setWordWrap(True)
            slay.addWidget(cfg_label)
        if self.game_path:
            game_label = QLabel(f"Game: {self.game_path}")
            game_label.setStyleSheet("color: gray; font-size: 11px;")
            game_label.setWordWrap(True)
            slay.addWidget(game_label)
        gh_label = QLabel(f'GitHub &amp; Install Instructions: <a href="https://github.com/{GITHUB_REPO}/blob/main/INSTALL.md">'
                          f'github.com/{GITHUB_REPO}</a>')
        gh_label.setStyleSheet("color: gray; font-size: 11px;")
        gh_label.setOpenExternalLinks(True)
        slay.addWidget(gh_label)
        slay.addSpacing(12)
        update_btn = QPushButton("Update Mod from GitHub")
        update_btn.setToolTip("Download latest DLL and configurator from GitHub")
        update_btn.clicked.connect(self._update_from_github)
        slay.addWidget(update_btn)
        s_reset_btn = QPushButton("Reset to Vanilla Config")
        s_reset_btn.clicked.connect(self._reset_defaults)
        slay.addWidget(s_reset_btn)
        s_share_btn = QPushButton("Share Config Code")
        s_share_btn.setToolTip("Copy current settings as a shareable code to clipboard")
        s_share_btn.clicked.connect(self._copy_code)
        slay.addWidget(s_share_btn)
        s_import_btn = QPushButton("Import Config Code")
        s_import_btn.setToolTip("Load settings from a code string in your clipboard")
        s_import_btn.clicked.connect(self._paste_code)
        slay.addWidget(s_import_btn)
        s_export_cfg_btn = QPushButton("Export Config .cfg")
        s_export_cfg_btn.setToolTip("Save a copy of the config file to a chosen location")
        s_export_cfg_btn.clicked.connect(self._export_cfg)
        slay.addWidget(s_export_cfg_btn)
        s_import_cfg_btn = QPushButton("Import Config .cfg")
        s_import_cfg_btn.setToolTip("Load settings from an external .cfg file")
        s_import_cfg_btn.clicked.connect(self._import_cfg)
        slay.addWidget(s_import_cfg_btn)
        slay.addSpacing(12)
        open_mods_btn = QPushButton("Open Mods Folder")
        open_mods_btn.setToolTip("Open the Mods folder in your file manager")
        open_mods_btn.clicked.connect(self._open_mod_folder)
        slay.addWidget(open_mods_btn)
        open_game_btn = QPushButton("Open Game Folder")
        open_game_btn.setToolTip("Open the SWORN game folder in your file manager")
        open_game_btn.clicked.connect(self._open_game_folder)
        slay.addWidget(open_game_btn)
        open_cfg_btn = QPushButton("Open Config Folder")
        open_cfg_btn.setToolTip("Open the folder containing MelonPreferences.cfg")
        open_cfg_btn.clicked.connect(self._open_config_folder)
        slay.addWidget(open_cfg_btn)
        slay.addSpacing(12)
        self._auto_update_cb = QCheckBox("Check for updates on startup")
        self._auto_update_cb.setChecked(_load_settings().get("auto_update_check", True))
        self._auto_update_cb.stateChanged.connect(self._on_auto_update_toggled)
        slay.addWidget(self._auto_update_cb)
        slay.addSpacing(8)
        mascot_data = base64.b64decode(_MASCOT_B64)
        mascot_pix = QPixmap()
        mascot_pix.loadFromData(mascot_data)
        mascot_pix = mascot_pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        mascot_label = QLabel()
        mascot_label.setPixmap(mascot_pix)
        mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slay.addWidget(mascot_label)
        slay.addStretch()
        self._tabs.addTab(_scroll_tab(settings_page), "Settings")

        # Help button as corner widget on the tab bar
        help_corner = QPushButton("Help")
        help_corner.setStyleSheet(
            "QPushButton { background-color: #c62828; color: white; font-weight: bold; padding: 4px 12px; }"
            "QPushButton:hover { background-color: #d32f2f; }"
        )
        help_corner.clicked.connect(self._open_help)
        self._tabs.setCornerWidget(help_corner, Qt.Corner.TopRightCorner)

        outer.addWidget(self._tabs)

        # ── Bottom bar ──────────────────────────────────────────────

        bottom = QHBoxLayout()
        copyright_label = QLabel("\u00a9 JJ")
        copyright_label.setStyleSheet("color: gray;")
        bottom.addWidget(copyright_label)
        bottom.addStretch()

        save_btn = QPushButton("Save Config")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("QPushButton { background-color: #2e7d32; color: white; font-weight: bold; }"
                               "QPushButton:hover { background-color: #388e3c; }")
        save_btn.clicked.connect(self._save)
        bottom.addWidget(save_btn)

        start_btn = QPushButton("Start Game")
        start_btn.setToolTip("Launch SWORN via Steam")
        start_btn.setStyleSheet("QPushButton { background-color: #1565c0; color: white; font-weight: bold; }"
                                "QPushButton:hover { background-color: #1976d2; }")
        start_btn.clicked.connect(self._start_game)
        bottom.addWidget(start_btn)

        outer.addLayout(bottom)
        self.setCentralWidget(central)
        self._load()

        # Wire up the enable extra bosses checkbox to show/hide beast fields
        self._enable_bosses_cb.stateChanged.connect(self._on_vanilla_beast_toggled)
        self._on_vanilla_beast_toggled(None)
        self._on_dispel_toggled(None)

        # Auto-check for updates on startup (if enabled)
        if self._auto_update_cb.isChecked():
            self._update_checker = UpdateChecker()
            self._update_checker.update_available.connect(self._on_update_available)
            self._update_checker.start()

    def _on_auto_update_toggled(self, _state):
        """Persist the auto-update-check preference."""
        data = _load_settings()
        data["auto_update_check"] = self._auto_update_cb.isChecked()
        _save_settings(data)

    def _on_update_available(self, remote_version: str):
        """Show update prompt when a newer version is found on GitHub."""
        reply = QMessageBox.question(
            self, "Update Available",
            f"A new version of SwornTweaks is available!\n\n"
            f"Current: v{VERSION}\n"
            f"Latest:  v{remote_version}\n\n"
            "Would you like to update now?\n"
            "(Downloads the latest DLL and configurator from GitHub)",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._update_from_github()

    # ── Game path ────────────────────────────────────────────────

    def _ask_game_path(self) -> Path | None:
        QMessageBox.information(
            None, "SWORN Not Found",
            "Could not auto-detect your SWORN installation.\n"
            "Please select the SWORN game folder."
        )
        d = QFileDialog.getExistingDirectory(None, "Select SWORN Game Folder")
        return Path(d) if d else None

    @property
    def cfg_path(self) -> Path | None:
        if self.game_path:
            return self.game_path / "UserData" / "MelonPreferences.cfg"
        return None

    @property
    def mods_path(self) -> Path | None:
        if self.game_path:
            return self.game_path / "Mods"
        return None

    # ── Widget builders ──────────────────────────────────────────

    def _group(self, title: str, rows: list, tooltip: str = "") -> QGroupBox:
        box = QGroupBox(title)
        vbox = QVBoxLayout()
        for row in rows:
            if isinstance(row, QHBoxLayout):
                vbox.addLayout(row)
            elif isinstance(row, QWidget):
                vbox.addWidget(row)
        box.setLayout(vbox)
        if tooltip:
            self._add_help_button(box, tooltip)
        return box

    def _int_row(self, key: str, label: str, lo: int, hi: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        spin = QSpinBox()
        spin.setRange(lo, hi)
        spin.setFixedWidth(90)
        self.widgets[key] = spin
        row.addWidget(spin)
        return row

    def _float_row(self, key: str, label: str, lo: float, hi: float, suffix: str = "") -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(2)
        spin.setSingleStep(0.1)
        spin.setFixedWidth(90)
        if suffix:
            spin.setSuffix(f" {suffix}")
        self.widgets[key] = spin
        row.addWidget(spin)
        return row

    def _pct_row(self, key: str, label: str, lo: float, hi: float) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(1)
        spin.setSingleStep(1.0)
        spin.setSuffix(" %")
        spin.setFixedWidth(100)
        self.widgets[key] = spin
        row.addWidget(spin)
        return row

    def _bool_row(self, key: str, label: str) -> QHBoxLayout:
        row = QHBoxLayout()
        cb = QCheckBox(label)
        self.widgets[key] = cb
        row.addWidget(cb)
        row.addStretch()
        return row

    def _label_row(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: gray; font-size: 11px;")
        lbl.setWordWrap(True)
        return lbl

    # ── Help buttons ────────────────────────────────────────────

    def _add_help_button(self, group: QGroupBox, tooltip: str):
        # Append a small "?" indicator to the group title with the tooltip
        title = group.title()
        group.setTitle(f"{title}  \u24d8")
        group.setToolTip(tooltip)

    # ── Beast vanilla toggle ────────────────────────────────────

    def _on_dispel_toggled(self, _state):
        """Disable No Gem Cost when Ring of Dispel Free is checked (gems are irrelevant)."""
        dispel = self.widgets["RingOfDispelFree"].isChecked()
        self.widgets["NoGemCost"].setEnabled(not dispel)

    def _on_vanilla_beast_toggled(self, _state):
        """Show/hide beast sub-controls based on Enable Extra Boss Rooms checkbox."""
        enabled = self._enable_bosses_cb.isChecked()
        self._beast_details.setVisible(enabled)
        if enabled:
            self._update_beast_enables()

    def _update_extra_enables(self):
        """Update enable states for run length controls."""
        extra = self._extra_cb.isChecked()
        all_random = self.widgets["AllBiomesRandom"].isChecked()
        self.widgets["ExtraBiomes"].setEnabled(extra)
        self.widgets["RandomizeRepeats"].setEnabled(extra)
        # All Biomes Random forces progressive scaling on (can't play random without HP correction)
        if all_random:
            self.widgets["ProgressiveScaling"].setChecked(True)
            self.widgets["ProgressiveScaling"].setEnabled(False)
        else:
            self.widgets["ProgressiveScaling"].setEnabled(extra)
        prog_on = self.widgets["ProgressiveScaling"].isChecked()
        growth_enabled = (extra or all_random) and prog_on
        self.widgets["ProgressiveScalingGrowth"].setEnabled(growth_enabled)
        self._growth_label.setEnabled(growth_enabled)

    def _update_rush_enables(self):
        """Update visibility for boss rush controls and section lockout."""
        rush = self.widgets["BossRushMode"].isChecked()
        self._rush_details.setVisible(rush)
        # Status label
        if rush:
            self._rush_status.setText("Activated")
            self._rush_status.setStyleSheet("color: #2e7d32; font-weight: bold;")
        else:
            self._rush_status.setText("Deactivated")
            self._rush_status.setStyleSheet("color: #c62828; font-weight: bold;")
        # Section lockout: disable incompatible groups when boss rush is active
        for grp in (self._toggles_group, self._skip_group, self._intensity_group,
                     self._fae_group, self._sword_group):
            grp.setEnabled(not rush)
        # Hide run length and extra bosses entirely when rush is on
        self._run_length_group.setVisible(not rush)
        self._extra_boss_group.setVisible(not rush)
        self._fight_boss_group.setEnabled(not rush)
        # Re-apply sub-control states when rush is turned off
        if not rush:
            self._on_vanilla_beast_toggled(None)
            self._on_dispel_toggled(None)
            self._update_beast_enables()
            self._update_extra_enables()

    def _update_boss_hp_hint(self):
        """Update the HP hint label based on selected boss."""
        boss = self._fight_boss_combo.currentData()
        hp = _BOSS_DEFAULT_HP.get(boss, 0)
        self._fight_boss_hp_hint.setText(f"0 = use default boss health (default: {hp:,} on Squire difficulty)")

    def _update_fight_boss_enables(self):
        """Show/hide fight boss details and lock all non-Player sections when active."""
        active = self._fight_boss_cb.isChecked()
        self._fight_boss_details.setVisible(active)
        # When fight boss is active, disable Enemies tab, Toggles tab, and all
        # Game Modes groups except Fight Boss itself
        self._tabs.setTabEnabled(1, not active)  # Enemies
        self._tabs.setTabEnabled(2, not active)  # Toggles
        self._boss_rush_group.setEnabled(not active)
        self._run_length_group.setEnabled(not active)
        self._extra_boss_group.setEnabled(not active)
        # When turning off, re-apply rush state (rush may have had its own lockout)
        if not active:
            self._update_rush_enables()

    def _update_sword_enables(self):
        """Enable/disable sword biome spinner based on checkbox."""
        on = self._sword_cb.isChecked()
        self.widgets["GuaranteedSwordsBiomes"].setEnabled(on)

    def _update_beast_enables(self):
        """Update spinbox enable states based on enable toggle + individual checkboxes."""
        random_on = self._random_cb.isChecked()
        self.widgets["BeastChancePercent"].setEnabled(random_on)
        self.widgets["MaxBeastsPerBiome"].setEnabled(random_on)
        self.widgets["FixedExtraBosses"].setEnabled(self._fixed_bosses_cb.isChecked())

    # ── Percentage helpers ───────────────────────────────────────

    def _cfg_to_display(self, key: str, value: float) -> float:
        if key in _DECIMAL_PCT_KEYS:
            return value * 100.0
        return value

    def _display_to_cfg(self, key: str, value: float) -> float:
        if key in _DECIMAL_PCT_KEYS:
            return value / 100.0
        return value

    # ── Load / Save / Reset ──────────────────────────────────────

    def _load(self):
        self._load_from_cfg(self.cfg_path)

    def _load_from_cfg(self, path: Path | None):
        """Load values from a cfg file. Falls back to vanilla defaults for missing keys."""
        cfg = ConfigParser()
        cfg.optionxform = str  # preserve PascalCase keys for MelonPreferences
        if path and path.exists():
            # MelonPreferences.cfg may have stray lines before section headers
            # (e.g. old mod entries). Skip lines before the first [Section].
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            first_section = next((i for i, l in enumerate(lines) if l.strip().startswith("[")), 0)
            cfg.read_file(StringIO("".join(lines[first_section:])))
        for key, widget in self.widgets.items():
            default = VANILLA_DEFAULTS[key]
            raw = cfg.get(SECTION, key, fallback=None)
            if isinstance(widget, QCheckBox):
                val = raw.lower() in ("true", "1", "yes") if raw is not None else default
                widget.setChecked(val)
            elif isinstance(widget, QSpinBox):
                val = int(raw) if raw is not None else default
                # BeastRoom spinboxes have range 0+; clamp -1 to 0
                widget.setValue(max(val, widget.minimum()))
            elif isinstance(widget, QDoubleSpinBox):
                val = float(raw) if raw is not None else default
                widget.setValue(self._cfg_to_display(key, val))

        # UseVanillaBeastSettings is inverted into _enable_bosses_cb
        vanilla_raw = cfg.get(SECTION, "UseVanillaBeastSettings", fallback=None)
        vanilla_val = vanilla_raw.lower() in ("true", "1", "yes") if vanilla_raw is not None else VANILLA_DEFAULTS["UseVanillaBeastSettings"]
        self._enable_bosses_cb.setChecked(not vanilla_val)

        # Set enable checkboxes based on loaded cfg values
        fixed_raw = cfg.get(SECTION, "FixedExtraBosses", fallback=None)
        fixed_val = int(fixed_raw) if fixed_raw is not None else VANILLA_DEFAULTS["FixedExtraBosses"]
        self._fixed_bosses_cb.setChecked(fixed_val > 0)

        chance_val = self.widgets["BeastChancePercent"].value()
        self._random_cb.setChecked(chance_val > 0)

        extra_val = self.widgets["ExtraBiomes"].value()
        self._extra_cb.setChecked(extra_val > 0)

        # Sword in the Stone: enable checkbox if biomes > 0
        sword_val = self.widgets["GuaranteedSwordsBiomes"].value()
        self._sword_cb.setChecked(sword_val > 0)

        # Fight Boss manual controls
        fb_raw = cfg.get(SECTION, "FightBossMode", fallback=None)
        fb_val = fb_raw.lower() in ("true", "1", "yes") if fb_raw is not None else VANILLA_DEFAULTS["FightBossMode"]
        self._fight_boss_cb.setChecked(fb_val)

        fb_sel_raw = cfg.get(SECTION, "FightBossSelection", fallback=None)
        fb_sel = fb_sel_raw if fb_sel_raw is not None else VANILLA_DEFAULTS["FightBossSelection"]
        idx = self._fight_boss_combo.findData(fb_sel)
        if idx >= 0:
            self._fight_boss_combo.setCurrentIndex(idx)

        self._on_vanilla_beast_toggled(None)
        self._update_beast_enables()
        self._update_extra_enables()
        self._update_sword_enables()
        self._update_rush_enables()
        self._update_fight_boss_enables()

    def _save(self):
        if not self.cfg_path:
            QMessageBox.warning(self, "Error", "No game path set. Cannot save.")
            return
        cfg = ConfigParser()
        cfg.optionxform = str  # preserve PascalCase keys for MelonPreferences
        # Preserve any lines before the first section header (e.g. old mod entries)
        preamble = ""
        if self.cfg_path.exists():
            lines = self.cfg_path.read_text(encoding="utf-8").splitlines(keepends=True)
            first_section = next((i for i, l in enumerate(lines) if l.strip().startswith("[")), 0)
            preamble = "".join(lines[:first_section])
            cfg.read_file(StringIO("".join(lines[first_section:])))
        if not cfg.has_section(SECTION):
            cfg.add_section(SECTION)
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                cfg.set(SECTION, key, str(widget.isChecked()).lower())
            elif isinstance(widget, QSpinBox):
                # Toggle-controlled fields: write 0 when disabled
                if key == "FixedExtraBosses" and not self._fixed_bosses_cb.isChecked():
                    cfg.set(SECTION, key, "0")
                elif key == "ExtraBiomes" and not self._extra_cb.isChecked():
                    cfg.set(SECTION, key, "0")
                elif key == "GuaranteedSwordsBiomes" and not self._sword_cb.isChecked():
                    cfg.set(SECTION, key, "0")
                else:
                    cfg.set(SECTION, key, str(widget.value()))
            elif isinstance(widget, QDoubleSpinBox):
                # Toggle-controlled random chance: write 0 when disabled
                if key == "BeastChancePercent" and not self._random_cb.isChecked():
                    cfg.set(SECTION, key, "0.0")
                else:
                    val = self._display_to_cfg(key, widget.value())
                    cfg.set(SECTION, key, f"{val:g}")

        # UseVanillaBeastSettings is the inverse of the Enable checkbox
        cfg.set(SECTION, "UseVanillaBeastSettings", str(not self._enable_bosses_cb.isChecked()).lower())

        # Fight Boss manual controls
        cfg.set(SECTION, "FightBossMode", str(self._fight_boss_cb.isChecked()).lower())
        cfg.set(SECTION, "FightBossSelection", self._fight_boss_combo.currentData())

        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg_path, "w") as f:
            if preamble:
                f.write(preamble)
            cfg.write(f)

        QMessageBox.information(self, "Saved", f"Config saved to:\n{self.cfg_path}")

    def _reset_defaults(self):
        """Reset all fields to vanilla game values (unmodded behavior)."""
        for key, widget in self.widgets.items():
            default = VANILLA_DEFAULTS[key]
            if isinstance(widget, QCheckBox):
                widget.setChecked(default)
            elif isinstance(widget, QSpinBox):
                # Room defaults are -1 but spinbox min is 0; set to 0
                widget.setValue(max(default, widget.minimum()))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(self._cfg_to_display(key, default))
        # Reset enable toggles (vanilla: bosses off, fixed off, random off, extra off)
        self._enable_bosses_cb.setChecked(False)
        self._fixed_bosses_cb.setChecked(False)
        self._random_cb.setChecked(False)
        self._extra_cb.setChecked(False)
        self._fight_boss_cb.setChecked(False)
        self._fight_boss_combo.setCurrentIndex(0)
        self._sword_cb.setChecked(False)
        self._on_vanilla_beast_toggled(None)
        self._on_dispel_toggled(None)
        self._update_beast_enables()
        self._update_extra_enables()
        self._update_sword_enables()
        self._update_rush_enables()
        self._update_fight_boss_enables()

    def _start_game(self):
        """Launch SWORN via Steam."""
        QDesktopServices.openUrl(QUrl("steam://rungameid/1763250"))

    @staticmethod
    def _open_help():
        """Open the README / install instructions on GitHub."""
        QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}#readme"))

    def _open_mod_folder(self):
        """Open the Mods folder in the system file manager."""
        mods = self.mods_path
        if mods and mods.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(mods)))
        else:
            QMessageBox.warning(self, "Error", "Mods folder not found. Set the game path first.")

    def _open_game_folder(self):
        """Open the SWORN game folder in the system file manager."""
        if self.game_path and self.game_path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.game_path)))
        else:
            QMessageBox.warning(self, "Error", "Game folder not found.")

    def _open_config_folder(self):
        """Open the folder containing MelonPreferences.cfg."""
        if self.cfg_path and self.cfg_path.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.cfg_path.parent)))
        else:
            QMessageBox.warning(self, "Error", "Config folder not found.")

    def _export_cfg(self):
        """Save a copy of the current config to a user-chosen location."""
        if not self.cfg_path or not self.cfg_path.exists():
            QMessageBox.warning(self, "Error", "No config file found. Save first.")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Export Config", "MelonPreferences.cfg", "Config files (*.cfg)")
        if dest:
            import shutil
            shutil.copy2(str(self.cfg_path), dest)
            QMessageBox.information(self, "Exported", f"Config exported to:\n{dest}")

    def _import_cfg(self):
        """Load settings from an external .cfg file."""
        src, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "Config files (*.cfg);;All files (*)")
        if src:
            self._load_from_cfg(Path(src))
            self._on_vanilla_beast_toggled(None)
            self._on_dispel_toggled(None)
            self._update_beast_enables()
            self._update_extra_enables()
            self._update_rush_enables()
            self._update_fight_boss_enables()
            QMessageBox.information(self, "Imported", "Config loaded. Click Save Config to write to disk.")

    # ── Config code sharing ──────────────────────────────────────

    def _build_code_dict(self) -> dict[str, str]:
        """Build a dict of current widget values for code sharing."""
        d = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                d[key] = "1" if widget.isChecked() else "0"
            elif isinstance(widget, QSpinBox):
                d[key] = str(widget.value())
            elif isinstance(widget, QDoubleSpinBox):
                val = self._display_to_cfg(key, widget.value())
                d[key] = f"{val:g}"
        # Toggle states
        d["_enable_bosses"] = "1" if self._enable_bosses_cb.isChecked() else "0"
        d["_fixed"] = "1" if self._fixed_bosses_cb.isChecked() else "0"
        d["_random"] = "1" if self._random_cb.isChecked() else "0"
        d["_extra"] = "1" if self._extra_cb.isChecked() else "0"
        d["_fight_boss"] = "1" if self._fight_boss_cb.isChecked() else "0"
        d["_fight_boss_sel"] = self._fight_boss_combo.currentData()
        d["_sword"] = "1" if self._sword_cb.isChecked() else "0"
        return d

    def _copy_code(self):
        """Encode current settings as a compact shareable code and copy to clipboard."""
        d = self._build_code_dict()
        payload = "|".join(f"{k}={v}" for k, v in d.items())
        code = "ST1:" + base64.b64encode(payload.encode()).decode()
        QApplication.clipboard().setText(code)
        QMessageBox.information(self, "Copied", "Config code copied to clipboard.\nShare it with others to replicate your settings.")

    def _paste_code(self):
        """Decode a config code from clipboard and apply it."""
        text = (QApplication.clipboard().text() or "").strip()
        if not text.startswith("ST1:"):
            QMessageBox.warning(self, "Invalid Code", "Clipboard doesn't contain a valid SwornTweaks config code.\n\nCodes start with 'ST1:'.")
            return
        try:
            payload = base64.b64decode(text[4:]).decode()
        except Exception:
            QMessageBox.warning(self, "Invalid Code", "Could not decode the config code.")
            return
        pairs = {}
        for part in payload.split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                pairs[k] = v
        # Apply to widgets
        for key, widget in self.widgets.items():
            if key not in pairs:
                continue
            raw = pairs[key]
            if isinstance(widget, QCheckBox):
                widget.setChecked(raw in ("1", "true", "True"))
            elif isinstance(widget, QSpinBox):
                widget.setValue(max(int(raw), widget.minimum()))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(self._cfg_to_display(key, float(raw)))
        # Toggle states
        if "_enable_bosses" in pairs:
            self._enable_bosses_cb.setChecked(pairs["_enable_bosses"] == "1")
        elif "UseVanillaBeastSettings" in pairs:
            # Backward compat: old codes stored UseVanillaBeastSettings directly
            self._enable_bosses_cb.setChecked(pairs["UseVanillaBeastSettings"] not in ("1", "true", "True"))
        if "_fixed" in pairs:
            self._fixed_bosses_cb.setChecked(pairs["_fixed"] == "1")
        if "_random" in pairs:
            self._random_cb.setChecked(pairs["_random"] == "1")
        if "_extra" in pairs:
            self._extra_cb.setChecked(pairs["_extra"] == "1")
        if "_fight_boss" in pairs:
            self._fight_boss_cb.setChecked(pairs["_fight_boss"] == "1")
        if "_fight_boss_sel" in pairs:
            idx = self._fight_boss_combo.findData(pairs["_fight_boss_sel"])
            if idx >= 0:
                self._fight_boss_combo.setCurrentIndex(idx)
        if "_sword" in pairs:
            self._sword_cb.setChecked(pairs["_sword"] == "1")
        self._on_vanilla_beast_toggled(None)
        self._on_dispel_toggled(None)
        self._update_beast_enables()
        self._update_extra_enables()
        self._update_sword_enables()
        self._update_rush_enables()
        self._update_fight_boss_enables()
        QMessageBox.information(self, "Applied", "Config code applied. Click Save .cfg to write to disk.")

    # ── Update from GitHub ───────────────────────────────────────

    def _update_from_github(self):
        if not self.mods_path:
            QMessageBox.warning(self, "Error", "No game path set.")
            return
        if not self.mods_path.is_dir():
            QMessageBox.warning(self, "Error", f"Mods folder not found:\n{self.mods_path}")
            return

        reply = QMessageBox.question(
            self, "Update from GitHub",
            "This will download the latest:\n"
            "  - SwornTweaks.dll (into Mods/)\n"
            "  - configurator.py (self-update)\n\n"
            "Proceed?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Download DLL
        dll_worker = DownloadWorker(GITHUB_DLL, self.mods_path / "SwornTweaks.dll")
        dll_worker.finished.connect(lambda p: self._on_dll_updated(p))
        dll_worker.error.connect(lambda e: self._on_update_error("DLL", e))
        self._workers.append(dll_worker)

        # Download configurator.py (self-update)
        script_path = Path(sys.argv[0]).resolve()
        cfg_worker = DownloadWorker(GITHUB_CONFIGURATOR, script_path)
        cfg_worker.finished.connect(lambda p: self._on_script_updated(p))
        cfg_worker.error.connect(lambda e: self._on_update_error("Configurator", e))
        self._workers.append(cfg_worker)

        dll_worker.start()
        cfg_worker.start()

    def _on_dll_updated(self, path: str):
        self.statusBar().showMessage(f"DLL updated: {path}", 5000)

    def _on_script_updated(self, path: str):
        QMessageBox.information(
            self, "Updated",
            f"SwornTweaks.dll and configurator updated.\n\n"
            f"Restart the configurator to use the new version."
        )

    def _on_update_error(self, what: str, err: str):
        QMessageBox.critical(self, "Update Failed", f"Failed to download {what}:\n{err}")


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(make_icon())
    win = Configurator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
