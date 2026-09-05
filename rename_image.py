import os
import re
import glob

def rename_images_sequential(directory_path):
    """
    Rename all image files in the specified directory to sequential numbers (1.jpg, 2.jpg, 3.jpg, etc.)
    
    This function handles:
    - Multiple image extensions (.jpg, .jpeg, .png, .gif, .bmp, .webp)
    - Files with existing numbers (1.jpg, 3.jpg, 5.jpg, etc.)
    - Files with complex names (screenshot_2024_01_01.jpg, image_001.png, etc.)
    - Files with no numbers at all
    
    Args:
        directory_path (str): Path to the directory containing the images
    
    Returns:
        dict: A dictionary mapping old filenames to new filenames
    """
    
    print(f"🔄 [RENAME_IMAGES] Starting sequential rename in: {directory_path}")
    
    # Check if directory exists
    if not os.path.exists(directory_path):
        print(f"❌ Error: Directory '{directory_path}' does not exist.")
        return {}
    
    if not os.path.isdir(directory_path):
        print(f"❌ Error: '{directory_path}' is not a directory.")
        return {}
    
    # Get all image files (case insensitive)
    image_extensions = [
        '*.jpg', '*.jpeg', '*.JPG', '*.JPEG',
        '*.png', '*.PNG',
        '*.gif', '*.GIF',
        '*.bmp', '*.BMP',
        '*.webp', '*.WEBP',
        '*.tiff', '*.tif', '*.TIFF', '*.TIF'
    ]
    
    image_files = []
    
    for extension in image_extensions:
        try:
            files = glob.glob(os.path.join(directory_path, extension))
            image_files.extend(files)
        except Exception as e:
            print(f"⚠️ Warning: Error scanning for {extension}: {e}")
            continue
    
    # Remove duplicates (in case of overlapping extensions)
    image_files = list(set(image_files))
    
    if not image_files:
        print(f"❌ No image files found in '{directory_path}'.")
        print(f"   Supported extensions: {', '.join(set([ext.replace('*.', '') for ext in image_extensions]))}")
        return {}
    
    print(f"📁 Found {len(image_files)} image files")
    
    # Sort files by their existing number if they have one, otherwise by filename
    def extract_number(filename):
        """Extract the first number found in the filename."""
        match = re.search(r'(\d+)', os.path.basename(filename))
        if match:
            return int(match.group(1))
        return float('inf')  # Files without numbers go to the end
    
    def sort_key(filepath):
        """Sort by: existing number (if any), then by filename."""
        basename = os.path.basename(filepath)
        # Try to extract number from filename
        match = re.search(r'(\d+)', basename)
        if match:
            num = int(match.group(1))
            # If filename starts with the number, sort by it
            if basename.startswith(str(num)):
                return (num, 0, basename)
            else:
                return (num, 1, basename)
        else:
            # No number found, sort by filename
            return (float('inf'), 0, basename)
    
    # Sort files
    image_files.sort(key=sort_key)
    
    # Show first few files for debugging
    print(f"📋 First 10 files (sorted):")
    for i, f in enumerate(image_files[:10]):
        print(f"   {i+1}. {os.path.basename(f)}")
    if len(image_files) > 10:
        print(f"   ... and {len(image_files) - 10} more")
    
    # Dictionary to track renamed files
    renamed_files = {}
    skipped_files = []
    renamed_count = 0
    
    # Create a set of existing target filenames to avoid conflicts
    existing_targets = set()
    for ext in image_extensions:
        pattern = ext.replace('*', '')
        for f in glob.glob(os.path.join(directory_path, f"*{pattern}")):
            existing_targets.add(os.path.basename(f))
    
    print(f"\n🔄 Renaming files sequentially...")
    
    for index, old_path in enumerate(image_files, start=1):
        # Get the file extension
        _, ext = os.path.splitext(old_path)
        old_filename = os.path.basename(old_path)
        
        # Create new filename with sequential number
        new_filename = f"{index}{ext}"
        new_path = os.path.join(directory_path, new_filename)
        
        # Check if the new filename already exists and is not the current file
        if os.path.exists(new_path) and new_path != old_path:
            # Handle conflict by adding a suffix
            counter = 1
            while os.path.exists(new_path):
                new_filename = f"{index}_{counter}{ext}"
                new_path = os.path.join(directory_path, new_filename)
                counter += 1
            print(f"   ⚠️ Conflict: {old_filename} -> {new_filename} (renamed with suffix)")
        
        # Skip if the file already has the correct name
        if old_path == new_path:
            print(f"   ℹ️ Skipping: {old_filename} (already correctly named)")
            skipped_files.append(old_filename)
            continue
        
        # Rename the file
        try:
            os.rename(old_path, new_path)
            renamed_files[old_filename] = new_filename
            renamed_count += 1
            print(f"   ✅ {old_filename} -> {new_filename}")
        except Exception as e:
            print(f"   ❌ Error renaming {old_filename}: {e}")
            skipped_files.append(old_filename)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 [RENAME_IMAGES] SUMMARY")
    print("="*60)
    print(f"   Total images found: {len(image_files)}")
    print(f"   Successfully renamed: {renamed_count}")
    print(f"   Skipped (already correct): {len([f for f in skipped_files if f not in renamed_files])}")
    print(f"   Failed: {len(image_files) - renamed_count - len([f for f in skipped_files if f not in renamed_files])}")
    print("="*60)
    
    # Show final filenames
    if renamed_count > 0 or len(image_files) > 0:
        print("\n📋 Final filenames (first 10):")
        all_files = sorted([f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))])
        image_final = []
        for f in all_files:
            f_lower = f.lower()
            if any(f_lower.endswith(ext.replace('*.', '').lower()) for ext in image_extensions):
                image_final.append(f)
        
        for i, f in enumerate(image_final[:10]):
            print(f"   {i+1}. {f}")
        if len(image_final) > 10:
            print(f"   ... and {len(image_final) - 10} more")
    
    print(f"\n✅ [RENAME_IMAGES] Complete! Renamed {renamed_count} files.")
    
    return renamed_files


def rename_images_sequential_smart(directory_path):
    """
    Smart rename that handles files with numbers and gaps.
    
    This function:
    1. Finds the highest number in existing filenames
    2. Renames all files sequentially from 1 to N
    3. Handles gaps (1.jpg, 5.jpg, 10.jpg -> 1.jpg, 2.jpg, 3.jpg)
    4. Preserves file extensions
    5. Handles naming conflicts safely
    
    Args:
        directory_path (str): Path to the directory containing the images
    
    Returns:
        dict: A dictionary mapping old filenames to new filenames
    """
    
    print(f"🔄 [RENAME_SMART] Smart sequential rename in: {directory_path}")
    
    # Check if directory exists
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        print(f"❌ Error: Directory '{directory_path}' does not exist or is not a directory.")
        return {}
    
    # Get all image files with their numbers
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif']
    image_files = []
    
    for file in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file)
        if not os.path.isfile(file_path):
            continue
        
        _, ext = os.path.splitext(file)
        if ext.lower() in image_extensions:
            # Try to extract number from filename
            match = re.search(r'(\d+)', file)
            if match:
                num = int(match.group(1))
                image_files.append({
                    'path': file_path,
                    'filename': file,
                    'number': num,
                    'ext': ext
                })
            else:
                # Files without numbers get assigned a high number
                image_files.append({
                    'path': file_path,
                    'filename': file,
                    'number': float('inf'),
                    'ext': ext
                })
    
    # Sort by number
    image_files.sort(key=lambda x: x['number'])
    
    if not image_files:
        print(f"❌ No image files found in '{directory_path}'.")
        return {}
    
    print(f"📁 Found {len(image_files)} image files")
    
    # Show current files
    print(f"📋 Current files (first 10):")
    for i, img in enumerate(image_files[:10]):
        num_str = str(img['number']) if img['number'] != float('inf') else 'No number'
        print(f"   {i+1}. {img['filename']} (number: {num_str})")
    if len(image_files) > 10:
        print(f"   ... and {len(image_files) - 10} more")
    
    # Rename files sequentially
    renamed_files = {}
    temp_files = []  # For handling conflicts
    
    print(f"\n🔄 Renaming files sequentially...")
    
    for index, img_data in enumerate(image_files, start=1):
        old_path = img_data['path']
        old_filename = img_data['filename']
        ext = img_data['ext']
        
        # Create new filename with sequential number
        new_filename = f"{index}{ext}"
        new_path = os.path.join(directory_path, new_filename)
        
        # Skip if already correctly named
        if old_path == new_path:
            print(f"   ℹ️ Skipping: {old_filename} (already correctly named)")
            continue
        
        # Handle conflicts
        if os.path.exists(new_path):
            # Rename the existing file to a temp name first
            temp_name = f"_temp_{index}_{os.urandom(4).hex()}{ext}"
            temp_path = os.path.join(directory_path, temp_name)
            try:
                os.rename(new_path, temp_path)
                temp_files.append((temp_path, new_path))
                print(f"   🔄 Moved conflicting file to temp: {os.path.basename(temp_path)}")
            except Exception as e:
                print(f"   ⚠️ Could not move conflicting file: {e}")
                # Try with suffix
                counter = 1
                while os.path.exists(new_path):
                    new_filename = f"{index}_{counter}{ext}"
                    new_path = os.path.join(directory_path, new_filename)
                    counter += 1
        
        # Rename the file
        try:
            os.rename(old_path, new_path)
            renamed_files[old_filename] = new_filename
            print(f"   ✅ {old_filename} -> {new_filename}")
        except Exception as e:
            print(f"   ❌ Error renaming {old_filename}: {e}")
    
    # Restore any temp files
    for temp_path, original_path in temp_files:
        try:
            if os.path.exists(temp_path) and not os.path.exists(original_path):
                os.rename(temp_path, original_path)
                print(f"   🔄 Restored temp file to: {os.path.basename(original_path)}")
        except Exception as e:
            print(f"   ⚠️ Could not restore temp file: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 [RENAME_SMART] SUMMARY")
    print("="*60)
    print(f"   Total images found: {len(image_files)}")
    print(f"   Successfully renamed: {len(renamed_files)}")
    print(f"   Files skipped: {len(image_files) - len(renamed_files)}")
    print("="*60)
    
    print(f"\n✅ [RENAME_SMART] Complete! Renamed {len(renamed_files)} files.")
    
    return renamed_files


def rename_and_fix_gaps(directory_path):
    """
    Rename all images sequentially, fixing any gaps in numbering.
    
    This is the main function to use. It:
    1. Finds all image files
    2. Extracts numbers from filenames
    3. Renames them sequentially from 1 to N
    4. Handles all edge cases
    
    Args:
        directory_path (str): Path to the directory containing the images
    
    Returns:
        dict: A dictionary mapping old filenames to new filenames
    """
    
    print(f"🔄 [FIX_GAPS] Renaming images sequentially and fixing gaps...")
    
    # Use the smart rename function
    result = rename_images_sequential_smart(directory_path)
    
    # Additional verification
    if result:
        print(f"\n🔍 Verifying renamed files...")
        image_files = []
        for f in os.listdir(directory_path):
            f_lower = f.lower()
            if any(f_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                image_files.append(f)
        
        image_files.sort(key=lambda x: int(re.search(r'^(\d+)', x).group(1)) if re.search(r'^(\d+)', x) else float('inf'))
        
        # Check for gaps
        for i, f in enumerate(image_files, start=1):
            match = re.match(r'^(\d+)', f)
            if match:
                num = int(match.group(1))
                if num != i:
                    print(f"   ⚠️ Gap detected: Expected {i}, found {num} in {f}")
            else:
                print(f"   ⚠️ File not numbered: {f}")
        
        print(f"   ✅ Total files: {len(image_files)}")
    
    return result


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Your specific path
    path = r"C:\xampp\htdocs\AI automation\scenIQ\project\iamkennykings_project_1\images"
    
    # Option 1: Simple sequential rename
    print("\n" + "="*60)
    print("OPTION 1: Sequential Rename")
    print("="*60)
    result1 = rename_images_sequential(path)
    
    # Option 2: Smart rename (recommended)
    print("\n" + "="*60)
    print("OPTION 2: Smart Rename (Recommended)")
    print("="*60)
    result2 = rename_images_sequential_smart(path)
    
    # Option 3: Fix gaps (full solution)
    print("\n" + "="*60)
    print("OPTION 3: Fix Gaps (Full Solution)")
    print("="*60)
    result3 = rename_and_fix_gaps(path)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    if result3:
        print(f"   Successfully renamed {len(result3)} files")
        print("   All files should now be numbered 1, 2, 3, ... without gaps")
    else:
        print("   No files were renamed")
    print("="*60)