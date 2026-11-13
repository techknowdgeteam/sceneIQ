"""Extract the main foreground subject from one image and save it as a sticker PNG.

The input path is configured below. The output is written to the current user's
Windows Downloads folder as <original-name>_sticker.png.

First-time setup (recommended Python 3.12):
    py -3.12 -m pip install "rembg[cpu]" Pillow

The first run downloads the selected ONNX segmentation model. The model is then
cached locally by rembg and reused on later runs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
except ImportError:
    print("ERROR: Pillow is not installed.")
    print('Install it with: py -3.12 -m pip install "rembg[cpu]" Pillow')
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
INPUT_IMAGE = Path(
    r"C:\xampp\htdocs\AI automation\serenum\files\jpgfolders\Silverrose\generated\SmartSelect_20250902-190659_Facebook_jpg_generated.jpg"
)

# BiRefNet is the primary general-purpose model. If it cannot be initialized,
# the script tries ISNet as a fallback.
PRIMARY_MODEL = "birefnet-general"
FALLBACK_MODEL = "isnet-general-use"

# A sticker-style white border helps separate the cutout from video backgrounds.
ADD_WHITE_OUTLINE = True
OUTLINE_WIDTH_RATIO = 0.008  # 0.8% of the longest image dimension
MIN_OUTLINE_PX = 5
MAX_OUTLINE_PX = 24

# Transparent padding around the final sticker after trimming empty canvas.
PADDING_PX = 36


# ---------------------------------------------------------------------------
# IMAGE PROCESSING
# ---------------------------------------------------------------------------
def create_sticker_canvas(
    subject: Image.Image,
    add_outline: bool = True,
) -> Image.Image:
    """Add an optional white sticker border while preserving transparent edges."""
    subject = subject.convert("RGBA")
    if not add_outline:
        return subject

    alpha = subject.getchannel("A")
    longest_side = max(subject.size)
    outline_width = max(
        MIN_OUTLINE_PX,
        min(MAX_OUTLINE_PX, int(round(longest_side * OUTLINE_WIDTH_RATIO))),
    )

    # MaxFilter expands the extracted alpha mask, creating the sticker border.
    # The extracted subject is composited over this white silhouette.
    filter_size = outline_width * 2 + 1
    expanded_alpha = alpha.filter(ImageFilter.MaxFilter(filter_size))

    white_border = Image.new("RGBA", subject.size, (255, 255, 255, 0))
    white_border.putalpha(expanded_alpha)
    sticker = Image.alpha_composite(white_border, subject)
    return sticker


def crop_to_visible_subject(image: Image.Image, padding: int) -> Image.Image:
    """Trim transparent margins and retain a small transparent safety border."""
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError(
            "The segmentation model returned a fully transparent image. "
            "No foreground subject could be detected."
        )

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def load_rembg_session():
    """Load the preferred model, falling back to another general model if needed."""
    try:
        from rembg import new_session
    except ImportError:
        print("ERROR: rembg is not installed.")
        print('Install it with: py -3.12 -m pip install "rembg[cpu]" Pillow')
        raise SystemExit(1)

    print(f"Loading background-removal model: {PRIMARY_MODEL}")
    try:
        return new_session(PRIMARY_MODEL), PRIMARY_MODEL
    except Exception as primary_error:
        print(f"WARNING: {PRIMARY_MODEL} could not be loaded: {primary_error}")
        print(f"Trying fallback model: {FALLBACK_MODEL}")
        try:
            return new_session(FALLBACK_MODEL), FALLBACK_MODEL
        except Exception as fallback_error:
            raise RuntimeError(
                "Neither background-removal model could be initialized. "
                "Check your internet connection and rembg installation.\n"
                f"Primary model error: {primary_error}\n"
                f"Fallback model error: {fallback_error}"
            ) from fallback_error


def extract_subject_to_downloads(input_path: Path) -> Path:
    """Remove the image background and save a transparent sticker PNG."""
    if not input_path.is_file():
        raise FileNotFoundError(
            "The source image was not found. Confirm that this exact path exists:\n"
            f"{input_path}"
        )

    downloads_folder = Path.home() / "Downloads"
    downloads_folder.mkdir(parents=True, exist_ok=True)
    output_path = downloads_folder / f"{input_path.stem}_sticker.png"

    from rembg import remove

    session, model_used = load_rembg_session()

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print("Preparing image...")

    with Image.open(input_path) as opened_image:
        # Apply EXIF orientation before segmentation and keep the original
        # resolution; do not resize or crop the source before removing its BG.
        source_image = ImageOps.exif_transpose(opened_image).convert("RGBA")

    print("Detecting the foreground subject and removing the background...")
    try:
        extracted = remove(
            source_image,
            session=session,
            post_process_mask=True,
        ).convert("RGBA")
    except Exception as exc:
        raise RuntimeError(f"Background removal failed: {exc}") from exc
    finally:
        source_image.close()

    print("Creating sticker border and trimming transparent margins...")
    sticker = create_sticker_canvas(extracted, add_outline=ADD_WHITE_OUTLINE)
    extracted.close()
    sticker = crop_to_visible_subject(sticker, padding=PADDING_PX)

    # PNG is required to retain the transparent alpha channel.
    sticker.save(output_path, format="PNG", optimize=True)

    # Verify the saved file really contains transparency.
    with Image.open(output_path) as check_image:
        check_image.load()
        if check_image.mode != "RGBA":
            raise RuntimeError(
                f"Output PNG unexpectedly has mode {check_image.mode}; expected RGBA."
            )
        if check_image.getchannel("A").getextrema() == (255, 255):
            raise RuntimeError(
                "The saved image has no transparent pixels. The background may not "
                "have been removed correctly."
            )
        output_size = check_image.size

    print("\nSUCCESS: Subject extracted as a transparent sticker.")
    print(f"Model used: {model_used}")
    print(f"Sticker size: {output_size[0]} x {output_size[1]} pixels")
    print(f"Saved to: {output_path}")
    return output_path


def main() -> int:
    try:
        extract_subject_to_downloads(INPUT_IMAGE)
        return 0
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}")
        return 2
    except Exception as exc:
        print(f"\nERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
