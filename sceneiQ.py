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


# Configure Paths
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata"
tessdata_path = r"C:\xampp\htdocs\AI automation\scenIQ\pytesseract\tessdata\eng.traineddata"
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SCREEN_IMAGE = r"C:\xampp\htdocs\AI automation\scenIQ\input_images\screen.png"
TEXT_TARGET = r"C:\xampp\htdocs\AI automation\scenIQ\text_target.json"
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
SCREEN_TEXT_CONTENT = r"C:\xampp\htdocs\AI automation\scenIQ\screen_content.text"
INPUT_IMAGES = r"C:\xampp\htdocs\AI automation\scenIQ\input_images"
GUI_IMAGES = r"C:\xampp\htdocs\AI automation\scenIQ\gui_images"
IMAGES_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\project"

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



def process_single_region(args):
    """
    Process a single region with vision.
    
    Args:
        args: Tuple containing (region_data, SCREEN_IMAGE, region_index)
    
    Returns:
        Dictionary with vision results for this region
    """
    import cv2
    import pytesseract
    import os
    
    region, preprocessed_SCREEN_IMAGE, idx = args
    
    try:
        # Load the preprocessed image
        image = cv2.imread(preprocessed_SCREEN_IMAGE)
        if image is None:
            return {'region_id': idx, 'error': f"Failed to load image at {preprocessed_SCREEN_IMAGE}"}
        
        left = region['left']
        top = region['top']
        right = region['right']
        bottom = region['bottom']
        
        # Crop the region from the image
        cropped = image[top:bottom, left:right]
        
        if cropped.size == 0:
            return {'region_id': idx, 'error': "Empty region", 'texts': []}
        
        # Process cropped region with Tesseract
        custom_config = (
            '--psm 11 -c tessedit_char_whitelist='
            '\'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:-_=@############/\\\\?&|()[]{}<>~°%©®+— \\"\\\'\''
        )
        
        data = pytesseract.image_to_data(cropped, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Extract text from this region
        region_texts = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            confidence = int(data['conf'][i])
            
            if text:
                # Adjust coordinates relative to the full image
                rel_left = data['left'][i] + left
                rel_top = data['top'][i] + top
                rel_width = data['width'][i]
                rel_height = data['height'][i]
                
                region_texts.append({
                    'text': text,
                    'left': rel_left,
                    'top': rel_top,
                    'right': rel_left + rel_width,
                    'bottom': rel_top + rel_height,
                    'width': rel_width,
                    'height': rel_height,
                    'confidence': confidence,
                    'region_id': idx
                })
        
        # Merge characters into words within this region
        if region_texts:
            region_texts.sort(key=lambda x: (x['top'], x['left']))
            
            merged_texts = []
            screen_height = image.shape[0]
            
            while region_texts:
                current = region_texts.pop(0)
                max_horizontal_gap = max(12, current['height'] * 0.4)
                max_vertical_deviation = current['height'] * 0.4
                
                merged_any = True
                while merged_any:
                    merged_any = False
                    for i, next_el in enumerate(region_texts):
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
                            
                            region_texts.pop(i)
                            merged_any = True
                            break
                
                # Fix common vision errors
                if "htips" in current['text']:
                    current['text'] = current['text'].replace("htips", "https")
                if "searcl" in current['text'].lower():
                    current['text'] = current['text'].lower().replace("searcl", "search").replace("Searcl", "Search")
                
                current['distance_from_top'] = current['top']
                current['distance_from_bottom'] = screen_height - current['bottom']
                current['screen_percentage'] = (current['top'] / screen_height) * 100
                
                merged_texts.append(current)
            
            return {
                'region_id': idx,
                'texts': merged_texts,
                'error': None
            }
        else:
            return {'region_id': idx, 'error': "No text found", 'texts': []}
            
    except Exception as e:
        return {'region_id': idx, 'error': str(e), 'texts': []}
    
def vision():
    def prepare_file():
        """
        Captures the screen, saves it to SCREEN_IMAGE, and creates/empties the output text file.
        """
        
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            print(f"❌ Error: Tesseract executable not found at: {pytesseract.pytesseract.tesseract_cmd}")
            return None
        if not os.path.exists(tessdata_path):
            print(f"❌ Error: English language data not found at: {tessdata_path}")
            return None
            
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(SCREEN_TEXT_CONTENT), exist_ok=True)
            os.makedirs(os.path.dirname(SCREEN_IMAGE), exist_ok=True)
            
            # Create/empty the output text file
            with open(SCREEN_TEXT_CONTENT, 'w', encoding='utf-8') as f:
                pass  # Just create or empty the file
            print(f"📝 Created/emptied output file: {SCREEN_TEXT_CONTENT}")
            
            # Capture screen
            print("📸 Capturing screen...")
            screenshot = pyautogui.screenshot()
            
            # Save to SCREEN_IMAGE
            screenshot.save(SCREEN_IMAGE)
            print(f"✅ Screen saved to: {SCREEN_IMAGE}")
            
            screen_width, screen_height = pyautogui.size()
            print(f"🖥️ Screen Dimensions: {screen_width} x {screen_height} pixels")
            
            print("="*80)
            print(f"✅ Ready for processing. Image saved to: {SCREEN_IMAGE}")
            print(f"✅ Output file ready at: {SCREEN_TEXT_CONTENT}")
            print("="*80)
            
            return True
            
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def preprocess_image():
        """
        Loads the image from global SCREEN_IMAGE, applies CLAHE for contrast enhancement,
        and uses adaptive thresholding to robustly handle varied text colors, uneven lighting,
        and shadows (preventing broken characters), then saves the result.
        Also detects text regions and records their positions to a text file.
        Takes no parameters.
        """
        import numpy as np
        
        # Ensure SCREEN_IMAGE is available
        if 'SCREEN_IMAGE' not in globals() and 'SCREEN_IMAGE' not in locals():
            print("❌ Error: 'SCREEN_IMAGE' variable is not defined.")
            return None

        if not os.path.exists(SCREEN_IMAGE):
            print(f"❌ Error: Image not found at: {SCREEN_IMAGE}")
            return None

        # Load image
        img = cv2.imread(SCREEN_IMAGE)
        if img is None:
            print(f"❌ Error: Failed to load image at {SCREEN_IMAGE}")
            return None

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) 
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Apply Adaptive Thresholding
        preprocessed_img = cv2.adaptiveThreshold(
            enhanced, 
            255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            blockSize=11, 
            C=2
        )

        # Load original color image
        original_color = cv2.imread(SCREEN_IMAGE)
        if original_color is None:
            print("❌ Error: Failed to load original image for visualization")
            return None
        
        # Find all black regions
        black_mask = (preprocessed_img == 0).astype(np.uint8) * 255
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            black_mask, 
            connectivity=8
        )
        
        # Define size threshold
        LARGE_REGION_THRESHOLD = 500
        
        # Store detected boxes
        detected_boxes = []
        
        # Process each connected component
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            if area >= LARGE_REGION_THRESHOLD:
                # Draw green border
                cv2.rectangle(original_color, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Store box coordinates (left, top, right, bottom)
                detected_boxes.append({
                    'left': x,
                    'top': y,
                    'right': x + w,
                    'bottom': y + h,
                    'width': w,
                    'height': h,
                    'area': area
                })
        
        # ===== TEXT REGION DETECTION (Sub-boxing) =====
        print("🔍 Detecting text regions and sub-boxing...")
        
        # 1. Adaptive Thresholding for text detection
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 15, 8
        )

        # 2. Pass 1: Macro-level grouping (find lines/paragraphs)
        macro_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 3))
        macro_dilated = cv2.dilate(thresh, macro_kernel, iterations=1)
        macro_closing = cv2.morphologyEx(macro_dilated, cv2.MORPH_CLOSE, macro_kernel)
        
        contours, _ = cv2.findContours(macro_closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        padding = 3  # 3px padding around text chunks
        text_boxes = []

        # 3. Pass 2: Sub-boxing wide regions into individual word chunks
        micro_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 1))

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Filter layout noise
            if w > 12 and h > 8 and w < img.shape[1] * 0.95 and h < img.shape[0] * 0.4:
                # If the block is wide (multiple words or sentence), sub-segment it
                if w > 75:  
                    roi_thresh = thresh[y:y+h, x:x+w]
                    roi_dilated = cv2.dilate(roi_thresh, micro_kernel, iterations=1)
                    sub_contours, _ = cv2.findContours(roi_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    sub_found = False
                    for sub_cnt in sub_contours:
                        sx, sy, sw, sh = cv2.boundingRect(sub_cnt)
                        if sw > 4 and sh > 4:  # Valid sub-box dimensions
                            global_x = x + sx
                            global_y = y + sy
                            
                            x_pad = max(0, global_x - padding)
                            y_pad = max(0, global_y - padding)
                            w_pad = min(img.shape[1] - x_pad, sw + (2 * padding))
                            h_pad = min(img.shape[0] - y_pad, sh + (2 * padding))
                            
                            text_boxes.append({
                                'left': x_pad,
                                'top': y_pad,
                                'right': x_pad + w_pad,
                                'bottom': y_pad + h_pad,
                                'width': w_pad,
                                'height': h_pad
                            })
                            # Draw inner sub-boxes in Orange (BGR: 0, 140, 255)
                            cv2.rectangle(original_color, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 140, 255), 1)
                            sub_found = True
                    
                    # Fallback if sub-segmentation didn't split it cleanly
                    if not sub_found:
                        x_pad = max(0, x - padding)
                        y_pad = max(0, y - padding)
                        w_pad = min(img.shape[1] - x_pad, w + (2 * padding))
                        h_pad = min(img.shape[0] - y_pad, h + (2 * padding))
                        text_boxes.append({
                            'left': x_pad,
                            'top': y_pad,
                            'right': x_pad + w_pad,
                            'bottom': y_pad + h_pad,
                            'width': w_pad,
                            'height': h_pad
                        })
                        cv2.rectangle(original_color, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 255, 0), 2)
                else:
                    # Small box, keep as a single chunk
                    x_pad = max(0, x - padding)
                    y_pad = max(0, y - padding)
                    w_pad = min(img.shape[1] - x_pad, w + (2 * padding))
                    h_pad = min(img.shape[0] - y_pad, h + (2 * padding))
                    text_boxes.append({
                        'left': x_pad,
                        'top': y_pad,
                        'right': x_pad + w_pad,
                        'bottom': y_pad + h_pad,
                        'width': w_pad,
                        'height': h_pad
                    })
                    cv2.rectangle(original_color, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 255, 0), 2)

        # ===== RECORD BOX POSITIONS TO TEXT FILE =====
        print(f"📝 Recording box positions to: {SCREEN_TEXT_CONTENT}")
        
        with open(SCREEN_TEXT_CONTENT, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("DETECTED LARGE REGIONS (Green Boxes)\n")
            f.write("=" * 60 + "\n\n")
            
            for idx, box in enumerate(detected_boxes, 1):
                f.write(f"Large Region #{idx}:\n")
                f.write(f"  Left: {box['left']}\n")
                f.write(f"  Top: {box['top']}\n")
                f.write(f"  Right: {box['right']}\n")
                f.write(f"  Bottom: {box['bottom']}\n")
                f.write(f"  Width: {box['width']}\n")
                f.write(f"  Height: {box['height']}\n")
                f.write(f"  Area: {box['area']} pixels\n")
                f.write("-" * 40 + "\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("DETECTED TEXT REGIONS (Orange/Green Sub-boxes)\n")
            f.write("=" * 60 + "\n\n")
            
            for idx, box in enumerate(text_boxes, 1):
                f.write(f"Text Region #{idx}:\n")
                f.write(f"  Left: {box['left']}\n")
                f.write(f"  Top: {box['top']}\n")
                f.write(f"  Right: {box['right']}\n")
                f.write(f"  Bottom: {box['bottom']}\n")
                f.write(f"  Width: {box['width']}\n")
                f.write(f"  Height: {box['height']}\n")
                f.write("-" * 40 + "\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"SUMMARY:\n")
            f.write(f"  Total Large Regions: {len(detected_boxes)}\n")
            f.write(f"  Total Text Regions: {len(text_boxes)}\n")
            f.write("=" * 60 + "\n")
        
        # Save the image as preprocessed.png
        base = os.path.dirname(SCREEN_IMAGE)
        marked_original_path = os.path.join(base, "preprocessed.png")
        cv2.imwrite(marked_original_path, original_color)
        
        print(f"✅ Saved: {marked_original_path}")
        print(f"✅ Detected {len(detected_boxes)} large regions and {len(text_boxes)} text regions")
        
        return marked_original_path

    def full_image_vision():
        """
        Process the entire image at once without using regions or multiprocessing.
        This runs FIRST as the primary approach.
        
        Returns:
            List of vision results for the entire image, or None if failed
        """
        import cv2
        import pytesseract
        import os
        import json
        from datetime import datetime
        
        # Check if Tesseract is available
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            print(f"❌ Error: Tesseract executable not found at: {pytesseract.pytesseract.tesseract_cmd}")
            return None
        if not os.path.exists(tessdata_path):
            print(f"❌ Error: English language data not found at: {tessdata_path}")
            return None
        
        # Check if preprocessed image exists
        preprocessed_SCREEN_IMAGE = os.path.join(os.path.dirname(SCREEN_IMAGE), "preprocessed.png")
        if not os.path.exists(preprocessed_SCREEN_IMAGE):
            print(f"❌ Error: Preprocessed image not found at: {preprocessed_SCREEN_IMAGE}")
            return None
        
        try:
            # Load the preprocessed image
            print(f"📂 Loading preprocessed image from: {preprocessed_SCREEN_IMAGE}")
            image = cv2.imread(preprocessed_SCREEN_IMAGE)
            if image is None:
                print(f"❌ Error: Failed to load image at {preprocessed_SCREEN_IMAGE}")
                return None
            
            screen_height, screen_width = image.shape[:2]
            print(f"🖥️ Image Dimensions: {screen_width} x {screen_height} pixels")
            
            # Process the entire image with Tesseract
            print("🔍 Running FULL IMAGE vision (First Attempt)...")
            
            custom_config = (
                '--psm 11 -c tessedit_char_whitelist='
                '\'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:-_=@############/\\\\?&|()[]{}<>~°%©®+— \\"\\\'\''
            )
            
            data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
            
            # Extract text from the entire image
            all_texts = []
            n_boxes = len(data['text'])
            
            for i in range(n_boxes):
                text = data['text'][i].strip()
                confidence = int(data['conf'][i])
                
                if text:
                    all_texts.append({
                        'text': text,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'right': data['left'][i] + data['width'][i],
                        'bottom': data['top'][i] + data['height'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'confidence': confidence,
                        'region_id': 0  # Single region for entire image
                    })
            
            # Merge characters into words
            if all_texts:
                all_texts.sort(key=lambda x: (x['top'], x['left']))
                
                merged_texts = []
                
                while all_texts:
                    current = all_texts.pop(0)
                    max_horizontal_gap = max(12, current['height'] * 0.4)
                    max_vertical_deviation = current['height'] * 0.4
                    
                    merged_any = True
                    while merged_any:
                        merged_any = False
                        for i, next_el in enumerate(all_texts):
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
                                
                                all_texts.pop(i)
                                merged_any = True
                                break
                    
                    # Fix common vision errors
                    if "htips" in current['text']:
                        current['text'] = current['text'].replace("htips", "https")
                    if "searcl" in current['text'].lower():
                        current['text'] = current['text'].lower().replace("searcl", "search").replace("Searcl", "Search")
                    
                    current['distance_from_top'] = current['top']
                    current['distance_from_bottom'] = screen_height - current['bottom']
                    current['screen_percentage'] = (current['top'] / screen_height) * 100
                    
                    merged_texts.append(current)
                
                # Prepare JSON data
                json_data = []
                for idx, result in enumerate(merged_texts, 1):
                    json_data.append({
                        f"text_{idx}": result['text'],
                        "coordinates": {
                            "top": result['top'],
                            "right": result['right'],
                            "left": result['left'],
                            "bottom": result['bottom']
                        }
                    })
                
                # Append vision results to the text file
                print(f"\n📝 Appending FULL IMAGE vision results to: {SCREEN_TEXT_CONTENT}")
                
                with open(SCREEN_TEXT_CONTENT, 'a', encoding='utf-8') as f:
                    # Existing text format
                    f.write("\n\n" + "="*80 + "\n")
                    f.write("FULL IMAGE vision RESULTS (Primary Attempt - No Regions)\n")
                    f.write("="*80 + "\n")
                    f.write(f"Processed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Text Blocks Found: {len(merged_texts)}\n")
                    f.write(f"Image Dimensions: {screen_width} x {screen_height} pixels\n")
                    f.write("="*80 + "\n\n")
                    
                    for idx, result in enumerate(merged_texts, 1):
                        f.write(f"TEXT BLOCK #{idx}:\n")
                        f.write(f"  • {result['text']}\n")
                        f.write(f"    Left: {result['left']:>6}  Top: {result['top']:>6}\n")
                        f.write(f"    Right: {result['right']:>6}  Bottom: {result['bottom']:>6}\n")
                        f.write(f"    Width: {result['width']:>6}  Height: {result['height']:>6}\n")
                        f.write(f"    Confidence: {result['confidence']}%\n")
                        f.write(f"    Distance from Top: {result['distance_from_top']:>6}px ({result['screen_percentage']:.1f}%)\n")
                        f.write("-" * 30 + "\n")
                    
                    # Write compact format
                    f.write("\n" + "="*80 + "\n")
                    f.write("COMPACT FORMAT (left, top, right, bottom, text):\n")
                    f.write("="*80 + "\n")
                    for result in merged_texts:
                        f.write(f"{result['left']:>6}, {result['top']:>6}, {result['right']:>6}, {result['bottom']:>6}, '{result['text']}'\n")
                    
                    # JSON format
                    f.write("\n\n" + "="*80 + "\n")
                    f.write("JSON FORMAT:\n")
                    f.write("="*80 + "\n")
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                
                # Summary
                print("\n" + "="*80)
                print(f"✅ FULL IMAGE vision COMPLETE!")
                print(f"  • Total Text Blocks Found: {len(merged_texts)}")
                print(f"  • Results Appended to: {SCREEN_TEXT_CONTENT}")
                print("="*80)
                
                return merged_texts
            else:
                return []
                
        except Exception as e:
            print(f"❌ Error during full image vision: {e}")
            import traceback
            traceback.print_exc()
            return None

    def region_based_vision():
        """
        Reads region coordinates from SCREEN_TEXT_CONTENT, processes each region individually
        using ThreadPoolExecutor for parallel processing, and appends vision results back to the text file.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import json
        from datetime import datetime
        
        # Path to the specific image file requested
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
            print(f"❌ Error: Tesseract executable not found at: {pytesseract.pytesseract.tesseract_cmd}")
            return None
        if not os.path.exists(tessdata_path):
            print(f"❌ Error: English language data not found at: {tessdata_path}")
            return None
            
        # Check if preprocessed image exists
        preprocessed_SCREEN_IMAGE = os.path.join(os.path.dirname(SCREEN_IMAGE), "preprocessed.png")
        if not os.path.exists(preprocessed_SCREEN_IMAGE):
            print(f"❌ Error: Preprocessed image not found at: {preprocessed_SCREEN_IMAGE}")
            return None
        
        # Check if output text file exists with region data
        if not os.path.exists(SCREEN_TEXT_CONTENT):
            print(f"❌ Error: Output text file not found at: {SCREEN_TEXT_CONTENT}")
            return None

        try:
            # Load the preprocessed image
            print(f"📂 Loading preprocessed image from: {preprocessed_SCREEN_IMAGE}")
            image = cv2.imread(preprocessed_SCREEN_IMAGE)
            if image is None:
                print(f"❌ Error: Failed to load image at {preprocessed_SCREEN_IMAGE}")
                return None
                
            screen_height, screen_width = image.shape[:2]
            print(f"🖥️ Image Dimensions: {screen_width} x {screen_height} pixels")
            
            # Parse the text file to extract region coordinates
            print(f"📝 Reading regions from: {SCREEN_TEXT_CONTENT}")
            
            regions = []
            current_region = {}
            reading_large_regions = False
            reading_text_regions = False
            
            with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                
                # Detect which section we're in
                if "DETECTED LARGE REGIONS" in line:
                    reading_large_regions = True
                    reading_text_regions = False
                    continue
                elif "DETECTED TEXT REGIONS" in line:
                    reading_large_regions = False
                    reading_text_regions = True
                    continue
                elif "SUMMARY" in line:
                    break
                    
                # Parse region data
                if "Large Region #" in line or "Text Region #" in line:
                    if current_region and 'left' in current_region:
                        regions.append(current_region)
                    current_region = {}
                    continue
                    
                # Parse coordinate lines
                if "Left:" in line:
                    current_region['left'] = int(line.split("Left:")[1].strip())
                elif "Top:" in line:
                    current_region['top'] = int(line.split("Top:")[1].strip())
                elif "Right:" in line:
                    current_region['right'] = int(line.split("Right:")[1].strip())
                elif "Bottom:" in line:
                    current_region['bottom'] = int(line.split("Bottom:")[1].strip())
                elif "Width:" in line:
                    current_region['width'] = int(line.split("Width:")[1].strip())
                elif "Height:" in line:
                    current_region['height'] = int(line.split("Height:")[1].strip())
                elif "Area:" in line and reading_large_regions:
                    current_region['area'] = int(line.split("Area:")[1].strip().split()[0])
            
            # Add the last region
            if current_region and 'left' in current_region:
                regions.append(current_region)
            
            print(f"✅ Found {len(regions)} regions to process")
            
            if len(regions) == 0:
                print("⚠️ No regions found to process")
                return None
            
            # Prepare arguments for parallel processing
            args_list = [(region, preprocessed_SCREEN_IMAGE, idx) for idx, region in enumerate(regions, 1)]
            
            # Determine number of workers (threads)
            # Use more threads than CPU cores for I/O bound operations
            max_workers = min(len(regions), 100)  # Max 100 threads
            print(f"🚀 Starting parallel processing with {max_workers} threads...")
            
            # Process regions in parallel using ThreadPoolExecutor
            vision_results = []
            region_count = 0
            failed_regions = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_result = {
                    executor.submit(process_single_region, args): idx 
                    for idx, args in enumerate(args_list, 1)
                }
                
                # Process results as they complete
                for future in as_completed(future_to_result):
                    region_id = future_to_result[future]
                    try:
                        result = future.result(timeout=60)  # 60 second timeout per region
                        region_count += 1
                        
                        if result['error']:
                            failed_regions += 1
                            print(f"  ⚠️ Region #{result['region_id']}: {result['error']}")
                        else:
                            texts_found = len(result.get('texts', []))
                            print(f"  ✅ Region #{result['region_id']}: Found {texts_found} text blocks")
                        
                        vision_results.append(result)
                        
                        # Show progress
                        progress = (region_count / len(regions)) * 100
                        
                    except Exception as e:
                        failed_regions += 1
                        region_count += 1
                        print(f"  ❌ Region #{region_id} failed with exception: {e}")
                        vision_results.append({
                            'region_id': region_id,
                            'error': str(e),
                            'texts': []
                        })
            
            # Combine results
            all_vision_results = []
            for result in vision_results:
                if not result.get('error') and result.get('texts'):
                    all_vision_results.extend(result['texts'])
            
            # Sort results by region_id then by position
            all_vision_results.sort(key=lambda x: (x['region_id'], x['top'], x['left']))
            
            print(f"\n✅ Processed {region_count} regions, found {len(all_vision_results)} text blocks")
            
            # Prepare JSON data
            json_data = []
            for idx, result in enumerate(all_vision_results, 1):
                json_data.append({
                    f"text_{idx}": result['text'],
                    "coordinates": {
                        "top": result['top'],
                        "right": result['right'],
                        "left": result['left'],
                        "bottom": result['bottom']
                    }
                })
            
            # Append vision results to the text file
            print(f"\n📝 Appending vision results to: {SCREEN_TEXT_CONTENT}")
            
            with open(SCREEN_TEXT_CONTENT, 'a', encoding='utf-8') as f:
                # Existing text format
                f.write("\n\n" + "="*80 + "\n")
                f.write("vision EXTRACTION RESULTS (Per Region - Parallel Processing with Threads)\n")
                f.write("="*80 + "\n")
                f.write(f"Processed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Regions Processed: {region_count}\n")
                f.write(f"Total Text Blocks Found: {len(all_vision_results)}\n")
                f.write(f"Failed Regions: {failed_regions}\n")
                f.write(f"Parallel Workers: {max_workers} threads\n")
                f.write("="*80 + "\n\n")
                
                # Group results by region
                current_region = 0
                for result in all_vision_results:
                    if result['region_id'] != current_region:
                        current_region = result['region_id']
                        f.write(f"\n{'─'*40}\n")
                        f.write(f"REGION #{current_region} RESULTS:\n")
                        f.write(f"{'─'*40}\n")
                    
                    f.write(f"  • {result['text']}\n")
                    f.write(f"    Left: {result['left']:>6}  Top: {result['top']:>6}\n")
                    f.write(f"    Right: {result['right']:>6}  Bottom: {result['bottom']:>6}\n")
                    f.write(f"    Width: {result['width']:>6}  Height: {result['height']:>6}\n")
                    f.write(f"    Confidence: {result['confidence']}%\n")
                    f.write(f"    Distance from Top: {result['distance_from_top']:>6}px ({result['screen_percentage']:.1f}%)\n")
                    f.write("-" * 30 + "\n")
                
                # Write compact format
                f.write("\n" + "="*80 + "\n")
                f.write("COMPACT FORMAT (left, top, right, bottom, text):\n")
                f.write("="*80 + "\n")
                for result in all_vision_results:
                    f.write(f"{result['left']:>6}, {result['top']:>6}, {result['right']:>6}, {result['bottom']:>6}, '{result['text']}'\n")
                
                # JSON format
                f.write("\n\n" + "="*80 + "\n")
                f.write("JSON FORMAT:\n")
                f.write("="*80 + "\n")
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            
            # Summary
            print("\n" + "="*80)
            print(f"✅ vision COMPLETE!")
            print(f"  • Regions Processed: {region_count}")
            print(f"  • Total Text Blocks Found: {len(all_vision_results)}")
            print(f"  • Failed Regions: {failed_regions}")
            print(f"  • Results Appended to: {SCREEN_TEXT_CONTENT}")
            print("="*80)
            
            return all_vision_results

        except Exception as e:
            print(f"❌ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def normalize_text_for_comparison(text):
        """
        Normalize text for comparison by removing all non-alphanumeric characters
        and converting to lowercase.
        """
        if not text:
            return ""
        # Remove all non-alphanumeric characters and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

    def main():
        
        print("🚀 Starting vision Process...")
        
        # Step 1: Capture screen and prepare files
        result1 = prepare_file()
        if result1 is None:
            print("❌ Failed to prepare file. Exiting.")
            return
        
        # Step 2: Preprocess image and detect regions
        result2 = preprocess_image()
        if result2 is None:
            print("❌ Failed to preprocess image. Exiting.")
            return
        
        # Step 3: Run FULL IMAGE vision FIRST
        print("=" * 80)
        print("🔍 Running FULL IMAGE vision (First Attempt)...")
        print("=" * 80)
        
        full_image_vision()
        
        # Step 4: Check if the text target value was found in the screen content
        # Read the text target file to get the value we're looking for
        target_value = None
        try:
            if os.path.exists(TEXT_TARGET):
                with open(TEXT_TARGET, 'r', encoding='utf-8') as file:
                    text_target_data = json.load(file)
                    target_value = text_target_data.get('value', '')
                    print(f"🔍 [MAIN] Looking for target value: '{target_value}'")
        except Exception as e:
            print(f"⚠️ [MAIN] Error reading text target: {e}")
        
        # Normalize the target value for comparison
        target_found_in_full_image = False
        
        if target_value:
            # Read the screen content file to check if target value was found
            try:
                if os.path.exists(SCREEN_TEXT_CONTENT):
                    with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                        screen_content = file.read()
                    
                    # Normalize both the target and the screen content for comparison
                    normalized_target = normalize_text_for_comparison(target_value)
                    
                    # Check if the normalized target is in the screen content
                    # Also check for common variations
                    target_variations = [
                        target_value,
                        target_value.lower(),
                        target_value.upper(),
                        target_value.replace(' ', ''),
                        target_value.replace(' ', '').lower(),
                        target_value.replace(' ', '').upper(),
                        target_value.replace(' ', '|'),
                        target_value.replace(' ', ':'),
                        target_value.replace(' ', ''),
                        target_value.replace(' ', '') + '|',
                        target_value.replace(' ', '') + ':',
                    ]
                    
                    # Remove duplicates
                    target_variations = list(set(target_variations))
                    
                    print(f"🔍 [MAIN] Checking for target variations: {target_variations[:5]}...")
                    
                    for variation in target_variations:
                        if variation in screen_content:
                            print(f"✅ [MAIN] Found target value variation in FULL IMAGE vision: '{variation}'")
                            target_found_in_full_image = True
                            break
                    
                    # Also check using regex for case-insensitive matching
                    if not target_found_in_full_image:
                        # Use regex with re.IGNORECASE
                        pattern = re.compile(re.escape(target_value), re.IGNORECASE)
                        if pattern.search(screen_content):
                            print(f"✅ [MAIN] Found target value (case-insensitive) in FULL IMAGE vision: '{target_value}'")
                            target_found_in_full_image = True
                    
                    # Also check normalized form (remove all non-alphanumeric)
                    if not target_found_in_full_image:
                        normalized_screen = re.sub(r'[^a-zA-Z0-9]', '', screen_content).lower()
                        if normalized_target in normalized_screen:
                            print(f"✅ [MAIN] Found normalized target in FULL IMAGE vision: '{normalized_target}'")
                            target_found_in_full_image = True
                            
                else:
                    print(f"⚠️ [MAIN] screen_content.text not found at: {SCREEN_TEXT_CONTENT}")
                    
            except Exception as e:
                print(f"⚠️ [MAIN] Error checking screen content: {e}")
        
        # Step 5: Decide whether to run region-based vision
        if target_found_in_full_image:
            print("=" * 80)
            print(f"✅ [MAIN] Target value '{target_value}' found in FULL IMAGE vision!")
            print("🔄 [MAIN] Skipping region-based vision (target already found)")
            print("=" * 80)
            print("✅ vision COMPLETE! (Target found in full image)")
        else:
            print("=" * 80)
            print(f"❌ [MAIN] Target value '{target_value}' NOT found in FULL IMAGE vision.")
            print("🔄 [MAIN] Running region-based vision as fallback...")
            print("=" * 80)
            region_based_vision()
            
            # After region-based vision, check again if target was found
            try:
                if os.path.exists(SCREEN_TEXT_CONTENT):
                    with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                        screen_content = file.read()
                    
                    if target_value and target_value in screen_content:
                        print(f"✅ [MAIN] Target value found in region-based vision results!")
            except Exception as e:
                print(f"⚠️ [MAIN] Error checking screen content after region-based vision: {e}")
        
        # Final summary
        print("=" * 80)

    # Execute main
    main()
    
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

def operate_google_flow_project():
    """
    Launches/uses Microsoft Edge for Google Flow operations.
    Features: Live HUD tracking, click-through overlay, 
    global hotkey interception, and simple URL launch with "all media" detection.
    Uses JSON format for text extraction and case-insensitive/normalized text matching.
    Includes full download mechanism with modal dismissal, zip extraction, and image validation.
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
        update_operation_status(f"Aborting Google Flow operation: {reason}", is_abort=True)
        # The update_operation_status will raise SystemExit

    def check_operation_status():
        """Check if operation status is still valid (not aborted/errored)."""
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting Google Flow operation", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status("Google Flow operation manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status("Google Flow operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

    def safe_vision():
        """
        Capture screen without hiding the HUD (HUD is click-through)
        AND properly parse the screen_content.text file to return text elements.
        Now uses JSON format for parsing.
        """
        check_for_termination()
        
        # Call the vision() function to capture screen
        vision()
        
        # Now read the screen_content.text file to get the parsed results
        text_elements = []
        
        try:
            if os.path.exists(SCREEN_TEXT_CONTENT):
                with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # ============================================
                # FIRST: Parse JSON format from FULL IMAGE vision RESULTS
                # ============================================
                # Look for JSON array in the FULL IMAGE section
                full_image_json_match = re.search(
                    r'FULL IMAGE vision RESULTS.*?JSON FORMAT:\s*=\s*\n(\[.*?\])\s*(?=\n\n|$|\s*vision EXTRACTION RESULTS)',
                    content,
                    re.DOTALL | re.IGNORECASE
                )
                
                if full_image_json_match:
                    try:
                        json_text = full_image_json_match.group(1)
                        # Clean up any extraneous text that might be in the JSON
                        json_text = re.sub(r'^[^{[]*', '', json_text)
                        json_text = re.sub(r'[^}\]]*$', '', json_text)
                        json_data = json.loads(json_text)
                        
                        for item in json_data:
                            # Extract text from the dynamic key (text_1, text_2, etc.)
                            text_value = None
                            for key, value in item.items():
                                if key.startswith('text_'):
                                    text_value = value
                                    break
                            
                            if text_value and 'coordinates' in item:
                                coords = item['coordinates']
                                text_elements.append({
                                    'text': text_value.strip(),
                                    'left': coords.get('left', 0),
                                    'top': coords.get('top', 0),
                                    'right': coords.get('right', 0),
                                    'bottom': coords.get('bottom', 0),
                                    'width': coords.get('right', 0) - coords.get('left', 0),
                                    'height': coords.get('bottom', 0) - coords.get('top', 0)
                                })
                        
                        if text_elements:
                            print(f"✅ [VISION] Parsed {len(text_elements)} text elements from FULL IMAGE JSON section")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ [VISION] Failed to parse FULL IMAGE JSON: {e}")
                        # Continue to next parsing method if JSON fails
                
                # ============================================
                # SECOND: Parse JSON format from REGION-BASED vision RESULTS
                # ============================================
                if not text_elements:
                    # Find all JSON sections from region-based results
                    region_json_matches = re.findall(
                        r'vision EXTRACTION RESULTS.*?JSON FORMAT:\s*=\s*\n(\[.*?\])\s*(?=\n\n|$|\s*FULL IMAGE vision RESULTS)',
                        content,
                        re.DOTALL | re.IGNORECASE
                    )
                    
                    for json_match in region_json_matches:
                        try:
                            json_text = json_match
                            json_text = re.sub(r'^[^{[]*', '', json_text)
                            json_text = re.sub(r'[^}\]]*$', '', json_text)
                            json_data = json.loads(json_text)
                            
                            for item in json_data:
                                text_value = None
                                for key, value in item.items():
                                    if key.startswith('text_'):
                                        text_value = value
                                        break
                                
                                if text_value and 'coordinates' in item:
                                    coords = item['coordinates']
                                    text_elements.append({
                                        'text': text_value.strip(),
                                        'left': coords.get('left', 0),
                                        'top': coords.get('top', 0),
                                        'right': coords.get('right', 0),
                                        'bottom': coords.get('bottom', 0),
                                        'width': coords.get('right', 0) - coords.get('left', 0),
                                        'height': coords.get('bottom', 0) - coords.get('top', 0)
                                    })
                            
                            if text_elements:
                                print(f"✅ [VISION] Parsed {len(text_elements)} text elements from REGION-BASED JSON section")
                                break
                        except json.JSONDecodeError as e:
                            print(f"⚠️ [VISION] Failed to parse REGION-BASED JSON: {e}")
                            continue
                
                # ============================================
                # THIRD: Fallback - Try parsing TEXT format if JSON parsing failed
                # ============================================
                if not text_elements:
                    print("ℹ️ [VISION] No JSON data found, falling back to text format parsing...")
                    
                    # Parse FULL IMAGE vision RESULTS (text format)
                    text_blocks = re.findall(
                        r'TEXT BLOCK #\d+:\s*•\s*(.+?)\s+Left:\s*(\d+)\s+Top:\s*(\d+)\s+Right:\s*(\d+)\s+Bottom:\s*(\d+)\s+Width:\s*(\d+)\s+Height:\s*(\d+)',
                        content,
                        re.DOTALL
                    )
                    
                    for match in text_blocks:
                        text, left, top, right, bottom, width, height = match
                        text_elements.append({
                            'text': text.strip(),
                            'left': int(left),
                            'top': int(top),
                            'right': int(right),
                            'bottom': int(bottom),
                            'width': int(width),
                            'height': int(height)
                        })
                    
                    if text_elements:
                        print(f"✅ [VISION] Parsed {len(text_elements)} text elements from FULL IMAGE text section")
                    
                    # Parse REGION-BASED vision RESULTS (text format)
                    if not text_elements:
                        region_sections = re.findall(
                            r'────────────────────────────────────────\s*REGION #(\d+) RESULTS:\s*────────────────────────────────────────\s*(.*?)(?=(?:────────────────────────────────────────\s*REGION #\d+ RESULTS:|$))',
                            content,
                            re.DOTALL | re.IGNORECASE
                        )
                        
                        region_count = 0
                        for region_num, region_content in region_sections:
                            region_texts = re.findall(
                                r'•\s*(.+?)\s+Left:\s*(\d+)\s+Top:\s*(\d+)\s+Right:\s*(\d+)\s+Bottom:\s*(\d+)\s+Width:\s*(\d+)\s+Height:\s*(\d+)',
                                region_content,
                                re.DOTALL
                            )
                            
                            for match in region_texts:
                                text, left, top, right, bottom, width, height = match
                                text_elements.append({
                                    'text': text.strip(),
                                    'left': int(left),
                                    'top': int(top),
                                    'right': int(right),
                                    'bottom': int(bottom),
                                    'width': int(width),
                                    'height': int(height)
                                })
                                region_count += 1
                        
                        if region_count > 0:
                            print(f"✅ [VISION] Parsed {region_count} text elements from REGION-BASED text sections")
                    
                    # Parse COMPACT FORMAT section as last resort
                    if not text_elements:
                        compact_section = re.search(
                            r'COMPACT FORMAT.*?\n(.*?)(?:\n\n|\Z)',
                            content,
                            re.DOTALL | re.IGNORECASE
                        )
                        
                        if compact_section:
                            compact_lines = compact_section.group(1).strip().split('\n')
                            for line in compact_lines:
                                if line.strip():
                                    match = re.match(
                                        r'\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*[\'"](.+?)[\'"]\s*$',
                                        line.strip()
                                    )
                                    if match:
                                        left, top, right, bottom, text = match.groups()
                                        text_elements.append({
                                            'text': text.strip(),
                                            'left': int(left),
                                            'top': int(top),
                                            'right': int(right),
                                            'bottom': int(bottom),
                                            'width': int(right) - int(left),
                                            'height': int(bottom) - int(top)
                                        })
                            
                            if text_elements:
                                print(f"✅ [VISION] Parsed {len(text_elements)} text elements from COMPACT format")
                
                # ============================================
                # FINAL: Log what we found
                # ============================================
                if text_elements:
                    print(f"📊 [VISION] TOTAL: {len(text_elements)} text elements parsed")
                    # Print first 5 for debugging
                    for i, el in enumerate(text_elements[:5]):
                        print(f"  [{i}] '{el.get('text', '')}'")
                else:
                    print(f"⚠️ [VISION] Could not parse any text elements from screen_content.text")
                    
        except Exception as e:
            print(f"⚠️ [VISION] Error reading screen_content.text: {e}")
        
        return text_elements
    
    # ============================================
    # TEXT NORMALIZATION HELPERS
    # ============================================
    
    def normalize_text_for_comparison(text):
        """
        Normalize text for comparison by:
        1. Converting to lowercase
        2. Removing all non-alphanumeric characters (spaces, punctuation, special chars)
        3. This makes "all media", "AllMedia", "all-media", "all_media" all become "allmedia"
        
        Args:
            text: The text string to normalize
            
        Returns:
            Normalized string with only alphanumeric characters, lowercase
        """
        if not text:
            return ""
        
        # Convert to lowercase
        t = text.lower()
        
        # Remove all non-alphanumeric characters
        # This handles spaces, apostrophes, hyphens, underscores, punctuation, etc.
        t = re.sub(r'[^a-z0-9]', '', t)
        
        return t

    def text_contains_normalized(text_to_search, target_text):
        """
        Check if target_text is contained in text_to_search using normalized comparison.
        
        Args:
            text_to_search: The text to search within
            target_text: The target text to look for
            
        Returns:
            True if the normalized target is found in the normalized search text
        """
        if not text_to_search or not target_text:
            return False
        
        normalized_search = normalize_text_for_comparison(text_to_search)
        normalized_target = normalize_text_for_comparison(target_text)
        
        return normalized_target in normalized_search

    def clean_string_completely(text):
        """
        Clean a string for comparison by:
        1. Converting to lowercase
        2. Removing all non-alphanumeric characters
        3. Removing common URL prefixes
        4. Normalizing spaces and special characters
        
        This ensures that "iamkennyking's project_1" and "iamkennyking'sproject_1" 
        both become "iamkennykingsproject1"
        """
        if not text:
            return ""
        
        # Convert to lowercase
        t = text.lower()
        
        # Remove common URL prefixes
        t = t.replace("https://", "").replace("http://", "").replace("www.", "")
        
        # Remove all non-alphanumeric characters (this handles apostrophes, spaces, underscores, etc.)
        # This is the key change - it removes ALL non-alphanumeric characters
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
                update_operation_status("Browser window ready for Google Flow operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for Google Flow operation...")
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
                    update_operation_status("Browser launched for Google Flow operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        error_msg = "Failed to get or launch Edge window for Google Flow operation"
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
        hud.print("📋 Navigating to URL...", "typing")
        print(f"📋 Pasting URL: {url}")
        pyperclip.copy(url)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.1)
        
        enforce_window_focus(hwnd)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        update_operation_status(f"Navigating to Google Flow URL...")

    # ============================================
    # SECTION 2: GOOGLE FLOW SPECIFIC HELPERS
    # ============================================
    
    def check_for_all_media_with_vision(hwnd, timeout_seconds=30, check_interval=0.5):
        """
        Google Flow specific: Write "all media" to text_target.json and then call vision.
        Wait for "all media" to appear in the screen content using case-insensitive
        and normalized text matching. Uses JSON format for text extraction.
        
        Returns: (found, text_elements)
        """
        print("🔍 [GOOGLE_FLOW] Checking for 'all media' in screen content (case-insensitive, normalized)...")
        update_operation_status("Checking for 'all media' content...")
        
        # Pre-normalize the target text for comparison
        normalized_target = normalize_text_for_comparison("all media")
        print(f"🔍 [GOOGLE_FLOW] Normalized target: '{normalized_target}'")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            attempts += 1
            
            print(f"📝 [GOOGLE_FLOW] Attempt {attempts}: Writing 'all media' to text target...")
            
            # Write "all media" to text_target.json
            try:
                text_target_data = {"value": "all media"}
                with open(TEXT_TARGET, 'w', encoding='utf-8') as file:
                    json.dump(text_target_data, file, indent=4)
                print(f"✅ [GOOGLE_FLOW] Wrote 'all media' to {TEXT_TARGET}")
            except Exception as e:
                print(f"⚠️ [GOOGLE_FLOW] Error writing to text_target.json: {e}")
            
            # Wait a moment for the system to process the text target
            time.sleep(0.3)
            
            # Call vision to capture screen content (now uses JSON format)
            current_texts = safe_vision()
            
            if current_texts:
                print(f"🔍 [GOOGLE_FLOW] Found {len(current_texts)} text elements on screen")
                
                # Check if "all media" is in the screen content using normalized comparison
                found_all_media = False
                for element in current_texts:
                    element_text = element['text'].strip()
                    
                    # Use the normalized text comparison function
                    if text_contains_normalized(element_text, "all media"):
                        print(f"✅ [GOOGLE_FLOW] Found 'all media' in screen content: '{element_text}'")
                        found_all_media = True
                        update_operation_status("'All media' found in Google Flow project")
                        return True, current_texts
                
                if found_all_media:
                    return True, current_texts
                else:
                    print(f"⏳ [GOOGLE_FLOW] 'all media' not found in screen content yet (attempt {attempts})")
                    
                    # Log a few examples of what was found to help with debugging
                    if attempts <= 3:
                        sample_texts = [e['text'].strip()[:50] for e in current_texts[:10]]
                        print(f"🔍 [GOOGLE_FLOW] Sample texts found: {sample_texts}")
            else:
                print(f"⏳ [GOOGLE_FLOW] No text found on screen (attempt {attempts})")
                
                # Check if the screen_content.text file exists and has content
                if os.path.exists(SCREEN_TEXT_CONTENT):
                    try:
                        with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check JSON format for "AllMedia"
                            json_match = re.search(r'"text_\d+":\s*"([^"]*AllMedia[^"]*)"', content, re.IGNORECASE)
                            if json_match:
                                print(f"✅ [GOOGLE_FLOW] Found 'AllMedia' in JSON format: {json_match.group(1)}")
                                # Manually add the text element
                                current_texts = [{'text': json_match.group(1), 'left': 0, 'top': 0, 'right': 0, 'bottom': 0, 'width': 0, 'height': 0}]
                                update_operation_status("'All media' found in Google Flow project (direct JSON match)")
                                return True, current_texts
                    except Exception as e:
                        print(f"⚠️ [GOOGLE_FLOW] Error checking screen_content.text: {e}")
            
            # If attempts exceeded 10, try reloading the page
            if attempts > 10 and attempts % 3 == 0:
                print(f"🔄 [GOOGLE_FLOW] Attempt {attempts}: 'all media' not found, reloading page...")
                hud.print("🔄 Reloading page...", "warning")
                update_operation_status(f"Reloading page (attempt {attempts})...")
                enforce_window_focus(hwnd)
                pyautogui.hotkey('ctrl', 'r')
                time.sleep(2)
                hwnd = ensure_window_ready_and_focused()
                continue
            
            time.sleep(check_interval)
        
        print(f"❌ [GOOGLE_FLOW] 'all media' not found within {timeout_seconds} seconds")
        hud.print("❌ 'All media' not found", "error")
        error_msg = f"'All media' not found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, None

    def load_google_flow_url(hwnd, google_flow_url):
        """
        Load the Google Flow URL directly.
        """
        print(f"🌐 [GOOGLE_FLOW] Loading Google Flow URL: {google_flow_url}")
        hud.print("📋 Loading Google Flow...", "navigating")
        update_operation_status(f"Loading Google Flow project...")
        
        # Navigate to the URL
        fast_paste_url(hwnd, google_flow_url)
        time.sleep(3)
        hwnd = ensure_window_ready_and_focused()
        
        return True, hwnd

    def verify_google_flow_page_loaded(hwnd, max_attempts=10):
        """
        Verify Google Flow page is loaded by writing "all media" to text_target.json
        and checking if it appears in vision results using normalized comparison.
        Uses JSON format for text extraction.
        """
        print(f"🔍 [GOOGLE_FLOW] Verifying page is loaded with 'all media' detection (case-insensitive, normalized)...")
        hud.print("⏳ Checking Google Flow...", "waiting")
        update_operation_status("Verifying Google Flow page load...")
        
        for attempt in range(max_attempts):
            check_for_termination()
            
            # Write "all media" to text target and check vision
            found_all_media, current_texts = check_for_all_media_with_vision(
                hwnd, timeout_seconds=5, check_interval=0.3
            )
            
            if found_all_media:
                print(f"✅ [GOOGLE_FLOW] Page loaded successfully - 'all media' found!")
                hud.print("✅ Google Flow loaded", "success")
                update_operation_status("Google Flow project loaded successfully")
                return True, hwnd
            
            # If not found, try reloading
            if attempt < max_attempts - 1:
                print(f"🔄 [GOOGLE_FLOW] Attempt {attempt + 1}/{max_attempts} - Reloading page...")
                hud.print(f"🔄 Reloading... ({attempt + 1}/{max_attempts})", "warning")
                enforce_window_focus(hwnd)
                pyautogui.hotkey('ctrl', 'r')
                time.sleep(3)
                hwnd = ensure_window_ready_and_focused()
        
        print(f"❌ [GOOGLE_FLOW] Page verification failed after {max_attempts} attempts")
        hud.print("❌ Google Flow load failed", "error")
        error_msg = f"Page verification failed after {max_attempts} attempts"
        update_operation_status(error_msg, is_error=True)
        return False, hwnd

    # ============================================
    # SECTION 3: DOWNLOAD AND EXTRACTION HELPERS (from operate_google_flow_browser)
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
                # PART 2: MONITOR SCREEN FOR DOWNLOADING TEXT (FAST vision using JSON)
                # ============================================
                # Ensure window has focus for accurate vision
                enforce_window_focus(hwnd)
                
                # Get current screen text with fast vision (now uses JSON format)
                current_texts = safe_vision()
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
    
    def find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth=0, expected_images=None):
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
            
            dot_1_path = os.path.join(GUI_IMAGES, "vertical_dot_1.png")
            dot_2_path = os.path.join(GUI_IMAGES, "vertical_dot_2.png")
            
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
                return find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth + 1, expected_images)
            
            x, y = found_location
            print(f"🎯 [DOT] Selecting at position ({x}, {y})")
            update_operation_status(f"Found menu for {project_title}, clicking...")
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth + 1, expected_images)
            
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
                
                current_texts = safe_vision()
                
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
                return find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth + 1, expected_images)
            
            click_x, click_y = download_click_position
            
            if not enforce_window_focus(hwnd):
                print("❌ [WATCHDOG] Window not focusable before download selection")
                hwnd = ensure_window_ready_and_focused()
                return find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth + 1, expected_images)
            
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
            return find_and_click_vertical_dot(hwnd, google_flow_url, project_title, depth + 1, expected_images)
    
    def dismiss_download_modal_if_present(hwnd):
        """
        Check if download modal is present by looking for downloads icon.
        Searches in the upper half of the screen.
        If found, click on it to dismiss the modal.
        """
        check_for_termination()
        print(f"🔍 [MODAL] Checking for download modal using icon recognition...")
        
        # Define paths to download icon images
        downloads_icon1_path = os.path.join(GUI_IMAGES, "downloads_icon1.png")
        downloads_icon2_path = os.path.join(GUI_IMAGES, "downloads_icon2.png")
        
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
    # SECTION 4: MAIN GOOGLE FLOW WORKFLOW WITH DOWNLOAD
    # ============================================
    
    def main_google_flow_workflow_with_restart(hwnd=None, google_flow_url=None, depth=0, expected_images=None):
        """
        Main Google Flow workflow execution with restart capability.
        Simple: Open Edge, launch URL, wait for "all media" to appear.
        Then initiate download, monitor, extract, and validate.
        Uses case-insensitive and normalized text matching with JSON format parsing.
        """
        try:
            # Load panel data once at the beginning
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return False
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Navigate to google_flow_config
            google_flow_config = panel_data.get('google_flow_config', {})
            operate_google_flow = google_flow_config.get('operate_google_flow', False)
            
            if not operate_google_flow:
                print("ℹ️ Google Flow operation is disabled in config")
                hud.print("ℹ️ Google Flow operation disabled", "info")
                update_operation_status("Google Flow operation is disabled in configuration")
                return False
            
            # Get Google Flow project link
            if google_flow_url is None:
                google_flow_url = google_flow_config.get('google_flow_project_link')
                if not google_flow_url or not google_flow_url.strip():
                    print("❌ Error: 'google_flow_project_link' not configured")
                    hud.print("❌ No Google Flow URL configured", "error")
                    error_msg = "No Google Flow URL configured in google_flow_config"
                    update_operation_status(error_msg, is_error=True)
                    return False
            
            # Get expected images count
            if expected_images is None:
                expected_images = google_flow_config.get('expected_projectlink_images')
                if expected_images is not None:
                    print(f"📊 [CONFIG] Expected images: {expected_images}")
                else:
                    print(f"ℹ️ [CONFIG] No expected image count specified")
            
            # Get project title (from root level)
            project_title = panel_data.get('project_title', 'google_flow_project')
            
            if hwnd is None:
                hwnd = ensure_window_ready_and_focused()
                print(f"🪟 [GOOGLE_FLOW] Browser ready (HWND: {hwnd})")
            
            print(f"🎬 [GOOGLE_FLOW] Starting Google Flow workflow (depth {depth})...")
            print(f"🌐 [GOOGLE_FLOW] URL: {google_flow_url}")
            print(f"📁 [GOOGLE_FLOW] Project: '{project_title}'")
            print(f"🔍 [GOOGLE_FLOW] Using case-insensitive, normalized text matching with JSON format")
            update_operation_status(f"Starting Google Flow workflow for {project_title}")
            
            # Step 1: Load the Google Flow URL
            print(f"🔍 [GOOGLE_FLOW] Step 1: Loading Google Flow URL...")
            success, hwnd = load_google_flow_url(hwnd, google_flow_url)
            if not success:
                print(f"❌ [GOOGLE_FLOW] Failed to load Google Flow URL")
                error_msg = f"Failed to load Google Flow URL"
                update_operation_status(error_msg, is_error=True)
                return False
            
            # Step 2: Verify page loaded using "all media" detection with normalized matching
            print(f"🔍 [GOOGLE_FLOW] Step 2: Verifying page loaded with 'all media' detection (case-insensitive, normalized)...")
            success, hwnd = verify_google_flow_page_loaded(hwnd, max_attempts=10)
            if not success:
                print(f"❌ [GOOGLE_FLOW] Page verification failed")
                error_msg = f"Page verification failed for Google Flow"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print("✅ [GOOGLE_FLOW] Page loaded and verified! Proceeding to download...")
            update_operation_status(f"Page verified, initiating download for {project_title}...")
            
            # Step 3: Find and click vertical dot to initiate download
            print(f"🔘 [GOOGLE_FLOW] Step 3: Initiating download...")
            download_success = find_and_click_vertical_dot(
                hwnd, 
                google_flow_url, 
                project_title,
                expected_images=expected_images
            )
            
            if download_success:
                print("🎉 [GOOGLE_FLOW] Download and extraction completed successfully!")
                hud.print("🎉 Google Flow workflow complete!", "success")
                update_operation_status(f"Google Flow operation for {project_title} completed successfully", is_success=True)
                return True
            else:
                print(f"❌ [GOOGLE_FLOW] Download failed for {project_title}")
                error_msg = f"Download failed for {project_title}"
                update_operation_status(error_msg, is_error=True)
                return False
            
        except KeyboardInterrupt as ki:
            update_operation_status("Google Flow operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
            return False
        except SystemExit as se:
            # This is expected from abort_operation
            print(f"🛑 System exit: {se}")
            return False
        except Exception as e:
            print(f"❌ [GOOGLE_FLOW] Error: {e}")
            error_msg = f"Error in Google Flow workflow: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
            return False
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass

    def main_google_flow_workflow():
        """Wrapper for main Google Flow workflow with restart capability."""
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            # Navigate to google_flow_config
            google_flow_config = panel_data.get('google_flow_config', {})
            operate_google_flow = google_flow_config.get('operate_google_flow', False)
            
            if not operate_google_flow:
                print("ℹ️ Google Flow operation is disabled in config")
                hud.print("ℹ️ Google Flow operation disabled", "info")
                update_operation_status("Google Flow operation is disabled in configuration")
                return
            
            # Get Google Flow project link
            google_flow_url = google_flow_config.get('google_flow_project_link')
            if not google_flow_url or not google_flow_url.strip():
                print("❌ Error: 'google_flow_project_link' not configured")
                hud.print("❌ No Google Flow URL configured", "error")
                error_msg = "No Google Flow URL configured in google_flow_config"
                update_operation_status(error_msg, is_error=True)
                return
            
            # Get expected images count
            expected_images = google_flow_config.get('expected_projectlink_images')
            if expected_images is not None:
                print(f"📊 [CONFIG] Expected images: {expected_images}")
            else:
                print(f"ℹ️ [CONFIG] No expected image count specified")
            
            # Initialize browser window
            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized for Google Flow operation")
            
            success = main_google_flow_workflow_with_restart(
                hwnd=hwnd,
                google_flow_url=google_flow_url,
                depth=0,
                expected_images=expected_images
            )
            
            if success:
                print("✅ [MAIN] Google Flow workflow completed successfully!")
                update_operation_status("Google Flow workflow completed successfully", is_success=True)
            else:
                print("❌ [MAIN] Google Flow workflow failed after multiple attempts")
                error_msg = "Google Flow workflow failed after multiple attempts"
                update_operation_status(error_msg, is_error=True)
                
        except KeyboardInterrupt as ki:
            update_operation_status("Google Flow operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            # This is expected from abort_operation
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            error_msg = f"Unexpected error in Google Flow operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    
    main_google_flow_workflow()

def operate_turboscribe():
    """
    Launches/uses Microsoft Edge for Turboscribe operations.
    Workflow:
    1. Navigate to Turboscribe project URL
    2. Confirm page loaded by detecting project title (case-insensitive, normalized)
    3. Click on project title to focus/select it
    4. Ctrl+A to select all text, Ctrl+C to copy
    5. Save copied text to project's audio folder as {project_title}.txt
    6. Clean up text: remove everything before "Speaker 1" and after "Ready to Go Unlimited?"
    7. Delete existing audio files in the project's audio folder
    8. Look for any download button (txt, pdf, srt, docx) - move mouse to it but DON'T click
    9. Scroll down to reveal "download audio" button
    10. Find and click "download audio" button
    11. Monitor audio download
    12. Move downloaded audio file to project's audio folder
    13. Dismiss download modal when it appears
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
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting Turboscribe operation: {reason}", is_abort=True)

    def check_operation_status():
        if not operation_status_flag or operation_aborted:
            print("🛑 [STATUS] Operation status is invalid - aborting")
            update_operation_status("Operation status invalid - aborting Turboscribe operation", is_abort=True)
            return False
        return True

    def on_terminate_shortcut():
        nonlocal terminate_automation
        hud.print("🛑 Manual Stop Triggered!", "warning")
        print("🛑 Manual Stop Triggered!")
        terminate_automation = True
        update_operation_status("Turboscribe operation manually terminated by user (Alt+/)", is_abort=True)

    keyboard.add_hotkey('alt+/', on_terminate_shortcut)

    def check_for_termination():
        if terminate_automation:
            update_operation_status("Turboscribe operation terminated by user", is_abort=True)
            raise KeyboardInterrupt("User forced exit via shortcut key.")
        if not check_operation_status():
            raise SystemExit("Operation status invalid")

    # ============================================
    # WINDOW MANAGEMENT HELPERS
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
                update_operation_status("Browser window ready for Turboscribe operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No Edge window found, launching new instance...")
        update_operation_status("Launching browser for Turboscribe operation...")
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
                    update_operation_status("Browser launched for Turboscribe operation")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        error_msg = "Failed to get or launch Edge window for Turboscribe operation"
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
        update_operation_status(f"Navigating to Turboscribe URL...")

    # ============================================
    # TEXT NORMALIZATION HELPERS
    # ============================================
    
    def normalize_text_for_comparison(text):
        if not text:
            return ""
        t = text.lower()
        t = re.sub(r'[^a-z0-9]', '', t)
        return t

    def text_contains_normalized(text_to_search, target_text):
        if not text_to_search or not target_text:
            return False
        normalized_search = normalize_text_for_comparison(text_to_search)
        normalized_target = normalize_text_for_comparison(target_text)
        return normalized_target in normalized_search

    # ============================================
    # VISION HELPER
    # ============================================
    
    def safe_vision():
        check_for_termination()
        vision()
        
        text_elements = []
        
        try:
            if os.path.exists(SCREEN_TEXT_CONTENT):
                with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                json_match = re.search(
                    r'FULL IMAGE vision RESULTS.*?JSON FORMAT:\s*=\s*\n(\[.*?\])\s*(?=\n\n|$|\s*vision EXTRACTION RESULTS)',
                    content,
                    re.DOTALL | re.IGNORECASE
                )
                
                if json_match:
                    try:
                        json_text = json_match.group(1)
                        json_text = re.sub(r'^[^{[]*', '', json_text)
                        json_text = re.sub(r'[^}\]]*$', '', json_text)
                        json_data = json.loads(json_text)
                        
                        for item in json_data:
                            text_value = None
                            for key, value in item.items():
                                if key.startswith('text_'):
                                    text_value = value
                                    break
                            
                            if text_value and 'coordinates' in item:
                                coords = item['coordinates']
                                text_elements.append({
                                    'text': text_value.strip(),
                                    'left': coords.get('left', 0),
                                    'top': coords.get('top', 0),
                                    'right': coords.get('right', 0),
                                    'bottom': coords.get('bottom', 0),
                                    'width': coords.get('right', 0) - coords.get('left', 0),
                                    'height': coords.get('bottom', 0) - coords.get('top', 0)
                                })
                        
                        if text_elements:
                            print(f"✅ [VISION] Parsed {len(text_elements)} text elements from JSON")
                    except json.JSONDecodeError:
                        pass
                
                if not text_elements:
                    text_blocks = re.findall(
                        r'TEXT BLOCK #\d+:\s*•\s*(.+?)\s+Left:\s*(\d+)\s+Top:\s*(\d+)\s+Right:\s*(\d+)\s+Bottom:\s*(\d+)\s+Width:\s*(\d+)\s+Height:\s*(\d+)',
                        content,
                        re.DOTALL
                    )
                    
                    for match in text_blocks:
                        text, left, top, right, bottom, width, height = match
                        text_elements.append({
                            'text': text.strip(),
                            'left': int(left),
                            'top': int(top),
                            'right': int(right),
                            'bottom': int(bottom),
                            'width': int(width),
                            'height': int(height)
                        })
                    
                    if text_elements:
                        print(f"✅ [VISION] Parsed {len(text_elements)} text elements from text format")
                
                if text_elements:
                    print(f"📊 [VISION] TOTAL: {len(text_elements)} text elements parsed")
        except Exception as e:
            print(f"⚠️ [VISION] Error reading screen_content.text: {e}")
        
        return text_elements

    # ============================================
    # MODAL DISMISSAL MECHANISM
    # ============================================
    
    def dismiss_download_modal_if_present(hwnd):
        """
        Check if download modal is present by looking for downloads icon.
        Searches in the upper half of the screen.
        If found, click on it to dismiss the modal.
        """
        check_for_termination()
        print(f"🔍 [MODAL] Checking for download modal using icon recognition...")
        
        # Define paths to download icon images
        downloads_icon1_path = os.path.join(GUI_IMAGES, "downloads_icon1.png")
        downloads_icon2_path = os.path.join(GUI_IMAGES, "downloads_icon2.png")
        
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
    # TURBOSCRIBE SPECIFIC HELPERS
    # ============================================
    
    def check_for_project_title_with_vision(hwnd, project_title, timeout_seconds=30, check_interval=0.5):
        """
        Check for project title on the page using case-insensitive normalized matching.
        Returns: (found, click_coordinates, text_elements)
        """
        print(f"🔍 [TURBOSCRIBE] Checking for project title '{project_title}' in screen content...")
        update_operation_status(f"Checking for project title '{project_title}'...")
        
        # Normalize project title for comparison
        normalized_target = normalize_text_for_comparison(project_title)
        print(f"🔍 [TURBOSCRIBE] Normalized target: '{normalized_target}'")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            attempts += 1
            
            print(f"📝 [TURBOSCRIBE] Attempt {attempts}: Writing '{project_title}' to text target...")
            
            try:
                text_target_data = {"value": project_title}
                with open(TEXT_TARGET, 'w', encoding='utf-8') as file:
                    json.dump(text_target_data, file, indent=4)
                print(f"✅ [TURBOSCRIBE] Wrote '{project_title}' to {TEXT_TARGET}")
            except Exception as e:
                print(f"⚠️ [TURBOSCRIBE] Error writing to text_target.json: {e}")
            
            time.sleep(0.3)
            
            current_texts = safe_vision()
            
            if current_texts:
                print(f"🔍 [TURBOSCRIBE] Found {len(current_texts)} text elements on screen")
                
                for element in current_texts:
                    element_text = element['text'].strip()
                    
                    if text_contains_normalized(element_text, project_title):
                        print(f"✅ [TURBOSCRIBE] Found project title in screen content: '{element_text}'")
                        
                        click_x = int(element['left'] + element['width'] / 2)
                        click_y = int(element['top'] + element['height'] / 2)
                        
                        print(f"🎯 [TURBOSCRIBE] Click position: ({click_x}, {click_y})")
                        update_operation_status(f"Found project title: {project_title}")
                        return True, (click_x, click_y), current_texts
            else:
                print(f"⏳ [TURBOSCRIBE] No text found on screen (attempt {attempts})")
            
            if attempts > 10 and attempts % 3 == 0:
                print(f"🔄 [TURBOSCRIBE] Attempt {attempts}: project title not found, reloading page...")
                hud.print("🔄 Reloading page...", "warning")
                update_operation_status(f"Reloading page (attempt {attempts})...")
                enforce_window_focus(hwnd)
                pyautogui.hotkey('ctrl', 'r')
                time.sleep(2)
                hwnd = ensure_window_ready_and_focused()
                continue
            
            time.sleep(check_interval)
        
        print(f"❌ [TURBOSCRIBE] Project title '{project_title}' not found within {timeout_seconds} seconds")
        hud.print(f"❌ Project title not found", "error")
        error_msg = f"Project title '{project_title}' not found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, None, None

    def click_on_project_title(hwnd, click_coords):
        """
        Click on the project title to focus/select it.
        """
        check_for_termination()
        print(f"🎯 [TURBOSCRIBE] Clicking on project title at ({click_coords[0]}, {click_coords[1]})")
        hud.print("🎯 Selecting project title...", "clicking")
        update_operation_status("Clicking on project title...")
        
        enforce_window_focus(hwnd)
        pyautogui.moveTo(click_coords[0], click_coords[1], duration=0.2)
        pyautogui.click()
        time.sleep(0.3)
        
        print(f"✅ [TURBOSCRIBE] Clicked on project title")
        return True

    def copy_all_text_from_page(hwnd):
        """
        Select all text on the page (Ctrl+A) and copy it (Ctrl+C).
        Returns: (success, copied_text)
        """
        check_for_termination()
        print(f"📋 [TURBOSCRIBE] Selecting all text and copying...")
        hud.print("📋 Copying transcript text...", "typing")
        update_operation_status("Copying transcript text...")
        
        try:
            # Ensure window has focus
            enforce_window_focus(hwnd)
            time.sleep(0.2)
            
            # Click on the page to ensure focus
            current_monitor = get_current_monitor()
            monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
            center_x = monitor_left + (monitor_right - monitor_left) // 2
            center_y = monitor_top + (monitor_bottom - monitor_top) // 2
            pyautogui.click(center_x, center_y)
            time.sleep(0.2)
            
            # Select all (Ctrl+A)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            
            # Copy (Ctrl+C)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.3)
            
            # Get clipboard content
            copied_text = pyperclip.paste()
            
            if copied_text and len(copied_text) > 100:  # Ensure we got substantial text
                print(f"✅ [TURBOSCRIBE] Copied {len(copied_text)} characters")
                update_operation_status(f"Copied {len(copied_text)} characters of transcript")
                return True, copied_text
            else:
                print(f"⚠️ [TURBOSCRIBE] Copied text is too short or empty: {len(copied_text) if copied_text else 0} chars")
                hud.print("⚠️ Could not copy transcript text", "warning")
                error_msg = "Copied text is too short or empty"
                update_operation_status(error_msg, is_error=True)
                return False, None
                
        except Exception as e:
            print(f"❌ [TURBOSCRIBE] Failed to copy text: {e}")
            error_msg = f"Failed to copy transcript text: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False, None

    def clean_transcript_text(raw_text):
        """
        Clean the transcript text by:
        1. Finding "Speaker 1" and removing everything before it
        2. Finding "Ready to Go Unlimited?" and removing everything after it
        """
        print(f"🧹 [TURBOSCRIBE] Cleaning transcript text...")
        
        if not raw_text:
            return ""
        
        cleaned_text = raw_text
        
        # Find "Speaker 1" and remove everything before it
        speaker_pattern = r'(Speaker\s*1\s*\n?.*?\(0:00\))'
        speaker_match = re.search(speaker_pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
        
        if speaker_match:
            start_index = speaker_match.start()
            print(f"   Found 'Speaker 1' at position {start_index}")
            cleaned_text = cleaned_text[start_index:]
            print(f"   Removed {start_index} characters before 'Speaker 1'")
        else:
            # Try alternative pattern without newline
            alt_pattern = r'(Speaker\s*1.*?\(0:00\))'
            alt_match = re.search(alt_pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
            if alt_match:
                start_index = alt_match.start()
                print(f"   Found 'Speaker 1' (alt pattern) at position {start_index}")
                cleaned_text = cleaned_text[start_index:]
                print(f"   Removed {start_index} characters before 'Speaker 1'")
            else:
                print(f"   ⚠️ Could not find 'Speaker 1' pattern in text")
        
        # Find "Ready to Go Unlimited?" and remove everything after it
        end_pattern = r'(Ready to Go Unlimited\??)'
        end_match = re.search(end_pattern, cleaned_text, re.IGNORECASE | re.DOTALL)
        
        if end_match:
            end_index = end_match.start()
            print(f"   Found 'Ready to Go Unlimited?' at position {end_index}")
            cleaned_text = cleaned_text[:end_index]
            print(f"   Removed {len(raw_text) - end_index} characters after 'Ready to Go Unlimited?'")
        else:
            print(f"   ⚠️ Could not find 'Ready to Go Unlimited?' pattern in text")
        
        # Clean up any extra whitespace at the end
        cleaned_text = cleaned_text.rstrip()
        
        print(f"✅ [TURBOSCRIBE] Cleaned text: {len(cleaned_text)} characters")
        return cleaned_text

    def save_transcript_to_audio_folder(cleaned_text, project_title):
        """
        Save the cleaned transcript text to the project's audio folder.
        """
        check_for_termination()
        print(f"💾 [TURBOSCRIBE] Saving transcript to audio folder for {project_title}...")
        hud.print("💾 Saving transcript...", "processing")
        update_operation_status(f"Saving transcript to audio folder for {project_title}...")
        
        def normalize_project_title(name):
            if not name:
                return "unnamed_project"
            normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
            normalized = re.sub(r'\s+', '_', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            normalized = normalized.strip('_')
            return normalized if normalized else "unnamed_project"
        
        normalized_project_title = normalize_project_title(project_title)
        print(f"📝 [TURBOSCRIBE] Normalized project name: '{normalized_project_title}'")
        
        project_folder = os.path.join(IMAGES_PATH, normalized_project_title)
        audio_folder = os.path.join(project_folder, "audio")
        
        if not os.path.exists(audio_folder):
            try:
                os.makedirs(audio_folder)
                print(f"📁 [TURBOSCRIBE] Created audio folder: {audio_folder}")
            except Exception as e:
                print(f"❌ [TURBOSCRIBE] Failed to create audio folder: {e}")
                error_msg = f"Failed to create audio folder: {e}"
                update_operation_status(error_msg, is_error=True)
                return False
        
        # Create filename with project title
        filename = f"{normalized_project_title}.txt"
        file_path = os.path.join(audio_folder, filename)
        
        # Handle duplicate filenames
        if os.path.exists(file_path):
            name_without_ext = os.path.splitext(filename)[0]
            counter = 1
            while os.path.exists(file_path):
                new_name = f"{name_without_ext}_{counter}.txt"
                file_path = os.path.join(audio_folder, new_name)
                counter += 1
            print(f"📝 [TURBOSCRIBE] Renaming to avoid conflict: {os.path.basename(file_path)}")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(cleaned_text)
            print(f"✅ [TURBOSCRIBE] Transcript saved to: {file_path}")
            hud.print("✅ Transcript saved!", "success")
            update_operation_status(f"Transcript saved to audio folder for {project_title}")
            return True
        except Exception as e:
            print(f"❌ [TURBOSCRIBE] Failed to save transcript: {e}")
            error_msg = f"Failed to save transcript: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False

    def check_for_download_button_with_vision(hwnd, target_text_list, timeout_seconds=15, check_interval=0.3):
        """
        Check for any download button from a list of target texts.
        Returns: (found, click_coordinates, text_elements, matched_text)
        """
        print(f"🔍 [TURBOSCRIBE] Looking for any of these download buttons: {target_text_list}")
        update_operation_status(f"Looking for download buttons...")
        
        # Normalize all target texts
        normalized_targets = {}
        for target in target_text_list:
            normalized_targets[target] = normalize_text_for_comparison(target)
        
        print(f"🔍 [TURBOSCRIBE] Normalized targets: {normalized_targets}")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            attempts += 1
            
            # Write all targets to text target
            try:
                text_target_data = {"value": ", ".join(target_text_list)}
                with open(TEXT_TARGET, 'w', encoding='utf-8') as file:
                    json.dump(text_target_data, file, indent=4)
                print(f"✅ [TURBOSCRIBE] Wrote '{', '.join(target_text_list)}' to {TEXT_TARGET}")
            except Exception as e:
                print(f"⚠️ [TURBOSCRIBE] Error writing to text_target.json: {e}")
            
            time.sleep(0.3)
            
            current_texts = safe_vision()
            
            if current_texts:
                print(f"🔍 [TURBOSCRIBE] Found {len(current_texts)} text elements on screen")
                
                for element in current_texts:
                    element_text = element['text'].strip()
                    normalized_element = normalize_text_for_comparison(element_text)
                    
                    # Check each target
                    for target, normalized_target in normalized_targets.items():
                        if normalized_target in normalized_element:
                            print(f"✅ [TURBOSCRIBE] Found '{target}' in screen content: '{element_text}'")
                            
                            click_x = int(element['left'] + element['width'] / 2)
                            click_y = int(element['top'] + element['height'] / 2)
                            
                            print(f"🎯 [TURBOSCRIBE] Click position: ({click_x}, {click_y})")
                            update_operation_status(f"Found {target} button")
                            return True, (click_x, click_y), current_texts, target
            
            print(f"⏳ [TURBOSCRIBE] No download buttons found (attempt {attempts})")
            time.sleep(check_interval)
        
        print(f"❌ [TURBOSCRIBE] No download buttons found within {timeout_seconds} seconds")
        hud.print(f"❌ No download buttons found", "error")
        error_msg = f"No download buttons found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, None, None, None

    def move_mouse_to_button(hwnd, click_coords):
        """
        Move the mouse to the button coordinates but DON'T click.
        """
        check_for_termination()
        print(f"🖱️ [TURBOSCRIBE] Moving mouse to button at ({click_coords[0]}, {click_coords[1]}) - NOT clicking")
        hud.print("🖱️ Moving to button...", "navigating")
        update_operation_status("Moving mouse to download button...")
        
        enforce_window_focus(hwnd)
        pyautogui.moveTo(click_coords[0], click_coords[1], duration=0.2)
        time.sleep(0.3)
        
        print(f"✅ [TURBOSCRIBE] Mouse moved to button position")
        return True

    def scroll_down_after_download(hwnd, download_click_coords):
        """
        Scroll down after a download is clicked to reveal content below.
        Moves mouse back to the download region, then scrolls.
        """
        check_for_termination()
        print(f"📜 [TURBOSCRIBE] Scrolling down after download...")
        hud.print("📜 Scrolling down...", "navigating")
        update_operation_status("Scrolling down to reveal more content...")
        
        try:
            # Focus the window
            enforce_window_focus(hwnd)
            
            # Move mouse back to the download region if coordinates are available
            if download_click_coords:
                click_x, click_y = download_click_coords
                print(f"🔄 [TURBOSCRIBE] Moving mouse back to download region: ({click_x}, {click_y})")
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                time.sleep(0.3)
            else:
                # If no coordinates, move to center of screen
                current_monitor = get_current_monitor()
                monitor_left, monitor_top, monitor_right, monitor_bottom = current_monitor
                center_x = monitor_left + (monitor_right - monitor_left) // 2
                center_y = monitor_top + (monitor_bottom - monitor_top) // 2
                print(f"🔄 [TURBOSCRIBE] Moving mouse to center of screen: ({center_x}, {center_y})")
                pyautogui.moveTo(center_x, center_y, duration=0.2)
                time.sleep(0.3)
            
            # Scroll down hard (large scroll amount)
            print(f"📜 [TURBOSCRIBE] Scrolling down hard...")
            pyautogui.scroll(-500)  # Large scroll down
            time.sleep(1)
            
            # Scroll again to ensure we've gone far enough
            pyautogui.scroll(-300)
            time.sleep(0.5)
            
            print(f"✅ [TURBOSCRIBE] Scroll down completed")
            hud.print("✅ Scroll down complete", "info")
            update_operation_status("Scrolled down successfully")
            return True
            
        except Exception as e:
            print(f"⚠️ [TURBOSCRIBE] Error during scroll: {e}")
            return False

    def check_for_specific_download_button_with_vision(hwnd, target_text, timeout_seconds=15, check_interval=0.3):
        """
        Find a specific download button with the given target text.
        Returns: (found, click_coordinates, text_elements)
        """
        print(f"🔍 [TURBOSCRIBE] Looking for '{target_text}' in screen content...")
        update_operation_status(f"Looking for {target_text} button...")
        
        normalized_target = normalize_text_for_comparison(target_text)
        print(f"🔍 [TURBOSCRIBE] Normalized target: '{normalized_target}'")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            attempts += 1
            
            print(f"📝 [TURBOSCRIBE] Attempt {attempts}: Writing '{target_text}' to text target...")
            
            try:
                text_target_data = {"value": target_text}
                with open(TEXT_TARGET, 'w', encoding='utf-8') as file:
                    json.dump(text_target_data, file, indent=4)
                print(f"✅ [TURBOSCRIBE] Wrote '{target_text}' to {TEXT_TARGET}")
            except Exception as e:
                print(f"⚠️ [TURBOSCRIBE] Error writing to text_target.json: {e}")
            
            time.sleep(0.3)
            
            current_texts = safe_vision()
            
            if current_texts:
                print(f"🔍 [TURBOSCRIBE] Found {len(current_texts)} text elements on screen")
                
                for element in current_texts:
                    element_text = element['text'].strip()
                    
                    # Try various forms of the target text
                    normalized_element = normalize_text_for_comparison(element_text)
                    if text_contains_normalized(element_text, target_text) or \
                       normalized_target in normalized_element:
                        print(f"✅ [TURBOSCRIBE] Found '{target_text}' in screen content: '{element_text}'")
                        
                        click_x = int(element['left'] + element['width'] / 2)
                        click_y = int(element['top'] + element['height'] / 2)
                        
                        print(f"🎯 [TURBOSCRIBE] Click position: ({click_x}, {click_y})")
                        update_operation_status(f"Found {target_text} button")
                        return True, (click_x, click_y), current_texts
            
            print(f"⏳ [TURBOSCRIBE] '{target_text}' not found (attempt {attempts})")
            time.sleep(check_interval)
        
        print(f"❌ [TURBOSCRIBE] '{target_text}' not found within {timeout_seconds} seconds")
        hud.print(f"❌ {target_text} button not found", "error")
        error_msg = f"'{target_text}' not found within {timeout_seconds} seconds"
        update_operation_status(error_msg, is_error=True)
        return False, None, None

    # ============================================
    # FILE MANAGEMENT HELPERS
    # ============================================
    
    def delete_existing_audio_files(project_title):
        """
        Delete all existing audio files in the project's audio folder.
        """
        check_for_termination()
        print(f"🗑️ [TURBOSCRIBE] Checking for existing audio files to delete...")
        hud.print("🗑️ Removing existing audio files...", "warning")
        update_operation_status(f"Removing existing audio files for {project_title}...")
        
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
        audio_folder = os.path.join(project_folder, "audio")
        
        # Check if audio folder exists
        if not os.path.exists(audio_folder):
            print(f"ℹ️ [TURBOSCRIBE] Audio folder doesn't exist yet: {audio_folder}")
            return True
        
        # Count files before deletion
        try:
            files = os.listdir(audio_folder)
            if not files:
                print(f"ℹ️ [TURBOSCRIBE] Audio folder is empty: {audio_folder}")
                return True
            
            print(f"📁 [TURBOSCRIBE] Found {len(files)} file(s) in audio folder")
            
            # Delete all files in the audio folder
            deleted_count = 0
            for filename in files:
                file_path = os.path.join(audio_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"   🗑️ Deleted: {filename}")
                except Exception as e:
                    print(f"   ⚠️ Could not delete {filename}: {e}")
            
            print(f"✅ [TURBOSCRIBE] Deleted {deleted_count} existing audio file(s)")
            
            # Check if folder is empty now
            remaining = os.listdir(audio_folder)
            if remaining:
                print(f"⚠️ [TURBOSCRIBE] {len(remaining)} file(s) remain in audio folder")
            else:
                print(f"✅ [TURBOSCRIBE] Audio folder is now empty")
            
            update_operation_status(f"Removed {deleted_count} existing audio files for {project_title}")
            return True
            
        except Exception as e:
            print(f"❌ [TURBOSCRIBE] Failed to delete audio files: {e}")
            error_msg = f"Failed to delete existing audio files: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False

    def move_file_to_audio_folder(file_path, filename, project_title, file_type="file"):
        """
        Move a downloaded file to the project's audio folder.
        """
        check_for_termination()
        print(f"📁 [TURBOSCRIBE] Moving {file_type} to audio folder for {project_title}...")
        hud.print(f"📁 Organizing {file_type}...", "processing")
        update_operation_status(f"Moving {file_type} to audio folder for {project_title}...")
        
        def normalize_project_title(name):
            if not name:
                return "unnamed_project"
            normalized = re.sub(r'[^a-zA-Z0-9\s_]', '', name)
            normalized = re.sub(r'\s+', '_', normalized)
            normalized = re.sub(r'_+', '_', normalized)
            normalized = normalized.strip('_')
            return normalized if normalized else "unnamed_project"
        
        normalized_project_title = normalize_project_title(project_title)
        print(f"📝 [TURBOSCRIBE] Normalized project name: '{normalized_project_title}'")
        
        project_folder = os.path.join(IMAGES_PATH, normalized_project_title)
        audio_folder = os.path.join(project_folder, "audio")
        
        if not os.path.exists(audio_folder):
            try:
                os.makedirs(audio_folder)
                print(f"📁 [TURBOSCRIBE] Created audio folder: {audio_folder}")
            except Exception as e:
                print(f"❌ [TURBOSCRIBE] Failed to create audio folder: {e}")
                error_msg = f"Failed to create audio folder: {e}"
                update_operation_status(error_msg, is_error=True)
                return False
        
        if not os.path.exists(file_path):
            print(f"❌ [TURBOSCRIBE] File not found: {file_path}")
            error_msg = f"File not found: {filename}"
            update_operation_status(error_msg, is_error=True)
            return False
        
        dest_path = os.path.join(audio_folder, filename)
        
        # Handle duplicate filenames
        if os.path.exists(dest_path):
            name_without_ext = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            counter = 1
            while os.path.exists(dest_path):
                new_name = f"{name_without_ext}_{counter}{ext}"
                dest_path = os.path.join(audio_folder, new_name)
                counter += 1
            print(f"📝 [TURBOSCRIBE] Renaming to avoid conflict: {os.path.basename(dest_path)}")
        
        try:
            import shutil
            shutil.move(file_path, dest_path)
            print(f"✅ [TURBOSCRIBE] {file_type.capitalize()} moved to: {dest_path}")
            hud.print(f"✅ {file_type.capitalize()} organized!", "success")
            update_operation_status(f"{file_type.capitalize()} saved to audio folder for {project_title}")
            return True
        except Exception as e:
            print(f"❌ [TURBOSCRIBE] Failed to move {file_type}: {e}")
            error_msg = f"Failed to move {file_type}: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            return False

    # ============================================
    # DOWNLOAD MONITORING (Generic)
    # ============================================
    
    def check_download_status_generic(hwnd, project_title, file_extension, timeout_seconds=180, check_interval=0.1):
        """
        Generic download monitor for any file type.
        Returns: (success, file_path, filename)
        """
        check_for_termination()
        print(f"📊 [TURBOSCRIBE_DOWNLOAD] Starting download status monitor for {file_extension} file...")
        hud.print(f"📊 Monitoring {file_extension} download...", "waiting")
        update_operation_status(f"Monitoring {file_extension} download for {project_title}...")
        
        start_time = time.time()
        downloads_folder = os.path.expanduser("~/Downloads")
        
        # Track existing files
        existing_files = {}
        if os.path.exists(downloads_folder):
            try:
                with os.scandir(downloads_folder) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.endswith(file_extension):
                            try:
                                stat = entry.stat()
                                if os.name == 'nt':
                                    file_time = stat.st_ctime
                                else:
                                    file_time = stat.st_mtime
                                existing_files[entry.name] = {
                                    'path': entry.path,
                                    'time': file_time,
                                    'size': stat.st_size
                                }
                            except Exception:
                                existing_files[entry.name] = {
                                    'path': entry.path,
                                    'time': 0,
                                    'size': 0
                                }
                print(f"📁 [TURBOSCRIBE_DOWNLOAD] Found {len(existing_files)} existing {file_extension} files")
            except Exception as e:
                print(f"⚠️ [TURBOSCRIBE_DOWNLOAD] Error scanning existing files: {e}")
        
        # Track latest known file
        latest_known_file = None
        latest_known_time = 0
        
        if existing_files:
            for name, info in existing_files.items():
                if info['time'] > latest_known_time:
                    latest_known_time = info['time']
                    latest_known_file = name
            print(f"📁 [TURBOSCRIBE_DOWNLOAD] Latest existing {file_extension}: {latest_known_file}")
        
        # Monitoring loop
        last_modal_check = 0
        modal_check_interval = 10
        
        while time.time() - start_time < timeout_seconds:
            try:
                check_for_termination()
                
                # Periodic modal check
                elapsed = int(time.time() - start_time)
                if elapsed - last_modal_check >= modal_check_interval:
                    try:
                        print(f"🔍 [TURBOSCRIBE_DOWNLOAD] Checking for download modal...")
                        hwnd = dismiss_download_modal_if_present(hwnd)
                        last_modal_check = elapsed
                    except Exception as e:
                        print(f"⚠️ [TURBOSCRIBE_DOWNLOAD] Error checking modal: {e}")
                
                # Check for new files
                if os.path.exists(downloads_folder):
                    with os.scandir(downloads_folder) as entries:
                        for entry in entries:
                            if entry.is_file() and entry.name.endswith(file_extension):
                                if entry.name not in existing_files:
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
                                    
                                    # Check if different from latest known
                                    is_different = True
                                    if latest_known_file and latest_known_file == entry.name:
                                        try:
                                            latest_path = os.path.join(downloads_folder, latest_known_file)
                                            if os.path.exists(latest_path):
                                                latest_stat = os.stat(latest_path)
                                                if os.name == 'nt':
                                                    latest_time = latest_stat.st_ctime
                                                else:
                                                    latest_time = latest_stat.st_mtime
                                                if abs(file_time - latest_time) < 1.0:
                                                    is_different = False
                                        except Exception:
                                            pass
                                    
                                    if is_different:
                                        print(f"🆕 [TURBOSCRIBE_DOWNLOAD] New {file_extension} file detected: {entry.name}")
                                        hud.print(f"🆕 {file_extension.upper()} download detected!", "info")
                                        update_operation_status(f"{file_extension.upper()} download detected: {entry.name}")
                                        
                                        # Wait for file to stabilize
                                        stable_count = 0
                                        stable_size = 0
                                        max_stable_checks = 5
                                        
                                        print(f"⏳ [TURBOSCRIBE_DOWNLOAD] Waiting for file to stabilize...")
                                        while stable_count < 3 and stable_count < max_stable_checks:
                                            try:
                                                current_size = os.path.getsize(entry.path)
                                                if current_size == stable_size and current_size > 0:
                                                    stable_count += 1
                                                    print(f"✅ [TURBOSCRIBE_DOWNLOAD] File stable ({stable_count}/3), size: {current_size} bytes")
                                                else:
                                                    stable_count = 0
                                                    stable_size = current_size
                                                    print(f"⏳ [TURBOSCRIBE_DOWNLOAD] File size changing: {current_size} bytes")
                                            except Exception:
                                                pass
                                            time.sleep(0.5)
                                        
                                        # One final modal check before completing
                                        try:
                                            hwnd = dismiss_download_modal_if_present(hwnd)
                                        except Exception:
                                            pass
                                        
                                        print(f"✅ [TURBOSCRIBE_DOWNLOAD] Download complete! File ready: {entry.name}")
                                        hud.print(f"✅ {file_extension.upper()} download complete!", "success")
                                        update_operation_status(f"{file_extension.upper()} download complete: {entry.name}")
                                        
                                        return True, entry.path, entry.name
                                    
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print(f"🛑 [TURBOSCRIBE_DOWNLOAD] Download monitoring interrupted")
                raise
            except Exception as e:
                print(f"⚠️ [TURBOSCRIBE_DOWNLOAD] Error in monitoring loop: {e}")
                time.sleep(check_interval)
                continue
        
        print(f"⏰ [TURBOSCRIBE_DOWNLOAD] Timeout reached after {timeout_seconds} seconds")
        error_msg = f"{file_extension.upper()} download timed out after {timeout_seconds} seconds"
        hud.print(f"⏰ Download monitoring timed out", "error")
        update_operation_status(error_msg, is_error=True)
        return False, None, None

    # ============================================
    # MAIN TURBOSCRIBE WORKFLOW
    # ============================================
    
    def main_turboscribe_workflow_with_restart(hwnd=None, turboscribe_url=None, depth=0):
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return False
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            turboscribe_config = panel_data.get('turboscribe_config', {})
            operate_turboscribe = turboscribe_config.get('operate_turboscribe', False)
            
            if not operate_turboscribe:
                print("ℹ️ Turboscribe operation is disabled in config")
                hud.print("ℹ️ Turboscribe operation disabled", "info")
                update_operation_status("Turboscribe operation is disabled in configuration")
                return False
            
            if turboscribe_url is None:
                turboscribe_url = turboscribe_config.get('turboscribe_project_url')
                if not turboscribe_url or not turboscribe_url.strip():
                    print("❌ Error: 'turboscribe_project_url' not configured")
                    hud.print("❌ No Turboscribe URL configured", "error")
                    error_msg = "No Turboscribe URL configured in turboscribe_config"
                    update_operation_status(error_msg, is_error=True)
                    return False
            
            project_title = panel_data.get('project_title', 'turboscribe_project')
            
            if hwnd is None:
                hwnd = ensure_window_ready_and_focused()
                print(f"🪟 [TURBOSCRIBE] Browser ready (HWND: {hwnd})")
            
            print(f"🎬 [TURBOSCRIBE] Starting Turboscribe workflow (depth {depth})...")
            print(f"🌐 [TURBOSCRIBE] URL: {turboscribe_url}")
            print(f"📁 [TURBOSCRIBE] Project: '{project_title}'")
            update_operation_status(f"Starting Turboscribe workflow for {project_title}")
            
            # Step 1: Load the Turboscribe URL
            print(f"🔍 [TURBOSCRIBE] Step 1: Loading Turboscribe URL...")
            hud.print("📋 Loading Turboscribe...", "navigating")
            fast_paste_url(hwnd, turboscribe_url)
            time.sleep(3)
            hwnd = ensure_window_ready_and_focused()
            
            # Step 2: Confirm page loaded by detecting project title
            print(f"🔍 [TURBOSCRIBE] Step 2: Confirming page loaded by finding project title: '{project_title}'...")
            success, click_coords, text_elements = check_for_project_title_with_vision(
                hwnd, project_title, timeout_seconds=30
            )
            
            if not success or not click_coords:
                print(f"❌ [TURBOSCRIBE] Page verification failed - project title not found")
                error_msg = f"Page verification failed - project title '{project_title}' not found"
                update_operation_status(error_msg, is_error=True)
                
                if depth == 0:
                    print("🔄 [TURBOSCRIBE] Retrying page load...")
                    time.sleep(2)
                    return main_turboscribe_workflow_with_restart(hwnd, turboscribe_url, depth + 1)
                return False
            
            print(f"✅ [TURBOSCRIBE] Page loaded and verified! Found project title.")
            update_operation_status(f"Page verified for {project_title}")
            
            # Step 3: Click on the project title to focus it
            print(f"🎯 [TURBOSCRIBE] Step 3: Clicking on project title...")
            click_success = click_on_project_title(hwnd, click_coords)
            if not click_success:
                print(f"⚠️ [TURBOSCRIBE] Could not click on project title, but continuing...")
                hud.print("⚠️ Could not click on project title", "warning")
            
            # Step 4: Copy all text from the page (Ctrl+A, Ctrl+C)
            print(f"📋 [TURBOSCRIBE] Step 4: Copying all text from page...")
            copy_success, raw_text = copy_all_text_from_page(hwnd)
            
            if not copy_success or not raw_text:
                print(f"❌ [TURBOSCRIBE] Failed to copy text from page")
                error_msg = "Failed to copy transcript text"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print(f"✅ [TURBOSCRIBE] Copied {len(raw_text)} characters of raw text")
            
            # Step 5: Clean the transcript text
            print(f"🧹 [TURBOSCRIBE] Step 5: Cleaning transcript text...")
            cleaned_text = clean_transcript_text(raw_text)
            
            if not cleaned_text:
                print(f"⚠️ [TURBOSCRIBE] Cleaned text is empty!")
                hud.print("⚠️ Cleaned text is empty", "warning")
                # Use raw text as fallback
                cleaned_text = raw_text
            
            print(f"✅ [TURBOSCRIBE] Cleaned text: {len(cleaned_text)} characters")
            
            # Step 6: Delete existing audio files before saving new ones
            print(f"🗑️ [TURBOSCRIBE] Step 6: Deleting existing audio files...")
            delete_success = delete_existing_audio_files(project_title)
            if not delete_success:
                print(f"⚠️ [TURBOSCRIBE] Could not delete existing audio files, but continuing...")
                hud.print("⚠️ Could not delete existing audio files", "warning")
            
            # Step 7: Save the cleaned transcript to audio folder
            print(f"💾 [TURBOSCRIBE] Step 7: Saving transcript to audio folder...")
            save_success = save_transcript_to_audio_folder(cleaned_text, project_title)
            
            if not save_success:
                print(f"⚠️ [TURBOSCRIBE] Could not save transcript, but continuing...")
                hud.print("⚠️ Could not save transcript", "warning")
            
            # ============================================
            # STEP 8: LOOK FOR DOWNLOAD BUTTONS AND MOVE MOUSE (NO CLICK)
            # ============================================
            print(f"🔍 [TURBOSCRIBE] Step 8: Looking for download buttons (txt, pdf, srt, docx)...")
            download_buttons = ["download txt", "download pdf", "download srt", "download docx", "download docs"]
            
            success, button_coords, text_elements, matched_text = check_for_download_button_with_vision(
                hwnd, download_buttons, timeout_seconds=15
            )
            
            if success and button_coords:
                print(f"✅ [TURBOSCRIBE] Found '{matched_text}' - moving mouse to it (NOT clicking)")
                
                # Move mouse to the button but DON'T click
                move_success = move_mouse_to_button(hwnd, button_coords)
                if not move_success:
                    print(f"⚠️ [TURBOSCRIBE] Could not move mouse to button, but continuing...")
                    hud.print("⚠️ Could not move to button", "warning")
            else:
                print(f"⚠️ [TURBOSCRIBE] No download buttons found, but continuing...")
                hud.print("⚠️ No download buttons found", "warning")
            
            # ============================================
            # STEP 9: SCROLL DOWN TO REVEAL "DOWNLOAD AUDIO"
            # ============================================
            print(f"📜 [TURBOSCRIBE] Step 9: Scrolling down to reveal 'download audio' button...")
            scroll_success = scroll_down_after_download(hwnd, button_coords if button_coords else None)
            
            if not scroll_success:
                print(f"⚠️ [TURBOSCRIBE] Could not scroll down, but continuing...")
                hud.print("⚠️ Could not scroll down", "warning")
            
            # Wait a moment after scrolling
            time.sleep(2)
            
            # ============================================
            # STEP 10: FIND AND CLICK "DOWNLOAD AUDIO"
            # ============================================
            print(f"🔍 [TURBOSCRIBE] Step 10: Finding 'download audio' button...")
            success, audio_click_coords, text_elements = check_for_specific_download_button_with_vision(
                hwnd, "download audio", timeout_seconds=15
            )
            
            if not success or not audio_click_coords:
                print(f"❌ [TURBOSCRIBE] Could not find 'download audio' button")
                error_msg = "Could not find 'download audio' button"
                update_operation_status(error_msg, is_error=True)
                return False
            
            # Click the download audio button
            audio_click_x, audio_click_y = audio_click_coords
            print(f"🎯 [TURBOSCRIBE] Clicking 'download audio' at ({audio_click_x}, {audio_click_y})")
            hud.print("📥 Clicking download audio button...", "clicking")
            update_operation_status(f"Clicking download audio button for {project_title}...")
            
            enforce_window_focus(hwnd)
            pyautogui.moveTo(audio_click_x, audio_click_y, duration=0.2)
            pyautogui.click()
            time.sleep(0.5)
            
            # Step 11: Monitor audio download
            print(f"📊 [TURBOSCRIBE] Step 11: Monitoring audio download...")
            audio_download_successful, audio_file_path, audio_filename = check_download_status_generic(
                hwnd, project_title, ".mp3", timeout_seconds=180, check_interval=0.1
            )
            
            # Also check for other audio formats if mp3 not found
            if not audio_download_successful:
                print(f"ℹ️ [TURBOSCRIBE] No MP3 found, checking for other audio formats...")
                for ext in [".wav", ".m4a", ".aac", ".flac", ".ogg"]:
                    audio_download_successful, audio_file_path, audio_filename = check_download_status_generic(
                        hwnd, project_title, ext, timeout_seconds=30, check_interval=0.1
                    )
                    if audio_download_successful:
                        print(f"✅ [TURBOSCRIBE] Found audio file with extension: {ext}")
                        break
            
            if not audio_download_successful or not audio_file_path or not audio_filename:
                print(f"❌ [TURBOSCRIBE] Audio download failed")
                error_msg = "Audio download failed"
                update_operation_status(error_msg, is_error=True)
                return False
            
            print(f"✅ [TURBOSCRIBE] Audio download complete: {audio_filename}")
            update_operation_status(f"Audio download complete: {audio_filename}")
            
            # Step 12: Move audio file to audio folder
            print(f"📁 [TURBOSCRIBE] Step 12: Moving audio file to audio folder...")
            audio_move_successful = move_file_to_audio_folder(
                audio_file_path, audio_filename, project_title, "audio file"
            )
            
            if not audio_move_successful:
                print(f"⚠️ [TURBOSCRIBE] Could not move audio file")
                hud.print("⚠️ Could not move audio file", "warning")
            
            print("🎉 [TURBOSCRIBE] Operation fully completed!")
            hud.print("✅ Turboscribe complete!", "success")
            update_operation_status(f"Turboscribe operation for {project_title} completed successfully", is_success=True)
            return True
            
        except KeyboardInterrupt as ki:
            update_operation_status("Turboscribe operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
            return False
        except SystemExit as se:
            print(f"🛑 System exit: {se}")
            return False
        except Exception as e:
            print(f"❌ [TURBOSCRIBE] Error: {e}")
            error_msg = f"Error in Turboscribe workflow: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
            return False
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass

    def main_turboscribe_workflow():
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            turboscribe_config = panel_data.get('turboscribe_config', {})
            operate_turboscribe = turboscribe_config.get('operate_turboscribe', False)
            
            if not operate_turboscribe:
                print("ℹ️ Turboscribe operation is disabled in config")
                hud.print("ℹ️ Turboscribe operation disabled", "info")
                update_operation_status("Turboscribe operation is disabled in configuration")
                return
            
            turboscribe_url = turboscribe_config.get('turboscribe_project_url')
            if not turboscribe_url or not turboscribe_url.strip():
                print("❌ Error: 'turboscribe_project_url' not configured")
                hud.print("❌ No Turboscribe URL configured", "error")
                error_msg = "No Turboscribe URL configured in turboscribe_config"
                update_operation_status(error_msg, is_error=True)
                return
            
            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] Browser ready (HWND: {hwnd})")
            update_operation_status("Browser initialized for Turboscribe operation")
            
            success = main_turboscribe_workflow_with_restart(
                hwnd=hwnd,
                turboscribe_url=turboscribe_url,
                depth=0
            )
            
            if success:
                print("✅ [MAIN] Turboscribe workflow completed successfully!")
                update_operation_status("Turboscribe workflow completed successfully", is_success=True)
            else:
                print("❌ [MAIN] Turboscribe workflow failed")
                error_msg = "Turboscribe workflow failed"
                update_operation_status(error_msg, is_error=True)
                
        except KeyboardInterrupt as ki:
            update_operation_status("Turboscribe operation manually terminated by user", is_abort=True)
            hud.show_summary("🛑 Program Halted")
            print(f"\n✅ Program successfully halted: {ki}")
        except SystemExit as se:
            print(f"🛑 System exit: {se}")
        except Exception as e:
            print(f"❌ [MAIN] Error: {e}")
            error_msg = f"Unexpected error in Turboscribe operation: {str(e)}"
            update_operation_status(error_msg, is_error=True)
            hud.print("❌ Error occurred", "error")
        finally:
            try:
                keyboard.remove_hotkey('alt+/')
                print("🧹 Cleaned up hotkey")
            except Exception:
                pass
    
    main_turboscribe_workflow()

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

    def safe_vision():
        """Capture screen without hiding the HUD (HUD is click-through)"""
        check_for_termination()
        return vision()

    def clean_string_completely(text):
        """
        Clean a string for comparison by:
        1. Converting to lowercase
        2. Removing all non-alphanumeric characters
        3. Removing common URL prefixes
        4. Normalizing spaces and special characters
        
        This ensures that "iamkennyking's project_1" and "iamkennyking'sproject_1" 
        both become "iamkennykingsproject1"
        """
        if not text:
            return ""
        
        # Convert to lowercase
        t = text.lower()
        
        # Remove common URL prefixes
        t = t.replace("https://", "").replace("http://", "").replace("www.", "")
        
        # Remove all non-alphanumeric characters (this handles apostrophes, spaces, underscores, etc.)
        # This is the key change - it removes ALL non-alphanumeric characters
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
        
        current_texts = safe_vision()
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
            
            current_texts = safe_vision()
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
            
            current_texts = safe_vision()
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
            
            page_loaded, indicator = check_for_page_load_indicators(safe_vision())
            
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
        
        current_texts = safe_vision()
        
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
            
            current_texts = safe_vision()
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
        Extract video ID from vision text elements.
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
        Get the current video ID from the browser using vision.
        Returns the video ID string or None.
        """
        print(f"🔍 [CURRENT_ID] Getting current video ID...")
        hud.print("🔍 Checking video...", "searching")
        update_operation_status("Getting current video ID...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            check_for_termination()
            enforce_window_focus(hwnd)
            
            current_texts = safe_vision()
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
            
            current_texts = safe_vision()
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
        
        current_texts = safe_vision()
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
        download_btn1_path = os.path.join(GUI_IMAGES, "download_btn1.png")
        download_btn2_path = os.path.join(GUI_IMAGES, "download_btn2.png")
        
        # Check if image files exist
        if not os.path.exists(download_btn1_path) and not os.path.exists(download_btn2_path):
            print("❌ [DOWNLOAD_BTN] No download button images found in GUI_IMAGES")
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
            current_texts = safe_vision()
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
                current_texts = safe_vision()
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
        downloads_icon1_path = os.path.join(GUI_IMAGES, "downloads_icon1.png")
        downloads_icon2_path = os.path.join(GUI_IMAGES, "downloads_icon2.png")
        
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
                current_texts = safe_vision()
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
            
            current_texts = safe_vision()
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
    Launches/uses CapCut for project operations.
    Workflow:
    1. Write "create project, media, audio, import" to text_target.json
    2. Call vision() to capture screen
    3. If "create project" is found - click it (HIGHEST PRIORITY - always click if found)
    4. If "create project" not found but "media", "audio", or "import" found - we're already in edit interface
    5. If neither found - keep trying or report that CapCut isn't ready
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
        print(f"🛑 [ABORT] Aborting operation: {reason}")
        update_operation_status(f"Aborting CapCut operation: {reason}", is_abort=True)

    def check_operation_status():
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

    # ============================================
    # WINDOW MANAGEMENT HELPERS
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
        monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_bounds
        capcut_windows = []
        capcut_process_names = ["capcut.exe", "CapCut.exe"]
        
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    if process.name().lower() in [name.lower() for name in capcut_process_names]:
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

    def ensure_capcut_window_ready():
        check_for_termination()
        
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
                update_operation_status("CapCut window ready for operation")
                return hwnd
            except Exception as e:
                print(f"⚠️ [WINDOW] Error preparing existing window: {e}")
                pass
        
        print("💻 [WINDOW] No CapCut window found, launching new instance...")
        update_operation_status("Launching CapCut for operation...")
        
        capcut_paths = [
            r"C:\Program Files\CapCut\CapCut.exe",
            r"C:\Program Files (x86)\CapCut\CapCut.exe",
            r"C:\Users\{}\AppData\Local\CapCut\CapCut.exe".format(os.getlogin()),
        ]
        
        capcut_exe = None
        for path in capcut_paths:
            if os.path.exists(path):
                capcut_exe = path
                break
        
        if capcut_exe:
            subprocess.Popen([capcut_exe])
        else:
            subprocess.Popen(["start", "CapCut"], shell=True)
        
        for attempt in range(30):
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
                    update_operation_status("CapCut launched successfully")
                    return hwnd
                except Exception as e:
                    print(f"⚠️ [WINDOW] Error preparing new window: {e}")
                    continue
        
        error_msg = "Failed to get or launch CapCut window for operation"
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
        check_for_termination()
        hwnd = ensure_capcut_window_ready()
        enforce_window_focus(hwnd)
        return hwnd

    # ============================================
    # CHECK INTERFACE STATE
    # ============================================
    
    def check_interface_state():
        """
        Checks the screen_content.text file to determine the current CapCut interface state.
        Returns:
            dict: {
                'has_create_project': bool,
                'has_edit_interface': bool,
                'create_project_coords': dict or None,
                'found_values': list
            }
        """
        print("🔍 [CAPCUT_STATE] Analyzing CapCut interface state...")
        
        result = {
            'has_create_project': False,
            'has_edit_interface': False,
            'create_project_coords': None,
            'found_values': []
        }
        
        try:
            if not os.path.exists(SCREEN_TEXT_CONTENT):
                print(f"❌ [CAPCUT_STATE] screen_content.text not found at: {SCREEN_TEXT_CONTENT}")
                return result
            
            with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # ============================================
            # Check for "Create project" with coordinates
            # ============================================
            create_project_pattern = r'"text_\d+":\s*"([^"]*Create[Pp]roject[^"]*)"\s*,\s*"coordinates":\s*\{\s*"top":\s*(\d+)\s*,\s*"right":\s*(\d+)\s*,\s*"left":\s*(\d+)\s*,\s*"bottom":\s*(\d+)\s*\}'
            
            create_match = re.search(create_project_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if create_match:
                text_value = create_match.group(1)
                top = int(create_match.group(2))
                right = int(create_match.group(3))
                left = int(create_match.group(4))
                bottom = int(create_match.group(5))
                
                result['has_create_project'] = True
                result['create_project_coords'] = {
                    'left': left,
                    'top': top,
                    'right': right,
                    'bottom': bottom,
                    'text': text_value
                }
                result['found_values'].append('create_project')
                print(f"✅ [CAPCUT_STATE] Found 'Create project' at ({left}, {top}) -> ({right}, {bottom})")
            
            # ============================================
            # Check for edit interface values (media, audio, import)
            # ============================================
            # Search in JSON format
            json_pattern = r'"text_\d+":\s*"([^"]+)"'
            json_matches = re.findall(json_pattern, content, re.IGNORECASE)
            
            edit_keywords = ["media", "audio", "import"]
            
            for text in json_matches:
                text_lower = text.lower()
                for keyword in edit_keywords:
                    if keyword in text_lower and keyword not in result['found_values']:
                        result['found_values'].append(keyword)
                        print(f"✅ [CAPCUT_STATE] Found '{keyword}' in text: '{text[:50]}...'")
            
            # Search in compact format
            compact_pattern = r',\s*[\'"]([^\'"]+)[\'"]'
            compact_matches = re.findall(compact_pattern, content, re.IGNORECASE)
            
            for text in compact_matches:
                text_lower = text.lower()
                for keyword in edit_keywords:
                    if keyword in text_lower and keyword not in result['found_values']:
                        result['found_values'].append(keyword)
                        print(f"✅ [CAPCUT_STATE] Found '{keyword}' in compact format: '{text[:50]}...'")
            
            # Search in text format
            text_pattern = r'•\s*([^\n]+)'
            text_matches = re.findall(text_pattern, content)
            
            for text in text_matches:
                text_lower = text.lower()
                for keyword in edit_keywords:
                    if keyword in text_lower and keyword not in result['found_values']:
                        result['found_values'].append(keyword)
                        print(f"✅ [CAPCUT_STATE] Found '{keyword}' in text format: '{text[:50]}...'")
            
            # Determine if we have edit interface
            edit_interface_values = ["media", "audio", "import"]
            has_edit_values = any(val in result['found_values'] for val in edit_interface_values)
            
            if has_edit_values:
                result['has_edit_interface'] = True
                print(f"✅ [CAPCUT_STATE] Edit interface detected! Found: {', '.join([v for v in result['found_values'] if v in edit_interface_values])}")
            
            return result
            
        except Exception as e:
            print(f"❌ [CAPCUT_STATE] Error: {e}")
            import traceback
            traceback.print_exc()
            return result

    # ============================================
    # CLICK CREATE PROJECT - DIRECT FILE READ
    # ============================================
    
    def click_create_project():
        """
        Directly reads the screen_content.text file, finds "Createproject" in the JSON format,
        extracts the coordinates, and clicks on the center of the region.
        Does NOT call safe_vision() - just reads the file and clicks.
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("🔍 [CAPCUT_CLICK] Looking for 'Createproject' in screen_content.text...")
        
        try:
            if not os.path.exists(SCREEN_TEXT_CONTENT):
                print(f"❌ [CAPCUT_CLICK] screen_content.text not found at: {SCREEN_TEXT_CONTENT}")
                return False
            
            with open(SCREEN_TEXT_CONTENT, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # ============================================
            # METHOD 1: Find "Createproject" in JSON format
            # ============================================
            json_pattern = r'"text_\d+":\s*"([^"]*Create[Pp]roject[^"]*)"\s*,\s*"coordinates":\s*\{\s*"top":\s*(\d+)\s*,\s*"right":\s*(\d+)\s*,\s*"left":\s*(\d+)\s*,\s*"bottom":\s*(\d+)\s*\}'
            
            match = re.search(json_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                text_value = match.group(1)
                top = int(match.group(2))
                right = int(match.group(3))
                left = int(match.group(4))
                bottom = int(match.group(5))
                
                print(f"✅ [CAPCUT_CLICK] Found 'Createproject' in JSON:")
                print(f"   Text: '{text_value}'")
                print(f"   Coordinates: Left={left}, Top={top}, Right={right}, Bottom={bottom}")
                
                click_x = left + ((right - left) // 2)
                click_y = top + ((bottom - top) // 2)
                
                print(f"🎯 [CAPCUT_CLICK] Click position: ({click_x}, {click_y})")
                
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                pyautogui.click()
                
                print(f"✅ [CAPCUT_CLICK] Clicked 'Createproject' at ({click_x}, {click_y})")
                return True
            
            # ============================================
            # METHOD 2: Look for "Createproject" in compact format
            # ============================================
            compact_pattern = r'(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\'"]([^\'"]*Create[Pp]roject[^\'"]*)[\'"]'
            
            compact_match = re.search(compact_pattern, content, re.IGNORECASE)
            
            if compact_match:
                left = int(compact_match.group(1))
                top = int(compact_match.group(2))
                right = int(compact_match.group(3))
                bottom = int(compact_match.group(4))
                text_value = compact_match.group(5)
                
                print(f"✅ [CAPCUT_CLICK] Found 'Createproject' in compact format:")
                print(f"   Text: '{text_value}'")
                print(f"   Coordinates: Left={left}, Top={top}, Right={right}, Bottom={bottom}")
                
                click_x = left + ((right - left) // 2)
                click_y = top + ((bottom - top) // 2)
                
                print(f"🎯 [CAPCUT_CLICK] Click position: ({click_x}, {click_y})")
                
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                pyautogui.click()
                
                print(f"✅ [CAPCUT_CLICK] Clicked 'Createproject' at ({click_x}, {click_y})")
                return True
            
            # ============================================
            # METHOD 3: Look for "Createproject" in text format
            # ============================================
            text_pattern = r'TEXT BLOCK #\d+:\s*•\s*(.+?Create[Pp]roject.+?)\s+Left:\s*(\d+)\s+Top:\s*(\d+)\s+Right:\s*(\d+)\s+Bottom:\s*(\d+)'
            
            text_match = re.search(text_pattern, content, re.DOTALL | re.IGNORECASE)
            
            if text_match:
                text_value = text_match.group(1).strip()
                left = int(text_match.group(2))
                top = int(text_match.group(3))
                right = int(text_match.group(4))
                bottom = int(text_match.group(5))
                
                print(f"✅ [CAPCUT_CLICK] Found 'Createproject' in text format:")
                print(f"   Text: '{text_value}'")
                print(f"   Coordinates: Left={left}, Top={top}, Right={right}, Bottom={bottom}")
                
                click_x = left + ((right - left) // 2)
                click_y = top + ((bottom - top) // 2)
                
                print(f"🎯 [CAPCUT_CLICK] Click position: ({click_x}, {click_y})")
                
                pyautogui.moveTo(click_x, click_y, duration=0.2)
                pyautogui.click()
                
                print(f"✅ [CAPCUT_CLICK] Clicked 'Createproject' at ({click_x}, {click_y})")
                return True
            
            print(f"❌ [CAPCUT_CLICK] Could not find 'Createproject' in screen_content.text")
            return False
            
        except Exception as e:
            print(f"❌ [CAPCUT_CLICK] Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ============================================
    # MAIN CAPCUT WORKFLOW
    # ============================================
    
    def main_capcut_workflow():
        try:
            if not os.path.exists(PANEL_PATH):
                print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
                update_operation_status("panel.json not found", is_error=True)
                return
            
            with open(PANEL_PATH, 'r', encoding='utf-8') as file:
                panel_data = json.load(file)
            
            capcut_config = panel_data.get('capcut_config', {})
            operate_capcut = capcut_config.get('operate_capcut', False)
            
            if not operate_capcut:
                print("ℹ️ CapCut operation is disabled in config")
                hud.print("ℹ️ CapCut operation disabled", "info")
                update_operation_status("CapCut operation is disabled in configuration")
                return
            
            project_title = panel_data.get('project_title', 'capcut_project')
            
            # Ensure CapCut window is ready
            hwnd = ensure_window_ready_and_focused()
            print(f"🪟 [MAIN] CapCut ready (HWND: {hwnd})")
            update_operation_status(f"Starting CapCut workflow for {project_title}")
            
            # ============================================
            # STEP 1: Write all targets and capture screen
            # ============================================
            print("📝 [CAPCUT] Analyzing current CapCut interface state...")
            
            # Write all target values to text_target.json
            try:
                text_target_data = {"value": "create project, media, audio, import"}
                with open(TEXT_TARGET, 'w', encoding='utf-8') as file:
                    json.dump(text_target_data, file, indent=4)
                print(f"✅ [CAPCUT] Wrote 'create project, media, audio, import' to {TEXT_TARGET}")
            except Exception as e:
                print(f"⚠️ [CAPCUT] Error writing to text_target.json: {e}")
            
            # Wait a moment
            time.sleep(0.5)
            
            # Call vision() to capture the current screen
            print(f"📸 [CAPCUT] Calling vision() to capture screen...")
            vision()
            
            # Wait for file to be written
            time.sleep(0.5)
            
            # ============================================
            # STEP 2: Check interface state
            # ============================================
            interface_state = check_interface_state()
            
            print("\n" + "="*60)
            print("📊 [CAPCUT] Interface State Summary:")
            print(f"   Has 'Create Project': {interface_state['has_create_project']}")
            print(f"   Has Edit Interface: {interface_state['has_edit_interface']}")
            print(f"   Found Values: {', '.join(interface_state['found_values']) if interface_state['found_values'] else 'None'}")
            print("="*60 + "\n")
            
            # ============================================
            # STEP 3: Decision logic - CLEAR AND SIMPLE
            # ============================================
            if interface_state['has_create_project']:
                # HIGHEST PRIORITY: If Create Project exists, ALWAYS click it
                print("🎯 [CAPCUT] 'Create Project' detected - clicking it to create project...")
                click_success = click_create_project()
                
                if click_success:
                    print("✅ [CAPCUT] 'Create project' clicked successfully!")
                    update_operation_status(f"CapCut project creation clicked successfully", is_success=True)
                    
                    # Wait for project to create
                    print(f"⏳ [CAPCUT] Waiting for project to create...")
                    time.sleep(3)
                    
                    # Re-check interface after clicking create project
                    print("📸 [CAPCUT] Re-checking interface after clicking create project...")
                    vision()
                    time.sleep(0.5)
                    
                    # Check if we're now in edit interface
                    new_state = check_interface_state()
                    if new_state['has_edit_interface']:
                        print("🎉 [CAPCUT] Successfully created project and entered edit interface!")
                        hud.print("✅ CapCut project created successfully!", "success")
                        update_operation_status(f"CapCut project for {project_title} created and in edit interface", is_success=True)
                    else:
                        print("⚠️ [CAPCUT] Project created but edit interface not detected yet")
                        hud.print("⚠️ CapCut project created, but edit interface pending", "warning")
                        update_operation_status(f"CapCut project created, edit interface not confirmed", is_error=True)
                else:
                    print(f"❌ [CAPCUT] Failed to click 'create project'")
                    error_msg = f"Failed to click 'create project' in CapCut"
                    update_operation_status(error_msg, is_error=True)
                    
            elif interface_state['has_edit_interface']:
                # We're already in edit interface - no need to click anything
                print("✅ [CAPCUT] Already in edit interface! No action needed.")
                hud.print("✅ CapCut edit interface ready!", "success")
                update_operation_status(f"CapCut already in edit interface for {project_title}", is_success=True)
                
            else:
                # Neither create project nor edit interface found - CapCut is in an unknown state
                # This means CapCut might be on a different screen or still loading
                print("❌ [CAPCUT] Neither 'Create Project' nor edit interface detected.")
                print("   This means CapCut is in an UNKNOWN state (not on create project screen, not in edit interface)")
                print("   Possible reasons:")
                print("   1. CapCut is still loading")
                print("   2. A different dialog/window is showing")
                print("   3. Vision detection failed to capture the text")
                print("   4. CapCut is minimized or not focused")
                update_operation_status("CapCut in UNKNOWN state - neither create project nor edit interface detected", is_error=True)
                hud.print("❌ CapCut in unknown state", "error")
            
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
    
    main_capcut_workflow()

def extend_images():
    """
    Extends images in the project's images folder based on transcript timestamps.
    
    Workflow:
    1. Read the transcript text from project's audio folder
    2. Extract all timestamps from the transcript
    3. Calculate duration for each image based on timestamp differences
    4. Calculate how many images are needed (based on timestamp count)
    5. Match images by number (1.jpeg → timestamp index 0, 2.jpeg → timestamp index 1, etc.)
    6. Only extend images that have a corresponding timestamp
    7. Move extended .mp4 files to a new 'extended_images' folder
    8. Leave original images untouched in the 'images' folder
    """
    
    # ============================================
    # CONFIGURATION
    # ============================================
    
    # Get project title from panel.json
    if not os.path.exists(PANEL_PATH):
        print(f"❌ Error: panel.json missing at: {PANEL_PATH}")
        return None
    
    with open(PANEL_PATH, 'r', encoding='utf-8') as file:
        panel_data = json.load(file)
    
    project_title = panel_data.get('project_title')
    
    if not project_title:
        print(f"❌ Error: project_title not found in panel.json")
        return None
    
    print(f"📁 [EXTEND_IMAGES] Processing project: {project_title}")
    
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
    audio_folder = os.path.join(project_folder, "audio")
    images_folder = os.path.join(project_folder, "images")
    extended_images_folder = os.path.join(project_folder, "extended_images")
    
    # Find the transcript file
    transcript_file = None
    if os.path.exists(audio_folder):
        for file in os.listdir(audio_folder):
            if file.endswith('.txt') and normalized_project_title in file:
                transcript_file = os.path.join(audio_folder, file)
                break
    
    if not transcript_file:
        # Try to find any txt file in audio folder
        if os.path.exists(audio_folder):
            for file in os.listdir(audio_folder):
                if file.endswith('.txt'):
                    transcript_file = os.path.join(audio_folder, file)
                    break
        
        if not transcript_file:
            print(f"❌ [EXTEND_IMAGES] Transcript file not found in: {audio_folder}")
            return None
    
    print(f"📄 [EXTEND_IMAGES] Found transcript: {transcript_file}")
    
    # Create extended_images folder if it doesn't exist
    if not os.path.exists(extended_images_folder):
        try:
            os.makedirs(extended_images_folder)
            print(f"📁 [EXTEND_IMAGES] Created extended_images folder: {extended_images_folder}")
        except Exception as e:
            print(f"❌ [EXTEND_IMAGES] Failed to create extended_images folder: {e}")
            return None
    else:
        print(f"📁 [EXTEND_IMAGES] Using existing extended_images folder: {extended_images_folder}")
        
        # Clean up any existing .mp4 files in extended_images folder
        existing_mp4s = [f for f in os.listdir(extended_images_folder) if f.endswith('.mp4')]
        if existing_mp4s:
            print(f"🗑️ [EXTEND_IMAGES] Cleaning {len(existing_mp4s)} existing .mp4 files from extended_images folder...")
            for f in existing_mp4s:
                try:
                    os.remove(os.path.join(extended_images_folder, f))
                except Exception as e:
                    print(f"   ⚠️ Could not remove {f}: {e}")
    
    # ============================================
    # STEP 1: READ AND PARSE TRANSCRIPT
    # ============================================
    
    def parse_timestamps_from_transcript(file_path):
        """
        Parse the transcript file to extract all timestamps and their corresponding text.
        Returns: list of tuples (timestamp_seconds, text)
        """
        print(f"🔍 [EXTEND_IMAGES] Parsing timestamps from transcript...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Find all timestamps in format (MM:SS) or (H:MM:SS)
            timestamp_pattern = r'\((\d+):(\d+)\)'
            
            # Find all matches with their positions
            matches = list(re.finditer(timestamp_pattern, content))
            
            if not matches:
                print(f"❌ [EXTEND_IMAGES] No timestamps found in transcript")
                return []
            
            timestamps = []
            for i, match in enumerate(matches):
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                total_seconds = minutes * 60 + seconds
                
                # Get the text following this timestamp until the next timestamp
                start_pos = match.end()
                end_pos = matches[i+1].start() if i+1 < len(matches) else len(content)
                text_segment = content[start_pos:end_pos].strip()
                
                timestamps.append({
                    'timestamp': match.group(0),
                    'minutes': minutes,
                    'seconds': seconds,
                    'total_seconds': total_seconds,
                    'text': text_segment[:100] + '...' if len(text_segment) > 100 else text_segment
                })
            
            print(f"✅ [EXTEND_IMAGES] Found {len(timestamps)} timestamps")
            
            # Print first few for debugging
            for i, ts in enumerate(timestamps[:5]):
                print(f"   [{i}] {ts['timestamp']} = {ts['total_seconds']}s - {ts['text'][:50]}...")
            
            return timestamps
            
        except Exception as e:
            print(f"❌ [EXTEND_IMAGES] Error parsing transcript: {e}")
            return []
    
    timestamps = parse_timestamps_from_transcript(transcript_file)
    
    if not timestamps:
        print(f"❌ [EXTEND_IMAGES] No timestamps extracted")
        return None
    
    # ============================================
    # STEP 2: CALCULATE DURATIONS FOR EACH IMAGE
    # ============================================
    
    def calculate_image_durations(timestamps):
        """
        Calculate the duration for each image based on timestamp differences.
        The first image duration is from timestamp 0 to timestamp 1.
        The last image duration is from last timestamp to end (default 5 seconds).
        """
        print(f"📊 [EXTEND_IMAGES] Calculating durations for {len(timestamps)} images...")
        
        durations = []
        total_timestamps = len(timestamps)
        
        for i in range(total_timestamps):
            current_time = timestamps[i]['total_seconds']
            
            if i + 1 < total_timestamps:
                # Duration is the difference between current and next timestamp
                next_time = timestamps[i+1]['total_seconds']
                duration = next_time - current_time
            else:
                # Last timestamp: use 5 seconds as default duration
                duration = 5.0
            
            # Ensure minimum duration of 1 second
            if duration < 1.0:
                duration = 1.0
            
            durations.append(duration)
        
        # Print duration summary
        print(f"📊 [EXTEND_IMAGES] Duration summary (first 10):")
        for i, duration in enumerate(durations[:10]):
            print(f"   Image {i+1}: {duration:.2f}s (from {timestamps[i]['timestamp']})")
        if len(durations) > 10:
            print(f"   ... and {len(durations) - 10} more images")
        
        return durations
    
    durations = calculate_image_durations(timestamps)
    
    # ============================================
    # STEP 3: GET IMAGES FROM IMAGES FOLDER
    # ============================================
    
    def get_sorted_images(folder_path):
        """
        Get all image files from the folder, sorted by number.
        Supports: .jpg, .jpeg, .png, .gif, .bmp, .webp
        """
        if not os.path.exists(folder_path):
            print(f"❌ [EXTEND_IMAGES] Images folder not found: {folder_path}")
            return []
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for file in os.listdir(folder_path):
            file_lower = file.lower()
            # Check if it's an image
            if any(file_lower.endswith(ext) for ext in image_extensions):
                # Extract number from filename
                match = re.match(r'^(\d+)', file)
                if match:
                    num = int(match.group(1))
                    image_files.append({
                        'number': num,
                        'filename': file,
                        'path': os.path.join(folder_path, file)
                    })
                else:
                    # For files without a number at the start, try to find any number
                    match = re.search(r'(\d+)', file)
                    if match:
                        num = int(match.group(1))
                        image_files.append({
                            'number': num,
                            'filename': file,
                            'path': os.path.join(folder_path, file)
                        })
        
        # Sort by number
        image_files.sort(key=lambda x: x['number'])
        
        print(f"📁 [EXTEND_IMAGES] Found {len(image_files)} images in folder")
        for img in image_files[:5]:
            print(f"   Image {img['number']}: {img['filename']}")
        if len(image_files) > 5:
            print(f"   ... and {len(image_files) - 5} more images")
        
        return image_files
    
    image_files = get_sorted_images(images_folder)
    
    if not image_files:
        print(f"❌ [EXTEND_IMAGES] No images found in: {images_folder}")
        return None
    
    # ============================================
    # STEP 4: CALCULATE HOW MANY IMAGES ARE NEEDED
    # ============================================
    
    num_timestamps = len(timestamps)
    num_images_available = len(image_files)
    
    # IMPORTANT: We need images numbered 1 through num_timestamps
    # Check which images we have that match the needed numbers
    image_number_map = {}
    for img in image_files:
        image_number_map[img['number']] = img
    
    # Determine which images we need (1 through num_timestamps)
    needed_image_numbers = set(range(1, num_timestamps + 1))
    available_image_numbers = set(image_number_map.keys())
    
    # Find which images we have vs need
    have_images = available_image_numbers & needed_image_numbers
    missing_images = needed_image_numbers - available_image_numbers
    extra_images = available_image_numbers - needed_image_numbers
    
    num_images_needed = len(have_images)
    
    print(f"\n📊 [EXTEND_IMAGES] Image Requirements:")
    print(f"   Timestamps found: {num_timestamps}")
    print(f"   Images available: {num_images_available}")
    print(f"   Images needed (1 to {num_timestamps}): {num_timestamps}")
    print(f"   Images we have that match: {len(have_images)}")
    
    if missing_images:
        print(f"   ⚠️ Missing images: {sorted(missing_images)[:10]}{'...' if len(missing_images) > 10 else ''}")
        print(f"   These images will be skipped (no corresponding image file)")
    
    if extra_images:
        print(f"   ℹ️ Extra images (beyond needed range): {sorted(extra_images)[:10]}{'...' if len(extra_images) > 10 else ''}")
        print(f"   These images will be left untouched")
    
    # ============================================
    # STEP 5: EXTEND IMAGES AND MOVE TO EXTENDED_IMAGES FOLDER
    # ============================================
    
    def extend_single_image(image_path, duration_seconds, output_path):
        """
        Extends a single image to the specified duration.
        """
        try:
            # Create the image clip with specified duration
            clip = ImageClip(image_path).with_duration(duration_seconds)
            
            # Save as video file
            clip.write_videofile(
                output_path,
                fps=1,  # 1 frame per second for still images
                logger=None  # Suppress output
            )
            
            return True
        except Exception as e:
            print(f"❌ [EXTEND_IMAGES] Error extending {image_path}: {e}")
            return False
    
    def extend_and_move_images(image_files, durations, images_folder, extended_images_folder, num_timestamps):
        """
        Extend images that have corresponding timestamps.
        Match image number to timestamp index (image 1 → timestamp index 0).
        """
        print(f"\n🎬 [EXTEND_IMAGES] Extending images...")
        print(f"   (Extended files will be saved to: {extended_images_folder})")
        print(f"   (Original images remain in: {images_folder})")
        print(f"   (Only images 1 through {num_timestamps} will be processed)\n")
        
        # Create a lookup for image by number
        image_by_number = {}
        for img in image_files:
            image_by_number[img['number']] = img
        
        extended_count = 0
        failed_count = 0
        skipped_count = 0
        created_files = []
        
        # Process images 1 through num_timestamps
        for i in range(num_timestamps):
            image_number = i + 1  # 1-indexed for image numbers
            duration = durations[i] if i < len(durations) else 5.0
            
            # Check if we have this image
            if image_number not in image_by_number:
                print(f"⏭️ [EXTEND_IMAGES] Skipping image {image_number} (file not found)")
                skipped_count += 1
                continue
            
            image_info = image_by_number[image_number]
            
            # Create output filename
            output_filename = f"{image_number}_duration_{int(duration)}s.mp4"
            temp_output_path = os.path.join(images_folder, output_filename)
            final_output_path = os.path.join(extended_images_folder, output_filename)
            
            print(f"🎬 [EXTEND_IMAGES] Extending image {image_number} ({image_info['filename']}) to {duration:.2f}s")
            
            # Extend the image (save temporarily in images folder)
            success = extend_single_image(image_info['path'], duration, temp_output_path)
            
            if success:
                # Move the file to extended_images folder
                try:
                    shutil.move(temp_output_path, final_output_path)
                    extended_count += 1
                    created_files.append(final_output_path)
                    print(f"   ✅ Created and moved: {output_filename}")
                except Exception as e:
                    print(f"   ⚠️ Created but failed to move: {e}")
                    # Keep it in the images folder if move fails
                    extended_count += 1
                    created_files.append(temp_output_path)
                    print(f"   ✅ Created (kept in images folder): {output_filename}")
            else:
                failed_count += 1
                print(f"   ❌ Failed to extend: {image_info['filename']}")
        
        print(f"\n📊 [EXTEND_IMAGES] Results: {extended_count} extended, {failed_count} failed, {skipped_count} skipped")
        print(f"   Extended files are in: {extended_images_folder}")
        
        return extended_count, failed_count, skipped_count, created_files
    
    extended_count, failed_count, skipped_count, created_files = extend_and_move_images(
        image_files, 
        durations, 
        images_folder, 
        extended_images_folder, 
        num_timestamps
    )
    
    # ============================================
    # STEP 6: VERIFY FILES IN EXTENDED_IMAGES FOLDER
    # ============================================
    
    def verify_extended_files(extended_images_folder, expected_count):
        """
        Verify that the expected number of .mp4 files are in the extended_images folder.
        """
        if not os.path.exists(extended_images_folder):
            return 0
        
        mp4_files = [f for f in os.listdir(extended_images_folder) if f.endswith('.mp4')]
        mp4_files.sort()
        
        print(f"\n📁 [EXTEND_IMAGES] Extended Images Folder Contents:")
        print(f"   Location: {extended_images_folder}")
        print(f"   Total .mp4 files: {len(mp4_files)}")
        
        if len(mp4_files) > 0:
            print(f"   First 5 files:")
            for f in mp4_files[:5]:
                file_size = os.path.getsize(os.path.join(extended_images_folder, f)) / 1024
                print(f"      - {f} ({file_size:.1f} KB)")
            if len(mp4_files) > 5:
                print(f"      ... and {len(mp4_files) - 5} more")
        
        if len(mp4_files) != expected_count:
            print(f"   ⚠️ Warning: Expected {expected_count} files but found {len(mp4_files)}")
        
        return len(mp4_files)
    
    actual_mp4_count = verify_extended_files(extended_images_folder, extended_count)
    
    # ============================================
    # STEP 7: SUMMARY
    # ============================================
    
    print("\n" + "="*60)
    print("📊 [EXTEND_IMAGES] SUMMARY")
    print("="*60)
    print(f"   Project: {project_title}")
    print(f"   Transcript: {os.path.basename(transcript_file)}")
    print(f"   Timestamps found: {num_timestamps}")
    print(f"   Images available: {num_images_available}")
    print(f"   Images that matched: {len(have_images)}")
    print(f"   Images extended: {extended_count}")
    print(f"   Images failed: {failed_count}")
    print(f"   Images skipped (missing): {skipped_count}")
    print(f"   Original images: KEPT in {images_folder}")
    print(f"   Extended files: SAVED in {extended_images_folder}")
    print(f"   .mp4 files in extended_images folder: {actual_mp4_count}")
    print("="*60)
    print("✅ [EXTEND_IMAGES] Complete!")
    
    return {
        'project_title': project_title,
        'timestamps_count': num_timestamps,
        'images_available': num_images_available,
        'images_matched': len(have_images),
        'images_extended': extended_count,
        'images_failed': failed_count,
        'images_skipped': skipped_count,
        'images_folder': images_folder,
        'extended_images_folder': extended_images_folder,
        'mp4_files_created': actual_mp4_count,
        'original_images_kept': num_images_available,
        'extended_files_list': [os.path.basename(f) for f in created_files]
    }



if __name__ == "__main__":
   extend_images()
    
