from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from .detect import AppEntry


def _default_output_dir() -> Path:
    override = os.environ.get("MATUGENIUM_OUTPUT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config/matugenium/generated"


def _default_end4_dir() -> Path | None:
    override = os.environ.get("MATUGENIUM_END4_DIR")
    if override:
        return Path(override).expanduser()
    candidate = Path.home() / ".config/end-4"
    return candidate if candidate.exists() else None


@dataclass
class GenerationResult:
    app_key: str
    output_dir: Path
    source_image: str
    command: list[str]
    colors_json_path: Path | None
    end4_json_path: Path | None


def normalize_app_key(raw_name: str) -> str:
    key = "".join(char.lower() if char.isalnum() else "-" for char in raw_name).strip("-")
    while "--" in key:
        key = key.replace("--", "-")
    return key or "unknown-app"


def resolve_icon_source(icon_name: str) -> str:
    if not icon_name:
        return ""
    if Path(icon_name).exists():
        return icon_name
    icon_extensions = (".png", ".svg", ".jpg", ".jpeg", ".webp")
    icon_dirs = (
        Path.home() / ".local/share/icons",
        Path.home() / ".icons",
        Path("/usr/share/icons"),
        Path("/usr/share/pixmaps"),
    )
    for icon_dir in icon_dirs:
        if not icon_dir.exists():
            continue
        for ext in icon_extensions:
            candidate = icon_dir / f"{icon_name}{ext}"
            if candidate.exists():
                return str(candidate)
    return ""


def ensure_matugen_available() -> None:
    if which("matugen") is None:
        raise RuntimeError("matugen command not found in PATH.")


def _safe_within(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def generate_for_app(
    app: AppEntry,
    output_root: Path | None = None,
    end4_dir: Path | None = None,
    fallback_image: str | None = None,
    dry_run: bool = False,
) -> GenerationResult:
    ensure_matugen_available()
    app_key = normalize_app_key(app.desktop_id or app.name)
    output_dir = (output_root or _default_output_dir()) / app_key
    source_image = resolve_icon_source(app.icon)
    if not source_image:
        source_image = str(Path(fallback_image).expanduser()) if fallback_image else ""
    if not Path(source_image).exists():
        raise RuntimeError(
            "Could not resolve a valid icon/image source. "
            "Use --image with a path to any wallpaper/icon image."
        )

    command = [
        "matugen",
        "image",
        source_image,
        "-m",
        "dark",
        "-j",
        "hex",
    ]
    colors_json_path = output_dir / "colors.json"
    end4_target: Path | None = None
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True, cwd=output_dir)
        end4_base = end4_dir or _default_end4_dir()
        if end4_base:
            end4_target = end4_base / "matugenium" / "apps" / app_key / "colors.json"
            if not _safe_within(end4_base, end4_target):
                raise RuntimeError("Computed End-4 output path is unsafe.")
            end4_target.parent.mkdir(parents=True, exist_ok=True)
            if colors_json_path.exists():
                shutil.copy2(colors_json_path, end4_target)
    return GenerationResult(
        app_key=app_key,
        output_dir=output_dir,
        source_image=source_image,
        command=command,
        colors_json_path=colors_json_path if colors_json_path.exists() else None,
        end4_json_path=end4_target,
    )


def ungen_app_path(path: Path, dry_run: bool = False, managed_root: Path | None = None) -> None:
    if not path.exists():
        return
    if managed_root and not _safe_within(managed_root, path):
        raise RuntimeError(f"Refusing to remove unmanaged path: {path}")
    if not dry_run:
        shutil.rmtree(path)
