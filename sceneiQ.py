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

def operate_google_flow_browser():
    """
    Launches Microsoft Edge, maximizes it.
    Features: Live HUD tracking, click-through overlay, 
    global hotkey interception, and step routing matrices.
    """
    # --- SPEED TUNING PARAMETERS ---
    pyautogui.PAUSE = 0.0  
    
    terminate_automation = False

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            raise KeyboardInterrupt("User forced exit via shortcut key.")

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
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
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
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        raise RuntimeError("Failed to get or launch Edge window")

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
        print("🛡️ [ALL_WATCHDOG] Starting all projects watchdog...")
        hud.print("🔍 Analyzing page context...", "searching")
        
        if depth > 5:
            print("❌ [ALL_WATCHDOG] Max recursion depth reached")
            hud.print("❌ Watchdog recursion limit", "error")
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
            return True, False, False, hwnd
        
        # If we're on a project page
        if on_project:
            print("✅ [ALL_WATCHDOG] On a specific project page")
            hud.print("📋 On project page", "info")
            
            if project_found:
                print("✅ [ALL_WATCHDOG] Target project identified on page")
                hud.print("✅ Project verified", "success")
                return False, True, True, hwnd
            else:
                print(f"⚠️ [ALL_WATCHDOG] On project page but target project not found")
                hud.print("⚠️ Project mismatch", "warning")
                return False, True, False, hwnd
        
        # Context unknown - navigate to all projects
        print("❌ [ALL_WATCHDOG] Page context unknown, navigating to all projects...")
        hud.print("❌ Page context unknown, navigating...", "error")
        fast_paste_url(hwnd, all_project_url)
        time.sleep(3)
        return all_project_watchdog(hwnd, all_project_url, project_title, depth + 1)

    def wait_for_all_projects_page_ready(hwnd, all_project_url, project_title, timeout_seconds=60, depth=0):
        """Wait for All Projects page to be ready with context analysis on each attempt."""
        print("⏳ [ALL_READY] Waiting for All Projects page to load...")
        hud.print("⏳ Loading projects list...", "waiting")
        
        if depth > 5:
            print("❌ [ALL_READY] Max recursion depth reached")
            hud.print("❌ Page ready timeout", "error")
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
                return True, hwnd
            
            # If on project page with wrong project, navigate back
            if on_project and not project_found:
                print(f"⚠️ [ALL_READY] On project page but wrong project (attempt {specific_attempts + 1})")
                hud.print("⚠️ Wrong project, navigating back...", "warning")
                
                if specific_attempts < 3:
                    fast_paste_url(hwnd, all_project_url)
                    time.sleep(3)
                    specific_attempts += 1
                    continue
                else:
                    print("🔄 [ALL_READY] Too many attempts, proceeding with specific page")
                    hud.print("📋 Proceeding with current page...", "info")
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
                    return True, hwnd
            
            # If context unknown, navigate
            if context == "unknown":
                print(f"⏳ [ALL_READY] Context unknown, navigating to all projects...")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                continue
            
            # Not ready yet, wait and retry
            elapsed = int(time.time() - start_time)
            print(f"⏳ [ALL_READY] Waiting for page to be ready... ({elapsed}s)")
            hud.print(f"⏳ Loading... ({elapsed}s)", "waiting")
            time.sleep(1.0)
        
        print("❌ [ALL_READY] Timeout - attempting recovery...")
        hud.print("🔄 Attempting recovery...", "warning")
        fast_paste_url(hwnd, all_project_url)
        time.sleep(3)
        return wait_for_all_projects_page_ready(hwnd, all_project_url, project_title, timeout_seconds, depth + 1)

    def scroll_in_all_projects(hwnd, all_project_url, project_title, depth=0):
        """Scroll through All Projects page to find the project card with context analysis."""
        print("⬇️ [SCROLL_ALL] Starting scroll in All Projects page...")
        hud.print("🔍 Searching for target...", "searching")
        
        if depth > 5:
            print("❌ [SCROLL_ALL] Max recursion depth reached - restarting")
            hud.print("🔄 Restarting search...", "warning")
            return False, None, hwnd
        
        if not project_title or not project_title.strip():
            print("❌ [SCROLL_ALL] Project name is empty!")
            hud.print("❌ Project name missing", "error")
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
                return True, None, hwnd
            
            # If on wrong project page, navigate back
            if on_project and not project_found:
                print("⚠️ [SCROLL_ALL] On wrong project page - navigating back")
                hud.print("⚠️ Wrong project, navigating back...", "warning")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                recovery_attempts += 1
                if recovery_attempts > 3:
                    print("🔄 [SCROLL_ALL] Too many recovery attempts, restarting...")
                    return scroll_in_all_projects(hwnd, all_project_url, project_title, depth + 1)
                continue
            
            # If context unknown, navigate
            if context == "unknown":
                print("⚠️ [SCROLL_ALL] Page context unknown - navigating to all projects")
                hud.print("⚠️ Page context lost, navigating...", "warning")
                fast_paste_url(hwnd, all_project_url)
                time.sleep(3)
                continue
            
            # If not on all projects, navigate
            if not on_all:
                print("⚠️ [SCROLL_ALL] Not on all projects page - navigating...")
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
                        fast_paste_url(hwnd, all_project_url)
                        time.sleep(3)
                        return scroll_in_all_projects(hwnd, all_project_url, project_title, depth + 1)
            else:
                scroll_attempts = 0
                previous_fingerprint = current_fingerprint
            
            if scroll_direction == "down":
                print("⬇️ [SCROLL_ALL] Scrolling down...")
                hud.print("⬇️ Scrolling...", "navigating")
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(-500)
                time.sleep(1.5)
            else:
                print("⬆️ [SCROLL_ALL] Scrolling up...")
                hud.print("⬆️ Scrolling...", "navigating")
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(500)
                time.sleep(1.5)

    def click_project_card(hwnd, card_element, all_project_url, project_title, depth=0):
        """Click on the project card with context analysis on each attempt."""
        print("🎯 [CLICK] Clicking project card...")
        hud.print("🎯 Selecting target...", "selecting")
        
        if depth > 5:
            print("❌ [CLICK] Max recursion depth reached - restarting")
            hud.print("🔄 Restarting selection...", "warning")
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
            return True, hwnd
        
        # If no card element provided, we need to find it
        if card_element is None:
            print("ℹ️ [CLICK] No card element provided - attempting to find it")
            
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
                return False, hwnd
        
        # Calculate click position
        click_x = int(card_element['left'] + (card_element['width'] / 2))
        click_y = int(card_element['top'] - 50)  # Click above the text to avoid text selection
        
        print(f"🎯 [CLICK] Selecting at position: ({click_x}, {click_y})")
        hud.print("📍 Selecting target...", "selecting")
        
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
            return True, hwnd
        
        # If we're on all projects still, click might have failed or SPA didn't navigate
        if on_all:
            print("⚠️ [CLICK] Still on all projects page - trying click at different position")
            hud.print("⚠️ Retrying selection...", "warning")
            
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
                return True, hwnd
        
        # If context unknown, navigate to all projects and retry
        if context == "unknown":
            print("⚠️ [CLICK] Page context unknown - navigating to all projects")
            fast_paste_url(hwnd, all_project_url)
            time.sleep(3)
            return click_project_card(hwnd, card_element, all_project_url, project_title, depth + 1)
        
        print("❌ [CLICK] Failed to open target - restarting")
        hud.print("🔄 Restarting operation...", "warning")
        return click_project_card(hwnd, card_element, all_project_url, project_title, depth + 1)

    # ============================================
    # SECTION 4: SELF-HEALING HELPERS FOR SPECIFIC PROJECT PAGE
    # ============================================
    
    def specific_project_watchdog(hwnd, specific_url, project_title, depth=0):
        """Watchdog for Specific Project page with context analysis first."""
        print("🛡️ [SPEC_WATCHDOG] Starting specific project watchdog...")
        hud.print("🔍 Analyzing page context...", "searching")
        
        if depth > 5:
            print("❌ [SPEC_WATCHDOG] Max recursion depth reached")
            hud.print("❌ Watchdog recursion limit", "error")
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
            
            if project_found:
                print("✅ [SPEC_WATCHDOG] Project verification successful")
                hud.print("✅ Project verified", "success")
                return True, True, hwnd
            else:
                print(f"⚠️ [SPEC_WATCHDOG] On project page but target project not found")
                hud.print("⚠️ Project mismatch", "warning")
                return True, False, hwnd
        
        # If on all projects page, navigate to project
        if on_all:
            print("🔄 [SPEC_WATCHDOG] On all projects page - navigating to project")
            hud.print("🔄 Navigating to project...", "warning")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return specific_project_watchdog(hwnd, specific_url, project_title, depth + 1)
        
        # If context unknown, navigate to project
        print("❌ [SPEC_WATCHDOG] Page context unknown - navigating to project")
        hud.print("❌ Page context unknown, navigating...", "error")
        fast_paste_url(hwnd, specific_url)
        time.sleep(3)
        return specific_project_watchdog(hwnd, specific_url, project_title, depth + 1)

    def wait_for_specific_page_ready(hwnd, specific_url, project_title, timeout_seconds=60, depth=0):
        """Wait for Specific Project page to be ready with context analysis."""
        print("⏳ [SPEC_READY] Waiting for project page to load...")
        hud.print("⏳ Loading project page...", "waiting")
        
        if depth > 5:
            print("❌ [SPEC_READY] Max recursion depth reached")
            hud.print("❌ Page ready timeout", "error")
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
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                continue
            
            # If not on project page and context unknown, navigate
            if not on_project and context == "unknown":
                print(f"⏳ [SPEC_READY] Context unknown, navigating to project...")
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
                    
                    # Verify project name
                    if project_found:
                        print(f"✅ [SPEC_READY] Target project confirmed on page")
                        return True, True, hwnd
                    else:
                        print(f"⚠️ [SPEC_READY] Target project not found on page - will try to scroll")
                        scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                            hwnd, specific_url, project_title, depth + 1
                        )
                        if found_after_scroll:
                            return True, True, recovered_hwnd
                        return True, False, recovered_hwnd
            
            elapsed = int(time.time() - start_time)
            print(f"⏳ [SPEC_READY] Waiting for page to be ready... ({elapsed}s)")
            hud.print(f"⏳ Loading... ({elapsed}s)", "waiting")
            time.sleep(1.0)
        
        print("❌ [SPEC_READY] Timeout - attempting recovery...")
        hud.print("🔄 Attempting recovery...", "warning")
        fast_paste_url(hwnd, specific_url)
        time.sleep(3)
        return wait_for_specific_page_ready(hwnd, specific_url, project_title, timeout_seconds, depth + 1)

    def scroll_in_specific_project(hwnd, specific_url, project_title, depth=0):
        """
        Scroll in Specific Project page with context analysis.
        Only scrolls up twice, then navigates back if not found.
        """
        print("⬆️ [SCROLL_SPEC] Starting scroll in specific project page...")
        hud.print("🔍 Verifying page content...", "searching")
        
        if depth > 5:
            print("❌ [SCROLL_SPEC] Max recursion depth reached - navigating back")
            hud.print("🔄 Navigating back...", "warning")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return False, False, hwnd
        
        if not project_title or not project_title.strip():
            print("❌ [SCROLL_SPEC] Project name is empty!")
            hud.print("❌ Project name missing", "error")
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
            hud.print("✅ Project verified", "success")
            return True, True, hwnd
        
        # If on all projects page, navigate to project
        if on_all:
            print("⚠️ [SCROLL_SPEC] On all projects page - navigating to project")
            hud.print("⚠️ Navigating to project...", "warning")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # If not on project page, navigate
        if not on_project:
            print("⚠️ [SCROLL_SPEC] Not on project page - navigating...")
            hud.print("⚠️ Navigating to project...", "warning")
            fast_paste_url(hwnd, specific_url)
            time.sleep(3)
            return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # Target not found - perform up to 2 scrolls
        print("⬆️ [SCROLL_SPEC] Target not visible, scrolling up (max 2 attempts)...")
        hud.print("⬆️ Scrolling to locate target...", "navigating")
        
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
            
            # Analyze context after scroll
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, specific_url, project_title
            )
            
            print(f"📊 [SCROLL_SPEC] After scroll {scroll_count} context: {context}, on_project={on_project}, project_found={project_found}")
            
            # If project found, we're done
            if project_found:
                print(f"✅ [SCROLL_SPEC] Target found after scroll {scroll_count}")
                hud.print("✅ Project verified", "success")
                return True, True, hwnd
            
            # If not on project page anymore, navigate back
            if not on_project:
                print("⚠️ [SCROLL_SPEC] Not on project page anymore - navigating back")
                hud.print("⚠️ Page context lost", "warning")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return scroll_in_specific_project(hwnd, specific_url, project_title, depth + 1)
        
        # After max scrolls, if not found, navigate back to all projects
        print("❌ [SCROLL_SPEC] Target not found after max scroll attempts - navigating back to all projects")
        hud.print("❌ Project not found, returning...", "error")
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
        
        When a new zip file is detected, it immediately signals for extraction.
        
        Args:
            hwnd: Window handle for focus management
            timeout_seconds: Maximum time to wait for download (default 5 minutes)
            check_interval: Seconds between checks (default 0.1 seconds - 100ms)
        
        Returns:
            tuple: (success, zip_file_path, zip_filename) or (False, None, None)
        """
        print("📊 [DOWNLOAD_STATUS] Starting download status monitor (100ms precision)...")
        hud.print("📊 Monitoring download progress...", "waiting")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Track existing zip files before download starts
        existing_zips = set()
        if os.path.exists(downloads_folder):
            for file in os.listdir(downloads_folder):
                if file.endswith('.zip'):
                    existing_zips.add(file)
            print(f"📁 [DOWNLOAD_STATUS] Found {len(existing_zips)} existing .zip files")
        
        download_started = False
        downloading_active = False
        confirmation_waited = False
        previous_downloading_status = False
        new_zip_detected = False
        new_zip_path = None
        new_zip_name = None
        
        # For performance tracking
        last_status_update = 0
        status_update_interval = 2  # Update HUD every 2 seconds
        
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
                                    if entry.name not in existing_zips:
                                        # New zip file detected!
                                        new_zip_path = entry.path
                                        new_zip_name = entry.name
                                        new_zip_detected = True
                                        print(f"✅ [DOWNLOAD_STATUS] New zip file detected: {entry.name}")
                                        hud.print(f"✅ Zip file detected!", "success")
                                        
                                        # Immediately add to existing zips to prevent re-detection
                                        existing_zips.add(entry.name)
                                        
                                        # Return immediately with the zip file info
                                        return True, new_zip_path, new_zip_name
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
                
                # Check if download is still active
                if download_started and not downloading_found and previous_downloading_status:
                    # Download text just disappeared - might be complete
                    if not confirmation_waited:
                        print("🔍 [DOWNLOAD_STATUS] 'Downloading' text disappeared - verifying completion...")
                        hud.print("🔍 Verifying download completion...", "verifying")
                        confirmation_waited = True
                        
                        # Wait up to 5 seconds for zip to appear (checking every 100ms)
                        wait_start = time.time()
                        while time.time() - wait_start < 5:
                            try:
                                if os.path.exists(downloads_folder):
                                    with os.scandir(downloads_folder) as entries:
                                        for entry in entries:
                                            if entry.is_file() and entry.name.endswith('.zip') and entry.name not in existing_zips:
                                                new_zip_path = entry.path
                                                new_zip_name = entry.name
                                                new_zip_detected = True
                                                print(f"✅ [DOWNLOAD_STATUS] New zip file found: {entry.name}")
                                                hud.print("✅ Download confirmed!", "success")
                                                existing_zips.add(entry.name)
                                                return True, new_zip_path, new_zip_name
                            except Exception as e:
                                print(f"⚠️ [DOWNLOAD_STATUS] Error checking during wait: {e}")
                            time.sleep(0.1)  # Check every 100ms during confirmation
                        
                        # If we get here, no zip found yet - continue monitoring
                        print("⏳ [DOWNLOAD_STATUS] No zip found yet, continuing monitoring...")
                        hud.print("⏳ Waiting for zip file...", "waiting")
                
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
        hud.print("⏰ Download monitoring timed out", "error")
        
        try:
            if os.path.exists(downloads_folder):
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.endswith('.zip') and entry.name not in existing_zips:
                            new_zip_path = entry.path
                            new_zip_name = entry.name
                            print(f"✅ [DOWNLOAD_STATUS] Found zip after timeout: {entry.name}")
                            hud.print("✅ Download confirmed (late detection)!", "success")
                            return True, new_zip_path, new_zip_name
        except Exception:
            pass
        
        return False, None, None

    def extract_zip_to_images(zip_file_path, zip_filename, project_title):
        """
        Extracts the provided zip file to the IMAGES_PATH directory,
        separates images and videos into subfolders (flattened, no subfolders),
        and renames the parent folder to the normalized project name.
        
        If the project folder already exists, it will be deleted before extraction.
        
        Args:
            zip_file_path: Full path to the zip file
            zip_filename: Name of the zip file
            project_title: Original project name to normalize and use for folder name
        
        Returns:
            bool: True if extraction completed successfully, False if failed
        """
        print(f"📦 [EXTRACT] Starting extraction of: {zip_filename}")
        hud.print(f"📦 Extracting {zip_filename}...", "processing")
        
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
                return False
        
        # Verify zip file exists and is readable
        if not os.path.exists(zip_file_path):
            print(f"❌ [EXTRACT] Zip file not found: {zip_file_path}")
            hud.print("❌ Zip file not found", "error")
            return False
        
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
            
            try:
                # Use shutil.rmtree to delete the entire folder and its contents
                import shutil
                shutil.rmtree(target_folder)
                print(f"✅ [EXTRACT] Successfully deleted existing project folder")
                hud.print("✅ Removed existing folder", "info")
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
                except Exception as e2:
                    print(f"❌ [EXTRACT] Failed to rename folder, aborting: {e2}")
                    hud.print("❌ Cannot proceed", "error")
                    return False
        
        # Extract the zip file to a temporary location first
        temp_extract_folder = target_folder + "_temp"
        try:
            print(f"📦 [EXTRACT] Extracting to temporary location: {temp_extract_folder}")
            hud.print("📦 Extracting files...", "processing")
            
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
                        except Exception as e:
                            print(f"⚠️ [EXTRACT] Could not move image {file}: {e}")
                            # Copy instead of move
                            import shutil
                            shutil.copy2(file_path, dest_path)
                            image_count += 1
                    
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
            
            # Clean up: remove the zip file after successful extraction
            try:
                os.remove(zip_file_path)
                print(f"🗑️ [EXTRACT] Removed zip file: {zip_filename}")
            except Exception as e:
                print(f"⚠️ [EXTRACT] Could not remove zip file: {e}")
            
            return True
                
        except zipfile.BadZipFile:
            print(f"❌ [EXTRACT] Corrupt or invalid zip file: {zip_file_path}")
            hud.print("❌ Invalid zip file", "error")
            # Clean up temp folder if it exists
            try:
                import shutil
                if os.path.exists(temp_extract_folder):
                    shutil.rmtree(temp_extract_folder)
            except:
                pass
            return False
        except Exception as e:
            if "LargeZipFile" in str(type(e)):
                print(f"❌ [EXTRACT] Zip file too large (requires ZIP64): {zip_file_path}")
                hud.print("❌ Zip too large", "error")
            else:
                print(f"❌ [EXTRACT] Unexpected error during extraction: {e}")
                hud.print(f"❌ Extraction error: {str(e)[:30]}...", "error")
            
            # Clean up temp folder if it exists
            try:
                import shutil
                if os.path.exists(temp_extract_folder):
                    shutil.rmtree(temp_extract_folder)
            except:
                pass
            return False
       
    def find_and_click_vertical_dot(hwnd, specific_url, project_title, depth=0):
        """Searches for vertical dot menu and initiates download with context analysis."""
        try:
            if depth > 5:
                print("❌ [DOT] Max recursion depth reached - restarting")
                hud.print("🔄 Restarting operation...", "warning")
                return False
            
            print("🔘 [DOT] Starting download sequence...")
            hud.print("🔍 Locating download option...", "searching")
            
            # Analyze current page context
            on_all, on_project, project_found, context = analyze_current_page_context(
                hwnd, specific_url, project_title
            )
            
            print(f"📊 [DOT] Initial context: {context}, on_project={on_project}, project_found={project_found}")
            
            # If not on project page, navigate
            if not on_project:
                print("❌ [DOT] Not on project page - navigating...")
                hud.print("❌ Navigating to project...", "error")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
            # If on wrong project, navigate
            if on_project and not project_found:
                print("❌ [DOT] Project name not found - navigating back")
                hud.print("❌ Project mismatch, navigating...", "error")
                fast_paste_url(hwnd, specific_url)
                time.sleep(3)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
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
                current_monitor = get_current_monitor()
                monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
                center_x = monitor_left + (monitor_right - monitor_left) // 2
                center_y = monitor_top + (monitor_bottom - monitor_top) // 2
                pyautogui.moveTo(center_x, center_y, duration=0)
                pyautogui.scroll(-300)
                time.sleep(1)
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
            x, y = found_location
            print(f"🎯 [DOT] Selecting at position ({x}, {y})")
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
            pyautogui.moveTo(x, y, duration=0.2)
            time.sleep(0.2)
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
                        hud.print("📥 Selecting download...", "selecting")
                        break
                
                if download_found and download_click_position:
                    break
                
                time.sleep(0.5)
                print(f"⏳ [DOWNLOAD] Retry {attempt + 1}/10...")
                hud.print(f"⏳ Searching...", "waiting")
            
            if not download_found or not download_click_position:
                print("❌ [DOWNLOAD] Could not find download option - retrying")
                hud.print("🔄 Retrying download search...", "warning")
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
            click_x, click_y = download_click_position
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before download selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.click()
            time.sleep(0.5)
            
            print("📊 [DOWNLOAD] Starting download status monitoring...")
            
            # Use the download status checker - now returns (success, zip_path, zip_name)
            download_successful, zip_file_path, zip_filename = check_download_status(
                hwnd, timeout_seconds=300, check_interval=0.1
            )
            
            if download_successful and zip_file_path and zip_filename:
                print("🎉 [DOWNLOAD] Download completed successfully!")
                hud.print("✅ Download completed!", "success")
                
                # Now extract the zip file immediately
                print("📦 [EXTRACT] Starting zip extraction...")
                extraction_successful = extract_zip_to_images(
                    zip_file_path, zip_filename, project_title
                )
                
                if extraction_successful:
                    print("🎉 [COMPLETE] Operation fully completed - Download and extraction successful!")
                    hud.print("✅ Complete - Project extracted!", "success")
                    return True
                else:
                    print("⚠️ [COMPLETE] Download completed but extraction failed")
                    hud.print("⚠️ Download OK, extraction failed", "warning")
                    # Return True anyway since download succeeded
                    return True
            else:
                print("⚠️ [DOWNLOAD] Download status check timed out or failed")
                hud.print("⚠️ Download status uncertain", "warning")
                return False
                
        except Exception as e:
            print(f"❌ [DOT] Error: {e}")
            hud.print(f"❌ Error occurred, retrying...", "error")
            print("🔄 [DOT] Attempting recovery...")
            hwnd = ensure_window_ready_and_focused()
            return find_and_click_vertical_dot(hwnd, specific_url, project_title, depth + 1)
            
    # ============================================
    # SECTION 6: MAIN EXECUTION FLOW - NEVER EXITS UNLESS CRITICAL
    # ============================================
    
    def perform_navigation_and_restart(hwnd, url, operation_name="navigation"):
        """Perform navigation and then restart the entire operation from beginning"""
        print(f"🔄 [RESTART] {operation_name} - navigating to {url} and restarting operation")
        hud.print(f"🔄 Restarting operation after {operation_name}...", "warning")
        
        # Navigate to the destination
        fast_paste_url(hwnd, url)
        time.sleep(3)
        
        # Ensure window is ready after navigation
        hwnd = ensure_window_ready_and_focused()
        
        # CRITICAL: Restart the entire operation by calling main()
        print(f"🔄 [RESTART] Operation restarting from beginning after {operation_name}")
        hud.print("🔄 Operation restarting...", "warning")
        time.sleep(1)
        
        # Call main() to restart the entire workflow
        main()
        return  # This will never be reached if main() runs properly
    
    def main():
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                return
        
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Check if Google Flow operation is enabled
            operate_google_flow = panel_data.get('operate_google_flow', False)
            if not operate_google_flow:
                print("ℹ️ Google Flow operation is disabled in config")
                hud.print("ℹ️ Google Flow operation disabled", "info")
                return
            
            all_project_url = panel_data.get('google_flow_url')
            project_title = panel_data.get('project_title')
            google_flow_project_link = panel_data.get('google_flow_project_link')
            
            if project_title:
                project_title = project_title.strip()
            
            print(f"🌐 [MAIN] All Projects URL: {all_project_url}")
            print(f"🌐 [MAIN] Project Name: [HIDDEN]")
            print(f"🌐 [MAIN] Project Link: {google_flow_project_link if google_flow_project_link else '[EMPTY]'}")
            
            # CRITICAL: Only exit if these are missing
            if not all_project_url and not google_flow_project_link:
                print("❌ Error: Neither 'google_flow_url' nor 'google_flow_project_link' configured.")
                return
            
            # CRITICAL: Exit if project name is empty when using all projects workflow
            if all_project_url and (not project_title or not project_title.strip()):
                print("❌ Error: 'project_title' is empty or missing.")
                return
            
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
            # FLOW 1: DIRECT PROJECT LINK PROVIDED
            # ============================================
            
            if google_flow_project_link and google_flow_project_link.strip():
                print("🚀 [ROUTING] Project link detected - loading directly...")
                hud.print("📋 Loading project directly...", "navigating")
                
                fast_paste_url(hwnd_to_use, google_flow_project_link)
                hwnd_to_use = ensure_window_ready_and_focused()
                
                # Keep retrying until we succeed
                max_attempts = 5
                attempt = 0
                success = False
                
                while attempt < max_attempts and not success:
                    attempt += 1
                    print(f"🔄 [MAIN] Attempt {attempt}/{max_attempts} for project link workflow...")
                    
                    # Analyze current page context
                    on_all, on_project, project_found, context = analyze_current_page_context(
                        hwnd_to_use, google_flow_project_link, project_title
                    )
                    
                    print(f"📊 [MAIN] Page context: {context}, on_project={on_project}, project_found={project_found}")
                    
                    if on_project:
                        print("✅ [MAIN] On project page")
                        hud.print("✅ On correct page", "success")
                        
                        page_ready, name_verified, recovered_hwnd = wait_for_specific_page_ready(
                            hwnd_to_use, google_flow_project_link, project_title
                        )
                        
                        if recovered_hwnd != hwnd_to_use:
                            hwnd_to_use = recovered_hwnd
                            print("🔄 [MAIN] Window recovered after page ready")
                        
                        if page_ready:
                            print("✅ [MAIN] Project page ready, proceeding to download...")
                            hud.print("🚀 Proceeding...", "success")
                            
                            scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                                hwnd_to_use, google_flow_project_link, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after scrolling")
                            
                            if scroll_complete:
                                print("✅ [MAIN] Project verified")
                                hud.print("✅ Project verified", "success")
                                
                                success = find_and_click_vertical_dot(hwnd_to_use, google_flow_project_link, project_title)
                                
                                if success:
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Project verification incomplete, retrying...")
                                hud.print("🔄 Retrying verification...", "warning")
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Page not ready, retrying...")
                            hud.print("🔄 Retrying page load...", "warning")
                            time.sleep(2)
                    else:
                        print("⚠️ [MAIN] Not on project page, navigating...")
                        hud.print("🔄 Navigating to project...", "warning")
                        fast_paste_url(hwnd_to_use, google_flow_project_link)
                        time.sleep(3)
                
                # If we exhausted attempts, restart the whole process
                print("🔄 [MAIN] Max attempts reached for project link, restarting...")
                hud.print("🔄 Restarting operation...", "warning")
                time.sleep(2)
                perform_navigation_and_restart(hwnd_to_use, google_flow_project_link, "project link workflow retry")
                return
            
            # ============================================
            # FLOW 2: ALL PROJECTS WORKFLOW - NEVER EXITS
            # ============================================
            
            if all_project_url and all_project_url.strip():
                print("🚀 [ROUTING] Using All Projects page workflow...")
                hud.print("📋 Navigating to projects list...", "navigating")
                
                # Keep retrying until we succeed
                max_attempts = 5
                attempt = 0
                success = False
                
                while attempt < max_attempts and not success:
                    attempt += 1
                    print(f"🔄 [MAIN] Attempt {attempt}/{max_attempts} for all projects workflow...")
                    
                    # Analyze current page context
                    on_all, on_project, project_found, context = analyze_current_page_context(
                        hwnd_to_use, all_project_url, project_title
                    )
                    
                    print(f"📊 [MAIN] Page context: {context}, on_all={on_all}, on_project={on_project}, project_found={project_found}")
                    
                    # CRITICAL FIX: If on project page AND project found, skip selection and go to download
                    if on_project and project_found:
                        print("✅ [MAIN] Already on target project page - skipping card selection")
                        hud.print("✅ On target page", "success")
                        
                        page_ready, name_verified, recovered_hwnd = wait_for_specific_page_ready(
                            hwnd_to_use, all_project_url, project_title
                        )
                        
                        if recovered_hwnd != hwnd_to_use:
                            hwnd_to_use = recovered_hwnd
                            print("🔄 [MAIN] Window recovered after page ready")
                        
                        if page_ready:
                            print("✅ [MAIN] Project page ready, proceeding to download...")
                            hud.print("🚀 Proceeding...", "success")
                            
                            scroll_complete, found_after_scroll, recovered_hwnd = scroll_in_specific_project(
                                hwnd_to_use, all_project_url, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after scrolling")
                            
                            if scroll_complete:
                                print("✅ [MAIN] Project verified")
                                hud.print("✅ Project verified", "success")
                                
                                success = find_and_click_vertical_dot(hwnd_to_use, all_project_url, project_title)
                                
                                if success:
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Project verification incomplete, retrying...")
                                hud.print("🔄 Retrying verification...", "warning")
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Page not ready, retrying...")
                            hud.print("🔄 Retrying page load...", "warning")
                            time.sleep(2)
                        continue
                    
                    # If on wrong project page, navigate to all projects
                    if on_project and not project_found:
                        print("⚠️ [MAIN] On wrong project page - navigating to all projects")
                        hud.print("⚠️ Wrong project, navigating...", "warning")
                        fast_paste_url(hwnd_to_use, all_project_url)
                        time.sleep(3)
                        # RESTART: We navigated to all projects, so restart the operation
                        perform_navigation_and_restart(hwnd_to_use, all_project_url, "wrong project navigation")
                        return
                    
                    # If context unknown, navigate to all projects
                    if context == "unknown":
                        print("⚠️ [MAIN] Page context unknown - navigating to all projects")
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
                            
                            success = find_and_click_vertical_dot(hwnd_to_use, all_project_url, project_title)
                            
                            if success:
                                hud.print("✅ Operation complete!", "success")
                                print("✅ [VERIFICATION] All checks passed and download initiated!")
                                return
                            else:
                                print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                hud.print("🔄 Retrying download...", "warning")
                                time.sleep(2)
                                continue
                        
                        # We found a card to click
                        if card_found and card_element:
                            print("✅ [MAIN] Project card found - clicking it")
                            hud.print("✅ Target located - clicking", "success")
                            
                            click_success, recovered_hwnd = click_project_card(
                                hwnd_to_use, card_element, all_project_url, project_title
                            )
                            
                            if recovered_hwnd != hwnd_to_use:
                                hwnd_to_use = recovered_hwnd
                                print("🔄 [MAIN] Window recovered after selection")
                            
                            if click_success:
                                print("✅ [MAIN] Project card selected, proceeding to download...")
                                hud.print("🚀 Proceeding...", "success")
                                
                                # Wait a bit for the page to load
                                time.sleep(2)
                                
                                success = find_and_click_vertical_dot(hwnd_to_use, all_project_url, project_title)
                                
                                if success:
                                    hud.print("✅ Operation complete!", "success")
                                    print("✅ [VERIFICATION] All checks passed and download initiated!")
                                    return
                                else:
                                    print("⚠️ [MAIN] Download flow incomplete, retrying...")
                                    hud.print("🔄 Retrying download...", "warning")
                                    time.sleep(2)
                            else:
                                print("⚠️ [MAIN] Failed to select project card, retrying...")
                                hud.print("🔄 Retrying selection...", "warning")
                                time.sleep(2)
                        else:
                            print("⚠️ [MAIN] Project card not found, retrying...")
                            hud.print("🔄 Retrying search...", "warning")
                            time.sleep(2)
                    else:
                        print("⚠️ [MAIN] All Projects page not ready, retrying...")
                        hud.print("🔄 Retrying page load...", "warning")
                        time.sleep(2)
                
                # If we exhausted attempts, restart the whole process
                print("🔄 [MAIN] Max attempts reached, restarting...")
                hud.print("🔄 Restarting operation...", "warning")
                time.sleep(2)
                perform_navigation_and_restart(hwnd_to_use, all_project_url, "max attempts reached")
                return

        except KeyboardInterrupt as ki:
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except Exception as e:
            print(f"❌ Error caught: {e}")
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
    
    terminate_automation = False
    video_urls_file = None
    project_title = None

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            raise KeyboardInterrupt("User forced exit via shortcut key.")

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
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
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
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        raise RuntimeError("Failed to get or launch Edge window")

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
        
        # Step 1: Check if history is already visible
        print(f"🔍 [CTRL+B] Step 1: Checking if history is already visible...")
        history_already_visible, _ = check_for_history(hwnd, timeout_seconds=3, check_interval=0.3)
        
        if history_already_visible:
            print(f"✅ [CTRL+B] History already visible - no need to press Ctrl+B")
            return True, hwnd
        
        print(f"ℹ️ [CTRL+B] History not visible - will press Ctrl+B to reveal it")
        
        for attempt in range(max_attempts):
            check_for_termination()
            
            print(f"🔄 [CTRL+B] Attempt {attempt + 1}/{max_attempts}")
            
            # Step 2: Verify page is still loaded by checking for indicators
            print(f"🔍 [CTRL+B] Verifying page is still loaded...")
            
            page_loaded, indicator = check_for_page_load_indicators(safe_ocr())
            
            if not page_loaded:
                print(f"⚠️ [CTRL+B] Page not loaded (attempt {attempt + 1}) - reloading...")
                hud.print("⚠️ Page not loaded, reloading...", "warning")
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
                return True, hwnd
            else:
                print(f"⏳ [CTRL+B] 'history' not found yet (attempt {attempt + 1})")
                hud.print(f"⏳ Trying again... ({attempt + 1}/{max_attempts})", "waiting")
                time.sleep(0.5)
        
        print(f"❌ [CTRL+B] Failed to find 'history' after {max_attempts} attempts")
        return False, hwnd

    def click_history_button(hwnd, depth=0):
        """Find and click the 'history' button/text on screen."""
        print("🎯 [HISTORY] Looking for history option...")
        
        if depth > 5:
            print("❌ [HISTORY] Max recursion depth reached")
            hud.print("❌ Option search recursion limit", "error")
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
        
        return True, hwnd

    def find_and_click_video_duration(hwnd, timeout_seconds=10, check_interval=0.1):
        """Find and click the FIRST time value in format 0:XX."""
        print("⏱️ [TIME] Looking for first time value to click...")
        
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
                return True, hwnd
            
            if attempts % 3 == 0:
                print(f"⬇️ [TIME] Scrolling down more (attempt {attempts})...")
                hud.print("⬇️ Scrolling more...", "navigating")
                pyautogui.scroll(-200)
                time.sleep(0.5)
            
            time.sleep(check_interval)
        
        print(f"❌ [TIME] No time value found within {timeout_seconds}s")
        hud.print("❌ No time value found", "error")
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
        hud.print("❌ Prompt ID not found", "error")
        return False, None

    def click_download_button(hwnd, timeout_seconds=5, check_interval=0.1):
        """
        Find and click the download button using image recognition.
        Looks for download_btn1.png first, then falls back to download_btn2.png.
        Searches specifically in the bottom-right quadrant of the screen.
        
        Returns:
            tuple: (success, hwnd)
        """
        print("📥 [DOWNLOAD_BTN] Looking for Download button using image recognition...")
        
        # Define paths to download button images
        download_btn1_path = os.path.join(GUI_IMAGE_PATH, "download_btn1.png")
        download_btn2_path = os.path.join(GUI_IMAGE_PATH, "download_btn2.png")
        
        # Check if image files exist
        if not os.path.exists(download_btn1_path) and not os.path.exists(download_btn2_path):
            print("❌ [DOWNLOAD_BTN] No download button images found in GUI_IMAGE_PATH")
            hud.print("❌ Download images missing", "error")
            return False, hwnd
        
        start_time = time.time()
        attempts = 0
        
        # Get current monitor bounds for region restriction
        current_monitor = get_current_monitor()
        monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
        monitor_width = monitor_right - monitor_left
        monitor_height = monitor_bottom - monitor_top
        
        # Divide screen into 8 grids (2 columns x 4 rows)
        # Grid 8 is bottom-right: column 2 (right half), row 4 (bottom quarter)
        grid_width = monitor_width // 2
        grid_height = monitor_height // 4
        
        # Bottom-right grid: column 2 (index 1), row 4 (index 3)
        # This is the bottom-right quadrant of the screen
        region_left = monitor_left + grid_width  # Start of right half
        region_top = monitor_top + (grid_height * 3)  # Start of bottom quarter
        region_width = grid_width
        region_height = grid_height
        
        # Add some padding to ensure we catch buttons near the edges
        padding = 50
        region_left = max(monitor_left, region_left - padding)
        region_top = max(monitor_top, region_top - padding)
        region_width = min(monitor_width, region_width + (padding * 2))
        region_height = min(monitor_height, region_height + (padding * 2))
        
        # Define search region
        region = (region_left, region_top, region_width, region_height)
        
        print(f"📐 [DOWNLOAD_BTN] Screen: {monitor_width}x{monitor_height}")
        print(f"📐 [DOWNLOAD_BTN] Grid size: {grid_width}x{grid_height}")
        print(f"📐 [DOWNLOAD_BTN] Search region (bottom-right): {region}")
        
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
                        print(f"✅ [DOWNLOAD_BTN] Found download_btn1.png at position ({x}, {y}) in bottom-right region")
                        
                        # Click the download button
                        enforce_window_focus(hwnd)
                        pyautogui.moveTo(x, y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        print(f"✅ [DOWNLOAD_BTN] Successfully clicked download button using download_btn1.png")
                        return True, hwnd
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_BTN] Error searching for download_btn1.png: {e}")
            
            # If download_btn1.png not found or failed, try download_btn2.png
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
                        print(f"✅ [DOWNLOAD_BTN] Found download_btn2.png at position ({x}, {y}) in bottom-right region")
                        
                        # Click the download button
                        enforce_window_focus(hwnd)
                        pyautogui.moveTo(x, y, duration=0.2)
                        pyautogui.click()
                        time.sleep(0.5)
                        
                        print(f"✅ [DOWNLOAD_BTN] Successfully clicked download button using download_btn2.png")
                        return True, hwnd
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_BTN] Error searching for download_btn2.png: {e}")
            
            # If we get here, no download button found yet
            print(f"⏳ [DOWNLOAD_BTN] Download button not found in bottom-right region (attempt {attempts})")
            
            # Small delay before next attempt
            time.sleep(check_interval)
        
        print(f"❌ [DOWNLOAD_BTN] No Download button found in bottom-right region within {timeout_seconds}s")
        hud.print("❌ Download button not found", "error")
        return False, hwnd
    
    def check_download_in_progress(hwnd, timeout_seconds=60, check_interval=0.5):
        """
        Check if a download is in progress and wait for it to complete.
        Monitors for "downloading" text or checks the downloads folder for new files.
        
        Returns:
            tuple: (download_started, download_completed, hwnd)
        """
        print(f"📊 [DOWNLOAD_PROGRESS] Starting download progress monitor...")
        hud.print("📊 Monitoring download...", "waiting")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Get initial list of files in downloads folder
        initial_files = set()
        if os.path.exists(downloads_folder):
            try:
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file():
                            initial_files.add((entry.name, entry.stat().st_size))
                print(f"📁 [DOWNLOAD_PROGRESS] Found {len(initial_files)} initial files in Downloads")
            except Exception as e:
                print(f"⚠️ [DOWNLOAD_PROGRESS] Could not scan Downloads folder: {e}")
        
        download_started = False
        download_completed = False
        downloading_text_seen = False
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            # Check for "downloading" text on screen
            current_texts = safe_ocr()
            downloading_found = False
            
            if current_texts:
                for element in current_texts:
                    element_text = element['text'].strip().lower()
                    if "downloading" in element_text:
                        downloading_found = True
                        if not download_started:
                            print(f"✅ [DOWNLOAD_PROGRESS] Download started! (text detected: '{element_text}')")
                            hud.print("📥 Download started...", "downloading")
                            download_started = True
                            downloading_text_seen = True
                        break
            
            # Check downloads folder for new files
            if os.path.exists(downloads_folder):
                try:
                    current_files = set()
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file():
                                current_files.add((entry.name, entry.stat().st_size))
                    
                    # Check if there are new files not in initial list
                    new_files = current_files - initial_files
                    
                    if new_files and not download_started:
                        print(f"✅ [DOWNLOAD_PROGRESS] New file detected in Downloads! ({len(new_files)} new files)")
                        download_started = True
                        hud.print("📥 Download started...", "downloading")
                    
                    # Check if files are still growing (download in progress)
                    if download_started and not download_completed:
                        # Check if any file is currently being written (size changing)
                        files_changing = False
                        for file_name, size in current_files:
                            if (file_name, size) not in initial_files:
                                # Check if file size is stable (not changing)
                                try:
                                    file_path = os.path.join(downloads_folder, file_name)
                                    if os.path.exists(file_path):
                                        current_size = os.path.getsize(file_path)
                                        # Wait a moment and check again
                                        time.sleep(0.1)
                                        new_size = os.path.getsize(file_path)
                                        if current_size != new_size:
                                            files_changing = True
                                            break
                                except Exception:
                                    pass
                        
                        if not files_changing and not downloading_found:
                            # No downloading text and no files changing - download likely complete
                            # But wait a bit to make sure
                            if downloading_text_seen and not download_completed:
                                print(f"✅ [DOWNLOAD_PROGRESS] Download appears complete (no activity detected)")
                                hud.print("✅ Download completed", "success")
                                download_completed = True
                                return True, True, hwnd
                
                except Exception as e:
                    print(f"⚠️ [DOWNLOAD_PROGRESS] Error scanning Downloads: {e}")
            
            # If we haven't seen downloading text but download started via file detection
            if download_started and not download_completed and not downloading_found:
                # Check if enough time has passed since download started
                elapsed = time.time() - start_time
                if elapsed > 10 and downloading_text_seen:
                    print(f"⏳ [DOWNLOAD_PROGRESS] Download in progress... ({elapsed:.1f}s)")
                    hud.print(f"📥 Downloading... ({elapsed:.1f}s)", "downloading")
            
            time.sleep(check_interval)
        
        # Timeout reached
        if download_started and not download_completed:
            print(f"⏰ [DOWNLOAD_PROGRESS] Timeout reached, but download may still be in progress")
            hud.print("⏰ Download monitor timed out", "warning")
            return True, False, hwnd
        elif not download_started:
            print(f"⏰ [DOWNLOAD_PROGRESS] No download detected within timeout")
            hud.print("⏰ No download detected", "warning")
            return False, False, hwnd
        
        return download_started, download_completed, hwnd

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
        
        current_id = get_current_video_id(hwnd)
        if not current_id:
            print("❌ [LATEST_VIDEO] Could not get current video ID")
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
                return True, hwnd
            
            if new_id in visited_ids:
                print(f"⚠️ [LATEST_VIDEO] Cycle detected at ID: {new_id}")
                print(f"✅ [LATEST_VIDEO] Latest video is: {current_id}")
                hud.print("✅ Gotten to the latest video", "success")
                return True, hwnd
            
            visited_ids.add(new_id)
            print(f"⬅️ [LATEST_VIDEO] Navigated to video ID: {new_id}")
            hud.print("⬅️ Not latest video", "navigating")
            current_id = new_id
        
        if not latest_reached:
            print(f"❌ [LATEST_VIDEO] Failed to reach latest video after {max_attempts} attempts")
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
            return True
                
        except Exception as e:
            print(f"❌ [RECORD] Error recording video info: {e}")
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
    
    def get_video_prompt_ids_with_download(hwnd, base_url, prompt_id, project_title):
        """
        Operation 2: Navigate right and record videos with matching prompt ID.
        For each matching video, clicks the download button and waits for download to complete.
        """
        print("➡️ [PROMPT_IDS] Starting 'Get Video Prompt IDs' operation...")
        print(f"🔍 [PROMPT_IDS] Looking for prompt ID: '{prompt_id}'")
        hud.print("🔍 Searching for matching videos...", "searching")
        
        current_id = get_current_video_id(hwnd)
        if not current_id:
            print("❌ [PROMPT_IDS] Could not get current video ID")
            return False, hwnd
        
        print(f"📋 [PROMPT_IDS] Starting from video ID: {current_id}")
        
        visited_ids = set()
        visited_ids.add(current_id)
        
        consecutive_misses = 0
        max_misses = 3
        videos_found = 0
        
        # Check starting video
        prompt_found, _ = check_for_prompt_id(hwnd, prompt_id, timeout_seconds=3)
        
        if prompt_found:
            print(f"✅ [PROMPT_IDS] Starting video has the prompt ID!")
            
            # Record the video ID
            record_success = record_video_id_to_file(
                current_id, prompt_id, project_title
            )
            if record_success:
                videos_found += 1
                hud.print(f"✅ Video identified ({videos_found})", "success")
            
            # Click download button and wait for completion
            print(f"📥 [PROMPT_IDS] Downloading video {current_id}...")
            download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
            
            if download_success:
                # Wait for download to complete
                started, completed, hwnd = check_download_in_progress(
                    hwnd, timeout_seconds=120, check_interval=0.5
                )
                if completed:
                    print(f"✅ [PROMPT_IDS] Video {current_id} downloaded successfully!")
                    hud.print("✅ Download complete", "success")
                else:
                    print(f"⚠️ [PROMPT_IDS] Download for video {current_id} may not have completed")
                    hud.print("⚠️ Download may be incomplete", "warning")
            else:
                print(f"⚠️ [PROMPT_IDS] Failed to click download button for video {current_id}")
                hud.print("⚠️ Download button not found", "warning")
        
        # Navigate right and continue
        while consecutive_misses < max_misses:
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
                print(f"📊 [PROMPT_IDS] Found {videos_found} matching videos")
                hud.print(f"📊 Found {videos_found} matching videos", "info")
                break
            
            visited_ids.add(new_id)
            print(f"➡️ [PROMPT_IDS] Navigated to video ID: {new_id}")
            
            prompt_found, _ = check_for_prompt_id(hwnd, prompt_id, timeout_seconds=3)
            
            if prompt_found:
                print(f"✅ [PROMPT_IDS] Found matching video at ID: {new_id}")
                
                # Record the video ID
                record_success = record_video_id_to_file(
                    new_id, prompt_id, project_title
                )
                
                if record_success:
                    videos_found += 1
                    hud.print(f"✅ Video identified ({videos_found})", "success")
                
                # Click download button and wait for completion
                print(f"📥 [PROMPT_IDS] Downloading video {new_id}...")
                download_success, hwnd = click_download_button(hwnd, timeout_seconds=5)
                
                if download_success:
                    # Wait for download to complete
                    started, completed, hwnd = check_download_in_progress(
                        hwnd, timeout_seconds=120, check_interval=0.5
                    )
                    if completed:
                        print(f"✅ [PROMPT_IDS] Video {new_id} downloaded successfully!")
                        hud.print("✅ Download complete", "success")
                    else:
                        print(f"⚠️ [PROMPT_IDS] Download for video {new_id} may not have completed")
                        hud.print("⚠️ Download may be incomplete", "warning")
                else:
                    print(f"⚠️ [PROMPT_IDS] Failed to click download button for video {new_id}")
                    hud.print("⚠️ Download button not found", "warning")
                
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                print(f"❌ [PROMPT_IDS] Prompt ID not found (miss {consecutive_misses}/{max_misses})")
                hud.print(f"❌ No match ({consecutive_misses}/{max_misses})", "warning")
        
        if videos_found > 0:
            print(f"✅ [PROMPT_IDS] Completed! Found {videos_found} videos with prompt ID")
            hud.print(f"✅ Found {videos_found} matching videos", "success")
            return True, hwnd
        else:
            print(f"❌ [PROMPT_IDS] No videos found with the prompt ID")
            hud.print("❌ No matching videos found", "error")
            return False, hwnd

    # ============================================
    # SECTION 6: MAIN VIDEO WORKFLOW
    # ============================================
    def main_video_workflow_with_restart(hwnd=None, video_project_url=None, depth=0):
        """
        Main video workflow execution with restart capability.
        """
        try:
            if video_project_url is None:
                if not os.path.exists(PANEL_PATH):
                    print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                    return False
                
                with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                    panel_data = json.load(file)
                
                operate_video = panel_data.get('operate_grok', False)
                if not operate_video:
                    print("ℹ️ Video operation is disabled in config")
                    hud.print("ℹ️ Video operation disabled", "info")
                    return False
                
                video_project_url = panel_data.get('grok_imagine_url')
                prompt_id = panel_data.get('video_prompt_id', 'no music')
                project_title = panel_data.get('project_title', 'video_project')
                
                if not video_project_url or not video_project_url.strip():
                    print("❌ Error: 'grok_imagine_url' not configured")
                    hud.print("❌ No video URL configured", "error")
                    return False
                
                if not prompt_id or not prompt_id.strip():
                    print("⚠️ Warning: 'video_prompt_id' not configured, using default 'no music'")
                    prompt_id = "no music"
            else:
                with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                    panel_data = json.load(file)
                prompt_id = panel_data.get('video_prompt_id', 'no music')
                project_title = panel_data.get('project_title', 'video_project')
            
            if hwnd is None:
                hwnd = ensure_window_ready_and_focused()
                print(f"🪟 [VIDEO] Browser ready (HWND: {hwnd})")
            
            print(f"🎬 [VIDEO] Starting video workflow (depth {depth})...")
            print(f"🌐 [VIDEO] URL: {video_project_url}")
            print(f"🔍 [VIDEO] Prompt ID: '{prompt_id}'")
            print(f"📁 [VIDEO] Project: '{project_title}'")
            
            # Step 1: Check if URL is already loaded - DON'T launch immediately
            print(f"🔍 [VIDEO] Step 1: Checking if target URL is already loaded...")
            url_found, current_texts = check_current_url_contains_target(hwnd, video_project_url)
            
            if url_found:
                print(f"✅ [VIDEO] Target URL already loaded - proceeding without navigation")
                hud.print("✅ URL already loaded", "success")
            else:
                print(f"🔄 [VIDEO] Target URL not found - navigating to it")
                hud.print("📋 Navigating to URL...", "navigating")
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
                        break
                
                if not page_loaded:
                    reload_attempts += 1
                    if reload_attempts < max_reloads:
                        print(f"🔄 [VIDEO] Page not loaded, reloading (attempt {reload_attempts}/{max_reloads})...")
                        hud.print(f"🔄 Reloading page ({reload_attempts}/{max_reloads})...", "warning")
                        enforce_window_focus(hwnd)
                        pyautogui.hotkey('ctrl', 'r')
                        time.sleep(3)
                        hwnd = ensure_window_ready_and_focused()
                    else:
                        print(f"❌ [VIDEO] Page failed to load after {max_reloads} reload attempts")
                        hud.print("❌ Page load failed", "error")
                        return False
            
            if not page_loaded:
                print("❌ [VIDEO] Page not loaded - aborting")
                return False
            
            print("✅ [VIDEO] Page loaded successfully")
            
            # Step 3: Check for time value - THIS IS THE MAIN CHARACTER NOW
            print(f"🔍 [VIDEO] Step 3: Checking for time value...")
            
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
            else:
                # No time value found - check history and activate Ctrl+B if needed
                print(f"ℹ️ [VIDEO] No time value found - checking history...")
                history_found, hwnd = activate_ctrl_b_and_check_history(hwnd, max_attempts=5)
                
                if not history_found:
                    print("❌ [VIDEO] Failed to find history option")
                    return False
                
                print("✅ [VIDEO] History option found - proceeding to click")
                
                # Click the history button
                print(f"🎯 [VIDEO] Clicking history option...")
                
                clicked_successfully, hwnd = click_history_button(hwnd)
                
                if not clicked_successfully:
                    print("❌ [VIDEO] Failed to click history option")
                    return False
                
                print("✅ [VIDEO] History option clicked successfully!")
                
                # Wait for history panel to load
                print("⏳ [VIDEO] Waiting for history panel to load...")
                hud.print("⏳ Checking history...", "waiting")
                
                # Find and click the first time value
                print(f"🔍 [VIDEO] Looking for first time value...")
                
                time_found, hwnd = find_and_click_video_duration(hwnd, timeout_seconds=10, check_interval=0.1)
                
                if not time_found:
                    print("❌ [VIDEO] Failed to find and click time value")
                    hud.print("❌ Couldn't find a video", "error")
                    return False
                
                print(" [VIDEO] First time value clicked successfully!")
                hud.print("🎦", "waiting")
            
            # Give the video player a moment to load
            time.sleep(2)
            hwnd = ensure_window_ready_and_focused()
            
            # OPERATION 1: Get to Latest Video
            print("=" * 60)
            print("🎬 [VIDEO] Starting Operation 1: Get to Latest Video")
            print("=" * 60)
            
            latest_success, hwnd = get_to_latest_video(
                hwnd, 
                video_project_url.rstrip('/')
            )
            
            if not latest_success:
                print("❌ [VIDEO] Failed to reach latest video")
                hud.print("❌ Could not reach latest video", "error")
                return False
            
            print("✅ [VIDEO] Operation 1 completed - At latest video")
            
            # OPERATION 2: Get Video Prompt IDs with Download
            print("=" * 60)
            print("🎬 [VIDEO] Starting Operation 2: Get Video Prompt IDs with Download")
            print("=" * 60)
            
            prompt_success, hwnd = get_video_prompt_ids_with_download(
                hwnd,
                video_project_url.rstrip('/'),
                prompt_id,
                project_title
            )
            
            if not prompt_success:
                print("❌ [VIDEO] Video navigation and recording failed")
                hud.print("❌ Video recording failed", "error")
                return False
            
            print("🎉 [VIDEO] Video workflow completed successfully!")
            hud.print("🎉 Video workflow complete!", "success")
            return True
            
        except KeyboardInterrupt as ki:
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
            return False
        except Exception as e:
            print(f"❌ [VIDEO] Error: {e}")
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
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            operate_video = panel_data.get('operate_grok', False)
            if not operate_video:
                print("ℹ️ Video operation is disabled in config")
                hud.print("ℹ️ Video operation disabled", "info")
                return
            
            video_project_url = panel_data.get('grok_imagine_url')
            if not video_project_url or not video_project_url.strip():
                print("❌ Error: 'grok_imagine_url' not configured")
                hud.print("❌ No video URL configured", "error")
                return
            
            success = main_video_workflow_with_restart(
                hwnd=None, 
                video_project_url=video_project_url, 
                depth=0
            )
            
            if success:
                print("✅ [MAIN] Video workflow completed successfully!")
            else:
                print("❌ [MAIN] Video workflow failed after multiple attempts")
                
        except KeyboardInterrupt as ki:
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    
    main_video_workflow()
    
def run_operations():
    """
    Main orchestrator function that runs Google Flow and Grok operations
    based on operation status tracking.
    
    Features:
    - Reads/writes operation status from panel.json
    - Prevents re-running completed operations
    - Sets status at each step
    - Runs operations in sequence
    """
    
    # --- Load or create panel.json ---
    if not os.path.exists(PANEL_PATH):
        print(f"📝 [RUN_OPS] Creating new panel.json at: {PANEL_PATH}")
        default_config = {
            "operate_google_flow": False,
            "operate_grok": False,
            "google_flow_project_link": "",
            "google_flow_url": "https://labs.google/fx/tools/flow",
            "grok_imagine_url": "https://grok.com/imagine",
            "project_title": "",
            "video_prompt_id": "no music",
            "operation_status": ""
        }
        try:
            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print("✅ [RUN_OPS] Created default panel.json")
        except Exception as e:
            print(f"❌ [RUN_OPS] Failed to create panel.json: {e}")
            hud.print("❌ Failed to create config file", "error")
            return
    
    # --- Read panel.json ---
    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as file:
            panel_data = json.load(file)
    except Exception as e:
        print(f"❌ [RUN_OPS] Failed to read panel.json: {e}")
        hud.print("❌ Failed to read config", "error")
        return
    
    # --- Get operation status ---
    operation_status = panel_data.get('operation_status', '')
    print(f"📊 [RUN_OPS] Current operation status: '{operation_status}'")
    
    # --- Check if operations are enabled ---
    operate_google_flow = panel_data.get('operate_google_flow', False)
    operate_grok = panel_data.get('operate_grok', False)
    
    if not operate_google_flow and not operate_grok:
        print("ℹ️ [RUN_OPS] No operations enabled in config")
        hud.print("ℹ️ No operations enabled", "info")
        return
    
    # --- Determine which operations need to run ---
    run_google_flow = False
    run_grok = False
    
    # Google Flow conditions:
    # Run if: status is empty, or status is "starting_google_flow", 
    # or status is "all_operations_completed", or status != "completed_google_flow_operation"
    if operate_google_flow:
        if (operation_status == "" or 
            operation_status == "starting_google_flow" or 
            operation_status == "all_operations_completed" or
            operation_status != "completed_google_flow_operation"):
            run_google_flow = True
            print("✅ [RUN_OPS] Google Flow operation will run")
        else:
            print(f"ℹ️ [RUN_OPS] Google Flow already completed (status: '{operation_status}') - skipping")
    else:
        print("ℹ️ [RUN_OPS] Google Flow is disabled in config")
    
    # Grok conditions:
    # Run if: status is empty, or status is "starting_grok_operation", 
    # or status is "all_operations_completed", or status != "completed_grok_operation"
    if operate_grok:
        if (operation_status == "" or 
            operation_status == "starting_grok_operation" or 
            operation_status == "all_operations_completed" or
            operation_status != "completed_grok_operation"):
            run_grok = True
            print("✅ [RUN_OPS] Grok operation will run")
        else:
            print(f"ℹ️ [RUN_OPS] Grok already completed (status: '{operation_status}') - skipping")
    else:
        print("ℹ️ [RUN_OPS] Grok is disabled in config")
    
    # --- If nothing to run, exit ---
    if not run_google_flow and not run_grok:
        print("ℹ️ [RUN_OPS] All operations already completed or disabled")
        hud.print("✅ All operations completed", "success")
        return
    
    # --- Execute Google Flow first ---
    if run_google_flow:
        print("=" * 60)
        print("🚀 [RUN_OPS] Starting Google Flow operation...")
        print("=" * 60)
        hud.print("🚀 Starting Google Flow...", "info")
        
        # Update status to "starting_google_flow"
        try:
            panel_data['operation_status'] = "starting_google_flow"
            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(panel_data, f, indent=4)
            print("📝 [RUN_OPS] Updated status to: starting_google_flow")
        except Exception as e:
            print(f"⚠️ [RUN_OPS] Failed to update status: {e}")
        
        # Execute Google Flow
        try:
            operate_google_flow_browser()
            print("✅ [RUN_OPS] Google Flow operation completed successfully")
            
            # Update status to "completed_google_flow_operation"
            try:
                with open(PANEL_PATH, 'r', encoding='utf-8') as f:
                    panel_data = json.load(f)
                panel_data['operation_status'] = "completed_google_flow_operation"
                with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                    json.dump(panel_data, f, indent=4)
                print("📝 [RUN_OPS] Updated status to: completed_google_flow_operation")
            except Exception as e:
                print(f"⚠️ [RUN_OPS] Failed to update status: {e}")
                
        except KeyboardInterrupt:
            print("🛑 [RUN_OPS] Google Flow interrupted by user")
            raise
        except Exception as e:
            print(f"❌ [RUN_OPS] Google Flow failed: {e}")
            hud.print("❌ Google Flow failed", "error")
            # Don't update status on failure - allow retry
            return
    
    # --- Execute Grok operation ---
    if run_grok:
        print("=" * 60)
        print("🚀 [RUN_OPS] Starting Grok operation...")
        print("=" * 60)
        hud.print("🚀 Starting Grok...", "info")
        
        # Update status to "starting_grok_operation"
        try:
            with open(PANEL_PATH, 'r', encoding='utf-8') as f:
                panel_data = json.load(f)
            panel_data['operation_status'] = "starting_grok_operation"
            with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                json.dump(panel_data, f, indent=4)
            print("📝 [RUN_OPS] Updated status to: starting_grok_operation")
        except Exception as e:
            print(f"⚠️ [RUN_OPS] Failed to update status: {e}")
        
        # Execute Grok
        try:
            operate_grok_browser()
            print("✅ [RUN_OPS] Grok operation completed successfully")
            
            # Update status to "completed_grok_operation"
            try:
                with open(PANEL_PATH, 'r', encoding='utf-8') as f:
                    panel_data = json.load(f)
                panel_data['operation_status'] = "completed_grok_operation"
                with open(PANEL_PATH, 'w', encoding='utf-8') as f:
                    json.dump(panel_data, f, indent=4)
                print("📝 [RUN_OPS] Updated status to: completed_grok_operation")
            except Exception as e:
                print(f"⚠️ [RUN_OPS] Failed to update status: {e}")
                
        except KeyboardInterrupt:
            print("🛑 [RUN_OPS] Grok interrupted by user")
            raise
        except Exception as e:
            print(f"❌ [RUN_OPS] Grok failed: {e}")
            hud.print("❌ Grok failed", "error")
            # Don't update status on failure - allow retry
            return
    
    # --- All operations completed successfully ---
    print("=" * 60)
    print("🎉 [RUN_OPS] All operations completed successfully!")
    print("=" * 60)
    hud.print("🎉 All operations complete!", "success")
    
    # Update status to "all_operations_completed"
    try:
        with open(PANEL_PATH, 'r', encoding='utf-8') as f:
            panel_data = json.load(f)
        panel_data['operation_status'] = "all_operations_completed"
        with open(PANEL_PATH, 'w', encoding='utf-8') as f:
            json.dump(panel_data, f, indent=4)
        print("📝 [RUN_OPS] Updated status to: all_operations_completed")
    except Exception as e:
        print(f"⚠️ [RUN_OPS] Failed to update status: {e}")  


if __name__ == "__main__":
   operate_grok_browser()
    
