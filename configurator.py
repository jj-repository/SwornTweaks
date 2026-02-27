#!/usr/bin/env python3
"""SwornTweaks Configurator — lightweight PyQt6 GUI for editing MelonPreferences.cfg"""

import json
import os
import platform
import sys
import urllib.error
import urllib.request
from configparser import ConfigParser
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

VERSION = "1.1.0"
GITHUB_REPO = "jj-repository/SwornTweaks"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
GITHUB_DLL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/SwornTweaks.dll"
SECTION = "SwornTweaks"
BIOMES = ["Kingswood", "Cornucopia", "DeepHarbor", "Camelot", "Somewhere"]

DEFAULTS = {
    "BonusRerolls": 50,
    "InfiniteRerolls": False,
    "LegendaryChance": 0.03,
    "EpicChance": 0.08,
    "RareChance": 0.20,
    "UncommonChance": 0.25,
    "NoGemCost": True,
    "NoCurrencyDoorRewards": True,
    "DuoChance": 0.35,
    "EnableBiomeRepeat": True,
    "RepeatBiome": "Kingswood",
    "RepeatAfterBiome": "Cornucopia",
    "BeastChancePercent": 0.0,
    "BeastRoom1": 4,
    "BeastRoom2": 8,
    "BossHealthMultiplier": 2.0,
    "BeastHealthMultiplier": 2.0,
}

_DECIMAL_PCT_KEYS = {"LegendaryChance", "EpicChance", "RareChance", "UncommonChance", "DuoChance"}


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
        # Common custom library locations
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
    """Path to store configurator settings (game path cache)."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "SwornTweaks" / "configurator.json"


def load_game_path() -> Path | None:
    """Load cached game path from settings."""
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
    """Cache game path to settings."""
    sp = settings_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"game_path": str(path)}))


class UpdateWorker(QThread):
    """Background thread for downloading updates from GitHub."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, mods_dir: Path):
        super().__init__()
        self.mods_dir = mods_dir

    def run(self):
        try:
            dll_path = self.mods_dir / "SwornTweaks.dll"
            urllib.request.urlretrieve(GITHUB_DLL, str(dll_path))
            self.finished.emit(str(dll_path))
        except Exception as e:
            self.error.emit(str(e))


class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SwornTweaks Configurator v{VERSION}")
        self.setMinimumWidth(700)
        self.widgets: dict[str, QWidget] = {}
        self._update_worker: UpdateWorker | None = None

        # Resolve game path
        self.game_path = load_game_path() or find_game_path()
        if self.game_path is None:
            self.game_path = self._ask_game_path()
        if self.game_path:
            save_game_path(self.game_path)

        central = QWidget()
        outer = QVBoxLayout(central)

        # Two-column layout
        columns = QHBoxLayout()
        left = QVBoxLayout()
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

        left.addStretch()

        # ── Right column ─────────────────────────────────────────
        right.addWidget(self._group("Biome Repeat", [
            self._bool_row("EnableBiomeRepeat", "Enable Biome Repeat"),
            self._combo_row("RepeatBiome", "Repeat Biome", BIOMES),
            self._combo_row("RepeatAfterBiome", "Repeat After", BIOMES),
        ]))

        right.addWidget(self._group("Beast Rooms", [
            self._pct_row("BeastChancePercent", "Random Chance", 0, 100),
            self._int_row("BeastRoom1", "Hardset Room 1", -1, 20),
            self._int_row("BeastRoom2", "Hardset Room 2", -1, 20),
        ]))

        right.addWidget(self._group("Health Multipliers", [
            self._float_row("BossHealthMultiplier", "Boss Health", 0.1, 50.0, "x"),
            self._float_row("BeastHealthMultiplier", "Beast Health", 0.1, 50.0, "x"),
        ]))

        right.addStretch()

        columns.addLayout(left)
        columns.addLayout(right)
        outer.addLayout(columns)

        # Bottom bar: copyright left, buttons right
        bottom = QHBoxLayout()
        copyright_label = QLabel("\u00a9 JJ")
        copyright_label.setStyleSheet("color: gray;")
        bottom.addWidget(copyright_label)
        bottom.addStretch()

        update_btn = QPushButton("Update from GitHub")
        update_btn.clicked.connect(self._update_from_github)
        bottom.addWidget(update_btn)

        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        bottom.addWidget(reset_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        bottom.addWidget(save_btn)

        outer.addLayout(bottom)

        self.setCentralWidget(central)
        self._load()

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

    def _group(self, title: str, rows: list[QHBoxLayout]) -> QGroupBox:
        box = QGroupBox(title)
        vbox = QVBoxLayout()
        for row in rows:
            vbox.addLayout(row)
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

    def _combo_row(self, key: str, label: str, items: list[str]) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addStretch()
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedWidth(140)
        self.widgets[key] = combo
        row.addWidget(combo)
        return row

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
        cfg = ConfigParser()
        if self.cfg_path and self.cfg_path.exists():
            cfg.read(str(self.cfg_path))
        for key, widget in self.widgets.items():
            default = DEFAULTS[key]
            raw = cfg.get(SECTION, key, fallback=None)
            if isinstance(widget, QCheckBox):
                val = raw.lower() in ("true", "1", "yes") if raw is not None else default
                widget.setChecked(val)
            elif isinstance(widget, QComboBox):
                val = raw if raw is not None else default
                idx = widget.findText(val, Qt.MatchFlag.MatchFixedString)
                widget.setCurrentIndex(max(idx, 0))
            elif isinstance(widget, QSpinBox):
                val = int(raw) if raw is not None else default
                widget.setValue(val)
            elif isinstance(widget, QDoubleSpinBox):
                val = float(raw) if raw is not None else default
                widget.setValue(self._cfg_to_display(key, val))

    def _save(self):
        if not self.cfg_path:
            QMessageBox.warning(self, "Error", "No game path set. Cannot save.")
            return
        cfg = ConfigParser()
        if self.cfg_path.exists():
            cfg.read(str(self.cfg_path))
        if not cfg.has_section(SECTION):
            cfg.add_section(SECTION)
        for key, widget in self.widgets.items():
            if isinstance(widget, QCheckBox):
                cfg.set(SECTION, key, str(widget.isChecked()).lower())
            elif isinstance(widget, QComboBox):
                cfg.set(SECTION, key, widget.currentText())
            elif isinstance(widget, QSpinBox):
                cfg.set(SECTION, key, str(widget.value()))
            elif isinstance(widget, QDoubleSpinBox):
                val = self._display_to_cfg(key, widget.value())
                cfg.set(SECTION, key, f"{val:g}")

        self.cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cfg_path, "w") as f:
            cfg.write(f)

        QMessageBox.information(self, "Saved", f"Config saved to:\n{self.cfg_path}")

    def _reset_defaults(self):
        for key, widget in self.widgets.items():
            default = DEFAULTS[key]
            if isinstance(widget, QCheckBox):
                widget.setChecked(default)
            elif isinstance(widget, QComboBox):
                idx = widget.findText(default, Qt.MatchFlag.MatchFixedString)
                widget.setCurrentIndex(max(idx, 0))
            elif isinstance(widget, QSpinBox):
                widget.setValue(default)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(self._cfg_to_display(key, default))

    # ── Update from GitHub ───────────────────────────────────────

    def _update_from_github(self):
        if not self.mods_path:
            QMessageBox.warning(self, "Error", "No game path set. Cannot update.")
            return
        if not self.mods_path.is_dir():
            QMessageBox.warning(self, "Error", f"Mods folder not found:\n{self.mods_path}")
            return

        reply = QMessageBox.question(
            self, "Update",
            f"Download latest SwornTweaks.dll from GitHub and install to:\n{self.mods_path}\n\nProceed?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._update_worker = UpdateWorker(self.mods_path)
        self._update_worker.finished.connect(self._on_update_done)
        self._update_worker.error.connect(self._on_update_error)
        self._update_worker.start()

    def _on_update_done(self, path: str):
        QMessageBox.information(self, "Updated", f"SwornTweaks.dll updated:\n{path}")
        self._update_worker = None

    def _on_update_error(self, err: str):
        QMessageBox.critical(self, "Update Failed", f"Failed to download update:\n{err}")
        self._update_worker = None


def main():
    app = QApplication(sys.argv)
    win = Configurator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
