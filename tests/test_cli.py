from pathlib import Path
from unittest.mock import patch

from matugenium.cli import main
from matugenium.detect import AppEntry
from matugenium.generate import GenerationResult
from matugenium.state import StateStore


def _app() -> AppEntry:
    return AppEntry(
        desktop_id="org.demo.App.desktop",
        name="Demo App",
        generic_name="Demo",
        icon="demo",
        exec_cmd="demo",
        desktop_file="/tmp/demo.desktop",
        keywords=("demo",),
    )


def test_list_apps(capsys) -> None:
    with patch("matugenium.cli.discover_apps", return_value=[_app()]):
        rc = main(["--list-apps"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Demo App" in out


def test_gen_command_records_state(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    store = StateStore(state_path)
    result = GenerationResult(
        app_key="org-demo-app-desktop",
        output_dir=tmp_path / "generated" / "org-demo-app-desktop",
        source_image="/tmp/icon.png",
        command=["matugen", "image", "/tmp/icon.png", "-m", "dark", "-j", "hex"],
        colors_json_path=None,
        end4_json_path=None,
    )
    with patch("matugenium.cli.discover_apps", return_value=[_app()]), patch(
        "matugenium.cli.generate_for_app", return_value=result
    ), patch("matugenium.cli.StateStore", return_value=store):
        rc = main(["--gen", "demo"])
    assert rc == 0
    assert state_path.exists()


def test_gen_all_skips_existing(tmp_path: Path, capsys) -> None:
    state_path = tmp_path / "state.json"
    store = StateStore(state_path)
    store.record_profile(
        "org-demo-app-desktop",
        {
            "name": "Demo App",
            "desktop_id": "org.demo.App.desktop",
            "output_dir": str(tmp_path / "generated" / "org-demo-app-desktop"),
            "source_image": "/tmp/icon.png",
        },
    )
    with patch("matugenium.cli.discover_apps", return_value=[_app()]), patch(
        "matugenium.cli.StateStore", return_value=store
    ):
        rc = main(["--gen-all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "skipped=1" in out
