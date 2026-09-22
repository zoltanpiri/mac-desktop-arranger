"""Bindings to the private SkyLight window-server API.

macOS gives no public API to read or change the Space (desktop) of a window.
This module loads the necessary functions from the SkyLight private framework.

Risk: these symbols are private. Apple can change or remove them in a macOS
update. Every function here fails in a safe manner: it raises
`SkyLightUnavailable`, or it returns an empty result. Never let a failure here
stop the menu bar app.
"""

from __future__ import annotations

import objc
from Foundation import NSBundle

from .models import Display, DisplayLayout, Space

_SKYLIGHT_PATH = "/System/Library/PrivateFrameworks/SkyLight.framework"

# name, signature. "@" = object, "i" = int32, "Q" = uint64, "v" = void.
_FUNCTIONS = [
    ("SLSMainConnectionID", b"i"),
    ("SLSCopyManagedDisplaySpaces", b"@i"),
    ("SLSProcessAssignToSpace", b"iiiQ"),
    ("SLSManagedDisplaySetCurrentSpace", b"vi@Q"),
    ("SLSCopyActiveMenuBarDisplayIdentifier", b"@i"),
    ("SLSCopySpacesForWindows", b"@ii@"),
]

_loaded: dict[str, object] = {}
_load_error: str | None = None


class SkyLightUnavailable(RuntimeError):
    """The private window-server API is not available on this system."""


def _load() -> dict[str, object]:
    """Load the SkyLight functions one time and keep them."""
    global _load_error
    if _loaded or _load_error:
        if _load_error:
            raise SkyLightUnavailable(_load_error)
        return _loaded

    bundle = NSBundle.bundleWithPath_(_SKYLIGHT_PATH)
    if bundle is None:
        _load_error = f"cannot open {_SKYLIGHT_PATH}"
        raise SkyLightUnavailable(_load_error)

    namespace: dict[str, object] = {}
    missing = objc.loadBundleFunctions(bundle, namespace, _FUNCTIONS)
    if missing:
        _load_error = "missing SkyLight symbols: " + ", ".join(str(m) for m in missing)
        raise SkyLightUnavailable(_load_error)

    _loaded.update(namespace)
    return _loaded


def is_available() -> bool:
    """True when this Mac gives the private API that the app needs."""
    try:
        _load()
    except SkyLightUnavailable:
        return False
    return True


def unavailable_reason() -> str | None:
    """The reason the private API does not work, or None when it works."""
    try:
        _load()
    except SkyLightUnavailable as error:
        return str(error)
    return None


def connection_id() -> int:
    """The window-server connection of this process."""
    return int(_load()["SLSMainConnectionID"]())


def _space_kind(raw: int) -> str:
    # 0 = user desktop, 4 = full-screen application.
    return "user" if int(raw) == 0 else "fullscreen"


def read_layouts(displays_by_uuid: dict[str, Display] | None = None) -> list[DisplayLayout]:
    """Read every monitor with its desktops, in the order macOS keeps them.

    Returns an empty list when the private API does not answer.
    """
    try:
        functions = _load()
        cid = int(functions["SLSMainConnectionID"]())
        raw_displays = functions["SLSCopyManagedDisplaySpaces"](cid)
    except SkyLightUnavailable:
        return []
    if raw_displays is None:
        return []

    displays_by_uuid = displays_by_uuid or {}
    layouts: list[DisplayLayout] = []

    for raw_display in raw_displays:
        uuid = str(raw_display.get("Display Identifier", ""))
        if not uuid:
            continue

        spaces: list[Space] = []
        user_index = 0
        for raw_space in raw_display.get("Spaces", ()) or ():
            kind = _space_kind(raw_space.get("type", 0))
            if kind == "user":
                user_index += 1
            spaces.append(
                Space(
                    space_id=int(raw_space.get("id64", 0)),
                    uuid=str(raw_space.get("uuid", "")),
                    index=user_index if kind == "user" else 0,
                    kind=kind,
                )
            )

        current = raw_display.get("Current Space") or {}
        display = displays_by_uuid.get(uuid) or Display(uuid=uuid)
        layouts.append(
            DisplayLayout(
                display=display,
                spaces=tuple(spaces),
                current_space_id=int(current.get("id64", 0)),
            )
        )

    return layouts


def assign_process_to_space(pid: int, space_id: int) -> bool:
    """Move every window of this application to this desktop.

    macOS gives no way to move one window. It moves the whole application.
    This is the same operation as “Assign To” in the Dock menu.

    Do not use `SLSMoveWindowsToManagedSpace` for this. That function reports
    success and does nothing, because macOS refuses a window-level move from a
    process without privilege.
    """
    if not pid or not space_id:
        return False
    try:
        functions = _load()
        cid = int(functions["SLSMainConnectionID"]())
        error = int(functions["SLSProcessAssignToSpace"](cid, int(pid), int(space_id)))
    except SkyLightUnavailable:
        return False
    return error == 0


def release_process(pid: int) -> bool:
    """Release the desktop binding of this application.

    The windows stay where they are. Without this call the application stays
    tied to that desktop, and the user can no longer move it by hand.
    """
    if not pid:
        return False
    try:
        functions = _load()
        cid = int(functions["SLSMainConnectionID"]())
        error = int(functions["SLSProcessAssignToSpace"](cid, int(pid), 0))
    except SkyLightUnavailable:
        return False
    return error == 0


def show_space(display_uuid: str, space_id: int) -> bool:
    """Make this desktop the visible one on this monitor."""
    if not display_uuid or not space_id:
        return False
    try:
        functions = _load()
        cid = int(functions["SLSMainConnectionID"]())
        functions["SLSManagedDisplaySetCurrentSpace"](cid, display_uuid, space_id)
    except SkyLightUnavailable:
        return False
    return True


# Ask for every space, visible or not.
_ALL_SPACES_MASK = 0x7


def space_for_window(window_id: int) -> int | None:
    """The desktop that holds this window, or None.

    None also means that the window is not on a desktop at all: the menu bar,
    a pop-up, and other system windows give None. Use this to tell a true
    application window from a system window.
    """
    try:
        functions = _load()
        cid = int(functions["SLSMainConnectionID"]())
        raw = functions["SLSCopySpacesForWindows"](cid, _ALL_SPACES_MASK, [int(window_id)])
    except SkyLightUnavailable:
        return None
    if not raw:
        return None
    return int(raw[0])


def space_id_by_window(window_ids: list[int]) -> dict[int, int]:
    """The desktop of each window. Windows that are on no desktop are absent.

    The window server gives a set, not a list, when you ask for many windows
    together. Thus this function asks for one window at a time.
    """
    result: dict[int, int] = {}
    for window_id in window_ids:
        space_id = space_for_window(window_id)
        if space_id:
            result[window_id] = space_id
    return result
