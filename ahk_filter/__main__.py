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
from .scanner import ScanResult, scan_scripts, scripts_root


def workdir_from_argv() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path(__file__).resolve().parent.parent


def ensure_scripts_dir(workdir: Path) -> None:
    scripts_root(workdir).mkdir(parents=True, exist_ok=True)


def bootstrap_scan(workdir: Path, config: ConfigStore, runtime: AhkRuntime) -> ScanResult:
    ensure_scripts_dir(workdir)
    scan = scan_scripts(workdir)
    ensure_all([s.path for s in scan.all_scripts()])
    config.sync_with_files([s.script_id for s in scan.all_scripts()])
    smap = {
        s.script_id: bool(config.script_entry(s.script_id).get("enabled", False))
        for s in scan.all_scripts()
    }
    runtime.set_script_list(scan.all_scripts(), smap)
    config.save()
    return scan


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
    scan = bootstrap_scan(workdir, config, runtime)

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

        for sid, entry in config.data.get("scripts", {}).items():
            if not isinstance(entry, dict):
                continue
            hk = entry.get("hotkey")
            if hk:
                bindings[str(hk)] = (
                    lambda script_id=sid: schedule(lambda: do_script_toggle(script_id))
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
            runtime.terminate_all()
            scan_now = scan_scripts(workdir)
            ensure_all([s.path for s in scan_now.all_scripts()])
            config.sync_with_files([s.script_id for s in scan_now.all_scripts()])
            smap = {
                s.script_id: bool(config.script_entry(s.script_id).get("enabled", False))
                for s in scan_now.all_scripts()
            }
            runtime.refresh_hard(scan_now.all_scripts(), smap)
            config.save()
            app.reload_scan(scan_now)
            rebind_hotkeys()
        except Exception as exc:
            messagebox.showerror("刷新失败", f"{exc}\n\n{traceback.format_exc()}")

    def do_script_toggle(script_id: str) -> None:
        runtime.toggle_script(script_id)
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
        scan=scan,
        ahk_path=ahk,
        on_global_toggle=do_global_toggle,
        on_refresh=do_refresh,
        begin_record=begin_record,
        cancel_record=cancel_record,
        rebind_hotkeys=rebind_hotkeys,
    )
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
