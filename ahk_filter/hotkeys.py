"""Hotkey parsing helpers shared by UI and runtime."""

from __future__ import annotations

from pynput.keyboard import Key, KeyCode

_MOD_ORDER = ("ctrl", "alt", "shift", "win")

_SPECIAL = {
    Key.ctrl_l: "ctrl",
    Key.ctrl_r: "ctrl",
    Key.alt_l: "alt",
    Key.alt_r: "alt",
    Key.alt_gr: "alt",
    Key.shift_l: "shift",
    Key.shift_r: "shift",
    Key.cmd: "win",
    Key.cmd_l: "win",
    Key.cmd_r: "win",
}


def normalize_hotkey(text: str | None) -> str | None:
    if not text or not str(text).strip():
        return None
    parts = [p.strip().lower() for p in str(text).replace("-", "+").split("+") if p.strip()]
    if not parts:
        return None
    mods = [p for p in _MOD_ORDER if p in parts]
    keys = [p for p in parts if p not in _MOD_ORDER]
    if len(keys) != 1:
        return None
    return "+".join([*mods, keys[0]])


def format_hotkey(text: str | None) -> str:
    n = normalize_hotkey(text)
    if not n:
        return "未设置"
    return n.upper().replace("CTRL", "Ctrl").replace("ALT", "Alt").replace("SHIFT", "Shift").replace("WIN", "Win")


def key_to_token(key: Key | KeyCode) -> str | None:
    if key in _SPECIAL:
        return None  # modifiers alone are not the trigger
    if isinstance(key, Key):
        name = str(key).replace("Key.", "")
        aliases = {
            "space": "space",
            "enter": "enter",
            "tab": "tab",
            "esc": "esc",
            "escape": "esc",
            "backspace": "backspace",
            "delete": "delete",
            "insert": "insert",
            "home": "home",
            "end": "end",
            "page_up": "pageup",
            "page_down": "pagedown",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "caps_lock": "capslock",
            "print_screen": "printscreen",
            "scroll_lock": "scrolllock",
            "pause": "pause",
            "menu": "menu",
            "num_lock": "numlock",
        }
        if name in aliases:
            return aliases[name]
        if name.startswith("f") and name[1:].isdigit():
            return name
        if name.startswith("media_") or name.startswith("f"):
            return name
        return None
    if isinstance(key, KeyCode):
        if key.char:
            ch = key.char.lower()
            if ch.isprintable() and ch != " ":
                return ch
        if key.vk is not None:
            # Numpad and function-ish via vk
            vk = key.vk
            if 0x70 <= vk <= 0x7B:  # F1-F12
                return f"f{vk - 0x6F}"
            if 0x30 <= vk <= 0x39:
                return chr(vk)
            if 0x41 <= vk <= 0x5A:
                return chr(vk + 32)
    return None


def current_modifiers(pressed: set) -> list[str]:
    mods: list[str] = []
    mapping = [
        ("ctrl", {Key.ctrl, Key.ctrl_l, Key.ctrl_r}),
        ("alt", {Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr}),
        ("shift", {Key.shift, Key.shift_l, Key.shift_r}),
        ("win", {Key.cmd, Key.cmd_l, Key.cmd_r}),
    ]
    for name, keys in mapping:
        if pressed & keys:
            mods.append(name)
    return mods


def compose_hotkey(pressed: set, key: Key | KeyCode) -> str | None:
    token = key_to_token(key)
    if not token:
        return None
    mods = current_modifiers(pressed)
    return normalize_hotkey("+".join([*mods, token]))
