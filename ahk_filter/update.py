"""GitHub docs fetch and hot-update helpers."""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import __version__

GITHUB_OWNER = "Antelope693"
GITHUB_REPO = "AHKv1.1_Filter"
RAW_HANDBOOK_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/docs/HANDBOOK.md"
)
API_LATEST_RELEASE = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
REPO_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"

# Paths that must survive a hot update
PRESERVE_NAMES = {
    "ahk_filter_config.json",
    "scripts",
    ".cache",
    ".git",
    ".venv",
    "venv",
}


@dataclass
class ReleaseInfo:
    tag: str
    name: str
    body: str
    zipball_url: str
    html_url: str


def _http_get(url: str, timeout: float = 15.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"AHK_Filter/{__version__}",
            "Accept": "application/vnd.github+json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_handbook_markdown(local_fallback: Path) -> str:
    try:
        data = _http_get(RAW_HANDBOOK_URL)
        text = data.decode("utf-8")
        if text.strip():
            return text
    except Exception:
        pass
    if local_fallback.is_file():
        return local_fallback.read_text(encoding="utf-8")
    return (
        "# AHK_Filter 手册\n\n"
        "无法从 GitHub 拉取手册，且本地 docs/HANDBOOK.md 不存在。\n"
        f"仓库：{REPO_PAGE}\n"
    )


def parse_version(tag: str) -> tuple[int, ...]:
    t = tag.strip().lstrip("vV")
    parts: list[int] = []
    for chunk in t.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer(remote_tag: str, local_version: str = __version__) -> bool:
    try:
        return parse_version(remote_tag) > parse_version(local_version)
    except Exception:
        return False


def fetch_latest_release() -> ReleaseInfo | None:
    try:
        raw = _http_get(API_LATEST_RELEASE)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or data.get("message") == "Not Found":
            return None
        tag = str(data.get("tag_name") or "")
        if not tag:
            return None
        return ReleaseInfo(
            tag=tag,
            name=str(data.get("name") or tag),
            body=str(data.get("body") or ""),
            zipball_url=str(data.get("zipball_url") or ""),
            html_url=str(data.get("html_url") or REPO_PAGE),
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        return None
    except Exception:
        return None


def apply_hot_update(workdir: Path, release: ReleaseInfo) -> None:
    """
    Download release zipball and overlay onto workdir.
    Preserves user scripts/ and ahk_filter_config.json.
    """
    if not release.zipball_url:
        raise RuntimeError("Release 未提供 zipball_url")

    data = _http_get(release.zipball_url, timeout=120.0)
    with tempfile.TemporaryDirectory(prefix="ahk_filter_upd_") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(tmp_path)
        roots = [p for p in tmp_path.iterdir() if p.is_dir()]
        if not roots:
            raise RuntimeError("更新包结构无效")
        src_root = roots[0]

        # Copy overlay while preserving user data
        for item in src_root.iterdir():
            name = item.name
            if name in PRESERVE_NAMES:
                continue
            dest = workdir / name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)


def relaunch_app(workdir: Path) -> None:
    """Restart current process in workdir, then exit."""
    args = [sys.executable, str(workdir / "run.py"), *sys.argv[1:]]
    os.chdir(workdir)
    os.execv(sys.executable, args)
