import os
from moviepy import ImageClip

def extend_image_duration(image_path, duration_seconds, output_folder=None):
    """
    Extends an image's duration and saves it as a video file.
    
    Args:
        image_path: Path to the image file
        duration_seconds: Duration in seconds (e.g., 5 for 5 seconds)
        output_folder: Where to save the output (default: same folder as input)
    
    Returns:
        Path to the saved file
    """
    # Check if input file exists
    if not os.path.exists(image_path):
        print(f"❌ Error: File not found: {image_path}")
        return None
    
    # Set output folder
    if output_folder is None:
        output_folder = os.path.dirname(image_path)
    
    # Create output filename with duration
    base_name = os.path.basename(image_path)
    name, ext = os.path.splitext(base_name)
    output_filename = f"{name}_duration_{duration_seconds}s.mp4"
    output_path = os.path.join(output_folder, output_filename)
    
    try:
        # Create the image clip with specified duration
        clip = ImageClip(image_path).with_duration(duration_seconds)
        
        # Save as video file (removed verbose parameter)
        clip.write_videofile(
            output_path,
            fps=1,  # 1 frame per second for still images
            logger=None  # Keep logger if you want to suppress output, or remove it
        )
        
        print(f"✅ Image extended to {duration_seconds} seconds")
        print(f"📁 Saved to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# =====================
# 🔧 CONFIGURE HERE
# =====================

# Your image path
input_image = r"C:\xampp\htdocs\scenIQ\project\iamkennykings_project_1\images\1_202607291840.jpeg"

# ⏱️ SET DURATION (in seconds)
duration = 5  # Change this number

# Output folder (same as input if not specified)
output_folder = r"C:\xampp\htdocs\scenIQ\project\iamkennykings_project_1\images"

# Run the function
result = extend_image_duration(input_image, duration, output_folder)

if result:
    print(f"\n🎬 Done! Your image is now a {duration}-second video.")