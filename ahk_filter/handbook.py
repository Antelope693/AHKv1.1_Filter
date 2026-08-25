"""Handbook / changelog window and optional hot-update prompt."""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from . import __version__
from .update import (
    REPO_PAGE,
    ReleaseInfo,
    apply_hot_update,
    fetch_handbook_markdown,
    fetch_latest_release,
    is_newer,
    relaunch_app,
)


class HandbookWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        workdir: Path,
        on_updated: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master)
        self.workdir = workdir
        self.on_updated = on_updated
        self.title("AHK_Filter 手册")
        self.geometry("720x560")
        self.minsize(520, 400)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top,
            text=f"公告 / 使用手册 / 更新记录    v{__version__}",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=8)

        self.status = ctk.CTkLabel(top, text="", anchor="e", text_color=("gray40", "gray65"))
        self.status.grid(row=0, column=1, padx=8)

        ctk.CTkButton(top, text="打开仓库", width=90, command=self._open_repo).grid(
            row=0, column=2, padx=4
        )
        ctk.CTkButton(top, text="检查更新", width=90, command=self._check_update).grid(
            row=0, column=3, padx=4
        )
        ctk.CTkButton(top, text="刷新内容", width=90, command=self._reload).grid(
            row=0, column=4, padx=4
        )

        self.text = ctk.CTkTextbox(
            self, wrap="word", font=ctk.CTkFont(family="Microsoft YaHei UI", size=13)
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.after(50, self._reload)
        self.after(200, self._silent_check_update)

    def _open_repo(self) -> None:
        webbrowser.open(REPO_PAGE)

    def _reload(self) -> None:
        self.status.configure(text="加载中…")
        local = self.workdir / "docs" / "HANDBOOK.md"

        def worker() -> None:
            md = fetch_handbook_markdown(local)
            self.after(0, lambda: self._set_markdown(md))

        threading.Thread(target=worker, daemon=True).start()

    def _set_markdown(self, md: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", md)
        self.text.configure(state="disabled")
        self.status.configure(text="已加载")

    def _silent_check_update(self) -> None:
        def worker() -> None:
            release = fetch_latest_release()
            self.after(0, lambda: self._maybe_prompt_update(release, silent=True))

        threading.Thread(target=worker, daemon=True).start()

    def _check_update(self) -> None:
        self.status.configure(text="检查更新…")

        def worker() -> None:
            release = fetch_latest_release()
            self.after(0, lambda: self._maybe_prompt_update(release, silent=False))

        threading.Thread(target=worker, daemon=True).start()

    def _maybe_prompt_update(self, release: ReleaseInfo | None, silent: bool) -> None:
        if release is None:
            if not silent:
                messagebox.showinfo("检查更新", "暂无可用 Release，或网络不可达。", parent=self)
            self.status.configure(text=f"当前 v{__version__}")
            return
        if not is_newer(release.tag):
            if not silent:
                messagebox.showinfo(
                    "检查更新",
                    f"已是最新版本。\n当前：v{__version__}\n远端：{release.tag}",
                    parent=self,
                )
            self.status.configure(text=f"已是最新 {release.tag}")
            return

        self.status.configure(text=f"发现 {release.tag}")
        detail = release.body.strip()[:800] if release.body else ""
        msg = (
            f"发现新版本 {release.tag}\n"
            f"当前版本 v{__version__}\n\n"
            f"{detail}\n\n"
            "是否热更新？\n"
            "（保留 scripts/ 与热键、勾选等配置）"
        )
        if not messagebox.askyesno("发现新版本", msg, parent=self):
            return
        self._do_update(release)

    def _do_update(self, release: ReleaseInfo) -> None:
        self.status.configure(text="正在更新…")

        def worker() -> None:
            try:
                apply_hot_update(self.workdir, release)
            except Exception as exc:
                self.after(
                    0,
                    lambda: messagebox.showerror("更新失败", str(exc), parent=self),
                )
                self.after(0, lambda: self.status.configure(text="更新失败"))
                return
            self.after(0, lambda: self._finish_update(release))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update(self, release: ReleaseInfo) -> None:
        messagebox.showinfo(
            "更新完成",
            f"已更新到 {release.tag}。\n配置与脚本已保留，即将重启。",
            parent=self,
        )
        try:
            if self.on_updated:
                self.on_updated()
        except Exception:
            pass
        relaunch_app(self.workdir)
