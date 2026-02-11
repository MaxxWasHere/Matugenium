from pathlib import Path

from matugenium.detect import AppEntry, _parse_desktop_entry, match_app


def test_parse_desktop_entry_filters_hidden(tmp_path: Path) -> None:
    desktop_file = tmp_path / "hidden.desktop"
    desktop_file.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Hidden App",
                "Hidden=true",
            ]
        ),
        encoding="utf-8",
    )

    app = _parse_desktop_entry(desktop_file)
    assert app is None


def test_parse_desktop_entry_accepts_application(tmp_path: Path) -> None:
    desktop_file = tmp_path / "demo.desktop"
    desktop_file.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=Demo App",
                "GenericName=Demo",
                "Icon=demo",
                "Exec=demo --start",
                "Keywords=demo;color;theme;",
            ]
        ),
        encoding="utf-8",
    )

    app = _parse_desktop_entry(desktop_file)
    assert app is not None
    assert app.name == "Demo App"
    assert app.generic_name == "Demo"
    assert "color" in app.aliases


def test_match_app_exact_and_fuzzy() -> None:
    apps = [
        AppEntry(
            desktop_id="org.gnome.Nautilus.desktop",
            name="Files",
            generic_name="File Manager",
            icon="org.gnome.Nautilus",
            exec_cmd="nautilus",
            desktop_file="/tmp/a.desktop",
            keywords=("file", "browse"),
        ),
        AppEntry(
            desktop_id="org.kde.konsole.desktop",
            name="Konsole",
            generic_name="Terminal",
            icon="utilities-terminal",
            exec_cmd="konsole",
            desktop_file="/tmp/b.desktop",
            keywords=("shell",),
        ),
    ]

    assert match_app("Konsole", apps, exact=True).name == "Konsole"
    assert match_app("terminal", apps).name == "Konsole"
