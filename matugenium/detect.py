from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import os
from pathlib import Path
import sys
from typing import Iterable


DESKTOP_DIRS = (
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local/share/applications",
    Path.home() / ".local/share/flatpak/exports/share/applications",
    Path("/var/lib/flatpak/exports/share/applications"),
)


@dataclass(frozen=True)
class AppEntry:
    desktop_id: str
    name: str
    generic_name: str
    icon: str
    exec_cmd: str
    desktop_file: str
    keywords: tuple[str, ...]

    @property
    def aliases(self) -> tuple[str, ...]:
        alias_items = {
            self.desktop_id,
            Path(self.desktop_id).stem,
            self.name,
            self.generic_name,
            self.icon,
            *self.keywords,
        }
        return tuple(a for a in alias_items if a)


def _parse_desktop_entry(path: Path) -> AppEntry | None:
    name = ""
    generic_name = ""
    icon = ""
    exec_cmd = ""
    app_type = "Application"
    hidden = False
    no_display = False
    keywords: tuple[str, ...] = ()
    in_desktop_entry = False

    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            in_desktop_entry = line == "[Desktop Entry]"
            continue
        if not in_desktop_entry:
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key.startswith("Name[") and not name:
            name = value
        elif key == "Name" and not name:
            name = value
        elif key.startswith("GenericName[") and not generic_name:
            generic_name = value
        elif key == "GenericName" and not generic_name:
            generic_name = value
        elif key == "Icon" and not icon:
            icon = value
        elif key == "Exec" and not exec_cmd:
            exec_cmd = value
        elif key == "Type":
            app_type = value
        elif key == "Hidden":
            hidden = value.lower() == "true"
        elif key == "NoDisplay":
            no_display = value.lower() == "true"
        elif key == "Keywords":
            keywords = tuple(part.strip() for part in value.split(";") if part.strip())

    if not name:
        return None
    if app_type.lower() != "application":
        return None
    if hidden or no_display:
        return None

    return AppEntry(
        desktop_id=path.name,
        name=name,
        generic_name=generic_name,
        icon=icon,
        exec_cmd=exec_cmd,
        desktop_file=str(path),
        keywords=keywords,
    )


def discover_apps() -> list[AppEntry]:
    if sys.platform == "darwin":
        return _discover_macos_apps()
    if os.name == "nt":
        return _discover_windows_apps()

    found: dict[str, AppEntry] = {}
    for desktop_dir in DESKTOP_DIRS:
        if not desktop_dir.exists():
            continue
        for desktop_file in sorted(desktop_dir.glob("*.desktop")):
            app = _parse_desktop_entry(desktop_file)
            if app:
                found.setdefault(app.desktop_id, app)
    return sorted(found.values(), key=lambda item: item.name.lower())


def _discover_macos_apps() -> list[AppEntry]:
    roots = (Path("/Applications"), Path.home() / "Applications")
    apps: dict[str, AppEntry] = {}
    for root in roots:
        if not root.exists():
            continue
        for app_bundle in sorted(root.glob("*.app")):
            name = app_bundle.stem
            desktop_id = f"{name}.app"
            apps[desktop_id] = AppEntry(
                desktop_id=desktop_id,
                name=name,
                generic_name="",
                icon="",
                exec_cmd="",
                desktop_file=str(app_bundle),
                keywords=(),
            )
    return sorted(apps.values(), key=lambda item: item.name.lower())


def _discover_windows_apps() -> list[AppEntry]:
    appdata = os.environ.get("APPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", "")
    roots = []
    if programdata:
        roots.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if appdata:
        roots.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

    apps: dict[str, AppEntry] = {}
    for root in roots:
        if not root.exists():
            continue
        for entry in root.rglob("*.lnk"):
            name = entry.stem
            desktop_id = f"{name}.lnk"
            apps[desktop_id] = AppEntry(
                desktop_id=desktop_id,
                name=name,
                generic_name="",
                icon="",
                exec_cmd="",
                desktop_file=str(entry),
                keywords=(),
            )
    return sorted(apps.values(), key=lambda item: item.name.lower())


def match_app(app_name: str, apps: Iterable[AppEntry], exact: bool = False) -> AppEntry:
    app_name_norm = app_name.strip().lower()
    if not app_name_norm:
        raise ValueError("App name cannot be empty.")

    app_list = list(apps)
    if not app_list:
        raise ValueError("No desktop apps detected.")

    if exact:
        for app in app_list:
            if any(alias.lower() == app_name_norm for alias in app.aliases):
                return app
        raise ValueError(f"No exact app match for '{app_name}'.")

    # Strongly prefer exact/contains matches before fuzzy ranking.
    contains: list[AppEntry] = []
    for app in app_list:
        app_aliases = tuple(alias.lower() for alias in app.aliases)
        if any(app_name_norm in alias or alias in app_name_norm for alias in app_aliases):
            contains.append(app)
    if len(contains) == 1:
        return contains[0]
    if contains:
        app_list = contains

    best: tuple[float, AppEntry] | None = None
    for app in app_list:
        score = max(
            SequenceMatcher(None, app_name_norm, alias.lower()).ratio()
            for alias in app.aliases
        )
        if best is None or score > best[0]:
            best = (score, app)

    assert best is not None
    min_score = 0.45
    if best[0] < min_score:
        raise ValueError(f"No likely app match for '{app_name}'.")
    return best[1]
