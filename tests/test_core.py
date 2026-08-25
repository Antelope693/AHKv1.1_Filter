"""Unit tests for AHK_Filter core helpers (no GUI / no elevation)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ahk_filter.config import ConfigStore
from ahk_filter.hotkeys import format_hotkey, normalize_hotkey
from ahk_filter.injector import BEGIN, END, ensure_managed_block, has_managed_block, strip_managed_block
from ahk_filter.scanner import scan_ahk_directory


class HotkeyTests(unittest.TestCase):
    def test_normalize(self) -> None:
        self.assertEqual(normalize_hotkey("Ctrl+Shift+F8"), "ctrl+shift+f8")
        self.assertEqual(normalize_hotkey("alt-a"), "alt+a")
        self.assertIsNone(normalize_hotkey("ctrl+alt"))
        self.assertIsNone(normalize_hotkey(""))

    def test_format(self) -> None:
        self.assertEqual(format_hotkey(None), "未设置")
        self.assertIn("Ctrl", format_hotkey("ctrl+f8"))


class InjectorTests(unittest.TestCase):
    def test_inject_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo.ahk"
            path.write_text("MsgBox, hi\n", encoding="utf-8")
            self.assertTrue(ensure_managed_block(path))
            text = path.read_text(encoding="utf-8")
            self.assertTrue(has_managed_block(text))
            self.assertIn("MsgBox, hi", text)
            # Second pass should be stable
            self.assertFalse(ensure_managed_block(path))
            text2 = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(BEGIN), 1)
            self.assertEqual(text2.count(END), 1)
            body = strip_managed_block(text2)
            self.assertNotIn(BEGIN, body)
            self.assertIn("MsgBox, hi", body)


class ScannerTests(unittest.TestCase):
    def test_scan_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.ahk").write_text(";b\n", encoding="utf-8")
            (root / "a.ahk").write_text(";a\n", encoding="utf-8")
            (root / "ignore.txt").write_text("x", encoding="utf-8")
            names = [s.name for s in scan_ahk_directory(root)]
            self.assertEqual(names, ["a.ahk", "b.ahk"])


class ConfigTests(unittest.TestCase):
    def test_sync_and_hotkeys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp) / "cfg.json")
            store.load()
            store.sync_with_files(["a.ahk", "b.ahk"])
            store.script_entry("a.ahk")["hotkey"] = "ctrl+1"
            store.script_entry("b.ahk")["enabled"] = False
            store.save()
            store2 = ConfigStore(Path(tmp) / "cfg.json")
            store2.load()
            self.assertEqual(store2.script_entry("a.ahk")["hotkey"], "ctrl+1")
            self.assertFalse(store2.script_entry("b.ahk")["enabled"])
            store2.sync_with_files(["a.ahk"])
            self.assertNotIn("b.ahk", store2.data["scripts"])
            owners = store2.all_hotkeys()
            self.assertIn("ctrl+1", owners)


if __name__ == "__main__":
    unittest.main()
