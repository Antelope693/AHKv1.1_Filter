"""Persistent configuration for AHK_Filter."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "global_toggle_hotkey": "ctrl+shift+f8",
    "refresh_hotkey": "ctrl+shift+f5",
    "scripts": {},  # filename -> {enabled: bool, hotkey: str|null}
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
            merged.update({k: v for k, v in raw.items() if k in DEFAULT_CONFIG or k == "scripts"})
            scripts = raw.get("scripts", {})
            merged["scripts"] = scripts if isinstance(scripts, dict) else {}
            self.data = merged
        except Exception:
            self.data = deepcopy(DEFAULT_CONFIG)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def script_entry(self, filename: str) -> dict[str, Any]:
        scripts = self.data.setdefault("scripts", {})
        entry = scripts.get(filename)
        if not isinstance(entry, dict):
            entry = {"enabled": True, "hotkey": None}
            scripts[filename] = entry
        entry.setdefault("enabled", True)
        entry.setdefault("hotkey", None)
        return entry

    def sync_with_files(self, filenames: list[str]) -> None:
        scripts = self.data.setdefault("scripts", {})
        known = set(filenames)
        for name in list(scripts.keys()):
            if name not in known:
                del scripts[name]
        for name in filenames:
            self.script_entry(name)

    def all_hotkeys(self) -> dict[str, str]:
        """Map normalized hotkey string -> owner label."""
        result: dict[str, str] = {}
        gt = self.data.get("global_toggle_hotkey")
        rh = self.data.get("refresh_hotkey")
        if isinstance(gt, str) and gt:
            result[gt.lower()] = "global_toggle"
        if isinstance(rh, str) and rh:
            result[rh.lower()] = "refresh"
        for name, entry in self.data.get("scripts", {}).items():
            if not isinstance(entry, dict):
                continue
            hk = entry.get("hotkey")
            if isinstance(hk, str) and hk:
                result[hk.lower()] = f"script:{name}"
        return result
