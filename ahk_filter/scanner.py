"""Scan the scripts/ directory for AutoHotkey scripts and configuration groups."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AhkScript:
    path: Path
    script_id: str  # relative path from scripts/ using forward slashes
    name: str
    group: str | None  # group folder name, or None for loose scripts
    size: int
    mtime: float

    @property
    def stem(self) -> str:
        return self.path.stem


@dataclass
class ScriptGroup:
    name: str
    folder: Path
    scripts: list[AhkScript] = field(default_factory=list)


@dataclass
class ScanResult:
    scripts_dir: Path
    groups: list[ScriptGroup] = field(default_factory=list)
    loose: list[AhkScript] = field(default_factory=list)

    def all_scripts(self) -> list[AhkScript]:
        items: list[AhkScript] = []
        for group in self.groups:
            items.extend(group.scripts)
        items.extend(self.loose)
        return items

    @property
    def total_count(self) -> int:
        return sum(len(g.scripts) for g in self.groups) + len(self.loose)


def scripts_root(workdir: Path) -> Path:
    return workdir.resolve() / "scripts"


def _is_valid_ahk(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith("~$") or path.name.endswith(".bak.ahk"):
        return False
    return path.suffix.lower() == ".ahk"


def _make_script(path: Path, scripts_dir: Path, group: str | None) -> AhkScript | None:
    try:
        rel = path.resolve().relative_to(scripts_dir.resolve())
    except ValueError:
        return None
    script_id = rel.as_posix()
    try:
        st = path.stat()
    except OSError:
        return None
    return AhkScript(
        path=path.resolve(),
        script_id=script_id,
        name=path.name,
        group=group,
        size=st.st_size,
        mtime=st.st_mtime,
    )


def _scan_folder(folder: Path, scripts_dir: Path, group: str | None) -> list[AhkScript]:
    found: list[AhkScript] = []
    for path in sorted(folder.rglob("*.ahk"), key=lambda p: p.as_posix().lower()):
        if not _is_valid_ahk(path):
            continue
        script = _make_script(path, scripts_dir, group)
        if script:
            found.append(script)
    return found


def scan_scripts(workdir: Path) -> ScanResult:
    """
    Layout:
      scripts/<group>/**/*.ahk  -> configuration groups (sorted by folder name)
      scripts/*.ahk              -> loose scripts (shown below all groups)
    """
    scripts_dir = scripts_root(workdir)
    result = ScanResult(scripts_dir=scripts_dir)
    if not scripts_dir.is_dir():
        return result

    for child in sorted(scripts_dir.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        scripts = _scan_folder(child, scripts_dir, child.name)
        if scripts:
            result.groups.append(ScriptGroup(name=child.name, folder=child, scripts=scripts))

    for path in sorted(scripts_dir.glob("*.ahk"), key=lambda p: p.name.lower()):
        if not _is_valid_ahk(path):
            continue
        script = _make_script(path, scripts_dir, None)
        if script:
            result.loose.append(script)

    return result


# Backward-compatible helper used in older tests
def scan_ahk_directory(directory: Path) -> list[AhkScript]:
    directory = directory.resolve()
    if not directory.is_dir():
        return []
    scripts: list[AhkScript] = []
    for path in sorted(directory.glob("*.ahk"), key=lambda p: p.name.lower()):
        if not _is_valid_ahk(path):
            continue
        script = _make_script(path, directory, None)
        if script:
            scripts.append(script)
    return scripts
