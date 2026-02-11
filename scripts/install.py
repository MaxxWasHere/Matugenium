#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def user_bin_dir() -> Path:
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "matugenium" / "bin"
        return Path.home() / "AppData" / "Local" / "matugenium" / "bin"
    return Path.home() / ".local" / "bin"


def write_unix_launcher(target: Path, root: Path) -> None:
    content = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            'PYTHON_BIN="${PYTHON_BIN:-python3}"',
            f'export PYTHONPATH="{root}:${{PYTHONPATH:-}}"',
            'exec "${PYTHON_BIN}" -m matugenium.cli "$@"',
            "",
        ]
    )
    target.write_text(content, encoding="utf-8")
    target.chmod(0o755)


def write_windows_launchers(bin_dir: Path, root: Path) -> None:
    ps1 = bin_dir / "matugenium.ps1"
    ps1.write_text(
        "\n".join(
            [
                '$pythonBin = $env:PYTHON_BIN',
                "if (-not $pythonBin) { $pythonBin = 'python' }",
                f'$env:PYTHONPATH = "{root};$env:PYTHONPATH"',
                f'& $pythonBin -m matugenium.cli $args',
                "",
            ]
        ),
        encoding="utf-8",
    )
    cmd = bin_dir / "matugenium.cmd"
    cmd.write_text(
        "\n".join(
            [
                "@echo off",
                "set PYTHON_BIN=%PYTHON_BIN%",
                'if "%PYTHON_BIN%"=="" set PYTHON_BIN=python',
                f"set PYTHONPATH={root};%PYTHONPATH%",
                "%PYTHON_BIN% -m matugenium.cli %*",
                "",
            ]
        ),
        encoding="utf-8",
    )


def print_path_instructions(bin_dir: Path) -> None:
    print(f"Installed launchers in: {bin_dir}")
    print("")
    if os.name == "nt":
        print("Add this directory to PATH (PowerShell):")
        print(f'  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";{bin_dir}", "User")')
        print("")
        print("Then restart terminal and run:")
        print("  matugenium --help")
        return

    shell = os.environ.get("SHELL", "")
    shell_name = Path(shell).name
    print("Add to PATH based on your shell:")
    print(f'  bash/zsh: echo \'export PATH="{bin_dir}:$PATH"\' >> ~/.bashrc')
    print(f"  fish:     fish_add_path -U {bin_dir}")
    print("")
    if shell_name:
        print(f"Detected shell: {shell_name}")
    print("Then restart terminal and run:")
    print("  matugenium --help")


def main() -> int:
    root = project_root()
    bin_dir = user_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        write_windows_launchers(bin_dir, root)
    else:
        write_unix_launcher(bin_dir / "matugenium", root)

    print(f"Platform: {platform.system()} {platform.release()}")
    print_path_instructions(bin_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
