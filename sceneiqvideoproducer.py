"""SceneIQ standalone video producer.
sceneiqvideoproducer.py
This module runs video rendering only. Google Flow image generation lives in
sceniqimageproduction.py and is not imported or started here.
"""
import pyautogui
from PIL import Image
import os
import glob
from datetime import datetime
import subprocess
import json
import psutil
import time
import re
import difflib
import pyperclip
import keyboard 
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

    # Tracks titles attempted during this one invocation only. It is deliberately
    # in-memory: a later execution re-checks every project, including previously
    # aborted projects whose missing assets may have been restored.
    attempted_project_keys = set()

    def _run_video_producer():
        """
        Assemble entry_N images into a narrated video using AI-directed per-entry.
        Narration audio and a complete, readable image set (one per scene) are mandatory;
        projects failing either check are marked aborted and skipped.
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

        # The current validation result is authoritative on every execution.
        # Existing aborted markers are historical information only; they never
        # block a fresh attempt after assets may have been restored.
        VIDEO_VALIDATION_BLOCK_MARKER = "VIDEO_PRODUCER_VALIDATION_FAILED"

        def _set_root_field(record, field_name, value):
            wanted = _normalise_key(field_name)
            for existing_key in list(record.keys()):
                if _normalise_key(existing_key) == wanted:
                    record[existing_key] = value
                    return
            record[field_name] = value

        def _save_ready_data_atomic():
            ready_directory = os.path.dirname(READY_SCRIPT)
            if ready_directory:
                os.makedirs(ready_directory, exist_ok=True)
            temporary_path = READY_SCRIPT + f".validation_{os.getpid()}.tmp"
            try:
                with open(temporary_path, "w", encoding="utf-8") as temporary_file:
                    json.dump(ready_data, temporary_file, indent=4, ensure_ascii=False)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                os.replace(temporary_path, READY_SCRIPT)
                return True
            except Exception as save_exc:
                try:
                    if os.path.exists(temporary_path):
                        os.remove(temporary_path)
                except OSError:
                    pass
                print(f"❌ [READY-SCRIPT] Could not persist validation status: {save_exc}")
                return False

        def _mark_record_aborted(record, title, reason):
            reason_text = (
                f"{VIDEO_VALIDATION_BLOCK_MARKER} | {reason} "
                "Video production was skipped; no output was rendered."
            )
            _set_root_field(record, "status", "aborted")
            _set_root_field(record, "operation_status", reason_text)
            if _save_ready_data_atomic():
                print(f"🛑 [READY-SCRIPT] Marked '{title}' as aborted: {reason_text}")
                return True
            return False

        def _mark_record_operating(record, title):
            """Clear any old validation failure and mark a newly valid project operating."""
            operation_text = (
                "video_production_started: Required narration audio and all expected "
                "scene images have been verified; video production is in progress."
            )
            _set_root_field(record, "status", "operating")
            _set_root_field(record, "operation_status", operation_text)
            if _save_ready_data_atomic():
                print(f"🚀 [READY-SCRIPT] '{title}' status updated to operating.")
                return True
            return False

        def _mark_record_completed(record, title, video_path):
            """Record successful output only after a non-empty video file exists."""
            operation_text = f"video_production_completed: Video successfully rendered to '{video_path}'."
            _set_root_field(record, "status", "completed")
            _set_root_field(record, "operation_status", operation_text)
            if _save_ready_data_atomic():
                print(f"✅ [READY-SCRIPT] '{title}' status updated to completed.")
                return True
            return False

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
            candidate_key = normalize_project_title(candidate_title).casefold()
            if candidate_key in attempted_project_keys:
                print(
                    f"⏭️ [READY-SCRIPT] '{candidate_title}' was already checked during this "
                    "execution. It will be checked again on the next execution."
                )
                continue
            # Never use status or an old operation_status validation marker as a
            # queue filter. Every project is re-evaluated on each new execution.
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
                # Keep the candidate in the queue even when no image exists. The
                # validation gate below must mark it aborted rather than silently
                # ignoring it or allowing a partial video to be rendered.
                found_image_folder = next(
                    (folder for folder in candidate_image_folders if os.path.isdir(folder)),
                    candidate_image_folders[0],
                )
            attempted_project_keys.add(candidate_key)
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
                "✅ [READY-SCRIPT] No more projects remain to check in this execution. "
                "All projects, including previously aborted projects, will be re-evaluated "
                "the next time the producer is started."
            )
            return None

        def _abort_current_project(reason):
            """Persist a validation failure, then continue to the next queue item."""
            saved = _mark_record_aborted(panel_data, project_title, reason)
            if not saved:
                # Stop rather than recursively selecting the same project when
                # the failure marker could not be persisted.
                return None
            print("🔎 [READY-SCRIPT] Continuing with the next eligible project...")
            return _run_video_producer()

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
            return _abort_current_project(
                f"The project image folder is unavailable: '{project_folder}'. "
                "The required scene images could not be checked."
            )
        if not source_folder or not _has_entry_images(source_folder):
            return _abort_current_project(
                f"No usable scene images are currently available in '{source_folder}'. "
                "The required scene-image set is incomplete."
            )
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
            return _abort_current_project(
                "No scene entries were found in the project script, so the required scene count is unavailable."
            )
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
            """Return one best readable image per scene number, in scene order.

            Duplicate files for the same entry are deduplicated in memory; source
            files are never deleted. The highest-resolution valid image is preferred,
            followed by a lossless-format preference, file size, and modification
            time for deterministic selection.
            """
            if not folder_path or not os.path.isdir(folder_path):
                return []

            supported_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}
            extension_priority = {
                ".png": 7,
                ".tiff": 6,
                ".tif": 6,
                ".webp": 5,
                ".bmp": 4,
                ".jpg": 3,
                ".jpeg": 3,
                ".gif": 2,
            }
            try:
                filenames = os.listdir(folder_path)
            except OSError as folder_exc:
                print(f"⚠️ [READY-SCRIPT] Cannot inspect entry-image folder '{folder_path}': {folder_exc}")
                return []

            candidates_by_number = {}
            for filename in filenames:
                match = re.fullmatch(
                    r"entry[_-]?(\d+)\.(png|jpg|jpeg|gif|bmp|webp|tiff)",
                    filename,
                    re.IGNORECASE,
                )
                if not match:
                    continue

                image_number = int(match.group(1))
                image_path = os.path.join(folder_path, filename)
                try:
                    if not os.path.isfile(image_path):
                        continue
                    file_size = os.path.getsize(image_path)
                    if file_size <= 0:
                        continue
                    # Verify the image payload and capture resolution before rendering.
                    with Image.open(image_path) as image_check:
                        image_width, image_height = image_check.size
                        image_check.verify()
                    if image_width <= 0 or image_height <= 0:
                        raise ValueError("Image has invalid dimensions")
                    modified_at = os.path.getmtime(image_path)
                except Exception as image_exc:
                    print(f"⚠️ [READY-SCRIPT] Invalid scene image rejected: {image_path} ({image_exc})")
                    continue

                extension = os.path.splitext(filename)[1].lower()
                candidate = {
                    "number": image_number,
                    "filename": filename,
                    "path": image_path,
                    "width": image_width,
                    "height": image_height,
                    "file_size": file_size,
                    "modified_at": modified_at,
                    "_selection_score": (
                        image_width * image_height,
                        extension_priority.get(extension, 0),
                        file_size,
                        modified_at,
                        filename.casefold(),
                    ),
                }
                candidates_by_number.setdefault(image_number, []).append(candidate)

            selected_items = []
            for image_number in sorted(candidates_by_number):
                candidates = candidates_by_number[image_number]
                # Select one image per scene. Additional copies are ignored rather
                # than causing the entire project to fail validation.
                selected = max(candidates, key=lambda item: item["_selection_score"])
                selected = {
                    key: value for key, value in selected.items()
                    if not key.startswith("_")
                }
                selected_items.append(selected)

                if len(candidates) > 1:
                    ignored_names = [
                        item["filename"] for item in candidates
                        if item["filename"] != selected["filename"]
                    ]
                    print(
                        f"♻️ [READY-SCRIPT] Deduplicated {len(candidates)} files for entry_{image_number}; "
                        f"using '{selected['filename']}' and ignoring: {', '.join(ignored_names)}"
                    )

            return selected_items

        image_files = get_sorted_images(source_folder)

        def find_audio_file(title):
            """Find narration audio using punctuation- and spacing-insensitive names.

            For example, "I am audio", "i_am_audio", "i-am-audio", and
            "iamaudio" all normalize to the same matching key: "iamaudio".
            Matching remains a normalized substring search, allowing filenames
            to contain additional prefixes or suffixes around the project title.
            """
            import unicodedata

            def normalize_audio_match_text(value):
                value = unicodedata.normalize("NFKD", str(value or "")).casefold()
                # Keep letters and digits only: discard spaces, underscores,
                # hyphens, apostrophes, brackets, emoji, and other punctuation.
                return "".join(character for character in value if character.isalnum())

            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads):
                print(f"⚠️ [AUDIO] Downloads folder was not found: {downloads}")
                return None

            normalized_title = normalize_audio_match_text(title)
            if not normalized_title:
                print(
                    f"⚠️ [AUDIO] Cannot match narration audio because the project title "
                    f"has no letters or numbers: {title!r}"
                )
                return None

            audio_exts = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma")
            try:
                matches = []
                for name in os.listdir(downloads):
                    if not name.casefold().endswith(audio_exts):
                        continue

                    audio_path = os.path.join(downloads, name)
                    if not os.path.isfile(audio_path):
                        continue
                    try:
                        if os.path.getsize(audio_path) <= 0:
                            continue
                    except OSError:
                        continue

                    # Compare without the extension so it cannot affect the match.
                    audio_name_without_extension = os.path.splitext(name)[0]
                    normalized_audio_name = normalize_audio_match_text(
                        audio_name_without_extension
                    )
                    if normalized_title in normalized_audio_name:
                        matches.append(audio_path)
                        print(
                            f"🔎 [AUDIO] Normalized filename match: '{name}' "
                            f"(project key: '{normalized_title}')"
                        )
            except OSError as audio_folder_exc:
                print(f"⚠️ [AUDIO] Could not inspect Downloads folder: {audio_folder_exc}")
                return None

            if not matches:
                print(
                    f"⚠️ [AUDIO] No narration filename matched project '{title}' "
                    f"after removing spaces and special characters "
                    f"(normalized key: '{normalized_title}')."
                )
                return None

            # Preserve the existing preference for the newest matching audio file.
            return max(matches, key=os.path.getmtime)

        # Mandatory validation gate: every scene requires one readable image and
        # every project requires usable narration audio. Duplicate image copies are
        # collapsed to one best image per entry before count/sequence validation.
        # No partial or silent video is permitted.
        validation_reasons = []
        expected_scene_count = len(entries)
        actual_image_count = len(image_files)
        image_numbers = [item["number"] for item in image_files]

        if actual_image_count != expected_scene_count:
            validation_reasons.append(
                f"Scene-image count mismatch: expected {expected_scene_count} readable entry images "
                f"for {expected_scene_count} scene entries, but found {actual_image_count} in '{source_folder}'."
            )
        expected_image_numbers = list(range(1, expected_scene_count + 1))
        if sorted(image_numbers) != expected_image_numbers:
            missing_numbers = sorted(set(expected_image_numbers) - set(image_numbers))
            unexpected_numbers = sorted(set(image_numbers) - set(expected_image_numbers))
            numbering_details = []
            if missing_numbers:
                numbering_details.append(
                    "missing " + ", ".join(f"entry_{number}" for number in missing_numbers)
                )
            if unexpected_numbers:
                numbering_details.append(
                    "unexpected " + ", ".join(f"entry_{number}" for number in unexpected_numbers)
                )
            validation_reasons.append(
                "Scene-image sequence is incomplete; expected one-based numbering "
                f"entry_1 through entry_{expected_scene_count}"
                + (" (" + "; ".join(numbering_details) + ")." if numbering_details else ".")
            )

        audio_file_path = find_audio_file(project_title)
        audio_duration = None
        if not audio_file_path:
            validation_reasons.append(
                "Required narration audio is missing: no matching non-empty audio file was found "
                f"in the Downloads folder for '{project_title}'."
            )
        else:
            audio_probe = None
            try:
                audio_probe = AudioFileClip(audio_file_path)
                audio_duration = float(audio_probe.duration or 0.0)
                if not math.isfinite(audio_duration) or audio_duration <= 0:
                    raise ValueError("The narration audio has no valid duration.")
                print(
                    f"🎵 [AUDIO] Required narration audio verified: "
                    f"{os.path.basename(audio_file_path)} ({audio_duration:.2f}s)"
                )
            except Exception as audio_exc:
                validation_reasons.append(
                    "Required narration audio is unavailable or unreadable: "
                    f"'{os.path.basename(audio_file_path)}' could not be validated ({audio_exc})."
                )
                audio_file_path = None
                audio_duration = None
            finally:
                if audio_probe is not None:
                    try:
                        audio_probe.close()
                    except Exception:
                        pass

        if validation_reasons:
            return _abort_current_project(" ".join(validation_reasons))

        # This replaces any old aborted marker as soon as the current files pass
        # validation, so a repaired project visibly returns to active processing.
        if not _mark_record_operating(panel_data, project_title):
            print(
                f"❌ [READY-SCRIPT] Could not save the operating status for '{project_title}'. "
                "Stopping this project before rendering to avoid an untracked run."
            )
            return None

        print(
            f"✅ [READY-SCRIPT] Mandatory asset check passed: "
            f"{actual_image_count}/{expected_scene_count} scene images and narration audio are available."
        )
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

        if len(entries) != len(image_files):
            return _abort_current_project(
                f"Scene-image count changed after validation: expected {len(entries)} images, "
                f"but found {len(image_files)}."
            )
        count = len(entries)
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
        if len(prepared) != len(entries):
            return _abort_current_project(
                f"Scene-image preparation was incomplete: expected {len(entries)} prepared images, "
                f"but only {len(prepared)} could be loaded. No video was rendered."
            )
        if not prepared:
            return _abort_current_project("No readable scene images could be prepared for video production.")
        # audio_duration was verified by the mandatory pre-render validation gate.
        if not audio_file_path or not os.path.isfile(audio_file_path) or audio_duration is None or audio_duration <= 0:
            return _abort_current_project(
                "Required narration audio became unavailable after validation; video production was cancelled."
            )
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
            # Fail closed: audio is mandatory. Never write a silent video.
            if not audio_file_path or not os.path.isfile(audio_file_path) or os.path.getsize(audio_file_path) <= 0:
                raise RuntimeError("Required narration audio is missing at render time; silent output is prohibited.")
            audio_clip = AudioFileClip(audio_file_path)
            if not audio_duration or audio_duration <= 0:
                raise RuntimeError("Required narration audio has an invalid duration; video rendering is prohibited.")
            if audio_duration > total_duration:
                try:
                    audio_clip = audio_clip.subclipped(0, total_duration)
                except AttributeError:
                    audio_clip = audio_clip.subclip(0, total_duration)
            elif audio_duration < total_duration:
                try:
                    final_clip = final_clip.subclipped(0, audio_duration)
                except AttributeError:
                    final_clip = final_clip.subclip(0, audio_duration)
                total_duration = audio_duration
            if hasattr(final_clip, "with_audio"):
                final_clip = final_clip.with_audio(audio_clip)
            else:
                final_clip = final_clip.set_audio(audio_clip)
            if getattr(final_clip, "audio", None) is None:
                raise RuntimeError("Narration audio could not be attached; silent output is prohibited.")
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
            if getattr(final_clip, "audio", None) is None:
                raise RuntimeError("Final video has no narration track; refusing to render a silent video.")
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
            if not _mark_record_completed(panel_data, project_title, output_path):
                print(
                    f"⚠️ [READY-SCRIPT] Video was rendered, but completion status could not "
                    f"be saved for '{project_title}'. The output file is safely present."
                )
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
        # skips this newly-created output and selects another project. Validation
        # failures are skipped only for this invocation; a later execution retries
        # them regardless of their persisted status or operation_status text.
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

if __name__ == "__main__":
    video_producer()

    