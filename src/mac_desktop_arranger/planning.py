"""Decide what to capture and what to move.

This module holds the rules of the app. It is pure Python: it gets the current
state as arguments and gives back plain data. The macOS calls stay in
`arrange.py`. This keeps the rules easy to test.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .models import DisplayLayout, Placement, Preset, WindowInfo


@dataclass(frozen=True)
class Move:
    """Move one application to this desktop.

    macOS moves a whole application, not one window, so the move carries the
    process IDs of the application, not the window IDs. An application can run
    as more than one process.
    """

    app: str
    pids: tuple[int, ...]
    space_id: int
    display_uuid: str
    desktop_index: int


@dataclass
class MovePlan:
    moves: list[Move] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # app: reason


def _space_index_by_id(layouts: list[DisplayLayout]) -> dict[int, tuple[str, int]]:
    """Map each desktop ID to its monitor UUID and its 1-based desktop number."""
    result: dict[int, tuple[str, int]] = {}
    for layout in layouts:
        for space in layout.user_spaces:
            result[space.space_id] = (layout.display.uuid, space.index)
    return result


def capture_placements(
    layouts: list[DisplayLayout],
    windows_by_app: dict[str, list[WindowInfo]],
    space_id_by_window: dict[int, int],
) -> tuple[Placement, ...]:
    """Make one rule for each application from the current state.

    An application can have windows on more than one desktop. The rule takes
    the desktop that holds most of its windows.
    """
    index = _space_index_by_id(layouts)
    placements: list[Placement] = []

    for app, windows in sorted(windows_by_app.items()):
        counts: Counter[tuple[str, int]] = Counter()
        for window in windows:
            space_id = space_id_by_window.get(window.window_id)
            if space_id in index:
                counts[index[space_id]] += 1
        if not counts:
            continue
        (display_uuid, desktop_index), _ = counts.most_common(1)[0]
        placements.append(
            Placement(app=app, display_uuid=display_uuid, desktop_index=desktop_index)
        )

    return tuple(placements)


def desktops_per_display(layouts: list[DisplayLayout]) -> dict[str, int]:
    """The number of desktops on each monitor."""
    return {layout.display.uuid: len(layout.user_spaces) for layout in layouts}


@dataclass(frozen=True)
class Switch:
    """Show this desktop on this monitor."""

    display_uuid: str
    space_id: int
    desktop_index: int


def visible_desktops(layouts: list[DisplayLayout]) -> dict[str, int]:
    """The desktop that each monitor shows now, as a 1-based number."""
    result: dict[str, int] = {}
    for layout in layouts:
        for space in layout.user_spaces:
            if space.space_id == layout.current_space_id:
                result[layout.display.uuid] = space.index
    return result


def plan_switches(preset: Preset, layouts: list[DisplayLayout]) -> list[Switch]:
    """The monitors that must show a different desktop.

    Gives nothing for a monitor that already shows the correct desktop, for a
    monitor that is not connected, or for a desktop that does not exist.
    """
    layout_by_uuid = {layout.display.uuid: layout for layout in layouts}
    switches: list[Switch] = []

    for display_uuid, desktop_index in sorted(preset.visible_desktops.items()):
        layout = layout_by_uuid.get(display_uuid)
        if layout is None:
            continue
        space = layout.space_at(desktop_index)
        if space is None or space.space_id == layout.current_space_id:
            continue
        switches.append(
            Switch(
                display_uuid=display_uuid,
                space_id=space.space_id,
                desktop_index=desktop_index,
            )
        )

    return switches


def plan_moves(
    preset: Preset,
    layouts: list[DisplayLayout],
    windows_by_app: dict[str, list[WindowInfo]],
) -> MovePlan:
    """Work out the moves that put the applications where the preset says.

    An application is skipped, not failed, when it does not run now, or when
    its monitor is not connected. Only a missing desktop is a true problem.
    """
    plan = MovePlan()
    layout_by_uuid = {layout.display.uuid: layout for layout in layouts}

    for placement in preset.placements:
        windows = windows_by_app.get(placement.app)
        if not windows:
            plan.skipped.append(f"{placement.app}: not running")
            continue

        layout = layout_by_uuid.get(placement.display_uuid)
        if layout is None:
            plan.skipped.append(f"{placement.app}: monitor not connected")
            continue

        space = layout.space_at(placement.desktop_index)
        if space is None:
            plan.skipped.append(
                f"{placement.app}: desktop {placement.desktop_index} does not exist"
            )
            continue

        plan.moves.append(
            Move(
                app=placement.app,
                pids=tuple(sorted({w.pid for w in windows})),
                space_id=space.space_id,
                display_uuid=placement.display_uuid,
                desktop_index=placement.desktop_index,
            )
        )

    return plan


def missing_desktops(preset: Preset, layouts: list[DisplayLayout]) -> dict[str, int]:
    """Monitors that have fewer desktops than the preset needs.

    Gives the monitor UUID and the number of desktops to add. macOS gives no
    API to add a desktop, so the user must add them in Mission Control.
    """
    have = desktops_per_display(layouts)
    need: dict[str, int] = {}
    for placement in preset.placements:
        current = need.get(placement.display_uuid, 0)
        need[placement.display_uuid] = max(current, placement.desktop_index)

    missing: dict[str, int] = {}
    for uuid, count in need.items():
        if uuid in have and have[uuid] < count:
            missing[uuid] = count - have[uuid]
    return missing
