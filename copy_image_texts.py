import os
import json
import warnings
from datetime import datetime
import pyautogui

# Suppress warnings
warnings.filterwarnings('ignore')

# Fix protobuf compatibility
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Import the library
from chrome_lens_py import LensAPI

# Define your paths
SCREEN_IMAGE = r"C:\xampp\htdocs\AI automation\scenIQ\input_images\screen.png"
SCREEN_TEXT_CONTENT = r"C:\xampp\htdocs\AI automation\scenIQ\screen_content.json"

def vision():
    """
    Captures the screen, extracts text using Google Lens API, and saves in EXACT same format as full_image_vision().
    OVERWRITES the file completely - no appending.
    """
    
    # ===== INTERNAL FUNCTION: CAPTURE SCREEN =====
    def capture_screen():
        """
        Captures the current screen and saves it to SCREEN_IMAGE path.
        Ensures the directory exists before saving.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("📸 Capturing screen...")
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(SCREEN_IMAGE), exist_ok=True)
            
            # Capture the entire screen
            screenshot = pyautogui.screenshot()
            
            # Save to SCREEN_IMAGE
            screenshot.save(SCREEN_IMAGE)
            
            # Get screen dimensions
            screen_width, screen_height = pyautogui.size()
            print(f"✅ Screen captured: {SCREEN_IMAGE}")
            print(f"🖥️ Screen Dimensions: {screen_width} x {screen_height} pixels")
            
            return True
            
        except Exception as e:
            print(f"❌ Error capturing screen: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ===== STEP 1: CAPTURE THE SCREEN =====
    if not capture_screen():
        print("❌ Failed to capture screen. Exiting.")
        return
    
    # ===== STEP 2: CHECK IF IMAGE EXISTS =====
    if not os.path.exists(SCREEN_IMAGE):
        print(f"❌ Error: Image not found at {SCREEN_IMAGE}")
        return
    
    try:
        print("="*80)
        print("🔍 GOOGLE LENS TEXT EXTRACTION")
        print("="*80)
        print("🚀 Starting Google Lens text extraction...")
        print(f"📷 Processing image: {SCREEN_IMAGE}")
        
        # Initialize the API client
        api = LensAPI()
        print("✅ API initialized successfully")
        
        # Process the image (synchronous)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            api.process_image(image_path=SCREEN_IMAGE)
        )
        loop.close()
        
        # Get extracted text
        extracted_text = result.get('ocr_text', '')
        text_blocks = result.get('text_blocks', [])
        
        print(f"📦 Found {len(text_blocks)} text blocks from Google Lens")
        
        # ===== PROCESS TEXT BLOCKS - KEEP SENTENCES TOGETHER =====
        ocr_results = {}
        merged_texts = []
        
        # If we have text blocks, keep them as sentences/phrases
        if text_blocks and isinstance(text_blocks, list):
            print(f"\n📝 Processing {len(text_blocks)} text blocks as sentences...")
            
            for block in text_blocks:
                if isinstance(block, dict):
                    text = block.get('text', '').strip()
                    if not text:
                        continue
                    
                    # Extract coordinates
                    left = 0
                    top = 0
                    width = 0
                    height = 0
                    confidence = 90
                    
                    if 'bounding_box' in block:
                        bbox = block['bounding_box']
                        left = int(bbox.get('left', 0))
                        top = int(bbox.get('top', 0))
                        width = int(bbox.get('width', 0))
                        height = int(bbox.get('height', 0))
                    elif 'left' in block and 'top' in block:
                        left = int(block.get('left', 0))
                        top = int(block.get('top', 0))
                        width = int(block.get('width', 0))
                        height = int(block.get('height', 0))
                    else:
                        # If no coordinates, use position based on index
                        left = 10
                        top = 10 + (len(merged_texts) * 35)
                        width = len(text) * 8
                        height = 25
                    
                    right = left + width
                    bottom = top + height
                    
                    # ===== KEEP THE FULL TEXT AS A SENTENCE/PHRASE =====
                    merged_texts.append({
                        'text': text,  # Keep the full text (sentence/phrase)
                        'left': left,
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'width': width,
                        'height': height,
                        'confidence': confidence,
                        'region_id': 0,
                        'distance_from_top': top,
                        'distance_from_bottom': 0,
                        'screen_percentage': 0
                    })
                    
        
        # If no text blocks, split the full text into sentences
        elif extracted_text:
            print(f"\n⚠️ No text blocks found. Creating from extracted text as sentences...")
            lines = extracted_text.split('\n')
            y_pos = 10
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # ===== KEEP THE FULL LINE AS A SENTENCE =====
                line_width = len(line) * 8
                merged_texts.append({
                    'text': line,  # Keep the full line
                    'left': 10,
                    'top': y_pos,
                    'right': 10 + line_width,
                    'bottom': y_pos + 25,
                    'width': line_width,
                    'height': 25,
                    'confidence': 90,
                    'region_id': 0,
                    'distance_from_top': y_pos,
                    'distance_from_bottom': 0,
                    'screen_percentage': 0
                })
                print(f"  📝 Sentence: '{line[:50]}{'...' if len(line) > 50 else ''}' at (10, {y_pos})")
                
                y_pos += 35
        
        # ===== PREPARE OCR RESULTS =====
        ocr_results = {}
        for idx, result in enumerate(merged_texts, 1):
            ocr_results[f"region_{idx}"] = {
                "search_engine": "google-lens-vision",
                "text_value_found": [result['text']],  # The full sentence/phrase
                "Left": int(result.get('left', 0)),
                "Top": int(result.get('top', 0)),
                "Right": int(result.get('right', 0)),
                "Bottom": int(result.get('bottom', 0)),
                "Width": int(result.get('width', 0)),
                "Height": int(result.get('height', 0)),
                "Area": int(result.get('width', 0) * result.get('height', 0)),
                "Confidence": int(result.get('confidence', 0)),
                "Region_ID": idx
            }
        
        # ===== PREPARE METADATA =====
        metadata = {
            "processed_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_text_regions": len(merged_texts),
            "total_ocr_results": len(merged_texts),
            "failed_regions": 0,
            "empty_results": 0,
            "vision_method": "google-lens-api",
            "image_dimensions": "auto-detected"
        }
        
        # ===== BUILD DATA STRUCTURE =====
        final_data = {
            "metadata": metadata,
            "text_regions": [],
            "ocr_results": ocr_results
        }
        
        # ===== OVERWRITE THE FILE =====
        with open(SCREEN_TEXT_CONTENT, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Data saved to: {SCREEN_TEXT_CONTENT}")
        
        # ===== PRINT SUMMARY =====
        print("\n" + "="*80)
        print(f"✅ GOOGLE LENS vision COMPLETE!")
        print(f"  • Total Sentences/Phrases Found: {len(merged_texts)}")
        print(f"  • Results Saved to: {SCREEN_TEXT_CONTENT}")
        print("="*80)
        
        return merged_texts
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Save error information
        error_data = {
            "metadata": {
                "processed_on": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "vision_method": "google-lens-api",
                "status": "error"
            },
            "text_regions": [],
            "ocr_results": {}
        }
        with open(SCREEN_TEXT_CONTENT, 'w', encoding='utf-8') as f:
            json.dump(error_data, f, indent=2, ensure_ascii=False)

# The caller just calls vision()
if __name__ == "__main__":
    vision()
    