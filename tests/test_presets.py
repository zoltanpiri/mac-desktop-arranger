from __future__ import annotations

from mac_desktop_arranger.models import Placement, Preset
from mac_desktop_arranger.presets import PresetStore


def make_preset(name: str = "work", uuids: tuple[str, ...] = ("A", "B")) -> Preset:
    return Preset(
        name=name,
        display_uuids=uuids,
        placements=(
            Placement(app="com.apple.Safari", display_uuid="A", desktop_index=1),
            Placement(app="com.jetbrains.pycharm", display_uuid="B", desktop_index=2),
        ),
        desktops_per_display={"A": 2, "B": 3},
    )


def test_put_then_load_gives_the_same_preset(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    original = make_preset()

    store.put(original)

    loaded = store.get("work")
    assert loaded == original


def test_load_gives_empty_dict_when_no_file(tmp_path):
    assert PresetStore(tmp_path / "absent.json").load() == {}


def test_load_gives_empty_dict_when_file_is_bad(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text("{ this is not json", encoding="utf-8")

    assert PresetStore(path).load() == {}


def test_put_replaces_the_preset_with_the_same_name(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    store.put(make_preset(uuids=("A", "B")))

    store.put(make_preset(uuids=("C",)))

    assert len(store.load()) == 1
    assert store.get("work").monitor_count == 1


def test_delete_removes_one_preset(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    store.put(make_preset("one"))
    store.put(make_preset("two"))

    assert store.delete("one") is True
    assert store.names() == ["two"]
    assert store.delete("one") is False


def test_names_sort_by_monitor_count_then_name(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    store.put(make_preset("triple", ("A", "B", "C")))
    store.put(make_preset("solo", ("A",)))
    store.put(make_preset("dual", ("A", "B")))

    assert store.names() == ["solo", "dual", "triple"]


def test_for_displays_ignores_the_monitor_order(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    store.put(make_preset("work", ("A", "B")))

    assert [p.name for p in store.for_displays(("B", "A"))] == ["work"]
    assert store.for_displays(("A", "C")) == []


def test_for_monitor_count_finds_the_setup(tmp_path):
    store = PresetStore(tmp_path / "presets.json")
    store.put(make_preset("dual", ("A", "B")))
    store.put(make_preset("solo", ("A",)))

    assert [p.name for p in store.for_monitor_count(1)] == ["solo"]


def test_a_bad_preset_does_not_hide_the_good_ones(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text(
        '{"schema_version": 1, "presets": [{"no_name": true}, '
        '{"name": "good", "display_uuids": ["A"], "placements": []}]}',
        encoding="utf-8",
    )

    assert list(PresetStore(path).load()) == ["good"]
