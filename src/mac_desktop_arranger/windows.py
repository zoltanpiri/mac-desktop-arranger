"""List the windows that the user can arrange, and group them by application.

The window server shows many windows that the user never sees: the menu bar,
pop-ups, tool-tips, and windows of background helpers. The app must not move
those. `list_windows` removes them with three tests:

1. The window is on layer 0. Higher layers are the menu bar and the Dock.
2. The window is not fully transparent.
3. The owner is a normal application, one with an icon in the Dock.

`arrange.py` makes a fourth test: the window must be on a desktop.
"""

from __future__ import annotations

import Quartz
from AppKit import NSApplicationActivationPolicyRegular, NSWorkspace

from .models import WindowInfo

_NORMAL_LAYER = 0


def _regular_apps_by_pid() -> dict[int, str]:
    """The applications with an icon in the Dock, keyed on process ID.

    The value is the bundle ID. The bundle ID is stable, so a preset still
    works after the user renames the application.
    """
    result: dict[int, str] = {}
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.activationPolicy() != NSApplicationActivationPolicyRegular:
            continue
        pid = int(app.processIdentifier())
        bundle_id = app.bundleIdentifier()
        name = app.localizedName()
        result[pid] = str(bundle_id or name or pid)
    return result


def list_windows() -> list[WindowInfo]:
    """Every window that the user can arrange, on any desktop."""
    options = Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements
    raw_windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or ()
    apps = _regular_apps_by_pid()

    windows: list[WindowInfo] = []
    for raw in raw_windows:
        if int(raw.get(Quartz.kCGWindowLayer, -1)) != _NORMAL_LAYER:
            continue
        if float(raw.get(Quartz.kCGWindowAlpha, 0.0)) <= 0.0:
            continue
        pid = int(raw.get(Quartz.kCGWindowOwnerPID, 0))
        app = apps.get(pid)
        if app is None:
            continue
        windows.append(
            WindowInfo(
                window_id=int(raw.get(Quartz.kCGWindowNumber, 0)),
                pid=pid,
                app=app,
                title=str(raw.get(Quartz.kCGWindowName, "") or ""),
            )
        )
    return windows


def group_by_app(windows: list[WindowInfo]) -> dict[str, list[WindowInfo]]:
    """The windows of each application, keyed on bundle ID."""
    grouped: dict[str, list[WindowInfo]] = {}
    for window in windows:
        grouped.setdefault(window.app, []).append(window)
    return grouped


def running_app_labels() -> dict[str, str]:
    """The name that the user sees for each running application, keyed on bundle ID."""
    labels: dict[str, str] = {}
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.activationPolicy() != NSApplicationActivationPolicyRegular:
            continue
        bundle_id = app.bundleIdentifier()
        name = app.localizedName()
        if bundle_id and name:
            labels[str(bundle_id)] = str(name)
    return labels


def display_name(app: str, labels: dict[str, str] | None = None) -> str:
    """The name to show in the menu.

    Uses the name of the running application. When the application does not
    run, gives the last part of the bundle ID.
    """
    if labels and app in labels:
        return labels[app]
    if "." in app and " " not in app:
        return app.rsplit(".", 1)[-1]
    return app
