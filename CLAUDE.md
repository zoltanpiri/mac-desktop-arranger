# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

The project uses `uv`. Never call `pip` or a bare `python`.

```sh
uv sync                                # make .venv and install everything
uv run mac-desktop-arranger            # start the menu bar app
uv run python -m mac_desktop_arranger  # the same, without the script
uv run pytest                          # all tests
uv run pytest tests/test_planning.py::test_plan_skips_an_application_that_does_not_run  # one test
uv run ruff check . --fix              # lint
```

The app needs the **Accessibility** permission. macOS gives it to the application that starts
the process, so a run from a terminal needs that terminal switched on in
System Settings → Privacy & Security → Accessibility. Without it, every move fails in silence.

## Layers

The code is in three layers. Keep them apart. This is the main rule of the repository.

1. **Pure rules** — `models.py`, `planning.py`, `presets.py`.
   No macOS import. All the decisions live here: which desktop an application belongs to,
   which applications to move, which monitor must show a different desktop. Every test covers
   this layer only, so the tests run without a Mac and without a screen.
2. **macOS bindings** — `displays.py`, `spaces.py`, `windows.py`, `permissions.py`.
   Thin. Each function reads or writes one thing and gives back the types from `models.py`.
   No rules here.
3. **Glue and UI** — `arrange.py`, `app.py`.
   `arrange.py` joins layer 2 to layer 1. `app.py` is the rumps menu bar.

When you add a rule, put it in `planning.py` and cover it with a test. When you add a macOS
call, put it in layer 2 and keep it free of decisions.

## The private API

macOS publishes no way to read or set the desktop (Space) of a window. `spaces.py` loads
these symbols from the **SkyLight** private framework with `objc.loadBundleFunctions`:

| Symbol | Use |
| --- | --- |
| `SLSMainConnectionID` | The window-server connection of this process |
| `SLSCopyManagedDisplaySpaces` | Every monitor with its desktops, in macOS order |
| `SLSCopySpacesForWindows` | The desktop of a window |
| `SLSProcessAssignToSpace` | Move an application to a desktop, and release it again |
| `SLSManagedDisplaySetCurrentSpace` | Show a desktop on a monitor |

Rules for this file:

- Every function must fail in a safe manner. A missing symbol raises `SkyLightUnavailable`,
  which the public functions catch and turn into an empty result or `False`. A macOS update
  must never stop the menu bar item.
- `SLSCopySpacesForWindows` gives a **set**, not one answer per window. Ask for one window at
  a time. `space_id_by_window()` does this. Do not "improve" it into one batch call.
- The `SLS` names are the current ones. The old `CGS` names are aliases in the same framework.

`CGDisplayCreateUUIDFromDisplayID` is public but PyObjC does not publish it, so `displays.py`
loads it from `ColorSync.framework` in the same manner.

## Tested on macOS 26.6: what works and what does not

Do not repeat this work. These results come from live tests on a three-monitor Mac.

| Operation | Result |
| --- | --- |
| `SLSMoveWindowsToManagedSpace` (move one window) | **Does not work.** Returns 0, moves nothing. |
| `SLSSpaceAddWindowsAndRemoveFromSpaces` | **Does not work.** Same: returns 0, moves nothing. |
| `com.apple.spaces` `app-bindings` in the preferences | **Does not work.** The key survives a Dock restart but macOS ignores it. |
| `SLSProcessAssignToSpace(cid, pid, space)` | **Works.** Moves every window of the application. |
| `SLSProcessAssignToSpace(cid, pid, 0)` | **Works.** Releases the binding; the windows stay. |
| `SLSManagedDisplaySetCurrentSpace` | **Works**, even with no permission. |
| Accessibility `AXPosition` on another app's window | **Works**, and moves a window between monitors. |

Two results shape the whole design:

- **The move is per application, never per window.** macOS refuses a window-level move from a
  process without privilege; only `yabai` can do it, and only with SIP partly off. So
  `planning.Move` carries process IDs, not window IDs.
- **Always release after a move.** `assign_process_to_space()` ties the application to that
  desktop, the same as “Assign To” in the Dock menu. `arrange.apply()` calls
  `release_process()` straight after, or the user can no longer move the application by hand.

## Facts that shape the design

- **Key monitors on the UUID, never on the display index.** macOS changes the index when you
  connect or disconnect a monitor. `Display.uuid` is stable.
- **Never put a space ID in a preset.** The 64-bit space ID changes at logout and when the
  user adds or removes a desktop. A preset holds the 1-based desktop number
  (`Placement.desktop_index`), which counts user desktops only, in macOS order.
- **Most windows are not real windows.** The window server reports about 14 windows per
  application; only one or two are true windows. The others are backing windows, one per
  desktop. `windows.list_windows()` removes windows that are not on layer 0, are transparent,
  or belong to an application with no Dock icon. `arrange._windows_on_desktops()` then removes
  every window that sits on no desktop. Keep all four tests.
- **A full-screen application has its own space** of kind `fullscreen`. It has no desktop
  number and stays out of presets.
- **An application can have windows on several desktops.** `capture_placements()` takes the
  desktop that holds most of its windows. An apply then brings them all together.
- **The bundle ID is the key for an application** (`Placement.app`), because it survives a
  rename. `windows.display_name()` turns it into the name the user sees.
- **Window titles need the Screen Recording permission.** `WindowInfo.title` is empty without
  it. Nothing in the app depends on the title; keep it that way.

## What macOS cannot do

State these limits; do not try to work around them.

- No API adds or removes a desktop. `planning.missing_desktops()` reports how many the user
  must add in Mission Control.
- No API moves a desktop to a different monitor. A preset records the monitor of each
  desktop, and `plan_moves()` skips a placement when its monitor is absent.

## Style

- Simplified Technical English in the docstrings and the user-facing text: short sentences,
  one idea each, active voice.
- A missing application or a missing monitor is **skipped**, not **failed**. Only a real
  problem goes in `ApplyReport.failed`.
- Line length 100. Ruff rules `E, F, I, UP, B`.

## Licence

GPL-3.0-or-later. Keep new dependencies compatible with it.
