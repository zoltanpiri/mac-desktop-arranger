"""Read the current arrangement, and put the applications back.

This is the only module that joins the macOS calls to the rules in
`planning.py`.
"""

from __future__ import annotations

from . import displays, spaces, windows
from .models import ApplyReport, DisplayLayout, Preset, WindowInfo
from .planning import (
    capture_placements,
    desktops_per_display,
    missing_desktops,
    plan_moves,
    plan_switches,
    visible_desktops,
)


def current_layouts() -> list[DisplayLayout]:
    """The monitors with their desktops, as macOS holds them now."""
    return spaces.read_layouts(displays.displays_by_uuid())


def current_display_uuids() -> tuple[str, ...]:
    """The UUIDs of the connected monitors, sorted, for a preset match."""
    return tuple(sorted(display.uuid for display in displays.active_displays()))


def _windows_on_desktops() -> tuple[dict[str, list[WindowInfo]], dict[int, int]]:
    """The arrangeable windows that sit on a desktop, and the desktop of each.

    A window that is on no desktop is a system window, such as the menu bar.
    This function removes it.
    """
    candidates = windows.list_windows()
    space_by_window = spaces.space_id_by_window([w.window_id for w in candidates])
    on_desktop = [w for w in candidates if w.window_id in space_by_window]
    return windows.group_by_app(on_desktop), space_by_window


def capture(name: str) -> Preset:
    """Make a preset from the arrangement on the screen now."""
    layouts = current_layouts()
    grouped, space_by_window = _windows_on_desktops()

    return Preset(
        name=name,
        display_uuids=current_display_uuids(),
        placements=capture_placements(layouts, grouped, space_by_window),
        desktops_per_display=desktops_per_display(layouts),
        visible_desktops=visible_desktops(layouts),
    )


def apply(preset: Preset) -> ApplyReport:
    """Move the windows of each application to the desktop of the preset."""
    report = ApplyReport()
    layouts = current_layouts()
    if not layouts:
        report.failed.append("cannot read the desktops: " + (spaces.unavailable_reason() or "?"))
        return report

    for uuid, count in missing_desktops(preset, layouts).items():
        report.failed.append(f"monitor {uuid[:8]} needs {count} more desktop(s)")

    grouped, _ = _windows_on_desktops()
    plan = plan_moves(preset, layouts, grouped)
    labels = windows.running_app_labels()
    report.skipped.extend(plan.skipped)

    for move in plan.moves:
        name = windows.display_name(move.app, labels)
        done = all(spaces.assign_process_to_space(pid, move.space_id) for pid in move.pids)
        # Always release, so the user keeps control of the application.
        for pid in move.pids:
            spaces.release_process(pid)
        if done:
            report.moved.append(f"{name} → desktop {move.desktop_index}")
        else:
            report.failed.append(f"{name}: the move failed")

    # Last, show the desktop that each monitor showed when the user saved.
    labels_by_uuid = monitor_labels()
    for switch in plan_switches(preset, layouts):
        label = labels_by_uuid.get(switch.display_uuid, switch.display_uuid[:8])
        if spaces.show_space(switch.display_uuid, switch.space_id):
            report.moved.append(f"{label} shows desktop {switch.desktop_index}")
        else:
            report.failed.append(f"{label}: cannot show desktop {switch.desktop_index}")

    return report


def monitor_labels() -> dict[str, str]:
    """A short name for each monitor. Adds a number when two are the same."""
    active = displays.active_displays()
    labels: dict[str, str] = {}
    seen: dict[str, int] = {}
    for display in active:
        base = display.label
        seen[base] = seen.get(base, 0) + 1
        labels[display.uuid] = base
    counted: dict[str, int] = {}
    for display in active:
        base = display.label
        if seen[base] > 1:
            counted[base] = counted.get(base, 0) + 1
            labels[display.uuid] = f"{base} #{counted[base]}"
    return labels


def describe_current() -> str:
    """A short text of the current arrangement, for the menu bar."""
    layouts = current_layouts()
    if not layouts:
        return "Cannot read the desktops."
    labels = monitor_labels()
    lines = []
    for layout in layouts:
        current = next(
            (s.index for s in layout.user_spaces if s.space_id == layout.current_space_id), 0
        )
        label = labels.get(layout.display.uuid, layout.display.label)
        lines.append(f"{label}: desktop {current} of {len(layout.user_spaces)}")
    return "\n".join(lines)
