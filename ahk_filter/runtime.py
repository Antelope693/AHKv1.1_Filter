"""Launch, suspend/resume, and track AutoHotkey script processes."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import win32con
import win32gui
import win32process

from .injector import FILTER_MSG

# AHK tray Suspend toggle (fallback if custom message fails)
AHK_ID_SUSPEND = 65305
WM_COMMAND = 0x111


@dataclass
class ScriptRuntime:
    path: Path
    name: str
    pid: int | None = None
    hwnd: int | None = None
    effective: bool = False  # hotkeys currently active
    selected: bool = True  # checkbox — participate on global start


@dataclass
class ManagerState:
    running: bool = False  # global start active
    scripts: dict[str, ScriptRuntime] = field(default_factory=dict)


class AhkRuntime:
    def __init__(
        self,
        workdir: Path,
        ahk_exe: Path,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self.workdir = workdir.resolve()
        self.ahk_exe = ahk_exe
        self.on_change = on_change
        self.state = ManagerState()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()

    def set_script_list(self, paths: list[Path], selected_map: dict[str, bool]) -> None:
        """Replace tracked scripts metadata without launching (stopped mode)."""
        new_map: dict[str, ScriptRuntime] = {}
        for path in paths:
            name = path.name
            prev = self.state.scripts.get(name)
            new_map[name] = ScriptRuntime(
                path=path.resolve(),
                name=name,
                pid=None,
                hwnd=None,
                effective=False,
                selected=selected_map.get(name, True if prev is None else prev.selected),
            )
        self.state.scripts = new_map
        self.state.running = False
        self._notify()

    def _find_hwnd_for_pid(self, pid: int, script_path: Path, timeout: float = 5.0) -> int | None:
        deadline = time.time() + timeout
        needle = str(script_path.resolve()).lower()
        needle_alt = needle.replace("\\", "/")
        while time.time() < deadline:
            found: list[int] = []

            def enum_handler(hwnd: int, _: None) -> None:
                if not win32gui.IsWindow(hwnd):
                    return
                try:
                    cls = win32gui.GetClassName(hwnd)
                except Exception:
                    return
                if cls != "AutoHotkey":
                    return
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid != pid:
                    return
                title = win32gui.GetWindowText(hwnd) or ""
                title_l = title.lower()
                if needle in title_l or needle_alt in title_l or script_path.name.lower() in title_l:
                    found.append(hwnd)

            try:
                win32gui.EnumWindows(enum_handler, None)
            except Exception:
                pass
            if found:
                return found[0]
            time.sleep(0.05)
        # Fallback: any AutoHotkey window for this PID
        fallback: list[int] = []

        def enum_pid(hwnd: int, _: None) -> None:
            if not win32gui.IsWindow(hwnd):
                return
            try:
                if win32gui.GetClassName(hwnd) != "AutoHotkey":
                    return
            except Exception:
                return
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid:
                fallback.append(hwnd)

        try:
            win32gui.EnumWindows(enum_pid, None)
        except Exception:
            pass
        return fallback[0] if fallback else None

    def _send_filter(self, hwnd: int, enable: bool) -> bool:
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False
        try:
            win32gui.SendMessage(hwnd, FILTER_MSG, 1 if enable else 0, 0)
            return True
        except Exception:
            return False

    def _send_suspend_toggle(self, hwnd: int) -> None:
        try:
            win32gui.PostMessage(hwnd, WM_COMMAND, AHK_ID_SUSPEND, 0)
        except Exception:
            pass

    def _ping(self, hwnd: int) -> bool:
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False
        try:
            result = win32gui.SendMessage(hwnd, FILTER_MSG, 3, 0)
            return result == 1
        except Exception:
            return False

    def _launch_one(self, rt: ScriptRuntime, effective: bool) -> None:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [str(self.ahk_exe), str(rt.path)],
            cwd=str(self.workdir),
            creationflags=creationflags,
            close_fds=True,
        )
        rt.pid = proc.pid
        hwnd = self._find_hwnd_for_pid(proc.pid, rt.path)
        rt.hwnd = hwnd
        # Scripts start unsuspended; force desired state via managed message.
        if hwnd:
            # Small delay so OnMessage is registered
            time.sleep(0.05)
            if not self._send_filter(hwnd, effective):
                # Fallback: if we need suspended, toggle once (scripts start active)
                if not effective:
                    self._send_suspend_toggle(hwnd)
            else:
                # Confirm ping
                self._ping(hwnd)
        rt.effective = effective if hwnd else False

    def _terminate_one(self, rt: ScriptRuntime) -> None:
        if rt.hwnd and win32gui.IsWindow(rt.hwnd):
            try:
                win32gui.PostMessage(rt.hwnd, WM_COMMAND, 65307, 0)  # Exit
            except Exception:
                pass
        if rt.pid:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(rt.pid), "/F"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except Exception:
                pass
        rt.pid = None
        rt.hwnd = None
        rt.effective = False

    def terminate_all(self) -> None:
        for rt in list(self.state.scripts.values()):
            if rt.pid:
                self._terminate_one(rt)
        self.state.running = False
        self._notify()

    def global_start(self) -> None:
        """Launch missing processes; enable selected, suspend unselected."""
        for rt in self.state.scripts.values():
            want = bool(rt.selected)
            if rt.pid and rt.hwnd and win32gui.IsWindow(rt.hwnd):
                self._send_filter(rt.hwnd, want)
                rt.effective = want
            else:
                rt.pid = None
                rt.hwnd = None
                self._launch_one(rt, effective=want)
        self.state.running = True
        self._notify()

    def global_stop(self) -> None:
        """Suspend all scripts but keep elevated processes alive (Option A)."""
        for rt in self.state.scripts.values():
            if rt.hwnd and win32gui.IsWindow(rt.hwnd):
                self._send_filter(rt.hwnd, False)
                rt.effective = False
            elif rt.pid:
                # Try rediscover hwnd
                hwnd = self._find_hwnd_for_pid(rt.pid, rt.path, timeout=0.5)
                rt.hwnd = hwnd
                if hwnd:
                    self._send_filter(hwnd, False)
                rt.effective = False
        self.state.running = False
        self._notify()

    def toggle_script(self, name: str) -> None:
        if not self.state.running:
            return
        rt = self.state.scripts.get(name)
        if not rt or not rt.selected:
            return
        if not rt.hwnd or not win32gui.IsWindow(rt.hwnd):
            if rt.pid:
                rt.hwnd = self._find_hwnd_for_pid(rt.pid, rt.path, timeout=1.0)
            if not rt.hwnd:
                self._launch_one(rt, effective=True)
                self._notify()
                return
        new_state = not rt.effective
        self._send_filter(rt.hwnd, new_state)
        rt.effective = new_state
        self._notify()

    def set_selected(self, name: str, selected: bool) -> None:
        rt = self.state.scripts.get(name)
        if not rt:
            return
        rt.selected = selected
        if self.state.running:
            if selected:
                if not rt.pid or not rt.hwnd or not win32gui.IsWindow(rt.hwnd):
                    self._launch_one(rt, effective=True)
                else:
                    self._send_filter(rt.hwnd, True)
                    rt.effective = True
            else:
                if rt.hwnd and win32gui.IsWindow(rt.hwnd):
                    self._send_filter(rt.hwnd, False)
                rt.effective = False
        self._notify()

    def refresh_hard(self, paths: list[Path], selected_map: dict[str, bool]) -> None:
        """
        Robust refresh — only valid while globally stopped.
        Terminates all managed AHK processes, then rebuilds tracking list.
        """
        if self.state.running:
            raise RuntimeError("Refresh is only allowed while globally stopped")
        self.terminate_all()
        # Extra settle time so file locks / window handles release
        time.sleep(0.15)
        self.set_script_list(paths, selected_map)
