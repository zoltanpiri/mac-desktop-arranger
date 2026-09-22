"""Read and write the saved presets.

This module is pure Python and takes the store path as an argument, so you can
test it without touching the home directory of the user.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import SCHEMA_VERSION, Preset

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "mac-desktop-arranger"
PRESETS_FILE = APP_SUPPORT_DIR / "presets.json"


class PresetStore:
    """The set of presets on disk, keyed on the preset name."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else PRESETS_FILE

    def load(self) -> dict[str, Preset]:
        """Every saved preset. Gives an empty dict when the file is absent or bad."""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        if not isinstance(raw, dict):
            return {}

        presets: dict[str, Preset] = {}
        for item in raw.get("presets", ()):
            try:
                preset = Preset.from_dict(item)
            except (KeyError, TypeError, ValueError):
                continue  # Keep the good presets. Drop the bad one.
            presets[preset.name] = preset
        return presets

    def save_all(self, presets: dict[str, Preset]) -> None:
        """Write every preset. Writes to a temporary file first, then renames it,
        so a crash cannot leave a half-written file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "presets": [preset.to_dict() for preset in presets.values()],
        }
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def put(self, preset: Preset) -> None:
        """Add the preset, or replace the one with the same name."""
        presets = self.load()
        presets[preset.name] = preset
        self.save_all(presets)

    def delete(self, name: str) -> bool:
        """Remove one preset. False when no preset has this name."""
        presets = self.load()
        if name not in presets:
            return False
        del presets[name]
        self.save_all(presets)
        return True

    def get(self, name: str) -> Preset | None:
        return self.load().get(name)

    def names(self) -> list[str]:
        """The preset names, sorted by monitor count, then by name."""
        presets = self.load()
        return sorted(presets, key=lambda n: (presets[n].monitor_count, n.lower()))

    def for_displays(self, display_uuids: tuple[str, ...]) -> list[Preset]:
        """The presets that were saved for exactly these monitors."""
        return [p for p in self.load().values() if p.matches(display_uuids)]

    def for_monitor_count(self, count: int) -> list[Preset]:
        """The presets that were saved for this number of monitors."""
        return [p for p in self.load().values() if p.monitor_count == count]
