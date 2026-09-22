"""Helpers to build a fake macOS state for the tests.

The tests import only the pure modules (`models`, `presets`, `planning`), so
they run without the macOS frameworks.
"""

from __future__ import annotations

import pytest

from mac_desktop_arranger.models import Display, DisplayLayout, Space, WindowInfo

MAIN = "37D8832A-2D66-02CA-B9F7-8F30A301B230"
SIDE = "9B2A1C44-1111-4E2F-9C0E-2A1B3C4D5E6F"


def make_layout(uuid: str, desktop_count: int, current: int = 1, base: int = 100) -> DisplayLayout:
    """A monitor with `desktop_count` user desktops. Desktop IDs start at `base`."""
    spaces = tuple(
        Space(space_id=base + i, uuid=f"space-{base + i}", index=i, kind="user")
        for i in range(1, desktop_count + 1)
    )
    return DisplayLayout(
        display=Display(uuid=uuid, width=3840, height=2160, is_main=(base == 100)),
        spaces=spaces,
        current_space_id=base + current,
    )


@pytest.fixture
def two_monitors() -> list[DisplayLayout]:
    return [make_layout(MAIN, 3, base=100), make_layout(SIDE, 2, base=200)]


@pytest.fixture
def windows() -> dict[str, list[WindowInfo]]:
    return {
        "com.apple.Safari": [WindowInfo(window_id=1, pid=10, app="com.apple.Safari")],
        "com.jetbrains.pycharm": [
            WindowInfo(window_id=2, pid=20, app="com.jetbrains.pycharm"),
            WindowInfo(window_id=3, pid=20, app="com.jetbrains.pycharm"),
        ],
        "com.tinyspeck.slackmacgap": [
            WindowInfo(window_id=4, pid=30, app="com.tinyspeck.slackmacgap")
        ],
    }
