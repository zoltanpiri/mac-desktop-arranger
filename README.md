# mac-desktop-arranger

A tiny app to remember which app lives on each desktop, and which desktop lives on each monitor.
You can save presets for 1, 2 or 3 monitor setups.

It sits in the menu bar. Arrange your applications as you like them, save a preset, and put
everything back with one click after you connect or disconnect a monitor.

## Install and run

You need [uv](https://docs.astral.sh/uv/) and macOS.

```sh
uv sync
uv run mac-desktop-arranger
```

The app needs the **Accessibility** permission. It asks for it, and the menu shows a warning
until you give it. Open System Settings → Privacy & Security → Accessibility and switch the
app on. macOS gives the permission to the application that starts the process, so when you
start the app from a terminal, switch that terminal on.

## Use

| Menu item | What it does |
| --- | --- |
| The first lines | The monitors, and the desktop you are on |
| Save current arrangement… | Makes a preset from the windows on the screen now |
| Apply preset | Moves the applications back to their desktops, then shows the desktop each monitor showed |
| Delete preset | Removes a preset |

The presets are in `~/Library/Application Support/mac-desktop-arranger/presets.json`.

## Limits

- macOS gives no API to add or remove a desktop. When a preset needs a desktop that does not
  exist, the app tells you how many to add in Mission Control.
- macOS gives no API to move a desktop to a different monitor. The app records which monitor
  holds which desktop, and applies the part of the preset that fits.
- **macOS moves a whole application, not one window.** This is the same operation as
  “Assign To” in the Dock menu. When an application has windows on two desktops, all of them
  go to the desktop in the preset.
- The app uses private window-server functions, because macOS publishes no other way to read
  or set the desktop of a window. A macOS update can stop them. The app then tells you, and
  the menu bar item keeps working.

## Licence

GPL-3.0-or-later. See `LICENSE`.
