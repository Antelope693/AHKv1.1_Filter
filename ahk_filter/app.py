"""CustomTkinter front-end for AHK_Filter."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from . import __version__
from .config import ConfigStore
from .handbook import HandbookWindow
from .hotkeys import format_hotkey, normalize_hotkey
from .runtime import AhkRuntime
from .scanner import AhkScript, ScanResult


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

COLOR_RUNNING = ("#2563eb", "#1d4ed8")  # blue — started
COLOR_STOPPED = ("#dc2626", "#b91c1c")  # red — not started
COLOR_MUTED = ("gray75", "gray35")


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
        indent: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.script_id = script.script_id

        self.grid_columnconfigure(1, weight=1)

        self.var = tk.BooleanVar(value=selected)
        self.chk = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var,
            width=28,
            command=lambda: on_toggle_selected(script.script_id, bool(self.var.get())),
        )
        self.chk.grid(row=0, column=0, padx=(8 + indent, 4), pady=8, sticky="w")

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        info.grid_columnconfigure(0, weight=1)

        title = script.name if script.group is None else f"{script.script_id}"
        self.title_lbl = ctk.CTkLabel(
            info, text=title, anchor="w", font=ctk.CTkFont(size=13, weight="bold")
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
            command=lambda: on_record_hotkey(script.script_id),
        )
        self.hk_btn.grid(row=0, column=3, padx=4)

        self.clear_btn = ctk.CTkButton(
            self,
            text="清除",
            width=56,
            fg_color=COLOR_MUTED,
            command=lambda: on_clear_hotkey(script.script_id),
        )
        self.clear_btn.grid(row=0, column=4, padx=(4, 8))

    def set_status(self, text: str) -> None:
        self.status_lbl.configure(text=text)

    def set_hotkey_label(self, hotkey: str | None) -> None:
        self.hk_btn.configure(text=format_hotkey(hotkey))

    def set_selected(self, selected: bool) -> None:
        self.var.set(selected)

    def set_recording(self, active: bool) -> None:
        if active:
            self.hk_btn.configure(text="按下热键…", fg_color=("#c47a00", "#a65c00"))
        else:
            self.hk_btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])


class GroupSection(ctk.CTkFrame):
    def __init__(
        self,
        master,
        group_name: str,
        scripts: list[AhkScript],
        collapsed: bool,
        config: ConfigStore,
        runtime: AhkRuntime,
        on_toggle_group: Callable[[str, bool], None],
        on_toggle_collapsed: Callable[[str, bool], None],
        build_row: Callable[[ctk.CTkFrame, AhkScript, int], ScriptRow],
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.group_name = group_name
        self.scripts = scripts
        self._on_toggle_collapsed = on_toggle_collapsed
        self._collapsed = collapsed
        self._rows: list[ScriptRow] = []

        self.grid_columnconfigure(1, weight=1)

        self.toggle_btn = ctk.CTkButton(
            self,
            text="▶" if collapsed else "▼",
            width=32,
            command=self._toggle_collapse,
        )
        self.toggle_btn.grid(row=0, column=0, padx=(8, 4), pady=8, sticky="w")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=1, sticky="ew", pady=6)
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=group_name,
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text=f"{len(scripts)} 个脚本",
            anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=1, column=0, sticky="w")

        all_selected = all(
            runtime.state.scripts.get(s.script_id)
            and runtime.state.scripts[s.script_id].selected
            for s in scripts
        ) if scripts else False
        self.group_var = tk.BooleanVar(value=all_selected)
        self.group_chk = ctk.CTkCheckBox(
            self,
            text="全选",
            variable=self.group_var,
            command=lambda: on_toggle_group(group_name, bool(self.group_var.get())),
        )
        self.group_chk.grid(row=0, column=2, padx=8, pady=8)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, columnspan=3, sticky="ew", padx=(12, 0))
        self.body.grid_columnconfigure(0, weight=1)

        for i, script in enumerate(scripts):
            row = build_row(self.body, script, indent=12)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            self._rows.append(row)

        if collapsed:
            self.body.grid_remove()

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self.toggle_btn.configure(text="▶" if self._collapsed else "▼")
        if self._collapsed:
            self.body.grid_remove()
        else:
            self.body.grid()
        self._on_toggle_collapsed(self.group_name, self._collapsed)

    def refresh_group_checkbox(self, runtime: AhkRuntime) -> None:
        if not self.scripts:
            return
        all_selected = all(
            runtime.state.scripts.get(s.script_id)
            and runtime.state.scripts[s.script_id].selected
            for s in self.scripts
        )
        self.group_var.set(all_selected)

    @property
    def rows(self) -> list[ScriptRow]:
        return self._rows


class App(ctk.CTk):
    _SPIN = ("◐", "◓", "◑", "◒")

    def __init__(
        self,
        workdir: Path,
        config: ConfigStore,
        runtime: AhkRuntime,
        scan: ScanResult,
        ahk_path: Path,
        on_global_toggle: Callable[[], None],
        on_refresh: Callable[[], None],
        begin_record: Callable[[str], None],
        cancel_record: Callable[[], None],
        rebind_hotkeys: Callable[[], None],
    ) -> None:
        super().__init__()
        self.workdir = workdir
        self.config = config
        self.runtime = runtime
        self.scan = scan
        self.ahk_path = ahk_path
        self._on_global_toggle = on_global_toggle
        self._on_refresh = on_refresh
        self._begin_record = begin_record
        self._cancel_record = cancel_record
        self._rebind_hotkeys = rebind_hotkeys

        self.title(f"AHK_Filter  v{__version__}")
        self.minsize(760, 460)
        self.geometry("920x600")

        self._rows: dict[str, ScriptRow] = {}
        self._groups: dict[str, GroupSection] = {}
        self._recording_target: str | None = None
        self._test_open = False
        self._refreshing = False
        self._spin_idx = 0
        self._handbook: HandbookWindow | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_test_panel()
        self._build_list()
        self._build_footer()
        self.reload_scan(scan)
        self._sync_status_bar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(400, self._poll_status)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 2))
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="w", padx=6, pady=(4, 0))

        ctk.CTkLabel(
            title_row,
            text="AHK_Filter",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text="  By SYL",
            font=ctk.CTkFont(size=12),
            text_color=("gray45", "gray65"),
            anchor="sw",
        ).pack(side="left", pady=(10, 0))

        self.subtitle = ctk.CTkLabel(
            header,
            text=str(self.scan.scripts_dir),
            anchor="w",
            text_color=("gray40", "gray65"),
            font=ctk.CTkFont(size=12),
        )
        self.subtitle.grid(row=1, column=0, sticky="w", padx=6, pady=(2, 6))

        self.state_badge = ctk.CTkLabel(
            header,
            text="未启动  ▶",
            width=108,
            height=30,
            corner_radius=8,
            fg_color=COLOR_STOPPED,
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.state_badge.grid(row=0, column=1, rowspan=2, padx=8)

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, corner_radius=12)
        bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 6))
        bar.grid_columnconfigure(4, weight=1)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # Merged start/stop: red = stopped (+ play), blue = running (+ pause)
        self.btn_toggle = ctk.CTkButton(
            left,
            text="未启动  ▶",
            width=128,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_STOPPED,
            hover_color=("#ef4444", "#991b1b"),
            command=self._ui_toggle,
        )
        self.btn_toggle.pack(side="left", padx=(0, 8))

        self.global_hk_btn = ctk.CTkButton(
            left,
            text=f"启停热键  {format_hotkey(self.config.data.get('global_toggle_hotkey'))}",
            width=210,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
            command=lambda: self._start_record("global_toggle"),
        )
        self.global_hk_btn.pack(side="left", padx=(0, 8))

        self.btn_test = ctk.CTkButton(
            left,
            text="TEST",
            width=78,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#64748b", "#475569"),
            hover_color=("#475569", "#334155"),
            command=self._toggle_test_panel,
        )
        self.btn_test.pack(side="left", padx=(0, 8))

        # Prominent handbook button
        self.btn_book = ctk.CTkButton(
            left,
            text="📖  手册",
            width=96,
            height=38,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0ea5e9", "#0284c7"),
            hover_color=("#0284c7", "#0369a1"),
            text_color="white",
            command=self._open_handbook,
        )
        self.btn_book.pack(side="left")

    def _build_test_panel(self) -> None:
        self.test_panel = ctk.CTkFrame(self, corner_radius=8)
        # Not gridded until opened — sits between toolbar (row1) and list (row3)
        self.test_panel.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.test_panel, text="TEST", width=56, font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(12, 6), pady=10
        )
        self.test_entry = ctk.CTkEntry(
            self.test_panel,
            placeholder_text="在此输入以验证脚本键鼠行为（不另开窗口）",
            height=34,
        )
        self.test_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=10)

        ctk.CTkButton(
            self.test_panel,
            text="清空",
            width=64,
            height=32,
            fg_color=COLOR_MUTED,
            command=lambda: self.test_entry.delete(0, "end"),
        ).grid(row=0, column=2, padx=(4, 6), pady=10)

        ctk.CTkButton(
            self.test_panel,
            text="收起",
            width=64,
            height=32,
            fg_color=COLOR_MUTED,
            command=self._toggle_test_panel,
        ).grid(row=0, column=3, padx=(0, 12), pady=10)

    def _build_list(self) -> None:
        wrap = ctk.CTkFrame(self)
        wrap.grid(row=3, column=0, sticky="nsew", padx=14, pady=6)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=1)

        list_hdr = ctk.CTkFrame(wrap, fg_color="transparent")
        list_hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        list_hdr.grid_columnconfigure(0, weight=1)

        self.list_title = ctk.CTkLabel(
            list_hdr,
            text="脚本列表",
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.list_title.grid(row=0, column=0, sticky="w", padx=4)

        self.btn_refresh = ctk.CTkButton(
            list_hdr,
            text="↻",
            width=36,
            height=28,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray25"),
            command=self._ui_refresh,
        )
        self.btn_refresh.grid(row=0, column=1, padx=4)

        self.scroll = ctk.CTkScrollableFrame(wrap, label_text="")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.scroll.grid_columnconfigure(0, weight=1)

    def _build_footer(self) -> None:
        foot = ctk.CTkFrame(self)
        foot.grid(row=4, column=0, sticky="ew", padx=14, pady=(4, 12))
        foot.grid_columnconfigure(0, weight=1)
        self.footer = ctk.CTkLabel(foot, text="", anchor="w")
        self.footer.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    def _toggle_test_panel(self) -> None:
        self._test_open = not self._test_open
        if self._test_open:
            self.test_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 4))
            self.btn_test.configure(fg_color=COLOR_RUNNING, hover_color=("#3b82f6", "#1e40af"))
            self.after(30, lambda: self.test_entry.focus_set())
        else:
            self.test_panel.grid_remove()
            self.btn_test.configure(
                fg_color=("#64748b", "#475569"),
                hover_color=("#475569", "#334155"),
            )

    def _open_handbook(self) -> None:
        if self._handbook is not None and self._handbook.winfo_exists():
            self._handbook.focus()
            return

        def before_relaunch() -> None:
            try:
                self.runtime.global_stop()
                self.runtime.terminate_all()
            except Exception:
                pass

        self._handbook = HandbookWindow(self, self.workdir, on_updated=before_relaunch)

    def _build_row(self, parent: ctk.CTkFrame, script: AhkScript, indent: int = 0) -> ScriptRow:
        entry = self.config.script_entry(script.script_id)
        rt = self.runtime.state.scripts.get(script.script_id)
        selected = bool(entry.get("enabled", False)) if rt is None else rt.selected
        row = ScriptRow(
            parent,
            script=script,
            selected=selected,
            hotkey=entry.get("hotkey"),
            status=self._status_text(script.script_id),
            on_toggle_selected=self._on_toggle_selected,
            on_record_hotkey=lambda sid: self._start_record(f"script:{sid}"),
            on_clear_hotkey=self._clear_script_hotkey,
            indent=indent,
        )
        self._rows[script.script_id] = row
        return row

    def reload_scan(self, scan: ScanResult) -> None:
        self.scan = scan
        self.subtitle.configure(text=str(scan.scripts_dir))
        for child in self.scroll.winfo_children():
            child.destroy()
        self._rows.clear()
        self._groups.clear()

        total = scan.total_count
        self.list_title.configure(text=f"脚本列表（{total}）")
        if total == 0:
            ctk.CTkLabel(
                self.scroll,
                text="scripts 目录中没有 .ahk 文件\n请将脚本放入 scripts/ 或其子文件夹",
                text_color=("gray40", "gray60"),
            ).grid(row=0, column=0, pady=24)
            self._adapt_geometry(0)
            return

        row_idx = 0
        for group in scan.groups:
            section = GroupSection(
                self.scroll,
                group_name=group.name,
                scripts=group.scripts,
                collapsed=self.config.is_group_collapsed(group.name),
                config=self.config,
                runtime=self.runtime,
                on_toggle_group=self._on_toggle_group,
                on_toggle_collapsed=self._on_toggle_collapsed,
                build_row=self._build_row,
            )
            section.grid(row=row_idx, column=0, sticky="ew", pady=6)
            self._groups[group.name] = section
            row_idx += 1

        if scan.loose:
            loose_hdr = ctk.CTkFrame(self.scroll, fg_color=("gray85", "gray20"))
            loose_hdr.grid(row=row_idx, column=0, sticky="ew", pady=(12, 4))
            loose_hdr.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                loose_hdr,
                text=f"散装脚本（{len(scan.loose)}）",
                anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=8)
            row_idx += 1

            for script in scan.loose:
                row = self._build_row(self.scroll, script, indent=0)
                row.grid(row=row_idx, column=0, sticky="ew", pady=2)
                row_idx += 1

        self._adapt_geometry(total)
        self._sync_status_bar()

    def _adapt_geometry(self, count: int) -> None:
        base = 400
        per = 52
        height = min(920, max(460, base + count * per))
        width = 920 if count <= 10 else 1000
        self.geometry(f"{width}x{height}")

    def _status_text(self, script_id: str) -> str:
        rt = self.runtime.state.scripts.get(script_id)
        if not self.runtime.state.running:
            return "待命"
        if not rt:
            return "—"
        if not rt.selected:
            return "未勾选"
        return "生效" if rt.effective else "暂停"

    def _on_toggle_selected(self, script_id: str, selected: bool) -> None:
        entry = self.config.script_entry(script_id)
        entry["enabled"] = selected
        self.config.save()
        self.runtime.set_selected(script_id, selected)
        for section in self._groups.values():
            section.refresh_group_checkbox(self.runtime)
        self._refresh_row_status()

    def _on_toggle_group(self, group_name: str, selected: bool) -> None:
        group = next((g for g in self.scan.groups if g.name == group_name), None)
        if not group:
            return
        for script in group.scripts:
            entry = self.config.script_entry(script.script_id)
            entry["enabled"] = selected
            self.runtime.set_selected(script.script_id, selected)
            if script.script_id in self._rows:
                self._rows[script.script_id].set_selected(selected)
        self.config.save()
        section = self._groups.get(group_name)
        if section:
            section.refresh_group_checkbox(self.runtime)
        self._refresh_row_status()
        self._sync_status_bar()

    def _on_toggle_collapsed(self, group_name: str, collapsed: bool) -> None:
        self.config.set_group_collapsed(group_name, collapsed)
        self.config.save()

    def _clear_script_hotkey(self, script_id: str) -> None:
        entry = self.config.script_entry(script_id)
        entry["hotkey"] = None
        self.config.save()
        if script_id in self._rows:
            self._rows[script_id].set_hotkey_label(None)
        self._rebind_hotkeys()
        self._sync_status_bar()

    def _start_record(self, target: str) -> None:
        if self._recording_target:
            self._cancel_record()
            self._reset_record_ui()
        self._recording_target = target
        if target == "global_toggle":
            self.global_hk_btn.configure(text="按下热键…")
        elif target.startswith("script:"):
            sid = target.split(":", 1)[1]
            if sid in self._rows:
                self._rows[sid].set_recording(True)
        self._begin_record(target)

    def finish_record(self, target: str, hotkey: str) -> None:
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
                text=f"启停热键  {format_hotkey(hotkey)}"
            )
        elif target.startswith("script:"):
            sid = target.split(":", 1)[1]
            entry = self.config.script_entry(sid)
            entry["hotkey"] = hotkey
            if sid in self._rows:
                self._rows[sid].set_recording(False)
                self._rows[sid].set_hotkey_label(hotkey)

        self.config.save()
        self._rebind_hotkeys()
        self._reset_record_ui()
        self._sync_status_bar()

    def _reset_record_ui(self) -> None:
        self.global_hk_btn.configure(
            text=f"启停热键  {format_hotkey(self.config.data.get('global_toggle_hotkey'))}"
        )
        for sid, row in self._rows.items():
            row.set_recording(False)
            row.set_hotkey_label(self.config.script_entry(sid).get("hotkey"))

    def _ui_toggle(self) -> None:
        if self.runtime.state.running:
            self._ui_stop()
        else:
            self._ui_start()

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
        if self._refreshing:
            return
        if self.runtime.state.running:
            messagebox.showinfo("无法刷新", "请先全局终止（点击蓝色按钮），再刷新扫描。")
            return
        self._refreshing = True
        self._spin_idx = 0
        self._animate_refresh()
        try:
            self._on_refresh()
        except Exception as exc:
            messagebox.showerror("刷新失败", str(exc))
        finally:
            self.after(350, self._finish_refresh_spin)

    def _animate_refresh(self) -> None:
        if not self._refreshing:
            self.btn_refresh.configure(text="↻")
            return
        self.btn_refresh.configure(text=self._SPIN[self._spin_idx % len(self._SPIN)])
        self._spin_idx += 1
        self.after(90, self._animate_refresh)

    def _finish_refresh_spin(self) -> None:
        self._refreshing = False
        self.btn_refresh.configure(text="↻")

    def _refresh_row_status(self) -> None:
        for sid, row in self._rows.items():
            row.set_status(self._status_text(sid))

    def _sync_status_bar(self) -> None:
        running = self.runtime.state.running
        if running:
            self.state_badge.configure(text="运行中  ■", fg_color=COLOR_RUNNING)
            self.btn_toggle.configure(
                text="运行中  ■",
                fg_color=COLOR_RUNNING,
                hover_color=("#3b82f6", "#1e40af"),
            )
            self.btn_refresh.configure(state="disabled")
        else:
            self.state_badge.configure(text="未启动  ▶", fg_color=COLOR_STOPPED)
            self.btn_toggle.configure(
                text="未启动  ▶",
                fg_color=COLOR_STOPPED,
                hover_color=("#ef4444", "#991b1b"),
            )
            self.btn_refresh.configure(state="normal")

        total = self.scan.total_count
        selected = sum(1 for rt in self.runtime.state.scripts.values() if rt.selected)
        self.footer.configure(
            text=(
                f"v{__version__}  |  {self.scan.scripts_dir}  |  "
                f"AHK: {self.ahk_path.name}  |  "
                f"脚本 {total} / 勾选 {selected}  |  "
                f"启停 {format_hotkey(self.config.data.get('global_toggle_hotkey'))}"
            )
        )

    def _poll_status(self) -> None:
        self._refresh_row_status()
        for section in self._groups.values():
            section.refresh_group_checkbox(self.runtime)
        self._sync_status_bar()
        self.after(500, self._poll_status)

    def _on_close(self) -> None:
        try:
            self.runtime.global_stop()
            self.runtime.terminate_all()
        except Exception:
            pass
        self.destroy()
