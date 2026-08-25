"""CustomTkinter front-end for AHK_Filter."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from .config import ConfigStore
from .hotkeys import format_hotkey, normalize_hotkey
from .runtime import AhkRuntime
from .scanner import AhkScript


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ScriptRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        script: AhkScript,
        selected: bool,
        hotkey: str | None,
        status: str,
        on_toggle_selected: Callable[[str, bool], None],
        on_record_hotkey: Callable[[str], None],
        on_clear_hotkey: Callable[[str], None],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.script_name = script.name

        self.grid_columnconfigure(1, weight=1)

        self.var = tk.BooleanVar(value=selected)
        self.chk = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var,
            width=28,
            command=lambda: on_toggle_selected(script.name, bool(self.var.get())),
        )
        self.chk.grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        info.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            info, text=script.name, anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew")

        meta = f"{script.size} bytes"
        self.meta_lbl = ctk.CTkLabel(info, text=meta, anchor="w", text_color=("gray40", "gray65"))
        self.meta_lbl.grid(row=1, column=0, sticky="ew")

        self.status_lbl = ctk.CTkLabel(self, text=status, width=72, anchor="center")
        self.status_lbl.grid(row=0, column=2, padx=6)

        self.hk_btn = ctk.CTkButton(
            self,
            text=format_hotkey(hotkey),
            width=130,
            command=lambda: on_record_hotkey(script.name),
        )
        self.hk_btn.grid(row=0, column=3, padx=4)

        self.clear_btn = ctk.CTkButton(
            self,
            text="清除",
            width=56,
            fg_color=("gray75", "gray35"),
            command=lambda: on_clear_hotkey(script.name),
        )
        self.clear_btn.grid(row=0, column=4, padx=(4, 8))

    def set_status(self, text: str) -> None:
        self.status_lbl.configure(text=text)

    def set_hotkey_label(self, hotkey: str | None) -> None:
        self.hk_btn.configure(text=format_hotkey(hotkey))

    def set_recording(self, active: bool) -> None:
        if active:
            self.hk_btn.configure(text="按下热键…", fg_color=("#c47a00", "#a65c00"))
        else:
            self.hk_btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])


class App(ctk.CTk):
    def __init__(
        self,
        workdir: Path,
        config: ConfigStore,
        runtime: AhkRuntime,
        scripts: list[AhkScript],
        ahk_path: Path,
        on_global_toggle: Callable[[], None],
        on_refresh: Callable[[], None],
        on_record_done: Callable[[str, str], None],
        begin_record: Callable[[str], None],
        cancel_record: Callable[[], None],
        rebind_hotkeys: Callable[[], None],
    ) -> None:
        super().__init__()
        self.workdir = workdir
        self.config = config
        self.runtime = runtime
        self.ahk_path = ahk_path
        self._on_global_toggle = on_global_toggle
        self._on_refresh = on_refresh
        self._on_record_done = on_record_done
        self._begin_record = begin_record
        self._cancel_record = cancel_record
        self._rebind_hotkeys = rebind_hotkeys

        self.title("AHK_Filter")
        self.minsize(720, 420)
        self.geometry("860x560")

        self._rows: dict[str, ScriptRow] = {}
        self._recording_target: str | None = None
        self._scripts = scripts

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_list()
        self._build_footer()
        self.reload_scripts(scripts)
        self._sync_status_bar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._poll_status)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="AHK_Filter",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 0))

        self.subtitle = ctk.CTkLabel(
            header,
            text=str(self.workdir),
            anchor="w",
            text_color=("gray35", "gray70"),
        )
        self.subtitle.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))

        self.state_badge = ctk.CTkLabel(
            header,
            text="已终止",
            width=90,
            height=28,
            corner_radius=6,
            fg_color=("gray70", "gray30"),
        )
        self.state_badge.grid(row=0, column=1, rowspan=2, padx=8)

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self)
        bar.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        for i in range(6):
            bar.grid_columnconfigure(i, weight=0)
        bar.grid_columnconfigure(5, weight=1)

        self.btn_start = ctk.CTkButton(bar, text="全局启动", width=100, command=self._ui_start)
        self.btn_start.grid(row=0, column=0, padx=6, pady=8)

        self.btn_stop = ctk.CTkButton(
            bar, text="全局终止", width=100, fg_color=("#a33", "#722"), command=self._ui_stop
        )
        self.btn_stop.grid(row=0, column=1, padx=6, pady=8)

        self.btn_refresh = ctk.CTkButton(bar, text="刷新扫描", width=100, command=self._ui_refresh)
        self.btn_refresh.grid(row=0, column=2, padx=6, pady=8)

        self.global_hk_btn = ctk.CTkButton(
            bar,
            text=f"启停热键: {format_hotkey(self.config.data.get('global_toggle_hotkey'))}",
            width=180,
            command=lambda: self._start_record("global_toggle"),
        )
        self.global_hk_btn.grid(row=0, column=3, padx=6, pady=8)

        self.refresh_hk_btn = ctk.CTkButton(
            bar,
            text=f"刷新热键: {format_hotkey(self.config.data.get('refresh_hotkey'))}",
            width=180,
            command=lambda: self._start_record("refresh"),
        )
        self.refresh_hk_btn.grid(row=0, column=4, padx=6, pady=8)

    def _build_list(self) -> None:
        wrap = ctk.CTkFrame(self)
        wrap.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(wrap, label_text="脚本列表")
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.scroll.grid_columnconfigure(0, weight=1)

        self.empty_lbl = ctk.CTkLabel(
            self.scroll, text="当前目录没有 .ahk 文件", text_color=("gray40", "gray60")
        )

    def _build_footer(self) -> None:
        foot = ctk.CTkFrame(self)
        foot.grid(row=3, column=0, sticky="ew", padx=12, pady=(6, 12))
        foot.grid_columnconfigure(0, weight=1)
        self.footer = ctk.CTkLabel(foot, text="", anchor="w")
        self.footer.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    def reload_scripts(self, scripts: list[AhkScript]) -> None:
        self._scripts = scripts
        for child in self.scroll.winfo_children():
            child.destroy()
        self._rows.clear()

        if not scripts:
            self.empty_lbl = ctk.CTkLabel(
                self.scroll, text="当前目录没有 .ahk 文件", text_color=("gray40", "gray60")
            )
            self.empty_lbl.grid(row=0, column=0, pady=24)
            self._adapt_geometry(0)
            return

        for i, script in enumerate(scripts):
            entry = self.config.script_entry(script.name)
            rt = self.runtime.state.scripts.get(script.name)
            selected = bool(entry.get("enabled", True)) if rt is None else rt.selected
            status = self._status_text(script.name)
            row = ScriptRow(
                self.scroll,
                script=script,
                selected=selected,
                hotkey=entry.get("hotkey"),
                status=status,
                on_toggle_selected=self._on_toggle_selected,
                on_record_hotkey=lambda name: self._start_record(f"script:{name}"),
                on_clear_hotkey=self._clear_script_hotkey,
            )
            row.grid(row=i, column=0, sticky="ew", pady=3)
            self._rows[script.name] = row

        self._adapt_geometry(len(scripts))
        self._sync_status_bar()

    def _adapt_geometry(self, count: int) -> None:
        # Grow window height with script count, capped for usability.
        base = 360
        per = 64
        height = min(820, max(420, base + count * per))
        width = 860 if count <= 8 else 940
        self.geometry(f"{width}x{height}")
        label = f"脚本列表（{count}）"
        try:
            self.scroll.configure(label_text=label)
        except Exception:
            pass

    def _status_text(self, name: str) -> str:
        rt = self.runtime.state.scripts.get(name)
        if not self.runtime.state.running:
            return "待命"
        if not rt:
            return "—"
        if not rt.selected:
            return "未勾选"
        return "生效" if rt.effective else "暂停"

    def _on_toggle_selected(self, name: str, selected: bool) -> None:
        entry = self.config.script_entry(name)
        entry["enabled"] = selected
        self.config.save()
        self.runtime.set_selected(name, selected)
        self._refresh_row_status()

    def _clear_script_hotkey(self, name: str) -> None:
        entry = self.config.script_entry(name)
        entry["hotkey"] = None
        self.config.save()
        if name in self._rows:
            self._rows[name].set_hotkey_label(None)
        self._rebind_hotkeys()
        self._sync_status_bar()

    def _start_record(self, target: str) -> None:
        if self._recording_target:
            self._cancel_record()
            self._reset_record_ui()
        self._recording_target = target
        if target == "global_toggle":
            self.global_hk_btn.configure(text="按下热键…")
        elif target == "refresh":
            self.refresh_hk_btn.configure(text="按下热键…")
        elif target.startswith("script:"):
            name = target.split(":", 1)[1]
            if name in self._rows:
                self._rows[name].set_recording(True)
        self._begin_record(target)

    def finish_record(self, target: str, hotkey: str) -> None:
        """Called from main thread after a hotkey was captured."""
        self._recording_target = None
        hotkey = normalize_hotkey(hotkey) or hotkey
        owners = self.config.all_hotkeys()
        existing = owners.get(hotkey.lower())
        if existing and existing != target:
            messagebox.showwarning(
                "热键冲突",
                f"热键 {format_hotkey(hotkey)} 已被 {existing} 占用",
            )
            self._reset_record_ui()
            return

        if target == "global_toggle":
            self.config.data["global_toggle_hotkey"] = hotkey
            self.global_hk_btn.configure(
                text=f"启停热键: {format_hotkey(hotkey)}"
            )
        elif target == "refresh":
            self.config.data["refresh_hotkey"] = hotkey
            self.refresh_hk_btn.configure(
                text=f"刷新热键: {format_hotkey(hotkey)}"
            )
        elif target.startswith("script:"):
            name = target.split(":", 1)[1]
            entry = self.config.script_entry(name)
            entry["hotkey"] = hotkey
            if name in self._rows:
                self._rows[name].set_recording(False)
                self._rows[name].set_hotkey_label(hotkey)

        self.config.save()
        self._rebind_hotkeys()
        self._reset_record_ui()
        self._sync_status_bar()

    def _reset_record_ui(self) -> None:
        self.global_hk_btn.configure(
            text=f"启停热键: {format_hotkey(self.config.data.get('global_toggle_hotkey'))}"
        )
        self.refresh_hk_btn.configure(
            text=f"刷新热键: {format_hotkey(self.config.data.get('refresh_hotkey'))}"
        )
        for name, row in self._rows.items():
            row.set_recording(False)
            row.set_hotkey_label(self.config.script_entry(name).get("hotkey"))

    def _ui_start(self) -> None:
        try:
            self.runtime.global_start()
        except Exception as exc:
            messagebox.showerror("启动失败", str(exc))
        self._sync_status_bar()
        self._refresh_row_status()

    def _ui_stop(self) -> None:
        try:
            self.runtime.global_stop()
        except Exception as exc:
            messagebox.showerror("终止失败", str(exc))
        self._sync_status_bar()
        self._refresh_row_status()

    def _ui_refresh(self) -> None:
        if self.runtime.state.running:
            messagebox.showinfo("无法刷新", "请先全局终止，再刷新扫描。")
            return
        try:
            self._on_refresh()
        except Exception as exc:
            messagebox.showerror("刷新失败", str(exc))

    def _refresh_row_status(self) -> None:
        for name, row in self._rows.items():
            row.set_status(self._status_text(name))

    def _sync_status_bar(self) -> None:
        running = self.runtime.state.running
        if running:
            self.state_badge.configure(text="运行中", fg_color=("#2f9e44", "#2b8a3e"))
            self.btn_refresh.configure(state="disabled")
        else:
            self.state_badge.configure(text="已终止", fg_color=("gray70", "gray30"))
            self.btn_refresh.configure(state="normal")

        n = len(self._scripts)
        selected = sum(
            1
            for s in self._scripts
            if self.runtime.state.scripts.get(s.name)
            and self.runtime.state.scripts[s.name].selected
        )
        self.footer.configure(
            text=(
                f"工作目录: {self.workdir}  |  AutoHotkey: {self.ahk_path.name}  |  "
                f"脚本 {n} 个 / 勾选 {selected} 个  |  "
                f"启停 {format_hotkey(self.config.data.get('global_toggle_hotkey'))}  "
                f"刷新 {format_hotkey(self.config.data.get('refresh_hotkey'))}"
            )
        )

    def _poll_status(self) -> None:
        self._refresh_row_status()
        self._sync_status_bar()
        self.after(500, self._poll_status)

    def _on_close(self) -> None:
        try:
            # Keep processes? On exit, stop effectiveness but leave option to terminate.
            self.runtime.global_stop()
            self.runtime.terminate_all()
        except Exception:
            pass
        self.destroy()
