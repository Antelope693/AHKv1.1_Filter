"""DPI awareness and crisp UI fonts for Windows + CustomTkinter."""

from __future__ import annotations

import ctypes
import sys
from functools import lru_cache

import customtkinter as ctk

_UI_FAMILY = "Microsoft YaHei UI"
_EMOJI_FAMILY = "Segoe UI Emoji"


def configure_dpi() -> None:
    """Call once before creating any Tk window."""
    if sys.platform != "win32":
        return
    try:
        # Per-monitor DPI awareness v2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        # Avoid double-scaling blur with CustomTkinter
        ctk.deactivate_automatic_dpi_awareness()
    except Exception:
        pass
    try:
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
    except Exception:
        pass


@lru_cache(maxsize=8)
def ui_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """Prefer YaHei UI — clearer Chinese glyphs under Windows ClearType."""
    return ctk.CTkFont(family=_UI_FAMILY, size=size, weight=weight)


def title_font(size: int = 22) -> ctk.CTkFont:
    return ui_font(size=size, weight="bold")


@lru_cache(maxsize=4)
def emoji_font(size: int = 20) -> ctk.CTkFont:
    return ctk.CTkFont(family=_EMOJI_FAMILY, size=size, weight="normal")
