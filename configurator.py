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

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap, QFont, QPen
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

VERSION = "1.4.0"
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
    "PlayerHealthMultiplier": 1.0,
    "EnemyHealthMultiplier": 1.0,
    "EnemyDamageMultiplier": 1.0,
    "ChaosMode": False,
}

# Keys for beast section that get disabled when UseVanillaBeastSettings is checked
_BEAST_KEYS = ("BeastChancePercent", "MaxBeastsPerBiome", "BeastRoom1", "BeastRoom2")

_DECIMAL_PCT_KEYS = {"LegendaryChance", "EpicChance", "RareChance", "UncommonChance", "DuoChance"}


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

        left.addWidget(self._group("Player", [
            self._float_row("PlayerHealthMultiplier", "Health Multiplier", 0.1, 50.0, "x"),
        ]))

        left.addWidget(self._group("Blessing Selection", [
            self._bool_row("ChaosMode", "Chaos Mode"),
            self._label_row("Bypass all blessing prerequisites"),
        ]))

        left.addStretch()

        # ── Center column ─────────────────────────────────────────
        center.addWidget(self._group("Beast Boss Room Spawns", [
            self._bool_row("UseVanillaBeastSettings", "Use Vanilla Beast Settings"),
            self._pct_row("BeastChancePercent", "Random Chance", 0, 100),
            self._int_row("MaxBeastsPerBiome", "Max per Biome", 0, 15),
            self._int_row("BeastRoom1", "Fixed Beast Room 1", -1, MAX_FIXED_ROOM),
            self._int_row("BeastRoom2", "Fixed Beast Room 2", -1, MAX_FIXED_ROOM),
        ]))

        center.addWidget(self._group("Health Multipliers", [
            self._float_row("BossHealthMultiplier", "Boss Health", 0.1, 50.0, "x"),
            self._float_row("BeastHealthMultiplier", "Beast Health", 0.1, 50.0, "x"),
        ]))

        center.addWidget(self._group("Intensity", [
            self._float_row("IntensityMultiplier", "Room Intensity", 0.1, 10.0, "x"),
            self._label_row("Scales enemy spawn count per room."),
        ]))

        center.addWidget(self._group("Enemy Scaling", [
            self._float_row("EnemyHealthMultiplier", "Enemy Health", 0.1, 50.0, "x"),
            self._float_row("EnemyDamageMultiplier", "Enemy Damage", 0.1, 50.0, "x"),
            self._label_row("Affects normal enemies only.\nBoss/beast health has its own multipliers."),
        ]))

        center.addStretch()

        # ── Right column ──────────────────────────────────────────
        right.addWidget(self._group("Increase Run Length", [
            self._int_row("ExtraBiomes", "Extra Biomes", 0, 3),
            self._label_row("Adds combat biomes after DeepHarbor.\n"
                            "1 = +Kingswood, 2 = +Cornucopia,\n"
                            "3 = +DeepHarbor (cycles in order)"),
            self._bool_row("RandomizeRepeats", "Randomize Repeated Biomes"),
            self._bool_row("AllBiomesRandom", "All Biomes Random"),
            self._label_row("Randomizes all 3 combat biome slots\n"
                            "plus extras. Camelot/Somewhere stay last."),
        ]))

        right.addStretch()

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

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        bottom.addWidget(save_btn)

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

    def _label_row(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: gray; font-size: 11px;")
        lbl.setWordWrap(True)
        return lbl

    # ── Beast vanilla toggle ────────────────────────────────────

    def _on_vanilla_beast_toggled(self, _state):
        """Disable beast fields when Use Vanilla Beast Settings is checked."""
        checked = self.widgets["UseVanillaBeastSettings"].isChecked()
        for key in _BEAST_KEYS:
            w = self.widgets[key]
            w.setEnabled(not checked)
            if checked:
                default = VANILLA_DEFAULTS[key]
                if isinstance(w, QSpinBox):
                    w.setValue(default)
                elif isinstance(w, QDoubleSpinBox):
                    w.setValue(self._cfg_to_display(key, default))

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
        if path and path.exists():
            cfg.read(str(path))
        for key, widget in self.widgets.items():
            default = VANILLA_DEFAULTS[key]
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
        """Reset all fields to vanilla game values (unmodded behavior)."""
        for key, widget in self.widgets.items():
            default = VANILLA_DEFAULTS[key]
            if isinstance(widget, QCheckBox):
                widget.setChecked(default)
            elif isinstance(widget, QComboBox):
                idx = widget.findText(default, Qt.MatchFlag.MatchFixedString)
                widget.setCurrentIndex(max(idx, 0))
            elif isinstance(widget, QSpinBox):
                widget.setValue(default)
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(self._cfg_to_display(key, default))

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
        script_path = Path(__file__).resolve() if "__file__" in dir() else Path(sys.argv[0]).resolve()
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
