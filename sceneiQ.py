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

# Configure Paths
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\xampp\htdocs\sceniq\pytesseract\tessdata"
tessdata_path = r"C:\xampp\htdocs\scenIQ\pytesseract\tessdata\eng.traineddata"
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PANEL_PATH = r"C:\xampp\htdocs\scenIQ\panel.json"
INPUT_IMAGE_PATH = r"C:\xampp\htdocs\sceniq\input_images"
GUI_IMAGE_PATH = r"C:\xampp\htdocs\sceniq\gui_images"
OUTPUT_TEXT_PATH = r"C:\xampp\htdocs\scenIQ\screen_content.text"
IMAGES_PATH = r"C:\xampp\htdocs\sceniq\project"

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

def ocr():
    """
    Validates environment, cleans working directories, captures the screen,
    extracts all characters, spatially merges characters/words purely by coordinate 
    proximity (ignoring brittle Tesseract line numbers) to rebuild clean text chunks, 
    writes output logs, and summarizes results.
    """
    
    
    if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
        print(f"❌ Error: Tesseract executable not found at: {pytesseract.pytesseract.tesseract_cmd}")
        return None
    if not os.path.exists(tessdata_path):
        print(f"❌ Error: English language data not found at: {tessdata_path}")
        return None
    try:
        # Create the input_images directory if it doesn't exist
        os.makedirs(INPUT_IMAGE_PATH, exist_ok=True)
        
        if os.path.exists(INPUT_IMAGE_PATH):
            for file in glob.glob(os.path.join(INPUT_IMAGE_PATH, "*.png")):
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"   ⚠️ Could not delete {os.path.basename(file)}: {e}")

        print("📸 Capturing screen...")
        screenshot = pyautogui.screenshot()
        output_image_path = os.path.join(INPUT_IMAGE_PATH, "screen.png")
        screenshot.save(output_image_path)

        screen_width, screen_height = pyautogui.size()
        print(f"🖥️ Screen Dimensions: {screen_width} x {screen_height} pixels")
        
        print("📝 Extracting text with coordinates...")
        custom_config = (
            '--psm 11 -c tessedit_char_whitelist='
            '\'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:-_=@############/\\\\?&|()[]{}<>~°%©®+— \\"\\\'\''
        )
        
        data = pytesseract.image_to_data(screenshot, config=custom_config, output_type=pytesseract.Output.DICT)
        
        raw_elements = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            confidence = int(data['conf'][i])
            
            if text:
                left = data['left'][i]
                top = data['top'][i]
                width = data['width'][i]
                height = data['height'][i]
                
                raw_elements.append({
                    'text': text,
                    'left': left,
                    'top': top,
                    'right': left + width,
                    'bottom': top + height,
                    'width': width,
                    'height': height,
                    'confidence': confidence
                })
        clean_texts = []
        
        if raw_elements:
            raw_elements.sort(key=lambda x: (x['top'], x['left']))
            
            while raw_elements:
                current = raw_elements.pop(0)
                max_horizontal_gap = max(12, current['height'] * 0.4) 
                max_vertical_deviation = current['height'] * 0.4      
                
                merged_any = True
                while merged_any:
                    merged_any = False
                    for i, next_el in enumerate(raw_elements):
                        current_center_y = current['top'] + (current['height'] / 2)
                        next_center_y = next_el['top'] + (next_el['height'] / 2)
                        
                        is_same_line_geometry = abs(current_center_y - next_center_y) <= max_vertical_deviation
                        horizontal_gap = next_el['left'] - current['right']
                        is_close_horizontally = (-5 <= horizontal_gap <= max_horizontal_gap)
                        
                        if is_same_line_geometry and is_close_horizontally:
                            if horizontal_gap > 3 and not current['text'].endswith(('/', ':', '.', '@', '-')):
                                current['text'] += " " + next_el['text']
                            else:
                                current['text'] += next_el['text']
                                
                            current['right'] = max(current['right'], next_el['right'])
                            current['left'] = min(current['left'], next_el['left'])
                            current['top'] = min(current['top'], next_el['top'])
                            current['bottom'] = max(current['bottom'], next_el['bottom'])
                            current['width'] = current['right'] - current['left']
                            current['height'] = current['bottom'] - current['top']
                            
                            if current['confidence'] != -1 and next_el['confidence'] != -1:
                                current['confidence'] = (current['confidence'] + next_el['confidence']) // 2
                            
                            raw_elements.pop(i)
                            merged_any = True
                            break
                
                current['distance_from_top'] = current['top']
                current['distance_from_bottom'] = screen_height - current['bottom']
                current['screen_percentage'] = (current['top'] / screen_height) * 100
                
                if "htips" in current['text']:
                    current['text'] = current['text'].replace("htips", "https")
                if "searcl" in current['text'].lower():
                    current['text'] = current['text'].lower().replace("searcl", "search").replace("Searcl", "Search")
                    
                clean_texts.append(current)

            clean_texts.sort(key=lambda x: (x['top'], x['left']))

        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(OUTPUT_TEXT_PATH), exist_ok=True)
        with open(OUTPUT_TEXT_PATH, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("GEOMETRICALLY CLEANED SCREEN EXTRACTION\n")
            f.write(f"Extracted on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Screen Resolution: {screen_width} x {screen_height} pixels\n")
            f.write("="*80 + "\n\n")
            
            for i, word_data in enumerate(clean_texts, 1):
                f.write(f"Text Block {i}: {word_data['text']}\n")
                f.write(f"  Left: {word_data['left']:>6}  Top: {word_data['top']:>6}\n")
                f.write(f"  Right: {word_data['right']:>6}  Bottom: {word_data['bottom']:>6}\n")
                f.write(f"  Width: {word_data['width']:>6}  Height: {word_data['height']:>6}\n")
                f.write(f"  📏 Distance from Top: {word_data['distance_from_top']:>6} pixels ({word_data['screen_percentage']:.1f}% of screen)\n")
                f.write(f"  📏 Distance from Bottom: {word_data['distance_from_bottom']:>6} pixels\n")
                f.write(f"  Confidence: {word_data['confidence']}%\n")
                f.write("-" * 40 + "\n")
            
            f.write("\n\n" + "="*80 + "\n")
            f.write("COMPACT FORMAT (left, top, right, bottom, distance_from_top_px, screen_percentage%, text):\n")
            f.write("="*80 + "\n")
            for word_data in clean_texts:
                f.write(f"{word_data['left']:>6}, {word_data['top']:>6}, {word_data['right']:>6}, {word_data['bottom']:>6}, "
                        f"{word_data['distance_from_top']:>6}px, {word_data['screen_percentage']:>5.1f}%, '{word_data['text']}'\n")

        full_text = "   ".join([word['text'] for word in clean_texts])
        print(f"✅ Total clean text blocks saved: {len(clean_texts)}")
        
        if clean_texts:
            highest = min(clean_texts, key=lambda x: x['top'])
            lowest = max(clean_texts, key=lambda x: x['bottom'])
        print("="*80)

        return clean_texts

    except Exception as e:
        print(f"❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def abort_operation(reason="Operation aborted"):
        """
        Global abort helper that triggers the Alt+/ hotkey to stop the automation.
        Can be called from anywhere in the function to gracefully terminate.
        
        Args:
            reason: String describing why the operation was aborted
        """
        print(f"🛑 [ABORT] {reason}")
        hud.print(f"🛑 {reason}", "error")
        
        # Trigger the termination flag
        global terminate_automation
        terminate_automation = True
        
        # Also simulate the hotkey press as a backup
        try:
            pyautogui.hotkey('alt', '/')
        except Exception:
            pass
        
        # Raise KeyboardInterrupt to break out of loops
        raise KeyboardInterrupt(f"Operation aborted: {reason}")

def operate_google_flow_browser():
    """
    Launches Microsoft Edge, maximizes it.
    Features: Live HUD tracking, click-through overlay, 
    global hotkey interception, and step routing matrices.
    """
    # --- SPEED TUNING PARAMETERS ---
    pyautogui.PAUSE = 0.0  

    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    with open(PANEL_PATH, 'r', encoding='utf-8') as file:
        panel_data = json.load(file)

    project_title = panel_data.get('project_title')
    terminate_automation = False
    operation_status_flag = True  # Global flag tracking operation health
    operation_status_message = ""  # Current status message
    operation_aborted = False  # Flag for abortion state

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        """
        Update the operation status in panel.json with a professional message.
        
        Args:
            message: The status message to write
            is_error: Whether this is an error state
            is_abort: Whether this is an abortion state
            is_success: Whether this is a success state
        """
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        
        try:
            # Read current panel data
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)
            
            # Format the status message professionally
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
            
            # Update the operation_status field
            current_panel['operation_status'] = operation_status_message
            
            # Write back to file
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(current_panel, file, indent=4, ensure_ascii=False)
            
            # If aborted, we should stop the program
            if is_abort:
                print(f"🛑 [STATUS] Operation aborted: {message}")
                raise SystemExit(f"Operation aborted: {message}")
                
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        """Abort the operation with a specific reason."""
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting {project_title}: {reason}", is_abort=True)
        # The update_operation_status will raise SystemExit

    def check_operation_status():
        """Check if operation status is still valid (not aborted/errored)."""
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status(f"Manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status(f"Operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

    def safe_ocr():
        """Capture screen without hiding the HUD (HUD is click-through)"""
        check_for_termination()
        return ocr()

    def clean_string_completely(text):
        if not text: return ""
        t = text.lower().replace("https", "").replace("http", "").replace("www", "")
        return re.sub(r'[^a-z0-9]', '', t)
    
    # ============================================
    # SECTION 1: WINDOW MANAGEMENT HELPERS
    # ============================================
    
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
        print(f"🖥️ [MONITOR] Bounds: ({monitor_left}, {monitor_top}) to ({monitor_right}, {monitor_bottom})")
        print(f"📐 [MONITOR] Size: {monitor_right - monitor_left} x {monitor_bottom - monitor_top} pixels")
        
        edge_windows = get_edge_window_on_monitor(current_monitor)
        
        if edge_windows:
            hwnd = edge_windows[0]['hwnd']
            print(f"🪟 [WINDOW] Found existing Edge window handle: {hwnd}")
            print(f"📏 [WINDOW] Size: {edge_windows[0]['width']} x {edge_windows[0]['height']}")
            
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
                update_operation_status(f"Browser window ready and maximized")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status(f"Launching Microsoft Edge browser...")
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
                    update_operation_status(f"Microsoft Edge launched and maximized")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        error_msg = "Failed to get or launch Edge window"
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
            except Exception as e:
                print(f"⚠️ [FOCUS] Could not check maximize state, attempting maximize anyway: {e}")
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
        hud.print("📋 Navigating to destination...", "typing")
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.1)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        hud.print("")
        update_operation_status(f"Navigating to {project_title if project_title else 'destination'}...")

    # ============================================
    # SECTION 2: COMMON UTILITY FUNCTIONS
    # ============================================
    
    def analyze_url_visibility(target, extracted_elements):
        """Check if we're on the right page based on URL text in OCR"""
        if not extracted_elements: 
            return False, None
        clean_target = clean_string_completely(target)
        clean_project_sig = clean_string_completely(f"{target}/project")
        if not clean_target: 
            return False, None
            
        is_base_found = False
        is_project_found = False

        for element in extracted_elements:
            clean_element_text = clean_string_completely(element['text'])
            if clean_project_sig in clean_element_text:
                is_project_found = True
            elif clean_target in clean_element_text:
                is_base_found = True

        if is_project_found:
            return True, "project"
        elif is_base_found:
            return True, "all_projects"
            
        return False, None

    def get_screen_fingerprint(extracted_elements):
        """Create a fingerprint of current screen text for change detection"""
        if not extracted_elements: 
            return ""
        return "||".join([el['text'].strip() for el in extracted_elements])

    def verify_if_text_changes(current_texts, previous_fingerprint):
        """
        Compare current OCR text with previous fingerprint.
        Returns: (text_changed, new_fingerprint)
        """
        current_fingerprint = get_screen_fingerprint(current_texts)
        
        if not previous_fingerprint:
            print("🔄 [CHANGE] First scan - treating as changed")
            return True, current_fingerprint
        
        if current_fingerprint == previous_fingerprint:
            print("📄 [CHANGE] No text content changes detected")
            return False, current_fingerprint
        else:
            print("🔄 [CHANGE] Text content has changed")
            return True, current_fingerprint

    # ============================================
    # SECTION 3: SELF-HEALING HELPERS FOR ALL PROJECTS PAGE
    # ============================================
    
    def analyze_current_page_context(hwnd, target_url, project_title=None):
        """
        Analyzes current page context.
        For SPA: We check if the project name is visible AND if we're on the correct view.
        Returns: (is_on_all_projects, is_on_project_page, project_title_found, context_string)
        """
        check_for_termination()
        current_texts = safe_ocr()
        
        if not current_texts:
            return False, False, False, "no_text"
        
        # Check URL context
        url_found, current_state = analyze_url_visibility(target_url, current_texts)
        
        # Check for project page indicators
        has_all_media = False
        has_new_project = False
        project_title_found = False
        
        clean_project_title = clean_string_completely(project_title) if project_title else ""
        
        for element in current_texts:
            clean_text = clean_string_completely(element['text'])
            if "allmedia" in clean_text or "all media" in clean_text:
                has_all_media = True
            if "newproject" in clean_text:
                has_new_project = True
            if clean_project_title and clean_project_title in clean_text:
                project_title_found = True
                # Check if this element is likely a card (not header/button)
                element_text = element['text'].lower()
                if "all media" in element_text or "new project" in element_text:
                    # This is UI text, not a card
                    project_title_found = False
        
        # SPECIAL SPA DETECTION:
        # If we see "All Media" AND the project name, we're ON a project page
        # If we see "New Project" AND project name is visible in a card context, we're on All Projects
        # But if project name is found AND "All Media" is found, we're on project page
        # If project name is found AND "New Project" is found, we're on All Projects page
        
        is_on_project = False
        is_on_all_projects = False
        
        # CRITICAL FIX: Detect project page by presence of "All Media" AND project name
        if has_all_media and project_title_found:
            is_on_project = True
            is_on_all_projects = False
            return False, True, True, "project_correct"
        
        # Detect All Projects page by presence of "New Project" AND project name in card context
        if has_new_project and project_title_found:
            is_on_all_projects = True
            is_on_project = False
            return True, False, True, "all_projects"
        
        # If only project name found but no context, check URL-based detection
        if url_found and current_state == "all_projects":
            return True, False, project_title_found, "all_projects"
        elif (url_found and current_state == "project") or has_all_media:
            return False, True, project_title_found, "project_correct"
        
        # If we only found project name without context, assume All Projects
        if project_title_found:
            return True, False, True, "all_projects"
        
        return False, False, False, "unknown"
    
    def all_project_watchdog(hwnd, all_project_url, project_title, depth=0):
        """Watchdog for All Projects page with self-healing capabilities."""
        check_for_termination()
        print("🛡️ [ALL_WATCHDOG] Starting all projects watchdog...")
        hud.print("🔍 Analyzing page context...", "searching")
        update_operation_status(f"Analyzing page context for projects list...")
        
        if depth > 5:
            print("❌ [ALL_WATCHDOG] Max recursion depth reached")
            hud.print("❌ Watchdog recursion limit", "error")
            error_msg = "Max recursion depth reached in watchdog"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, False, False, hwnd
        
        # Analyze current page context
        on_all, on_project, project_found, context = analyze_current_page_context(
            hwnd, all_project_url, project_title
        )
        
        print(f"📊 [ALL_WATCHDOG] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
        
        # If we're on All Projects page
        if on_all:
            print("✅ [ALL_WATCHDOG] On All Projects page")
            hud.print("📋 On projects list", "success")
            update_operation_status(f"Successfully navigated to All Projects page")
            return True, False, False, hwnd
        
        # If we're on a project page
        if on_project:
            print("✅ [ALL_WATCHDOG] On a specific project page")
            hud.print("📋 On project page", "info")
            update_operation_status(f"Currently on a project page, verifying {project_title}...")
            
            if project_found:
                print("✅ [ALL_WATCHDOG] Target project identified on page")
                hud.print(f"✅ {project_title} verified", "success")
                update_operation_status(f"Successfully verified {project_title} on project page")
                return False, True, True, hwnd
            else:
                print(f"⚠️ [ALL_WATCHDOG] On project page but target project not found")
                hud.print("⚠️ Project mismatch", "warning")
                error_msg = f"On project page but {project_title} not found"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return False, True, False, hwnd
        
        # Context unknown - navigate to all projects
        print("❌ [ALL_WATCHDOG] Page context unknown, navigating to all projects...")
        hud.print("❌ Page context unknown, navigating...", "error")
        update_operation_status(f"Page context unknown, navigating to projects list...")
        fast_paste_url(hwnd, all_project_url)
        time.sleep(3)
        return all_project_watchdog(hwnd, all_project_url, project_title, depth + 1)

    def wait_for_all_projects_page_ready(hwnd, all_project_url, project_title, timeout_seconds=60, depth=0):
        """Wait for All Projects page to be ready with context analysis on each attempt."""
        check_for_termination()
        print("⏳ [ALL_READY] Waiting for All Projects page to load...")
        hud.print("⏳ Loading projects list...", "waiting")
        update_operation_status(f"Loading All Projects page...")
        
        if depth > 5:
            print("❌ [ALL_READY] Max recursion depth reached")
            hud.print("❌ Page ready timeout", "error")
            error_msg = "Max recursion depth reached waiting for All Projects page"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        start_time = time.time()
        confirmation_text = "new project"
        clean_confirmation = clean_string_completely(confirmation_text)
        specific_attempts = 0
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Analyze current page context
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, all_project_url, project_title
            )
            
            print(f"📊 [ALL_READY] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
            
            # If on project page with correct project, we're done
            if on_project and project_found:
                print("✅ [ALL_READY] Already on correct project page - proceeding")
                hud.print("✅ Target found, proceeding...", "success")
                update_operation_status(f"Already on {project_title} project page")
                return True, hwnd
            
            # If on project page with wrong project, navigate back
            if on_project and not project_found:
                print(f"⚠️ [ALL_READY] On project page but wrong project (attempt {specific_attempts + 1})")
                hud.print("⚠️ Wrong project, navigating back...", "warning")
                update_operation_status(f"Wrong project detected, navigating back to projects list...")
                
                if specific_attempts < 3:
                    fast_paste_url(hwnd, all_project_url)
                    time.sleep(3)
                    specific_attempts += 1
                    continue
                else:
                    print("🔄 [ALL_READY] Too many attempts, proceeding with specific page")
                    hud.print("📋 Proceeding with current page...", "info")
                    update_operation_status(f"Proceeding with current page after multiple attempts")
                    return True, hwnd
            
            # If on all projects page, check for confirmation text
            if on_all:
                current_texts = safe_ocr()
                confirmation_found = False
                for element in current_texts:
                    if clean_confirmation in clean_string_completely(element['text']):
                        confirmation_found = True
                        break
                
                if confirmation_found:
                    print("✅ [ALL_READY] All Projects page ready")
                    hud.print("✅ Projects list loaded", "success")
                    update_operation_status(f"All Projects page ready and loaded")
                    return True, hwnd
            
            # If context unknown, navigate
            if context == "unknown":
                print(f"⏳ [ALL_READY] Context unknown, navigating to all projects...")
                update_operation_status(f"Page context unknown, navigating to projects list...")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                continue
            
            # Not ready yet, wait and retry
            elapsed = int(time.time() - start_time)
            print(f"⏳ [ALL_READY] Waiting for page to be ready... ({elapsed}s)")
            hud.print(f"⏳ Loading... ({elapsed}s)", "waiting")
            update_operation_status(f"Loading All Projects page... ({elapsed}s elapsed)")
            time.sleep(1.0)
        
        print("❌ [ALL_READY] Timeout - attempting recovery...")
        hud.print("🔄 Attempting recovery...", "warning")
        error_msg = f"Timeout waiting for All Projects page after {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        fast_paste_url(hwnd, all_project_url)
        time.sleep(3)
        return wait_for_all_projects_page_ready(hwnd, all_project_url, project_title, timeout_seconds, depth + 1)

    def scroll_in_all_projects(hwnd, all_project_url, project_title, depth=0):
        """Scroll through All Projects page to find the project card with context analysis."""
        check_for_termination()
        print("⬇️ [SCROLL_ALL] Starting scroll in All Projects page...")
        hud.print("🔍 Searching for target...", "searching")
        update_operation_status(f"Searching for {project_title} in projects list...")
        
        if depth > 5:
            print("❌ [SCROLL_ALL] Max recursion depth reached - restarting")
            hud.print("🔄 Restarting search...", "warning")
            error_msg = f"Max recursion depth reached searching for {project_title}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, None, hwnd
        
        if not project_title or not project_title.strip():
            print("❌ [SCROLL_ALL] Project name is empty!")
            hud.print("❌ Project name missing", "error")
            error_msg = "Project title is empty or missing"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, None, hwnd
        
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        center_x = monitor_left + (monitor_right - monitor_left) // 2
        center_y = monitor_top + (monitor_bottom - monitor_top) // 2
        
        clean_project_title = clean_string_completely(project_title)
        print(f"🔍 [SCROLL_ALL] Searching for target project...")
        
        previous_fingerprint = ""
        scroll_attempts = 0
        max_scroll_attempts = 10
        scroll_direction = "down"
        down_scroll_complete = False
        recovery_attempts = 0
        
        while True:
            check_for_termination()
            
            if not enforce_window_focus(hwnd):
                print("🔄 [SCROLL_ALL] Window lost, reacquiring...")
                hwnd = ensure_window_ready_and_focused()
            
            # Analyze current page context
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, all_project_url, project_title
            )
            
            print(f"📊 [SCROLL_ALL] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
            
            # If on correct project page, we're done - return success with no card needed
            if on_project and project_found:
                print("✅ [SCROLL_ALL] Already on target project page - no card needed")
                hud.print("✅ Target located", "success")
                update_operation_status(f"Target {project_title} already located")
                return True, None, hwnd
            
            # If on wrong project page, navigate back
            if on_project and not project_found:
                print("⚠️ [SCROLL_ALL] On wrong project page - navigating back")
                hud.print("⚠️ Wrong project, navigating back...", "warning")
                update_operation_status(f"Wrong project detected, returning to projects list...")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                recovery_attempts += 1
                if recovery_attempts > 3:
                    print("🔄 [SCROLL_ALL] Too many recovery attempts, restarting...")
                    error_msg = f"Too many recovery attempts while searching for {project_title}"
                    update_operation_status(error_msg, is_error=True)
                    abort_operation(error_msg)
                    return scroll_in_all_projects(hwnd, all_project_url, project_title, depth + 1)
                continue
            
            # If context unknown, navigate
            if context == "unknown":
                print("⚠️ [SCROLL_ALL] Page context unknown - navigating to all projects")
                hud.print("⚠️ Page context lost, navigating...", "warning")
                update_operation_status(f"Page context lost, navigating to projects list...")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                continue
            
            # If not on all projects, navigate
            if not on_all:
                print("⚠️ [SCROLL_ALL] Not on all projects page - navigating...")
                update_operation_status(f"Not on All Projects page, navigating...")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                continue
            
            # Get current texts for searching
            current_texts = safe_ocr()
            
            # Search for project on current screen
            found_element = None
            for element in current_texts:
                if clean_project_title in clean_string_completely(element['text']):
                    # Verify this is a card element (not a header/button)
                    element_text = element['text'].lower()
                    # Skip if this is UI text that contains project name but isn't a card
                    if "new project" in element_text or "all media" in element_text:
                        continue
                    found_element = element
                    print(f"🎉 [SCROLL_ALL] Target card found at position ({element['left']}, {element['top']})")
                    hud.print("✅ Target located!", "success")
                    update_operation_status(f"Found {project_title} card in projects list")
                    return True, found_element, hwnd
            
            if not found_element:
                print(f"🔍 [SCROLL_ALL] Target not found on current screen")
            
            text_changed, current_fingerprint = verify_if_text_changes(current_texts, previous_fingerprint)
            
            if not text_changed:
                scroll_attempts += 1
                print(f"🔄 [SCROLL_ALL] No change detected - scroll attempt {scroll_attempts}/{max_scroll_attempts}")
                
                if scroll_attempts >= max_scroll_attempts:
                    if not down_scroll_complete:
                        print("⬆️ [SCROLL_ALL] Reached bottom, switching to scroll up...")
                        hud.print("⬆️ Reached bottom, scrolling up...", "navigating")
                        update_operation_status(f"Reached bottom, scrolling up to find {project_title}...")
                        scroll_direction = "up"
                        down_scroll_complete = True
                        scroll_attempts = 0
                        previous_fingerprint = ""
                        pyautogui.moveTo(center_x, center_y, duration=0)
                        pyautogui.scroll(5000)
                        time.sleep(2.0)
                        continue
                    else:
                        print("❌ [SCROLL_ALL] Target not found - refreshing and retrying...")
                        hud.print("🔄 Refreshing and retrying...", "warning")
                        error_msg = f"Could not find {project_title} in projects list after scrolling"
                        update_operation_status(error_msg, is_error=True)
                        fast_paste_url(hwnd, all_project_url)
                        time.sleep(3)
                        return scroll_in_all_projects(hwnd, all_project_url, project_title, depth + 1)
            else:
                scroll_attempts = 0
                previous_fingerprint = current_fingerprint
            
            if scroll_direction == "down":
                print("⬇️ [SCROLL_ALL] Scrolling down...")
                hud.print("⬇️ Scrolling...", "navigating")
                update_operation_status(f"Scrolling down through projects list...")
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(-500)
                time.sleep(1.5)
            else:
                print("⬆️ [SCROLL_ALL] Scrolling up...")
                hud.print("⬆️ Scrolling...", "navigating")
                update_operation_status(f"Scrolling up through projects list...")
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(500)
                time.sleep(1.5)

    def click_project_card(hwnd, card_element, all_project_url, project_title, depth=0):
        """Click on the project card with context analysis on each attempt."""
        check_for_termination()
        print("🎯 [CLICK] Clicking project card...")
        hud.print("🎯 Selecting target...", "selecting")
        update_operation_status(f"Selecting {project_title} from projects list...")
        
        if depth > 5:
            print("❌ [CLICK] Max recursion depth reached - restarting")
            hud.print("🔄 Restarting selection...", "warning")
            error_msg = f"Max recursion depth reached while selecting {project_title}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        # Analyze current page context
        on_all, on_project, project_found, context = analyze_current_page_context(
            hwnd, all_project_url, project_title
        )
        
        print(f"📊 [CLICK] Page context before click: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
        
        # If already on correct project page, we're done
        if on_project and project_found:
            print("✅ [CLICK] Already on target project page")
            hud.print("✅ Target selected", "success")
            update_operation_status(f"Already on {project_title} project page")
            return True, hwnd
        
        # If no card element provided, we need to find it
        if card_element is None:
            print("ℹ️ [CLICK] No card element provided - attempting to find it")
            update_operation_status(f"Locating {project_title} card...")
            
            # Try to find the card in current OCR
            current_texts = safe_ocr()
            clean_project_title = clean_string_completely(project_title)
            found_element = None
            
            for element in current_texts:
                if clean_project_title in clean_string_completely(element['text']):
                    element_text = element['text'].lower()
                    if "new project" not in element_text and "all media" not in element_text:
                        found_element = element
                        break
            
            if found_element:
                print(f"✅ [CLICK] Found card at position ({found_element['left']}, {found_element['top']})")
                card_element = found_element
            else:
                print("❌ [CLICK] Could not find card element")
                hud.print("❌ Cannot select - no card", "error")
                error_msg = f"Could not find {project_title} card to click"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return False, hwnd
        
        # Calculate click position
        click_x = int(card_element['left'] + (card_element['width'] / 2))
        click_y = int(card_element['top'] - 50)  # Click above the text to avoid text selection
        
        print(f"🎯 [CLICK] Selecting at position: ({click_x}, {click_y})")
        hud.print("📍 Selecting target...", "selecting")
        update_operation_status(f"Clicking on {project_title} card...")
        
        enforce_window_focus(hwnd)
        pyautogui.click(x=click_x, y=click_y)
        time.sleep(2)
        
        # Verify selection worked by analyzing context again
        on_all, on_project, project_found, context = analyze_current_page_context(
            hwnd, all_project_url, project_title
        )
        
        print(f"📊 [CLICK] Page context after click: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
        
        # CRITICAL: In SPA, the context might not change immediately
        # We need to check if we see "All Media" AND project name together (means we're on project page)
        if on_project and project_found:
            print("✅ [CLICK] Target selected successfully")
            hud.print("✅ Target opened", "success")
            update_operation_status(f"Successfully opened {project_title} project")
            return True, hwnd
        
        # If we're on all projects still, click might have failed or SPA didn't navigate
        if on_all:
            print("⚠️ [CLICK] Still on all projects page - trying click at different position")
            hud.print("⚠️ Retrying selection...", "warning")
            update_operation_status(f"Retrying selection of {project_title}...")
            
            # Try clicking on the actual text
            click_x_alt = int(card_element['left'] + (card_element['width'] / 2))
            click_y_alt = int(card_element['top'] + (card_element['height'] / 2))
            pyautogui.click(x=click_x_alt, y=click_y_alt)
            time.sleep(2)
            
            # Final verification
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, all_project_url, project_title
            )
            
            print(f"📊 [CLICK] Final context after retry: {context}, on_project={on_project}, project_found={project_found}")
            
            if on_project and project_found:
                print("✅ [CLICK] Target selected on retry")
                hud.print("✅ Target opened", "success")
                update_operation_status(f"Successfully opened {project_title} project on retry")
                return True, hwnd
        
        # If context unknown, navigate to all projects and retry
        if context == "unknown":
            print("⚠️ [CLICK] Page context unknown - navigating to all projects")
            update_operation_status(f"Page context lost, returning to projects list...")
            fast_paste_url(hwnd, all_project_url)
            time.sleep(3)
            return click_project_card(hwnd, card_element, all_project_url, project_title, depth + 1)
        
        print("❌ [CLICK] Failed to open target - restarting")
        hud.print("🔄 Restarting operation...", "warning")
        error_msg = f"Failed to open {project_title} project"
        update_operation_status(error_msg, is_error=True)
        abort_operation(error_msg)
        return click_project_card(hwnd, card_element, all_project_url, project_title, depth + 1)

    # ============================================
    # SECTION 4: SELF-HEALING HELPERS FOR SPECIFIC PROJECT PAGE
    # ============================================
    
    def specific_project_watchdog(hwnd, specific_url, project_title, depth=0):
        """Watchdog for Specific Project page with context analysis first."""
        check_for_termination()
        print("🛡️ [SPEC_WATCHDOG] Starting specific project watchdog...")
        hud.print("🔍 Analyzing page context...", "searching")
        update_operation_status(f"Analyzing page context for {project_title}...")
        
        if depth > 5:
            print("❌ [SPEC_WATCHDOG] Max recursion depth reached")
            hud.print("❌ Watchdog recursion limit", "error")
            error_msg = f"Max recursion depth reached in watchdog for {project_title}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, False, hwnd
        
        # Analyze current page context
        on_all, on_project, project_found, context = analyze_current_page_context(
            hwnd, specific_url, project_title
        )
        
        print(f"📊 [SPEC_WATCHDOG] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
        
        # If on project page
        if on_project:
            print("✅ [SPEC_WATCHDOG] On specific project page")
            hud.print("📋 On project page", "success")
            update_operation_status(f"Currently on {project_title} project page")
            
            if project_found:
                print("✅ [SPEC_WATCHDOG] Project verification successful")
                hud.print(f"✅ {project_title} verified", "success")
                update_operation_status(f"Successfully verified {project_title} project")
                return True, True, hwnd
            else:
                print(f"⚠️ [SPEC_WATCHDOG] On project page but target project not found")
                hud.print("⚠️ Project mismatch", "warning")
                error_msg = f"On project page but {project_title} not found"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return True, False, hwnd
        
        # If on all projects page, navigate to project
        if on_all:
            print("🔄 [SPEC_WATCHDOG] On all projects page - navigating to project")
            hud.print("🔄 Navigating to project...", "warning")
            update_operation_status(f"Navigating to {project_title} from projects list...")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return specific_project_watchdog(hwnd, specific_url, project_title, depth + 1)
        
        # If context unknown, navigate to project
        print("❌ [SPEC_WATCHDOG] Page context unknown - navigating to project")
        hud.print("❌ Page context unknown, navigating...", "error")
        update_operation_status(f"Page context unknown, navigating to {project_title}...")
        fast_paste_url(hwnd, specific_url)
        time.sleep(3)
        return specific_project_watchdog(hwnd, specific_url, project_title, depth + 1)

    def wait_for_specific_page_ready(hwnd, specific_url, project_title, timeout_seconds=60, depth=0):
        """Wait for Specific Project page to be ready with context analysis."""
        check_for_termination()
        print("⏳ [SPEC_READY] Waiting for project page to load...")
        hud.print("⏳ Loading project page...", "waiting")
        update_operation_status(f"Loading {project_title} project page...")
        
        if depth > 5:
            print("❌ [SPEC_READY] Max recursion depth reached")
            hud.print("❌ Page ready timeout", "error")
            error_msg = f"Max recursion depth reached waiting for {project_title} page"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, False, hwnd
        
        start_time = time.time()
        confirmation_text = "all media"
        clean_confirmation = clean_string_completely(confirmation_text)
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Analyze current page context
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, specific_url, project_title
            )
            
            print(f"📊 [SPEC_READY] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
            
            # If on all projects page, navigate to project
            if on_all:
                print("🔄 [SPEC_READY] On all projects page - navigating to project")
                update_operation_status(f"Navigating to {project_title} project...")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                continue
            
            # If not on project page and context unknown, navigate
            if not on_project and context == "unknown":
                print(f"⏳ [SPEC_READY] Context unknown, navigating to project...")
                update_operation_status(f"Page context unknown, navigating to {project_title}...")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                continue
            
            # If on project page, check for confirmation text
            if on_project:
                current_texts = safe_ocr()
                confirmation_found = False
                for element in current_texts:
                    if clean_confirmation in clean_string_completely(element['text']):
                        confirmation_found = True
                        break
                
                if confirmation_found:
                    print("✅ [SPEC_READY] Project page ready - confirmation text found")
                    hud.print("✅ Project page loaded", "success")
                    update_operation_status(f"{project_title} project page loaded successfully")
                    
                    # Verify project name
                    if project_found:
                        print(f"✅ [SPEC_READY] Target project confirmed on page")
                        update_operation_status(f"Successfully verified {project_title} project")
                        return True, True, hwnd
                    else:
                        print(f"⚠️ [SPEC_READY] Target project not found on page - will try to scroll")
                        update_operation_status(f"Searching for {project_title} on page...")
                        scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                            hwnd, specific_url, project_title, depth + 1
                        )
                        if found_after_scroll:
                            update_operation_status(f"Found {project_title} after scrolling")
                            return True, True, recovered_hwnd
                        error_msg = f"Could not find {project_title} on page after scrolling"
                        update_operation_status(error_msg, is_error=True)
                        abort_operation(error_msg)
                        return True, False, recovered_hwnd
            
            elapsed = int(time.time() - start_time)
            print(f"⏳ [SPEC_READY] Waiting for page to be ready... ({elapsed}s)")
            hud.print(f"⏳ Loading... ({elapsed}s)", "waiting")
            update_operation_status(f"Loading {project_title} project page... ({elapsed}s elapsed)")
            time.sleep(1.0)
        
        print("❌ [SPEC_READY] Timeout - attempting recovery...")
        hud.print("🔄 Attempting recovery...", "warning")
        error_msg = f"Timeout waiting for {project_title} page after {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        fast_paste_url(hwnd, specific_url)
        time.sleep(3)
        return wait_for_specific_page_ready(hwnd, specific_url, project_title, timeout_seconds, depth + 1)

    def scroll_in_specific_project(hwnd, specific_url, project_title, depth=0):
        """
        Scroll in Specific Project page with context analysis.
        Only scrolls up twice, then navigates back if not found.
        """
        check_for_termination()
        print("⬆️ [SCROLL_SPEC] Starting scroll in specific project page...")
        hud.print("🔍 Verifying project...", "searching")
        update_operation_status(f"Verifying {project_title} on project page...")
        
        if depth > 5:
            print("❌ [SCROLL_SPEC] Max recursion depth reached - navigating back")
            hud.print("🔄 Navigating back...", "warning")
            error_msg = f"Max recursion depth reached while verifying {project_title}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, False, hwnd
        
        if not project_title or not project_title.strip():
            print("❌ [SCROLL_SPEC] Project name is empty!")
            hud.print("❌ Project name missing", "error")
            error_msg = "Project title is empty or missing"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, False, hwnd
        
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        center_x = monitor_left + (monitor_right - monitor_left) // 2
        center_y = monitor_top + (monitor_bottom - monitor_top) // 2
        
        clean_project_title = clean_string_completely(project_title)
        print(f"🔍 [SCROLL_SPEC] Verifying target project...")
        
        # Analyze current page context
        on_all, on_project, project_found, context = analyze_current_page_context(
            hwnd, specific_url, project_title
        )
        
        print(f"📊 [SCROLL_SPEC] Initial context: {context}, on_project={on_project}, project_found={project_found}")
        
        # If on project page and project found, we're done
        if on_project and project_found:
            print("✅ [SCROLL_SPEC] Target project already visible")
            hud.print(f"✅ {project_title} verified", "success")
            update_operation_status(f"{project_title} verified successfully")
            return True, True, hwnd
        
        # If on all projects page, navigate to project
        if on_all:
            print("⚠️ [SCROLL_SPEC] On all projects page - navigating to project")
            hud.print("⚠️ Navigating to project...", "warning")
            update_operation_status(f"Navigating to {project_title} project...")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # If not on project page, navigate
        if not on_project:
            print("⚠️ [SCROLL_SPEC] Not on project page - navigating...")
            hud.print("⚠️ Navigating to project...", "warning")
            update_operation_status(f"Navigating to {project_title} project...")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # Target not found - perform up to 2 scrolls
        print("⬆️ [SCROLL_SPEC] Target not visible, scrolling up (max 2 attempts)...")
        hud.print("⬆️ Scrolling to locate target...", "navigating")
        update_operation_status(f"Scrolling to locate {project_title} on page...")
        
        max_scrolls = 2
        scroll_count = 0
        
        while scroll_count < max_scrolls:
            check_for_termination()
            
            if not enforce_window_focus(hwnd):
                print("🔄 [SCROLL_SPEC] Window lost, reacquiring...")
                hwnd = ensure_window_ready_and_focused()
            
            # Scroll up
            pyautogui.moveTo(center_x, center_y, duration=0)
            pyautogui.scroll(500)
            time.sleep(1.5)
            scroll_count += 1
            print(f"⬆️ [SCROLL_SPEC] Scroll {scroll_count}/{max_scrolls} completed")
            hud.print(f"⬆️ Scrolling... ({scroll_count}/{max_scrolls})", "navigating")
            update_operation_status(f"Scrolling to find {project_title} ({scroll_count}/{max_scrolls})...")
            
            # Analyze context after scroll
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, specific_url, project_title
            )
            
            print(f"📊 [SCROLL_SPEC] After scroll {scroll_count} context: {context}, on_project={on_project}, project_found={project_found}")
            
            # If project found, we're done
            if project_found:
                print(f"✅ [SCROLL_SPEC] Target found after scroll {scroll_count}")
                hud.print(f"✅ {project_title} verified", "success")
                update_operation_status(f"Found {project_title} after scrolling")
                return True, True, hwnd
            
            # If not on project page anymore, navigate back
            if not on_project:
                print("⚠️ [SCROLL_SPEC] Not on project page anymore - navigating back")
                hud.print("⚠️ Page context lost", "warning")
                update_operation_status(f"Page context lost, returning to project page...")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # After max scrolls, if not found, navigate back to all projects
        print("❌ [SCROLL_SPEC] Target not found after max scroll attempts - navigating back to all projects")
        hud.print("❌ Project not found, returning...", "error")
        error_msg = f"Could not find {project_title} on project page after scrolling"
        update_operation_status(error_msg, is_error=True)
        abort_operation(error_msg)
        fast_paste_url(hwnd, specific_url)
        time.sleep(3)
        return False, False, hwnd

    # ============================================
    # SECTION 5: VERTICAL DOT OPERATIONS WITH SELF-HEALING
    # ============================================
    
    def check_download_status(hwnd, timeout_seconds=300, check_interval=0.1):
        """
        Constantly checks download status with millisecond precision by monitoring:
        1. The "downloading items" text on screen
        2. Local file system for new .zip downloads (every 100ms)
        
        Now tracks existing files with timestamps to ensure we detect new files
        and confirms the downloaded file is different from previously noted files.
        
        When a new zip file is detected, it immediately signals for extraction.
        
        Args:
            hwnd: Window handle for focus management
            timeout_seconds: Maximum time to wait for download (default 5 minutes)
            check_interval: Seconds between checks (default 0.1 seconds - 100ms)
        
        Returns:
            tuple: (success, zip_file_path, zip_filename) or (False, None, None)
        """
        check_for_termination()
        print("📊 [DOWNLOAD_STATUS] Starting download status monitor with file tracking...")
        hud.print("📊 Monitoring download progress...", "waiting")
        update_operation_status(f"Monitoring download progress for {project_title}...")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Track existing zip files with their timestamps BEFORE download starts
        existing_zips = {}
        if os.path.exists(downloads_folder):
            try:
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.endswith('.zip'):
                            try:
                                # Get file stats for timestamp
                                stat = entry.stat()
                                # Use creation time on Windows, modification time on Unix
                                if os.name == 'nt':
                                    file_time = stat.st_ctime
                                else:
                                    file_time = stat.st_mtime
                                existing_zips[entry.name] = {
                                    'path': entry.path,
                                    'time': file_time,
                                    'size': stat.st_size
                                }
                            except Exception as e:
                                print(f"⚠️ [DOWNLOAD_STATUS] Could not get stats for {entry.name}: {e}")
                                existing_zips[entry.name] = {
                                    'path': entry.path,
                                    'time': 0,
                                    'size': 0
                                }
                print(f"📁 [DOWNLOAD_STATUS] Found {len(existing_zips)} existing .zip files with timestamps")
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_STATUS] Error scanning existing files: {e}")
        
        # Track the latest known zip file (for comparison)
        latest_known_zip = None
        latest_known_time = 0
        
        if existing_zips:
            # Find the latest existing zip by timestamp
            for name, info in existing_zips.items():
                if info['time'] > latest_known_time:
                    latest_known_time = info['time']
                    latest_known_zip = name
            print(f"📁 [DOWNLOAD_STATUS] Latest existing zip: {latest_known_zip} (time: {latest_known_time})")
        
        download_started = False
        downloading_active = False
        confirmation_waited = False
        previous_downloading_status = False
        new_zip_detected = False
        new_zip_path = None
        new_zip_name = None
        file_confirmed = False
        
        # For performance tracking
        last_status_update = 0
        status_update_interval = 2  # Update HUD every 2 seconds
        
        # Track the first detected new file to confirm it's different from latest known
        first_detected_new_file = None
        first_detected_time = 0
        
        # Start monitoring loop
        while time.time() - start_time < timeout_seconds:
            try:
                # Check for termination shortcut
                check_for_termination()
                
                # ============================================
                # PART 1: MONITOR FOR NEW ZIP FILES (FASTEST CHECK)
                # ============================================
                try:
                    if os.path.exists(downloads_folder):
                        # Use os.scandir for faster directory listing
                        with os.scandir(downloads_folder) as entries:
                            for entry in entries:
                                if entry.is_file() and entry.name.endswith('.zip'):
                                    # Check if this file is NOT in our existing zips
                                    if entry.name not in existing_zips:
                                        # Get file stats
                                        try:
                                            stat = entry.stat()
                                            if os.name == 'nt':
                                                file_time = stat.st_ctime
                                            else:
                                                file_time = stat.st_mtime
                                            file_size = stat.st_size
                                        except Exception:
                                            file_time = time.time()
                                            file_size = 0
                                        
                                        # ===== CONFIRMATION STEP: Ensure it's different from latest known =====
                                        is_different = True
                                        
                                        # Check if this file name was previously known
                                        if entry.name in existing_zips:
                                            existing_info = existing_zips[entry.name]
                                            # If the file already existed, check if it's the same file
                                            if existing_info['time'] == file_time and existing_info['size'] == file_size:
                                                is_different = False
                                                print(f"ℹ️ [DOWNLOAD_STATUS] File {entry.name} already existed (same file)")
                                        else:
                                            # New file name - confirm it's not just a renamed existing file
                                            # Check if any existing file has the same size and similar timestamp
                                            for existing_name, existing_info in existing_zips.items():
                                                # If size is similar and timestamp is within 2 seconds, it's likely the same file
                                                if abs(existing_info['size'] - file_size) < 1000:  # Within 1KB
                                                    time_diff = abs(existing_info['time'] - file_time)
                                                    if time_diff < 2.0:  # Within 2 seconds
                                                        is_different = False
                                                        print(f"ℹ️ [DOWNLOAD_STATUS] File {entry.name} appears to be same as {existing_name}")
                                                        break
                                        
                                        # If this is a new file and different from latest known, process it
                                        if is_different:
                                            # First detection of a new file
                                            if not new_zip_detected:
                                                print(f"🆕 [DOWNLOAD_STATUS] New zip file detected: {entry.name}")
                                                hud.print("🆕 New file detected", "info")
                                                update_operation_status(f"New zip file detected: {entry.name}")
                                                first_detected_new_file = entry.name
                                                first_detected_time = file_time
                                                
                                                # Wait for file to stabilize (multiple checks)
                                                stable_count = 0
                                                stable_size = 0
                                                max_stable_checks = 5
                                                
                                                print(f"⏳ [DOWNLOAD_STATUS] Waiting for file to stabilize...")
                                                while stable_count < 3 and stable_count < max_stable_checks:
                                                    try:
                                                        # Get file size
                                                        current_size = os.path.getsize(entry.path)
                                                        if current_size == stable_size and current_size > 0:
                                                            stable_count += 1
                                                            print(f"✅ [DOWNLOAD_STATUS] File stable ({stable_count}/3), size: {current_size} bytes")
                                                        else:
                                                            stable_count = 0
                                                            stable_size = current_size
                                                            print(f"⏳ [DOWNLOAD_STATUS] File size changing: {current_size} bytes")
                                                    except Exception:
                                                        pass
                                                    time.sleep(0.5)
                                                
                                                # File is stable - confirm it's different from latest known
                                                print(f"🔍 [DOWNLOAD_STATUS] Confirming file is different from latest known...")
                                                
                                                # Compare with latest known zip
                                                if latest_known_zip:
                                                    # Get info about the latest known file if it still exists
                                                    latest_known_path = os.path.join(downloads_folder, latest_known_zip)
                                                    if os.path.exists(latest_known_path):
                                                        try:
                                                            latest_stat = os.stat(latest_known_path)
                                                            if os.name == 'nt':
                                                                latest_time = latest_stat.st_ctime
                                                            else:
                                                                latest_time = latest_stat.st_mtime
                                                            latest_size = latest_stat.st_size
                                                            
                                                            # Check if new file is different
                                                            if abs(file_time - latest_time) < 1.0 and abs(file_size - latest_size) < 1000:
                                                                print(f"⚠️ [DOWNLOAD_STATUS] New file appears to be same as latest known: {latest_known_zip}")
                                                                print(f"   Latest time: {latest_time}, New time: {file_time}")
                                                                print(f"   Latest size: {latest_size}, New size: {file_size}")
                                                                # Wait for a different file
                                                                continue
                                                            else:
                                                                print(f"✅ [DOWNLOAD_STATUS] File confirmed different from latest known")
                                                                file_confirmed = True
                                                        except Exception as e:
                                                            print(f"⚠️ [DOWNLOAD_STATUS] Error comparing with latest known: {e}")
                                                            # If we can't compare, assume it's different
                                                            file_confirmed = True
                                                    else:
                                                        print(f"✅ [DOWNLOAD_STATUS] Latest known file no longer exists - new file is valid")
                                                        file_confirmed = True
                                                else:
                                                    print(f"✅ [DOWNLOAD_STATUS] No latest known file - new file is valid")
                                                    file_confirmed = True
                                                
                                                if file_confirmed:
                                                    new_zip_path = entry.path
                                                    new_zip_name = entry.name
                                                    new_zip_detected = True
                                                    print(f"✅ [DOWNLOAD_STATUS] File confirmed! Ready for extraction.")
                                                    hud.print(f"✅ File confirmed!", "success")
                                                    update_operation_status(f"Download complete: {entry.name}")
                                                    
                                                    # Add to existing zips to prevent re-detection
                                                    existing_zips[entry.name] = {
                                                        'path': entry.path,
                                                        'time': file_time,
                                                        'size': file_size
                                                    }
                                                    
                                                    # Update latest known
                                                    latest_known_zip = entry.name
                                                    latest_known_time = file_time
                                                    
                                                    # Return immediately with the zip file info
                                                    return True, new_zip_path, new_zip_name
                                                else:
                                                    print(f"ℹ️ [DOWNLOAD_STATUS] File not confirmed as new - waiting for different file")
                                                    # Reset detection state
                                                    new_zip_detected = False
                                                    first_detected_new_file = None
                                                    continue
                                            else:
                                                # Already detected a new file, continue monitoring for stability
                                                # But also check if there's a newer file
                                                try:
                                                    if os.path.exists(entry.path):
                                                        current_size = os.path.getsize(entry.path)
                                                        if current_size > 0:
                                                            new_zip_path = entry.path
                                                            new_zip_name = entry.name
                                                            print(f"✅ [DOWNLOAD_STATUS] Download complete! File ready: {entry.name}")
                                                            hud.print("✅ Download complete!", "success")
                                                            update_operation_status(f"Download complete: {entry.name}")
                                                            return True, new_zip_path, new_zip_name
                                                except Exception:
                                                    pass
                                else:
                                    # File exists in our tracking, check if it's updated (size changed)
                                    if entry.name in existing_zips:
                                        try:
                                            stat = entry.stat()
                                            current_size = stat.st_size
                                            existing_size = existing_zips[entry.name]['size']
                                            
                                            # If size changed significantly, it might be a new version
                                            if abs(current_size - existing_size) > 10000:  # More than 10KB difference
                                                if os.name == 'nt':
                                                    current_time = stat.st_ctime
                                                else:
                                                    current_time = stat.st_mtime
                                                
                                                print(f"🔄 [DOWNLOAD_STATUS] File {entry.name} updated! Size: {existing_size} → {current_size}")
                                                # Update tracking
                                                existing_zips[entry.name]['size'] = current_size
                                                existing_zips[entry.name]['time'] = current_time
                                                
                                                # Check if this update is different from latest known
                                                if latest_known_zip == entry.name:
                                                    # Update latest known time
                                                    latest_known_time = current_time
                                                    print(f"📁 [DOWNLOAD_STATUS] Updated latest known timestamp for {entry.name}")
                                        except Exception:
                                            pass
                                        
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_STATUS] Error checking for new zip: {e}")
                
                # ============================================
                # PART 2: MONITOR SCREEN FOR DOWNLOADING TEXT (FAST OCR)
                # ============================================
                # Ensure window has focus for accurate OCR
                enforce_window_focus(hwnd)
                
                # Get current screen text with fast OCR
                current_texts = safe_ocr()
                downloading_found = False
                
                # Search for "downloading items" or similar phrases
                if current_texts:
                    for element in current_texts:
                        element_text = element['text'].strip().lower()
                        if "downloading items" in element_text or "downloading" in element_text:
                            downloading_found = True
                            break
                
                # Track if download has started
                if downloading_found and not download_started:
                    download_started = True
                    downloading_active = True
                    elapsed = int(time.time() - start_time)
                    print(f"⏳ [DOWNLOAD_STATUS] Download started! ({elapsed}s elapsed)")
                    hud.print(f"📥 Downloading...", "downloading")
                    update_operation_status(f"Download started for {project_title}...")
                
                # Check if download is still active
                if download_started and not downloading_found and previous_downloading_status:
                    # Download text just disappeared - might be complete
                    if not confirmation_waited:
                        print("🔍 [DOWNLOAD_STATUS] 'Downloading' text disappeared - verifying completion...")
                        hud.print("🔍 Verifying download completion...", "verifying")
                        update_operation_status(f"Verifying download completion for {project_title}...")
                        confirmation_waited = True
                        
                        # Wait up to 5 seconds for zip to appear (checking every 100ms)
                        wait_start = time.time()
                        while time.time() - wait_start < 5:
                            try:
                                if os.path.exists(downloads_folder):
                                    with os.scandir(downloads_folder) as entries:
                                        for entry in entries:
                                            if entry.is_file() and entry.name.endswith('.zip'):
                                                if entry.name not in existing_zips:
                                                    # New zip found - confirm it's different
                                                    is_confirmed = True
                                                    if latest_known_zip and latest_known_zip == entry.name:
                                                        # Same name as latest known - check if it's actually different
                                                        try:
                                                            stat = entry.stat()
                                                            if os.name == 'nt':
                                                                file_time = stat.st_ctime
                                                            else:
                                                                file_time = stat.st_mtime
                                                            if abs(file_time - latest_known_time) < 1.0:
                                                                is_confirmed = False
                                                                print(f"ℹ️ [DOWNLOAD_STATUS] File {entry.name} is same as latest known (time diff < 1s)")
                                                        except Exception:
                                                            pass
                                                    
                                                    if is_confirmed:
                                                        new_zip_path = entry.path
                                                        new_zip_name = entry.name
                                                        new_zip_detected = True
                                                        print(f"✅ [DOWNLOAD_STATUS] New zip file found and confirmed: {entry.name}")
                                                        hud.print("✅ Download confirmed!", "success")
                                                        update_operation_status(f"Download confirmed: {entry.name}")
                                                        
                                                        # Update tracking
                                                        try:
                                                            stat = entry.stat()
                                                            if os.name == 'nt':
                                                                file_time = stat.st_ctime
                                                            else:
                                                                file_time = stat.st_mtime
                                                            existing_zips[entry.name] = {
                                                                'path': entry.path,
                                                                'time': file_time,
                                                                'size': stat.st_size
                                                            }
                                                            latest_known_zip = entry.name
                                                            latest_known_time = file_time
                                                        except Exception:
                                                            pass
                                                        
                                                        return True, new_zip_path, new_zip_name
                            except Exception as e:
                                print(f"⚠️ [DOWNLOAD_STATUS] Error checking during wait: {e}")
                            time.sleep(0.1)  # Check every 100ms during confirmation
                        
                        # If we get here, no zip found yet - continue monitoring
                        print("⏳ [DOWNLOAD_STATUS] No zip found yet, continuing monitoring...")
                        hud.print("⏳ Waiting for zip file...", "waiting")
                        update_operation_status(f"Waiting for download to complete...")
                
                # Handle active downloading state
                if downloading_found:
                    downloading_active = True
                    previous_downloading_status = True
                    elapsed = int(time.time() - start_time)
                    
                    # Update status every 2 seconds (less frequent to reduce overhead)
                    if elapsed % 2 == 0 and elapsed > 0 and elapsed != last_status_update:
                        last_status_update = elapsed
                        print(f"⏳ [DOWNLOAD_STATUS] Downloading... ({elapsed}s elapsed)")
                        hud.print(f"📥 Downloading...", "downloading")
                        update_operation_status(f"Downloading {project_title}... ({elapsed}s elapsed)")
                else:
                    if download_started and not confirmation_waited and downloading_active:
                        # Download text disappeared but we haven't waited yet
                        pass
                    elif download_started and not confirmation_waited:
                        # Download hasn't started yet, text not visible
                        pass
                    else:
                        previous_downloading_status = False
                
                # Update status text for user (every 2 seconds)
                if not download_started:
                    elapsed = int(time.time() - start_time)
                    if elapsed % 2 == 0 and elapsed > 0 and elapsed != last_status_update:
                        last_status_update = elapsed
                        hud.print(f"⏳ Waiting for download to start... ({elapsed}s)", "waiting")
                        update_operation_status(f"Waiting for download to start... ({elapsed}s elapsed)")
                
                # ============================================
                # PART 3: PERIODIC MODAL CHECK
                # ============================================
                # Check for download modal every 10 seconds
                if int(time.time()) % 10 == 0:
                    try:
                        hwnd = dismiss_download_modal_if_present(hwnd)
                    except Exception:
                        pass
                
                # Sleep before next check (millisecond precision)
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("🛑 [DOWNLOAD_STATUS] Download monitoring interrupted by user")
                raise
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_STATUS] Error in monitoring loop: {e}")
                time.sleep(check_interval)
                continue
        
        # Timeout reached - check one more time for any zip
        print(f"⏰ [DOWNLOAD_STATUS] Timeout reached after {timeout_seconds} seconds")
        error_msg = f"Download timed out after {timeout_seconds} seconds"
        hud.print("⏰ Download monitoring timed out", "error")
        update_operation_status(error_msg, is_error=True)
        
        try:
            if os.path.exists(downloads_folder):
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.endswith('.zip'):
                            if entry.name not in existing_zips:
                                # Check if it's different from latest known
                                is_confirmed = True
                                if latest_known_zip and latest_known_zip == entry.name:
                                    try:
                                        stat = entry.stat()
                                        if os.name == 'nt':
                                            file_time = stat.st_ctime
                                        else:
                                            file_time = stat.st_mtime
                                        if abs(file_time - latest_known_time) < 1.0:
                                            is_confirmed = False
                                    except Exception:
                                        pass
                                
                                if is_confirmed:
                                    new_zip_path = entry.path
                                    new_zip_name = entry.name
                                    print(f"✅ [DOWNLOAD_STATUS] Found zip after timeout: {entry.name}")
                                    hud.print("✅ Download confirmed (late detection)!", "success")
                                    update_operation_status(f"Download confirmed (late detection): {entry.name}")
                                    
                                    # Dismiss modal after timeout detection
                                    try:
                                        hwnd = dismiss_download_modal_if_present(hwnd)
                                    except Exception:
                                        pass
                                    
                                    return True, new_zip_path, new_zip_name
        except Exception:
            pass
        
        # If we still have a download in progress but no file, treat as failure
        abort_operation(f"Download for {project_title} failed - no zip file found")
        return False, None, None

    def extract_zip_to_images(zip_file_path, zip_filename, project_title, hwnd=None, expected_images=None):
        """
        Extracts the provided zip file to the IMAGES_PATH directory,
        separates images and videos into subfolders (flattened, no subfolders),
        and renames the parent folder to the normalized project name.
        
        If the project folder already exists, it will be deleted before extraction.
        
        Now dismisses the download modal after extraction completes and validates
        the number of extracted images against expected count.
        
        Args:
            zip_file_path: Full path to the zip file
            zip_filename: Name of the zip file
            project_title: Original project name to normalize and use for folder name
            hwnd: Window handle for modal dismissal (optional)
            expected_images: Expected number of images (optional). If provided, validates count.
        
        Returns:
            tuple: (success, image_count, video_count) or (False, 0, 0)
        """
        check_for_termination()
        print(f"📦 [EXTRACT] Starting extraction of: {zip_filename}")
        hud.print(f"📦 Extracting {zip_filename}...", "processing")
        update_operation_status(f"Extracting {zip_filename} for {project_title}...")
        
        # Normalize project name - remove special characters, keep alphanumeric and underscore
        def normalize_project_title(name):
            if not name:
                return "unnamed_project"
            # Remove special characters but keep alphanumeric, spaces, and underscores
            normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
            # Replace spaces with underscores
            normalized = re.sub(r'\s+', '_', normalized)
            # Remove multiple underscores
            normalized = re.sub(r'_+', '_', normalized)
            # Remove leading/trailing underscores
            normalized = normalized.strip('_')
            return normalized if normalized else "unnamed_project"
        
        # Normalize the project name
        normalized_project_title = normalize_project_title(project_title)
        print(f"📝 [EXTRACT] Normalized project name: '{normalized_project_title}'")
        
        images_path = IMAGES_PATH
        
        # Ensure images path exists
        if not os.path.exists(images_path):
            try:
                os.makedirs(images_path)
                print(f"📁 [EXTRACT] Created images directory: {images_path}")
            except Exception as e:
                print(f"❌ [EXTRACT] Failed to create images directory: {e}")
                hud.print("❌ Failed to create images directory", "error")
                error_msg = f"Failed to create images directory: {e}"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return False, 0, 0
        
        # Verify zip file exists and is readable
        if not os.path.exists(zip_file_path):
            print(f"❌ [EXTRACT] Zip file not found: {zip_file_path}")
            hud.print("❌ Zip file not found", "error")
            error_msg = f"Zip file not found: {zip_filename}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, 0, 0
        
        # Wait for file to stabilize (check size)
        print("⏳ [EXTRACT] Waiting for file to stabilize...")
        stable_count = 0
        previous_size = -1
        max_stable_checks = 5
        while stable_count < 3 and stable_count < max_stable_checks:
            try:
                current_size = os.path.getsize(zip_file_path)
                if current_size == previous_size:
                    stable_count += 1
                else:
                    stable_count = 0
                    previous_size = current_size
                    print(f"⏳ [EXTRACT] File size: {current_size} bytes, waiting to stabilize...")
                    time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ [EXTRACT] Error checking file size: {e}")
                time.sleep(0.5)
        
        print(f"✅ [EXTRACT] Zip file stable at {previous_size} bytes")
        
        # Define extraction target path
        target_folder = os.path.join(images_path, normalized_project_title)
        
        # Check if folder already exists - DELETE IT if it does
        if os.path.exists(target_folder):
            print(f"🗑️ [EXTRACT] Project folder already exists, deleting: {target_folder}")
            hud.print(f"🗑️ Removing existing project folder...", "warning")
            update_operation_status(f"Removing existing project folder for {project_title}...")
            
            try:
                # Use shutil.rmtree to delete the entire folder and its contents
                import shutil
                shutil.rmtree(target_folder)
                print(f"✅ [EXTRACT] Successfully deleted existing project folder")
                hud.print("✅ Removed existing folder", "info")
                update_operation_status(f"Removed existing folder for {project_title}")
            except Exception as e:
                print(f"❌ [EXTRACT] Failed to delete existing folder: {e}")
                hud.print("❌ Could not delete existing folder", "error")
                
                # Try to rename as backup instead
                try:
                    backup_counter = 1
                    backup_folder = f"{target_folder}_backup_{backup_counter}"
                    while os.path.exists(backup_folder):
                        backup_counter += 1
                        backup_folder = f"{target_folder}_backup_{backup_counter}"
                    
                    os.rename(target_folder, backup_folder)
                    print(f"📁 [EXTRACT] Renamed existing folder to: {backup_folder}")
                    hud.print(f"📁 Backup created: {os.path.basename(backup_folder)}", "info")
                    update_operation_status(f"Created backup: {os.path.basename(backup_folder)}")
                except Exception as e2:
                    print(f"❌ [EXTRACT] Failed to rename folder, aborting: {e2}")
                    hud.print("❌ Cannot proceed", "error")
                    error_msg = f"Failed to remove or backup existing folder: {e2}"
                    update_operation_status(error_msg, is_error=True)
                    abort_operation(error_msg)
                    return False, 0, 0
        
        # Extract the zip file to a temporary location first
        temp_extract_folder = target_folder + "_temp"
        try:
            print(f"📦 [EXTRACT] Extracting to temporary location: {temp_extract_folder}")
            hud.print("📦 Extracting files...", "processing")
            update_operation_status(f"Extracting files for {project_title}...")
            
            # Create temporary extraction folder
            if not os.path.exists(temp_extract_folder):
                os.makedirs(temp_extract_folder)
            
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # Get list of files in zip
                file_list = zip_ref.namelist()
                print(f"📄 [EXTRACT] Zip contains {len(file_list)} items")
                
                # Extract all files to temporary location
                zip_ref.extractall(temp_extract_folder)
            
            print(f"✅ [EXTRACT] Successfully extracted to temporary location")
            
            # Define image and video extensions
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico', '.psd', '.ai', '.eps'}
            video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogg', '.ogv'}
            
            # Create subfolders (flat structure - no subfolders inside)
            images_subfolder = os.path.join(target_folder, "images")
            videos_subfolder = os.path.join(target_folder, "videos")
            
            os.makedirs(images_subfolder, exist_ok=True)
            os.makedirs(videos_subfolder, exist_ok=True)
            
            print(f"📁 [EXTRACT] Created folders:")
            print(f"   📁 Images: {images_subfolder}")
            print(f"   📁 Videos: {videos_subfolder}")
            
            # Walk through the extracted files and sort them (flattened)
            image_count = 0
            video_count = 0
            other_count = 0
            
            # Store image files for validation
            image_files = []
            
            for root, dirs, files in os.walk(temp_extract_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # Check if file is an image
                    if file_ext in image_extensions:
                        # Handle duplicate filenames
                        base_name = file
                        dest_path = os.path.join(images_subfolder, base_name)
                        
                        # If file already exists, add a number suffix
                        counter = 1
                        while os.path.exists(dest_path):
                            name_without_ext = os.path.splitext(base_name)[0]
                            ext = os.path.splitext(base_name)[1]
                            new_name = f"{name_without_ext}_{counter}{ext}"
                            dest_path = os.path.join(images_subfolder, new_name)
                            counter += 1
                        
                        try:
                            # Move the file (flattened, no subfolders)
                            os.rename(file_path, dest_path)
                            image_count += 1
                            image_files.append(dest_path)
                        except Exception as e:
                            print(f"⚠️ [EXTRACT] Could not move image {file}: {e}")
                            # Copy instead of move
                            import shutil
                            shutil.copy2(file_path, dest_path)
                            image_count += 1
                            image_files.append(dest_path)
                    
                    # Check if file is a video
                    elif file_ext in video_extensions:
                        # Handle duplicate filenames
                        base_name = file
                        dest_path = os.path.join(videos_subfolder, base_name)
                        
                        # If file already exists, add a number suffix
                        counter = 1
                        while os.path.exists(dest_path):
                            name_without_ext = os.path.splitext(base_name)[0]
                            ext = os.path.splitext(base_name)[1]
                            new_name = f"{name_without_ext}_{counter}{ext}"
                            dest_path = os.path.join(videos_subfolder, new_name)
                            counter += 1
                        
                        try:
                            # Move the file (flattened, no subfolders)
                            os.rename(file_path, dest_path)
                            video_count += 1
                        except Exception as e:
                            print(f"⚠️ [EXTRACT] Could not move video {file}: {e}")
                            # Copy instead of move
                            import shutil
                            shutil.copy2(file_path, dest_path)
                            video_count += 1
                    
                    # Other files (keep in root)
                    else:
                        # Handle duplicate filenames
                        base_name = file
                        dest_path = os.path.join(target_folder, base_name)
                        
                        # If file already exists, add a number suffix
                        counter = 1
                        while os.path.exists(dest_path):
                            name_without_ext = os.path.splitext(base_name)[0]
                            ext = os.path.splitext(base_name)[1]
                            new_name = f"{name_without_ext}_{counter}{ext}"
                            dest_path = os.path.join(target_folder, new_name)
                            counter += 1
                        
                        try:
                            os.rename(file_path, dest_path)
                            other_count += 1
                        except Exception as e:
                            print(f"⚠️ [EXTRACT] Could not move file {file}: {e}")
                            import shutil
                            shutil.copy2(file_path, dest_path)
                            other_count += 1
            
            # Remove empty directories from temp folder
            try:
                import shutil
                shutil.rmtree(temp_extract_folder)
                print(f"🗑️ [EXTRACT] Removed temporary extraction folder")
            except Exception as e:
                print(f"⚠️ [EXTRACT] Could not remove temp folder: {e}")
            
            # Print summary
            print(f"📊 [EXTRACT] File organization summary:")
            print(f"   🖼️ Images: {image_count} files → {images_subfolder}")
            print(f"   🎬 Videos: {video_count} files → {videos_subfolder}")
            print(f"   📄 Other: {other_count} files → {target_folder}")
            
            hud.print(f"✅ Extracted: {image_count} images, {video_count} videos", "success")
            update_operation_status(f"Extracted {image_count} images and {video_count} videos for {project_title}")
            
            # Clean up: remove the zip file after successful extraction
            try:
                os.remove(zip_file_path)
                print(f"🗑️ [EXTRACT] Removed zip file: {zip_filename}")
            except Exception as e:
                print(f"⚠️ [EXTRACT] Could not remove zip file: {e}")
            
            # ===== VALIDATE IMAGE COUNT AGAINST EXPECTED =====
            if expected_images is not None:
                print(f"🔍 [EXTRACT] Validating image count against expected: {expected_images}")
                update_operation_status(f"Validating image count: expected {expected_images}, extracted {image_count}...")
                
                if image_count != expected_images:
                    print(f"❌ [EXTRACT] Image count mismatch! Expected: {expected_images}, Actual: {image_count}")
                    hud.print(f"❌ Image count mismatch: {image_count} vs {expected_images}", "error")
                    
                    # ===== ABORT OPERATION =====
                    abort_operation(f"Image count mismatch for {project_title}: Expected {expected_images}, got {image_count}")
                    return False, image_count, video_count
                else:
                    print(f"✅ [EXTRACT] Image count validation passed: {image_count} images")
                    hud.print(f"✅ Image count validated: {image_count}", "success")
                    update_operation_status(f"Image count validation passed: {image_count} images")
            
            # ===== Dismiss download modal after extraction completes =====
            if hwnd is not None:
                try:
                    print(f"🔍 [EXTRACT] Dismissing download modal...")
                    hwnd = dismiss_download_modal_if_present(hwnd)
                    print(f"✅ [EXTRACT] Download modal dismissed")
                except Exception as e:
                    print(f"⚠️ [EXTRACT] Could not dismiss modal: {e}")
            
            return True, image_count, video_count
                
        except zipfile.BadZipFile:
            print(f"❌ [EXTRACT] Corrupt or invalid zip file: {zip_file_path}")
            hud.print("❌ Invalid zip file", "error")
            error_msg = f"Corrupt or invalid zip file: {zip_filename}"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            # Clean up temp folder if it exists
            try:
                import shutil
                if os.path.exists(temp_extract_folder):
                    shutil.rmtree(temp_extract_folder)
            except:
                pass
            return False, 0, 0
        except Exception as e:
            if "LargeZipFile" in str(type(e)):
                print(f"❌ [EXTRACT] Zip file too large (requires ZIP64): {zip_file_path}")
                hud.print("❌ Zip too large", "error")
                error_msg = f"Zip file too large (ZIP64 required): {zip_filename}"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
            else:
                print(f"❌ [EXTRACT] Unexpected error during extraction: {e}")
                hud.print(f"❌ Extraction error: {str(e)[:30]}...", "error")
                error_msg = f"Extraction error: {str(e)}"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
            
            # Clean up temp folder if it exists
            try:
                import shutil
                if os.path.exists(temp_extract_folder):
                    shutil.rmtree(temp_extract_folder)
            except:
                pass
            return False, 0, 0
     
    def find_and_click_vertical_dot(hwnd, specific_url, project_title, depth=0, expected_images=None):
        """Searches for vertical dot menu and initiates download with context analysis."""
        try:
            check_for_termination()
            if depth > 5:
                print("❌ [DOT] Max recursion depth reached - restarting")
                hud.print("🔄 Restarting operation...", "warning")
                error_msg = f"Max recursion depth reached while initiating download for {project_title}"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return False
            
            print("🔘 [DOT] Starting download sequence...")
            update_operation_status(f"Initiating download for {project_title}...")
            
            # Analyze current page context
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, specific_url, project_title
            )
            
            print(f"📊 [DOT] Initial context: {context}, on_project={on_project}, project_found={project_found}")
            
            # If not on project page, navigate
            if not on_project:
                print("❌ [DOT] Not on project page - navigating...")
                hud.print("❌ Navigating to project...", "error")
                update_operation_status(f"Not on {project_title} page, navigating...")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            # If on wrong project, navigate
            if on_project and not project_found:
                print("❌ [DOT] Project name not found - navigating back")
                hud.print("❌ Project mismatch, navigating...", "error")
                error_msg = f"Project name mismatch: {project_title} not found on page"
                update_operation_status(error_msg, is_error=True)
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            enforce_window_focus(hwnd)
            
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            right_half_left = screen_width // 2
            region_left = right_half_left
            region_top = 0
            region_width = screen_width // 2
            region_height = screen_height // 2
            
            print(f"📐 [DOT] Screen size: {screen_width}x{screen_height}")
            print(f"📐 [DOT] Search region: left={region_left}, top={region_top}, width={region_width}, height={region_height}")
            
            region = (region_left, region_top, region_width, region_height)
            
            dot_1_path = os.path.join(GUI_IMAGE_PATH, "vertical_dot_1.png")
            dot_2_path = os.path.join(GUI_IMAGE_PATH, "vertical_dot_2.png")
            
            found_location = None
            used_image = None
            
            if not os.path.exists(dot_1_path) and not os.path.exists(dot_2_path):
                print("❌ [WATCHDOG] No vertical dot images found")
                hud.print("❌ UI images missing", "error")
                error_msg = "Vertical dot UI images not found"
                update_operation_status(error_msg, is_error=True)
                abort_operation(error_msg)
                return False
            
            if os.path.exists(dot_1_path):
                print(f"🔍 [DOT] Trying to find vertical_dot_1.png...")
                try:
                    found_location = pyautogui.locateCenterOnScreen(
                        dot_1_path, 
                        region=region,
                        confidence=0.8,
                        grayscale=False
                    )
                    if found_location:
                        used_image = "vertical_dot_1.png"
                        print(f"✅ [DOT] Found at location: {found_location}")
                except Exception as e:
                    print(f"⚠️ [DOT] Error searching: {e}")
            
            if not found_location and os.path.exists(dot_2_path):
                print(f"🔍 [DOT] Falling back to vertical_dot_2.png...")
                try:
                    found_location = pyautogui.locateCenterOnScreen(
                        dot_2_path, 
                        region=region,
                        confidence=0.8,
                        grayscale=False
                    )
                    if found_location:
                        used_image = "vertical_dot_2.png"
                        print(f"✅ [DOT] Found at location: {found_location}")
                except Exception as e:
                    print(f"⚠️ [DOT] Error searching: {e}")
            
            if not found_location:
                print("❌ [DOT] Could not find vertical dot - scrolling to find it")
                hud.print("⬆️ Scrolling to find menu...", "navigating")
                update_operation_status(f"Scrolling to find menu for {project_title}...")
                current_monitor = get_current_monitor()
                monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
                center_x = monitor_left + (monitor_right - monitor_left) // 2
                center_y = monitor_top + (monitor_bottom - monitor_top) // 2
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(-300)
                time.sleep(1)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            x, y = found_location
            print(f"🎯 [DOT] Selecting at position ({x}, {y})")
            update_operation_status(f"Found menu for {project_title}, clicking...")
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            time.sleep(0.5)
            
            print(f"✅ [DOT] Successfully selected using {used_image}")
            
            print("📥 [DOWNLOAD] Looking for download option...")
            download_found = False
            download_click_position = None
            
            for attempt in range(10):
                check_for_termination()
                
                if not enforce_window_focus(hwnd):
                    print(f"⚠️ [WATCHDOG] Window lost focus during download search (attempt {attempt+1})")
                    hwnd = ensure_window_ready_and_focused()
                    continue
                
                current_texts = safe_ocr()
                
                if not current_texts:
                    print(f"⚠️ [WATCHDOG] No text found during download search (attempt {attempt+1})")
                    time.sleep(0.5)
                    continue
                
                for element in current_texts:
                    element_text = element['text'].strip().lower()
                    if "download project" in element_text or ("download" in element_text and "project" in element_text):
                        download_found = True
                        click_x = int(element['left'] + element['width'] / 2)
                        click_y = int(element['top'] + element['height'] / 2)
                        download_click_position = (click_x, click_y)
                        print(f"📥 [DOWNLOAD] Found download option at: ({click_x}, {click_y})")
                        break
                
                if download_found and download_click_position:
                    break
                
                time.sleep(0.5)
                print(f"⏳ [DOWNLOAD] Retry {attempt + 1}/10...")
                hud.print(f"⏳ Searching...", "waiting")
                update_operation_status(f"Searching for download option for {project_title}... (attempt {attempt + 1}/10)")
            
            if not download_found or not download_click_position:
                print("❌ [DOWNLOAD] Could not find download option - retrying")
                hud.print("🔄 Retrying download search...", "warning")
                error_msg = f"Could not find download option for {project_title}"
                update_operation_status(error_msg, is_error=True)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            click_x, click_y = download_click_position
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before download selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
            
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            pyautogui.click()
            time.sleep(0.5)
            
            print("📊 [DOWNLOAD] Starting download status monitoring...")
            update_operation_status(f"Download initiated for {project_title}, monitoring progress...")
            
            # Use the updated download status checker - returns (success, zip_path, zip_name)
            download_successful, zip_file_path, zip_filename = check_download_status(
                hwnd, timeout_seconds=300, check_interval=0.1
            )
            
            if download_successful and zip_file_path and zip_filename:
                print("🎉 [DOWNLOAD] Download completed successfully!")
                hud.print("✅ Download completed!", "success")
                update_operation_status(f"Download completed successfully for {project_title}")
                
                # Now extract the zip file immediately - PASS HWND AND EXPECTED IMAGES FOR VALIDATION
                print("📦 [EXTRACT] Starting zip extraction...")
                extraction_successful, image_count, video_count = extract_zip_to_images(
                    zip_file_path, zip_filename, project_title, hwnd, expected_images
                )
                
                if extraction_successful:
                    print("🎉 [COMPLETE] Operation fully completed - Download and extraction successful!")
                    hud.print("✅ Complete - Project extracted!", "success")
                    
                    # Report final counts
                    if expected_images is not None:
                        print(f"📊 [SUMMARY] Images: {image_count}/{expected_images} (expected)")
                    else:
                        print(f"📊 [SUMMARY] Images: {image_count}, Videos: {video_count}")
                    
                    update_operation_status(f"Successfully processed {project_title}: {image_count} images, {video_count} videos")
                    return True
                else:
                    print("⚠️ [COMPLETE] Download completed but extraction failed")
                    hud.print("⚠️ Download OK, extraction failed", "warning")
                    # Return True anyway since download succeeded
                    update_operation_status(f"Download completed but extraction failed for {project_title}", is_error=True)
                    return True
            else:
                print("⚠️ [DOWNLOAD] Download status check timed out or failed")
                hud.print("⚠️ Download status uncertain", "warning")
                error_msg = f"Download for {project_title} timed out or failed"
                update_operation_status(error_msg, is_error=True)
                return False
                
        except Exception as e:
            print(f"❌ [DOT] Error: {e}")
            hud.print(f"❌ Error occurred, retrying...", "error")
            error_msg = f"Error in download sequence: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            print("🔄 [DOT] Attempting recovery...")
            hwnd = ensure_window_ready_and_focused()
            return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1, expected_images)
    
    def dismiss_download_modal_if_present(hwnd):
        """
        Check if download modal is present by looking for downloads icon.
        Searches in the upper half of the screen.
        If found, click on it to dismiss the modal.
        """
        check_for_termination()
        print(f"🔍 [MODAL] Checking for download modal using icon recognition...")
        
        # Define paths to download icon images
        downloads_icon1_path = os.path.join(GUI_IMAGE_PATH, "downloads_icon1.png")
        downloads_icon2_path = os.path.join(GUI_IMAGE_PATH, "downloads_icon2.png")
        
        # Check if image files exist
        if not os.path.exists(downloads_icon1_path) and not os.path.exists(downloads_icon2_path):
            print("ℹ️ [MODAL] No download icon images found - skipping modal check")
            return hwnd
        
        # Get current monitor bounds
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        monitor_width = monitor_right - monitor_left
        monitor_height = monitor_bottom - monitor_top
        
        # Search only in the upper half of the screen
        region_left = monitor_left
        region_top = monitor_top
        region_width = monitor_width
        region_height = monitor_height // 2
        
        region = (region_left, region_top, region_width, region_height)
        
        print(f"📐 [MODAL] Searching for downloads icon in upper half: {region}")
        
        # Try to find the icon
        icon_found = False
        
        # Try downloads_icon1.png first
        if os.path.exists(downloads_icon1_path):
            try:
                found_location = pyautogui.locateCenterOnScreen(
                    downloads_icon1_path,
                    region=region,
                    confidence=0.8,
                    grayscale=False
                )
                
                if found_location:
                    x, y = found_location
                    print(f"✅ [MODAL] Found downloads_icon1.png at position ({x}, {y})")
                    icon_found = True
                    
                    # Click the icon
                    enforce_window_focus(hwnd)
                    pyautogui.moveTo(x, y, duration=0.2)
                    pyautogui.click()
                    time.sleep(0.3)
                    
                    print(f"✅ [MODAL] Clicked downloads icon to dismiss modal")
                    hud.print("✅ Modal dismissed", "success")
                    update_operation_status(f"Dismissed download modal")
                    return hwnd
            except Exception as e:
                print(f"⚠️ [MODAL] Error searching for downloads_icon1.png: {e}")
        
        # Try downloads_icon2.png if first wasn't found
        if not icon_found and os.path.exists(downloads_icon2_path):
            try:
                found_location = pyautogui.locateCenterOnScreen(
                    downloads_icon2_path,
                    region=region,
                    confidence=0.8,
                    grayscale=False
                )
                
                if found_location:
                    x, y = found_location
                    print(f"✅ [MODAL] Found downloads_icon2.png at position ({x}, {y})")
                    icon_found = True
                    
                    # Click the icon
                    enforce_window_focus(hwnd)
                    pyautogui.moveTo(x, y, duration=0.2)
                    pyautogui.click()
                    time.sleep(0.3)
                    
                    print(f"✅ [MODAL] Clicked downloads icon to dismiss modal")
                    hud.print("✅ Modal dismissed", "success")
                    update_operation_status(f"Dismissed download modal")
                    return hwnd
            except Exception as e:
                print(f"⚠️ [MODAL] Error searching for downloads_icon2.png: {e}")
        
        if not icon_found:
            print(f"ℹ️ [MODAL] No downloads icon found - no modal to dismiss")
        
        return hwnd
      
    # ============================================
    # SECTION 6: MAIN EXECUTION FLOW - NEVER EXITS UNLESS CRITICAL
    # ============================================
    def perform_navigation_and_restart(hwnd, url, operation_name="navigation"):
        """Perform navigation and then restart the entire operation from beginning"""
        print(f"🔄 [RESTART] {operation_name} - navigating to {url} and restarting operation")
        hud.print(f"🔄 Restarting operation after {operation_name}...", "warning")
        update_operation_status(f"Restarting operation after {operation_name}...")
        
        # Navigate to the destination
        fast_paste_url(hwnd, url)
        time.sleep(3)
        
        # Ensure window is ready after navigation
        hwnd = ensure_window_ready_and_focused()
        
        # CRITICAL: Restart the entire operation by calling main()
        print(f"🔄 [RESTART] Operation restarting from beginning after {operation_name}")
        hud.print("🔄 Operation restarting...", "warning")
        update_operation_status(f"Operation restarting after {operation_name}")
        time.sleep(1)
        
        # Call main() to restart the entire workflow
        main()
        return  # This will never be reached if main() runs properly
        
    def main():
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
        
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # ===== CHECK IF OPERATION WAS ALREADY ABORTED =====
            existing_status = panel_data.get('operation_status', '')
            
            # Check if the existing status contains abortion indicators
            if 'aborting' in existing_status.lower() or 'aborted' in existing_status.lower():
                print(f"🛑 [SYNC] Operation was previously aborted: '{existing_status}'")
                print(f"🛑 [SYNC] Skipping Google Flow operation to maintain sync")
                hud.print("🛑 Operation was aborted - skipping", "error")
                update_operation_status("Operation was previously aborted - skipping Google Flow", is_abort=True)
                return
            
            # Get google_flow_config
            google_flow_config = panel_data.get('google_flow_config', {})
            
            # Check if Google Flow operation is enabled
            operate_google_flow = google_flow_config.get('operate_google_flow', False)
            if not operate_google_flow:
                print("ℹ️ Google Flow operation is disabled in config")
                hud.print("ℹ️ Google Flow operation disabled", "info")
                update_operation_status("Google Flow operation is disabled in configuration")
                return
            
            # Get URLs from the nested config
            all_project_url = google_flow_config.get('google_flow_url')
            google_flow_project_link = google_flow_config.get('google_flow_project_link')
            
            # Get expected images count
            expected_images = google_flow_config.get('expected_projectlink_images')
            if expected_images is not None:
                print(f"📊 [CONFIG] Expected images: {expected_images}")
            else:
                print(f"ℹ️ [CONFIG] No expected image count specified")
            
            # Get project title from the root level
            project_title = panel_data.get('project_title')
            
            if project_title:
                project_title = project_title.strip()
            
            print(f"🌐 [MAIN] All Projects URL: {all_project_url}")
            print(f"🌐 [MAIN] Project Name: [HIDDEN]")
            print(f"🌐 [MAIN] Project Link: {google_flow_project_link if google_flow_project_link else '[EMPTY]'}")
            
            # CRITICAL: Only exit if these are missing
            if not all_project_url and not google_flow_project_link:
                print("❌ Error: Neither 'google_flow_url' nor 'google_flow_project_link' configured.")
                update_operation_status("Error: Neither Google Flow URL nor project link is configured", is_error=True)
                return
            
            # CRITICAL: Exit if project name is empty when using all projects workflow
            if all_project_url and (not project_title or not project_title.strip()):
                print("❌ Error: 'project_title' is empty or missing.")
                update_operation_status("Error: Project title is empty or missing", is_error=True)
                return
            
            # Update initial status
            update_operation_status(f"Starting Google Flow operation for {project_title}")
            
            # Ensure browser is ready
            hwnd_to_use = ensure_window_ready_and_focused()
            current_monitor = get_current_monitor()
            monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
            monitor_width = monitor_right - monitor_left
            monitor_height = monitor_bottom - monitor_top
            print(f"🖥️ [MAIN] Monitor bounds: ({monitor_left}, {monitor_top}) to ({monitor_right}, {monitor_bottom})")
            print(f"📐 [MAIN] Monitor size: {monitor_width} x {monitor_height} pixels")
            
            time.sleep(0.5)
            
            # ============================================
            # FLOW 1: DIRECT PROJECT LINK PROVIDED - SIMPLIFIED
            # ============================================
            
            if google_flow_project_link and google_flow_project_link.strip():
                print("🚀 [ROUTING] Project link detected - loading directly...")
                update_operation_status(f"Loading {project_title} from direct link...")
                
                # Navigate to the project link
                fast_paste_url(hwnd_to_use, google_flow_project_link)
                hwnd_to_use = ensure_window_ready_and_focused()
                
                # Wait a moment for the page to render
                time.sleep(2)
                
                print("🔍 [MAIN] Looking for project name immediately...")
                update_operation_status(f"Verifying {project_title} on page...")
                
                # FIRST: Try to find the project name directly
                current_texts = safe_ocr()
                clean_project_title = clean_string_completely(project_title)
                project_found = False
                
                if current_texts:
                    for element in current_texts:
                        if clean_project_title in clean_string_completely(element['text']):
                            element_text = element['text'].lower()
                            # Skip UI text that isn't the project card
                            if "new project" not in element_text and "all media" not in element_text:
                                project_found = True
                                print(f"✅ [MAIN] Project name found immediately!")
                                hud.print("✅ Project found!", "success")
                                update_operation_status(f"Successfully verified {project_title} on page")
                                break
                
                # If project name found, proceed directly to download
                if project_found:
                    print("🚀 [MAIN] Project verified - proceeding directly to download...")
                    hud.print("🚀 Proceeding to download...", "success")
                    update_operation_status(f"Proceeding to download {project_title}...")
                    
                    # Scroll to make sure the page is ready
                    scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                        hwnd_to_use, google_flow_project_link, project_title
                    )
                    
                    if recovered_hwnd != hwnd_to_use:
                        hwnd_to_use = recovered_hwnd
                        print("🔄 [MAIN] Window recovered after scrolling")
                    
                    # Proceed to download immediately
                    success = find_and_click_vertical_dot(
                        hwnd_to_use, 
                        google_flow_project_link, 
                        project_title,
                        expected_images=expected_images
                    )
                    
                    if success:
                        update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                        hud.print("✅ Operation complete!", "success")
                        print("✅ [VERIFICATION] Download initiated successfully!")
                        return
                    else:
                        print("⚠️ [MAIN] Download flow incomplete, retrying...")
                        hud.print("🔄 Retrying download...", "warning")
                        update_operation_status(f"Download flow incomplete for {project_title}, retrying...", is_error=True)
                        time.sleep(2)
                        # Try one more time with recovery
                        return main()
                
                # SECOND: If project name not found, use the existing recovery mechanisms
                print("⚠️ [MAIN] Project name not found immediately - using recovery flow")
                hud.print("🔄 Project not found - checking page...", "warning")
                update_operation_status(f"Project {project_title} not found immediately, running recovery...")
                
                # Now use the existing recovery logic
                max_attempts = 5
                attempt = 0
                success = False
                
                while attempt < max_attempts and not success:
                    attempt += 1
                    print(f"🔄 [MAIN] Recovery attempt {attempt}/{max_attempts}...")
                    update_operation_status(f"Recovery attempt {attempt}/{max_attempts} for {project_title}...")
                    
                    # Analyze current page context
                    on_all, on_project, project_found_recovery, context = analyze_current_page_context(
                        hwnd_to_use, google_flow_project_link, project_title
                    )
                    
                    print(f"📊 [MAIN] Recovery context: {context}, on_project={on_project}, project_found={project_found_recovery}")
                    
                    if on_project:
                        print("✅ [MAIN] On project page (recovery mode)")
                        hud.print("✅ On project page", "success")
                        update_operation_status(f"On {project_title} project page (recovery mode)")
                        
                        page_ready, name_verified, recovered_hwnd = wait_for_specific_page_ready(
                            hwnd_to_use, google_flow_project_link, project_title
                        )
                        
                        if recovered_hwnd != hwnd_to_use:
                            hwnd_to_use = recovered_hwnd
                            print("🔄 [MAIN] Window recovered after page ready")
                        
                        if page_ready:
                            print("✅ [MAIN] Project page ready, proceeding to download...")
                            hud.print("🚀 Proceeding...", "success")
                            update_operation_status(f"Project page ready, proceeding to download {project_title}...")
                            
                            scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                                hwnd_to_use, google_flow_project_link, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after scrolling")
                            
                            if scroll_complete:
                                print("✅ [MAIN] Project verified")
                                hud.print(f"✅ {project_title} verified", "success")
                                update_operation_status(f"Successfully verified {project_title}")
                                
                                # Pass expected_images to download function
                                success = find_and_click_vertical_dot(
                                    hwnd_to_use, 
                                    google_flow_project_link, 
                                    project_title,
                                    expected_images=expected_images
                                )
                                
                                if success:
                                    update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    update_operation_status(f"Download flow incomplete for {project_title}, retrying...", is_error=True)
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Project verification incomplete, retrying...")
                                hud.print("🔄 Retrying verification...", "warning")
                                update_operation_status(f"Project verification incomplete for {project_title}, retrying...", is_error=True)
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Page not ready, retrying...")
                            hud.print("🔄 Retrying page load...", "warning")
                            update_operation_status(f"Page not ready for {project_title}, retrying...", is_error=True)
                            time.sleep(2)
                    else:
                        print("⚠️ [MAIN] Not on project page - refreshing and trying again...")
                        hud.print("🔄 Refreshing page...", "warning")
                        update_operation_status(f"Not on {project_title} page, refreshing...")
                        fast_paste_url(hwnd_to_use, google_flow_project_link)
                        time.sleep(3)
                        hwnd_to_use = ensure_window_ready_and_focused()
                
                # If we exhausted attempts, restart the whole process
                print("🔄 [MAIN] Max recovery attempts reached, restarting...")
                hud.print("🔄 Restarting operation...", "warning")
                error_msg = f"Max recovery attempts reached for {project_title}, restarting..."
                update_operation_status(error_msg, is_error=True)
                time.sleep(2)
                perform_navigation_and_restart(hwnd_to_use, google_flow_project_link, "max recovery attempts")
                return
            
            # ============================================
            # FLOW 2: ALL PROJECTS WORKFLOW - UNCHANGED
            # ============================================
            
            if all_project_url and all_project_url.strip():
                # ... (keep the existing ALL PROJECTS WORKFLOW code unchanged) ...
                print("🚀 [ROUTING] Using All Projects page workflow...")
                hud.print("📋 Navigating to projects list...", "navigating")
                update_operation_status(f"Navigating to All Projects page for {project_title}...")
                
                # Keep retrying until we succeed
                max_attempts = 5
                attempt = 0
                success = False
                
                while attempt < max_attempts and not success:
                    attempt += 1
                    print(f"🔄 [MAIN] Attempt {attempt}/{max_attempts} for all projects workflow...")
                    update_operation_status(f"Attempt {attempt}/{max_attempts} for {project_title}...")
                    
                    # Analyze current page context
                    on_all, on_project, project_found, context = analyze_current_page_context(
                        hwnd_to_use, all_project_url, project_title
                    )
                    
                    print(f"📊 [MAIN] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
                    
                    # CRITICAL FIX: If on project page AND project found, skip selection and go to download
                    if on_project and project_found:
                        print("✅ [MAIN] Already on target project page - skipping card selection")
                        hud.print("✅ On target page", "success")
                        update_operation_status(f"Already on {project_title} project page")
                        
                        page_ready, name_verified, recovered_hwnd = wait_for_specific_page_ready(
                            hwnd_to_use, all_project_url, project_title
                        )
                        
                        if recovered_hwnd != hwnd_to_use:
                            hwnd_to_use = recovered_hwnd
                            print("🔄 [MAIN] Window recovered after page ready")
                        
                        if page_ready:
                            print("✅ [MAIN] Project page ready, proceeding to download...")
                            hud.print("🚀 Proceeding...", "success")
                            update_operation_status(f"Project page ready, proceeding to download {project_title}...")
                            
                            scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                                hwnd_to_use, all_project_url, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after scrolling")
                            
                            if scroll_complete:
                                print("✅ [MAIN] Project verified")
                                hud.print(f"✅ {project_title} verified", "success")
                                update_operation_status(f"Successfully verified {project_title}")
                                
                                # Pass expected_images to download function
                                success = find_and_click_vertical_dot(
                                    hwnd_to_use, 
                                    all_project_url, 
                                    project_title,
                                    expected_images=expected_images
                                )
                                
                                if success:
                                    update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    update_operation_status(f"Download flow incomplete for {project_title}, retrying...", is_error=True)
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Project verification incomplete, retrying...")
                                hud.print("🔄 Retrying verification...", "warning")
                                update_operation_status(f"Project verification incomplete for {project_title}, retrying...", is_error=True)
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Page not ready, retrying...")
                            hud.print("🔄 Retrying page load...", "warning")
                            update_operation_status(f"Page not ready for {project_title}, retrying...", is_error=True)
                            time.sleep(2)
                        continue
                    
                    # If on wrong project page, navigate to all projects
                    if on_project and not project_found:
                        print("⚠️ [MAIN] On wrong project page - navigating to all projects")
                        hud.print("⚠️ Wrong project, navigating...", "warning")
                        update_operation_status(f"Wrong project detected, navigating to projects list...")
                        fast_paste_url(hwnd_to_use, all_project_url)
                        time.sleep(3)
                        # RESTART: We navigated to all projects, so restart the operation
                        perform_navigation_and_restart(hwnd_to_use, all_project_url, "wrong project navigation")
                        return
                    
                    # If context unknown, navigate to all projects
                    if context == "unknown":
                        print("⚠️ [MAIN] Page context unknown - navigating to all projects")
                        update_operation_status(f"Page context unknown, navigating to projects list...")
                        fast_paste_url(hwnd_to_use, all_project_url)
                        time.sleep(3)
                        hwnd_to_use = ensure_window_ready_and_focused()
                        # RESTART: We navigated to all projects, so restart the operation
                        perform_navigation_and_restart(hwnd_to_use, all_project_url, "unknown context navigation")
                        return
                    
                    # If not on all projects, navigate there
                    if not on_all:
                        fast_paste_url(hwnd_to_use, all_project_url)
                        time.sleep(3)
                        hwnd_to_use = ensure_window_ready_and_focused()
                        # RESTART: We navigated to all projects, so restart the operation
                        perform_navigation_and_restart(hwnd_to_use, all_project_url, "not on all projects navigation")
                        return
                    
                    # Now we should be on all projects page
                    page_ready, recovered_hwnd = wait_for_all_projects_page_ready(
                        hwnd_to_use, all_project_url, project_title
                    )
                    
                    if recovered_hwnd != hwnd_to_use:
                        hwnd_to_use = recovered_hwnd
                        print("🔄 [MAIN] Window recovered after page ready")
                    
                    if page_ready:
                        print("✅ [MAIN] All Projects page ready")
                        update_operation_status(f"All Projects page ready, searching for {project_title}...")
                        
                        card_found, card_element, recovered_hwnd = scroll_in_all_projects(
                            hwnd_to_use, all_project_url, project_title
                        )
                        
                        if recovered_hwnd != hwnd_to_use:
                            hwnd_to_use = recovered_hwnd
                            print("🔄 [MAIN] Window recovered after scrolling")
                        
                        # If we're already on the project page (card_element is None)
                        if card_found and card_element is None:
                            print("✅ [MAIN] Already on project page, proceeding to download...")
                            hud.print("🚀 Proceeding...", "success")
                            update_operation_status(f"Already on {project_title} page, proceeding to download...")
                            
                            # Pass expected_images to download function
                            success = find_and_click_vertical_dot(
                                hwnd_to_use, 
                                all_project_url, 
                                project_title,
                                expected_images=expected_images
                            )
                            
                            if success:
                                update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                                hud.print("✅ Operation complete!", "success")
                                print("✅ [VERIFICATION] All checks passed and download initiated!")
                                return
                            else:
                                print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                hud.print("🔄 Retrying download...", "warning")
                                update_operation_status(f"Download flow incomplete for {project_title}, retrying...", is_error=True)
                                time.sleep(2)
                                continue
                        
                        # We found a card to click
                        if card_found and card_element:
                            print("✅ [MAIN] Project card found - clicking it")
                            hud.print("✅ Target located - clicking", "success")
                            update_operation_status(f"Found {project_title} card, clicking...")
                            
                            click_success, recovered_hwnd = click_project_card(
                                hwnd_to_use, card_element, all_project_url, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after selection")
                            
                            if click_success:
                                print("✅ [MAIN] Project card selected, proceeding to download...")
                                hud.print("🚀 Proceeding...", "success")
                                update_operation_status(f"Successfully selected {project_title}, proceeding to download...")
                                
                                # Wait a bit for the page to load
                                time.sleep(2)
                                
                                # Pass expected_images to download function
                                success = find_and_click_vertical_dot(
                                    hwnd_to_use, 
                                    all_project_url, 
                                    project_title,
                                    expected_images=expected_images
                                )
                                
                                if success:
                                    update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    update_operation_status(f"Download flow incomplete for {project_title}, retrying...", is_error=True)
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Failed to select project card, retrying...")
                                hud.print("🔄 Retrying selection...", "warning")
                                update_operation_status(f"Failed to select {project_title} card, retrying...", is_error=True)
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Project card not found, retrying...")
                            hud.print("🔄 Retrying search...", "warning")
                            update_operation_status(f"Could not find {project_title} card, retrying...", is_error=True)
                            time.sleep(2)
                    else:
                        print("⚠️ [MAIN] All Projects page not ready, retrying...")
                        hud.print("🔄 Retrying page load...", "warning")
                        update_operation_status(f"All Projects page not ready, retrying...", is_error=True)
                        time.sleep(2)
                
                # If we exhausted attempts, restart the whole process
                print("🔄 [MAIN] Max attempts reached, restarting...")
                hud.print("🔄 Restarting operation...", "warning")
                error_msg = f"Max attempts reached for {project_title}, restarting..."
                update_operation_status(error_msg, is_error=True)
                time.sleep(2)
                perform_navigation_and_restart(hwnd_to_use, all_project_url, "max attempts reached")
                return

        except KeyboardInterrupt as ki:
            update_operation_status(f"Google Flow operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            # This is expected from abort_operation
            print(f"🛑 System exit: {se}")
            # The abort message is already in the status
        except Exception as e:
            print(f"❌ Error caught: {e}")
            error_msg = f"Unexpected error in main: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("🔄 Attempting recovery...", "warning")
            print("🔄 [MAIN] Attempting global recovery...")
            time.sleep(2)
            # Restart the entire operation
            try:
                # Try to get current URL and restart
                if all_project_url and all_project_url.strip():
                    hwnd = ensure_window_ready_and_focused()
                    perform_navigation_and_restart(hwnd, all_project_url, "exception recovery")
                elif google_flow_project_link and google_flow_project_link.strip():
                    hwnd = ensure_window_ready_and_focused()
                    perform_navigation_and_restart(hwnd, google_flow_project_link, "exception recovery")
                else:
                    return main()
            except:
                pass
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    main()

def operate_grok_browser():
    """
    Launches/uses Microsoft Edge for video operations.
    Features: Live HUD tracking, click-through overlay, 
    global hotkey interception, and video-specific workflow with navigation.
    """
    # --- SPEED TUNING PARAMETERS ---
    pyautogui.PAUSE = 0.0  
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    with open(PANEL_PATH, 'r', encoding='utf-8') as file:
        panel_data = json.load(file)

    project_title = panel_data.get('project_title')
    
    terminate_automation = False
    video_urls_file = None
    project_title = None
    operation_status_flag = True  # Global flag tracking operation health
    operation_status_message = ""  # Current status message
    operation_aborted = False  # Flag for abortion state

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        """
        Update the operation status in panel.json with a professional message.
        
        Args:
            message: The status message to write
            is_error: Whether this is an error state
            is_abort: Whether this is an abortion state
            is_success: Whether this is a success state
        """
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        
        try:
            # Read current panel data
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)
            
            # Format the status message professionally
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
            
            # Update the operation_status field
            current_panel['operation_status'] = operation_status_message
            
            # Write back to file
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(current_panel, file, indent=4, ensure_ascii=False)
            
            # If aborted, we should stop the program
            if is_abort:
                print(f"🛑 [STATUS] Operation aborted: {message}")
                raise SystemExit(f"Operation aborted: {message}")
                
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        """Abort the operation with a specific reason."""
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting video operation: {reason}", is_abort=True)
        # The update_operation_status will raise SystemExit

    def check_operation_status():
        """Check if operation status is still valid (not aborted/errored)."""
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting video operation", is_abort=True)
            return False
        return True

    def check_google_flow_status():
        """
        Check if Google Flow operation was aborted.
        If the operation_status contains 'aborting' or 'aborted', don't proceed.
        """
        try:
            if not os.path.exists(PANEL_PATH):
                print("⚠️ [SYNC] panel.json not found, proceeding cautiously")
                return True
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)
            
            current_status = current_panel.get('operation_status', '')
            
            # Check if the status contains abortion indicators
            if 'aborting' in current_status.lower() or 'aborted' in current_status.lower():
                print(f"🛑 [SYNC] Google Flow operation was aborted: '{current_status}'")
                print(f"🛑 [SYNC] Skipping video operation to maintain sync")
                update_operation_status("Video operation skipped: Google Flow was aborted", is_abort=True)
                return False
            
            print(f"✅ [SYNC] Google Flow status is valid, proceeding with video operation")
            return True
            
        except Exception as e:
            print(f"⚠️ [SYNC] Error checking Google Flow status: {e}")
            return True  # Proceed cautiously if we can't check

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status("Video operation manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status("Video operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

    def safe_ocr():
        """Capture screen without hiding the HUD (HUD is click-through)"""
        check_for_termination()
        return ocr()

    def clean_string_completely(text):
        """Normalize text by removing special characters and spaces for comparison"""
        if not text: 
            return ""
        t = text.lower().replace("https", "").replace("http", "").replace("www", "")
        t = re.sub(r'[^a-z0-9]', '', t)
        return t

    def normalize_text_for_comparison(text):
        """More aggressive normalization for text matching"""
        if not text:
            return ""
        t = text.lower()
        t = re.sub(r'[^a-z0-9]', '', t)
        return t
    
    def extract_id_from_url(url):
        """Extract ID from URL by getting everything after the last '/'"""
        if not url:
            return None
        # Get everything after the last '/'
        parts = url.rstrip('/').split('/')
        if parts:
            last_part = parts[-1]
            # Remove .mp4 extension if present
            if last_part.endswith('.mp4'):
                last_part = last_part[:-4]
            return last_part
        return None
    
    def check_for_timevalue(text_elements):
        """
        Check if any time value in format {anytimevalue}:{anytimevalue} exists.
        Returns: (found, first_time_element)
        """
        if not text_elements:
            return False, None
        
        time_pattern = re.compile(r'\d+:\d{2}')
        
        for element in text_elements:
            element_text = element['text'].strip()
            if time_pattern.search(element_text):
                print(f"✅ [TIMEVALUE] Found time value: '{element_text}'")
                return True, element
        
        return False, None

    def check_for_page_load_indicators(text_elements):
        """
        Check for various page load indicators (excluding time values).
        Returns: (is_loaded, indicator_found)
        """
        if not text_elements:
            return False, None
        
        # Load indicators (excluding time values)
        load_indicators = [
            "grok", "imagine", "type to imagine", "history",
            "makevideo", "extend", "regenerate"
        ]
        
        for element in text_elements:
            element_text = element['text'].strip().lower()
            for indicator in load_indicators:
                if indicator in element_text:
                    print(f"✅ [PAGE_LOAD] Page loaded - found indicator: '{indicator}'")
                    return True, indicator
        
        return False, None
    
    # ============================================
    # SECTION 1: WINDOW MANAGEMENT HELPERS
    # ============================================
    
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
        print(f"🖥️ [MONITOR] Bounds: ({monitor_left}, {monitor_top}) to ({monitor_right}, {monitor_bottom})")
        print(f"📐 [MONITOR] Size: {monitor_right - monitor_left} x {monitor_bottom - monitor_top} pixels")
        
        edge_windows = get_edge_window_on_monitor(current_monitor)
        
        if edge_windows:
            hwnd = edge_windows[0]['hwnd']
            print(f"🪟 [WINDOW] Found existing Edge window handle: {hwnd}")
            print(f"📏 [WINDOW] Size: {edge_windows[0]['width']} x {edge_windows[0]['height']}")
            
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
                update_operation_status("Browser window ready for video operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for video operation...")
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
                    update_operation_status("Browser launched for video operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        error_msg = "Failed to get or launch Edge window for video operation"
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
            except Exception as e:
                print(f"⚠️ [FOCUS] Could not check maximize state, attempting maximize anyway: {e}")
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
        hud.print("📋 Navigating destination...", "typing")
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.1)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status(f"Navigating to video URL...")

    def check_current_url_contains_target(hwnd, target_url):
        """
        Check if the current page contains the target URL in its text.
        Returns: (found, current_texts)
        """
        print(f"🔍 [URL_CHECK] Checking if current page contains target URL: {target_url}")
        
        current_texts = safe_ocr()
        if not current_texts:
            return False, None
        
        # Clean the target URL for comparison
        clean_target = clean_string_completely(target_url)
        
        for element in current_texts:
            element_text = element['text'].strip().lower()
            clean_element = clean_string_completely(element_text)
            
            # Check if the clean target is in the element text
            if clean_target in clean_element:
                print(f"✅ [URL_CHECK] Found target URL in page: '{element_text}'")
                return True, current_texts
            
            # Also check if the URL is partially present
            # Sometimes the URL appears with extra characters
            target_parts = clean_target.split('/')
            for part in target_parts:
                if len(part) > 5 and part in clean_element:
                    print(f"✅ [URL_CHECK] Found URL part '{part}' in page")
                    return True, current_texts
        
        print(f"❌ [URL_CHECK] Target URL not found in current page")
        return False, current_texts

    # ============================================
    # SECTION 2: VIDEO-SPECIFIC HELPERS
    # ============================================
    
    def check_for_text_on_screen(hwnd, target_text, timeout_seconds=10, check_interval=0.1):
        """Check if specific text appears on screen within timeout period."""
        print(f"🔍 [CHECK_TEXT] Looking for target text: '{target_text}'")
        
        normalized_target = normalize_text_for_comparison(target_text)
        print(f"🔍 [CHECK_TEXT] Normalized target: '{normalized_target}'")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    
                    if normalized_target in normalized_element:
                        print(f"✅ [CHECK_TEXT] Found target text: '{element_text}'")
                        return True, current_texts
            
            time.sleep(check_interval)
        
        print(f"❌ [CHECK_TEXT] Target text not found within {timeout_seconds}s")
        hud.print("❌ Page content not ready", "error")
        return False, None

    def check_for_history(hwnd, timeout_seconds=3, check_interval=0.3):
        """Specifically check if 'history' is already visible on screen."""
        print(f"🔍 [HISTORY_CHECK] Checking if history is already visible...")
        
        normalized_history = normalize_text_for_comparison("history")
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    if normalized_history in normalized_element:
                        print(f"✅ [HISTORY_CHECK] History already visible: '{element_text}'")
                        return True, current_texts
            
            time.sleep(check_interval)
        
        print(f"❌ [HISTORY_CHECK] History not found")
        return False, None

    def activate_ctrl_b_and_check_history(hwnd, max_attempts=5):
        """
        Checks if 'history' is already visible. If not, activates Ctrl+B and looks for history.
        """
        print("🎮 [CTRL+B] Starting Ctrl+B activation sequence...")
        update_operation_status("Activating video history panel...")
        
        # Step 1: Check if history is already visible
        print(f"🔍 [CTRL+B] Step 1: Checking if history is already visible...")
        history_already_visible, _ = check_for_history(hwnd, timeout_seconds=3, check_interval=0.3)
        
        if history_already_visible:
            print(f"✅ [CTRL+B] History already visible - no need to press Ctrl+B")
            update_operation_status("Video history panel already visible")
            return True, hwnd
        
        print(f"ℹ️ [CTRL+B] History not visible - will press Ctrl+B to reveal it")
        update_operation_status("Revealing video history panel...")
        
        for attempt in range(max_attempts):
            check_for_termination()
            
            print(f"🔄 [CTRL+B] Attempt {attempt + 1}/{max_attempts}")
            
            # Step 2: Verify page is still loaded by checking for indicators
            print(f"🔍 [CTRL+B] Verifying page is still loaded...")
            
            page_loaded, indicator = check_for_page_load_indicators(safe_ocr())
            
            if not page_loaded:
                print(f"⚠️ [CTRL+B] Page not loaded (attempt {attempt + 1}) - reloading...")
                hud.print("⚠️ Page not loaded, reloading...", "warning")
                update_operation_status(f"Page not loaded, reloading (attempt {attempt + 1})...")
                enforce_window_focus(hwnd)
                pyautogui.hotkey('ctrl', 'r')
                time.sleep(3)
                continue
            
            # Step 3: Activate Ctrl+B
            print(f"⌨️ [CTRL+B] Pressing Ctrl+B (attempt {attempt + 1})...")
            
            enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', 'b')
            time.sleep(1.5)
            
            # Step 4: Check for "history" text
            print(f"🔍 [CTRL+B] Checking for history option...")
            
            history_found, text_elements = check_for_text_on_screen(
                hwnd, "history", timeout_seconds=3, check_interval=0.3
            )
            
            if history_found:
                print(f"✅ [CTRL+B] 'history' found after {attempt + 1} attempts!")
                update_operation_status("History panel revealed successfully")
                return True, hwnd
            else:
                print(f"⏳ [CTRL+B] 'history' not found yet (attempt {attempt + 1})")
                hud.print(f"⏳ Trying again... ({attempt + 1}/{max_attempts})", "waiting")
                update_operation_status(f"Searching for history panel ({attempt + 1}/{max_attempts})...")
                time.sleep(0.5)
        
        print(f"❌ [CTRL+B] Failed to find 'history' after {max_attempts} attempts")
        error_msg = f"Failed to reveal history panel after {max_attempts} attempts"
        update_operation_status(error_msg, is_error=True)
        abort_operation(error_msg)
        return False, hwnd

    def click_history_button(hwnd, depth=0):
        """Find and click the 'history' button/text on screen."""
        print("🎯 [HISTORY] Looking for history option...")
        update_operation_status("Clicking history button...")
        
        if depth > 5:
            print("❌ [HISTORY] Max recursion depth reached")
            hud.print("❌ Option search recursion limit", "error")
            error_msg = "Max recursion depth reached finding history button"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        current_texts = safe_ocr()
        
        if not current_texts:
            print("⚠️ [HISTORY] No text found on screen")
            hud.print("⚠️ No text detected", "warning")
            time.sleep(1)
            return click_history_button(hwnd, depth + 1)
        
        history_elements = []
        normalized_history = normalize_text_for_comparison("history")
        
        for element in current_texts:
            element_text = element['text'].strip()
            normalized_element = normalize_text_for_comparison(element_text)
            if normalized_history in normalized_element:
                history_elements.append(element)
                print(f"🔍 [HISTORY] Found 'history' at position ({element['left']}, {element['top']})")
                print(f"🔍 [HISTORY] Text: '{element_text}'")
        
        if not history_elements:
            print("❌ [HISTORY] No history option found on screen")
            error_msg = "History button not found on screen"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        element = history_elements[0]
        click_x = int(element['left'] + (element['width'] / 2))
        click_y = int(element['top'] + (element['height'] / 2))
        
        print(f"🎯 [HISTORY] Clicking history at position ({click_x}, {click_y})")
        
        enforce_window_focus(hwnd)
        pyautogui.moveTo(click_x, click_y, duration=0.2)
        pyautogui.click()
        time.sleep(0.5)
        
        print("✅ [HISTORY] Successfully clicked history")
        update_operation_status("History button clicked successfully")
        
        return True, hwnd

    def find_and_click_video_duration(hwnd, timeout_seconds=10, check_interval=0.1):
        """Find and click the FIRST time value in format 0:XX."""
        print("⏱️ [TIME] Looking for first time value to click...")
        update_operation_status("Looking for video duration...")
        
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        center_x = monitor_left + (monitor_right - monitor_left) // 2
        center_y = monitor_top + (monitor_bottom - monitor_top) // 2
        
        print(f"🖱️ [TIME] Moving mouse to center: ({center_x}, {center_y})")
        pyautogui.moveTo(center_x, center_y, duration=0.3)
        time.sleep(0.3)
        
        print(f"⬇️ [TIME] Scrolling down...")
        hud.print("⬇️ Scrolling...", "navigating")
        pyautogui.scroll(-300)
        time.sleep(0.5)
        
        start_time = time.time()
        attempts = 0
        
        time_pattern = re.compile(r'\d+:\d{2}')
        all_time_elements = []
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            attempts += 1
            
            if not current_texts:
                print(f"⏳ [TIME] No text found (attempt {attempts})")
                time.sleep(check_interval)
                continue
            
            time_elements = []
            for element in current_texts:
                element_text = element['text'].strip()
                if time_pattern.search(element_text):
                    time_elements.append(element)
                    print(f"🔍 [TIME] Found time value: '{element_text}' at position ({element['left']}, {element['top']})")
            
            if time_elements:
                all_time_elements.extend(time_elements)
                all_time_elements.sort(key=lambda e: e['top'])
                first_element = all_time_elements[0]
                
                click_x = int(first_element['left'] + (first_element['width'] / 2))
                click_y = int(first_element['top'] + (first_element['height'] / 2))
                
                print(f"🎯 [TIME] Clicking FIRST time value at position ({click_x}, {click_y})")
                print(f"🎯 [TIME] Text: '{first_element['text'].strip()}'")
                
                enforce_window_focus(hwnd)
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.5)
                
                print("✅ [TIME] Successfully clicked first time value")
                hud.print("🎦")
                update_operation_status("Video duration selected successfully")
                return True, hwnd
            
            if attempts % 3 == 0:
                print(f"⬇️ [TIME] Scrolling down more (attempt {attempts})...")
                hud.print("⬇️ Scrolling more...", "navigating")
                pyautogui.scroll(-200)
                time.sleep(0.5)
            
            time.sleep(check_interval)
        
        print(f"❌ [TIME] No time value found within {timeout_seconds}s")
        hud.print("❌ No time value found", "error")
        error_msg = f"No video duration found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        abort_operation(error_msg)
        return False, hwnd

    # ============================================
    # SECTION 3: VIDEO NAVIGATION AND DOWNLOAD HELPERS
    # ============================================
    
    def extract_video_id_from_text(text_elements):
        """
        Extract video ID from OCR text elements.
        Looks for the pattern: /post/ or /imagine/ followed by ID
        Returns the video ID string or None.
        """
        if not text_elements:
            return None
        
        # Pattern to match video ID in URLs
        patterns = [
            r'/post/([a-f0-9-]+)',  # UUID format
            r'/imagine/(\d+)',       # Number format
            r'grok\.com/imagine/(\d+)',  # Full URL with number
            r'grok\.com/imagine/post/([a-f0-9-]+)',  # Full URL with UUID
            r'post/([a-f0-9-]+)',    # Just post/UUID
        ]
        
        for element in text_elements:
            element_text = element['text'].strip()
            
            for pattern in patterns:
                match = re.search(pattern, element_text)
                if match:
                    video_id = match.group(1)
                    print(f"🔍 [URL] Extracted video ID: {video_id}")
                    return video_id
        
        return None

    def get_current_video_id(hwnd, timeout_seconds=5):
        """
        Get the current video ID from the browser using OCR.
        Returns the video ID string or None.
        """
        print(f"🔍 [CURRENT_ID] Getting current video ID...")
        hud.print("🔍 Checking video...", "searching")
        update_operation_status("Getting current video ID...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            if current_texts:
                video_id = extract_video_id_from_text(current_texts)
                if video_id:
                    print(f"✅ [CURRENT_ID] Found video ID: {video_id}")
                    return video_id
            
            time.sleep(0.3)
        
        print(f"❌ [CURRENT_ID] Could not extract video ID")
        hud.print("❌ Could not get current video", "error")
        error_msg = "Could not extract current video ID"
        update_operation_status(error_msg, is_error=True)
        abort_operation(error_msg)
        return None

    def navigate_to_previous_video(hwnd):
        """Press left arrow key to navigate to previous video."""
        print("⬅️ [NAVIGATE] Navigating to previous video...")
        hud.print("⬅️ Previous video...", "navigating")
        
        enforce_window_focus(hwnd)
        pyautogui.press('left')
        time.sleep(1.5)
        
        return hwnd

    def navigate_to_next_video(hwnd):
        """Press right arrow key to navigate to next video."""
        print("➡️ [NAVIGATE] Navigating to next video...")
        hud.print("➡️ Next video...", "navigating")
        
        enforce_window_focus(hwnd)
        pyautogui.press('right')
        time.sleep(1.5)
        
        return hwnd

    def check_for_prompt_id(hwnd, prompt_id, timeout_seconds=3):
        """
        Check if the prompt ID is visible on screen.
        Returns: (found, text_elements)
        """
        print(f"🔍 [PROMPT_ID] Looking for prompt ID: '{prompt_id}'")
        hud.print("🔍 Getting Video ID...", "searching")
        
        normalized_prompt = normalize_text_for_comparison(prompt_id)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    if normalized_prompt in normalized_element:
                        print(f"✅ [PROMPT_ID] Found prompt ID: '{element_text}'")
                        return True, current_texts
            
            time.sleep(0.3)
        
        print(f"❌ [PROMPT_ID] Prompt ID not found")
        return False, None

    def click_download_button(hwnd, timeout_seconds=5, check_interval=0.2):
        """
        Find and click the download button using image recognition.
        First checks for and dismisses any download modal.
        Looks for download_btn1.png first, then falls back to download_btn2.png.
        Searches specifically in the bottom-right quadrant of the screen.
        
        Returns:
            tuple: (success, hwnd)
        """
        print("📥 [DOWNLOAD_BTN] Looking for Download button using image recognition...")
        update_operation_status("Searching for download button...")
        
        # ===== NEW: Pre-check for download modal before clicking download button =====
        print(f"🔍 [DOWNLOAD_BTN] Pre-checking for download modal...")
        hwnd = dismiss_download_modal_if_present(hwnd)
        time.sleep(0.3)
        
        # Check for 'regenerate' or 'extend' before looking for download button
        print(f"🔍 [DOWNLOAD_BTN] Checking for 'regenerate' or 'extend'...")
        
        current_texts = safe_ocr()
        found_indicator = False
        
        if current_texts:
            for element in current_texts:
                element_text = element['text'].strip().lower()
                if 'regenerate' in element_text or 'extend' in element_text:
                    print(f"✅ [DOWNLOAD_BTN] Found indicator text: '{element_text}'")
                    found_indicator = True
                    break
        
        if found_indicator:
            print(f"⌨️ [DOWNLOAD_BTN] Activating Ctrl+/ (found regenerate/extend)...")
            enforce_window_focus(hwnd)
            pyautogui.hotkey('ctrl', '/')
            time.sleep(0.5)
            print(f"✅ [DOWNLOAD_BTN] Ctrl+/ activated")
        
        # Define paths to download button images
        download_btn1_path = os.path.join(GUI_IMAGE_PATH, "download_btn1.png")
        download_btn2_path = os.path.join(GUI_IMAGE_PATH, "download_btn2.png")
        
        # Check if image files exist
        if not os.path.exists(download_btn1_path) and not os.path.exists(download_btn2_path):
            print("❌ [DOWNLOAD_BTN] No download button images found in GUI_IMAGE_PATH")
            hud.print("❌ Download images missing", "error")
            error_msg = "Download button images not found"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        start_time = time.time()
        attempts = 0
        
        # Get current monitor bounds for region restriction
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        monitor_width = monitor_right - monitor_left
        monitor_height = monitor_bottom - monitor_top
        
        # Search bottom-right region
        region_left = monitor_left + (monitor_width // 2) - 50
        region_top = monitor_top + (monitor_height // 2) - 50
        region_width = monitor_width // 2 + 100
        region_height = monitor_height // 2 + 100
        
        # Define search region
        region = (region_left, region_top, region_width, region_height)
        
        print(f"📐 [DOWNLOAD_BTN] Screen: {monitor_width}x{monitor_height}")
        print(f"📐 [DOWNLOAD_BTN] Search region: {region}")
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            attempts += 1
            
            print(f"🔍 [DOWNLOAD_BTN] Attempt {attempts} - Searching in bottom-right region...")
            
            # Try download_btn1.png first
            if os.path.exists(download_btn1_path):
                try:
                    found_location = pyautogui.locateCenterOnScreen(
                        download_btn1_path,
                        region=region,
                        confidence=0.8,
                        grayscale=False
                    )
                    
                    if found_location:
                        x, y = found_location
                        print(f"✅ [DOWNLOAD_BTN] Found download_btn1.png at position ({x}, {y})")
                        
                        # Click the download button
                        enforce_window_focus(hwnd)
                        pyautogui.moveTo(x, y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        print(f"✅ [DOWNLOAD_BTN] Successfully clicked download button using download_btn1.png")
                        update_operation_status("Download button clicked successfully")
                        return True, hwnd
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_BTN] Error searching for download_btn1.png: {e}")
            
            # Try download_btn2.png
            if os.path.exists(download_btn2_path):
                try:
                    found_location = pyautogui.locateCenterOnScreen(
                        download_btn2_path,
                        region=region,
                        confidence=0.8,
                        grayscale=False
                    )
                    
                    if found_location:
                        x, y = found_location
                        print(f"✅ [DOWNLOAD_BTN] Found download_btn2.png at position ({x}, {y})")
                        
                        # Click the download button
                        enforce_window_focus(hwnd)
                        pyautogui.moveTo(x, y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        print(f"✅ [DOWNLOAD_BTN] Successfully clicked download button using download_btn2.png")
                        update_operation_status("Download button clicked successfully")
                        return True, hwnd
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_BTN] Error searching for download_btn2.png: {e}")
            
            # If not found, try a larger region
            if attempts == 3:
                print(f"🔍 [DOWNLOAD_BTN] Expanding search region...")
                region_left = monitor_left + (monitor_width // 4)
                region_top = monitor_top + (monitor_height // 4)
                region_width = monitor_width // 2
                region_height = monitor_height // 2
                region = (region_left, region_top, region_width, region_height)
                print(f"📐 [DOWNLOAD_BTN] New search region: {region}")
            
            time.sleep(check_interval)
        
        print(f"❌ [DOWNLOAD_BTN] No Download button found within {timeout_seconds}s")
        hud.print("❌ Download button not found", "error")
        error_msg = f"Download button not found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, hwnd

    # ============================================
    # SECTION 4: GET TO LATEST VIDEO OPERATION
    # ============================================
    
    def get_to_latest_video(hwnd, base_url, max_attempts=30):
        """
        Operation 1: Navigate left until reaching the latest video.
        Stops when pressing left doesn't change the video ID (we're at the latest).
        """
        print("⬅️ [LATEST_VIDEO] Starting 'Get to Latest Video' operation...")
        hud.print("⬅️ Finding latest video...", "navigating")
        update_operation_status("Navigating to latest video...")
        
        current_id = get_current_video_id(hwnd)
        if not current_id:
            print("❌ [LATEST_VIDEO] Could not get current video ID")
            error_msg = "Could not get current video ID for navigation"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        print(f"📋 [LATEST_VIDEO] Starting video ID: {current_id}")
        
        visited_ids = set()
        visited_ids.add(current_id)
        
        attempt = 0
        latest_reached = False
        
        while attempt < max_attempts and not latest_reached:
            check_for_termination()
            
            hwnd = navigate_to_previous_video(hwnd)
            attempt += 1
            
            new_id = get_current_video_id(hwnd, timeout_seconds=3)
            
            if not new_id:
                print(f"⚠️ [LATEST_VIDEO] Could not get ID after left navigation (attempt {attempt})")
                continue
            
            if new_id == current_id:
                latest_reached = True
                print(f"✅ [LATEST_VIDEO] Reached latest video! ID: {new_id}")
                print(f"✅ [LATEST_VIDEO] Pressed left {attempt} times to reach it")
                hud.print("✅ Gotten to the latest video", "success")
                update_operation_status(f"Reached latest video after {attempt} navigations")
                return True, hwnd
            
            if new_id in visited_ids:
                print(f"⚠️ [LATEST_VIDEO] Cycle detected at ID: {new_id}")
                print(f"✅ [LATEST_VIDEO] Latest video is: {current_id}")
                hud.print("✅ Gotten to the latest video", "success")
                update_operation_status(f"Reached latest video (cycle detected at ID: {new_id})")
                return True, hwnd
            
            visited_ids.add(new_id)
            print(f"⬅️ [LATEST_VIDEO] Navigated to video ID: {new_id}")
            hud.print("⬅️ Not latest video", "navigating")
            update_operation_status(f"Navigating to latest video... (attempt {attempt})")
            current_id = new_id
        
        if not latest_reached:
            print(f"❌ [LATEST_VIDEO] Failed to reach latest video after {max_attempts} attempts")
            error_msg = f"Failed to reach latest video after {max_attempts} attempts"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        return True, hwnd

    def record_video_id_to_file(video_id, prompt_id, project_title):
        """
        Record only the video ID to a permanent file in the project folder.
        """
        try:
            # Create project folder if it doesn't exist
            project_folder = os.path.join(IMAGES_PATH, normalize_project_title(project_title))
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)
                print(f"📁 [RECORD] Created project folder: {project_folder}")
            
            # Create video_urls.csv file in project folder
            video_urls_file = os.path.join(project_folder, "video_urls.csv")
            
            # Read existing recordings if any
            existing_recordings = []
            if os.path.exists(video_urls_file):
                with open(video_urls_file, 'r', encoding='utf-8') as f:
                    existing_recordings = [line.strip() for line in f if line.strip()]
            
            # Check if this video ID is already recorded
            for recording in existing_recordings:
                if f"video id: {video_id}" in recording.lower():
                    print(f"ℹ️ [RECORD] Video ID {video_id} already recorded")
                    return False
            
            # Record the new video info
            video_number = len(existing_recordings) // 2 + 1
            with open(video_urls_file, 'a', encoding='utf-8') as f:
                f.write(f"video {video_number} identified:\n")
                f.write(f"video prompt id: {prompt_id}\n")
                f.write(f"video id: {video_id}\n")
                f.write("-" * 50 + "\n")
            
            print(f"📝 [RECORD] Recorded video {video_number}:")
            print(f"   Prompt ID: {prompt_id}")
            print(f"   ID: {video_id}")
            hud.print(f"✅ Video identified ({video_number})", "success")
            update_operation_status(f"Recorded video {video_number} with prompt ID: {prompt_id}")
            return True
                
        except Exception as e:
            print(f"❌ [RECORD] Error recording video info: {e}")
            error_msg = f"Error recording video info: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False

    def normalize_project_title(name):
        """Normalize project name by removing special characters but keeping underscores."""
        if not name:
            return "unnamed_project"
        normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'_+', '_', normalized)
        normalized = normalized.strip('_')
        return normalized if normalized else "unnamed_project"

    # ============================================
    # SECTION 5: GET VIDEO PROMPT IDS OPERATION WITH DOWNLOAD
    # ============================================
    def get_downloads_folder_files():
        """
        Get a set of filenames currently in the Downloads folder.
        Returns a set of filenames.
        """
        downloads_folder = os.path.expanduser("~/Downloads")
        files = set()
        
        if os.path.exists(downloads_folder):
            try:
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file():
                            files.add(entry.name)
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_FILES] Error scanning Downloads: {e}")
        
        return files

    def get_newest_download_file(hwnd, initial_files, timeout_seconds=60, check_interval=1.0):
        """
        Monitor Downloads folder for new files after clicking download.
        Returns the name of the newest downloaded file or None if timeout.
        
        Args:
            hwnd: Window handle for focus management
            initial_files: Set of filenames present before download
            timeout_seconds: Maximum time to wait for download (default 60 seconds)
            check_interval: Seconds between checks (default 1 second)
        
        Returns:
            tuple: (success, filename, file_path)
        """
        print(f"📊 [DOWNLOAD_MONITOR] Starting download monitoring...")
        hud.print("📊 Monitoring Downloads folder...", "waiting")
        update_operation_status("Monitoring download progress...")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Track when we last saw a new file
        new_file_stable_count = 0
        current_new_file = None
        current_new_file_path = None
        file_detected = False  # NEW: Flag to track if file has been detected
        
        while time.time() - start_time < timeout_seconds:
            try:
                check_for_termination()
                
                # Get current files in Downloads
                current_files = set()
                if os.path.exists(downloads_folder):
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file():
                                current_files.add(entry.name)
                
                # Find new files (not in initial set)
                new_files = current_files - initial_files
                
                if new_files:
                    # Get the newest file (by creation time or modification time)
                    newest_file = None
                    newest_file_path = None
                    newest_time = 0
                    
                    for filename in new_files:
                        file_path = os.path.join(downloads_folder, filename)
                        try:
                            # Get creation time or modification time
                            stat = os.stat(file_path)
                            # Use creation time on Windows, modification time on other platforms
                            if os.name == 'nt':
                                file_time = stat.st_ctime  # Creation time on Windows
                            else:
                                file_time = stat.st_mtime  # Modification time on Unix
                            
                            if file_time > newest_time:
                                newest_time = file_time
                                newest_file = filename
                                newest_file_path = file_path
                        except Exception:
                            continue
                    
                    if newest_file:
                        # Check if this is the same file we saw before
                        if current_new_file != newest_file:
                            # New file detected - reset stability counter
                            current_new_file = newest_file
                            current_new_file_path = newest_file_path
                            new_file_stable_count = 0
                            file_detected = True  # NEW: Mark that file has been detected
                            print(f"🆕 [DOWNLOAD_MONITOR] New file detected: {newest_file}")
                            hud.print(f"📥 New file detected", "success")  # Changed to success
                            update_operation_status(f"New file detected: {newest_file}")
                        else:
                            # Same file - check if it's stable (not being written)
                            try:
                                # Check if file is still being written
                                size1 = os.path.getsize(current_new_file_path)
                                time.sleep(0.5)
                                size2 = os.path.getsize(current_new_file_path)
                                
                                if size1 == size2 and size1 > 0:
                                    # File size stable and > 0
                                    new_file_stable_count += 1
                                    print(f"✅ [DOWNLOAD_MONITOR] File stable ({new_file_stable_count}/3), size: {size1} bytes")
                                    
                                    if new_file_stable_count >= 3:
                                        print(f"✅ [DOWNLOAD_MONITOR] Download complete!")
                                        hud.print("✅ Download complete!", "success")
                                        update_operation_status("Download completed successfully")
                                        return True, current_new_file, current_new_file_path
                                else:
                                    # File still being written
                                    new_file_stable_count = 0
                                    print(f"⏳ [DOWNLOAD_MONITOR] File being written... size: {size1} → {size2}")
                                    # Only show downloading if we haven't already detected the file
                                    if not file_detected:
                                        hud.print(f"⏳ Downloading...", "downloading")
                            except Exception as e:
                                print(f"⚠️ [DOWNLOAD_MONITOR] Error checking file size: {e}")
                                new_file_stable_count = 0
                
                # Update progress every 5 seconds - ONLY if no file detected yet
                elapsed = int(time.time() - start_time)
                if elapsed > 0 and elapsed % 5 == 0:
                    if not file_detected:  # Only show waiting if no file detected
                        hud.print(f"⏳ Waiting for download... ({elapsed}s)", "waiting")
                        update_operation_status(f"Waiting for download... ({elapsed}s)")
                    # If file is detected, we show the "New file detected" message instead
                
                # Keep window focused
                enforce_window_focus(hwnd)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("🛑 [DOWNLOAD_MONITOR] Download monitoring interrupted by user")
                raise
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_MONITOR] Error: {e}")
                time.sleep(check_interval)
                continue
        
        # Timeout reached
        print(f"⏰ [DOWNLOAD_MONITOR] Timeout reached after {timeout_seconds} seconds")
        hud.print("⏰ Download monitoring timed out", "error")
        error_msg = f"Download monitoring timed out after {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, None, None

    def move_downloaded_video_to_project(video_filename, video_file_path, project_title):
        """
        Move the downloaded video to the project folder's video subfolder and rename it to a number.
        Checks if 1.mp4 exists, then 2.mp4, etc.
        
        Args:
            video_filename: The original filename
            video_file_path: Full path to the video file
            project_title: Project title for folder naming
        
        Returns:
            tuple: (success, new_path, video_number)
        """
        print(f"📦 [MOVE_VIDEO] Moving downloaded video to project folder...")
        
        # Normalize project name
        def normalize_project_title(name):
            if not name:
                return "unnamed_project"
            normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
            normalized = re.sub(r'\s+', '_', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            normalized = normalized.strip('_')
            return normalized if normalized else "unnamed_project"
        
        # Get file extension
        _, ext = os.path.splitext(video_filename)
        
        # Create project folder
        project_folder = os.path.join(IMAGES_PATH, normalize_project_title(project_title))
        if not os.path.exists(project_folder):
            os.makedirs(project_folder)
            print(f"📁 [MOVE_VIDEO] Created project folder: {project_folder}")
        
        # Create video subfolder inside project folder
        video_folder = os.path.join(project_folder, "videos")
        if not os.path.exists(video_folder):
            os.makedirs(video_folder)
            print(f"📁 [MOVE_VIDEO] Created video subfolder: {video_folder}")
        
        # Find the next available number
        video_number = 1
        while True:
            new_filename = f"{video_number}{ext}"
            new_path = os.path.join(video_folder, new_filename)
            if not os.path.exists(new_path):
                break
            video_number += 1
        
        try:
            # Move and rename the file
            os.rename(video_file_path, new_path)
            print(f"✅ [MOVE_VIDEO] Moved video to: {new_path}")
            print(f"📊 [MOVE_VIDEO] Video number: {video_number}")
            hud.print(f"✅ Video saved as {video_number}{ext} in video folder", "success")
            update_operation_status(f"Video {video_number} saved successfully")
            return True, new_path, video_number
        except Exception as e:
            print(f"❌ [MOVE_VIDEO] Error moving video: {e}")
            error_msg = f"Error moving video: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False, None, None
        
    def get_video_prompt_ids_with_download(hwnd, base_url, prompt_id, project_title, max_videos=50):
        """
        Operation 2: Navigate right and record videos with matching prompt ID.
        For each matching video, clicks the download button, monitors Downloads folder,
        and moves the downloaded video to the project folder with a numbered name.
        """
        print("➡️ [PROMPT_IDS] Starting 'Get Video Prompt IDs' operation...")
        print(f"🔍 [PROMPT_IDS] Looking for prompt ID: '{prompt_id}'")
        hud.print("🔍 Searching for matching videos...", "searching")
        update_operation_status(f"Searching for videos with prompt ID: {prompt_id}")
        
        current_id = get_current_video_id(hwnd)
        if not current_id:
            print("❌ [PROMPT_IDS] Could not get current video ID")
            error_msg = "Could not get current video ID for matching"
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            return False, hwnd
        
        print(f"📋 [PROMPT_IDS] Starting from video ID: {current_id}")
        
        visited_ids = set()
        visited_ids.add(current_id)
        
        consecutive_misses = 0
        max_misses = 5
        videos_found = 0
        videos_downloaded = 0
        
        # Check starting video
        prompt_found, _ = check_for_prompt_id(hwnd, prompt_id, timeout_seconds=3)
        
        if prompt_found:
            print(f"✅ [PROMPT_IDS] Starting video has the prompt ID!")
            update_operation_status(f"Found matching video {videos_found + 1} with prompt ID: {prompt_id}")
            
            # Record the video ID
            record_success = record_video_id_to_file(
                current_id, prompt_id, project_title
            )
            if record_success:
                videos_found += 1
                hud.print(f"✅ Video identified ({videos_found})", "success")
                update_operation_status(f"Recorded video {videos_found}")
            
            # ========== DOWNLOAD PROCESS ==========
            # Step 1: Get initial files in Downloads folder BEFORE clicking download
            print(f"📁 [PROMPT_IDS] Getting initial Downloads folder state...")
            initial_files = get_downloads_folder_files()
            print(f"📁 [PROMPT_IDS] Found {len(initial_files)} files in Downloads")
            
            # Step 2: Click the download button
            print(f"📥 [PROMPT_IDS] Clicking download button for video {current_id}...")
            download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
            
            if download_success:
                # Step 3: Monitor Downloads folder for new file with retry
                success, downloaded_filename, downloaded_path = get_newest_download_file_with_retry(
                    hwnd, 
                    initial_files, 
                    timeout_seconds=120, 
                    check_interval=1.0,
                    video_url=base_url,
                    title=f"video_{current_id}"
                )
                
                if success and downloaded_filename and downloaded_path:
                    print(f"✅ [PROMPT_IDS] Download successful!")
                    update_operation_status(f"Download successful for video {videos_found}")
                    
                    # Step 4: Dismiss download modal if present
                    hwnd = dismiss_download_modal_if_present(hwnd)
                    
                    # Step 5: Move to project folder with numbered name
                    move_success, new_path, video_number = move_downloaded_video_to_project(
                        downloaded_filename, downloaded_path, project_title
                    )
                    
                    if move_success:
                        videos_downloaded += 1
                        hud.print(f"✅ Video {video_number} saved", "success")
                        print(f"📊 [PROMPT_IDS] Total videos downloaded: {videos_downloaded}")
                        update_operation_status(f"Video {video_number} downloaded and saved")
                    else:
                        print(f"⚠️ [PROMPT_IDS] Failed to move downloaded video")
                        hud.print("⚠️ Could not move video", "warning")
                        update_operation_status("Download succeeded but move failed", is_error=True)
                else:
                    print(f"⚠️ [PROMPT_IDS] Download monitoring timed out or failed")
                    hud.print("⚠️ Download may have failed", "warning")
                    update_operation_status("Download monitoring failed", is_error=True)
            else:
                print(f"⚠️ [PROMPT_IDS] Failed to click download button for video {current_id}")
                hud.print("⚠️ Download button not found", "warning")
                update_operation_status("Could not find download button", is_error=True)
        
        # Navigate right and continue
        print(f"🔍 [PROMPT_IDS] Starting navigation to find more videos...")
        update_operation_status(f"Continuing search for matching videos...")
        
        while consecutive_misses < max_misses and videos_found < max_videos:
            check_for_termination()
            
            hwnd = navigate_to_next_video(hwnd)
            
            new_id = get_current_video_id(hwnd, timeout_seconds=3)
            
            if not new_id:
                print(f"⚠️ [PROMPT_IDS] Could not get ID after right navigation")
                consecutive_misses += 1
                print(f"❌ [PROMPT_IDS] Miss {consecutive_misses}/{max_misses}")
                continue
            
            if new_id in visited_ids:
                print(f"⚠️ [PROMPT_IDS] Cycle detected at ID: {new_id}")
                print(f"📊 [PROMPT_IDS] Found {videos_found} matching videos, downloaded {videos_downloaded}")
                hud.print(f"📊 Found {videos_found} matching videos, downloaded {videos_downloaded}", "info")
                update_operation_status(f"Cycle detected: Found {videos_found} matching videos, downloaded {videos_downloaded}")
                break
            
            visited_ids.add(new_id)
            print(f"➡️ [PROMPT_IDS] Navigated to video ID: {new_id}")
            
            prompt_found, _ = check_for_prompt_id(hwnd, prompt_id, timeout_seconds=3)
            
            if prompt_found:
                print(f"✅ [PROMPT_IDS] Found matching video at ID: {new_id}")
                update_operation_status(f"Found matching video {videos_found + 1}")
                
                # Record the video ID
                record_success = record_video_id_to_file(
                    new_id, prompt_id, project_title
                )
                
                if record_success:
                    videos_found += 1
                    hud.print(f"✅ Video identified ({videos_found})", "success")
                    update_operation_status(f"Recorded video {videos_found}")
                
                # ========== DOWNLOAD PROCESS ==========
                # Step 1: Get initial files in Downloads folder BEFORE clicking download
                print(f"📁 [PROMPT_IDS] Getting initial Downloads folder state...")
                initial_files = get_downloads_folder_files()
                print(f"📁 [PROMPT_IDS] Found {len(initial_files)} files in Downloads")
                
                # Step 2: Click the download button
                print(f"📥 [PROMPT_IDS] Clicking download button for video {new_id}...")
                download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
                
                if download_success:
                    # Step 3: Monitor Downloads folder for new file with retry
                    success, downloaded_filename, downloaded_path = get_newest_download_file_with_retry(
                        hwnd, 
                        initial_files, 
                        timeout_seconds=120, 
                        check_interval=1.0,
                        video_url=base_url,
                        title=f"video_{new_id}"
                    )
                    
                    if success and downloaded_filename and downloaded_path:
                        print(f"✅ [PROMPT_IDS] Download successful!")
                        update_operation_status(f"Download successful for video {videos_found}")
                        
                        # Step 4: Dismiss download modal if present
                        hwnd = dismiss_download_modal_if_present(hwnd)
                        
                        # Step 5: Move to project folder with numbered name
                        move_success, new_path, video_number = move_downloaded_video_to_project(
                            downloaded_filename, downloaded_path, project_title
                        )
                        
                        if move_success:
                            videos_downloaded += 1
                            hud.print(f"✅ Video {video_number} saved", "success")
                            print(f"📊 [PROMPT_IDS] Total videos downloaded: {videos_downloaded}")
                            update_operation_status(f"Video {video_number} downloaded and saved")
                        else:
                            print(f"⚠️ [PROMPT_IDS] Failed to move downloaded video")
                            hud.print("⚠️ Could not move video", "warning")
                            update_operation_status("Download succeeded but move failed", is_error=True)
                    else:
                        print(f"⚠️ [PROMPT_IDS] Download monitoring timed out or failed")
                        hud.print("⚠️ Download may have failed", "warning")
                        update_operation_status("Download monitoring failed", is_error=True)
                else:
                    print(f"⚠️ [PROMPT_IDS] Failed to click download button for video {new_id}")
                    hud.print("⚠️ Download button not found", "warning")
                    update_operation_status("Could not find download button", is_error=True)
                
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                print(f"❌ [PROMPT_IDS] Prompt ID not found (miss {consecutive_misses}/{max_misses})")
                hud.print(f"❌ No match ({consecutive_misses}/{max_misses})", "warning")
                update_operation_status(f"Searching for matching videos... ({consecutive_misses}/{max_misses} misses)")
        
        # Summary
        print("=" * 60)
        print(f"📊 [PROMPT_IDS] OPERATION SUMMARY:")
        print(f"   ✅ Matching videos found: {videos_found}")
        print(f"   💾 Videos downloaded: {videos_downloaded}")
        print(f"   📁 Project: {project_title}")
        print("=" * 60)
        
        if videos_downloaded > 0:
            hud.print(f"✅ Downloaded {videos_downloaded} videos", "success")
            update_operation_status(f"Successfully downloaded {videos_downloaded} videos", is_success=True)
            return True, hwnd
        elif videos_found > 0:
            print(f"⚠️ [PROMPT_IDS] Found {videos_found} videos but downloads failed")
            hud.print(f"⚠️ Found {videos_found} videos, downloads failed", "warning")
            error_msg = f"Found {videos_found} matching videos but downloads failed"
            update_operation_status(error_msg, is_error=True)
            return False, hwnd
        else:
            print(f"❌ [PROMPT_IDS] No videos found with the prompt ID")
            hud.print("❌ No matching videos found", "error")
            error_msg = f"No videos found with prompt ID: {prompt_id}"
            update_operation_status(error_msg, is_error=True)
            return False, hwnd
        
    # ============================================
    # SECTION 6: MAIN VIDEO WORKFLOW
    # ============================================
    def load_individual_video_url(hwnd, video_url):
        """
        Load an individual video URL directly.
        This bypasses the normal navigation flow and just loads the specific video.
        """
        print(f"🎬 [INDIVIDUAL] Loading video URL: {video_url}")
        
        # Check if URL is already loaded
        url_found, _ = check_current_url_contains_target(hwnd, video_url)
        
        if url_found:
            print(f"✅ [INDIVIDUAL] URL already loaded")
            return True, hwnd
        
        # Navigate to the URL
        fast_paste_url(hwnd, video_url)
        time.sleep(3)
        hwnd = ensure_window_ready_and_focused()
        
        return True, hwnd

    def verify_page_loaded_individual(hwnd, max_attempts=5):
        """
        Verify page is loaded for individual video URLs.
        Uses page load indicators but doesn't click on history.
        """
        print(f"🔍 [INDIVIDUAL] Verifying page is loaded...")
        hud.print("⏳ Checking page...", "waiting")
        
        for attempt in range(max_attempts):
            check_for_termination()
            
            # Check for page load indicators
            current_texts = safe_ocr()
            if current_texts:
                page_loaded, indicator = check_for_page_load_indicators(current_texts)
                
                if page_loaded:
                    print(f"✅ [INDIVIDUAL] Page loaded - indicator: {indicator}")
                    hud.print("✅ Page loaded", "success")
                    update_operation_status("Individual video page loaded successfully")
                    return True, hwnd
            
            # If not loaded, try Ctrl+B to reveal content (but don't click history)
            if attempt < max_attempts - 1:
                print(f"🔄 [INDIVIDUAL] Attempt {attempt + 1}/{max_attempts} - Pressing Ctrl+B to refresh content...")
                enforce_window_focus(hwnd)
                pyautogui.hotkey('ctrl', 'b')
                time.sleep(1.5)
                
                # Check again after Ctrl+B
                current_texts = safe_ocr()
                if current_texts:
                    page_loaded, indicator = check_for_page_load_indicators(current_texts)
                    if page_loaded:
                        print(f"✅ [INDIVIDUAL] Page loaded after Ctrl+B - indicator: {indicator}")
                        hud.print("✅ Page loaded", "success")
                        update_operation_status("Individual video page loaded after refresh")
                        return True, hwnd
                
                time.sleep(0.5)
        
        print(f"❌ [INDIVIDUAL] Page failed to load after {max_attempts} attempts")
        hud.print("❌ Page load failed", "error")
        error_msg = f"Page failed to load after {max_attempts} attempts"
        update_operation_status(error_msg, is_error=True)
        return False, hwnd

    def dismiss_download_modal_if_present(hwnd):
        """
        Check if download modal is present by looking for downloads icon.
        Searches in the upper half of the screen.
        If found, click on it to dismiss the modal.
        """
        print(f"🔍 [MODAL] Checking for download modal using icon recognition...")
        
        # Define paths to download icon images
        downloads_icon1_path = os.path.join(GUI_IMAGE_PATH, "downloads_icon1.png")
        downloads_icon2_path = os.path.join(GUI_IMAGE_PATH, "downloads_icon2.png")
        
        # Check if image files exist
        if not os.path.exists(downloads_icon1_path) and not os.path.exists(downloads_icon2_path):
            print("ℹ️ [MODAL] No download icon images found - skipping modal check")
            return hwnd
        
        # Get current monitor bounds
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        monitor_width = monitor_right - monitor_left
        monitor_height = monitor_bottom - monitor_top
        
        # Search only in the upper half of the screen
        region_left = monitor_left
        region_top = monitor_top
        region_width = monitor_width
        region_height = monitor_height // 2
        
        region = (region_left, region_top, region_width, region_height)
        
        print(f"📐 [MODAL] Searching for downloads icon in upper half: {region}")
        
        # Try to find the icon
        icon_found = False
        
        # Try downloads_icon1.png first
        if os.path.exists(downloads_icon1_path):
            try:
                found_location = pyautogui.locateCenterOnScreen(
                    downloads_icon1_path,
                    region=region,
                    confidence=0.8,
                    grayscale=False
                )
                
                if found_location:
                    x, y = found_location
                    print(f"✅ [MODAL] Found downloads_icon1.png at position ({x}, {y})")
                    icon_found = True
                    
                    # Click the icon
                    enforce_window_focus(hwnd)
                    pyautogui.moveTo(x, y, duration=0.2)
                    pyautogui.click()
                    time.sleep(0.3)
                    
                    print(f"✅ [MODAL] Clicked downloads icon to dismiss modal")
                    hud.print("✅ Modal dismissed", "success")
                    update_operation_status("Download modal dismissed")
                    return hwnd
            except Exception as e:
                print(f"⚠️ [MODAL] Error searching for downloads_icon1.png: {e}")
        
        # Try downloads_icon2.png if first wasn't found
        if not icon_found and os.path.exists(downloads_icon2_path):
            try:
                found_location = pyautogui.locateCenterOnScreen(
                    downloads_icon2_path,
                    region=region,
                    confidence=0.8,
                    grayscale=False
                )
                
                if found_location:
                    x, y = found_location
                    print(f"✅ [MODAL] Found downloads_icon2.png at position ({x}, {y})")
                    icon_found = True
                    
                    # Click the icon
                    enforce_window_focus(hwnd)
                    pyautogui.moveTo(x, y, duration=0.2)
                    pyautogui.click()
                    time.sleep(0.3)
                    
                    print(f"✅ [MODAL] Clicked downloads icon to dismiss modal")
                    hud.print("✅ Modal dismissed", "success")
                    update_operation_status("Download modal dismissed")
                    return hwnd
            except Exception as e:
                print(f"⚠️ [MODAL] Error searching for downloads_icon2.png: {e}")
        
        if not icon_found:
            print(f"ℹ️ [MODAL] No downloads icon found - no modal to dismiss")
        
        return hwnd

    def get_newest_download_file_with_retry(hwnd, initial_files, timeout_seconds=120, check_interval=1.0, video_url=None, title=None):
        """
        Monitor Downloads folder for new files with retry capability.
        If download takes too long, restart the process.
        """
        print(f"📊 [DOWNLOAD_MONITOR] Starting download monitoring with retry...")
        hud.print("📊 Monitoring Downloads folder...", "waiting")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Track when we last saw a new file
        new_file_stable_count = 0
        current_new_file = None
        current_new_file_path = None
        file_detected = False
        
        # Track last check for modal
        last_modal_check = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                check_for_termination()
                
                # Get current files in Downloads
                current_files = set()
                if os.path.exists(downloads_folder):
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file():
                                current_files.add(entry.name)
                
                # Find new files (not in initial set)
                new_files = current_files - initial_files
                
                if new_files:
                    # Get the newest file (by creation time or modification time)
                    newest_file = None
                    newest_file_path = None
                    newest_time = 0
                    
                    for filename in new_files:
                        file_path = os.path.join(downloads_folder, filename)
                        try:
                            # Get creation time or modification time
                            stat = os.stat(file_path)
                            # Use creation time on Windows, modification time on other platforms
                            if os.name == 'nt':
                                file_time = stat.st_ctime  # Creation time on Windows
                            else:
                                file_time = stat.st_mtime  # Modification time on Unix
                            
                            if file_time > newest_time:
                                newest_time = file_time
                                newest_file = filename
                                newest_file_path = file_path
                        except Exception:
                            continue
                    
                    if newest_file:
                        # Check if this is the same file we saw before
                        if current_new_file != newest_file:
                            # New file detected - reset stability counter
                            current_new_file = newest_file
                            current_new_file_path = newest_file_path
                            new_file_stable_count = 0
                            file_detected = True
                            print(f"🆕 [DOWNLOAD_MONITOR] New file detected: {newest_file}")
                            hud.print(f"📥 New file detected", "success")
                            update_operation_status(f"New file detected: {newest_file}")
                        else:
                            # Same file - check if it's stable (not being written)
                            try:
                                # Check if file is still being written
                                size1 = os.path.getsize(current_new_file_path)
                                time.sleep(0.5)
                                size2 = os.path.getsize(current_new_file_path)
                                
                                if size1 == size2 and size1 > 0:
                                    # File size stable and > 0
                                    new_file_stable_count += 1
                                    print(f"✅ [DOWNLOAD_MONITOR] File stable ({new_file_stable_count}/3), size: {size1} bytes")
                                    
                                    if new_file_stable_count >= 3:
                                        print(f"✅ [DOWNLOAD_MONITOR] Download complete!")
                                        hud.print("✅ Download complete!", "success")
                                        update_operation_status("Download completed successfully")
                                        return True, current_new_file, current_new_file_path
                                else:
                                    # File still being written
                                    new_file_stable_count = 0
                                    print(f"⏳ [DOWNLOAD_MONITOR] File being written... size: {size1} → {size2}")
                                    if not file_detected:
                                        hud.print(f"⏳ Downloading...", "downloading")
                            except Exception as e:
                                print(f"⚠️ [DOWNLOAD_MONITOR] Error checking file size: {e}")
                                new_file_stable_count = 0
                
                # Check for modal every 30 seconds and dismiss if found
                current_time = time.time()
                if current_time - last_modal_check >= 30:
                    print(f"🔍 [DOWNLOAD_MONITOR] Checking for download modal (30s check)...")
                    hwnd = dismiss_download_modal_if_present(hwnd)
                    last_modal_check = current_time
                
                # If no file detected after 60 seconds, try to restart
                elapsed = int(time.time() - start_time)
                if elapsed > 60 and not file_detected:
                    print(f"⏰ [DOWNLOAD_MONITOR] No download detected after 60 seconds - restarting...")
                    hud.print("🔄 Restarting download...", "warning")
                    update_operation_status("No download detected, restarting...")
                    
                    # Dismiss any modal that might be blocking
                    hwnd = dismiss_download_modal_if_present(hwnd)
                    
                    # Reload the URL
                    if video_url:
                        print(f"🔄 [DOWNLOAD_MONITOR] Reloading URL: {video_url}")
                        enforce_window_focus(hwnd)
                        fast_paste_url(hwnd, video_url)
                        time.sleep(3)
                        hwnd = ensure_window_ready_and_focused()
                        
                        # Verify page loaded
                        success, hwnd = verify_page_loaded_individual(hwnd, max_attempts=3)
                        if success:
                            # Click download button again (this will also check for modal)
                            print(f"📥 [DOWNLOAD_MONITOR] Clicking download button again...")
                            download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
                            
                            if download_success:
                                # Reset the timer and continue monitoring
                                print(f"✅ [DOWNLOAD_MONITOR] Download restarted successfully")
                                hud.print("🔄 Download restarted", "info")
                                update_operation_status("Download restarted successfully")
                                # Reset the start time to give more time
                                start_time = time.time()
                                last_modal_check = time.time()
                                # Don't reset file_detected, keep monitoring
                                continue
                            else:
                                print(f"❌ [DOWNLOAD_MONITOR] Failed to restart download")
                                update_operation_status("Failed to restart download", is_error=True)
                        else:
                            print(f"❌ [DOWNLOAD_MONITOR] Failed to reload page")
                            update_operation_status("Failed to reload page", is_error=True)
                
                # Keep window focused
                enforce_window_focus(hwnd)
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("🛑 [DOWNLOAD_MONITOR] Download monitoring interrupted by user")
                raise
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_MONITOR] Error: {e}")
                time.sleep(check_interval)
                continue
        
        # Timeout reached
        print(f"⏰ [DOWNLOAD_MONITOR] Timeout reached after {timeout_seconds} seconds")
        hud.print("⏰ Download monitoring timed out", "error")
        error_msg = f"Download monitoring timed out after {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        
        # Try one last time to dismiss modal
        hwnd = dismiss_download_modal_if_present(hwnd)
        
        return False, None, None

    def process_individual_video(hwnd, video_url, title, project_title):
        """
        Process a single individual video URL.
        Downloads the video and saves it with the title name.
        """
        print(f"🎬 [INDIVIDUAL] Processing video: {title if title else 'Unnamed'}")
        print(f"🔗 [INDIVIDUAL] URL: {video_url}")
        hud.print(f"📥 Processing: {title if title else 'Video'}", "downloading")
        update_operation_status(f"Processing video: {title if title else 'Unnamed'}")
        
        try:
            # Step 1: Load the video URL
            success, hwnd = load_individual_video_url(hwnd, video_url)
            if not success:
                print(f"❌ [INDIVIDUAL] Failed to load URL")
                error_msg = f"Failed to load video URL"
                update_operation_status(error_msg, is_error=True)
                return False, hwnd
            
            # Step 2: Verify page is loaded (using Ctrl+B if needed, but not clicking history)
            success, hwnd = verify_page_loaded_individual(hwnd, max_attempts=5)
            if not success:
                print(f"❌ [INDIVIDUAL] Page verification failed")
                error_msg = f"Page verification failed for video"
                update_operation_status(error_msg, is_error=True)
                return False, hwnd
            
            # Step 3: Wait a moment for video to fully load
            time.sleep(1.5)
            hwnd = ensure_window_ready_and_focused()
            
            # Step 4: Get initial files in Downloads folder BEFORE clicking download
            print(f"📁 [INDIVIDUAL] Getting initial Downloads folder state...")
            initial_files = get_downloads_folder_files()
            print(f"📁 [INDIVIDUAL] Found {len(initial_files)} files in Downloads")
            
            # Step 5: Click the download button
            print(f"📥 [INDIVIDUAL] Clicking download button...")
            download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
            
            if not download_success:
                print(f"❌ [INDIVIDUAL] Failed to click download button")
                hud.print("❌ Download button not found", "error")
                error_msg = "Download button not found"
                update_operation_status(error_msg, is_error=True)
                return False, hwnd
            
            # Step 6: Monitor Downloads folder for new file with timeout
            print(f"📊 [INDIVIDUAL] Monitoring for download...")
            update_operation_status("Monitoring download progress...")
            success, downloaded_filename, downloaded_path = get_newest_download_file_with_retry(
                hwnd, 
                initial_files, 
                timeout_seconds=120, 
                check_interval=1.0,
                video_url=video_url,
                title=title
            )
            
            if not success or not downloaded_filename or not downloaded_path:
                print(f"❌ [INDIVIDUAL] Download monitoring failed")
                hud.print("❌ Download failed", "error")
                error_msg = "Download failed"
                update_operation_status(error_msg, is_error=True)
                return False, hwnd
            
            print(f"✅ [INDIVIDUAL] Download successful!")
            update_operation_status("Download successful")
            
            # Step 7: Check for and dismiss download modal
            print(f"🔍 [INDIVIDUAL] Checking for download modal...")
            hwnd = dismiss_download_modal_if_present(hwnd)
            
            # Step 8: Move to project folder with appropriate naming
            # If title is not empty, use title; otherwise use default numbering
            video_filename, ext = os.path.splitext(downloaded_filename)
            
            # Create project folder and video subfolder
            project_folder = os.path.join(IMAGES_PATH, normalize_project_title(project_title))
            if not os.path.exists(project_folder):
                os.makedirs(project_folder)
                print(f"📁 [INDIVIDUAL] Created project folder: {project_folder}")
            
            video_folder = os.path.join(project_folder, "videos")
            if not os.path.exists(video_folder):
                os.makedirs(video_folder)
                print(f"📁 [INDIVIDUAL] Created video subfolder: {video_folder}")
            
            # Determine the final filename
            if title and title.strip():
                # Use title as filename (sanitize for filesystem)
                safe_title = re.sub(r'[^a-zA-Z0-9\s_-]', '', title)
                safe_title = re.sub(r'\s+', '_', safe_title)
                final_filename = f"{safe_title}{ext}"
                print(f"📝 [INDIVIDUAL] Using title as filename: {final_filename}")
                
                # Check if file with same name exists and delete it
                final_path = os.path.join(video_folder, final_filename)
                if os.path.exists(final_path):
                    try:
                        os.remove(final_path)
                        print(f"🗑️ [INDIVIDUAL] Deleted existing file: {final_path}")
                    except Exception as e:
                        print(f"⚠️ [INDIVIDUAL] Could not delete existing file: {e}")
                        # If can't delete, use numbered version
                        video_number = 1
                        while True:
                            final_filename = f"{safe_title}_{video_number}{ext}"
                            final_path = os.path.join(video_folder, final_filename)
                            if not os.path.exists(final_path):
                                break
                            video_number += 1
                        print(f"📝 [INDIVIDUAL] Using numbered version: {final_filename}")
            else:
                # Use default numbering
                video_number = 1
                while True:
                    final_filename = f"{video_number}{ext}"
                    final_path = os.path.join(video_folder, final_filename)
                    if not os.path.exists(final_path):
                        break
                    video_number += 1
                print(f"📝 [INDIVIDUAL] Using default numbering: {final_filename}")
            
            # Move and rename the file
            final_path = os.path.join(video_folder, final_filename)
            try:
                # If file exists, delete it first
                if os.path.exists(final_path):
                    os.remove(final_path)
                    print(f"🗑️ [INDIVIDUAL] Deleted existing file at destination")
                
                os.rename(downloaded_path, final_path)
                print(f"✅ [INDIVIDUAL] Moved video to: {final_path}")
                hud.print(f"✅ Video saved: {final_filename}", "success")
                update_operation_status(f"Video saved as: {final_filename}")
                
                # Check again for modal after moving (sometimes modal appears after file is saved)
                time.sleep(0.5)
                hwnd = dismiss_download_modal_if_present(hwnd)
                
                return True, hwnd
            except Exception as e:
                print(f"❌ [INDIVIDUAL] Error moving video: {e}")
                error_msg = f"Error moving video: {str(e)}"
                update_operation_status(error_msg, is_error=True)
                return False, hwnd
                
        except Exception as e:
            print(f"❌ [INDIVIDUAL] Error processing video: {e}")
            error_msg = f"Error processing video: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error processing video", "error")
            return False, hwnd
    
    def process_individual_videos(hwnd, video_list, project_title):
        """
        Process a list of individual video URLs.
        Each video is loaded, downloaded, and saved with its title.
        """
        print(f"🎬 [INDIVIDUAL] Processing {len(video_list)} individual videos...")
        hud.print(f"📊 Processing {len(video_list)} videos", "info")
        update_operation_status(f"Processing {len(video_list)} individual videos")
        
        success_count = 0
        fail_count = 0
        
        for index, video_data in enumerate(video_list, 1):
            check_for_termination()
            
            # Extract data from the video entry
            title = video_data.get('title', '')
            url = video_data.get('url', '')
            
            if not url:
                print(f"⚠️ [INDIVIDUAL] Video {index} has no URL, skipping...")
                fail_count += 1
                continue
            
            print(f"\n{'='*60}")
            print(f"🎬 [INDIVIDUAL] Processing video {index}/{len(video_list)}")
            print(f"📝 Title: {title if title else 'Unnamed'}")
            print(f"🔗 URL: {url}")
            print(f"{'='*60}\n")
            
            # Process the individual video
            success, hwnd = process_individual_video(hwnd, url, title, project_title)
            
            if success:
                success_count += 1
                hud.print(f"✅ Video {index} completed", "success")
                update_operation_status(f"Video {index} of {len(video_list)} completed successfully")
            else:
                fail_count += 1
                hud.print(f"❌ Video {index} failed", "error")
                update_operation_status(f"Video {index} of {len(video_list)} failed", is_error=True)
            
            # Wait a bit before processing the next video
            if index < len(video_list):
                print(f"⏳ [INDIVIDUAL] Waiting before next video...")
                time.sleep(2)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"📊 [INDIVIDUAL] OPERATION SUMMARY:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Failed: {fail_count}")
        print(f"   📊 Total: {len(video_list)}")
        print(f"{'='*60}\n")
        
        if success_count > 0:
            hud.print(f"✅ Completed {success_count} videos", "success")
            update_operation_status(f"Video operation completed: {success_count} of {len(video_list)} videos downloaded", is_success=True)
            return True, hwnd
        else:
            hud.print("❌ No videos completed", "error")
            error_msg = f"All {len(video_list)} videos failed"
            update_operation_status(error_msg, is_error=True)
            return False, hwnd
    
    def main_video_workflow_with_restart(hwnd=None, video_project_url=None, prompt_id=None, project_title=None, depth=0):
        """
        Main video workflow execution with restart capability.
        Now checks for individual video URLs first.
        """
        try:
            # Load panel data once at the beginning
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return False
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Navigate to grok_config
            grok_config = panel_data.get('grok_config', {})
            operate_video = grok_config.get('operate_grok', False)
            
            if not operate_video:
                print("ℹ️ Video operation is disabled in config")
                hud.print("ℹ️ Video operation disabled", "info")
                update_operation_status("Video operation is disabled in configuration")
                return False
            
            # Get project title (from root level if not provided)
            if project_title is None:
                project_title = panel_data.get('project_title', 'video_project')
            
            # CHECK FOR INDIVIDUAL VIDEO URLs FIRST - ALWAYS CHECK THIS REGARDLESS OF PARAMETERS
            individual_videos = grok_config.get('grok_invidual_videos_url', [])
            
            # If there are individual video URLs, process them and skip the main flow
            if individual_videos and len(individual_videos) > 0:
                print(f"🎯 [MAIN] Found {len(individual_videos)} individual video URLs - using shortcut mode")
                hud.print(f"🎯 Processing {len(individual_videos)} individual videos", "info")
                update_operation_status(f"Processing {len(individual_videos)} individual videos")
                
                if hwnd is None:
                    hwnd = ensure_window_ready_and_focused()
                    print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
                
                # Process individual videos
                success, hwnd = process_individual_videos(hwnd, individual_videos, project_title)
                
                if success:
                    print(f"✅ [MAIN] {project_title} video processing completed successfully!")
                    update_operation_status(f"Video operation completed successfully", is_success=True)
                    return True
                else:
                    print(f"❌ [MAIN] Individual video processing failed")
                    error_msg = "Individual video processing failed"
                    update_operation_status(error_msg, is_error=True)
                    return False
            
            # If no individual videos, continue with the main flow
            print(f"ℹ️ [MAIN] No individual videos found - using main flow")
            
            # Get main URL and prompt ID
            if video_project_url is None:
                video_project_url = grok_config.get('grok_imagine_url')
                if not video_project_url or not video_project_url.strip():
                    print("❌ Error: 'grok_imagine_url' not configured")
                    hud.print("❌ No video URL configured", "error")
                    error_msg = "No video URL configured in grok_config"
                    update_operation_status(error_msg, is_error=True)
                    return False
            
            if prompt_id is None:
                prompt_id = grok_config.get('video_prompt_id', 'no music')
                if not prompt_id or not prompt_id.strip():
                    print("⚠️ Warning: 'video_prompt_id' not configured, using default 'no music'")
                    prompt_id = "no music"
            
            if hwnd is None:
                hwnd = ensure_window_ready_and_focused()
                print(f"🪟 [VIDEO] Browser ready (HWND: {hwnd})")
            
            print(f"🎬 [VIDEO] Starting video workflow (depth {depth})...")
            print(f"🌐 [VIDEO] URL: {video_project_url}")
            print(f"🔍 [VIDEO] Prompt ID: '{prompt_id}'")
            print(f"📁 [VIDEO] Project: '{project_title}'")
            update_operation_status(f"Starting video workflow for {project_title}")
            
            # Step 1: Check if URL is already loaded - DON'T launch immediately
            print(f"🔍 [VIDEO] Step 1: Checking if target URL is already loaded...")
            url_found, current_texts = check_current_url_contains_target(hwnd, video_project_url)
            
            if url_found:
                print(f"✅ [VIDEO] Target URL already loaded - proceeding without navigation")
                hud.print("✅ URL already loaded", "success")
                update_operation_status("Target URL already loaded")
            else:
                print(f"🔄 [VIDEO] Target URL not found - navigating to it")
                hud.print("📋 Navigating to URL...", "navigating")
                update_operation_status(f"Navigating to video URL")
                # Clean up old records before navigation
                project_folder = os.path.join(IMAGES_PATH, normalize_project_title(project_title))
                video_urls_file = os.path.join(project_folder, "video_urls.csv")
                if os.path.exists(video_urls_file):
                    try:
                        os.remove(video_urls_file)
                        print(f"🗑️ [VIDEO] Deleted old records file: {video_urls_file}")
                    except Exception as e:
                        print(f"⚠️ [VIDEO] Could not delete old records: {e}")
                
                fast_paste_url(hwnd, video_project_url)
                time.sleep(3)
                hwnd = ensure_window_ready_and_focused()
            
            # Step 2: Wait for page to load with multi-indicator check (EXCLUDING time values)
            print(f"🔍 [VIDEO] Step 2: Waiting for page to load...")
            hud.print("⏳ Checking page...", "waiting")
            update_operation_status("Waiting for page to load...")
            
            reload_attempts = 0
            max_reloads = 3
            page_loaded = False
            load_indicator = None
            
            while reload_attempts < max_reloads and not page_loaded:
                # Check for page load indicators (excluding time values)
                current_texts = safe_ocr()
                if current_texts:
                    page_loaded, load_indicator = check_for_page_load_indicators(current_texts)
                    
                    if page_loaded:
                        print(f"✅ [VIDEO] Page loaded - indicator: {load_indicator}")
                        hud.print(f"✅ Page loaded", "success")
                        update_operation_status(f"Page loaded successfully")
                        break
                
                if not page_loaded:
                    reload_attempts += 1
                    if reload_attempts < max_reloads:
                        print(f"🔄 [VIDEO] Page not loaded, reloading (attempt {reload_attempts}/{max_reloads})...")
                        hud.print(f"🔄 Reloading page ({reload_attempts}/{max_reloads})...", "warning")
                        update_operation_status(f"Page not loaded, reloading ({reload_attempts}/{max_reloads})...")
                        enforce_window_focus(hwnd)
                        pyautogui.hotkey('ctrl', 'r')
                        time.sleep(3)
                        hwnd = ensure_window_ready_and_focused()
                    else:
                        print(f"❌ [VIDEO] Page failed to load after {max_reloads} reload attempts")
                        hud.print("❌ Page load failed", "error")
                        error_msg = f"Page failed to load after {max_reloads} attempts"
                        update_operation_status(error_msg, is_error=True)
                        return False
            
            if not page_loaded:
                print("❌ [VIDEO] Page not loaded - aborting")
                error_msg = "Page not loaded - aborting video operation"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print("✅ [VIDEO] Page loaded successfully")
            
            # Step 3: Check for time value - THIS IS THE MAIN CHARACTER NOW
            print(f"🔍 [VIDEO] Step 3: Checking for time value...")
            update_operation_status("Checking for video content...")
            
            current_texts = safe_ocr()
            has_timevalue, time_element = check_for_timevalue(current_texts)
            
            if has_timevalue and time_element:
                print(f"✅ [VIDEO] Time value found! Skipping history and Ctrl+B entirely.")
                # Click the time value directly
                click_x = int(time_element['left'] + (time_element['width'] / 2))
                click_y = int(time_element['top'] + (time_element['height'] / 2))
                print(f"🎯 [VIDEO] Clicking time value at ({click_x}, {click_y})")
                enforce_window_focus(hwnd)
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.5)
                print("✅ [VIDEO] Time value clicked - proceeding directly to video player")
                update_operation_status("Video content found, proceeding...")
            else:
                # No time value found - check history and activate Ctrl+B if needed
                print(f"ℹ️ [VIDEO] No time value found - checking history...")
                update_operation_status("No video content found, checking history...")
                history_found, hwnd = activate_ctrl_b_and_check_history(hwnd, max_attempts=5)
                
                if not history_found:
                    print("❌ [VIDEO] Failed to find history option")
                    error_msg = "Failed to find history option"
                    update_operation_status(error_msg, is_error=True)
                    return False
                
                print("✅ [VIDEO] History option found - proceeding to click")
                update_operation_status("History option found, proceeding...")
                
                # Click the history button
                print(f"🎯 [VIDEO] Clicking history option...")
                
                clicked_successfully, hwnd = click_history_button(hwnd)
                
                if not clicked_successfully:
                    print("❌ [VIDEO] Failed to click history option")
                    error_msg = "Failed to click history option"
                    update_operation_status(error_msg, is_error=True)
                    return False
                
                print("✅ [VIDEO] History option clicked successfully!")
                update_operation_status("History option clicked successfully")
                
                # Wait for history panel to load
                print("⏳ [VIDEO] Waiting for history panel to load...")
                hud.print("⏳ Checking history...", "waiting")
                update_operation_status("Checking history panel...")
                
                # Find and click the first time value
                print(f"🔍 [VIDEO] Looking for first time value...")
                
                time_found, hwnd = find_and_click_video_duration(hwnd, timeout_seconds=10, check_interval=0.1)
                
                if not time_found:
                    print("❌ [VIDEO] Failed to find and click time value")
                    hud.print("❌ Couldn't find a video", "error")
                    error_msg = "Failed to find and click time value"
                    update_operation_status(error_msg, is_error=True)
                    return False
                
                print(" [VIDEO] First time value clicked successfully!")
                hud.print("🎦", "waiting")
                update_operation_status("Video content accessed")
            
            # Give the video player a moment to load
            time.sleep(2)
            hwnd = ensure_window_ready_and_focused()
            
            # OPERATION 1: Get to Latest Video
            print("=" * 60)
            print("🎬 [VIDEO] Starting Operation 1: Get to Latest Video")
            print("=" * 60)
            update_operation_status("Navigating to latest video...")
            
            latest_success, hwnd = get_to_latest_video(
                hwnd, 
                video_project_url.rstrip('/')
            )
            
            if not latest_success:
                print("❌ [VIDEO] Failed to reach latest video")
                hud.print("❌ Could not reach latest video", "error")
                error_msg = "Failed to reach latest video"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print("✅ [VIDEO] Operation 1 completed - At latest video")
            update_operation_status("Latest video reached")
            
            # OPERATION 2: Get Video Prompt IDs with Download
            print("=" * 60)
            print("🎬 [VIDEO] Starting Operation 2: Get Video Prompt IDs with Download")
            print("=" * 60)
            update_operation_status(f"Searching for videos with prompt ID: {prompt_id}")
            
            prompt_success, hwnd = get_video_prompt_ids_with_download(
                hwnd,
                video_project_url.rstrip('/'),
                prompt_id,
                project_title
            )
            
            if not prompt_success:
                print("❌ [VIDEO] Video navigation and recording failed")
                hud.print("❌ Video recording failed", "error")
                error_msg = f"Video navigation and recording failed for prompt ID: {prompt_id}"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print("🎉 [VIDEO] Video workflow completed successfully!")
            hud.print("🎉 Video workflow complete!", "success")
            update_operation_status(f"Video operation for {project_title} completed successfully", is_success=True)
            return True
            
        except KeyboardInterrupt as ki:
            update_operation_status("Video operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
            return False
        except SystemExit as se:
            # This is expected from abort_operation
            print(f"🛑 System exit: {se}")
            return False
        except Exception as e:
            print(f"❌ [VIDEO] Error: {e}")
            error_msg = f"Error in video workflow: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
            return False
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass

    def main_video_workflow():
        """Wrapper for main video workflow with restart capability."""
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
            
            # ===== SYNC: Check Google Flow status before proceeding =====
            if not check_google_flow_status():
                print("🛑 [SYNC] Google Flow was aborted - skipping video operation")
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Navigate to grok_config
            grok_config = panel_data.get('grok_config', {})
            operate_video = grok_config.get('operate_grok', False)
            
            if not operate_video:
                print("ℹ️ Video operation is disabled in config")
                hud.print("ℹ️ Video operation disabled", "info")
                update_operation_status("Video operation is disabled in configuration")
                return
            
            # Get project title (from root level)
            project_title = panel_data.get('project_title', 'video_project')
            
            # Check for individual videos from grok_config
            individual_videos = grok_config.get('grok_invidual_videos_url', [])
            video_project_url = grok_config.get('grok_imagine_url')
            
            # Validate that at least one source is available
            if not individual_videos and (not video_project_url or not video_project_url.strip()):
                print("❌ Error: No video sources configured (individual URLs or main URL)")
                hud.print("❌ No video sources configured", "error")
                error_msg = "No video sources configured (individual URLs or main URL)"
                update_operation_status(error_msg, is_error=True)
                return
            
            # Initialize browser window
            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized for video operation")
            
            # Process individual videos if they exist (they take priority)
            if individual_videos and len(individual_videos) > 0:
                print(f"🎯 [MAIN] Found {len(individual_videos)} individual video URLs - using shortcut mode")
                hud.print(f"🎯 Processing {len(individual_videos)} individual videos", "info")
                update_operation_status(f"Processing {len(individual_videos)} individual videos")
                
                # Process individual videos
                success, hwnd = process_individual_videos(hwnd, individual_videos, project_title)
                
                if success:
                    print(f"✅ [MAIN] {project_title} video processing completed successfully!")
                    update_operation_status(f"{project_title} video processing completed successfully", is_success=True)
                    return
                else:
                    print("❌ [MAIN] Individual video processing failed")
                    error_msg = "Individual video processing failed"
                    update_operation_status(error_msg, is_error=True)
                    return
            
            # If no individual videos, run the main workflow
            print(f"ℹ️ [MAIN] No individual videos found - using main flow")
            
            if not video_project_url or not video_project_url.strip():
                print("❌ Error: 'grok_imagine_url' not configured")
                hud.print("❌ No video URL configured", "error")
                error_msg = "No video URL configured in grok_config"
                update_operation_status(error_msg, is_error=True)
                return
            
            # Get prompt ID from grok_config
            prompt_id = grok_config.get('video_prompt_id', 'no music')
            
            success = main_video_workflow_with_restart(
                hwnd=hwnd, 
                video_project_url=video_project_url,
                prompt_id=prompt_id,
                project_title=project_title,
                depth=0
            )
            
            if success:
                print("✅ [MAIN] Video workflow completed successfully!")
                update_operation_status(f"Video workflow for {project_title} completed successfully", is_success=True)
            else:
                print("❌ [MAIN] Video workflow failed after multiple attempts")
                error_msg = "Video workflow failed after multiple attempts"
                update_operation_status(error_msg, is_error=True)
                
        except KeyboardInterrupt as ki:
            update_operation_status("Video operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            # This is expected from abort_operation
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            error_msg = f"Unexpected error in video operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
            
    main_video_workflow()

def operate_capcut():
    """
    Launches/uses CapCut for video operations.
    Features: Live HUD tracking, click-through overlay,
    global hotkey interception, and CapCut-specific workflow.
    Currently: Opens CapCut, finds and clicks "Create new project" text, stops there.
    """
    # --- SPEED TUNING PARAMETERS ---
    pyautogui.PAUSE = 0.0
    
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return

    with open(PANEL_PATH, 'r', encoding='utf-8') as file:
        panel_data = json.load(file)

    project_title = panel_data.get('project_title')
    
    terminate_automation = False
    operation_status_flag = True
    operation_status_message = ""
    operation_aborted = False

    def update_operation_status(message, is_error=False, is_abort=False, is_success=False):
        """
        Update the operation status in panel.json with a professional message.
        
        Args:
            message: The status message to write
            is_error: Whether this is an error state
            is_abort: Whether this is an abortion state
            is_success: Whether this is a success state
        """
        nonlocal operation_status_message, operation_status_flag, operation_aborted
        
        try:
            # Read current panel data
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                current_panel = json.load(file)
            
            # Format the status message professionally
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
            
            # Update the operation_status field
            current_panel['operation_status'] = operation_status_message
            
            # Write back to file
            with open(PANEL_PATH, 'w', encoding='utf-8') as file:
                json.dump(current_panel, file, indent=4, ensure_ascii=False)
            
            # If aborted, we should stop the program
            if is_abort:
                print(f"🛑 [STATUS] Operation aborted: {message}")
                raise SystemExit(f"Operation aborted: {message}")
                
        except Exception as e:
            print(f"⚠️ [STATUS] Failed to update operation status: {e}")

    def abort_operation(reason):
        """Abort the operation with a specific reason."""
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting CapCut operation: {reason}", is_abort=True)

    def check_operation_status():
        """Check if operation status is still valid (not aborted/errored)."""
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting CapCut operation", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status("CapCut operation manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status("CapCut operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

    def safe_ocr():
        """Capture screen without hiding the HUD (HUD is click-through)"""
        check_for_termination()
        return ocr()

    def normalize_text_for_comparison(text):
        """More aggressive normalization for text matching"""
        if not text:
            return ""
        t = text.lower()
        t = re.sub(r'[^a-z0-9]', '', t)
        return t

    # ============================================
    # SECTION 1: WINDOW MANAGEMENT HELPERS
    # ============================================
    
    def get_current_monitor():
        try:
            cursor_pos = win32api.GetCursorPos()
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint(cursor_pos))
            return monitor_info['Monitor']
        except Exception:
            return (0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN), 
                   win32api.GetSystemMetrics(win32con.SM_CYSCREEN))
    
    def get_capcut_window_on_monitor(monitor_bounds):
        """Get CapCut window on specified monitor"""
        monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_bounds
        capcut_windows = []
        capcut_process_names = ["capcut.exe", "CapCut.exe"]
        
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    if process.name().lower() in [p.lower() for p in capcut_process_names]:
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
        
        win32gui.EnumWindows(enum_windows_callback, capcut_windows)
        capcut_windows.sort(key=lambda w: w['width'] * w['height'], reverse=True)
        return capcut_windows

    def find_latest_capcut_path():
        """
        Dynamically find the latest CapCut executable path.
        Searches in common locations and returns the path with the highest version number.
        """
        print(f"🔍 [CAPCUT] Searching for CapCut executable...")
        
        # Define base search paths
        search_paths = [
            os.path.join(os.environ.get('USERPROFILE', ''), 'CapCut'),
            r"C:\Program Files\CapCut",
            r"C:\Program Files (x86)\CapCut",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CapCut'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'CapCut'),
            os.path.join(os.environ.get('APPDATA', ''), 'CapCut'),
        ]
        
        found_versions = []
        
        # Search for CapCut.exe in all possible locations
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
            
            print(f"🔍 [CAPCUT] Searching in: {search_path}")
            
            # Check if CapCut.exe exists directly in this path
            direct_path = os.path.join(search_path, 'CapCut.exe')
            if os.path.exists(direct_path):
                # Try to extract version from parent directory name
                version = os.path.basename(search_path)
                # If the directory name doesn't look like a version, use a default
                if not re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                    version = '0.0.0.0'
                found_versions.append((version, direct_path))
                print(f"   ✅ Found: {direct_path} (version: {version})")
            
            # Check for version subdirectories
            try:
                for item in os.listdir(search_path):
                    item_path = os.path.join(search_path, item)
                    if os.path.isdir(item_path):
                        # Check if this directory contains CapCut.exe
                        exe_path = os.path.join(item_path, 'CapCut.exe')
                        if os.path.exists(exe_path):
                            # Try to extract version from directory name
                            version = item
                            if not re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                                # Try to extract version from directory name with pattern
                                version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', item)
                                if version_match:
                                    version = version_match.group(1)
                                else:
                                    version = '0.0.0.0'
                            found_versions.append((version, exe_path))
                            print(f"   ✅ Found: {exe_path} (version: {version})")
            except Exception as e:
                print(f"   ⚠️ Error scanning {search_path}: {e}")
        
        # If no versions found, try a more aggressive search
        if not found_versions:
            print(f"🔍 [CAPCUT] No CapCut found in common locations, performing deep search...")
            
            # Search in user's home directory
            home_dir = os.environ.get('USERPROFILE', '')
            if home_dir:
                for root, dirs, files in os.walk(home_dir):
                    if 'CapCut.exe' in files:
                        exe_path = os.path.join(root, 'CapCut.exe')
                        # Try to extract version from path
                        version_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', root)
                        if version_match:
                            version = version_match.group(1)
                        else:
                            # Try to get version from file properties
                            try:
                                import win32api
                                info = win32api.GetFileVersionInfo(exe_path, "\\")
                                version = f"{info['FileVersionMS'] >> 16}.{info['FileVersionMS'] & 0xFFFF}.{info['FileVersionLS'] >> 16}.{info['FileVersionLS'] & 0xFFFF}"
                            except:
                                version = '0.0.0.0'
                        found_versions.append((version, exe_path))
                        print(f"   ✅ Found: {exe_path} (version: {version})")
                        break  # Stop after finding first one to avoid too many results
        
        if not found_versions:
            print(f"❌ [CAPCUT] No CapCut executable found")
            return None
        
        # Sort by version and return the latest
        def parse_version(version_str):
            try:
                return tuple(map(int, version_str.split('.')))
            except:
                return (0, 0, 0, 0)
        
        found_versions.sort(key=lambda x: parse_version(x[0]), reverse=True)
        latest_version, latest_path = found_versions[0]
        
        print(f"✅ [CAPCUT] Latest version found: {latest_version} at {latest_path}")
        return latest_path

    def handle_capcut_loading(hwnd, timeout_seconds=60, check_interval=0.5):
        """
        Handle CapCut's loading process including:
        - "Running environment" screen
        - "Confirm" button clicks
        - Wait for main window to fully appear
        """
        print(f"⏳ [CAPCUT] Handling CapCut loading process...")
        hud.print("⏳ CapCut is loading...", "waiting")
        update_operation_status("CapCut loading, please wait...")
        
        start_time = time.time()
        confirm_clicked = False
        main_window_detected = False
        
        # First, wait for any window to appear
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            
            # Check if CapCut main window exists
            current_monitor = get_current_monitor()
            capcut_windows = get_capcut_window_on_monitor(current_monitor)
            
            if capcut_windows:
                hwnd = capcut_windows[0]['hwnd']
                print(f"🪟 [CAPCUT] Found CapCut window: {hwnd}")
                
                # Try to bring it to focus
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.3)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.2)
                except:
                    pass
                
                # Check for "Confirm" button or similar text
                print(f"🔍 [CAPCUT] Checking for Confirm button...")
                current_texts = safe_ocr()
                
                if current_texts:
                    confirm_found = False
                    confirm_element = None
                    
                    # Look for "Confirm", "Continue", "OK", "Yes" buttons
                    confirm_variations = ["confirm", "continue", "ok", "yes", "accept"]
                    
                    for element in current_texts:
                        element_text = element['text'].strip().lower()
                        normalized_element = normalize_text_for_comparison(element_text)
                        
                        for variation in confirm_variations:
                            if variation in normalized_element or variation == normalized_element:
                                confirm_found = True
                                confirm_element = element
                                print(f"✅ [CAPCUT] Found '{element_text}' button")
                                break
                        
                        if confirm_found:
                            break
                    
                    if confirm_found and confirm_element and not confirm_clicked:
                        # Click the confirm button
                        click_x = int(confirm_element['left'] + (confirm_element['width'] / 2))
                        click_y = int(confirm_element['top'] + (confirm_element['height'] / 2))
                        
                        print(f"🎯 [CAPCUT] Clicking Confirm at position ({click_x}, {click_y})")
                        hud.print("✅ Clicking Confirm...", "success")
                        update_operation_status("Clicking Confirm button...")
                        
                        pyautogui.moveTo(click_x, click_y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        confirm_clicked = True
                        print(f"✅ [CAPCUT] Confirm button clicked")
                        
                        # Wait for main window after clicking
                        time.sleep(3)
                        continue
                    
                    # Check if main window has loaded (look for typical CapCut UI elements)
                    main_indicators = ["timeline", "video", "audio", "media", "export", "project"]
                    for indicator in main_indicators:
                        for element in current_texts:
                            element_text = element['text'].strip().lower()
                            normalized_element = normalize_text_for_comparison(element_text)
                            if indicator in normalized_element:
                                main_window_detected = True
                                print(f"✅ [CAPCUT] Main window detected - found '{indicator}'")
                                update_operation_status("CapCut main window loaded")
                                return True, hwnd
                
                # If we clicked confirm but main window not detected yet, keep waiting
                if confirm_clicked:
                    print(f"⏳ [CAPCUT] Waiting for main window...")
                    time.sleep(check_interval)
                    continue
                
                # Check if window size is large enough (might be loaded)
                if capcut_windows:
                    window = capcut_windows[0]
                    if window['width'] > 800 and window['height'] > 600:
                        print(f"✅ [CAPCUT] Large window detected - assuming loaded")
                        update_operation_status("CapCut window loaded")
                        return True, hwnd
            
            # If no window found yet, wait and try again
            time.sleep(check_interval)
            
            # Show progress every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 10 == 0:
                print(f"⏳ [CAPCUT] Still loading... ({elapsed}s)")
                hud.print(f"⏳ Loading CapCut... ({elapsed}s)", "waiting")
                update_operation_status(f"CapCut loading... ({elapsed}s)")
        
        print(f"❌ [CAPCUT] Timeout waiting for CapCut to load")
        return False, hwnd

    def ensure_capcut_window_ready():
        """Ensure CapCut window exists and is maximized/focused"""
        check_for_termination()
        
        # Get CapCut executable path dynamically
        capcut_path = find_latest_capcut_path()
        
        if not capcut_path:
            error_msg = "CapCut executable not found on system"
            print(f"❌ [CAPCUT] {error_msg}")
            hud.print("❌ CapCut not found", "error")
            update_operation_status(error_msg, is_error=True)
            abort_operation(error_msg)
            raise RuntimeError(error_msg)
        
        print(f"✅ [CAPCUT] Using CapCut at: {capcut_path}")
        
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        print(f"🖥️ [MONITOR] Bounds: ({monitor_left}, {monitor_top}) to ({monitor_right}, {monitor_bottom})")
        print(f"📐 [MONITOR] Size: {monitor_right - monitor_left} x {monitor_bottom - monitor_top} pixels")
        
        capcut_windows = get_capcut_window_on_monitor(current_monitor)
        
        if capcut_windows:
            hwnd = capcut_windows[0]['hwnd']
            print(f"🪟 [WINDOW] Found existing CapCut window handle: {hwnd}")
            print(f"📏 [WINDOW] Size: {capcut_windows[0]['width']} x {capcut_windows[0]['height']}")
            
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
                update_operation_status("CapCut window ready")
                
                # Handle loading process if needed
                success, hwnd = handle_capcut_loading(hwnd)
                if success:
                    return hwnd
                else:
                    print(f"⚠️ [CAPCUT] Loading handling failed, but continuing...")
                    return hwnd
                    
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        # No CapCut window found, launch new instance
        print(f"💻 [WINDOW] No CapCut window found, launching new instance...")
        print(f"🚀 [WINDOW] Launching: {capcut_path}")
        update_operation_status("Launching CapCut...")
        subprocess.Popen([capcut_path])
        
        # Wait for the window to appear with loading handling
        print(f"⏳ [WINDOW] Waiting for CapCut to launch and load...")
        hud.print("⏳ Launching CapCut...", "waiting")
        
        for attempt in range(60):  # Wait up to 30 seconds for initial window
            check_for_termination()
            time.sleep(0.5)
            capcut_windows = get_capcut_window_on_monitor(current_monitor)
            if capcut_windows:
                hwnd = capcut_windows[0]['hwnd']
                print(f"🪟 [WINDOW] New CapCut window launched, handle: {hwnd}")
                
                try:
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        time.sleep(0.3)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.5)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.2)
                    print("✅ [WINDOW] New window ready - maximized and focused")
                    update_operation_status("CapCut window ready")
                    
                    # Handle loading process
                    success, hwnd = handle_capcut_loading(hwnd)
                    if success:
                        return hwnd
                    else:
                        print(f"⚠️ [CAPCUT] Loading handling failed, but continuing...")
                        return hwnd
                        
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
            
            # Show progress every 10 seconds
            if attempt > 0 and attempt % 20 == 0:
                print(f"⏳ [WINDOW] Still waiting for CapCut... ({attempt/2}s)")
                hud.print(f"⏳ Waiting for CapCut... ({attempt/2}s)", "waiting")
        
        error_msg = "Failed to get or launch CapCut window"
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
            except Exception as e:
                print(f"⚠️ [FOCUS] Could not check maximize state, attempting maximize anyway: {e}")
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    time.sleep(0.3)
                except:
                    pass
            
            return True
        except Exception as e:
            print(f"⚠️ [FOCUS] Focus correction exception: {e}")
            return False

    # ============================================
    # SECTION 2: CAPCUT-SPECIFIC HELPERS
    # ============================================
    
    def wait_for_text_on_screen(target_text, timeout_seconds=15, check_interval=0.2):
        """
        Wait for specific text to appear on screen using OCR.
        Returns: (found, text_elements)
        """
        print(f"🔍 [OCR] Waiting for text: '{target_text}'")
        
        normalized_target = normalize_text_for_comparison(target_text)
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            
            current_texts = safe_ocr()
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    
                    if normalized_target in normalized_element:
                        print(f"✅ [OCR] Found text: '{element_text}'")
                        return True, current_texts
            
            time.sleep(check_interval)
        
        print(f"❌ [OCR] Text not found within {timeout_seconds}s: '{target_text}'")
        return False, None

    def click_text_on_screen(hwnd, target_text, timeout_seconds=15, check_interval=0.2):
        """
        Find text using OCR and click it.
        Returns: (success, hwnd)
        """
        print(f"🎯 [CLICK] Looking for text to click: '{target_text}'")
        hud.print(f"🔍 Finding: {target_text}...", "searching")
        update_operation_status(f"Looking for '{target_text}'...")
        
        normalized_target = normalize_text_for_comparison(target_text)
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_ocr()
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    
                    if normalized_target in normalized_element:
                        click_x = int(element['left'] + (element['width'] / 2))
                        click_y = int(element['top'] + (element['height'] / 2))
                        
                        print(f"🎯 [CLICK] Found '{target_text}' at position ({click_x}, {click_y})")
                        print(f"🎯 [CLICK] Text: '{element_text}'")
                        
                        enforce_window_focus(hwnd)
                        pyautogui.moveTo(click_x, click_y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        print(f"✅ [CLICK] Successfully clicked '{target_text}'")
                        hud.print(f"✅ Clicked: {target_text}", "success")
                        update_operation_status(f"Clicked '{target_text}' successfully")
                        return True, hwnd
            
            time.sleep(check_interval)
        
        print(f"❌ [CLICK] Could not find text within {timeout_seconds}s: '{target_text}'")
        hud.print(f"❌ Not found: {target_text}", "error")
        error_msg = f"Could not find '{target_text}' on screen within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, hwnd

    def capcut_create_new_project_workflow(hwnd):
        """
        CapCut workflow: Find and click "Create new project" text.
        Stops after clicking and waits for the project window to appear.
        """
        print("🎬 [CAPCUT] Starting CapCut workflow...")
        update_operation_status("Starting CapCut workflow...")
        
        # Step 1: Wait for CapCut to fully load
        print(f"⏳ [CAPCUT] Waiting for CapCut interface to load...")
        hud.print("⏳ Waiting for CapCut...", "waiting")
        time.sleep(3)
        
        # Step 2: Look for "Create new project" text
        print(f"🔍 [CAPCUT] Looking for 'Create new project'...")
        hud.print("🔍 Looking for Create new project...", "searching")
        update_operation_status("Searching for 'Create new project'...")
        
        # Try multiple variations of the text
        text_variations = [
            "Create new project",
            "New project",
            "Create project",
            "Create"
        ]
        
        found = False
        for variation in text_variations:
            print(f"🔍 [CAPCUT] Trying variation: '{variation}'")
            success, hwnd = click_text_on_screen(
                hwnd, 
                variation, 
                timeout_seconds=5, 
                check_interval=0.2
            )
            
            if success:
                found = True
                print(f"✅ [CAPCUT] Successfully clicked '{variation}'")
                update_operation_status(f"Clicked '{variation}' successfully")
                break
        
        if not found:
            print(f"❌ [CAPCUT] Could not find 'Create new project' button")
            hud.print("❌ Create new project not found", "error")
            error_msg = "Could not find 'Create new project' button in CapCut"
            update_operation_status(error_msg, is_error=True)
            return False, hwnd
        
        # Step 3: Wait for the project window to appear
        print(f"⏳ [CAPCUT] Waiting for project window to appear...")
        hud.print("⏳ Waiting for project window...", "waiting")
        update_operation_status("Waiting for CapCut project window...")
        time.sleep(3)
        
        # Step 4: Verify the project window loaded by checking for common elements
        print(f"🔍 [CAPCUT] Verifying project window is loaded...")
        
        # Look for common CapCut project window indicators
        project_indicators = [
            "timeline",
            "video",
            "audio",
            "media",
            "export"
        ]
        
        found_indicator = False
        for indicator in project_indicators:
            success, _ = wait_for_text_on_screen(indicator, timeout_seconds=3, check_interval=0.3)
            if success:
                found_indicator = True
                print(f"✅ [CAPCUT] Project window verified - found '{indicator}'")
                update_operation_status(f"CapCut project window loaded - found '{indicator}'")
                break
        
        if not found_indicator:
            print(f"ℹ️ [CAPCUT] Project window appears to be loaded (no specific indicator found)")
            update_operation_status("CapCut project window loaded")
        
        print(f"✅ [CAPCUT] CapCut workflow completed - stopped at project window")
        hud.print("✅ CapCut ready at project window", "success")
        update_operation_status("CapCut workflow completed - ready at project window", is_success=True)
        
        return True, hwnd

    # ============================================
    # SECTION 3: MAIN CAPCUT WORKFLOW
    # ============================================
    
    def main_capcut_workflow():
        """Main CapCut workflow execution."""
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Navigate to capcut_config
            capcut_config = panel_data.get('capcut_config', {})
            operate_capcut = capcut_config.get('operate_capcut', False)
            
            if not operate_capcut:
                print("ℹ️ CapCut operation is disabled in config")
                hud.print("ℹ️ CapCut operation disabled", "info")
                update_operation_status("CapCut operation is disabled in configuration")
                return
            
            print("🎬 [MAIN] Starting CapCut operation...")
            hud.print("🎬 Starting CapCut...", "info")
            update_operation_status("Starting CapCut operation...")
            
            # Initialize CapCut window
            hwnd = ensure_capcut_window_ready()
            print(f"🪟 [MAIN] CapCut ready (HWND: {hwnd})")
            update_operation_status("CapCut initialized")
            
            # Run the CapCut workflow
            success, hwnd = capcut_create_new_project_workflow(hwnd)
            
            if success:
                print("✅ [MAIN] CapCut workflow completed successfully!")
                update_operation_status("CapCut workflow completed successfully", is_success=True)
            else:
                print("❌ [MAIN] CapCut workflow failed")
                error_msg = "CapCut workflow failed"
                update_operation_status(error_msg, is_error=True)
            
        except KeyboardInterrupt as ki:
            update_operation_status("CapCut operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            error_msg = f"Unexpected error in CapCut operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    
    # Execute the main workflow
    main_capcut_workflow()
       
def run_operation():
    operate_google_flow_browser()
    operate_grok_browser()

if __name__ == "__main__":
   operate_capcut()
    
