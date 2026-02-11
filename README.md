# matugenium

`matugenium` is an app-aware wrapper around `matugen` for Linux/macOS/Windows workflows, including custom End-4 dot setups.

## Features

- Detect installed desktop applications from `.desktop` entries.
- Generate app-scoped color outputs with:
  - `matugenium --gen <appName>`
  - `matugenium --gen-all`
- Remove managed outputs safely with:
  - `matugenium --ungen <appName>`
- Supports fuzzy or exact app matching.
- Tracks generated profiles in a local state file for reliable cleanup.
- Optional End-4 copy integration for generated `colors.json`.
- Optional custom source image via `--image` (works even when icons are unavailable).

## Install (easy)

One command:

```bash
curl -fsSL https://raw.githubusercontent.com/MaxxWasHere/matugenium/main/install.sh | bash
```

This installer:

- uses `pipx` when available (recommended for global CLI apps)
- falls back to `python3 -m pip install --user` if `pipx` is missing
- prints next steps if your PATH needs `~/.local/bin`

## Install (from cloned repo)

From this project directory, run one command:

```bash
./install.sh
```

Or directly:

```bash
python3 scripts/install.py
```

The installer creates launcher files in your user bin directory:

- Linux/macOS: `~/.local/bin/matugenium`
- Windows: `%LOCALAPPDATA%\\matugenium\\bin\\matugenium.cmd` and `.ps1`

It prints PATH instructions for bash/zsh/fish/PowerShell.

Optional package install path (pip/pipx):

```bash
python -m pip install --user .
```

Or for isolated CLI install:

```bash
pipx install .
```

## Requirements

- Python 3.10+ (Linux/macOS/Windows)
- `matugen` installed and available in `PATH`

## Usage

Generate for a single app:

```bash
matugenium --gen "Firefox"
```

Remove generated profile for a single app:

```bash
matugenium --ungen "Firefox"
```

Generate for all detected installed apps:

```bash
matugenium --gen-all
```

Useful flags:

```bash
matugenium --list-apps
matugenium --gen "code" --exact
matugenium --gen-all --force --verbose
matugenium --gen "kitty" --dry-run
matugenium --gen "wezterm" --output-dir ~/.config/matugenium/generated
matugenium --gen "thunar" --end4-dir ~/.config/end-4-custom
matugenium --gen "MyApp" --image ~/Pictures/wallpaper.png
```

## Paths and State

- Default managed output directory:
  - `~/.config/matugenium/generated`
- State file:
  - `$XDG_STATE_HOME/matugenium/state.json`
  - fallback: `~/.local/state/matugenium/state.json`
- End-4 copy target (if configured or detected):
  - `<end4-dir>/matugenium/apps/<app-key>/colors.json`

## Environment Variables

- `MATUGENIUM_OUTPUT_DIR`: override managed output root.
- `MATUGENIUM_END4_DIR`: override End-4 root path.

## End-4 Integration Notes

Use `--end4-dir` for customized End-4 dot paths, or set `MATUGENIUM_END4_DIR` once in your shell profile. `matugenium` writes generated app colors into its own managed subdirectory so it does not overwrite unrelated dotfiles.

## Development

Run tests:

```bash
python -m pytest -q
```
