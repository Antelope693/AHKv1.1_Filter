"""Global hotkey listener using pynput."""

from __future__ import annotations

import threading
from typing import Callable

from pynput import keyboard

from .hotkeys import compose_hotkey, normalize_hotkey


class HotkeyBus:
    """
    Single keyboard listener that dispatches normalized hotkey strings.
    Recording mode captures the next complete combo and calls on_record.
    """

    def __init__(self) -> None:
        self._bindings: dict[str, Callable[[], None]] = {}
        self._pressed: set = set()
        self._lock = threading.Lock()
        self._recording = False
        self._on_record: Callable[[str], None] | None = None
        self._listener: keyboard.Listener | None = None
        self._suppress_until = 0.0

    def start(self) -> None:
        if self._listener:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_bindings(self, bindings: dict[str, Callable[[], None]]) -> None:
        normalized: dict[str, Callable[[], None]] = {}
        for key, cb in bindings.items():
            n = normalize_hotkey(key)
            if n:
                normalized[n] = cb
        with self._lock:
            self._bindings = normalized

    def begin_record(self, on_record: Callable[[str], None]) -> None:
        with self._lock:
            self._recording = True
            self._on_record = on_record
            self._pressed.clear()

    def cancel_record(self) -> None:
        with self._lock:
            self._recording = False
            self._on_record = None
            self._pressed.clear()

    def _on_press(self, key) -> None:
        with self._lock:
            self._pressed.add(key)
            combo = compose_hotkey(self._pressed, key)
            if not combo:
                return
            if self._recording and self._on_record:
                cb = self._on_record
                self._recording = False
                self._on_record = None
                self._pressed.clear()
                # Dispatch outside lock
                threading.Thread(target=cb, args=(combo,), daemon=True).start()
                return
            action = self._bindings.get(combo)
        if action:
            threading.Thread(target=action, daemon=True).start()

    def _on_release(self, key) -> None:
        with self._lock:
            self._pressed.discard(key)
            # Also discard related modifier variants loosely
            to_discard = [k for k in self._pressed if k == key]
            for k in to_discard:
                self._pressed.discard(k)
