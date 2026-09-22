"""The menu bar application."""

from __future__ import annotations

import rumps

from . import arrange, permissions, spaces
from .models import Preset
from .presets import PresetStore

TITLE = "🖥"
REFRESH_SECONDS = 15


class ArrangerApp(rumps.App):
    """A menu bar item that saves and applies desktop arrangements."""

    def __init__(self, store: PresetStore | None = None) -> None:
        super().__init__(TITLE, quit_button="Quit")
        self.store = store or PresetStore()
        self._build_menu()
        self._timer = rumps.Timer(self._on_tick, REFRESH_SECONDS)
        self._timer.start()

    # --- menu ---------------------------------------------------------------

    def _build_menu(self) -> None:
        self.menu.clear()

        reason = spaces.unavailable_reason()
        if reason:
            warning = rumps.MenuItem(f"⚠️ {reason}")
            warning.set_callback(None)
            self.menu.add(warning)
            self.menu.add(rumps.separator)

        if not permissions.is_accessibility_trusted():
            self.menu.add(
                rumps.MenuItem(
                    "⚠️ Give the Accessibility permission…", callback=self._on_permission
                )
            )
            self.menu.add(rumps.separator)

        for line in arrange.describe_current().splitlines():
            item = rumps.MenuItem(line)
            item.set_callback(None)  # Text only. Not clickable.
            self.menu.add(item)
        self.menu.add(rumps.separator)

        self.menu.add(rumps.MenuItem("Save current arrangement…", callback=self._on_save))

        names = self.store.names()
        apply_menu = rumps.MenuItem("Apply preset")
        delete_menu = rumps.MenuItem("Delete preset")
        if names:
            presets = self.store.load()
            for name in names:
                count = presets[name].monitor_count
                label = f"{name}  ({count} monitor{'s' if count != 1 else ''})"
                apply_menu.add(rumps.MenuItem(label, callback=self._make_apply(name)))
                delete_menu.add(rumps.MenuItem(label, callback=self._make_delete(name)))
        else:
            empty = rumps.MenuItem("No presets yet")
            empty.set_callback(None)
            apply_menu.add(empty)
        self.menu.add(apply_menu)
        if names:
            self.menu.add(delete_menu)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Refresh", callback=self._on_refresh))

    def _make_apply(self, name: str):
        def callback(_sender: rumps.MenuItem) -> None:
            self._apply(name)

        return callback

    def _make_delete(self, name: str):
        def callback(_sender: rumps.MenuItem) -> None:
            self._delete(name)

        return callback

    # --- actions ------------------------------------------------------------

    def _on_tick(self, _timer: rumps.Timer) -> None:
        self._build_menu()

    def _on_refresh(self, _sender: rumps.MenuItem) -> None:
        self._build_menu()

    def _on_permission(self, _sender: rumps.MenuItem) -> None:
        if permissions.request_accessibility():
            self._build_menu()
            return
        permissions.open_accessibility_settings()
        rumps.alert(
            "Accessibility permission",
            "Switch on this app in System Settings → Privacy & Security → "
            "Accessibility. Without it macOS does not let the app move the windows "
            "of other applications.",
        )

    def _on_save(self, _sender: rumps.MenuItem) -> None:
        count = len(arrange.current_display_uuids())
        default = f"{count} monitor setup"
        window = rumps.Window(
            message="Name for this arrangement:",
            title="Save preset",
            default_text=default,
            ok="Save",
            cancel="Cancel",
            dimensions=(260, 22),
        )
        response = window.run()
        if not response.clicked:
            return

        name = response.text.strip()
        if not name:
            rumps.alert("Save preset", "Give the preset a name.")
            return

        if self.store.get(name) is not None:
            confirm = rumps.alert(
                "Replace preset?",
                f"A preset with the name “{name}” exists. Replace it?",
                ok="Replace",
                cancel="Cancel",
            )
            if not confirm:
                return

        preset = arrange.capture(name)
        if not preset.placements:
            rumps.alert("Save preset", "Found no application windows to save.")
            return

        self.store.put(preset)
        self._build_menu()
        rumps.alert(
            "Preset saved",
            f"“{name}” holds {len(preset.placements)} application(s) "
            f"on {preset.monitor_count} monitor(s).",
        )

    def _apply(self, name: str) -> None:
        preset: Preset | None = self.store.get(name)
        if preset is None:
            rumps.alert("Apply preset", f"The preset “{name}” is gone.")
            return

        current = arrange.current_display_uuids()
        if not preset.matches(current):
            confirm = rumps.alert(
                "Different monitors",
                f"“{name}” was saved for {preset.monitor_count} monitor(s) that are "
                f"not all connected. Apply the part that fits?",
                ok="Apply",
                cancel="Cancel",
            )
            if not confirm:
                return

        report = arrange.apply(preset)
        lines = [report.summary()]
        for group in (report.failed, report.skipped):
            lines.extend(f"• {entry}" for entry in group[:8])
        rumps.alert(f"Applied “{name}”", "\n".join(lines))
        self._build_menu()

    def _delete(self, name: str) -> None:
        confirm = rumps.alert(
            "Delete preset?", f"Delete “{name}”?", ok="Delete", cancel="Cancel"
        )
        if not confirm:
            return
        self.store.delete(name)
        self._build_menu()


def run() -> None:
    ArrangerApp().run()
