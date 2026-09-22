"""Find the connected monitors and give each one a stable key.

macOS can change the display index when you connect or disconnect a monitor.
The display UUID does not change, so the app keys on the UUID.

PyObjC does not publish `CGDisplayCreateUUIDFromDisplayID`, although the
function is public. This module loads it from the ColorSync framework.
"""

from __future__ import annotations

import objc
import Quartz
from CoreFoundation import CFUUIDCreateString
from Foundation import NSBundle

from .models import Display

_MAX_DISPLAYS = 16
_COLORSYNC_PATH = "/System/Library/Frameworks/ColorSync.framework"

_colorsync: dict[str, object] = {}


def _load_colorsync() -> dict[str, object]:
    """Load `CGDisplayCreateUUIDFromDisplayID` one time and keep it."""
    if _colorsync:
        return _colorsync
    bundle = NSBundle.bundleWithPath_(_COLORSYNC_PATH)
    if bundle is None:
        return _colorsync
    namespace: dict[str, object] = {}
    objc.loadBundleFunctions(bundle, namespace, [("CGDisplayCreateUUIDFromDisplayID", b"@I")])
    _colorsync.update(namespace)
    return _colorsync


def _display_uuid(display_id: int) -> str | None:
    """The UUID string of one display, or None when macOS does not give it."""
    create = _load_colorsync().get("CGDisplayCreateUUIDFromDisplayID")
    if create is None:
        return None
    uuid_ref = create(display_id)
    if uuid_ref is None:
        return None
    text = CFUUIDCreateString(None, uuid_ref)
    return str(text) if text else None


def active_displays() -> list[Display]:
    """Every monitor that shows a desktop now, main monitor first."""
    error, display_ids, _count = Quartz.CGGetActiveDisplayList(_MAX_DISPLAYS, None, None)
    if error != 0 or not display_ids:
        return []

    main_id = Quartz.CGMainDisplayID()
    displays: list[Display] = []
    for display_id in display_ids:
        uuid = _display_uuid(display_id)
        if not uuid:
            continue
        bounds = Quartz.CGDisplayBounds(display_id)
        displays.append(
            Display(
                uuid=uuid,
                width=int(bounds.size.width),
                height=int(bounds.size.height),
                is_main=(display_id == main_id),
            )
        )

    displays.sort(key=lambda d: (not d.is_main, d.uuid))
    return displays


def displays_by_uuid() -> dict[str, Display]:
    """The connected monitors in a dict, keyed on the stable UUID."""
    return {display.uuid: display for display in active_displays()}
