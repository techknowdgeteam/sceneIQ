# -*- coding: utf-8 -*-
"""SceneIQ first-run setup and dependency verifier.

This launcher is intentionally GUI-only. It checks the exact imports used by
sceneiqvideoproduction.py and sceniqimageproduction.py, installs only missing
third-party distributions, prepares the application folders/assets, verifies
both engines, and opens the shared SceneIQ desktop only on success.
"""
from __future__ import annotations

import ast
import base64
import importlib.util
import json
import os
import random
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "SCiQ / SceneIQ"
INSTALL_DIR = Path(r"C:\xampp\htdocs\AI automation\scenIQ")

# The updater points setup at the selected matched pair from Downloads.
_VIDEO_OVERRIDE = os.environ.get("SCENEIQ_SOURCE_VIDEO_SCRIPT", "").strip()
_IMAGE_OVERRIDE = os.environ.get("SCENEIQ_SOURCE_IMAGE_SCRIPT", "").strip()
SOURCE_DIR = Path(_VIDEO_OVERRIDE).expanduser().resolve().parent if _VIDEO_OVERRIDE else Path(__file__).resolve().parent
SOURCE_VIDEO_SCRIPT = Path(_VIDEO_OVERRIDE).expanduser().resolve() if _VIDEO_OVERRIDE else SOURCE_DIR / "sceneiqvideoproduction.py"
SOURCE_IMAGE_SCRIPT = Path(_IMAGE_OVERRIDE).expanduser().resolve() if _IMAGE_OVERRIDE else SOURCE_DIR / "sceniqimageproduction.py"
SETUP_SCRIPT_NAME = "sceniq_setup.pyw"
LAUNCHER_NAME = "Start_SceneIQ.vbs"

PACKAGE_MAP = {
    "PIL": "Pillow",
    "ctranslate2": "ctranslate2",
    "faster_whisper": "faster-whisper",
    "imageio_ffmpeg": "imageio-ffmpeg",
    "moviepy": "moviepy",
    "numpy": "numpy",
    "proglog": "proglog",
    "psutil": "psutil",
    "cv2": "opencv-python",
    "keyboard": "keyboard",
    "pyautogui": "PyAutoGUI",
    "pyperclip": "pyperclip",
    "ultralytics": "ultralytics",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "win32process": "pywin32",
}

REQUIRED_DIRECTORIES = [
    INSTALL_DIR,
    INSTALL_DIR / "project",
    INSTALL_DIR / "input_images",
    INSTALL_DIR / "gui_images",
    INSTALL_DIR / "subscribe",
    INSTALL_DIR / "video_producer_runs",
]
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# AST scanning sees imports in both sides of an operating-system branch.
# These modules are intentionally unavailable on the opposite platform and
# must not be treated as installable dependencies. SceneIQ targets Windows.
PLATFORM_EXCLUSIVE_IMPORTS = {
    "nt": {
        "fcntl", "grp", "pwd", "resource", "termios", "tty", "pty",
        "spwd", "syslog", "posix", "_posixsubprocess",
    },
    "posix": {
        "msvcrt", "winreg", "win32api", "win32clipboard", "win32con",
        "win32event", "win32file", "win32gui", "win32process", "win32security",
        "win32service", "win32timezone", "winsound",
    },
}


def _windows_dark_titlebar(window, background="#07111F", foreground="#EAF5FF"):
    """Ask Windows DWM to render the native title bar in SceneIQ's dark palette."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        window.update_idletasks()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = wintypes.HWND(window.winfo_id())
        try:
            root_hwnd = user32.GetAncestor(hwnd, 2)  # GA_ROOT
            if root_hwnd:
                hwnd = root_hwnd
        except Exception:
            pass
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        set_attribute = dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        set_attribute.restype = ctypes.c_long

        enabled = ctypes.c_int(1)
        size = ctypes.sizeof(enabled)
        # Attribute 20 is current; 19 is supported by older Windows 10 builds.
        dark_enabled = False
        for attribute in (20, 19):
            try:
                if set_attribute(hwnd, attribute, ctypes.byref(enabled), size) == 0:
                    dark_enabled = True
                    break
            except Exception:
                continue

        def colorref(hex_color):
            value = str(hex_color).lstrip("#")
            red, green, blue = (int(value[i:i+2], 16) for i in (0, 2, 4))
            return blue << 16 | green << 8 | red

        # Windows 11 caption/text color attributes. Unsupported builds ignore them.
        for attribute, color in ((35, background), (36, foreground), (34, background)):
            try:
                value = wintypes.DWORD(colorref(color))
                set_attribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
            except Exception:
                pass
        return dark_enabled
    except Exception:
        return False


class SetupFailure(RuntimeError):
    pass


class SceneIQSetup:
    BG = "#07111F"
    PANEL = "#0D1B2D"
    PANEL2 = "#10243A"
    BORDER = "#1E4968"
    TEXT = "#EAF5FF"
    MUTED = "#9BB4C9"
    CYAN = "#24C8F5"
    GREEN = "#31D58A"
    RED = "#FF657A"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.thread: threading.Thread | None = None
        self.started = False
        self.completed = False
        self.failed = False
        self.install_log: list[str] = []
        self.log_file = INSTALL_DIR / "sceneiq_setup.log"
        self.main_script = INSTALL_DIR / "sceneiqvideoproduction.py"
        self.python_console = self._python_console_executable()
        self._build_ui()
        self.root.after(180, lambda: _windows_dark_titlebar(self.root, self.BG, self.TEXT))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_events)
        self.root.after(350, self.start_setup)

    def _python_console_executable(self) -> str:
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            sibling = exe.with_name("python.exe")
            if sibling.is_file():
                return str(sibling)
        return str(exe)

    def _build_ui(self):
        self.root.title("SCiQ • SceneIQ Setup Center")
        self.root.configure(bg=self.BG)
        try:
            icon_candidate = SOURCE_DIR / "SceneIQ.ico"
            if icon_candidate.is_file():
                self.root.iconbitmap(str(icon_candidate))
        except Exception:
            pass
        self.root.geometry("760x540")
        self.root.minsize(680, 480)
        self._center(760, 540)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "SCiQ.Green.Horizontal.TProgressbar",
            troughcolor="#173049", background=self.GREEN,
            bordercolor="#173049", lightcolor=self.GREEN,
            darkcolor=self.GREEN, thickness=13,
        )

        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=22, pady=18)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x")
        brand = tk.Label(
            header, text="SCiQ", bg="#073A5B", fg=self.CYAN,
            font=("Segoe UI", 15, "bold"), width=5, height=2,
        )
        brand.pack(side="left", padx=(0, 12))
        brand_text = tk.Frame(header, bg=self.BG)
        brand_text.pack(side="left", fill="y")
        tk.Label(
            brand_text, text="SCiQ  /  SCENEIQ", bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand_text, text="AUTOMATION CONTROL CENTER", bg=self.BG,
            fg=self.MUTED, font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header, text="FIRST-RUN ENVIRONMENT CHECK", bg=self.BG,
            fg=self.CYAN, font=("Segoe UI", 9, "bold"),
        ).pack(side="right", anchor="center")

        card = tk.Frame(outer, bg=self.PANEL, highlightthickness=1, highlightbackground=self.BORDER)
        card.pack(fill="both", expand=True, pady=(18, 0))

        art = tk.Canvas(card, width=104, height=104, bg=self.PANEL, highlightthickness=0)
        art.pack(pady=(18, 3))
        self._draw_robot(art)

        self.heading = tk.Label(
            card, text="Preparing SceneIQ", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 18, "bold"),
        )
        self.heading.pack(pady=(2, 4))
        self.subheading = tk.Label(
            card, text="Checking the application, Python libraries and required folders.",
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9),
        )
        self.subheading.pack(pady=(0, 16))

        self.progress = ttk.Progressbar(
            card, style="SCiQ.Green.Horizontal.TProgressbar",
            mode="determinate", maximum=100, value=0,
        )
        self.progress.pack(fill="x", padx=36)

        status_row = tk.Frame(card, bg=self.PANEL)
        status_row.pack(fill="x", padx=36, pady=(8, 4))
        self.status_label = tk.Label(
            status_row, text="Starting checks…", bg=self.PANEL, fg=self.GREEN,
            font=("Segoe UI", 9, "bold"), anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self.percent_label = tk.Label(
            status_row, text="0%", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 9, "bold"),
        )
        self.percent_label.pack(side="right")

        self.log_box = tk.Text(
            card, height=7, bg="#050B14", fg="#B8D6E9",
            insertbackground=self.CYAN, relief="flat", bd=0,
            font=("Consolas", 8), padx=12, pady=9, wrap="word",
            state="disabled",
        )
        self.log_box.pack(fill="both", expand=True, padx=22, pady=(12, 14))

        footer = tk.Frame(outer, bg=self.BG)
        footer.pack(fill="x", pady=(12, 0))
        self.copy_button = tk.Button(
            footer, text="COPY SETUP REPORT", command=self.copy_report,
            bg="#19334C", fg=self.TEXT, activebackground="#244866",
            activeforeground=self.TEXT, relief="flat", padx=16, pady=9,
            font=("Segoe UI", 8, "bold"), cursor="hand2", state="disabled",
        )
        self.copy_button.pack(side="left")
        self.action_button = tk.Button(
            footer, text="CANCEL SETUP", command=self.close,
            bg="#1A2A3D", fg=self.MUTED, activebackground="#263B52",
            activeforeground=self.TEXT, relief="flat", padx=18, pady=9,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        )
        self.action_button.pack(side="right")

    def _draw_robot(self, canvas: tk.Canvas):
        """Draw a compact SCiQ robot mascot; no Serenum S-mark is used."""
        canvas.create_oval(5, 5, 99, 99, outline="#145A7A", width=2)
        canvas.create_oval(17, 10, 87, 75, fill="#DCEBFA", outline="#38C8F4", width=2)
        canvas.create_oval(24, 21, 80, 65, fill="#071426", outline="#2FCBF7", width=2)
        canvas.create_arc(34, 31, 49, 48, start=195, extent=150, style="arc", outline="#55E1FF", width=3)
        canvas.create_arc(56, 31, 71, 48, start=195, extent=150, style="arc", outline="#55E1FF", width=3)
        canvas.create_oval(9, 32, 22, 49, fill="#123D5E", outline="#39D3F8", width=2)
        canvas.create_oval(82, 32, 95, 49, fill="#123D5E", outline="#39D3F8", width=2)
        canvas.create_line(52, 74, 52, 88, fill="#9EBBD0", width=5)
        canvas.create_oval(27, 79, 77, 112, fill="#D8E8F6", outline="#37CFF4", width=2)
        canvas.create_text(52, 96, text="SCiQ", fill="#087DAB", font=("Segoe UI", 7, "bold"))

    def _center(self, width, height):
        self.root.update_idletasks()
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _emit(self, kind: str, **data):
        self.events.put((kind, data))

    def _write_log(self, line: str):
        self.install_log.append(line)
        self.install_log = self.install_log[-600:]
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except Exception:
            pass

    def _set_progress(self, value: int, status: str, message: str | None = None):
        self._emit("progress", value=max(0, min(100, int(value))), status=status, message=message)

    def _run_hidden_command(self, command: list[str], env: dict | None = None, cwd: Path | None = None):
        process = subprocess.Popen(
            command,
            cwd=str(cwd or INSTALL_DIR),
            env=env or os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        captured = []
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip("\r\n")
            if line:
                captured.append(line)
                self._emit("log", line=line)
        code = process.wait()
        return code, captured

    def _install_layout(self):
        """Install both producer engines and support tools without touching user data."""
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        for folder in REQUIRED_DIRECTORIES:
            folder.mkdir(parents=True, exist_ok=True)

        destinations = [
            (SOURCE_VIDEO_SCRIPT, INSTALL_DIR / "sceneiqvideoproduction.py", "video"),
            (SOURCE_IMAGE_SCRIPT, INSTALL_DIR / "sceniqimageproduction.py", "image"),
        ]
        # A complete SceneIQ install/update always requires a matched script pair.
        missing_sources = [str(source) for source, _dest, _kind in destinations if not source.is_file()]
        if missing_sources:
            raise SetupFailure(
                "The complete SceneIQ package must include both sceneiqvideoproduction.py "
                "and sceniqimageproduction.py in the same extracted folder. Missing: "
                + "; ".join(missing_sources)
            )

        backup_dir = INSTALL_DIR / "_update_backups"
        for source, destination, kind in destinations:
            source_text = source.read_text(encoding="utf-8-sig")
            compile(source_text, str(source), "exec")
            if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(destination)):
                self._write_log(f"Installed {kind} producer is already the selected source file.")
                continue
            if destination.is_file():
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{destination.stem}_{stamp}{destination.suffix}"
                shutil.copy2(destination, backup_path)
                self._write_log(f"Previous {kind} producer backed up as {backup_path.name}.")
            staged = destination.with_name(destination.name + ".installing")
            shutil.copy2(source, staged)
            compile(staged.read_text(encoding="utf-8-sig"), str(staged), "exec")
            os.replace(staged, destination)
            self._write_log(f"Installed {kind} producer: {destination.name}")

        support_files = (
            "sceniq_setup.pyw", "sceniq_updater.pyw",
            "Start_SceneIQ.vbs", "Update_SceneIQ.vbs", "Install_SceneIQ.vbs",
            "SceneIQ_Launcher.bat", "SceneIQ_Launcher_NoConsole.vbs",
            "requirements-sceneiq.txt", "README_SceneIQ_Desktop_Installer.txt",
            "SceneIQ.ico", "SCiQ_Brand.png", "SceneIQ_AppIcon.png",
            "Robot(1).gif", "Mapping for machine learning(1).gif",
        )
        for filename in support_files:
            source = SOURCE_DIR / filename
            destination = INSTALL_DIR / filename
            if source.is_file() and os.path.normcase(os.path.abspath(source)) != os.path.normcase(os.path.abspath(destination)):
                self._copy_file(source, destination)
                self._write_log(f"Application component refreshed: {filename}")

        # Existing project configuration and working folders are user-owned.
        # Never replace, reset, rewrite or seed panel.json / ready_script.json here.
        for data_name in ("panel.json", "ready_script.json"):
            data_path = INSTALL_DIR / data_name
            self._write_log(
                f"Preserving existing {data_name}." if data_path.exists()
                else f"{data_name} is not present yet; setup will not create or overwrite it."
            )

        for required in (INSTALL_DIR / "sceneiqvideoproduction.py", INSTALL_DIR / "sceniqimageproduction.py"):
            if not required.is_file():
                raise SetupFailure(f"Required producer file was not installed: {required.name}")
            compile(required.read_text(encoding="utf-8-sig"), str(required), "exec")

    def _create_desktop_shortcuts(self):
        """Create and verify SceneIQ and Update SceneIQ shortcuts on Desktop and Start Menu."""
        start_vbs = INSTALL_DIR / "Start_SceneIQ.vbs"
        update_vbs = INSTALL_DIR / "Update_SceneIQ.vbs"
        if not start_vbs.is_file() or not update_vbs.is_file():
            raise SetupFailure("SceneIQ start/update launchers are missing from the complete package.")

        def vb(value: str) -> str:
            return '"' + str(value).replace('"', '""') + '"'

        icon = INSTALL_DIR / "SceneIQ.ico"
        icon_location = f"{icon},0" if icon.is_file() else r"%SystemRoot%\System32\shell32.dll,21"
        marker = INSTALL_DIR / ".sceneiq_shortcut_locations.txt"
        helper = INSTALL_DIR / "_create_sceneiq_shortcuts.vbs"
        script = "\r\n".join([
            "Option Explicit",
            "Dim sh, fso, desktop, programs, appMenu, link, outFile",
            "Set sh = CreateObject(\"WScript.Shell\")",
            "Set fso = CreateObject(\"Scripting.FileSystemObject\")",
            "desktop = sh.SpecialFolders(\"Desktop\")",
            "programs = sh.SpecialFolders(\"Programs\")",
            "appMenu = programs & \"\\SceneIQ\"",
            "If Not fso.FolderExists(appMenu) Then fso.CreateFolder(appMenu)",
            "Set link = sh.CreateShortcut(desktop & \"\\SceneIQ.lnk\")",
            f"link.TargetPath = {vb(start_vbs)}",
            f"link.WorkingDirectory = {vb(INSTALL_DIR)}",
            f"link.IconLocation = {vb(icon_location)}",
            "link.Description = \"Open SCiQ SceneIQ Image & Video Studio\"",
            "link.Save",
            "Set link = sh.CreateShortcut(desktop & \"\\Update SceneIQ.lnk\")",
            f"link.TargetPath = {vb(update_vbs)}",
            f"link.WorkingDirectory = {vb(INSTALL_DIR)}",
            f"link.IconLocation = {vb(icon_location)}",
            "link.Description = \"Find and install the newest SceneIQ producer pair from Downloads\"",
            "link.Save",
            "Set link = sh.CreateShortcut(appMenu & \"\\SceneIQ.lnk\")",
            f"link.TargetPath = {vb(start_vbs)}",
            f"link.WorkingDirectory = {vb(INSTALL_DIR)}",
            f"link.IconLocation = {vb(icon_location)}",
            "link.Description = \"Open SCiQ SceneIQ Image & Video Studio\"",
            "link.Save",
            "Set link = sh.CreateShortcut(appMenu & \"\\Update SceneIQ.lnk\")",
            f"link.TargetPath = {vb(update_vbs)}",
            f"link.WorkingDirectory = {vb(INSTALL_DIR)}",
            f"link.IconLocation = {vb(icon_location)}",
            "link.Description = \"Update SceneIQ from the newest extracted Downloads package\"",
            "link.Save",
            f"Set outFile = fso.CreateTextFile({vb(marker)}, True, True)",
            "outFile.WriteLine desktop",
            "outFile.WriteLine appMenu",
            "outFile.Close",
            "Set link = Nothing",
            "Set outFile = Nothing",
            "Set fso = Nothing",
            "Set sh = Nothing",
        ])
        helper.write_text(script, encoding="utf-8")
        marker.unlink(missing_ok=True)
        wscript = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "wscript.exe"
        if not wscript.is_file():
            raise SetupFailure("Windows Script Host is unavailable; SceneIQ shortcuts could not be created.")
        result = subprocess.run(
            [str(wscript), str(helper)], cwd=str(INSTALL_DIR),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW, timeout=25, check=False,
        )
        if result.returncode != 0 or not marker.is_file():
            raise SetupFailure("Windows did not confirm creation of the SceneIQ Desktop/Start Menu shortcuts.")
        try:
            locations = marker.read_text(encoding="utf-16").splitlines()
            desktop, app_menu = Path(locations[0]), Path(locations[1])
        except Exception as exc:
            raise SetupFailure(f"SceneIQ shortcut locations could not be verified: {exc}") from exc
        expected = [
            desktop / "SceneIQ.lnk", desktop / "Update SceneIQ.lnk",
            app_menu / "SceneIQ.lnk", app_menu / "Update SceneIQ.lnk",
        ]
        missing = [str(path) for path in expected if not path.is_file()]
        if missing:
            raise SetupFailure("SceneIQ setup could not verify all four shortcuts. Missing: " + "; ".join(missing))
        self.shortcut_summary = (
            "Desktop: SceneIQ and Update SceneIQ.\n"
            "Start Menu: Programs > SceneIQ (SceneIQ and Update SceneIQ).\n"
            "Search Windows for SceneIQ or use the desktop shortcut."
        )
        self._write_log("Verified all four SceneIQ shortcuts: two on Desktop and two in Start Menu > Programs > SceneIQ.")
        marker.unlink(missing_ok=True)
        helper.unlink(missing_ok=True)

    @staticmethod
    def _copy_file(source: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(destination)):
            return
        shutil.copy2(source, destination)

    def _extract_imports(self, script_path: Path) -> list[dict]:
        """Collect every direct module path and imported symbol from the script."""
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(script_path))
        targets = set()
        skipped = set()
        incompatible = PLATFORM_EXCLUSIVE_IMPORTS.get(os.name, set())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if module.split(".", 1)[0] in incompatible:
                        skipped.add(module)
                        continue
                    targets.add((module, None))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".", 1)[0] in incompatible:
                    skipped.add(node.module)
                    continue
                for alias in node.names:
                    if alias.name != "*":
                        targets.add((node.module, alias.name))
                if not node.names:
                    targets.add((node.module, None))
        if skipped:
            existing = getattr(self, "_platform_skipped_imports", set())
            existing.update(skipped)
            self._platform_skipped_imports = existing
        return [
            {"module": module, "member": member}
            for module, member in sorted(targets, key=lambda item: (item[0], item[1] or ""))
        ]

    def _module_root(self, module: str) -> str:
        return module.split(".", 1)[0]

    def _is_stdlib(self, module: str) -> bool:
        root = self._module_root(module)
        stdlib = getattr(sys, "stdlib_module_names", set())
        # imghdr is part of the supported Python 3.10–3.12 runtimes; it was
        # removed only in Python 3.13, which this setup intentionally rejects.
        return root in stdlib or root in sys.builtin_module_names or root == "imghdr"

    def _find_missing(self, imports: list[dict]):
        missing = []
        unknown = []
        checked_modules = set()
        for item in imports:
            module = item["module"]
            if module in checked_modules or self._is_stdlib(module):
                continue
            checked_modules.add(module)
            try:
                spec = importlib.util.find_spec(module)
            except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
                spec = None
            if spec is None:
                distribution = PACKAGE_MAP.get(self._module_root(module))
                if distribution:
                    missing.append((module, distribution))
                else:
                    unknown.append(module)
        return missing, unknown

    def _ensure_pip(self):
        code, _ = self._run_hidden_command([self.python_console, "-m", "pip", "--version"])
        if code == 0:
            self._write_log("pip is available in the selected Python installation.")
            return
        self._write_log("pip is unavailable; enabling Python ensurepip.")
        code, output = self._run_hidden_command([self.python_console, "-m", "ensurepip", "--upgrade"])
        if code != 0:
            raise SetupFailure(
                "Python's package installer could not be enabled. Repair the Python installation and ensure pip is included. "
                + " | ".join(output[-8:])
            )

    def _pip_install(self, packages: list[str], force: bool = False):
        if not packages:
            return
        base_args = [
            self.python_console, "-m", "pip", "install",
            "--disable-pip-version-check", "--no-warn-script-location",
            "--progress-bar", "off", "--user", "--retries", "5", "--timeout", "45",
        ]
        if force:
            base_args.extend(["--upgrade", "--force-reinstall"])
        base_args.extend(packages)
        self._write_log("Installing required libraries: " + ", ".join(packages))
        self._set_progress(58, "INSTALLING REQUIRED LIBRARIES", "Downloading and repairing required libraries through Python's package installer.")
        last_output = []
        for attempt in range(1, 3):
            self._write_log(f"Python package installation attempt {attempt}/2.")
            code, output = self._run_hidden_command(base_args)
            if code == 0:
                return
            last_output = output
            if attempt == 1:
                self._write_log("The first pip attempt failed; retrying automatically.")
                time.sleep(1.2)
        raise SetupFailure(
            "One or more Python libraries could not be installed after automatic retry. "
            "Check internet access or the Python package index. "
            + " | ".join(last_output[-12:])
        )

    def _verify_imports(self, imports: list[dict]):
        # Test exact modules and imported symbols in a clean child interpreter.
        # This also catches native DLL errors and renamed/missing API members.
        payload = json.dumps(imports)
        code_text = (
            "import importlib,json,sys\n"
            f"items=json.loads({payload!r})\n"
            "bad=0\n"
            "for item in items:\n"
            " try:\n"
            "  member=item.get('member')\n"
            "  module=__import__(item['module'],fromlist=[member] if member else [])\n"
            "  if member: getattr(module,member)\n"
            "  label=item['module'] + ('.'+member if member else '')\n"
            "  print('IMPORT_OK\\t'+label,flush=True)\n"
            " except BaseException as exc:\n"
            "  bad+=1\n"
            "  label=item['module'] + ('.'+item['member'] if item.get('member') else '')\n"
            "  msg=str(exc).replace('\\\\','/').replace('\\n',' ')[:500]\n"
            "  print('IMPORT_FAIL\\t'+label+'\\t'+type(exc).__name__+'\\t'+msg,flush=True)\n"
            "sys.exit(1 if bad else 0)\n"
        )
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(INSTALL_DIR) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
        process = subprocess.Popen(
            [self.python_console, "-c", code_text],
            cwd=str(INSTALL_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        failures = []
        checked = 0
        total = max(1, len(imports))
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.rstrip("\r\n")
            if line.startswith("IMPORT_OK\t"):
                label = line.split("\t", 1)[1]
                checked += 1
                self._emit("log", line=f"Verified: {label}")
                pct = 60 + int((checked / total) * 35)
                self._set_progress(pct, "VERIFYING PYTHON MODULES", f"Checking import {checked} of {total}.")
            elif line.startswith("IMPORT_FAIL\t"):
                parts = line.split("\t", 3)
                label = parts[1] if len(parts) > 1 else "unknown"
                error_type = parts[2] if len(parts) > 2 else "ImportError"
                message = parts[3] if len(parts) > 3 else "Import failed"
                module = label.split(".", 1)[0]
                failures.append((module, label, error_type, message))
                checked += 1
                self._emit("log", line=f"Not verified: {label} — {error_type}: {message}")
                pct = 60 + int((checked / total) * 35)
                self._set_progress(pct, "VERIFYING PYTHON MODULES", f"Checking import {checked} of {total}.")
            elif line:
                self._emit("log", line=line)
        return_code = process.wait()
        return failures, return_code

    def _setup_background(self):
        try:
            self._write_log("Starting SCiQ / SceneIQ setup and validation.")
            self._set_progress(5, "PREPARING SCENEIQ", "Installing the shared desktop application and both isolated producer engines.")
            self._install_layout()

            version = sys.version_info
            self._write_log(f"Python runtime detected: {version.major}.{version.minor}.{version.micro}")
            if not (version.major == 3 and 10 <= version.minor <= 12):
                raise SetupFailure(
                    f"SceneIQ requires Python 3.10, 3.11 or 3.12 with Tcl/Tk. "
                    f"The selected runtime is {version.major}.{version.minor}. Install a supported Python runtime and retry."
                )

            self._set_progress(18, "CHECKING PYTHON PACKAGE INSTALLER", "Confirming pip is available for automatic dependency repair.")
            self._ensure_pip()

            video_path = INSTALL_DIR / "sceneiqvideoproduction.py"
            image_path = INSTALL_DIR / "sceniqimageproduction.py"
            self._set_progress(28, "SCANNING PRODUCER IMPORTS", "Reading the imports required by both Video Producer and Image Producer.")
            modules = self._extract_imports(video_path) + self._extract_imports(image_path)
            modules = list({(item["module"], item.get("member")): item for item in modules}.values())
            self._write_log(f"Found {len(modules)} unique import/module-symbol checks across both producer scripts.")
            skipped_platform = sorted(getattr(self, "_platform_skipped_imports", set()))
            if skipped_platform:
                self._write_log(
                    "Skipped imports that belong to the other operating system: "
                    + ", ".join(skipped_platform)
                    + ". These are guarded OS-specific code paths, not missing dependencies."
                )
            missing, unknown = self._find_missing(modules)
            if unknown:
                raise SetupFailure(
                    "The following modules are not installed and have no safe package mapping: "
                    + ", ".join(unknown)
                )
            missing_packages = sorted({dist for _module, dist in missing}, key=str.lower)
            self._write_log(f"Missing import paths: {len(missing)}. Missing distributions: {len(missing_packages)}.")
            if missing_packages:
                self._set_progress(40, "INSTALLING MISSING LIBRARIES", f"Installing {len(missing_packages)} required distributions.")
                self._pip_install(missing_packages)

            self._set_progress(60, "VERIFYING PYTHON MODULES", f"Testing {len(modules)} imports used by both engines.")
            failures, code = self._verify_imports(modules)
            if failures:
                repair = sorted({
                    PACKAGE_MAP.get(self._module_root(module))
                    for module, _label, _kind, _message in failures
                    if PACKAGE_MAP.get(self._module_root(module))
                }, key=str.lower)
                if repair:
                    self._write_log("Repairing packages with import errors: " + ", ".join(repair))
                    self._pip_install(repair, force=True)
                    failures, code = self._verify_imports(modules)
            if failures or code != 0:
                detail = "; ".join(f"{label}: {kind}: {msg}" for _m, label, kind, msg in failures[:12])
                raise SetupFailure("One or more SceneIQ dependencies still fail import verification. " + detail)

            for source_path in (video_path, image_path):
                source = source_path.read_text(encoding="utf-8-sig")
                compile(source, str(source_path), "exec")
            self._set_progress(96, "CREATING DESKTOP SHORTCUTS", "Preparing SceneIQ and Update SceneIQ shortcuts.")
            self._create_desktop_shortcuts()
            self._set_progress(100, "SCENEIQ READY", "Both producer engines and the shared desktop passed setup checks.")
            self._write_log("All SceneIQ imports and script syntax checks passed.")
            self._write_log("SceneIQ setup completed successfully.")
            self._emit("complete", message="SCiQ is ready. The shared SceneIQ desktop will now open.")
        except BaseException as exc:
            payload = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
            self._write_log(f"SETUP FAILED: {payload['type']}: {payload['message']}")
            self._write_log(payload["traceback"])
            self._emit("failed", payload=payload)

    def start_setup(self):
        if self.started:
            return
        self.started = True
        self.copy_button.configure(state="normal")
        self.action_button.configure(text="CANCEL SETUP")
        self.thread = threading.Thread(target=self._setup_background, daemon=True)
        self.thread.start()

    def _poll_events(self):
        if not self.root.winfo_exists():
            return
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self._append_log(data.get("line", ""))
                elif kind == "progress":
                    value = data.get("value", 0)
                    self.progress.configure(value=value)
                    self.percent_label.configure(text=f"{value}%")
                    self.status_label.configure(text=data.get("status", "Working…"))
                    if data.get("message"):
                        self.subheading.configure(text=data["message"])
                elif kind == "complete":
                    self._show_complete(data.get("message", "Setup complete."))
                elif kind == "failed":
                    self._show_failure(data.get("payload", {}))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    @staticmethod
    def _redact_for_screen(text: str) -> str:
        text = str(text)
        text = re.sub(r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:\\|\\\\)[^\r\n<>|]+", "[installation detail hidden]", text)
        text = re.sub(r"(?<![A-Za-z0-9])/(?:[^\s<>|]+/)*[^\s<>|]+", "[installation detail hidden]", text)
        return text

    def _append_log(self, line: str):
        line = self._redact_for_screen(line)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        # Keep the setup UI responsive and bounded.
        line_count = int(self.log_box.index("end-1c").split(".")[0])
        if line_count > 160:
            self.log_box.delete("1.0", f"{line_count - 130}.0")
        self.log_box.configure(state="disabled")

    def _show_complete(self, message: str):
        self.completed = True
        self.progress.configure(value=100)
        self.percent_label.configure(text="100%")
        self.status_label.configure(text="SETUP COMPLETE", fg=self.GREEN)
        self.heading.configure(text="SceneIQ is ready")
        self.subheading.configure(text=message + " Opening the main control center shortly.")
        self._append_log("SUCCESS — Environment confirmed. Desktop and Start Menu shortcuts have been verified.")
        details = getattr(self, "shortcut_summary", "SceneIQ shortcuts have been created.")
        self.subheading.configure(text=message + "\n\n" + details + "\n\nOpening the main control center shortly.")
        try:
            messagebox.showinfo(
                "SceneIQ installation complete",
                "SCiQ / SceneIQ has been installed successfully.\n\n"
                "You can now find it on your Desktop as 'SceneIQ' or in Windows Search / Start Menu.\n"
                "The updater is available as 'Update SceneIQ'.\n\n"
                "The main SceneIQ window will open automatically.",
                parent=self.root,
            )
        except Exception:
            pass
        self.action_button.configure(
            text="OPEN SCENEIQ NOW", command=self.open_sceneiq,
            bg="#0B704A", fg="#FFFFFF", state="normal",
        )
        self.root.after(700, self.open_sceneiq)

    def _show_failure(self, payload: dict):
        self.failed = True
        self.status_label.configure(text="SETUP NEEDS ATTENTION", fg=self.RED)
        self.heading.configure(text="Setup could not be completed")
        self.subheading.configure(
            text="SceneIQ has not been opened because one or more checks failed. Review the message below, correct the issue, and retry."
        )
        self.progress.configure(value=100)
        self.percent_label.configure(text="CHECK FAILED")
        self._append_log(f"ERROR — {payload.get('type', 'Setup error')}: {payload.get('message', 'Unknown setup error')}")
        self.action_button.configure(
            text="RETRY SETUP", command=self.retry_setup,
            bg="#173D36", fg=self.GREEN, state="normal",
        )
        self.copy_button.configure(state="normal")
        messagebox.showerror(
            "SceneIQ setup needs attention",
            self._redact_for_screen(payload.get("message") or "Setup could not be completed. Copy the setup report for full diagnostics."),
            parent=self.root,
        )

    def retry_setup(self):
        self.started = False
        self.completed = False
        self.failed = False
        self.progress.configure(value=0)
        self.percent_label.configure(text="0%")
        self.status_label.configure(text="Retrying setup…", fg=self.GREEN)
        self.heading.configure(text="Preparing SceneIQ")
        self.subheading.configure(text="Checking the application, Python libraries and required folders.")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.action_button.configure(text="CANCEL SETUP", command=self.close, bg="#1A2A3D", fg=self.MUTED)
        self.start_setup()

    def open_sceneiq(self):
        if not self.completed:
            return
        try:
            app_path = INSTALL_DIR / "sceneiqvideoproduction.py"
            if not app_path.is_file():
                raise FileNotFoundError("The main SceneIQ script is not installed.")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            subprocess.Popen(
                [sys.executable, "-X", "utf8", str(app_path)],
                cwd=str(INSTALL_DIR),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                close_fds=True,
            )
            self.root.destroy()
        except Exception as exc:
            self.failed = True
            messagebox.showerror(
                "Could not open SceneIQ",
                f"The environment check passed, but the main window could not be opened.\n\n{type(exc).__name__}: {exc}",
                parent=self.root,
            )

    def copy_report(self):
        try:
            report = "\n".join(self._redact_for_screen(line) for line in self.install_log) or "No setup output has been recorded yet."
            self.root.clipboard_clear()
            self.root.clipboard_append(report)
            self.root.update_idletasks()
            self.status_label.configure(text="SETUP REPORT COPIED", fg=self.GREEN)
        except Exception as exc:
            messagebox.showerror("Copy failed", str(exc), parent=self.root)

    def close(self):
        if self.thread and self.thread.is_alive() and not self.completed and not self.failed:
            if not messagebox.askyesno("Cancel setup?", "Setup is still running. Cancel and close this window?", parent=self.root):
                return
        try:
            self.root.destroy()
        except Exception:
            pass


def main():
    if sys.platform != "win32":
        raise SystemExit("SceneIQ setup is designed for Windows.")
    root = tk.Tk()
    SceneIQSetup(root)
    root.mainloop()


if __name__ == "__main__":
    main()
