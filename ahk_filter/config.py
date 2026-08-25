"""Persistent configuration for AHK_Filter."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 2,
    "global_toggle_hotkey": "ctrl+shift+f8",
    "collapsed_groups": {},  # group name -> bool (True = collapsed)
    "scripts": {},  # script_id -> {enabled: bool, hotkey: str|null}
}


class ConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = deepcopy(DEFAULT_CONFIG)

    def load(self) -> None:
        if not self.path.is_file():
            self.data = deepcopy(DEFAULT_CONFIG)
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("config root must be object")
            merged = deepcopy(DEFAULT_CONFIG)
            for key in DEFAULT_CONFIG:
                if key in raw:
                    merged[key] = raw[key]
            scripts = raw.get("scripts", {})
            merged["scripts"] = scripts if isinstance(scripts, dict) else {}
            collapsed = raw.get("collapsed_groups", {})
            merged["collapsed_groups"] = collapsed if isinstance(collapsed, dict) else {}
            # Drop legacy refresh hotkey if present
            merged.pop("refresh_hotkey", None)
            self.data = merged
        except Exception:
            self.data = deepcopy(DEFAULT_CONFIG)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = {k: v for k, v in self.data.items() if k != "refresh_hotkey"}
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def script_entry(self, script_id: str) -> dict[str, Any]:
        scripts = self.data.setdefault("scripts", {})
        entry = scripts.get(script_id)
        if not isinstance(entry, dict):
            entry = {"enabled": False, "hotkey": None}
            scripts[script_id] = entry
        if "enabled" not in entry:
            entry["enabled"] = False
        entry.setdefault("hotkey", None)
        return entry

    def sync_with_files(self, script_ids: list[str]) -> None:
        scripts = self.data.setdefault("scripts", {})
        known = set(script_ids)
        for sid in list(scripts.keys()):
            if sid not in known:
                del scripts[sid]
        for sid in script_ids:
            self.script_entry(sid)

    def is_group_collapsed(self, group_name: str) -> bool:
        collapsed = self.data.setdefault("collapsed_groups", {})
        # Default collapsed on first encounter
        return bool(collapsed.get(group_name, True))

    def set_group_collapsed(self, group_name: str, collapsed: bool) -> None:
        groups = self.data.setdefault("collapsed_groups", {})
        groups[group_name] = collapsed

    def all_hotkeys(self) -> dict[str, str]:
        """Map normalized hotkey string -> owner label."""
        result: dict[str, str] = {}
        gt = self.data.get("global_toggle_hotkey")
        if isinstance(gt, str) and gt:
            result[gt.lower()] = "global_toggle"
        for sid, entry in self.data.get("scripts", {}).items():
            if not isinstance(entry, dict):
                continue
            hk = entry.get("hotkey")
            if isinstance(hk, str) and hk:
                result[hk.lower()] = f"script:{sid}"
        return result
