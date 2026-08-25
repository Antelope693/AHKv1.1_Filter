"""Startup environment checks and guided installs."""

from __future__ import annotations

import importlib
import subprocess
import sys
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import messagebox

from .ahk_find import find_autohotkey

REQUIRED_PACKAGES = (
    ("customtkinter", "customtkinter"),
    ("pynput", "pynput"),
    ("win32gui", "pywin32"),
)

AHK_DOWNLOAD = "https://www.autohotkey.com/download/ahk-install.exe"
AHK_PAGE = "https://www.autohotkey.com/"


@dataclass
class EnvIssue:
    kind: str  # package | ahk
    name: str
    detail: str


@dataclass
class EnvReport:
    ok: bool
    issues: list[EnvIssue] = field(default_factory=list)
    ahk_path: Path | None = None


def check_packages() -> list[EnvIssue]:
    issues: list[EnvIssue] = []
    for mod, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(mod)
        except Exception:
            issues.append(
                EnvIssue("package", pip_name, f"缺少 Python 包：{pip_name}")
            )
    return issues


def check_ahk() -> tuple[Path | None, EnvIssue | None]:
    path = find_autohotkey()
    if path:
        return path, None
    return None, EnvIssue("ahk", "AutoHotkey v1.1", "未找到 AutoHotkey v1.x 可执行文件")


def check_environment() -> EnvReport:
    issues = check_packages()
    ahk, ahk_issue = check_ahk()
    if ahk_issue:
        issues.append(ahk_issue)
    return EnvReport(ok=not issues, issues=issues, ahk_path=ahk)


def install_packages(names: list[str]) -> tuple[bool, str]:
    if not names:
        return True, ""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *names]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or "pip install failed")[-2000:]
        return True, ""
    except Exception as exc:
        return False, str(exc)


def download_ahk_installer(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(AHK_DOWNLOAD, dest)
    return dest


def guide_fix_environment(report: EnvReport, workdir: Path) -> EnvReport:
    """
    If environment is incomplete, prompt and attempt guided installs.
    Returns a fresh report after remediation attempts.
    Silent when already OK.
    """
    if report.ok:
        return report

    lines = ["检测到运行环境不完整：", ""]
    for issue in report.issues:
        lines.append(f"• {issue.detail}")
    lines.append("")
    lines.append("是否由 AHK_Filter 协助安装缺失项？")
    if not messagebox.askyesno("环境检测", "\n".join(lines)):
        messagebox.showwarning(
            "环境检测",
            "未完成依赖安装，程序可能无法正常运行。",
        )
        return check_environment()

    package_names = [i.name for i in report.issues if i.kind == "package"]
    if package_names:
        ok, err = install_packages(package_names)
        if not ok:
            messagebox.showerror("安装失败", f"pip 安装失败：\n{err}")

    need_ahk = any(i.kind == "ahk" for i in report.issues)
    if need_ahk and find_autohotkey() is None:
        try:
            installer = download_ahk_installer(workdir / ".cache" / "ahk-install.exe")
            messagebox.showinfo(
                "安装 AutoHotkey",
                "即将打开 AutoHotkey 安装程序。\n"
                "请安装 v1.1（Unicode 64-bit 即可），完成后回到本程序。",
            )
            subprocess.Popen([str(installer)], shell=True)
            webbrowser.open(AHK_PAGE)
            messagebox.showinfo("安装 AutoHotkey", "安装完成后点击确定继续检测。")
        except Exception as exc:
            messagebox.showerror(
                "下载失败",
                f"无法自动下载 AutoHotkey 安装包：\n{exc}\n\n请手动访问：\n{AHK_PAGE}",
            )
            webbrowser.open(AHK_PAGE)

    return check_environment()
