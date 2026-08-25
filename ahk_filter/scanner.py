"""Scan the working directory for AutoHotkey scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AhkScript:
    path: Path
    name: str
    size: int
    mtime: float

    @property
    def stem(self) -> str:
        return self.path.stem


def scan_ahk_directory(directory: Path) -> list[AhkScript]:
    directory = directory.resolve()
    if not directory.is_dir():
        return []
    scripts: list[AhkScript] = []
    for path in sorted(directory.glob("*.ahk"), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        # Skip temporary / backup files
        if path.name.startswith("~$") or path.name.endswith(".bak.ahk"):
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        scripts.append(
            AhkScript(path=path, name=path.name, size=st.st_size, mtime=st.st_mtime)
        )
    return scripts
