import pytesseract
from PIL import Image, ImageEnhance, ImageGrab
import os
import re
import time

# Tesseract path (same as your script)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Users\PC\Desktop\DESKTOP\Python\pytesseract\tessdata"

OUTPUT_TEXT_PATH = r"C:\xampp\htdocs\scenIQ\screen_content.text"

def perform_ocr():
    """
    Captures the entire screen, performs OCR using Tesseract,
    and saves the extracted text to OUTPUT_TEXT_PATH.
    Uses the same preprocessing as your script.
    """
    try:
        # Capture full screen
        screenshot = ImageGrab.grab()
        
        # Preprocess image (same as your tradingview_displaycheck function)
        img = screenshot.convert('L')  # Convert to grayscale
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(3)  # Increase contrast
        img = img.resize((int(img.width * 3), int(img.height * 3)), Image.Resampling.LANCZOS)
        img = img.point(lambda p: 0 if p < 128 else 255)  # Binarize (black and white)
        
        # Perform OCR with same configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        
        # Save extracted text
        with open(OUTPUT_TEXT_PATH, 'w', encoding='utf-8') as f:
            f.write(text)
        
        print(f"OCR completed. Text saved to {OUTPUT_TEXT_PATH}")
        return text
        
    except Exception as e:
        print(f"OCR Error: {e}")
        return None

# Usage
if __name__ == "__main__":
    time.sleep(5)
    perform_ocr()
    