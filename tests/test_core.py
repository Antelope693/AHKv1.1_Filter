"""Unit tests for AHK_Filter core helpers (no GUI / no elevation)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ahk_filter.config import ConfigStore
from ahk_filter.hotkeys import format_hotkey, normalize_hotkey
from ahk_filter.injector import BEGIN, END, ensure_managed_block, has_managed_block, strip_managed_block
from ahk_filter.scanner import scan_ahk_directory, scan_scripts
from ahk_filter.update import is_newer, parse_version


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
            self.assertIn("Suspend, On", text)
            self.assertIn("MsgBox, hi", text)
            self.assertFalse(ensure_managed_block(path))
            body = strip_managed_block(path.read_text(encoding="utf-8"))
            self.assertNotIn(BEGIN, body)
            self.assertIn("MsgBox, hi", body)


class ScannerTests(unittest.TestCase):
    def test_scan_flat_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.ahk").write_text(";b\n", encoding="utf-8")
            (root / "a.ahk").write_text(";a\n", encoding="utf-8")
            names = [s.name for s in scan_ahk_directory(root)]
            self.assertEqual(names, ["a.ahk", "b.ahk"])

    def test_scan_scripts_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            group = scripts / "Game"
            group.mkdir(parents=True)
            (group / "a.ahk").write_text(";a\n", encoding="utf-8")
            (scripts / "loose.ahk").write_text(";l\n", encoding="utf-8")
            result = scan_scripts(root)
            self.assertEqual(len(result.groups), 1)
            self.assertEqual(result.groups[0].name, "Game")
            self.assertEqual(result.groups[0].scripts[0].script_id, "Game/a.ahk")
            self.assertEqual(len(result.loose), 1)
            self.assertEqual(result.loose[0].script_id, "loose.ahk")
            self.assertEqual(result.total_count, 2)


class ConfigTests(unittest.TestCase):
    def test_sync_and_hotkeys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(Path(tmp) / "cfg.json")
            store.load()
            store.sync_with_files(["Pure/a.ahk", "b.ahk"])
            store.script_entry("Pure/a.ahk")["hotkey"] = "ctrl+1"
            self.assertFalse(store.script_entry("b.ahk")["enabled"])
            store.save()
            store2 = ConfigStore(Path(tmp) / "cfg.json")
            store2.load()
            self.assertEqual(store2.script_entry("Pure/a.ahk")["hotkey"], "ctrl+1")
            store2.sync_with_files(["Pure/a.ahk"])
            self.assertNotIn("b.ahk", store2.data["scripts"])
            owners = store2.all_hotkeys()
            self.assertIn("ctrl+1", owners)
            self.assertNotIn("refresh", owners.values())

    def test_group_collapsed_default(self) -> None:
        store = ConfigStore(Path("unused.json"))
        store.load()
        self.assertTrue(store.is_group_collapsed("Pure"))


class UpdateTests(unittest.TestCase):
    def test_parse_and_compare(self) -> None:
        self.assertEqual(parse_version("v1.1.0"), (1, 1, 0))
        self.assertTrue(is_newer("1.2.0", "1.1.0"))
        self.assertFalse(is_newer("1.1.0", "1.1.0"))
        self.assertFalse(is_newer("1.0.9", "1.1.0"))


if __name__ == "__main__":
    unittest.main()
