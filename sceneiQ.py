import pyautogui
from PIL import Image
import os
import glob
from datetime import datetime
import subprocess
import json
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
import zipfile
import csv
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from moviepy import ImageClip
import os
import re
import json
import shutil
import os
import json
import warnings
from datetime import datetime
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, VideoClip, CompositeVideoClip
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix protobuf compatibility
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Import the library
from chrome_lens_py import LensAPI




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
READY_SCRIPT = r"C:\xampp\htdocs\AI automation\scenIQ\ready_script.json"
GUI_REGION_SAVER = r"C:\xampp\htdocs\AI automation\scenIQ\gui.json"
SUBSCRIBE_STICKERS = r"C:\xampp\htdocs\AI automation\scenIQ\subscribe"

class AutomationHUD:
    def __init__(self):
        self.root = None
        self.label_status = None
        self.visible = True
        self.current_text = "Initializing..."
        self.status_history = []
        self.current_status_type = "initializing"
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
        
        self.root.mainloop()

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
hud = AutomationHUD()

def fetch_settings():
    """
    Launches/uses Microsoft Edge for phpMyAdmin operations.
    Gets settings from sceneiq_config and saves to PANEL_PATH.
    Uses clipboard-based communication only.
    Uses PHPSQLURL as the phpMyAdmin URL.
    Creates default files if they don't exist or are invalid.
    Window remains open after completion.
    Automatically cleans and repairs JSON data.
    Removes outer array wrapper.

    Executes only when currently_running is None/"none"/empty or "fetch_settings()".
    Sets currently_running to "fetch_settings()" on start.
    On full success sets currently_running to "fetch_settings_successful".
    """
    import os
    import json
    import time
    import shutil
    import subprocess
    import traceback
    import re

    try:
        import pyautogui
        import pyperclip
        import win32api
        import win32con
        import win32gui
        import win32process
        import psutil
    except ImportError as e:
        print(f"❌ [FETCH] Missing dependency: {e}")
        return False

    pyautogui.PAUSE = 0.0

    # Termination flag
    terminate_automation = False
    MAX_OPERATION_RETRIES = 5

    def check_for_termination():
        if terminate_automation:
            raise KeyboardInterrupt("User forced exit via shortcut key.")

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
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ [STATUS] Failed to save panel: {e}")
            return False

    def _get_currently_running():
        data = _load_panel()
        val = data.get("currently_running")
        if val is None:
            return None
        val = str(val).strip()
        if val.lower() in ("", "none", "null"):
            return None
        return val

    def _set_currently_running(value, status=None, operation_status=None):
        data = _load_panel()
        data["currently_running"] = value
        if status is not None:
            data["status"] = status
        if operation_status is not None:
            data["operation_status"] = operation_status
        return _save_panel(data)

    # ----- Gate: only run when allowed -----
    current = _get_currently_running()
    allowed = (current is None) or (current == "fetch_settings()")
    if not allowed:
        print(f"⏭️ [FETCH] Skipping – currently_running is '{current}' (expected None or 'fetch_settings()')")
        return False

    # Claim the slot
    _set_currently_running("fetch_settings()", status="pending",
                           operation_status="Running fetch_settings()")
    print("🔒 [FETCH] Claimed currently_running = 'fetch_settings()'")

    # -----------------------------------------------------------------
    # Helper functions (self-contained)
    # -----------------------------------------------------------------
    def ensure_panel_path_exists():
        if os.path.exists(PANEL_PATH):
            try:
                with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if not content:
                        return False
                    json.loads(content)
                return True
            except Exception:
                try:
                    os.remove(PANEL_PATH)
                except Exception:
                    pass

        default_config = {
            "url": PHPSQLURL,
            "author": "Brilliance",
            "engine": "csv",
            "page": "none",
            "group": "include",
            "processjpgfrom": "freshjpgs",
            "status": "pending",
            "currently_running": "fetch_settings()",
            "operation_status": "Initializing"
        }
        try:
            os.makedirs(os.path.dirname(PANEL_PATH) or '.', exist_ok=True)
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(default_config, file, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def clean_and_repair_json(content):
        try:
            return json.loads(content)
        except Exception:
            pass
        try:
            cleaned = content.strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
                cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            try:
                return json.loads(cleaned)
            except Exception:
                pass
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
                    inner = parsed[0]
                    if inner.startswith('{') or inner.startswith('['):
                        return json.loads(inner)
            except Exception:
                pass
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            cleaned = cleaned.replace('\\n', ' ').replace('\\r', ' ').replace('\\t', ' ')
            cleaned = cleaned.replace('"true"', 'true').replace('"false"', 'false')
            cleaned = cleaned.replace("'true'", 'true').replace("'false'", 'false')
            cleaned = cleaned.replace('"null"', 'null').replace("'null'", 'null')
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            json_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1)
            try:
                return json.loads(cleaned)
            except Exception:
                pass
            return {}
        except Exception as e:
            print(f"⚠️ [CLEAN] Error cleaning JSON: {e}")
            return {}

    def clean_json_data(data):
        if isinstance(data, dict):
            return {k: clean_json_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [clean_json_data(item) for item in data]
        elif isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                try:
                    return clean_json_data(json.loads(stripped))
                except Exception:
                    pass
            elif stripped.startswith('[') and stripped.endswith(']'):
                try:
                    return clean_json_data(json.loads(stripped))
                except Exception:
                    pass
            elif stripped.lower() == 'true':
                return True
            elif stripped.lower() == 'false':
                return False
            elif stripped.lower() == 'null':
                return None
            return data
        return data

    def remove_outer_array_wrapper(data):
        if isinstance(data, list):
            if len(data) == 1:
                return data[0]
            return data
        return data

    def repair_json_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            cleaned_data = clean_and_repair_json(content)
            cleaned_data = remove_outer_array_wrapper(cleaned_data)
            final_data = clean_json_data(cleaned_data)
            # Preserve status fields if they exist
            existing = _load_panel()
            if isinstance(final_data, dict):
                for key in ("status", "currently_running", "operation_status"):
                    if key in existing and key not in final_data:
                        final_data[key] = existing[key]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            return True, final_data
        except Exception as e:
            print(f"❌ [REPAIR] Failed to repair JSON: {e}")
            return False, None

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
        print(f"🖥️ [WATCHDOG] Monitor bounds: {current_monitor}")
        edge_windows = get_edge_window_on_monitor(current_monitor)

        if edge_windows:
            hwnd = edge_windows[0]['hwnd']
            print(f"🪟 [WATCHDOG] Found existing Edge window handle: {hwnd}")
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.3)
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                time.sleep(0.5)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.2)
                except Exception:
                    try:
                        pyautogui.hotkey('alt', 'tab')
                        time.sleep(0.3)
                    except Exception:
                        pass
                return hwnd
            except Exception:
                return hwnd

        subprocess.Popen([edge_path, "about:blank"])
        for attempt in range(20):
            check_for_termination()
            time.sleep(0.5)
            edge_windows = get_edge_window_on_monitor(current_monitor)
            if edge_windows:
                hwnd = edge_windows[0]['hwnd']
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.3)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.5)
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.2)
                    except Exception:
                        pass
                    return hwnd
                except Exception:
                    continue
        raise RuntimeError("Failed to get or launch Edge window")

    def enforce_window_focus(hwnd):
        check_for_termination()
        try:
            if not win32gui.IsWindow(hwnd):
                return ensure_edge_window_ready()
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.3)
            current_foreground = win32gui.GetForegroundWindow()
            if current_foreground != hwnd:
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.15)
                except Exception:
                    try:
                        pyautogui.hotkey('alt', 'tab')
                        time.sleep(0.3)
                    except Exception:
                        pass
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] != win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
            except Exception:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
                except Exception:
                    pass
            return hwnd
        except Exception:
            return hwnd

    def ensure_window_ready_and_focused():
        check_for_termination()
        hwnd = ensure_edge_window_ready()
        return enforce_window_focus(hwnd)

    def fast_paste_url(hwnd, url, retry_count=0):
        check_for_termination()
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        try:
            hwnd = enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.1)
            hwnd = enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')
            return True, hwnd
        except Exception:
            if retry_count < 3:
                time.sleep(0.5)
                hwnd = ensure_window_ready_and_focused()
                return fast_paste_url(hwnd, url, retry_count + 1)
            return False, hwnd

    def wait_for_clipboard_content(expected_contains=None, timeout=60, check_interval=0.5):
        check_for_termination()
        start_time = time.time()
        while time.time() - start_time < timeout:
            check_for_termination()
            try:
                current_content = pyperclip.paste()
                if current_content and current_content.strip():
                    if expected_contains:
                        if expected_contains in current_content:
                            return current_content
                    else:
                        return current_content
            except Exception:
                pass
            time.sleep(check_interval)
        return None

    def wait_for_enter_confirmation(timeout=5, check_interval=0.3):
        start_time = time.time()
        while time.time() - start_time < timeout:
            check_for_termination()
            try:
                current_content = pyperclip.paste()
                if current_content and "enter button activated" in current_content:
                    return True
            except Exception:
                pass
            time.sleep(check_interval)
        return False

    def create_backup_file(file_path):
        backup_path = file_path + ".backup"
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_path)
            return backup_path
        return None

    def restore_from_backup(file_path):
        backup_path = file_path + ".backup"
        if os.path.exists(backup_path):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                shutil.copy2(backup_path, file_path)
                os.remove(backup_path)
                return True
            except Exception:
                return False
        return False

    def wait_for_clipboard_data_with_retry(max_retries=15, retry_delay=1.0, min_content_length=10, hwnd=None):
        print(f"⏳ [CLIPBOARD] Waiting for data with {max_retries} retries...")
        previous_content = None
        enter_confirmation_seen = False
        for attempt in range(max_retries):
            check_for_termination()
            try:
                current_content = pyperclip.paste()
                if current_content and current_content.strip():
                    content_length = len(current_content.strip())
                    if "enter button activated" in current_content:
                        if not enter_confirmation_seen:
                            print("ℹ️ [CLIPBOARD] Enter confirmation received, waiting for actual data...")
                            enter_confirmation_seen = True
                        previous_content = current_content
                        time.sleep(retry_delay)
                        continue
                    if current_content != previous_content:
                        print(f"📋 [CLIPBOARD] Attempt {attempt + 1}/{max_retries}: New content found ({content_length} chars)")
                        if content_length > min_content_length:
                            return current_content
                        else:
                            print(f"⚠️ [CLIPBOARD] Content too short ({content_length} chars), waiting...")
                    else:
                        print(f"⏳ [CLIPBOARD] Attempt {attempt + 1}/{max_retries}: No new content")
                else:
                    print(f"⏳ [CLIPBOARD] Attempt {attempt + 1}/{max_retries}: Empty clipboard")
                previous_content = current_content
            except Exception as e:
                print(f"⚠️ [CLIPBOARD] Error reading: {e}")
            if attempt > 0 and attempt % 5 == 0 and hwnd:
                try:
                    hwnd = enforce_window_focus(hwnd)
                except Exception:
                    pass
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        return None

    def clean_clipboard_data(raw_data):
        try:
            data = raw_data.strip()
            if data.startswith('"') and data.endswith('"'):
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, str):
                        data = parsed
                except Exception:
                    data = data[1:-1]
                    data = data.replace('\\"', '"').replace('\\\\', '\\')
            json_match = re.search(r'(\{.*\}|\[.*\])', data, re.DOTALL)
            if json_match:
                data = json_match.group(1)
            bracket_count = 0
            in_string = False
            escape_next = False
            end_pos = -1
            for i, char in enumerate(data):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char in '{[':
                        bracket_count += 1
                    elif char in '}]':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i + 1
                            break
            if end_pos > 0:
                data = data[:end_pos]
            data = re.sub(r',\s*}', '}', data)
            data = re.sub(r',\s*]', ']', data)
            data = data.replace('"true"', 'true').replace('"false"', 'false')
            data = data.replace("'true'", 'true').replace("'false'", 'false')
            data = data.replace('"null"', 'null').replace("'null'", 'null')
            return data
        except Exception as e:
            print(f"⚠️ [CLEAN] Error cleaning clipboard data: {e}")
            return raw_data

    def overwrite_file_with_content(file_path, content):
        try:
            cleaned_content = clean_clipboard_data(content)
            try:
                parsed_content = json.loads(cleaned_content)
                parsed_content = remove_outer_array_wrapper(parsed_content)
                parsed_content = clean_json_data(parsed_content)
                # Preserve status fields
                existing = _load_panel()
                if isinstance(parsed_content, dict):
                    for key in ("status", "currently_running", "operation_status"):
                        if key in existing:
                            parsed_content[key] = existing[key]
                content = json.dumps(parsed_content, indent=2, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(f"⚠️ [PARSE] Initial parse failed: {e}, trying deeper cleaning...")
                try:
                    parsed_content = clean_and_repair_json(cleaned_content)
                    parsed_content = remove_outer_array_wrapper(parsed_content)
                    parsed_content = clean_json_data(parsed_content)
                    existing = _load_panel()
                    if isinstance(parsed_content, dict):
                        for key in ("status", "currently_running", "operation_status"):
                            if key in existing:
                                parsed_content[key] = existing[key]
                    content = json.dumps(parsed_content, indent=2, ensure_ascii=False)
                except Exception as e2:
                    print(f"⚠️ [PARSE] Deep cleaning failed: {e2}")
                    content = cleaned_content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ [SAVE] Error saving file: {e}")
            return False

    def execute_sql_query_and_save(hwnd, sql_query, file_path, operation_description, retry_count=0):
        try:
            print(f"\n{'='*60}")
            print(f"🚀 [OPERATION] {operation_description} (Attempt {retry_count + 1}/{MAX_OPERATION_RETRIES})")
            print(f"📝 [SQL] {sql_query}")
            print(f"💾 [OUTPUT] {file_path}")
            print(f"{'='*60}")

            print("⌨️ [STEP 1] Ensuring window focus and maximized state...")
            hwnd = enforce_window_focus(hwnd)
            time.sleep(0.2)

            print("⌨️ [STEP 2] Pressing Tab to focus textarea...")
            hwnd = enforce_window_focus(hwnd)
            pyautogui.press('tab')
            time.sleep(0.5)

            print("⌨️ [STEP 3] Ctrl+A to select all text...")
            hwnd = enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)

            print("⌨️ [STEP 4] Deleting text...")
            pyautogui.press('delete')
            time.sleep(0.3)

            print(f"⌨️ [STEP 5] Typing SQL query: {sql_query}")
            hwnd = enforce_window_focus(hwnd)
            pyperclip.copy(sql_query)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)

            print("⌨️ [STEP 6] Pressing Enter to execute query...")
            hwnd = enforce_window_focus(hwnd)
            pyautogui.press('enter')

            enter_confirmed = wait_for_enter_confirmation(timeout=5)
            if enter_confirmed:
                print("✅ [STEP 6] Enter confirmed")
            else:
                print("⚠️ [STEP 6] Enter not confirmed, but proceeding")

            print("⏳ [STEP 7] Waiting for query execution...")
            time.sleep(2.0)

            print("⌨️ [STEP 8] Pressing Ctrl+M to copy results...")
            hwnd = enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', 'm')
            time.sleep(1.0)

            print("⏳ [STEP 9] Waiting for clipboard data...")
            backup_created = create_backup_file(file_path)

            final_result = wait_for_clipboard_data_with_retry(
                max_retries=20,
                retry_delay=1.0,
                min_content_length=20,
                hwnd=hwnd
            )

            if not final_result:
                error_msg = (f"SQL query '{sql_query}' executed but no data was returned "
                             f"or the clipboard was empty after 20 retry attempts.")
                print(f"❌ {error_msg}")
                if retry_count < MAX_OPERATION_RETRIES - 1:
                    print("🔄 [RETRY] Operation failed, retrying in 2 seconds...")
                    time.sleep(2)
                    hwnd = enforce_window_focus(hwnd)
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, operation_description, retry_count + 1
                    )
                if backup_created and os.path.exists(file_path + ".backup"):
                    restore_from_backup(file_path)
                return False, error_msg

            print(f"✅ [STEP 9] Data received successfully: {len(final_result)} characters")
            print(f"💾 [STEP 10] Overwriting file {file_path} with data...")
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

            print("🧹 [STEP 11] Cleaning and repairing JSON data...")
            if overwrite_file_with_content(file_path, final_result):
                print("✅ [STEP 11] Data cleaned and saved successfully!")
                backup_path = file_path + ".backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return True, None
            else:
                error_msg = f"Failed to clean and save data to {file_path}."
                print(f"❌ {error_msg}")
                if retry_count < MAX_OPERATION_RETRIES - 1:
                    print("🔄 [RETRY] File save failed, retrying in 2 seconds...")
                    time.sleep(2)
                    hwnd = enforce_window_focus(hwnd)
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, operation_description, retry_count + 1
                    )
                if backup_created and os.path.exists(file_path + ".backup"):
                    restore_from_backup(file_path)
                return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error during SQL execution: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            if retry_count < MAX_OPERATION_RETRIES - 1:
                print("🔄 [RETRY] Exception occurred, retrying in 2 seconds...")
                time.sleep(2)
                try:
                    hwnd = ensure_window_ready_and_focused()
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, operation_description, retry_count + 1
                    )
                except Exception:
                    pass
            try:
                backup_path = file_path + ".backup"
                if os.path.exists(backup_path):
                    restore_from_backup(file_path)
            except Exception:
                pass
            return False, error_msg

    # ============================================================
    # MAIN EXECUTION
    # ============================================================
    try:
        errors_encountered = []
        warnings_encountered = []

        if not ensure_panel_path_exists():
            error_msg = "The configuration file could not be created or validated. Please check file permissions and disk space."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
        except json.JSONDecodeError as e:
            error_msg = f"The configuration file contains invalid JSON: {str(e)}. Please check the file format."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Failed to read the configuration file: {str(e)}. Check file permissions."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        phpmyadmin_url = PHPSQLURL
        print(f"🔍 [PHPMYADMIN] Using PHPSQLURL: {phpmyadmin_url}")

        try:
            hwnd = ensure_window_ready_and_focused()
        except Exception as e:
            error_msg = f"Failed to launch or focus Microsoft Edge: {str(e)}. Check if Edge is installed and accessible."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        success, hwnd = fast_paste_url(hwnd, phpmyadmin_url)
        if not success:
            error_msg = f"Failed to navigate to '{phpmyadmin_url}'. The browser may have issues loading the page."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        print("⏳ [NAVIGATION] Waiting for page to load...")
        page_ready = None
        for attempt in range(MAX_OPERATION_RETRIES):
            hwnd = enforce_window_focus(hwnd)
            if attempt > 0:
                print(f"🔄 [NAVIGATION] Reloading page (attempt {attempt + 1})...")
                pyautogui.hotkey('ctrl', 'r')
                time.sleep(2)
                hwnd = enforce_window_focus(hwnd)
            page_ready = wait_for_clipboard_content(
                expected_contains="page is ready",
                timeout=15 if attempt == 0 else 10,
                check_interval=0.5
            )
            if page_ready:
                print(f"✅ [NAVIGATION] Page is ready (attempt {attempt + 1})")
                break
            else:
                print(f"⚠️ [NAVIGATION] Page not ready (attempt {attempt + 1})")
                time.sleep(1)

        if not page_ready:
            error_msg = (f"The phpMyAdmin page at '{phpmyadmin_url}' failed to load after "
                         f"{MAX_OPERATION_RETRIES} attempts. Check if the URL is accessible and the server is running.")
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        print("✅ [NAVIGATION] Page is ready")
        hwnd = enforce_window_focus(hwnd)

        # OPERATION: Get settings from sceneiq_config
        sql_query = "select settings from sceneiq_config"
        success, error_msg = execute_sql_query_and_save(
            hwnd, sql_query, PANEL_PATH,
            "Fetching settings from sceneiq_config"
        )

        if not success:
            if error_msg:
                errors_encountered.append(error_msg)
            else:
                error_msg = ("The SQL query 'select settings from sceneiq_config' executed but failed "
                             "to return valid data. Check if the 'sceneiq_config' table exists and contains data.")
                errors_encountered.append(error_msg)
            _set_currently_running("fetch_settings()", status="error",
                                   operation_status=f"❌ {error_msg}")
            return False

        print("✅ [OPERATION] Settings fetched and saved successfully")

        # Final JSON repair
        print("🔄 [REPAIR] Running final JSON repair...")
        repair_success, repaired_data = repair_json_file(PANEL_PATH)
        if repair_success:
            print("✅ [REPAIR] JSON file successfully repaired")
        else:
            print("⚠️ [REPAIR] Could not repair JSON file, but data was saved")
            warnings_encountered.append("JSON data may not be fully valid")

        # SUCCESS – hand off
        _set_currently_running(
            "fetch_settings_successful",
            status="pending",
            operation_status="✅ fetch_settings completed successfully"
        )
        print("🏁 [FETCH] currently_running set to 'fetch_settings_successful'")

        print(f"{'='*60}")
        print("✅ [PHPMYADMIN] OPERATION COMPLETED!")
        print("ℹ️ Browser window remains open for your use.")

        if warnings_encountered:
            print(f"\n⚠️ WARNINGS ({len(warnings_encountered)}):")
            for warning in warnings_encountered[:5]:
                print(f"    - {warning}")
            if len(warnings_encountered) > 5:
                print(f"    ... and {len(warnings_encountered) - 5} more warnings")

        if errors_encountered:
            print(f"\n❌ ERRORS ({len(errors_encountered)}):")
            for error in errors_encountered[:5]:
                print(f"    - {error}")
            if len(errors_encountered) > 5:
                print(f"    ... and {len(errors_encountered) - 5} more errors")

        print(f"{'='*60}\n")
        return len(errors_encountered) == 0

    except KeyboardInterrupt:
        print("🛑 [PHPMYADMIN] Operation interrupted by user")
        try:
            backup_path = PANEL_PATH + ".backup"
            if os.path.exists(backup_path):
                restore_from_backup(PANEL_PATH)
        except Exception:
            pass
        _set_currently_running("fetch_settings()", status="aborted",
                               operation_status="❌ ABORTED: fetch_settings terminated by user")
        return False
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ [PHPMYADMIN] {error_msg}")
        traceback.print_exc()
        try:
            backup_path = PANEL_PATH + ".backup"
            if os.path.exists(backup_path):
                restore_from_backup(PANEL_PATH)
        except Exception:
            pass
        _set_currently_running("fetch_settings()", status="error",
                               operation_status=f"❌ {error_msg}")
        return False

def distribute_characters():
    """
    Distributes character visual prompts from characters_visual_prompts to each entry
    based on the view_focus_characters field.

    For each entry, extracts character names from view_focus_characters,
    normalizes them (removes special characters, handles "and" separator),
    looks up each character in characters_visual_prompts, and adds them
    as new fields in the entry.

    IMPORTANT:
    Every distributed character receives the following default instruction
    at the beginning of its character details, even if that character was
    already distributed previously:

    "Don't generate this character image it is just detail and definition
    of the character only generate the scene pov prompt, i repeat dont
    generate this character image but use the details as key and
    information of what the character looks like"

    Executes only when currently_running is None/"none"/empty,
    "fetch_settings_successful", or "distribute_characters()".
    On start sets currently_running to "distribute_characters()".
    On clean success sets currently_running to "distribute_characters_successful".
    """
    import os
    import json
    import traceback

    # ================================================================
    # DEFAULT CHARACTER INSTRUCTION
    # ================================================================
    DEFAULT_CHARACTER_INSTRUCTION = (
        "Don't generate this character image it is just detail and definition "
        "of the character only generate the scene pov prompt, i repeat dont "
        "generate this character image but use the details as key and "
        "information of what the character looks like"
    )

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
            os.makedirs(
                os.path.dirname(PANEL_PATH) or '.',
                exist_ok=True
            )

            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(
                    data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            return True

        except Exception as e:
            print(f"❌ [STATUS] Failed to save panel: {e}")
            return False

    def _get_currently_running():
        data = _load_panel()
        val = data.get("currently_running")

        if val is None:
            return None

        val = str(val).strip()

        if val.lower() in ("", "none", "null"):
            return None

        return val

    def _set_currently_running(
        value,
        status=None,
        operation_status=None
    ):
        data = _load_panel()

        data["currently_running"] = value

        if status is not None:
            data["status"] = status

        if operation_status is not None:
            data["operation_status"] = operation_status

        return _save_panel(data)

    # ================================================================
    # GATE: ONLY RUN WHEN ALLOWED
    # ================================================================
    current = _get_currently_running()

    allowed = (
        current is None
        or current == "fetch_settings_successful"
        or current == "distribute_characters()"
    )

    if not allowed:
        print(
            f"⏭️ [DISTRIBUTE] Skipping – currently_running is "
            f"'{current}' "
            f"(expected None, 'fetch_settings_successful' or "
            f"'distribute_characters()')"
        )
        return None

    # ================================================================
    # CLAIM THE SLOT
    # ================================================================
    _set_currently_running(
        "distribute_characters()",
        status="pending",
        operation_status="Running distribute_characters()"
    )

    print(
        "🔒 [DISTRIBUTE] Claimed currently_running = "
        "'distribute_characters()'"
    )

    # ================================================================
    # MAIN LOGIC
    # ================================================================
    if not os.path.exists(PANEL_PATH):
        msg = f"❌ Error: panel.json missing at: {PANEL_PATH}"

        print(msg)

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)

    except json.JSONDecodeError as e:
        msg = f"❌ Error: panel.json is not valid JSON: {e}"

        print(msg)

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None

    except Exception as e:
        msg = f"❌ Error reading panel.json: {e}"

        print(msg)

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None

    # ================================================================
    # GET CHARACTERS_VISUAL_PROMPTS
    # ================================================================
    script_json = (
        panel_data
        .get('project_name', {})
        .get('script_json', {})
    )

    characters_visual_prompts = script_json.get(
        'characters_visual_prompts',
        {}
    )

    if not characters_visual_prompts:
        msg = (
            "⚠️ No characters_visual_prompts found in panel.json "
            "(path: project_name.script_json.characters_visual_prompts)"
        )

        print(msg)

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None

    # ================================================================
    # GET SCRIPT ENTRIES
    # ================================================================
    script_data = script_json.get('script', {})

    if not script_data:
        msg = "⚠️ No script data found in panel.json"

        print(msg)

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None

    print(
        f"📊 [DISTRIBUTE] Found "
        f"{len(characters_visual_prompts)} characters in lookup"
    )

    # ================================================================
    # NORMALIZATION
    # ================================================================
    def normalize_name(name):
        if not name:
            return ""

        name = ' '.join(name.split())

        return name.lower().strip()

    # ================================================================
    # BUILD CHARACTER LOOKUP
    # ================================================================
    character_lookup = {}

    for char_name, char_data in characters_visual_prompts.items():
        normalized = normalize_name(char_name)

        if normalized:
            character_lookup[normalized] = {
                'original_name': char_name,
                'data': char_data
            }

    print(
        f"📊 [DISTRIBUTE] Character lookup built with "
        f"{len(character_lookup)} entries"
    )

    # ================================================================
    # COUNTERS
    # ================================================================
    entries_processed = 0
    total_characters_added = 0
    total_character_instructions_applied = 0
    batches_processed = 0

    # ================================================================
    # EXTRACT CHARACTER NAMES
    # ================================================================
    def extract_character_names(view_focus_string):
        if not view_focus_string:
            return []

        normalized = view_focus_string.replace(
            ' and ',
            ', '
        )

        normalized = normalized.replace(
            ' and',
            ','
        )

        normalized = normalized.replace(
            'and ',
            ','
        )

        raw_names = [
            name.strip()
            for name in normalized.split(',')
            if name.strip()
        ]

        return raw_names

    # ================================================================
    # APPLY DEFAULT CHARACTER INSTRUCTION
    # ================================================================
    def apply_default_character_instruction(char_data):
        """
        Adds the required default instruction to the character data.

        The instruction is applied every time distribution runs,
        including when the character was already distributed.

        If the character data is a string:
            prepend the instruction.

        If the character data is a dictionary:
            preserve all existing fields and add the instruction
            as a dedicated field while also ensuring it is represented
            in the character definition.

        If the character data is a list:
            preserve the existing list and add the instruction as
            the first item.

        Other data types are converted safely to a dictionary/string
        representation without losing the original information.
        """

        instruction = DEFAULT_CHARACTER_INSTRUCTION

        # ------------------------------------------------------------
        # STRING CHARACTER DATA
        # ------------------------------------------------------------
        if isinstance(char_data, str):
            existing = char_data.strip()

            if not existing:
                return instruction

            # Prevent duplicate copies while still guaranteeing
            # the instruction exists.
            if instruction.lower() in existing.lower():
                return existing

            return f"{instruction}\n\n{existing}"

        # ------------------------------------------------------------
        # DICTIONARY CHARACTER DATA
        # ------------------------------------------------------------
        if isinstance(char_data, dict):
            updated = dict(char_data)

            # Always explicitly store the instruction.
            updated["character_generation_instruction"] = instruction

            return updated

        # ------------------------------------------------------------
        # LIST CHARACTER DATA
        # ------------------------------------------------------------
        if isinstance(char_data, list):
            updated = list(char_data)

            # Remove an existing exact instruction so we can put one
            # clean copy at the beginning.
            updated = [
                item
                for item in updated
                if not (
                    isinstance(item, str)
                    and item.strip().lower() == instruction.lower()
                )
            ]

            updated.insert(0, instruction)

            return updated

        # ------------------------------------------------------------
        # OTHER DATA TYPES
        # ------------------------------------------------------------
        if char_data is None:
            return {
                "character_generation_instruction": instruction
            }

        return {
            "character_generation_instruction": instruction,
            "character_details": char_data
        }

    # ================================================================
    # PROCESS EACH BATCH
    # ================================================================
    for batch_key, batch_data in script_data.items():

        if not isinstance(batch_data, dict):
            continue

        entries = batch_data.get('entries', [])

        if not entries:
            continue

        batches_processed += 1

        print(
            f"\n📁 [DISTRIBUTE] Processing batch: "
            f"{batch_key} ({len(entries)} entries)"
        )

        # ============================================================
        # PROCESS EACH ENTRY
        # ============================================================
        for entry_idx, entry in enumerate(entries):

            if not isinstance(entry, dict):
                print(
                    f"  ⏭️ Entry {entry_idx + 1}: "
                    f"Invalid entry structure, skipping"
                )
                continue

            view_focus = entry.get(
                'view_focus_characters',
                ''
            )

            if not view_focus:
                print(
                    f"  ⏭️ Entry {entry_idx + 1}: "
                    f"No view_focus_characters, skipping"
                )
                continue

            raw_names = extract_character_names(
                view_focus
            )

            if not raw_names:
                print(
                    f"  ⏭️ Entry {entry_idx + 1}: "
                    f"No names extracted from '{view_focus}'"
                )
                continue

            print(
                f"  📝 Entry {entry_idx + 1}: "
                f"Extracted names: {raw_names}"
            )

            characters_added = 0

            # ========================================================
            # PROCESS EACH CHARACTER
            # ========================================================
            for raw_name in raw_names:

                normalized_raw = normalize_name(
                    raw_name
                )

                matched_char = None

                # ----------------------------------------------------
                # EXACT MATCH
                # ----------------------------------------------------
                if normalized_raw in character_lookup:
                    matched_char = character_lookup[
                        normalized_raw
                    ]

                # ----------------------------------------------------
                # PARTIAL MATCH
                # ----------------------------------------------------
                else:
                    for lookup_key, lookup_data in character_lookup.items():

                        if (
                            normalized_raw in lookup_key
                            or lookup_key in normalized_raw
                        ):
                            matched_char = lookup_data

                            print(
                                f"    🔍 Partial match: "
                                f"'{raw_name}' -> '{lookup_key}'"
                            )

                            break

                # ====================================================
                # CHARACTER FOUND
                # ====================================================
                if matched_char:

                    char_name = matched_char['original_name']
                    char_data = matched_char['data']

                    # ------------------------------------------------
                    # ALWAYS APPLY THE DEFAULT INSTRUCTION
                    # ------------------------------------------------
                    updated_char_data = (
                        apply_default_character_instruction(
                            char_data
                        )
                    )

                    # ------------------------------------------------
                    # DISTRIBUTE / OVERWRITE THE CHARACTER FIELD
                    # ------------------------------------------------
                    entry[char_name] = updated_char_data

                    characters_added += 1
                    total_characters_added += 1
                    total_character_instructions_applied += 1

                    print(
                        f"    ✅ Added/updated character: "
                        f"{char_name}"
                    )

                    print(
                        f"       ↳ Default character instruction "
                        f"applied"
                    )

                # ====================================================
                # CHARACTER NOT FOUND
                # ====================================================
                else:

                    print(
                        f"    ⚠️ Character not found in lookup: "
                        f"'{raw_name}'"
                    )

                    print(
                        f"       Available characters: "
                        f"{list(character_lookup.keys())}"
                    )

            # ========================================================
            # ENTRY SUMMARY
            # ========================================================
            if characters_added > 0:

                entries_processed += 1

                print(
                    f"  ✅ Entry {entry_idx + 1}: "
                    f"Added/updated {characters_added} characters"
                )

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'=' * 60}")
    print("📊 [DISTRIBUTE] Summary:")
    print(
        f"   - Batches processed: "
        f"{batches_processed}"
    )
    print(
        f"   - Entries with characters distributed: "
        f"{entries_processed}"
    )
    print(
        f"   - Total character references added/updated: "
        f"{total_characters_added}"
    )
    print(
        f"   - Default character instructions applied: "
        f"{total_character_instructions_applied}"
    )
    print(
        f"   - Default instruction: "
        f"'{DEFAULT_CHARACTER_INSTRUCTION}'"
    )
    print(f"{'=' * 60}")

    # ================================================================
    # SAVE UPDATED PANEL.JSON
    # ================================================================
    try:

        # Preserve / update status fields
        panel_data["currently_running"] = (
            "distribute_characters_successful"
        )

        panel_data["status"] = "pending"

        panel_data["operation_status"] = (
            "✅ distribute_characters completed successfully"
        )

        with open(
            PANEL_PATH,
            'w',
            encoding='utf-8'
        ) as file:

            json.dump(
                panel_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            "✅ [DISTRIBUTE] Successfully updated panel.json"
        )

        print(
            "🏁 [DISTRIBUTE] currently_running set to "
            "'distribute_characters_successful'"
        )

        return (
            entries_processed,
            total_characters_added
        )

    except Exception as e:

        msg = f"❌ Error saving panel.json: {e}"

        print(msg)

        traceback.print_exc()

        _set_currently_running(
            "distribute_characters()",
            status="error",
            operation_status=msg
        )

        return None
      
def generate_gemini_images():
    """
    Generates images using Gemini via GUI automation with pyautogui image recognition.
    Features: 
    - Uses GEMINI_URL and GUI_IMAGES path variable
    - Checks panel.json for image_generation_engine == "Gemini" (case-insensitive)
    - If engine is not Gemini, function exits immediately
    - Runs only when currently_running is None/"none"/empty,
      "distribute_characters_successful", or "generate_gemini_images()"
    - On start sets currently_running to "generate_gemini_images()"
    - On clean success sets currently_running to "generate_gemini_images_successful"
    - On any error/abort keeps currently_running as "generate_gemini_images()"
    - Waits for ask_gemini.png to appear, clicks and pastes full entry JSON
    - Looks for upload_to_gemini.png to confirm paste, clicks on RIGHT side (not center)
    - Waits for generating_image.png or gemini_microphone.png
    - Checks for gemini_generation_limit_message.png - if found, terminates
    - When gemini_microphone.png is found, FIRST checks for limit message
    - If limit message found, aborts; otherwise proceeds to find more.png
    - Clicks more.png on the right side (not center)
    - Clicks download_gemini_image.png
    - Monitors downloads with background function
    - If download not found after 30 seconds, retries: click more.png, then download_gemini_image.png
    - Renames downloaded file to entry name (entry_1.png, entry_2.png, etc.)
    - Moves to images folder in project title directory
    - Validates entry order and handles missing entries
    - No JSON tracking for entries
    - Dynamic fallback support: checks for image_name{number}.png variants
    - Enhanced upload detection: waits indefinitely for upload button if text is already pasted
    """
    import os
    import json
    import time
    import re
    import subprocess
    import traceback

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
        print(f"❌ [GEMINI] Missing dependency: {e}")
        return

    pyautogui.PAUSE = 0.0

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

    def _get_currently_running():
        data = _load_panel()
        val = data.get("currently_running")
        if val is None:
            return None
        val = str(val).strip()
        if val.lower() in ("", "none", "null"):
            return None
        return val

    def _set_currently_running(value, status=None, operation_status=None):
        data = _load_panel()
        data["currently_running"] = value
        if status is not None:
            data["status"] = status
        if operation_status is not None:
            data["operation_status"] = operation_status
        return _save_panel(data)

    # ------------------------------------------------------------------
    # Engine + status gate
    # ------------------------------------------------------------------
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)

        engines = panel_data.get('engines', {})
        image_generation_engine = engines.get('image_generation_engine', '').strip()

        if image_generation_engine.lower() != 'gemini':
            print(f"ℹ️ [ENGINE] Image generation engine is '{image_generation_engine}', not 'Gemini' - skipping operation")
            print(f"   To use this function, set 'image_generation_engine' to 'Gemini' in panel.json")
            return

        print(f"✅ [ENGINE] Image generation engine is 'Gemini' - proceeding with operation")

    except json.JSONDecodeError as e:
        print(f"❌ Error: panel.json is not valid JSON: {e}")
        return
    except Exception as e:
        print(f"❌ Error reading panel.json: {e}")
        return

    current = _get_currently_running()
    allowed = (
        current is None
        or current == "distribute_characters_successful"
        or current == "generate_gemini_images()"
    )
    if not allowed:
        print(f"⏭️ [GEMINI] Skipping – currently_running is '{current}' "
              f"(expected None, 'distribute_characters_successful' or 'generate_gemini_images()')")
        return

    # Claim the slot
    _set_currently_running(
        "generate_gemini_images()",
        status="pending",
        operation_status="Running generate_gemini_images()"
    )
    print("🔒 [GEMINI] Claimed currently_running = 'generate_gemini_images()'")

    # ------------------------------------------------------------------
    # Rest of original logic (with status updates on success / error)
    # ------------------------------------------------------------------
    project_title = panel_data.get('project_name', {}).get('project_title', 'workproject1')
    script_json = panel_data.get('project_name', {}).get('script_json', {})
    script_data = script_json.get('script', {})

    all_entries = []
    for batch_key, batch_data in script_data.items():
        if isinstance(batch_data, dict) and 'entries' in batch_data:
            entries = batch_data.get('entries', [])
            for entry in entries:
                if 'scene_pov_prompt' in entry:
                    all_entries.append(entry)

    total_entries = len(all_entries)
    print(f"📊 [CONFIG] Found {total_entries} total entries")

    if total_entries == 0:
        print("❌ No entries found to process")
        _set_currently_running("generate_gemini_images()", status="error",
                               operation_status="❌ No entries found to process")
        return

    terminate_automation = False
    operation_status_flag = True
    operation_status_message = ""
    operation_aborted = False

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)

            if is_abort:
                operation_status_message = f"❌ ABORTED: {message}"
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

            current_panel['operation_status'] = operation_status_message
            # Keep currently_running as the function name on error/abort
            if is_error or is_abort:
                current_panel['currently_running'] = "generate_gemini_images()"
                current_panel['status'] = "error" if is_error else "aborted"
            elif is_success:
                # Final success is handled at the very end; intermediate successes keep the running name
                current_panel['currently_running'] = "generate_gemini_images()"
                current_panel['status'] = "pending"

            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(current_panel, file, indent=4, ensure_ascii=False)

            if is_abort:
                print(f"🛑 [STATUS] Operation aborted: {message}")
                raise SystemExit(f"Operation aborted: {message}")
        except SystemExit:
            raise
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting Gemini image generation: {reason}", is_abort=True)

    def check_operation_status():
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting Gemini operation", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        try:
            hud.print("🛑 Manual Stop Triggered!", "warning")
        except Exception:
            pass
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status("Gemini operation manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status("Gemini operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

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
        print(f"🔍 [FALLBACK] Searching for {image_name} with {len(variants)} variant(s)...")
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateCenterOnScreen(
                    variant_path, confidence=confidence, grayscale=False
                )
                if location:
                    print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                    return location, variant_path
            except Exception:
                pass
        return None, None

    def wait_for_image_with_fallback(image_name, timeout_seconds=60, confidence=0.8, region=None):
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
                        variant_path, confidence=confidence, grayscale=False
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
            time.sleep(0.3)
        print(f"❌ [FALLBACK] {image_name} not found in any variant within {timeout_seconds} seconds")
        return None, None

    def find_image_location_with_fallback(image_name, confidence=0.8, region=None):
        variants = get_image_variants(image_name)
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateOnScreen(
                    variant_path, confidence=confidence, grayscale=False
                )
                if location:
                    print(f"✅ [FALLBACK] Found {variant_name} at ({location.left}, {location.top})")
                    return location, variant_path
            except Exception:
                pass
        return None, None

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
                    time.sleep(0.3)
                print("🔄 [WINDOW] Maximizing window...")
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                time.sleep(0.5)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.2)
                print("✅ [WINDOW] Window ready - maximized and focused")
                update_operation_status("Browser window ready for Gemini operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")

        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for Gemini operation...")
        subprocess.Popen([edge_path, "about:blank"])

        for attempt in range(20):
            check_for_termination()
            time.sleep(0.5)
            edge_windows = get_edge_window_on_monitor(current_monitor)
            if edge_windows:
                hwnd = edge_windows[0]['hwnd']
                print(f"🪟 [WINDOW] New Edge window launched, handle: {hwnd}")
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.3)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.5)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.2)
                    print("✅ [WINDOW] New window ready - maximized and focused")
                    update_operation_status("Browser launched for Gemini operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue

        error_msg = "Failed to get or launch Edge window for Gemini operation"
        update_operation_status(error_msg, is_error=True)
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
                time.sleep(0.3)
            current_foreground = win32gui.GetForegroundWindow()
            if current_foreground != hwnd:
                print("🛡️ [FOCUS] Correcting window focus...")
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.15)
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] != win32con.SW_SHOWMAXIMIZED:
                    print("🔄 [FOCUS] Window not maximized, maximizing...")
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
            except Exception:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
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
            hud.print("📋 Navigating to URL...", "typing")
        except Exception:
            pass
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.1)
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status("Navigating to Gemini URL...")

    # --- IMAGE RECOGNITION HELPERS ---
    def wait_for_image(image_name, timeout_seconds=60, confidence=0.8, region=None):
        location, _ = wait_for_image_with_fallback(image_name, timeout_seconds, confidence, region)
        return location

    def find_image(image_name, confidence=0.8, region=None):
        location, _ = find_image_with_fallback(image_name, confidence, region)
        return location

    def click_image_center(image_name, confidence=0.8, wait_time=0.3):
        location = find_image(image_name, confidence)
        if location:
            pyautogui.moveTo(location.x, location.y, duration=0.1)
            pyautogui.click()
            time.sleep(wait_time)
            return True
        return False

    def click_image_right(image_name, confidence=0.8, wait_time=0.3):
        variants = get_image_variants(image_name)
        if not variants:
            print(f"❌ [IMAGE] No variants found for {image_name}")
            return False
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateOnScreen(variant_path, confidence=confidence, grayscale=False)
                if location:
                    click_x = location.left + int(location.width * 0.75)
                    click_y = location.top + int(location.height / 2)
                    print(f"✅ [IMAGE] Found {variant_name}, clicking right side at ({click_x}, {click_y})")
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    pyautogui.click()
                    time.sleep(wait_time)
                    return True
            except Exception:
                pass
        print(f"❌ [IMAGE] {image_name} not found in any variant")
        return False

    def scroll_up_multiple(times=3):
        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        center_x = screen_width // 2
        center_y = screen_height // 2
        for i in range(times):
            pyautogui.moveTo(center_x, center_y, duration=0.05)
            pyautogui.scroll(-500)
            time.sleep(0.3)
            print(f"⬆️ [SCROLL] Scrolled up ({i+1}/{times})")
        time.sleep(0.5)

    # --- DOWNLOAD MONITORING ---
    def check_and_rename_download(entry_name, images_folder, timeout_seconds=180, check_interval=0.3):
        print(f"📊 [DOWNLOAD] Monitoring for download for {entry_name}...")
        try:
            hud.print("📊 Monitoring download...", "waiting")
        except Exception:
            pass
        update_operation_status(f"Waiting for download: {entry_name}")

        downloads_folder = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_folder):
            print(f"❌ [DOWNLOAD] Downloads folder not found: {downloads_folder}")
            return False, None

        initial_files = {}
        try:
            with os.scandir(downloads_folder) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            stat = entry.stat()
                            initial_files[entry.name] = {
                                'path': entry.path, 'time': stat.st_mtime, 'size': stat.st_size
                            }
                        except Exception:
                            pass
            print(f"📁 [DOWNLOAD] Found {len(initial_files)} existing files before download")
        except Exception as e:
            print(f"⚠️ [DOWNLOAD] Error scanning existing files: {e}")
            initial_files = {}

        start_time = time.time()
        download_detected = False
        downloaded_file_path = None
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}

        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            elapsed = int(time.time() - start_time)
            try:
                if os.path.exists(downloads_folder):
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file():
                                file_name = entry.name
                                file_ext = os.path.splitext(file_name)[1].lower()
                                is_new_file = file_name not in initial_files
                                is_recent = False
                                try:
                                    stat = entry.stat()
                                    if stat.st_mtime > start_time - 10:
                                        is_recent = True
                                except Exception:
                                    pass
                                if (is_new_file or is_recent) and file_ext in image_extensions:
                                    print(f"🆕 [DOWNLOAD] Found new/updated image file: {file_name}")
                                    print(f"   📁 Path: {entry.path}")
                                    print(f"   📏 Size: {stat.st_size} bytes")
                                    stable_count = 0
                                    stable_size = 0
                                    max_stable_checks = 5
                                    while stable_count < 3 and stable_count < max_stable_checks:
                                        try:
                                            current_size = os.path.getsize(entry.path)
                                            if current_size == stable_size and current_size > 1024:
                                                stable_count += 1
                                                print(f"   ⏳ File stable ({stable_count}/3), size: {current_size} bytes")
                                            else:
                                                stable_count = 0
                                                stable_size = current_size
                                                print(f"   ⏳ File size changing: {current_size} bytes")
                                        except Exception as e:
                                            print(f"   ⚠️ Error checking size: {e}")
                                        time.sleep(0.3)
                                    if stable_count >= 3:
                                        print(f"✅ [DOWNLOAD] File stable and ready!")
                                        downloaded_file_path = entry.path
                                        download_detected = True
                                        break
                                    else:
                                        print(f"⚠️ [DOWNLOAD] File not stable, continuing to monitor...")
                                elif file_name.endswith('.crdownload') or file_name.endswith('.tmp'):
                                    print(f"⏳ [DOWNLOAD] Found temp download: {file_name}")
                            if download_detected:
                                break
                if download_detected and downloaded_file_path:
                    break
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ [DOWNLOAD] Still waiting for download... ({elapsed}s elapsed)")
                    try:
                        hud.print(f"⏳ Waiting... ({elapsed}s)", "waiting")
                    except Exception:
                        pass
                    update_operation_status(f"Waiting for download {entry_name}... ({elapsed}s)")
                time.sleep(check_interval)
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Error in monitoring loop: {e}")
                time.sleep(check_interval)
                continue

        if not download_detected or not downloaded_file_path:
            print(f"⏰ [DOWNLOAD] Timeout or no download detected after {timeout_seconds} seconds")
            try:
                print(f"🔍 [DOWNLOAD] Performing final scan for new image files...")
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file():
                            file_name = entry.name
                            file_ext = os.path.splitext(file_name)[1].lower()
                            if file_ext in image_extensions:
                                try:
                                    stat = entry.stat()
                                    if stat.st_mtime > start_time - 10:
                                        print(f"🆕 [DOWNLOAD] Found new file in final scan: {file_name}")
                                        downloaded_file_path = entry.path
                                        download_detected = True
                                        break
                                except Exception:
                                    pass
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Final scan error: {e}")

        if not download_detected or not downloaded_file_path:
            print(f"❌ [DOWNLOAD] No download detected")
            return False, None

        try:
            file_name = os.path.basename(downloaded_file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            new_filename = f"{entry_name}{file_ext}"
            target_path = os.path.join(images_folder, new_filename)
            if not os.path.exists(images_folder):
                os.makedirs(images_folder, exist_ok=True)
            if not os.path.exists(downloaded_file_path):
                print(f"❌ [DOWNLOAD] File no longer exists: {downloaded_file_path}")
                return False, None
            try:
                time.sleep(0.5)
                os.rename(downloaded_file_path, target_path)
                print(f"✅ [DOWNLOAD] File renamed to: {new_filename}")
                print(f"📁 [DOWNLOAD] Moved to: {target_path}")
                try:
                    hud.print(f"✅ Saved: {new_filename}", "success")
                except Exception:
                    pass
                update_operation_status(f"Downloaded and saved: {new_filename}")
                return True, target_path
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Error moving file: {e}")
                import shutil
                try:
                    shutil.copy2(downloaded_file_path, target_path)
                    try:
                        os.remove(downloaded_file_path)
                    except Exception:
                        pass
                    print(f"✅ [DOWNLOAD] File copied and renamed: {new_filename}")
                    return True, target_path
                except Exception as e2:
                    print(f"❌ [DOWNLOAD] Failed to save file: {e2}")
                    return False, None
        except Exception as e:
            print(f"❌ [DOWNLOAD] Error processing downloaded file: {e}")
            return False, None

    def click_more_and_download(hwnd, entry_name, max_retries=3):
        print(f"🔄 [RETRY] Attempting to click more.png and download for {entry_name}...")
        for attempt in range(max_retries):
            check_for_termination()
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [RETRY] Generation limit reached! Aborting.")
                try:
                    hud.print("❌ Generation limit reached!", "error")
                except Exception:
                    pass
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                abort_operation(f"Generation limit reached for {entry_name}")
                return False
            scroll_up_multiple(3)
            time.sleep(0.5)
            more_location, more_path = find_image_with_fallback("more.png", confidence=0.8)
            if more_location and more_path:
                try:
                    location = pyautogui.locateOnScreen(more_path, confidence=0.8)
                    if location:
                        click_x = location.left + int(location.width * 0.75)
                        click_y = location.top + int(location.height / 2)
                        print(f"🎯 [RETRY] Clicking {os.path.basename(more_path)} right side at ({click_x}, {click_y}) (attempt {attempt+1})")
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        pyautogui.click()
                        time.sleep(0.5)
                        print(f"✅ [RETRY] Clicked more.png right side")
                    else:
                        print(f"⚠️ [RETRY] Could not get bounds for {os.path.basename(more_path)}")
                        scroll_up_multiple(2)
                        time.sleep(0.3)
                        continue
                except Exception as e:
                    print(f"⚠️ [RETRY] Error clicking more.png: {e}")
                    scroll_up_multiple(2)
                    time.sleep(0.3)
                    continue
            else:
                print(f"⚠️ [RETRY] more.png not found (attempt {attempt+1}/{max_retries}) - scrolling...")
                scroll_up_multiple(3)
                time.sleep(0.5)
                continue
            download_location = wait_for_image("download_gemini_image.png", timeout_seconds=10, confidence=0.8)
            if download_location:
                pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                pyautogui.click()
                time.sleep(0.5)
                print(f"✅ [RETRY] Download initiated (attempt {attempt+1})")
                return True
            else:
                print(f"⚠️ [RETRY] download_gemini_image.png not found (attempt {attempt+1}/{max_retries})")
                scroll_up_multiple(2)
                time.sleep(0.3)
                download_location = wait_for_image("download_gemini_image.png", timeout_seconds=10, confidence=0.8)
                if download_location:
                    pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                    pyautogui.click()
                    time.sleep(0.5)
                    print(f"✅ [RETRY] Download initiated after scroll (attempt {attempt+1})")
                    return True
        print(f"❌ [RETRY] Failed to initiate download after {max_retries} attempts")
        return False

    # --- ENTRY ORDER VALIDATION ---
    def validate_entry_order(images_folder):
        if not os.path.exists(images_folder):
            os.makedirs(images_folder, exist_ok=True)
            return True, 0
        image_files = []
        for file in os.listdir(images_folder):
            if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                image_files.append(file)
        if not image_files:
            print(f"📁 [VALIDATE] No image files found in {images_folder}")
            return True, 0
        entry_numbers = []
        for filename in image_files:
            match = re.search(r'entry[_\-]?(\d+)\.(png|jpg|jpeg|gif|webp)$', filename, re.IGNORECASE)
            if match:
                entry_numbers.append(int(match.group(1)))
        if not entry_numbers:
            print(f"⚠️ [VALIDATE] No valid entry files found, starting from 0")
            return True, 0
        entry_numbers.sort()
        print(f"📊 [VALIDATE] Found entry numbers: {entry_numbers}")
        expected_next = 1
        for num in entry_numbers:
            if num != expected_next:
                print(f"❌ [VALIDATE] Gap detected: Expected entry {expected_next}, found entry {num}")
                print(f"🗑️ [VALIDATE] Deleting all image files and starting over...")
                try:
                    hud.print("🗑️ Resetting due to missing entries...", "warning")
                except Exception:
                    pass
                update_operation_status("Gap detected - resetting all entries")
                for file in image_files:
                    file_path = os.path.join(images_folder, file)
                    try:
                        os.remove(file_path)
                        print(f"🗑️ [VALIDATE] Deleted: {file}")
                    except Exception as e:
                        print(f"⚠️ [VALIDATE] Could not delete {file}: {e}")
                return True, 0
            expected_next += 1
        next_entry = len(entry_numbers)
        print(f"✅ [VALIDATE] Entries are in order, next entry: {next_entry + 1}")
        return True, next_entry

    def format_entry_json(entry_data):
        try:
            return json.dumps(entry_data, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [FORMAT] Error formatting JSON: {e}")
            return entry_data.get('scene_pov_prompt', '')

    # --- MAIN GEMINI WORKFLOW HELPERS ---
    def load_gemini_url(hwnd):
        print(f"🌐 [GEMINI] Loading Gemini URL: {GEMINI_URL}")
        try:
            hud.print("📋 Loading Gemini...", "navigating")
        except Exception:
            pass
        update_operation_status("Loading Gemini...")
        fast_paste_url(hwnd, GEMINI_URL)
        time.sleep(3)
        hwnd = ensure_window_ready_and_focused()
        return True, hwnd

    def wait_for_generation_complete(hwnd, entry_name, max_wait_seconds=300, check_interval=0.5):
        print(f"⏳ [ENTRY] Waiting for generation to complete...")
        try:
            hud.print("⏳ Generating image...", "processing")
        except Exception:
            pass
        update_operation_status(f"Generating image for {entry_name}...")

        start_time = time.time()
        last_scroll_time = 0
        scroll_interval = 5
        found_generating = False
        generating_first_seen = None

        print(f"🔍 [ENTRY] Phase 1: Waiting for generating_image.png to confirm work has started...")
        while time.time() - start_time < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached while waiting for generating_image.png!")
                try:
                    hud.print("❌ Generation limit reached!", "error")
                except Exception:
                    pass
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                return False, "limit_reached"
            generating_location = find_image("generating_image.png", confidence=0.7)
            if generating_location:
                print(f"✅ [ENTRY] Found generating_image.png - work has started!")
                found_generating = True
                generating_first_seen = time.time()
                try:
                    hud.print("⏳ Generation in progress...", "processing")
                except Exception:
                    pass
                update_operation_status(f"Generation in progress for {entry_name}")
                break
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"⏳ [ENTRY] Waiting for generation to start... ({elapsed}s elapsed)")
                try:
                    hud.print(f"⏳ Waiting to start... ({elapsed}s)", "processing")
                except Exception:
                    pass
                update_operation_status(f"Waiting for generation to start for {entry_name}... ({elapsed}s)")
            if time.time() - last_scroll_time > scroll_interval:
                scroll_up_multiple(2)
                last_scroll_time = time.time()
            time.sleep(check_interval)

        if not found_generating:
            print(f"❌ [ENTRY] generating_image.png not found within timeout - generation may not have started")
            return False, "timeout"

        print(f"🔍 [ENTRY] Phase 2: Work confirmed, waiting for gemini_microphone.png (generation complete)...")
        try:
            hud.print("⏳ Generating image...", "processing")
        except Exception:
            pass
        update_operation_status("Generation in progress, waiting for completion...")

        phase2_start = time.time()
        phase2_timeout = max_wait_seconds - (generating_first_seen - start_time) if generating_first_seen else max_wait_seconds - 30
        if phase2_timeout < 30:
            phase2_timeout = 30
            print(f"⚠️ [ENTRY] Adjusted phase 2 timeout to {phase2_timeout}s")

        while time.time() - phase2_start < phase2_timeout:
            check_for_termination()
            enforce_window_focus(hwnd)
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached! Found gemini_generation_limit_message.png")
                try:
                    hud.print("❌ Generation limit reached!", "error")
                except Exception:
                    pass
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                return False, "limit_reached"
            microphone_location = find_image("gemini_microphone.png", confidence=0.7)
            if microphone_location:
                print(f"✅ [ENTRY] Found gemini_microphone.png - image is ready!")
                try:
                    hud.print("✅ Image ready", "success")
                except Exception:
                    pass
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            generating_location = find_image("generating_image.png", confidence=0.7)
            if generating_location:
                elapsed = int(time.time() - phase2_start)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ [ENTRY] Still generating... ({elapsed}s elapsed in phase 2)")
                    try:
                        hud.print(f"⏳ Generating... ({elapsed}s)", "processing")
                    except Exception:
                        pass
                    update_operation_status(f"Generating image for {entry_name}... ({elapsed}s)")
                if time.time() - last_scroll_time > scroll_interval:
                    scroll_up_multiple(3)
                    last_scroll_time = time.time()
                time.sleep(check_interval)
                continue
            else:
                print(f"⚠️ [ENTRY] generating_image.png disappeared, checking for microphone...")
                time.sleep(0.5)
                microphone_location = find_image("gemini_microphone.png", confidence=0.7)
                if microphone_location:
                    print(f"✅ [ENTRY] Found gemini_microphone.png - image is ready!")
                    try:
                        hud.print("✅ Image ready", "success")
                    except Exception:
                        pass
                    update_operation_status(f"Image generation complete for {entry_name}")
                    return True, "complete"
                continue

        print(f"⏰ [ENTRY] Generation timeout after {max_wait_seconds} seconds")
        return False, "timeout"

    def wait_for_upload_button_indefinitely(hwnd, entry_name, check_interval=0.5):
        print(f"⏳ [UPLOAD] Waiting indefinitely for upload_to_gemini.png button...")
        try:
            hud.print("⏳ Waiting for upload button...", "waiting")
        except Exception:
            pass
        update_operation_status("Waiting for upload button to appear...")
        last_status_time = 0
        start_time = time.time()
        while True:
            check_for_termination()
            enforce_window_focus(hwnd)
            upload_location = find_image("upload_to_gemini.png", confidence=0.7)
            if upload_location:
                print(f"✅ [UPLOAD] Found upload_to_gemini.png after waiting!")
                return upload_location
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [UPLOAD] Generation limit reached while waiting for upload button!")
                try:
                    hud.print("❌ Generation limit reached!", "error")
                except Exception:
                    pass
                update_operation_status(f"Generation limit reached while waiting for upload for {entry_name}", is_error=True)
                return None
            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(f"⏳ [UPLOAD] Still waiting for upload button... ({elapsed}s elapsed)")
                try:
                    hud.print(f"⏳ Waiting for upload... ({elapsed}s)", "waiting")
                except Exception:
                    pass
                update_operation_status(f"Waiting for upload button for {entry_name}... ({elapsed}s)")
                last_status_time = current_time
            if int(current_time - start_time) % 10 == 0 and int(current_time - start_time) > 0:
                scroll_up_multiple(2)
            time.sleep(check_interval)

    def process_single_entry(hwnd, entry_index, entry_data, images_folder):
        entry_name = f"entry_{entry_index + 1}"
        entry_json = format_entry_json(entry_data)
        if not entry_json:
            print(f"⚠️ [ENTRY] No data found for {entry_name}")
            return False

        print(f"\n{'='*50}")
        print(f"📝 [ENTRY] Processing {entry_name}/{total_entries}")
        print(f"{'='*50}")
        update_operation_status(f"Processing {entry_name}...")

        print(f"🔍 [ENTRY] Step 1: Looking for ask_gemini.png with fallback support...")
        ask_location = wait_for_image("ask_gemini.png", timeout_seconds=60, confidence=0.8)
        if not ask_location:
            print(f"❌ [ENTRY] Could not find ask_gemini.png in any variant")
            try:
                hud.print("❌ UI element not found", "error")
            except Exception:
                pass
            update_operation_status(f"Could not find ask_gemini.png for {entry_name}", is_error=True)
            return False

        pyautogui.moveTo(ask_location.x, ask_location.y, duration=0.1)
        pyautogui.click()
        time.sleep(0.3)

        print(f"📝 [ENTRY] Step 2: Pasting full entry JSON...")
        try:
            hud.print(f"📝 Pasting {entry_name}...", "typing")
        except Exception:
            pass
        pyautogui.click()
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyautogui.press('backspace')
        time.sleep(0.05)
        pyperclip.copy(entry_json)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)

        print(f"🔍 [ENTRY] Step 3: Looking for upload_to_gemini.png to confirm paste...")
        upload_location = wait_for_image("upload_to_gemini.png", timeout_seconds=10, confidence=0.7)

        if not upload_location:
            print(f"⚠️ [UPLOAD] Upload button not found initially - verifying text was pasted...")
            pyautogui.click()
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            clipboard_content = pyperclip.paste()
            if clipboard_content and len(clipboard_content) > 10:
                entry_check = entry_json[:100] if len(entry_json) > 100 else entry_json
                clipboard_check = clipboard_content[:100] if len(clipboard_content) > 100 else clipboard_content
                if entry_check.strip() in clipboard_check or clipboard_check.strip() in entry_check:
                    print(f"✅ [UPLOAD] Text was successfully pasted (verified by clipboard)")
                    print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png button to appear...")
                    upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                    if upload_location is None:
                        return False
                else:
                    print(f"⚠️ [UPLOAD] Text not properly pasted - clipboard content doesn't match")
                    print(f"🔄 [UPLOAD] Retrying paste...")
                    pyautogui.click()
                    time.sleep(0.1)
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.05)
                    pyautogui.press('backspace')
                    time.sleep(0.05)
                    pyperclip.copy(entry_json)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.3)
                    print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png after retry...")
                    upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                    if upload_location is None:
                        return False
            else:
                print(f"❌ [UPLOAD] Paste verification failed - clipboard is empty")
                print(f"🔄 [UPLOAD] Retrying paste...")
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.05)
                pyautogui.press('backspace')
                time.sleep(0.05)
                pyperclip.copy(entry_json)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png after retry...")
                upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                if upload_location is None:
                    return False

        if upload_location:
            print(f"✅ [ENTRY] Found upload_to_gemini.png - clicking on RIGHT side to submit")
            variants = get_image_variants("upload_to_gemini.png")
            found_variant = False
            for variant_path in variants:
                try:
                    location = pyautogui.locateOnScreen(variant_path, confidence=0.7)
                    if location:
                        click_x = location.left + int(location.width * 0.75)
                        click_y = location.top + int(location.height / 2)
                        print(f"🎯 [ENTRY] Clicking {os.path.basename(variant_path)} right side at ({click_x}, {click_y})")
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        pyautogui.click()
                        time.sleep(0.5)
                        found_variant = True
                        break
                except Exception:
                    pass
            if not found_variant:
                pyautogui.moveTo(upload_location.x, upload_location.y, duration=0.1)
                pyautogui.click()
                time.sleep(0.5)
            for _ in range(10):
                if not find_image("upload_to_gemini.png", confidence=0.7):
                    print(f"✅ [ENTRY] upload_to_gemini.png disappeared - request sent")
                    break
                time.sleep(0.3)
        else:
            print(f"❌ [ENTRY] Could not find upload_to_gemini.png - aborting entry")
            try:
                hud.print("❌ Upload button not found", "error")
            except Exception:
                pass
            update_operation_status(f"Could not find upload_to_gemini.png for {entry_name}", is_error=True)
            return False

        print(f"⏳ [ENTRY] Step 4: Waiting for generation to complete...")
        generation_complete, status = wait_for_generation_complete(hwnd, entry_name, max_wait_seconds=300)

        if status == "limit_reached":
            print(f"❌ [ENTRY] Generation limit reached - aborting all operations")
            abort_operation("Gemini generation limit reached")
            return False
        if not generation_complete:
            print(f"❌ [ENTRY] Generation did not complete within timeout")
            try:
                hud.print("❌ Generation timeout", "error")
            except Exception:
                pass
            update_operation_status(f"Generation timeout for {entry_name}", is_error=True)
            return False

        print(f"🔍 [ENTRY] Step 5: Checking for limit message before proceeding...")
        limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
        if limit_location:
            print(f"❌ [ENTRY] Generation limit reached! Aborting.")
            try:
                hud.print("❌ Generation limit reached!", "error")
            except Exception:
                pass
            update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
            abort_operation(f"Generation limit reached for {entry_name}")
            return False

        print(f"🔍 [ENTRY] Step 6: Looking for more.png...")
        scroll_up_multiple(3)
        time.sleep(0.5)
        more_location = None
        for attempt in range(5):
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached while searching for menu!")
                try:
                    hud.print("❌ Generation limit reached!", "error")
                except Exception:
                    pass
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                abort_operation(f"Generation limit reached for {entry_name}")
                return False
            more_location = find_image("more.png", confidence=0.8)
            if more_location:
                break
            print(f"⏳ [ENTRY] more.png not found (attempt {attempt+1}/5) - scrolling up...")
            scroll_up_multiple(2)
            time.sleep(0.5)

        if more_location:
            variants = get_image_variants("more.png")
            found_variant = False
            for variant_path in variants:
                try:
                    location = pyautogui.locateOnScreen(variant_path, confidence=0.8)
                    if location:
                        click_x = location.left + int(location.width * 0.75)
                        click_y = location.top + int(location.height / 2)
                        print(f"🎯 [ENTRY] Clicking {os.path.basename(variant_path)} right side at ({click_x}, {click_y})")
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        pyautogui.click()
                        time.sleep(0.5)
                        print(f"✅ [ENTRY] Clicked more.png right side")
                        found_variant = True
                        break
                except Exception:
                    pass
            if not found_variant:
                print(f"⚠️ [ENTRY] Could not click more.png - none of the variants worked")
        else:
            print(f"⚠️ [ENTRY] more.png not found after multiple attempts - skipping")

        print(f"🔍 [ENTRY] Step 7: Looking for download_gemini_image.png...")
        download_location = wait_for_image("download_gemini_image.png", timeout_seconds=30, confidence=0.8)
        if not download_location:
            scroll_up_multiple(2)
            time.sleep(0.5)
            download_location = wait_for_image("download_gemini_image.png", timeout_seconds=20, confidence=0.8)
        if not download_location:
            print(f"❌ [ENTRY] Could not find download_gemini_image.png")
            try:
                hud.print("❌ Download button not found", "error")
            except Exception:
                pass
            update_operation_status(f"Could not find download button for {entry_name}", is_error=True)
            return False

        pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
        pyautogui.click()
        time.sleep(0.5)
        print(f"✅ [ENTRY] Download initiated")
        try:
            hud.print(f"📥 Downloading {entry_name}...", "downloading")
        except Exception:
            pass
        update_operation_status(f"Downloading {entry_name}...")

        print(f"📊 [ENTRY] Step 8: Monitoring download with retry...")
        download_success = False
        file_path = None
        download_attempts = 0
        max_download_attempts = 3
        while download_attempts < max_download_attempts and not download_success:
            download_attempts += 1
            print(f"🔄 [ENTRY] Download attempt {download_attempts}/{max_download_attempts}")
            timeout_seconds = 30 if download_attempts == 1 else 20
            download_success, file_path = check_and_rename_download(
                entry_name, images_folder, timeout_seconds=timeout_seconds, check_interval=0.3
            )
            if download_success:
                print(f"✅ [ENTRY] Download successful on attempt {download_attempts}")
                break
            if download_attempts < max_download_attempts:
                print(f"⚠️ [ENTRY] Download not found after {timeout_seconds}s - retrying...")
                try:
                    hud.print(f"🔄 Retry download... ({download_attempts}/{max_download_attempts})", "warning")
                except Exception:
                    pass
                update_operation_status(f"Retrying download for {entry_name}... (attempt {download_attempts + 1})")
                retry_success = click_more_and_download(hwnd, entry_name, max_retries=3)
                if not retry_success:
                    print(f"❌ [ENTRY] Failed to initiate retry download")
                    break
                time.sleep(2)

        if download_success:
            print(f"🎉 [ENTRY] {entry_name} downloaded and saved successfully!")
            try:
                hud.print(f"✅ {entry_name} complete", "success")
            except Exception:
                pass
            update_operation_status(f"{entry_name} completed successfully", is_success=True)
            return True
        else:
            print(f"❌ [ENTRY] Failed to download {entry_name} after {max_download_attempts} attempts")
            try:
                hud.print("❌ Download failed", "error")
            except Exception:
                pass
            update_operation_status(f"Failed to download {entry_name} after multiple attempts", is_error=True)
            return False

    def main_gemini_workflow():
        try:
            if not os.path.exists(GUI_IMAGES):
                print(f"❌ Error: GUI_IMAGES path not found: {GUI_IMAGES}")
                update_operation_status(f"GUI_IMAGES path not found: {GUI_IMAGES}", is_error=True)
                return

            images_folder = os.path.join(IMAGES_PATH, project_title)
            print(f"🎬 [MAIN] Starting Gemini image generation workflow...")
            print(f"🖥️ [MAIN] GUI Images path: {GUI_IMAGES}")
            print(f"📁 [MAIN] Project: '{project_title}'")
            print(f"📁 [MAIN] Images folder: {images_folder}")
            print(f"📊 [MAIN] Total entries: {total_entries}")

            valid, start_index = validate_entry_order(images_folder)
            if not valid:
                print(f"❌ [MAIN] Entry validation failed")
                return
            if start_index >= total_entries:
                print(f"✅ [MAIN] All {total_entries} entries already processed!")
                try:
                    hud.print("✅ All entries complete!", "success")
                except Exception:
                    pass
                _set_currently_running(
                    "generate_gemini_images_successful",
                    status="pending",
                    operation_status=f"✅ All {total_entries} entries already processed"
                )
                print("🏁 [GEMINI] currently_running set to 'generate_gemini_images_successful'")
                return

            print(f"📊 [MAIN] Starting from entry {start_index + 1}")

            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized for Gemini operation")

            print(f"🔍 [MAIN] Loading Gemini URL...")
            success, hwnd = load_gemini_url(hwnd)
            if not success:
                print(f"❌ [MAIN] Failed to load Gemini URL")
                update_operation_status("Failed to load Gemini URL", is_error=True)
                return

            print(f"🔍 [MAIN] Waiting for Gemini UI to load...")
            ask_location = wait_for_image("ask_gemini.png", timeout_seconds=60, confidence=0.8)
            if not ask_location:
                print(f"⚠️ [MAIN] ask_gemini.png not found - page may not be loaded")
                update_operation_status("Gemini UI not loaded", is_error=True)
                return
            print(f"✅ [MAIN] Gemini UI loaded successfully")

            all_ok = True
            for i in range(start_index, total_entries):
                check_for_termination()
                entry = all_entries[i]
                success = process_single_entry(hwnd, i, entry, images_folder)
                if success:
                    time.sleep(2)
                else:
                    all_ok = False
                    print(f"⚠️ [MAIN] Entry {i+1} failed - continuing with next")
                    time.sleep(3)
                    try:
                        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                        pyautogui.click(screen_width // 2, screen_height // 4)
                    except Exception:
                        pass
                    if not find_image("ask_gemini.png", confidence=0.7):
                        print(f"🔍 [MAIN] ask_gemini.png not found - navigating to Gemini URL again...")
                        fast_paste_url(hwnd, GEMINI_URL)
                        time.sleep(3)
                        wait_for_image("ask_gemini.png", timeout_seconds=30)

            print(f"\n{'='*50}")
            print(f"🎉 [MAIN] All entries processed!")
            print(f"{'='*50}")
            try:
                hud.print("🎉 All entries processed!", "success")
            except Exception:
                pass

            if all_ok:
                _set_currently_running(
                    "generate_gemini_images_successful",
                    status="pending",
                    operation_status=f"✅ All {total_entries} entries processed successfully"
                )
                print("🏁 [GEMINI] currently_running set to 'generate_gemini_images_successful'")
            else:
                # Some entries failed – keep the function name so it can be retried
                _set_currently_running(
                    "generate_gemini_images()",
                    status="error",
                    operation_status="⚠️ Some entries failed during Gemini generation"
                )
                print("⚠️ [GEMINI] Some entries failed – currently_running remains 'generate_gemini_images()'")

        except KeyboardInterrupt as ki:
            update_operation_status("Gemini operation manually terminated by user", is_abort=True)
            try:
                hud.show_summary("🛑 Program Halted")
            except Exception:
                pass
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            traceback.print_exc()
            error_msg = f"Unexpected error in Gemini operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            try:
                hud.print("❌ Error occurred", "error")
            except Exception:
                pass
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass

    main_gemini_workflow()

def sceneiq_google_flow_images_generation_engine():
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
    - Requires imagerenderingprogress.png and positions the cursor 50px left and 50px below it before preparing a download
    - Restores the image-hover cursor position before each download retry\n    - While locked, continuously checks the verified web-download confirmation modal\n    - Rechecks rendering while waiting for moregf and returns to render-wait if it reappears\n    - Blocks Windows mouse-wheel scrolling while the image-position lock is active
    - On a fresh function execution only, checks and clicks exactly nanobanana_16ratio9.png
      once after the Google Flow prompt workspace is ready
    - Does not search for or click any other Nano Banana ratio image
    - Automatic and Ctrl+Shift+F12 workflow restarts never repeat Nano Banana activation
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
        """Remove project title/script data but preserve sibling engine/status settings."""
        if isinstance(node, list):
            for item in node:
                _remove_project_payload(item)
            return
        if not isinstance(node, dict):
            return
        key_map = {_normalise_key(key): key for key in list(node.keys())}
        has_title = any(k in key_map for k in ("projecttitle", "projectname"))
        has_script = any(k in key_map for k in ("script", "scriptjson"))
        if has_title and has_script:
            for normalized in ("projecttitle", "projectname", "script", "scriptjson"):
                original_key = key_map.get(normalized)
                if original_key is not None:
                    node.pop(original_key, None)
        for key in list(node.keys()):
            value = node[key]
            if _normalise_key(key) == "projectname":
                node.pop(key, None)
            elif isinstance(value, (dict, list)):
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

    def on_restart_shortcut():
        restart_from_url_event.set()
        print("🔁 [HOTKEY] Ctrl+Shift+F12 pressed — restarting from GOOGLE_FLOW_URL without checking the current page.")

    def on_terminate_shortcut():
        nonlocal terminate_automation
        terminate_automation = True
        stop_event.set()
        print("🛑 [HOTKEY] Alt+/ pressed — manual stop requested.")

    def check_for_termination():
        nonlocal last_exit_editing_check_at, exit_editing_check_active
        nonlocal download_ui_sequence_active

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
                location = pyautogui.locateCenterOnScreen(variant_path, confidence=confidence, grayscale=False)
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
                    location = pyautogui.locateCenterOnScreen(variant_path, confidence=confidence, grayscale=False)
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

    def click_startup_nanobanana_16ratio9(hwnd):
        """Click only the exact 16:9 Nano Banana reference image, once when requested."""
        image_name = "nanobanana_16ratio9.png"
        image_path = os.path.join(GUI_IMAGES, image_name)

        # Do not use find_image_with_fallback here: it scans numbered variants.
        # This startup action is deliberately restricted to this exact file.
        if not os.path.isfile(image_path):
            print(
                f"⚠️ [NANO-BANANA] Exact reference image is missing: {image_path}. "
                "No other ratio image will be searched or clicked."
            )
            return False

        check_for_termination()
        enforce_window_focus(hwnd)
        try:
            location = pyautogui.locateCenterOnScreen(
                image_path,
                confidence=0.8,
                grayscale=False
            )
        except Exception as image_error:
            print(
                f"⚠️ [NANO-BANANA] Could not inspect {image_name}: {image_error}. "
                "No other ratio image will be searched or clicked."
            )
            return False

        if location is None:
            print(
                f"ℹ️ [NANO-BANANA] {image_name} is not visible on the current screen. "
                "The one-time startup check is complete; no other ratio image will be checked."
            )
            return False

        pyautogui.click(int(location.x), int(location.y))
        print(
            f"✅ [NANO-BANANA] Clicked {image_name} once at "
            f"({location.x}, {location.y}). No other ratio image was searched or clicked."
        )
        _sleep(0.8)
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

    def click_right_edge_of_image(image_name, confidence=0.7):
        variants = get_image_variants(image_name)
        for variant_path in variants:
            try:
                location = pyautogui.locateOnScreen(variant_path, confidence=confidence)
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

    # --- DOWNLOAD HELPERS (same as original) ---
    def check_and_rename_download(
        entry_name, images_folder, timeout_seconds=40, check_interval=0.3,
        force_png=False
    ):
        timeout_seconds = _bounded_timeout(timeout_seconds)
        print(f"📊 [DOWNLOAD] Monitoring for download for {entry_name}...")
        try:
            hud.print("Waiting for the download to finish...", "waiting")
        except Exception:
            pass
        update_operation_status(f"Waiting for download: {entry_name}")

        downloads_folder = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads_folder):
            print(f"❌ [DOWNLOAD] Downloads folder not found: {downloads_folder}")
            return False, None

        initial_files = {}
        try:
            with os.scandir(downloads_folder) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            stat = entry.stat()
                            initial_files[entry.name] = {'path': entry.path, 'time': stat.st_mtime, 'size': stat.st_size}
                        except Exception:
                            pass
            print(f"📁 [DOWNLOAD] Found {len(initial_files)} existing files before download")
        except Exception as e:
            print(f"⚠️ [DOWNLOAD] Error scanning existing files: {e}")
            initial_files = {}

        start_time = time.time()
        download_detected = False
        downloaded_file_path = None
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}

        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            check_and_click_exit_editing()
            elapsed = int(time.time() - start_time)
            try:
                if os.path.exists(downloads_folder):
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file():
                                file_name = entry.name
                                file_ext = os.path.splitext(file_name)[1].lower()
                                is_new_file = file_name not in initial_files
                                is_recent = False
                                try:
                                    stat = entry.stat()
                                    if stat.st_mtime > start_time - 10:
                                        is_recent = True
                                except Exception:
                                    pass
                                if (is_new_file or is_recent) and file_ext in image_extensions:
                                    print(f"🆕 [DOWNLOAD] Found new/updated image file: {file_name}")
                                    print(f"   📁 Path: {entry.path}")
                                    print(f"   📏 Size: {stat.st_size} bytes")
                                    stable_count = 0
                                    stable_size = 0
                                    max_stable_checks = 5
                                    while stable_count < 3 and stable_count < max_stable_checks:
                                        if time.time() - start_time >= timeout_seconds:
                                            break
                                        try:
                                            current_size = os.path.getsize(entry.path)
                                            if current_size == stable_size and current_size > 1024:
                                                stable_count += 1
                                                print(f"   ⏳ File stable ({stable_count}/3), size: {current_size} bytes")
                                            else:
                                                stable_count = 0
                                                stable_size = current_size
                                                print(f"   ⏳ File size changing: {current_size} bytes")
                                        except Exception as e:
                                            print(f"   ⚠️ Error checking size: {e}")
                                        _sleep(min(0.3, max(0.0, timeout_seconds - (time.time() - start_time))))
                                    if stable_count >= 3:
                                        print(f"✅ [DOWNLOAD] File stable and ready!")
                                        downloaded_file_path = entry.path
                                        download_detected = True
                                        break
                                    else:
                                        print(f"⚠️ [DOWNLOAD] File not stable, continuing to monitor...")
                                elif file_name.endswith('.crdownload') or file_name.endswith('.tmp'):
                                    print(f"⏳ [DOWNLOAD] Found temp download: {file_name}")
                            if download_detected:
                                break
                if download_detected and downloaded_file_path:
                    break
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ [DOWNLOAD] Still waiting for download... ({elapsed}s elapsed)")
                    try:
                        hud.print(f"Still downloading... ({elapsed}s)", "waiting")
                    except Exception:
                        pass
                    update_operation_status(f"Waiting for download {entry_name}... ({elapsed}s)")
                _sleep(check_interval)
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Error in monitoring loop: {e}")
                _sleep(check_interval)
                continue

        if not download_detected or not downloaded_file_path:
            print(f"⏰ [DOWNLOAD] Timeout or no download detected after {timeout_seconds} seconds")
            try:
                print(f"🔍 [DOWNLOAD] Performing final scan for new image files...")
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file():
                            file_name = entry.name
                            file_ext = os.path.splitext(file_name)[1].lower()
                            if file_ext in image_extensions:
                                try:
                                    stat = entry.stat()
                                    if stat.st_mtime > start_time - 10:
                                        print(f"🆕 [DOWNLOAD] Found new file in final scan: {file_name}")
                                        downloaded_file_path = entry.path
                                        download_detected = True
                                        break
                                except Exception:
                                    pass
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Final scan error: {e}")

        if not download_detected or not downloaded_file_path:
            print(f"❌ [DOWNLOAD] No download detected")
            return False, None

        try:
            file_name = os.path.basename(downloaded_file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            new_filename = f"{entry_name}.png" if force_png else f"{entry_name}{file_ext}"
            target_path = os.path.join(images_folder, new_filename)
            if not os.path.exists(images_folder):
                os.makedirs(images_folder, exist_ok=True)
            if not os.path.exists(downloaded_file_path):
                print(f"❌ [DOWNLOAD] File no longer exists: {downloaded_file_path}")
                return False, None

            try:
                _sleep(0.5)
                if force_png:
                    # Do not just rename a JPG/WebP file to .png. Convert the
                    # downloaded image so Thumbnail.png is a genuine PNG file.
                    from PIL import Image
                    with Image.open(downloaded_file_path) as source_image:
                        converted = source_image.convert(
                            "RGBA" if "A" in source_image.getbands() else "RGB"
                        )
                        converted.save(target_path, format="PNG", optimize=True)
                    try:
                        os.remove(downloaded_file_path)
                    except OSError:
                        pass
                    print(f"✅ [DOWNLOAD] Thumbnail converted and saved as: {new_filename}")
                else:
                    # Replace only the same expected entry filename if a retry
                    # is correcting a previously invalid/partial download.
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    try:
                        os.replace(downloaded_file_path, target_path)
                    except OSError:
                        import shutil
                        shutil.copy2(downloaded_file_path, target_path)
                        try:
                            os.remove(downloaded_file_path)
                        except OSError:
                            pass
                    print(f"✅ [DOWNLOAD] File saved as: {new_filename}")

                print(f"📁 [DOWNLOAD] Moved to: {target_path}")
                try:
                    hud.print("Saved successfully.", "success")
                except Exception:
                    pass
                update_operation_status(f"Downloaded and saved: {new_filename}")
                return True, target_path
            except Exception as e:
                print(f"❌ [DOWNLOAD] Failed to save/convert downloaded image: {e}")
                traceback.print_exc()
                return False, None
        except Exception as e:
            print(f"❌ [DOWNLOAD] Error processing downloaded file: {e}")
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
                rendering_again = find_image("imagerenderingprogress.png", confidence=0.7)
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
                moregf_location = find_image("moregf.png", confidence=0.7)
                if moregf_location:
                    print(
                        f"✅ [GF-DOWNLOAD] moregf.png found at "
                        f"({moregf_location.x}, {moregf_location.y}); clicking its right edge."
                    )
                    clicked = click_right_edge_of_image("moregf.png", confidence=0.7)
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
                pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                pyautogui.click()
                _sleep(0.5)
                print(f"✅ [GF-DOWNLOAD] Clicked downloadgfimage.png")
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
                timeout_seconds = 30 if download_attempts == 1 else 20
                download_success, file_path = check_and_rename_download(
                    entry_name,
                    images_folder,
                    timeout_seconds=timeout_seconds,
                    check_interval=0.3,
                    force_png=force_png
                )
                if download_success:
                    print(f"✅ [GF-DOWNLOAD] Download successful on attempt {download_attempts}")
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
                    more_retry_location = find_image("moregf.png", confidence=0.7)
                    if more_retry_location:
                        click_right_edge_of_image("moregf.png", confidence=0.7)
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

    def main_google_flow_workflow(force_url_restart=False, activate_startup_nanobanana=False):
        try:
            if not os.path.exists(GUI_IMAGES):
                print(f"❌ Error: GUI_IMAGES path not found: {GUI_IMAGES}")
                try:
                    hud.print("A required folder is missing.", "error")
                except Exception:
                    pass
                update_operation_status(f"GUI_IMAGES path not found: {GUI_IMAGES}", is_error=True)
                return

            images_folder = os.path.join(IMAGES_PATH, project_title)
            print(f"🎬 [MAIN] Starting Google Flow image generation workflow...")
            print(f"🖥️ [MAIN] GUI Images path: {GUI_IMAGES}")
            print(f"📁 [MAIN] Project: '{project_title}'")
            print(f"📁 [MAIN] Images folder: {images_folder}")
            print(f"📊 [MAIN] Total entries: {total_entries}")

            try:
                hud.print(f"Preparing to generate {total_entries} images...", "initializing")
            except Exception:
                pass

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

            # Nano Banana ratio selection is allowed only for the first normal
            # function-start attempt. The supervisor passes False on every
            # automatic or shortcut-triggered workflow restart.
            if activate_startup_nanobanana:
                print(
                    "🟦 [NANO-BANANA] Fresh function execution detected. "
                    "Checking only nanobanana_16ratio9.png once."
                )
                click_startup_nanobanana_16ratio9(hwnd)
            else:
                print(
                    "⏭️ [NANO-BANANA] Startup activation is disabled for this attempt "
                    "(workflow restart or not the initial function execution)."
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

                # Attempt 1 is the only attempt that may activate Nano Banana,
                # and a shortcut-requested URL restart is explicitly excluded.
                activate_startup_nanobanana = (
                    restart_number == 1 and not force_this_attempt
                )
                if activate_startup_nanobanana:
                    print(
                        "🟦 [NANO-BANANA] One-time startup activation enabled for "
                        "the initial function execution only."
                    )
                else:
                    print(
                        "⏭️ [NANO-BANANA] Ratio activation skipped: this is not "
                        "the initial uninterrupted function-start attempt."
                    )

                main_google_flow_workflow(
                    force_url_restart=force_this_attempt,
                    activate_startup_nanobanana=activate_startup_nanobanana
                )
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

def video_producer():
    """
    Run the complete video-producer queue while keeping the Windows display and
    system awake from function entry until every queued project is finished.
    The Windows execution-state request is refreshed on a dedicated worker
    thread every five seconds, including queue lookup, imports, transcription,
    image preparation, caption generation, clip assembly, encoding, and recursion.
    """
    import os as _awake_os
    import threading as _awake_threading

    _awake_stop = _awake_threading.Event()
    _awake_ready = _awake_threading.Event()
    _awake_state = {"first_result": None, "error": None}

    def _keep_awake_worker():
        set_execution_state = None
        try:
            if _awake_os.name != "nt":
                _awake_state["error"] = "Windows keep-awake is only available on Windows"
                _awake_ready.set()
                return

            import ctypes as _awake_ctypes
            kernel32 = _awake_ctypes.windll.kernel32
            set_execution_state = kernel32.SetThreadExecutionState
            set_execution_state.argtypes = [_awake_ctypes.c_uint]
            set_execution_state.restype = _awake_ctypes.c_uint

            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            # Prevent both system sleep and display idle timeout.
            required_state = 0x80000000 | 0x00000001 | 0x00000002
            while not _awake_stop.is_set():
                result = set_execution_state(required_state)
                if _awake_state["first_result"] is None:
                    _awake_state["first_result"] = int(result)
                    _awake_ready.set()
                if _awake_stop.wait(5.0):
                    break
        except Exception as awake_exc:
            _awake_state["error"] = str(awake_exc)
            _awake_ready.set()
        finally:
            # Release this worker thread's execution-state request only after
            # the complete producer call (including queued projects) has ended.
            if set_execution_state is not None:
                try:
                    set_execution_state(0x80000000)  # ES_CONTINUOUS only
                except Exception:
                    pass

    _awake_thread = _awake_threading.Thread(
        target=_keep_awake_worker,
        name="VideoProducerKeepAwake",
        daemon=True,
    )
    _awake_thread.start()
    _awake_ready.wait(timeout=3.0)

    if _awake_os.name == "nt":
        if _awake_state["first_result"]:
            print("🖥️ [KEEP-AWAKE] Windows system and display awake protection is active; refreshing every 5 seconds from function start")
        elif _awake_state["error"]:
            print(f"⚠️ [KEEP-AWAKE] Could not activate Windows keep-awake: {_awake_state['error']}")
        else:
            print("⚠️ [KEEP-AWAKE] Windows keep-awake worker did not confirm its first refresh")
    else:
        print("ℹ️ [KEEP-AWAKE] Windows display/system sleep prevention is unavailable on this operating system")

    def _run_video_producer():
        """
        Assemble entry_N images into a narrated video using AI-directed per-entry
        transitions and keyframes, speech-synchronized captions, and subscribe stickers.
        - The JSON transition_to_next object controls each scene boundary.
        - The JSON keyframes object controls each scene's camera-motion sequence.
        - No random or duration-pool camera/transition selection is performed.
        - Final caption words are accelerated when needed so each row completes
          before the following caption row takes over.
        - Stage/Step/Level/Example headings are detected from dynamic JSON metadata,
          synchronized to the actual spoken words using Faster-Whisper word timestamps,
          displayed as a full-screen black/white interstitial, then removed exactly
          when the heading finishes so the animated scene resumes underneath.
        - Heading words are omitted from ordinary captions while the centered overlay
          displays them. Overlay ASR still runs when ordinary captions are disabled.
        - AI-provided transition and keyframe identifiers, action sequences, zoom modes,
          labels, and supported descriptive keywords are normalized and executed.
        - Like/subscribe stickers are rendered at 50% of the currently supplied size.
        Captions and overlays are rendered frame-by-frame; source images are unchanged.
        Keeps the original project lookup, script_json timing, audio matching,
        image normalization, and memory-conscious sequential clip assembly.
        Requires: PANEL_PATH, IMAGES_PATH, plus Pillow and MoviePy.
        """
        import os
        import re
        import json
        import shutil
        import traceback
        import time
        import random
        import math
        from functools import lru_cache
        from PIL import Image, ImageDraw, ImageFont, ImageColor
        import numpy as np
        # Import from MoviePy's public package namespace. MoviePy 2.x removed
        # the old \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\`moviepy.editor\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\` module, so do not fall back to that path.
        try:
            from moviepy import VideoClip, AudioFileClip, concatenate_videoclips
        except ImportError as exc:
            print(
                "❌ MoviePy imports failed. Install/upgrade MoviePy with: "
                "python -m pip install --upgrade moviepy"
            )
            print(f"   Import details: {exc}")
            return None
        # READY_SCRIPT is the queue. Deduplicate by normalized project title,
        # then process the first project whose final video does not already exist.
        # Existing completed videos are skipped; no project is overwritten.
        if not os.path.exists(READY_SCRIPT):
            print(f"❌ READY_SCRIPT missing: {READY_SCRIPT}")
            return None
        def normalize_project_title(name):
            normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", str(name or ""))
            normalized = re.sub(r"\s+", "_", normalized)
            normalized = re.sub(r"_+", "_", normalized).strip("_")
            return normalized or "unnamed_project"
        try:
            with open(READY_SCRIPT, "r", encoding="utf-8") as file:
                ready_data = json.load(file)
        except Exception as exc:
            print(f"❌ Error reading READY_SCRIPT: {exc}")
            return None
        # Discover project records regardless of root shape or wrapper names.
        # This mirrors sceneiq_google_flow_images_generation_engine() and supports root lists,
        # {"value": {...}}, {"projects": [...]}, and deeper arbitrary nesting.
        def _normalise_key(key):
            return re.sub(r"[^a-z0-9]", "", str(key).lower())
        def _walk_json(node, path=()):
            yield path, node
            if isinstance(node, dict):
                for key, value in node.items():
                    yield from _walk_json(value, path + (key,))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    yield from _walk_json(value, path + (index,))
        def _find_field(node, aliases, require_value=True):
            wanted = {_normalise_key(alias) for alias in aliases}
            for _, current in _walk_json(node):
                if not isinstance(current, dict):
                    continue
                for key, value in current.items():
                    if _normalise_key(key) in wanted and (
                        not require_value or value not in (None, "", [], {})
                    ):
                        return value
            return None
        def _find_project_title(node):
            # Prefer explicit title fields; project_name may itself be a wrapper.
            value = _find_field(node, ("project_title", "projectTitle", "project_name", "projectName"))
            if isinstance(value, dict):
                value = _find_field(value, ("project_title", "projectTitle", "title", "name"))
            if isinstance(value, (str, int, float)) and str(value).strip():
                return str(value).strip()
            return None
        def _find_script_data(node):
            candidates = []
            for path, current in _walk_json(node):
                if not path or not isinstance(path[-1], str) or _normalise_key(path[-1]) != "script":
                    continue
                if isinstance(current, list):
                    score = 0
                    for item in current:
                        if isinstance(item, dict):
                            keys = {_normalise_key(k) for k in item}
                            if keys.intersection({
                                "sceneimagegeneration", "sceneimageprompt",
                                "imagegenerationprompt", "imageprompt",
                                "charactersreference", "characterreference",
                                "scenepovprompt", "shotnumber", "dialogue",
                                "narration", "voiceover", "spoken_text"
                            }):
                                score += 10
                            if "entries" in keys:
                                score += 2
                    candidates.append((score, len(current), current))
                elif isinstance(current, dict):
                    nested = _find_field(current, ("script",))
                    if isinstance(nested, list):
                        candidates.append((1, len(nested), nested))
                    else:
                        candidates.append((0, len(current), current))
            if candidates:
                candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
                return candidates[0][2]
            return None
        def _collect_project_records(node):
            records = []
            visited = set()
            def visit(current):
                if isinstance(current, list):
                    for child in current:
                        visit(child)
                    return
                if not isinstance(current, dict) or id(current) in visited:
                    return
                visited.add(id(current))
                title = _find_project_title(current)
                script = _find_script_data(current)
                if title and isinstance(script, (dict, list)) and bool(script):
                    records.append((current, title, script))
                    return
                # Continue through arbitrary wrappers and nested root records.
                for child in current.values():
                    if isinstance(child, (dict, list)):
                        visit(child)
            visit(node)
            # A wrapper may expose the same project more than once. Deduplicate by
            # normalized title while preserving the first occurrence.
            unique = []
            seen = set()
            for record, title, script in records:
                key = normalize_project_title(title).casefold()
                if key not in seen:
                    seen.add(key)
                    unique.append((record, title, script))
                else:
                    print(f"⏭️ [READY-SCRIPT] Duplicate project title skipped: {title}")
            return unique
        unique_projects = _collect_project_records(ready_data)
        if not unique_projects:
            print("❌ READY_SCRIPT contains no discoverable project title with a valid script.")
            return None
        def _has_entry_images(folder):
            if not folder or not os.path.isdir(folder):
                return False
            try:
                return any(
                    os.path.isfile(os.path.join(folder, name))
                    and re.fullmatch(
                        r"entry[_-]?\d+\.(png|jpg|jpeg|gif|bmp|webp|tiff)",
                        name,
                        re.IGNORECASE
                    )
                    and os.path.getsize(os.path.join(folder, name)) > 0
                    for name in os.listdir(folder)
                )
            except OSError as exc:
                print(f"⚠️ [READY-SCRIPT] Cannot inspect image folder '{folder}': {exc}")
                return False
        def _resolve_project_folder(title):
            """
            Resolve the generator's real folder first (original title with spaces),
            then the producer's legacy normalized folder, then a case/punctuation-
            insensitive match against actual directory names.
            """
            raw_title = str(title or "").strip()
            normalized_title = normalize_project_title(raw_title)
            candidates = [
                os.path.join(IMAGES_PATH, raw_title),
                os.path.join(IMAGES_PATH, normalized_title),
            ]
            try:
                if os.path.isdir(IMAGES_PATH):
                    wanted = re.sub(r"[^a-z0-9]", "", raw_title.casefold())
                    for dirname in os.listdir(IMAGES_PATH):
                        full = os.path.join(IMAGES_PATH, dirname)
                        if not os.path.isdir(full):
                            continue
                        actual_key = re.sub(r"[^a-z0-9]", "", dirname.casefold())
                        if actual_key == wanted:
                            candidates.append(full)
            except OSError as exc:
                print(f"⚠️ [READY-SCRIPT] Could not scan IMAGES_PATH: {exc}")
            seen_paths = set()
            for candidate_path in candidates:
                absolute = os.path.abspath(candidate_path)
                if absolute.casefold() in seen_paths:
                    continue
                seen_paths.add(absolute.casefold())
                if os.path.isdir(absolute):
                    return absolute
            return candidates[0]
        def _move_thumbnail_to_edited_folder(source_candidates, destination_folder):
            """Move the first valid Thumbnail.png into <project>/edited safely."""
            destination_path = os.path.join(destination_folder, "Thumbnail.png")
            source_path = None
            for candidate_path in source_candidates:
                if not candidate_path:
                    continue
                try:
                    if (
                        os.path.isfile(candidate_path)
                        and os.path.getsize(candidate_path) > 0
                    ):
                        source_path = candidate_path
                        break
                except OSError:
                    continue

            if source_path is None:
                if os.path.isfile(destination_path) and os.path.getsize(destination_path) > 0:
                    print(f"✅ [THUMBNAIL] Already present in edited folder: {destination_path}")
                    return destination_path
                print(
                    "⚠️ [THUMBNAIL] Thumbnail.png was not found in the project image folders; "
                    "the video can still be rendered, but no thumbnail was moved."
                )
                return None

            if os.path.abspath(source_path).casefold() == os.path.abspath(destination_path).casefold():
                print(f"✅ [THUMBNAIL] Thumbnail is already in the edited folder: {destination_path}")
                return destination_path

            os.makedirs(destination_folder, exist_ok=True)
            temporary_path = destination_path + f".incoming_{os.getpid()}.tmp"
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
                shutil.copy2(source_path, temporary_path)
                if not os.path.isfile(temporary_path) or os.path.getsize(temporary_path) <= 0:
                    raise IOError("The temporary thumbnail copy is missing or empty")
                os.replace(temporary_path, destination_path)
                try:
                    os.remove(source_path)
                except OSError as remove_exc:
                    print(
                        f"⚠️ [THUMBNAIL] Copied thumbnail to edited folder, but could not "
                        f"remove the source copy '{source_path}': {remove_exc}"
                    )
                print(f"📦 [THUMBNAIL] Moved Thumbnail.png to: {destination_path}")
                return destination_path
            except Exception:
                try:
                    if os.path.exists(temporary_path):
                        os.remove(temporary_path)
                except OSError:
                    pass
                raise
        panel_data = None
        project_title = None
        selected_script_data = None
        project_folder = None
        source_folder = None
        for candidate, candidate_title, candidate_script_data in unique_projects:
            candidate_folder = _resolve_project_folder(candidate_title)
            normalized_candidate_title = normalize_project_title(candidate_title)
            candidate_edited_folder = os.path.join(candidate_folder, "edited")
            expected_video = os.path.join(
                candidate_edited_folder, f"{normalized_candidate_title}.mp4"
            )
            # Also recognize a previously rendered file in a legacy normalized folder.
            legacy_folder = os.path.join(IMAGES_PATH, normalized_candidate_title)
            legacy_video = os.path.join(
                legacy_folder, "edited", f"{normalized_candidate_title}.mp4"
            )
            existing_video = next(
                (
                    path for path in (expected_video, legacy_video)
                    if os.path.isfile(path) and os.path.getsize(path) > 0
                ),
                None
            )
            if existing_video:
                candidate_thumbnail_sources = [
                    os.path.join(candidate_folder, "Thumbnail.png"),
                    os.path.join(candidate_folder, "images", "Thumbnail.png"),
                    os.path.join(legacy_folder, "Thumbnail.png"),
                    os.path.join(legacy_folder, "images", "Thumbnail.png"),
                ]
                try:
                    _move_thumbnail_to_edited_folder(
                        candidate_thumbnail_sources,
                        candidate_edited_folder,
                    )
                except Exception as thumbnail_exc:
                    print(f"⚠️ [THUMBNAIL] Could not move thumbnail for skipped project: {thumbnail_exc}")
                print(
                    f"⏭️ [READY-SCRIPT] Video already exists; skipping "
                    f"'{candidate_title}': {existing_video}"
                )
                continue
            candidate_image_folders = [
                os.path.join(candidate_folder, "images"),
                candidate_folder,
            ]
            if legacy_folder.casefold() != candidate_folder.casefold():
                candidate_image_folders.extend([
                    os.path.join(legacy_folder, "images"),
                    legacy_folder,
                ])
            found_image_folder = next(
                (folder for folder in candidate_image_folders if _has_entry_images(folder)),
                None
            )
            if not found_image_folder:
                print(
                    f"⚠️ [READY-SCRIPT] No entry images found for '{candidate_title}'. "
                    f"Checked project folder: {candidate_folder}"
                )
                continue
            panel_data = candidate
            project_title = candidate_title
            selected_script_data = candidate_script_data
            project_folder = candidate_folder
            source_folder = found_image_folder
            print(f"🎯 [READY-SCRIPT] Selected next unfinished project: '{project_title}'")
            print(f"📂 [READY-SCRIPT] Resolved project folder: {project_folder}")
            print(f"🖼️ [READY-SCRIPT] Resolved entry-image folder: {source_folder}")
            break
        if panel_data is None or not project_title:
            print(
                "✅ [READY-SCRIPT] No unfinished projects remain "
                "(or no eligible project has images and script data)."
            )
            return None
        def _setting_is_yes(value):
            return str(value if value is not None else "").strip().casefold() == "yes"
        raw_transition_setting = _find_field(
            panel_data, ("include_transitions", "includeTransitions")
        )
        # The project-level flag is only a master safety switch. When absent or
        # enabled, each entry's transition_to_next object makes the actual decision.
        # A project-level explicit "no" disables every transition.
        include_transitions = (
            str(raw_transition_setting).strip().casefold() not in
            {"no", "false", "0", "off", "disabled"}
            if raw_transition_setting not in (None, "")
            else True
        )
        include_captions = _setting_is_yes(
            _find_field(panel_data, ("include_captions", "includeCaptions"))
        )
        print(
            f"⚙️ [VIDEO-OPTIONS] AI-directed per-entry transitions: "
            f"{'ENABLED' if include_transitions else 'GLOBALLY DISABLED'} | "
            f"Captions: {'ON' if include_captions else 'OFF'}"
        )
        normalized_project_title = normalize_project_title(project_title)
        # project_folder and source_folder were resolved from the actual on-disk
        # directory. Do not rebuild project_folder from the sanitized title here:
        # Google Flow stores projects under the original title (usually spaces).
        if not project_folder or not os.path.isdir(project_folder):
            print(f"❌ [READY-SCRIPT] Resolved project folder is unavailable: {project_folder}")
            return None
        if not source_folder or not _has_entry_images(source_folder):
            print(f"❌ [READY-SCRIPT] Resolved image folder has no valid entry_N images: {source_folder}")
            return None
        try:
            verified_image_names = [
                name for name in os.listdir(source_folder)
                if re.fullmatch(
                    r"entry[_-]?\d+\.(png|jpg|jpeg|gif|bmp|webp|tiff)",
                    name,
                    re.IGNORECASE
                )
                and os.path.isfile(os.path.join(source_folder, name))
                and os.path.getsize(os.path.join(source_folder, name)) > 0
            ]
            print(
                f"✅ [READY-SCRIPT] Confirmed {len(verified_image_names)} "
                f"non-empty entry image(s) in: {source_folder}"
            )
        except OSError as exc:
            print(f"❌ [READY-SCRIPT] Cannot read resolved image folder: {exc}")
            return None
        edited_folder = os.path.join(project_folder, "edited")
        temp_folder = os.path.join(project_folder, "temp_captions")
        os.makedirs(edited_folder, exist_ok=True)
        thumbnail_path = _move_thumbnail_to_edited_folder(
            [
                os.path.join(source_folder, "Thumbnail.png"),
                os.path.join(project_folder, "Thumbnail.png"),
                os.path.join(project_folder, "images", "Thumbnail.png"),
            ],
            edited_folder,
        )
        if include_captions:
            os.makedirs(temp_folder, exist_ok=True)
        def parse_timestamp_to_seconds(value):
            if value is None:
                return 0.0
            value = str(value).strip()
            try:
                parts = value.split(":")
                if len(parts) == 2:
                    return float(int(parts[0]) * 60 + float(parts[1]))
                if len(parts) == 3:
                    return float(int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2]))
            except (ValueError, TypeError):
                pass
            return 0.0
        def get_entries(data):
            """
            Read scenes from the SAME panel.json location used by the Google Flow
            image-generation function:
                panel_data["project_name"]["script_json"]["script"]
            Supports both:
              1. New scene-by-scene script lists containing fields such as
                 characters_reference and scene_Image_generation.
              2. Older nested batches containing an "entries" list and
                 scene_pov_prompt.
            Caption text is taken from a narration/dialogue field if one exists.
            No separate JSON file is required.
            """
            # Use the same structure-independent script discovery as the Google
            # Flow generator; do not assume project_name/script_json wrapper keys.
            script_data = selected_script_data
            if not isinstance(script_data, (dict, list)):
                script_data = _find_script_data(data)
            if not isinstance(script_data, (dict, list)):
                print(
                    "⚠️ [CAPTIONS] project_name.script_json.script exists but is not "
                    f"a dictionary/list (found {type(script_data).__name__})."
                )
                return []
            collected = []
            seen_ids = set()
            # These fields identify a scene object without requiring the legacy
            # scene_pov_prompt field to exist.
            scene_markers = {
                "scene_pov_prompt",
                "scene_Image_generation",
                "characters_reference",
                "shot_number",
                "dialogue",
                "narration",
                "voiceover",
                "voice_over",
                "spoken_text",
            }
            def is_scene_entry(item):
                return isinstance(item, dict) and bool(scene_markers.intersection(item.keys()))
            def add_entry(item):
                if not isinstance(item, dict):
                    return
                # Deduplicate the same dictionary if encountered through a wrapper.
                identity = id(item)
                if identity in seen_ids:
                    return
                seen_ids.add(identity)
                collected.append(dict(item))
            def walk(node):
                if isinstance(node, list):
                    for child in node:
                        if is_scene_entry(child):
                            add_entry(child)
                        elif isinstance(child, (dict, list)):
                            walk(child)
                    return
                if not isinstance(node, dict):
                    return
                # Legacy batch format: {"entries": [scene, scene, ...]}.
                entries_list = node.get("entries")
                if isinstance(entries_list, list):
                    for child in entries_list:
                        if isinstance(child, dict):
                            add_entry(child)
                # New direct scene object, e.g. an item in script: [...].
                if is_scene_entry(node):
                    add_entry(node)
                    return
                # Recurse through nested script containers while avoiding a second
                # pass through an entries list already collected above.
                for key, value in node.items():
                    if key == "entries":
                        continue
                    if isinstance(value, (dict, list)):
                        walk(value)
            walk(script_data)
            def first_text(entry, keys):
                for key in keys:
                    value = entry.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        return str(value)
                return ""
            caption_keys = (
                "dialogue",
                "narration",
                "voiceover",
                "voice_over",
                "voice_over_script",
                "spoken_text",
                "caption",
                "subtitle",
                "text",
            )
            result = []
            running_cursor = 0.0
            for index, entry in enumerate(collected):
                # A scene can qualify in the new format without scene_pov_prompt.
                # Ignore obvious non-scene metadata dictionaries.
                if not is_scene_entry(entry):
                    continue
                raw_start = entry.get("start", entry.get("start_time", entry.get("scene_start")))
                raw_stop = entry.get("stop", entry.get("end", entry.get("stop_time", entry.get("scene_end"))))
                start = parse_timestamp_to_seconds(raw_start) if raw_start is not None else running_cursor
                stop = parse_timestamp_to_seconds(raw_stop) if raw_stop is not None else None
                raw_duration = entry.get("duration", entry.get("duration_seconds", entry.get("scene_duration")))
                try:
                    explicit_duration = float(raw_duration) if raw_duration is not None else None
                except (ValueError, TypeError):
                    explicit_duration = None
                if stop is not None and stop > start:
                    duration = stop - start
                elif explicit_duration is not None and explicit_duration > 0:
                    duration = explicit_duration
                    stop = start + duration
                else:
                    # A reasonable fallback when the scene has no timing metadata.
                    duration = 5.0
                    stop = start + duration
                if duration <= 0:
                    duration = 5.0
                    stop = start + duration
                item = dict(entry)
                item["start_seconds"] = start
                item["stop_seconds"] = stop
                item["duration_seconds"] = duration
                # Keep source dialogue even when caption rendering is disabled.
                # Stage/step/level detection and subscribe-sticker matching must not
                # depend on the caption toggle.
                source_dialogue = first_text(entry, caption_keys)
                item["source_dialogue"] = source_dialogue
                item["dialogue"] = source_dialogue if include_captions else ""
                result.append(item)
                running_cursor = max(running_cursor, stop)
            # Preserve explicit timing order where present; for entries without
            # timestamps, the walk order is retained through running_cursor.
            result.sort(key=lambda item: item.get("start_seconds", 0.0))
            if include_captions:
                print(f"📚 [CAPTIONS] Read {len(result)} scene entries from panel.json")
                if result:
                    caption_count = sum(bool(item.get("dialogue")) for item in result)
                    print(f"📝 [CAPTIONS] {caption_count}/{len(result)} scenes contain caption/narration text")
                    if caption_count == 0:
                        print(
                            "⚠️ [CAPTIONS] Scene entries were found, but none contains dialogue/narration "
                            "text. Animated captions need a text field such as dialogue, narration, "
                            "voiceover, spoken_text, caption, or subtitle."
                        )
            else:
                print(f"📚 [VIDEO] Read {len(result)} scene entries; caption extraction is disabled")
            return result
        entries = get_entries(panel_data)
        if not entries:
            print("❌ No scene entries found in the discovered project script (new and legacy formats were checked).")
            return None
        def _entry_has_overlay_metadata(entry):
            if not isinstance(entry, dict):
                return False
            for key, value in entry.items():
                if re.fullmatch(r"(?:stage|step|level|example)_.+_involved", str(key), re.IGNORECASE):
                    if value is True or str(value).strip().casefold() in {"true", "yes", "1", "on", "enabled"}:
                        return True
            return False

        has_overlay_metadata = any(_entry_has_overlay_metadata(entry) for entry in entries)
        if has_overlay_metadata:
            print("🎯 [STAGE-OVERLAY] Dynamic Stage/Step/Level/Example metadata detected; speech-timed overlay processing is enabled")
        def get_sorted_images(folder_path):
            items = []
            for filename in os.listdir(folder_path):
                match = re.match(r"entry[_-]?(\d+)", filename, re.IGNORECASE)
                if not match or os.path.splitext(filename)[1].lower() not in {
                    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"
                }:
                    continue
                items.append({
                    "number": int(match.group(1)),
                    "filename": filename,
                    "path": os.path.join(folder_path, filename),
                })
            return sorted(items, key=lambda item: item["number"])
        image_files = get_sorted_images(source_folder)
        if not image_files:
            print("❌ No usable entry images found")
            return None
        def find_audio_file(title):
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads):
                return None
            audio_exts = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma")
            matches = [
                os.path.join(downloads, name)
                for name in os.listdir(downloads)
                if name.lower().endswith(audio_exts) and title.lower() in name.lower()
            ]
            return max(matches, key=os.path.getmtime) if matches else None
        audio_file_path = find_audio_file(project_title)
        if audio_file_path:
            print(f"🎵 Found audio: {os.path.basename(audio_file_path)}")
        else:
            print("⚠️ No matching audio found; video will be silent")
        import sys
        caption_progress_state = {"started": False, "finished": False, "last_percent": -1}

        def _update_caption_progress(percent, finish=False):
            if not caption_progress_state["started"] or caption_progress_state["finished"]:
                return
            percent = max(0, min(100, int(round(float(percent)))))
            percent = max(caption_progress_state["last_percent"], percent)
            if percent != caption_progress_state["last_percent"] or finish:
                bar_width = 32
                filled = int(round(bar_width * percent / 100.0))
                bar = "█" * filled + "░" * (bar_width - filled)
                sys.stdout.write(f"\\rGenerating Caption {percent:3d}% [{bar}]")
                sys.stdout.flush()
                caption_progress_state["last_percent"] = percent
            if finish:
                sys.stdout.write("\\n")
                sys.stdout.flush()
                caption_progress_state["finished"] = True

        def _start_caption_progress():
            if caption_progress_state["started"]:
                return
            caption_progress_state["started"] = True
            _update_caption_progress(0)

        def _close_caption_progress():
            if caption_progress_state["started"] and not caption_progress_state["finished"]:
                sys.stdout.write("\\n")
                sys.stdout.flush()
                caption_progress_state["finished"] = True

        if include_captions or has_overlay_metadata:
            # One ASR pass supplies word-level timing for captions and for dynamic
            # Stage/Step/Level/Example overlays. Overlay timing is still available
            # when ordinary captions are switched OFF.
            audio_words = []
            if audio_file_path and os.path.isfile(audio_file_path):
                try:
                    from faster_whisper import WhisperModel
                    whisper_model_name = os.environ.get("WHISPER_MODEL", "small")
                    whisper_device = os.environ.get("WHISPER_DEVICE", "cpu")
                    whisper_compute_type = os.environ.get(
                        "WHISPER_COMPUTE_TYPE",
                        "int8" if whisper_device.lower() == "cpu" else "float16"
                    )
                    print(
                        f"🗣️ [ASR] Loading Faster-Whisper model '{whisper_model_name}' "
                        f"({whisper_device}/{whisper_compute_type})..."
                    )
                    whisper_model = WhisperModel(
                        whisper_model_name,
                        device=whisper_device,
                        compute_type=whisper_compute_type,
                        cpu_threads=max(2, min(8, os.cpu_count() or 2)),
                    )
                    # First use Faster-Whisper's normal file-path decoder.
                    # Some older PyAV builds do not accept the metadata_errors
                    # keyword used by newer Faster-Whisper releases. If that exact
                    # compatibility error occurs, decode with FFmpeg ourselves and
                    # pass a 16 kHz mono float32 NumPy array to Faster-Whisper.
                    try:
                        segments, transcription_info = whisper_model.transcribe(
                            audio_file_path,
                            beam_size=5,
                            word_timestamps=True,
                            vad_filter=True,
                            condition_on_previous_text=True,
                        )
                    except TypeError as decode_exc:
                        if "metadata_errors" not in str(decode_exc):
                            raise
                        print(
                            "⚠️ [ASR] Installed PyAV is incompatible with Faster-Whisper's "
                            "audio decoder (metadata_errors unsupported). "
                            "Using FFmpeg audio-decoding fallback..."
                        )
                        import subprocess
                        ffmpeg_exe = None
                        try:
                            import imageio_ffmpeg
                            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                        except Exception:
                            ffmpeg_exe = shutil.which("ffmpeg")
                        if not ffmpeg_exe:
                            raise RuntimeError(
                                "PyAV compatibility fallback requires FFmpeg, but no "
                                "FFmpeg executable was found. Install imageio-ffmpeg "
                                "with `python -m pip install --upgrade imageio-ffmpeg`, "
                                "or install FFmpeg and add it to PATH."
                            ) from decode_exc
                        ffmpeg_command = [
                            ffmpeg_exe,
                            "-nostdin",
                            "-hide_banner",
                            "-loglevel", "error",
                            "-i", audio_file_path,
                            "-vn",
                            "-ac", "1",
                            "-ar", "16000",
                            "-f", "f32le",
                            "pipe:1",
                        ]
                        decoded_audio = subprocess.run(
                            ffmpeg_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                        )
                        if decoded_audio.returncode != 0:
                            ffmpeg_error = decoded_audio.stderr.decode(
                                "utf-8", errors="replace"
                            ).strip()
                            raise RuntimeError(
                                "FFmpeg could not decode the narration audio: "
                                + (ffmpeg_error or f"exit code {decoded_audio.returncode}")
                            ) from decode_exc
                        audio_array = np.frombuffer(
                            decoded_audio.stdout, dtype=np.float32
                        ).copy()
                        if audio_array.size == 0:
                            raise RuntimeError(
                                "FFmpeg returned empty audio; check the narration file."
                            ) from decode_exc
                        print(
                            f"✅ [ASR] FFmpeg decoded {audio_array.size / 16000:.2f}s "
                            "of 16 kHz mono audio; continuing with word timestamps."
                        )
                        segments, transcription_info = whisper_model.transcribe(
                            audio_array,
                            beam_size=5,
                            word_timestamps=True,
                            vad_filter=True,
                            condition_on_previous_text=True,
                        )
                    detected_language = getattr(transcription_info, "language", "unknown")
                    print(f"🗣️ [ASR] Detected language: {detected_language}")
                    try:
                        asr_duration = float(getattr(transcription_info, "duration", 0) or 0)
                    except (TypeError, ValueError):
                        asr_duration = 0.0
                    for segment in segments:
                        segment_words = getattr(segment, "words", None) or []
                        for word_info in segment_words:
                            spoken_word = str(getattr(word_info, "word", "") or "").strip()
                            word_start = getattr(word_info, "start", None)
                            word_end = getattr(word_info, "end", None)
                            if not spoken_word or word_start is None or word_end is None:
                                continue
                            word_start = max(0.0, float(word_start))
                            word_end = max(word_start + 0.015, float(word_end))
                            audio_words.append({
                                "word": spoken_word,
                                "start": word_start,
                                "end": word_end,
                            })
                    if not audio_words:
                        raise RuntimeError(
                            "Speech recognition returned no word timestamps. "
                            "Check that the audio contains clear speech."
                        )
                    print(
                        f"✅ [ASR] Recognized {len(audio_words)} words from the audio file."
                    )
                    print(
                        "📝 [ASR] Transcript: "
                        + " ".join(item["word"] for item in audio_words)
                    )
                    del whisper_model
                except ImportError as exc:
                    _close_caption_progress()
                    print(
                        "❌ faster-whisper is not installed. Install it with: "
                        "python -m pip install --upgrade faster-whisper"
                    )
                    print(f"   Import details: {exc}")
                    if include_captions:
                        return None
                    audio_words = []
                    print("⚠️ [STAGE-OVERLAY] Cannot synchronize headings without Faster-Whisper; continuing without spoken overlays")
                except Exception as exc:
                    _close_caption_progress()
                    print(f"❌ [ASR] Speech recognition failed: {exc}")
                    traceback.print_exc()
                    if include_captions:
                        return None
                    audio_words = []
                    print("⚠️ [STAGE-OVERLAY] ASR failed; continuing without spoken-heading overlays")
            else:
                audio_words = []
                print("⚠️ [ASR] No audio file found; captions and speech-timed Stage/Step/Level/Example overlays cannot be synchronized.")
        else:
            audio_words = []
            print("⏭️ [CAPTIONS] Disabled and no dynamic heading metadata exists; skipping Faster-Whisper")
        def discover_transparent_subscribe_stickers():
            """Return only image files that contain a real transparent background."""
            sticker_folder = globals().get("SUBSCRIBE_STICKERS")
            if not sticker_folder:
                print("⚠️ [SUBSCRIBE-STICKERS] Global SUBSCRIBE_STICKERS path is not defined")
                return []
            if not os.path.isdir(sticker_folder):
                print(f"⚠️ [SUBSCRIBE-STICKERS] Folder does not exist: {sticker_folder}")
                return []
            supported_extensions = (".gif", ".webp", ".apng")
            valid_stickers = []
            rejected_count = 0
            for filename in os.listdir(sticker_folder):
                path = os.path.join(sticker_folder, filename)
                if not os.path.isfile(path) or not filename.lower().endswith(supported_extensions):
                    continue
                try:
                    with Image.open(path) as source:
                        frame_count = max(1, int(getattr(source, "n_frames", 1)))
                        # The request is for animated stickers, not still images.
                        if frame_count <= 1:
                            rejected_count += 1
                            print(
                                f"⏭️ [SUBSCRIBE-STICKERS] Rejected static image (not animated): {filename}"
                            )
                            continue
                        transparent_frames = 0
                        total_duration_ms = 0
                        for frame_index in range(frame_count):
                            source.seek(frame_index)
                            frame_duration = source.info.get("duration", 100)
                            try:
                                frame_duration = max(20, int(frame_duration or 100))
                            except (TypeError, ValueError):
                                frame_duration = 100
                            total_duration_ms += frame_duration
                            rgba = source.convert("RGBA")
                            alpha_histogram = rgba.getchannel("A").histogram()
                            pixel_count = max(1, rgba.width * rgba.height)
                            transparent_ratio = sum(alpha_histogram[:255]) / pixel_count
                            visible_ratio = sum(alpha_histogram[1:]) / pixel_count
                            # A valid sticker needs both visible artwork and a meaningful
                            # transparent area. This rejects ordinary opaque GIFs.
                            if transparent_ratio >= 0.005 and visible_ratio >= 0.005:
                                transparent_frames += 1
                            rgba.close()
                        transparency_frame_ratio = transparent_frames / frame_count
                        # Animated stickers must retain transparency for most frames.
                        if transparency_frame_ratio < 0.70:
                            rejected_count += 1
                            print(
                                f"⏭️ [SUBSCRIBE-STICKERS] Rejected non-transparent/opaque file: {filename}"
                            )
                            continue
                        cycle_duration = max(0.10, total_duration_ms / 1000.0)
                        valid_stickers.append({
                            "path": path,
                            "filename": filename,
                            "cycle_duration": cycle_duration,
                        })
                except Exception as sticker_exc:
                    rejected_count += 1
                    print(
                        f"⚠️ [SUBSCRIBE-STICKERS] Could not inspect '{filename}': {sticker_exc}"
                    )
            random.shuffle(valid_stickers)
            print(
                f"✅ [SUBSCRIBE-STICKERS] {len(valid_stickers)} transparent sticker file(s) ready "
                f"({rejected_count} rejected); display scale is 50% of the previous size"
            )
            return valid_stickers
        def build_subscribe_sticker_events(scene_items):
            """
            Place one subscribe sticker in the centre of each scene whose source
            dialogue contains LIKE AND SUBSCRIBE or SUBSCRIBE. The sticker is fixed
            in screen position (never keyframed) and disappears 0.2s before the
            scene ends. This works with captions ON or OFF.
            """
            selected_events = []
            pool_index = 0
            previous_path = None
            scene_cursor = 0.0
            trigger_pattern = re.compile(r"\b(?:like\s+(?:and|&)\s+subscribe|subscribe)\b", re.IGNORECASE)
            triggered_scenes = []

            for scene_index, scene_item in enumerate(scene_items):
                scene_duration = max(0.0, float(scene_item.get("duration", 0.0)))
                scene_start = scene_cursor
                scene_end = scene_start + scene_duration
                scene_cursor = scene_end

                source_text = str(
                    scene_item.get("source_dialogue")
                    or scene_item.get("dialogue")
                    or ""
                )
                if trigger_pattern.search(source_text):
                    triggered_scenes.append((scene_index, scene_start, scene_end, scene_item))

            if not triggered_scenes:
                print("ℹ️ [SUBSCRIBE-STICKERS] No LIKE AND SUBSCRIBE / SUBSCRIBE scene found")
                return []

            sticker_pool = discover_transparent_subscribe_stickers()
            if not sticker_pool:
                print("⚠️ [SUBSCRIBE-STICKERS] No verified transparent stickers available; continuing without overlays")
                return []

            for scene_index, scene_start, scene_end, scene_item in triggered_scenes:
                # Keep the overlay on this scene only. It starts with the scene and
                # ends 0.2 seconds before the next scene can appear.
                sticker_start = scene_start
                sticker_end = scene_end - 0.2
                if sticker_end <= sticker_start + 0.05:
                    print(
                        f"⏭️ [SUBSCRIBE-STICKERS] Scene {scene_index + 1} is too short "
                        "to display a sticker safely before its final 0.2s."
                    )
                    continue

                if pool_index >= len(sticker_pool):
                    random.shuffle(sticker_pool)
                    if len(sticker_pool) > 1 and sticker_pool[0]["path"] == previous_path:
                        sticker_pool[0], sticker_pool[1] = sticker_pool[1], sticker_pool[0]
                    pool_index = 0

                selected_sticker = sticker_pool[pool_index]
                pool_index += 1
                previous_path = selected_sticker["path"]
                selected_events.append({
                    "path": selected_sticker["path"],
                    "filename": selected_sticker["filename"],
                    "start_time": sticker_start,
                    "end_time": sticker_end,
                    "display_duration": sticker_end - sticker_start,
                    "scene_index": scene_index,
                    "trigger_word": "subscribe",
                })
                print(
                    f"🎯 [SUBSCRIBE-STICKERS] Scene {scene_index + 1}: "
                    f"'{selected_sticker['filename']}' centred for "
                    f"{sticker_end - sticker_start:.2f}s "
                    "(fixed position; removed 0.20s before scene end)"
                )

            print(f"✅ [SUBSCRIBE-STICKERS] Scheduled {len(selected_events)} fixed-centre sticker overlay(s)")
            return selected_events
        # Force the finished video and every scene image to a fixed 16:9 frame.
        video_width, video_height = 1920, 1080
        print(f"📐 Output size (forced 16:9): {video_width}x{video_height}")
        def fit_image(image, width, height):
            # Fill the 16:9 frame by center-cropping excess edges, then resize.
            # This prevents letterboxing and ensures every normalized image is 16:9.
            image = image.convert("RGB")
            source_width, source_height = image.size
            target_ratio = width / height
            source_ratio = source_width / source_height
            if source_ratio > target_ratio:
                crop_width = int(source_height * target_ratio)
                left = max(0, (source_width - crop_width) // 2)
                image = image.crop((left, 0, left + crop_width, source_height))
            elif source_ratio < target_ratio:
                crop_height = int(source_width / target_ratio)
                top = max(0, (source_height - crop_height) // 2)
                image = image.crop((0, top, source_width, top + crop_height))
            return image.resize((width, height), Image.Resampling.LANCZOS)
        def load_font(size):
            candidates = [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            for font_path in candidates:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
            return ImageFont.load_default()
        def wrap_words(draw, text, font, max_width):
            words = text.split()
            lines, current = [], ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if draw.textbbox((0, 0), candidate, font=font, stroke_width=2)[2] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    # Keep exceptionally long words from running off-screen.
                    chunk = ""
                    for char in word:
                        test = chunk + char
                        if draw.textbbox((0, 0), test, font=font, stroke_width=2)[2] <= max_width:
                            chunk = test
                        else:
                            if chunk:
                                lines.append(chunk)
                            chunk = char
                    current = chunk
            if current:
                lines.append(current)
            return lines
        # Cache caption text measurements. Font and output dimensions stay unchanged.
        caption_text_width_cache = {}
        def _clean_caption_text(value):
            """Normalize whitespace and remove only a trailing scene-boundary comma."""
            value = re.sub(r"\s+", " ", str(value or "").strip())
            return re.sub(r",\s*$", "", value).rstrip()
        def _caption_text_width(draw, text, font):
            text = str(text or " ")
            cached = caption_text_width_cache.get(text)
            if cached is None:
                cached = draw.textbbox((0, 0), text, font=font, stroke_width=2)[2]
                if len(caption_text_width_cache) >= 50000:
                    caption_text_width_cache.clear()
                caption_text_width_cache[text] = cached
            return cached
        def _fit_word_suffix(draw, text, font, max_width):
            """Keep an exceptionally long word within the single visible row."""
            text = str(text or "")
            if not text:
                return ""
            if _caption_text_width(draw, text, font) <= max_width:
                return text
            for start_index in range(len(text)):
                suffix = text[start_index:]
                if _caption_text_width(draw, suffix, font) <= max_width:
                    return suffix
            return text[-1:]
        @lru_cache(maxsize=1)
        def _load_subscribe_sticker_animation(sticker_path, frame_width, frame_height):
            """Load and resize a transparent sticker animation only when it is needed."""
            # Keep the same sizing calculation as the prior producer version,
            # but halve its final rendered dimensions (4.0x -> 2.0x).
            max_sticker_width = max(1, int(frame_width * 0.40))
            max_sticker_height = max(1, int(frame_height * 0.28))
            sticker_scale_multiplier = 2.0
            max_cached_frames = 18
            try:
                with Image.open(sticker_path) as source:
                    frame_count = max(1, int(getattr(source, "n_frames", 1)))
                    frame_step = max(1, (frame_count + max_cached_frames - 1) // max_cached_frames)
                    animation_frames = []
                    pending_duration_ms = 0
                    total_duration_ms = 0
                    for frame_index in range(frame_count):
                        source.seek(frame_index)
                        raw_duration = source.info.get("duration", 100)
                        try:
                            frame_duration_ms = max(20, int(raw_duration or 100))
                        except (TypeError, ValueError):
                            frame_duration_ms = 100
                        pending_duration_ms += frame_duration_ms
                        total_duration_ms += frame_duration_ms
                        should_keep_frame = (
                            frame_index % frame_step == 0
                            or frame_index == frame_count - 1
                        )
                        if not should_keep_frame:
                            continue
                        sticker_frame = source.convert("RGBA")
                        original_width, original_height = sticker_frame.size
                        if original_width <= 0 or original_height <= 0:
                            sticker_frame.close()
                            pending_duration_ms = 0
                            continue
                        original_scale = min(
                            max_sticker_width / original_width,
                            max_sticker_height / original_height,
                            2.5,
                        )
                        scale = original_scale * sticker_scale_multiplier
                        resized_size = (
                            max(1, int(round(original_width * scale))),
                            max(1, int(round(original_height * scale))),
                        )
                        if resized_size != sticker_frame.size:
                            resized = sticker_frame.resize(
                                resized_size, Image.Resampling.LANCZOS
                            )
                            sticker_frame.close()
                            sticker_frame = resized

                        # The sticker is centred on the output frame. Any pixels
                        # beyond the video canvas would be clipped during paste,
                        # so crop those invisible edges now to control memory while
                        # retaining the full visible four-times-size result.
                        if (
                            sticker_frame.width > frame_width
                            or sticker_frame.height > frame_height
                        ):
                            crop_left = max(0, (sticker_frame.width - frame_width) // 2)
                            crop_top = max(0, (sticker_frame.height - frame_height) // 2)
                            crop_right = min(sticker_frame.width, crop_left + frame_width)
                            crop_bottom = min(sticker_frame.height, crop_top + frame_height)
                            visible_crop = sticker_frame.crop(
                                (crop_left, crop_top, crop_right, crop_bottom)
                            )
                            sticker_frame.close()
                            sticker_frame = visible_crop

                        animation_frames.append((
                            sticker_frame.copy(),
                            max(0.02, pending_duration_ms / 1000.0),
                        ))
                        sticker_frame.close()
                        pending_duration_ms = 0
                    if not animation_frames:
                        return (), 0.0
                    cycle_duration = max(0.02, total_duration_ms / 1000.0)
                    return tuple(animation_frames), cycle_duration
            except Exception as sticker_load_exc:
                print(
                    f"⚠️ [SUBSCRIBE-STICKERS] Could not load sticker '{os.path.basename(sticker_path)}': "
                    f"{sticker_load_exc}"
                )
                return (), 0.0
        def draw_animated_caption(frame_image, global_time, duration, caption_plan):
            """
            Preserve the existing single-row typewriter appearance, but reveal each
            recognized character according to the word timestamps detected in audio.
            """
            if not caption_plan:
                return frame_image
            width, height = frame_image.size
            now = max(0.0, float(global_time))
            # Render any active transparent sticker first, centered in both axes.
            # The caption is drawn afterwards, so the existing caption appearance remains intact.
            for sticker_event in caption_plan.get("sticker_events", []):
                sticker_start = float(sticker_event.get("start_time", 0.0))
                sticker_end = float(sticker_event.get("end_time", sticker_start))
                if not (sticker_start <= now < sticker_end):
                    continue
                animation_frames, animation_cycle = _load_subscribe_sticker_animation(
                    sticker_event["path"], width, height
                )
                if not animation_frames or animation_cycle <= 0:
                    continue
                animation_time = (now - sticker_start) % animation_cycle
                elapsed_frame_time = 0.0
                sticker_frame = animation_frames[-1][0]
                for candidate_frame, candidate_duration in animation_frames:
                    if animation_time < elapsed_frame_time + candidate_duration:
                        sticker_frame = candidate_frame
                        break
                    elapsed_frame_time += candidate_duration
                sticker_x = (width - sticker_frame.width) // 2
                sticker_y = (height - sticker_frame.height) // 2
                frame_image.paste(sticker_frame, (sticker_x, sticker_y), sticker_frame)
            events = caption_plan.get("events", [])
            if not events:
                return frame_image
            # IMPORTANT: original font-size calculation is unchanged.
            font_size = max(24, min(64, int(width / 35)))
            font = load_font(font_size)
            draw = ImageDraw.Draw(frame_image)
            event_starts = caption_plan["event_start_times"]
            low, high = 0, len(event_starts)
            while low < high:
                middle = (low + high) // 2
                if event_starts[middle] <= now:
                    low = middle + 1
                else:
                    high = middle
            event_index = low - 1
            if event_index < 0:
                return frame_image
            event = events[event_index]
            char_times = event["char_times"]
            # Reveal only characters whose corresponding spoken-word timing has
            # arrived. The text still appears with the same progressive typewriter.
            visible_count = 0
            for reveal_time in char_times:
                if reveal_time <= now:
                    visible_count += 1
                else:
                    break
            row = event["text"][:visible_count].rstrip()
            if not row:
                return frame_image
            bbox = draw.textbbox((0, 0), row or " ", font=font, stroke_width=1)
            line_height = bbox[3] - bbox[1]
            bottom_margin = int(height * 0.075)
            y = max(4, height - bottom_margin - line_height)
            anchor_width = max(
                1,
                min(
                    int(width * 0.84),
                    int(event.get("anchor_width", caption_plan["anchor_width"]))
                )
            )
            x_left = max(10, (width - anchor_width) // 2)
            # Existing shadow, white text and black outline remain unchanged.
            shadow_offset = max(2, font_size // 28)
            draw.text(
                (x_left + shadow_offset, y + shadow_offset),
                row,
                font=font,
                fill=(0, 0, 0),
                stroke_width=2,
                stroke_fill=(0, 0, 0),
            )
            draw.text(
                (x_left, y),
                row,
                font=font,
                fill=(255, 255, 255),
                stroke_width=1,
                stroke_fill=(0, 0, 0),
            )
            return frame_image

        def draw_stage_title_overlay(frame_image, global_time, overlay_events):
            """Cover the scene with its timed title, then reveal the moving scene again."""
            if not overlay_events:
                return frame_image
            now = max(0.0, float(global_time))
            active_event = next((event for event in overlay_events
                                 if float(event.get("start_time", 0.0)) <= now < float(event.get("end_time", 0.0))), None)
            if active_event is None:
                return frame_image

            width, height = frame_image.size
            background_name = str(active_event.get("background", "black")).casefold()
            background_rgb = (0, 0, 0) if background_name == "black" else (255, 255, 255)
            text_color_name = str(active_event.get("text_color", "white" if background_name == "black" else "black"))
            try:
                color_token = text_color_name.strip().replace("_", "")
                parsed_color = ImageColor.getrgb(color_token)
                text_rgb = tuple(parsed_color[:3])
            except Exception:
                text_rgb = (255, 255, 255) if background_name == "black" else (0, 0, 0)

            # Defend against low-contrast values while retaining valid authored colors.
            luminance = (0.2126 * text_rgb[0] + 0.7152 * text_rgb[1] + 0.0722 * text_rgb[2])
            if background_name == "black" and luminance < 105:
                text_rgb = (255, 255, 255)
            elif background_name == "white" and luminance > 175:
                text_rgb = (0, 0, 0)

            display_text = str(active_event.get("display_text") or "Stage").strip()
            overlay = Image.new("RGB", (width, height), background_rgb)
            draw = ImageDraw.Draw(overlay)

            # Large central heading. Shrink only as needed to keep long Example names
            # fully visible within the frame; never wrap the heading to a second row.
            font_size = max(72, int(min(width * 0.12, height * 0.22)))
            max_text_width = int(width * 0.88)
            max_text_height = int(height * 0.34)
            font = load_font(font_size)
            bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=2)
            while font_size > 48 and (
                (bbox[2] - bbox[0]) > max_text_width
                or (bbox[3] - bbox[1]) > max_text_height
            ):
                font_size -= 4
                font = load_font(font_size)
                bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=2)

            start_time = float(active_event.get("start_time", now))
            end_time = float(active_event.get("end_time", start_time + 0.1))
            spoken_duration = max(0.02, end_time - start_time)
            elapsed = max(0.0, now - start_time)
            # Finish typing in the first 55% of the pronunciation, leaving the
            # completed heading visible until the final spoken word has ended.
            reveal_duration = max(0.015, min(0.45, spoken_duration * 0.55))
            reveal_progress = min(1.0, elapsed / reveal_duration)
            visible_characters = min(
                len(display_text),
                max(1, int(math.ceil(len(display_text) * reveal_progress))),
            )
            visible_text = display_text[:visible_characters]
            bbox = draw.textbbox((0, 0), visible_text, font=font, stroke_width=2)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = int((width - text_width) / 2 - bbox[0])
            y = int((height - text_height) / 2 - bbox[1])
            outline_rgb = (0, 0, 0) if background_name == "white" else (255, 255, 255)
            draw.text(
                (x, y), visible_text, font=font, fill=text_rgb,
                stroke_width=2, stroke_fill=outline_rgb,
            )
            return overlay

        def build_caption_stream_plans(
            prepared_items,
            frame_width,
            recognized_words,
            sticker_events=None,
            suppressed_word_indices=None,
        ):
            """
            Build one continuous, single-row caption stream from ASR word timings.
            Each character is revealed during the actual spoken interval of its word.
            ASR words used by a centered Stage/Step/Level/Example overlay are excluded
            so the same heading is not duplicated in the bottom captions.
            """
            suppressed_word_indices = set(suppressed_word_indices or ())
            measure_canvas = Image.new("RGB", (frame_width, 100))
            measure_draw = ImageDraw.Draw(measure_canvas)
            # IMPORTANT: original font-size calculation is unchanged.
            font_size = max(24, min(64, int(frame_width / 35)))
            font = load_font(font_size)
            max_text_width = int(frame_width * 0.84)
            rows = []
            token_total = max(1, len(recognized_words))
            for token_index, token in enumerate(recognized_words):
                if token_index in suppressed_word_indices:
                    _update_caption_progress(((token_index + 1) / token_total) * 70)
                    continue
                raw_word = str(token.get("word", "")).strip()
                if not raw_word:
                    _update_caption_progress(((token_index + 1) / token_total) * 70)
                    continue
                display_word = raw_word.upper()
                if _caption_text_width(measure_draw, display_word, font) > max_text_width:
                    display_word = _fit_word_suffix(
                        measure_draw, display_word, font, max_text_width
                    )
                token_start = max(0.0, float(token.get("start", 0.0)))
                token_end = max(token_start + 0.015, float(token.get("end", token_start + 0.1)))
                if not rows:
                    rows.append({
                        "words": [],
                        "tokens": [],
                        "start_time": token_start,
                    })
                current_text = " ".join(rows[-1]["words"])
                candidate = f"{current_text} {display_word}".strip()
                if rows[-1]["words"] and _caption_text_width(
                    measure_draw, candidate, font
                ) > max_text_width:
                    rows.append({
                        "words": [],
                        "tokens": [],
                        "start_time": token_start,
                    })
                rows[-1]["words"].append(display_word)
                rows[-1]["tokens"].append({
                    "word": display_word,
                    "start": token_start,
                    "end": token_end,
                })
                _update_caption_progress(((token_index + 1) / token_total) * 70)
            row_widths = []
            row_total = max(1, len(rows))
            for row_index, row_info in enumerate(rows):
                row_text = " ".join(row_info["words"])
                row_widths.append(_caption_text_width(measure_draw, row_text, font))
                _update_caption_progress(70 + ((row_index + 1) / row_total) * 10)
            anchor_width = max(row_widths, default=1)
            events = []
            total_event_tokens = max(1, sum(len(row_info["tokens"]) for row_info in rows))
            processed_event_tokens = 0
            pretyped_row_count = 0
            for row_id, row_info in enumerate(rows):
                words = row_info["words"]
                tokens = row_info["tokens"]
                full_text = " ".join(words)
                row_start = float(row_info["start_time"])
                has_following_row = row_id + 1 < len(rows)
                next_row_start = (
                    float(rows[row_id + 1]["start_time"])
                    if has_following_row
                    else max(
                        sum(float(item["duration"]) for item in prepared_items),
                        max(
                            (token["end"] for token in row_info["tokens"]),
                            default=row_start
                        ) + 0.5
                    )
                )
                slot_duration = max(0.01, next_row_start - row_start)

                char_times = []
                word_char_starts = []
                for token_index, token in enumerate(tokens):
                    word = token["word"]
                    word_char_starts.append(len(char_times))
                    word_start = token["start"]
                    word_end = max(word_start + 0.015, token["end"])
                    word_duration = word_end - word_start

                    # Normal words follow their detected speech timings.
                    for char_index in range(len(word)):
                        reveal_time = word_start + (
                            (char_index + 1) / max(1, len(word))
                        ) * word_duration
                        if char_times:
                            reveal_time = max(reveal_time, char_times[-1])
                        char_times.append(reveal_time)

                    if token_index < len(tokens) - 1:
                        # The space appears as the next word begins.
                        space_time = tokens[token_index + 1]["start"]
                        if char_times:
                            space_time = max(space_time, char_times[-1])
                        char_times.append(space_time)

                    processed_event_tokens += 1
                    _update_caption_progress(80 + (processed_event_tokens / total_event_tokens) * 20)

                # CAPTION ROW HANDOFF FIX:
                # The final two words are deliberately pre-typed at a faster rate
                # and completed just BEFORE the next row becomes active. This stops
                # the previous row being cut off while its final word is unfinished.
                # The lead window adapts to the available row duration. If ASR places
                # preceding characters too close to the handoff, the pre-type window
                # expands leftward (one word at a time) to preserve chronological,
                # monotonic character reveal times.
                if has_following_row and len(tokens) >= 2 and char_times:
                    suffix_token_index = len(tokens) - 2

                    def _tail_start_char(token_index):
                        start_index = word_char_starts[token_index]
                        # Include the space immediately before the accelerated suffix.
                        return max(0, start_index - 1) if token_index > 0 else 0

                    tail_start_char = _tail_start_char(suffix_token_index)
                    handoff_margin = min(0.85, max(0.25, slot_duration * 0.12))
                    pretype_deadline = max(
                        row_start + 0.015,
                        next_row_start - handoff_margin,
                    )
                    pretype_lead = min(
                        1.35,
                        max(0.35, slot_duration * 0.32),
                    )
                    desired_pretype_start = max(
                        row_start,
                        pretype_deadline - pretype_lead,
                    )

                    # Only intervene when the last two words would otherwise begin
                    # too late or remain unfinished at the next-row handoff. Words
                    # already completed comfortably on their ASR timings are untouched.
                    suffix_already_starts_early = (
                        char_times[tail_start_char] <= desired_pretype_start
                    )
                    suffix_already_finishes = char_times[-1] <= pretype_deadline
                    if not (suffix_already_starts_early and suffix_already_finishes):
                        # If preceding ASR characters leave no room for the final
                        # two-word burst, extend the accelerated tail leftward.
                        while tail_start_char > 0:
                            prefix_last_time = char_times[tail_start_char - 1]
                            if prefix_last_time < pretype_deadline - 0.025:
                                break
                            suffix_token_index -= 1
                            tail_start_char = _tail_start_char(suffix_token_index)

                        prefix_last_time = (
                            char_times[tail_start_char - 1]
                            if tail_start_char > 0
                            else None
                        )
                        original_suffix_start = char_times[tail_start_char]
                        pretype_start = min(
                            original_suffix_start,
                            desired_pretype_start,
                        )
                        pretype_start = max(row_start, pretype_start)
                        if prefix_last_time is not None:
                            pretype_start = max(
                                pretype_start,
                                prefix_last_time + 0.008,
                            )

                        # Extremely compressed rows can leave no clean suffix window.
                        # Accelerate the complete row rather than allowing its final
                        # words to be cut off by the next row.
                        if pretype_start >= pretype_deadline:
                            tail_start_char = 0
                            pretype_start = row_start

                        suffix_length = len(char_times) - tail_start_char
                        available = max(0.005, pretype_deadline - pretype_start)
                        for suffix_offset in range(suffix_length):
                            reveal_time = pretype_start + (
                                (suffix_offset + 1) / max(1, suffix_length)
                            ) * available
                            char_index = tail_start_char + suffix_offset
                            if char_index > 0:
                                reveal_time = max(
                                    reveal_time,
                                    char_times[char_index - 1] + 0.001,
                                )
                            char_times[char_index] = min(pretype_deadline, reveal_time)

                        # Defensive monotonicity pass: the typewriter renderer reveals
                        # a continuous prefix, so no later character may be scheduled
                        # before an earlier character.
                        for char_index in range(1, len(char_times)):
                            char_times[char_index] = max(
                                char_times[char_index],
                                char_times[char_index - 1],
                            )
                        pretyped_row_count += 1

                events.append({
                    "row_id": row_id,
                    "start_time": row_start,
                    "slot_duration": slot_duration,
                    "text": full_text,
                    "char_times": char_times,
                    "anchor_width": max(row_widths[:row_id + 1], default=1),
                })
            try:
                measure_canvas.close()
            except Exception:
                pass
            caption_plan_summary = (
                f"📝 [CAPTIONS] Planned {len(events)} single-row caption segments "
                f"from {sum(len(row['tokens']) for row in rows)} recognized words. "
                f"Final-word pretyping enabled on {pretyped_row_count} row(s); "
                "normal words follow ASR timing and each row finishes before the next row."
            )
            scene_starts = []
            scene_cursor = 0.0
            for item in prepared_items:
                scene_starts.append(scene_cursor)
                scene_cursor += max(0.001, float(item.get("duration", 0.1)))
            _update_caption_progress(100, finish=True)
            print(caption_plan_summary)
            return {
                "events": events,
                "event_start_times": [event["start_time"] for event in events],
                "scene_starts": scene_starts,
                "anchor_width": anchor_width,
                "sticker_events": sticker_events or [],
            }
        def _contains_instructional_reference(dialogue):
            """Detect heading language for diagnostics only; never disable scene motion."""
            return bool(re.search(
                r"\b(?:stage|step|level|example)\s*(?:(?:no\.?|number)\s*)?#?\s*(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
                str(dialogue or ""), re.IGNORECASE,
            ))

        # These are the keyframe variations the AI storyboard may explicitly select.
        # The producer no longer picks from random/duration-based pools: it reads
        # each entry's keyframes object and executes that exact plan.
        KEYFRAME_VARIATIONS = [
            {"id": "pan_right", "label": "pan right", "sequence": ["pan_right"], "zoom_mode": "hold"},
            {"id": "pan_left", "label": "pan left", "sequence": ["pan_left"], "zoom_mode": "hold"},
            {"id": "pan_left_right", "label": "pan left + pan right", "sequence": ["pan_left", "pan_right"], "zoom_mode": "hold"},
            {"id": "pan_right_left", "label": "pan right + pan left", "sequence": ["pan_right", "pan_left"], "zoom_mode": "hold"},
            {"id": "zoom", "label": "zoom", "sequence": ["zoom_in"], "zoom_mode": "zoom_only"},
            {"id": "zoom_pan_left", "label": "zoom + pan left", "sequence": ["zoom_in", "pan_left"], "zoom_mode": "sequential"},
            {"id": "pan_left_zoom", "label": "pan left + zoom", "sequence": ["pan_left", "zoom_in"], "zoom_mode": "sequential"},
            {"id": "zoom_pan_right", "label": "zoom + pan right", "sequence": ["zoom_in", "pan_right"], "zoom_mode": "sequential"},
            {"id": "pan_right_zoom", "label": "pan right + zoom", "sequence": ["pan_right", "zoom_in"], "zoom_mode": "sequential"},
            {"id": "pan_right_left_zoom", "label": "pan right + pan left while zooming", "sequence": ["pan_right", "pan_left"], "zoom_mode": "concurrent_in"},
            {"id": "pan_left_right_zoom", "label": "pan left + pan right while zooming", "sequence": ["pan_left", "pan_right"], "zoom_mode": "concurrent_in"},
            {"id": "pan_left_right_center_zoom_reset", "label": "pan left + pan right + pan centre + zoom back", "sequence": ["pan_left", "pan_right", "pan_center"], "zoom_mode": "in_out"},
            {"id": "pan_left_right_zoom_soft", "label": "pan left + pan right + gentle zoom", "sequence": ["pan_left", "pan_right"], "zoom_mode": "concurrent_in_soft"},
            {"id": "pan_right_left_zoom_soft", "label": "pan right + pan left + gentle zoom", "sequence": ["pan_right", "pan_left"], "zoom_mode": "concurrent_in_soft"},
            {"id": "pan_center_zoom_out", "label": "recenter + zoom out", "sequence": ["pan_center_zoom_out"], "zoom_mode": "sequential"},
            # Legacy four-action ID is recognized for compatibility. Its sequence
            # is safely limited to the first three actions at execution time.
            {"id": "zoom_pan_left_right_center_reset", "label": "zoom + pan left + pan right + pan centre + zoom back (legacy; capped at 3 actions)", "sequence": ["zoom_in", "pan_left", "pan_right", "pan_center_zoom_out"], "zoom_mode": "sequential_reset"},
            {"id": "zoom_pan_left_right", "label": "zoom + pan left + pan right", "sequence": ["zoom_in", "pan_left", "pan_right"], "zoom_mode": "sequential"},
            {"id": "zoom_pan_right_left", "label": "zoom + pan right + pan left", "sequence": ["zoom_in", "pan_right", "pan_left"], "zoom_mode": "sequential"},
        ]
        KEYFRAME_BY_ID = {item["id"]: item for item in KEYFRAME_VARIATIONS}

        SUPPORTED_KEYFRAME_ACTIONS = {
            "pan_left",
            "pan_right",
            "pan_center",
            "zoom_in",
            "pan_center_zoom_out",
        }
        SUPPORTED_ZOOM_MODES = {
            "hold",
            "zoom_only",
            "sequential",
            "sequential_reset",
            "concurrent_in",
            "concurrent_in_soft",
            "in_out",
        }
        SUPPORTED_TRANSITIONS = {
            "none",
            "crossfade",
            "wipe_left",
            "wipe_right",
            "slide_left",
            "slide_right",
        }

        def _metadata_bool(value, default=False):
            if isinstance(value, bool):
                return value
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return bool(value)
            normalized = str(value).strip().casefold()
            if normalized in {"yes", "true", "1", "on", "enabled"}:
                return True
            if normalized in {"no", "false", "0", "off", "disabled", "none"}:
                return False
            return default

        def _normalise_metadata_token(value):
            return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().casefold()).strip("_")

        def extract_stage_overlay_specs(scene_entry):
            """Read the schema's dynamic {category}_{id}_* fields from one entry."""
            if not isinstance(scene_entry, dict):
                return []
            specs = []
            for field_name, involved_value in scene_entry.items():
                match = re.fullmatch(
                    r"(stage|step|level|example)_(.+)_involved",
                    str(field_name),
                    re.IGNORECASE,
                )
                if not match or not _metadata_bool(involved_value, default=False):
                    continue
                category = match.group(1).casefold()
                identifier = match.group(2).casefold()
                display_text = str(
                    scene_entry.get(f"{category}_{identifier}_display_text")
                    or f"{category.title()} {identifier.replace('_', ' ').title()}"
                ).strip()
                background = str(
                    scene_entry.get(f"{category}_{identifier}_background") or "black"
                ).strip().casefold()
                if background not in {"black", "white"}:
                    print(
                        f"⚠️ [STAGE-OVERLAY] Invalid background '{background}' for {display_text}; using black"
                    )
                    background = "black"
                text_color = str(
                    scene_entry.get(f"{category}_{identifier}_text_color")
                    or ("white" if background == "black" else "black")
                ).strip()
                specs.append({
                    "category": category,
                    "identifier": identifier,
                    "display_text": display_text,
                    "background": background,
                    "text_color": text_color,
                })
            return specs

        _NUMBER_WORDS = {
            "zero": "0", "one": "1", "two": "2", "three": "3",
            "four": "4", "five": "5", "six": "6", "seven": "7",
            "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
            "twelve": "12", "thirteen": "13", "fourteen": "14",
            "fifteen": "15", "sixteen": "16", "seventeen": "17",
            "eighteen": "18", "nineteen": "19", "twenty": "20",
            "first": "1", "second": "2", "third": "3", "fourth": "4",
            "fifth": "5", "sixth": "6", "seventh": "7", "eighth": "8",
            "ninth": "9", "tenth": "10", "eleventh": "11", "twelfth": "12",
            "thirteenth": "13", "fourteenth": "14", "fifteenth": "15",
            "sixteenth": "16", "seventeenth": "17", "eighteenth": "18",
            "nineteenth": "19", "twentieth": "20",
        }

        def _spoken_token(value):
            token = re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())
            if token in _NUMBER_WORDS:
                return _NUMBER_WORDS[token]
            # Whisper may return a hyphenated number as one token (for example,
            # "twenty-one"). Normalize common compound cardinal/ordinal forms.
            tens = {
                "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
                "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
            }
            units = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9,
            }
            for tens_word, tens_value in tens.items():
                if token.startswith(tens_word):
                    remainder = token[len(tens_word):]
                    if remainder in units:
                        return str(tens_value + units[remainder])
                    ordinal_units = {
                        "first": 1, "second": 2, "third": 3, "fourth": 4,
                        "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
                        "ninth": 9,
                    }
                    if remainder in ordinal_units:
                        return str(tens_value + ordinal_units[remainder])
            return token

        def _expected_overlay_phrases(spec):
            display_tokens = [_spoken_token(part) for part in re.findall(r"[A-Za-z0-9]+", spec["display_text"])]
            display_tokens = [part for part in display_tokens if part]
            candidates = []
            if display_tokens:
                candidates.append(display_tokens)
            identifier = spec["identifier"].replace("_", " ").strip()
            id_tokens = [_spoken_token(part) for part in re.findall(r"[A-Za-z0-9]+", identifier)]
            id_tokens = [part for part in id_tokens if part]
            category = spec["category"]
            if id_tokens:
                candidates.append([category] + id_tokens)
                if len(id_tokens) == 1 and id_tokens[0].isdigit():
                    number_value = int(id_tokens[0])
                    candidates.append([category, "number", id_tokens[0]])
                    ordinal_by_number = {value: key for key, value in _NUMBER_WORDS.items() if key in {
                        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                        "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth"
                    }}
                    ordinal = ordinal_by_number.get(id_tokens[0])
                    if ordinal:
                        candidates.append([_spoken_token(ordinal), category])
                    # Spoken multi-word numbers are normalized token-by-token by
                    # _spoken_token, e.g. "twenty two" -> ["20", "2"].
                    tens_value = (number_value // 10) * 10
                    unit_value = number_value % 10
                    if 20 < number_value < 100 and unit_value:
                        candidates.append([category, str(tens_value), str(unit_value)])
                        # Also recognize ordinal speech before the category, e.g.
                        # "twenty-first stage" for a visible "Stage 21" heading.
                        candidates.append([str(tens_value), str(unit_value), category])
                    elif 20 <= number_value < 100:
                        candidates.append([category, str(number_value)])
            unique = []
            seen = set()
            for candidate in candidates:
                key = tuple(candidate)
                if candidate and key not in seen:
                    seen.add(key)
                    unique.append(candidate)
            return unique

        def build_stage_overlay_events(prepared_items, scene_start_offsets, recognized_words):
            """Match each enabled overlay phrase to exact ASR word timestamps."""
            suppressed_word_indices = set()
            total_events = 0
            for scene_index, item in enumerate(prepared_items):
                specs = item.get("stage_overlay_specs", [])
                item_events = []
                if not specs:
                    item["stage_overlay_events"] = item_events
                    continue
                scene_start = float(scene_start_offsets[scene_index])
                scene_end = scene_start + float(item.get("duration", 0.0))
                normalized_words = [_spoken_token(word.get("word", "")) for word in recognized_words]
                for spec in specs:
                    matched = None
                    for phrase in _expected_overlay_phrases(spec):
                        phrase_len = len(phrase)
                        for word_index in range(max(0, len(normalized_words) - phrase_len + 1)):
                            if normalized_words[word_index:word_index + phrase_len] != phrase:
                                continue
                            first_word = recognized_words[word_index]
                            last_word = recognized_words[word_index + phrase_len - 1]
                            spoken_start = float(first_word.get("start", 0.0))
                            spoken_end = float(last_word.get("end", spoken_start))
                            # The reference must be spoken within this entry's own
                            # timeline. A small tolerance handles ASR boundary drift.
                            if spoken_start < scene_start - 0.30 or spoken_start >= scene_end + 0.10:
                                continue
                            if spoken_end <= scene_start or spoken_end > scene_end + 0.45:
                                continue
                            matched = (word_index, phrase_len, spoken_start, spoken_end)
                            break
                        if matched:
                            break
                    if not matched:
                        print(
                            f"⚠️ [STAGE-OVERLAY] Scene {scene_index + 1}: could not match spoken "
                            f"'{spec['display_text']}' to ASR words inside this entry; no overlay will be shown"
                        )
                        continue
                    first_index, phrase_len, spoken_start, spoken_end = matched
                    overlay_start = max(scene_start, spoken_start)
                    overlay_end = min(scene_end, spoken_end)
                    if overlay_end <= overlay_start:
                        continue
                    word_indices = list(range(first_index, first_index + phrase_len))
                    suppressed_word_indices.update(word_indices)
                    item_events.append({
                        **spec,
                        "start_time": overlay_start,
                        "end_time": overlay_end,
                        "spoken_duration": max(0.02, overlay_end - overlay_start),
                        "word_indices": word_indices,
                    })
                    total_events += 1
                    print(
                        f"🎯 [STAGE-OVERLAY] Scene {scene_index + 1}: '{spec['display_text']}' "
                        f"from {overlay_start:.2f}s to {overlay_end:.2f}s | "
                        f"full-screen {spec['background']} | text {spec['text_color']}"
                    )
                item_events.sort(key=lambda event: event["start_time"])
                # Prevent two separately declared headings from drawing on top of
                # each other if their detected speech intervals overlap.
                for event_index in range(len(item_events) - 1):
                    next_start = item_events[event_index + 1]["start_time"]
                    if item_events[event_index]["end_time"] > next_start:
                        item_events[event_index]["end_time"] = next_start
                        item_events[event_index]["spoken_duration"] = max(
                            0.02,
                            item_events[event_index]["end_time"] - item_events[event_index]["start_time"],
                        )
                item["stage_overlay_events"] = item_events
            print(
                f"✅ [STAGE-OVERLAY] Scheduled {total_events} speech-synchronized heading overlay(s); "
                f"{len(suppressed_word_indices)} heading word(s) excluded from ordinary captions"
            )
            return suppressed_word_indices

        def build_transition_plan(scene_entry):
            """
            Read the transition explicitly assigned by the storyboard to the
            boundary AFTER this entry. No camera-direction guessing or rotation.
            """
            raw = scene_entry.get(
                "transition_to_next",
                scene_entry.get("transition", scene_entry.get("transition_plan")),
            )
            if isinstance(raw, str):
                raw = {"type": raw}
            if not isinstance(raw, dict):
                raw = {}

            raw_type = (
                raw.get("type")
                or raw.get("transition_type")
                or raw.get("effect")
                or raw.get("name")
                or raw.get("keyword")
                or raw.get("transition_keyword")
                or raw.get("keywords")
                or raw.get("label")
                or "none"
            )
            if isinstance(raw_type, (list, tuple, set)):
                raw_type = " ".join(str(value) for value in raw_type)
            transition_type = _normalise_metadata_token(raw_type)
            transition_aliases = {
                "cut": "none", "direct_cut": "none", "hard_cut": "none",
                "straight_cut": "none", "no_transition": "none", "no_effect": "none",
                "fade": "crossfade", "cross_fade": "crossfade",
                "cross_dissolve": "crossfade", "dissolve": "crossfade",
                "fade_through": "crossfade", "soft_fade": "crossfade",
                "wipeleft": "wipe_left", "wipe_from_left": "wipe_left",
                "wipe_in_from_left": "wipe_left", "wipe_left_to_right": "wipe_left",
                "wiperight": "wipe_right", "wipe_from_right": "wipe_right",
                "wipe_in_from_right": "wipe_right", "wipe_right_to_left": "wipe_right",
                "slideleft": "slide_left", "slide_from_left": "slide_left",
                "slide_in_from_left": "slide_left", "slideright": "slide_right",
                "slide_from_right": "slide_right", "slide_in_from_right": "slide_right",
            }
            transition_type = transition_aliases.get(transition_type, transition_type)
            if transition_type not in SUPPORTED_TRANSITIONS:
                # Some prompt versions provide a descriptive keyword rather than
                # the canonical identifier in the type/label field.
                keyword_text = " ".join(str(raw.get(key) or "") for key in (
                    "keyword", "keywords", "transition_keyword", "label", "description", "reason"
                )).casefold()
                keyword_rules = (
                    (r"\b(?:crossfade|cross fade|cross dissolve|dissolve|fade)\b", "crossfade"),
                    (r"\b(?:wipe left|wipe from left|left wipe)\b", "wipe_left"),
                    (r"\b(?:wipe right|wipe from right|right wipe)\b", "wipe_right"),
                    (r"\b(?:slide left|slide from left|left slide)\b", "slide_left"),
                    (r"\b(?:slide right|slide from right|right slide)\b", "slide_right"),
                    (r"\b(?:direct cut|hard cut|straight cut|no transition)\b", "none"),
                )
                for pattern, canonical in keyword_rules:
                    if re.search(pattern, keyword_text):
                        transition_type = canonical
                        break
            if transition_type not in SUPPORTED_TRANSITIONS:
                print(
                    f"⚠️ [TRANSITIONS] Unsupported transition '{raw_type}'. "
                    "Using a direct cut for this boundary."
                )
                transition_type = "none"

            inferred_apply = transition_type != "none"
            apply_transition = _metadata_bool(
                raw.get("apply", raw.get("enabled")),
                default=inferred_apply,
            )
            if not include_transitions:
                apply_transition = False
            if not apply_transition or transition_type == "none":
                transition_type = "none"
                apply_transition = False

            raw_duration = (
                raw.get("duration_seconds")
                if raw.get("duration_seconds") is not None
                else raw.get("duration", raw.get("transition_duration", 0.34))
            )
            try:
                transition_duration_seconds = max(0.0, min(2.0, float(raw_duration)))
            except (TypeError, ValueError):
                transition_duration_seconds = 0.34 if apply_transition else 0.0
            if apply_transition and transition_duration_seconds <= 0:
                transition_duration_seconds = 0.34
            if not apply_transition:
                transition_duration_seconds = 0.0

            return {
                "apply": bool(apply_transition),
                "type": transition_type,
                "duration_seconds": transition_duration_seconds,
                "reason": str(raw.get("reason") or "").strip(),
            }

        def build_scene_motion_plan(scene_entry, dialogue, scene_index):
            """
            Translate an entry's explicit keyframes object into the renderer's
            motion_plan. Missing/disabled metadata means static; never randomize.
            """
            raw = (
                scene_entry.get("keyframes")
                or scene_entry.get("key_frames")
                or scene_entry.get("keyframe")
                or scene_entry.get("key_frame")
            )
            if isinstance(raw, str):
                raw = {"variation_id": raw}
            if not isinstance(raw, dict):
                raw = {}

            # Stage/Step/Level/Example wording is handled by a separate timed
            # overlay layer. It must NEVER override the scene's own camera plan.
            variation_value = (
                raw.get("variation_id")
                or raw.get("id")
                or raw.get("variation")
                or raw.get("variation_keyword")
                or raw.get("camera_movement")
                or raw.get("keyword")
                or raw.get("keywords")
                or raw.get("label")
                or ""
            )
            if isinstance(variation_value, list):
                variation_value = " ".join(str(value) for value in variation_value)
            variation_id = str(variation_value).strip()
            variation_key = _normalise_metadata_token(variation_id)
            variation_aliases = {
                "pan_center": "pan_center",
                "pan_centre": "pan_center",
                "zoom_in": "zoom",
                "pan_left_right_center": "pan_left_right_center_zoom_reset",
                "pan_left_right_centre_zoom_reset": "pan_left_right_center_zoom_reset",
                "left_right_center_zoom_reset": "pan_left_right_center_zoom_reset",
                "left_right_centre_zoom_reset": "pan_left_right_center_zoom_reset",
                "left_then_right": "pan_left_right",
                "pan_left_then_right": "pan_left_right",
                "pan_left_then_pan_right": "pan_left_right",
                "pan_left_and_then_right": "pan_left_right",
                "right_then_left": "pan_right_left",
                "pan_right_then_left": "pan_right_left",
                "pan_right_then_pan_left": "pan_right_left",
                "pan_right_and_then_left": "pan_right_left",
                "zoom_then_left": "zoom_pan_left",
                "zoom_then_pan_left": "zoom_pan_left",
                "left_then_zoom": "pan_left_zoom",
                "pan_left_then_zoom": "pan_left_zoom",
                "zoom_then_right": "zoom_pan_right",
                "zoom_then_pan_right": "zoom_pan_right",
                "right_then_zoom": "pan_right_zoom",
                "pan_right_then_zoom": "pan_right_zoom",
                "right_left_concurrent_zoom": "pan_right_left_zoom",
                "pan_right_then_left_while_zooming": "pan_right_left_zoom",
                "left_right_concurrent_zoom": "pan_left_right_zoom",
                "pan_left_then_right_while_zooming": "pan_left_right_zoom",
                "pan_left_then_right_with_concurrent_zoom": "pan_left_right_zoom",
                "pan_left_then_pan_right_with_zoom": "pan_left_right_zoom",
                "pan_left_and_right_while_zooming": "pan_left_right_zoom",
                "pan_left_right_with_zoom": "pan_left_right_zoom",
                "left_right_soft_zoom": "pan_left_right_zoom_soft",
                "pan_left_then_right_with_gentle_zoom": "pan_left_right_zoom_soft",
                "pan_left_right_with_soft_zoom": "pan_left_right_zoom_soft",
                "right_left_soft_zoom": "pan_right_left_zoom_soft",
                "pan_right_then_left_with_gentle_zoom": "pan_right_left_zoom_soft",
                "pan_right_left_with_soft_zoom": "pan_right_left_zoom_soft",
                "pan_right_then_left_with_concurrent_zoom": "pan_right_left_zoom",
                "pan_right_then_pan_left_with_zoom": "pan_right_left_zoom",
                "pan_right_left_with_zoom": "pan_right_left_zoom",
                "pan_right_and_left_while_zooming": "pan_right_left_zoom",
                "zoom_left_right": "zoom_pan_left_right",
                "zoom_then_left_then_right": "zoom_pan_left_right",
                "zoom_then_pan_left_and_right": "zoom_pan_left_right",
                "zoom_then_pan_left_then_right": "zoom_pan_left_right",
                "zoom_right_left": "zoom_pan_right_left",
                "zoom_then_right_then_left": "zoom_pan_right_left",
                "zoom_then_pan_right_and_left": "zoom_pan_right_left",
                "zoom_then_pan_right_then_left": "zoom_pan_right_left",
                "pan_center_zoom_out": "pan_center_zoom_out",
                "pan_centre_zoom_out": "pan_center_zoom_out",
                "pan_center_and_zoom_out": "pan_center_zoom_out",
                "pan_centre_and_zoom_out": "pan_center_zoom_out",
            }
            variation_key = variation_aliases.get(variation_key, variation_key)
            template = KEYFRAME_BY_ID.get(variation_key)

            has_explicit_keyframes = bool(raw) and (
                "enabled" in raw
                or "static" in raw
                or bool(variation_id)
                or isinstance(raw.get("sequence"), list)
                or isinstance(raw.get("actions"), list)
                or isinstance(raw.get("camera_actions"), list)
                or isinstance(raw.get("action_sequence"), list)
                or isinstance(raw.get("keywords"), list)
            )
            enabled = _metadata_bool(
                raw.get("enabled"),
                default=has_explicit_keyframes,
            )
            is_static = _metadata_bool(raw.get("static"), default=False)

            if not enabled or is_static:
                return {
                    "static": True,
                    "enabled": False,
                    "id": variation_key or "static",
                    "label": str(raw.get("label") or "STATIC — no camera movement"),
                    "group": raw.get("group"),
                    "end_position": "centre",
                    "sequence": [],
                    "zoom_mode": "hold",
                }

            raw_sequence = (
                raw.get("sequence")
                or raw.get("actions")
                or raw.get("camera_actions")
                or raw.get("action_sequence")
            )
            if raw_sequence is None and isinstance(raw.get("keywords"), list):
                # In some generated plans the camera action sequence is supplied
                # as a keyword array rather than under the canonical sequence key.
                keyword_actions = [
                    _normalise_metadata_token(action) for action in raw["keywords"]
                ]
                action_tokens = {
                    "pan_left", "pan_right", "pan_center", "pan_centre",
                    "center", "centre", "zoom", "zoom_in", "pan_center_zoom_out",
                    "pan_centre_zoom_out", "pan_center_and_zoom_out",
                    "pan_centre_and_zoom_out",
                }
                if keyword_actions and all(action in action_tokens for action in keyword_actions):
                    raw_sequence = raw["keywords"]
            if isinstance(raw_sequence, list):
                sequence = [
                    _normalise_metadata_token(action)
                    for action in raw_sequence
                    if str(action or "").strip()
                ]
            elif template:
                sequence = list(template["sequence"])
            else:
                sequence = []

            if not sequence and template:
                sequence = list(template["sequence"])

            if not sequence:
                print(
                    f"⚠️ [KEYFRAMES] Entry {scene_index + 1} has enabled keyframes "
                    "but no usable sequence/variation. Keeping the image static."
                )
                return {
                    "static": True,
                    "enabled": False,
                    "id": variation_key or "static_missing_sequence",
                    "label": "STATIC — missing valid keyframe sequence",
                    "group": raw.get("group"),
                    "end_position": "centre",
                    "sequence": [],
                    "zoom_mode": "hold",
                }

            action_aliases = {
                "pan_centre": "pan_center",
                "center": "pan_center",
                "centre": "pan_center",
                "pan_centered": "pan_center",
                "zoom": "zoom_in",
                "zoom_inward": "zoom_in",
                "pan_center_and_zoom_out": "pan_center_zoom_out",
                "pan_centre_and_zoom_out": "pan_center_zoom_out",
                "center_and_zoom_out": "pan_center_zoom_out",
                "centre_and_zoom_out": "pan_center_zoom_out",
            }
            sequence = [action_aliases.get(action, action) for action in sequence]
            phrase_action_aliases = {
                "pan_leftward": "pan_left", "move_camera_left": "pan_left",
                "leftward_pan": "pan_left", "pan_rightward": "pan_right",
                "move_camera_right": "pan_right", "rightward_pan": "pan_right",
                "progressive_zoom": "zoom_in", "camera_push_in": "zoom_in",
            }
            sequence = [phrase_action_aliases.get(action, action) for action in sequence]

            invalid_actions = [
                action for action in sequence
                if action not in SUPPORTED_KEYFRAME_ACTIONS
            ]
            if invalid_actions:
                print(
                    f"⚠️ [KEYFRAMES] Entry {scene_index + 1} contains unsupported "
                    f"action(s) {invalid_actions}. Keeping the image static rather than "
                    "inventing camera behavior."
                )
                return {
                    "static": True,
                    "enabled": False,
                    "id": variation_key or "static_invalid_sequence",
                    "label": "STATIC — invalid keyframe sequence",
                    "group": raw.get("group"),
                    "end_position": "centre",
                    "sequence": [],
                    "zoom_mode": "hold",
                }

            if len(sequence) > 3:
                print(
                    f"⚠️ [KEYFRAMES] Entry {scene_index + 1} supplied "
                    f"{len(sequence)} actions; enforcing the three-action maximum."
                )
                sequence = sequence[:3]

            raw_zoom_mode = _normalise_metadata_token(
                raw.get("zoom_mode")
                or raw.get("zoom_keyword")
                or (template.get("zoom_mode") if template else "hold")
            )
            zoom_mode_aliases = {
                "no_zoom": "hold",
                "maintain_zoom": "hold",
                "gradual_zoom": "zoom_only",
                "concurrent": "concurrent_in",
                "simultaneous_zoom_in": "concurrent_in",
                "soft_concurrent_in": "concurrent_in_soft",
                "soft_concurrent_zoom": "concurrent_in_soft",
                "gentle_concurrent_zoom": "concurrent_in_soft",
                "zoom_in_out": "in_out",
                "zoom_in_and_out": "in_out",
                "sequential_zoom_reset": "sequential_reset",
            }
            zoom_mode = zoom_mode_aliases.get(raw_zoom_mode, raw_zoom_mode)
            if zoom_mode not in SUPPORTED_ZOOM_MODES:
                print(
                    f"⚠️ [KEYFRAMES] Entry {scene_index + 1} has unsupported zoom mode "
                    f"'{raw_zoom_mode}'. Using the variation's supported default."
                )
                zoom_mode = (
                    template.get("zoom_mode", "hold")
                    if template and template.get("zoom_mode") in SUPPORTED_ZOOM_MODES
                    else "hold"
                )

            # If a legacy four-action reset variation is truncated, its reset action
            # may no longer be present. Keep the remaining three actions sequential.
            if (
                variation_key == "zoom_pan_left_right_center_reset"
                and len(sequence) == 3
                and "pan_center_zoom_out" not in sequence
                and zoom_mode == "sequential_reset"
            ):
                zoom_mode = "sequential"

            raw_end_position = _normalise_metadata_token(
                raw.get("end_position") or raw.get("final_position") or ""
            )
            end_position_aliases = {
                "center": "centre",
                "centre": "centre",
                "left": "left",
                "right": "right",
            }
            end_position = end_position_aliases.get(raw_end_position)
            if end_position is None:
                end_position = "centre"
                for action in reversed(sequence):
                    if action == "pan_left":
                        end_position = "left"
                        break
                    if action == "pan_right":
                        end_position = "right"
                        break
                    if action in {"pan_center", "pan_center_zoom_out"}:
                        end_position = "centre"
                        break

            label = str(
                raw.get("label")
                or (template.get("label") if template else variation_key)
                or "AI-directed camera movement"
            )
            return {
                "static": False,
                "enabled": True,
                "id": variation_key or "explicit_custom_keyframes",
                "label": label,
                "group": raw.get("group"),
                "sequence": sequence,
                "zoom_mode": zoom_mode,
                "end_position": end_position,
                "keyframe_count": len(sequence),
                "reason": str(raw.get("reason") or "").strip(),
            }

        def _ease_in_out(value):
            value = max(0.0, min(1.0, float(value)))
            return value * value * (3.0 - 2.0 * value)

        def apply_image_motion(image, local_time, duration, motion_plan):
            """Render gentle, eased pan/zoom motion from a pre-assigned scene plan."""
            if not motion_plan or motion_plan.get("static"):
                return image.copy()

            width, height = image.size
            safe_duration = max(0.001, float(duration))
            progress = max(0.0, min(1.0, float(local_time) / safe_duration))
            sequence = motion_plan.get("sequence", [])
            if not sequence:
                return image.copy()

            # Small overscan keeps edge movement visible without aggressive crops.
            base_zoom = 1.035
            peak_zoom = min(1.078, 1.045 + max(0.0, safe_duration - 1.0) * 0.006)
            mode = motion_plan.get("zoom_mode", "hold")
            step_count = max(1, len(sequence))

            def pan_target(action):
                if action == "pan_left":
                    return 0.0
                if action == "pan_right":
                    return 1.0
                if action in ("pan_center", "pan_center_zoom_out"):
                    return 0.5
                return None

            # Pre-position at the opposite edge before the first pan begins. This
            # makes a left pan start on the right-hand content and vice versa.
            first_pan_target = next(
                (pan_target(action) for action in sequence if pan_target(action) is not None),
                0.5,
            )
            pan_position = (
                1.0 if first_pan_target == 0.0
                else 0.0 if first_pan_target == 1.0
                else 0.5
            )
            pan_segments = []
            current_pan = pan_position
            for action in sequence:
                target = pan_target(action)
                if target is None:
                    target = current_pan
                pan_segments.append((current_pan, target))
                current_pan = target

            scaled_progress = min(step_count, progress * step_count)
            step_index = min(step_count - 1, int(scaled_progress))
            step_progress = 1.0 if progress >= 1.0 else scaled_progress - step_index
            step_progress = _ease_in_out(step_progress)
            pan_start, pan_end = pan_segments[step_index]
            pan_fraction = pan_start + (pan_end - pan_start) * step_progress

            # Keep the last pan endpoint fully visible on the final frames so the
            # outgoing transition agrees with the direction of the scene movement.
            if (
                progress >= 0.985
                and pan_target(sequence[-1]) is not None
            ):
                pan_fraction = pan_segments[-1][1]

            eased_progress = _ease_in_out(progress)
            if mode == "hold":
                zoom = 1.045
            elif mode == "zoom_only":
                zoom = base_zoom + (peak_zoom - base_zoom) * eased_progress
            elif mode in ("concurrent_in", "concurrent_in_soft"):
                strength = 1.0 if mode == "concurrent_in" else 0.72
                zoom = base_zoom + ((peak_zoom - base_zoom) * strength * eased_progress)
            elif mode == "in_out":
                if progress <= 0.55:
                    zoom = base_zoom + (peak_zoom - base_zoom) * _ease_in_out(progress / 0.55)
                else:
                    zoom = peak_zoom - (peak_zoom - base_zoom) * _ease_in_out((progress - 0.55) / 0.45)
            elif mode in ("sequential", "sequential_reset"):
                current_action = sequence[step_index]
                previous_zoom_step = any(
                    action == "zoom_in" for action in sequence[:step_index]
                )
                if current_action == "zoom_in":
                    zoom = base_zoom + (peak_zoom - base_zoom) * step_progress
                elif current_action == "pan_center_zoom_out":
                    zoom = peak_zoom - (peak_zoom - base_zoom) * step_progress
                elif previous_zoom_step:
                    zoom = peak_zoom
                else:
                    zoom = base_zoom
            else:
                zoom = 1.045

            zoom = max(1.0, float(zoom))
            crop_width = max(2, min(width, int(round(width / zoom))))
            crop_height = max(2, min(height, int(round(height / zoom))))
            max_x = max(0, width - crop_width)
            max_y = max(0, height - crop_height)
            x = int(round(max_x * max(0.0, min(1.0, pan_fraction))))
            y = int(round(max_y * 0.5))
            x = max(0, min(x, width - crop_width))
            y = max(0, min(y, height - crop_height))
            cropped = image.crop((x, y, x + crop_width, y + crop_height))
            return cropped.resize((width, height), Image.Resampling.LANCZOS)

        count = min(len(entries), len(image_files))
        if len(entries) != len(image_files):
            print(f"⚠️ Entry/image count differs: {len(entries)} entries, {len(image_files)} images; processing {count} pairs")
        prepared = []
        for index in range(count):
            entry = entries[index]
            image_info = image_files[index]
            duration = max(0.1, float(entry.get("duration_seconds", 5.0)))
            try:
                with Image.open(image_info["path"]) as source:
                    base_image = fit_image(source, video_width, video_height)
                source_dialogue = entry.get("source_dialogue") or entry.get("dialogue", "")
                prepared.append({
                    "number": image_info["number"],
                    "image": base_image,
                    "duration": duration,
                    "caption": entry.get("dialogue", ""),
                    "source_dialogue": source_dialogue,
                    "stage_overlay_specs": extract_stage_overlay_specs(entry),
                    "script_start_seconds": entry.get("start_seconds"),
                    "script_stop_seconds": entry.get("stop_seconds"),
                    "filename": image_info["filename"],
                    # The storyboard's per-entry editing metadata is authoritative.
                    "transition_plan": build_transition_plan(entry),
                    "motion_plan": build_scene_motion_plan(entry, source_dialogue, index),
                })
                print(f"🎬 [{index + 1}/{count}] {image_info['filename']} — {duration:.1f}s")
            except Exception as exc:
                print(f"⚠️ Skipping unreadable image {image_info['path']}: {exc}")
        if not prepared:
            print("❌ No images could be processed")
            return None
        audio_duration = None
        audio_probe = None
        if audio_file_path:
            try:
                audio_probe = AudioFileClip(audio_file_path)
                audio_duration = float(audio_probe.duration)
                print(f"🎵 Audio duration: {audio_duration:.2f}s")
            except Exception as exc:
                print(f"⚠️ Could not read audio duration: {exc}")
            finally:
                if audio_probe is not None:
                    try:
                        audio_probe.close()
                    except Exception:
                        pass
        total_duration = sum(item["duration"] for item in prepared)
        if audio_duration and audio_duration > 0 and prepared:
            # Keep the final image visible through the exact end of the narration.
            # Earlier scenes keep their durations when they fit within the audio.
            previous_duration = sum(float(item["duration"]) for item in prepared[:-1])
            original_last_duration = max(0.1, float(prepared[-1]["duration"]))
            last_available = float(audio_duration) - previous_duration
            if last_available > 0:
                # Extend OR shorten only the final image so the video ends with audio.
                prepared[-1]["duration"] = last_available
                total_duration = float(audio_duration)
                change = last_available - original_last_duration
                if change > 0.01:
                    print(f"🔄 Extended final image by {change:.2f}s to reach audio end")
                elif change < -0.01:
                    print(f"✂️ Adjusted final image by {change:.2f}s so it ends with audio")
                else:
                    print("🎯 Final image timing already matches the audio end")
            else:
                # If all preceding scenes alone exceed the audio, preserve the final
                # image and proportionally fit the preceding scenes into the remaining
                # time rather than cutting off the final image entirely.
                last_duration = min(original_last_duration, max(0.1, float(audio_duration) * 0.15))
                available_for_previous = max(0.0, float(audio_duration) - last_duration)
                if previous_duration > 0 and available_for_previous > 0:
                    scale = available_for_previous / previous_duration
                    for item in prepared[:-1]:
                        item["duration"] = max(0.01, float(item["duration"]) * scale)
                elif available_for_previous <= 0:
                    prepared = prepared[-1:]
                    last_duration = float(audio_duration)
                prepared[-1]["duration"] = last_duration
                total_duration = sum(float(item["duration"]) for item in prepared)
                # Remove tiny floating-point discrepancies so the last frame lands
                # on the audio endpoint.
                if prepared:
                    prepared[-1]["duration"] = max(
                        0.01, float(audio_duration) - sum(float(item["duration"]) for item in prepared[:-1])
                    )
                    total_duration = float(audio_duration)
                print("⚠️ Scene timings exceeded the audio; fitted earlier scenes so the final image remains until audio ends")
        # Existing outputs are preserved. If the target project filename already
        # exists, it will be renamed to \\\\\\\\\\\\\\\<project>_old_N.mp4 before the new render
        # is written, where N is one greater than the highest existing old number.
        clips = []
        final_clip = None
        audio_clip = None
        output_filename = f"{normalized_project_title}.mp4"
        output_path = os.path.join(edited_folder, output_filename)
        try:
            if include_transitions:
                print(
                    "🎬 [TRANSITIONS] AI-directed mode enabled: each entry's "
                    "transition_to_next metadata controls its outgoing boundary"
                )
            else:
                print("⏭️ [TRANSITIONS] Globally disabled; all boundaries use direct cuts")
            if include_captions:
                print("📝 [CAPTIONS] Caption engine enabled for this project")
            else:
                print("⏭️ [CAPTIONS] Caption engine is OFF; stage overlays can still use ASR word timing")
            print("🖥️ [KEEP-AWAKE] Five-second Windows keep-awake heartbeat remains active through rendering")
            # Transition choices and durations are read from each entry's
            # transition_to_next metadata. Supported canonical IDs and descriptive
            # keywords are normalized; no random transition selection occurs.
            clips = []
            # Each scene uses its full assigned duration. The next scene begins
            # exactly when the current scene's duration ends; no early time shift.
            visual_durations = [float(item["duration"]) for item in prepared]
            scene_start_offsets = []
            scene_cursor = 0.0
            for scene_duration in visual_durations:
                scene_start_offsets.append(scene_cursor)
                scene_cursor += max(0.001, float(scene_duration))
            # Subscribe stickers are driven by the scene's source dialogue, not by
            # ASR, so they remain available whether captions are ON or OFF.
            subscribe_sticker_events = build_subscribe_sticker_events(prepared)
            sticker_only_plan = {"events": [], "sticker_events": subscribe_sticker_events}

            # Locate the Stage/Step/Level/Example words in the actual narration.
            # The event covers the complete phrase pronunciation and excludes those
            # same ASR tokens from bottom captions.
            suppressed_heading_word_indices = build_stage_overlay_events(
                prepared, scene_start_offsets, audio_words
            )
            if include_captions:
                _start_caption_progress()
                caption_stream_plan = build_caption_stream_plans(
                    prepared,
                    video_width,
                    audio_words,
                    subscribe_sticker_events,
                    suppressed_word_indices=suppressed_heading_word_indices,
                )
            else:
                caption_stream_plan = None

            # Each prepared entry already contains the AI director's explicit
            # keyframe plan. Execute its supported variation, action sequence, and
            # zoom mode. Stage/Step/Level/Example metadata never disables camera motion.
            for scene_index, item in enumerate(prepared):
                base_image = item["image"]
                duration = float(visual_durations[scene_index])
                caption_plan = caption_stream_plan if include_captions else None
                global_scene_start = (
                    caption_stream_plan["scene_starts"][scene_index]
                    if include_captions and caption_stream_plan
                    else scene_start_offsets[scene_index]
                )
                motion_plan = item.get("motion_plan") or {"static": True}
                previous_image = prepared[scene_index - 1]["image"] if scene_index > 0 else None
                previous_motion_plan = (
                    prepared[scene_index - 1].get("motion_plan") if scene_index > 0 else None
                )
                previous_duration = (
                    float(visual_durations[scene_index - 1]) if scene_index > 0 else 0.0
                )
                # A boundary is controlled by the PREVIOUS entry's
                # transition_to_next object. This is intentionally not inferred
                # from camera direction or selected automatically.
                previous_transition_plan = (
                    prepared[scene_index - 1].get("transition_plan")
                    if scene_index > 0 else None
                )
                transition_type = (
                    previous_transition_plan.get("type", "none")
                    if previous_transition_plan and previous_transition_plan.get("apply")
                    and include_transitions
                    else "none"
                )
                requested_transition_duration = (
                    float(previous_transition_plan.get("duration_seconds", 0.0))
                    if transition_type != "none" and previous_transition_plan
                    else 0.0
                )
                active_transition = (
                    min(
                        requested_transition_duration,
                        duration * 0.28,
                        previous_duration * 0.28,
                    )
                    if transition_type != "none" and previous_image is not None
                    else 0.0
                )
                if transition_type != "none" and active_transition <= 0:
                    transition_type = "none"
                def make_frame(
                    t,
                    base=base_image,
                    clip_duration=duration,
                    previous=previous_image,
                    previous_plan=previous_motion_plan,
                    previous_clip_duration=previous_duration,
                    effect=transition_type,
                    trans_duration=active_transition,
                    scene_motion_plan=motion_plan,
                    stream_plan=caption_plan,
                    sticker_plan=sticker_only_plan,
                    absolute_scene_start=global_scene_start,
                    title_overlay_events=item.get("stage_overlay_events", []),
                ):
                    t = max(0.0, float(t))
                    animated_current = apply_image_motion(
                        base, t, clip_duration, scene_motion_plan
                    )
                    current = animated_current.copy()
                    # Start the transition from the previous scene's actual final
                    # camera position, rather than its unanimated source image.
                    if effect != "none" and previous is not None and trans_duration > 0 and t < trans_duration:
                        progress = min(1.0, max(0.0, t / trans_duration))
                        old = apply_image_motion(
                            previous, previous_clip_duration, previous_clip_duration, previous_plan
                        )
                        w, h = current.size
                        if effect == "crossfade":
                            current = Image.blend(old, current, progress)
                        elif effect in ("wipe_left", "wipe_right"):
                            current = old.copy()
                            reveal = int(w * progress)
                            if effect == "wipe_left":
                                if reveal > 0:
                                    current.paste(animated_current.crop((0, 0, reveal, h)), (0, 0))
                            else:
                                if reveal > 0:
                                    current.paste(animated_current.crop((w - reveal, 0, w, h)), (w - reveal, 0))
                        else:  # slide_left / slide_right
                            current = Image.new("RGB", (w, h), (0, 0, 0))
                            offset = int(w * progress)
                            if effect == "slide_left":
                                current.paste(old.crop((offset, 0, w, h)), (0, 0))
                                current.paste(animated_current.crop((0, 0, offset, h)), (w - offset, 0))
                            else:
                                current.paste(old.crop((0, 0, w - offset, h)), (offset, 0))
                                current.paste(animated_current.crop((w - offset, 0, w, h)), (0, 0))

                    # Captions are optional; subscribe stickers are not. The sticker
                    # overlay is always fixed at the centre and is never keyframed.
                    if include_captions and stream_plan:
                        rendered = draw_animated_caption(
                            current, absolute_scene_start + t, clip_duration, stream_plan
                        )
                    elif sticker_plan and sticker_plan.get("sticker_events"):
                        rendered = draw_animated_caption(
                            current, absolute_scene_start + t, clip_duration, sticker_plan
                        )
                    else:
                        rendered = current

                    # The heading is the top-most visual layer. During its spoken
                    # interval it fully covers the scene, captions, and stickers;
                    # immediately afterward the current animated scene is visible.
                    rendered = draw_stage_title_overlay(
                        rendered,
                        absolute_scene_start + t,
                        title_overlay_events,
                    )
                    return np.asarray(rendered, dtype=np.uint8)
                clip = VideoClip(frame_function=make_frame, duration=duration)
                clips.append(clip)
                print(
                    f"🎞️ Clip {scene_index + 1}/{len(prepared)} ready: "
                    f"{item.get('filename', 'entry')} | {duration:.2f}s | "
                    f"keyframe={motion_plan.get('label', 'static')} | "
                    f"group={motion_plan.get('group', 'STATIC')} | "
                    f"transition={transition_type if include_transitions else 'OFF'} | "
                    f"captions={'ON' if include_captions else 'OFF'} | "
                    f"spoken_heading_overlays={len(item.get('stage_overlay_events', []))}"
                )
            final_clip = concatenate_videoclips(clips, method="chain")
            if audio_file_path and os.path.exists(audio_file_path):
                audio_clip = AudioFileClip(audio_file_path)
                if audio_duration and audio_duration > total_duration:
                    try:
                        audio_clip = audio_clip.subclipped(0, total_duration)
                    except AttributeError:
                        audio_clip = audio_clip.subclip(0, total_duration)
                elif audio_duration and audio_duration < total_duration:
                    try:
                        final_clip = final_clip.subclipped(0, audio_duration)
                    except AttributeError:
                        final_clip = final_clip.subclip(0, audio_duration)
                    total_duration = audio_duration
                if hasattr(final_clip, "with_audio"):
                    final_clip = final_clip.with_audio(audio_clip)
                else:
                    final_clip = final_clip.set_audio(audio_clip)
            # Preserve the previous project output instead of deleting it.
            # Continue numbering after the highest existing \\\\\\\\\\\\\\\<project>_old_N.mp4.
            if os.path.isfile(output_path):
                old_pattern = re.compile(
                    rf"^{re.escape(normalized_project_title)}_old_(\d+).mp4$",
                    re.IGNORECASE,
                )
                existing_numbers = []
                for existing_name in os.listdir(edited_folder):
                    match = old_pattern.match(existing_name)
                    if match:
                        existing_numbers.append(int(match.group(1)))
                next_old_number = max(existing_numbers, default=0) + 1
                backup_filename = f"{normalized_project_title}_old_{next_old_number}.mp4"
                backup_path = os.path.join(edited_folder, backup_filename)
                while os.path.exists(backup_path):
                    next_old_number += 1
                    backup_filename = f"{normalized_project_title}_old_{next_old_number}.mp4"
                    backup_path = os.path.join(edited_folder, backup_filename)
                os.replace(output_path, backup_path)
                print(f"📦 Preserved previous output as: {backup_path}")
            print(f"   Duration: {total_duration:.2f}s | FPS: 24 | Size: {video_width}x{video_height}")
            print("📊 Rendering progress will be shown in this console. No extra window will open.")
            render_started = time.monotonic()
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="320k",
                preset="slow",
                ffmpeg_params=[
                    "-crf", "16",
                    "-pix_fmt", "yuv420p",
                    "-profile:v", "high",
                    "-level", "4.1",
                    "-movflags", "+faststart",
                    "-color_primaries", "bt709",
                    "-color_trc", "bt709",
                    "-colorspace", "bt709",
                ],
                threads=max(2, min(8, os.cpu_count() or 2)),
                logger="bar",
            )
            elapsed_minutes = (time.monotonic() - render_started) / 60.0
            print(f"⏱️ Render elapsed time: {elapsed_minutes:.2f} minutes")
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise RuntimeError("FFmpeg finished without creating a valid output file")
            print(f"✅ Video saved: {output_path}")
            print(f"📊 Size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")
        except Exception as exc:
            print(f"❌ Video assembly failed: {exc}")
            traceback.print_exc()
            return None
        finally:
            seen = set()
            for resource in [final_clip, audio_clip, *clips]:
                if resource is None or id(resource) in seen:
                    continue
                seen.add(id(resource))
                try:
                    resource.close()
                except Exception:
                    pass
        # Clean temporary folder left by older versions, if present.
        try:
            if os.path.isdir(temp_folder):
                shutil.rmtree(temp_folder)
        except Exception as exc:
            print(f"⚠️ Could not clean temporary folder: {exc}")
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"   Project: {project_title}")
        print(f"   Entries found: {len(entries)}")
        print(f"   Images processed: {len(prepared)}")
        print(f"   Final duration: {total_duration:.2f}s")
        planned_transition_count = sum(
            1
            for scene_item in prepared[:-1]
            if scene_item.get("transition_plan", {}).get("apply")
        )
        dynamic_keyframe_count = sum(
            1
            for scene_item in prepared
            if scene_item.get("motion_plan")
            and not scene_item["motion_plan"].get("static")
        )
        print(
            f"   AI-directed transitions: {planned_transition_count} boundary/boundaries "
            + ("enabled by entry metadata" if include_transitions else "(master switch OFF)")
        )
        print(f"   AI-directed camera-motion scenes: {dynamic_keyframe_count}/{len(prepared)}")
        stage_overlay_count = sum(len(item.get("stage_overlay_events", [])) for item in prepared)
        print(f"   Spoken Stage/Step/Level/Example overlays: {stage_overlay_count}")
        print("   Subscribe sticker size: 50% of the previous producer version")
        print(
            "   Captions: "
            + ("✅ Animated typewriter reveal" if include_captions else "⏭️ Disabled")
        )
        print(f"   Audio: {'✅ Added' if audio_file_path else '❌ None'}")
        if audio_file_path:
            print(f"   Audio file: {os.path.basename(audio_file_path)}")
        print(f"   Output: {output_path}")
        print(f"   Thumbnail: {thumbnail_path or '⚠️ Not found'}")
        print("=" * 60)
        print("✅ Complete!")
        completed_result = {
            "project_title": project_title,
            "entries_count": len(entries),
            "images_processed": len(prepared),
            "total_duration": total_duration,
            "audio_added": bool(audio_file_path),
            "audio_file": os.path.basename(audio_file_path) if audio_file_path else None,
            "output_folder": edited_folder,
            "output_file": output_filename,
            "output_path": output_path,
            "thumbnail_path": thumbnail_path,
            "include_transitions": include_transitions,
            "dynamic_transitions_planned": planned_transition_count,
            "dynamic_keyframe_scenes": dynamic_keyframe_count,
            "include_captions": include_captions,
            "caption_animation": "typewriter_pop" if include_captions else None,
            "stage_overlay_count": sum(len(item.get("stage_overlay_events", [])) for item in prepared),
            "stage_overlay_mode": "ASR-word-synchronized-full-screen" if has_overlay_metadata else None,
            "subscribe_sticker_scale": 0.5,
        }
        # Continue through READY_SCRIPT in the same invocation. The next call
        # re-scans the queue, skips this newly-created output, and selects the next
        # unfinished project. Return the current result if no further project is
        # eligible; otherwise return the last successful project's result.
        # Release any cached sticker frames before the next queued project starts.
        if include_captions:
            try:
                _load_subscribe_sticker_animation.cache_clear()
            except Exception:
                pass
        print("🔎 [READY-SCRIPT] Looking for the next unfinished project...")
        next_result = _run_video_producer()
        return next_result if isinstance(next_result, dict) else completed_result

    try:
        return _run_video_producer()
    finally:
        _awake_stop.set()
        _awake_thread.join(timeout=2.0)
        if _awake_thread.is_alive():
            print("⚠️ [KEEP-AWAKE] Worker did not stop within 2 seconds; it will exit as a daemon thread")
        else:
            print("🖥️ [KEEP-AWAKE] Windows awake protection released after video producer finished")

def main():
    fetch_settings()
    distribute_characters()
    generate_gemini_images()
    sceneiq_google_flow_images_generation_engine()
    video_producer()
  
if __name__ == "__main__":
    print("🚀 Starting Google Flow image generation...", flush=True)

    try:
        sceneiq_google_flow_images_generation_engine()
        #video_producer()
    except Exception as e:
        import traceback
        print(f"❌ FATAL ERROR: {e}", flush=True)
        traceback.print_exc()

   

   

         
