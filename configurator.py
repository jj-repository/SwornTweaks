#!/usr/bin/env python3
"""SwornTweaks Configurator — lightweight PyQt6 GUI for editing MelonPreferences.cfg"""
from __future__ import annotations

import base64
import json
import os
import platform
import sys
import ssl
import urllib.request

# PyInstaller bundles don't include system SSL certificates.
# Use certifi if available, otherwise fall back to default context.
try:
    import certifi
    _ssl_ctx = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _ssl_ctx = None  # use system certs (works outside frozen builds)
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

VERSION = "1.9.5"
_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB safety cap for downloads
GITHUB_REPO = "jj-repository/SwornTweaks"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_DLL = f"{GITHUB_RAW}/SwornTweaks.dll"
GITHUB_CONFIGURATOR = f"{GITHUB_RAW}/configurator.py"
_EXE_ASSET = "SwornTweaks-Windows.exe" if platform.system() == "Windows" else "SwornTweaks-Linux"
GITHUB_EXE = f"https://github.com/{GITHUB_REPO}/releases/latest/download/{_EXE_ASSET}"
SECTION = "SwornTweaks"
IS_FROZEN = getattr(sys, "frozen", False)  # True when running as PyInstaller .exe

_LIGHT_STYLE = """
QWidget { background-color: #f0f0f0; color: #1e1e1e; }
QGroupBox { border: 1px solid #bbb; border-radius: 4px; margin-top: 8px; padding-top: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #1e1e1e; }
QTabWidget::pane { border: 1px solid #bbb; }
QTabBar::tab { background: #e0e0e0; color: #1e1e1e; padding: 6px 14px; border: 1px solid #bbb;
               border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #f0f0f0; }
QTabBar::tab:!selected { margin-top: 2px; }
QTabBar::tab:disabled { background: transparent; border: none; min-width: 40px; max-width: 40px; }
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit { background: #ffffff; color: #1e1e1e;
               border: 1px solid #bbb; border-radius: 3px; padding: 2px; }
QScrollArea { border: none; }
QPushButton { background: #e0e0e0; color: #1e1e1e; border: 1px solid #bbb; border-radius: 3px; padding: 5px 12px; }
QPushButton:hover { background: #d0d0d0; }
QCheckBox { color: #1e1e1e; }
QCheckBox::indicator { width: 14px; height: 14px; border: 2px solid #888; border-radius: 3px; background: #ffffff; }
QCheckBox::indicator:checked { background: #2e7d32; border-color: #2e7d32; }
QCheckBox::indicator:unchecked:hover { border-color: #555; }
QCheckBox::indicator:disabled { background: #e0e0e0; border-color: #bbb; }
QLabel { color: #1e1e1e; }
QMessageBox { background-color: #f0f0f0; }
QStatusBar { background: #e0e0e0; color: #555; }
QToolTip { background: #ffffcc; color: #1e1e1e; border: 1px solid #bbb; }
"""


def _make_checkbox_images() -> tuple[str, str]:
    """Generate checked/unchecked checkbox images and return their file paths."""
    import tempfile
    d = tempfile.mkdtemp(prefix="sworntweaks_")

    size = 18
    # Unchecked: empty dark box with border
    unchecked = QPixmap(size, size)
    unchecked.fill(QColor(0, 0, 0, 0))
    p = QPainter(unchecked)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(136, 136, 136), 2))
    p.setBrush(QColor(45, 45, 45))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    p.end()
    unchecked_path = os.path.join(d, "cb_unchecked.png")
    unchecked.save(unchecked_path)

    # Checked: green box with white checkmark
    checked = QPixmap(size, size)
    checked.fill(QColor(0, 0, 0, 0))
    p = QPainter(checked)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(46, 125, 50))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    pen = QPen(QColor(255, 255, 255), 2.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(4, 9)
    path.lineTo(7.5, 13)
    path.lineTo(14, 5)
    p.drawPath(path)
    p.end()
    checked_path = os.path.join(d, "cb_checked.png")
    checked.save(checked_path)

    return checked_path, unchecked_path


def _build_dark_style() -> str:
    """Build the dark stylesheet with generated checkbox images."""
    checked, unchecked = _make_checkbox_images()
    # Qt stylesheets need forward slashes in paths on all platforms
    checked = checked.replace("\\", "/")
    unchecked = unchecked.replace("\\", "/")
    return f"""
QWidget {{ background-color: #1e1e1e; color: #dcdcdc; }}
QGroupBox {{ border: 1px solid #444; border-radius: 4px; margin-top: 8px; padding-top: 14px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #dcdcdc; }}
QTabWidget::pane {{ border: 1px solid #444; }}
QTabBar::tab {{ background: #2d2d2d; color: #dcdcdc; padding: 6px 14px; border: 1px solid #444;
               border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }}
QTabBar::tab:selected {{ background: #1e1e1e; }}
QTabBar::tab:!selected {{ margin-top: 2px; }}
QTabBar::tab:disabled {{ background: transparent; border: none; min-width: 40px; max-width: 40px; }}
QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {{ background: #2d2d2d; color: #dcdcdc;
               border: 1px solid #555; border-radius: 3px; padding: 2px; }}
QScrollArea {{ border: none; }}
QPushButton {{ background: #333; color: #dcdcdc; border: 1px solid #555; border-radius: 3px; padding: 5px 12px; }}
QPushButton:hover {{ background: #444; }}
QCheckBox {{ color: #dcdcdc; spacing: 6px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QCheckBox::indicator:unchecked {{ image: url({unchecked}); }}
QCheckBox::indicator:checked {{ image: url({checked}); }}
QLabel {{ color: #dcdcdc; }}
QMessageBox {{ background-color: #1e1e1e; }}
QStatusBar {{ background: #2d2d2d; color: #aaa; }}
QToolTip {{ background: #2d2d2d; color: #dcdcdc; border: 1px solid #555; }}
"""

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

_TAKO_B64 = (
    "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"
    "FtswQdgqAAAAAElFTkSuQmCC"
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
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
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
    download_finished = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, url: str, dest: Path):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            self.dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.dest.with_suffix(self.dest.suffix + ".tmp")
            req = urllib.request.Request(self.url, headers={"User-Agent": "SwornTweaks"})
            with urllib.request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                data = resp.read(_MAX_DOWNLOAD_BYTES + 1)
                if len(data) > _MAX_DOWNLOAD_BYTES:
                    raise RuntimeError("Download exceeds 50 MB safety limit")
                tmp.write_bytes(data)
            # On Windows, you can't overwrite a running exe, but you CAN
            # rename it. Move the old file aside, put the new one in place.
            # Use a unique .old name to avoid conflicts with locked files
            # from previous updates (WinError 5).
            # Verify the downloaded tmp file exists and is non-empty
            if not tmp.exists() or tmp.stat().st_size == 0:
                raise RuntimeError("Downloaded file is missing or empty")
            import time
            old = self.dest.with_suffix(f".old{int(time.time())}")
            if self.dest.exists():
                self.dest.rename(old)
            try:
                tmp.rename(self.dest)
            except Exception:
                # Restore from backup if moving the new file into place fails
                if old.exists() and not self.dest.exists():
                    old.rename(self.dest)
                raise
            # Best-effort cleanup of .old files — don't fail if locked
            for stale in self.dest.parent.glob(self.dest.stem + ".old[0-9]*"):
                try:
                    stale.unlink()
                except OSError:
                    pass  # locked by OS — will be cleaned up next time
            self.download_finished.emit(str(self.dest))
        except Exception as e:
            self.download_error.emit(str(e))


class UpdateChecker(QThread):
    """Background thread to check GitHub for a newer version."""
    update_available = pyqtSignal(str)  # emits the remote version string
    no_update = pyqtSignal()            # emits when already up to date
    check_failed = pyqtSignal(str)      # emits error message on failure

    def run(self):
        try:
            import re
            req = urllib.request.Request(GITHUB_CONFIGURATOR, headers={"User-Agent": "SwornTweaks"})
            with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx) as resp:
                # Only read first 2KB — VERSION is near the top
                head = resp.read(2048).decode("utf-8", errors="ignore")
            m = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', head)
            if m:
                remote = m.group(1)
                try:
                    remote_tuple = tuple(map(int, remote.split(".")))
                    local_tuple = tuple(map(int, VERSION.split(".")))
                    if remote_tuple > local_tuple:
                        self.update_available.emit(remote)
                    else:
                        self.no_update.emit()
                except (ValueError, TypeError):
                    self.no_update.emit()
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_failed.emit(str(e))


class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SwornTweaks Configurator v{VERSION}")
        self.setWindowIcon(make_icon())
        self.resize(540, 740)
        self.widgets: dict[str, QWidget] = {}
        self._workers: list[QThread] = []

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

        # Invisible spacer tab for visual gap between Game Modes and Settings
        self._tabs.addTab(QWidget(), "")
        _spacer_idx = self._tabs.count() - 1
        self._tabs.setTabEnabled(_spacer_idx, False)
        self._tabs.setStyleSheet(self._tabs.styleSheet())  # force refresh
        self._tabs.tabBar().setTabButton(_spacer_idx, self._tabs.tabBar().ButtonPosition.LeftSide, None)
        self._tabs.tabBar().setTabButton(_spacer_idx, self._tabs.tabBar().ButtonPosition.RightSide, None)

        settings_page = QWidget()
        slay = QVBoxLayout(settings_page)
        version_label = QLabel(f"SwornTweaks Configurator v{VERSION}")
        version_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        slay.addWidget(version_label)
        slay.addSpacing(4)
        gh_label = QLabel(f'GitHub &amp; Install Instructions: <a href="https://github.com/{GITHUB_REPO}/blob/main/INSTALL.md">'
                          f'github.com/{GITHUB_REPO}</a>')
        gh_label.setStyleSheet("color: gray; font-size: 11px;")
        gh_label.setOpenExternalLinks(True)
        slay.addWidget(gh_label)
        slay.addSpacing(12)
        update_btn = QPushButton("Update Mod from GitHub")
        update_btn.setToolTip("Download latest DLL and configurator from GitHub")
        update_btn.clicked.connect(self._check_and_update)
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
        self._dark_mode_cb = QCheckBox("Dark Mode")
        self._dark_mode_cb.setChecked(_load_settings().get("dark_mode", True))
        self._dark_mode_cb.stateChanged.connect(self._on_dark_mode_toggled)
        slay.addWidget(self._dark_mode_cb)
        slay.addSpacing(8)
        tako_data = base64.b64decode(_TAKO_B64)
        tako_pix = QPixmap()
        tako_pix.loadFromData(tako_data)
        tako_pix = tako_pix.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        tako_label = QLabel()
        tako_label.setPixmap(tako_pix)
        tako_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slay.addWidget(tako_label)
        by_label = QLabel("by JJ")
        by_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        by_label.setStyleSheet("color: gray; font-size: 11px;")
        slay.addWidget(by_label)
        slay.addStretch()
        self._tabs.addTab(_scroll_tab(settings_page), "Settings")

        # ── Help tab ───────────────────────────────────────────────
        help_page = QWidget()
        hlay = QVBoxLayout(help_page)

        help_title = QLabel("SwornTweaks Help")
        help_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        hlay.addWidget(help_title)
        hlay.addSpacing(8)

        help_btns = QHBoxLayout()
        readme_btn = QPushButton("Readme")
        readme_btn.setToolTip("Open install instructions and documentation on GitHub")
        readme_btn.setStyleSheet("QPushButton { background-color: #1565c0; color: white; font-weight: bold; }"
                                 "QPushButton:hover { background-color: #1976d2; }")
        readme_btn.clicked.connect(self._open_help)
        help_btns.addWidget(readme_btn)
        report_btn = QPushButton("Report Bug")
        report_btn.setToolTip("Open a bug report on GitHub")
        report_btn.setStyleSheet("QPushButton { background-color: #f9a825; color: #1e1e1e; font-weight: bold; }"
                                 "QPushButton:hover { background-color: #fbc02d; }")
        report_btn.clicked.connect(self._report_bug)
        help_btns.addWidget(report_btn)
        logs_btn = QPushButton("Open Logs Folder")
        logs_btn.setToolTip("Open MelonLoader logs folder — attach Latest.log to bug reports")
        logs_btn.clicked.connect(self._open_logs_folder)
        help_btns.addWidget(logs_btn)
        help_btns.addStretch()
        hlay.addLayout(help_btns)
        hlay.addSpacing(12)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #444;")
        hlay.addWidget(sep)
        hlay.addSpacing(8)

        help_sections = [
            ("Reporting Bugs", "Found a bug? Click the yellow 'Report Bug' button above to open a structured "
                               "bug report on GitHub. Fill out the version, OS, and steps to reproduce. "
                               "Attach your MelonLoader log (click 'Open Logs Folder' above, then attach "
                               "Latest.log to the report) for faster troubleshooting."),
            ("Player", "Adjust player health and damage multipliers, toggle infinite mana or invincibility. "
                        "Set bonus rerolls, tweak blessing rarity percentages, and add extra blessings per room."),
            ("Enemies", "Scale boss, beast, and regular enemy health and damage independently. "
                        "Adjust enemy spawn intensity per room."),
            ("Toggles", "Quick on/off switches for quality-of-life features: free gems, Ring of Dispel unlock, "
                        "unlimited gold, skip Somewhere, guaranteed Fae Realm portals, and Sword in the Stone."),
            ("Game Modes", "Boss Rush: fight all bosses back-to-back with configurable scaling and rewards. "
                           "Extra Biomes: add more combat biomes before Camelot. Progressive HP Scaling "
                           "increases enemy health each biome so extended runs stay challenging. "
                           "Extra Bosses: inject additional beast/boss encounters per biome. "
                           "Fight Boss: force-load a specific boss for practice or testing."),
            ("Settings", "Update the mod and configurator from GitHub, reset to vanilla defaults, "
                         "share or import config codes, export/import .cfg files, and open game folders. "
                         "Toggle dark mode and auto-update checks."),
        ]
        for title_text, desc_text in help_sections:
            sec_title = QLabel(title_text)
            sec_title.setStyleSheet("font-size: 13px; font-weight: bold;")
            hlay.addWidget(sec_title)
            sec_desc = QLabel(desc_text)
            sec_desc.setWordWrap(True)
            sec_desc.setStyleSheet("color: gray; font-size: 11px; margin-left: 8px;")
            hlay.addWidget(sec_desc)
            hlay.addSpacing(6)

        # Old mascot image at the bottom of help
        hlay.addSpacing(8)
        mascot_data = base64.b64decode(_MASCOT_B64)
        mascot_pix = QPixmap()
        mascot_pix.loadFromData(mascot_data)
        mascot_pix = mascot_pix.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        mascot_label = QLabel()
        mascot_label.setPixmap(mascot_pix)
        mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hlay.addWidget(mascot_label)

        hlay.addStretch()
        self._tabs.addTab(_scroll_tab(help_page), "Help")

        outer.addWidget(self._tabs)

        # ── Bottom bar ──────────────────────────────────────────────

        bottom = QHBoxLayout()
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

        # Apply theme
        self._apply_theme()

        # Auto-check for updates on startup (if enabled)
        if self._auto_update_cb.isChecked():
            self._update_checker = UpdateChecker()
            self._update_checker.update_available.connect(self._on_update_available)
            self._update_checker.finished.connect(self._update_checker.deleteLater)
            self._update_checker.start()

    def _on_auto_update_toggled(self, _state):
        """Persist the auto-update-check preference."""
        data = _load_settings()
        data["auto_update_check"] = self._auto_update_cb.isChecked()
        _save_settings(data)

    def _on_dark_mode_toggled(self, _state):
        """Persist dark mode preference and apply theme."""
        data = _load_settings()
        data["dark_mode"] = self._dark_mode_cb.isChecked()
        _save_settings(data)
        self._apply_theme()

    def _apply_theme(self):
        """Apply dark or light theme to the application."""
        dark = self._dark_mode_cb.isChecked()
        if dark:
            if not hasattr(self, "_dark_style_cache"):
                self._dark_style_cache = _build_dark_style()
            QApplication.instance().setStyleSheet(self._dark_style_cache)
        else:
            QApplication.instance().setStyleSheet(_LIGHT_STYLE)

    def _on_update_available(self, remote_version: str):
        """Show update prompt when a newer version is found on GitHub."""
        if not self.mods_path or not self.mods_path.is_dir():
            return  # can't update without a valid game path
        reply = QMessageBox.question(
            self, "Update Available",
            f"A new version of SwornTweaks is available!\n\n"
            f"Current: v{VERSION}\n"
            f"Latest:  v{remote_version}\n\n"
            "Would you like to update now?\n"
            "(Downloads the latest DLL and configurator from GitHub)",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._do_update()

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
                if raw is not None:
                    try:
                        val = int(raw)
                    except ValueError:
                        val = default
                else:
                    val = default
                # BeastRoom spinboxes have range 0+; clamp -1 to 0
                widget.setValue(max(val, widget.minimum()))
            elif isinstance(widget, QDoubleSpinBox):
                if raw is not None:
                    try:
                        val = float(raw)
                    except ValueError:
                        val = default
                else:
                    val = default
                widget.setValue(self._cfg_to_display(key, val))

        # UseVanillaBeastSettings is inverted into _enable_bosses_cb
        vanilla_raw = cfg.get(SECTION, "UseVanillaBeastSettings", fallback=None)
        vanilla_val = vanilla_raw.lower() in ("true", "1", "yes") if vanilla_raw is not None else VANILLA_DEFAULTS["UseVanillaBeastSettings"]
        self._enable_bosses_cb.setChecked(not vanilla_val)

        # Set enable checkboxes based on loaded cfg values
        fixed_raw = cfg.get(SECTION, "FixedExtraBosses", fallback=None)
        if fixed_raw is not None:
            try:
                fixed_val = int(fixed_raw)
            except ValueError:
                fixed_val = VANILLA_DEFAULTS["FixedExtraBosses"]
        else:
            fixed_val = VANILLA_DEFAULTS["FixedExtraBosses"]
        self._fixed_bosses_cb.setChecked(fixed_val > 0)

        # Use raw config values (not clamped widget values) for enable checkboxes
        def _raw_float(key: str) -> float:
            r = cfg.get(SECTION, key, fallback=None)
            if r is None: return VANILLA_DEFAULTS[key]
            try: return float(r)
            except ValueError: return VANILLA_DEFAULTS[key]

        def _raw_int(key: str) -> int:
            r = cfg.get(SECTION, key, fallback=None)
            if r is None: return VANILLA_DEFAULTS[key]
            try: return int(r)
            except ValueError: return VANILLA_DEFAULTS[key]

        self._random_cb.setChecked(_raw_float("BeastChancePercent") > 0)
        self._extra_cb.setChecked(_raw_int("ExtraBiomes") > 0)
        self._sword_cb.setChecked(_raw_int("GuaranteedSwordsBiomes") > 0)

        # Fight Boss manual controls
        fb_raw = cfg.get(SECTION, "FightBossMode", fallback=None)
        fb_val = fb_raw.lower() in ("true", "1", "yes") if fb_raw is not None else VANILLA_DEFAULTS["FightBossMode"]
        self._fight_boss_cb.setChecked(fb_val)

        fb_sel_raw = cfg.get(SECTION, "FightBossSelection", fallback=None)
        fb_sel = fb_sel_raw.strip('"') if fb_sel_raw is not None else VANILLA_DEFAULTS["FightBossSelection"]
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
        if self.cfg_path.exists():
            lines = self.cfg_path.read_text(encoding="utf-8").splitlines(keepends=True)
            # Skip stray lines before the first [Section] — they cause TOML parse errors
            first_section = next((i for i, l in enumerate(lines) if l.strip().startswith("[")), 0)
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
        cfg.set(SECTION, "FightBossSelection", f'"{self._fight_boss_combo.currentData()}"')

        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg_path, "w", encoding="utf-8") as f:
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
    def _report_bug():
        """Open the GitHub bug report template in the browser."""
        QDesktopServices.openUrl(QUrl(
            f"https://github.com/{GITHUB_REPO}/issues/new?template=bug_report.yml"
        ))

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

    def _open_logs_folder(self):
        """Open the MelonLoader logs folder for bug report attachments."""
        if self.game_path:
            logs = self.game_path / "MelonLoader"
            if logs.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs)))
                return
        QMessageBox.warning(self, "Error", "MelonLoader folder not found.")

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
                try:
                    widget.setValue(max(int(raw), widget.minimum()))
                except ValueError:
                    pass
            elif isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(self._cfg_to_display(key, float(raw)))
                except ValueError:
                    pass
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

    # ── Update logic ──────────────────────────────────────────────

    def _check_and_update(self):
        """Manual update button: check version first, then download if newer."""
        if self._workers:
            self.statusBar().showMessage("Update already in progress…", 3000)
            return
        if not self.mods_path:
            QMessageBox.warning(self, "Error", "No game path set.")
            return
        if not self.mods_path.is_dir():
            QMessageBox.warning(self, "Error", f"Mods folder not found:\n{self.mods_path}")
            return

        self.statusBar().showMessage("Checking for updates…")
        checker = UpdateChecker()
        checker.update_available.connect(self._confirm_and_update)
        checker.no_update.connect(self._on_already_up_to_date)
        checker.check_failed.connect(self._on_check_failed)
        self._workers.append(checker)
        checker.start()

    def _confirm_and_update(self, remote_version: str):
        """Version check found a newer release — ask user to confirm."""
        reply = QMessageBox.question(
            self, "Update Available",
            f"A new version is available!\n\n"
            f"Current: v{VERSION}\n"
            f"Latest:  v{remote_version}\n\n"
            "Download and install the update?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._do_update()
        else:
            self._workers.clear()

    def _on_check_failed(self, err: str):
        self._workers.clear()
        QMessageBox.critical(self, "Update Check Failed", f"Could not reach GitHub:\n{err}")

    def _on_already_up_to_date(self):
        self._workers.clear()
        self.statusBar().showMessage(f"Already up to date (v{VERSION}).", 5000)
        QMessageBox.information(
            self, "Up to Date",
            f"You already have the latest version (v{VERSION}).")

    def _do_update(self):
        """Download latest DLL and configurator (exe or .py depending on mode)."""
        if IS_FROZEN:
            self._update_results = {"dll": None, "exe": None}
        else:
            self._update_results = {"dll": None, "cfg": None}

        # Download DLL
        dll_worker = DownloadWorker(GITHUB_DLL, self.mods_path / "SwornTweaks.dll")
        dll_worker.download_finished.connect(lambda p: self._on_download_done("dll", p))
        dll_worker.download_error.connect(lambda e: self._on_download_fail("dll", "DLL", e))
        self._workers.append(dll_worker)
        dll_worker.start()

        if IS_FROZEN:
            # Running as compiled .exe — download new exe from GitHub releases.
            # DownloadWorker renames the running .exe aside (.old) and puts the
            # new one in place (Windows allows renaming a running .exe).
            exe_path = Path(sys.executable).resolve()
            exe_worker = DownloadWorker(GITHUB_EXE, exe_path)
            exe_worker.download_finished.connect(lambda p: self._on_download_done("exe", p))
            exe_worker.download_error.connect(lambda e: self._on_download_fail("exe", "Configurator", e))
            self._workers.append(exe_worker)
            exe_worker.start()
        else:
            # Running as .py script — safe to self-update and restart.
            script_path = Path(sys.argv[0]).resolve()
            cfg_worker = DownloadWorker(GITHUB_CONFIGURATOR, script_path)
            cfg_worker.download_finished.connect(lambda p: self._on_download_done("cfg", p))
            cfg_worker.download_error.connect(lambda e: self._on_download_fail("cfg", "Configurator", e))
            self._workers.append(cfg_worker)
            cfg_worker.start()

        self.statusBar().showMessage("Downloading update...", 0)

    def _on_download_done(self, key: str, path: str):
        self._update_results[key] = path
        self._check_update_complete()

    def _on_download_fail(self, key: str, what: str, err: str):
        self._update_results[key] = False
        QMessageBox.critical(self, "Update Failed", f"Failed to download {what}:\n{err}")
        self._check_update_complete()

    def _check_update_complete(self):
        """Called after each download finishes. Acts when both are done."""
        if any(v is None for v in self._update_results.values()):
            return  # still waiting
        self._workers.clear()

        if not all(v and v is not False for v in self._update_results.values()):
            self.statusBar().showMessage("Update finished with errors", 5000)
            return

        self.statusBar().showMessage("Update complete — restarting…", 5000)
        QMessageBox.information(
            self, "Updated",
            "SwornTweaks has been updated.\n\n"
            "The configurator will now restart.")
        import subprocess
        exe = str(Path(sys.executable).resolve())
        try:
            if IS_FROZEN and platform.system() == "Windows":
                subprocess.Popen(
                    [exe],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    close_fds=True,
                )
            elif IS_FROZEN:
                subprocess.Popen([exe])
            else:
                subprocess.Popen([sys.executable] + sys.argv)
        except Exception as e:
            QMessageBox.warning(
                self, "Restart Failed",
                f"Could not restart automatically:\n{e}\n\n"
                f"Please reopen the configurator manually.")
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(make_icon())
    win = Configurator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
