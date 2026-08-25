#!/usr/bin/env python3
"""Entry point for AHK_Filter."""

from ahk_filter.ui_theme import configure_dpi

# Must run before any Tk / CustomTkinter window is created.
configure_dpi()

from ahk_filter.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
