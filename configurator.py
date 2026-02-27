#!/usr/bin/env python3
"""SwornTweaks Configurator — lightweight PyQt6 GUI for editing MelonPreferences.cfg"""

import sys
from configparser import ConfigParser
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget, QMessageBox,
)

CFG_PATH = Path("/mnt/ext4gamedrive/SteamLibrary/steamapps/common/SWORN/UserData/MelonPreferences.cfg")
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

# Keys where cfg stores a decimal (0.03) but GUI shows percentage (3%)
_DECIMAL_PCT_KEYS = {"LegendaryChance", "EpicChance", "RareChance", "UncommonChance", "DuoChance"}


class Configurator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SwornTweaks Configurator")
        self.setMinimumWidth(700)
        self.widgets: dict[str, QWidget] = {}

        central = QWidget()
        outer = QVBoxLayout(central)

        # Two-column layout
        columns = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        # ── Left column ──────────────────────────────────────────
        left.addWidget(self._group("Rerolls", [
            self._int_row("BonusRerolls", "Bonus Rerolls", 0, 9999),
            self._bool_row("InfiniteRerolls", "Infinite Rerolls (500 per scene)"),
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

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        reset_btn = QPushButton("Reset Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

        self.setCentralWidget(central)
        self._load()

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
        """Convert cfg value to GUI display value."""
        if key in _DECIMAL_PCT_KEYS:
            return value * 100.0
        return value

    def _display_to_cfg(self, key: str, value: float) -> float:
        """Convert GUI display value to cfg value."""
        if key in _DECIMAL_PCT_KEYS:
            return value / 100.0
        return value

    # ── Load / Save / Reset ──────────────────────────────────────

    def _load(self):
        cfg = ConfigParser()
        cfg.read(str(CFG_PATH))
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
        cfg = ConfigParser()
        cfg.read(str(CFG_PATH))
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

        CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CFG_PATH, "w") as f:
            cfg.write(f)

        QMessageBox.information(self, "Saved", f"Config saved to:\n{CFG_PATH}")

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


def main():
    app = QApplication(sys.argv)
    win = Configurator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
