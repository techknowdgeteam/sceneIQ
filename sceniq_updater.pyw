# -*- coding: utf-8 -*-
"""SCiQ updater: find the newest complete pair of SceneIQ producer scripts and reinstall safely."""
from __future__ import annotations

import ast
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "SCiQ / SceneIQ"


def _sceneiq_dark_titlebar(window, background="#07111F", foreground="#EAF5FF"):
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        window.update_idletasks()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = wintypes.HWND(window.winfo_id())
        try:
            top = user32.GetAncestor(hwnd, 2)
            if top:
                hwnd = top
        except Exception:
            pass
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        setter = dwmapi.DwmSetWindowAttribute
        setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        setter.restype = ctypes.c_long
        enabled = ctypes.c_int(1)
        for attribute in (20, 19):
            try:
                if setter(hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)) == 0:
                    break
            except Exception:
                continue
        def colorref(value):
            value = str(value).lstrip("#")
            r, g, b = (int(value[i:i+2], 16) for i in (0, 2, 4))
            return b << 16 | g << 8 | r
        for attribute, value in ((35, background), (36, foreground), (34, background)):
            try:
                color = wintypes.DWORD(colorref(value))
                setter(hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color))
            except Exception:
                pass
        return True
    except Exception:
        return False
INSTALL_DIR = Path(r"C:\xampp\htdocs\AI automation\scenIQ")
SETUP_SCRIPT = INSTALL_DIR / "sceniq_setup.pyw"
VIDEO_SCRIPT_NAME = "sceneiqvideoproduction.py"
IMAGE_SCRIPT_NAME = "sceniqimageproduction.py"
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env", "site-packages",
    "node_modules", "build", "dist", "_update_backups", "temp", "tmp",
}


def get_downloads_folder() -> Path:
    """Resolve the Windows Downloads known folder, falling back safely."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _kind = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
            candidate = Path(os.path.expandvars(value)).expanduser()
            if candidate.is_dir():
                return candidate
    except Exception:
        pass
    profile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    for candidate in (profile / "Downloads", Path.home() / "Downloads"):
        if candidate.is_dir():
            return candidate
    return profile / "Downloads"


def is_valid_sceneiq_pair(video_path: Path, image_path: Path) -> tuple[bool, str]:
    """Require both complete scripts and their expected top-level components."""
    try:
        if not video_path.is_file() or video_path.name.casefold() != VIDEO_SCRIPT_NAME:
            return False, "The video producer file is missing."
        if not image_path.is_file() or image_path.name.casefold() != IMAGE_SCRIPT_NAME:
            return False, "The image producer file is missing."
        video_source = video_path.read_text(encoding="utf-8-sig")
        image_source = image_path.read_text(encoding="utf-8-sig")
        video_tree = ast.parse(video_source, filename=str(video_path))
        image_tree = ast.parse(image_source, filename=str(image_path))
        video_names = {node.name for node in video_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        image_names = {node.name for node in image_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        required_video = {"SceneIQApp", "video_producer_service_loop", "_sceneiq_worker_entry"}
        required_image = {"sceneiq_image_producer_loop", "main", "_sceneiq_on_stop_hotkey"}
        missing_video = sorted(required_video - video_names)
        missing_image = sorted(required_image - image_names)
        if missing_video or missing_image:
            return False, "Incomplete SceneIQ package. Missing video components: " + ", ".join(missing_video) + "; missing image components: " + ", ".join(missing_image)
        if len(video_source) < 300_000 or len(image_source) < 300_000:
            return False, "One of the SceneIQ producer scripts is unexpectedly small."
        compile(video_source, str(video_path), "exec")
        compile(image_source, str(image_path), "exec")
        return True, "Valid matched SceneIQ producer pair."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _stamp(path: Path) -> tuple[int, int, int]:
    try:
        folder = path.parent.stat()
    except OSError:
        folder = path.stat()
    file_stat = path.stat()
    folder_created = int(getattr(folder, "st_birthtime", folder.st_ctime) * 1_000_000_000)
    file_created = int(getattr(file_stat, "st_birthtime", file_stat.st_ctime) * 1_000_000_000)
    return (max(folder_created, file_created), int(file_stat.st_mtime_ns), int(file_stat.st_size))


def find_latest_download_package(progress=None) -> tuple[Path | None, int]:
    """Find the newest extracted folder containing a valid matched producer pair."""
    downloads = get_downloads_folder()
    if not downloads.is_dir():
        return None, 0
    matches = []
    scanned = 0
    for root, dirs, files in os.walk(downloads, topdown=True):
        dirs[:] = [name for name in dirs if name.casefold() not in SKIP_DIRS and not name.startswith(".")]
        scanned += 1
        if progress and scanned % 25 == 0:
            progress(scanned)
        names = {name.casefold() for name in files}
        if VIDEO_SCRIPT_NAME.casefold() not in names or IMAGE_SCRIPT_NAME.casefold() not in names:
            continue
        folder = Path(root)
        video_path = folder / VIDEO_SCRIPT_NAME
        image_path = folder / IMAGE_SCRIPT_NAME
        try:
            installed_video = (INSTALL_DIR / VIDEO_SCRIPT_NAME).resolve()
            if video_path.resolve() == installed_video:
                continue
        except Exception:
            pass
        valid, _reason = is_valid_sceneiq_pair(video_path, image_path)
        if valid:
            matches.append(video_path)
    if not matches:
        return None, scanned
    matches.sort(key=_stamp, reverse=True)
    return matches[0], scanned


def running_sceneiq_processes() -> list:
    """Find only running Python processes that reference either installed producer."""
    try:
        import psutil
    except Exception:
        return []
    targets = [
        os.path.normcase(str((INSTALL_DIR / VIDEO_SCRIPT_NAME).resolve())),
        os.path.normcase(str((INSTALL_DIR / IMAGE_SCRIPT_NAME).resolve())),
    ]
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.pid in (os.getpid(), os.getppid()):
                continue
            joined = " ".join(str(value) for value in (proc.info.get("cmdline") or []))
            if not joined:
                continue
            normalized = os.path.normcase(joined)
            if any(target in normalized for target in targets) and "sceniq_updater.pyw" not in normalized and "sceniq_setup.pyw" not in normalized:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def stop_running_sceneiq(processes: list) -> tuple[bool, str]:
    try:
        import psutil
    except Exception:
        return False, "Process-control support is unavailable. Close SceneIQ manually, then retry the update."
    all_processes = {}
    for proc in processes:
        try:
            all_processes[proc.pid] = proc
            for child in proc.children(recursive=True):
                all_processes[child.pid] = child
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    items = list(all_processes.values())
    for proc in items:
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _gone, alive = psutil.wait_procs(items, timeout=8)
    for proc in alive:
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _gone2, alive2 = psutil.wait_procs(alive, timeout=5)
    if alive2:
        return False, "SceneIQ is still running. Close it manually and click Update SceneIQ again."
    return True, "Previous SCiQ session closed safely."


class UpdaterWindow:
    BG = "#07111F"
    PANEL = "#0D1B2D"
    BORDER = "#245276"
    TEXT = "#EAF5FF"
    MUTED = "#9BB4C9"
    CYAN = "#29C9F5"
    GREEN = "#31D58A"
    RED = "#FF6C83"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.events: queue.Queue = queue.Queue()
        self.latest: Path | None = None
        self.scanning = False
        self.installing = False
        self.root.title("SCiQ • SceneIQ Update Center")
        self.root.configure(bg=self.BG)
        try:
            icon_candidate = INSTALL_DIR / "SceneIQ.ico"
            if icon_candidate.is_file():
                self.root.iconbitmap(str(icon_candidate))
        except Exception:
            pass
        self.root.geometry("660x470")
        self.root.resizable(False, False)
        self._center()
        self._build()
        self.root.after(180, lambda: _sceneiq_dark_titlebar(self.root, self.BG, self.TEXT))
        self.root.after(100, self._poll)
        self.root.after(250, self.scan)

    def _center(self):
        self.root.update_idletasks()
        w, h = 660, 470
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=24, pady=22)
        head = tk.Frame(outer, bg=self.BG)
        head.pack(fill="x")
        tk.Label(head, text="SCiQ", bg="#073A5B", fg=self.CYAN, font=("Segoe UI", 17, "bold"), width=5, height=2).pack(side="left", padx=(0, 12))
        titlebox = tk.Frame(head, bg=self.BG)
        titlebox.pack(side="left")
        tk.Label(titlebox, text="UPDATE SCiQ / SCENEIQ", bg=self.BG, fg=self.TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(titlebox, text="DESKTOP APPLICATION INSTALLER", bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        panel = tk.Frame(outer, bg=self.PANEL, highlightbackground=self.BORDER, highlightthickness=1)
        panel.pack(fill="both", expand=True, pady=(22, 15))
        self.status = tk.Label(panel, text="SEARCHING DOWNLOADS", bg=self.PANEL, fg=self.CYAN, font=("Segoe UI", 11, "bold"))
        self.status.pack(anchor="w", padx=20, pady=(20, 8))
        self.message = tk.Label(panel, text="Looking for a matched SceneIQ video + image producer pair.", bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 10), wraplength=570, justify="left")
        self.message.pack(anchor="w", padx=20, pady=(0, 14))
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Updater.Horizontal.TProgressbar", troughcolor="#173049", background=self.GREEN, bordercolor="#173049", thickness=12)
        self.progress = ttk.Progressbar(panel, style="Updater.Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=20, pady=(0, 9))
        self.detail = tk.Label(panel, text="", bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9), wraplength=570, justify="left")
        self.detail.pack(anchor="w", padx=20)
        self.folder_label = tk.Label(panel, text="", bg=self.PANEL, fg=self.CYAN, font=("Segoe UI", 10, "bold"), wraplength=570, justify="left")
        self.folder_label.pack(anchor="w", padx=20, pady=(13, 0))
        foot = tk.Frame(outer, bg=self.BG)
        foot.pack(fill="x")
        self.cancel_button = tk.Button(foot, text="CANCEL", command=self.root.destroy, bg="#1A2A3D", fg=self.MUTED, activebackground="#263D55", activeforeground=self.TEXT, relief="flat", padx=18, pady=11, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.cancel_button.pack(side="right")
        self.update_button = tk.Button(foot, text="SEARCHING…", command=self.confirm_update, state="disabled", bg="#0A704A", fg="white", activebackground="#0D8A5D", relief="flat", padx=20, pady=11, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.update_button.pack(side="right", padx=(0, 10))

    def scan(self):
        if self.scanning or self.installing:
            return
        self.scanning = True
        self.status.configure(text="SEARCHING DOWNLOADS", fg=self.CYAN)
        self.message.configure(text="Searching Downloads for the newest extracted folder containing BOTH SceneIQ producer scripts.")
        self.progress.configure(value=5)
        self.update_button.configure(text="SEARCHING…", state="disabled")

        def on_progress(count):
            self.events.put(("progress", count))
        def run():
            try:
                candidate, scanned = find_latest_download_package(on_progress)
                self.events.put(("scan_done", candidate, scanned, None))
            except Exception as exc:
                self.events.put(("scan_done", None, 0, f"{type(exc).__name__}: {exc}"))
        threading.Thread(target=run, daemon=True).start()

    def _scan_finished(self, candidate: Path | None, scanned: int, error: str | None):
        self.scanning = False
        self.progress.configure(value=100)
        if error:
            self.status.configure(text="SEARCH COULD NOT BE COMPLETED", fg=self.RED)
            self.message.configure(text="SCiQ could not search Downloads. Check folder access, then try again.")
            self.detail.configure(text=error)
            self.update_button.configure(text="RESCAN DOWNLOADS", state="normal", command=self.scan)
            return
        if candidate is None:
            self.latest = None
            self.status.configure(text="NO SCENEIQ UPDATE FOUND", fg=self.RED)
            self.message.configure(text="No valid matched pair was found. Extract a complete SceneIQ update folder containing sceneiqvideoproduction.py and sceniqimageproduction.py, then rescan.")
            self.detail.configure(text=f"Folders checked: {scanned}")
            self.folder_label.configure(text="Both producer scripts must be together in the same folder.")
            self.update_button.configure(text="RESCAN DOWNLOADS", state="normal", command=self.scan)
            return
        self.latest = candidate
        image_candidate = candidate.parent / IMAGE_SCRIPT_NAME
        valid, reason = is_valid_sceneiq_pair(candidate, image_candidate)
        if not valid:
            self._scan_finished(None, scanned, reason)
            return
        stat = candidate.stat()
        modified = time.strftime("%d %b %Y • %H:%M", time.localtime(stat.st_mtime))
        self.status.configure(text="LATEST SCENEIQ UPDATE FOUND", fg=self.GREEN)
        self.message.configure(text="A complete matched SceneIQ producer pair is ready. Confirm below to replace both engines and refresh the desktop shortcuts.")
        self.detail.configure(
            text=f"Source folder: {candidate.parent.name}\nVideo script: {candidate.name}\nImage script: {image_candidate.name}\nModified: {modified} • Video size: {stat.st_size / (1024 * 1024):.2f} MB"
        )
        self.folder_label.configure(text="Your panel.json, ready_script.json, project images, generated outputs and other working data will be preserved.")
        self.update_button.configure(text="INSTALL LATEST UPDATE", state="normal", command=self.confirm_update)

    def confirm_update(self):
        if not self.latest or self.installing:
            self.scan()
            return
        image_latest = self.latest.parent / IMAGE_SCRIPT_NAME
        valid, reason = is_valid_sceneiq_pair(self.latest, image_latest)
        if not valid:
            messagebox.showerror("Invalid SceneIQ package", reason, parent=self.root)
            self.scan()
            return

        processes = running_sceneiq_processes()
        if processes:
            yes = messagebox.askyesno(
                "Close SceneIQ before updating?",
                "SCiQ is currently open. Updating will close the shared desktop and its active Video Producer / Image Producer workers. Their saved output and configuration files will be preserved. Continue?",
                parent=self.root,
            )
            if not yes:
                return
            ok, result = stop_running_sceneiq(processes)
            if not ok:
                messagebox.showerror("Could not close SceneIQ", result, parent=self.root)
                return

        yes = messagebox.askyesno(
            "Confirm SceneIQ update",
            "Install BOTH producer scripts from the newest valid SceneIQ folder in Downloads?\n\nThe current video and image scripts will be backed up and replaced. Setup components and shortcuts will be refreshed. panel.json, ready_script.json, project images, generated images/videos and working data will not be deleted or overwritten.",
            parent=self.root,
        )
        if not yes:
            return

        self.installing = True
        self.update_button.configure(text="INSTALLING…", state="disabled")
        self.cancel_button.configure(state="disabled")
        self.status.configure(text="PREPARING SCENEIQ UPDATE", fg=self.GREEN)
        self.message.configure(text="Launching the SCiQ setup verifier. It will check dependencies for both producer engines before opening the shared desktop.")
        self.progress.configure(value=20, mode="indeterminate")
        self.progress.start(12)
        try:
            if not SETUP_SCRIPT.is_file():
                raise FileNotFoundError("The installed SceneIQ setup program is missing. Run Install_SceneIQ.vbs from the complete installer ZIP first.")
            env = os.environ.copy()
            env["SCENEIQ_SOURCE_VIDEO_SCRIPT"] = str(self.latest.resolve())
            env["SCENEIQ_SOURCE_IMAGE_SCRIPT"] = str(image_latest.resolve())
            env["SCENEIQ_UPDATE_MODE"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            subprocess.Popen(
                [sys.executable, "-X", "utf8", str(SETUP_SCRIPT)],
                cwd=str(INSTALL_DIR), env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True,
            )
            self.status.configure(text="SCENEIQ UPDATE SETUP STARTED", fg=self.GREEN)
            self.message.configure(text="The SceneIQ setup window is verifying and installing both producer engines. This update-center window will close.")
            self.root.after(900, self.root.destroy)
        except Exception as exc:
            self.installing = False
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.status.configure(text="UPDATE COULD NOT START", fg=self.RED)
            self.message.configure(text="The SceneIQ setup process could not be opened. Review the detail below and retry.")
            self.detail.configure(text=f"{type(exc).__name__}: {exc}")
            self.update_button.configure(text="RETRY UPDATE", state="normal", command=self.confirm_update)
            self.cancel_button.configure(state="normal")

    def _poll(self):
        try:
            while True:
                item = self.events.get_nowait()
                if item[0] == "progress":
                    count = item[1]
                    self.message.configure(text=f"Searching Downloads… checked {count} folders so far.")
                elif item[0] == "scan_done":
                    _, candidate, scanned, error = item
                    self._scan_finished(candidate, scanned, error)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(120, self._poll)


def main():
    if sys.platform != "win32":
        raise SystemExit("The SceneIQ desktop updater is designed for Windows.")
    root = tk.Tk()
    UpdaterWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
