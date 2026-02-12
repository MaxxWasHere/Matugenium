from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .detect import AppEntry, discover_apps, match_app
from .generate import generate_for_app, normalize_app_key, ungen_app_path
from .state import StateStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matugenium",
        description="App-aware Matugen color generation helper.",
    )
    parser.add_argument("--gen", metavar="APP_NAME", help="Generate colors for one app.")
    parser.add_argument("--ungen", metavar="APP_NAME", help="Remove generated profile for app.")
    parser.add_argument(
        "--gen-all",
        action="store_true",
        help="Generate colors for all detected desktop apps.",
    )
    parser.add_argument("--list-apps", action="store_true", help="List detected apps.")
    parser.add_argument("--exact", action="store_true", help="Use exact app matching.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions only.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed command output.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even when profile already exists in state.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override managed output directory.",
    )
    parser.add_argument(
        "--end4-dir",
        type=Path,
        default=None,
        help="End-4 dotfiles root to receive app color copies.",
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Fallback image path when app icon cannot be resolved.",
    )
    return parser


def _print(text: str, verbose: bool = False) -> None:
    if verbose:
        print(text)


def _info(message: str) -> None:
    print(f"INFO: {message}")


def _warn(message: str) -> None:
    print(f"WARN: {message}")


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _record_payload(app_name: str, desktop_id: str, output_dir: Path, source_image: str, end4_path: Path | None) -> dict[str, str]:
    payload: dict[str, str] = {
        "name": app_name,
        "desktop_id": desktop_id,
        "output_dir": str(output_dir),
        "source_image": source_image,
    }
    if end4_path:
        payload["end4_json_path"] = str(end4_path)
    return payload


def _remove_tracked_paths(record: dict[str, str], dry_run: bool, managed_root: Path | None) -> None:
    output_dir_value = record.get("output_dir", "")
    if output_dir_value:
        output_dir = Path(output_dir_value)
        ungen_app_path(output_dir, dry_run=dry_run, managed_root=managed_root)
    end4_json = record.get("end4_json_path")
    if end4_json:
        end4_path = Path(end4_json)
        if end4_path.exists() and not dry_run:
            end4_path.unlink()
            try:
                end4_path.parent.rmdir()
                end4_path.parent.parent.rmdir()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    requested_actions = sum(
        1 for selected in (args.gen, args.ungen, args.gen_all, args.list_apps) if selected
    )
    if requested_actions == 0:
        parser.print_help()
        return 1
    if requested_actions > 1:
        parser.error("Choose only one action at a time.")

    apps = discover_apps()
    state = StateStore()

    if args.list_apps:
        _info(f"Detected applications: {len(apps)}")
        for app in apps:
            icon_state = "icon" if app.icon else "no-icon"
            print(f"- {app.name} ({app.desktop_id}) [{icon_state}]")
        return 0

    if args.gen:
        try:
            if apps:
                app = match_app(args.gen, apps, exact=args.exact)
            else:
                app = AppEntry(
                    desktop_id=args.gen,
                    name=args.gen,
                    generic_name="",
                    icon="",
                    exec_cmd="",
                    desktop_file="",
                    keywords=(),
                )
            app_key = normalize_app_key(app.desktop_id or app.name)
            existing = state.all_profiles().get(app_key)
            if existing and not args.force:
                _warn(f"Profile already exists for {app.name}. Use --force to regenerate.")
                return 0
            _info(f"Generating profile for app: {app.name}")
            result = generate_for_app(
                app,
                output_root=args.output_dir,
                end4_dir=args.end4_dir,
                fallback_image=str(args.image.expanduser()) if args.image else None,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        except Exception as exc:  # noqa: BLE001
            _error(str(exc))
            return 2
        state.record_profile(
            result.app_key,
            _record_payload(
                app.name,
                app.desktop_id,
                result.output_dir,
                result.source_image,
                result.end4_json_path,
            ),
        )
        _print(f"command: {' '.join(result.command)}", args.verbose)
        _info(f"Generated profile for {app.name} -> {result.output_dir}")
        return 0

    if args.ungen:
        try:
            app = match_app(args.ungen, apps, exact=args.exact) if apps else None
        except Exception as exc:  # noqa: BLE001
            _print(f"match miss: {exc}", args.verbose)
            app = None

        direct_key = state.find_profile_key(args.ungen)
        fallback_key = normalize_app_key(app.desktop_id or app.name) if app else None
        final_key = direct_key or fallback_key
        if not final_key:
            _warn(f"No managed profile found for {args.ungen}")
            return 0

        record = state.get_profile(final_key)
        if not record:
            _warn(f"No managed profile found for {args.ungen}")
            return 0
        managed_root = args.output_dir.expanduser() if args.output_dir else None
        try:
            _remove_tracked_paths(record, dry_run=args.dry_run, managed_root=managed_root)
        except Exception as exc:  # noqa: BLE001
            _error(str(exc))
            return 3
        state.remove_profile(final_key)
        _info(f"Removed profile for {record.get('name', args.ungen)}")
        return 0

    if args.gen_all:
        success = 0
        failed = 0
        skipped = 0
        failures: list[str] = []
        if not apps:
            _warn("No installed desktop applications detected.")
            return 0
        state_profiles = state.all_profiles()
        total = len(apps)
        _info(f"Starting gen-all for {total} detected app(s)")
        for app in apps:
            app_key = normalize_app_key(app.desktop_id or app.name)
            if app_key in state_profiles and not args.force:
                skipped += 1
                _print(f"[skip] {app.name} (exists)", args.verbose)
                continue
            try:
                _print(f"[{success + failed + skipped + 1}/{total}] generating {app.name}", args.verbose)
                result = generate_for_app(
                    app,
                    output_root=args.output_dir,
                    end4_dir=args.end4_dir,
                    fallback_image=str(args.image.expanduser()) if args.image else None,
                    dry_run=args.dry_run,
                    verbose=args.verbose,
                )
                state.record_profile(
                    result.app_key,
                    _record_payload(
                        app.name,
                        app.desktop_id,
                        result.output_dir,
                        result.source_image,
                        result.end4_json_path,
                    ),
                )
                success += 1
                _print(f"[ok] {app.name}", args.verbose)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                failures.append(f"{app.name}: {exc}")
                _print(f"[fail] {app.name}: {exc}", args.verbose)
                continue
        _info(f"gen-all complete: success={success} failed={failed} skipped={skipped}")
        if failures:
            max_items = len(failures) if args.verbose else min(5, len(failures))
            for failure in failures[:max_items]:
                _warn(failure)
            remaining = len(failures) - max_items
            if remaining > 0:
                _warn(f"... and {remaining} more failure(s). Re-run with --verbose for full details.")
        return 0 if failed == 0 else 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
