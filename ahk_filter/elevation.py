"""Elevation helpers — single UAC prompt for the manager process."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> None:
    """Re-exec the current entrypoint with a single runas prompt, then exit."""
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        executable = sys.executable
        main = Path(__file__).resolve().parent.parent / "run.py"
        args = [str(main), *sys.argv[1:]]
        params = " ".join(f'"{a}"' for a in args)

    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1
    )
    if rc <= 32:
        raise RuntimeError(f"Elevation failed (ShellExecuteW returned {rc})")
    sys.exit(0)


def ensure_admin() -> None:
    if not is_admin():
        relaunch_as_admin()
