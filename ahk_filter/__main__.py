"""Application controller — wires UI, config, runtime, and hotkeys."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from tkinter import messagebox

from .ahk_find import find_autohotkey
from .app import App
from .config import ConfigStore
from .elevation import ensure_admin, is_admin
from .hotkey_bus import HotkeyBus
from .injector import ensure_all
from .runtime import AhkRuntime
from .scanner import scan_ahk_directory


def workdir_from_argv() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    # Prefer the directory containing run.py / project root
    return Path(__file__).resolve().parent.parent


def main() -> int:
    workdir = workdir_from_argv()
    try:
        ensure_admin()
    except Exception as exc:
        print(f"Elevation failed: {exc}", file=sys.stderr)
        return 1

    if not is_admin():
        print("Administrator privileges are required.", file=sys.stderr)
        return 1

    ahk = find_autohotkey()
    if ahk is None:
        messagebox.showerror(
            "AHK_Filter",
            "未找到 AutoHotkey v1.x。\n"
            "请安装 AutoHotkey 1.1 后重试。\n"
            "https://www.autohotkey.com/",
        )
        return 2

    config = ConfigStore(workdir / "ahk_filter_config.json")
    config.load()

    bus = HotkeyBus()
    runtime = AhkRuntime(workdir=workdir, ahk_exe=ahk)

    def selected_map() -> dict[str, bool]:
        return {
            name: bool(config.script_entry(name).get("enabled", True))
            for name in config.data.get("scripts", {})
        }

    def bootstrap_scan() -> list:
        scripts = scan_ahk_directory(workdir)
        ensure_all([s.path for s in scripts])
        config.sync_with_files([s.name for s in scripts])
        # Align selected flags from config
        smap = {s.name: bool(config.script_entry(s.name).get("enabled", True)) for s in scripts}
        runtime.set_script_list([s.path for s in scripts], smap)
        config.save()
        return scripts

    scripts = bootstrap_scan()

    ui_holder: dict[str, App | None] = {"app": None}

    def rebind_hotkeys() -> None:
        bindings: dict = {}

        def schedule(fn):
            app = ui_holder["app"]
            if app is not None:
                app.after(0, fn)

        gt = config.data.get("global_toggle_hotkey")
        if gt:
            bindings[str(gt)] = lambda: schedule(do_global_toggle)

        rh = config.data.get("refresh_hotkey")
        if rh:
            bindings[str(rh)] = lambda: schedule(do_refresh)

        for name, entry in config.data.get("scripts", {}).items():
            if not isinstance(entry, dict):
                continue
            hk = entry.get("hotkey")
            if hk:
                bindings[str(hk)] = (
                    lambda n=name: schedule(lambda: do_script_toggle(n))
                )
        bus.set_bindings(bindings)

    def do_global_toggle() -> None:
        app = ui_holder["app"]
        if app is None:
            return
        if runtime.state.running:
            app._ui_stop()
        else:
            app._ui_start()

    def do_refresh() -> None:
        app = ui_holder["app"]
        if app is None:
            return
        if runtime.state.running:
            messagebox.showinfo("无法刷新", "请先全局终止，再刷新扫描。")
            return
        try:
            # Hard refresh for robustness
            runtime.terminate_all()
            scripts_now = scan_ahk_directory(workdir)
            ensure_all([s.path for s in scripts_now])
            config.sync_with_files([s.name for s in scripts_now])
            smap = {
                s.name: bool(config.script_entry(s.name).get("enabled", True))
                for s in scripts_now
            }
            runtime.refresh_hard([s.path for s in scripts_now], smap)
            config.save()
            app.reload_scripts(scripts_now)
            rebind_hotkeys()
        except Exception as exc:
            messagebox.showerror("刷新失败", f"{exc}\n\n{traceback.format_exc()}")

    def do_script_toggle(name: str) -> None:
        runtime.toggle_script(name)
        app = ui_holder["app"]
        if app:
            app._refresh_row_status()
            app._sync_status_bar()

    def begin_record(target: str) -> None:
        def on_captured(combo: str) -> None:
            app = ui_holder["app"]
            if app:
                app.after(0, lambda: app.finish_record(target, combo))

        bus.begin_record(on_captured)

    def cancel_record() -> None:
        bus.cancel_record()

    bus.start()
    rebind_hotkeys()

    app = App(
        workdir=workdir,
        config=config,
        runtime=runtime,
        scripts=scripts,
        ahk_path=ahk,
        on_global_toggle=do_global_toggle,
        on_refresh=do_refresh,
        on_record_done=lambda t, h: None,
        begin_record=begin_record,
        cancel_record=cancel_record,
        rebind_hotkeys=rebind_hotkeys,
    )
    # Hook refresh button to robust path
    app._on_refresh = do_refresh
    ui_holder["app"] = app

    app.mainloop()
    bus.stop()
    try:
        runtime.terminate_all()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
