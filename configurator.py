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
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap, QFont, QPen
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

VERSION = "1.5.0"
GITHUB_REPO = "jj-repository/SwornTweaks"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_DLL = f"{GITHUB_RAW}/SwornTweaks.dll"
GITHUB_CONFIGURATOR = f"{GITHUB_RAW}/configurator.py"
SECTION = "SwornTweaks"

# Highest selectable room index across biomes
MAX_FIXED_ROOM = 12

# Mod defaults — what the mod ships with on first run
VANILLA_DEFAULTS = {
    "BonusRerolls": 0,
    "InfiniteRerolls": False,
    "LegendaryChance": 0.03,
    "EpicChance": 0.08,
    "RareChance": 0.20,
    "UncommonChance": 0.25,
    "NoGemCost": False,
    "NoCurrencyDoorRewards": False,
    "DuoChance": 0.0,
    "ExtraBiomes": 0,
    "RandomizeRepeats": False,
    "AllBiomesRandom": False,
    "UseVanillaBeastSettings": True,
    "BeastChancePercent": 0.0,
    "MaxBeastsPerBiome": 5,
    "BeastRoom1": -1,
    "BeastRoom2": -1,
    "BossHealthMultiplier": 1.0,
    "BeastHealthMultiplier": 1.0,
    "IntensityMultiplier": 1.0,
    "EnemyHealthMultiplier": 1.0,
    "EnemyDamageMultiplier": 1.0,
    "ChaosMode": False,
    "ForceBiomeBoss": False,
}

# Keys managed directly by _on_vanilla_beast_toggled (not via enable checkboxes)
_BEAST_DIRECT_KEYS = ("ForceBiomeBoss",)

_DECIMAL_PCT_KEYS = {"LegendaryChance", "EpicChance", "RareChance", "UncommonChance", "DuoChance"}

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


def load_game_path() -> Path | None:
    sp = settings_path()
    if sp.exists():
        try:
            data = json.loads(sp.read_text())
            p = Path(data["game_path"])
            if p.is_dir():
                return p
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def save_game_path(path: Path):
    sp = settings_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"game_path": str(path)}))


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
            urllib.request.urlretrieve(self.url, str(self.dest))
            self.finished.emit(str(self.dest))
        except Exception as e:
            self.error.emit(str(e))


class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SwornTweaks Configurator v{VERSION}")
        self.setWindowIcon(make_icon())
        self.setMinimumWidth(960)
        self.widgets: dict[str, QWidget] = {}
        self._workers: list[DownloadWorker] = []
        self._initial_values: dict[str, object] = {}  # snapshot of cfg values at launch

        # Resolve game path
        self.game_path = load_game_path() or find_game_path()
        if self.game_path is None:
            self.game_path = self._ask_game_path()
        if self.game_path:
            save_game_path(self.game_path)

        central = QWidget()
        outer = QVBoxLayout(central)

        # Three-column layout
        columns = QHBoxLayout()
        left = QVBoxLayout()
        center = QVBoxLayout()
        right = QVBoxLayout()

        # ── Left column ──────────────────────────────────────────
        left.addWidget(self._group("Rerolls", [
            self._int_row("BonusRerolls", "Bonus Rerolls", 0, 9999),
            self._bool_row("InfiniteRerolls", "Infinite Rerolls"),
        ]))

        left.addWidget(self._group("Blessing Rarity", [
            self._pct_row("LegendaryChance", "Legendary Chance", 0, 100),
            self._pct_row("EpicChance", "Epic Chance", 0, 100),
            self._pct_row("RareChance", "Rare Chance", 0, 100),
            self._pct_row("UncommonChance", "Uncommon Chance", 0, 100),
            self._pct_row("DuoChance", "Duo Chance", 0, 100),
        ]))

        left.addWidget(self._group("Toggles", [
            self._bool_row("NoGemCost", "No Gem Cost"),
            self._bool_row("NoCurrencyDoorRewards", "No Currency Door Rewards"),
        ]))

        left.addWidget(self._group("Blessing Selection", [
            self._bool_row("ChaosMode", "Chaos Mode"),
            self._label_row("Bypass all blessing prerequisites"),
        ]))

        left.addWidget(self._group("Spawn Intensity", [
            self._float_row("IntensityMultiplier", "Room Intensity", 0.1, 10.0, "x"),
            self._label_row("Scales enemy spawn count per room."),
        ]))

        left.addStretch()

        # ── Center column ─────────────────────────────────────────
        # Build Boss Room Spawns rows with toggle checkboxes
        boss_rows = []
        boss_rows.append(self._label_row("Makes Beast Bosses Spawn"))
        boss_rows.append(self._bool_row("UseVanillaBeastSettings", "Use Vanilla Boss Settings"))
        boss_rows.append(self._bool_row("ForceBiomeBoss", "Also Spawn Main Bosses"))
        boss_rows.append(self._label_row("Adds biome end bosses to the spawn pool (experimental)."))

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
        boss_rows.append(random_row)

        boss_rows.append(self._int_row("MaxBeastsPerBiome", "Max per Biome", 0, 15))
        boss_rows.append(self._label_row("Excludes fixed boss rooms."))

        # Fixed Boss Room 1: enable checkbox + spinbox
        room1_row = QHBoxLayout()
        self._room1_cb = QCheckBox("Fixed Boss Room 1")
        room1_row.addWidget(self._room1_cb)
        room1_row.addStretch()
        room1_spin = QSpinBox()
        room1_spin.setRange(0, MAX_FIXED_ROOM)
        room1_spin.setFixedWidth(90)
        self.widgets["BeastRoom1"] = room1_spin
        room1_row.addWidget(room1_spin)
        boss_rows.append(room1_row)

        # Fixed Boss Room 2: enable checkbox + spinbox
        room2_row = QHBoxLayout()
        self._room2_cb = QCheckBox("Fixed Boss Room 2")
        room2_row.addWidget(self._room2_cb)
        room2_row.addStretch()
        room2_spin = QSpinBox()
        room2_spin.setRange(0, MAX_FIXED_ROOM)
        room2_spin.setFixedWidth(90)
        self.widgets["BeastRoom2"] = room2_spin
        room2_row.addWidget(room2_spin)
        boss_rows.append(room2_row)

        boss_rows.append(self._label_row("First room = room 0."))
        center.addWidget(self._group("Boss Room Spawns", boss_rows))

        # Wire up toggle callbacks for boss room controls
        self._random_cb.stateChanged.connect(lambda _: self._update_beast_enables())
        self._room1_cb.stateChanged.connect(lambda _: self._update_beast_enables())
        self._room2_cb.stateChanged.connect(lambda _: self._update_beast_enables())

        center.addWidget(self._group("Health Multipliers", [
            self._float_row("BossHealthMultiplier", "Boss Health", 0.1, 50.0, "x"),
            self._float_row("BeastHealthMultiplier", "Beast Health", 0.1, 50.0, "x"),
        ]))

        center.addWidget(self._group("Enemy Scaling", [
            self._float_row("EnemyHealthMultiplier", "Enemy Health", 0.1, 50.0, "x"),
            self._float_row("EnemyDamageMultiplier", "Enemy Damage", 0.1, 50.0, "x"),
            self._label_row("Affects normal enemies only.\nBoss/beast health has its own multipliers."),
        ]))

        center.addStretch()

        # ── Right column ──────────────────────────────────────────
        # Extra Biomes: enable checkbox + spinbox
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
        run_rows.append(self._label_row("Adds combat biomes after DeepHarbor.\n"
                            "1 = +Kingswood, 2 = +Cornucopia,\n"
                            "3 = +DeepHarbor (cycles in order)"))
        run_rows.append(self._bool_row("RandomizeRepeats", "Randomize Repeated Biomes"))
        run_rows.append(self._bool_row("AllBiomesRandom", "All Biomes Random"))
        run_rows.append(self._label_row("Randomizes all 3 combat biome slots\n"
                            "plus extras. Camelot/Somewhere stay last."))
        right.addWidget(self._group("Increase Run Length", run_rows))

        # Wire up extra biomes toggle
        self._extra_cb.stateChanged.connect(lambda _: self._update_extra_enables())

        # Mascot image — centered in remaining space
        right.addStretch(1)
        mascot_data = base64.b64decode(_MASCOT_B64)
        mascot_pix = QPixmap()
        mascot_pix.loadFromData(mascot_data)
        mascot_label = QLabel()
        mascot_label.setPixmap(mascot_pix)
        mascot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(mascot_label, 0, Qt.AlignmentFlag.AlignCenter)
        right.addStretch(1)

        columns.addLayout(left)
        columns.addLayout(center)
        columns.addLayout(right)
        outer.addLayout(columns)

        # Bottom bar
        bottom = QHBoxLayout()
        copyright_label = QLabel("\u00a9 JJ")
        copyright_label.setStyleSheet("color: gray;")
        bottom.addWidget(copyright_label)
        bottom.addStretch()

        help_btn = QPushButton("Help")
        help_btn.setStyleSheet("QPushButton { background-color: #c62828; color: white; font-weight: bold; }"
                               "QPushButton:hover { background-color: #d32f2f; }")
        help_btn.clicked.connect(self._open_help)
        bottom.addWidget(help_btn)

        setcfg_btn = QPushButton("Set .cfg Path")
        setcfg_btn.clicked.connect(self._set_cfg_path)
        bottom.addWidget(setcfg_btn)

        import_btn = QPushButton("Import Config")
        import_btn.clicked.connect(self._import_config)
        bottom.addWidget(import_btn)

        update_btn = QPushButton("Update from GitHub")
        update_btn.clicked.connect(self._update_from_github)
        bottom.addWidget(update_btn)

        reset_btn = QPushButton("Reset to Vanilla")
        reset_btn.clicked.connect(self._reset_defaults)
        bottom.addWidget(reset_btn)

        reset_initial_btn = QPushButton("Reset to Initial")
        reset_initial_btn.setToolTip("Reset all fields to the values loaded when the app first opened")
        reset_initial_btn.clicked.connect(self._reset_to_initial)
        bottom.addWidget(reset_initial_btn)

        save_btn = QPushButton("Save")
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

        # Wire up the vanilla beast checkbox to disable/enable beast fields
        vanilla_cb = self.widgets["UseVanillaBeastSettings"]
        vanilla_cb.stateChanged.connect(self._on_vanilla_beast_toggled)
        self._on_vanilla_beast_toggled(vanilla_cb.checkState().value)

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

    def _group(self, title: str, rows: list) -> QGroupBox:
        box = QGroupBox(title)
        vbox = QVBoxLayout()
        for row in rows:
            if isinstance(row, QHBoxLayout):
                vbox.addLayout(row)
            elif isinstance(row, QWidget):
                vbox.addWidget(row)
        box.setLayout(vbox)
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

    # ── Beast vanilla toggle ────────────────────────────────────

    def _on_vanilla_beast_toggled(self, _state):
        """Disable beast fields when Use Vanilla Beast Settings is checked."""
        vanilla = self.widgets["UseVanillaBeastSettings"].isChecked()
        # Direct keys (just ForceBiomeBoss)
        for key in _BEAST_DIRECT_KEYS:
            self.widgets[key].setEnabled(not vanilla)
        # Enable checkboxes
        self._random_cb.setEnabled(not vanilla)
        self._room1_cb.setEnabled(not vanilla)
        self._room2_cb.setEnabled(not vanilla)
        # Update spinbox enable states
        self._update_beast_enables()

    def _update_extra_enables(self):
        """Update Extra Biomes spinbox enable state based on checkbox."""
        enabled = self._extra_cb.isChecked()
        self.widgets["ExtraBiomes"].setEnabled(enabled)
        self.widgets["RandomizeRepeats"].setEnabled(enabled)
        self.widgets["AllBiomesRandom"].setEnabled(enabled)

    def _update_beast_enables(self):
        """Update spinbox enable states based on vanilla toggle + individual checkboxes."""
        vanilla = self.widgets["UseVanillaBeastSettings"].isChecked()
        random_on = not vanilla and self._random_cb.isChecked()
        self.widgets["BeastChancePercent"].setEnabled(random_on)
        self.widgets["MaxBeastsPerBiome"].setEnabled(random_on)
        self.widgets["BeastRoom1"].setEnabled(not vanilla and self._room1_cb.isChecked())
        self.widgets["BeastRoom2"].setEnabled(not vanilla and self._room2_cb.isChecked())

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
        # Snapshot current widget values as "initial" for Reset to Initial
        if not self._initial_values:
            self._initial_values = self._snapshot_widgets()

    def _load_from_cfg(self, path: Path | None):
        """Load values from a cfg file. Falls back to vanilla defaults for missing keys."""
        cfg = ConfigParser()
        cfg.optionxform = str  # preserve PascalCase keys for MelonPreferences
        if path and path.exists():
            # MelonPreferences.cfg may have stray lines before section headers
            # (e.g. old mod entries). Skip lines before the first [Section].
            from io import StringIO
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

        # Set enable checkboxes based on loaded cfg values
        br1_raw = cfg.get(SECTION, "BeastRoom1", fallback=None)
        br1_val = int(br1_raw) if br1_raw is not None else VANILLA_DEFAULTS["BeastRoom1"]
        self._room1_cb.setChecked(br1_val >= 0)

        br2_raw = cfg.get(SECTION, "BeastRoom2", fallback=None)
        br2_val = int(br2_raw) if br2_raw is not None else VANILLA_DEFAULTS["BeastRoom2"]
        self._room2_cb.setChecked(br2_val >= 0)

        chance_val = self.widgets["BeastChancePercent"].value()
        self._random_cb.setChecked(chance_val > 0)

        extra_val = self.widgets["ExtraBiomes"].value()
        self._extra_cb.setChecked(extra_val > 0)

        self._update_beast_enables()
        self._update_extra_enables()

    def _save(self):
        if not self.cfg_path:
            QMessageBox.warning(self, "Error", "No game path set. Cannot save.")
            return
        cfg = ConfigParser()
        cfg.optionxform = str  # preserve PascalCase keys for MelonPreferences
        # Preserve any lines before the first section header (e.g. old mod entries)
        preamble = ""
        if self.cfg_path.exists():
            from io import StringIO
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
                # Toggle-controlled room fields: write -1 when disabled
                if key == "BeastRoom1" and not self._room1_cb.isChecked():
                    cfg.set(SECTION, key, "-1")
                elif key == "BeastRoom2" and not self._room2_cb.isChecked():
                    cfg.set(SECTION, key, "-1")
                elif key == "ExtraBiomes" and not self._extra_cb.isChecked():
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
        # Reset enable toggles (vanilla: rooms off, random off, extra off)
        self._room1_cb.setChecked(False)
        self._room2_cb.setChecked(False)
        self._random_cb.setChecked(False)
        self._extra_cb.setChecked(False)
        self._update_beast_enables()
        self._update_extra_enables()

    def _snapshot_widgets(self) -> dict[str, object]:
        """Capture current widget values as a dict."""
        snap = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                snap[key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                snap[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                snap[key] = widget.value()
        # Also snapshot toggle checkbox states
        snap["_room1_enabled"] = self._room1_cb.isChecked()
        snap["_room2_enabled"] = self._room2_cb.isChecked()
        snap["_random_enabled"] = self._random_cb.isChecked()
        snap["_extra_enabled"] = self._extra_cb.isChecked()
        return snap

    def _reset_to_initial(self):
        """Reset all fields to the values loaded when the app first opened."""
        if not self._initial_values:
            return
        for key, widget in self.widgets.items():
            val = self._initial_values.get(key)
            if val is None:
                continue
            if isinstance(widget, QCheckBox):
                widget.setChecked(val)
            elif isinstance(widget, QSpinBox):
                widget.setValue(val)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(val)
        # Restore toggle checkbox states
        self._room1_cb.setChecked(self._initial_values.get("_room1_enabled", False))
        self._room2_cb.setChecked(self._initial_values.get("_room2_enabled", False))
        self._random_cb.setChecked(self._initial_values.get("_random_enabled", False))
        self._extra_cb.setChecked(self._initial_values.get("_extra_enabled", False))
        self._update_beast_enables()
        self._update_extra_enables()

    def _start_game(self):
        """Launch SWORN via Steam."""
        QDesktopServices.openUrl(QUrl("steam://rungameid/1763250"))

    def _import_config(self):
        """Import settings from an external MelonPreferences.cfg file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import MelonPreferences.cfg", "",
            "Config files (*.cfg);;All files (*)"
        )
        if not path:
            return
        p = Path(path)
        cfg = ConfigParser()
        cfg.optionxform = str  # preserve PascalCase keys for MelonPreferences
        try:
            cfg.read(str(p))
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Could not read file:\n{e}")
            return
        if not cfg.has_section(SECTION):
            QMessageBox.warning(
                self, "Import Failed",
                f"No [{SECTION}] section found in:\n{p.name}\n\n"
                "Make sure this is a MelonPreferences.cfg with SwornTweaks settings."
            )
            return
        self._load_from_cfg(p)
        QMessageBox.information(self, "Imported", f"Settings loaded from:\n{p}")

    def _set_cfg_path(self):
        """Manually select the SWORN game folder (changes where .cfg is read/written)."""
        d = QFileDialog.getExistingDirectory(self, "Select SWORN Game Folder")
        if not d:
            return
        p = Path(d)
        cfg_file = p / "UserData" / "MelonPreferences.cfg"
        if not cfg_file.parent.is_dir():
            reply = QMessageBox.question(
                self, "UserData Not Found",
                f"No UserData/ folder found in:\n{p}\n\n"
                "Are you sure this is the SWORN game folder?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.game_path = p
        save_game_path(p)
        self._load()
        QMessageBox.information(
            self, "Path Set",
            f"Game path set to:\n{p}\n\nConfig: {cfg_file}"
        )

    @staticmethod
    def _open_help():
        """Open the README / install instructions on GitHub."""
        QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}#readme"))

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
