"""The macOS permission that the app needs.

macOS refuses to move the windows of another application unless the user gives
the Accessibility permission. macOS gives the permission to the application
that started the process. When you start the app from a terminal, give the
permission to that terminal.
"""

from __future__ import annotations

from AppKit import NSURL, NSWorkspace
from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions

_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def is_accessibility_trusted() -> bool:
    """True when macOS lets this process move the windows of other applications."""
    return bool(AXIsProcessTrusted())


def request_accessibility() -> bool:
    """Ask macOS to show the permission dialog. True when the permission is already there."""
    return bool(AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True}))


def open_accessibility_settings() -> None:
    """Open the Accessibility page of System Settings."""
    NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(_SETTINGS_URL))
