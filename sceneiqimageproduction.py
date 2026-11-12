"""SceneIQ standalone Google Flow image producer.

This module runs image generation only. Video rendering lives in
sceniqvideoproduction.py and is not imported or started here.
"""

import traceback

import pyautogui
from PIL import Image
import os
import glob
from datetime import datetime
import subprocess
import json
import hashlib
import win32gui
import win32con
import win32process
import win32api
import win32process
import psutil
import time
import re
import difflib
import pyperclip
import keyboard 
import tkinter as tk
import threading
import queue
import traceback
import zipfile
import csv
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import json
import shutil
import warnings
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix protobuf compatibility
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Image producer dependencies are imported by this standalone module.




# Configure Paths
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#os.environ["TESSDATA_PREFIX"] = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata"
#tessdata_path = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata\eng.traineddata"
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCREEN_IMAGE = r"C:\xampp\htdocs\AI automation\scenIQ\input_images\screen.png"
TEXT_TARGET = r"C:\xampp\htdocs\AI automation\scenIQ\text_target.json"
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
SCREEN_TEXT_CONTENT = r"C:\xampp\htdocs\AI automation\scenIQ\screen_content.json"
INPUT_IMAGES = r"C:\xampp\htdocs\AI automation\scenIQ\input_images"
IMAGES_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\project"
PHPSQLURL = "https://fhdrikxsirudr.fwh.is/phpmyadmintemplate.php"
GEMINI_URL = "https://gemini.google.com/app"
GOOGLE_FLOW_URL = "https://flow.google.com/#overview"
GUI_IMAGES = r"C:\xampp\htdocs\AI automation\gui_images"
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
CONTROLLER_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
READY_SCRIPT = r"C:\xampp\htdocs\AI automation\scenIQ\ready_script.json"
GUI_REGION_SAVER = r"C:\xampp\htdocs\AI automation\scenIQ\gui.json"
SUBSCRIBE_STICKERS = r"C:\xampp\htdocs\AI automation\scenIQ\subscribe"

# The image-producer controller is intentionally independent from video workers.
# CONTROLLER_PATH currently points to panel.json and expects:
# {"imageproducercontroller": {"operation": "run|pause|continue|restart|stop"}}
_SCENEIQ_CONTROLLER_LOCK = threading.RLock()


def _sceneiq_normalize_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _sceneiq_walk_json(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _sceneiq_walk_json(value)
    elif isinstance(node, list):
        for value in node:
            yield from _sceneiq_walk_json(value)


def _sceneiq_find_field(node, aliases, default=None):
    wanted = {_sceneiq_normalize_key(alias) for alias in aliases}
    for current in _sceneiq_walk_json(node):
        for key, value in current.items():
            if _sceneiq_normalize_key(key) in wanted and value not in (None, "", [], {}):
                return value
    return default


def _sceneiq_find_named_object(node, wanted_name):
    wanted = _sceneiq_normalize_key(wanted_name)
    for current in _sceneiq_walk_json(node):
        for key, value in current.items():
            if _sceneiq_normalize_key(key) == wanted and isinstance(value, dict):
                return value
    return None


def _sceneiq_safe_path_component(value, fallback="Uncategorized"):
    """Return one safe Windows path component while preserving readable names."""
    raw = str(value or "").strip()
    raw = re.sub(r'[<>:"/\\\\|?*]+', "_", raw)
    raw = raw.strip(" .")
    if raw in {"", ".", ".."}:
        return fallback
    return raw[:150]



def _sceneiq_project_title_variants(project_title):
    """Return safe original and normalized folder-name variants for a title."""
    safe_title = _sceneiq_safe_path_component(project_title, "unnamed_project")
    normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", str(project_title or ""))
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_") or "unnamed_project"
    normalized = _sceneiq_safe_path_component(normalized, "unnamed_project")
    return list(dict.fromkeys((safe_title, normalized)))


def _sceneiq_resolve_project_folder_path(
    images_root,
    project_title,
    project_category=None,
    create_if_missing=False,
):
    """Resolve category/title and historical flat/Uncategorized folder layouts.

    New layout:      <root>/<projectcategory>/<project_title>/
    Original layout: <root>/<project_title>/
    Older fallback:  <root>/Uncategorized/<project_title>/

    If category metadata is missing, the flat legacy folder is preferred. If it
    is absent, a unique matching category/title folder may be reused. Ambiguous
    matches are not selected arbitrarily.
    """
    root = os.path.abspath(os.fspath(images_root)) if images_root else ""
    if not root or not project_title:
        return None

    title_variants = _sceneiq_project_title_variants(project_title)
    category_text = str(project_category or "").strip()
    category_component = _sceneiq_safe_path_component(category_text) if category_text else ""

    def existing_child(parent, variant):
        direct = os.path.join(parent, variant)
        if os.path.isdir(direct):
            return direct
        try:
            wanted = _sceneiq_normalize_key(variant)
            for child_name in os.listdir(parent):
                child_path = os.path.join(parent, child_name)
                if os.path.isdir(child_path) and _sceneiq_normalize_key(child_name) == wanted:
                    return child_path
        except OSError:
            pass
        return None

    candidate_parents = []
    if category_component:
        candidate_parents.append(os.path.join(root, category_component))
    candidate_parents.append(root)
    # Also recognize the prior default-category layout, including records that
    # may now carry a category value different from the one used when saved.
    candidate_parents.append(os.path.join(root, "Uncategorized"))
    candidate_parents = list(dict.fromkeys(candidate_parents))

    for parent in candidate_parents:
        if not os.path.isdir(parent):
            continue
        for variant in title_variants:
            match = existing_child(parent, variant)
            if match:
                return os.path.abspath(match)

    # Some category-less READY_SCRIPT records may already have been saved in a
    # categorized folder. Reuse it only if one unique match can be identified.
    if not category_component and os.path.isdir(root):
        category_matches = []
        excluded = {
            "video_producer_runs", "worker_workspaces", "input_images",
            "gui_images", "subscribe", "__pycache__", "uncategorized",
        }
        try:
            for parent_name in os.listdir(root):
                parent_path = os.path.join(root, parent_name)
                if not os.path.isdir(parent_path) or parent_name.casefold() in excluded:
                    continue
                for variant in title_variants:
                    match = existing_child(parent_path, variant)
                    if match:
                        category_matches.append(match)
                        break
        except OSError:
            pass

        unique_matches = []
        seen_matches = set()
        for match in category_matches:
            key = os.path.abspath(match).casefold()
            if key not in seen_matches:
                seen_matches.add(key)
                unique_matches.append(match)

        if len(unique_matches) == 1:
            return os.path.abspath(unique_matches[0])
        if len(unique_matches) > 1:
            image_bearing = []
            for match in unique_matches:
                try:
                    has_entry = any(
                        os.path.isfile(os.path.join(match, filename))
                        and re.fullmatch(
                            r"entry[_-]?\d+\.(png|jpg|jpeg|gif|bmp|webp|tiff)",
                            filename,
                            re.IGNORECASE,
                        )
                        and os.path.getsize(os.path.join(match, filename)) > 0
                        for filename in os.listdir(match)
                    )
                    if has_entry:
                        image_bearing.append(match)
                except OSError:
                    continue
            if len(image_bearing) == 1:
                return os.path.abspath(image_bearing[0])
            print(
                f"⚠️ [PROJECT-PATH] Category-less project '{project_title}' matches "
                f"multiple categorized folders; refusing to choose arbitrarily: {unique_matches}"
            )

    if create_if_missing:
        # Do not invent an Uncategorized directory for records that have no
        # category. They continue using the original flat project path.
        destination_parent = os.path.join(root, category_component) if category_component else root
        destination = os.path.join(destination_parent, title_variants[0])
        os.makedirs(destination, exist_ok=True)
        return os.path.abspath(destination)
    return None


def _sceneiq_resolve_project_images_folder(project_title, project_category=None):
    """Image-producer resolver: category path when known, legacy path otherwise."""
    return _sceneiq_resolve_project_folder_path(
        IMAGES_PATH,
        project_title,
        project_category=project_category,
        create_if_missing=True,
    )

def _sceneiq_controller_file_path():
    return os.path.abspath(os.fspath(CONTROLLER_PATH or PANEL_PATH))


def _sceneiq_read_image_controller_operation():
    """Read the remote image command. Missing/empty/unknown values mean run."""
    path = _sceneiq_controller_file_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, TypeError):
        return "run"

    controller = _sceneiq_find_named_object(data, "imageproducercontroller")
    raw = None
    if isinstance(controller, dict):
        for key, value in controller.items():
            if _sceneiq_normalize_key(key) == "operation":
                raw = value
                break
    command = _sceneiq_normalize_key(raw)
    if command in {"", "run", "running", "start", "continue", "resume"}:
        return "continue" if command in {"continue", "resume"} else "run"
    if command in {"pause", "paused", "hold"}:
        return "pause"
    if command in {"restart", "reboot", "reload"}:
        return "restart"
    if command in {"stop", "stopped", "halt", "terminate"}:
        return "stop"
    return "run"


def _sceneiq_write_controller_operation(operation):
    """Persist a controller command without changing the rest of panel.json."""
    path = _sceneiq_controller_file_path()
    temporary_path = path + f".controller_{os.getpid()}.tmp"
    with _SCENEIQ_CONTROLLER_LOCK:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            else:
                data = {}
            if not isinstance(data, (dict, list)):
                data = {}
            controller = _sceneiq_find_named_object(data, "imageproducercontroller")
            if controller is None:
                controller = {"operation": str(operation)}
                if isinstance(data, dict):
                    data["imageproducercontroller"] = controller
                else:
                    data.append({"imageproducercontroller": controller})
            else:
                operation_key = next(
                    (key for key in controller if _sceneiq_normalize_key(key) == "operation"),
                    "operation",
                )
                controller[operation_key] = str(operation)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(temporary_path, "w", encoding="utf-8", newline="") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=4)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            os.replace(temporary_path, path)
            return True
        except Exception as exc:
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass
            print(f"⚠️ [IMAGE-CONTROLLER] Could not save controller operation '{operation}': {exc}")
            return False


def _sceneiq_get_automation_settings(panel_data):
    automation = _sceneiq_find_named_object(panel_data, "automation")
    if isinstance(automation, dict):
        return automation
    return {}


def _sceneiq_get_project_metadata(panel_data):
    automation = _sceneiq_get_automation_settings(panel_data)

    def from_automation(names):
        wanted = {_sceneiq_normalize_key(name) for name in names}
        for key, value in automation.items():
            if _sceneiq_normalize_key(key) in wanted and value not in (None, "", [], {}):
                return value
        return None

    title = from_automation(("project_title", "project_name", "projectTitle", "projectName"))
    if title is None:
        title = _sceneiq_find_field(panel_data, ("project_title", "project_name", "projectTitle", "projectName"))
    category = from_automation(("projectcategory", "project_category", "projectCategory"))
    if category is None:
        category = _sceneiq_find_field(panel_data, ("projectcategory", "project_category", "projectCategory"))
    engine = from_automation(("engine", "image_generation_engine", "engine_type"))
    if engine is None:
        engine = _sceneiq_find_field(panel_data, ("image_generation_engine", "imageGenerationEngine", "engine_type", "engineType", "engine"))
    operator = from_automation(("engineoperator", "engine_operator", "operator"))
    if operator is None:
        operator = _sceneiq_find_field(panel_data, ("engineoperator", "engine_operator", "image_engine_operator"))
    script = _sceneiq_find_field(panel_data, ("script", "script_json", "scriptJson"))
    return {
        "project_title": str(title).strip() if title not in (None, "") else "",
        "project_category": str(category).strip() if category not in (None, "") else "",
        "engine": str(engine).strip() if engine is not None else "",
        "engineoperator": str(operator).strip() if operator is not None else "Single operator",
        "script": script,
    }


def _sceneiq_select_image_engine_operation(panel_data):
    """Choose exactly one GUI image engine based on automation.engineoperator."""
    metadata = _sceneiq_get_project_metadata(panel_data)
    engine = _sceneiq_normalize_key(metadata["engine"])
    operator = _sceneiq_normalize_key(metadata["engineoperator"])
    if engine and engine != "googleflow":
        return None, metadata
    is_multiple = (
        "multiple" in operator
        or operator.startswith("multi")
        or operator in {"manyworkers", "manyoperators", "parallelworkers", "paralleloperators"}
    )
    if is_multiple:
        return sceneiq_google_flow_images_generation_engine_mp_opertion, metadata
    return sceneiq_google_flow_images_generation_engine_single_operation, metadata


class AutomationHUD:
    def __init__(self):
        self.root = None
        self.label_status = None
        self.visible = True
        self.current_text = "Initializing..."
        self.status_history = []
        self.current_status_type = "initializing"
        self._modal_queue = queue.Queue()
        self._modal_window = None
        self._modal_generation = 0
        self.thread = threading.Thread(target=self._run_hud, daemon=True)
        self.thread.start()

    def _run_hud(self):
        self.root = tk.Tk()
        self.root.title("Automation HUD")
        
        # Frameless, always on top, transparent background
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.config(bg="black")
        
        # Make window larger to display full text
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = 600, 120  # Increased height for text visibility
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2) - 100
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        
        # Main container with black background
        container = tk.Frame(self.root, bg="black")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Status message with large, bold font centered
        self.label_status = tk.Label(container, text="🚀 Initializing...", 
                                   font=("Segoe UI", 10, "bold"), 
                                   fg="#00FFCC", bg="black",
                                   wraplength=560, justify="center")
        self.label_status.pack(expand=True, fill="both")
        
        # Apply Windows styling hooks for click-through
        try:
            hwnd = win32gui.GetParent(self.root.winfo_id())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                                 ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
        except:
            pass  # Fallback if Windows API fails
        
        self.root.after(100, self._drain_modal_queue)
        self.root.mainloop()

    def notify_modal(self, message, persistent=False, duration_ms=4200):
        """Queue a wide, topmost controller notification without blocking automation."""
        try:
            self._modal_queue.put(("show", str(message), bool(persistent), int(duration_ms)))
        except Exception:
            print(f"[IMAGE-CONTROLLER] {message}")

    def close_modal(self):
        try:
            self._modal_queue.put(("close", "", False, 0))
        except Exception:
            pass

    def _destroy_modal_window(self, expected=None):
        window = self._modal_window
        if window is None or (expected is not None and window is not expected):
            return
        try:
            if window.winfo_exists():
                window.destroy()
        except Exception:
            pass
        self._modal_window = None

    def _drain_modal_queue(self):
        if not self.root:
            return
        try:
            while True:
                action, message, persistent, duration_ms = self._modal_queue.get_nowait()
                if action == "close":
                    self._destroy_modal_window()
                    continue
                self._destroy_modal_window()
                self._modal_generation += 1
                generation = self._modal_generation
                window = tk.Toplevel(self.root)
                self._modal_window = window
                window.overrideredirect(True)
                window.attributes("-topmost", True)
                window.configure(bg="#111827")
                width, height = 900, 92
                screen_width = window.winfo_screenwidth()
                x = max(0, (screen_width - width) // 2)
                window.geometry(f"{width}x{height}+{x}+48")
                outer = tk.Frame(window, bg="#111827", highlightthickness=2, highlightbackground="#22C55E")
                outer.pack(fill="both", expand=True)
                label = tk.Label(
                    outer,
                    text=message,
                    font=("Segoe UI", 15, "bold"),
                    fg="#F9FAFB",
                    bg="#111827",
                    wraplength=850,
                    justify="center",
                    padx=22,
                    pady=18,
                )
                label.pack(fill="both", expand=True)
                if not persistent:
                    window.after(
                        max(1200, duration_ms),
                        lambda w=window, g=generation: self._destroy_modal_window(w)
                        if self._modal_generation == g else None,
                    )
        except queue.Empty:
            pass
        except Exception as modal_exc:
            print(f"⚠️ [HUD] Controller modal could not be displayed: {modal_exc}")
        try:
            self.root.after(100, self._drain_modal_queue)
        except Exception:
            pass

    def print(self, text, status_type="processing"):
        """Update status text"""
        self.current_text = text
        self.current_status_type = status_type
        
        # Store history
        self.status_history.append((time.time(), text))
        if len(self.status_history) > 20:
            self.status_history.pop(0)
        
        # Update UI in thread-safe manner
        if self.root and self.label_status:
            # Color mapping for different status types
            color_map = {
                "searching": "#00CCFF",
                "scanning": "#00FF88",
                "processing": "#00FFCC",
                "success": "#00FF88",
                "warning": "#FFAA00",
                "waiting": "#8888FF",
                "clicking": "#FF66CC",
                "typing": "#66CCFF",
                "navigating": "#FF8844",
                "error": "#FF4466",
                "initializing": "#00FFCC",
                "booting": "#00CCFF",
                "connecting": "#66CCFF",
                "loading": "#00FF88",
                "verifying": "#00FFCC",
                "complete": "#FF66CC"
            }
            color = color_map.get(status_type, "white")
            self.root.after(0, lambda: self.label_status.config(text=text, fg=color))
        
        # Log with timestamp
        timestamp = time.strftime("%H:%M:%S")
        # Extract emoji from text if present
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]+', flags=re.UNICODE)
        emojis = emoji_pattern.findall(text)
        icon = emojis[0] if emojis else "📊"
        clean_text = emoji_pattern.sub('', text).strip()
        print(f"{icon} [HUD @ {timestamp}] {clean_text}")

    def hide(self):
        """Hide the HUD (kept for compatibility but not used)"""
        self.visible = False

    def show(self):
        """Show the HUD (kept for compatibility)"""
        self.visible = True

    def show_summary(self, final_status="✅ Operation Complete"):
        """Display final operation summary with flash effect"""
        if self.root:
            self.print(final_status, "complete")
            # Flash effect for completion
            for _ in range(3):
                if self.root:
                    self.root.attributes("-alpha", 0.7)
                    time.sleep(0.1)
                    self.root.attributes("-alpha", 1.0)
                    time.sleep(0.1)

    def cleanup(self):
        """Clean up resources"""
        if self.root:
            self.root.quit()
            self.root.destroy()
class _NullAutomationHUD:
    """No-op HUD used inside spawned video workers; workers must not create GUI roots."""
    def print(self, *args, **kwargs):
        return None

    def notify_modal(self, *args, **kwargs):
        return None

    def close_modal(self, *args, **kwargs):
        return None

    def show(self, *args, **kwargs):
        return None

    def hide(self, *args, **kwargs):
        return None

    def show_summary(self, *args, **kwargs):
        return None

    def cleanup(self, *args, **kwargs):
        return None


try:
    import multiprocessing as _sceneiq_multiprocessing
    _sceneiq_is_parent_process = (
        _sceneiq_multiprocessing.current_process().name == "MainProcess"
    )
except Exception:
    _sceneiq_is_parent_process = True

# Tkinter HUDs belong only to the parent automation process. Windows spawn-mode
# video workers import this module too, but must remain isolated/headless.
hud = AutomationHUD() if _sceneiq_is_parent_process else _NullAutomationHUD()



# -----------------------------------------------------------------------------
# Google Flow image generation engines (single + multiple operator)
# -----------------------------------------------------------------------------
def sceneiq_google_flow_images_generation_engine_mp_opertion():
    """
    Generates images using Google Flow via GUI automation with pyautogui image recognition.
    Features:
    - Uses GOOGLE_FLOW_URL and GUI_IMAGES path variable
    - Checks panel.json for image_generation_engine == "Google Flow" (case-insensitive)
    - If engine is not Google Flow, function exits immediately
    - Always runs when the selected image engine is Google Flow; no currently_running gate
    - On start sets currently_running to "sceneiq_google_flow_images_generation_engine()"
    - Recognizes only entry_N scene images and the canonical Thumbnail.png;
      deletes unrelated image files from the project image folder
    - Resumes by generating only missing entry_N images, without resetting
      valid later entries when a numbering gap is found
    - Generates Thumbnail.png only after every scene entry image is verified
    - On completion, verifies every scene image plus Thumbnail.png, appends the
      completed project snapshot to READY_SCRIPT, then removes project_name from PANEL_PATH
    - On any error/abort keeps currently_running as "sceneiq_google_flow_images_generation_engine()"
    - Ctrl+Shift+F12 restarts the workflow from its entry point without resuming a scene phase
    - Restart page detection checks whatdoyouwantocreate FIRST, then new_project,
      and navigates to GOOGLE_FLOW_URL only when neither is visible
    - A restart never resumes directly at generation completion or image download
    - Alt+/ is the explicit manual stop shortcut
    - UI waits use bounded polling where appropriate; generation/card readiness continues to be polled
    - A single OS/pyautogui call cannot be safely force-killed while it is blocked
    - Failed stages trigger a full automatic restart with fresh panel.json state
    - Before opening Google Flow, detects the current visible page state in Edge
    - Resumes directly from the prompt workspace or New Project chooser when visible
    - Navigates to GOOGLE_FLOW_URL only when neither known page state is visible
    - Re-detects the page state on every automatic or manual restart
    - On every restart checks whatdoyouwantocreate FIRST, then new_project,
      and opens GOOGLE_FLOW_URL only when neither is visible
    - Restart does not reuse saved scene-phase checkpoints
    - Checks for exit_editinggfimage.png regularly throughout every workflow stage
    - Uses OpenCV to detect full rectangular image cards in Google Flow screenshots
    - Uses YOLO object detections inside each card to confirm genuine scene content
    - Counts the expected cards across overlapping viewport screenshots before downloading
    - Maps the newest visible card to the last submitted prompt, then proceeds newest-first
    - Hovers the centre of each YOLO-confirmed image card to reveal its download controls
    - Re-identifies every card by perceptual image hash before hovering and downloading
    - Keeps the existing verified web-download confirmation modal and file validation
    - Does not use imagerenderingprogress.png to track, count, or decide scene completion
    - Blocks Windows mouse-wheel scrolling only while an individual card download is active
    - Uses multi-scale OpenCV template matching for Flow page/control detection,
      with one screenshot per page-state scan and PyAutoGUI as a compatibility fallback
    - Saves a full desktop diagnostic screenshot plus best-match scores when page
      detection times out; does not mistake a detected Flow shell for an unknown page
    - Gives navigation a separate bounded 75-second page-detection window
    - On every confirmed Google Flow prompt workspace, configures Nano Banana
      before project validation or scene-entry processing
    - Follows the complete startup sequence: click nanobananaconfig.png,
      nanobanana_16ratio9.png, oneimageperprompt.png, then nanobananaconfig.png
      again to close the settings modal
    - Download monitoring snapshots the real Windows/Edge download folders BEFORE
      triggering the download and detects new or updated image files across them
    - Detects Edge custom download directories from profile Preferences and the
      Windows Downloads known-folder registry values
    - Handles temporary download files, waits for stable/valid image data, and
      verifies the saved destination before reporting success
    - Captures pre-existing gallery-card fingerprints before each scene batch
    - Sends up to six prompts consecutively before running the combined visual scan
    - Excludes old gallery cards, detects new rectangular cards with OpenCV, and
      requires YOLO object confirmation before mapping or downloading them
    - Scans overlapping scroll viewports so cards hidden by the prompt composer
      can be brought fully into view and counted
    - Maps newest-first cards to the reverse order of submitted prompts
    - Re-identifies each card by perceptual hash immediately before download
    - Downloads each card from its own centre hover position and verifies the
      saved file before moving to the next card
    """
    import os
    import json
    import time
    import re
    import subprocess
    import traceback
    import threading
    import ctypes
    import itertools
    from ctypes import wintypes

    try:
        import pyautogui
        import pyperclip
        import win32api
        import win32con
        import win32gui
        import win32process
        import psutil
        import keyboard
        import cv2
        import numpy as np
        from ultralytics import YOLO
    except ImportError as e:
        print(
            f"❌ [GF] Missing dependency: {e}. Install the CV/YOLO dependencies with: "
            "python -m pip install --upgrade opencv-python numpy ultralytics"
        )
        return

    pyautogui.PAUSE = 0.0
    STAGE_TIMEOUT_SECONDS = 40.0
    # Page navigation can take longer than a normal UI control wait. The user
    # stopped the previous run at about 32 seconds, before its 40-second wait
    # could finish, so navigation now receives its own longer bounded window.
    PAGE_NAVIGATION_TIMEOUT_SECONDS = 75.0
    PAGE_STATE_MATCH_THRESHOLD = 0.68
    PAGE_STATE_MATCH_SCALES = tuple(round(value, 2) for value in np.arange(0.55, 1.66, 0.05))
    template_match_debug = {}
    restart_event = threading.Event()
    restart_from_url_event = threading.Event()
    stop_event = threading.Event()
    terminate_automation = False

    # YOLO is loaded lazily after prompts have been submitted. The default
    # lightweight COCO model can identify common scene objects (especially people).
    # Set SCENEIQ_GOOGLE_FLOW_YOLO_MODEL to a local .pt model path when preferred.
    flow_yolo_model = None
    FLOW_YOLO_MODEL_DEFAULT = "yolo11n.pt"
    FLOW_YOLO_CONFIDENCE = 0.08
    FLOW_YOLO_MIN_OBJECT_AREA_RATIO = 0.0008
    FLOW_CARD_SCAN_MAX_PAGES = 14
    FLOW_CARD_BASELINE_MAX_PAGES = 30
    FLOW_CARD_SCROLL_NOTCHES = 2
    FLOW_CARD_HASH_TOLERANCE = 12
    FLOW_CARD_BASELINE_HASH_TOLERANCE = 5

    # The shared polling path checks the exit editing control at most once per
    # second. The re-entry guard is essential because clicking that control
    # itself uses _sleep(), which also calls check_for_termination().
    exit_editing_CHECK_INTERVAL = 1.0
    last_exit_editing_check_at = 0.0
    exit_editing_check_active = False
    exit_editing_click_in_progress = False
    download_ui_sequence_active = False

    # While this lock is active, the cursor is pinned below the one
    # imagerenderingprogress match. Only that progress indicator (during
    # rendering) and moregf.png (after rendering) may be searched.
    image_render_lock_active = False
    image_render_lock_position = None

    # A Windows low-level mouse hook blocks physical wheel scrolling while the
    # image-position lock is active. It is installed only for the locked phase.
    scroll_hook_thread = None
    scroll_hook_thread_id = None
    scroll_hook_stop_event = threading.Event()
    scroll_hook_ready_event = threading.Event()
    scroll_hook_callback_ref = None
    scroll_hook_handle = None
    scroll_key_hook_handles = []

    class _WorkflowRestart(BaseException):
        """Unwind the current workflow; optionally force URL-first navigation."""
        def __init__(self, message, force_url=False):
            super().__init__(message)
            self.force_url = bool(force_url)

    class _ManualStop(BaseException):
        """Raised only when the user presses Alt+/ ."""
        pass

    class _NanoBananaStartupFailure(BaseException):
        """Stop safely when this workflow attempt cannot confirm Nano Banana setup."""
        pass

    class _BatchTrackingFailure(BaseException):
        """Stop safely when a batched UI position can no longer be mapped to an entry."""
        pass

    def set_image_scroll_lock(enabled):
        """
        Block mouse-wheel and horizontal-wheel input at the Windows OS level
        while the image cursor anchor is locked. This prevents accidental
        scrolling rather than trying to chase a moving page position.
        """
        nonlocal scroll_hook_thread, scroll_hook_thread_id
        nonlocal scroll_hook_callback_ref, scroll_hook_handle

        if enabled:
            if scroll_hook_thread and scroll_hook_thread.is_alive():
                return True

            scroll_hook_stop_event.clear()
            scroll_hook_ready_event.clear()

            def _hook_worker():
                nonlocal scroll_hook_thread_id, scroll_hook_callback_ref, scroll_hook_handle
                WH_MOUSE_LL = 14
                WM_MOUSEWHEEL = 0x020A
                WM_MOUSEHWHEEL = 0x020E
                WM_QUIT = 0x0012
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                scroll_hook_thread_id = kernel32.GetCurrentThreadId()

                LRESULT = ctypes.c_ssize_t
                HOOKPROC = ctypes.WINFUNCTYPE(
                    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
                )

                def _low_level_mouse_proc(n_code, w_param, l_param):
                    if n_code >= 0 and image_render_lock_active:
                        if int(w_param) in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
                            # Swallow wheel input while the lock is active.
                            return 1
                    return user32.CallNextHookEx(
                        scroll_hook_handle, n_code, w_param, l_param
                    )

                scroll_hook_callback_ref = HOOKPROC(_low_level_mouse_proc)
                module_handle = kernel32.GetModuleHandleW(None)
                scroll_hook_handle = user32.SetWindowsHookExW(
                    WH_MOUSE_LL, scroll_hook_callback_ref, module_handle, 0
                )
                if not scroll_hook_handle:
                    print("⚠️ [SCROLL-LOCK] Windows mouse-wheel hook could not be installed.")
                    scroll_hook_ready_event.set()
                    return

                scroll_hook_ready_event.set()
                message = wintypes.MSG()
                try:
                    while not scroll_hook_stop_event.is_set():
                        result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                        if result <= 0:
                            break
                        user32.TranslateMessage(ctypes.byref(message))
                        user32.DispatchMessageW(ctypes.byref(message))
                finally:
                    try:
                        user32.UnhookWindowsHookEx(scroll_hook_handle)
                    except Exception:
                        pass
                    scroll_hook_handle = None

            scroll_hook_thread = threading.Thread(
                target=_hook_worker,
                name="GoogleFlowScrollLock",
                daemon=True
            )
            scroll_hook_thread.start()
            scroll_hook_ready_event.wait(timeout=2.0)
            # Also block common browser scrolling keys while the cursor is
            # pinned. These hooks are removed as soon as More is clicked.
            try:
                for key_name in ("page up", "page down", "home", "end", "up", "down", "space"):
                    try:
                        scroll_key_hook_handles.append(keyboard.block_key(key_name))
                    except Exception:
                        pass
            except Exception:
                pass

            if scroll_hook_handle:
                print(
                    "🔒 [SCROLL-LOCK] OS-level mouse-wheel scrolling and common "
                    "page-scrolling keys are blocked."
                )
                return True
            print(
                "⚠️ [SCROLL-LOCK] Wheel blocking is unavailable; common scrolling "
                "keys and cursor-position checks remain active."
            )
            return False

        for hook_handle in list(scroll_key_hook_handles):
            try:
                keyboard.unhook(hook_handle)
            except Exception:
                pass
        scroll_key_hook_handles.clear()

        if scroll_hook_thread and scroll_hook_thread.is_alive():
            scroll_hook_stop_event.set()
            try:
                if scroll_hook_thread_id:
                    ctypes.windll.user32.PostThreadMessageW(
                        scroll_hook_thread_id, 0x0012, 0, 0
                    )
            except Exception:
                pass
            scroll_hook_thread.join(timeout=1.0)
        scroll_hook_thread = None
        scroll_hook_thread_id = None
        scroll_hook_callback_ref = None
        scroll_hook_handle = None
        return True

    def restore_locked_cursor():
        """Force the pointer back to its saved anchor and keep wheel lock enabled."""
        if not image_render_lock_active or image_render_lock_position is None:
            return
        target_x, target_y = image_render_lock_position
        try:
            current_x, current_y = pyautogui.position()
            if abs(current_x - target_x) > 3 or abs(current_y - target_y) > 3:
                print(
                    f"🛡️ [GF-LOCK] Cursor drifted to ({current_x}, {current_y}); "
                    f"forcing it back to ({target_x}, {target_y})."
                )
                pyautogui.moveTo(target_x, target_y, duration=0.1)
        except Exception as cursor_error:
            print(f"⚠️ [GF-LOCK] Cursor check failed; restoring anchor: {cursor_error}")
            pyautogui.moveTo(target_x, target_y, duration=0.1)

    def _bounded_timeout(value):
        try:
            return max(0.1, min(float(value), STAGE_TIMEOUT_SECONDS))
        except (TypeError, ValueError):
            return STAGE_TIMEOUT_SECONDS

    def _sleep(seconds):
        """Sleep in short slices so Ctrl+Shift+F12 and Alt+/ are handled promptly."""
        deadline = time.monotonic() + max(0.0, float(seconds))
        while True:
            # Poll continuously so Ctrl+Shift+F12, Alt+/, and the exit editing control
            # are handled during all waits, including generation/download stages.
            check_for_termination()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    def _supervisor_wait(seconds):
        """Interruptible delay used only between complete workflow attempts."""
        deadline = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < deadline:
            if stop_event.is_set() or restart_event.is_set() or restart_from_url_event.is_set():
                return
            time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))

    # ------------------------------------------------------------------
    # Structure-independent JSON discovery helpers
    # ------------------------------------------------------------------
    def _normalise_key(key):
        return re.sub(r"[^a-z0-9]", "", str(key).lower())

    def _walk_json(node, path=()):
        """Yield every JSON node with its path, regardless of wrapper/key names."""
        yield path, node
        if isinstance(node, dict):
            for key, value in node.items():
                yield from _walk_json(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from _walk_json(value, path + (index,))

    def _find_field(node, aliases, require_value=True):
        wanted = {_normalise_key(alias) for alias in aliases}
        for path, current in _walk_json(node):
            if not isinstance(current, dict):
                continue
            for key, value in current.items():
                if _normalise_key(key) in wanted:
                    if not require_value or value not in (None, "", [], {}):
                        return value
        return None

    def _find_project_title(node):
        value = _find_field(node, ("project_title", "projectTitle", "project_name", "projectName"))
        if isinstance(value, dict):
            value = _find_field(value, ("project_title", "title", "name"))
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
        return "workproject1"

    def _find_engine(node):
        value = _find_field(node, (
            "image_generation_engine", "imageGenerationEngine",
            "engine_type", "engineType", "engine"
        ))
        if isinstance(value, dict):
            value = _find_field(value, ("image_generation_engine", "engine_type", "engine", "type"))
        return str(value).strip() if value is not None else ""

    def _find_script_data(node):
        """Find the best script list anywhere, ignoring character-prompt lists."""
        candidates = []
        for path, current in _walk_json(node):
            if not path or not isinstance(path[-1], str):
                continue
            if _normalise_key(path[-1]) != "script":
                continue
            if isinstance(current, list):
                score = 0
                for item in current:
                    if isinstance(item, dict):
                        keys = {_normalise_key(k) for k in item}
                        if keys.intersection({
                            "sceneimagegeneration", "sceneimageprompt",
                            "imagegenerationprompt", "imageprompt",
                            "charactersreference", "scenepovprompt",
                            "shotnumber", "dialogue"
                        }):
                            score += 10
                        if "entries" in keys:
                            score += 2
                candidates.append((score, len(current), current))
            elif isinstance(current, dict):
                nested = _find_field(current, ("script",))
                if isinstance(nested, list):
                    candidates.append((1, len(nested), nested))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return candidates[0][2]
        value = _find_field(node, ("script",))
        return value if isinstance(value, (dict, list)) else {}

    def _remove_project_payload(node):
        """Remove the completed project's title/script while preserving automation settings."""
        if isinstance(node, list):
            for item in node:
                _remove_project_payload(item)
            return
        if not isinstance(node, dict):
            return

        key_map = {_normalise_key(key): key for key in list(node.keys())}
        has_direct_title = any(k in key_map for k in ("projecttitle", "projectname"))
        has_script = any(k in key_map for k in ("script", "scriptjson"))
        automation_key = key_map.get("automation")
        automation = node.get(automation_key) if automation_key else None
        has_automation_title = (
            isinstance(automation, dict)
            and any(_normalise_key(key) in {"projecttitle", "projectname"} for key in automation)
        )

        # The new schema places project_title inside automation while script is
        # commonly a sibling. Remove that script payload together with the title.
        if has_script and (has_direct_title or has_automation_title):
            for normalized in ("script", "scriptjson"):
                original_key = key_map.get(normalized)
                if original_key is not None:
                    node.pop(original_key, None)

        # Remove only project-identifying keys. Keep engine, engineoperator,
        # projectcategory, imageproducercontroller, and status settings intact.
        for key in list(node.keys()):
            if _normalise_key(key) in {"projectname", "projecttitle"}:
                node.pop(key, None)
                continue
            value = node.get(key)
            if isinstance(value, (dict, list)):
                _remove_project_payload(value)


    # ------------------------------------------------------------------
    # Status helpers (self-contained)
    # ------------------------------------------------------------------
    def _load_panel():
        if not os.path.exists(PANEL_PATH):
            return {}
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_panel(data):
        try:
            os.makedirs(os.path.dirname(PANEL_PATH) or '.', exist_ok=True)
            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ [STATUS] Failed to save panel: {e}")
            return False

    def _find_status_container(node):
        """Find the best dictionary for status fields anywhere in the JSON tree.

        Prefer the actual project/configuration dictionary (project title plus
        script). After a completed project payload is removed, fall back to the
        deepest dictionary already carrying status fields. If neither exists,
        use the root dictionary or create a metadata dictionary in a root list.
        The original root structure and wrapper keys are preserved.
        """
        candidates = []

        def visit(current, path=()):
            if isinstance(current, dict):
                normalized = {_normalise_key(k): v for k, v in current.items()}
                has_title = any(k in normalized for k in ("projecttitle", "projectname"))
                has_script = any(k in normalized for k in ("script", "scriptjson"))
                has_status = any(k in normalized for k in ("currentlyrunning", "status", "operationstatus"))
                # Configuration container is the strongest match. Status-only
                # containers remain discoverable after the project is removed.
                score = (100 if has_title and has_script else 0)
                if has_status:
                    score += 40
                if any(k in normalized for k in ("engine", "imagegenerationengine", "enginetype")):
                    score += 5
                candidates.append((score, len(path), path, current))
                for key, child in current.items():
                    if isinstance(child, (dict, list)):
                        visit(child, path + (key,))
            elif isinstance(current, list):
                for index, child in enumerate(current):
                    if isinstance(child, (dict, list)):
                        visit(child, path + (index,))

        visit(node)
        if not candidates:
            return None

        # Prefer the best semantic match; on ties, prefer the deeper container.
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best = candidates[0]
        if best[0] == 0 and isinstance(node, dict):
            return node
        return best[3]

    def _get_status_value(data, key, default=None):
        container = _find_status_container(data)
        if isinstance(container, dict):
            # Match status keys case-insensitively and regardless of punctuation.
            wanted = _normalise_key(key)
            for existing_key, value in container.items():
                if _normalise_key(existing_key) == wanted:
                    return value
        return default

    def _get_currently_running():
        data = _load_panel()
        val = _get_status_value(data, "currently_running")
        if val is None:
            return None
        val = str(val).strip()
        if val.lower() in ("", "none", "null"):
            return None
        return val

    def _set_currently_running(value, status=None, operation_status=None):
        data = _load_panel()
        container = _find_status_container(data)

        if container is None:
            if isinstance(data, list):
                # Keep the root as a list; add a dedicated metadata object only
                # when no existing dictionary can safely hold status fields.
                container = {"_automation_status": True}
                data.append(container)
            elif isinstance(data, dict):
                container = data
            else:
                print("❌ [STATUS] Cannot update status: panel JSON root is not an object/list.")
                return False

        container["currently_running"] = value
        if status is not None:
            safe_status = str(status).strip().lower()
            if safe_status == "aborted":
                safe_status = "pending"
            container["status"] = safe_status
        if operation_status is not None:
            container["operation_status"] = operation_status
        return _save_panel(data)

    def _transfer_completed_project_to_ready_script(images_folder, expected_entries):
        """
        Append a completed project snapshot to READY_SCRIPT without overwriting
        existing projects. Only remove project_name from PANEL_PATH after the
        append has been successfully written and verified.
        """
        import copy

        # Verify the exact scene-image naming convention and the required
        # video-level thumbnail before the project can be marked complete.
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
        found_entries = set()
        if os.path.isdir(images_folder):
            for filename in os.listdir(images_folder):
                match = re.fullmatch(
                    r"entry_(\d+)\.(png|jpg|jpeg|gif|webp|bmp|tiff)",
                    filename,
                    re.IGNORECASE
                )
                if not match:
                    continue
                number = int(match.group(1))
                full_path = os.path.join(images_folder, filename)
                try:
                    if (
                        1 <= number <= expected_entries
                        and os.path.isfile(full_path)
                        and os.path.getsize(full_path) > 0
                        and os.path.splitext(filename)[1].lower() in image_extensions
                    ):
                        found_entries.add(number)
                except OSError:
                    pass

        missing = [
            f"entry_{number}"
            for number in range(1, expected_entries + 1)
            if number not in found_entries
        ]

        thumbnail_path = os.path.join(images_folder, "Thumbnail.png")
        if not os.path.isfile(thumbnail_path) or os.path.getsize(thumbnail_path) <= 0:
            missing.append("Thumbnail.png")

        if missing:
            print("❌ [READY-SCRIPT] Transfer cancelled; missing required image(s): " + ", ".join(missing))
            update_operation_status(
                "Project was not transferred because one or more scene images or Thumbnail.png are missing",
                is_error=True
            )
            return False

        # Re-read the source so status updates made during the workflow are retained.
        try:
            with open(PANEL_PATH, "r", encoding="utf-8") as source_file:
                source_data = json.load(source_file)
            if not isinstance(source_data, (dict, list)):
                print("❌ [READY-SCRIPT] Source panel is not a JSON object/list.")
                return False

            source_title = _find_project_title(source_data)
            project_snapshot = copy.deepcopy(source_data)
            snapshot_status_container = _find_status_container(project_snapshot)
            if snapshot_status_container is None:
                if isinstance(project_snapshot, dict):
                    snapshot_status_container = project_snapshot
                elif isinstance(project_snapshot, list):
                    snapshot_status_container = {"_automation_status": True}
                    project_snapshot.append(snapshot_status_container)
            if isinstance(snapshot_status_container, dict):
                snapshot_status_container["currently_running"] = "sceneiq_google_flow_images_generation_engine_successful"
                snapshot_status_container["status"] = "completed"
                snapshot_status_container["operation_status"] = (
                    f"Completed project '{source_title}' with {expected_entries} verified image(s)"
                )

            ready_dir = os.path.dirname(READY_SCRIPT)
            if ready_dir:
                os.makedirs(ready_dir, exist_ok=True)

            if os.path.exists(READY_SCRIPT) and os.path.getsize(READY_SCRIPT) > 0:
                with open(READY_SCRIPT, "r", encoding="utf-8") as ready_file:
                    ready_data = json.load(ready_file)
            else:
                ready_data = {"projects": []}

            # Supported append formats: a JSON list, {"projects": [...]}, or a
            # legacy single-project object. Preserve existing metadata/projects.
            if isinstance(ready_data, list):
                ready_data.append(project_snapshot)
            elif isinstance(ready_data, dict):
                if isinstance(ready_data.get("projects"), list):
                    ready_data["projects"].append(project_snapshot)
                elif _find_field(ready_data, ("project_title", "projectTitle", "project_name", "projectName")) is not None:
                    existing_project = ready_data
                    ready_data = {"projects": [existing_project, project_snapshot]}
                else:
                    ready_data["projects"] = [project_snapshot]
            else:
                raise ValueError("ready_script.json must contain a JSON object or list")

            with open(READY_SCRIPT, "w", encoding="utf-8") as ready_file:
                json.dump(ready_data, ready_file, indent=4, ensure_ascii=False)
                ready_file.flush()
                os.fsync(ready_file.fileno())

            # Verify the appended project can be read back before touching source.
            with open(READY_SCRIPT, "r", encoding="utf-8") as verify_file:
                verified_data = json.load(verify_file)
            if isinstance(verified_data, list):
                verified = any(
                    isinstance(item, (dict, list))
                    and _find_field(item, ("project_title", "projectTitle", "project_name", "projectName")) is not None
                    and _find_project_title(item) == source_title
                    for item in verified_data
                )
            else:
                verified = any(
                    isinstance(item, (dict, list))
                    and _find_field(item, ("project_title", "projectTitle", "project_name", "projectName")) is not None
                    and _find_project_title(item) == source_title
                    for item in verified_data.get("projects", [])
                )
            if not verified:
                raise IOError("Could not verify the project in ready_script.json")

            # Remove only the completed project payload while preserving the
            # original root type (dictionary OR list) and its wrapper structure.
            if isinstance(source_data, (dict, list)):
                _remove_project_payload(source_data)
                source_status_container = _find_status_container(source_data)
                if source_status_container is None:
                    if isinstance(source_data, dict):
                        source_status_container = source_data
                    else:
                        source_status_container = {"_automation_status": True}
                        source_data.append(source_status_container)
                source_status_container["currently_running"] = "sceneiq_google_flow_images_generation_engine_successful"
                source_status_container["status"] = "completed"
                source_status_container["operation_status"] = f"Project transferred to ready script: {source_title}"
            with open(PANEL_PATH, "w", encoding="utf-8") as source_file:
                json.dump(source_data, source_file, indent=4, ensure_ascii=False)

            print(
                f"✅ [READY-SCRIPT] Appended completed project "
                f"'{source_title}' "
                f"to {READY_SCRIPT}; removed completed project payload from {PANEL_PATH}"
            )
            return True

        except Exception as exc:
            print(f"❌ [READY-SCRIPT] Failed to transfer completed project: {exc}")
            traceback.print_exc()
            update_operation_status(f"Failed to transfer completed project: {exc}", is_error=True)
            return False

    # ------------------------------------------------------------------
    # Engine check (no currently_running gate)
    # ------------------------------------------------------------------
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        try:
            hud.print("Configuration file is missing.", "error")
        except Exception:
            pass
        return

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)

        image_generation_engine = _find_engine(panel_data)

        if image_generation_engine.lower() != 'google flow':
            print(f"ℹ️ [ENGINE] Image generation engine is '{image_generation_engine}', not 'Google Flow' - skipping operation")
            print(f"   To use this function, set 'image_generation_engine' to 'Google Flow' in panel.json")
            try:
                hud.print("Google Flow is not the selected engine — skipping.", "waiting")
            except Exception:
                pass
            return

        print(f"✅ [ENGINE] Image generation engine is 'Google Flow' - proceeding with operation")

    except json.JSONDecodeError as e:
        print(f"❌ Error: panel.json is not valid JSON: {e}")
        try:
            hud.print("Configuration file appears to be corrupted.", "error")
        except Exception:
            pass
        return
    except Exception as e:
        print(f"❌ Error reading panel.json: {e}")
        try:
            hud.print("Could not read the configuration file.", "error")
        except Exception:
            pass
        return

    # Claim the slot
    _set_currently_running(
        "sceneiq_google_flow_images_generation_engine()",
        status="pending",
        operation_status="Running sceneiq_google_flow_images_generation_engine()"
    )
    print("🔒 [GF] Claimed currently_running = 'sceneiq_google_flow_images_generation_engine()'")

    # ------------------------------------------------------------------
    # Rest of original logic
    # ------------------------------------------------------------------
    # Discover project title and script by key/value anywhere in the JSON tree.
    # The wrapper may be project_name, automation, value, or any other key.
    project_title = _find_project_title(panel_data)
    project_category = _find_field(panel_data, ("projectcategory", "project_category", "projectCategory"))
    script_data = _find_script_data(panel_data)

    # Support the new scene-by-scene structure:
    # {
    #   "characters_prompt": [...],
    #   "script": [
    #       {
    #           "shot_number": 1,
    #           "characters_reference": {...},
    #           "scene_Image_generation": "...",
    #           ...
    #       }
    #   ]
    # }
    # Also retain compatibility with the previous nested batches/entries format.
    all_entries = []

    def _is_new_scene_entry(item):
        if not isinstance(item, dict):
            return False
        keys = {_normalise_key(key) for key in item}
        has_reference = bool(keys.intersection({"charactersreference", "characterreference"}))
        has_image_prompt = any(
            key in keys for key in (
                "sceneimagegeneration", "sceneimageprompt",
                "imagegenerationprompt", "imageprompt"
            )
        )
        return has_reference and has_image_prompt

    def _collect_scene_entries(node):
        if isinstance(node, list):
            for item in node:
                if _is_new_scene_entry(item):
                    all_entries.append(item)
                elif isinstance(item, (dict, list)):
                    _collect_scene_entries(item)
        elif isinstance(node, dict):
            # A direct scene object should be collected once.
            if _is_new_scene_entry(node):
                all_entries.append(node)
                return
            # Old format: batches containing an "entries" list.
            entries = _find_field(node, ("entries",))
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and (
                        _is_new_scene_entry(entry) or "scene_pov_prompt" in entry
                    ):
                        all_entries.append(entry)
                # Continue through other branches too, in case the structure mixes formats.
            for key, value in node.items():
                if _normalise_key(key) not in (
                    "charactersprompt", "charactersvisualprompt", "entries"
                ):
                    if isinstance(value, (dict, list)):
                        _collect_scene_entries(value)

    _collect_scene_entries(script_data)

    total_entries = len(all_entries)
    print(f"📊 [CONFIG] Found {total_entries} total entries")

    if total_entries == 0:
        print("⚠️ No entries are currently available; the supervisor will re-read panel.json and retry.")

    operation_status_flag = True
    operation_status_message = ""
    operation_aborted = False

    # Only these two fields are sent to Google Flow for each new-format scene.
    # Timing, dialogue, shot_number, and all other metadata are intentionally excluded.
    SCENE_PROMPT_FIELDS = ("characters_reference", "scene_Image_generation")
    FIELDS_TO_STRIP = {"start", "stop", "duration", "audio_focus"}
    SEND_LOCATION_TOLERANCE = 20

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)

            if is_abort:
                operation_status_message = f"⚠️ STOPPED: {message}"
                operation_status_flag = False
                operation_aborted = True
            elif is_error:
                operation_status_message = f"⚠️ ERROR: {message}"
                operation_status_flag = False
            elif is_success:
                operation_status_message = f"✅ {message}"
                operation_status_flag = True
            else:
                operation_status_message = f"ℹ️ {message}"

            status_container = _find_status_container(current_panel)
            if status_container is None:
                if isinstance(current_panel, dict):
                    status_container = current_panel
                elif isinstance(current_panel, list):
                    status_container = {"_automation_status": True}
                    current_panel.append(status_container)
                else:
                    raise TypeError("panel.json root must be a JSON object or list")

            status_container['operation_status'] = operation_status_message
            if is_error or is_abort:
                status_container['currently_running'] = "sceneiq_google_flow_images_generation_engine()"
                status_container['status'] = "error"
            elif is_success:
                status_container['currently_running'] = "sceneiq_google_flow_images_generation_engine()"
                status_container['status'] = "pending"

            if not _save_panel(current_panel):
                raise IOError("Could not persist operation status to panel.json")

            if is_abort:
                print(f"🛑 [STATUS] Operation recorded as an error: {message}")
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        print(f"🔁 [RECOVERY] Restarting the complete Google Flow function: {reason}")
        update_operation_status(f"Restart requested: {reason}", is_error=True)
        raise _WorkflowRestart(str(reason))

    def check_operation_status():
        return bool(operation_status_flag and not operation_aborted)

    remote_controller_last_operation = "run"
    remote_controller_last_poll_at = 0.0

    def _poll_remote_controller(force=False):
        nonlocal remote_controller_last_operation, remote_controller_last_poll_at
        now = time.monotonic()
        if not force and now - remote_controller_last_poll_at < 1.0:
            return remote_controller_last_operation
        remote_controller_last_poll_at = now
        command = _sceneiq_read_image_controller_operation()
        previous = remote_controller_last_operation
        if command != previous:
            remote_controller_last_operation = command
            messages = {
                "pause": ("Image production has been paused by the remote controller.", True),
                "continue": ("Image production has resumed by the remote controller.", False),
                "restart": ("Image production has been restarted by the remote controller. Restarting the workflow...", False),
                "stop": ("Image production has been stopped by the remote controller. The controller remains active.", False),
            }
            notice = messages.get(command)
            if notice:
                try:
                    hud.notify_modal(notice[0], persistent=notice[1])
                except Exception:
                    print(f"[IMAGE-CONTROLLER] {notice[0]}")
                print(f"📡 [IMAGE-CONTROLLER] operation changed: {previous} -> {command}")
            elif command == "run" and previous == "pause":
                try:
                    hud.notify_modal("Image production has resumed. Continuing the current workflow...", persistent=False)
                except Exception:
                    pass
            if command == "restart":
                # Restart is an edge-triggered command, not a permanent state.
                # Consume it after capturing the command so the internal workflow
                # supervisor performs one restart instead of restarting forever.
                _sceneiq_write_controller_operation("run")
                remote_controller_last_operation = "run"
                return "restart"
        return remote_controller_last_operation

    def on_restart_shortcut():
        restart_from_url_event.set()
        try:
            hud.notify_modal("Image production is restarting from Google Flow. Reopening the workflow...", persistent=False)
        except Exception:
            pass
        print("🔁 [HOTKEY] Ctrl+Shift+F12 pressed — restarting from GOOGLE_FLOW_URL without checking the current page.")

    def on_terminate_shortcut():
        nonlocal terminate_automation
        terminate_automation = True
        stop_event.set()
        _sceneiq_write_controller_operation("stop")
        try:
            hud.notify_modal("Image production has been stopped by the keyboard shortcut. The remote controller is still listening.", persistent=False)
        except Exception:
            pass
        print("🛑 [HOTKEY] Alt+/ pressed — image production stopped; controller remains available.")

    def check_for_termination():
        nonlocal last_exit_editing_check_at, exit_editing_check_active
        nonlocal download_ui_sequence_active, terminate_automation

        remote_operation = _poll_remote_controller()
        if remote_operation == "pause":
            # Stay responsive while paused: the loop keeps polling controller
            # commands and honours both existing manual hotkeys.
            while remote_operation == "pause":
                if stop_event.is_set() or terminate_automation:
                    raise _ManualStop("Image production stopped while remotely paused")
                if restart_from_url_event.is_set():
                    restart_from_url_event.clear()
                    raise _WorkflowRestart("Manual Ctrl+Shift+F12 requested while paused", force_url=True)
                if restart_event.is_set():
                    restart_event.clear()
                    raise _WorkflowRestart("Manual restart requested while paused")
                time.sleep(0.2)
                remote_operation = _poll_remote_controller()
        if remote_operation == "stop":
            stop_event.set()
            terminate_automation = True
            raise _ManualStop("Remote controller requested image production stop")
        if remote_operation == "restart":
            raise _WorkflowRestart("Remote controller requested a full image workflow restart")

        if stop_event.is_set() or terminate_automation:
            raise _ManualStop("Manual stop requested with Alt+/")
        if restart_from_url_event.is_set():
            restart_from_url_event.clear()
            raise _WorkflowRestart(
                "Manual Ctrl+Shift+F12 requested: restart directly from GOOGLE_FLOW_URL",
                force_url=True,
            )
        if restart_event.is_set():
            restart_event.clear()
            raise _WorkflowRestart("Manual restart requested")
        if not check_operation_status():
            raise _WorkflowRestart("Operation status is invalid; restarting the workflow")

        # exit editing may appear unexpectedly if a generated photo opens in
        # the editor. Check for it at every shared polling point, but throttle
        # screen matching so it does not dominate the GUI automation.
        now = time.monotonic()
        if (
            not download_ui_sequence_active
            and not image_render_lock_active
            and not exit_editing_check_active
            and now - last_exit_editing_check_at >= exit_editing_CHECK_INTERVAL
        ):
            last_exit_editing_check_at = now
            exit_editing_check_active = True
            try:
                check_and_click_exit_editing()
            except (_WorkflowRestart, _ManualStop):
                raise
            except Exception as exit_editing_error:
                print(f"⚠️ [DONE-EDITING] Periodic check failed safely: {exit_editing_error}")
            finally:
                exit_editing_check_active = False

    def format_entry_for_paste(entry_data):
        """Serialize only the two approved prompt fields for the new scene schema."""
        try:
            if not isinstance(entry_data, dict):
                print("⚠️ [PREPARE] Scene entry is not a JSON object.")
                return ""

            # Locate the two scene prompt fields independent of capitalization,
            # punctuation, or surrounding JSON structure.
            key_lookup = {_normalise_key(key): key for key in entry_data}
            reference_key = next(
                (key_lookup[name] for name in ("charactersreference", "characterreference")
                 if name in key_lookup), None
            )
            image_key = next(
                (key_lookup[name] for name in (
                    "sceneimagegeneration", "sceneimageprompt",
                    "imagegenerationprompt", "imageprompt"
                ) if name in key_lookup), None
            )
            if reference_key is not None or image_key is not None:
                cleaned = {}
                if reference_key is not None:
                    cleaned["characters_reference"] = entry_data[reference_key]
                if image_key is not None:
                    cleaned["scene_Image_generation"] = entry_data[image_key]

                missing = [
                    key for key in SCENE_PROMPT_FIELDS
                    if key not in cleaned
                ]
                if missing:
                    print(
                        "⚠️ [PREPARE] New-format scene is missing required field(s): "
                        + ", ".join(missing)
                    )
                    return ""

                return json.dumps(cleaned, indent=4, ensure_ascii=False)

            # Legacy fallback: keep the former scene prompt behaviour for old entries,
            # while still stripping timing/audio metadata.
            cleaned = {
                key: value
                for key, value in entry_data.items()
                if key not in FIELDS_TO_STRIP
            }
            return json.dumps(cleaned, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [PREPARE] Error preparing scene data: {e}")
            return ""

    # --- DYNAMIC FALLBACK HELPERS ---
    def get_image_variants(base_name):
        variants = []
        base_name_without_ext = os.path.splitext(base_name)[0]
        ext = os.path.splitext(base_name)[1]
        original_path = os.path.join(GUI_IMAGES, base_name)
        if os.path.exists(original_path):
            variants.append(original_path)
        pattern = re.compile(rf'^{re.escape(base_name_without_ext)}(\d+)\.{re.escape(ext[1:])}$', re.IGNORECASE)
        try:
            files = os.listdir(GUI_IMAGES)
            numbered_variants = []
            for filename in files:
                match = pattern.match(filename)
                if match:
                    number = int(match.group(1))
                    full_path = os.path.join(GUI_IMAGES, filename)
                    numbered_variants.append((number, full_path))
            numbered_variants.sort(key=lambda x: x[0])
            for _, full_path in numbered_variants:
                variants.append(full_path)
        except Exception as e:
            print(f"⚠️ [FALLBACK] Error scanning for variants of {base_name}: {e}")
        return variants

    def _capture_screen_bgr(region=None):
        """Capture one screenshot and convert it to OpenCV BGR format."""
        screenshot = pyautogui.screenshot(region=region)
        pixels = np.asarray(screenshot)
        if pixels.ndim == 2:
            return cv2.cvtColor(pixels, cv2.COLOR_GRAY2BGR)
        if pixels.shape[2] == 4:
            return cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)
        return cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)

    def _opencv_multiscale_template_match(screen_bgr, template_path, scales=None):
        """Return (score, left, top, width, height, scale) for the best scale."""
        template = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        if template is None or template.size == 0:
            return None

        alpha_mask = None
        if template.ndim == 2:
            template_gray = template
        else:
            if template.shape[2] == 4:
                alpha_mask = (template[:, :, 3] > 8).astype(np.uint8) * 255
                template = template[:, :, :3]
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_BGR2GRAY)
        # Local contrast normalization helps when Windows/browser scaling and
        # display colour management make a template slightly lighter/darker.
        screen_gray = cv2.equalizeHist(screen_gray)
        template_gray = cv2.equalizeHist(template_gray)
        screen_h, screen_w = screen_gray.shape[:2]
        template_h, template_w = template_gray.shape[:2]
        if template_w < 8 or template_h < 8:
            return None

        best = None
        scale_values = scales if scales is not None else PAGE_STATE_MATCH_SCALES
        for scale in scale_values:
            width = max(8, int(round(template_w * float(scale))))
            height = max(8, int(round(template_h * float(scale))))
            if width > screen_w or height > screen_h:
                continue
            if width == template_w and height == template_h:
                resized_gray = template_gray
                resized_mask = alpha_mask
            else:
                interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
                resized_gray = cv2.resize(
                    template_gray, (width, height), interpolation=interpolation
                )
                resized_mask = (
                    cv2.resize(alpha_mask, (width, height), interpolation=cv2.INTER_NEAREST)
                    if alpha_mask is not None else None
                )

            try:
                if resized_mask is not None and cv2.countNonZero(resized_mask) > 0:
                    result = cv2.matchTemplate(
                        screen_gray, resized_gray, cv2.TM_CCORR_NORMED,
                        mask=resized_mask
                    )
                else:
                    result = cv2.matchTemplate(
                        screen_gray, resized_gray, cv2.TM_CCOEFF_NORMED
                    )
                _min_value, max_value, _min_location, max_location = cv2.minMaxLoc(result)
                score = float(max_value)
                if not np.isfinite(score):
                    continue
                if best is None or score > best[0]:
                    best = (score, int(max_location[0]), int(max_location[1]),
                            int(width), int(height), float(scale))
            except cv2.error:
                # Some OpenCV builds reject masks for a particular matching
                # method. Retry that scale without the alpha mask.
                try:
                    result = cv2.matchTemplate(
                        screen_gray, resized_gray, cv2.TM_CCOEFF_NORMED
                    )
                    _min_value, max_value, _min_location, max_location = cv2.minMaxLoc(result)
                    score = float(max_value)
                    if np.isfinite(score) and (best is None or score > best[0]):
                        best = (score, int(max_location[0]), int(max_location[1]),
                                int(width), int(height), float(scale))
                except cv2.error:
                    continue
        return best

    def find_image_with_fallback(
        image_name, confidence=0.8, region=None, screen_bgr=None
    ):
        """Find a GUI template using scale-tolerant OpenCV, then legacy PyAutoGUI.

        OpenCV scans a single captured frame at multiple scales. This fixes the
        previous page-detection weakness where locateCenterOnScreen compared a
        fixed-size template and silently missed controls after browser zoom,
        Windows DPI scaling, or a different capture resolution.
        """
        variants = get_image_variants(image_name)
        if not variants:
            template_match_debug[image_name] = {
                "score": None, "reason": "no template files found", "variants": 0
            }
            print(f"❌ [FALLBACK] No variants found for {image_name} in: {GUI_IMAGES}")
            return None, None

        screenshot_origin = (0, 0)
        search_frame = screen_bgr
        try:
            if search_frame is None:
                search_frame = _capture_screen_bgr(region=region)
                if region is not None:
                    screenshot_origin = (int(region[0]), int(region[1]))
            elif region is not None:
                left, top, width, height = [int(value) for value in region]
                search_frame = search_frame[top:top + height, left:left + width]
                screenshot_origin = (left, top)
        except Exception as screenshot_error:
            print(f"⚠️ [CV-MATCH] Screenshot capture failed for {image_name}: {screenshot_error}")
            search_frame = None

        best_match = None
        best_variant = None
        variant_scores = []
        if search_frame is not None:
            for variant_path in variants:
                try:
                    match = _opencv_multiscale_template_match(
                        search_frame, variant_path
                    )
                    score = float(match[0]) if match else None
                    variant_scores.append((score, os.path.basename(variant_path)))
                    if match and (best_match is None or match[0] > best_match[0]):
                        best_match = match
                        best_variant = variant_path
                except Exception as match_error:
                    print(
                        f"⚠️ [CV-MATCH] Could not compare {os.path.basename(variant_path)}: "
                        f"{match_error}"
                    )

        best_score = float(best_match[0]) if best_match else None
        template_match_debug[image_name] = {
            "score": best_score,
            "variant": os.path.basename(best_variant) if best_variant else None,
            "variant_scores": variant_scores,
        }

        if best_match and best_score >= float(confidence):
            _score, left, top, width, height, scale = best_match
            center_x = int(round(left + width / 2 + screenshot_origin[0]))
            center_y = int(round(top + height / 2 + screenshot_origin[1]))
            location = type("ImageMatchPoint", (), {})()
            location.x = center_x
            location.y = center_y
            print(
                f"✅ [CV-MATCH] Found {os.path.basename(best_variant)} for {image_name} "
                f"at ({center_x}, {center_y}); score={best_score:.3f}, scale={scale:.2f}"
            )
            return location, best_variant

        # Retain the former matcher as a compatibility fallback. It can still
        # win when an image is an exact pixel-size match but the CV score is low.
        for variant_path in variants:
            try:
                location = pyautogui.locateCenterOnScreen(
                    variant_path, confidence=confidence, grayscale=False, region=region
                )
                if location:
                    template_match_debug[image_name] = {
                        "score": best_score,
                        "variant": os.path.basename(variant_path),
                        "fallback": "pyautogui exact-size match",
                        "variant_scores": variant_scores,
                    }
                    print(
                        f"✅ [FALLBACK] Found {os.path.basename(variant_path)} at "
                        f"({location.x}, {location.y}) using PyAutoGUI fallback"
                    )
                    return location, variant_path
            except Exception:
                continue

        best_label = (
            f"{best_score:.3f}" if best_score is not None else "unavailable"
        )
        print(
            f"ℹ️ [CV-MATCH] {image_name} not matched at threshold {confidence:.2f}; "
            f"best score={best_label}; checked {len(variants)} template variant(s)."
        )
        return None, None

    def find_all_image_centers_with_fallback(image_name, confidence=0.7, region=None):
        """Find every visible instance of a template, merging duplicate variants."""
        variants = get_image_variants(image_name)
        if not variants:
            return []

        matches = []
        for variant_path in variants:
            try:
                for box in pyautogui.locateAllOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False,
                    region=region
                ):
                    center = (int(box.left + box.width / 2), int(box.top + box.height / 2))
                    duplicate = False
                    for existing in matches:
                        if abs(existing[0] - center[0]) <= 18 and abs(existing[1] - center[1]) <= 18:
                            duplicate = True
                            break
                    if not duplicate:
                        matches.append(center)
            except Exception:
                continue

        matches.sort(key=lambda point: (point[1], point[0]))
        return matches

    def wait_for_image_with_fallback(image_name, timeout_seconds=40, confidence=0.8, region=None):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        variants = get_image_variants(image_name)
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        print(f"🔍 [FALLBACK] Waiting for {image_name} with {len(variants)} variant(s)...")
        start_time = time.time()
        last_status_time = 0
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            for variant_path in variants:
                variant_name = os.path.basename(variant_path)
                try:
                    location = pyautogui.locateCenterOnScreen(variant_path, confidence=confidence, grayscale=False, region=region)
                    if location:
                        print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                        return location, variant_path
                except Exception:
                    pass
            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(f"⏳ [FALLBACK] Still waiting for {image_name}... ({elapsed}s elapsed)")
                last_status_time = current_time
            _sleep(0.3)
        print(f"❌ [FALLBACK] {image_name} not found in any variant within {timeout_seconds} seconds")
        return None, None

    def wait_for_image_indefinitely(image_name, confidence=0.8, region=None):
        """Legacy name; this is deliberately bounded and triggers recovery."""
        location, _ = wait_for_image_with_fallback(
            image_name,
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=confidence,
            region=region
        )
        if not location:
            raise _WorkflowRestart(f"{image_name} was not found within 40 seconds")
        return location

    def find_image_at_location(image_name, target_x, target_y, tolerance=20, confidence=0.7):
        variants = get_image_variants(image_name)
        if not variants:
            return None
        for variant_path in variants:
            try:
                location = pyautogui.locateCenterOnScreen(variant_path, confidence=confidence, grayscale=False)
                if location:
                    dx = abs(location.x - target_x)
                    dy = abs(location.y - target_y)
                    if dx <= tolerance and dy <= tolerance:
                        print(f"✅ [LOC-LOCK] {os.path.basename(variant_path)} matched at "
                              f"({location.x}, {location.y}) — within tolerance of "
                              f"({target_x}, {target_y}) [dx={dx}, dy={dy}]")
                        return location
                    else:
                        print(f"⚠️ [LOC-LOCK] {os.path.basename(variant_path)} matched at "
                              f"({location.x}, {location.y}) BUT outside tolerance of "
                              f"({target_x}, {target_y}) [dx={dx}, dy={dy}] — rejecting this match")
            except Exception:
                pass
        return None

    # --- WINDOW MANAGEMENT HELPERS ---
    def get_current_monitor():
        try:
            cursor_pos = win32api.GetCursorPos()
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint(cursor_pos))
            return monitor_info['Monitor']
        except Exception:
            return (0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                    win32api.GetSystemMetrics(win32con.SM_CYSCREEN))

    def get_edge_window_on_monitor(monitor_bounds):
        monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_bounds
        edge_windows = []
        edge_process_names = ["msedge.exe"]

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    if process.name().lower() in edge_process_names:
                        rect = win32gui.GetWindowRect(hwnd)
                        left, top, right, bottom = rect
                        width, height = right - left, bottom - top
                        if width > 200 and height > 200:
                            window_center_x = (left + right) / 2
                            window_center_y = (top + bottom) / 2
                            is_on_current_monitor = (
                                monitor_left <= window_center_x <= monitor_right and
                                monitor_top <= window_center_y <= monitor_bottom
                            )
                            if is_on_current_monitor:
                                windows.append({'hwnd': hwnd, 'width': width, 'height': height})
                except Exception:
                    pass
            return True

        win32gui.EnumWindows(enum_windows_callback, edge_windows)
        edge_windows.sort(key=lambda w: w['width'] * w['height'], reverse=True)
        return edge_windows

    def ensure_edge_window_ready():
        check_for_termination()
        current_monitor = get_current_monitor()
        edge_windows = get_edge_window_on_monitor(current_monitor)

        if edge_windows:
            hwnd = edge_windows[0]['hwnd']
            print(f"🪟 [WINDOW] Found existing Edge window handle: {hwnd}")
            try:
                if win32gui.IsIconic(hwnd):
                    print("🔄 [WINDOW] Window was minimized, restoring...")
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    _sleep(0.3)
                print("🔄 [WINDOW] Maximizing window...")
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                _sleep(0.5)
                win32gui.SetForegroundWindow(hwnd)
                _sleep(0.2)
                print("✅ [WINDOW] Window ready - maximized and focused")
                update_operation_status("Browser window ready for Google Flow operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")

        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for Google Flow operation...")
        try:
            hud.print("Opening the browser...", "navigating")
        except Exception:
            pass
        subprocess.Popen([edge_path, "about:blank"])

        for attempt in range(20):
            check_for_termination()
            _sleep(0.5)
            edge_windows = get_edge_window_on_monitor(current_monitor)
            if edge_windows:
                hwnd = edge_windows[0]['hwnd']
                print(f"🪟 [WINDOW] New Edge window launched, handle: {hwnd}")
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        _sleep(0.3)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.5)
                    win32gui.SetForegroundWindow(hwnd)
                    _sleep(0.2)
                    print("✅ [WINDOW] New window ready - maximized and focused")
                    update_operation_status("Browser launched for Google Flow operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue

        error_msg = "Failed to get or launch Edge window for Google Flow operation"
        update_operation_status(error_msg, is_error=True)
        try:
            hud.print("Could not open the browser window.", "error")
        except Exception:
            pass
        abort_operation(error_msg)
        raise RuntimeError(error_msg)

    def enforce_window_focus(hwnd):
        check_for_termination()
        try:
            if not win32gui.IsWindow(hwnd):
                print("⚠️ [FOCUS] Window handle invalid, reacquiring...")
                return False
            if win32gui.IsIconic(hwnd):
                print("🔄 [FOCUS] Window was minimized, restoring...")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                _sleep(0.3)
            current_foreground = win32gui.GetForegroundWindow()
            if current_foreground != hwnd:
                print("🛡️ [FOCUS] Correcting window focus...")
                win32gui.SetForegroundWindow(hwnd)
                _sleep(0.15)
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] != win32con.SW_SHOWMAXIMIZED:
                    print("🔄 [FOCUS] Window not maximized, maximizing...")
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.3)
            except Exception:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.3)
                except Exception:
                    pass
            return True
        except Exception as e:
            print(f"⚠️ [FOCUS] Focus correction exception: {e}")
            return False

    def ensure_window_ready_and_focused():
        check_for_termination()
        hwnd = ensure_edge_window_ready()
        enforce_window_focus(hwnd)
        return hwnd

    def fast_paste_url(hwnd, url):
        check_for_termination()
        try:
            hud.print("Opening Google Flow...", "navigating")
        except Exception:
            pass
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        _sleep(0.1)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status("Navigating to Google Flow URL...")

    def wait_for_image(image_name, timeout_seconds=40, confidence=0.8, region=None):
        location, _ = wait_for_image_with_fallback(image_name, timeout_seconds, confidence, region)
        return location

    def find_image(image_name, confidence=0.8, region=None):
        location, _ = find_image_with_fallback(image_name, confidence, region)
        return location

    def configure_startup_nanobanana_16ratio9(hwnd):
        """Configure Nano Banana and explicitly close its settings modal.

        Required order on every workflow attempt:
          1. Click nanobananaconfig.png to open configuration.
          2. Select nanobanana_16ratio9.png.
          3. Select oneimageperprompt.png.
          4. Find nanobananaconfig.png again and click it to close configuration.
          5. Confirm that the prompt input is reachable after the modal closes.
        """
        check_for_termination()
        enforce_window_focus(hwnd)

        print("\n⚙️ [NANO-BANANA] Starting the complete Nano Banana configuration sequence...")
        update_operation_status(
            "Opening Nano Banana settings, selecting 16:9 and one image per prompt, then closing settings"
        )

        config_location = wait_for_image(
            "nanobananaconfig.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.72,
        )
        if not config_location:
            message = (
                "nanobananaconfig.png was not detected. Check the gui_images asset "
                "and the saved Google Flow diagnostic screenshot."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        if not _click_google_flow_control(hwnd, config_location, "nanobananaconfig.png (open settings)"):
            raise _NanoBananaStartupFailure(
                "Could not open the Nano Banana configuration modal."
            )

        print("🔎 [NANO-BANANA] Looking for nanobanana_16ratio9.png...")
        ratio_location, _ = wait_for_image_with_fallback(
            "nanobanana_16ratio9.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.72,
        )
        if not ratio_location:
            raise _NanoBananaStartupFailure(
                "nanobanana_16ratio9.png was not detected inside Nano Banana settings."
            )
        if not _click_google_flow_control(
            hwnd, ratio_location, "nanobanana_16ratio9.png"
        ):
            raise _NanoBananaStartupFailure(
                "Could not select the Nano Banana 16:9 ratio."
            )

        print("🔎 [NANO-BANANA] Ratio selected. Now looking for oneimageperprompt.png...")
        one_image_location, _ = wait_for_image_with_fallback(
            "oneimageperprompt.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.72,
        )
        if not one_image_location:
            message = (
                "oneimageperprompt.png was not detected after selecting 16:9. "
                "No prompts will be submitted because the image-count setting is unconfirmed."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)
        if not _click_google_flow_control(
            hwnd, one_image_location, "oneimageperprompt.png"
        ):
            raise _NanoBananaStartupFailure(
                "Could not select one image per prompt."
            )

        # The config control is deliberately searched AGAIN after selecting
        # oneimageperprompt. This second click toggles the settings modal closed.
        print(
            "🔎 [NANO-BANANA] One image per prompt selected. "
            "Finding nanobananaconfig.png again to close the settings modal..."
        )
        close_config_location, _ = wait_for_image_with_fallback(
            "nanobananaconfig.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.72,
        )
        if not close_config_location:
            raise _NanoBananaStartupFailure(
                "Could not relocate nanobananaconfig.png to close the settings modal."
            )
        if not _click_google_flow_control(
            hwnd, close_config_location, "nanobananaconfig.png (close settings)"
        ):
            raise _NanoBananaStartupFailure(
                "Could not close the Nano Banana settings modal."
            )

        # Confirm the modal has actually closed. The one-image option should no
        # longer be visible once its containing settings panel is dismissed.
        close_deadline = time.monotonic() + 8.0
        modal_option_still_visible = False
        while time.monotonic() < close_deadline:
            check_for_termination()
            option_location = find_image(
                "oneimageperprompt.png", confidence=0.72
            )
            if not option_location:
                modal_option_still_visible = False
                break
            modal_option_still_visible = True
            _sleep(0.35)

        if modal_option_still_visible:
            print(
                "⚠️ [NANO-BANANA] oneimageperprompt.png remains visible after the "
                "close click; checking the prompt input before deciding whether setup succeeded."
            )

        print("🔎 [NANO-BANANA] Confirming the prompt input is reachable after closing settings...")
        prompt_location = find_whatdoyouwantocreate_with_fallbacks(
            hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS
        )
        if not prompt_location:
            message = (
                "Prompt input did not become available after selecting 16:9, "
                "one image per prompt, and closing Nano Banana settings."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        print(
            "✅ [NANO-BANANA] Startup setup completed: "
            "nanobananaconfig → nanobanana_16ratio9 → oneimageperprompt "
            "→ nanobananaconfig (close)."
        )
        return True

    def move_mouse_to_center_of_screen():
        try:
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            center_x = screen_width // 2
            center_y = screen_height // 2
            pyautogui.moveTo(center_x, center_y, duration=0.15)
            print(f"🖱️ [MOUSE] Moved cursor to screen center ({center_x}, {center_y})")
        except Exception as e:
            print(f"⚠️ [MOUSE] Could not move cursor to center: {e}")

    def move_cursor_below_search(search_location, offset_px=50):
        target_x = int(search_location.x - offset_px)
        target_y = int(search_location.y + offset_px)
        print(
            f"🖱️ [CURSOR] Moving cursor {offset_px}px LEFT and "
            f"{offset_px}px BELOW imagerenderingprogress.png "
            f"to ({target_x}, {target_y})"
        )
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        _sleep(0.3)
        return target_x, target_y

    def click_right_edge_of_image(image_name, confidence=0.7, region=None):
        variants = get_image_variants(image_name)
        for variant_path in variants:
            try:
                location = pyautogui.locateOnScreen(variant_path, confidence=confidence, region=region)
                if location:
                    click_x = location.left + int(location.width * 0.95)
                    click_y = location.top + int(location.height / 2)
                    print(f"🎯 [RIGHT-EDGE] Clicking {os.path.basename(variant_path)} right edge at ({click_x}, {click_y})")
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    pyautogui.click()
                    _sleep(0.5)
                    return True
            except Exception:
                pass
        return False

    def scroll_down_multiple(times=3):
        for i in range(times):
            pyautogui.scroll(500)
            _sleep(0.3)
            print(f"⬇️ [SCROLL] Scrolled down ({i+1}/{times}) at current cursor position")
        _sleep(0.5)

    # --- GOOGLE FLOW PAGE-STATE DETECTION / RECOVERY HELPERS ---
    def _get_edge_window_title(hwnd=None):
        try:
            return win32gui.GetWindowText(hwnd) if hwnd and win32gui.IsWindow(hwnd) else ""
        except Exception:
            return ""

    def _save_google_flow_page_diagnostic(reason, hwnd=None):
        """Save the actual desktop screenshot when Flow controls cannot be identified."""
        try:
            diagnostics_dir = os.path.join(
                os.path.dirname(os.path.abspath(GUI_IMAGES)),
                "google_flow_diagnostics"
            )
            os.makedirs(diagnostics_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(
                diagnostics_dir, f"page_state_{reason}_{stamp}.png"
            )
            pyautogui.screenshot().save(screenshot_path)
            title = _get_edge_window_title(hwnd)
            print(f"🧾 [PAGE-DIAGNOSTIC] Browser title: {title or '(not available)'}")
            print(f"🧾 [PAGE-DIAGNOSTIC] Full desktop screenshot saved: {screenshot_path}")
            print(f"🧾 [PAGE-DIAGNOSTIC] GUI_IMAGES directory: {os.path.abspath(GUI_IMAGES)}")
            for asset_name in (
                "whatdoyouwantocreate.png", "new_project.png",
                "expandgfsidepanel.png", "gfmedia.png",
                "nanobananaconfig.png", "nanobanana_16ratio9.png",
                "oneimageperprompt.png"
            ):
                available = bool(get_image_variants(asset_name))
                print(
                    f"   {'✅' if available else '❌'} [PAGE-DIAGNOSTIC] "
                    f"{asset_name}: {'available' if available else 'MISSING'}"
                )
            return screenshot_path
        except Exception as diagnostic_error:
            print(f"⚠️ [PAGE-DIAGNOSTIC] Could not save diagnostic screenshot: {diagnostic_error}")
            return None

    def _find_page_control(image_name, screen_bgr, threshold=None):
        threshold = (
            PAGE_STATE_MATCH_THRESHOLD if threshold is None else float(threshold)
        )
        location, variant = find_image_with_fallback(
            image_name, confidence=threshold, screen_bgr=screen_bgr
        )
        details = template_match_debug.get(image_name, {})
        score = details.get("score")
        score_text = f"{float(score):.3f}" if score is not None else "n/a"
        if location:
            print(
                f"✅ [PAGE-STATE] {image_name} detected at "
                f"({location.x}, {location.y}); match={score_text}; "
                f"asset={os.path.basename(variant) if variant else image_name}"
            )
        else:
            print(
                f"🔎 [PAGE-STATE] {image_name} not matched; "
                f"best OpenCV score={score_text}, required={threshold:.2f}"
            )
        return location, variant

    def detect_google_flow_stage(hwnd=None):
        """Detect page state using one screenshot and multi-scale template matching.

        Priority remains prompt workspace first, New Project second, followed by
        collapsed-panel and loaded-Flow-shell clues. A loaded shell is not
        mistaken for an unknown page that should be navigated to again.
        """
        check_for_termination()
        if hwnd is not None:
            enforce_window_focus(hwnd)

        try:
            screen_bgr = _capture_screen_bgr()
        except Exception as screenshot_error:
            print(f"⚠️ [PAGE-STATE] Could not capture screen for page detection: {screenshot_error}")
            screen_bgr = None

        prompt_location, _ = _find_page_control(
            "whatdoyouwantocreate.png", screen_bgr, threshold=0.70
        )
        if prompt_location:
            return "prompt", prompt_location

        new_project_location, _ = _find_page_control(
            "new_project.png", screen_bgr, threshold=0.70
        )
        if new_project_location:
            return "new_project", new_project_location

        expand_location, _ = _find_page_control(
            "expandgfsidepanel.png", screen_bgr, threshold=0.70
        )
        if expand_location:
            print("✅ [PAGE-STATE] Existing Flow workspace detected with its prompt panel collapsed.")
            return "collapsed_workspace", expand_location

        # A loaded Flow shell is evidence that navigation reached Flow, even if
        # its project/prompt controls are still loading or have changed layout.
        gfmedia_location, _ = _find_page_control(
            "gfmedia.png", screen_bgr, threshold=0.72
        )
        if gfmedia_location:
            print(
                "ℹ️ [PAGE-STATE] Google Flow shell detected, but its prompt/project "
                "control is not ready yet. Continue waiting; do not reload the URL."
            )
            return "flow_loading", gfmedia_location

        config_location, _ = _find_page_control(
            "nanobananaconfig.png", screen_bgr, threshold=0.72
        )
        if config_location:
            print(
                "ℹ️ [PAGE-STATE] Nano Banana control detected. Treating this as an "
                "existing Flow workspace while waiting for the prompt control."
            )
            return "flow_loading", config_location

        title = _get_edge_window_title(hwnd)
        title_lower = title.lower()
        if "flow" in title_lower or "google labs" in title_lower:
            print(
                f"ℹ️ [PAGE-STATE] Browser title suggests Google Flow is loaded "
                f"('{title}'), but no control template matched. Continue waiting."
            )
            return "flow_loading", None

        print(
            "ℹ️ [PAGE-STATE] No Flow page control matched this screenshot. "
            f"Browser title: {title or '(not available)'}."
        )
        return "unknown", None

    def detect_restart_page_stage(hwnd=None):
        """Restart priority: prompt workspace -> New Project -> existing Flow shell.

        The first two checks preserve the established priority. Only after those
        are checked do we test collapsed/loading states before deciding to navigate.
        """
        check_for_termination()
        if hwnd is not None:
            enforce_window_focus(hwnd)

        try:
            screen_bgr = _capture_screen_bgr()
        except Exception as screenshot_error:
            print(f"⚠️ [RESTART-STATE] Screenshot capture failed: {screenshot_error}")
            screen_bgr = None

        print("🔎 [RESTART-STATE] First checking whatdoyouwantocreate.png...")
        prompt_location, _ = _find_page_control(
            "whatdoyouwantocreate.png", screen_bgr, threshold=0.70
        )
        if prompt_location:
            return "prompt", prompt_location

        print("🔎 [RESTART-STATE] Prompt field not found; now checking new_project.png...")
        new_project_location, _ = _find_page_control(
            "new_project.png", screen_bgr, threshold=0.70
        )
        if new_project_location:
            return "new_project", new_project_location

        expand_location, _ = _find_page_control(
            "expandgfsidepanel.png", screen_bgr, threshold=0.70
        )
        if expand_location:
            return "collapsed_workspace", expand_location

        gfmedia_location, _ = _find_page_control(
            "gfmedia.png", screen_bgr, threshold=0.72
        )
        if gfmedia_location:
            print("ℹ️ [RESTART-STATE] Flow shell detected; waiting for its workspace controls instead of reloading.")
            return "flow_loading", gfmedia_location

        config_location, _ = _find_page_control(
            "nanobananaconfig.png", screen_bgr, threshold=0.72
        )
        if config_location:
            print("ℹ️ [RESTART-STATE] Nano Banana control detected; treating the current tab as a Flow workspace.")
            return "flow_loading", config_location

        title = _get_edge_window_title(hwnd)
        if "flow" in title.lower() or "google labs" in title.lower():
            print(
                f"ℹ️ [RESTART-STATE] Current tab title is '{title}'. "
                "Waiting for Flow controls instead of opening another URL."
            )
            return "flow_loading", None

        _save_google_flow_page_diagnostic("initial_unknown", hwnd)
        print(
            "ℹ️ [RESTART-STATE] Prompt, New Project, collapsed workspace, and Flow "
            "shell controls were not found. GOOGLE_FLOW_URL navigation is required."
        )
        return "unknown", None

    def _click_google_flow_control(hwnd, location, description):
        if location is None:
            return False
        check_for_termination()
        enforce_window_focus(hwnd)
        try:
            pyautogui.moveTo(location.x, location.y, duration=0.1)
            pyautogui.click()
            _sleep(0.8)
            print(f"🖱️ [PAGE-STATE] Clicked {description} at ({location.x}, {location.y})")
            return True
        except Exception as click_error:
            print(f"⚠️ [PAGE-STATE] Could not click {description}: {click_error}")
            return False

    def wait_for_google_flow_stage(hwnd, timeout_seconds=None, check_interval=0.5):
        """Wait for a real prompt/project control after Flow has been opened.

        Unlike the old 40-second fixed-size template loop, this uses the
        multi-scale CV matcher and a separate 75-second navigation window.
        A detected Flow shell keeps the workflow waiting on the current page.
        """
        if timeout_seconds is None:
            timeout_seconds = PAGE_NAVIGATION_TIMEOUT_SECONDS
        timeout_seconds = max(1.0, min(float(timeout_seconds), PAGE_NAVIGATION_TIMEOUT_SECONDS))
        print(
            f"🔍 [PAGE-STATE] Waiting up to {timeout_seconds:.0f}s for a prompt "
            "workspace, New Project, or collapsed Flow workspace..."
        )
        try:
            hud.print("Identifying the current Google Flow page...", "waiting")
        except Exception:
            pass
        update_operation_status("Detecting Google Flow page state using multi-scale OpenCV matching...")

        start_time = time.monotonic()
        last_status_time = start_time
        expanded_panel = False
        flow_shell_reported = False
        last_stage = None

        while time.monotonic() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            stage, location = detect_google_flow_stage(hwnd)
            last_stage = stage

            if stage in ("prompt", "new_project"):
                return stage, location

            if stage == "collapsed_workspace" and not expanded_panel:
                print("🔄 [PAGE-STATE] Collapsed Flow side panel found; expanding it once...")
                if _click_google_flow_control(hwnd, location, "expandgfsidepanel.png"):
                    expanded_panel = True
                    _sleep(0.5)
                    continue
                expanded_panel = True

            if stage == "flow_loading" and not flow_shell_reported:
                flow_shell_reported = True
                print(
                    "ℹ️ [PAGE-STATE] Flow shell is present. Waiting for the actual "
                    "prompt/project control; the page will not be reloaded."
                )

            now = time.monotonic()
            if now - last_status_time >= 10:
                elapsed = int(now - start_time)
                print(
                    f"⏳ [PAGE-STATE] Still waiting for Google Flow controls "
                    f"({elapsed}s/{timeout_seconds:.0f}s); last state={last_stage}."
                )
                try:
                    hud.print(f"Waiting for Flow controls... ({elapsed}s)", "waiting")
                except Exception:
                    pass
                update_operation_status(
                    f"Waiting for Google Flow prompt/project controls ({elapsed}s); last state={last_stage}"
                )
                last_status_time = now

            _sleep(check_interval)

        print(
            f"⏰ [PAGE-STATE] Timed out after {timeout_seconds:.0f}s; "
            f"last detected state={last_stage}."
        )
        _save_google_flow_page_diagnostic("navigation_timeout", hwnd)
        return "timeout", None

    def wait_for_prompt_workspace(hwnd, timeout_seconds=40, check_interval=0.5):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        """Wait specifically for the prompt workspace after opening New Project."""
        print(
            f"🔍 [PAGE-STATE] Waiting up to {timeout_seconds}s for "
            "whatdoyouwantocreate.png after opening the project..."
        )
        update_operation_status("Waiting for the prompt workspace to become ready...")
        start_time = time.monotonic()
        last_status_time = start_time
        expanded_panel = False
        flow_shell_reported = False

        while time.monotonic() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            try:
                screen_bgr = _capture_screen_bgr()
            except Exception:
                screen_bgr = None
            prompt_location, prompt_variant = _find_page_control(
                "whatdoyouwantocreate.png", screen_bgr, threshold=0.70
            )
            if prompt_location:
                variant_name = os.path.basename(prompt_variant) if prompt_variant else "whatdoyouwantocreate.png"
                print(
                    f"✅ [PAGE-STATE] Prompt workspace is ready ({variant_name}) at "
                    f"({prompt_location.x}, {prompt_location.y})"
                )
                try:
                    hud.print("Workspace is ready.", "success")
                except Exception:
                    pass
                update_operation_status("Prompt workspace detected and ready for scene processing")
                return True

            if not expanded_panel:
                expand_location, _ = _find_page_control(
                    "expandgfsidepanel.png", screen_bgr, threshold=0.70
                )
                if expand_location:
                    print("🔄 [PAGE-STATE] Prompt field is not visible; expanding the side panel once...")
                    if _click_google_flow_control(hwnd, expand_location, "expandgfsidepanel.png"):
                        expanded_panel = True
                        _sleep(0.5)
                        continue
                    expanded_panel = True

            if not flow_shell_reported:
                gfmedia_location, _ = _find_page_control(
                    "gfmedia.png", screen_bgr, threshold=0.72
                )
                if gfmedia_location:
                    flow_shell_reported = True
                    print(
                        "ℹ️ [PAGE-STATE] Flow shell is present; continuing to wait "
                        "for the prompt field rather than navigating again."
                    )

            now = time.monotonic()
            if now - last_status_time >= 10:
                elapsed = int(now - start_time)
                print(f"⏳ [PAGE-STATE] Waiting for prompt workspace ({elapsed}s/{timeout_seconds}s)...")
                try:
                    hud.print(f"Waiting for the prompt area... ({elapsed}s)", "waiting")
                except Exception:
                    pass
                last_status_time = now

            _sleep(check_interval)

        print(
            f"⏰ [PAGE-STATE] Prompt workspace did not appear within {timeout_seconds}s."
        )
        _save_google_flow_page_diagnostic("prompt_workspace_timeout", hwnd)
        return False

    def wait_for_new_project_and_click(hwnd, timeout_seconds=40, initial_location=None):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        """Click New Project using a bounded wait; never wait forever for the image."""
        print("🔍 [GF] Looking for new_project.png before clicking...")
        try:
            hud.print("Starting a fresh workspace...", "waiting")
        except Exception:
            pass
        update_operation_status("Looking for the New Project button...")

        location = initial_location
        if location is None:
            location, _ = wait_for_image_with_fallback(
                "new_project.png", timeout_seconds=timeout_seconds, confidence=0.8
            )

        if not location:
            print(f"❌ [GF] new_project.png was not found within {timeout_seconds}s")
            return False

        if not _click_google_flow_control(hwnd, location, "new_project.png"):
            return False

        try:
            hud.print("Starting a fresh workspace...", "success")
        except Exception:
            pass
        update_operation_status("Clicked New Project; waiting for the prompt workspace")
        return True

    def wait_for_gfmedia_and_confirm(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS):
        """Legacy compatibility helper; bounded and page-state aware."""
        stage, _ = wait_for_google_flow_stage(hwnd, timeout_seconds=timeout_seconds)
        if stage == "prompt":
            return True
        if stage == "new_project":
            return wait_for_new_project_and_click(hwnd, initial_location=None) and wait_for_prompt_workspace(hwnd)
        print("⚠️ [GF] Could not confirm a usable Google Flow page state.")
        return False

    def find_whatdoyouwantocreate_with_fallbacks(hwnd, timeout_seconds=40):
        """Find the prompt field first; expand the panel only when it is absent."""
        timeout_seconds = _bounded_timeout(timeout_seconds)
        check_for_termination()
        enforce_window_focus(hwnd)

        try:
            hud.print("Getting the prompt area ready...", "waiting")
        except Exception:
            pass
        update_operation_status("Looking for the Google Flow prompt input field...")

        print("🔎 [GF-PROMPT] First checking whatdoyouwantocreate.png directly...")
        location, _ = find_image_with_fallback(
            "whatdoyouwantocreate.png", confidence=0.70
        )
        if location:
            print(
                f"✅ [GF-PROMPT] Prompt input already visible at "
                f"({location.x}, {location.y}); no panel click is needed."
            )
            return location

        print(
            "ℹ️ [GF-PROMPT] Prompt input is not visible. "
            "Now checking whether the side panel is collapsed."
        )
        expand_location = find_image("expandgfsidepanel.png", confidence=0.70)
        if expand_location:
            if not _click_google_flow_control(
                hwnd, expand_location, "expandgfsidepanel.png"
            ):
                print("⚠️ [GF-PROMPT] Side-panel expand control was found but could not be clicked.")
                return None
            print("✅ [GF-PROMPT] Side panel expanded; searching for the prompt field again.")
            location, _ = wait_for_image_with_fallback(
                "whatdoyouwantocreate.png",
                timeout_seconds=timeout_seconds,
                confidence=0.70,
            )
            if location:
                return location

        print("🔎 [GF-PROMPT] Final direct prompt-field lookup...")
        location, _ = wait_for_image_with_fallback(
            "whatdoyouwantocreate.png",
            timeout_seconds=timeout_seconds,
            confidence=0.70,
        )
        if location:
            print(
                f"✅ [GF-PROMPT] Prompt field found at "
                f"({location.x}, {location.y})."
            )
            return location

        _save_google_flow_page_diagnostic("prompt_input_not_found", hwnd)
        print("❌ [GF-PROMPT] Could not locate the prompt input after direct and collapsed-panel checks.")
        return None

    def check_for_tryagain_and_abort():
        tryagain_location = find_image("tryagain.png", confidence=0.7)
        if tryagain_location:
            print(f"❌ [NETWORK] Found tryagain.png — poor network detected!")
            try:
                hud.print("Your internet connection seems unstable — stopping now.", "error")
            except Exception:
                pass
            update_operation_status(
                "Poor network detected (tryagain.png found) — stopping this attempt",
                is_abort=True
            )
            abort_operation("Poor network detected (tryagain.png found)")
            return True
        return False

    def check_and_click_exit_editing():
        """Exit an accidentally opened image editor whenever its Done control appears."""
        nonlocal exit_editing_click_in_progress

        # Prevent a periodic polling pass from double-clicking while an explicit
        # exit editing click is still completing its short UI transition.
        if exit_editing_click_in_progress:
            return False

        exit_editing_click_in_progress = True
        try:
            clicked = click_right_edge_of_image("exit_editinggfimage.png", confidence=0.7)
            if clicked:
                print(
                    "✅ [DONE-EDITING] Clicked the right edge of exit_editinggfimage.png; "
                    "the image editor should now be closed."
                )
                return True
            return False
        finally:
            exit_editing_click_in_progress = False

    def ensure_image_hover_position(timeout_seconds=STAGE_TIMEOUT_SECONDS, offset_px=50):
        """
        Return to the exact cursor anchor recorded when progress was first
        detected. Never re-search imagerenderingprogress after that point.
        """
        nonlocal image_render_lock_active, image_render_lock_position

        if image_render_lock_position is not None:
            target_x, target_y = image_render_lock_position
            image_render_lock_active = True
            set_image_scroll_lock(True)
            current_x, current_y = pyautogui.position()
            if abs(current_x - target_x) > 3 or abs(current_y - target_y) > 3:
                print(
                    f"🛡️ [HOVER-LOCK] Restoring cursor from ({current_x}, {current_y}) "
                    f"to locked position ({target_x}, {target_y})."
                )
                pyautogui.moveTo(target_x, target_y, duration=0.1)
            # Return the original progress-indicator center, not the shifted cursor anchor.
            return type(
                "LockedImagePosition",
                (),
                {"x": target_x + offset_px, "y": target_y - offset_px}
            )()

        # Compatibility fallback for a workflow where the progress indicator
        # never appeared and the legacy generation path completed instead.
        timeout_seconds = _bounded_timeout(timeout_seconds)
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            check_for_termination()
            search_location = find_image("imagerenderingprogress.png", confidence=0.7)
            if search_location:
                image_render_lock_position = (
                    int(search_location.x - offset_px),
                    int(search_location.y + offset_px)
                )
                image_render_lock_active = True
                set_image_scroll_lock(True)
                pyautogui.moveTo(*image_render_lock_position, duration=0.2)
                return search_location
            _sleep(0.4)

        abort_operation(
            f"Could not establish the image hover position within {timeout_seconds} seconds"
        )
        return None

    def handle_exit_gfsidebar_and_recheck():
        print(f"🔍 [GF] no_active_gf_generation.png not found — looking for exit_gfsidebar.png fallback...")
        exit_sidebar_location = find_image("exit_gfsidebar.png", confidence=0.7)
        if exit_sidebar_location:
            print(f"✅ [GF] Found exit_gfsidebar.png — clicking right edge...")
            variants = get_image_variants("exit_gfsidebar.png")
            clicked = False
            for variant_path in variants:
                try:
                    location = pyautogui.locateOnScreen(variant_path, confidence=0.7)
                    if location:
                        click_x = location.left + int(location.width * 0.95)
                        click_y = location.top + int(location.height / 2)
                        print(f"🎯 [GF] Clicking {os.path.basename(variant_path)} right edge at ({click_x}, {click_y})")
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.8)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                pyautogui.moveTo(exit_sidebar_location.x, exit_sidebar_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.8)
            print(f"🔄 [GF] Re-checking for no_active_gf_generation.png after exit_gfsidebar click...")
            recheck_location = find_image("no_active_gf_generation.png", confidence=0.7)
            if recheck_location:
                print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback!")
                return recheck_location
            else:
                print(f"⚠️ [GF] no_active_gf_generation.png still not found after exit_gfsidebar click")
        else:
            print(f"⚠️ [GF] exit_gfsidebar.png not found either")
        return None

    def paste_prompt_and_click_send_batch(hwnd, entry_json, entry_name):
        """Fast batch-only prompt submission; deliberately performs no render scan."""
        check_for_termination()
        enforce_window_focus(hwnd)

        # The prompt workspace normally stays open between entries. Search it
        # directly first; only use the expand control if the input is not visible.
        prompt_location = find_image("whatdoyouwantocreate.png", confidence=0.8)
        if not prompt_location:
            expand_location = find_image("expandgfsidepanel.png", confidence=0.8)
            if expand_location:
                pyautogui.click(expand_location.x, expand_location.y)
                _sleep(0.25)
            prompt_location = wait_for_image(
                "whatdoyouwantocreate.png", timeout_seconds=5, confidence=0.8
            )

        if not prompt_location:
            print(f"❌ [BATCH-SEND] Prompt area not found for {entry_name}.")
            return None

        pyautogui.moveTo(prompt_location.x, prompt_location.y, duration=0.04)
        pyautogui.click()
        _sleep(0.08)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        pyperclip.copy(entry_json)
        pyautogui.hotkey("ctrl", "v")
        _sleep(0.12)

        # Poll briefly for the enabled send button. Never search for
        # imagerenderingprogress until AFTER the send action has happened.
        send_location = None
        send_deadline = time.monotonic() + 2.0
        while time.monotonic() < send_deadline:
            check_for_termination()
            send_location = find_image("sendgf.png", confidence=0.8)
            if send_location:
                break
            _sleep(0.08)

        if send_location:
            send_x, send_y = int(send_location.x), int(send_location.y)
            pyautogui.moveTo(send_x, send_y, duration=0.04)
            pyautogui.click()
            move_mouse_to_center_of_screen()
            print(
                f"✅ [BATCH-SEND] {entry_name} submitted using sendgf.png "
                f"at ({send_x}, {send_y})."
            )
            _sleep(0.12)
            return (send_x, send_y)

        # Enter is a last-resort send action. After the full batch is submitted,
        # OpenCV card detection plus YOLO object confirmation will verify the images.
        pyautogui.press("enter")
        move_mouse_to_center_of_screen()
        _sleep(0.18)
        print(
            f"⚠️ [BATCH-SEND] sendgf.png was not found for {entry_name}; "
            "pressed Enter and will verify using the post-send render scan."
        )
        return (int(prompt_location.x), int(prompt_location.y))


    def paste_prompt_and_click_send(hwnd, entry_json, entry_name):
        print(f"🔍 [SEND-STEP] Looking for whatdoyouwantocreate.png...")
        location = find_whatdoyouwantocreate_with_fallbacks(hwnd, timeout_seconds=30)
        if not location:
            print(f"❌ [SEND-STEP] Could not find the prompt input area")
            try:
                hud.print("Could not find the prompt area.", "error")
            except Exception:
                pass
            update_operation_status(f"Could not find input field for {entry_name}", is_error=True)
            return None

        pyautogui.moveTo(location.x, location.y, duration=0.1)
        pyautogui.click()
        _sleep(0.3)

        print(f"📝 [SEND-STEP] Pasting scene details...")
        try:
            hud.print(f"Preparing {entry_name}...", "typing")
        except Exception:
            pass
        pyautogui.click()
        _sleep(0.1)
        pyautogui.hotkey('ctrl', 'a')
        _sleep(0.05)
        pyautogui.press('backspace')
        _sleep(0.05)
        pyperclip.copy(entry_json)
        pyautogui.hotkey('ctrl', 'v')
        _sleep(0.3)

        print(f"🔍 [SEND-STEP] Looking for sendgf.png (initial click)...")
        send_location = wait_for_image("sendgf.png", timeout_seconds=10, confidence=0.8)
        if not send_location:
            print(f"⚠️ [SEND-STEP] Send button not found - pressing Enter instead...")
            pyautogui.press('enter')
            _sleep(0.5)
            move_mouse_to_center_of_screen()
            return (None, None)

        send_x, send_y = int(send_location.x), int(send_location.y)
        print(f"🎯 [SEND-STEP] RECORDED sendgf location: ({send_x}, {send_y})")

        print(f"🖱️ [SEND-STEP] Moving arrow away from send region before clicking...")
        move_mouse_to_center_of_screen()
        _sleep(0.15)
        pyautogui.click(send_x, send_y)
        _sleep(0.4)
        print(f"✅ [SEND-STEP] Initial click on sendgf.png sent at ({send_x}, {send_y})")
        print(f"🖱️ [SEND-STEP] Moving arrow away from send region after clicking...")
        move_mouse_to_center_of_screen()
        return (send_x, send_y)

    def confirm_sendgf_and_wait_for_generating(hwnd, entry_name, entry_json=None,
                                               send_x=None, send_y=None,
                                               max_confirm_seconds=40, check_interval=0.4,
                                               baseline_render_count=None,
                                               baseline_prompt_sent_visible=None,
                                               baseline_render_centers=None):
        max_confirm_seconds = _bounded_timeout(max_confirm_seconds)
        """
        CONFIRMATION RULE:
        - First try gfpromptsent.png and its numbered variants.
        - If gfpromptsent is not visible, use imagerenderingprogress.png and its
          numbered variants as an alternative confirmation that the prompt was sent.
        - Do not use sendgf.png or no_active_gf_generation.png as prompt-sent
          confirmation signals.
        - If neither confirmation image appears within the confirmation window,
          return needs_restart so the existing outer send loop can retry.
        """

        print(
            f"🔎 [SEND-CONFIRM] Confirming prompt for {entry_name}: "
            f"checking gfpromptsent first, with imagerenderingprogress as fallback..."
        )

        if send_x is not None and send_y is not None:
            print(
                f"   ℹ️ Initial send location was ({send_x}, {send_y}); "
                f"confirmation will use on-screen status images."
            )

        try:
            hud.print("Confirming the prompt was sent...", "waiting")
        except Exception:
            pass

        update_operation_status(
            f"Confirming prompt submission for {entry_name} "
            f"(gfpromptsent, with image-rendering fallback)..."
        )

        prompt_sent_variants = get_image_variants("gfpromptsent.png")
        rendering_variants = get_image_variants("imagerenderingprogress.png")

        if prompt_sent_variants:
            print(
                f"🔍 [SEND-CONFIRM] Found {len(prompt_sent_variants)} "
                f"gfpromptsent variant(s)."
            )
            for variant_path in prompt_sent_variants:
                print(f"   • {os.path.basename(variant_path)}")
        else:
            print(
                "⚠️ [SEND-CONFIRM] No gfpromptsent variants found in gui_images; "
                "will rely on imagerenderingprogress if it appears."
            )

        if rendering_variants:
            print(
                f"🔍 [SEND-CONFIRM] Found {len(rendering_variants)} "
                f"imagerenderingprogress variant(s) available as fallback."
            )
            for variant_path in rendering_variants:
                print(f"   • {os.path.basename(variant_path)}")
        else:
            print(
                "⚠️ [SEND-CONFIRM] No imagerenderingprogress variants currently "
                "exist in gui_images."
            )

        start_time = time.time()
        last_status_time = start_time
        prompt_sent_was_cleared = not bool(baseline_prompt_sent_visible)

        while time.time() - start_time < max_confirm_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)

            if check_for_tryagain_and_abort():
                return "poor_network"

            check_and_click_exit_editing()

            # Primary confirmation: prompt-sent image.
            prompt_sent_location, matched_prompt_variant = find_image_with_fallback(
                "gfpromptsent.png",
                confidence=0.8
            )

            if not prompt_sent_location:
                prompt_sent_was_cleared = True
            elif prompt_sent_was_cleared:
                matched_name = (
                    os.path.basename(matched_prompt_variant)
                    if matched_prompt_variant
                    else "gfpromptsent variant"
                )
                print(
                    f"✅ [SEND-CONFIRM] Fresh {matched_name} detected at "
                    f"({prompt_sent_location.x}, {prompt_sent_location.y})."
                )
                try:
                    hud.print("Prompt sent.", "success")
                except Exception:
                    pass
                update_operation_status(
                    f"Prompt confirmed for {entry_name} (fresh gfpromptsent detected)"
                )
                return "confirmed"
            else:
                print(
                    "ℹ️ [SEND-CONFIRM] gfpromptsent is still visible from an earlier "
                    "submission; it is not being accepted as confirmation for this entry."
                )

            # For batched submissions, an already-running entry's progress image
            # must not confirm the newly submitted prompt. Require the count to
            # increase over the pre-send snapshot. Legacy single-job callers keep
            # the original any-progress fallback when no baseline was supplied.
            rendering_centers = find_all_image_centers_with_fallback(
                "imagerenderingprogress.png", confidence=0.7
            )
            if baseline_render_count is None:
                new_render_detected = bool(rendering_centers)
            else:
                baseline_positions = tuple(baseline_render_centers or ())
                new_render_detected = bool(rendering_centers) and (
                    len(rendering_centers) > int(baseline_render_count)
                    or (baseline_render_centers is not None and tuple(rendering_centers) != baseline_positions)
                )
            if new_render_detected:
                first_render = rendering_centers[-1]
                print(
                    "✅ [SEND-CONFIRM] A new image-rendering indicator was detected "
                    f"(visible count={len(rendering_centers)}, baseline={baseline_render_count}); "
                    f"latest ordered position=({first_render[0]}, {first_render[1]})."
                )
                try:
                    hud.print("Prompt sent — image rendering has started.", "success")
                except Exception:
                    pass
                update_operation_status(
                    f"Prompt confirmed for {entry_name} using a newly appearing render indicator"
                )
                return "confirmed"

            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(
                    f"⏳ [SEND-CONFIRM] Waiting for gfpromptsent or "
                    f"imagerenderingprogress confirmation... ({elapsed}s elapsed)"
                )
                last_status_time = current_time

            _sleep(check_interval)

        print(
            f"⚠️ [SEND-CONFIRM] Neither gfpromptsent nor "
            f"imagerenderingprogress was detected within "
            f"{max_confirm_seconds}s for {entry_name}."
        )
        print(
            "🔁 [SEND-CONFIRM] Returning needs_restart so the existing send loop "
            "can re-search the prompt input, re-paste, and send again."
        )

        try:
            hud.print(
                "Prompt confirmation not detected — trying the prompt again.",
                "warning"
            )
        except Exception:
            pass

        update_operation_status(
            f"No gfpromptsent or imagerenderingprogress confirmation for "
            f"{entry_name} — re-searching input, re-pasting, and resending"
        )

        return "needs_restart"


    def wait_for_imagerenderingprogress_and_jump_to_search(hwnd, entry_name, max_wait_seconds=40, check_interval=0.4):
        """
        Find imagerenderingprogress once, then lock the cursor 50px left and
        50px below that exact match until rendering finishes.

        Once the progress image is first found, no other GUI image/template is
        searched until it disappears. Rendering has NO timeout. After it
        disappears, the cursor remains locked while the caller searches only
        for moregf.png.
        """
        nonlocal image_render_lock_active, image_render_lock_position

        max_wait_seconds = _bounded_timeout(max_wait_seconds)
        print("🔍 [GF-LOCK] Waiting for the FIRST imagerenderingprogress.png match...")
        first_seen_at = time.monotonic()
        rendering_location = None

        # Before the progress indicator is found, retain the normal bounded
        # discovery window. The strict lock begins immediately on first match.
        while time.monotonic() - first_seen_at < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False
            rendering_location = find_image("imagerenderingprogress.png", confidence=0.7)
            if rendering_location:
                break
            _sleep(check_interval)

        if not rendering_location:
            print(
                f"ℹ️ [GF-LOCK] imagerenderingprogress.png did not appear within "
                f"{max_wait_seconds}s; normal generation fallback may be used."
            )
            return False

        # Record the original match and the exact cursor target. Do not search
        # for the progress image a second time merely to position the cursor.
        image_render_lock_position = (
            int(rendering_location.x - 50),
            int(rendering_location.y + 50)
        )
        image_render_lock_active = True
        set_image_scroll_lock(True)
        target_x, target_y = image_render_lock_position
        print(
            "🔒 [GF-LOCK] First match recorded at "
            f"({rendering_location.x}, {rendering_location.y}); "
            f"cursor target permanently locked at ({target_x}, {target_y})."
        )
        pyautogui.moveTo(target_x, target_y, duration=0.2)

        try:
            hud.print("Image generation in progress...", "processing")
        except Exception:
            pass
        update_operation_status(f"Rendering in progress for {entry_name}; cursor position locked")

        render_started = time.monotonic()
        last_status_time = render_started

        # IMPORTANT: no 40-second deadline here. Keep waiting for as long as
        # Google Flow needs. During this phase, only search the progress image.
        while True:
            check_for_termination()

            # The download-confirmation modal is the only additional UI
            # exception allowed during the rendering lock. Its existing
            # two-image verification remains mandatory.
            _service_modal_and_restore_locked_cursor()
            restore_locked_cursor()

            # Search the rendering indicator only after modal servicing.
            rendering_location = find_image("imagerenderingprogress.png", confidence=0.7)
            if not rendering_location:
                elapsed = int(time.monotonic() - render_started)
                print(
                    f"✅ [GF-LOCK] imagerenderingprogress.png disappeared after "
                    f"{elapsed}s. Cursor remains locked at ({target_x}, {target_y}); "
                    "next permitted search is moregf.png only."
                )
                try:
                    hud.print("Image is ready; locating its More control...", "success")
                except Exception:
                    pass
                update_operation_status(
                    f"Rendering complete for {entry_name}; cursor remains locked while locating moregf.png"
                )
                return True

            now = time.monotonic()
            if now - last_status_time >= 10:
                elapsed = int(now - render_started)
                print(f"⏳ [GF-LOCK] Still rendering... ({elapsed}s elapsed; no timeout)")
                try:
                    hud.print(f"Image generation in progress... ({elapsed}s)", "processing")
                except Exception:
                    pass
                update_operation_status(
                    f"Google Flow image generation in progress for {entry_name} ({elapsed}s); waiting without timeout"
                )
                last_status_time = now

            _sleep(check_interval)


    def wait_for_generation_complete_gf(hwnd, entry_name, max_wait_seconds=40, check_interval=0.5):
        max_wait_seconds = _bounded_timeout(max_wait_seconds)
        print(f"⏳ [GF] Waiting for generation to complete...")
        print(f"🚀 [GF] Attempting fast-path via imagerenderingprogress.png...")
        fastpath_done = wait_for_imagerenderingprogress_and_jump_to_search(
            hwnd, entry_name, max_wait_seconds=max_wait_seconds, check_interval=check_interval
        )
        if fastpath_done:
            print(f"🎉 [GF] Fast-path completed — rendering finished, proceeding to download")
            return True, "complete"
        else:
            print(f"ℹ️ [GF] Fast-path did not trigger — falling back to normal generation wait flow")

        status_counter = 0
        try:
            hud.print("Google Flow image generation in progress... ", "processing")
        except Exception:
            pass
        update_operation_status("Google Flow image generation in progress... ")

        start_time = time.time()
        found_generating = False
        generating_first_seen = None

        print(f"🔍 [GF] Phase 1: Waiting for generatinggf_image.png...")
        while time.time() - start_time < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            check_and_click_exit_editing()
            generating_location = find_image("generatinggf_image.png", confidence=0.7)
            if generating_location:
                print(f"✅ [GF] Found generatinggf_image.png - generation in progress!")
                found_generating = True
                generating_first_seen = time.time()
                status_counter += 1
                try:
                    hud.print("Google Flow image generation in progress... ", "processing")
                except Exception:
                    pass
                update_operation_status("Google Flow image generation in progress... ")
                break
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                status_counter += 1
                print(f"⏳ [GF] Google Flow image generation in progress... ({elapsed}s elapsed, counter={status_counter})")
                try:
                    hud.print("Google Flow image generation in progress... ", "processing")
                except Exception:
                    pass
                update_operation_status("Google Flow image generation in progress... ")
            _sleep(check_interval)

        if not found_generating:
            print(f"⚠️ [GF] generatinggf_image.png not found within timeout — checking fallbacks...")
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            print(f"🔍 [GF] Checking for no_active_gf_generation.png directly...")
            check_and_click_exit_editing()
            no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
            if no_active_location:
                print(f"✅ [GF] Found no_active_gf_generation.png directly — image is ready!")
                try:
                    hud.print("Your image is ready.", "success")
                except Exception:
                    pass
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            recheck = handle_exit_gfsidebar_and_recheck()
            if recheck:
                print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback — image is ready!")
                try:
                    hud.print("Your image is ready.", "success")
                except Exception:
                    pass
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            print(f"❌ [GF] Could not confirm generation completion after all fallbacks")
            return False, "timeout"

        print(f"🔍 [GF] Phase 2: Waiting for generatinggf_image.png to disappear...")
        status_counter += 1
        try:
            hud.print("Google Flow image generation in progress... ", "processing")
        except Exception:
            pass
        update_operation_status("Google Flow image generation in progress... ")

        phase2_start = time.time()
        phase2_timeout = max_wait_seconds - (generating_first_seen - start_time) if generating_first_seen else max_wait_seconds - 30
        if phase2_timeout < 30:
            phase2_timeout = 30

        while time.time() - phase2_start < phase2_timeout:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            check_and_click_exit_editing()
            generating_location = find_image("generatinggf_image.png", confidence=0.7)
            if not generating_location:
                print(f"✅ [GF] generatinggf_image.png disappeared - checking for completion...")
                _sleep(0.5)
                check_and_click_exit_editing()
                no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
                if no_active_location:
                    print(f"✅ [GF] Found no_active_gf_generation.png - image is ready!")
                    try:
                        hud.print("Your image is ready.", "success")
                    except Exception:
                        pass
                    update_operation_status(f"Image generation complete for {entry_name}")
                    return True, "complete"
                else:
                    print(f"⚠️ [GF] no_active_gf_generation.png not found yet - trying exit_gfsidebar fallback...")
                    recheck = handle_exit_gfsidebar_and_recheck()
                    if recheck:
                        print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback - image is ready!")
                        try:
                            hud.print("Your image is ready.", "success")
                        except Exception:
                            pass
                        update_operation_status(f"Image generation complete for {entry_name}")
                        return True, "complete"
                    else:
                        print(f"⚠️ [GF] Still not found - continuing to wait...")
                        for _ in range(10):
                            check_for_termination()
                            _sleep(0.5)
                            if check_for_tryagain_and_abort():
                                return False, "poor_network"
                            check_and_click_exit_editing()
                            no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
                            if no_active_location:
                                print(f"✅ [GF] Found no_active_gf_generation.png - image is ready!")
                                try:
                                    hud.print("Your image is ready.", "success")
                                except Exception:
                                    pass
                                update_operation_status(f"Image generation complete for {entry_name}")
                                return True, "complete"
                        continue
            else:
                elapsed = int(time.time() - phase2_start)
                if elapsed % 10 == 0 and elapsed > 0:
                    status_counter += 1
                    print(f"⏳ [GF] Google Flow image generation in progress... ({elapsed}s elapsed in phase 2, counter={status_counter})")
                    try:
                        hud.print("Google Flow image generation in progress... ", "processing")
                    except Exception:
                        pass
                    update_operation_status("Google Flow image generation in progress... ")
                _sleep(check_interval)

        print(f"⏰ [GF] Generation timeout after {max_wait_seconds} seconds")
        return False, "timeout"

    # --- ROBUST DOWNLOAD HELPERS ---
    DOWNLOAD_IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"
    }
    DOWNLOAD_TEMP_SUFFIXES = (".crdownload", ".part", ".tmp", ".download")

    def _get_download_directories(extra_directory=None):
        """Discover Windows Downloads and any custom Edge profile download paths."""
        candidates = []

        def _add_directory(value):
            if not value:
                return
            try:
                expanded = os.path.expandvars(os.path.expanduser(str(value).strip().strip('"')))
                if not expanded:
                    return
                absolute = os.path.abspath(expanded)
                normalized = os.path.normcase(absolute)
                if all(os.path.normcase(os.path.abspath(item)) != normalized for item in candidates):
                    candidates.append(absolute)
            except Exception:
                pass

        # Windows Known Downloads directory (including redirected OneDrive paths).
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            import winreg
            registry_locations = (
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            for registry_path in registry_locations:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                        for value_name in (downloads_guid, "{374DE290-123F-4565-9164-39C4925E467B}"):
                            try:
                                value, _ = winreg.QueryValueEx(key, value_name)
                                _add_directory(value)
                            except OSError:
                                continue
                except OSError:
                    continue
        except Exception as registry_error:
            print(f"ℹ️ [DOWNLOAD] Windows Downloads registry lookup unavailable: {registry_error}")

        # Standard profile fallbacks.
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            _add_directory(os.path.join(user_profile, "Downloads"))
        _add_directory(os.path.expanduser("~/Downloads"))

        # Edge can use a custom directory per browser profile. Read every profile's
        # Preferences file so Profile 1/Profile 2 paths are included as well as Default.
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            edge_user_data = os.path.join(
                local_app_data, "Microsoft", "Edge", "User Data"
            )
            try:
                if os.path.isdir(edge_user_data):
                    for profile_name in os.listdir(edge_user_data):
                        profile_path = os.path.join(edge_user_data, profile_name)
                        preferences_path = os.path.join(profile_path, "Preferences")
                        if not os.path.isdir(profile_path) or not os.path.isfile(preferences_path):
                            continue
                        try:
                            with open(preferences_path, "r", encoding="utf-8") as pref_file:
                                preferences = json.load(pref_file)
                            download_settings = preferences.get("download", {})
                            if isinstance(download_settings, dict):
                                _add_directory(download_settings.get("default_directory"))
                        except Exception as pref_error:
                            print(
                                f"ℹ️ [DOWNLOAD] Could not read Edge profile '{profile_name}' "
                                f"download settings: {pref_error}"
                            )
            except Exception as edge_profile_error:
                print(f"ℹ️ [DOWNLOAD] Edge profile scan unavailable: {edge_profile_error}")

        # Include the project directory in case Edge is configured to save there.
        _add_directory(extra_directory)

        # Keep existing directories first, but retain not-yet-created custom paths
        # because Edge may create them when the download is triggered.
        return candidates

    def _capture_download_snapshot(extra_directory=None):
        """Capture file identity/size/time before clicking Google's download controls."""
        directories = _get_download_directories(extra_directory)
        files = {}
        scanned_count = 0
        for directory in directories:
            if not os.path.isdir(directory):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            if not entry.is_file(follow_symlinks=True):
                                continue
                            stat = entry.stat(follow_symlinks=True)
                            full_path = os.path.abspath(entry.path)
                            files[os.path.normcase(full_path)] = {
                                "mtime_ns": getattr(
                                    stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)
                                ),
                                "size": int(stat.st_size),
                            }
                            scanned_count += 1
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError) as scan_error:
                print(f"⚠️ [DOWNLOAD] Could not snapshot '{directory}': {scan_error}")

        snapshot = {
            "captured_at": time.time(),
            "captured_at_ns": time.time_ns(),
            "directories": directories,
            "files": files,
        }
        print(
            f"📸 [DOWNLOAD] Pre-click download snapshot captured: "
            f"{scanned_count} existing file(s) across {len(directories)} possible folder(s)."
        )
        for directory in directories:
            print(f"   📁 {directory}")
        return snapshot

    def _get_download_image_extension(file_path):
        """Return a supported image extension, using the file signature as fallback."""
        extension = os.path.splitext(file_path)[1].lower()
        if extension in DOWNLOAD_IMAGE_EXTENSIONS:
            return extension
        try:
            with open(file_path, "rb") as image_file:
                header = image_file.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ".png"
            if header.startswith(b"\xff\xd8\xff"):
                return ".jpg"
            if header.startswith((b"GIF87a", b"GIF89a")):
                return ".gif"
            if header.startswith(b"BM"):
                return ".bmp"
            if header.startswith((b"II*\x00", b"MM\x00*")):
                return ".tiff"
            if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return ".webp"
        except Exception:
            pass
        return None

    def _download_image_is_valid(file_path):
        """Reject incomplete/corrupt files instead of treating any new file as success."""
        try:
            if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 1024:
                return False
            from PIL import Image
            with Image.open(file_path) as image_file:
                image_file.verify()
            return _get_download_image_extension(file_path) is not None
        except ImportError:
            return _get_download_image_extension(file_path) is not None
        except Exception:
            return False

    def _get_new_download_candidates(snapshot):
        """Return only image files created/changed after the pre-click snapshot."""
        baseline = snapshot.get("files", {}) if isinstance(snapshot, dict) else {}
        directories = snapshot.get("directories", []) if isinstance(snapshot, dict) else []
        candidates = []
        pending_files = []

        for directory in directories:
            if not os.path.isdir(directory):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            if not entry.is_file(follow_symlinks=True):
                                continue
                            name = entry.name
                            lower_name = name.lower()
                            full_path = os.path.abspath(entry.path)
                            if lower_name.endswith(DOWNLOAD_TEMP_SUFFIXES):
                                pending_files.append(full_path)
                                continue

                            extension = _get_download_image_extension(full_path)
                            if extension is None:
                                continue

                            stat = entry.stat(follow_symlinks=True)
                            mtime_ns = getattr(
                                stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)
                            )
                            size = int(stat.st_size)
                            key = os.path.normcase(full_path)
                            previous = baseline.get(key)
                            is_new = previous is None
                            is_updated = (
                                previous is not None
                                and (
                                    size != int(previous.get("size", -1))
                                    or mtime_ns > int(previous.get("mtime_ns", 0))
                                )
                            )
                            if is_new or is_updated:
                                candidates.append({
                                    "path": full_path,
                                    "mtime_ns": mtime_ns,
                                    "size": size,
                                    "extension": extension,
                                })
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError) as scan_error:
                print(f"⚠️ [DOWNLOAD] Could not scan '{directory}': {scan_error}")

        candidates.sort(key=lambda item: item["mtime_ns"], reverse=True)
        return candidates, pending_files

    def _wait_for_download_file_stability(file_path, deadline):
        """Wait for a candidate to stop changing, then validate its image contents."""
        previous_signature = None
        stable_samples = 0
        last_logged_size = None

        while time.monotonic() < deadline:
            check_for_termination()
            try:
                stat = os.stat(file_path)
                signature = (
                    int(stat.st_size),
                    getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)),
                )
                if signature[0] > 1024 and signature == previous_signature:
                    stable_samples += 1
                else:
                    stable_samples = 0
                    previous_signature = signature

                if signature[0] != last_logged_size:
                    print(
                        f"   ⏳ [DOWNLOAD] Candidate size: {signature[0]} bytes; "
                        f"waiting for it to stabilize."
                    )
                    last_logged_size = signature[0]

                if stable_samples >= 2:
                    if _download_image_is_valid(file_path):
                        return True
                    # An image can be stable briefly while the browser is still
                    # finalizing it. Keep monitoring until the deadline.
                    stable_samples = 0
            except (OSError, PermissionError):
                previous_signature = None
                stable_samples = 0
            _sleep(0.25)
        return False

    def check_and_rename_download(
        entry_name, images_folder, timeout_seconds=40, check_interval=0.3,
        force_png=False, download_snapshot=None
    ):
        """Find, validate, and move the image created after the pre-click snapshot."""
        timeout_seconds = _bounded_timeout(timeout_seconds)
        print(f"📊 [DOWNLOAD] Monitoring all discovered Windows/Edge download folders for {entry_name}...")
        try:
            hud.print("Waiting for the download to finish...", "waiting")
        except Exception:
            pass
        update_operation_status(f"Waiting for download: {entry_name}")

        if not isinstance(download_snapshot, dict):
            download_snapshot = _capture_download_snapshot(images_folder)
        directories = download_snapshot.get("directories", [])
        if not directories:
            print("❌ [DOWNLOAD] No download directories could be identified.")
            return False, None

        start_time = time.monotonic()
        deadline = start_time + timeout_seconds
        downloaded_file_path = None
        last_status_time = start_time
        last_pending_report = 0.0
        rejected_candidates = set()

        while time.monotonic() < deadline:
            check_for_termination()
            try:
                # The Google Flow confirmation overlay can appear after the
                # download-menu click. Handle it during file monitoring too.
                now = time.monotonic()
                if now - last_pending_report >= 0.8:
                    try:
                        handle_webdownloadconfirmationmodal()
                    except (_WorkflowRestart, _ManualStop):
                        raise
                    except Exception as modal_error:
                        print(f"⚠️ [DOWNLOAD] Confirmation-modal check failed safely: {modal_error}")
                    last_pending_report = now

                check_and_click_exit_editing()
                candidates, pending_files = _get_new_download_candidates(download_snapshot)
                for pending_path in pending_files:
                    # Log partial downloads once per path; Chrome/Edge commonly
                    # use .crdownload while the browser is still writing.
                    if pending_path not in rejected_candidates:
                        print(f"⏳ [DOWNLOAD] Browser is still writing: {pending_path}")
                        rejected_candidates.add(pending_path)

                for candidate in candidates:
                    candidate_path = candidate["path"]
                    if candidate_path in rejected_candidates:
                        continue
                    print(
                        f"🆕 [DOWNLOAD] New/updated image candidate detected: {candidate_path} "
                        f"({candidate['size']} bytes)"
                    )
                    if _wait_for_download_file_stability(candidate_path, deadline):
                        downloaded_file_path = candidate_path
                        print(f"✅ [DOWNLOAD] Stable, valid image confirmed: {downloaded_file_path}")
                        break
                    # Keep an unsteady candidate eligible for another check unless
                    # it disappeared or became invalid; the next scan uses fresh stats.
                    try:
                        if not os.path.exists(candidate_path):
                            rejected_candidates.add(candidate_path)
                    except Exception:
                        pass

                if downloaded_file_path:
                    break

                elapsed = int(time.monotonic() - start_time)
                if time.monotonic() - last_status_time >= 5:
                    print(
                        f"⏳ [DOWNLOAD] Still monitoring for {entry_name}... "
                        f"({elapsed}s elapsed; {len(candidates)} candidate(s), "
                        f"{len(pending_files)} partial download(s))"
                    )
                    try:
                        hud.print(f"Still downloading... ({elapsed}s)", "waiting")
                    except Exception:
                        pass
                    update_operation_status(f"Waiting for download {entry_name}... ({elapsed}s)")
                    last_status_time = time.monotonic()
                _sleep(check_interval)
            except (_WorkflowRestart, _ManualStop):
                raise
            except Exception as monitor_error:
                print(f"⚠️ [DOWNLOAD] Monitoring pass failed safely: {monitor_error}")
                _sleep(check_interval)

        # Final grace scan covers a browser that completed the file right at the
        # timeout boundary; it still requires a stable and valid image.
        if not downloaded_file_path:
            print("🔍 [DOWNLOAD] Performing final cross-folder scan (including timeout grace)...")
            grace_deadline = time.monotonic() + 2.0
            candidates, pending_files = _get_new_download_candidates(download_snapshot)
            for candidate in candidates:
                candidate_path = candidate["path"]
                print(
                    f"🔎 [DOWNLOAD] Final candidate: {candidate_path} "
                    f"({candidate['size']} bytes)"
                )
                if _wait_for_download_file_stability(candidate_path, grace_deadline):
                    downloaded_file_path = candidate_path
                    break

        if not downloaded_file_path:
            print(
                f"❌ [DOWNLOAD] No new/updated valid image was found in any monitored folder. "
                f"Monitored {len(directories)} folder(s):"
            )
            for directory in directories:
                print(f"   • {directory} (exists={os.path.isdir(directory)})")
            return False, None

        try:
            os.makedirs(images_folder, exist_ok=True)
            source_path = os.path.abspath(downloaded_file_path)
            source_extension = _get_download_image_extension(source_path)
            if source_extension is None:
                print(f"❌ [DOWNLOAD] Detected file is not a supported image: {source_path}")
                return False, None

            new_filename = f"{entry_name}.png" if force_png else f"{entry_name}{source_extension}"
            target_path = os.path.abspath(os.path.join(images_folder, new_filename))

            if force_png:
                # Save to a temporary sibling and atomically replace the target.
                # This also handles a source that was already saved as Thumbnail.png.
                temp_target = target_path + ".download_tmp"
                from PIL import Image
                with Image.open(source_path) as source_image:
                    converted = source_image.convert(
                        "RGBA" if "A" in source_image.getbands() else "RGB"
                    )
                    converted.save(temp_target, format="PNG", optimize=True)
                os.replace(temp_target, target_path)
                if os.path.normcase(source_path) != os.path.normcase(target_path):
                    try:
                        os.remove(source_path)
                    except OSError:
                        pass
                print(f"✅ [DOWNLOAD] Thumbnail converted and saved as genuine PNG: {target_path}")
            else:
                if os.path.normcase(source_path) != os.path.normcase(target_path):
                    try:
                        os.replace(source_path, target_path)
                    except OSError:
                        import shutil
                        temporary_copy = target_path + ".download_tmp"
                        shutil.copy2(source_path, temporary_copy)
                        os.replace(temporary_copy, target_path)
                        try:
                            os.remove(source_path)
                        except OSError:
                            pass
                print(f"✅ [DOWNLOAD] Scene image saved as: {target_path}")

            if not _download_image_is_valid(target_path):
                print(f"❌ [DOWNLOAD] Destination image failed final validation: {target_path}")
                return False, None

            print(f"📁 [DOWNLOAD] Verified destination: {target_path}")
            try:
                hud.print("Saved successfully.", "success")
            except Exception:
                pass
            update_operation_status(f"Downloaded and verified: {os.path.basename(target_path)}")
            return True, target_path

        except Exception as save_error:
            print(f"❌ [DOWNLOAD] Failed to move/convert/verify downloaded image: {save_error}")
            traceback.print_exc()
            return False, None

    def download_google_flow_image(hwnd, entry_name, images_folder, force_png=False,
                                   known_render_center=None, known_card_box=None):
        # These variables belong to sceneiq_google_flow_images_generation_engine(), not this
        # nested function. Declaring them nonlocal also keeps the finally
        # block safe when Alt+/ interrupts the first polling wait.
        nonlocal download_ui_sequence_active
        nonlocal image_render_lock_active, image_render_lock_position

        print(f"📥 [GF-DOWNLOAD] Starting Google Flow download procedure for {entry_name}...")

        # A scene batch supplies the exact OpenCV rectangle of a YOLO-confirmed
        # image card. Hover the card's centre so Google Flow reveals that card's
        # own More/download controls. The older render-marker route remains only
        # for legacy callers such as the project thumbnail.
        batch_download_region = None
        if known_card_box is not None:
            card_x, card_y, card_width, card_height = [int(v) for v in known_card_box]
            target_x = card_x + card_width // 2
            target_y = card_y + card_height // 2
            image_render_lock_position = (target_x, target_y)
            image_render_lock_active = True
            set_image_scroll_lock(True)
            screen_width, screen_height = pyautogui.size()
            region_left = max(0, card_x - 8)
            region_top = max(0, card_y - 8)
            region_right = min(screen_width, card_x + card_width + 8)
            region_bottom = min(screen_height, card_y + card_height + 8)
            batch_download_region = (
                region_left,
                region_top,
                max(1, region_right - region_left),
                max(1, region_bottom - region_top)
            )
            print(
                f"🎯 [GF-DOWNLOAD] Hovering the centre of the YOLO-confirmed "
                f"{entry_name} image card at ({target_x}, {target_y}); "
                f"card box=({card_x},{card_y},{card_width},{card_height})."
            )
            pyautogui.moveTo(target_x, target_y, duration=0.18)
            _sleep(0.35)
            search_location = type(
                "TrackedImageCardPosition",
                (),
                {"x": target_x, "y": target_y}
            )()
        elif known_render_center is not None:
            render_x, render_y = int(known_render_center[0]), int(known_render_center[1])
            image_render_lock_position = (render_x - 50, render_y + 50)
            image_render_lock_active = True
            set_image_scroll_lock(True)
            target_x, target_y = image_render_lock_position
            pyautogui.moveTo(target_x, target_y, duration=0.2)
            _sleep(0.3)
            search_location = type(
                "TrackedRenderPosition",
                (),
                {"x": render_x, "y": render_y}
            )()
            screen_width, screen_height = pyautogui.size()
            region_top = max(0, render_y - 450)
            region_bottom = min(screen_height, render_y + 450)
            batch_download_region = (0, region_top, screen_width, max(1, region_bottom - region_top))
            print(
                f"🔒 [GF-DOWNLOAD] Using legacy tracked render center "
                f"({render_x}, {render_y}); cursor anchor=({target_x}, {target_y})."
            )
        else:
            # Legacy single-job / thumbnail route.
            search_location = ensure_image_hover_position(
                timeout_seconds=STAGE_TIMEOUT_SECONDS,
                offset_px=50
            )

        # Protect the complete download UI sequence from periodic exit editing
        # detection. Hotkeys/timeouts continue to be checked normally.
        download_ui_sequence_active = True
        try:

            print(
                "✅ [GF-DOWNLOAD] Image hover position is confirmed; now preparing "
                "the download controls."
            )
            try:
                hud.print("Preparing the download...", "downloading")
            except Exception:
                pass
            update_operation_status(f"Starting download for {entry_name}...")

            print(
                "🔍 [GF-DOWNLOAD] Step 1 complete: the target image hover position "
                "has been established before preparing that card's download controls."
            )

            print(
                "🔒 [GF-DOWNLOAD] Cursor remains locked at the original image position. "
                "Searching for moregf.png inside the target card; no scrolling is allowed while locked."
            )
            moregf_found = False
            moregf_wait_started = time.monotonic()
            last_more_log = moregf_wait_started

            while not moregf_found:
                check_for_termination()

                # The confirmation modal may appear at any time. Handle it
                # using its existing two-image verification, then restore anchor.
                _service_modal_and_restore_locked_cursor()
                restore_locked_cursor()

                # If rendering has resumed while waiting for More, re-anchor
                # 50px left and 50px below the new progress match, then wait again.
                rendering_again = (
                    find_image("imagerenderingprogress.png", confidence=0.7)
                    if known_render_center is None and known_card_box is None
                    else None
                )
                if rendering_again:
                    image_render_lock_position = (
                        int(rendering_again.x - 50),
                        int(rendering_again.y + 50)
                    )
                    target_x, target_y = image_render_lock_position
                    image_render_lock_active = True
                    set_image_scroll_lock(True)
                    pyautogui.moveTo(target_x, target_y, duration=0.1)
                    print(
                        "🔁 [GF-DOWNLOAD-LOCK] Rendering indicator reappeared; "
                        f"re-anchored at ({target_x}, {target_y}) and waiting again."
                    )
                    render_again_started = time.monotonic()
                    last_render_again_log = render_again_started

                    while True:
                        check_for_termination()
                        _service_modal_and_restore_locked_cursor()
                        restore_locked_cursor()
                        still_rendering = find_image(
                            "imagerenderingprogress.png", confidence=0.7
                        )
                        if not still_rendering:
                            elapsed_again = int(time.monotonic() - render_again_started)
                            print(
                                "✅ [GF-DOWNLOAD-LOCK] Rendering indicator disappeared "
                                f"again after {elapsed_again}s; resuming More search."
                            )
                            break
                        now_again = time.monotonic()
                        if now_again - last_render_again_log >= 10:
                            elapsed_again = int(now_again - render_again_started)
                            print(
                                f"⏳ [GF-DOWNLOAD-LOCK] Rendering resumed "
                                f"({elapsed_again}s); waiting without timeout."
                            )
                            last_render_again_log = now_again
                        _sleep(0.4)
                    restore_locked_cursor()
                    continue

                # Search More only after confirming rendering is not active.
                moregf_location = find_image(
                    "moregf.png", confidence=0.7, region=batch_download_region
                )
                if moregf_location:
                    print(
                        f"✅ [GF-DOWNLOAD] moregf.png found at "
                        f"({moregf_location.x}, {moregf_location.y}); clicking its right edge."
                    )
                    clicked = click_right_edge_of_image(
                        "moregf.png", confidence=0.7, region=batch_download_region
                    )
                    if clicked:
                        moregf_found = True
                        image_render_lock_active = False
                        set_image_scroll_lock(False)
                        print(
                            "🔓 [GF-DOWNLOAD] More control found and clicked; "
                            "cursor-position lock released."
                        )
                        break
                    # If the match could not be clicked, restore the anchor and
                    # continue looking ONLY for moregf.png.
                    pyautogui.moveTo(target_x, target_y, duration=0.1)

                now = time.monotonic()
                if now - last_more_log >= 10:
                    elapsed = int(now - moregf_wait_started)
                    print(
                        f"⏳ [GF-DOWNLOAD-LOCK] moregf.png not found after {elapsed}s; "
                        f"cursor remains forced to ({target_x}, {target_y})."
                    )
                    update_operation_status(
                        f"Waiting for moregf.png for {entry_name}; cursor position remains locked"
                    )
                    last_more_log = now
                _sleep(0.4)

            print(f"🔍 [GF-DOWNLOAD] Step 4: Looking for downloadgfimage.png...")
            download_location = wait_for_image("downloadgfimage.png", timeout_seconds=20, confidence=0.7)
            if download_location:
                # CRITICAL: take the filesystem baseline BEFORE the click. The old
                # watcher took its snapshot after the download started, which could
                # miss fast files or classify them as pre-existing.
                download_snapshot = _capture_download_snapshot(images_folder)
                pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.5)
                print(f"✅ [GF-DOWNLOAD] Clicked downloadgfimage.png; pre-click snapshot is active")
            else:
                print(f"❌ [GF-DOWNLOAD] downloadgfimage.png not found — download cannot proceed")
                return False

            print(f"🔍 [GF-DOWNLOAD] Step 5: Looking for gfdownloadquality.png...")
            quality_location = wait_for_image("gfdownloadquality.png", timeout_seconds=15, confidence=0.7)
            if quality_location:
                pyautogui.moveTo(quality_location.x, quality_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.5)
                print(f"✅ [GF-DOWNLOAD] Clicked gfdownloadquality.png")
            else:
                print(f"⚠️ [GF-DOWNLOAD] gfdownloadquality.png not found — download may still proceed...")

            print(f"📊 [GF-DOWNLOAD] Step 6: Monitoring background for new download...")
            try:
                hud.print("Downloading your image...", "downloading")
            except Exception:
                pass
            update_operation_status(f"Downloading {entry_name}...")

            download_success = False
            file_path = None
            download_attempts = 0
            max_download_attempts = 3

            while download_attempts < max_download_attempts and not download_success:
                download_attempts += 1
                print(f"🔄 [GF-DOWNLOAD] Download attempt {download_attempts}/{max_download_attempts}")
                timeout_seconds = 40 if download_attempts == 1 else 30
                download_success, file_path = check_and_rename_download(
                    entry_name,
                    images_folder,
                    timeout_seconds=timeout_seconds,
                    check_interval=0.3,
                    force_png=force_png,
                    download_snapshot=download_snapshot
                )
                if download_success:
                    print(f"✅ [GF-DOWNLOAD] Download successful on attempt {download_attempts}")
                    break

                if download_attempts < max_download_attempts:
                    # A file can finish between the previous timeout return and
                    # the retry UI sequence. Re-scan against the original baseline
                    # before clicking Download again, avoiding duplicate downloads.
                    print("🔎 [GF-DOWNLOAD] Quick late-arrival scan before retrying the UI...")
                    late_success, late_file_path = check_and_rename_download(
                        entry_name,
                        images_folder,
                        timeout_seconds=2,
                        check_interval=0.2,
                        force_png=force_png,
                        download_snapshot=download_snapshot
                    )
                    if late_success:
                        download_success = True
                        file_path = late_file_path
                        print("✅ [GF-DOWNLOAD] Late-arriving download detected; no second click needed.")
                        break

                if download_attempts < max_download_attempts:
                    print(f"⚠️ [GF-DOWNLOAD] Download not found after {timeout_seconds}s — retrying...")
                    try:
                        hud.print(f"Retrying the download... ({download_attempts}/{max_download_attempts})", "warning")
                    except Exception:
                        pass
                    update_operation_status(f"Retrying download for {entry_name}... (attempt {download_attempts + 1})")

                    # Restore the precise saved hover point. For the CV/YOLO
                    # route this is the card centre; legacy callers retain their
                    # previous hover-position helper.
                    if known_card_box is None and known_render_center is None:
                        search_location = ensure_image_hover_position(
                            timeout_seconds=STAGE_TIMEOUT_SECONDS,
                            offset_px=50
                        )
                    print(
                        "🖱️ [GF-DOWNLOAD-RETRY] Restoring the saved card/render "
                        "hover position before retrying the download controls."
                    )

                    target_x, target_y = image_render_lock_position
                    pyautogui.moveTo(target_x, target_y, duration=0.1)
                    more_retry_location = find_image(
                        "moregf.png", confidence=0.7, region=batch_download_region
                    )
                    if more_retry_location:
                        click_right_edge_of_image(
                            "moregf.png", confidence=0.7, region=batch_download_region
                        )
                    download_location = wait_for_image("downloadgfimage.png", timeout_seconds=10, confidence=0.7)
                    if download_location:
                        pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.5)
                    quality_location = wait_for_image("gfdownloadquality.png", timeout_seconds=10, confidence=0.7)
                    if quality_location:
                        pyautogui.moveTo(quality_location.x, quality_location.y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.5)
                    _sleep(2)

            if download_success:
                print(f"🎉 [GF-DOWNLOAD] {entry_name} downloaded and saved successfully!")
                try:
                    hud.print("Image downloaded successfully.", "success")
                except Exception:
                    pass
                update_operation_status(f"{entry_name} completed successfully", is_success=True)
                return True
            else:
                print(f"❌ [GF-DOWNLOAD] Failed to download {entry_name} after {max_download_attempts} attempts")
                try:
                    hud.print("Could not download the image.", "error")
                except Exception:
                    pass
                update_operation_status(f"Failed to download {entry_name} after multiple attempts", is_error=True)
                return False

        finally:
            download_ui_sequence_active = False
            if known_render_center is not None or known_card_box is not None:
                image_render_lock_active = False
                image_render_lock_position = None
                set_image_scroll_lock(False)
            elif not image_render_lock_active:
                set_image_scroll_lock(False)
    def handle_webdownloadconfirmationmodal():
        """
        Handles webdownloadconfirmationmodal.png using a mandatory 2-step
        verification.

        The confirmation button may ONLY be clicked when BOTH of these
        images are currently visible on screen:

            1. webdownloadconfirmationmodal.png
            2. webdownloadmodalappearance.png

        If webdownloadconfirmationmodal.png is visible but
        webdownloadmodalappearance.png is NOT visible, the confirmation
        button is NOT clicked and the function skips it entirely.
        """

        print(f"🔍 [MODAL] Step 1: Checking for webdownloadconfirmationmodal.png...")
        modal_location = find_image(
            "webdownloadconfirmationmodal.png",
            confidence=0.7
        )

        if not modal_location:
            print(
                f"ℹ️ [MODAL] webdownloadconfirmationmodal.png not found "
                f"— proceeding normally"
            )
            return False

        print(
            f"✅ [MODAL] webdownloadconfirmationmodal.png found at "
            f"({modal_location.x}, {modal_location.y})"
        )

        # --------------------------------------------------------------
        # REQUIRED SECOND VERIFICATION
        # --------------------------------------------------------------
        print(
            f"🔍 [MODAL] Step 2: Checking for webdownloadmodalappearance.png..."
        )

        modal_appearance_location = find_image(
            "webdownloadmodalappearance.png",
            confidence=0.7
        )

        if not modal_appearance_location:
            print(
                f"⚠️ [MODAL] webdownloadconfirmationmodal.png was found, "
                f"BUT webdownloadmodalappearance.png was NOT found."
            )
            print(
                f"⏭️ [MODAL] 2-step verification FAILED — "
                f"SKIPPING webdownloadconfirmationmodal click entirely."
            )
            return False

        print(
            f"✅ [MODAL] webdownloadmodalappearance.png found at "
            f"({modal_appearance_location.x}, "
            f"{modal_appearance_location.y})"
        )

        # BOTH required images are visible, so clicking is now permitted.
        print(
            f"🔐 [MODAL] 2-step verification PASSED — "
            f"both required images are visible."
        )
        print(
            f"🖱️ [MODAL] Clicking webdownloadconfirmationmodal.png..."
        )

        try:
            hud.print("Confirming the download...", "warning")
        except Exception:
            pass

        pyautogui.moveTo(
            modal_location.x,
            modal_location.y,
            duration=0.1
        )
        pyautogui.click()
        _sleep(0.5)
        move_mouse_to_center_of_screen()
        _sleep(0.3)

        # --------------------------------------------------------------
        # RE-CHECK AFTER THE FIRST CLICK
        # --------------------------------------------------------------
        print(
            f"🔍 [MODAL] Re-checking both verification images "
            f"after first click..."
        )

        recheck_appearance_location = find_image(
            "webdownloadmodalappearance.png",
            confidence=0.7
        )

        recheck_modal_location = find_image(
            "webdownloadconfirmationmodal.png",
            confidence=0.7
        )

        if recheck_modal_location and recheck_appearance_location:
            print(
                f"⚠️ [MODAL] Both verification images are still visible "
                f"after the first click — clicking confirmation again..."
            )

            pyautogui.moveTo(
                recheck_modal_location.x,
                recheck_modal_location.y,
                duration=0.1
            )
            pyautogui.click()
            _sleep(0.5)
            move_mouse_to_center_of_screen()
            _sleep(0.3)

            print(
                f"✅ [MODAL] Second click completed with both "
                f"verification conditions satisfied."
            )

        elif recheck_modal_location and not recheck_appearance_location:
            print(
                f"ℹ️ [MODAL] webdownloadconfirmationmodal.png is still "
                f"visible, but webdownloadmodalappearance.png is no longer "
                f"visible — NOT clicking again."
            )
            print(
                f"⏭️ [MODAL] Skipping the confirmation button because "
                f"the required 2-step verification is no longer satisfied."
            )

        elif not recheck_modal_location:
            print(
                f"✅ [MODAL] webdownloadconfirmationmodal.png is no longer "
                f"visible — confirmation completed."
            )

        else:
            print(
                f"ℹ️ [MODAL] Verification state changed after the click — "
                f"no additional click required."
            )

        print(
            f"✅ [MODAL] Modal handling completed — proceeding with "
            f"normal protocol"
        )
        return True

    def _service_modal_and_restore_locked_cursor():
        """
        Poll the download-confirmation modal during the locked phase. If it is
        visible, the existing handler verifies both modal images and clicks it.
        Always restore the saved image anchor immediately afterward.
        """
        if not image_render_lock_active or image_render_lock_position is None:
            return False
        handled = False
        try:
            handled = handle_webdownloadconfirmationmodal()
        except (_WorkflowRestart, _ManualStop):
            set_image_scroll_lock(False)
            raise
        except Exception as modal_error:
            print(f"⚠️ [MODAL-LOCK] Modal check failed safely: {modal_error}")
        finally:
            restore_locked_cursor()
        return handled

    IMAGE_FILE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"
    }
    ENTRY_IMAGE_PATTERN = re.compile(
        r"^entry_(\d+)\.(png|jpg|jpeg|gif|webp|bmp|tiff)$",
        re.IGNORECASE
    )
    THUMBNAIL_FILENAME = "Thumbnail.png"

    def _cleanup_project_image_folder(images_folder, expected_entries):
        """
        Keep only entry_N image files within the expected range and Thumbnail.png.
        Delete every other image file, including numbered variants and unrelated
        images. For duplicate formats of the same entry, keep the newest valid
        file and delete the others.
        """
        os.makedirs(images_folder, exist_ok=True)
        valid_entries = {}
        thumbnail_candidates = []

        try:
            filenames = os.listdir(images_folder)
        except OSError as scan_error:
            print(f"❌ [IMAGE-CLEANUP] Could not scan {images_folder}: {scan_error}")
            return False

        for filename in filenames:
            full_path = os.path.join(images_folder, filename)
            if not os.path.isfile(full_path):
                continue

            extension = os.path.splitext(filename)[1].lower()
            stem = os.path.splitext(filename)[0]

            # The one permitted video-level thumbnail is a PNG named Thumbnail.
            if stem.lower() == "thumbnail" and extension == ".png":
                try:
                    if os.path.getsize(full_path) > 0:
                        thumbnail_candidates.append(full_path)
                    else:
                        os.remove(full_path)
                        print(f"🗑️ [IMAGE-CLEANUP] Deleted empty thumbnail: {filename}")
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not inspect {filename}: {cleanup_error}")
                continue

            match = ENTRY_IMAGE_PATTERN.fullmatch(filename)
            if match:
                number = int(match.group(1))
                try:
                    valid_file = os.path.getsize(full_path) > 0
                except OSError:
                    valid_file = False

                if 1 <= number <= expected_entries and valid_file:
                    try:
                        modified = os.path.getmtime(full_path)
                    except OSError:
                        modified = 0
                    valid_entries.setdefault(number, []).append((modified, full_path))
                    continue

            # Delete unrelated images and entry files outside the current script's
            # valid numbering range. Non-image support files are left untouched.
            if extension in IMAGE_FILE_EXTENSIONS:
                try:
                    os.remove(full_path)
                    print(f"🗑️ [IMAGE-CLEANUP] Deleted unrecognized image: {filename}")
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete {filename}: {cleanup_error}")

        # Resolve duplicate entry formats, keeping the newest non-empty image.
        for number, candidates in valid_entries.items():
            candidates.sort(key=lambda item: item[0], reverse=True)
            for _, duplicate_path in candidates[1:]:
                try:
                    os.remove(duplicate_path)
                    print(
                        f"🗑️ [IMAGE-CLEANUP] Deleted duplicate for entry_{number}: "
                        f"{os.path.basename(duplicate_path)}"
                    )
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete duplicate {duplicate_path}: {cleanup_error}")

        # Keep exactly one canonical Thumbnail.png. Prefer the newest valid PNG.
        if thumbnail_candidates:
            thumbnail_candidates.sort(
                key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0,
                reverse=True
            )
            keep_thumbnail = thumbnail_candidates[0]
            canonical_thumbnail = os.path.join(images_folder, THUMBNAIL_FILENAME)
            if os.path.abspath(keep_thumbnail) != os.path.abspath(canonical_thumbnail):
                try:
                    if os.path.exists(canonical_thumbnail):
                        os.remove(canonical_thumbnail)
                    os.replace(keep_thumbnail, canonical_thumbnail)
                    keep_thumbnail = canonical_thumbnail
                except OSError as rename_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not normalize thumbnail filename: {rename_error}")

            for duplicate_path in thumbnail_candidates[1:]:
                if os.path.abspath(duplicate_path) == os.path.abspath(keep_thumbnail):
                    continue
                try:
                    if os.path.exists(duplicate_path):
                        os.remove(duplicate_path)
                        print(
                            "🗑️ [IMAGE-CLEANUP] Deleted duplicate thumbnail: "
                            f"{os.path.basename(duplicate_path)}"
                        )
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete duplicate thumbnail: {cleanup_error}")

        print(
            f"🧹 [IMAGE-CLEANUP] Accepted scene images: "
            f"{sorted(valid_entries.keys())}; thumbnail: "
            f"{'present' if os.path.isfile(os.path.join(images_folder, THUMBNAIL_FILENAME)) else 'missing'}"
        )
        return True

    def _find_entry_image(images_folder, entry_number):
        """Return one non-empty file that exactly matches entry_N.ext."""
        if not os.path.isdir(images_folder):
            return None
        try:
            for filename in os.listdir(images_folder):
                match = ENTRY_IMAGE_PATTERN.fullmatch(filename)
                if match and int(match.group(1)) == int(entry_number):
                    full_path = os.path.join(images_folder, filename)
                    if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                        return full_path
        except OSError as scan_error:
            print(f"⚠️ [VALIDATE] Could not inspect entry_{entry_number}: {scan_error}")
        return None

    def _thumbnail_exists(images_folder):
        thumbnail_path = os.path.join(images_folder, THUMBNAIL_FILENAME)
        try:
            if not os.path.isfile(thumbnail_path) or os.path.getsize(thumbnail_path) <= 0:
                return False
            from PIL import Image
            with Image.open(thumbnail_path) as thumbnail_image:
                if thumbnail_image.format != "PNG":
                    raise ValueError("Thumbnail file is not a genuine PNG image")
                thumbnail_image.verify()
            return True
        except Exception as thumbnail_error:
            if os.path.exists(thumbnail_path):
                try:
                    os.remove(thumbnail_path)
                    print(
                        f"🗑️ [THUMBNAIL] Removed invalid Thumbnail.png: "
                        f"{thumbnail_error}"
                    )
                except OSError as remove_error:
                    print(
                        f"⚠️ [THUMBNAIL] Invalid thumbnail could not be removed: "
                        f"{remove_error}"
                    )
            return False

    def validate_entry_order(images_folder, expected_entries):
        """
        Do not reset valid files when a gap exists. Return the exact missing
        entry numbers so only those images are regenerated.
        """
        if not _cleanup_project_image_folder(images_folder, expected_entries):
            return False, []
        missing_numbers = [
            number
            for number in range(1, expected_entries + 1)
            if _find_entry_image(images_folder, number) is None
        ]
        existing_numbers = [
            number
            for number in range(1, expected_entries + 1)
            if number not in missing_numbers
        ]
        print(f"📊 [VALIDATE] Existing valid entries: {existing_numbers}")
        print(f"📊 [VALIDATE] Missing entries to generate: {missing_numbers}")
        return True, missing_numbers

    def process_prompt_job_gf(
        hwnd, job_name, prompt_text, images_folder,
        success_message, force_png=False
    ):
        """Submit one prompt, verify it was sent, wait for render, and download."""
        if not isinstance(prompt_text, str) or not prompt_text.strip():
            print(f"⚠️ [PROMPT-JOB] Empty prompt for {job_name}")
            return False

        print(f"\n{'='*50}")
        print(f"📝 [PROMPT-JOB] Generating: {job_name}")
        print(f"{'='*50}")
        update_operation_status(f"Preparing image generation for {job_name}...")
        try:
            hud.print(f"Preparing {job_name}...", "processing")
        except Exception:
            pass

        # A restart always begins again at prompt submission. No saved scene
        # or thumbnail phase is trusted as proof of a completed image.
        send_attempt = 0
        send_confirmed = False

        while not send_confirmed:
            send_attempt += 1
            print(f"\\n🔁 [SEND-LOOP] Send attempt #{send_attempt} for {job_name}")
            update_operation_status(
                f"Submitting {job_name} prompt (attempt {send_attempt})..."
            )
            check_and_click_exit_editing()
            send_coords = paste_prompt_and_click_send(hwnd, prompt_text, job_name)
            if send_coords is None:
                print(f"❌ [SEND-LOOP] Could not paste & click send for {job_name}")
                return False

            send_x, send_y = send_coords
            confirm_result = confirm_sendgf_and_wait_for_generating(
                hwnd,
                job_name,
                prompt_text,
                send_x,
                send_y,
                max_confirm_seconds=STAGE_TIMEOUT_SECONDS,
                check_interval=0.4
            )

            if confirm_result == "confirmed":
                print(f"✅ [SEND-LOOP] Prompt confirmed for {job_name}")
                send_confirmed = True
            elif confirm_result in ("needs_restart", "timeout"):
                abort_operation(
                    f"Prompt confirmation was not detected for {job_name} within 40 seconds"
                )
            elif confirm_result == "poor_network":
                print(f"❌ [SEND-LOOP] Poor network detected while submitting {job_name}")
                return False
            elif confirm_result == "aborted":
                print(f"🛑 [SEND-LOOP] Submission aborted for {job_name}")
                return False
            else:
                abort_operation(
                    f"Unexpected send-confirmation result for {job_name}: {confirm_result}"
                )

        print(f"⏳ [PROMPT-JOB] Waiting for Google Flow to render {job_name}...")
        generation_complete, status = wait_for_generation_complete_gf(
            hwnd, job_name, max_wait_seconds=STAGE_TIMEOUT_SECONDS
        )
        if not generation_complete:
            print(f"❌ [PROMPT-JOB] Generation did not complete for {job_name}: {status}")
            update_operation_status(
                f"Generation failed for {job_name}: {status}",
                is_error=True
            )
            if status == "poor_network":
                return False
            abort_operation(f"Generation failed for {job_name}: {status}")
            return False

        print(f"📥 [PROMPT-JOB] Downloading completed image for {job_name}...")
        download_success = download_google_flow_image(
            hwnd, job_name, images_folder, force_png=force_png
        )
        if not download_success:
            print(f"❌ [PROMPT-JOB] Download failed for {job_name}; the job will not be skipped")
            update_operation_status(
                f"Download failed for {job_name}",
                is_abort=True
            )
            abort_operation(f"Download failed for {job_name}")
            return False

        if force_png:
            expected_path = os.path.join(images_folder, THUMBNAIL_FILENAME)
            if not os.path.isfile(expected_path) or os.path.getsize(expected_path) <= 0:
                abort_operation(
                    f"{job_name} download did not produce a valid {THUMBNAIL_FILENAME}"
                )

        print(f"🎉 [PROMPT-JOB] {success_message}")
        try:
            hud.print(f"{success_message}", "success")
        except Exception:
            pass
        update_operation_status(f"{job_name} complete", is_success=True)
        return True

    def process_single_entry_gf(hwnd, entry_index, entry_data, images_folder):
        entry_name = f"entry_{entry_index + 1}"
        entry_json = format_entry_for_paste(entry_data)
        if not entry_json:
            print(f"⚠️ [SCENE] No data found for {entry_name}")
            return False

        return process_prompt_job_gf(
            hwnd=hwnd,
            job_name=entry_name,
            prompt_text=entry_json,
            images_folder=images_folder,
            success_message=f"Scene {entry_index + 1} image is ready and downloaded",
            force_png=False
        )

    # ------------------------------------------------------------------
    # OpenCV + YOLO image-card detection
    # ------------------------------------------------------------------
    def _get_flow_yolo_model():
        """Load the configured YOLO model once and reuse it for every card."""
        nonlocal flow_yolo_model
        if flow_yolo_model is None:
            model_name = os.environ.get(
                "SCENEIQ_GOOGLE_FLOW_YOLO_MODEL",
                FLOW_YOLO_MODEL_DEFAULT
            ).strip() or FLOW_YOLO_MODEL_DEFAULT
            print(f"🧠 [YOLO] Loading object-detection model: {model_name}")
            try:
                flow_yolo_model = YOLO(model_name)
                print("✅ [YOLO] Model loaded; object validation is enabled.")
            except Exception as model_error:
                message = (
                    f"Could not load YOLO model '{model_name}': {model_error}. "
                    "Install ultralytics and ensure the model weights are available."
                )
                print(f"❌ [YOLO] {message}")
                update_operation_status(message, is_error=True)
                raise _BatchTrackingFailure(message)
        return flow_yolo_model

    def _capture_google_flow_frame():
        """Capture the visible desktop as an OpenCV BGR frame."""
        screenshot = pyautogui.screenshot()
        frame_rgb = np.asarray(screenshot)
        if frame_rgb.ndim != 3 or frame_rgb.shape[2] < 3:
            raise _BatchTrackingFailure("Desktop screenshot did not contain an RGB image")
        return cv2.cvtColor(frame_rgb[:, :, :3], cv2.COLOR_RGB2BGR)

    def _box_iou_xywh(box_a, box_b):
        ax, ay, aw, ah = [int(v) for v in box_a]
        bx, by, bw, bh = [int(v) for v in box_b]
        left = max(ax, bx)
        top = max(ay, by)
        right = min(ax + aw, bx + bw)
        bottom = min(ay + ah, by + bh)
        intersection = max(0, right - left) * max(0, bottom - top)
        union = aw * ah + bw * bh - intersection
        return float(intersection / union) if union > 0 else 0.0

    def _detect_google_flow_image_cards(frame):
        """
        Detect complete 16:9 image cards with OpenCV.

        The screenshot can contain adjacent card borders that OpenCV merges into
        one wide contour. Such a contour is split into individual 16:9 cells.
        The bottom prompt composer is treated as an occlusion mask: cards under
        it are ignored until scrolling brings them fully into view.
        """
        if frame is None or frame.size == 0:
            return []

        screen_h, screen_w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 45, 145)
        edges[:int(screen_h * 0.085), :] = 0
        edges[:, :int(screen_w * 0.17)] = 0

        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel, iterations=1)
        contours = cv2.findContours(
            closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )[-2]

        min_width = max(260, int(screen_w * 0.18))
        min_height = max(135, int(screen_h * 0.15))
        composer_x1 = int(screen_w * 0.24)
        composer_y1 = int(screen_h * 0.79)
        composer_x2 = int(screen_w * 0.73)
        composer_y2 = int(screen_h * 0.96)
        candidates = []

        def _add_candidate(box):
            x, y, width, height = [int(v) for v in box]
            if width < min_width or height < min_height:
                return
            if x < int(screen_w * 0.17) or y < int(screen_h * 0.08):
                return
            if x + width > screen_w - 2 or y + height > screen_h - 3:
                return
            aspect_ratio = width / float(height)
            if not 1.48 <= aspect_ratio <= 2.05:
                return

            rectangle_area = width * height
            overlap_width = max(
                0, min(x + width, composer_x2) - max(x, composer_x1)
            )
            overlap_height = max(
                0, min(y + height, composer_y2) - max(y, composer_y1)
            )
            overlap_ratio = (
                (overlap_width * overlap_height) / float(rectangle_area)
            ) if rectangle_area else 1.0
            if overlap_ratio > 0.025:
                return

            inset = max(5, int(min(width, height) * 0.025))
            crop = frame[
                y + inset:y + height - inset,
                x + inset:x + width - inset
            ]
            if crop.size == 0:
                return
            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            if float(np.std(crop_gray)) < 12.0:
                return
            if float(cv2.Laplacian(crop_gray, cv2.CV_64F).var()) < 12.0:
                return

            box = (x, y, width, height)
            if any(_box_iou_xywh(box, old) >= 0.72 for old in candidates):
                return
            candidates.append(box)

        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if width < min_width or height < min_height:
                continue
            if y < int(screen_h * 0.08) or y + height > screen_h - 3:
                continue
            rectangle_area = width * height
            if rectangle_area <= 0:
                continue
            if float(cv2.contourArea(contour)) < rectangle_area * 0.35:
                continue

            aspect_ratio = width / float(height)
            if 1.48 <= aspect_ratio <= 2.05:
                _add_candidate((x, y, width, height))
                continue

            # When a row's two/three adjacent cards become one contour, split
            # it using the known 16:9 card geometry instead of rejecting the row.
            if 2.55 <= aspect_ratio <= 7.2 and height <= int(screen_h * 0.72):
                guessed_card_width = int(round(height * (16.0 / 9.0)))
                if guessed_card_width < min_width:
                    continue
                for card_count in (2, 3, 4):
                    estimated_gap = (
                        width - card_count * guessed_card_width
                    ) / float(card_count - 1)
                    if not 0 <= estimated_gap <= 70:
                        continue
                    reconstructed = []
                    for card_index in range(card_count):
                        card_x = int(round(
                            x + card_index * (guessed_card_width + estimated_gap)
                        ))
                        reconstructed.append((
                            card_x, y, guessed_card_width, height
                        ))
                    if all(
                        1.48 <= box[2] / float(box[3]) <= 2.05
                        and box[0] + box[2] <= screen_w - 2
                        for box in reconstructed
                    ):
                        for box in reconstructed:
                            _add_candidate(box)
                        break

        candidates.sort(key=lambda item: (item[1], item[0]))
        return candidates

    def _flow_card_perceptual_hash(frame, box):
        """Return a 64-bit pHash for re-identifying the same card after scrolling."""
        x, y, width, height = [int(v) for v in box]
        # Hash the central image area, not the rounded card border/hover chrome.
        # A deeper inset tolerates small contour-box differences after scrolling.
        inset_x = max(8, int(width * 0.12))
        inset_y = max(8, int(height * 0.12))
        crop = frame[
            y + inset_y:y + height - inset_y,
            x + inset_x:x + width - inset_x
        ]
        if crop.size == 0:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        coefficients = cv2.dct(np.float32(resized))[:8, :8]
        median_value = float(np.median(coefficients[1:, :]))
        bits = (coefficients > median_value).flatten()
        value = 0
        for bit in bits:
            value = (value << 1) | int(bool(bit))
        return int(value)

    def _flow_hash_distance(hash_a, hash_b):
        if hash_a is None or hash_b is None:
            return 64
        return int((int(hash_a) ^ int(hash_b)).bit_count())

    def _yolo_confirms_flow_card(frame, box):
        """
        Confirm that a rectangular candidate contains at least one identifiable
        object. The crop passed to YOLO is the card image only, not the browser UI.
        """
        x, y, width, height = [int(v) for v in box]
        inset_x = max(6, int(width * 0.035))
        inset_y = max(6, int(height * 0.035))
        crop = frame[
            y + inset_y:y + height - inset_y,
            x + inset_x:x + width - inset_x
        ]
        if crop.size == 0:
            return False, []

        model = _get_flow_yolo_model()
        try:
            predictions = model.predict(
                source=crop,
                imgsz=640,
                conf=FLOW_YOLO_CONFIDENCE,
                max_det=40,
                verbose=False
            )
        except Exception as inference_error:
            print(f"⚠️ [YOLO] Inference failed for card at ({x}, {y}): {inference_error}")
            return False, []

        if not predictions:
            return False, []

        result = predictions[0]
        names = getattr(result, "names", {}) or {}
        detections = []
        crop_area = float(crop.shape[0] * crop.shape[1])
        for detected_box in getattr(result, "boxes", []) or []:
            try:
                confidence = float(detected_box.conf[0].item())
                coordinates = detected_box.xyxy[0].tolist()
                left, top, right, bottom = [float(v) for v in coordinates]
                object_area = max(0.0, right - left) * max(0.0, bottom - top)
                if confidence < FLOW_YOLO_CONFIDENCE:
                    continue
                if crop_area <= 0 or object_area / crop_area < FLOW_YOLO_MIN_OBJECT_AREA_RATIO:
                    continue
                class_id = int(detected_box.cls[0].item())
                if isinstance(names, dict):
                    label = str(names.get(class_id, class_id))
                elif isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
                    label = str(names[class_id])
                else:
                    label = str(class_id)
                detections.append({
                    "label": label,
                    "confidence": round(confidence, 3),
                    "area_ratio": round(object_area / crop_area, 4)
                })
            except Exception:
                continue

        return bool(detections), detections

    def _scroll_google_flow_gallery(notches):
        """Scroll the Google Flow media gallery without locking the mouse."""
        nonlocal image_render_lock_active
        check_for_termination()
        if image_render_lock_active:
            image_render_lock_active = False
            set_image_scroll_lock(False)
        screen_width, screen_height = pyautogui.size()
        scroll_x = max(350, screen_width - 120)
        scroll_y = max(140, min(screen_height - 180, int(screen_height * 0.55)))
        pyautogui.moveTo(scroll_x, scroll_y, duration=0.04)
        pyautogui.scroll(int(notches))
        _sleep(0.45)

    def _reset_google_flow_gallery_to_top():
        """Return to the newest media cards before scanning or downloading."""
        _scroll_google_flow_gallery(45)
        _sleep(0.25)

    def _capture_yolo_card_candidates():
        """Detect and classify all complete image cards visible in this viewport."""
        frame = _capture_google_flow_frame()
        boxes = _detect_google_flow_image_cards(frame)
        candidates = []
        for box in boxes:
            fingerprint = _flow_card_perceptual_hash(frame, box)
            confirmed, objects = _yolo_confirms_flow_card(frame, box)
            candidates.append({
                "box": tuple(box),
                "fingerprint": fingerprint,
                "yolo_confirmed": bool(confirmed),
                "objects": objects,
                "frame_size": (int(frame.shape[1]), int(frame.shape[0]))
            })
        return frame, candidates

    def _capture_preexisting_flow_card_fingerprints(hwnd):
        """Snapshot existing gallery cards before submitting a new prompt batch.

        This prevents a previous image from being mistaken for a new batch card
        when one of the new generations is still in progress.
        """
        fingerprints = []
        pages_without_new_cards = 0
        _reset_google_flow_gallery_to_top()
        print("📸 [CV-BASELINE] Capturing the existing gallery before this batch is sent...")

        for page_index in range(FLOW_CARD_BASELINE_MAX_PAGES):
            check_for_termination()
            enforce_window_focus(hwnd)
            frame = _capture_google_flow_frame()
            boxes = _detect_google_flow_image_cards(frame)
            added_this_page = 0
            for box in boxes:
                fingerprint = _flow_card_perceptual_hash(frame, box)
                if fingerprint is None:
                    continue
                duplicate = any(
                    _flow_hash_distance(fingerprint, old_fingerprint)
                    <= FLOW_CARD_HASH_TOLERANCE
                    for old_fingerprint in fingerprints
                )
                if not duplicate:
                    fingerprints.append(fingerprint)
                    added_this_page += 1

            print(
                f"🔎 [CV-BASELINE] Viewport {page_index + 1}: "
                f"{len(boxes)} visible card(s), {added_this_page} new baseline fingerprint(s)."
            )
            if added_this_page == 0:
                pages_without_new_cards += 1
            else:
                pages_without_new_cards = 0

            # Stop at the bottom after repeated overlapping viewports add no
            # new card identity, rather than making all 30 scroll passes.
            if pages_without_new_cards >= 3:
                break
            _scroll_google_flow_gallery(-FLOW_CARD_SCROLL_NOTCHES)

        _reset_google_flow_gallery_to_top()
        print(
            f"✅ [CV-BASELINE] Recorded {len(fingerprints)} existing card fingerprint(s). "
            "Only cards absent from this snapshot can belong to the next batch."
        )
        return fingerprints

    def _fingerprint_matches_baseline(fingerprint, baseline_fingerprints):
        if fingerprint is None:
            return False
        return any(
            _flow_hash_distance(fingerprint, old_fingerprint)
            <= FLOW_CARD_BASELINE_HASH_TOLERANCE
            for old_fingerprint in (baseline_fingerprints or [])
        )

    def _same_flow_card(candidate_a, candidate_b):
        """Recognize a card repeated in overlapping scroll screenshots."""
        if _flow_hash_distance(
            candidate_a.get("fingerprint"), candidate_b.get("fingerprint")
        ) <= FLOW_CARD_HASH_TOLERANCE:
            return True
        return False

    def _wait_for_yolo_confirmed_flow_cards(
        hwnd, expected_count, baseline_fingerprints=None
    ):
        """
        Find the first N newest media-card rectangles across scrolling screenshots.
        OpenCV establishes the card slots; YOLO must identify at least one object
        inside every one of the first N slots before any download is attempted.

        This deliberately does not inspect imagerenderingprogress.png or use its
        disappearance as a completion signal.
        """
        expected_count = max(1, int(expected_count))
        _get_flow_yolo_model()
        scan_started = time.monotonic()
        last_status = scan_started
        scan_cycle = 0

        while True:
            check_for_termination()
            enforce_window_focus(hwnd)
            scan_cycle += 1
            _reset_google_flow_gallery_to_top()
            cards = []
            page_count = 0

            for page_index in range(FLOW_CARD_SCAN_MAX_PAGES):
                check_for_termination()
                enforce_window_focus(hwnd)
                frame = _capture_google_flow_frame()
                page_boxes = _detect_google_flow_image_cards(frame)
                page_cards = []
                ignored_existing = 0
                for box in page_boxes:
                    fingerprint = _flow_card_perceptual_hash(frame, box)
                    if _fingerprint_matches_baseline(
                        fingerprint, baseline_fingerprints
                    ):
                        ignored_existing += 1
                        continue
                    confirmed, objects = _yolo_confirms_flow_card(frame, box)
                    page_cards.append({
                        "box": tuple(box),
                        "fingerprint": fingerprint,
                        "yolo_confirmed": bool(confirmed),
                        "objects": objects,
                        "frame_size": (int(frame.shape[1]), int(frame.shape[0]))
                    })
                page_count += 1
                print(
                    f"🔎 [CV-CARDS] Scan {scan_cycle}, viewport {page_index + 1}: "
                    f"OpenCV found {len(page_boxes)} rectangle candidate(s), "
                    f"YOLO-checked {len(page_cards)} new card(s), "
                    f"ignored {ignored_existing} pre-existing card(s)."
                )

                for candidate in page_cards:
                    duplicate_index = next(
                        (
                            index for index, previous in enumerate(cards)
                            if _same_flow_card(candidate, previous)
                        ),
                        None
                    )
                    if duplicate_index is not None:
                        previous = cards[duplicate_index]
                        # Use the strongest/fullest observation of the same card.
                        if candidate.get("yolo_confirmed") and not previous.get("yolo_confirmed"):
                            cards[duplicate_index] = candidate
                        continue
                    cards.append(candidate)
                    if len(cards) >= expected_count:
                        break

                if len(cards) >= expected_count:
                    break
                _scroll_google_flow_gallery(-FLOW_CARD_SCROLL_NOTCHES)

            if len(cards) >= expected_count:
                selected = cards[:expected_count]
                unconfirmed = [
                    index + 1 for index, card in enumerate(selected)
                    if not card.get("yolo_confirmed")
                ]
                print(
                    f"📊 [CV-CARDS] Found {len(selected)}/{expected_count} newest card slot(s) "
                    f"across {page_count} viewport snapshot(s)."
                )
                for index, card in enumerate(selected, start=1):
                    object_summary = ", ".join(
                        f"{item['label']}:{item['confidence']}"
                        for item in card.get("objects", [])
                    ) or "no identifiable object yet"
                    x, y, width, height = card["box"]
                    print(
                        f"   • Slot {index}: box=({x},{y},{width},{height}); "
                        f"YOLO={'confirmed' if card.get('yolo_confirmed') else 'pending'}; "
                        f"objects={object_summary}"
                    )

                if not unconfirmed:
                    # Return to the newest cards so the download sequence begins
                    # from the first/top-left card, not the last scanned viewport.
                    _reset_google_flow_gallery_to_top()
                    print(
                        f"✅ [CV-CARDS] All {expected_count} expected image card(s) "
                        "were detected by OpenCV and confirmed by YOLO."
                    )
                    return selected

                print(
                    "⏳ [CV-CARDS] Rectangle slots are present, but YOLO has not "
                    "identified objects in card slot(s): "
                    + ", ".join(str(number) for number in unconfirmed)
                    + ". Waiting and rescanning; no card will be downloaded yet."
                )
            else:
                print(
                    f"⏳ [CV-CARDS] Only {len(cards)}/{expected_count} unique image-card "
                    f"rectangle(s) found after {page_count} viewport snapshot(s). "
                    "Waiting for more cards to appear."
                )

            now = time.monotonic()
            if now - last_status >= 8:
                elapsed = int(now - scan_started)
                update_operation_status(
                    f"OpenCV/YOLO image verification: {len(cards)}/{expected_count} "
                    f"cards detected; waiting for identifiable objects ({elapsed}s)"
                )
                try:
                    hud.print(
                        f"Checking generated images with YOLO... {len(cards)}/{expected_count}",
                        "processing"
                    )
                except Exception:
                    pass
                last_status = now
            _sleep(1.0)

    def _locate_yolo_card_for_download(
        hwnd, target_fingerprint, target_objects=None, max_scroll_pages=18
    ):
        """Find a previously validated card in the current gallery viewport."""
        if target_fingerprint is None:
            raise _BatchTrackingFailure("A validated card has no perceptual fingerprint")

        screen_width, screen_height = pyautogui.size()
        # Every download can leave the gallery at a different scroll offset.
        # Reset before searching so an earlier target is not skipped merely
        # because the previous card was found farther down the page.
        _reset_google_flow_gallery_to_top()
        # Move away from the image grid so hover controls do not contaminate its hash.
        pyautogui.moveTo(190, max(35, min(70, screen_height - 1)), duration=0.04)

        for page_index in range(max_scroll_pages):
            check_for_termination()
            enforce_window_focus(hwnd)
            frame, visible_cards = _capture_yolo_card_candidates()
            best_match = None
            best_distance = 65
            for candidate in visible_cards:
                distance = _flow_hash_distance(
                    target_fingerprint, candidate.get("fingerprint")
                )
                if distance < best_distance:
                    best_distance = distance
                    best_match = candidate

            if best_match is not None and best_distance <= 14:
                expected_labels = {
                    str(item.get("label", "")).strip().lower()
                    for item in (target_objects or [])
                    if str(item.get("label", "")).strip()
                }
                current_labels = {
                    str(item.get("label", "")).strip().lower()
                    for item in best_match.get("objects", [])
                    if str(item.get("label", "")).strip()
                }
                if expected_labels and current_labels and not expected_labels.intersection(current_labels):
                    best_match = None
                elif not best_match.get("yolo_confirmed"):
                    print(
                        f"⚠️ [CV-CARDS] Matching card hash found (distance={best_distance}), "
                        "but YOLO did not confirm its object content; rescanning."
                    )
                else:
                    x, y, width, height = best_match["box"]
                    print(
                        f"✅ [CV-CARDS] Re-identified target card at "
                        f"({x},{y},{width},{height}); pHash distance={best_distance}; "
                        f"objects={best_match.get('objects', [])}"
                    )
                    return tuple(best_match["box"])

            if page_index < max_scroll_pages - 1:
                _scroll_google_flow_gallery(-FLOW_CARD_SCROLL_NOTCHES)

        raise _BatchTrackingFailure(
            "Could not re-identify a YOLO-confirmed image card in the visible gallery "
            "before its download. The workflow stopped rather than hovering an "
            "unverified or incorrect card."
        )

    def _render_position_alignment_cost(previous_jobs, old_indices, current_centers, current_indices):
        """Score one order-preserving mapping while tolerating a common UI reflow."""
        shifts = []
        for old_index, current_index in zip(old_indices, current_indices):
            old_x, old_y = previous_jobs[old_index]["center"]
            new_x, new_y = current_centers[current_index]
            shifts.append((new_x - old_x, new_y - old_y))

        if shifts:
            median_dx = sorted(item[0] for item in shifts)[len(shifts) // 2]
            median_dy = sorted(item[1] for item in shifts)[len(shifts) // 2]
            residual = sum(
                abs(dx - median_dx) + abs(dy - median_dy)
                for dx, dy in shifts
            )
            # A small motion penalty breaks ties without rejecting a coherent
            # large shift caused by the cards being repositioned after a send.
            cost = residual + 0.035 * (abs(median_dx) + abs(median_dy))
            return cost, (median_dx, median_dy)
        return 0.0, (0, 0)

    unowned_render_marker_serial = 0

    def _make_unowned_render_job(center, reason="pre-existing/ambiguous marker"):
        """Track an unowned marker only for reflow alignment; it is never downloadable."""
        nonlocal unowned_render_marker_serial
        unowned_render_marker_serial += 1
        return {
            "entry_name": f"__unowned_render_{unowned_render_marker_serial}",
            "entry_index": None,
            "center": (int(center[0]), int(center[1])),
            "state": "unowned",
            "unowned_reason": reason,
        }

    def _reconcile_render_positions(previous_jobs, current_centers, newly_submitted=None):
        """
        Reconcile card positions using only snapshots taken AFTER prompts are sent.

        Previous tracked markers are aligned to their new positions after Google
        Flow reflows the cards. The one marker nearest the just-used send control
        is assigned to the newly submitted entry. Any additional first-seen
        markers are retained as unowned alignment anchors and are never downloaded.
        """
        previous = sorted(
            [dict(job) for job in previous_jobs],
            key=lambda job: (job["center"][1], job["center"][0])
        )
        current = sorted(
            [(int(point[0]), int(point[1])) for point in current_centers],
            key=lambda point: (point[1], point[0])
        )

        if newly_submitted is not None:
            if not current:
                return previous, [], None

            # Reserve one current marker for the newly sent entry; align as many
            # previously tracked markers as the remaining current set allows.
            old_match_count = min(len(previous), max(0, len(current) - 1))
            best = None
            for old_indices in itertools.combinations(range(len(previous)), old_match_count):
                for current_indices in itertools.combinations(range(len(current)), old_match_count):
                    cost, shift = _render_position_alignment_cost(
                        previous, old_indices, current, current_indices
                    )
                    if best is None or cost < best[0]:
                        best = (cost, old_indices, current_indices, shift)

            if best is None:
                matched_old_indices = ()
                matched_current_indices = ()
                shift = (0, 0)
            else:
                _, matched_old_indices, matched_current_indices, shift = best

            old_to_current = dict(zip(matched_old_indices, matched_current_indices))
            current_used = set(matched_current_indices)
            unmatched_current_indices = [
                index for index in range(len(current)) if index not in current_used
            ]
            if not unmatched_current_indices:
                raise _BatchTrackingFailure(
                    f"Could not isolate a post-send render marker for "
                    f"{newly_submitted['entry_name']}."
                )

            send_center = newly_submitted.get("send_center")
            if send_center is not None:
                send_x, send_y = int(send_center[0]), int(send_center[1])
                new_index = min(
                    unmatched_current_indices,
                    key=lambda index: (
                        (current[index][0] - send_x) ** 2
                        + (current[index][1] - send_y) ** 2
                    )
                )
            else:
                # Fallback: use the lowest unmatched marker in visual order.
                new_index = unmatched_current_indices[-1]

            active = []
            completed = []
            for old_index, job in enumerate(previous):
                if old_index in old_to_current:
                    updated = dict(job)
                    updated["center"] = current[old_to_current[old_index]]
                    updated["state"] = job.get("state", "rendering")
                    active.append(updated)
                else:
                    finished = dict(job)
                    finished["center"] = (
                        int(job["center"][0] + shift[0]),
                        int(job["center"][1] + shift[1])
                    )
                    finished["state"] = "render_complete"
                    completed.append(finished)

            new_job = dict(newly_submitted)
            new_job.pop("send_center", None)
            new_job["center"] = current[new_index]
            new_job["state"] = "rendering"
            active.append(new_job)

            # Extra matches on the first post-send scan may belong to an older
            # Flow card. Keep them in the alignment set, but never queue a download.
            for index in unmatched_current_indices:
                if index == new_index:
                    continue
                foreign = _make_unowned_render_job(
                    current[index],
                    reason="additional marker first observed after a send"
                )
                active.append(foreign)
                print(
                    f"ℹ️ [BATCH-TRACK] Keeping {foreign['entry_name']} at "
                    f"({foreign['center'][0]}, {foreign['center'][1]}) as an "
                    "unowned alignment marker; it will never be downloaded."
                )

            active.sort(key=lambda job: (job["center"][1], job["center"][0]))
            completed.sort(key=lambda job: (job["center"][1], job["center"][0]))
            return active, completed, new_job["center"]

        # Monitoring phase. Match every old marker that remains visible. A newly
        # appearing unmatched marker is treated as unowned rather than guessed to
        # be one of the six submitted scene entries.
        if len(current) >= len(previous):
            match_count = len(previous)
        else:
            match_count = len(current)

        best = None
        for old_indices in itertools.combinations(range(len(previous)), match_count):
            for current_indices in itertools.combinations(range(len(current)), match_count):
                cost, shift = _render_position_alignment_cost(
                    previous, old_indices, current, current_indices
                )
                if best is None or cost < best[0]:
                    best = (cost, old_indices, current_indices, shift)

        if best is None:
            matched_old_indices = ()
            matched_current_indices = ()
            shift = (0, 0)
        else:
            _, matched_old_indices, matched_current_indices, shift = best

        old_to_current = dict(zip(matched_old_indices, matched_current_indices))
        current_used = set(matched_current_indices)
        active = []
        completed = []

        for old_index, job in enumerate(previous):
            if old_index in old_to_current:
                updated = dict(job)
                updated["center"] = current[old_to_current[old_index]]
                active.append(updated)
            else:
                finished = dict(job)
                finished["center"] = (
                    int(job["center"][0] + shift[0]),
                    int(job["center"][1] + shift[1])
                )
                finished["state"] = "render_complete"
                completed.append(finished)

        for index, center in enumerate(current):
            if index not in current_used:
                foreign = _make_unowned_render_job(
                    center,
                    reason="additional marker appeared during monitoring"
                )
                active.append(foreign)
                print(
                    f"ℹ️ [BATCH-TRACK] New unowned marker {foreign['entry_name']} "
                    f"at ({center[0]}, {center[1]}); tracking only for card alignment."
                )

        active.sort(key=lambda job: (job["center"][1], job["center"][0]))
        completed.sort(key=lambda job: (job["center"][1], job["center"][0]))
        return active, completed, None

    def _apply_common_reflow_shift(previous_active, current_active, completed_queue):
        """Move already-completed cards with the common shift of surviving cards."""
        if not completed_queue or not previous_active or not current_active:
            return
        old_by_name = {job["entry_name"]: job["center"] for job in previous_active}
        shifts = []
        for job in current_active:
            old_center = old_by_name.get(job["entry_name"])
            if old_center is None:
                continue
            shifts.append((job["center"][0] - old_center[0], job["center"][1] - old_center[1]))
        if not shifts:
            return
        median_dx = sorted(item[0] for item in shifts)[len(shifts) // 2]
        median_dy = sorted(item[1] for item in shifts)[len(shifts) // 2]
        if median_dx == 0 and median_dy == 0:
            return
        for completed in completed_queue:
            completed["center"] = (
                int(completed["center"][0] + median_dx),
                int(completed["center"][1] + median_dy)
            )
        print(
            f"🧭 [BATCH-TRACK] Repositioned {len(completed_queue)} completed-card anchor(s) "
            f"by common UI shift ({median_dx:+d}, {median_dy:+d})."
        )

    def _order_render_centers_latest_first(current_centers, row_tolerance=58):
        """Order visible render cards as newest-first: rows top-to-bottom, each row left-to-right."""
        points = sorted(
            {(int(point[0]), int(point[1])) for point in current_centers},
            key=lambda point: (point[1], point[0])
        )
        rows = []
        for point in points:
            selected_row = None
            selected_distance = None
            for row in rows:
                row_y = sum(item[1] for item in row) / len(row)
                distance = abs(point[1] - row_y)
                if distance <= row_tolerance and (
                    selected_distance is None or distance < selected_distance
                ):
                    selected_row = row
                    selected_distance = distance
            if selected_row is None:
                rows.append([point])
            else:
                selected_row.append(point)

        rows.sort(key=lambda row: sum(item[1] for item in row) / len(row))
        ordered = []
        for row in rows:
            ordered.extend(sorted(row, key=lambda point: point[0]))
        return ordered

    def _cluster_axis_values(values, tolerance=55):
        """Collapse small coordinate variations into stable visual grid columns/rows."""
        groups = []
        for value in sorted(int(value) for value in values):
            if not groups or abs(value - (sum(groups[-1]) / len(groups[-1]))) > tolerance:
                groups.append([value])
            else:
                groups[-1].append(value)
        return [int(round(sum(group) / len(group))) for group in groups]

    def _estimate_batch_card_slot_center(ordered_centers, slot_index):
        """Estimate a missing tail card slot using the observed card-grid pitch."""
        if not ordered_centers:
            raise _BatchTrackingFailure(
                "Cannot estimate a completed card position because no render-card anchor was found."
            )
        if 0 <= slot_index < len(ordered_centers):
            return tuple(ordered_centers[slot_index])

        screen_width, screen_height = pyautogui.size()
        fallback_pitch_x = max(180.0, screen_width * 0.283)
        fallback_pitch_y = max(140.0, screen_height * 0.290)

        x_values = _cluster_axis_values([point[0] for point in ordered_centers])
        y_values = _cluster_axis_values([point[1] for point in ordered_centers])

        def _pitch_from_axis(axis_values, fallback):
            differences = [
                float(b - a) for a, b in zip(axis_values, axis_values[1:])
                if b - a >= 80
            ]
            if not differences:
                return fallback
            # A missing middle column/row can make an observed gap span two cells.
            normalized = []
            for difference in differences:
                multiplier = max(1, int(round(difference / fallback)))
                normalized.append(difference / multiplier)
            normalized.sort()
            return normalized[len(normalized) // 2]

        pitch_x = _pitch_from_axis(x_values, fallback_pitch_x)
        pitch_y = _pitch_from_axis(y_values, fallback_pitch_y)
        origin_x, origin_y = ordered_centers[0]
        column_count = 3
        row_index, column_index = divmod(int(slot_index), column_count)
        estimated = (
            int(round(origin_x + column_index * pitch_x)),
            int(round(origin_y + row_index * pitch_y))
        )
        print(
            f"🧭 [BATCH-GRID] Estimated missing card slot {slot_index + 1} at "
            f"({estimated[0]}, {estimated[1]}) using grid pitch "
            f"({pitch_x:.1f}, {pitch_y:.1f})."
        )
        return estimated

    def _bootstrap_batch_render_jobs(submitted_jobs, current_centers):
        """Map one post-submission screen snapshot to the submitted batch."""
        ordered_centers = _order_render_centers_latest_first(current_centers)
        if not ordered_centers:
            raise _BatchTrackingFailure(
                "All prompts were submitted, but no imagerenderingprogress.png markers "
                "were visible in the combined snapshot. There is no safe card anchor "
                "for downloading an already-completed image."
            )

        latest_first_jobs = list(reversed(submitted_jobs))
        visible_owned_count = min(len(latest_first_jobs), len(ordered_centers))
        active = []
        completed = []

        print(
            f"🔎 [BATCH-SNAPSHOT] Combined snapshot found {len(ordered_centers)} "
            f"render marker(s) for {len(submitted_jobs)} submitted scene(s)."
        )
        print(
            "🧭 [BATCH-SNAPSHOT] Assigning markers newest-first: the latest submitted "
            "entry maps to the first/top-left marker, then older entries map rightward "
            "and downward in row-major order."
        )

        for slot_index, job in enumerate(latest_first_jobs):
            assigned = dict(job)
            if slot_index < visible_owned_count:
                assigned["center"] = tuple(ordered_centers[slot_index])
                assigned["state"] = "rendering"
                active.append(assigned)
                print(
                    f"✅ [BATCH-SNAPSHOT] {assigned['entry_name']} -> "
                    f"({assigned['center'][0]}, {assigned['center'][1]}) [rendering]"
                )
            else:
                # Under the documented Flow ordering, the oldest submitted
                # cards occupy the tail/right/bottom slots. If their progress
                # marker is already gone in this first snapshot, they are ready.
                assigned["center"] = _estimate_batch_card_slot_center(
                    ordered_centers, slot_index
                )
                assigned["state"] = "render_complete"
                completed.append(assigned)
                print(
                    f"🎉 [BATCH-SNAPSHOT] {assigned['entry_name']} has no remaining "
                    f"render marker; treating its older tail slot as complete at "
                    f"({assigned['center'][0]}, {assigned['center'][1]})."
                )

        # Extra markers are older cards outside this six-entry batch. Retain them
        # as alignment anchors so subsequent reflows do not corrupt scene mapping.
        for center in ordered_centers[len(latest_first_jobs):]:
            foreign = _make_unowned_render_job(
                center,
                reason="older render marker outside the current submitted batch"
            )
            active.append(foreign)
            print(
                f"ℹ️ [BATCH-SNAPSHOT] Keeping {foreign['entry_name']} at "
                f"({foreign['center'][0]}, {foreign['center'][1]}) as an unowned "
                "older-card alignment anchor."
            )

        active.sort(key=lambda job: (job["center"][1], job["center"][0]))
        completed.sort(key=lambda job: (job["center"][1], job["center"][0]))
        return active, completed

    def _submit_scene_entry_to_batch(hwnd, entry_index):
        """Submit one prompt only; never scan render indicators or lock a card position here."""
        entry_name = f"entry_{entry_index + 1}"
        entry_json = format_entry_for_paste(all_entries[entry_index])
        if not entry_json:
            raise _WorkflowRestart(f"No valid prompt data found for {entry_name}")

        print(
            f"\n📝 [BATCH-SEND] Submitting {entry_name} consecutively. "
            "Rendering-progress lookup and card-position tracking are deferred "
            "until the entire batch has been sent."
        )
        check_for_termination()
        send_coords = paste_prompt_and_click_send_batch(hwnd, entry_json, entry_name)
        if send_coords is None:
            raise _WorkflowRestart(f"Could not paste or submit {entry_name}")

        job = {
            "entry_name": entry_name,
            "entry_index": entry_index,
            "center": None,
            "send_center": send_coords,
            "state": "sent"
        }
        print(
            f"✅ [BATCH-SEND] {entry_name} sent. No rendering-image search, "
            "position verification, or location lock was performed."
        )
        return job

    def _download_completed_scene_job(hwnd, job, images_folder):
        """Download one card only after its current position is re-confirmed by CV + YOLO."""
        entry_name = job["entry_name"]
        target_fingerprint = job.get("card_fingerprint")
        if target_fingerprint is None:
            raise _BatchTrackingFailure(
                f"{entry_name} has no verified image-card fingerprint; refusing to download."
            )

        card_box = _locate_yolo_card_for_download(
            hwnd,
            target_fingerprint,
            target_objects=job.get("card_objects")
        )
        print(
            f"\n📥 [BATCH-DOWNLOAD] {entry_name}: moving to the centre of its "
            f"re-identified image card at {card_box}."
        )
        download_success = download_google_flow_image(
            hwnd,
            entry_name,
            images_folder,
            force_png=False,
            known_card_box=card_box
        )
        if not download_success:
            raise _BatchTrackingFailure(
                f"Download failed for {entry_name}; stopping the batch rather than "
                "resubmitting prompts or selecting another card."
            )

        verified_path = _find_entry_image(
            images_folder, int(job["entry_index"]) + 1
        )
        if not verified_path:
            raise _BatchTrackingFailure(
                f"{entry_name} download reported success but its destination image "
                "is missing or invalid."
            )

        # The download watcher services the confirmation modal. Check once more
        # after the file has been verified before advancing to the next card.
        handle_webdownloadconfirmationmodal()
        pyautogui.moveTo(190, 55, duration=0.05)
        _sleep(0.35)
        print(
            f"✅ [BATCH-DOWNLOAD] {entry_name} saved and verified: {verified_path}. "
            "Proceeding to the next YOLO-confirmed card."
        )
        update_operation_status(f"{entry_name} downloaded and verified")
        return verified_path

    def process_scene_entries_in_batches(hwnd, missing_entry_numbers, images_folder, batch_size=6):
        """
        Submit prompts consecutively in batches of up to six, then detect the
        generated media cards with OpenCV and verify their contents with YOLO.

        The gallery is assumed to show newest first: the newest prompt maps to
        the first/top-left card, then older prompts proceed rightward and downward.
        No image-rendering-progress indicator is used to count or declare a scene
        complete. All expected card slots must be YOLO-confirmed before downloads
        begin. Each card is re-identified by perceptual hash immediately before
        its own hover/download sequence.
        """
        batch_size = max(1, min(6, int(batch_size)))
        entry_numbers = [int(number) for number in missing_entry_numbers]
        if not entry_numbers:
            return True

        batch_number = 0
        for batch_start in range(0, len(entry_numbers), batch_size):
            check_for_termination()
            batch_number += 1
            batch_label = str(batch_number)
            batch_numbers = entry_numbers[batch_start:batch_start + batch_size]
            print(
                f"\n{'=' * 64}\n"
                f"🚀 [BATCH] Starting CV/YOLO batch {batch_label}: "
                f"{batch_numbers} (maximum {batch_size} prompts)\n"
                f"{'=' * 64}"
            )
            print(
                "⚡ [BATCH] All prompts will be submitted consecutively. "
                "No render-marker scans, card locks, or downloads will run "
                "between prompt submissions."
            )

            # Establish a before-send identity baseline. Old cards remain valid
            # images and may contain YOLO-recognized people/objects, so rectangle
            # count + YOLO alone is not sufficient to prove they belong to this batch.
            baseline_fingerprints = _capture_preexisting_flow_card_fingerprints(hwnd)

            submitted_jobs = []
            for entry_number in batch_numbers:
                check_for_termination()
                entry_name = f"entry_{entry_number}"
                if _find_entry_image(images_folder, entry_number):
                    print(
                        f"⏭️ [BATCH] {entry_name} already has a valid local image; "
                        "skipping prompt submission."
                    )
                    continue

                job = _submit_scene_entry_to_batch(hwnd, entry_number - 1)
                submitted_jobs.append(job)
                update_operation_status(
                    f"Batch {batch_label}: submitted {len(submitted_jobs)}/"
                    f"{len(batch_numbers)} prompts consecutively; CV/YOLO scan "
                    "will start after the final prompt."
                )
                try:
                    hud.print(
                        f"Batch {batch_label}: sent {len(submitted_jobs)}/"
                        f"{len(batch_numbers)} prompts",
                        "processing"
                    )
                except Exception:
                    pass

            if not submitted_jobs:
                print(f"ℹ️ [BATCH] No new prompts needed in batch {batch_label}.")
                continue

            expected_count = len(submitted_jobs)
            print(
                f"✅ [BATCH] All {expected_count} prompt(s) have been submitted. "
                "Starting the combined OpenCV rectangle scan and YOLO object check."
            )
            update_operation_status(
                f"Batch {batch_label}: locating and validating {expected_count} "
                "generated image card(s) with OpenCV + YOLO"
            )
            try:
                hud.print(
                    f"Detecting {expected_count} generated images with OpenCV + YOLO...",
                    "processing"
                )
            except Exception:
                pass

            detected_cards = _wait_for_yolo_confirmed_flow_cards(
                hwnd,
                expected_count=expected_count,
                baseline_fingerprints=baseline_fingerprints
            )
            if len(detected_cards) != expected_count:
                raise _BatchTrackingFailure(
                    f"CV/YOLO returned {len(detected_cards)} card(s), expected "
                    f"{expected_count}; no downloads were started."
                )

            # Google Flow displays the newest card first. Therefore the last
            # prompt submitted is paired with detected card 1, and so forth.
            newest_first_jobs = list(reversed(submitted_jobs))
            for card_order, (job, card) in enumerate(
                zip(newest_first_jobs, detected_cards), start=1
            ):
                check_for_termination()
                job = dict(job)
                job["card_fingerprint"] = card.get("fingerprint")
                job["card_objects"] = list(card.get("objects", []))
                job["card_order"] = card_order
                job["state"] = "yolo_confirmed"
                object_names = ", ".join(
                    item["label"] for item in card.get("objects", [])
                ) or "identified object"
                print(
                    f"🧭 [BATCH-MAP] Latest-first gallery card {card_order} -> "
                    f"{job['entry_name']} (YOLO objects: {object_names})."
                )

                _download_completed_scene_job(hwnd, job, images_folder)
                update_operation_status(
                    f"Batch {batch_label}: downloaded {card_order}/{expected_count} "
                    "YOLO-confirmed cards"
                )

            missing_batch_files = [
                f"entry_{number}"
                for number in batch_numbers
                if _find_entry_image(images_folder, number) is None
            ]
            if missing_batch_files:
                raise _BatchTrackingFailure(
                    f"Batch {batch_label} finished without verified files for: "
                    + ", ".join(missing_batch_files)
                )

            print(
                f"🏁 [BATCH] Batch {batch_label} complete: all {expected_count} "
                "image card(s) were OpenCV-detected, YOLO-confirmed, downloaded, "
                "and verified on disk."
            )
            update_operation_status(
                f"Batch {batch_label} complete: {expected_count} CV/YOLO-verified "
                "scene images downloaded"
            )

        return True

    def process_thumbnail_gf(hwnd, thumbnail_prompt, images_folder):
        """Generate the single project-level thumbnail after all scene images."""
        print("\n🖼️ [THUMBNAIL] All scene images are verified. Preparing the YouTube thumbnail.")
        update_operation_status("All scene images are complete; generating Thumbnail.png...")
        try:
            hud.print("Generating the YouTube thumbnail...", "processing")
        except Exception:
            pass

        return process_prompt_job_gf(
            hwnd=hwnd,
            job_name="Thumbnail",
            prompt_text=thumbnail_prompt.strip(),
            images_folder=images_folder,
            success_message="YouTube thumbnail generated and saved as Thumbnail.png",
            force_png=True
        )

    def main_google_flow_workflow(force_url_restart=False):
        try:
            if not os.path.exists(GUI_IMAGES):
                print(f"❌ Error: GUI_IMAGES path not found: {GUI_IMAGES}")
                try:
                    hud.print("A required folder is missing.", "error")
                except Exception:
                    pass
                update_operation_status(f"GUI_IMAGES path not found: {GUI_IMAGES}", is_error=True)
                return

            images_folder = _sceneiq_resolve_project_images_folder(
                project_title,
                project_category=project_category,
            )
            print(f"🎬 [MAIN] Starting Google Flow image generation workflow...")
            print(f"🖥️ [MAIN] GUI Images path: {GUI_IMAGES}")
            print(f"📁 [MAIN] Project: '{project_title}'")
            print(f"📁 [MAIN] Images folder: {images_folder}")
            print(f"📊 [MAIN] Total entries: {total_entries}")

            try:
                hud.print(f"Preparing to generate {total_entries} images...", "initializing")
            except Exception:
                pass

            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized; inspecting the current Edge page before navigation")

            # IMPORTANT: on every automatic/manual restart, search in this exact
            # order before navigating: (1) whatdoyouwantocreate, (2) new_project,
            # (3) GOOGLE_FLOW_URL if neither is visible. This prevents a restart
            # from opening a second project when the prompt workspace is ready.
            print("🔎 [MAIN] Inspecting the current Edge page before loading any URL...")
            try:
                hud.print("Checking the current Google Flow page...", "waiting")
            except Exception:
                pass

            if force_url_restart:
                print("🌐 [MAIN] Ctrl+Shift+F12 requested a hard restart; opening GOOGLE_FLOW_URL immediately without inspecting the current page.")
                try:
                    hud.print("Restarting from Google Flow URL...", "navigating")
                except Exception:
                    pass
                if not GOOGLE_FLOW_URL:
                    update_operation_status("GOOGLE_FLOW_URL is empty; cannot perform Ctrl+Shift+F12 restart", is_error=True)
                    return
                fast_paste_url(hwnd, GOOGLE_FLOW_URL)
                _sleep(2)
                hwnd = ensure_window_ready_and_focused()
                current_stage, current_location = wait_for_google_flow_stage(
                    hwnd, timeout_seconds=PAGE_NAVIGATION_TIMEOUT_SECONDS, check_interval=0.5
                )
                print(f"🧭 [MAIN] Page state after forced URL navigation: {current_stage}")
            else:
                current_stage, current_location = detect_restart_page_stage(hwnd)
            print(
                f"🧭 [MAIN] Initial restart page state (prompt checked before New Project): "
                f"{current_stage}"
            )

            if current_stage == "prompt":
                print(
                    "✅ [MAIN] whatdoyouwantocreate.png is already visible. "
                    "Skipping URL navigation and New Project; starting the scene workflow from its entry point." 
                )
                update_operation_status("Existing prompt workspace detected; starting the scene workflow from its entry point")
                page_ready = True

            elif current_stage == "new_project":
                print(
                    "✅ [MAIN] new_project.png is already visible. "
                    "Skipping URL navigation and clicking the existing New Project control."
                )
                clicked = wait_for_new_project_and_click(
                    hwnd, timeout_seconds=20, initial_location=current_location
                )
                if not clicked:
                    update_operation_status("Could not click the detected New Project button", is_error=True)
                    return
                page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

            elif current_stage == "collapsed_workspace":
                print(
                    "✅ [MAIN] An existing Google Flow workspace is detected with its side panel collapsed. "
                    "Skipping URL navigation and expanding the existing workspace."
                )
                if not _click_google_flow_control(hwnd, current_location, "expandgfsidepanel.png"):
                    update_operation_status("Could not expand the existing Google Flow prompt panel", is_error=True)
                    return
                page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

            elif current_stage == "flow_loading":
                print(
                    "✅ [MAIN] Google Flow shell is already present. Staying on the current page "
                    "and waiting for prompt/project controls instead of navigating again."
                )
                detected_stage, detected_location = wait_for_google_flow_stage(
                    hwnd, timeout_seconds=PAGE_NAVIGATION_TIMEOUT_SECONDS, check_interval=0.5
                )
                if detected_stage == "prompt":
                    page_ready = True
                elif detected_stage == "new_project":
                    clicked = wait_for_new_project_and_click(
                        hwnd, timeout_seconds=20, initial_location=detected_location
                    )
                    page_ready = clicked and wait_for_prompt_workspace(
                        hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS
                    )
                else:
                    page_ready = False

            else:
                if force_url_restart:
                    page_ready = False
                else:
                    print(
                        "🌐 [MAIN] Neither the prompt workspace nor New Project is visible. "
                        "Only now will GOOGLE_FLOW_URL be opened."
                    )
                    try:
                        hud.print("Opening Google Flow because no known page is visible...", "navigating")
                    except Exception:
                        pass
                    update_operation_status("No known Google Flow page detected; opening Google Flow URL")
                    fast_paste_url(hwnd, GOOGLE_FLOW_URL)
                    _sleep(2)
                    hwnd = ensure_window_ready_and_focused()

                    detected_stage, detected_location = wait_for_google_flow_stage(
                        hwnd, timeout_seconds=PAGE_NAVIGATION_TIMEOUT_SECONDS, check_interval=0.5
                    )
                    print(f"🧭 [MAIN] Page state after navigation: {detected_stage}")

                    if detected_stage == "prompt":
                        print("✅ [MAIN] Prompt workspace detected after navigation; no New Project click needed.")
                        page_ready = True

                    elif detected_stage == "new_project":
                        print("✅ [MAIN] New Project chooser detected after navigation; clicking it now.")
                        clicked = wait_for_new_project_and_click(
                            hwnd, timeout_seconds=20, initial_location=detected_location
                        )
                        if not clicked:
                            update_operation_status("Could not click New Project after navigation", is_error=True)
                            return
                        page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

                    else:
                        page_ready = False

            if not page_ready:
                error_message = (
                    "Google Flow did not reach the whatdoyouwantocreate prompt workspace. "
                    "The supervisor will restart and inspect the current page before deciding whether to navigate."
                )
                print(f"❌ [MAIN] {error_message}")
                try:
                    hud.print("The prompt workspace was not detected. Retrying page detection...", "error")
                except Exception:
                    pass
                update_operation_status(error_message, is_error=True)
                return

            # Re-run the Serenum two-step Nano Banana setup on EVERY full workflow
            # attempt, but only after the Google Flow workspace is positively
            # confirmed as loaded and BEFORE project-folder validation or entries.
            # This intentionally runs again after Ctrl+Shift+F12 and auto-recovery.
            print(
                "🟦 [NANO-BANANA] Google Flow page is confirmed loaded. "
                "Running setup for this workflow attempt: "
                "nanobananaconfig.png → nanobanana_16ratio9.png → "
                "oneimageperprompt.png → nanobananaconfig.png (close)."
            )
            configure_startup_nanobanana_16ratio9(hwnd)
            print(
                "✅ [NANO-BANANA] Configuration, 16:9 ratio, one image per prompt, "
                "and modal closure confirmed. Continuing to project validation."
            )

            # Project-folder validation and scene-entry inspection happen only
            # AFTER this attempt's Nano Banana configuration is complete.
            valid, missing_entries = validate_entry_order(images_folder, total_entries)
            if not valid:
                print("❌ [MAIN] Project image-folder validation failed")
                return

            # The thumbnail prompt is a project-level field in the JSON, outside
            # the timed script entries. It is only submitted after every entry_N
            # image has been verified.
            latest_panel = _load_panel()
            thumbnail_value = _find_field(latest_panel, ("Thumbnail",))
            thumbnail_prompt = (
                thumbnail_value.strip()
                if isinstance(thumbnail_value, str)
                else ""
            )
            thumbnail_already_exists = _thumbnail_exists(images_folder)
            print(f"📊 [MAIN] Missing scene entries: {missing_entries}")
            print(
                f"🖼️ [MAIN] Thumbnail status: "
                f"{'already generated' if thumbnail_already_exists else 'not generated yet'}"
            )

            if not missing_entries and thumbnail_already_exists:
                print(
                    f"✅ [MAIN] All {total_entries} scene images and Thumbnail.png "
                    "already exist. Verifying project transfer."
                )
                transferred = _transfer_completed_project_to_ready_script(
                    images_folder, total_entries
                )
                if transferred:
                    _set_currently_running(
                        "sceneiq_google_flow_images_generation_engine_successful",
                        status="completed",
                        operation_status=(
                            f"✅ All {total_entries} scene images and Thumbnail.png "
                            "verified and transferred to ready_script.json"
                        )
                    )
                    print("🏁 [GF] Completed project appended to ready_script.json")
                return

            work_items = len(missing_entries) + (0 if thumbnail_already_exists else 1)
            print(
                f"📊 [MAIN] Work remaining: {len(missing_entries)} missing scene image(s), "
                f"{0 if thumbnail_already_exists else 1} thumbnail."
            )

            print(
                "✅ [MAIN] Google Flow prompt workspace is ready; "
                "processing missing scene entries first and the thumbnail last."
            )
            try:
                hud.print("Everything is ready. Starting now...", "success")
            except Exception:
                pass

            processed_job_this_attempt = False

            def _prepare_for_next_prompt_if_needed():
                nonlocal processed_job_this_attempt
                if not processed_job_this_attempt:
                    return
                download_confirmation_handled = handle_webdownloadconfirmationmodal()
                if not download_confirmation_handled:
                    return

                check_for_termination()
                enforce_window_focus(hwnd)
                print(
                    "🔍 [NEXT-PROMPT] Download confirmation handled. "
                    "Checking for generatinggf_image.png before the next prompt..."
                )
                generating_image_location = find_image(
                    "generatinggf_image.png",
                    confidence=0.7
                )
                if generating_image_location:
                    print(
                        "✅ [NEXT-PROMPT] generatinggf_image.png detected at "
                        f"({generating_image_location.x}, {generating_image_location.y}); "
                        "clicking its right edge."
                    )
                    if click_right_edge_of_image("generatinggf_image.png", confidence=0.7):
                        _sleep(0.5)
                        move_mouse_to_center_of_screen()
                        update_operation_status(
                            "Handled generatinggf_image.png after the previous download"
                        )
                    else:
                        print(
                            "⚠️ [NEXT-PROMPT] Could not click the right edge; "
                            "no centre click will be attempted."
                        )
                else:
                    print("ℹ️ [NEXT-PROMPT] generatinggf_image.png not present.")

            # Submit up to six missing scene entries before starting downloads.
            # Each progress indicator is re-mapped after every submission because
            # Google Flow repositions earlier cards as new scene prompts are added.
            if missing_entries:
                batch_success = process_scene_entries_in_batches(
                    hwnd,
                    missing_entries,
                    images_folder,
                    batch_size=6
                )
                if not batch_success:
                    abort_operation("One or more six-entry scene batches did not complete")
                processed_job_this_attempt = True

            # Final scene-image audit before the thumbnail is allowed to start.
            _cleanup_project_image_folder(images_folder, total_entries)
            missing_after_generation = [
                number
                for number in range(1, total_entries + 1)
                if _find_entry_image(images_folder, number) is None
            ]
            if missing_after_generation:
                abort_operation(
                    "Scene image audit found missing entries: "
                    + ", ".join(f"entry_{number}" for number in missing_after_generation)
                )

            print(
                f"✅ [MAIN] All {total_entries} scene images are present. "
                "The thumbnail phase may now begin."
            )

            # The thumbnail is deliberately generated LAST, and only when the
            # canonical Thumbnail.png is absent or invalid.
            if not _thumbnail_exists(images_folder):
                if not thumbnail_prompt:
                    print(
                        "❌ [THUMBNAIL] All scene images are complete, but panel.json "
                        "has no non-empty 'Thumbnail' prompt. Add the prompt before "
                        "the thumbnail can be generated."
                    )
                    update_operation_status(
                        "Thumbnail prompt is missing or empty; add text to the JSON Thumbnail field",
                        is_error=True
                    )
                    return

                _prepare_for_next_prompt_if_needed()
                thumbnail_success = process_thumbnail_gf(
                    hwnd, thumbnail_prompt, images_folder
                )
                if not thumbnail_success:
                    abort_operation("YouTube thumbnail generation failed")
                processed_job_this_attempt = True
                _sleep(2)
            else:
                print(
                    "⏭️ [THUMBNAIL] Thumbnail.png already exists and is valid; "
                    "skipping thumbnail generation."
                )

            # Strict final folder cleanup and verification before transfer.
            if not _cleanup_project_image_folder(images_folder, total_entries):
                abort_operation("Could not validate the final project image folder")

            missing_after_all = [
                f"entry_{number}"
                for number in range(1, total_entries + 1)
                if _find_entry_image(images_folder, number) is None
            ]
            if not _thumbnail_exists(images_folder):
                missing_after_all.append(THUMBNAIL_FILENAME)

            if missing_after_all:
                abort_operation(
                    "Final image audit failed; missing: " + ", ".join(missing_after_all)
                )

            print(f"\n{'='*60}")
            print(
                f"🎉 [MAIN] All {total_entries} entry images and "
                f"{THUMBNAIL_FILENAME} are generated and verified!"
            )
            print(f"{'='*60}")
            try:
                hud.print("All scene images and the thumbnail are ready.", "success")
            except Exception:
                pass

            transferred = _transfer_completed_project_to_ready_script(
                images_folder, total_entries
            )
            if transferred:
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine_successful",
                    status="completed",
                    operation_status=(
                        f"✅ All {total_entries} entry images plus {THUMBNAIL_FILENAME} "
                        "verified and transferred to ready_script.json"
                    )
                )
                print("🏁 [GF] Completed project appended to ready_script.json")
            else:
                print(
                    "⚠️ [GF] Images are present, but project transfer did not complete."
                )

        except (_WorkflowRestart, _ManualStop):
            set_image_scroll_lock(False)
            raise
        except KeyboardInterrupt as exc:
            raise _ManualStop(str(exc))
        except SystemExit as exc:
            raise _WorkflowRestart(str(exc))
        except Exception as exc:
            print(f"❌ [MAIN] Error: {exc}")
            traceback.print_exc()
            error_message = f"Unexpected error in Google Flow operation: {exc}"
            update_operation_status(error_message, is_error=True)
            try:
                hud.print("Something went wrong. Restarting the workflow...", "warning")
            except Exception:
                pass
            raise _WorkflowRestart(error_message) from exc

    # ------------------------------------------------------------------
    # Full-workflow restart supervisor and global keyboard shortcuts
    # ------------------------------------------------------------------
    # Ctrl+Shift+F12: hard-restart this function by navigating to GOOGLE_FLOW_URL first.
    # Alt+/: stop the function manually.
    # Both shortcuts are registered once and remain active across restarts.
    restart_number = 0
    force_url_restart_pending = False
    restart_hotkey = None
    url_restart_hotkey = None
    stop_hotkey = None

    try:
        url_restart_hotkey = keyboard.add_hotkey("ctrl+shift+f12", on_restart_shortcut, suppress=True)
        print("⌨️ [HOTKEY] Ctrl+Shift+F12 registered: hard restart from GOOGLE_FLOW_URL.")
    except Exception as hotkey_error:
        print(f"⚠️ [HOTKEY] Could not register Ctrl+Shift+F12: {hotkey_error}")

    try:
        stop_hotkey = keyboard.add_hotkey("alt+/", on_terminate_shortcut, suppress=True)
        print("⌨️ [HOTKEY] Alt+/ registered: stop the function manually.")
    except Exception as hotkey_error:
        print(f"⚠️ [HOTKEY] Could not register Alt+/: {hotkey_error}")

    try:
        while True:
            if stop_event.is_set() or terminate_automation:
                print("🛑 [SUPERVISOR] Manual stop requested; exiting the function.")
                break

            if restart_from_url_event.is_set():
                restart_from_url_event.clear()
                force_url_restart_pending = True
                print("🌐 [SUPERVISOR] Ctrl+Shift+F12 received; next attempt will launch GOOGLE_FLOW_URL first.")
            if restart_event.is_set():
                restart_event.clear()
                print("🔁 [SUPERVISOR] Restart request received; rebuilding all run state.")

            restart_number += 1
            operation_status_flag = True
            operation_status_message = ""
            operation_aborted = False

            # Re-read panel.json on every attempt so a restart behaves like a fresh console run.
            try:
                panel_data = _load_panel()
                if not panel_data:
                    raise ValueError("panel.json is empty, missing, or could not be read")
                image_generation_engine = _find_engine(panel_data)
                if image_generation_engine.lower() != "google flow":
                    print(f"ℹ️ [ENGINE] Image generation engine changed to '{image_generation_engine}'; Google Flow worker will stop.")
                    _set_currently_running(
                        None,
                        status="skipped",
                        operation_status=f"Google Flow worker skipped because the selected engine is '{image_generation_engine}'"
                    )
                    break
                project_title = _find_project_title(panel_data)
                script_data = _find_script_data(panel_data)
                all_entries.clear()
                _collect_scene_entries(script_data)
                total_entries = len(all_entries)
            except Exception as reload_error:
                print(f"⚠️ [SUPERVISOR] Could not refresh project configuration: {reload_error}")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Waiting for a readable Google Flow project configuration: {reload_error}"
                )
                _supervisor_wait(3)
                continue

            if total_entries <= 0:
                print("⚠️ [SUPERVISOR] No scene entries found; checking panel.json again in 3 seconds.")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status="No scene entries found yet; waiting and retrying automatically"
                )
                _supervisor_wait(3)
                continue

            print(
                f"\n🔁 [RESTART] Starting Google Flow workflow attempt {restart_number} "
                "from the beginning: reread panel.json, inspect prompt workspace, "
                "then New Project, otherwise navigate to GOOGLE_FLOW_URL; "
                f"project='{project_title}', scenes={total_entries}."
            )
            _set_currently_running(
                "sceneiq_google_flow_images_generation_engine()",
                status="pending",
                operation_status=f"Starting Google Flow workflow attempt {restart_number}"
            )

            try:
                force_this_attempt = force_url_restart_pending
                force_url_restart_pending = False

                main_google_flow_workflow(force_url_restart=force_this_attempt)
            except _WorkflowRestart as restart_reason:
                print(f"🔁 [SUPERVISOR] Restarting from the beginning: {restart_reason}")
                if getattr(restart_reason, "force_url", False):
                    force_url_restart_pending = True
                operation_status_flag = True
                operation_aborted = False
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Automatic restart after: {restart_reason}"
                )
            except _ManualStop as stop_reason:
                print(f"🛑 [SUPERVISOR] {stop_reason}")
                stop_event.set()
                terminate_automation = True
            except _NanoBananaStartupFailure as startup_error:
                print(f"🛑 [SUPERVISOR] Startup setup failed for this workflow attempt: {startup_error}")
                update_operation_status(
                    f"Startup setup failed; scene generation stopped for safety: {startup_error}",
                    is_error=True
                )
                stop_event.set()
                terminate_automation = True
            except _BatchTrackingFailure as batch_error:
                print(f"🛑 [SUPERVISOR] Batch tracking stopped safely: {batch_error}")
                update_operation_status(
                    f"Batch tracking stopped safely to prevent a wrong image download: {batch_error}",
                    is_error=True
                )
                stop_event.set()
                terminate_automation = True
            except Exception as unexpected_error:
                print(f"❌ [SUPERVISOR] Unexpected supervisor error: {unexpected_error}")
                traceback.print_exc()
                operation_status_flag = True
                operation_aborted = False
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Supervisor caught an error and will retry: {unexpected_error}"
                )

            if stop_event.is_set() or terminate_automation:
                break

            if restart_from_url_event.is_set():
                restart_from_url_event.clear()
                force_url_restart_pending = True
                operation_status_flag = True
                operation_aborted = False
                print("🌐 [SUPERVISOR] Ctrl+Shift+F12 arrived between attempts; restarting from GOOGLE_FLOW_URL.")
                continue
            if restart_event.is_set():
                restart_event.clear()
                operation_status_flag = True
                operation_aborted = False
                print("🔁 [SUPERVISOR] Ctrl+Shift+F12 arrived at the end of an attempt; starting a fresh attempt instead of accepting the old result.")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status="Manual Ctrl+Shift+F12 restart requested"
                )
                continue

            final_panel = _load_panel()
            final_running = str(_get_status_value(final_panel, "currently_running", "") or "").strip()
            if final_running == "sceneiq_google_flow_images_generation_engine_successful":
                print("✅ [SUPERVISOR] Workflow completed successfully; no restart is needed.")
                break

            operation_status_flag = True
            operation_aborted = False
            print("🔁 [SUPERVISOR] Workflow is incomplete; the next attempt will re-read panel.json and inspect the current Edge page.")
            try:
                hud.print("The workflow needs recovery. Restarting automatically...", "warning")
            except Exception:
                pass
            _supervisor_wait(2)
    finally:
        for hotkey_handle in (restart_hotkey, url_restart_hotkey, stop_hotkey):
            if hotkey_handle is not None:
                try:
                    keyboard.remove_hotkey(hotkey_handle)
                except Exception:
                    pass

        if stop_event.is_set() or terminate_automation:
            try:
                update_operation_status("Google Flow operation manually stopped by user (Alt+/); work remains resumable")
                hud.show_summary("Stopped at your request.")
            except Exception:
                pass
            print("🛑 [SUPERVISOR] Google Flow function stopped by the user.")

def sceneiq_google_flow_images_generation_engine_single_operation():
    """
    Generates images using Google Flow via GUI automation with pyautogui image recognition.
    Features:
    - Uses GOOGLE_FLOW_URL and GUI_IMAGES path variable
    - Checks panel.json for image_generation_engine == "Google Flow" (case-insensitive)
    - If engine is not Google Flow, function exits immediately
    - Always runs when the selected image engine is Google Flow; no currently_running gate
    - On start sets currently_running to "sceneiq_google_flow_images_generation_engine()"
    - Recognizes only entry_N scene images and the canonical Thumbnail.png;
      deletes unrelated image files from the project image folder
    - Resumes by generating only missing entry_N images, without resetting
      valid later entries when a numbering gap is found
    - Generates Thumbnail.png only after every scene entry image is verified
    - On completion, verifies every scene image plus Thumbnail.png, appends the
      completed project snapshot to READY_SCRIPT, then removes project_name from PANEL_PATH
    - On any error/abort keeps currently_running as "sceneiq_google_flow_images_generation_engine()"
    - Ctrl+Shift+F12 restarts the workflow from its entry point without resuming a scene phase
    - Restart page detection checks whatdoyouwantocreate FIRST, then new_project,
      and navigates to GOOGLE_FLOW_URL only when neither is visible
    - A restart never resumes directly at generation completion or image download
    - Alt+/ is the explicit manual stop shortcut
    - Every image/page/generation/download polling wait is bounded to 40 seconds
    - A single OS/pyautogui call cannot be safely force-killed while it is blocked
    - Failed stages trigger a full automatic restart with fresh panel.json state
    - Before opening Google Flow, detects the current visible page state in Edge
    - Resumes directly from the prompt workspace or New Project chooser when visible
    - Navigates to GOOGLE_FLOW_URL only when neither known page state is visible
    - Re-detects the page state on every automatic or manual restart
    - On every restart checks whatdoyouwantocreate FIRST, then new_project,
      and opens GOOGLE_FLOW_URL only when neither is visible
    - Restart does not reuse saved scene-phase checkpoints
    - Checks for exit_editinggfimage.png regularly throughout every workflow stage
    - Anchors rendering detection to a bounded screen region around the FIRST
      imagerenderingprogress match; unrelated matches elsewhere cannot keep the
      workflow stuck in the rendering state
    - Requires three consecutive misses in that anchored region before declaring
      rendering complete and handing off to download preparation
    - Positions the cursor 50px left and 50px below the original progress match
      before searching for moregf.png
    - Restores the image-hover cursor position before each download retry
    - Throttles download-confirmation modal checks while keeping the two-image
      verification requirement
    - Rechecks rendering only in the anchored region while waiting for moregf
      and returns to render-wait if the indicator genuinely reappears
    - Blocks Windows mouse-wheel scrolling while the image-position lock is active
    - On every confirmed Google Flow prompt workspace, including every automatic,
      shortcut, and fresh-function restart, configures Nano Banana BEFORE project
      validation or any scene-entry processing
    - Follows the Serenum sequence on every workflow attempt: click
      nanobananaconfig.png first, then click only nanobanana_16ratio9.png
    - Download monitoring snapshots the real Windows/Edge download folders BEFORE
      triggering the download and detects new or updated image files across them
    - Detects Edge custom download directories from profile Preferences and the
      Windows Downloads known-folder registry values
    - Handles temporary download files, waits for stable/valid image data, and
      verifies the saved destination before reporting success
    """
    import os
    import json
    import time
    import re
    import subprocess
    import traceback
    import threading
    import ctypes
    from ctypes import wintypes

    try:
        import pyautogui
        import pyperclip
        import win32api
        import win32con
        import win32gui
        import win32process
        import psutil
        import keyboard
    except ImportError as e:
        print(f"❌ [GF] Missing dependency: {e}")
        return

    pyautogui.PAUSE = 0.0
    STAGE_TIMEOUT_SECONDS = 40.0
    restart_event = threading.Event()
    restart_from_url_event = threading.Event()
    stop_event = threading.Event()
    terminate_automation = False

    # The shared polling path checks the exit editing control at most once per
    # second. The re-entry guard is essential because clicking that control
    # itself uses _sleep(), which also calls check_for_termination().
    exit_editing_CHECK_INTERVAL = 1.0
    last_exit_editing_check_at = 0.0
    exit_editing_check_active = False
    exit_editing_click_in_progress = False
    download_ui_sequence_active = False

    # While this lock is active, the cursor is pinned below the one
    # imagerenderingprogress match. Only that progress indicator (during
    # rendering) and moregf.png (after rendering) may be searched.
    image_render_lock_active = False
    image_render_lock_position = None
    RENDER_LOCK_PADDING_X = 260
    RENDER_LOCK_PADDING_Y = 170
    RENDER_DISAPPEAR_CONFIRM_SAMPLES = 3
    RENDER_MODAL_CHECK_INTERVAL = 1.25
    last_render_modal_check_at = 0.0

    # A Windows low-level mouse hook blocks physical wheel scrolling while the
    # image-position lock is active. It is installed only for the locked phase.
    scroll_hook_thread = None
    scroll_hook_thread_id = None
    scroll_hook_stop_event = threading.Event()
    scroll_hook_ready_event = threading.Event()
    scroll_hook_callback_ref = None
    scroll_hook_handle = None
    scroll_key_hook_handles = []

    class _WorkflowRestart(BaseException):
        """Unwind the current workflow; optionally force URL-first navigation."""
        def __init__(self, message, force_url=False):
            super().__init__(message)
            self.force_url = bool(force_url)

    class _ManualStop(BaseException):
        """Raised only when the user presses Alt+/ ."""
        pass

    class _NanoBananaStartupFailure(BaseException):
        """Stop safely when this workflow attempt cannot confirm Nano Banana setup."""
        pass

    def set_image_scroll_lock(enabled):
        """
        Block mouse-wheel and horizontal-wheel input at the Windows OS level
        while the image cursor anchor is locked. This prevents accidental
        scrolling rather than trying to chase a moving page position.
        """
        nonlocal scroll_hook_thread, scroll_hook_thread_id
        nonlocal scroll_hook_callback_ref, scroll_hook_handle

        if enabled:
            if scroll_hook_thread and scroll_hook_thread.is_alive():
                return True

            scroll_hook_stop_event.clear()
            scroll_hook_ready_event.clear()

            def _hook_worker():
                nonlocal scroll_hook_thread_id, scroll_hook_callback_ref, scroll_hook_handle
                WH_MOUSE_LL = 14
                WM_MOUSEWHEEL = 0x020A
                WM_MOUSEHWHEEL = 0x020E
                WM_QUIT = 0x0012
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                scroll_hook_thread_id = kernel32.GetCurrentThreadId()

                LRESULT = ctypes.c_ssize_t
                HOOKPROC = ctypes.WINFUNCTYPE(
                    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
                )

                def _low_level_mouse_proc(n_code, w_param, l_param):
                    if n_code >= 0 and image_render_lock_active:
                        if int(w_param) in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
                            # Swallow wheel input while the lock is active.
                            return 1
                    return user32.CallNextHookEx(
                        scroll_hook_handle, n_code, w_param, l_param
                    )

                scroll_hook_callback_ref = HOOKPROC(_low_level_mouse_proc)
                module_handle = kernel32.GetModuleHandleW(None)
                scroll_hook_handle = user32.SetWindowsHookExW(
                    WH_MOUSE_LL, scroll_hook_callback_ref, module_handle, 0
                )
                if not scroll_hook_handle:
                    print("⚠️ [SCROLL-LOCK] Windows mouse-wheel hook could not be installed.")
                    scroll_hook_ready_event.set()
                    return

                scroll_hook_ready_event.set()
                message = wintypes.MSG()
                try:
                    while not scroll_hook_stop_event.is_set():
                        result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                        if result <= 0:
                            break
                        user32.TranslateMessage(ctypes.byref(message))
                        user32.DispatchMessageW(ctypes.byref(message))
                finally:
                    try:
                        user32.UnhookWindowsHookEx(scroll_hook_handle)
                    except Exception:
                        pass
                    scroll_hook_handle = None

            scroll_hook_thread = threading.Thread(
                target=_hook_worker,
                name="GoogleFlowScrollLock",
                daemon=True
            )
            scroll_hook_thread.start()
            scroll_hook_ready_event.wait(timeout=2.0)
            # Also block common browser scrolling keys while the cursor is
            # pinned. These hooks are removed as soon as More is clicked.
            try:
                for key_name in ("page up", "page down", "home", "end", "up", "down", "space"):
                    try:
                        scroll_key_hook_handles.append(keyboard.block_key(key_name))
                    except Exception:
                        pass
            except Exception:
                pass

            if scroll_hook_handle:
                print(
                    "🔒 [SCROLL-LOCK] OS-level mouse-wheel scrolling and common "
                    "page-scrolling keys are blocked."
                )
                return True
            print(
                "⚠️ [SCROLL-LOCK] Wheel blocking is unavailable; common scrolling "
                "keys and cursor-position checks remain active."
            )
            return False

        for hook_handle in list(scroll_key_hook_handles):
            try:
                keyboard.unhook(hook_handle)
            except Exception:
                pass
        scroll_key_hook_handles.clear()

        if scroll_hook_thread and scroll_hook_thread.is_alive():
            scroll_hook_stop_event.set()
            try:
                if scroll_hook_thread_id:
                    ctypes.windll.user32.PostThreadMessageW(
                        scroll_hook_thread_id, 0x0012, 0, 0
                    )
            except Exception:
                pass
            scroll_hook_thread.join(timeout=1.0)
        scroll_hook_thread = None
        scroll_hook_thread_id = None
        scroll_hook_callback_ref = None
        scroll_hook_handle = None
        return True

    def restore_locked_cursor():
        """Force the pointer back to its saved anchor and keep wheel lock enabled."""
        if not image_render_lock_active or image_render_lock_position is None:
            return
        target_x, target_y = image_render_lock_position
        try:
            current_x, current_y = pyautogui.position()
            if abs(current_x - target_x) > 3 or abs(current_y - target_y) > 3:
                print(
                    f"🛡️ [GF-LOCK] Cursor drifted to ({current_x}, {current_y}); "
                    f"forcing it back to ({target_x}, {target_y})."
                )
                pyautogui.moveTo(target_x, target_y, duration=0.1)
        except Exception as cursor_error:
            print(f"⚠️ [GF-LOCK] Cursor check failed; restoring anchor: {cursor_error}")
            pyautogui.moveTo(target_x, target_y, duration=0.1)

    def _bounded_timeout(value):
        try:
            return max(0.1, min(float(value), STAGE_TIMEOUT_SECONDS))
        except (TypeError, ValueError):
            return STAGE_TIMEOUT_SECONDS

    def _sleep(seconds):
        """Sleep in short slices so Ctrl+Shift+F12 and Alt+/ are handled promptly."""
        deadline = time.monotonic() + max(0.0, float(seconds))
        while True:
            # Poll continuously so Ctrl+Shift+F12, Alt+/, and the exit editing control
            # are handled during all waits, including generation/download stages.
            check_for_termination()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    def _supervisor_wait(seconds):
        """Interruptible delay used only between complete workflow attempts."""
        deadline = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < deadline:
            if stop_event.is_set() or restart_event.is_set() or restart_from_url_event.is_set():
                return
            time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))

    # ------------------------------------------------------------------
    # Structure-independent JSON discovery helpers
    # ------------------------------------------------------------------
    def _normalise_key(key):
        return re.sub(r"[^a-z0-9]", "", str(key).lower())

    def _walk_json(node, path=()):
        """Yield every JSON node with its path, regardless of wrapper/key names."""
        yield path, node
        if isinstance(node, dict):
            for key, value in node.items():
                yield from _walk_json(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from _walk_json(value, path + (index,))

    def _find_field(node, aliases, require_value=True):
        wanted = {_normalise_key(alias) for alias in aliases}
        for path, current in _walk_json(node):
            if not isinstance(current, dict):
                continue
            for key, value in current.items():
                if _normalise_key(key) in wanted:
                    if not require_value or value not in (None, "", [], {}):
                        return value
        return None

    def _find_project_title(node):
        value = _find_field(node, ("project_title", "projectTitle", "project_name", "projectName"))
        if isinstance(value, dict):
            value = _find_field(value, ("project_title", "title", "name"))
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
        return "workproject1"

    def _find_engine(node):
        value = _find_field(node, (
            "image_generation_engine", "imageGenerationEngine",
            "engine_type", "engineType", "engine"
        ))
        if isinstance(value, dict):
            value = _find_field(value, ("image_generation_engine", "engine_type", "engine", "type"))
        return str(value).strip() if value is not None else ""

    def _find_script_data(node):
        """Find the best script list anywhere, ignoring character-prompt lists."""
        candidates = []
        for path, current in _walk_json(node):
            if not path or not isinstance(path[-1], str):
                continue
            if _normalise_key(path[-1]) != "script":
                continue
            if isinstance(current, list):
                score = 0
                for item in current:
                    if isinstance(item, dict):
                        keys = {_normalise_key(k) for k in item}
                        if keys.intersection({
                            "sceneimagegeneration", "sceneimageprompt",
                            "imagegenerationprompt", "imageprompt",
                            "charactersreference", "scenepovprompt",
                            "shotnumber", "dialogue"
                        }):
                            score += 10
                        if "entries" in keys:
                            score += 2
                candidates.append((score, len(current), current))
            elif isinstance(current, dict):
                nested = _find_field(current, ("script",))
                if isinstance(nested, list):
                    candidates.append((1, len(nested), nested))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return candidates[0][2]
        value = _find_field(node, ("script",))
        return value if isinstance(value, (dict, list)) else {}

    def _remove_project_payload(node):
        """Remove the completed project's title/script while preserving automation settings."""
        if isinstance(node, list):
            for item in node:
                _remove_project_payload(item)
            return
        if not isinstance(node, dict):
            return

        key_map = {_normalise_key(key): key for key in list(node.keys())}
        has_direct_title = any(k in key_map for k in ("projecttitle", "projectname"))
        has_script = any(k in key_map for k in ("script", "scriptjson"))
        automation_key = key_map.get("automation")
        automation = node.get(automation_key) if automation_key else None
        has_automation_title = (
            isinstance(automation, dict)
            and any(_normalise_key(key) in {"projecttitle", "projectname"} for key in automation)
        )

        # The new schema places project_title inside automation while script is
        # commonly a sibling. Remove that script payload together with the title.
        if has_script and (has_direct_title or has_automation_title):
            for normalized in ("script", "scriptjson"):
                original_key = key_map.get(normalized)
                if original_key is not None:
                    node.pop(original_key, None)

        # Remove only project-identifying keys. Keep engine, engineoperator,
        # projectcategory, imageproducercontroller, and status settings intact.
        for key in list(node.keys()):
            if _normalise_key(key) in {"projectname", "projecttitle"}:
                node.pop(key, None)
                continue
            value = node.get(key)
            if isinstance(value, (dict, list)):
                _remove_project_payload(value)


    # ------------------------------------------------------------------
    # Status helpers (self-contained)
    # ------------------------------------------------------------------
    def _load_panel():
        if not os.path.exists(PANEL_PATH):
            return {}
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_panel(data):
        try:
            os.makedirs(os.path.dirname(PANEL_PATH) or '.', exist_ok=True)
            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ [STATUS] Failed to save panel: {e}")
            return False

    def _find_status_container(node):
        """Find the best dictionary for status fields anywhere in the JSON tree.

        Prefer the actual project/configuration dictionary (project title plus
        script). After a completed project payload is removed, fall back to the
        deepest dictionary already carrying status fields. If neither exists,
        use the root dictionary or create a metadata dictionary in a root list.
        The original root structure and wrapper keys are preserved.
        """
        candidates = []

        def visit(current, path=()):
            if isinstance(current, dict):
                normalized = {_normalise_key(k): v for k, v in current.items()}
                has_title = any(k in normalized for k in ("projecttitle", "projectname"))
                has_script = any(k in normalized for k in ("script", "scriptjson"))
                has_status = any(k in normalized for k in ("currentlyrunning", "status", "operationstatus"))
                # Configuration container is the strongest match. Status-only
                # containers remain discoverable after the project is removed.
                score = (100 if has_title and has_script else 0)
                if has_status:
                    score += 40
                if any(k in normalized for k in ("engine", "imagegenerationengine", "enginetype")):
                    score += 5
                candidates.append((score, len(path), path, current))
                for key, child in current.items():
                    if isinstance(child, (dict, list)):
                        visit(child, path + (key,))
            elif isinstance(current, list):
                for index, child in enumerate(current):
                    if isinstance(child, (dict, list)):
                        visit(child, path + (index,))

        visit(node)
        if not candidates:
            return None

        # Prefer the best semantic match; on ties, prefer the deeper container.
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best = candidates[0]
        if best[0] == 0 and isinstance(node, dict):
            return node
        return best[3]

    def _get_status_value(data, key, default=None):
        container = _find_status_container(data)
        if isinstance(container, dict):
            # Match status keys case-insensitively and regardless of punctuation.
            wanted = _normalise_key(key)
            for existing_key, value in container.items():
                if _normalise_key(existing_key) == wanted:
                    return value
        return default

    def _get_currently_running():
        data = _load_panel()
        val = _get_status_value(data, "currently_running")
        if val is None:
            return None
        val = str(val).strip()
        if val.lower() in ("", "none", "null"):
            return None
        return val

    def _set_currently_running(value, status=None, operation_status=None):
        data = _load_panel()
        container = _find_status_container(data)

        if container is None:
            if isinstance(data, list):
                # Keep the root as a list; add a dedicated metadata object only
                # when no existing dictionary can safely hold status fields.
                container = {"_automation_status": True}
                data.append(container)
            elif isinstance(data, dict):
                container = data
            else:
                print("❌ [STATUS] Cannot update status: panel JSON root is not an object/list.")
                return False

        container["currently_running"] = value
        if status is not None:
            safe_status = str(status).strip().lower()
            if safe_status == "aborted":
                safe_status = "pending"
            container["status"] = safe_status
        if operation_status is not None:
            container["operation_status"] = operation_status
        return _save_panel(data)

    def _transfer_completed_project_to_ready_script(images_folder, expected_entries):
        """
        Append a completed project snapshot to READY_SCRIPT without overwriting
        existing projects. Only remove project_name from PANEL_PATH after the
        append has been successfully written and verified.
        """
        import copy

        # Verify the exact scene-image naming convention and the required
        # video-level thumbnail before the project can be marked complete.
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
        found_entries = set()
        if os.path.isdir(images_folder):
            for filename in os.listdir(images_folder):
                match = re.fullmatch(
                    r"entry_(\d+)\.(png|jpg|jpeg|gif|webp|bmp|tiff)",
                    filename,
                    re.IGNORECASE
                )
                if not match:
                    continue
                number = int(match.group(1))
                full_path = os.path.join(images_folder, filename)
                try:
                    if (
                        1 <= number <= expected_entries
                        and os.path.isfile(full_path)
                        and os.path.getsize(full_path) > 0
                        and os.path.splitext(filename)[1].lower() in image_extensions
                    ):
                        found_entries.add(number)
                except OSError:
                    pass

        missing = [
            f"entry_{number}"
            for number in range(1, expected_entries + 1)
            if number not in found_entries
        ]

        thumbnail_path = os.path.join(images_folder, "Thumbnail.png")
        if not os.path.isfile(thumbnail_path) or os.path.getsize(thumbnail_path) <= 0:
            missing.append("Thumbnail.png")

        if missing:
            print("❌ [READY-SCRIPT] Transfer cancelled; missing required image(s): " + ", ".join(missing))
            update_operation_status(
                "Project was not transferred because one or more scene images or Thumbnail.png are missing",
                is_error=True
            )
            return False

        # Re-read the source so status updates made during the workflow are retained.
        try:
            with open(PANEL_PATH, "r", encoding="utf-8") as source_file:
                source_data = json.load(source_file)
            if not isinstance(source_data, (dict, list)):
                print("❌ [READY-SCRIPT] Source panel is not a JSON object/list.")
                return False

            source_title = _find_project_title(source_data)
            project_snapshot = copy.deepcopy(source_data)
            snapshot_status_container = _find_status_container(project_snapshot)
            if snapshot_status_container is None:
                if isinstance(project_snapshot, dict):
                    snapshot_status_container = project_snapshot
                elif isinstance(project_snapshot, list):
                    snapshot_status_container = {"_automation_status": True}
                    project_snapshot.append(snapshot_status_container)
            if isinstance(snapshot_status_container, dict):
                snapshot_status_container["currently_running"] = "sceneiq_google_flow_images_generation_engine_successful"
                snapshot_status_container["status"] = "completed"
                snapshot_status_container["operation_status"] = (
                    f"Completed project '{source_title}' with {expected_entries} verified image(s)"
                )

            ready_dir = os.path.dirname(READY_SCRIPT)
            if ready_dir:
                os.makedirs(ready_dir, exist_ok=True)

            if os.path.exists(READY_SCRIPT) and os.path.getsize(READY_SCRIPT) > 0:
                with open(READY_SCRIPT, "r", encoding="utf-8") as ready_file:
                    ready_data = json.load(ready_file)
            else:
                ready_data = {"projects": []}

            # Supported append formats: a JSON list, {"projects": [...]}, or a
            # legacy single-project object. Preserve existing metadata/projects.
            if isinstance(ready_data, list):
                ready_data.append(project_snapshot)
            elif isinstance(ready_data, dict):
                if isinstance(ready_data.get("projects"), list):
                    ready_data["projects"].append(project_snapshot)
                elif _find_field(ready_data, ("project_title", "projectTitle", "project_name", "projectName")) is not None:
                    existing_project = ready_data
                    ready_data = {"projects": [existing_project, project_snapshot]}
                else:
                    ready_data["projects"] = [project_snapshot]
            else:
                raise ValueError("ready_script.json must contain a JSON object or list")

            with open(READY_SCRIPT, "w", encoding="utf-8") as ready_file:
                json.dump(ready_data, ready_file, indent=4, ensure_ascii=False)
                ready_file.flush()
                os.fsync(ready_file.fileno())

            # Verify the appended project can be read back before touching source.
            with open(READY_SCRIPT, "r", encoding="utf-8") as verify_file:
                verified_data = json.load(verify_file)
            if isinstance(verified_data, list):
                verified = any(
                    isinstance(item, (dict, list))
                    and _find_field(item, ("project_title", "projectTitle", "project_name", "projectName")) is not None
                    and _find_project_title(item) == source_title
                    for item in verified_data
                )
            else:
                verified = any(
                    isinstance(item, (dict, list))
                    and _find_field(item, ("project_title", "projectTitle", "project_name", "projectName")) is not None
                    and _find_project_title(item) == source_title
                    for item in verified_data.get("projects", [])
                )
            if not verified:
                raise IOError("Could not verify the project in ready_script.json")

            # Remove only the completed project payload while preserving the
            # original root type (dictionary OR list) and its wrapper structure.
            if isinstance(source_data, (dict, list)):
                _remove_project_payload(source_data)
                source_status_container = _find_status_container(source_data)
                if source_status_container is None:
                    if isinstance(source_data, dict):
                        source_status_container = source_data
                    else:
                        source_status_container = {"_automation_status": True}
                        source_data.append(source_status_container)
                source_status_container["currently_running"] = "sceneiq_google_flow_images_generation_engine_successful"
                source_status_container["status"] = "completed"
                source_status_container["operation_status"] = f"Project transferred to ready script: {source_title}"
            with open(PANEL_PATH, "w", encoding="utf-8") as source_file:
                json.dump(source_data, source_file, indent=4, ensure_ascii=False)

            print(
                f"✅ [READY-SCRIPT] Appended completed project "
                f"'{source_title}' "
                f"to {READY_SCRIPT}; removed completed project payload from {PANEL_PATH}"
            )
            return True

        except Exception as exc:
            print(f"❌ [READY-SCRIPT] Failed to transfer completed project: {exc}")
            traceback.print_exc()
            update_operation_status(f"Failed to transfer completed project: {exc}", is_error=True)
            return False

    # ------------------------------------------------------------------
    # Engine check (no currently_running gate)
    # ------------------------------------------------------------------
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        try:
            hud.print("Configuration file is missing.", "error")
        except Exception:
            pass
        return

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)

        image_generation_engine = _find_engine(panel_data)

        if image_generation_engine.lower() != 'google flow':
            print(f"ℹ️ [ENGINE] Image generation engine is '{image_generation_engine}', not 'Google Flow' - skipping operation")
            print(f"   To use this function, set 'image_generation_engine' to 'Google Flow' in panel.json")
            try:
                hud.print("Google Flow is not the selected engine — skipping.", "waiting")
            except Exception:
                pass
            return

        print(f"✅ [ENGINE] Image generation engine is 'Google Flow' - proceeding with operation")

    except json.JSONDecodeError as e:
        print(f"❌ Error: panel.json is not valid JSON: {e}")
        try:
            hud.print("Configuration file appears to be corrupted.", "error")
        except Exception:
            pass
        return
    except Exception as e:
        print(f"❌ Error reading panel.json: {e}")
        try:
            hud.print("Could not read the configuration file.", "error")
        except Exception:
            pass
        return

    # Claim the slot
    _set_currently_running(
        "sceneiq_google_flow_images_generation_engine()",
        status="pending",
        operation_status="Running sceneiq_google_flow_images_generation_engine()"
    )
    print("🔒 [GF] Claimed currently_running = 'sceneiq_google_flow_images_generation_engine()'")

    # ------------------------------------------------------------------
    # Rest of original logic
    # ------------------------------------------------------------------
    # Discover project title and script by key/value anywhere in the JSON tree.
    # The wrapper may be project_name, automation, value, or any other key.
    project_title = _find_project_title(panel_data)
    project_category = _find_field(panel_data, ("projectcategory", "project_category", "projectCategory"))
    script_data = _find_script_data(panel_data)

    # Support the new scene-by-scene structure:
    # {
    #   "characters_prompt": [...],
    #   "script": [
    #       {
    #           "shot_number": 1,
    #           "characters_reference": {...},
    #           "scene_Image_generation": "...",
    #           ...
    #       }
    #   ]
    # }
    # Also retain compatibility with the previous nested batches/entries format.
    all_entries = []

    def _is_new_scene_entry(item):
        if not isinstance(item, dict):
            return False
        keys = {_normalise_key(key) for key in item}
        has_reference = bool(keys.intersection({"charactersreference", "characterreference"}))
        has_image_prompt = any(
            key in keys for key in (
                "sceneimagegeneration", "sceneimageprompt",
                "imagegenerationprompt", "imageprompt"
            )
        )
        return has_reference and has_image_prompt

    def _collect_scene_entries(node):
        if isinstance(node, list):
            for item in node:
                if _is_new_scene_entry(item):
                    all_entries.append(item)
                elif isinstance(item, (dict, list)):
                    _collect_scene_entries(item)
        elif isinstance(node, dict):
            # A direct scene object should be collected once.
            if _is_new_scene_entry(node):
                all_entries.append(node)
                return
            # Old format: batches containing an "entries" list.
            entries = _find_field(node, ("entries",))
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and (
                        _is_new_scene_entry(entry) or "scene_pov_prompt" in entry
                    ):
                        all_entries.append(entry)
                # Continue through other branches too, in case the structure mixes formats.
            for key, value in node.items():
                if _normalise_key(key) not in (
                    "charactersprompt", "charactersvisualprompt", "entries"
                ):
                    if isinstance(value, (dict, list)):
                        _collect_scene_entries(value)

    _collect_scene_entries(script_data)

    total_entries = len(all_entries)
    print(f"📊 [CONFIG] Found {total_entries} total entries")

    if total_entries == 0:
        print("⚠️ No entries are currently available; the supervisor will re-read panel.json and retry.")

    operation_status_flag = True
    operation_status_message = ""
    operation_aborted = False

    # Only these two fields are sent to Google Flow for each new-format scene.
    # Timing, dialogue, shot_number, and all other metadata are intentionally excluded.
    SCENE_PROMPT_FIELDS = ("characters_reference", "scene_Image_generation")
    FIELDS_TO_STRIP = {"start", "stop", "duration", "audio_focus"}
    SEND_LOCATION_TOLERANCE = 20

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)

            if is_abort:
                operation_status_message = f"⚠️ STOPPED: {message}"
                operation_status_flag = False
                operation_aborted = True
            elif is_error:
                operation_status_message = f"⚠️ ERROR: {message}"
                operation_status_flag = False
            elif is_success:
                operation_status_message = f"✅ {message}"
                operation_status_flag = True
            else:
                operation_status_message = f"ℹ️ {message}"

            status_container = _find_status_container(current_panel)
            if status_container is None:
                if isinstance(current_panel, dict):
                    status_container = current_panel
                elif isinstance(current_panel, list):
                    status_container = {"_automation_status": True}
                    current_panel.append(status_container)
                else:
                    raise TypeError("panel.json root must be a JSON object or list")

            status_container['operation_status'] = operation_status_message
            if is_error or is_abort:
                status_container['currently_running'] = "sceneiq_google_flow_images_generation_engine()"
                status_container['status'] = "error"
            elif is_success:
                status_container['currently_running'] = "sceneiq_google_flow_images_generation_engine()"
                status_container['status'] = "pending"

            if not _save_panel(current_panel):
                raise IOError("Could not persist operation status to panel.json")

            if is_abort:
                print(f"🛑 [STATUS] Operation recorded as an error: {message}")
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        print(f"🔁 [RECOVERY] Restarting the complete Google Flow function: {reason}")
        update_operation_status(f"Restart requested: {reason}", is_error=True)
        raise _WorkflowRestart(str(reason))

    def check_operation_status():
        return bool(operation_status_flag and not operation_aborted)

    remote_controller_last_operation = "run"
    remote_controller_last_poll_at = 0.0

    def _poll_remote_controller(force=False):
        nonlocal remote_controller_last_operation, remote_controller_last_poll_at
        now = time.monotonic()
        if not force and now - remote_controller_last_poll_at < 1.0:
            return remote_controller_last_operation
        remote_controller_last_poll_at = now
        command = _sceneiq_read_image_controller_operation()
        previous = remote_controller_last_operation
        if command != previous:
            remote_controller_last_operation = command
            messages = {
                "pause": ("Image production has been paused by the remote controller.", True),
                "continue": ("Image production has resumed by the remote controller.", False),
                "restart": ("Image production has been restarted by the remote controller. Restarting the workflow...", False),
                "stop": ("Image production has been stopped by the remote controller. The controller remains active.", False),
            }
            notice = messages.get(command)
            if notice:
                try:
                    hud.notify_modal(notice[0], persistent=notice[1])
                except Exception:
                    print(f"[IMAGE-CONTROLLER] {notice[0]}")
                print(f"📡 [IMAGE-CONTROLLER] operation changed: {previous} -> {command}")
            elif command == "run" and previous == "pause":
                try:
                    hud.notify_modal("Image production has resumed. Continuing the current workflow...", persistent=False)
                except Exception:
                    pass
            if command == "restart":
                # Restart is an edge-triggered command, not a permanent state.
                # Consume it after capturing the command so the internal workflow
                # supervisor performs one restart instead of restarting forever.
                _sceneiq_write_controller_operation("run")
                remote_controller_last_operation = "run"
                return "restart"
        return remote_controller_last_operation

    def on_restart_shortcut():
        restart_from_url_event.set()
        try:
            hud.notify_modal("Image production is restarting from Google Flow. Reopening the workflow...", persistent=False)
        except Exception:
            pass
        print("🔁 [HOTKEY] Ctrl+Shift+F12 pressed — restarting from GOOGLE_FLOW_URL without checking the current page.")

    def on_terminate_shortcut():
        nonlocal terminate_automation
        terminate_automation = True
        stop_event.set()
        _sceneiq_write_controller_operation("stop")
        try:
            hud.notify_modal("Image production has been stopped by the keyboard shortcut. The remote controller is still listening.", persistent=False)
        except Exception:
            pass
        print("🛑 [HOTKEY] Alt+/ pressed — image production stopped; controller remains available.")

    def check_for_termination():
        nonlocal last_exit_editing_check_at, exit_editing_check_active
        nonlocal download_ui_sequence_active, terminate_automation

        remote_operation = _poll_remote_controller()
        if remote_operation == "pause":
            # Stay responsive while paused: the loop keeps polling controller
            # commands and honours both existing manual hotkeys.
            while remote_operation == "pause":
                if stop_event.is_set() or terminate_automation:
                    raise _ManualStop("Image production stopped while remotely paused")
                if restart_from_url_event.is_set():
                    restart_from_url_event.clear()
                    raise _WorkflowRestart("Manual Ctrl+Shift+F12 requested while paused", force_url=True)
                if restart_event.is_set():
                    restart_event.clear()
                    raise _WorkflowRestart("Manual restart requested while paused")
                time.sleep(0.2)
                remote_operation = _poll_remote_controller()
        if remote_operation == "stop":
            stop_event.set()
            terminate_automation = True
            raise _ManualStop("Remote controller requested image production stop")
        if remote_operation == "restart":
            raise _WorkflowRestart("Remote controller requested a full image workflow restart")

        if stop_event.is_set() or terminate_automation:
            raise _ManualStop("Manual stop requested with Alt+/")
        if restart_from_url_event.is_set():
            restart_from_url_event.clear()
            raise _WorkflowRestart(
                "Manual Ctrl+Shift+F12 requested: restart directly from GOOGLE_FLOW_URL",
                force_url=True,
            )
        if restart_event.is_set():
            restart_event.clear()
            raise _WorkflowRestart("Manual restart requested")
        if not check_operation_status():
            raise _WorkflowRestart("Operation status is invalid; restarting the workflow")

        # exit editing may appear unexpectedly if a generated photo opens in
        # the editor. Check for it at every shared polling point, but throttle
        # screen matching so it does not dominate the GUI automation.
        now = time.monotonic()
        if (
            not download_ui_sequence_active
            and not image_render_lock_active
            and not exit_editing_check_active
            and now - last_exit_editing_check_at >= exit_editing_CHECK_INTERVAL
        ):
            last_exit_editing_check_at = now
            exit_editing_check_active = True
            try:
                check_and_click_exit_editing()
            except (_WorkflowRestart, _ManualStop):
                raise
            except Exception as exit_editing_error:
                print(f"⚠️ [DONE-EDITING] Periodic check failed safely: {exit_editing_error}")
            finally:
                exit_editing_check_active = False

    def format_entry_for_paste(entry_data):
        """Serialize only the two approved prompt fields for the new scene schema."""
        try:
            if not isinstance(entry_data, dict):
                print("⚠️ [PREPARE] Scene entry is not a JSON object.")
                return ""

            # Locate the two scene prompt fields independent of capitalization,
            # punctuation, or surrounding JSON structure.
            key_lookup = {_normalise_key(key): key for key in entry_data}
            reference_key = next(
                (key_lookup[name] for name in ("charactersreference", "characterreference")
                 if name in key_lookup), None
            )
            image_key = next(
                (key_lookup[name] for name in (
                    "sceneimagegeneration", "sceneimageprompt",
                    "imagegenerationprompt", "imageprompt"
                ) if name in key_lookup), None
            )
            if reference_key is not None or image_key is not None:
                cleaned = {}
                if reference_key is not None:
                    cleaned["characters_reference"] = entry_data[reference_key]
                if image_key is not None:
                    cleaned["scene_Image_generation"] = entry_data[image_key]

                missing = [
                    key for key in SCENE_PROMPT_FIELDS
                    if key not in cleaned
                ]
                if missing:
                    print(
                        "⚠️ [PREPARE] New-format scene is missing required field(s): "
                        + ", ".join(missing)
                    )
                    return ""

                return json.dumps(cleaned, indent=4, ensure_ascii=False)

            # Legacy fallback: keep the former scene prompt behaviour for old entries,
            # while still stripping timing/audio metadata.
            cleaned = {
                key: value
                for key, value in entry_data.items()
                if key not in FIELDS_TO_STRIP
            }
            return json.dumps(cleaned, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [PREPARE] Error preparing scene data: {e}")
            return ""

    # --- DYNAMIC FALLBACK HELPERS ---
    def get_image_variants(base_name):
        variants = []
        base_name_without_ext = os.path.splitext(base_name)[0]
        ext = os.path.splitext(base_name)[1]
        original_path = os.path.join(GUI_IMAGES, base_name)
        if os.path.exists(original_path):
            variants.append(original_path)
        pattern = re.compile(rf'^{re.escape(base_name_without_ext)}(\d+)\.{re.escape(ext[1:])}$', re.IGNORECASE)
        try:
            files = os.listdir(GUI_IMAGES)
            numbered_variants = []
            for filename in files:
                match = pattern.match(filename)
                if match:
                    number = int(match.group(1))
                    full_path = os.path.join(GUI_IMAGES, filename)
                    numbered_variants.append((number, full_path))
            numbered_variants.sort(key=lambda x: x[0])
            for _, full_path in numbered_variants:
                variants.append(full_path)
        except Exception as e:
            print(f"⚠️ [FALLBACK] Error scanning for variants of {base_name}: {e}")
        return variants

    def find_image_with_fallback(image_name, confidence=0.8, region=None):
        variants = get_image_variants(image_name)
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateCenterOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False,
                    region=region
                )
                if location:
                    print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                    return location, variant_path
            except Exception:
                pass
        return None, None

    def wait_for_image_with_fallback(image_name, timeout_seconds=40, confidence=0.8, region=None):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        variants = get_image_variants(image_name)
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        print(f"🔍 [FALLBACK] Waiting for {image_name} with {len(variants)} variant(s)...")
        start_time = time.time()
        last_status_time = 0
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            for variant_path in variants:
                variant_name = os.path.basename(variant_path)
                try:
                    location = pyautogui.locateCenterOnScreen(
                        variant_path,
                        confidence=confidence,
                        grayscale=False,
                        region=region
                    )
                    if location:
                        print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                        return location, variant_path
                except Exception:
                    pass
            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(f"⏳ [FALLBACK] Still waiting for {image_name}... ({elapsed}s elapsed)")
                last_status_time = current_time
            _sleep(0.3)
        print(f"❌ [FALLBACK] {image_name} not found in any variant within {timeout_seconds} seconds")
        return None, None

    def wait_for_image_indefinitely(image_name, confidence=0.8, region=None):
        """Legacy name; this is deliberately bounded and triggers recovery."""
        location, _ = wait_for_image_with_fallback(
            image_name,
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=confidence,
            region=region
        )
        if not location:
            raise _WorkflowRestart(f"{image_name} was not found within 40 seconds")
        return location

    def find_image_at_location(image_name, target_x, target_y, tolerance=20, confidence=0.7):
        """Search only near a known point instead of matching an unrelated screen element."""
        variants = get_image_variants(image_name)
        if not variants:
            return None
        screen_width, screen_height = pyautogui.size()
        left = max(0, int(target_x - tolerance))
        top = max(0, int(target_y - tolerance))
        right = min(int(screen_width), int(target_x + tolerance + 1))
        bottom = min(int(screen_height), int(target_y + tolerance + 1))
        region = (left, top, max(1, right - left), max(1, bottom - top))
        for variant_path in variants:
            try:
                location = pyautogui.locateCenterOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False,
                    region=region
                )
                if location:
                    dx = abs(location.x - target_x)
                    dy = abs(location.y - target_y)
                    if dx <= tolerance and dy <= tolerance:
                        print(f"✅ [LOC-LOCK] {os.path.basename(variant_path)} matched at "
                              f"({location.x}, {location.y}) — within tolerance of "
                              f"({target_x}, {target_y}) [dx={dx}, dy={dy}]")
                        return location
            except Exception:
                pass
        return None

    # --- WINDOW MANAGEMENT HELPERS ---
    def get_current_monitor():
        try:
            cursor_pos = win32api.GetCursorPos()
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint(cursor_pos))
            return monitor_info['Monitor']
        except Exception:
            return (0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                    win32api.GetSystemMetrics(win32con.SM_CYSCREEN))

    def get_edge_window_on_monitor(monitor_bounds):
        monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_bounds
        edge_windows = []
        edge_process_names = ["msedge.exe"]

        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    if process.name().lower() in edge_process_names:
                        rect = win32gui.GetWindowRect(hwnd)
                        left, top, right, bottom = rect
                        width, height = right - left, bottom - top
                        if width > 200 and height > 200:
                            window_center_x = (left + right) / 2
                            window_center_y = (top + bottom) / 2
                            is_on_current_monitor = (
                                monitor_left <= window_center_x <= monitor_right and
                                monitor_top <= window_center_y <= monitor_bottom
                            )
                            if is_on_current_monitor:
                                windows.append({'hwnd': hwnd, 'width': width, 'height': height})
                except Exception:
                    pass
            return True

        win32gui.EnumWindows(enum_windows_callback, edge_windows)
        edge_windows.sort(key=lambda w: w['width'] * w['height'], reverse=True)
        return edge_windows

    def ensure_edge_window_ready():
        check_for_termination()
        current_monitor = get_current_monitor()
        edge_windows = get_edge_window_on_monitor(current_monitor)

        if edge_windows:
            hwnd = edge_windows[0]['hwnd']
            print(f"🪟 [WINDOW] Found existing Edge window handle: {hwnd}")
            try:
                if win32gui.IsIconic(hwnd):
                    print("🔄 [WINDOW] Window was minimized, restoring...")
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    _sleep(0.3)
                print("🔄 [WINDOW] Maximizing window...")
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                _sleep(0.5)
                win32gui.SetForegroundWindow(hwnd)
                _sleep(0.2)
                print("✅ [WINDOW] Window ready - maximized and focused")
                update_operation_status("Browser window ready for Google Flow operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")

        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for Google Flow operation...")
        try:
            hud.print("Opening the browser...", "navigating")
        except Exception:
            pass
        subprocess.Popen([edge_path, "about:blank"])

        for attempt in range(20):
            check_for_termination()
            _sleep(0.5)
            edge_windows = get_edge_window_on_monitor(current_monitor)
            if edge_windows:
                hwnd = edge_windows[0]['hwnd']
                print(f"🪟 [WINDOW] New Edge window launched, handle: {hwnd}")
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        _sleep(0.3)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.5)
                    win32gui.SetForegroundWindow(hwnd)
                    _sleep(0.2)
                    print("✅ [WINDOW] New window ready - maximized and focused")
                    update_operation_status("Browser launched for Google Flow operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue

        error_msg = "Failed to get or launch Edge window for Google Flow operation"
        update_operation_status(error_msg, is_error=True)
        try:
            hud.print("Could not open the browser window.", "error")
        except Exception:
            pass
        abort_operation(error_msg)
        raise RuntimeError(error_msg)

    def enforce_window_focus(hwnd):
        check_for_termination()
        try:
            if not win32gui.IsWindow(hwnd):
                print("⚠️ [FOCUS] Window handle invalid, reacquiring...")
                return False
            if win32gui.IsIconic(hwnd):
                print("🔄 [FOCUS] Window was minimized, restoring...")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                _sleep(0.3)
            current_foreground = win32gui.GetForegroundWindow()
            if current_foreground != hwnd:
                print("🛡️ [FOCUS] Correcting window focus...")
                win32gui.SetForegroundWindow(hwnd)
                _sleep(0.15)
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] != win32con.SW_SHOWMAXIMIZED:
                    print("🔄 [FOCUS] Window not maximized, maximizing...")
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.3)
            except Exception:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    _sleep(0.3)
                except Exception:
                    pass
            return True
        except Exception as e:
            print(f"⚠️ [FOCUS] Focus correction exception: {e}")
            return False

    def ensure_window_ready_and_focused():
        check_for_termination()
        hwnd = ensure_edge_window_ready()
        enforce_window_focus(hwnd)
        return hwnd

    def fast_paste_url(hwnd, url):
        check_for_termination()
        try:
            hud.print("Opening Google Flow...", "navigating")
        except Exception:
            pass
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        _sleep(0.1)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status("Navigating to Google Flow URL...")

    def wait_for_image(image_name, timeout_seconds=40, confidence=0.8, region=None):
        location, _ = wait_for_image_with_fallback(image_name, timeout_seconds, confidence, region)
        return location

    def find_image(image_name, confidence=0.8, region=None):
        location, _ = find_image_with_fallback(image_name, confidence, region)
        return location

    def configure_startup_nanobanana_16ratio9(hwnd):
        """
        Follow the same two-step Nano Banana setup used by Serenum:
        1. Open Nano Banana settings with nanobananaconfig.png.
        2. Select only nanobanana_16ratio9.png.
        3. Confirm the prompt input is reachable before continuing.

        This helper is called once per complete workflow attempt, including
        automatic and shortcut-triggered restarts.
        """
        check_for_termination()
        enforce_window_focus(hwnd)

        print("\n⚙️ [NANO-BANANA] Opening Nano Banana configuration first...")
        update_operation_status(
            "Opening Nano Banana configuration before selecting the 16:9 aspect ratio"
        )

        # STEP 1: Click the Nano Banana configuration control, exactly as Serenum does.
        config_location = wait_for_image(
            "nanobananaconfig.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.8,
        )
        if not config_location:
            message = (
                "nanobananaconfig.png was not found; Nano Banana setup cannot "
                "continue and no scene images will be generated."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        if not _click_google_flow_control(
            hwnd, config_location, "nanobananaconfig.png"
        ):
            message = "Could not click nanobananaconfig.png; no scene images will be generated."
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        print(
            "✅ [NANO-BANANA] Configuration opened. "
            "Now searching exclusively for nanobanana_16ratio9.png."
        )

        # STEP 2: Select only the requested 16:9 ratio. Do not search for 9:16,
        # 3:4, 1:1, or any other Nano Banana ratio asset.
        ratio_location = wait_for_image(
            "nanobanana_16ratio9.png",
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            confidence=0.8,
        )
        if not ratio_location:
            message = (
                "nanobanana_16ratio9.png was not visible after opening Nano Banana "
                "configuration; no scene images will be generated."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        if not _click_google_flow_control(
            hwnd, ratio_location, "nanobanana_16ratio9.png"
        ):
            message = "Could not select nanobanana_16ratio9.png; no scene images will be generated."
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        # Match Serenum's post-selection check: verify the prompt field can be
        # reached only after both Nano Banana controls have been clicked.
        prompt_location = find_whatdoyouwantocreate_with_fallbacks(
            hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS
        )
        if not prompt_location:
            message = (
                "Prompt input did not become available after selecting Nano Banana 16:9; "
                "no scene images will be generated."
            )
            print(f"❌ [NANO-BANANA] {message}")
            raise _NanoBananaStartupFailure(message)

        print(
            "✅ [NANO-BANANA] Startup setup completed in the correct order: "
            "nanobananaconfig.png → nanobanana_16ratio9.png."
        )
        return True

    def move_mouse_to_center_of_screen():
        try:
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            center_x = screen_width // 2
            center_y = screen_height // 2
            pyautogui.moveTo(center_x, center_y, duration=0.15)
            print(f"🖱️ [MOUSE] Moved cursor to screen center ({center_x}, {center_y})")
        except Exception as e:
            print(f"⚠️ [MOUSE] Could not move cursor to center: {e}")

    def move_cursor_below_search(search_location, offset_px=50):
        target_x = int(search_location.x - offset_px)
        target_y = int(search_location.y + offset_px)
        print(
            f"🖱️ [CURSOR] Moving cursor {offset_px}px LEFT and "
            f"{offset_px}px BELOW imagerenderingprogress.png "
            f"to ({target_x}, {target_y})"
        )
        pyautogui.moveTo(target_x, target_y, duration=0.2)
        _sleep(0.3)
        return target_x, target_y

    def click_right_edge_of_image(image_name, confidence=0.7, region=None):
        variants = get_image_variants(image_name)
        for variant_path in variants:
            try:
                location = pyautogui.locateOnScreen(
                    variant_path,
                    confidence=confidence,
                    region=region
                )
                if location:
                    click_x = location.left + int(location.width * 0.95)
                    click_y = location.top + int(location.height / 2)
                    print(f"🎯 [RIGHT-EDGE] Clicking {os.path.basename(variant_path)} right edge at ({click_x}, {click_y})")
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    pyautogui.click()
                    _sleep(0.5)
                    return True
            except Exception:
                pass
        return False

    def scroll_down_multiple(times=3):
        for i in range(times):
            pyautogui.scroll(500)
            _sleep(0.3)
            print(f"⬇️ [SCROLL] Scrolled down ({i+1}/{times}) at current cursor position")
        _sleep(0.5)

    # --- GOOGLE FLOW PAGE-STATE DETECTION / RECOVERY HELPERS ---
    # Page-state priority is intentional:
    #   1. whatdoyouwantocreate.png = already inside the prompt workspace (most advanced)
    #   2. new_project.png          = Google Flow landing / project chooser
    #   3. expandgfsidepanel.png    = likely an existing workspace with its prompt panel collapsed
    #   4. unknown                  = neither recognized page is currently visible
    # The prompt workspace is checked FIRST so a restart never clicks New Project
    # or reloads the URL when it can already continue processing entries.
    def detect_google_flow_stage(hwnd=None):
        check_for_termination()
        if hwnd is not None:
            enforce_window_focus(hwnd)

        prompt_location, prompt_variant = find_image_with_fallback(
            "whatdoyouwantocreate.png", confidence=0.8
        )
        if prompt_location:
            variant_name = os.path.basename(prompt_variant) if prompt_variant else "whatdoyouwantocreate.png"
            print(
                f"✅ [PAGE-STATE] Prompt workspace detected ({variant_name}) at "
                f"({prompt_location.x}, {prompt_location.y})"
            )
            return "prompt", prompt_location

        new_project_location, new_project_variant = find_image_with_fallback(
            "new_project.png", confidence=0.8
        )
        if new_project_location:
            variant_name = os.path.basename(new_project_variant) if new_project_variant else "new_project.png"
            print(
                f"✅ [PAGE-STATE] New Project page detected ({variant_name}) at "
                f"({new_project_location.x}, {new_project_location.y})"
            )
            return "new_project", new_project_location

        expand_location, expand_variant = find_image_with_fallback(
            "expandgfsidepanel.png", confidence=0.8
        )
        if expand_location:
            variant_name = os.path.basename(expand_variant) if expand_variant else "expandgfsidepanel.png"
            print(
                f"✅ [PAGE-STATE] Existing Flow workspace likely detected; prompt panel is "
                f"collapsed ({variant_name}) at ({expand_location.x}, {expand_location.y})"
            )
            return "collapsed_workspace", expand_location

        print(
            "ℹ️ [PAGE-STATE] Neither whatdoyouwantocreate.png nor new_project.png "
            "is visible; no recognized Google Flow page state is currently detected."
        )
        return "unknown", None

    def detect_restart_page_stage(hwnd=None):
        """Restart priority: prompt workspace -> New Project -> URL navigation.

        Do not inspect or act on New Project until the prompt field has first
        been searched for. If neither image is present, return unknown so the
        caller relaunches GOOGLE_FLOW_URL. The collapsed-panel fallback remains
        available after URL navigation through detect_google_flow_stage().
        """
        check_for_termination()
        if hwnd is not None:
            enforce_window_focus(hwnd)

        # Restart page detection must follow the user's exact priority with no
        # intervening image checks: prompt workspace, then New Project, then URL.
        print("🔎 [RESTART-STATE] First checking whatdoyouwantocreate.png...")
        prompt_location, prompt_variant = find_image_with_fallback(
            "whatdoyouwantocreate.png", confidence=0.8
        )
        if prompt_location:
            variant_name = os.path.basename(prompt_variant) if prompt_variant else "whatdoyouwantocreate.png"
            print(
                f"✅ [RESTART-STATE] Prompt workspace found FIRST ({variant_name}) at "
                f"({prompt_location.x}, {prompt_location.y}); New Project will not be checked."
            )
            return "prompt", prompt_location

        print("🔎 [RESTART-STATE] Prompt field not found; now checking new_project.png...")
        new_project_location, new_project_variant = find_image_with_fallback(
            "new_project.png", confidence=0.8
        )
        if new_project_location:
            variant_name = os.path.basename(new_project_variant) if new_project_variant else "new_project.png"
            print(
                f"✅ [RESTART-STATE] New Project found after the prompt-field check "
                f"({variant_name}) at ({new_project_location.x}, {new_project_location.y})."
            )
            return "new_project", new_project_location

        print(
            "ℹ️ [RESTART-STATE] Neither whatdoyouwantocreate.png nor new_project.png "
            "is visible. The restart path will open GOOGLE_FLOW_URL."
        )
        return "unknown", None

    def _click_google_flow_control(hwnd, location, description):
        if location is None:
            return False
        check_for_termination()
        enforce_window_focus(hwnd)
        try:
            pyautogui.moveTo(location.x, location.y, duration=0.1)
            pyautogui.click()
            _sleep(0.8)
            print(f"🖱️ [PAGE-STATE] Clicked {description} at ({location.x}, {location.y})")
            return True
        except Exception as click_error:
            print(f"⚠️ [PAGE-STATE] Could not click {description}: {click_error}")
            return False

    def wait_for_google_flow_stage(hwnd, timeout_seconds=40, check_interval=0.5):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        """Wait for either the prompt workspace or the New Project chooser.

        A collapsed side panel is expanded once, then the prompt field is checked
        again. gfmedia.png is logged as a loading clue only; it is NOT accepted
        as proof that the prompt workspace is ready.
        """
        print(
            f"🔍 [PAGE-STATE] Waiting up to {timeout_seconds}s for either "
            "whatdoyouwantocreate.png or new_project.png..."
        )
        try:
            hud.print("Identifying the current Google Flow page...", "waiting")
        except Exception:
            pass
        update_operation_status("Detecting current Google Flow page state...")

        start_time = time.time()
        last_status_time = start_time
        expanded_panel = False
        gfmedia_reported = False

        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            stage, location = detect_google_flow_stage(hwnd)

            if stage in ("prompt", "new_project"):
                return stage, location

            if stage == "collapsed_workspace" and not expanded_panel:
                print("🔄 [PAGE-STATE] Expanding the existing workspace side panel...")
                if _click_google_flow_control(hwnd, location, "expandgfsidepanel.png"):
                    expanded_panel = True
                    _sleep(0.5)
                    continue
                expanded_panel = True

            if not gfmedia_reported:
                gfmedia_location = find_image("gfmedia.png", confidence=0.8)
                if gfmedia_location:
                    gfmedia_reported = True
                    print(
                        "ℹ️ [PAGE-STATE] gfmedia.png is visible. The Flow page shell has "
                        "loaded, but the required prompt/project control is still being checked."
                    )

            now = time.time()
            if now - last_status_time >= 10:
                elapsed = int(now - start_time)
                print(
                    f"⏳ [PAGE-STATE] Still identifying the Google Flow page "
                    f"({elapsed}s/{timeout_seconds}s)..."
                )
                try:
                    hud.print(f"Identifying the page... ({elapsed}s)", "waiting")
                except Exception:
                    pass
                last_status_time = now

            _sleep(check_interval)

        print(
            f"⏰ [PAGE-STATE] Timed out after {timeout_seconds}s: neither "
            "whatdoyouwantocreate.png nor new_project.png became visible."
        )
        return "timeout", None

    def wait_for_prompt_workspace(hwnd, timeout_seconds=40, check_interval=0.5):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        """Wait specifically for the prompt workspace after opening New Project.

        The New Project button is deliberately ignored during this phase because
        it may remain visible briefly while Flow transitions to the workspace.
        """
        print(
            f"🔍 [PAGE-STATE] Waiting up to {timeout_seconds}s for "
            "whatdoyouwantocreate.png after opening the project..."
        )
        update_operation_status("Waiting for the prompt workspace to become ready...")
        start_time = time.time()
        last_status_time = start_time
        expanded_panel = False
        gfmedia_reported = False

        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)

            prompt_location, prompt_variant = find_image_with_fallback(
                "whatdoyouwantocreate.png", confidence=0.8
            )
            if prompt_location:
                variant_name = os.path.basename(prompt_variant) if prompt_variant else "whatdoyouwantocreate.png"
                print(
                    f"✅ [PAGE-STATE] Prompt workspace is ready ({variant_name}) at "
                    f"({prompt_location.x}, {prompt_location.y})"
                )
                try:
                    hud.print("Workspace is ready.", "success")
                except Exception:
                    pass
                update_operation_status("Prompt workspace detected and ready for scene processing")
                return True

            if not expanded_panel:
                expand_location = find_image("expandgfsidepanel.png", confidence=0.8)
                if expand_location:
                    print("🔄 [PAGE-STATE] Prompt field is not visible; expanding the side panel once...")
                    if _click_google_flow_control(hwnd, expand_location, "expandgfsidepanel.png"):
                        expanded_panel = True
                        _sleep(0.5)
                        continue
                    expanded_panel = True

            if not gfmedia_reported:
                gfmedia_location = find_image("gfmedia.png", confidence=0.8)
                if gfmedia_location:
                    gfmedia_reported = True
                    print(
                        "ℹ️ [PAGE-STATE] gfmedia.png detected; workspace shell is present. "
                        "Still waiting for the actual prompt input control."
                    )

            now = time.time()
            if now - last_status_time >= 10:
                elapsed = int(now - start_time)
                print(
                    f"⏳ [PAGE-STATE] Waiting for prompt workspace "
                    f"({elapsed}s/{timeout_seconds}s)..."
                )
                try:
                    hud.print(f"Waiting for the prompt area... ({elapsed}s)", "waiting")
                except Exception:
                    pass
                last_status_time = now

            _sleep(check_interval)

        print(
            f"⏰ [PAGE-STATE] Prompt workspace did not appear within {timeout_seconds}s. "
            "The automatic supervisor will restart and inspect the current page again."
        )
        return False

    def wait_for_new_project_and_click(hwnd, timeout_seconds=40, initial_location=None):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        """Click New Project using a bounded wait; never wait forever for the image."""
        print("🔍 [GF] Looking for new_project.png before clicking...")
        try:
            hud.print("Starting a fresh workspace...", "waiting")
        except Exception:
            pass
        update_operation_status("Looking for the New Project button...")

        location = initial_location
        if location is None:
            location, _ = wait_for_image_with_fallback(
                "new_project.png", timeout_seconds=timeout_seconds, confidence=0.8
            )

        if not location:
            print(f"❌ [GF] new_project.png was not found within {timeout_seconds}s")
            return False

        if not _click_google_flow_control(hwnd, location, "new_project.png"):
            return False

        try:
            hud.print("Starting a fresh workspace...", "success")
        except Exception:
            pass
        update_operation_status("Clicked New Project; waiting for the prompt workspace")
        return True

    def wait_for_gfmedia_and_confirm(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS):
        """Legacy compatibility helper; bounded and page-state aware."""
        stage, _ = wait_for_google_flow_stage(hwnd, timeout_seconds=timeout_seconds)
        if stage == "prompt":
            return True
        if stage == "new_project":
            return wait_for_new_project_and_click(hwnd, initial_location=None) and wait_for_prompt_workspace(hwnd)
        print("⚠️ [GF] Could not confirm a usable Google Flow page state.")
        return False

    def find_whatdoyouwantocreate_with_fallbacks(hwnd, timeout_seconds=40):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        print(f"🔍 [GF] Searching for whatdoyouwantocreate.png...")
        print(f"🔍 [GF] Step 1: Looking for expandgfsidepanel.png first...")
        try:
            hud.print("Getting the prompt area ready...", "waiting")
        except Exception:
            pass
        update_operation_status("Looking for expand side panel button...")

        expand_variants = get_image_variants("expandgfsidepanel.png")
        if expand_variants:
            expand_panel_location = find_image("expandgfsidepanel.png", confidence=0.8)
            if expand_panel_location:
                print(f"✅ [GF] Found expandgfsidepanel.png - clicking it...")
                try:
                    hud.print("Opening the side panel...", "warning")
                except Exception:
                    pass
                update_operation_status("Clicking expand side panel button")
                pyautogui.moveTo(expand_panel_location.x, expand_panel_location.y, duration=0.1)
                pyautogui.click()
                _sleep(1)
                print(f"🔍 [GF] Now looking for whatdoyouwantocreate.png after expanding panel...")
                location = wait_for_image("whatdoyouwantocreate.png", timeout_seconds=timeout_seconds, confidence=0.8)
                if location:
                    print(f"✅ [GF] Found whatdoyouwantocreate.png after expandgfsidepanel!")
                    return location
                else:
                    print(f"⚠️ [GF] whatdoyouwantocreate.png still not found after expanding panel")
            else:
                print(f"⚠️ [GF] expandgfsidepanel.png not currently visible on screen — will try direct whatdoyouwantocreate lookup")
        else:
            print(f"⚠️ [GF] No expandgfsidepanel.png variants exist in gui_images — falling back to direct lookup")

        print(f"🔍 [GF] Step 2: Direct lookup for whatdoyouwantocreate.png...")
        try:
            hud.print("Looking for the prompt area...", "waiting")
        except Exception:
            pass
        update_operation_status("Looking for whatdoyouwantocreate input field...")
        location = wait_for_image("whatdoyouwantocreate.png", timeout_seconds=timeout_seconds, confidence=0.8)
        if location:
            print(f"✅ [GF] Found whatdoyouwantocreate.png on direct lookup!")
            return location
        print(f"❌ [GF] Could not find whatdoyouwantocreate.png after all attempts")
        return None

    def check_for_tryagain_and_abort():
        tryagain_location = find_image("tryagain.png", confidence=0.7)
        if tryagain_location:
            print(f"❌ [NETWORK] Found tryagain.png — poor network detected!")
            try:
                hud.print("Your internet connection seems unstable — stopping now.", "error")
            except Exception:
                pass
            update_operation_status(
                "Poor network detected (tryagain.png found) — stopping this attempt",
                is_abort=True
            )
            abort_operation("Poor network detected (tryagain.png found)")
            return True
        return False

    def check_and_click_exit_editing():
        """Exit an accidentally opened image editor whenever its Done control appears."""
        nonlocal exit_editing_click_in_progress

        # Prevent a periodic polling pass from double-clicking while an explicit
        # exit editing click is still completing its short UI transition.
        if exit_editing_click_in_progress:
            return False

        exit_editing_click_in_progress = True
        try:
            clicked = click_right_edge_of_image("exit_editinggfimage.png", confidence=0.7)
            if clicked:
                print(
                    "✅ [DONE-EDITING] Clicked the right edge of exit_editinggfimage.png; "
                    "the image editor should now be closed."
                )
                return True
            return False
        finally:
            exit_editing_click_in_progress = False

    def ensure_image_hover_position(timeout_seconds=STAGE_TIMEOUT_SECONDS, offset_px=50):
        """
        Return to the exact cursor anchor recorded when progress was first
        detected. Never re-search imagerenderingprogress after that point.
        """
        nonlocal image_render_lock_active, image_render_lock_position

        if image_render_lock_position is not None:
            target_x, target_y = image_render_lock_position
            image_render_lock_active = True
            set_image_scroll_lock(True)
            current_x, current_y = pyautogui.position()
            if abs(current_x - target_x) > 3 or abs(current_y - target_y) > 3:
                print(
                    f"🛡️ [HOVER-LOCK] Restoring cursor from ({current_x}, {current_y}) "
                    f"to locked position ({target_x}, {target_y})."
                )
                pyautogui.moveTo(target_x, target_y, duration=0.1)
            # Return the original progress-indicator center, not the shifted cursor anchor.
            return type(
                "LockedImagePosition",
                (),
                {"x": target_x + offset_px, "y": target_y - offset_px}
            )()

        # Compatibility fallback for a workflow where the progress indicator
        # never appeared and the legacy generation path completed instead.
        timeout_seconds = _bounded_timeout(timeout_seconds)
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_seconds:
            check_for_termination()
            search_location = find_image("imagerenderingprogress.png", confidence=0.7)
            if search_location:
                image_render_lock_position = (
                    int(search_location.x - offset_px),
                    int(search_location.y + offset_px)
                )
                image_render_lock_active = True
                set_image_scroll_lock(True)
                pyautogui.moveTo(*image_render_lock_position, duration=0.2)
                return search_location
            _sleep(0.4)

        abort_operation(
            f"Could not establish the image hover position within {timeout_seconds} seconds"
        )
        return None

    def _get_render_lock_region(padding_x=None, padding_y=None):
        """
        Return a bounded search rectangle around the ORIGINAL rendering marker.

        image_render_lock_position stores the cursor anchor (50px left and
        50px below the progress marker), so reverse that offset to recover the
        progress marker's centre. This prevents variants elsewhere on the page
        (for example, the false match at the bottom-right of the screen) from
        being treated as active rendering.
        """
        if image_render_lock_position is None:
            return None

        pad_x = int(padding_x if padding_x is not None else RENDER_LOCK_PADDING_X)
        pad_y = int(padding_y if padding_y is not None else RENDER_LOCK_PADDING_Y)
        anchor_x, anchor_y = image_render_lock_position
        marker_x = int(anchor_x + 50)
        marker_y = int(anchor_y - 50)
        screen_width, screen_height = pyautogui.size()

        left = max(0, marker_x - pad_x)
        top = max(0, marker_y - pad_y)
        right = min(int(screen_width), marker_x + pad_x)
        bottom = min(int(screen_height), marker_y + pad_y)
        if right <= left or bottom <= top:
            return None
        return (left, top, right - left, bottom - top)

    def _find_locked_rendering_indicator():
        """Find the rendering marker only in the region established at first detection."""
        region = _get_render_lock_region()
        return find_image(
            "imagerenderingprogress.png",
            confidence=0.78,
            region=region
        )

    def handle_exit_gfsidebar_and_recheck():
        print(f"🔍 [GF] no_active_gf_generation.png not found — looking for exit_gfsidebar.png fallback...")
        exit_sidebar_location = find_image("exit_gfsidebar.png", confidence=0.7)
        if exit_sidebar_location:
            print(f"✅ [GF] Found exit_gfsidebar.png — clicking right edge...")
            variants = get_image_variants("exit_gfsidebar.png")
            clicked = False
            for variant_path in variants:
                try:
                    location = pyautogui.locateOnScreen(variant_path, confidence=0.7)
                    if location:
                        click_x = location.left + int(location.width * 0.95)
                        click_y = location.top + int(location.height / 2)
                        print(f"🎯 [GF] Clicking {os.path.basename(variant_path)} right edge at ({click_x}, {click_y})")
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.8)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                pyautogui.moveTo(exit_sidebar_location.x, exit_sidebar_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.8)
            print(f"🔄 [GF] Re-checking for no_active_gf_generation.png after exit_gfsidebar click...")
            recheck_location = find_image("no_active_gf_generation.png", confidence=0.7)
            if recheck_location:
                print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback!")
                return recheck_location
            else:
                print(f"⚠️ [GF] no_active_gf_generation.png still not found after exit_gfsidebar click")
        else:
            print(f"⚠️ [GF] exit_gfsidebar.png not found either")
        return None

    def paste_prompt_and_click_send(hwnd, entry_json, entry_name):
        print(f"🔍 [SEND-STEP] Looking for whatdoyouwantocreate.png...")
        location = find_whatdoyouwantocreate_with_fallbacks(hwnd, timeout_seconds=30)
        if not location:
            print(f"❌ [SEND-STEP] Could not find the prompt input area")
            try:
                hud.print("Could not find the prompt area.", "error")
            except Exception:
                pass
            update_operation_status(f"Could not find input field for {entry_name}", is_error=True)
            return None

        pyautogui.moveTo(location.x, location.y, duration=0.1)
        pyautogui.click()
        _sleep(0.3)

        print(f"📝 [SEND-STEP] Pasting scene details...")
        try:
            hud.print(f"Preparing {entry_name}...", "typing")
        except Exception:
            pass
        pyautogui.click()
        _sleep(0.1)
        pyautogui.hotkey('ctrl', 'a')
        _sleep(0.05)
        pyautogui.press('backspace')
        _sleep(0.05)
        pyperclip.copy(entry_json)
        pyautogui.hotkey('ctrl', 'v')
        _sleep(0.3)

        print(f"🔍 [SEND-STEP] Looking for sendgf.png (initial click)...")
        send_location = wait_for_image("sendgf.png", timeout_seconds=10, confidence=0.8)
        if not send_location:
            print(f"⚠️ [SEND-STEP] Send button not found - pressing Enter instead...")
            pyautogui.press('enter')
            _sleep(0.5)
            move_mouse_to_center_of_screen()
            return (None, None)

        send_x, send_y = int(send_location.x), int(send_location.y)
        print(f"🎯 [SEND-STEP] RECORDED sendgf location: ({send_x}, {send_y})")

        print(f"🖱️ [SEND-STEP] Moving arrow away from send region before clicking...")
        move_mouse_to_center_of_screen()
        _sleep(0.15)
        pyautogui.click(send_x, send_y)
        _sleep(0.4)
        print(f"✅ [SEND-STEP] Initial click on sendgf.png sent at ({send_x}, {send_y})")
        print(f"🖱️ [SEND-STEP] Moving arrow away from send region after clicking...")
        move_mouse_to_center_of_screen()
        return (send_x, send_y)

    def confirm_sendgf_and_wait_for_generating(hwnd, entry_name, entry_json=None,
                                               send_x=None, send_y=None,
                                               max_confirm_seconds=40, check_interval=0.4):
        max_confirm_seconds = _bounded_timeout(max_confirm_seconds)
        """
        CONFIRMATION RULE:
        - First try gfpromptsent.png and its numbered variants.
        - If gfpromptsent is not visible, use imagerenderingprogress.png and its
          numbered variants as an alternative confirmation that the prompt was sent.
        - Do not use sendgf.png or no_active_gf_generation.png as prompt-sent
          confirmation signals.
        - If neither confirmation image appears within the confirmation window,
          return needs_restart so the existing outer send loop can retry.
        """

        print(
            f"🔎 [SEND-CONFIRM] Confirming prompt for {entry_name}: "
            f"checking gfpromptsent first, with imagerenderingprogress as fallback..."
        )

        if send_x is not None and send_y is not None:
            print(
                f"   ℹ️ Initial send location was ({send_x}, {send_y}); "
                f"confirmation will use on-screen status images."
            )

        try:
            hud.print("Confirming the prompt was sent...", "waiting")
        except Exception:
            pass

        update_operation_status(
            f"Confirming prompt submission for {entry_name} "
            f"(gfpromptsent, with image-rendering fallback)..."
        )

        prompt_sent_variants = get_image_variants("gfpromptsent.png")
        rendering_variants = get_image_variants("imagerenderingprogress.png")

        if prompt_sent_variants:
            print(
                f"🔍 [SEND-CONFIRM] Found {len(prompt_sent_variants)} "
                f"gfpromptsent variant(s)."
            )
            for variant_path in prompt_sent_variants:
                print(f"   • {os.path.basename(variant_path)}")
        else:
            print(
                "⚠️ [SEND-CONFIRM] No gfpromptsent variants found in gui_images; "
                "will rely on imagerenderingprogress if it appears."
            )

        if rendering_variants:
            print(
                f"🔍 [SEND-CONFIRM] Found {len(rendering_variants)} "
                f"imagerenderingprogress variant(s) available as fallback."
            )
            for variant_path in rendering_variants:
                print(f"   • {os.path.basename(variant_path)}")
        else:
            print(
                "⚠️ [SEND-CONFIRM] No imagerenderingprogress variants currently "
                "exist in gui_images."
            )

        start_time = time.time()
        last_status_time = start_time

        while time.time() - start_time < max_confirm_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)

            if check_for_tryagain_and_abort():
                return "poor_network"

            check_and_click_exit_editing()

            # Primary confirmation: prompt-sent image.
            prompt_sent_location, matched_prompt_variant = find_image_with_fallback(
                "gfpromptsent.png",
                confidence=0.8
            )

            if prompt_sent_location:
                matched_name = (
                    os.path.basename(matched_prompt_variant)
                    if matched_prompt_variant
                    else "gfpromptsent variant"
                )
                print(
                    f"✅ [SEND-CONFIRM] {matched_name} found at "
                    f"({prompt_sent_location.x}, {prompt_sent_location.y})."
                )
                print(
                    f"✅ [SEND-CONFIRM] Prompt CONFIRMED SENT using "
                    f"gfpromptsent detection."
                )

                try:
                    hud.print("Prompt sent.", "success")
                except Exception:
                    pass

                update_operation_status(
                    f"Prompt confirmed for {entry_name} (gfpromptsent detected)"
                )
                return "confirmed"

            # Fallback confirmation: rendering progress means Flow has started
            # processing the submitted prompt, even if gfpromptsent is absent.
            rendering_location, matched_rendering_variant = find_image_with_fallback(
                "imagerenderingprogress.png",
                confidence=0.7
            )

            if rendering_location:
                matched_name = (
                    os.path.basename(matched_rendering_variant)
                    if matched_rendering_variant
                    else "imagerenderingprogress variant"
                )
                print(
                    f"✅ [SEND-CONFIRM] gfpromptsent was not found, but "
                    f"{matched_name} was detected at "
                    f"({rendering_location.x}, {rendering_location.y})."
                )
                print(
                    f"✅ [SEND-CONFIRM] Prompt CONFIRMED SENT using "
                    f"image-rendering progress fallback."
                )

                try:
                    hud.print("Prompt sent — image rendering has started.", "success")
                except Exception:
                    pass

                update_operation_status(
                    f"Prompt confirmed for {entry_name} "
                    f"(imagerenderingprogress fallback detected)"
                )
                return "confirmed"

            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(
                    f"⏳ [SEND-CONFIRM] Waiting for gfpromptsent or "
                    f"imagerenderingprogress confirmation... ({elapsed}s elapsed)"
                )
                last_status_time = current_time

            _sleep(check_interval)

        print(
            f"⚠️ [SEND-CONFIRM] Neither gfpromptsent nor "
            f"imagerenderingprogress was detected within "
            f"{max_confirm_seconds}s for {entry_name}."
        )
        print(
            "🔁 [SEND-CONFIRM] Returning needs_restart so the existing send loop "
            "can re-search the prompt input, re-paste, and send again."
        )

        try:
            hud.print(
                "Prompt confirmation not detected — trying the prompt again.",
                "warning"
            )
        except Exception:
            pass

        update_operation_status(
            f"No gfpromptsent or imagerenderingprogress confirmation for "
            f"{entry_name} — re-searching input, re-pasting, and resending"
        )

        return "needs_restart"


    def wait_for_imagerenderingprogress_and_jump_to_search(hwnd, entry_name, max_wait_seconds=40, check_interval=0.4):
        """
        Detect the first rendering marker, lock its cursor position, and wait
        until that SAME marker disappears from its bounded screen region.

        Three consecutive misses are required to avoid a one-frame recognition
        glitch. Importantly, after the first match no full-screen rendering
        searches are performed, so an unrelated variant elsewhere cannot keep
        the function stuck at "Image generation in progress".
        """
        nonlocal image_render_lock_active, image_render_lock_position

        max_wait_seconds = _bounded_timeout(max_wait_seconds)
        print("🔍 [GF-LOCK] Waiting for the FIRST imagerenderingprogress.png match...")
        first_seen_at = time.monotonic()
        rendering_location = None

        # First discovery is full-screen because the anchor is not known yet.
        while time.monotonic() - first_seen_at < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False
            rendering_location = find_image(
                "imagerenderingprogress.png",
                confidence=0.75
            )
            if rendering_location:
                break
            _sleep(check_interval)

        if not rendering_location:
            print(
                f"ℹ️ [GF-LOCK] imagerenderingprogress.png did not appear within "
                f"{max_wait_seconds}s; normal generation fallback may be used."
            )
            return False

        # Record the exact first match and lock the cursor at the required offset.
        image_render_lock_position = (
            int(rendering_location.x - 50),
            int(rendering_location.y + 50)
        )
        image_render_lock_active = True
        set_image_scroll_lock(True)
        target_x, target_y = image_render_lock_position
        render_region = _get_render_lock_region()
        print(
            "🔒 [GF-LOCK] First match recorded at "
            f"({rendering_location.x}, {rendering_location.y}); "
            f"cursor target locked at ({target_x}, {target_y}); "
            f"render search region={render_region}."
        )
        pyautogui.moveTo(target_x, target_y, duration=0.2)

        try:
            hud.print("Image generation in progress...", "processing")
        except Exception:
            pass
        update_operation_status(
            f"Rendering in progress for {entry_name}; monitoring only the original render location"
        )

        render_started = time.monotonic()
        last_status_time = render_started
        missing_samples = 0
        check_interval = max(0.2, min(float(check_interval), 1.0))

        while True:
            check_for_termination()
            enforce_window_focus(hwnd)

            # Modal checks are throttled independently. A false-positive modal
            # header must never block the render-state transition.
            _service_modal_and_restore_locked_cursor()
            restore_locked_cursor()

            # CRITICAL: only search around the first marker, never the whole screen.
            rendering_location = _find_locked_rendering_indicator()
            if rendering_location:
                if missing_samples:
                    print(
                        f"🔁 [GF-LOCK] Rendering marker reappeared in its anchor region; "
                        f"resetting disappearance counter ({missing_samples} → 0)."
                    )
                missing_samples = 0
            else:
                missing_samples += 1
                print(
                    f"🔎 [GF-LOCK] Original rendering marker absent in anchor region "
                    f"({missing_samples}/{RENDER_DISAPPEAR_CONFIRM_SAMPLES})."
                )
                if missing_samples >= RENDER_DISAPPEAR_CONFIRM_SAMPLES:
                    elapsed = int(time.monotonic() - render_started)
                    print(
                        f"✅ [GF-LOCK] Rendering is complete: the original marker was "
                        f"absent for {missing_samples} consecutive checks over "
                        f"approximately {elapsed}s. Handing off to download preparation."
                    )
                    try:
                        hud.print("Rendering complete. Preparing the download...", "success")
                    except Exception:
                        pass
                    update_operation_status(
                        f"Rendering complete for {entry_name}; preparing More/download controls"
                    )
                    return True

            now = time.monotonic()
            if now - last_status_time >= 10:
                elapsed = int(now - render_started)
                status_text = (
                    f"Image generation in progress... ({elapsed}s)"
                    if rendering_location else
                    f"Checking render completion... ({missing_samples}/"
                    f"{RENDER_DISAPPEAR_CONFIRM_SAMPLES} checks)"
                )
                print(f"⏳ [GF-LOCK] {status_text}")
                try:
                    hud.print(status_text, "processing")
                except Exception:
                    pass
                update_operation_status(
                    f"Waiting for original rendering marker to disappear for {entry_name}"
                )
                last_status_time = now

            _sleep(check_interval)


    def wait_for_generation_complete_gf(hwnd, entry_name, max_wait_seconds=40, check_interval=0.5):
        max_wait_seconds = _bounded_timeout(max_wait_seconds)
        print(f"⏳ [GF] Waiting for generation to complete...")
        print(f"🚀 [GF] Attempting fast-path via imagerenderingprogress.png...")
        fastpath_done = wait_for_imagerenderingprogress_and_jump_to_search(
            hwnd, entry_name, max_wait_seconds=max_wait_seconds, check_interval=check_interval
        )
        if fastpath_done:
            print(f"🎉 [GF] Fast-path completed — rendering finished, proceeding to download")
            return True, "complete"
        else:
            print(f"ℹ️ [GF] Fast-path did not trigger — falling back to normal generation wait flow")

        status_counter = 0
        try:
            hud.print("Google Flow image generation in progress... ", "processing")
        except Exception:
            pass
        update_operation_status("Google Flow image generation in progress... ")

        start_time = time.time()
        found_generating = False
        generating_first_seen = None

        print(f"🔍 [GF] Phase 1: Waiting for generatinggf_image.png...")
        while time.time() - start_time < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            check_and_click_exit_editing()
            generating_location = find_image("generatinggf_image.png", confidence=0.7)
            if generating_location:
                print(f"✅ [GF] Found generatinggf_image.png - generation in progress!")
                found_generating = True
                generating_first_seen = time.time()
                status_counter += 1
                try:
                    hud.print("Google Flow image generation in progress... ", "processing")
                except Exception:
                    pass
                update_operation_status("Google Flow image generation in progress... ")
                break
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                status_counter += 1
                print(f"⏳ [GF] Google Flow image generation in progress... ({elapsed}s elapsed, counter={status_counter})")
                try:
                    hud.print("Google Flow image generation in progress... ", "processing")
                except Exception:
                    pass
                update_operation_status("Google Flow image generation in progress... ")
            _sleep(check_interval)

        if not found_generating:
            print(f"⚠️ [GF] generatinggf_image.png not found within timeout — checking fallbacks...")
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            print(f"🔍 [GF] Checking for no_active_gf_generation.png directly...")
            check_and_click_exit_editing()
            no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
            if no_active_location:
                print(f"✅ [GF] Found no_active_gf_generation.png directly — image is ready!")
                try:
                    hud.print("Your image is ready.", "success")
                except Exception:
                    pass
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            recheck = handle_exit_gfsidebar_and_recheck()
            if recheck:
                print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback — image is ready!")
                try:
                    hud.print("Your image is ready.", "success")
                except Exception:
                    pass
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            print(f"❌ [GF] Could not confirm generation completion after all fallbacks")
            return False, "timeout"

        print(f"🔍 [GF] Phase 2: Waiting for generatinggf_image.png to disappear...")
        status_counter += 1
        try:
            hud.print("Google Flow image generation in progress... ", "processing")
        except Exception:
            pass
        update_operation_status("Google Flow image generation in progress... ")

        phase2_start = time.time()
        phase2_timeout = max_wait_seconds - (generating_first_seen - start_time) if generating_first_seen else max_wait_seconds - 30
        if phase2_timeout < 30:
            phase2_timeout = 30

        while time.time() - phase2_start < phase2_timeout:
            check_for_termination()
            enforce_window_focus(hwnd)
            if check_for_tryagain_and_abort():
                return False, "poor_network"
            check_and_click_exit_editing()
            generating_location = find_image("generatinggf_image.png", confidence=0.7)
            if not generating_location:
                print(f"✅ [GF] generatinggf_image.png disappeared - checking for completion...")
                _sleep(0.5)
                check_and_click_exit_editing()
                no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
                if no_active_location:
                    print(f"✅ [GF] Found no_active_gf_generation.png - image is ready!")
                    try:
                        hud.print("Your image is ready.", "success")
                    except Exception:
                        pass
                    update_operation_status(f"Image generation complete for {entry_name}")
                    return True, "complete"
                else:
                    print(f"⚠️ [GF] no_active_gf_generation.png not found yet - trying exit_gfsidebar fallback...")
                    recheck = handle_exit_gfsidebar_and_recheck()
                    if recheck:
                        print(f"✅ [GF] Found no_active_gf_generation.png after exit_gfsidebar fallback - image is ready!")
                        try:
                            hud.print("Your image is ready.", "success")
                        except Exception:
                            pass
                        update_operation_status(f"Image generation complete for {entry_name}")
                        return True, "complete"
                    else:
                        print(f"⚠️ [GF] Still not found - continuing to wait...")
                        for _ in range(10):
                            check_for_termination()
                            _sleep(0.5)
                            if check_for_tryagain_and_abort():
                                return False, "poor_network"
                            check_and_click_exit_editing()
                            no_active_location = find_image("no_active_gf_generation.png", confidence=0.7)
                            if no_active_location:
                                print(f"✅ [GF] Found no_active_gf_generation.png - image is ready!")
                                try:
                                    hud.print("Your image is ready.", "success")
                                except Exception:
                                    pass
                                update_operation_status(f"Image generation complete for {entry_name}")
                                return True, "complete"
                        continue
            else:
                elapsed = int(time.time() - phase2_start)
                if elapsed % 10 == 0 and elapsed > 0:
                    status_counter += 1
                    print(f"⏳ [GF] Google Flow image generation in progress... ({elapsed}s elapsed in phase 2, counter={status_counter})")
                    try:
                        hud.print("Google Flow image generation in progress... ", "processing")
                    except Exception:
                        pass
                    update_operation_status("Google Flow image generation in progress... ")
                _sleep(check_interval)

        print(f"⏰ [GF] Generation timeout after {max_wait_seconds} seconds")
        return False, "timeout"

    # --- ROBUST DOWNLOAD HELPERS ---
    DOWNLOAD_IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"
    }
    DOWNLOAD_TEMP_SUFFIXES = (".crdownload", ".part", ".tmp", ".download")

    def _get_download_directories(extra_directory=None):
        """Discover Windows Downloads and any custom Edge profile download paths."""
        candidates = []

        def _add_directory(value):
            if not value:
                return
            try:
                expanded = os.path.expandvars(os.path.expanduser(str(value).strip().strip('"')))
                if not expanded:
                    return
                absolute = os.path.abspath(expanded)
                normalized = os.path.normcase(absolute)
                if all(os.path.normcase(os.path.abspath(item)) != normalized for item in candidates):
                    candidates.append(absolute)
            except Exception:
                pass

        # Windows Known Downloads directory (including redirected OneDrive paths).
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            import winreg
            registry_locations = (
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            for registry_path in registry_locations:
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                        for value_name in (downloads_guid, "{374DE290-123F-4565-9164-39C4925E467B}"):
                            try:
                                value, _ = winreg.QueryValueEx(key, value_name)
                                _add_directory(value)
                            except OSError:
                                continue
                except OSError:
                    continue
        except Exception as registry_error:
            print(f"ℹ️ [DOWNLOAD] Windows Downloads registry lookup unavailable: {registry_error}")

        # Standard profile fallbacks.
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            _add_directory(os.path.join(user_profile, "Downloads"))
        _add_directory(os.path.expanduser("~/Downloads"))

        # Edge can use a custom directory per browser profile. Read every profile's
        # Preferences file so Profile 1/Profile 2 paths are included as well as Default.
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            edge_user_data = os.path.join(
                local_app_data, "Microsoft", "Edge", "User Data"
            )
            try:
                if os.path.isdir(edge_user_data):
                    for profile_name in os.listdir(edge_user_data):
                        profile_path = os.path.join(edge_user_data, profile_name)
                        preferences_path = os.path.join(profile_path, "Preferences")
                        if not os.path.isdir(profile_path) or not os.path.isfile(preferences_path):
                            continue
                        try:
                            with open(preferences_path, "r", encoding="utf-8") as pref_file:
                                preferences = json.load(pref_file)
                            download_settings = preferences.get("download", {})
                            if isinstance(download_settings, dict):
                                _add_directory(download_settings.get("default_directory"))
                        except Exception as pref_error:
                            print(
                                f"ℹ️ [DOWNLOAD] Could not read Edge profile '{profile_name}' "
                                f"download settings: {pref_error}"
                            )
            except Exception as edge_profile_error:
                print(f"ℹ️ [DOWNLOAD] Edge profile scan unavailable: {edge_profile_error}")

        # Include the project directory in case Edge is configured to save there.
        _add_directory(extra_directory)

        # Keep existing directories first, but retain not-yet-created custom paths
        # because Edge may create them when the download is triggered.
        return candidates

    def _capture_download_snapshot(extra_directory=None):
        """Capture file identity/size/time before clicking Google's download controls."""
        directories = _get_download_directories(extra_directory)
        files = {}
        scanned_count = 0
        for directory in directories:
            if not os.path.isdir(directory):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            if not entry.is_file(follow_symlinks=True):
                                continue
                            stat = entry.stat(follow_symlinks=True)
                            full_path = os.path.abspath(entry.path)
                            files[os.path.normcase(full_path)] = {
                                "mtime_ns": getattr(
                                    stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)
                                ),
                                "size": int(stat.st_size),
                            }
                            scanned_count += 1
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError) as scan_error:
                print(f"⚠️ [DOWNLOAD] Could not snapshot '{directory}': {scan_error}")

        snapshot = {
            "captured_at": time.time(),
            "captured_at_ns": time.time_ns(),
            "directories": directories,
            "files": files,
        }
        print(
            f"📸 [DOWNLOAD] Pre-click download snapshot captured: "
            f"{scanned_count} existing file(s) across {len(directories)} possible folder(s)."
        )
        for directory in directories:
            print(f"   📁 {directory}")
        return snapshot

    def _get_download_image_extension(file_path):
        """Return a supported image extension, using the file signature as fallback."""
        extension = os.path.splitext(file_path)[1].lower()
        if extension in DOWNLOAD_IMAGE_EXTENSIONS:
            return extension
        try:
            with open(file_path, "rb") as image_file:
                header = image_file.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ".png"
            if header.startswith(b"\xff\xd8\xff"):
                return ".jpg"
            if header.startswith((b"GIF87a", b"GIF89a")):
                return ".gif"
            if header.startswith(b"BM"):
                return ".bmp"
            if header.startswith((b"II*\x00", b"MM\x00*")):
                return ".tiff"
            if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
                return ".webp"
        except Exception:
            pass
        return None

    def _download_image_is_valid(file_path):
        """Reject incomplete/corrupt files instead of treating any new file as success."""
        try:
            if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 1024:
                return False
            from PIL import Image
            with Image.open(file_path) as image_file:
                image_file.verify()
            return _get_download_image_extension(file_path) is not None
        except ImportError:
            return _get_download_image_extension(file_path) is not None
        except Exception:
            return False

    def _get_new_download_candidates(snapshot):
        """Return only image files created/changed after the pre-click snapshot."""
        baseline = snapshot.get("files", {}) if isinstance(snapshot, dict) else {}
        directories = snapshot.get("directories", []) if isinstance(snapshot, dict) else []
        candidates = []
        pending_files = []

        for directory in directories:
            if not os.path.isdir(directory):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        try:
                            if not entry.is_file(follow_symlinks=True):
                                continue
                            name = entry.name
                            lower_name = name.lower()
                            full_path = os.path.abspath(entry.path)
                            if lower_name.endswith(DOWNLOAD_TEMP_SUFFIXES):
                                pending_files.append(full_path)
                                continue

                            extension = _get_download_image_extension(full_path)
                            if extension is None:
                                continue

                            stat = entry.stat(follow_symlinks=True)
                            mtime_ns = getattr(
                                stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)
                            )
                            size = int(stat.st_size)
                            key = os.path.normcase(full_path)
                            previous = baseline.get(key)
                            is_new = previous is None
                            is_updated = (
                                previous is not None
                                and (
                                    size != int(previous.get("size", -1))
                                    or mtime_ns > int(previous.get("mtime_ns", 0))
                                )
                            )
                            if is_new or is_updated:
                                candidates.append({
                                    "path": full_path,
                                    "mtime_ns": mtime_ns,
                                    "size": size,
                                    "extension": extension,
                                })
                        except (OSError, PermissionError):
                            continue
            except (OSError, PermissionError) as scan_error:
                print(f"⚠️ [DOWNLOAD] Could not scan '{directory}': {scan_error}")

        candidates.sort(key=lambda item: item["mtime_ns"], reverse=True)
        return candidates, pending_files

    def _wait_for_download_file_stability(file_path, deadline):
        """Wait for a candidate to stop changing, then validate its image contents."""
        previous_signature = None
        stable_samples = 0
        last_logged_size = None

        while time.monotonic() < deadline:
            check_for_termination()
            try:
                stat = os.stat(file_path)
                signature = (
                    int(stat.st_size),
                    getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)),
                )
                if signature[0] > 1024 and signature == previous_signature:
                    stable_samples += 1
                else:
                    stable_samples = 0
                    previous_signature = signature

                if signature[0] != last_logged_size:
                    print(
                        f"   ⏳ [DOWNLOAD] Candidate size: {signature[0]} bytes; "
                        f"waiting for it to stabilize."
                    )
                    last_logged_size = signature[0]

                if stable_samples >= 2:
                    if _download_image_is_valid(file_path):
                        return True
                    # An image can be stable briefly while the browser is still
                    # finalizing it. Keep monitoring until the deadline.
                    stable_samples = 0
            except (OSError, PermissionError):
                previous_signature = None
                stable_samples = 0
            _sleep(0.25)
        return False

    def check_and_rename_download(
        entry_name, images_folder, timeout_seconds=40, check_interval=0.3,
        force_png=False, download_snapshot=None
    ):
        """Find, validate, and move the image created after the pre-click snapshot."""
        timeout_seconds = _bounded_timeout(timeout_seconds)
        print(f"📊 [DOWNLOAD] Monitoring all discovered Windows/Edge download folders for {entry_name}...")
        try:
            hud.print("Waiting for the download to finish...", "waiting")
        except Exception:
            pass
        update_operation_status(f"Waiting for download: {entry_name}")

        if not isinstance(download_snapshot, dict):
            download_snapshot = _capture_download_snapshot(images_folder)
        directories = download_snapshot.get("directories", [])
        if not directories:
            print("❌ [DOWNLOAD] No download directories could be identified.")
            return False, None

        start_time = time.monotonic()
        deadline = start_time + timeout_seconds
        downloaded_file_path = None
        last_status_time = start_time
        last_pending_report = 0.0
        rejected_candidates = set()

        while time.monotonic() < deadline:
            check_for_termination()
            try:
                # The Google Flow confirmation overlay can appear after the
                # download-menu click. Handle it during file monitoring too.
                now = time.monotonic()
                if now - last_pending_report >= 0.8:
                    try:
                        handle_webdownloadconfirmationmodal()
                    except (_WorkflowRestart, _ManualStop):
                        raise
                    except Exception as modal_error:
                        print(f"⚠️ [DOWNLOAD] Confirmation-modal check failed safely: {modal_error}")
                    last_pending_report = now

                check_and_click_exit_editing()
                candidates, pending_files = _get_new_download_candidates(download_snapshot)
                for pending_path in pending_files:
                    # Log partial downloads once per path; Chrome/Edge commonly
                    # use .crdownload while the browser is still writing.
                    if pending_path not in rejected_candidates:
                        print(f"⏳ [DOWNLOAD] Browser is still writing: {pending_path}")
                        rejected_candidates.add(pending_path)

                for candidate in candidates:
                    candidate_path = candidate["path"]
                    if candidate_path in rejected_candidates:
                        continue
                    print(
                        f"🆕 [DOWNLOAD] New/updated image candidate detected: {candidate_path} "
                        f"({candidate['size']} bytes)"
                    )
                    if _wait_for_download_file_stability(candidate_path, deadline):
                        downloaded_file_path = candidate_path
                        print(f"✅ [DOWNLOAD] Stable, valid image confirmed: {downloaded_file_path}")
                        break
                    # Keep an unsteady candidate eligible for another check unless
                    # it disappeared or became invalid; the next scan uses fresh stats.
                    try:
                        if not os.path.exists(candidate_path):
                            rejected_candidates.add(candidate_path)
                    except Exception:
                        pass

                if downloaded_file_path:
                    break

                elapsed = int(time.monotonic() - start_time)
                if time.monotonic() - last_status_time >= 5:
                    print(
                        f"⏳ [DOWNLOAD] Still monitoring for {entry_name}... "
                        f"({elapsed}s elapsed; {len(candidates)} candidate(s), "
                        f"{len(pending_files)} partial download(s))"
                    )
                    try:
                        hud.print(f"Still downloading... ({elapsed}s)", "waiting")
                    except Exception:
                        pass
                    update_operation_status(f"Waiting for download {entry_name}... ({elapsed}s)")
                    last_status_time = time.monotonic()
                _sleep(check_interval)
            except (_WorkflowRestart, _ManualStop):
                raise
            except Exception as monitor_error:
                print(f"⚠️ [DOWNLOAD] Monitoring pass failed safely: {monitor_error}")
                _sleep(check_interval)

        # Final grace scan covers a browser that completed the file right at the
        # timeout boundary; it still requires a stable and valid image.
        if not downloaded_file_path:
            print("🔍 [DOWNLOAD] Performing final cross-folder scan (including timeout grace)...")
            grace_deadline = time.monotonic() + 2.0
            candidates, pending_files = _get_new_download_candidates(download_snapshot)
            for candidate in candidates:
                candidate_path = candidate["path"]
                print(
                    f"🔎 [DOWNLOAD] Final candidate: {candidate_path} "
                    f"({candidate['size']} bytes)"
                )
                if _wait_for_download_file_stability(candidate_path, grace_deadline):
                    downloaded_file_path = candidate_path
                    break

        if not downloaded_file_path:
            print(
                f"❌ [DOWNLOAD] No new/updated valid image was found in any monitored folder. "
                f"Monitored {len(directories)} folder(s):"
            )
            for directory in directories:
                print(f"   • {directory} (exists={os.path.isdir(directory)})")
            return False, None

        try:
            os.makedirs(images_folder, exist_ok=True)
            source_path = os.path.abspath(downloaded_file_path)
            source_extension = _get_download_image_extension(source_path)
            if source_extension is None:
                print(f"❌ [DOWNLOAD] Detected file is not a supported image: {source_path}")
                return False, None

            new_filename = f"{entry_name}.png" if force_png else f"{entry_name}{source_extension}"
            target_path = os.path.abspath(os.path.join(images_folder, new_filename))

            if force_png:
                # Save to a temporary sibling and atomically replace the target.
                # This also handles a source that was already saved as Thumbnail.png.
                temp_target = target_path + ".download_tmp"
                from PIL import Image
                with Image.open(source_path) as source_image:
                    converted = source_image.convert(
                        "RGBA" if "A" in source_image.getbands() else "RGB"
                    )
                    converted.save(temp_target, format="PNG", optimize=True)
                os.replace(temp_target, target_path)
                if os.path.normcase(source_path) != os.path.normcase(target_path):
                    try:
                        os.remove(source_path)
                    except OSError:
                        pass
                print(f"✅ [DOWNLOAD] Thumbnail converted and saved as genuine PNG: {target_path}")
            else:
                if os.path.normcase(source_path) != os.path.normcase(target_path):
                    try:
                        os.replace(source_path, target_path)
                    except OSError:
                        import shutil
                        temporary_copy = target_path + ".download_tmp"
                        shutil.copy2(source_path, temporary_copy)
                        os.replace(temporary_copy, target_path)
                        try:
                            os.remove(source_path)
                        except OSError:
                            pass
                print(f"✅ [DOWNLOAD] Scene image saved as: {target_path}")

            if not _download_image_is_valid(target_path):
                print(f"❌ [DOWNLOAD] Destination image failed final validation: {target_path}")
                return False, None

            print(f"📁 [DOWNLOAD] Verified destination: {target_path}")
            try:
                hud.print("Saved successfully.", "success")
            except Exception:
                pass
            update_operation_status(f"Downloaded and verified: {os.path.basename(target_path)}")
            return True, target_path

        except Exception as save_error:
            print(f"❌ [DOWNLOAD] Failed to move/convert/verify downloaded image: {save_error}")
            traceback.print_exc()
            return False, None

    def download_google_flow_image(hwnd, entry_name, images_folder, force_png=False):
        # These variables belong to sceneiq_google_flow_images_generation_engine(), not this
        # nested function. Declaring them nonlocal also keeps the finally
        # block safe when Alt+/ interrupts the first polling wait.
        nonlocal download_ui_sequence_active
        nonlocal image_render_lock_active, image_render_lock_position

        print(f"📥 [GF-DOWNLOAD] Starting Google Flow download procedure for {entry_name}...")

        # Rendering completion leaves the cursor locked at the original
        # progress-indicator anchor. Do not search for any other UI element
        # except moregf.png until that control is found.
        search_location = ensure_image_hover_position(
            timeout_seconds=STAGE_TIMEOUT_SECONDS,
            offset_px=50
        )

        # Protect the complete download UI sequence from periodic exit editing
        # detection. Hotkeys/timeouts continue to be checked normally.
        download_ui_sequence_active = True
        try:

            print(
                "✅ [GF-DOWNLOAD] Image hover position is confirmed; now preparing "
                "the download controls."
            )
            try:
                hud.print("Preparing the download...", "downloading")
            except Exception:
                pass
            update_operation_status(f"Starting download for {entry_name}...")

            print(
                "🔍 [GF-DOWNLOAD] Step 1 complete: imagerenderingprogress.png was found and "
                "the cursor was moved 50px left and 50px below it before download preparation."
            )

            print(
                "🔒 [GF-DOWNLOAD] Cursor remains locked at the original image position. "
                "Searching ONLY for moregf.png; no scrolling or other UI searches."
            )
            moregf_found = False
            moregf_wait_started = time.monotonic()
            last_more_log = moregf_wait_started

            while not moregf_found:
                check_for_termination()

                # The confirmation modal may appear at any time. Handle it
                # using its existing two-image verification, then restore anchor.
                _service_modal_and_restore_locked_cursor()
                restore_locked_cursor()

                # If rendering has resumed while waiting for More, re-anchor
                # 50px left and 50px below the new progress match, then wait again.
                rendering_again = _find_locked_rendering_indicator()
                if rendering_again:
                    image_render_lock_position = (
                        int(rendering_again.x - 50),
                        int(rendering_again.y + 50)
                    )
                    target_x, target_y = image_render_lock_position
                    image_render_lock_active = True
                    set_image_scroll_lock(True)
                    pyautogui.moveTo(target_x, target_y, duration=0.1)
                    print(
                        "🔁 [GF-DOWNLOAD-LOCK] Rendering indicator reappeared; "
                        f"re-anchored at ({target_x}, {target_y}) and waiting again."
                    )
                    render_again_started = time.monotonic()
                    last_render_again_log = render_again_started

                    while True:
                        check_for_termination()
                        _service_modal_and_restore_locked_cursor()
                        restore_locked_cursor()
                        still_rendering = _find_locked_rendering_indicator()
                        if not still_rendering:
                            elapsed_again = int(time.monotonic() - render_again_started)
                            print(
                                "✅ [GF-DOWNLOAD-LOCK] Rendering indicator disappeared "
                                f"again after {elapsed_again}s; resuming More search."
                            )
                            break
                        now_again = time.monotonic()
                        if now_again - last_render_again_log >= 10:
                            elapsed_again = int(now_again - render_again_started)
                            print(
                                f"⏳ [GF-DOWNLOAD-LOCK] Rendering resumed "
                                f"({elapsed_again}s); waiting without timeout."
                            )
                            last_render_again_log = now_again
                        _sleep(0.4)
                    restore_locked_cursor()
                    continue

                # Search More only after confirming rendering is not active.
                if time.monotonic() - moregf_wait_started > STAGE_TIMEOUT_SECONDS:
                    raise _WorkflowRestart(
                        f"Rendering ended for {entry_name}, but moregf.png was not found "
                        f"within {STAGE_TIMEOUT_SECONDS:.0f}s in the output-card region"
                    )
                # More may be positioned at the edge of the generated result card,
                # so keep its search global. The rendering indicator itself is
                # already restricted to the original anchor region above.
                moregf_location = find_image("moregf.png", confidence=0.75)
                if moregf_location:
                    print(
                        f"✅ [GF-DOWNLOAD] moregf.png found at "
                        f"({moregf_location.x}, {moregf_location.y}); clicking its right edge."
                    )
                    clicked = click_right_edge_of_image("moregf.png", confidence=0.75)
                    if clicked:
                        moregf_found = True
                        image_render_lock_active = False
                        set_image_scroll_lock(False)
                        print(
                            "🔓 [GF-DOWNLOAD] More control found and clicked; "
                            "cursor-position lock released."
                        )
                        break
                    # If the match could not be clicked, restore the anchor and
                    # continue looking ONLY for moregf.png.
                    pyautogui.moveTo(target_x, target_y, duration=0.1)

                now = time.monotonic()
                if now - last_more_log >= 10:
                    elapsed = int(now - moregf_wait_started)
                    print(
                        f"⏳ [GF-DOWNLOAD-LOCK] moregf.png not found after {elapsed}s; "
                        f"cursor remains forced to ({target_x}, {target_y})."
                    )
                    update_operation_status(
                        f"Waiting for moregf.png for {entry_name}; cursor position remains locked"
                    )
                    last_more_log = now
                _sleep(0.4)

            print(f"🔍 [GF-DOWNLOAD] Step 4: Looking for downloadgfimage.png...")
            download_location = wait_for_image("downloadgfimage.png", timeout_seconds=20, confidence=0.7)
            if download_location:
                # CRITICAL: take the filesystem baseline BEFORE the click. The old
                # watcher took its snapshot after the download started, which could
                # miss fast files or classify them as pre-existing.
                download_snapshot = _capture_download_snapshot(images_folder)
                pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.5)
                print(f"✅ [GF-DOWNLOAD] Clicked downloadgfimage.png; pre-click snapshot is active")
            else:
                print(f"❌ [GF-DOWNLOAD] downloadgfimage.png not found — download cannot proceed")
                return False

            print(f"🔍 [GF-DOWNLOAD] Step 5: Looking for gfdownloadquality.png...")
            quality_location = wait_for_image("gfdownloadquality.png", timeout_seconds=15, confidence=0.7)
            if quality_location:
                pyautogui.moveTo(quality_location.x, quality_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.5)
                print(f"✅ [GF-DOWNLOAD] Clicked gfdownloadquality.png")
            else:
                print(f"⚠️ [GF-DOWNLOAD] gfdownloadquality.png not found — download may still proceed...")

            print(f"📊 [GF-DOWNLOAD] Step 6: Monitoring background for new download...")
            try:
                hud.print("Downloading your image...", "downloading")
            except Exception:
                pass
            update_operation_status(f"Downloading {entry_name}...")

            download_success = False
            file_path = None
            download_attempts = 0
            max_download_attempts = 3

            while download_attempts < max_download_attempts and not download_success:
                download_attempts += 1
                print(f"🔄 [GF-DOWNLOAD] Download attempt {download_attempts}/{max_download_attempts}")
                timeout_seconds = 40 if download_attempts == 1 else 30
                download_success, file_path = check_and_rename_download(
                    entry_name,
                    images_folder,
                    timeout_seconds=timeout_seconds,
                    check_interval=0.3,
                    force_png=force_png,
                    download_snapshot=download_snapshot
                )
                if download_success:
                    print(f"✅ [GF-DOWNLOAD] Download successful on attempt {download_attempts}")
                    break

                if download_attempts < max_download_attempts:
                    # A file can finish between the previous timeout return and
                    # the retry UI sequence. Re-scan against the original baseline
                    # before clicking Download again, avoiding duplicate downloads.
                    print("🔎 [GF-DOWNLOAD] Quick late-arrival scan before retrying the UI...")
                    late_success, late_file_path = check_and_rename_download(
                        entry_name,
                        images_folder,
                        timeout_seconds=2,
                        check_interval=0.2,
                        force_png=force_png,
                        download_snapshot=download_snapshot
                    )
                    if late_success:
                        download_success = True
                        file_path = late_file_path
                        print("✅ [GF-DOWNLOAD] Late-arriving download detected; no second click needed.")
                        break

                if download_attempts < max_download_attempts:
                    print(f"⚠️ [GF-DOWNLOAD] Download not found after {timeout_seconds}s — retrying...")
                    try:
                        hud.print(f"Retrying the download... ({download_attempts}/{max_download_attempts})", "warning")
                    except Exception:
                        pass
                    update_operation_status(f"Retrying download for {entry_name}... (attempt {download_attempts + 1})")

                    # Restore the saved anchor directly. The progress indicator
                    # has already disappeared; never search for it again.
                    search_location = ensure_image_hover_position(
                        timeout_seconds=STAGE_TIMEOUT_SECONDS,
                        offset_px=50
                    )
                    print(
                        "🖱️ [GF-DOWNLOAD-RETRY] Required hover position restored; "
                        "retrying the download controls."
                    )

                    target_x, target_y = image_render_lock_position
                    pyautogui.moveTo(target_x, target_y, duration=0.1)
                    more_retry_location = find_image("moregf.png", confidence=0.75)
                    if more_retry_location:
                        click_right_edge_of_image("moregf.png", confidence=0.75)
                    download_location = wait_for_image("downloadgfimage.png", timeout_seconds=10, confidence=0.7)
                    if download_location:
                        pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.5)
                    quality_location = wait_for_image("gfdownloadquality.png", timeout_seconds=10, confidence=0.7)
                    if quality_location:
                        pyautogui.moveTo(quality_location.x, quality_location.y, duration=0.1)
                        pyautogui.click()
                        _sleep(0.5)
                    _sleep(2)

            if download_success:
                print(f"🎉 [GF-DOWNLOAD] {entry_name} downloaded and saved successfully!")
                try:
                    hud.print("Image downloaded successfully.", "success")
                except Exception:
                    pass
                update_operation_status(f"{entry_name} completed successfully", is_success=True)
                return True
            else:
                print(f"❌ [GF-DOWNLOAD] Failed to download {entry_name} after {max_download_attempts} attempts")
                try:
                    hud.print("Could not download the image.", "error")
                except Exception:
                    pass
                update_operation_status(f"Failed to download {entry_name} after multiple attempts", is_error=True)
                return False

        finally:
            download_ui_sequence_active = False
            if not image_render_lock_active:
                set_image_scroll_lock(False)
    def handle_webdownloadconfirmationmodal():
        """
        Handles webdownloadconfirmationmodal.png using a mandatory 2-step
        verification.

        The confirmation button may ONLY be clicked when BOTH of these
        images are currently visible on screen:

            1. webdownloadconfirmationmodal.png
            2. webdownloadmodalappearance.png

        If webdownloadconfirmationmodal.png is visible but
        webdownloadmodalappearance.png is NOT visible, the confirmation
        button is NOT clicked and the function skips it entirely.
        """

        print(f"🔍 [MODAL] Step 1: Checking for webdownloadconfirmationmodal.png...")
        modal_location = find_image(
            "webdownloadconfirmationmodal.png",
            confidence=0.7
        )

        if not modal_location:
            print(
                f"ℹ️ [MODAL] webdownloadconfirmationmodal.png not found "
                f"— proceeding normally"
            )
            return False

        print(
            f"✅ [MODAL] webdownloadconfirmationmodal.png found at "
            f"({modal_location.x}, {modal_location.y})"
        )

        # --------------------------------------------------------------
        # REQUIRED SECOND VERIFICATION
        # --------------------------------------------------------------
        print(
            f"🔍 [MODAL] Step 2: Checking for webdownloadmodalappearance.png..."
        )

        modal_appearance_location = find_image(
            "webdownloadmodalappearance.png",
            confidence=0.7
        )

        if not modal_appearance_location:
            print(
                f"⚠️ [MODAL] webdownloadconfirmationmodal.png was found, "
                f"BUT webdownloadmodalappearance.png was NOT found."
            )
            print(
                f"⏭️ [MODAL] 2-step verification FAILED — "
                f"SKIPPING webdownloadconfirmationmodal click entirely."
            )
            return False

        print(
            f"✅ [MODAL] webdownloadmodalappearance.png found at "
            f"({modal_appearance_location.x}, "
            f"{modal_appearance_location.y})"
        )

        # BOTH required images are visible, so clicking is now permitted.
        print(
            f"🔐 [MODAL] 2-step verification PASSED — "
            f"both required images are visible."
        )
        print(
            f"🖱️ [MODAL] Clicking webdownloadconfirmationmodal.png..."
        )

        try:
            hud.print("Confirming the download...", "warning")
        except Exception:
            pass

        pyautogui.moveTo(
            modal_location.x,
            modal_location.y,
            duration=0.1
        )
        pyautogui.click()
        _sleep(0.5)
        move_mouse_to_center_of_screen()
        _sleep(0.3)

        # --------------------------------------------------------------
        # RE-CHECK AFTER THE FIRST CLICK
        # --------------------------------------------------------------
        print(
            f"🔍 [MODAL] Re-checking both verification images "
            f"after first click..."
        )

        recheck_appearance_location = find_image(
            "webdownloadmodalappearance.png",
            confidence=0.7
        )

        recheck_modal_location = find_image(
            "webdownloadconfirmationmodal.png",
            confidence=0.7
        )

        if recheck_modal_location and recheck_appearance_location:
            print(
                f"⚠️ [MODAL] Both verification images are still visible "
                f"after the first click — clicking confirmation again..."
            )

            pyautogui.moveTo(
                recheck_modal_location.x,
                recheck_modal_location.y,
                duration=0.1
            )
            pyautogui.click()
            _sleep(0.5)
            move_mouse_to_center_of_screen()
            _sleep(0.3)

            print(
                f"✅ [MODAL] Second click completed with both "
                f"verification conditions satisfied."
            )

        elif recheck_modal_location and not recheck_appearance_location:
            print(
                f"ℹ️ [MODAL] webdownloadconfirmationmodal.png is still "
                f"visible, but webdownloadmodalappearance.png is no longer "
                f"visible — NOT clicking again."
            )
            print(
                f"⏭️ [MODAL] Skipping the confirmation button because "
                f"the required 2-step verification is no longer satisfied."
            )

        elif not recheck_modal_location:
            print(
                f"✅ [MODAL] webdownloadconfirmationmodal.png is no longer "
                f"visible — confirmation completed."
            )

        else:
            print(
                f"ℹ️ [MODAL] Verification state changed after the click — "
                f"no additional click required."
            )

        print(
            f"✅ [MODAL] Modal handling completed — proceeding with "
            f"normal protocol"
        )
        return True

    def _service_modal_and_restore_locked_cursor():
        """Check the verified confirmation modal on a short cadence, not every render poll."""
        nonlocal last_render_modal_check_at
        if not image_render_lock_active or image_render_lock_position is None:
            return False

        now = time.monotonic()
        if now - last_render_modal_check_at < RENDER_MODAL_CHECK_INTERVAL:
            restore_locked_cursor()
            return False
        last_render_modal_check_at = now

        handled = False
        try:
            handled = handle_webdownloadconfirmationmodal()
        except (_WorkflowRestart, _ManualStop):
            set_image_scroll_lock(False)
            raise
        except Exception as modal_error:
            print(f"⚠️ [MODAL-LOCK] Modal check failed safely: {modal_error}")
        finally:
            restore_locked_cursor()
        return handled

    IMAGE_FILE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"
    }
    ENTRY_IMAGE_PATTERN = re.compile(
        r"^entry_(\d+)\.(png|jpg|jpeg|gif|webp|bmp|tiff)$",
        re.IGNORECASE
    )
    THUMBNAIL_FILENAME = "Thumbnail.png"

    def _cleanup_project_image_folder(images_folder, expected_entries):
        """
        Keep only entry_N image files within the expected range and Thumbnail.png.
        Delete every other image file, including numbered variants and unrelated
        images. For duplicate formats of the same entry, keep the newest valid
        file and delete the others.
        """
        os.makedirs(images_folder, exist_ok=True)
        valid_entries = {}
        thumbnail_candidates = []

        try:
            filenames = os.listdir(images_folder)
        except OSError as scan_error:
            print(f"❌ [IMAGE-CLEANUP] Could not scan {images_folder}: {scan_error}")
            return False

        for filename in filenames:
            full_path = os.path.join(images_folder, filename)
            if not os.path.isfile(full_path):
                continue

            extension = os.path.splitext(filename)[1].lower()
            stem = os.path.splitext(filename)[0]

            # The one permitted video-level thumbnail is a PNG named Thumbnail.
            if stem.lower() == "thumbnail" and extension == ".png":
                try:
                    if os.path.getsize(full_path) > 0:
                        thumbnail_candidates.append(full_path)
                    else:
                        os.remove(full_path)
                        print(f"🗑️ [IMAGE-CLEANUP] Deleted empty thumbnail: {filename}")
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not inspect {filename}: {cleanup_error}")
                continue

            match = ENTRY_IMAGE_PATTERN.fullmatch(filename)
            if match:
                number = int(match.group(1))
                try:
                    valid_file = os.path.getsize(full_path) > 0
                except OSError:
                    valid_file = False

                if 1 <= number <= expected_entries and valid_file:
                    try:
                        modified = os.path.getmtime(full_path)
                    except OSError:
                        modified = 0
                    valid_entries.setdefault(number, []).append((modified, full_path))
                    continue

            # Delete unrelated images and entry files outside the current script's
            # valid numbering range. Non-image support files are left untouched.
            if extension in IMAGE_FILE_EXTENSIONS:
                try:
                    os.remove(full_path)
                    print(f"🗑️ [IMAGE-CLEANUP] Deleted unrecognized image: {filename}")
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete {filename}: {cleanup_error}")

        # Resolve duplicate entry formats, keeping the newest non-empty image.
        for number, candidates in valid_entries.items():
            candidates.sort(key=lambda item: item[0], reverse=True)
            for _, duplicate_path in candidates[1:]:
                try:
                    os.remove(duplicate_path)
                    print(
                        f"🗑️ [IMAGE-CLEANUP] Deleted duplicate for entry_{number}: "
                        f"{os.path.basename(duplicate_path)}"
                    )
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete duplicate {duplicate_path}: {cleanup_error}")

        # Keep exactly one canonical Thumbnail.png. Prefer the newest valid PNG.
        if thumbnail_candidates:
            thumbnail_candidates.sort(
                key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0,
                reverse=True
            )
            keep_thumbnail = thumbnail_candidates[0]
            canonical_thumbnail = os.path.join(images_folder, THUMBNAIL_FILENAME)
            if os.path.abspath(keep_thumbnail) != os.path.abspath(canonical_thumbnail):
                try:
                    if os.path.exists(canonical_thumbnail):
                        os.remove(canonical_thumbnail)
                    os.replace(keep_thumbnail, canonical_thumbnail)
                    keep_thumbnail = canonical_thumbnail
                except OSError as rename_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not normalize thumbnail filename: {rename_error}")

            for duplicate_path in thumbnail_candidates[1:]:
                if os.path.abspath(duplicate_path) == os.path.abspath(keep_thumbnail):
                    continue
                try:
                    if os.path.exists(duplicate_path):
                        os.remove(duplicate_path)
                        print(
                            "🗑️ [IMAGE-CLEANUP] Deleted duplicate thumbnail: "
                            f"{os.path.basename(duplicate_path)}"
                        )
                except OSError as cleanup_error:
                    print(f"⚠️ [IMAGE-CLEANUP] Could not delete duplicate thumbnail: {cleanup_error}")

        print(
            f"🧹 [IMAGE-CLEANUP] Accepted scene images: "
            f"{sorted(valid_entries.keys())}; thumbnail: "
            f"{'present' if os.path.isfile(os.path.join(images_folder, THUMBNAIL_FILENAME)) else 'missing'}"
        )
        return True

    def _find_entry_image(images_folder, entry_number):
        """Return one non-empty file that exactly matches entry_N.ext."""
        if not os.path.isdir(images_folder):
            return None
        try:
            for filename in os.listdir(images_folder):
                match = ENTRY_IMAGE_PATTERN.fullmatch(filename)
                if match and int(match.group(1)) == int(entry_number):
                    full_path = os.path.join(images_folder, filename)
                    if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                        return full_path
        except OSError as scan_error:
            print(f"⚠️ [VALIDATE] Could not inspect entry_{entry_number}: {scan_error}")
        return None

    def _thumbnail_exists(images_folder):
        thumbnail_path = os.path.join(images_folder, THUMBNAIL_FILENAME)
        try:
            if not os.path.isfile(thumbnail_path) or os.path.getsize(thumbnail_path) <= 0:
                return False
            from PIL import Image
            with Image.open(thumbnail_path) as thumbnail_image:
                if thumbnail_image.format != "PNG":
                    raise ValueError("Thumbnail file is not a genuine PNG image")
                thumbnail_image.verify()
            return True
        except Exception as thumbnail_error:
            if os.path.exists(thumbnail_path):
                try:
                    os.remove(thumbnail_path)
                    print(
                        f"🗑️ [THUMBNAIL] Removed invalid Thumbnail.png: "
                        f"{thumbnail_error}"
                    )
                except OSError as remove_error:
                    print(
                        f"⚠️ [THUMBNAIL] Invalid thumbnail could not be removed: "
                        f"{remove_error}"
                    )
            return False

    def validate_entry_order(images_folder, expected_entries):
        """
        Do not reset valid files when a gap exists. Return the exact missing
        entry numbers so only those images are regenerated.
        """
        if not _cleanup_project_image_folder(images_folder, expected_entries):
            return False, []
        missing_numbers = [
            number
            for number in range(1, expected_entries + 1)
            if _find_entry_image(images_folder, number) is None
        ]
        existing_numbers = [
            number
            for number in range(1, expected_entries + 1)
            if number not in missing_numbers
        ]
        print(f"📊 [VALIDATE] Existing valid entries: {existing_numbers}")
        print(f"📊 [VALIDATE] Missing entries to generate: {missing_numbers}")
        return True, missing_numbers

    def process_prompt_job_gf(
        hwnd, job_name, prompt_text, images_folder,
        success_message, force_png=False
    ):
        """Submit one prompt, verify it was sent, wait for render, and download."""
        if not isinstance(prompt_text, str) or not prompt_text.strip():
            print(f"⚠️ [PROMPT-JOB] Empty prompt for {job_name}")
            return False

        print(f"\n{'='*50}")
        print(f"📝 [PROMPT-JOB] Generating: {job_name}")
        print(f"{'='*50}")
        update_operation_status(f"Preparing image generation for {job_name}...")
        try:
            hud.print(f"Preparing {job_name}...", "processing")
        except Exception:
            pass

        # A restart always begins again at prompt submission. No saved scene
        # or thumbnail phase is trusted as proof of a completed image.
        send_attempt = 0
        send_confirmed = False

        while not send_confirmed:
            send_attempt += 1
            print(f"\\n🔁 [SEND-LOOP] Send attempt #{send_attempt} for {job_name}")
            update_operation_status(
                f"Submitting {job_name} prompt (attempt {send_attempt})..."
            )
            check_and_click_exit_editing()
            send_coords = paste_prompt_and_click_send(hwnd, prompt_text, job_name)
            if send_coords is None:
                print(f"❌ [SEND-LOOP] Could not paste & click send for {job_name}")
                return False

            send_x, send_y = send_coords
            confirm_result = confirm_sendgf_and_wait_for_generating(
                hwnd,
                job_name,
                prompt_text,
                send_x,
                send_y,
                max_confirm_seconds=STAGE_TIMEOUT_SECONDS,
                check_interval=0.4
            )

            if confirm_result == "confirmed":
                print(f"✅ [SEND-LOOP] Prompt confirmed for {job_name}")
                send_confirmed = True
            elif confirm_result in ("needs_restart", "timeout"):
                abort_operation(
                    f"Prompt confirmation was not detected for {job_name} within 40 seconds"
                )
            elif confirm_result == "poor_network":
                print(f"❌ [SEND-LOOP] Poor network detected while submitting {job_name}")
                return False
            elif confirm_result == "aborted":
                print(f"🛑 [SEND-LOOP] Submission aborted for {job_name}")
                return False
            else:
                abort_operation(
                    f"Unexpected send-confirmation result for {job_name}: {confirm_result}"
                )

        print(f"⏳ [PROMPT-JOB] Waiting for Google Flow to render {job_name}...")
        generation_complete, status = wait_for_generation_complete_gf(
            hwnd, job_name, max_wait_seconds=STAGE_TIMEOUT_SECONDS
        )
        if not generation_complete:
            print(f"❌ [PROMPT-JOB] Generation did not complete for {job_name}: {status}")
            update_operation_status(
                f"Generation failed for {job_name}: {status}",
                is_error=True
            )
            if status == "poor_network":
                return False
            abort_operation(f"Generation failed for {job_name}: {status}")
            return False

        print(f"📥 [PROMPT-JOB] Downloading completed image for {job_name}...")
        download_success = download_google_flow_image(
            hwnd, job_name, images_folder, force_png=force_png
        )
        if not download_success:
            print(f"❌ [PROMPT-JOB] Download failed for {job_name}; the job will not be skipped")
            update_operation_status(
                f"Download failed for {job_name}",
                is_abort=True
            )
            abort_operation(f"Download failed for {job_name}")
            return False

        if force_png:
            expected_path = os.path.join(images_folder, THUMBNAIL_FILENAME)
            if not os.path.isfile(expected_path) or os.path.getsize(expected_path) <= 0:
                abort_operation(
                    f"{job_name} download did not produce a valid {THUMBNAIL_FILENAME}"
                )

        print(f"🎉 [PROMPT-JOB] {success_message}")
        try:
            hud.print(f"{success_message}", "success")
        except Exception:
            pass
        update_operation_status(f"{job_name} complete", is_success=True)
        return True

    def process_single_entry_gf(hwnd, entry_index, entry_data, images_folder):
        entry_name = f"entry_{entry_index + 1}"
        entry_json = format_entry_for_paste(entry_data)
        if not entry_json:
            print(f"⚠️ [SCENE] No data found for {entry_name}")
            return False

        return process_prompt_job_gf(
            hwnd=hwnd,
            job_name=entry_name,
            prompt_text=entry_json,
            images_folder=images_folder,
            success_message=f"Scene {entry_index + 1} image is ready and downloaded",
            force_png=False
        )

    def process_thumbnail_gf(hwnd, thumbnail_prompt, images_folder):
        """Generate the single project-level thumbnail after all scene images."""
        print("\n🖼️ [THUMBNAIL] All scene images are verified. Preparing the YouTube thumbnail.")
        update_operation_status("All scene images are complete; generating Thumbnail.png...")
        try:
            hud.print("Generating the YouTube thumbnail...", "processing")
        except Exception:
            pass

        return process_prompt_job_gf(
            hwnd=hwnd,
            job_name="Thumbnail",
            prompt_text=thumbnail_prompt.strip(),
            images_folder=images_folder,
            success_message="YouTube thumbnail generated and saved as Thumbnail.png",
            force_png=True
        )

    def main_google_flow_workflow(force_url_restart=False):
        try:
            if not os.path.exists(GUI_IMAGES):
                print(f"❌ Error: GUI_IMAGES path not found: {GUI_IMAGES}")
                try:
                    hud.print("A required folder is missing.", "error")
                except Exception:
                    pass
                update_operation_status(f"GUI_IMAGES path not found: {GUI_IMAGES}", is_error=True)
                return

            images_folder = _sceneiq_resolve_project_images_folder(
                project_title,
                project_category=project_category,
            )
            print(f"🎬 [MAIN] Starting Google Flow image generation workflow...")
            print(f"🖥️ [MAIN] GUI Images path: {GUI_IMAGES}")
            print(f"📁 [MAIN] Project: '{project_title}'")
            print(f"📁 [MAIN] Images folder: {images_folder}")
            print(f"📊 [MAIN] Total entries: {total_entries}")

            try:
                hud.print(f"Preparing to generate {total_entries} images...", "initializing")
            except Exception:
                pass

            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized; inspecting the current Edge page before navigation")

            # IMPORTANT: on every automatic/manual restart, search in this exact
            # order before navigating: (1) whatdoyouwantocreate, (2) new_project,
            # (3) GOOGLE_FLOW_URL if neither is visible. This prevents a restart
            # from opening a second project when the prompt workspace is ready.
            print("🔎 [MAIN] Inspecting the current Edge page before loading any URL...")
            try:
                hud.print("Checking the current Google Flow page...", "waiting")
            except Exception:
                pass

            if force_url_restart:
                print("🌐 [MAIN] Ctrl+Shift+F12 requested a hard restart; opening GOOGLE_FLOW_URL immediately without inspecting the current page.")
                try:
                    hud.print("Restarting from Google Flow URL...", "navigating")
                except Exception:
                    pass
                if not GOOGLE_FLOW_URL:
                    update_operation_status("GOOGLE_FLOW_URL is empty; cannot perform Ctrl+Shift+F12 restart", is_error=True)
                    return
                fast_paste_url(hwnd, GOOGLE_FLOW_URL)
                _sleep(2)
                hwnd = ensure_window_ready_and_focused()
                current_stage, current_location = wait_for_google_flow_stage(
                    hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS, check_interval=0.5
                )
                print(f"🧭 [MAIN] Page state after forced URL navigation: {current_stage}")
            else:
                current_stage, current_location = detect_restart_page_stage(hwnd)
            print(
                f"🧭 [MAIN] Initial restart page state (prompt checked before New Project): "
                f"{current_stage}"
            )

            if current_stage == "prompt":
                print(
                    "✅ [MAIN] whatdoyouwantocreate.png is already visible. "
                    "Skipping URL navigation and New Project; starting the scene workflow from its entry point." 
                )
                update_operation_status("Existing prompt workspace detected; starting the scene workflow from its entry point")
                page_ready = True

            elif current_stage == "new_project":
                print(
                    "✅ [MAIN] new_project.png is already visible. "
                    "Skipping URL navigation and clicking the existing New Project control."
                )
                clicked = wait_for_new_project_and_click(
                    hwnd, timeout_seconds=20, initial_location=current_location
                )
                if not clicked:
                    update_operation_status("Could not click the detected New Project button", is_error=True)
                    return
                page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

            elif current_stage == "collapsed_workspace":
                print(
                    "✅ [MAIN] An existing Google Flow workspace is detected with its side panel collapsed. "
                    "Skipping URL navigation and expanding the existing workspace."
                )
                if not _click_google_flow_control(hwnd, current_location, "expandgfsidepanel.png"):
                    update_operation_status("Could not expand the existing Google Flow prompt panel", is_error=True)
                    return
                page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

            else:
                if force_url_restart:
                    page_ready = False
                else:
                    print(
                        "🌐 [MAIN] Neither the prompt workspace nor New Project is visible. "
                        "Only now will GOOGLE_FLOW_URL be opened."
                    )
                    try:
                        hud.print("Opening Google Flow because no known page is visible...", "navigating")
                    except Exception:
                        pass
                    update_operation_status("No known Google Flow page detected; opening Google Flow URL")
                    fast_paste_url(hwnd, GOOGLE_FLOW_URL)
                    _sleep(2)
                    hwnd = ensure_window_ready_and_focused()

                    detected_stage, detected_location = wait_for_google_flow_stage(
                        hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS, check_interval=0.5
                    )
                    print(f"🧭 [MAIN] Page state after navigation: {detected_stage}")

                    if detected_stage == "prompt":
                        print("✅ [MAIN] Prompt workspace detected after navigation; no New Project click needed.")
                        page_ready = True

                    elif detected_stage == "new_project":
                        print("✅ [MAIN] New Project chooser detected after navigation; clicking it now.")
                        clicked = wait_for_new_project_and_click(
                            hwnd, timeout_seconds=20, initial_location=detected_location
                        )
                        if not clicked:
                            update_operation_status("Could not click New Project after navigation", is_error=True)
                            return
                        page_ready = wait_for_prompt_workspace(hwnd, timeout_seconds=STAGE_TIMEOUT_SECONDS)

                    else:
                        page_ready = False

            if not page_ready:
                error_message = (
                    "Google Flow did not reach the whatdoyouwantocreate prompt workspace. "
                    "The supervisor will restart and inspect the current page before deciding whether to navigate."
                )
                print(f"❌ [MAIN] {error_message}")
                try:
                    hud.print("The prompt workspace was not detected. Retrying page detection...", "error")
                except Exception:
                    pass
                update_operation_status(error_message, is_error=True)
                return

            # Re-run the Serenum two-step Nano Banana setup on EVERY full workflow
            # attempt, but only after the Google Flow workspace is positively
            # confirmed as loaded and BEFORE project-folder validation or entries.
            # This intentionally runs again after Ctrl+Shift+F12 and auto-recovery.
            print(
                "🟦 [NANO-BANANA] Google Flow page is confirmed loaded. "
                "Running setup for this workflow attempt: "
                "nanobananaconfig.png first, then nanobanana_16ratio9.png."
            )
            configure_startup_nanobanana_16ratio9(hwnd)
            print(
                "✅ [NANO-BANANA] Configuration and 16:9 ratio selected for "
                "this workflow attempt. Continuing to project validation."
            )

            # Project-folder validation and scene-entry inspection happen only
            # AFTER this attempt's Nano Banana configuration is complete.
            valid, missing_entries = validate_entry_order(images_folder, total_entries)
            if not valid:
                print("❌ [MAIN] Project image-folder validation failed")
                return

            # The thumbnail prompt is a project-level field in the JSON, outside
            # the timed script entries. It is only submitted after every entry_N
            # image has been verified.
            latest_panel = _load_panel()
            thumbnail_value = _find_field(latest_panel, ("Thumbnail",))
            thumbnail_prompt = (
                thumbnail_value.strip()
                if isinstance(thumbnail_value, str)
                else ""
            )
            thumbnail_already_exists = _thumbnail_exists(images_folder)
            print(f"📊 [MAIN] Missing scene entries: {missing_entries}")
            print(
                f"🖼️ [MAIN] Thumbnail status: "
                f"{'already generated' if thumbnail_already_exists else 'not generated yet'}"
            )

            if not missing_entries and thumbnail_already_exists:
                print(
                    f"✅ [MAIN] All {total_entries} scene images and Thumbnail.png "
                    "already exist. Verifying project transfer."
                )
                transferred = _transfer_completed_project_to_ready_script(
                    images_folder, total_entries
                )
                if transferred:
                    _set_currently_running(
                        "sceneiq_google_flow_images_generation_engine_successful",
                        status="completed",
                        operation_status=(
                            f"✅ All {total_entries} scene images and Thumbnail.png "
                            "verified and transferred to ready_script.json"
                        )
                    )
                    print("🏁 [GF] Completed project appended to ready_script.json")
                return

            work_items = len(missing_entries) + (0 if thumbnail_already_exists else 1)
            print(
                f"📊 [MAIN] Work remaining: {len(missing_entries)} missing scene image(s), "
                f"{0 if thumbnail_already_exists else 1} thumbnail."
            )

            print(
                "✅ [MAIN] Google Flow prompt workspace is ready; "
                "processing missing scene entries first and the thumbnail last."
            )
            try:
                hud.print("Everything is ready. Starting now...", "success")
            except Exception:
                pass

            processed_job_this_attempt = False

            def _prepare_for_next_prompt_if_needed():
                nonlocal processed_job_this_attempt
                if not processed_job_this_attempt:
                    return
                download_confirmation_handled = handle_webdownloadconfirmationmodal()
                if not download_confirmation_handled:
                    return

                check_for_termination()
                enforce_window_focus(hwnd)
                print(
                    "🔍 [NEXT-PROMPT] Download confirmation handled. "
                    "Checking for generatinggf_image.png before the next prompt..."
                )
                generating_image_location = find_image(
                    "generatinggf_image.png",
                    confidence=0.7
                )
                if generating_image_location:
                    print(
                        "✅ [NEXT-PROMPT] generatinggf_image.png detected at "
                        f"({generating_image_location.x}, {generating_image_location.y}); "
                        "clicking its right edge."
                    )
                    if click_right_edge_of_image("generatinggf_image.png", confidence=0.7):
                        _sleep(0.5)
                        move_mouse_to_center_of_screen()
                        update_operation_status(
                            "Handled generatinggf_image.png after the previous download"
                        )
                    else:
                        print(
                            "⚠️ [NEXT-PROMPT] Could not click the right edge; "
                            "no centre click will be attempted."
                        )
                else:
                    print("ℹ️ [NEXT-PROMPT] generatinggf_image.png not present.")

            # Walk the complete expected range, not just a contiguous suffix.
            # A valid entry_5 is preserved even when entry_3 is missing.
            for i in range(total_entries):
                check_for_termination()
                entry_name = f"entry_{i + 1}"
                existing_image = _find_entry_image(images_folder, i + 1)
                if existing_image:
                    print(
                        f"⏭️ [MAIN] {entry_name} already exists and is valid; "
                        "skipping generation for this entry only."
                    )
                    continue

                _prepare_for_next_prompt_if_needed()
                entry = all_entries[i]
                success = process_single_entry_gf(hwnd, i, entry, images_folder)
                if success:
                    processed_job_this_attempt = True
                    _sleep(2)
                    if _find_entry_image(images_folder, i + 1) is None:
                        abort_operation(
                            f"{entry_name} generation returned success but the file is missing"
                        )
                else:
                    print(
                        f"❌ [MAIN] {entry_name} failed — aborting the entire operation "
                        "(the entry will not be skipped)."
                    )
                    try:
                        hud.print(f"Stopping — {entry_name} did not finish.", "error")
                    except Exception:
                        pass
                    update_operation_status(
                        f"{entry_name} failed — stopping this attempt (never skip)",
                        is_abort=True
                    )
                    abort_operation(f"{entry_name} failed — aborting operation")

            # Final scene-image audit before the thumbnail is allowed to start.
            _cleanup_project_image_folder(images_folder, total_entries)
            missing_after_generation = [
                number
                for number in range(1, total_entries + 1)
                if _find_entry_image(images_folder, number) is None
            ]
            if missing_after_generation:
                abort_operation(
                    "Scene image audit found missing entries: "
                    + ", ".join(f"entry_{number}" for number in missing_after_generation)
                )

            print(
                f"✅ [MAIN] All {total_entries} scene images are present. "
                "The thumbnail phase may now begin."
            )

            # The thumbnail is deliberately generated LAST, and only when the
            # canonical Thumbnail.png is absent or invalid.
            if not _thumbnail_exists(images_folder):
                if not thumbnail_prompt:
                    print(
                        "❌ [THUMBNAIL] All scene images are complete, but panel.json "
                        "has no non-empty 'Thumbnail' prompt. Add the prompt before "
                        "the thumbnail can be generated."
                    )
                    update_operation_status(
                        "Thumbnail prompt is missing or empty; add text to the JSON Thumbnail field",
                        is_error=True
                    )
                    return

                _prepare_for_next_prompt_if_needed()
                thumbnail_success = process_thumbnail_gf(
                    hwnd, thumbnail_prompt, images_folder
                )
                if not thumbnail_success:
                    abort_operation("YouTube thumbnail generation failed")
                processed_job_this_attempt = True
                _sleep(2)
            else:
                print(
                    "⏭️ [THUMBNAIL] Thumbnail.png already exists and is valid; "
                    "skipping thumbnail generation."
                )

            # Strict final folder cleanup and verification before transfer.
            if not _cleanup_project_image_folder(images_folder, total_entries):
                abort_operation("Could not validate the final project image folder")

            missing_after_all = [
                f"entry_{number}"
                for number in range(1, total_entries + 1)
                if _find_entry_image(images_folder, number) is None
            ]
            if not _thumbnail_exists(images_folder):
                missing_after_all.append(THUMBNAIL_FILENAME)

            if missing_after_all:
                abort_operation(
                    "Final image audit failed; missing: " + ", ".join(missing_after_all)
                )

            print(f"\n{'='*60}")
            print(
                f"🎉 [MAIN] All {total_entries} entry images and "
                f"{THUMBNAIL_FILENAME} are generated and verified!"
            )
            print(f"{'='*60}")
            try:
                hud.print("All scene images and the thumbnail are ready.", "success")
            except Exception:
                pass

            transferred = _transfer_completed_project_to_ready_script(
                images_folder, total_entries
            )
            if transferred:
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine_successful",
                    status="completed",
                    operation_status=(
                        f"✅ All {total_entries} entry images plus {THUMBNAIL_FILENAME} "
                        "verified and transferred to ready_script.json"
                    )
                )
                print("🏁 [GF] Completed project appended to ready_script.json")
            else:
                print(
                    "⚠️ [GF] Images are present, but project transfer did not complete."
                )

        except (_WorkflowRestart, _ManualStop):
            set_image_scroll_lock(False)
            raise
        except KeyboardInterrupt as exc:
            raise _ManualStop(str(exc))
        except SystemExit as exc:
            raise _WorkflowRestart(str(exc))
        except Exception as exc:
            print(f"❌ [MAIN] Error: {exc}")
            traceback.print_exc()
            error_message = f"Unexpected error in Google Flow operation: {exc}"
            update_operation_status(error_message, is_error=True)
            try:
                hud.print("Something went wrong. Restarting the workflow...", "warning")
            except Exception:
                pass
            raise _WorkflowRestart(error_message) from exc

    # ------------------------------------------------------------------
    # Full-workflow restart supervisor and global keyboard shortcuts
    # ------------------------------------------------------------------
    # Ctrl+Shift+F12: hard-restart this function by navigating to GOOGLE_FLOW_URL first.
    # Alt+/: stop the function manually.
    # Both shortcuts are registered once and remain active across restarts.
    restart_number = 0
    force_url_restart_pending = False
    restart_hotkey = None
    url_restart_hotkey = None
    stop_hotkey = None

    try:
        url_restart_hotkey = keyboard.add_hotkey("ctrl+shift+f12", on_restart_shortcut, suppress=True)
        print("⌨️ [HOTKEY] Ctrl+Shift+F12 registered: hard restart from GOOGLE_FLOW_URL.")
    except Exception as hotkey_error:
        print(f"⚠️ [HOTKEY] Could not register Ctrl+Shift+F12: {hotkey_error}")

    try:
        stop_hotkey = keyboard.add_hotkey("alt+/", on_terminate_shortcut, suppress=True)
        print("⌨️ [HOTKEY] Alt+/ registered: stop the function manually.")
    except Exception as hotkey_error:
        print(f"⚠️ [HOTKEY] Could not register Alt+/: {hotkey_error}")

    try:
        while True:
            if stop_event.is_set() or terminate_automation:
                print("🛑 [SUPERVISOR] Manual stop requested; exiting the function.")
                break

            if restart_from_url_event.is_set():
                restart_from_url_event.clear()
                force_url_restart_pending = True
                print("🌐 [SUPERVISOR] Ctrl+Shift+F12 received; next attempt will launch GOOGLE_FLOW_URL first.")
            if restart_event.is_set():
                restart_event.clear()
                print("🔁 [SUPERVISOR] Restart request received; rebuilding all run state.")

            restart_number += 1
            operation_status_flag = True
            operation_status_message = ""
            operation_aborted = False

            # Re-read panel.json on every attempt so a restart behaves like a fresh console run.
            try:
                panel_data = _load_panel()
                if not panel_data:
                    raise ValueError("panel.json is empty, missing, or could not be read")
                image_generation_engine = _find_engine(panel_data)
                if image_generation_engine.lower() != "google flow":
                    print(f"ℹ️ [ENGINE] Image generation engine changed to '{image_generation_engine}'; Google Flow worker will stop.")
                    _set_currently_running(
                        None,
                        status="skipped",
                        operation_status=f"Google Flow worker skipped because the selected engine is '{image_generation_engine}'"
                    )
                    break
                project_title = _find_project_title(panel_data)
                script_data = _find_script_data(panel_data)
                all_entries.clear()
                _collect_scene_entries(script_data)
                total_entries = len(all_entries)
            except Exception as reload_error:
                print(f"⚠️ [SUPERVISOR] Could not refresh project configuration: {reload_error}")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Waiting for a readable Google Flow project configuration: {reload_error}"
                )
                _supervisor_wait(3)
                continue

            if total_entries <= 0:
                print("⚠️ [SUPERVISOR] No scene entries found; checking panel.json again in 3 seconds.")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status="No scene entries found yet; waiting and retrying automatically"
                )
                _supervisor_wait(3)
                continue

            print(
                f"\n🔁 [RESTART] Starting Google Flow workflow attempt {restart_number} "
                "from the beginning: reread panel.json, inspect prompt workspace, "
                "then New Project, otherwise navigate to GOOGLE_FLOW_URL; "
                f"project='{project_title}', scenes={total_entries}."
            )
            _set_currently_running(
                "sceneiq_google_flow_images_generation_engine()",
                status="pending",
                operation_status=f"Starting Google Flow workflow attempt {restart_number}"
            )

            try:
                force_this_attempt = force_url_restart_pending
                force_url_restart_pending = False

                main_google_flow_workflow(force_url_restart=force_this_attempt)
            except _WorkflowRestart as restart_reason:
                print(f"🔁 [SUPERVISOR] Restarting from the beginning: {restart_reason}")
                if getattr(restart_reason, "force_url", False):
                    force_url_restart_pending = True
                operation_status_flag = True
                operation_aborted = False
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Automatic restart after: {restart_reason}"
                )
            except _ManualStop as stop_reason:
                print(f"🛑 [SUPERVISOR] {stop_reason}")
                stop_event.set()
                terminate_automation = True
            except _NanoBananaStartupFailure as startup_error:
                print(f"🛑 [SUPERVISOR] Nano Banana setup failed for this workflow attempt: {startup_error}")
                update_operation_status(
                    f"Nano Banana setup failed; scene generation stopped for safety: {startup_error}",
                    is_error=True
                )
                stop_event.set()
                terminate_automation = True
            except Exception as unexpected_error:
                print(f"❌ [SUPERVISOR] Unexpected supervisor error: {unexpected_error}")
                traceback.print_exc()
                operation_status_flag = True
                operation_aborted = False
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status=f"Supervisor caught an error and will retry: {unexpected_error}"
                )

            if stop_event.is_set() or terminate_automation:
                break

            if restart_from_url_event.is_set():
                restart_from_url_event.clear()
                force_url_restart_pending = True
                operation_status_flag = True
                operation_aborted = False
                print("🌐 [SUPERVISOR] Ctrl+Shift+F12 arrived between attempts; restarting from GOOGLE_FLOW_URL.")
                continue
            if restart_event.is_set():
                restart_event.clear()
                operation_status_flag = True
                operation_aborted = False
                print("🔁 [SUPERVISOR] Ctrl+Shift+F12 arrived at the end of an attempt; starting a fresh attempt instead of accepting the old result.")
                _set_currently_running(
                    "sceneiq_google_flow_images_generation_engine()",
                    status="pending",
                    operation_status="Manual Ctrl+Shift+F12 restart requested"
                )
                continue

            final_panel = _load_panel()
            final_running = str(_get_status_value(final_panel, "currently_running", "") or "").strip()
            if final_running == "sceneiq_google_flow_images_generation_engine_successful":
                print("✅ [SUPERVISOR] Workflow completed successfully; no restart is needed.")
                break

            operation_status_flag = True
            operation_aborted = False
            print("🔁 [SUPERVISOR] Workflow is incomplete; the next attempt will re-read panel.json and inspect the current Edge page.")
            try:
                hud.print("The workflow needs recovery. Restarting automatically...", "warning")
            except Exception:
                pass
            _supervisor_wait(2)
    finally:
        for hotkey_handle in (restart_hotkey, url_restart_hotkey, stop_hotkey):
            if hotkey_handle is not None:
                try:
                    keyboard.remove_hotkey(hotkey_handle)
                except Exception:
                    pass

        if stop_event.is_set() or terminate_automation:
            try:
                update_operation_status("Google Flow operation manually stopped by user (Alt+/); work remains resumable")
                hud.show_summary("Stopped at your request.")
            except Exception:
                pass
            print("🛑 [SUPERVISOR] Google Flow function stopped by the user.")

def sceneiq_image_producer_controller_loop(poll_interval=1.0):
    """Continuously supervise the image engine without terminating the process on stop."""
    poll_interval = max(0.25, float(poll_interval or 1.0))
    last_started_signature = None
    last_operation = _sceneiq_read_image_controller_operation()
    if last_operation == "pause":
        hud.notify_modal("Image production has been paused by the remote controller.", persistent=True)
    elif last_operation == "stop":
        hud.notify_modal("Image production is stopped by the remote controller. Waiting for continue/run/restart...", persistent=False)

    print("📡 [IMAGE-CONTROLLER] Remote image controller is active; polling every second.")
    while True:
        operation = _sceneiq_read_image_controller_operation()
        if operation != last_operation:
            previous = last_operation
            last_operation = operation
            notice = None
            persistent = False
            if operation == "pause":
                notice, persistent = "Image production has been paused by the remote controller.", True
            elif operation == "stop":
                notice = "Image production has been stopped by the remote controller. Waiting for a new command..."
            elif operation == "restart":
                notice = "Image production has been restarted by the remote controller. Restarting the workflow..."
                last_started_signature = None
            elif operation == "continue":
                notice = "Image production has resumed by the remote controller."
                if previous == "stop":
                    last_started_signature = None
            elif operation == "run" and previous in {"pause", "stop"}:
                notice = "Image production has resumed. Checking for the next project..."
                if previous == "stop":
                    last_started_signature = None
            if notice:
                hud.notify_modal(notice, persistent=persistent)
                print(f"📡 [IMAGE-CONTROLLER] operation changed: {previous} -> {operation}")

        # Pause/stop are image-only commands. The video service has no dependency
        # on this state and continues its own queue/workers independently.
        if operation in {"pause", "stop"}:
            time.sleep(poll_interval)
            continue

        try:
            with open(PANEL_PATH, "r", encoding="utf-8") as panel_file:
                panel_data = json.load(panel_file)
        except Exception:
            panel_data = {}

        metadata = _sceneiq_get_project_metadata(panel_data)
        engine_name = _sceneiq_normalize_key(metadata.get("engine"))
        title = metadata.get("project_title", "")
        script = metadata.get("script")
        has_script = isinstance(script, (dict, list)) and bool(script)
        if engine_name != "googleflow" or not title or not has_script:
            last_started_signature = None
            time.sleep(poll_interval)
            continue

        try:
            signature_payload = json.dumps(
                {
                    "project_title": title,
                    "project_category": metadata.get("project_category"),
                    "script": script,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        except Exception:
            signature_payload = f"{title}|{metadata.get('project_category')}|{repr(script)}"
        signature = hashlib.sha256(signature_payload.encode("utf-8", errors="replace")).hexdigest()

        # A new project, explicit restart, or continue after a stopped worker may
        # launch one image engine. Never start single and multiple operators together.
        should_start = signature != last_started_signature
        if should_start:
            engine_function, selected_metadata = _sceneiq_select_image_engine_operation(panel_data)
            if engine_function is None:
                print(f"ℹ️ [IMAGE-CONTROLLER] Image engine is not Google Flow: {selected_metadata.get('engine')!r}; waiting.")
                last_started_signature = signature
                time.sleep(poll_interval)
                continue
            operator_text = selected_metadata.get("engineoperator") or "Single operator"
            engine_label = "multiple operator" if engine_function is sceneiq_google_flow_images_generation_engine_mp_opertion else "single operator"
            print(
                f"🎬 [IMAGE-CONTROLLER] Launching {engine_label} for '{title}' "
                f"(automation.engineoperator={operator_text!r})."
            )
            last_started_signature = signature
            try:
                engine_function()
            except KeyboardInterrupt:
                print("🛑 [IMAGE-CONTROLLER] KeyboardInterrupt received; image service is stopping.")
                raise
            except BaseException as engine_error:
                print(f"❌ [IMAGE-CONTROLLER] Image engine ended unexpectedly: {engine_error}")
                traceback.print_exc()
                last_started_signature = None
                time.sleep(2.0)
            # Read the new controller value immediately after an engine exits.
            last_operation = _sceneiq_read_image_controller_operation()
        else:
            time.sleep(poll_interval)


def main():
    """Run only the Google Flow image-producer controller in this process."""
    print("\n" + "=" * 72)
    print("🚀 SCENEIQ IMAGE PRODUCER — STANDALONE")
    print("=" * 72)
    print(f"📄 PANEL_PATH: {PANEL_PATH}")
    print(f"📄 READY_SCRIPT: {READY_SCRIPT}")
    print(f"📁 IMAGES_PATH: {IMAGES_PATH}")
    print("ℹ️ Video production is not started or imported by this script.")
    sceneiq_image_producer_controller_loop()


if __name__ == "__main__":
    main()
