"""Data types for displays, spaces, presets, and the result of an apply.

This module is pure Python. It does not import macOS frameworks, so you can
test it on any machine.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Space:
    """One desktop (macOS calls it a Space).

    `space_id` is the 64-bit system ID. It changes when you log out or when
    you add or remove a desktop. Do not put it in a preset. Use `index`.
    """

    space_id: int
    uuid: str
    index: int
    kind: str = "user"  # "user" or "fullscreen"

    @property
    def is_user_space(self) -> bool:
        return self.kind == "user"


@dataclass(frozen=True)
class Display:
    """One monitor.

    `uuid` stays the same between sessions for the same physical monitor.
    The display index does not. Always key on `uuid`.
    """

    uuid: str
    width: int = 0
    height: int = 0
    is_main: bool = False

    @property
    def label(self) -> str:
        if self.width and self.height:
            return f"{self.width}x{self.height}" + (" (main)" if self.is_main else "")
        return self.uuid[:8]


@dataclass(frozen=True)
class DisplayLayout:
    """The desktops of one monitor, in the order macOS shows them."""

    display: Display
    spaces: tuple[Space, ...]
    current_space_id: int

    @property
    def user_spaces(self) -> tuple[Space, ...]:
        return tuple(s for s in self.spaces if s.is_user_space)

    def space_at(self, index: int) -> Space | None:
        for space in self.user_spaces:
            if space.index == index:
                return space
        return None


@dataclass(frozen=True)
class Placement:
    """The rule: this app belongs on this desktop of this monitor."""

    app: str  # bundle ID when known, else the process name
    display_uuid: str
    desktop_index: int  # 1-based, counts user spaces only

    def to_dict(self) -> dict[str, Any]:
        return {
            "app": self.app,
            "display_uuid": self.display_uuid,
            "desktop_index": self.desktop_index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Placement:
        return cls(
            app=data["app"],
            display_uuid=data["display_uuid"],
            desktop_index=int(data["desktop_index"]),
        )


@dataclass(frozen=True)
class Preset:
    """A saved arrangement for one monitor setup.

    `display_uuids` keeps the monitor order at save time. `monitor_count` lets
    the app find the correct preset when the user connects or disconnects a
    monitor.
    """

    name: str
    display_uuids: tuple[str, ...]
    placements: tuple[Placement, ...]
    desktops_per_display: dict[str, int] = field(default_factory=dict)
    visible_desktops: dict[str, int] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def monitor_count(self) -> int:
        return len(self.display_uuids)

    def matches(self, display_uuids: tuple[str, ...]) -> bool:
        """True when this preset was saved for exactly these monitors."""
        return set(self.display_uuids) == set(display_uuids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_uuids": list(self.display_uuids),
            "placements": [p.to_dict() for p in self.placements],
            "desktops_per_display": dict(self.desktops_per_display),
            "visible_desktops": dict(self.visible_desktops),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Preset:
        return cls(
            name=data["name"],
            display_uuids=tuple(data.get("display_uuids", ())),
            placements=tuple(Placement.from_dict(p) for p in data.get("placements", ())),
            desktops_per_display=dict(data.get("desktops_per_display", {})),
            visible_desktops=dict(data.get("visible_desktops", {})),
            created_at=float(data.get("created_at", 0.0)),
        )


@dataclass(frozen=True)
class WindowInfo:
    """One on-screen window of one application."""

    window_id: int
    pid: int
    app: str
    title: str = ""


@dataclass
class ApplyReport:
    """What happened when the app applied a preset."""

    moved: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        parts = [f"{len(self.moved)} moved"]
        if self.skipped:
            parts.append(f"{len(self.skipped)} skipped")
        if self.failed:
            parts.append(f"{len(self.failed)} failed")
        return ", ".join(parts)
