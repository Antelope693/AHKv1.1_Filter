"""Locate AutoHotkey v1.x interpreter on the local machine."""

from __future__ import annotations

import os
import shutil
import winreg
from pathlib import Path

CANDIDATE_NAMES = (
    "AutoHotkeyU64.exe",
    "AutoHotkeyU32.exe",
    "AutoHotkey.exe",
    "AutoHotkeyA32.exe",
)

COMMON_DIRS = (
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "AutoHotkey",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "AutoHotkey",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "AutoHotkey",
    Path(r"C:\Program Files\AutoHotkey"),
    Path(r"C:\Program Files (x86)\AutoHotkey"),
)


def _looks_like_v1(path: Path) -> bool:
    """Prefer v1 binaries; reject obvious v2-only installs when detectable."""
    name = path.name.lower()
    parent = path.parent
    # AHK v2 often ships as AutoHotkey64.exe / AutoHotkey32.exe under AutoHotkey\\v2
    if "v2" in parent.as_posix().lower():
        return False
    if name in ("autohotkey64.exe", "autohotkey32.exe") and not (parent / "AutoHotkey.ahk").exists():
        # Heuristic: v2 layout
        if (parent / "UX").is_dir() or (parent.parent / "v2").is_dir():
            return False
    return True


def _from_registry() -> Path | None:
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\AutoHotkey"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\AutoHotkey"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\AutoHotkey"),
    )
    for root, sub in keys:
        try:
            with winreg.OpenKey(root, sub) as key:
                for value_name in ("InstallDir", "InstallDir_64", ""):
                    try:
                        if value_name:
                            val, _ = winreg.QueryValueEx(key, value_name)
                        else:
                            val, _ = winreg.QueryValueEx(key, None)
                    except OSError:
                        continue
                    base = Path(str(val))
                    if base.is_file() and base.suffix.lower() == ".exe":
                        return base if _looks_like_v1(base) else None
                    if base.is_dir():
                        for name in CANDIDATE_NAMES:
                            cand = base / name
                            if cand.is_file() and _looks_like_v1(cand):
                                return cand
        except OSError:
            continue
    return None


def find_autohotkey() -> Path | None:
    found = _from_registry()
    if found and found.is_file():
        return found

    for directory in COMMON_DIRS:
        if not directory:
            continue
        for name in CANDIDATE_NAMES:
            cand = directory / name
            if cand.is_file() and _looks_like_v1(cand):
                return cand
        # nested v1.1 folder used by some installers
        for name in CANDIDATE_NAMES:
            cand = directory / "v1.1" / name
            if cand.is_file():
                return cand

    for name in CANDIDATE_NAMES:
        which = shutil.which(name)
        if which:
            path = Path(which)
            if path.is_file() and _looks_like_v1(path):
                return path
    return None
