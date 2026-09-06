import pyautogui
import pytesseract
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
from moviepy import ImageClip
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
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata"
tessdata_path = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata\eng.traineddata"
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCREEN_IMAGE = r"C:\xampp\htdocs\AI automation\scenIQ\input_images\screen.png"
TEXT_TARGET = r"C:\xampp\htdocs\AI automation\scenIQ\text_target.json"
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
SCREEN_TEXT_CONTENT = r"C:\xampp\htdocs\AI automation\scenIQ\screen_content.json"
INPUT_IMAGES = r"C:\xampp\htdocs\AI automation\scenIQ\input_images"
IMAGES_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\project"
PHPSQLURL = "https://fhdrikxsirudr.fwh.is/phpmyadmintemplate.php"
IMAGE_GENERATION_URL = "https://gemini.google.com/app"
GUI_IMAGES = r"C:\xampp\htdocs\AI automation\scenIQ\gui_images"
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
GUI_REGION_SAVER = r"C:\xampp\htdocs\AI automation\scenIQ\gui.json"

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
    """
    pyautogui.PAUSE = 0.0
    
    # Define termination flag
    terminate_automation = False
    
    # Define MAX_RETRIES for operations
    MAX_OPERATION_RETRIES = 5
    
    def check_for_termination():
        if terminate_automation:
            raise KeyboardInterrupt("User forced exit via shortcut key.")
    
    # Helper functions
    def ensure_panel_path_exists():
        """Create default PANEL_PATH file if it doesn't exist or is invalid."""
        if os.path.exists(PANEL_PATH):
            try:
                with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    if not content:
                        return False
                    json.loads(content)
                return True
            except Exception as e:
                try:
                    os.remove(PANEL_PATH)
                except:
                    pass
        else:
            pass
        
        default_config = {
            "url": PHPSQLURL,
            "author": "Brilliance",
            "engine": "csv",
            "page": "none",
            "group": "include",
            "processjpgfrom": "freshjpgs"
        }
        
        try:
            os.makedirs(os.path.dirname(PANEL_PATH), exist_ok=True)
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(default_config, file, indent=2, ensure_ascii=False, separators=(',', ': '))
            return True
        except Exception as e:
            return False
    
    def clean_and_repair_json(content):
        """Clean and repair JSON data from the database."""
        try:
            # First, try to parse as-is
            return json.loads(content)
        except:
            pass
        
        try:
            # Try to clean the content
            cleaned = content.strip()
            
            # Remove outer quotes if present (stringified JSON)
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
                # Unescape the content
                cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            
            # Try to parse the cleaned content
            try:
                return json.loads(cleaned)
            except:
                pass
            
            # If it's a list with a single item that's a stringified JSON
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
                    inner = parsed[0]
                    if inner.startswith('{') or inner.startswith('['):
                        return json.loads(inner)
            except:
                pass
            
            # Manual cleaning - remove escape characters and fix common issues
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            cleaned = cleaned.replace('\\n', ' ').replace('\\r', ' ')
            cleaned = cleaned.replace('\\t', ' ')
            
            # Fix boolean values that are strings
            cleaned = cleaned.replace('"true"', 'true').replace('"false"', 'false')
            cleaned = cleaned.replace("'true'", 'true').replace("'false'", 'false')
            
            # Fix null values that are strings
            cleaned = cleaned.replace('"null"', 'null').replace("'null'", 'null')
            
            # Remove trailing commas
            import re
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            
            # Remove extra data after the JSON object/array
            # Find the first complete JSON object or array
            json_match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1)
            
            # Try parsing again
            try:
                return json.loads(cleaned)
            except:
                pass
            
            # If all fails, return empty dict
            return {}
            
        except Exception as e:
            print(f"⚠️ [CLEAN] Error cleaning JSON: {e}")
            return {}
    
    def clean_json_data(data):
        """Recursively clean JSON data - remove string wrappers from objects, arrays, and booleans."""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                cleaned[key] = clean_json_data(value)
            return cleaned
        elif isinstance(data, list):
            return [clean_json_data(item) for item in data]
        elif isinstance(data, str):
            # Check if string is actually a JSON object or array
            stripped = data.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                try:
                    parsed = json.loads(stripped)
                    return clean_json_data(parsed)
                except:
                    pass
            elif stripped.startswith('[') and stripped.endswith(']'):
                try:
                    parsed = json.loads(stripped)
                    return clean_json_data(parsed)
                except:
                    pass
            # Check for boolean strings
            elif stripped.lower() == 'true':
                return True
            elif stripped.lower() == 'false':
                return False
            elif stripped.lower() == 'null':
                return None
            # Return as string
            return data
        else:
            return data
    
    def remove_outer_array_wrapper(data):
        """Remove the outer array wrapper if it exists."""
        if isinstance(data, list):
            # If it's a list with one item, return that item
            if len(data) == 1:
                return data[0]
            # If it's a list with multiple items, keep it as a list
            return data
        return data
    
    def repair_json_file(file_path):
        """Read, clean, and repair the JSON file."""
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean the content
            cleaned_data = clean_and_repair_json(content)
            
            # Remove outer array wrapper
            cleaned_data = remove_outer_array_wrapper(cleaned_data)
            
            # Further clean the data (remove string wrappers from objects/arrays/booleans)
            final_data = clean_json_data(cleaned_data)
            
            # Save the cleaned data
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
        """Ensure Edge window exists and is maximized/focused"""
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
                except Exception as e:
                    try:
                        pyautogui.hotkey('alt', 'tab')
                        time.sleep(0.3)
                    except:
                        pass
                
                return hwnd
            except Exception as e:
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
                    except:
                        pass
                    return hwnd
                except Exception as e:
                    continue
        
        raise RuntimeError("Failed to get or launch Edge window")
    
    def enforce_window_focus(hwnd):
        """Enforce window focus and maximized state"""
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
                except Exception as e:
                    try:
                        pyautogui.hotkey('alt', 'tab')
                        time.sleep(0.3)
                    except:
                        pass
            
            try:
                placement = win32gui.GetWindowPlacement(hwnd)
                if placement[1] != win32con.SW_SHOWMAXIMIZED:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
            except Exception as e:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
                except:
                    pass
            
            return hwnd
        except Exception as e:
            return hwnd
    
    def ensure_window_ready_and_focused():
        """Get or create window and ensure it's ready"""
        check_for_termination()
        hwnd = ensure_edge_window_ready()
        return enforce_window_focus(hwnd)
    
    def fast_paste_url(hwnd, url, retry_count=0):
        """Fast paste URL with watchdog and retry"""
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
        except Exception as e:
            if retry_count < 3:
                time.sleep(0.5)
                hwnd = ensure_window_ready_and_focused()
                return fast_paste_url(hwnd, url, retry_count + 1)
            else:
                return False, hwnd
    
    def wait_for_clipboard_content(expected_contains=None, timeout=60, check_interval=0.5):
        """Wait for clipboard to contain expected content or have any content."""
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
            except Exception as e:
                pass
            
            time.sleep(check_interval)
        
        return None
    
    def wait_for_enter_confirmation(timeout=5, check_interval=0.3):
        """Wait for 'enter button activated' in clipboard."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            check_for_termination()
            try:
                current_content = pyperclip.paste()
                if current_content and "enter button activated" in current_content:
                    return True
            except Exception as e:
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
            except Exception as e:
                return False
        return False
    
    def wait_for_clipboard_data_with_retry(max_retries=15, retry_delay=1.0, min_content_length=10, hwnd=None):
        """Wait for clipboard content with retries."""
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
                            print(f"ℹ️ [CLIPBOARD] Enter confirmation received, waiting for actual data...")
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
                except:
                    pass
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        return None
    
    def clean_clipboard_data(raw_data):
        """Clean clipboard data to extract valid JSON."""
        try:
            # Remove any leading/trailing whitespace
            data = raw_data.strip()
            
            # If the data is a string with escaped JSON, unescape it
            if data.startswith('"') and data.endswith('"'):
                try:
                    # Try to parse as a JSON string
                    parsed = json.loads(data)
                    if isinstance(parsed, str):
                        data = parsed
                except:
                    # If it fails, just remove the outer quotes
                    data = data[1:-1]
                    # Unescape
                    data = data.replace('\\"', '"').replace('\\\\', '\\')
            
            # Try to find the first complete JSON object or array
            import re
            # Look for a JSON object or array
            json_match = re.search(r'(\{.*\}|\[.*\])', data, re.DOTALL)
            if json_match:
                data = json_match.group(1)
            
            # Remove any extra text after the JSON
            # Find the matching closing brace/bracket
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
                    if char == '{' or char == '[':
                        bracket_count += 1
                    elif char == '}' or char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i + 1
                            break
            
            if end_pos > 0:
                data = data[:end_pos]
            
            # Remove trailing commas
            data = re.sub(r',\s*}', '}', data)
            data = re.sub(r',\s*]', ']', data)
            
            # Fix boolean values
            data = data.replace('"true"', 'true').replace('"false"', 'false')
            data = data.replace("'true'", 'true').replace("'false'", 'false')
            
            # Fix null values
            data = data.replace('"null"', 'null').replace("'null'", 'null')
            
            return data
            
        except Exception as e:
            print(f"⚠️ [CLEAN] Error cleaning clipboard data: {e}")
            return raw_data
    
    def overwrite_file_with_content(file_path, content):
        try:
            # First, clean the data
            cleaned_content = clean_clipboard_data(content)
            
            # Try to parse and clean the data
            try:
                parsed_content = json.loads(cleaned_content)
                # Remove outer array wrapper
                parsed_content = remove_outer_array_wrapper(parsed_content)
                # Recursively clean the data
                parsed_content = clean_json_data(parsed_content)
                content = json.dumps(parsed_content, indent=2, ensure_ascii=False, separators=(',', ': '))
            except json.JSONDecodeError as e:
                print(f"⚠️ [PARSE] Initial parse failed: {e}, trying deeper cleaning...")
                # Try deeper cleaning
                try:
                    parsed_content = clean_and_repair_json(cleaned_content)
                    # Remove outer array wrapper
                    parsed_content = remove_outer_array_wrapper(parsed_content)
                    parsed_content = clean_json_data(parsed_content)
                    content = json.dumps(parsed_content, indent=2, ensure_ascii=False, separators=(',', ': '))
                except Exception as e2:
                    print(f"⚠️ [PARSE] Deep cleaning failed: {e2}")
                    # If all parsing fails, save as-is with the cleaned content
                    content = cleaned_content
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ [SAVE] Error saving file: {e}")
            return False
    
    def execute_sql_query_and_save(hwnd, sql_query, file_path, operation_description, retry_count=0):
        """Execute SQL query on current page and save results to file."""
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
                error_msg = f"SQL query '{sql_query}' executed but no data was returned or the clipboard was empty after {20} retry attempts."
                print(f"❌ {error_msg}")
                
                if retry_count < MAX_OPERATION_RETRIES - 1:
                    print(f"🔄 [RETRY] Operation failed, retrying in 2 seconds...")
                    time.sleep(2)
                    hwnd = enforce_window_focus(hwnd)
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, 
                        operation_description, retry_count + 1
                    )
                
                if backup_created and os.path.exists(file_path + ".backup"):
                    restore_from_backup(file_path)
                return False, error_msg
            
            print(f"✅ [STEP 9] Data received successfully: {len(final_result)} characters")
            
            print(f"💾 [STEP 10] Overwriting file {file_path} with data...")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Clean and repair the data before saving
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
                    print(f"🔄 [RETRY] File save failed, retrying in 2 seconds...")
                    time.sleep(2)
                    hwnd = enforce_window_focus(hwnd)
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, 
                        operation_description, retry_count + 1
                    )
                
                if backup_created and os.path.exists(file_path + ".backup"):
                    restore_from_backup(file_path)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Unexpected error during SQL execution: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            if retry_count < MAX_OPERATION_RETRIES - 1:
                print(f"🔄 [RETRY] Exception occurred, retrying in 2 seconds...")
                time.sleep(2)
                try:
                    hwnd = ensure_window_ready_and_focused()
                    return execute_sql_query_and_save(
                        hwnd, sql_query, file_path, 
                        operation_description, retry_count + 1
                    )
                except:
                    pass
            
            try:
                backup_path = file_path + ".backup"
                if os.path.exists(backup_path):
                    restore_from_backup(file_path)
            except:
                pass
            return False, error_msg
    
    # ============================================================
    # MAIN EXECUTION
    # ============================================================
    try:
        # Track errors and warnings with detailed messages
        errors_encountered = []
        warnings_encountered = []
        
        # Step 1: Validate config file
        if not ensure_panel_path_exists():
            error_msg = "The configuration file could not be created or validated. Please check file permissions and disk space."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        
        # Step 2: Load panel data (just to validate it's valid JSON)
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
        except json.JSONDecodeError as e:
            error_msg = f"The configuration file contains invalid JSON: {str(e)}. Please check the file format."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Failed to read the configuration file: {str(e)}. Check file permissions."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        
        # Step 3: Use PHPSQLURL directly
        phpmyadmin_url = PHPSQLURL
        print(f"🔍 [PHPMYADMIN] Using PHPSQLURL: {phpmyadmin_url}")
        
        # Step 4: Get or create Edge window
        try:
            hwnd = ensure_window_ready_and_focused()
        except Exception as e:
            error_msg = f"Failed to launch or focus Microsoft Edge: {str(e)}. Check if Edge is installed and accessible."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        
        # Step 5: Navigate to phpMyAdmin URL
        success, hwnd = fast_paste_url(hwnd, phpmyadmin_url)
        if not success:
            error_msg = f"Failed to navigate to '{phpmyadmin_url}'. The browser may have issues loading the page."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        
        # Step 6: Wait for page to load
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
            error_msg = f"The phpMyAdmin page at '{phpmyadmin_url}' failed to load after {MAX_OPERATION_RETRIES} attempts. Check if the URL is accessible and the server is running."
            print(f"❌ {error_msg}")
            errors_encountered.append(error_msg)
            return False
        
        print("✅ [NAVIGATION] Page is ready")
        hwnd = enforce_window_focus(hwnd)
        
        # ============================================================
        # OPERATION: Get settings from sceneiq_config
        # ============================================================
        sql_query = "select settings from sceneiq_config"
        success, error_msg = execute_sql_query_and_save(
            hwnd, sql_query, PANEL_PATH,
            "Fetching settings from sceneiq_config"
        )
        
        if not success:
            if error_msg:
                errors_encountered.append(error_msg)
            else:
                error_msg = "The SQL query 'select settings from sceneiq_config' executed but failed to return valid data. Check if the 'sceneiq_config' table exists and contains data."
                errors_encountered.append(error_msg)
            return False
        
        print("✅ [OPERATION] Settings fetched and saved successfully")
        
        # Step 7: Repair the JSON file (additional pass)
        print("🔄 [REPAIR] Running final JSON repair...")
        repair_success, repaired_data = repair_json_file(PANEL_PATH)
        if repair_success:
            print("✅ [REPAIR] JSON file successfully repaired")
        else:
            print("⚠️ [REPAIR] Could not repair JSON file, but data was saved")
            warnings_encountered.append("JSON data may not be fully valid")
        
        # ============================================================
        # OPERATION COMPLETE - Window remains open
        # ============================================================
        print(f"{'='*60}")
        print("✅ [PHPMYADMIN] OPERATION COMPLETED!")
        print(f"ℹ️ Browser window remains open for your use.")
        
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
        except:
            pass
        return False
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ [PHPMYADMIN] {error_msg}")
        import traceback
        traceback.print_exc()
        
        try:
            backup_path = PANEL_PATH + ".backup"
            if os.path.exists(backup_path):
                restore_from_backup(PANEL_PATH)
        except:
            pass
        return False

def distribute_characters():
    """
    Distributes character visual prompts from characters_visual_prompts to each entry
    based on the view_focus_characters field.
    
    For each entry, it extracts character names from view_focus_characters,
    normalizes them (removes special characters, handles "and" separator),
    looks up each character in characters_visual_prompts, and adds them
    as new fields in the entry.
    """
    # Load panel.json
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)
    except json.JSONDecodeError as e:
        print(f"❌ Error: panel.json is not valid JSON: {e}")
        return
    except Exception as e:
        print(f"❌ Error reading panel.json: {e}")
        return

    # Get characters_visual_prompts - FIXED: Correct path to the data
    # The characters_visual_prompts is inside project_name.script_json
    script_json = panel_data.get('project_name', {}).get('script_json', {})
    characters_visual_prompts = script_json.get('characters_visual_prompts', {})
    
    if not characters_visual_prompts:
        print("⚠️ No characters_visual_prompts found in panel.json")
        print("   Tried path: project_name.script_json.characters_visual_prompts")
        return

    # Get script entries - FIXED: Use the correct path
    script_data = script_json.get('script', {})
    
    if not script_data:
        print("⚠️ No script data found in panel.json")
        return

    print(f"📊 [DISTRIBUTE] Found {len(characters_visual_prompts)} characters in lookup")

    # Create a normalized lookup dictionary for characters
    def normalize_name(name):
        """Normalize character name for lookup."""
        if not name:
            return ""
        # Remove extra whitespace
        name = ' '.join(name.split())
        # Convert to lowercase for case-insensitive matching
        return name.lower().strip()

    # Build character lookup dictionary with normalized keys
    character_lookup = {}
    for char_name, char_data in characters_visual_prompts.items():
        normalized = normalize_name(char_name)
        if normalized:
            character_lookup[normalized] = {
                'original_name': char_name,
                'data': char_data
            }
    
    print(f"📊 [DISTRIBUTE] Character lookup built with {len(character_lookup)} entries")

    # Track statistics
    entries_processed = 0
    total_characters_added = 0
    batches_processed = 0
    
    # Function to extract character names from view_focus_characters
    def extract_character_names(view_focus_string):
        """Extract character names from view_focus_string."""
        if not view_focus_string:
            return []
        
        # Handle " and " as a separator
        normalized = view_focus_string.replace(' and ', ', ')
        normalized = normalized.replace(' and', ',')
        normalized = normalized.replace('and ', ',')
        
        # Split by comma and clean up
        raw_names = [name.strip() for name in normalized.split(',') if name.strip()]
        
        return raw_names

    # Process each batch
    for batch_key, batch_data in script_data.items():
        if not isinstance(batch_data, dict):
            continue
            
        entries = batch_data.get('entries', [])
        if not entries:
            continue
        
        batches_processed += 1
        print(f"\n📁 [DISTRIBUTE] Processing batch: {batch_key} ({len(entries)} entries)")
        
        for entry_idx, entry in enumerate(entries):
            # Skip if no view_focus_characters
            view_focus = entry.get('view_focus_characters', '')
            if not view_focus:
                print(f"  ⏭️ Entry {entry_idx + 1}: No view_focus_characters, skipping")
                continue
            
            # Extract character names from view_focus
            raw_names = extract_character_names(view_focus)
            
            if not raw_names:
                print(f"  ⏭️ Entry {entry_idx + 1}: No names extracted from '{view_focus}'")
                continue
            
            print(f"  📝 Entry {entry_idx + 1}: Extracted names: {raw_names}")
            
            # Process each character
            characters_added = 0
            for raw_name in raw_names:
                # Try to find the character in the lookup
                normalized_raw = normalize_name(raw_name)
                
                # Try exact match
                matched_char = None
                if normalized_raw in character_lookup:
                    matched_char = character_lookup[normalized_raw]
                else:
                    # Try partial match (in case of slight variations)
                    for lookup_key, lookup_data in character_lookup.items():
                        # Check if either contains the other
                        if normalized_raw in lookup_key or lookup_key in normalized_raw:
                            matched_char = lookup_data
                            print(f"    🔍 Partial match: '{raw_name}' -> '{lookup_key}'")
                            break
                
                if matched_char:
                    char_name = matched_char['original_name']
                    char_data = matched_char['data']
                    
                    # Add character data to entry as a nested object
                    entry[char_name] = char_data
                    characters_added += 1
                    total_characters_added += 1
                    print(f"    ✅ Added character: {char_name}")
                else:
                    print(f"    ⚠️ Character not found in lookup: '{raw_name}'")
                    print(f"       Available characters: {list(character_lookup.keys())}")
            
            if characters_added > 0:
                entries_processed += 1
                print(f"  ✅ Entry {entry_idx + 1}: Added {characters_added} characters")

    print(f"\n{'='*50}")
    print(f"📊 [DISTRIBUTE] Summary:")
    print(f"   - Batches processed: {batches_processed}")
    print(f"   - Entries with characters distributed: {entries_processed}")
    print(f"   - Total character references added: {total_characters_added}")
    print(f"{'='*50}")

    # Save updated panel.json
    try:
        with open(PANEL_PATH, 'w', encoding='utf-8') as file:
            json.dump(panel_data, file, indent=4, ensure_ascii=False)
        print(f"✅ [DISTRIBUTE] Successfully updated panel.json")
    except Exception as e:
        print(f"❌ Error saving panel.json: {e}")
        import traceback
        traceback.print_exc()
        return

    return entries_processed, total_characters_added

def generate_gemini_images():
    """
    Generates images using Gemini via GUI automation with pyautogui image recognition.
    Features: 
    - Uses IMAGE_GENERATION_URL and GUI_IMAGES path variable
    - Checks panel.json for image_generation_engine == "Gemini" (case-insensitive)
    - If engine is not Gemini, function exits immediately
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
    # --- SPEED TUNING PARAMETERS ---
    pyautogui.PAUSE = 0.0
    
    # --- CHECK ENGINE CONFIGURATION FIRST ---
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)
        
        # Check engines configuration
        engines = panel_data.get('engines', {})
        image_generation_engine = engines.get('image_generation_engine', '').strip()
        
        # Case-insensitive check for "Gemini"
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

    # Load configuration
    project_title = panel_data.get('project_name', {}).get('project_title', 'workproject1')
    
    # Get script entries
    script_json = panel_data.get('project_name', {}).get('script_json', {})
    script_data = script_json.get('script', {})
    
    # Flatten all entries from all batches
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
        return
    
    terminate_automation = False
    operation_status_flag = True
    operation_status_message = ""
    operation_aborted = False

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        """Update the operation status in panel.json"""
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
            
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(current_panel, file, indent=4, ensure_ascii=False)
            
            if is_abort:
                print(f"🛑 [STATUS] Operation aborted: {message}")
                raise SystemExit(f"Operation aborted: {message}")
                
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        """Abort the operation with a specific reason."""
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting Gemini image generation: {reason}", is_abort=True)

    def check_operation_status():
        """Check if operation status is still valid."""
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting Gemini operation", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
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
        """
        Get all available variants of an image file.
        For example, for 'ask_gemini.png', it will find:
        - ask_gemini.png (original)
        - ask_gemini1.png, ask_gemini2.png, ask_gemini3.png, etc.
        
        Returns a list of full paths in order: original first, then numbered variants.
        """
        variants = []
        base_name_without_ext = os.path.splitext(base_name)[0]
        ext = os.path.splitext(base_name)[1]
        
        # First, check if the original file exists
        original_path = os.path.join(GUI_IMAGES, base_name)
        if os.path.exists(original_path):
            variants.append(original_path)
        
        # Then, look for numbered variants
        # Pattern: base_name{number}.ext (e.g., ask_gemini1.png)
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
            
            # Sort by number and add to variants
            numbered_variants.sort(key=lambda x: x[0])
            for _, full_path in numbered_variants:
                variants.append(full_path)
                
        except Exception as e:
            print(f"⚠️ [FALLBACK] Error scanning for variants of {base_name}: {e}")
        
        return variants

    def find_image_with_fallback(image_name, confidence=0.8, region=None):
        """
        Find an image on screen, trying all available variants (numbered fallbacks).
        Returns the location (x, y) if found, None otherwise.
        Also returns the path of the matched image for logging purposes.
        """
        variants = get_image_variants(image_name)
        
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        
        print(f"🔍 [FALLBACK] Searching for {image_name} with {len(variants)} variant(s)...")
        
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateCenterOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False
                )
                if location:
                    print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                    return location, variant_path
            except Exception as e:
                # Suppress the verbose error output to avoid log spam
                pass
        
        return None, None

    def wait_for_image_with_fallback(image_name, timeout_seconds=60, confidence=0.8, region=None):
        """
        Wait for an image to appear on screen, trying all available variants (numbered fallbacks).
        Returns the location (x, y) if found, None otherwise.
        Also returns the path of the matched image for logging purposes.
        """
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
                        grayscale=False
                    )
                    if location:
                        print(f"✅ [FALLBACK] Found {variant_name} at ({location.x}, {location.y})")
                        return location, variant_path
                except Exception as e:
                    # Suppress the verbose error output
                    pass
            
            # Print status every 5 seconds
            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(f"⏳ [FALLBACK] Still waiting for {image_name}... ({elapsed}s elapsed)")
                last_status_time = current_time
            
            time.sleep(0.3)
        
        print(f"❌ [FALLBACK] {image_name} not found in any variant within {timeout_seconds} seconds")
        return None, None

    def find_image_location_with_fallback(image_name, confidence=0.8, region=None):
        """
        Find an image on screen using fallback variants, returning the full bounding box.
        Returns the location object if found, None otherwise.
        Also returns the path of the matched image.
        """
        variants = get_image_variants(image_name)
        
        if not variants:
            print(f"❌ [FALLBACK] No variants found for {image_name}")
            return None, None
        
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                location = pyautogui.locateOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False
                )
                if location:
                    print(f"✅ [FALLBACK] Found {variant_name} at ({location.left}, {location.top})")
                    return location, variant_path
            except Exception as e:
                # Suppress verbose error
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
        """Get Edge window on specified monitor"""
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
        """Ensure Edge window exists and is maximized/focused"""
        check_for_termination()
        
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        
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
                pass
        
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
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"⚠️ [FOCUS] Focus correction exception: {e}")
            return False

    def ensure_window_ready_and_focused():
        """Get or create window and ensure it's ready"""
        check_for_termination()
        hwnd = ensure_edge_window_ready()
        enforce_window_focus(hwnd)
        return hwnd

    def fast_paste_url(hwnd, url):
        check_for_termination()
        hud.print("📋 Navigating to URL...", "typing")
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.1)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status(f"Navigating to Gemini URL...")

    # --- IMAGE RECOGNITION HELPERS (UPDATED WITH FALLBACKS) ---
    def wait_for_image(image_name, timeout_seconds=60, confidence=0.8, region=None):
        """
        Wait for an image to appear on screen using fallback variants.
        Returns the location (x, y) if found, None otherwise.
        """
        location, _ = wait_for_image_with_fallback(image_name, timeout_seconds, confidence, region)
        return location

    def find_image(image_name, confidence=0.8, region=None):
        """
        Find an image on screen without waiting, using fallback variants.
        Returns the location (x, y) if found, None otherwise.
        """
        location, _ = find_image_with_fallback(image_name, confidence, region)
        return location

    def click_image_center(image_name, confidence=0.8, wait_time=0.3):
        """Find and click the center of an image using fallback variants."""
        location = find_image(image_name, confidence)
        if location:
            pyautogui.moveTo(location.x, location.y, duration=0.1)
            pyautogui.click()
            time.sleep(wait_time)
            return True
        return False

    def click_image_right(image_name, confidence=0.8, wait_time=0.3):
        """
        Find an image using fallback variants and click on its right side (not center).
        """
        variants = get_image_variants(image_name)
        
        if not variants:
            print(f"❌ [IMAGE] No variants found for {image_name}")
            return False
        
        for variant_path in variants:
            variant_name = os.path.basename(variant_path)
            try:
                # Get the bounding box of the image
                location = pyautogui.locateOnScreen(
                    variant_path,
                    confidence=confidence,
                    grayscale=False
                )
                if location:
                    # Click on the right side (75% of the width from the left)
                    click_x = location.left + int(location.width * 0.75)
                    click_y = location.top + int(location.height / 2)
                    print(f"✅ [IMAGE] Found {variant_name}, clicking right side at ({click_x}, {click_y})")
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    pyautogui.click()
                    time.sleep(wait_time)
                    return True
            except Exception as e:
                # Suppress verbose error
                pass
        
        print(f"❌ [IMAGE] {image_name} not found in any variant")
        return False

    def scroll_up_multiple(times=3):
        """
        Scroll up multiple times to make elements visible.
        """
        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        for i in range(times):
            pyautogui.moveTo(center_x, center_y, duration=0.05)
            pyautogui.scroll(-500)  # Stronger scroll
            time.sleep(0.3)
            print(f"⬆️ [SCROLL] Scrolled up ({i+1}/{times})")
        
        time.sleep(0.5)

    # --- DOWNLOAD MONITORING ---
    def check_and_rename_download(entry_name, images_folder, timeout_seconds=180, check_interval=0.3):
        """
        Monitor for new downloads and rename/move to the correct location.
        Fixed to detect downloads properly with better file detection.
        """
        print(f"📊 [DOWNLOAD] Monitoring for download for {entry_name}...")
        hud.print(f"📊 Monitoring download...", "waiting")
        update_operation_status(f"Waiting for download: {entry_name}")
        
        downloads_folder = os.path.expanduser("~/Downloads")
        
        if not os.path.exists(downloads_folder):
            print(f"❌ [DOWNLOAD] Downloads folder not found: {downloads_folder}")
            return False, None
        
        # Get initial file list with timestamps
        initial_files = {}
        try:
            with os.scandir(downloads_folder) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            stat = entry.stat()
                            initial_files[entry.name] = {
                                'path': entry.path,
                                'time': stat.st_mtime,
                                'size': stat.st_size
                            }
                        except Exception:
                            pass
            print(f"📁 [DOWNLOAD] Found {len(initial_files)} existing files before download")
        except Exception as e:
            print(f"⚠️ [DOWNLOAD] Error scanning existing files: {e}")
            initial_files = {}
        
        start_time = time.time()
        last_file_check = 0
        download_detected = False
        downloaded_file_path = None
        
        # Image extensions to look for
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
                                
                                # Check if this is a new file (not in initial list)
                                is_new_file = file_name not in initial_files
                                
                                # Also check if it's a recently modified file
                                is_recent = False
                                try:
                                    stat = entry.stat()
                                    file_mtime = stat.st_mtime
                                    if file_mtime > start_time - 10:  # Modified after monitoring started
                                        is_recent = True
                                except Exception:
                                    pass
                                
                                # If it's a new image file or a recent file, process it
                                if (is_new_file or is_recent) and file_ext in image_extensions:
                                    print(f"🆕 [DOWNLOAD] Found new/updated image file: {file_name}")
                                    print(f"   📁 Path: {entry.path}")
                                    print(f"   📏 Size: {stat.st_size} bytes")
                                    
                                    # Wait for file to stabilize
                                    stable_count = 0
                                    stable_size = 0
                                    max_stable_checks = 5
                                    
                                    while stable_count < 3 and stable_count < max_stable_checks:
                                        try:
                                            current_size = os.path.getsize(entry.path)
                                            if current_size == stable_size and current_size > 1024:  # At least 1KB
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
                                
                                # Also check for temporary download files
                                elif file_name.endswith('.crdownload') or file_name.endswith('.tmp'):
                                    print(f"⏳ [DOWNLOAD] Found temp download: {file_name}")
                                    try:
                                        stat = entry.stat()
                                        if stat.st_size > 0:
                                            print(f"   📏 Temp file size: {stat.st_size} bytes")
                                    except Exception:
                                        pass
                            
                            if download_detected:
                                break
                
                if download_detected and downloaded_file_path:
                    break
                
                # Print status every 10 seconds
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ [DOWNLOAD] Still waiting for download... ({elapsed}s elapsed)")
                    hud.print(f"⏳ Waiting... ({elapsed}s)", "waiting")
                    update_operation_status(f"Waiting for download {entry_name}... ({elapsed}s)")
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Error in monitoring loop: {e}")
                time.sleep(check_interval)
                continue
        
        if not download_detected or not downloaded_file_path:
            print(f"⏰ [DOWNLOAD] Timeout or no download detected after {timeout_seconds} seconds")
            
            # Final check: scan for any new image files
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
        
        # Process the downloaded file
        try:
            file_name = os.path.basename(downloaded_file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            new_filename = f"{entry_name}{file_ext}"
            
            # Target path in images folder
            target_path = os.path.join(images_folder, new_filename)
            
            # Ensure images folder exists
            if not os.path.exists(images_folder):
                os.makedirs(images_folder, exist_ok=True)
            
            # Ensure file exists and is readable
            if not os.path.exists(downloaded_file_path):
                print(f"❌ [DOWNLOAD] File no longer exists: {downloaded_file_path}")
                return False, None
            
            # Move and rename the file
            try:
                # Wait a bit more to ensure file is fully written
                time.sleep(0.5)
                os.rename(downloaded_file_path, target_path)
                print(f"✅ [DOWNLOAD] File renamed to: {new_filename}")
                print(f"📁 [DOWNLOAD] Moved to: {target_path}")
                hud.print(f"✅ Saved: {new_filename}", "success")
                update_operation_status(f"Downloaded and saved: {new_filename}")
                return True, target_path
            except Exception as e:
                print(f"⚠️ [DOWNLOAD] Error moving file: {e}")
                # Try copying instead
                import shutil
                try:
                    shutil.copy2(downloaded_file_path, target_path)
                    try:
                        os.remove(downloaded_file_path)
                    except:
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
        """
        Click more.png and download_gemini_image.png with retries.
        First checks for limit message before proceeding.
        Returns True if download was initiated, False otherwise.
        """
        print(f"🔄 [RETRY] Attempting to click more.png and download for {entry_name}...")
        
        for attempt in range(max_retries):
            check_for_termination()
            
            # FIRST: Check for limit message before proceeding
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [RETRY] Generation limit reached! Aborting.")
                hud.print("❌ Generation limit reached!", "error")
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                abort_operation(f"Generation limit reached for {entry_name}")
                return False
            
            # Scroll up to make more.png visible
            scroll_up_multiple(3)
            time.sleep(0.5)
            
            # Look for more.png with fallback
            more_location, more_path = find_image_with_fallback("more.png", confidence=0.8)
            
            if more_location and more_path:
                # Click the right side of more.png
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
            
            # Now look for download_gemini_image.png
            download_location = wait_for_image("download_gemini_image.png", timeout_seconds=10, confidence=0.8)
            
            if download_location:
                pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
                pyautogui.click()
                time.sleep(0.5)
                print(f"✅ [RETRY] Download initiated (attempt {attempt+1})")
                return True
            else:
                print(f"⚠️ [RETRY] download_gemini_image.png not found (attempt {attempt+1}/{max_retries})")
                # Try scrolling and looking again
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
        """
        Check if entries are in correct order with no missing files.
        If there's a gap (e.g., entry1.png and entry3.png exist but entry2.png missing),
        delete all PNGs and start over.
        
        Returns:
            (valid, next_entry_index)
            valid: True if all existing files are in order
            next_entry_index: The next entry index to process (0-based)
        """
        if not os.path.exists(images_folder):
            os.makedirs(images_folder, exist_ok=True)
            return True, 0
        
        # Get all image files in the images folder
        image_files = []
        for file in os.listdir(images_folder):
            if file.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                image_files.append(file)
        
        if not image_files:
            print(f"📁 [VALIDATE] No image files found in {images_folder}")
            return True, 0
        
        # Extract entry numbers
        entry_numbers = []
        for filename in image_files:
            # Match pattern entry_X.png or entry_X.jpg etc.
            match = re.search(r'entry[_\-]?(\d+)\.(png|jpg|jpeg|gif|webp)$', filename, re.IGNORECASE)
            if match:
                entry_numbers.append(int(match.group(1)))
        
        if not entry_numbers:
            print(f"⚠️ [VALIDATE] No valid entry files found, starting from 0")
            return True, 0
        
        entry_numbers.sort()
        print(f"📊 [VALIDATE] Found entry numbers: {entry_numbers}")
        
        # Check for gaps
        expected_next = 1
        for num in entry_numbers:
            if num != expected_next:
                print(f"❌ [VALIDATE] Gap detected: Expected entry {expected_next}, found entry {num}")
                print(f"🗑️ [VALIDATE] Deleting all image files and starting over...")
                hud.print("🗑️ Resetting due to missing entries...", "warning")
                update_operation_status("Gap detected - resetting all entries")
                
                # Delete all image files in images folder
                for file in image_files:
                    file_path = os.path.join(images_folder, file)
                    try:
                        os.remove(file_path)
                        print(f"🗑️ [VALIDATE] Deleted: {file}")
                    except Exception as e:
                        print(f"⚠️ [VALIDATE] Could not delete {file}: {e}")
                
                return True, 0
            
            expected_next += 1
        
        # All entries are in order, continue from the next
        next_entry = len(entry_numbers)  # This gives the next index (0-based)
        print(f"✅ [VALIDATE] Entries are in order, next entry: {next_entry + 1}")
        return True, next_entry

    def format_entry_json(entry_data):
        """
        Format the entire entry JSON data as a string for pasting.
        """
        try:
            # Convert the entry to a JSON string with proper formatting
            json_str = json.dumps(entry_data, indent=4, ensure_ascii=False)
            return json_str
        except Exception as e:
            print(f"⚠️ [FORMAT] Error formatting JSON: {e}")
            # Fallback: use the scene_pov_prompt
            return entry_data.get('scene_pov_prompt', '')

    # --- MAIN GEMINI WORKFLOW ---
    def load_gemini_url(hwnd):
        """Load the Gemini URL."""
        print(f"🌐 [GEMINI] Loading Gemini URL: {IMAGE_GENERATION_URL}")
        hud.print("📋 Loading Gemini...", "navigating")
        update_operation_status("Loading Gemini...")
        
        fast_paste_url(hwnd, IMAGE_GENERATION_URL)
        time.sleep(3)
        hwnd = ensure_window_ready_and_focused()
        
        return True, hwnd

    def wait_for_generation_complete(hwnd, entry_name, max_wait_seconds=300, check_interval=0.5):
        """
        Wait for generation to complete by checking for generating_image.png first,
        then looking for gemini_microphone.png.
        
        CRITICAL FIX: Must find generating_image.png BEFORE looking for gemini_microphone.png.
        This ensures work is in progress before attempting to look for being ready.
        If generating_image.png is not found, it means the request hasn't been processed yet.
        
        If generating_image.png is found, then monitor for gemini_microphone.png.
        Also checks for gemini_generation_limit_message.png - if found, terminates.
        
        Returns:
            (True, None) if generation complete
            (False, "limit_reached") if generation limit reached
            (False, "timeout") if timeout
        """
        print(f"⏳ [ENTRY] Waiting for generation to complete...")
        hud.print("⏳ Generating image...", "processing")
        update_operation_status(f"Generating image for {entry_name}...")
        
        start_time = time.time()
        last_scroll_time = 0
        scroll_interval = 5  # Scroll every 5 seconds while waiting
        found_generating = False
        generating_first_seen = None
        
        # PHASE 1: Wait for generating_image.png to appear (indicating work has started)
        print(f"🔍 [ENTRY] Phase 1: Waiting for generating_image.png to confirm work has started...")
        
        while time.time() - start_time < max_wait_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Check for limit message (abort condition)
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached while waiting for generating_image.png!")
                hud.print("❌ Generation limit reached!", "error")
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                return False, "limit_reached"
            
            # Check for generating_image.png with fallback
            generating_location = find_image("generating_image.png", confidence=0.7)
            if generating_location:
                print(f"✅ [ENTRY] Found generating_image.png - work has started!")
                found_generating = True
                generating_first_seen = time.time()
                hud.print("⏳ Generation in progress...", "processing")
                update_operation_status(f"Generation in progress for {entry_name}")
                break
            
            # If neither, wait and check again
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"⏳ [ENTRY] Waiting for generation to start... ({elapsed}s elapsed)")
                hud.print(f"⏳ Waiting to start... ({elapsed}s)", "processing")
                update_operation_status(f"Waiting for generation to start for {entry_name}... ({elapsed}s)")
            
            # Scroll periodically to keep content visible
            if time.time() - last_scroll_time > scroll_interval:
                scroll_up_multiple(2)
                last_scroll_time = time.time()
            
            time.sleep(check_interval)
        
        # If generating_image.png was never found, it's a timeout
        if not found_generating:
            print(f"❌ [ENTRY] generating_image.png not found within timeout - generation may not have started")
            return False, "timeout"
        
        # PHASE 2: Now that generating_image.png was found, wait for gemini_microphone.png
        print(f"🔍 [ENTRY] Phase 2: Work confirmed, waiting for gemini_microphone.png (generation complete)...")
        hud.print("⏳ Generating image...", "processing")
        update_operation_status(f"Generation in progress, waiting for completion...")
        
        # Reset timer for phase 2
        phase2_start = time.time()
        phase2_timeout = max_wait_seconds - (generating_first_seen - start_time) if generating_first_seen else max_wait_seconds - 30
        
        # Ensure we have at least 30 seconds for phase 2
        if phase2_timeout < 30:
            phase2_timeout = 30
            print(f"⚠️ [ENTRY] Adjusted phase 2 timeout to {phase2_timeout}s")
        
        while time.time() - phase2_start < phase2_timeout:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Check for gemini_generation_limit_message.png (LIMIT REACHED - ABORT)
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached! Found gemini_generation_limit_message.png")
                hud.print("❌ Generation limit reached!", "error")
                update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
                return False, "limit_reached"
            
            # Check for gemini_microphone.png (indicates image is ready) with fallback
            microphone_location = find_image("gemini_microphone.png", confidence=0.7)
            if microphone_location:
                print(f"✅ [ENTRY] Found gemini_microphone.png - image is ready!")
                hud.print("✅ Image ready", "success")
                update_operation_status(f"Image generation complete for {entry_name}")
                return True, "complete"
            
            # Check if generating_image.png is still present (should be)
            generating_location = find_image("generating_image.png", confidence=0.7)
            if generating_location:
                elapsed = int(time.time() - phase2_start)
                if elapsed % 10 == 0 and elapsed > 0:
                    print(f"⏳ [ENTRY] Still generating... ({elapsed}s elapsed in phase 2)")
                    hud.print(f"⏳ Generating... ({elapsed}s)", "processing")
                    update_operation_status(f"Generating image for {entry_name}... ({elapsed}s)")
                
                # Scroll up periodically to keep content visible
                if time.time() - last_scroll_time > scroll_interval:
                    scroll_up_multiple(3)
                    last_scroll_time = time.time()
                
                time.sleep(check_interval)
                continue
            else:
                # generating_image.png disappeared but microphone not found yet
                # This could mean the generation finished and we're waiting for UI update
                print(f"⚠️ [ENTRY] generating_image.png disappeared, checking for microphone...")
                time.sleep(0.5)
                # Re-check for microphone with fallback
                microphone_location = find_image("gemini_microphone.png", confidence=0.7)
                if microphone_location:
                    print(f"✅ [ENTRY] Found gemini_microphone.png - image is ready!")
                    hud.print("✅ Image ready", "success")
                    update_operation_status(f"Image generation complete for {entry_name}")
                    return True, "complete"
                continue
        
        print(f"⏰ [ENTRY] Generation timeout after {max_wait_seconds} seconds")
        return False, "timeout"

    def wait_for_upload_button_indefinitely(hwnd, entry_name, check_interval=0.5):
        """
        Wait for upload_to_gemini.png button to appear INDEFINITELY.
        This is used when we've already pasted the text and just need to wait for the upload button.
        Only stops when button is found or user manually terminates.
        """
        print(f"⏳ [UPLOAD] Waiting indefinitely for upload_to_gemini.png button...")
        hud.print("⏳ Waiting for upload button...", "waiting")
        update_operation_status(f"Waiting for upload button to appear...")
        
        last_status_time = 0
        elapsed = 0
        start_time = time.time()
        
        while True:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Check for upload_to_gemini.png with fallback
            upload_location = find_image("upload_to_gemini.png", confidence=0.7)
            if upload_location:
                print(f"✅ [UPLOAD] Found upload_to_gemini.png after waiting!")
                return upload_location
            
            # Check for limit message (abort condition)
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [UPLOAD] Generation limit reached while waiting for upload button!")
                hud.print("❌ Generation limit reached!", "error")
                update_operation_status(f"Generation limit reached while waiting for upload for {entry_name}", is_error=True)
                return None
            
            # Print status every 5 seconds
            current_time = time.time()
            if current_time - last_status_time > 5:
                elapsed = int(current_time - start_time)
                print(f"⏳ [UPLOAD] Still waiting for upload button... ({elapsed}s elapsed)")
                hud.print(f"⏳ Waiting for upload... ({elapsed}s)", "waiting")
                update_operation_status(f"Waiting for upload button for {entry_name}... ({elapsed}s)")
                last_status_time = current_time
            
            # Scroll up periodically to make sure button is visible
            if elapsed % 10 == 0 and elapsed > 0:
                scroll_up_multiple(2)
            
            time.sleep(check_interval)

    def process_single_entry(hwnd, entry_index, entry_data, images_folder):
        """
        Process a single entry:
        1. Wait for ask_gemini.png and click
        2. Paste the full entry JSON
        3. Wait for upload_to_gemini.png (confirm paste), click on RIGHT side (NO Enter key)
        4. If upload_to_gemini.png not found, check if text was pasted (Ctrl+C verification)
        5. If text is pasted, wait INDEFINITELY for upload button
        6. If upload button appears, click it
        7. Wait for generating_image.png, gemini_microphone.png, or gemini_generation_limit_message.png
        8. If limit message found, abort operation
        9. When gemini_microphone.png found, check limit message FIRST
        10. If limit message found, abort; otherwise scroll up and click more.png right side
        11. Click download_gemini_image.png
        12. Monitor download with retry if not found after 30 seconds
        13. Rename and save
        """
        entry_name = f"entry_{entry_index + 1}"
        entry_json = format_entry_json(entry_data)
        
        if not entry_json:
            print(f"⚠️ [ENTRY] No data found for {entry_name}")
            return False
        
        print(f"\n{'='*50}")
        print(f"📝 [ENTRY] Processing {entry_name}/{total_entries}")
        print(f"{'='*50}")
        update_operation_status(f"Processing {entry_name}...")
        
        # Step 1: Wait for ask_gemini.png and click it (with fallback support)
        print(f"🔍 [ENTRY] Step 1: Looking for ask_gemini.png with fallback support...")
        ask_location = wait_for_image("ask_gemini.png", timeout_seconds=60, confidence=0.8)
        
        if not ask_location:
            print(f"❌ [ENTRY] Could not find ask_gemini.png in any variant")
            hud.print("❌ UI element not found", "error")
            update_operation_status(f"Could not find ask_gemini.png for {entry_name}", is_error=True)
            return False
        
        pyautogui.moveTo(ask_location.x, ask_location.y, duration=0.1)
        pyautogui.click()
        time.sleep(0.3)
        
        # Step 2: Paste the full entry JSON
        print(f"📝 [ENTRY] Step 2: Pasting full entry JSON...")
        hud.print(f"📝 Pasting {entry_name}...", "typing")
        
        # Click to ensure focus
        pyautogui.click()
        time.sleep(0.1)
        
        # Clear existing text (Ctrl+A, Delete)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.05)
        pyautogui.press('backspace')
        time.sleep(0.05)
        
        # Paste the JSON
        pyperclip.copy(entry_json)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)
        
        # Step 3: Wait for upload_to_gemini.png to confirm paste and click it on the RIGHT side
        print(f"🔍 [ENTRY] Step 3: Looking for upload_to_gemini.png to confirm paste...")
        
        # First, try to wait for upload button with a short timeout
        upload_location = wait_for_image("upload_to_gemini.png", timeout_seconds=10, confidence=0.7)
        
        if not upload_location:
            # If upload button not found immediately, verify text was pasted
            print(f"⚠️ [UPLOAD] Upload button not found initially - verifying text was pasted...")
            
            # Click on the text area to focus it
            pyautogui.click()
            time.sleep(0.1)
            
            # Select all and copy to verify
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            
            # Get clipboard content
            clipboard_content = pyperclip.paste()
            
            # Check if the pasted text matches (allow some tolerance for formatting)
            if clipboard_content and len(clipboard_content) > 10:
                # Verify that the pasted text is similar to what we intended
                # Check if key parts of the entry_json are in the clipboard
                entry_check = entry_json[:100] if len(entry_json) > 100 else entry_json
                clipboard_check = clipboard_content[:100] if len(clipboard_content) > 100 else clipboard_content
                
                if entry_check.strip() in clipboard_check or clipboard_check.strip() in entry_check:
                    print(f"✅ [UPLOAD] Text was successfully pasted (verified by clipboard)")
                    print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png button to appear...")
                    
                    # Wait indefinitely for the upload button
                    upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                    
                    if upload_location is None:
                        # User aborted or limit reached
                        return False
                else:
                    print(f"⚠️ [UPLOAD] Text not properly pasted - clipboard content doesn't match")
                    print(f"   Expected: {entry_check[:50]}...")
                    print(f"   Got: {clipboard_check[:50]}...")
                    
                    # Try pasting again
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
                    
                    # Now wait indefinitely for upload button
                    print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png after retry...")
                    upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                    
                    if upload_location is None:
                        # User aborted or limit reached
                        return False
            else:
                # Clipboard is empty - paste failed
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
                
                # Now wait indefinitely for upload button
                print(f"⏳ [UPLOAD] Waiting INDEFINITELY for upload_to_gemini.png after retry...")
                upload_location = wait_for_upload_button_indefinitely(hwnd, entry_name)
                
                if upload_location is None:
                    # User aborted or limit reached
                    return False
        
        # At this point, we have the upload_location
        if upload_location:
            print(f"✅ [ENTRY] Found upload_to_gemini.png - clicking on RIGHT side to submit")
            # Click the RIGHT side of upload_to_gemini.png (75% from left)
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
                except Exception as e:
                    # Suppress verbose error
                    pass
            
            if not found_variant:
                # Fallback: use the center
                pyautogui.moveTo(upload_location.x, upload_location.y, duration=0.1)
                pyautogui.click()
                time.sleep(0.5)
            
            # Check if upload_to_gemini.png disappeared (means it was sent)
            for _ in range(10):
                if not find_image("upload_to_gemini.png", confidence=0.7):
                    print(f"✅ [ENTRY] upload_to_gemini.png disappeared - request sent")
                    break
                time.sleep(0.3)
        else:
            # This shouldn't happen if we waited indefinitely, but just in case
            print(f"❌ [ENTRY] Could not find upload_to_gemini.png - aborting entry")
            hud.print("❌ Upload button not found", "error")
            update_operation_status(f"Could not find upload_to_gemini.png for {entry_name}", is_error=True)
            return False
        
        # Step 4: Wait for generation to complete (with limit check)
        print(f"⏳ [ENTRY] Step 4: Waiting for generation to complete...")
        generation_complete, status = wait_for_generation_complete(hwnd, entry_name, max_wait_seconds=300)
        
        if status == "limit_reached":
            # Generation limit reached - abort the entire operation
            print(f"❌ [ENTRY] Generation limit reached - aborting all operations")
            abort_operation("Gemini generation limit reached")
            return False
        
        if not generation_complete:
            print(f"❌ [ENTRY] Generation did not complete within timeout")
            hud.print("❌ Generation timeout", "error")
            update_operation_status(f"Generation timeout for {entry_name}", is_error=True)
            return False
        
        # Step 5: Check for limit message BEFORE looking for more.png
        print(f"🔍 [ENTRY] Step 5: Checking for limit message before proceeding...")
        limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
        if limit_location:
            print(f"❌ [ENTRY] Generation limit reached! Aborting.")
            hud.print("❌ Generation limit reached!", "error")
            update_operation_status(f"Generation limit reached for {entry_name}", is_error=True)
            abort_operation(f"Generation limit reached for {entry_name}")
            return False
        
        # Step 6: Look for more.png and click right side
        print(f"🔍 [ENTRY] Step 6: Looking for more.png...")
        
        # Scroll up multiple times to make more.png visible
        scroll_up_multiple(3)
        time.sleep(0.5)
        
        # Try multiple times with scrolling in between, checking for limit each time
        more_location = None
        for attempt in range(5):
            # Check for limit message each attempt
            limit_location = find_image("gemini_generation_limit_message.png", confidence=0.7)
            if limit_location:
                print(f"❌ [ENTRY] Generation limit reached while searching for menu!")
                hud.print("❌ Generation limit reached!", "error")
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
            # Click the right side of the image (75% from left)
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
                except Exception as e:
                    # Suppress verbose error
                    pass
            
            if not found_variant:
                print(f"⚠️ [ENTRY] Could not click more.png - none of the variants worked")
        else:
            print(f"⚠️ [ENTRY] more.png not found after multiple attempts - skipping")
        
        # Step 7: Look for download_gemini_image.png and click it
        print(f"🔍 [ENTRY] Step 7: Looking for download_gemini_image.png...")
        download_location = wait_for_image("download_gemini_image.png", timeout_seconds=30, confidence=0.8)
        
        if not download_location:
            # Try scrolling up and looking again
            scroll_up_multiple(2)
            time.sleep(0.5)
            download_location = wait_for_image("download_gemini_image.png", timeout_seconds=20, confidence=0.8)
        
        if not download_location:
            print(f"❌ [ENTRY] Could not find download_gemini_image.png")
            hud.print("❌ Download button not found", "error")
            update_operation_status(f"Could not find download button for {entry_name}", is_error=True)
            return False
        
        pyautogui.moveTo(download_location.x, download_location.y, duration=0.1)
        pyautogui.click()
        time.sleep(0.5)
        
        print(f"✅ [ENTRY] Download initiated")
        hud.print(f"📥 Downloading {entry_name}...", "downloading")
        update_operation_status(f"Downloading {entry_name}...")
        
        # Step 8: Monitor download with retry mechanism
        print(f"📊 [ENTRY] Step 8: Monitoring download with retry...")
        
        download_success = False
        file_path = None
        download_attempts = 0
        max_download_attempts = 3
        
        while download_attempts < max_download_attempts and not download_success:
            download_attempts += 1
            print(f"🔄 [ENTRY] Download attempt {download_attempts}/{max_download_attempts}")
            
            # Monitor for download with shorter timeout
            timeout_seconds = 30 if download_attempts == 1 else 20
            download_success, file_path = check_and_rename_download(
                entry_name, images_folder, timeout_seconds=timeout_seconds, check_interval=0.3
            )
            
            if download_success:
                print(f"✅ [ENTRY] Download successful on attempt {download_attempts}")
                break
            
            if download_attempts < max_download_attempts:
                print(f"⚠️ [ENTRY] Download not found after {timeout_seconds}s - retrying...")
                hud.print(f"🔄 Retry download... ({download_attempts}/{max_download_attempts})", "warning")
                update_operation_status(f"Retrying download for {entry_name}... (attempt {download_attempts + 1})")
                
                # Click more.png and download again
                retry_success = click_more_and_download(hwnd, entry_name, max_retries=3)
                
                if not retry_success:
                    print(f"❌ [ENTRY] Failed to initiate retry download")
                    break
                
                # Wait for download to start
                time.sleep(2)
        
        if download_success:
            print(f"🎉 [ENTRY] {entry_name} downloaded and saved successfully!")
            hud.print(f"✅ {entry_name} complete", "success")
            update_operation_status(f"{entry_name} completed successfully", is_success=True)
            return True
        else:
            print(f"❌ [ENTRY] Failed to download {entry_name} after {max_download_attempts} attempts")
            hud.print(f"❌ Download failed", "error")
            update_operation_status(f"Failed to download {entry_name} after multiple attempts", is_error=True)
            return False

    # --- MAIN WORKFLOW ---
    def main_gemini_workflow():
        """Main Gemini image generation workflow."""
        try:
            # Note: panel_data is already loaded from the engine check at the top
            # We use the existing panel_data variable
            
            # Check if GUI_IMAGES path exists
            if not os.path.exists(GUI_IMAGES):
                print(f"❌ Error: GUI_IMAGES path not found: {GUI_IMAGES}")
                update_operation_status(f"GUI_IMAGES path not found: {GUI_IMAGES}", is_error=True)
                return
            
            # Set up images folder
            images_folder = os.path.join(IMAGES_PATH, project_title)
            
            print(f"🎬 [MAIN] Starting Gemini image generation workflow...")
            print(f"🖥️ [MAIN] GUI Images path: {GUI_IMAGES}")
            print(f"📁 [MAIN] Project: '{project_title}'")
            print(f"📁 [MAIN] Images folder: {images_folder}")
            print(f"📊 [MAIN] Total entries: {total_entries}")
            
            # Validate entry order
            valid, start_index = validate_entry_order(images_folder)
            if not valid:
                print(f"❌ [MAIN] Entry validation failed")
                return
            
            if start_index >= total_entries:
                print(f"✅ [MAIN] All {total_entries} entries already processed!")
                hud.print("✅ All entries complete!", "success")
                update_operation_status(f"All {total_entries} entries already processed", is_success=True)
                return
            
            print(f"📊 [MAIN] Starting from entry {start_index + 1}")
            
            # Initialize browser
            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized for Gemini operation")
            
            # Load Gemini URL
            print(f"🔍 [MAIN] Loading Gemini URL...")
            success, hwnd = load_gemini_url(hwnd)
            if not success:
                print(f"❌ [MAIN] Failed to load Gemini URL")
                update_operation_status("Failed to load Gemini URL", is_error=True)
                return
            
            # Wait for initial page to load (wait for ask_gemini.png with fallback)
            print(f"🔍 [MAIN] Waiting for Gemini UI to load...")
            ask_location = wait_for_image("ask_gemini.png", timeout_seconds=60, confidence=0.8)
            if not ask_location:
                print(f"⚠️ [MAIN] ask_gemini.png not found - page may not be loaded")
                update_operation_status("Gemini UI not loaded", is_error=True)
                return
            
            print(f"✅ [MAIN] Gemini UI loaded successfully")
            
            # Process entries from start_index to end
            for i in range(start_index, total_entries):
                check_for_termination()
                entry = all_entries[i]
                
                success = process_single_entry(hwnd, i, entry, images_folder)
                
                if success:
                    # Small pause between entries
                    time.sleep(2)
                else:
                    print(f"⚠️ [MAIN] Entry {i+1} failed - continuing with next")
                    time.sleep(3)
                    # Try to reset focus by clicking on the page
                    try:
                        screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                        screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                        pyautogui.click(screen_width // 2, screen_height // 4)
                    except:
                        pass
                    # Check if we're still on the right page
                    if not find_image("ask_gemini.png", confidence=0.7):
                        print(f"🔍 [MAIN] ask_gemini.png not found - navigating to Gemini URL again...")
                        fast_paste_url(hwnd, IMAGE_GENERATION_URL)
                        time.sleep(3)
                        wait_for_image("ask_gemini.png", timeout_seconds=30)
            
            print(f"\n{'='*50}")
            print(f"🎉 [MAIN] All entries processed!")
            print(f"{'='*50}")
            hud.print("🎉 All entries processed!", "success")
            update_operation_status(f"All {total_entries} entries processed successfully", is_success=True)
            
        except KeyboardInterrupt as ki:
            update_operation_status("Gemini operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"Unexpected error in Gemini operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    
    # Call the main workflow
    main_gemini_workflow()
    
def produce_video_from_images_entries():
    """
    Extends images based on script_json entries and concatenates them into a single video.
    
    Workflow:
    1. Read script_json from panel.json
    2. For each entry, extract start/stop timestamps and calculate duration
    3. Match images by number (entry_1.png → entry index 0, entry_2.png → entry index 1, etc.)
    4. Add dialogue captions to each image using PIL (white text with light border, ALL UPPERCASE)
    5. Extend each image to match the entry's duration
    6. Concatenate all extended images into a single video file
    7. Find audio file in downloads folder matching project title
    8. Add audio as background sound to the video
    9. If audio is slightly longer (seconds), extend the last image
    10. If audio is significantly longer (minutes), trim audio to match video
    11. If video is longer, trim video to match audio
    12. Save the final video to 'edited' folder in project directory
    """
    
    # ============================================
    # CONFIGURATION
    # ============================================
    
    # Get panel.json data
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return None
    
    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)
    except Exception as e:
        print(f"❌ Error reading panel.json: {e}")
        return None
    
    # Get project title
    project_title = panel_data.get('project_name', {}).get('project_title')
    
    if not project_title:
        project_title = panel_data.get('project_title')
        
    if not project_title:
        print(f"❌ Error: project_title not found in panel.json")
        return None
    
    print(f"📁 [produce_video_from_images_entries] Processing project: {project_title}")
    
    # Define paths
    def normalize_project_title(name):
        if not name:
            return "unnamed_project"
        normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        normalized = normalized.strip('_')
        return normalized if normalized else "unnamed_project"
    
    normalized_project_title = normalize_project_title(project_title)
    project_folder = os.path.join(IMAGES_PATH, normalized_project_title)
    
    # Check multiple possible image source locations
    possible_image_folders = [
        os.path.join(project_folder, "images"),
        project_folder,
    ]
    
    # Find which folder has images
    source_folder = None
    
    for folder_path in possible_image_folders:
        if os.path.exists(folder_path):
            print(f"🔍 Checking: {folder_path}")
            try:
                image_files_check = [f for f in os.listdir(folder_path) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'))]
                if image_files_check:
                    source_folder = folder_path
                    print(f"✅ Found {len(image_files_check)} images in: {folder_path}")
                    break
            except Exception as e:
                print(f"   ⚠️ Error checking folder: {e}")
    
    if not source_folder:
        print(f"❌ No images found")
        return None
    
    images_folder = source_folder
    edited_folder = os.path.join(project_folder, "edited")
    temp_folder = os.path.join(project_folder, "temp_captions")
    
    # Create temp folder for captioned images
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
        print(f"📁 Created temp folder: {temp_folder}")
    
    # ============================================
    # STEP 1: GET ENTRIES FROM SCRIPT_JSON
    # ============================================
    
    def parse_timestamp_to_seconds(timestamp_str):
        if not timestamp_str:
            return 0
        
        timestamp_str = str(timestamp_str).strip()
        
        try:
            parts = timestamp_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            return 0
    
    def get_entries_from_script(panel_data):
        script_json = panel_data.get('project_name', {}).get('script_json', {})
        script_data = script_json.get('script', {})
        
        all_entries = []
        
        for batch_key, batch_data in script_data.items():
            if isinstance(batch_data, dict) and 'entries' in batch_data:
                entries = batch_data.get('entries', [])
                for entry in entries:
                    if 'scene_pov_prompt' in entry:
                        start_str = entry.get('start', '0:00')
                        stop_str = entry.get('stop', '0:05')
                        
                        start_seconds = parse_timestamp_to_seconds(start_str)
                        stop_seconds = parse_timestamp_to_seconds(stop_str)
                        
                        duration = stop_seconds - start_seconds
                        if duration < 0.5:
                            duration = 1.0
                        
                        processed_entry = entry.copy()
                        processed_entry['start_seconds'] = start_seconds
                        processed_entry['stop_seconds'] = stop_seconds
                        processed_entry['duration_seconds'] = duration
                        processed_entry['dialogue'] = entry.get('dialogue', '')
                        
                        all_entries.append(processed_entry)
        
        try:
            all_entries.sort(key=lambda x: x.get('start_seconds', 0))
        except:
            pass
        
        print(f"📊 Found {len(all_entries)} entries")
        return all_entries
    
    entries = get_entries_from_script(panel_data)
    
    if not entries:
        print(f"❌ No entries found")
        return None
    
    # ============================================
    # STEP 2: GET IMAGES
    # ============================================
    
    def get_sorted_images(folder_path):
        if not os.path.exists(folder_path):
            return []
        
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for file in os.listdir(folder_path):
            file_lower = file.lower()
            if any(file_lower.endswith(ext) for ext in image_extensions):
                match = re.match(r'entry[_\-]?(\d+)', file, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    image_files.append({
                        'number': num,
                        'filename': file,
                        'path': os.path.join(folder_path, file)
                    })
        
        image_files.sort(key=lambda x: x['number'])
        print(f"📁 Found {len(image_files)} images")
        return image_files
    
    image_files = get_sorted_images(images_folder)
    
    if not image_files:
        print(f"❌ No images found")
        return None
    
    # ============================================
    # STEP 3: FIND AUDIO FILE
    # ============================================
    
    def find_audio_file(project_title):
        downloads_folder = os.path.expanduser("~/Downloads")
        
        if not os.path.exists(downloads_folder):
            print(f"❌ Downloads folder not found")
            return None
        
        audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma'}
        
        try:
            print(f"🔍 Searching for audio files in: {downloads_folder}")
            
            for file in os.listdir(downloads_folder):
                file_lower = file.lower()
                if any(file_lower.endswith(ext) for ext in audio_extensions):
                    if project_title.lower() in file_lower:
                        file_path = os.path.join(downloads_folder, file)
                        print(f"✅ Found audio: {file}")
                        return file_path
        except Exception as e:
            print(f"⚠️ Error searching for audio: {e}")
        
        return None
    
    audio_file_path = find_audio_file(project_title)
    
    if audio_file_path:
        print(f"✅ Audio file found: {os.path.basename(audio_file_path)}")
    else:
        print(f"⚠️ No audio file found - video will be silent")
    
    # ============================================
    # STEP 4: CREATE EDITED FOLDER
    # ============================================
    
    if not os.path.exists(edited_folder):
        os.makedirs(edited_folder)
        print(f"📁 Created edited folder: {edited_folder}")
    else:
        print(f"📁 Using existing edited folder: {edited_folder}")
        existing_mp4s = [f for f in os.listdir(edited_folder) if f.endswith('.mp4')]
        if existing_mp4s:
            print(f"🗑️ Cleaning {len(existing_mp4s)} existing .mp4 files...")
            for f in existing_mp4s:
                try:
                    os.remove(os.path.join(edited_folder, f))
                except:
                    pass
    
    # ============================================
    # STEP 5: ADD CAPTIONS USING PIL (WHITE TEXT WITH LIGHT BORDER, ALL UPPERCASE, 60% WIDTH, DOUBLE PADDING)
    # ============================================
    
    def add_caption_with_pil(image_path, output_path, text, width, height):
        """
        Add caption to image using PIL (Pillow).
        White text with a very light border/outline for readability.
        ALL text is converted to UPPERCASE.
        Text width limited to 60% of image width.
        Bottom padding is 60px.
        """
        try:
            # Open image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Create a draw object
            draw = ImageDraw.Draw(img)
            
            # Try to load a font, fallback to default
            try:
                # Try to find a system font
                font_size = max(24, int(img_width / 45))
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("Arial.ttf", font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Convert text to UPPERCASE
            uppercase_text = text.upper()
            
            # Calculate max width for text (60% of image width)
            max_text_width = int(img_width * 0.6)
            
            # Simple text wrapping with 60% width limit
            words = uppercase_text.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                # Estimate text width (rough approximation)
                if len(test_line) * (font_size * 0.6) < max_text_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            wrapped_text = '\n'.join(lines)
            
            # Calculate text position (bottom center)
            text_bbox = draw.textbbox((0, 0), wrapped_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (img_width - text_width) // 2
            # Double the bottom padding: 30px -> 60px
            y = img_height - text_height - 60
            
            # Draw LIGHT border/outline first (very subtle)
            # Using a dark gray/charcoal color with very thin outline
            outline_color = (60, 60, 60)  # Dark gray, not pure black for subtlety
            outline_width = 1  # Very thin outline
            
            # Draw the outline in all 8 directions for a light border effect
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), wrapped_text, font=font, fill=outline_color)
            
            # Draw the main white text on top
            draw.text((x, y), wrapped_text, font=font, fill='white')
            
            # Save image
            img.save(output_path, quality=95)
            return True
            
        except Exception as e:
            print(f"⚠️ PIL caption error: {e}")
            # If PIL fails, copy original
            import shutil
            shutil.copy2(image_path, output_path)
            return False
    
    # ============================================
    # STEP 6: PROCESS ALL IMAGES WITH CAPTIONS
    # ============================================
    
    print(f"\n🎬 Adding captions to images using PIL...")
    
    # Get dimensions from first image
    first_image = image_files[0]['path']
    try:
        temp_img = Image.open(first_image)
        video_width, video_height = temp_img.size
        temp_img.close()
        print(f"📐 Image dimensions: {video_width}x{video_height}")
    except:
        video_width, video_height = 1920, 1080
        print(f"⚠️ Using default dimensions: {video_width}x{video_height}")
    
    captioned_images = []
    processed = 0
    failed = 0
    skipped = 0
    total_duration = 0
    
    # Process images
    for i in range(min(len(entries), len(image_files))):
        entry = entries[i]
        image_info = image_files[i]
        
        duration = entry.get('duration_seconds', 5.0)
        dialogue = entry.get('dialogue', '')
        entry_num = i + 1
        
        # Create temp filename
        temp_filename = f"captioned_{image_info['number']}.jpg"
        temp_path = os.path.join(temp_folder, temp_filename)
        
        print(f"🎬 [{entry_num}/{len(image_files)}] {image_info['filename']} - {duration:.1f}s")
        
        if dialogue:
            preview = dialogue[:40] + '...' if len(dialogue) > 40 else dialogue
            print(f"   💬 '{preview}' -> UPPERCASE")
            
            # Add caption using PIL (converts to UPPERCASE)
            success = add_caption_with_pil(
                image_info['path'],
                temp_path,
                dialogue,  # Pass original text, will be converted to UPPERCASE inside the function
                video_width,
                video_height
            )
            
            if success:
                captioned_images.append({
                    'number': image_info['number'],
                    'path': temp_path,
                    'duration': duration
                })
                processed += 1
                total_duration += duration
                print(f"   ✅ Caption added (UPPERCASE, light border)")
            else:
                # Use original image if caption fails
                captioned_images.append({
                    'number': image_info['number'],
                    'path': image_info['path'],
                    'duration': duration
                })
                processed += 1
                total_duration += duration
                print(f"   ⚠️ Used original image (no caption)")
        else:
            # No dialogue, use original
            captioned_images.append({
                'number': image_info['number'],
                'path': image_info['path'],
                'duration': duration
            })
            processed += 1
            total_duration += duration
            print(f"   ℹ️ No caption (dialogue empty)")
    
    if not captioned_images:
        print("❌ No images processed")
        return None
    
    print(f"\n📊 Processed {processed} images, {failed} failed, {skipped} skipped")
    print(f"⏱️ Total duration: {total_duration:.1f}s")
    
    # ============================================
    # STEP 7: CHECK AUDIO DURATION AND ADJUST
    # ============================================
    
    audio_duration = None
    if audio_file_path and os.path.exists(audio_file_path):
        try:
            # Load audio to check duration
            temp_audio = AudioFileClip(audio_file_path)
            audio_duration = temp_audio.duration
            temp_audio.close()
            print(f"🎵 Audio duration: {audio_duration:.1f}s")
            print(f"🎬 Video duration: {total_duration:.1f}s")
            
            # Calculate difference
            diff = audio_duration - total_duration
            
            if diff > 0:
                # Audio is longer than video
                if diff <= 30:  # If difference is 30 seconds or less (seconds difference)
                    print(f"   📊 Audio is {diff:.1f}s longer (seconds difference)")
                    print(f"   🔄 Extending last image to match audio duration")
                    
                    # Extend the last image
                    last_image = captioned_images[-1]
                    new_duration = last_image['duration'] + diff
                    captioned_images[-1]['duration'] = new_duration
                    total_duration = audio_duration
                    print(f"   ✅ Last image extended by {diff:.1f}s to {new_duration:.1f}s")
                    print(f"   📊 New total video duration: {total_duration:.1f}s")
                    
                else:  # Difference is more than 30 seconds (minutes difference)
                    print(f"   📊 Audio is {diff:.1f}s longer (minutes difference)")
                    print(f"   🔄 Trimming audio to match video duration")
                    # We'll trim the audio when adding it
                    audio_duration = total_duration
            elif diff < 0:
                # Video is longer than audio
                print(f"   📊 Video is {abs(diff):.1f}s longer than audio")
                print(f"   🔄 Trimming video to match audio duration")
                total_duration = audio_duration
                print(f"   📊 New total video duration: {total_duration:.1f}s")
            else:
                print(f"   ✅ Audio and video durations match exactly!")
                
        except Exception as e:
            print(f"⚠️ Error checking audio duration: {e}")
            audio_duration = None
    
    # ============================================
    # STEP 8: CREATE VIDEO CLIPS AND CONCATENATE
    # ============================================
    
    print(f"\n🎬 Creating video clips...")
    
    clips = []
    
    for img_data in captioned_images:
        try:
            clip = ImageClip(img_data['path']).with_duration(img_data['duration'])
            clips.append(clip)
        except Exception as e:
            print(f"⚠️ Error creating clip for {img_data['path']}: {e}")
    
    if not clips:
        print("❌ No clips created")
        return None
    
    print(f"🎬 Concatenating {len(clips)} clips...")
    print(f"   Target duration: {total_duration:.1f}s")
    
    try:
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # Add audio if available
        audio_clip = None
        if audio_file_path and os.path.exists(audio_file_path):
            try:
                print(f"🎵 Adding audio: {os.path.basename(audio_file_path)}")
                audio_clip = AudioFileClip(audio_file_path)
                actual_audio_duration = audio_clip.duration
                
                print(f"   Video: {total_duration:.1f}s, Audio: {actual_audio_duration:.1f}s")
                
                # Check if we need to trim audio (only if it's significantly longer)
                if actual_audio_duration > total_duration:
                    diff = actual_audio_duration - total_duration
                    if diff > 30:  # If difference is more than 30 seconds, trim audio
                        print(f"   🔄 Trimming audio to match video duration")
                        try:
                            audio_clip = audio_clip.subclip(0, total_duration)
                        except:
                            try:
                                audio_clip = audio_clip.with_duration(total_duration)
                            except:
                                pass
                    else:
                        # If we already extended the last image, audio should match
                        print(f"   ✅ Audio duration matches video (within {diff:.1f}s)")
                
                final_clip = final_clip.with_audio(audio_clip)
                print(f"✅ Audio added successfully")
                
            except Exception as e:
                print(f"⚠️ Error adding audio: {e}")
                if audio_clip:
                    try:
                        audio_clip.close()
                    except:
                        pass
                audio_clip = None
        
        # Save final video
        output_filename = f"{normalized_project_title}.mp4"
        output_path = os.path.join(edited_folder, output_filename)
        
        print(f"💾 Saving: {output_filename}")
        
        # Write video without verbose parameter
        try:
            # Try with logger only
            final_clip.write_videofile(
                output_path,
                fps=1,
                codec='libx264',
                audio_codec='aac' if audio_file_path else None,
                logger=None
            )
        except TypeError:
            # If logger fails, try without it
            try:
                final_clip.write_videofile(
                    output_path,
                    fps=1,
                    codec='libx264',
                    audio_codec='aac' if audio_file_path else None
                )
            except Exception as e:
                print(f"⚠️ Error saving video: {e}")
                # Try with minimal parameters
                final_clip.write_videofile(
                    output_path,
                    fps=1
                )
        
        # Clean up
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        
        try:
            final_clip.close()
        except:
            pass
        
        if audio_clip:
            try:
                audio_clip.close()
            except:
                pass
        
        print(f"✅ Video saved: {output_path}")
        print(f"📊 Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
        
        # Clean up temp folder
        try:
            import shutil
            shutil.rmtree(temp_folder)
            print(f"🧹 Cleaned up temp folder")
        except:
            pass
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # ============================================
    # SUMMARY
    # ============================================
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"   Project: {project_title}")
    print(f"   Entries: {len(entries)}")
    print(f"   Images processed: {processed}")
    print(f"   Total duration: {total_duration:.1f}s")
    print(f"   Captions: ALL UPPERCASE, 60% width, 60px bottom padding, light border")
    print(f"   Audio: {'✅ Added' if audio_file_path else '❌ None'}")
    if audio_file_path:
        print(f"   Audio file: {os.path.basename(audio_file_path)}")
        if audio_duration:
            print(f"   Audio duration: {audio_duration:.1f}s")
    print(f"   Output: {edited_folder}")
    print(f"   Video: {output_filename}")
    print("="*60)
    print("✅ Complete!")
    
    return {
        'project_title': project_title,
        'entries_count': len(entries),
        'images_processed': processed,
        'total_duration': total_duration,
        'audio_added': bool(audio_file_path),
        'audio_file': os.path.basename(audio_file_path) if audio_file_path else None,
        'output_folder': edited_folder,
        'output_file': output_filename,
        'output_path': output_path
    }

if __name__ == "__main__":
   produce_video_from_images_entries()

   

         
