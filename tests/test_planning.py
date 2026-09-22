from __future__ import annotations

from conftest import MAIN, SIDE, make_layout
from mac_desktop_arranger.models import Placement, Preset, WindowInfo
from mac_desktop_arranger.planning import (
    capture_placements,
    desktops_per_display,
    missing_desktops,
    plan_moves,
)


def preset_for(*placements: Placement, uuids: tuple[str, ...] = (MAIN, SIDE)) -> Preset:
    return Preset(name="test", display_uuids=uuids, placements=placements)


# --- capture ---------------------------------------------------------------


def test_capture_makes_one_rule_for_each_application(two_monitors, windows):
    on_space = {1: 101, 2: 202, 3: 202, 4: 103}

    placements = capture_placements(two_monitors, windows, on_space)

    assert placements == (
        Placement("com.apple.Safari", MAIN, 1),
        Placement("com.jetbrains.pycharm", SIDE, 2),
        Placement("com.tinyspeck.slackmacgap", MAIN, 3),
    )


def test_capture_takes_the_desktop_with_most_windows(two_monitors):
    windows = {
        "com.apple.Safari": [
            WindowInfo(window_id=1, pid=10, app="com.apple.Safari"),
            WindowInfo(window_id=2, pid=10, app="com.apple.Safari"),
            WindowInfo(window_id=3, pid=10, app="com.apple.Safari"),
        ]
    }
    on_space = {1: 102, 2: 102, 3: 101}

    assert capture_placements(two_monitors, windows, on_space) == (
        Placement("com.apple.Safari", MAIN, 2),
    )


def test_capture_ignores_a_window_with_an_unknown_desktop(two_monitors, windows):
    assert capture_placements(two_monitors, windows, {}) == ()


def test_desktops_per_display_counts_the_user_desktops(two_monitors):
    assert desktops_per_display(two_monitors) == {MAIN: 3, SIDE: 2}


# --- plan ------------------------------------------------------------------


def test_plan_moves_the_windows_of_each_application(two_monitors, windows):
    preset = preset_for(
        Placement("com.apple.Safari", MAIN, 2),
        Placement("com.jetbrains.pycharm", SIDE, 1),
    )

    plan = plan_moves(preset, two_monitors, windows)

    assert [(m.app, m.pids, m.space_id) for m in plan.moves] == [
        ("com.apple.Safari", (10,), 102),
        ("com.jetbrains.pycharm", (20,), 201),
    ]
    assert plan.skipped == []


def test_plan_lists_each_process_of_an_application_one_time(two_monitors, windows):
    """PyCharm has two windows in one process. The move must carry one PID."""
    preset = preset_for(Placement("com.jetbrains.pycharm", SIDE, 1))

    plan = plan_moves(preset, two_monitors, windows)

    assert plan.moves[0].pids == (20,)


def test_plan_skips_an_application_that_does_not_run(two_monitors, windows):
    preset = preset_for(Placement("com.apple.Mail", MAIN, 1))

    plan = plan_moves(preset, two_monitors, windows)

    assert plan.moves == []
    assert plan.skipped == ["com.apple.Mail: not running"]


def test_plan_skips_an_application_when_its_monitor_is_absent(windows):
    one_monitor = [make_layout(MAIN, 3, base=100)]
    preset = preset_for(Placement("com.apple.Safari", SIDE, 1))

    plan = plan_moves(preset, one_monitor, windows)

    assert plan.moves == []
    assert plan.skipped == ["com.apple.Safari: monitor not connected"]


def test_plan_skips_an_application_when_the_desktop_is_absent(two_monitors, windows):
    preset = preset_for(Placement("com.apple.Safari", SIDE, 9))

    plan = plan_moves(preset, two_monitors, windows)

    assert plan.moves == []
    assert plan.skipped == ["com.apple.Safari: desktop 9 does not exist"]


# --- desktops that the user must add ---------------------------------------


def test_missing_desktops_gives_how_many_to_add(two_monitors):
    preset = preset_for(
        Placement("com.apple.Safari", SIDE, 5),
        Placement("com.apple.Mail", MAIN, 2),
    )

    assert missing_desktops(preset, two_monitors) == {SIDE: 3}


def test_missing_desktops_is_empty_when_the_desktops_exist(two_monitors):
    preset = preset_for(Placement("com.apple.Safari", MAIN, 3))

    assert missing_desktops(preset, two_monitors) == {}


def test_missing_desktops_ignores_a_monitor_that_is_not_connected(two_monitors):
    preset = preset_for(Placement("com.apple.Safari", "unknown-uuid", 4))

    assert missing_desktops(preset, two_monitors) == {}


# --- which desktop each monitor shows --------------------------------------


def test_visible_desktops_reads_the_desktop_of_each_monitor(two_monitors):
    from mac_desktop_arranger.planning import visible_desktops

    # conftest makes the current space `base + current`, that is desktop 1.
    assert visible_desktops(two_monitors) == {MAIN: 1, SIDE: 1}


def test_plan_switches_gives_only_the_monitors_that_must_change(two_monitors):
    from mac_desktop_arranger.planning import plan_switches

    preset = Preset(
        name="p",
        display_uuids=(MAIN, SIDE),
        placements=(),
        visible_desktops={MAIN: 3, SIDE: 1},  # SIDE already shows desktop 1
    )

    switches = plan_switches(preset, two_monitors)

    assert [(s.display_uuid, s.space_id, s.desktop_index) for s in switches] == [
        (MAIN, 103, 3)
    ]


def test_plan_switches_ignores_a_desktop_that_does_not_exist(two_monitors):
    from mac_desktop_arranger.planning import plan_switches

    preset = Preset(name="p", display_uuids=(SIDE,), placements=(), visible_desktops={SIDE: 9})

    assert plan_switches(preset, two_monitors) == []


def test_plan_switches_ignores_a_monitor_that_is_not_connected(two_monitors):
    from mac_desktop_arranger.planning import plan_switches

    preset = Preset(name="p", display_uuids=("gone",), placements=(), visible_desktops={"gone": 1})

    assert plan_switches(preset, two_monitors) == []
