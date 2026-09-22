from __future__ import annotations

from mac_desktop_arranger.models import ApplyReport, Display, DisplayLayout, Preset, Space


def test_a_preset_survives_a_trip_through_a_dict():
    from test_presets import make_preset

    original = make_preset()

    assert Preset.from_dict(original.to_dict()) == original


def test_layout_counts_only_the_user_desktops():
    layout = DisplayLayout(
        display=Display(uuid="A"),
        spaces=(
            Space(space_id=1, uuid="s1", index=1, kind="user"),
            Space(space_id=2, uuid="s2", index=0, kind="fullscreen"),
            Space(space_id=3, uuid="s3", index=2, kind="user"),
        ),
        current_space_id=1,
    )

    assert [s.space_id for s in layout.user_spaces] == [1, 3]
    assert layout.space_at(2).space_id == 3
    assert layout.space_at(7) is None


def test_report_is_not_ok_when_something_failed():
    report = ApplyReport(moved=["a"], skipped=["b"], failed=["c"])

    assert report.ok is False
    assert report.summary() == "1 moved, 1 skipped, 1 failed"
    assert ApplyReport(moved=["a"]).ok is True
