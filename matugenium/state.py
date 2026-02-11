from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _default_state_path() -> Path:
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        base = Path(xdg_state_home)
    else:
        base = Path.home() / ".local/state"
    return base / "matugenium" / "state.json"


class StateStore:
    def __init__(self, state_path: Path | None = None) -> None:
        self.path = state_path or _default_state_path()

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"profiles": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"profiles": {}}
        if not isinstance(raw, dict):
            return {"profiles": {}}
        raw.setdefault("profiles", {})
        return raw

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.path)

    def record_profile(self, app_key: str, record: dict[str, Any]) -> None:
        state = self.load()
        profiles = state.setdefault("profiles", {})
        profiles[app_key] = record
        self.save(state)

    def remove_profile(self, app_key: str) -> dict[str, Any] | None:
        state = self.load()
        profiles = state.setdefault("profiles", {})
        removed = profiles.pop(app_key, None)
        self.save(state)
        return removed

    def all_profiles(self) -> dict[str, Any]:
        state = self.load()
        profiles = state.setdefault("profiles", {})
        return dict(profiles)

    def get_profile(self, app_key: str) -> dict[str, Any] | None:
        state = self.load()
        profiles = state.setdefault("profiles", {})
        profile = profiles.get(app_key)
        if isinstance(profile, dict):
            return dict(profile)
        return None

    def find_profile_key(self, query: str) -> str | None:
        query_norm = query.strip().lower()
        if not query_norm:
            return None
        profiles = self.all_profiles()
        if query_norm in profiles:
            return query_norm
        for app_key, profile in profiles.items():
            name = str(profile.get("name", "")).lower()
            desktop_id = str(profile.get("desktop_id", "")).lower()
            if query_norm == name or query_norm == desktop_id:
                return app_key
            if query_norm in name or query_norm in desktop_id:
                return app_key
        return None
