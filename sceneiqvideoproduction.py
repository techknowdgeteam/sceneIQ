"""SceneIQ standalone video producer.

This module runs video rendering only. Google Flow image generation lives in
sceniqimageproduction.py and is not imported or started here.
"""

import os
import re
import time
import traceback
import multiprocessing

# Shared disk interface used by the two independent producer processes.
# Image production writes completed projects to READY_SCRIPT; video production
# reads READY_SCRIPT and the corresponding project image folders.
PANEL_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\panel.json"
READY_SCRIPT = r"C:\xampp\htdocs\AI automation\scenIQ\ready_script.json"
IMAGES_PATH = r"C:\xampp\htdocs\AI automation\scenIQ\project"
SUBSCRIBE_STICKERS = r"C:\xampp\htdocs\AI automation\scenIQ\subscribe"

def _sceneiq_normalize_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _sceneiq_walk_json(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _sceneiq_walk_json(value)
    elif isinstance(node, list):
        for value in node:
            yield from _sceneiq_walk_json(value)


def _sceneiq_find_field(node, aliases, default=None):
    wanted = {_sceneiq_normalize_key(alias) for alias in aliases}
    for current in _sceneiq_walk_json(node):
        for key, value in current.items():
            if _sceneiq_normalize_key(key) in wanted and value not in (None, "", [], {}):
                return value
    return default


def _sceneiq_find_named_object(node, wanted_name):
    wanted = _sceneiq_normalize_key(wanted_name)
    for current in _sceneiq_walk_json(node):
        for key, value in current.items():
            if _sceneiq_normalize_key(key) == wanted and isinstance(value, dict):
                return value
    return None


def _sceneiq_safe_path_component(value, fallback="Uncategorized"):
    """Return one safe Windows path component while preserving readable names."""
    raw = str(value or "").strip()
    raw = re.sub(r'[<>:"/\\\\|?*]+', "_", raw)
    raw = raw.strip(" .")
    if raw in {"", ".", ".."}:
        return fallback
    return raw[:150]



def _sceneiq_project_title_variants(project_title):
    """Return safe original and normalized folder-name variants for a title."""
    safe_title = _sceneiq_safe_path_component(project_title, "unnamed_project")
    normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", str(project_title or ""))
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_") or "unnamed_project"
    normalized = _sceneiq_safe_path_component(normalized, "unnamed_project")
    return list(dict.fromkeys((safe_title, normalized)))


def _sceneiq_resolve_project_folder_path(
    images_root,
    project_title,
    project_category=None,
    create_if_missing=False,
):
    """Resolve category/title and historical flat/Uncategorized folder layouts.

    New layout:      <root>/<projectcategory>/<project_title>/
    Original layout: <root>/<project_title>/
    Older fallback:  <root>/Uncategorized/<project_title>/

    If category metadata is missing, the flat legacy folder is preferred. If it
    is absent, a unique matching category/title folder may be reused. Ambiguous
    matches are not selected arbitrarily.
    """
    root = os.path.abspath(os.fspath(images_root)) if images_root else ""
    if not root or not project_title:
        return None

    title_variants = _sceneiq_project_title_variants(project_title)
    category_text = str(project_category or "").strip()
    category_component = _sceneiq_safe_path_component(category_text) if category_text else ""

    def existing_child(parent, variant):
        direct = os.path.join(parent, variant)
        if os.path.isdir(direct):
            return direct
        try:
            wanted = _sceneiq_normalize_key(variant)
            for child_name in os.listdir(parent):
                child_path = os.path.join(parent, child_name)
                if os.path.isdir(child_path) and _sceneiq_normalize_key(child_name) == wanted:
                    return child_path
        except OSError:
            pass
        return None

    candidate_parents = []
    if category_component:
        candidate_parents.append(os.path.join(root, category_component))
    candidate_parents.append(root)
    # Also recognize the prior default-category layout, including records that
    # may now carry a category value different from the one used when saved.
    candidate_parents.append(os.path.join(root, "Uncategorized"))
    candidate_parents = list(dict.fromkeys(candidate_parents))

    for parent in candidate_parents:
        if not os.path.isdir(parent):
            continue
        for variant in title_variants:
            match = existing_child(parent, variant)
            if match:
                return os.path.abspath(match)

    # Some category-less READY_SCRIPT records may already have been saved in a
    # categorized folder. Reuse it only if one unique match can be identified.
    if not category_component and os.path.isdir(root):
        category_matches = []
        excluded = {
            "video_producer_runs", "worker_workspaces", "input_images",
            "gui_images", "subscribe", "__pycache__", "uncategorized",
        }
        try:
            for parent_name in os.listdir(root):
                parent_path = os.path.join(root, parent_name)
                if not os.path.isdir(parent_path) or parent_name.casefold() in excluded:
                    continue
                for variant in title_variants:
                    match = existing_child(parent_path, variant)
                    if match:
                        category_matches.append(match)
                        break
        except OSError:
            pass

        unique_matches = []
        seen_matches = set()
        for match in category_matches:
            key = os.path.abspath(match).casefold()
            if key not in seen_matches:
                seen_matches.add(key)
                unique_matches.append(match)

        if len(unique_matches) == 1:
            return os.path.abspath(unique_matches[0])
        if len(unique_matches) > 1:
            image_bearing = []
            for match in unique_matches:
                try:
                    has_entry = any(
                        os.path.isfile(os.path.join(match, filename))
                        and re.fullmatch(
                            r"entry[_-]?\d+\.(png|jpg|jpeg|gif|bmp|webp|tiff)",
                            filename,
                            re.IGNORECASE,
                        )
                        and os.path.getsize(os.path.join(match, filename)) > 0
                        for filename in os.listdir(match)
                    )
                    if has_entry:
                        image_bearing.append(match)
                except OSError:
                    continue
            if len(image_bearing) == 1:
                return os.path.abspath(image_bearing[0])
            print(
                f"⚠️ [PROJECT-PATH] Category-less project '{project_title}' matches "
                f"multiple categorized folders; refusing to choose arbitrarily: {unique_matches}"
            )

    if create_if_missing:
        # Do not invent an Uncategorized directory for records that have no
        # category. They continue using the original flat project path.
        destination_parent = os.path.join(root, category_component) if category_component else root
        destination = os.path.join(destination_parent, title_variants[0])
        os.makedirs(destination, exist_ok=True)
        return os.path.abspath(destination)
    return None


def process_single_video(
    target_project_title=None,
    target_project_category=None,
    ready_script_path=None,
    images_path=None,
    subscribe_stickers_path=None,
    whisper_device=None,
    whisper_compute_type=None,
    video_encoder="libx264",
    encoder_preset=None,
    ffmpeg_threads=None,
    ffmpeg_binary=None,
    worker_id=None,
    worker_lane=None,
    worker_status_path=None,
    worker_log_path=None,
    audio_path=None,
    private_workspace_mode=False,
):
    """
    Render one assigned project while keeping the Windows display and system awake.
    The Windows execution-state request is refreshed on a dedicated worker
    thread every five seconds, including project lookup, imports, transcription,
    image preparation, caption generation, clip assembly, and encoding.
    """
    import os as _awake_os
    import threading as _awake_threading
    import time as _worker_time

    _worker_started_epoch = _worker_time.time()

    def _set_worker_status(
        stage,
        progress=None,
        current=None,
        total=None,
        detail=None,
        status="running",
    ):
        if not worker_status_path:
            return
        payload = {
            "worker_id": worker_id or "worker",
            "lane": (worker_lane or "unknown").upper(),
            "pid": _awake_os.getpid(),
            "project_title": target_project_title or "Resolving project",
            "status": status,
            "stage": str(stage or "Working"),
            "progress": progress,
            "current": current,
            "total": total,
            "detail": str(detail or ""),
            "started_at": _worker_started_epoch,
            "updated_at": _worker_time.time(),
            "encoder": video_encoder,
            "whisper_device": whisper_device or "cpu",
            "whisper_compute_type": whisper_compute_type or "int8",
            "log_path": worker_log_path,
            "status_path": worker_status_path,
        }
        try:
            _video_producer_write_worker_status(worker_status_path, payload)
        except Exception as status_exc:
            # Monitoring must never interrupt video production.
            print(f"⚠️ [WORKER-STATUS] Could not update status file: {status_exc}")

    # Resolve paths in the parent before spawning. Passing these values to each
    # worker makes this function safe under Windows' multiprocessing "spawn" mode.
    _ready_script_path = ready_script_path or globals().get("READY_SCRIPT")
    _images_root_path = images_path or globals().get("IMAGES_PATH")
    _subscribe_stickers_root_path = (
        subscribe_stickers_path
        if (private_workspace_mode or subscribe_stickers_path is not None)
        else globals().get("SUBSCRIBE_STICKERS")
    )
    if _ready_script_path:
        _ready_script_path = _awake_os.fspath(_ready_script_path)
    if _images_root_path:
        _images_root_path = _awake_os.fspath(_images_root_path)
    if _subscribe_stickers_root_path:
        _subscribe_stickers_root_path = _awake_os.fspath(_subscribe_stickers_root_path)

    # Each worker has its own environment, so CPU and GPU lanes can select
    # different Faster-Whisper devices without changing another worker's settings.
    if whisper_device:
        _awake_os.environ["WHISPER_DEVICE"] = str(whisper_device)
    if whisper_compute_type:
        _awake_os.environ["WHISPER_COMPUTE_TYPE"] = str(whisper_compute_type)
    if ffmpeg_binary:
        _awake_os.environ["FFMPEG_BINARY"] = _awake_os.fspath(ffmpeg_binary)

    video_encoder = str(video_encoder or "libx264").strip().lower()
    if video_encoder not in {"libx264", "h264_nvenc"}:
        print(f"⚠️ [ENCODER] Unsupported encoder '{video_encoder}'; using libx264")
        video_encoder = "libx264"
    if ffmpeg_threads is not None:
        try:
            ffmpeg_threads = max(1, int(ffmpeg_threads))
        except (TypeError, ValueError):
            ffmpeg_threads = None

    _set_worker_status(
        "Starting worker",
        detail=f"PID {_awake_os.getpid()} | lane={(worker_lane or 'unknown').upper()} | encoder={video_encoder}",
    )

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

    def _run_video_producer():
        """
        Assemble entry_N images into a narrated video using AI-directed transitions,
        keyframes, per-scene video effects, dynamic instructional interstitials,
        configurable caption animations, and subscribe stickers.
        - transition_to_next controls each outgoing scene boundary.
        - keyframes controls each scene's camera-motion sequence.
        - video_effects applies context-selected effects to footage only, not captions.
        - instructional_overlay / legacy stage-step-level-example fields control
          a full-screen background, timed heading entrance, optional emphasis/hold,
          and optional exit animation. The project overlay palette is locked globally.
        - Captions always use the original producer's ASR-synchronized single-row typewriter style.
          Per-scene caption_animation/caption_effect styling metadata is ignored.
        - A single caption renderer is used per frame. ASR words are de-duplicated
          only when duplicate word timestamps overlap, preventing double captions.
        - Instructional-heading words are omitted from ordinary captions while the
          heading is displayed. Overlay ASR works even when ordinary captions are off.
        - AI-provided identifiers and descriptive keywords are normalized safely.
        - Like/subscribe stickers retain the existing 50% display scale.
        Captions, overlays, and effects are rendered frame-by-frame; source images remain unchanged.
        Keeps the existing queue, project lookup, script timing, audio matching,
        image normalization, output backup, and sequential clip assembly.
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
        from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps, ImageEnhance, ImageFilter, ImageChops
        import numpy as np
        # Import from MoviePy's public package namespace (MoviePy 2.x).
        try:
            from moviepy import VideoClip, AudioFileClip, concatenate_videoclips
        except ImportError as exc:
            print(
                "❌ MoviePy 2.x imports failed. Install/upgrade MoviePy with: "
                "python -m pip install --upgrade moviepy"
            )
            print(f"   Import details: {exc}")
            return None
        # READY_SCRIPT is the queue. Deduplicate by normalized project title,
        # then process the first project whose final video does not already exist.
        # Existing completed videos are skipped; no project is overwritten.
        if not _images_root_path or not os.path.isdir(_images_root_path):
            print(f"❌ IMAGES_PATH missing or unavailable: {_images_root_path}")
            return None
        if not _ready_script_path or not os.path.exists(_ready_script_path):
            print(f"❌ READY_SCRIPT missing or unavailable: {_ready_script_path}")
            return None
        def normalize_project_title(name):
            normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", str(name or ""))
            normalized = re.sub(r"\s+", "_", normalized)
            normalized = re.sub(r"_+", "_", normalized).strip("_")
            return normalized or "unnamed_project"
        try:
            with open(_ready_script_path, "r", encoding="utf-8") as file:
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
            # Read title fields at this record level only. The recursive project walk
            # below then discovers sibling projects independently instead of treating
            # their common wrapper as one project.
            if not isinstance(node, dict):
                return None
            value = None
            for key, candidate_value in node.items():
                if _normalise_key(key) in {"projecttitle", "projectname"} and candidate_value not in (None, "", [], {}):
                    value = candidate_value
                    break
            if isinstance(value, dict):
                for key, candidate_value in value.items():
                    if _normalise_key(key) in {"projecttitle", "title", "name"} and candidate_value not in (None, "", [], {}):
                        value = candidate_value
                        break
            if value is None:
                automation = next(
                    (candidate_value for key, candidate_value in node.items()
                     if _normalise_key(key) == "automation" and isinstance(candidate_value, dict)),
                    None,
                )
                if isinstance(automation, dict):
                    value = next(
                        (candidate_value for key, candidate_value in automation.items()
                         if _normalise_key(key) in {"projecttitle", "projectname"}
                         and candidate_value not in (None, "", [], {})),
                        None,
                    )
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
                                "narration", "voiceover", "spoken_text",
                                "instructionaloverlay", "stageoverlay", "videoeffects",
                                "captionanimation"
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
                record_category = _find_field(
                    record, ("projectcategory", "project_category", "projectCategory")
                ) or "Uncategorized"
                key = (
                    str(record_category).casefold(),
                    normalize_project_title(title).casefold(),
                )
                if key not in seen:
                    seen.add(key)
                    unique.append((record, title, script))
                else:
                    print(
                        f"⏭️ [READY-SCRIPT] Duplicate project skipped: "
                        f"{record_category}/{title}"
                    )
            return unique
        unique_projects = _collect_project_records(ready_data)
        if not unique_projects:
            print("❌ READY_SCRIPT contains no discoverable project title with a valid script.")
            return None
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
        def _resolve_project_folder(title, category=None):
            """Resolve categorized, legacy-flat, or prior Uncategorized folders."""
            return _sceneiq_resolve_project_folder_path(
                _images_root_path,
                title,
                project_category=category,
                create_if_missing=False,
            )
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
            if target_project_title and (
                normalize_project_title(candidate_title).casefold()
                != normalize_project_title(target_project_title).casefold()
            ):
                continue
            candidate_category = _find_field(candidate, ("projectcategory", "project_category", "projectCategory"))
            if target_project_category and candidate_category and (
                _sceneiq_normalize_key(candidate_category)
                != _sceneiq_normalize_key(target_project_category)
            ):
                continue
            candidate_folder = _resolve_project_folder(candidate_title, candidate_category)
            if not candidate_folder:
                print(
                    f"⏭️ [READY-SCRIPT] Could not safely resolve a unique image folder "
                    f"for '{candidate_title}' (category={candidate_category!r}); skipping."
                )
                continue
            normalized_candidate_title = normalize_project_title(candidate_title)
            candidate_edited_folder = os.path.join(candidate_folder, "edited")
            expected_video = os.path.join(
                candidate_edited_folder, f"{normalized_candidate_title}.mp4"
            )
            # Also recognize a previously rendered file in a legacy normalized folder.
            legacy_folder = os.path.join(_images_root_path, normalized_candidate_title)
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
                print(
                    f"⚠️ [READY-SCRIPT] No entry images found for '{candidate_title}'. "
                    f"Checked project folder: {candidate_folder}"
                )
                continue
            panel_data = candidate
            project_title = candidate_title
            selected_script_data = candidate_script_data
            project_folder = candidate_folder
            source_folder = found_image_folder
            _set_worker_status(
                "Project assigned",
                progress=0,
                detail=f"Project folder: {project_folder}",
            )
            print(f"🎯 [PROCESS-SINGLE] Assigned project: '{project_title}'")
            print(f"📂 [READY-SCRIPT] Resolved project folder: {project_folder}")
            print(f"🖼️ [READY-SCRIPT] Resolved entry-image folder: {source_folder}")
            break
        if panel_data is None or not project_title:
            print(
                "✅ [READY-SCRIPT] No unfinished projects remain "
                "(or no eligible project has images and script data)."
            )
            return None
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
            print(f"❌ [READY-SCRIPT] Resolved project folder is unavailable: {project_folder}")
            return None
        if not source_folder or not _has_entry_images(source_folder):
            print(f"❌ [READY-SCRIPT] Resolved image folder has no valid entry_N images: {source_folder}")
            return None
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
                "instructional_overlay",
                "stage_overlay",
                "video_effects",
                "video_effect",
                "caption_animation",
                "caption_effect",
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
            print("❌ No scene entries found in the discovered project script (new and legacy formats were checked).")
            return None
        def _entry_has_overlay_metadata(entry):
            if not isinstance(entry, dict):
                return False
            for key, value in entry.items():
                if re.fullmatch(r"(?:stage|step|level|example|chapter)_.+_involved", str(key), re.IGNORECASE):
                    if value is True or str(value).strip().casefold() in {"true", "yes", "1", "on", "enabled"}:
                        return True
            for nested_key in ("instructional_overlay", "stage_overlay"):
                nested = entry.get(nested_key)
                if isinstance(nested, dict) and (nested.get("enabled") is not False and str(nested.get("enabled", "true")).strip().casefold() not in {"false", "no", "0", "off", "disabled"}):
                    return True
                if isinstance(nested, list) and any(
                    isinstance(item, dict) and (item.get("enabled") is not False and str(item.get("enabled", "true")).strip().casefold() not in {"false", "no", "0", "off", "disabled"})
                    for item in nested
                ):
                    return True
            return False

        has_overlay_metadata = any(_entry_has_overlay_metadata(entry) for entry in entries)
        if has_overlay_metadata:
            print("🎯 [INSTRUCTIONAL-OVERLAY] Dynamic Stage/Step/Level/Example/Chapter metadata detected; speech-timed overlay processing is enabled")
        def get_sorted_images(folder_path):
            items = []
            for filename in os.listdir(folder_path):
                match = re.match(r"entry[_-]?(\d+)", filename, re.IGNORECASE)
                if not match or os.path.splitext(filename)[1].lower() not in {
                    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"
                }:
                    continue
                items.append({
                    "number": int(match.group(1)),
                    "filename": filename,
                    "path": os.path.join(folder_path, filename),
                })
            return sorted(items, key=lambda item: item["number"])
        image_files = get_sorted_images(source_folder)
        if not image_files:
            print("⏭️ [VIDEO-PREFLIGHT] No usable entry images found; skipping this project.")
            return None
        expected_image_numbers = set(range(1, len(entries) + 1))
        available_image_numbers = {int(item["number"]) for item in image_files}
        missing_image_numbers = sorted(expected_image_numbers - available_image_numbers)
        invalid_image_files = [
            item["filename"] for item in image_files
            if not os.path.isfile(item["path"]) or os.path.getsize(item["path"]) <= 0
        ]
        if missing_image_numbers or invalid_image_files:
            print(
                "⏭️ [VIDEO-PREFLIGHT] Missing/invalid scene image(s); skipping project. "
                f"Missing entry numbers: {missing_image_numbers or 'none'}; "
                f"invalid files: {invalid_image_files or 'none'}"
            )
            return None
        def find_audio_file(title):
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(downloads):
                return None
            audio_exts = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma")
            matches = [
                os.path.join(downloads, name)
                for name in os.listdir(downloads)
                if name.lower().endswith(audio_exts) and title.lower() in name.lower()
            ]
            return max(matches, key=os.path.getmtime) if matches else None
        audio_file_path = (
            os.path.abspath(os.fspath(audio_path))
            if audio_path and os.path.isfile(audio_path)
            else (None if private_workspace_mode else find_audio_file(project_title))
        )
        if not audio_file_path or not os.path.isfile(audio_file_path) or os.path.getsize(audio_file_path) <= 0:
            print(
                f"⏭️ [VIDEO-PREFLIGHT] No valid narration audio exists for '{project_title}'. "
                "Skipping this project and allowing the queue to continue."
            )
            return None
        print(f"🎵 Found verified narration audio: {os.path.basename(audio_file_path)}")
        import sys
        caption_progress_state = {"started": False, "finished": False, "last_percent": -1}

        def _update_caption_progress(percent, finish=False):
            if not caption_progress_state["started"] or caption_progress_state["finished"]:
                return
            percent = max(0, min(100, int(round(float(percent)))))
            percent = max(caption_progress_state["last_percent"], percent)
            _set_worker_status(
                "Planning captions and overlays",
                progress=percent,
                current=percent,
                total=100,
                detail="Generating timestamp-synchronized caption rows",
            )
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
            _set_worker_status(
                "Speech recognition",
                detail="Running Faster-Whisper word-timestamp transcription",
            )
            # One ASR pass supplies word-level timing for captions and for dynamic
            # Stage/Step/Level/Example/Chapter overlays. Overlay timing is still available
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
                        cpu_threads=max(1, min(4, int(ffmpeg_threads or 2))),
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
                    print("⚠️ [INSTRUCTIONAL-OVERLAY] Cannot synchronize headings without Faster-Whisper; continuing without spoken overlays")
                except Exception as exc:
                    _close_caption_progress()
                    print(f"❌ [ASR] Speech recognition failed: {exc}")
                    traceback.print_exc()
                    if include_captions:
                        return None
                    audio_words = []
                    print("⚠️ [INSTRUCTIONAL-OVERLAY] ASR failed; continuing without spoken-heading overlays")
            else:
                audio_words = []
                print("⚠️ [ASR] No audio file found; captions and speech-timed Stage/Step/Level/Example/Chapter overlays cannot be synchronized.")
        else:
            audio_words = []
            print("⏭️ [CAPTIONS] Disabled and no dynamic heading metadata exists; skipping Faster-Whisper")
        def _deduplicate_overlapping_asr_words(words):
            """Remove only exact duplicate ASR tokens with overlapping timestamps.

            Genuine repeated speech (for example, “no, no”) remains because its
            timestamps are distinct. This prevents an overlapping ASR duplicate
            from being painted twice in the same caption stream.
            """
            if not words:
                return []
            ordered = sorted(
                [dict(word) for word in words if isinstance(word, dict)],
                key=lambda item: (float(item.get("start", 0.0)), float(item.get("end", 0.0))),
            )
            cleaned = []
            for word in ordered:
                token = re.sub(r"[^a-z0-9']+", "", str(word.get("word", "")).casefold())
                try:
                    start = float(word.get("start", 0.0))
                    end = float(word.get("end", start + 0.02))
                except (TypeError, ValueError):
                    cleaned.append(word)
                    continue
                duplicate_index = None
                for index in range(max(0, len(cleaned) - 3), len(cleaned)):
                    previous = cleaned[index]
                    previous_token = re.sub(
                        r"[^a-z0-9']+", "", str(previous.get("word", "")).casefold()
                    )
                    try:
                        previous_start = float(previous.get("start", 0.0))
                        previous_end = float(previous.get("end", previous_start + 0.02))
                    except (TypeError, ValueError):
                        continue
                    overlap = min(end, previous_end) - max(start, previous_start)
                    if token and token == previous_token and overlap > 0:
                        duplicate_index = index
                        break
                if duplicate_index is not None:
                    previous = cleaned[duplicate_index]
                    previous["start"] = min(float(previous.get("start", start)), start)
                    previous["end"] = max(float(previous.get("end", end)), end)
                    continue
                cleaned.append(word)
            return cleaned

        audio_words = _deduplicate_overlapping_asr_words(audio_words)
        if audio_words:
            print(f"🧹 [ASR] Caption timeline contains {len(audio_words)} unique, timestamped word event(s)")

        def discover_transparent_subscribe_stickers():
            """Return only image files that contain a real transparent background."""
            sticker_folder = (
                _subscribe_stickers_root_path
                if private_workspace_mode
                else (_subscribe_stickers_root_path or globals().get("SUBSCRIBE_STICKERS"))
            )
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
            """Draw a persistent-palette interstitial with real entrance/emphasis/exit motion."""
            if not overlay_events:
                return frame_image
            now = max(0.0, float(global_time))
            active_event = next((event for event in overlay_events
                                 if float(event.get("start_time", 0.0)) <= now < float(event.get("end_time", 0.0))), None)
            if active_event is None:
                return frame_image

            width, height = frame_image.size
            background_color = _valid_color(active_event.get("background", "#FFFFFF"), "#FFFFFF")
            text_color = _valid_color(active_event.get("text_color", "#111111"), "#111111")
            background_rgb = ImageColor.getrgb(background_color)[:3]
            text_rgb = ImageColor.getrgb(text_color)[:3]
            luminance_bg = 0.2126 * background_rgb[0] + 0.7152 * background_rgb[1] + 0.0722 * background_rgb[2]
            luminance_text = 0.2126 * text_rgb[0] + 0.7152 * text_rgb[1] + 0.0722 * text_rgb[2]
            if abs(luminance_bg - luminance_text) < 95:
                text_rgb = (17, 17, 17) if luminance_bg > 128 else (255, 255, 255)

            # The project-wide background appears first during the configured pre-roll.
            overlay = Image.new("RGB", (width, height), background_rgb)
            text_start = float(active_event.get("text_start_time", active_event.get("start_time", now)))
            if now < text_start:
                return overlay

            display_text = str(active_event.get("display_text") or "Stage").strip()
            if not display_text:
                return overlay
            font_size = max(64, int(min(width * 0.115, height * 0.22)))
            font = load_font(font_size)
            measure = ImageDraw.Draw(overlay)
            max_text_width = int(width * 0.88)
            max_text_height = int(height * 0.34)
            bbox = measure.textbbox((0, 0), display_text, font=font, stroke_width=2)
            while font_size > 38 and ((bbox[2] - bbox[0]) > max_text_width or (bbox[3] - bbox[1]) > max_text_height):
                font_size -= 3
                font = load_font(font_size)
                bbox = measure.textbbox((0, 0), display_text, font=font, stroke_width=2)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            target_x = int((width - text_width) / 2 - bbox[0])
            target_y = int((height - text_height) / 2 - bbox[1])

            entrance = max(0.05, float(active_event.get("entrance_duration_seconds", 0.38)))
            entrance_progress = max(0.0, min(1.0, (now - text_start) / entrance))
            eased = entrance_progress * entrance_progress * (3.0 - 2.0 * entrance_progress)
            entrance_effect = _normalise_metadata_token(active_event.get("entrance_effect", "slam_in"))
            if entrance_effect in {"typewriter", "typing"}:
                reveal = max(1, min(len(display_text), int(math.ceil(len(display_text) * eased))))
                visible_text = display_text[:reveal]
                display_bbox = measure.textbbox((0, 0), visible_text, font=font, stroke_width=2)
                display_width = display_bbox[2] - display_bbox[0]
                draw_x = int((width - display_width) / 2 - display_bbox[0])
                draw_y = int((height - (display_bbox[3] - display_bbox[1])) / 2 - display_bbox[1])
                scale = 1.0
                alpha = 255
            else:
                visible_text = display_text
                scale = 1.0
                alpha = 255
                draw_x, draw_y = target_x, target_y
                if entrance_effect in {"fade_in", "fade", "dissolve_in"}:
                    alpha = int(255 * eased)
                elif entrance_effect in {"fly_in_left", "slide_in_left", "throw_from_left"}:
                    draw_x -= int((1.0 - eased) * width * 0.38)
                elif entrance_effect in {"fly_in_right", "slide_in_right", "throw_from_right"}:
                    draw_x += int((1.0 - eased) * width * 0.38)
                elif entrance_effect in {"drop_in", "throw_down", "slam_in", "throw_in", "pop_in"}:
                    scale = 0.50 + 0.50 * eased
                    draw_y -= int((1.0 - eased) * height * 0.10)
                elif entrance_effect in {"slide_up", "rise_in"}:
                    draw_y += int((1.0 - eased) * height * 0.08)
                elif entrance_effect in {"none", "instant", "appear"}:
                    pass
                else:
                    # Unknown wording should remain intelligible: use a clean fade.
                    alpha = int(255 * eased)

            emphasis_effect = _normalise_metadata_token(active_event.get("emphasis_effect", "none"))
            emphasis_duration = max(0.0, float(active_event.get("emphasis_duration_seconds", 0.30) or 0.0))
            emphasis_start = text_start + entrance
            if emphasis_effect in {"shake", "tremble", "vibrate", "text_shake"} and emphasis_duration > 0:
                emphasis_progress = now - emphasis_start
                if 0 <= emphasis_progress <= emphasis_duration:
                    amplitude = max(1, int(8 * (1.0 - emphasis_progress / emphasis_duration)))
                    draw_x += int(math.sin(emphasis_progress * 68.0) * amplitude)
                    draw_y += int(math.cos(emphasis_progress * 57.0) * amplitude * 0.45)

            hold_end = float(active_event.get("hold_end_time", active_event.get("end_time", now)))
            exit_effect = _normalise_metadata_token(active_event.get("exit_effect", "fade_out"))
            exit_duration = max(0.0, float(active_event.get("exit_duration_seconds", 0.24) or 0.0))
            if now >= hold_end and exit_duration > 0 and not active_event.get("keep_until_scene_end", False):
                exit_progress = max(0.0, min(1.0, (now - hold_end) / exit_duration))
                if exit_effect in {"fade_out", "fade", "dissolve_out"}:
                    alpha = int(alpha * (1.0 - exit_progress))
                elif exit_effect in {"shrink_out", "scale_down"}:
                    scale *= max(0.05, 1.0 - exit_progress)
                elif exit_effect in {"fly_out_up", "slide_out_up"}:
                    draw_y -= int(exit_progress * height * 0.10)
                elif exit_effect in {"fly_out_left", "slide_out_left"}:
                    draw_x -= int(exit_progress * width * 0.20)
                elif exit_effect in {"fly_out_right", "slide_out_right"}:
                    draw_x += int(exit_progress * width * 0.20)
                elif exit_effect in {"none", "hold", "stay"}:
                    pass
                else:
                    alpha = int(alpha * (1.0 - exit_progress))

            if scale != 1.0 and visible_text == display_text:
                text_layer = Image.new("RGBA", (max(1, text_width + 16), max(1, text_height + 16)), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                outline_rgb = (0, 0, 0) if luminance_bg > 128 else (255, 255, 255)
                text_draw.text((8 - bbox[0], 8 - bbox[1]), visible_text, font=font,
                               fill=(*text_rgb, alpha), stroke_width=2, stroke_fill=(*outline_rgb, alpha))
                resized = text_layer.resize((max(1, int(text_layer.width * scale)), max(1, int(text_layer.height * scale))), Image.Resampling.LANCZOS)
                x = int(target_x + (text_width - resized.width) / 2)
                y = int(target_y + (text_height - resized.height) / 2)
                overlay_rgba = overlay.convert("RGBA")
                overlay_rgba.alpha_composite(resized, (x, y))
                return overlay_rgba.convert("RGB")

            outline_rgb = (0, 0, 0) if luminance_bg > 128 else (255, 255, 255)
            text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)
            draw.text((draw_x, draw_y), visible_text, font=font, fill=(*text_rgb, alpha),
                      stroke_width=2, stroke_fill=(*outline_rgb, alpha))
            overlay_rgba = overlay.convert("RGBA")
            overlay_rgba.alpha_composite(text_layer)
            return overlay_rgba.convert("RGB")

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
            ASR words used by a centered Stage/Step/Level/Example/Chapter overlay are excluded
            so the same heading is not duplicated in the bottom captions.
            """
            suppressed_word_indices = set(suppressed_word_indices or ())
            scene_starts_for_caption = []
            scene_cursor_for_caption = 0.0
            for item in prepared_items:
                scene_starts_for_caption.append(scene_cursor_for_caption)
                scene_cursor_for_caption += max(0.001, float(item.get("duration", 0.1)))
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

                scene_for_row = 0
                for candidate_index, candidate_start in enumerate(scene_starts_for_caption):
                    if candidate_start <= row_start:
                        scene_for_row = candidate_index
                    else:
                        break
                scene_animation = (
                    prepared_items[scene_for_row].get("caption_animation")
                    if scene_for_row < len(prepared_items) else None
                ) or {"type": "typewriter"}
                row_end = next_row_start if has_following_row else max(
                    max((token["end"] for token in tokens), default=row_start) + 0.35,
                    row_start + 0.25,
                )
                events.append({
                    "row_id": row_id,
                    "start_time": row_start,
                    "end_time": max(row_start + 0.05, row_end),
                    "slot_duration": slot_duration,
                    "text": full_text,
                    "char_times": char_times,
                    "anchor_width": max(row_widths[:row_id + 1], default=1),
                    "animation": dict(scene_animation),
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
                r"\b(?:stage|step|level|example|chapter)\s*(?:(?:no\.?|number)\s*)?#?\s*(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
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

        def _valid_color(value, fallback):
            """Return a valid Pillow color string without limiting colors to B/W."""
            try:
                ImageColor.getrgb(str(value).strip())
                return str(value).strip()
            except Exception:
                return fallback

        def extract_stage_overlay_specs(scene_entry):
            """Read the new nested overlay schema and legacy dynamic flat fields."""
            if not isinstance(scene_entry, dict):
                return []
            specs = []

            def add_spec(category, identifier, raw_spec):
                raw_spec = raw_spec if isinstance(raw_spec, dict) else {}
                category = _normalise_metadata_token(category) or "stage"
                identifier = _normalise_metadata_token(identifier or raw_spec.get("number") or "1")
                display_text = str(
                    raw_spec.get("display_text")
                    or raw_spec.get("heading")
                    or raw_spec.get("title")
                    or f"{category.title()} {identifier.replace('_', ' ').title()}"
                ).strip()
                specs.append({
                    "category": category,
                    "identifier": identifier,
                    "display_text": display_text,
                    "background": str(
                        raw_spec.get("background_color")
                        or raw_spec.get("background")
                        or "white"
                    ).strip(),
                    "text_color": str(
                        raw_spec.get("text_color") or "#111111"
                    ).strip(),
                    "pre_roll_seconds": raw_spec.get("pre_roll_seconds", 0.65),
                    "entrance_effect": raw_spec.get("entrance_effect", "slam_in"),
                    "entrance_duration_seconds": raw_spec.get("entrance_duration_seconds", 0.38),
                    "emphasis_effect": raw_spec.get("emphasis_effect", "none"),
                    "emphasis_duration_seconds": raw_spec.get("emphasis_duration_seconds", 0.30),
                    "hold_seconds": raw_spec.get("hold_seconds", 0.65),
                    "exit_effect": raw_spec.get("exit_effect", "fade_out"),
                    "exit_duration_seconds": raw_spec.get("exit_duration_seconds", 0.24),
                    "keep_until_scene_end": _metadata_bool(
                        raw_spec.get("keep_until_scene_end"), default=False
                    ),
                })

            # Preferred schema: one nested object per scene. A list is accepted if
            # a scene intentionally needs more than one distinct overlay.
            nested = scene_entry.get("instructional_overlay")
            if nested is None:
                nested = scene_entry.get("stage_overlay")
            if isinstance(nested, dict):
                if _metadata_bool(nested.get("enabled", True), default=True):
                    add_spec(
                        nested.get("category", "stage"),
                        nested.get("identifier", nested.get("number", "1")),
                        nested,
                    )
            elif isinstance(nested, list):
                for raw_spec in nested:
                    if isinstance(raw_spec, dict) and _metadata_bool(
                        raw_spec.get("enabled", True), default=True
                    ):
                        add_spec(
                            raw_spec.get("category", "stage"),
                            raw_spec.get("identifier", raw_spec.get("number", "1")),
                            raw_spec,
                        )

            # Backward compatibility: {category}_{identifier}_* scene fields.
            for field_name, involved_value in scene_entry.items():
                match = re.fullmatch(
                    r"(stage|step|level|example|chapter)_(.+)_involved",
                    str(field_name),
                    re.IGNORECASE,
                )
                if not match or not _metadata_bool(involved_value, default=False):
                    continue
                category = match.group(1).casefold()
                identifier = match.group(2).casefold()
                prefix = f"{category}_{identifier}_"
                raw_spec = {
                    "display_text": scene_entry.get(prefix + "display_text"),
                    "background_color": scene_entry.get(prefix + "background"),
                    "text_color": scene_entry.get(prefix + "text_color"),
                    "pre_roll_seconds": scene_entry.get(prefix + "pre_roll_seconds", 0.65),
                    "entrance_effect": scene_entry.get(prefix + "entrance_effect", "slam_in"),
                    "entrance_duration_seconds": scene_entry.get(prefix + "entrance_duration_seconds", 0.38),
                    "emphasis_effect": scene_entry.get(prefix + "emphasis_effect", "none"),
                    "emphasis_duration_seconds": scene_entry.get(prefix + "emphasis_duration_seconds", 0.30),
                    "hold_seconds": scene_entry.get(prefix + "hold_seconds", 0.65),
                    "exit_effect": scene_entry.get(prefix + "exit_effect", "fade_out"),
                    "exit_duration_seconds": scene_entry.get(prefix + "exit_duration_seconds", 0.24),
                    "keep_until_scene_end": scene_entry.get(prefix + "keep_until_scene_end", False),
                }
                add_spec(category, identifier, raw_spec)

            # Avoid duplicate nested + legacy declaration of the same heading.
            unique = []
            seen = set()
            for spec in specs:
                key = (spec["category"], spec["identifier"], spec["display_text"].casefold())
                if key not in seen:
                    seen.add(key)
                    unique.append(spec)
            return unique

        def extract_caption_animation(scene_entry, root_defaults=None):
            """Lock every scene to the original producer's ASR-timed typewriter caption."""
            return {
                "enabled": True,
                "type": "typewriter",
                "legacy_layout": True,
            }

        _VIDEO_EFFECT_ALIASES = {
            "black_and_white": "black_white", "blackwhite": "black_white",
            "monochrome": "black_white", "b_w": "black_white", "bw": "black_white",
            "old_footage": "archival", "past_footage": "archival", "archive": "archival",
            "sepia_tone": "sepia", "vhs_glitch": "glitch", "digital_glitch": "glitch",
            "camera_shake": "shake", "handheld_shake": "shake", "tremble": "shake",
            "trembling": "shake", "flicker_light": "flicker", "film_noise": "film_grain",
            "grain": "film_grain", "cctv_footage": "cctv", "surveillance": "cctv",
            "soft_focus": "blur", "vignette_dark_edges": "vignette",
        }
        _SUPPORTED_VIDEO_EFFECTS = {
            "black_white", "sepia", "vintage", "archival", "cctv", "film_grain",
            "scanlines", "vignette", "glitch", "shake", "flicker", "blur",
            "high_contrast", "desaturate", "cold_tone", "warm_tone",
        }

        def extract_video_effect_plan(scene_entry):
            """Read explicit per-scene video effects. Missing metadata means no effect."""
            raw = scene_entry.get("video_effects") if isinstance(scene_entry, dict) else None
            if raw is None and isinstance(scene_entry, dict):
                raw = scene_entry.get("video_effect")
            if isinstance(raw, str):
                raw = {"effects": [raw]}
            elif isinstance(raw, list):
                raw = {"effects": raw}
            if not isinstance(raw, dict):
                return {"enabled": False, "effects": [], "start_offset_seconds": 0.0, "duration_seconds": None}
            enabled = _metadata_bool(raw.get("enabled"), default=bool(raw.get("effects") or raw.get("effect")))
            raw_effects = raw.get("effects", raw.get("effect", raw.get("keywords", [])))
            if isinstance(raw_effects, str):
                raw_effects = [raw_effects]
            if not isinstance(raw_effects, list):
                raw_effects = []
            effects = []
            for item in raw_effects:
                if isinstance(item, dict):
                    token = _normalise_metadata_token(item.get("type") or item.get("name") or item.get("effect"))
                    intensity = item.get("intensity", raw.get("intensity", 0.5))
                else:
                    token = _normalise_metadata_token(item)
                    intensity = raw.get("intensity", 0.5)
                token = _VIDEO_EFFECT_ALIASES.get(token, token)
                if token not in _SUPPORTED_VIDEO_EFFECTS:
                    print(f"⚠️ [VIDEO-EFFECTS] Ignoring unsupported effect keyword: {token or item}")
                    continue
                try:
                    intensity = max(0.0, min(1.0, float(intensity)))
                except (TypeError, ValueError):
                    intensity = 0.5
                effects.append({"type": token, "intensity": intensity})
            try:
                start_offset = max(0.0, float(raw.get("start_offset_seconds", 0.0) or 0.0))
            except (TypeError, ValueError):
                start_offset = 0.0
            try:
                effect_duration = (
                    max(0.0, float(raw.get("duration_seconds")))
                    if raw.get("duration_seconds") is not None else None
                )
            except (TypeError, ValueError):
                effect_duration = None
            return {
                "enabled": bool(enabled and effects),
                "effects": effects,
                "start_offset_seconds": start_offset,
                "duration_seconds": effect_duration,
            }

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
            """Match spoken headings and schedule background pre-roll, entrance, hold and exit."""
            suppressed_word_indices = set()
            total_events = 0
            normalized_words = [_spoken_token(word.get("word", "")) for word in recognized_words]
            for scene_index, item in enumerate(prepared_items):
                specs = item.get("stage_overlay_specs", [])
                item_events = []
                if not specs:
                    item["stage_overlay_events"] = item_events
                    continue
                scene_start = float(scene_start_offsets[scene_index])
                scene_end = scene_start + float(item.get("duration", 0.0))
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
                            f"⚠️ [INSTRUCTIONAL-OVERLAY] Scene {scene_index + 1}: "
                            f"could not match spoken '{spec['display_text']}' to ASR words; overlay skipped"
                        )
                        continue
                    first_index, phrase_len, spoken_start, spoken_end = matched
                    try:
                        pre_roll = max(0.0, min(3.0, float(spec.get("pre_roll_seconds", 0.65))))
                    except (TypeError, ValueError):
                        pre_roll = 0.65
                    try:
                        hold_seconds = max(0.0, min(8.0, float(spec.get("hold_seconds", 0.65))))
                    except (TypeError, ValueError):
                        hold_seconds = 0.65
                    try:
                        entrance_duration = max(0.05, min(2.0, float(spec.get("entrance_duration_seconds", 0.38))))
                    except (TypeError, ValueError):
                        entrance_duration = 0.38
                    try:
                        exit_duration = max(0.0, min(2.0, float(spec.get("exit_duration_seconds", 0.24))))
                    except (TypeError, ValueError):
                        exit_duration = 0.24
                    overlay_start = max(scene_start, spoken_start - pre_roll)
                    text_start = max(scene_start, spoken_start)
                    title_hold_end = min(scene_end, spoken_end + hold_seconds)
                    keep_until_scene_end = bool(spec.get("keep_until_scene_end"))
                    overlay_end = scene_end if keep_until_scene_end else min(
                        scene_end, title_hold_end + exit_duration
                    )
                    if overlay_end <= overlay_start:
                        continue
                    word_indices = list(range(first_index, first_index + phrase_len))
                    suppressed_word_indices.update(word_indices)
                    item_events.append({
                        **spec,
                        "start_time": overlay_start,
                        "text_start_time": text_start,
                        "spoken_start_time": spoken_start,
                        "spoken_end_time": spoken_end,
                        "hold_end_time": title_hold_end,
                        "end_time": overlay_end,
                        "entrance_duration_seconds": entrance_duration,
                        "exit_duration_seconds": exit_duration,
                        "word_indices": word_indices,
                    })
                    total_events += 1
                    print(
                        f"🎯 [INSTRUCTIONAL-OVERLAY] Scene {scene_index + 1}: '{spec['display_text']}' "
                        f"background ready at {overlay_start:.2f}s; heading begins at {text_start:.2f}s; "
                        f"holds through {title_hold_end:.2f}s; exits by {overlay_end:.2f}s"
                    )
                item_events.sort(key=lambda event: event["start_time"])
                for event_index in range(len(item_events) - 1):
                    next_start = item_events[event_index + 1]["start_time"]
                    if item_events[event_index]["end_time"] > next_start:
                        item_events[event_index]["end_time"] = next_start
                item["stage_overlay_events"] = item_events
            print(
                f"✅ [INSTRUCTIONAL-OVERLAY] Scheduled {total_events} heading overlay(s); "
                f"{len(suppressed_word_indices)} heading word(s) excluded from bottom captions"
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

            # Stage/Step/Level/Example/Chapter wording is handled by a separate timed
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

        # Resolve project-wide instructional-overlay palette. The first explicit
        # palette is locked for every Stage/Step/Level/Example/Chapter overlay unless
        # a root-level instructional_overlay_theme explicitly defines it.
        raw_overlay_theme = _find_field(
            panel_data,
            ("instructional_overlay_theme", "stage_overlay_theme", "overlay_theme"),
        )
        if not isinstance(raw_overlay_theme, dict):
            raw_overlay_theme = {}
        overlay_specs_by_entry = [extract_stage_overlay_specs(entry) for entry in entries]
        first_overlay_spec = next(
            (spec for specs in overlay_specs_by_entry for spec in specs), None
        )
        default_overlay_background = (
            raw_overlay_theme.get("background_color")
            or raw_overlay_theme.get("background")
            or (first_overlay_spec.get("background") if first_overlay_spec else "#FFFFFF")
        )
        default_overlay_text = (
            raw_overlay_theme.get("text_color")
            or (first_overlay_spec.get("text_color") if first_overlay_spec else "#111111")
        )
        project_overlay_theme = {
            "background_color": _valid_color(default_overlay_background, "#FFFFFF"),
            "text_color": _valid_color(default_overlay_text, "#111111"),
        }
        for specs in overlay_specs_by_entry:
            for spec in specs:
                requested_background = _valid_color(spec.get("background"), project_overlay_theme["background_color"])
                requested_text = _valid_color(spec.get("text_color"), project_overlay_theme["text_color"])
                try:
                    background_mismatch = ImageColor.getrgb(requested_background)[:3] != ImageColor.getrgb(project_overlay_theme["background_color"])[:3]
                except Exception:
                    background_mismatch = True
                try:
                    text_mismatch = ImageColor.getrgb(requested_text)[:3] != ImageColor.getrgb(project_overlay_theme["text_color"])[:3]
                except Exception:
                    text_mismatch = True
                if background_mismatch:
                    print(
                        f"⚠️ [INSTRUCTIONAL-OVERLAY] '{spec['display_text']}' requested a different "
                        "background; enforcing the project-wide background palette"
                    )
                if text_mismatch:
                    print(
                        f"⚠️ [INSTRUCTIONAL-OVERLAY] '{spec['display_text']}' requested a different "
                        "text color; enforcing the project-wide text palette"
                    )
                spec["background"] = project_overlay_theme["background_color"]
                spec["text_color"] = project_overlay_theme["text_color"]
        if first_overlay_spec:
            print(
                f"🎨 [INSTRUCTIONAL-OVERLAY] Project palette locked: "
                f"background={project_overlay_theme['background_color']} | "
                f"text={project_overlay_theme['text_color']}"
            )

        raw_caption_defaults = _find_field(
            panel_data, ("caption_defaults", "caption_animation_defaults", "caption_style_defaults")
        )
        project_caption_defaults = raw_caption_defaults if isinstance(raw_caption_defaults, dict) else {}

        def apply_video_effects(image, local_time, duration, effect_plan, scene_index=0):
            """Apply explicit visual treatment to footage only; captions remain crisp."""
            if not effect_plan or not effect_plan.get("enabled"):
                return image.copy()
            elapsed = max(0.0, float(local_time))
            start_offset = float(effect_plan.get("start_offset_seconds", 0.0) or 0.0)
            effect_duration = effect_plan.get("duration_seconds")
            if elapsed < start_offset or (effect_duration is not None and elapsed > start_offset + float(effect_duration)):
                return image.copy()
            result = image.convert("RGB").copy()
            width, height = result.size
            relative_time = elapsed - start_offset
            for effect in effect_plan.get("effects", []):
                effect_name = effect.get("type")
                intensity = max(0.0, min(1.0, float(effect.get("intensity", 0.5))))
                if effect_name == "black_white":
                    result = ImageOps.grayscale(result).convert("RGB")
                elif effect_name == "sepia":
                    result = ImageOps.colorize(ImageOps.grayscale(result), black="#342519", white="#E5D3AA").convert("RGB")
                elif effect_name in {"vintage", "archival"}:
                    gray = ImageOps.grayscale(result)
                    result = ImageOps.colorize(gray, black="#2C241C", white="#E9D7B2").convert("RGB")
                    result = ImageEnhance.Contrast(result).enhance(1.0 + 0.22 * intensity)
                    result = ImageEnhance.Color(result).enhance(max(0.12, 0.52 - 0.30 * intensity))
                elif effect_name == "cctv":
                    result = ImageOps.grayscale(result).convert("RGB")
                    result = ImageEnhance.Contrast(result).enhance(1.15 + 0.25 * intensity)
                elif effect_name == "desaturate":
                    result = ImageEnhance.Color(result).enhance(max(0.0, 1.0 - 0.85 * intensity))
                elif effect_name == "high_contrast":
                    result = ImageEnhance.Contrast(result).enhance(1.0 + 0.85 * intensity)
                elif effect_name == "cold_tone":
                    overlay = Image.new("RGB", result.size, (65, 105, 150))
                    result = Image.blend(result, overlay, 0.06 + 0.15 * intensity)
                elif effect_name == "warm_tone":
                    overlay = Image.new("RGB", result.size, (185, 115, 55))
                    result = Image.blend(result, overlay, 0.05 + 0.13 * intensity)
                elif effect_name == "blur":
                    result = result.filter(ImageFilter.GaussianBlur(radius=0.5 + 2.0 * intensity))
                elif effect_name == "flicker":
                    pulse = 0.93 + 0.07 * math.sin(relative_time * (13.0 + 12.0 * intensity))
                    pulse *= 1.0 - (0.05 * intensity * abs(math.sin(relative_time * 31.0)))
                    result = ImageEnhance.Brightness(result).enhance(max(0.78, pulse))
                elif effect_name == "film_grain":
                    # Low-resolution deterministic noise keeps the effect efficient at 1080p.
                    seed = int((relative_time * 24.0 + scene_index * 997) * 1000) & 0xFFFFFFFF
                    rng = np.random.default_rng(seed)
                    small_w, small_h = max(32, width // 12), max(18, height // 12)
                    noise_values = rng.integers(90, 166, size=(small_h, small_w), dtype=np.uint8)
                    noise = Image.fromarray(noise_values, mode="L").resize((width, height), Image.Resampling.BILINEAR)
                    grain_layer = Image.merge("RGB", (noise, noise, noise))
                    result = Image.blend(result, grain_layer, 0.04 + 0.10 * intensity)
                elif effect_name == "scanlines":
                    line_layer = Image.new("RGBA", result.size, (0, 0, 0, 0))
                    line_draw = ImageDraw.Draw(line_layer)
                    step = max(3, int(5 - 2 * intensity))
                    for y_line in range(0, height, step):
                        line_draw.line((0, y_line, width, y_line), fill=(0, 0, 0, int(22 + 48 * intensity)), width=1)
                    result = Image.alpha_composite(result.convert("RGBA"), line_layer).convert("RGB")
                elif effect_name == "vignette":
                    mask = Image.new("L", result.size, 255)
                    mask_draw = ImageDraw.Draw(mask)
                    inset_x = int(width * (0.08 + 0.10 * intensity))
                    inset_y = int(height * (0.08 + 0.10 * intensity))
                    mask_draw.ellipse((inset_x, inset_y, width - inset_x, height - inset_y), fill=0)
                    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(20, int(width * 0.12))))
                    dark = Image.new("RGB", result.size, (0, 0, 0))
                    strength = 0.20 + 0.34 * intensity
                    result = Image.composite(Image.blend(result, dark, strength), result, mask)
                elif effect_name == "glitch":
                    # Horizontal band displacement creates a restrained digital tear.
                    frame_no = int(relative_time * 24.0)
                    rng = random.Random(scene_index * 100003 + frame_no)
                    glitched = result.copy()
                    band_count = 2 + int(7 * intensity)
                    for _ in range(band_count):
                        band_y = rng.randint(0, max(0, height - 2))
                        band_h = rng.randint(2, max(3, int(8 + 30 * intensity)))
                        band_h = min(band_h, height - band_y)
                        offset = rng.randint(-max(2, int(8 + 30 * intensity)), max(2, int(8 + 30 * intensity)))
                        strip = result.crop((0, band_y, width, band_y + band_h))
                        glitched.paste(ImageChops.offset(strip, offset, 0), (0, band_y))
                    result = glitched
                elif effect_name == "shake":
                    amplitude = max(1, int(2 + 11 * intensity))
                    dx = int(math.sin(relative_time * (30 + 18 * intensity)) * amplitude)
                    dy = int(math.cos(relative_time * (27 + 16 * intensity)) * amplitude * 0.65)
                    padded = ImageOps.expand(result, border=amplitude + 2, fill=(0, 0, 0))
                    left = amplitude + 2 + dx
                    top = amplitude + 2 + dy
                    result = padded.crop((left, top, left + width, top + height))
            return result

        count = min(len(entries), len(image_files))
        if len(entries) != len(image_files):
            print(f"⚠️ Entry/image count differs: {len(entries)} entries, {len(image_files)} images; processing {count} pairs")
        prepared = []
        _set_worker_status(
            "Preparing scene images",
            progress=0,
            current=0,
            total=count,
            detail=f"Preparing {count} image(s)",
        )
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
                    "stage_overlay_specs": overlay_specs_by_entry[index] if index < len(overlay_specs_by_entry) else [],
                    "caption_animation": extract_caption_animation(entry, project_caption_defaults),
                    "video_effect_plan": extract_video_effect_plan(entry),
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
            _set_worker_status(
                "Preparing scene images",
                progress=round(((index + 1) / max(1, count)) * 100, 1),
                current=index + 1,
                total=count,
                detail=image_info["filename"],
            )
        if not prepared:
            print("❌ No images could be processed")
            return None
        audio_duration = None
        audio_probe = None
        if audio_file_path:
            try:
                audio_probe = AudioFileClip(audio_file_path)
                audio_duration = float(audio_probe.duration)
                print(f"🎵 Audio duration: {audio_duration:.2f}s")
            except Exception as exc:
                print(f"⚠️ Could not read audio duration: {exc}")
            finally:
                if audio_probe is not None:
                    try:
                        audio_probe.close()
                    except Exception:
                        pass
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

            # Locate the Stage/Step/Level/Example/Chapter words in the actual narration.
            # The event covers the complete phrase pronunciation and excludes those
            # same ASR tokens from bottom captions.
            suppressed_heading_word_indices = build_stage_overlay_events(
                prepared, scene_start_offsets, audio_words
            )
            if include_captions:
                _set_worker_status(
                    "Planning captions and overlays",
                    progress=0,
                    detail=f"Planning captions from {len(audio_words)} timestamped words",
                )
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
            # zoom mode. Stage/Step/Level/Example/Chapter metadata never disables camera motion.
            _set_worker_status(
                "Assembling scene clips",
                progress=0,
                current=0,
                total=len(prepared),
                detail=f"Building {len(prepared)} scene clip(s)",
            )
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
                    previous_video_effect_plan=(
                        prepared[scene_index - 1].get("video_effect_plan") if scene_index > 0 else None
                    ),
                    previous_scene_index=max(0, scene_index - 1),
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
                    animated_current = apply_video_effects(
                        animated_current, t, clip_duration, item.get("video_effect_plan"), scene_index
                    )
                    current = animated_current.copy()
                    # Start the transition from the previous scene's actual final
                    # camera position, rather than its unanimated source image.
                    if effect != "none" and previous is not None and trans_duration > 0 and t < trans_duration:
                        progress = min(1.0, max(0.0, t / trans_duration))
                        old = apply_image_motion(
                            previous, previous_clip_duration, previous_clip_duration, previous_plan
                        )
                        old = apply_video_effects(
                            old, previous_clip_duration, previous_clip_duration,
                            previous_video_effect_plan, previous_scene_index
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

                    # Exactly one caption-rendering call is allowed per frame. The
                    # ASR stream is the sole spoken-caption source; per-entry dialogue
                    # is not separately painted, preventing appended duplicate lines.
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
                _set_worker_status(
                    "Assembling scene clips",
                    progress=round(((scene_index + 1) / max(1, len(prepared))) * 100, 1),
                    current=scene_index + 1,
                    total=len(prepared),
                    detail=item.get("filename", "entry"),
                )
            final_clip = concatenate_videoclips(clips, method="chain")
            if audio_file_path and os.path.exists(audio_file_path):
                audio_clip = AudioFileClip(audio_file_path)
                if audio_duration and audio_duration > total_duration:
                    try:
                        audio_clip = audio_clip.subclipped(0, total_duration)
                    except AttributeError:
                        audio_clip = audio_clip.subclip(0, total_duration)
                elif audio_duration and audio_duration < total_duration:
                    try:
                        final_clip = final_clip.subclipped(0, audio_duration)
                    except AttributeError:
                        final_clip = final_clip.subclip(0, audio_duration)
                    total_duration = audio_duration
                if hasattr(final_clip, "with_audio"):
                    final_clip = final_clip.with_audio(audio_clip)
                else:
                    final_clip = final_clip.set_audio(audio_clip)
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
            print(f"   Duration: {total_duration:.2f}s | FPS: 24 | Size: {video_width}x{video_height}")
            print("📊 Rendering progress is displayed in this project's card in the SceneIQ Video Production dashboard.")
            render_started = time.monotonic()
            if video_encoder == "h264_nvenc":
                active_encoder_preset = encoder_preset or "p5"
                active_ffmpeg_params = [
                    "-rc", "vbr",
                    "-cq:v", "18",
                    "-b:v", "0",
                    "-pix_fmt", "yuv420p",
                    "-profile:v", "high",
                    "-level", "4.1",
                    "-movflags", "+faststart",
                    "-color_primaries", "bt709",
                    "-color_trc", "bt709",
                    "-colorspace", "bt709",
                ]
            else:
                active_encoder_preset = encoder_preset or "slow"
                active_ffmpeg_params = [
                    "-crf", "16",
                    "-pix_fmt", "yuv420p",
                    "-profile:v", "high",
                    "-level", "4.1",
                    "-movflags", "+faststart",
                    "-color_primaries", "bt709",
                    "-color_trc", "bt709",
                    "-colorspace", "bt709",
                ]
            active_encoder_threads = ffmpeg_threads or max(1, min(8, os.cpu_count() or 2))
            print(
                f"🎛️ [ENCODER] {video_encoder} | preset={active_encoder_preset} | "
                f"threads={active_encoder_threads}"
            )
            _set_worker_status(
                "Encoding video",
                progress=0,
                current=0,
                total=max(1, int(round(total_duration * 24))),
                detail=f"{video_encoder} | preset={active_encoder_preset}",
            )

            # MoviePy's normal tqdm logger writes carriage-return progress bars.
            # In multiple processes those bars overwrite one another. This logger
            # sends per-worker audio/video progress to the private GUI status file.
            from proglog import ProgressBarLogger

            class _WorkerMoviePyProgressLogger(ProgressBarLogger):
                def __init__(self):
                    super().__init__(logged_bars=[])
                    self._last_emit_time = 0.0
                    self._last_percent = {}

                def bars_callback(self, bar, attr, value, old_value=None):
                    if attr not in {"index", "total"}:
                        return
                    normalized_bar = str(bar).casefold()
                    if normalized_bar not in {"chunk", "frame_index"}:
                        return
                    bar_data = self.bars.get(bar, {})
                    current_value = bar_data.get("index")
                    total_value = bar_data.get("total")
                    if current_value is None or not total_value:
                        return
                    try:
                        current_int = int(current_value) + (1 if attr == "index" else 0)
                        total_int = max(1, int(total_value))
                    except (TypeError, ValueError):
                        return
                    current_int = min(total_int, max(0, current_int))
                    percent = round((current_int / total_int) * 100, 1)
                    now = _worker_time.monotonic()
                    last_percent = self._last_percent.get(normalized_bar, -1)
                    # Avoid a disk write for every frame while still keeping the
                    # GUI progress window responsive at roughly one-percent/one-second cadence.
                    if (
                        percent < 100
                        and percent < last_percent + 1
                        and now - self._last_emit_time < 0.8
                    ):
                        return
                    self._last_emit_time = now
                    self._last_percent[normalized_bar] = percent
                    if normalized_bar == "chunk":
                        stage_name = "Encoding audio"
                        detail_text = f"Audio chunks {current_int:,}/{total_int:,}"
                    else:
                        stage_name = "Encoding video"
                        detail_text = f"Frames {current_int:,}/{total_int:,}"
                    _set_worker_status(
                        stage_name,
                        progress=percent,
                        current=current_int,
                        total=total_int,
                        detail=detail_text,
                    )

            worker_progress_logger = _WorkerMoviePyProgressLogger()
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec=video_encoder,
                audio_codec="aac",
                audio_bitrate="320k",
                preset=active_encoder_preset,
                ffmpeg_params=active_ffmpeg_params,
                threads=active_encoder_threads,
                logger=worker_progress_logger,
            )
            _set_worker_status(
                "Finalizing output",
                progress=99.5,
                detail="Encoder finished; validating output file",
            )
            elapsed_minutes = (time.monotonic() - render_started) / 60.0
            print(f"⏱️ Render elapsed time: {elapsed_minutes:.2f} minutes")
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise RuntimeError("FFmpeg finished without creating a valid output file")
            print(f"✅ Video saved: {output_path}")
            print(f"📊 Size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")
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
        print(f"   Spoken Stage/Step/Level/Example/Chapter overlays: {stage_overlay_count}")
        print("   Subscribe sticker size: 50% of the previous producer version")
        print(
            "   Captions: "
            + ("✅ Original single-row ASR typewriter" if include_captions else "⏭️ Disabled")
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
            "caption_animation": "legacy_asr_typewriter" if include_captions else None,
            "stage_overlay_count": sum(len(item.get("stage_overlay_events", [])) for item in prepared),
            "stage_overlay_mode": "pre-roll + animated-heading + hold/exit" if has_overlay_metadata else None,
            "subscribe_sticker_scale": 0.5,
        }
        # One process owns one project. Release worker-local cached sticker frames
        # and return immediately; the parent process schedules the next project.
        if include_captions:
            try:
                _load_subscribe_sticker_animation.cache_clear()
            except Exception:
                pass
        _set_worker_status(
            "Render finished - waiting to publish",
            progress=98,
            current=98,
            total=100,
            detail="The private render is complete; waiting to publish it safely to the original project folder.",
            status="running",
        )
        return completed_result

    try:
        return _run_video_producer()
    finally:
        _awake_stop.set()
        _awake_thread.join(timeout=2.0)
        if _awake_thread.is_alive():
            print("⚠️ [KEEP-AWAKE] Worker did not stop within 2 seconds; it will exit as a daemon thread")
        else:
            print("🖥️ [KEEP-AWAKE] Windows awake protection released after video producer finished")

# -----------------------------------------------------------------------------
# Multiprocessing orchestration for independent video projects
# -----------------------------------------------------------------------------

def _video_producer_normalize_title(name):
    import re
    normalized = re.sub(r"[^a-zA-Z0-9\s_]", "", str(name or ""))
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unnamed_project"

def _video_producer_collect_ready_titles(ready_script_path):
    """Return unique project records from READY_SCRIPT, including projectcategory."""
    import json
    import re

    with open(ready_script_path, "r", encoding="utf-8") as handle:
        ready_data = json.load(handle)

    def normalise_key(key):
        return re.sub(r"[^a-z0-9]", "", str(key).lower())

    def walk_json(node, path=()):
        yield path, node
        if isinstance(node, dict):
            for key, value in node.items():
                yield from walk_json(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                yield from walk_json(value, path + (index,))

    def find_field(node, aliases, require_value=True):
        wanted = {normalise_key(alias) for alias in aliases}
        for _, current in walk_json(node):
            if not isinstance(current, dict):
                continue
            for key, value in current.items():
                if normalise_key(key) in wanted and (
                    not require_value or value not in (None, "", [], {})
                ):
                    return value
        return None

    def find_project_title(node):
        if not isinstance(node, dict):
            return None
        value = None
        for key, candidate_value in node.items():
            if normalise_key(key) in {"projecttitle", "projectname"} and candidate_value not in (None, "", [], {}):
                value = candidate_value
                break
        if isinstance(value, dict):
            value = next((v for k, v in value.items() if normalise_key(k) in {"projecttitle", "title", "name"} and v not in (None, "", [], {})), value)
        # The current panel schema stores these fields under automation.
        if value is None:
            automation = next((v for k, v in node.items() if normalise_key(k) == "automation" and isinstance(v, dict)), None)
            if isinstance(automation, dict):
                value = next((v for k, v in automation.items() if normalise_key(k) in {"projecttitle", "projectname"} and v not in (None, "", [], {})), None)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
        return None

    def find_script_data(node):
        candidates = []
        for path, current in walk_json(node):
            if not path or not isinstance(path[-1], str) or normalise_key(path[-1]) != "script":
                continue
            if isinstance(current, list):
                score = 0
                for item in current:
                    if isinstance(item, dict):
                        keys = {normalise_key(key) for key in item}
                        if keys.intersection({
                            "sceneimagegeneration", "sceneimageprompt",
                            "imagegenerationprompt", "imageprompt",
                            "charactersreference", "characterreference",
                            "scenepovprompt", "shotnumber", "dialogue",
                            "narration", "voiceover", "spoken_text",
                            "instructionaloverlay", "stageoverlay", "videoeffects",
                            "captionanimation",
                        }):
                            score += 10
                        if "entries" in keys:
                            score += 2
                candidates.append((score, len(current), current))
            elif isinstance(current, dict):
                nested = find_field(current, ("script",))
                if isinstance(nested, list):
                    candidates.append((1, len(nested), nested))
                else:
                    candidates.append((0, len(current), current))
        if candidates:
            candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return candidates[0][2]
        return None

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
        title = find_project_title(current)
        script = find_script_data(current)
        if title and isinstance(script, (dict, list)) and bool(script):
            category = find_field(current, ("projectcategory", "project_category", "projectCategory"))
            if category is None:
                automation = next((v for k, v in current.items() if normalise_key(k) == "automation" and isinstance(v, dict)), None)
                category = find_field(automation, ("projectcategory", "project_category", "projectCategory")) if automation else None
            records.append({
                "project_title": title,
                "project_category": str(category).strip() if category not in (None, "") else None,
            })
            return
        for child in current.values():
            if isinstance(child, (dict, list)):
                visit(child)

    visit(ready_data)
    unique_projects = []
    seen = set()
    for record in records:
        key = (
            str(record.get("project_category") or "").casefold(),
            _video_producer_normalize_title(record["project_title"]).casefold(),
        )
        if key not in seen:
            seen.add(key)
            unique_projects.append(record)
        else:
            print(
                f"⏭️ [READY-SCRIPT] Duplicate project skipped: "
                f"{record['project_category']}/{record['project_title']}"
            )
    return unique_projects

def _video_producer_detect_gpu():
    """Detect usable CTranslate2 CUDA and FFmpeg NVIDIA NVENC capabilities."""
    import shutil
    import subprocess

    cuda_device_count = 0
    try:
        import ctranslate2
        cuda_device_count = max(0, int(ctranslate2.get_cuda_device_count()))
    except Exception:
        cuda_device_count = 0

    ffmpeg_binary = shutil.which("ffmpeg")
    nvenc_available = False
    if ffmpeg_binary:
        try:
            result = subprocess.run(
                [ffmpeg_binary, "-hide_banner", "-encoders"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=12,
                check=False,
            )
            nvenc_available = result.returncode == 0 and "h264_nvenc" in result.stdout
        except Exception:
            nvenc_available = False

    return {
        "cuda_device_count": cuda_device_count,
        "cuda_available": cuda_device_count > 0,
        "nvenc_available": nvenc_available,
        "ffmpeg_binary": ffmpeg_binary if nvenc_available else None,
        "gpu_available": cuda_device_count > 0 or nvenc_available,
    }

def _video_producer_write_worker_status(status_path, payload):
    """Write one worker snapshot with Windows sharing-violation retries.

    Dashboard readers may briefly have a status file open. The writer therefore
    uses a unique temporary file, retries os.replace(), and finally falls back to
    a retrying direct write. A transient GUI/antivirus file handle must not flood
    the worker log or stop production.
    """
    import json
    import os
    import time
    import uuid

    if not status_path:
        return
    directory = os.path.dirname(os.path.abspath(status_path))
    os.makedirs(directory, exist_ok=True)
    token = f"{os.getpid()}_{uuid.uuid4().hex}"
    temporary_path = f"{status_path}.tmp_{token}"
    data = dict(payload or {})
    data["updated_at"] = time.time()
    encoded = json.dumps(data, ensure_ascii=False)

    try:
        with open(temporary_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(encoded)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass

        last_error = None
        replace_deadline = time.monotonic() + 4.0
        while time.monotonic() < replace_deadline:
            try:
                os.replace(temporary_path, status_path)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.12)
            except OSError as exc:
                last_error = exc
                # Only retry Windows sharing/access races. Other failures are
                # also retried briefly because a transient scanner can interfere.
                time.sleep(0.12)

        # Fallback: the dashboard already tolerates a short malformed-JSON
        # interval, and direct truncating writes can succeed when rename is denied.
        direct_deadline = time.monotonic() + 4.0
        while time.monotonic() < direct_deadline:
            try:
                with open(status_path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(encoded)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except OSError:
                        pass
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.15)

        raise last_error or OSError("Unable to publish worker status")
    finally:
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
        except OSError:
            pass

def _video_producer_read_worker_status(status_path):
    """Read one worker status file; tolerate atomic-replace races and shutdown."""
    import json
    try:
        with open(status_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}

def _video_producer_launch_dashboard_window(manifest_path):
    '''Launch one console-free SceneIQ dashboard for every production in this run.'''
    import os
    import sys
    import shutil
    import subprocess

    if os.name != "nt":
        return None

    script_path = os.path.abspath(globals().get("__file__", ""))
    if not script_path or not os.path.isfile(script_path):
        raise RuntimeError("Cannot locate the video producer script for the GUI dashboard")

    current_python = os.path.abspath(sys.executable)
    pythonw_candidate = os.path.join(os.path.dirname(current_python), "pythonw.exe")
    if os.path.isfile(pythonw_candidate):
        dashboard_python = pythonw_candidate
        creation_flags = 0
        startupinfo = None
    else:
        dashboard_python = shutil.which("pythonw") or current_python
        is_pythonw = os.path.basename(dashboard_python).casefold().startswith("pythonw")
        creation_flags = 0 if is_pythonw else getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = None
        if not is_pythonw and hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0

    command = [
        dashboard_python,
        script_path,
        "--video-producer-dashboard",
        os.path.abspath(manifest_path),
    ]
    process = subprocess.Popen(
        command,
        cwd=os.path.dirname(script_path) or None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creation_flags,
        startupinfo=startupinfo,
    )
    return process.pid

def _video_producer_dashboard_window(manifest_path):
    '''Show all project workers in one scrollable, live-updating grid window.'''
    import json
    import os
    import time
    import tkinter as tk
    from tkinter import ttk

    def read_manifest():
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    manifest = read_manifest()
    jobs = manifest.get("jobs") or []
    if not isinstance(jobs, list):
        jobs = []

    root = tk.Tk()
    root.title("SceneIQ Video Production")
    root.geometry("1540x960")
    root.minsize(1040, 700)
    root.configure(bg="#0b1220")

    background = "#0b1220"
    panel = "#121d2e"
    panel_alt = "#172438"
    foreground = "#eef4fb"
    muted = "#9aabc0"
    accent = "#39d6b0"
    accent_dark = "#163f3b"
    border = "#26364d"
    danger = "#ff7777"
    blue = "#8bb8ff"

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "SceneIQ.Horizontal.TProgressbar",
        troughcolor=panel_alt,
        background=accent,
        bordercolor=panel_alt,
        lightcolor=accent,
        darkcolor=accent,
        thickness=12,
    )

    outer = tk.Frame(root, bg=background, padx=16, pady=14)
    outer.pack(fill="both", expand=True)

    header = tk.Frame(outer, bg=background)
    header.pack(fill="x", pady=(0, 12))
    title_area = tk.Frame(header, bg=background)
    title_area.pack(side="left", fill="x", expand=True)
    tk.Label(
        title_area,
        text="SCENEIQ  /  VIDEO PRODUCTION",
        bg=background,
        fg=accent,
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w")
    tk.Label(
        title_area,
        text="Production dashboard",
        bg=background,
        fg=foreground,
        font=("Segoe UI", 19, "bold"),
    ).pack(anchor="w", pady=(3, 1))
    tk.Label(
        title_area,
        text="Each card reports one independent video worker. Closing this dashboard does not stop production.",
        bg=background,
        fg=muted,
        font=("Segoe UI", 9),
    ).pack(anchor="w")

    summary_label = tk.Label(
        header,
        text="Preparing workers…",
        bg=panel,
        fg=foreground,
        font=("Segoe UI", 10, "bold"),
        padx=13,
        pady=9,
    )
    summary_label.pack(side="right", padx=(10, 0), anchor="center")

    stats_row = tk.Frame(outer, bg=background)
    stats_row.pack(fill="x", pady=(0, 10))
    stat_labels = {}
    for key, caption, color in (
        ("running", "RUNNING", accent),
        ("queued", "QUEUED", blue),
        ("completed", "COMPLETED", accent),
        ("failed", "FAILED", danger),
        ("total", "TOTAL PROJECTS", foreground),
    ):
        stat = tk.Frame(stats_row, bg=panel, highlightbackground=border, highlightthickness=1, padx=12, pady=7)
        stat.pack(side="left", fill="x", expand=True, padx=(0, 7))
        tk.Label(stat, text=caption, bg=panel, fg=muted, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        value = tk.Label(stat, text="0", bg=panel, fg=color, font=("Segoe UI", 15, "bold"))
        value.pack(anchor="w", pady=(2, 0))
        stat_labels[key] = value

    grid_shell = tk.Frame(outer, bg=background)
    grid_shell.pack(fill="both", expand=True)
    canvas = tk.Canvas(grid_shell, bg=background, highlightthickness=0, borderwidth=0)
    vertical_scroll = ttk.Scrollbar(grid_shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vertical_scroll.set)
    vertical_scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    grid_frame = tk.Frame(canvas, bg=background)
    canvas_window = canvas.create_window((0, 0), window=grid_frame, anchor="nw")
    grid_frame.bind(
        "<Configure>",
        lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
    )

    # Each card stores its own log byte offset and widgets. No worker's output
    # is ever inserted into another project's card.
    cards = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            continue
        worker_id = str(job.get("worker_id") or f"WORKER-{index + 1:03d}")
        project_title = str(job.get("project_title") or "Video production")
        status_path = str(job.get("status_path") or "")
        log_path = str(job.get("log_path") or "")

        card = tk.Frame(
            grid_frame,
            bg=panel,
            highlightbackground=border,
            highlightthickness=1,
            padx=13,
            pady=11,
        )

        card_header = tk.Frame(card, bg=panel)
        card_header.pack(fill="x")
        card_title = tk.Label(
            card_header,
            text=project_title,
            bg=panel,
            fg=foreground,
            font=("Segoe UI", 11, "bold"),
            justify="left",
            anchor="w",
            wraplength=520,
        )
        card_title.pack(side="left", fill="x", expand=True)
        badge = tk.Label(
            card_header,
            text="QUEUED",
            bg="#1c3450",
            fg=blue,
            font=("Segoe UI", 8, "bold"),
            padx=9,
            pady=4,
        )
        badge.pack(side="right", padx=(8, 0), anchor="n")

        metadata = tk.Frame(card, bg=panel)
        metadata.pack(fill="x", pady=(7, 7))
        worker_meta = tk.Label(
            metadata,
            text=f"{worker_id}  •  PID —  •  {str(job.get('lane') or 'unknown').upper()} LANE",
            bg=panel,
            fg=muted,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        )
        worker_meta.pack(side="left", fill="x", expand=True)
        encoder_meta = tk.Label(
            metadata,
            text=f"Encoder: {job.get('encoder') or '—'}",
            bg=panel,
            fg=muted,
            font=("Segoe UI", 8),
            anchor="e",
        )
        encoder_meta.pack(side="right")

        stage_label = tk.Label(
            card,
            text="Waiting for a process slot",
            bg=panel,
            fg=foreground,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        )
        stage_label.pack(fill="x")
        detail_label = tk.Label(
            card,
            text="This project is queued for production.",
            bg=panel,
            fg=muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify="left",
            wraplength=540,
        )
        detail_label.pack(fill="x", pady=(3, 7))

        progress_row = tk.Frame(card, bg=panel)
        progress_row.pack(fill="x")
        progress_bar = ttk.Progressbar(
            progress_row,
            style="SceneIQ.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        progress_bar.pack(side="left", fill="x", expand=True)
        progress_label = tk.Label(
            progress_row,
            text="—",
            bg=panel,
            fg=accent,
            font=("Segoe UI", 9, "bold"),
            width=12,
            anchor="e",
        )
        progress_label.pack(side="right", padx=(9, 0))

        footer_meta = tk.Frame(card, bg=panel)
        footer_meta.pack(fill="x", pady=(6, 7))
        elapsed_label = tk.Label(footer_meta, text="Elapsed: 00:00", bg=panel, fg=muted, font=("Segoe UI", 8))
        elapsed_label.pack(side="left")
        whisper_label = tk.Label(footer_meta, text="Whisper: —", bg=panel, fg=muted, font=("Segoe UI", 8))
        whisper_label.pack(side="right")

        log_header = tk.Frame(card, bg=panel)
        log_header.pack(fill="x", pady=(2, 4))
        tk.Label(
            log_header,
            text="LIVE WORKER OUTPUT",
            bg=panel,
            fg=muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        log_frame = tk.Frame(card, bg="#080e18", highlightbackground=border, highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        log_text = tk.Text(
            log_frame,
            bg="#080e18",
            fg="#d7e3f0",
            insertbackground=foreground,
            selectbackground="#285b68",
            relief="flat",
            borderwidth=0,
            wrap="word",
            padx=8,
            pady=6,
            font=("Consolas", 8),
            height=7,
            state="disabled",
        )
        log_text.pack(side="left", fill="both", expand=True)
        log_text.configure(state="normal")
        log_text.insert("end", "Waiting for this worker's output…\n")
        log_text.configure(state="disabled")

        card_buttons = tk.Frame(card, bg=panel)
        card_buttons.pack(fill="x", pady=(6, 0))
        open_log_button = tk.Button(
            card_buttons,
            text="Open worker log",
            bg=panel_alt,
            fg=foreground,
            activebackground=border,
            activeforeground=foreground,
            relief="flat",
            padx=9,
            pady=4,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
            command=lambda path=log_path: os.startfile(path) if path and os.path.isfile(path) else None,
        )
        open_log_button.pack(side="right")

        cards.append({
            "worker_id": worker_id,
            "project_title": project_title,
            "status_path": status_path,
            "log_path": log_path,
            "card": card,
            "badge": badge,
            "worker_meta": worker_meta,
            "encoder_meta": encoder_meta,
            "stage_label": stage_label,
            "detail_label": detail_label,
            "progress_bar": progress_bar,
            "progress_label": progress_label,
            "elapsed_label": elapsed_label,
            "whisper_label": whisper_label,
            "log_text": log_text,
            "log_offset": 0,
            "terminal_status": None,
        })

    layout_state = {"columns": 0}

    def relayout_cards(_event=None):
        width = max(1, canvas.winfo_width())
        if width < 1120:
            columns = 1
        elif width < 1710:
            columns = 2
        else:
            columns = 3
        if columns == layout_state["columns"]:
            return
        layout_state["columns"] = columns
        for column in range(3):
            grid_frame.grid_columnconfigure(column, weight=1 if column < columns else 0, uniform="sceneiq_cards")
        for card_index, card_info in enumerate(cards):
            card_info["card"].grid_forget()
            card_info["card"].grid(
                row=card_index // columns,
                column=card_index % columns,
                sticky="nsew",
                padx=7,
                pady=7,
            )
        for row_index in range((len(cards) + columns - 1) // columns):
            grid_frame.grid_rowconfigure(row_index, weight=1)

    canvas.bind("<Configure>", lambda event: (canvas.itemconfigure(canvas_window, width=event.width), relayout_cards(event)))
    root.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

    def append_card_log(card_info, state):
        path = state.get("log_path") or card_info["log_path"]
        if not path or not os.path.isfile(path):
            return
        try:
            size = os.path.getsize(path)
            if card_info["log_offset"] > size:
                card_info["log_offset"] = 0
            with open(path, "rb") as handle:
                handle.seek(card_info["log_offset"])
                chunk = handle.read()
                card_info["log_offset"] = handle.tell()
        except OSError:
            return
        if not chunk:
            return
        rendered = chunk.decode("utf-8", errors="replace").replace("\r", "\n")
        text_widget = card_info["log_text"]
        should_follow = text_widget.yview()[1] >= 0.985
        text_widget.configure(state="normal")
        text_widget.insert("end", rendered)
        try:
            line_count = int(text_widget.index("end-1c").split(".")[0])
            if line_count > 180:
                text_widget.delete("1.0", f"{line_count - 130}.0")
        except Exception:
            pass
        if should_follow:
            text_widget.see("end")
        text_widget.configure(state="disabled")

    def refresh_dashboard():
        counts = {"running": 0, "queued": 0, "completed": 0, "failed": 0, "total": len(cards)}
        terminal_values = {"completed", "failed", "skipped_or_failed"}

        for card_info in cards:
            state = _video_producer_read_worker_status(card_info["status_path"])
            if not state:
                counts["queued"] += 1
                append_card_log(card_info, {})
                continue

            status = str(state.get("status") or "queued").casefold()
            if status == "running":
                counts["running"] += 1
            elif status == "queued":
                counts["queued"] += 1
            elif status == "completed":
                counts["completed"] += 1
            elif status in {"failed", "skipped_or_failed"}:
                counts["failed"] += 1

            card_info["card"].configure(bg=panel)
            card_info["badge"].configure(text={
                "queued": "QUEUED",
                "running": "PRODUCING",
                "completed": "COMPLETED",
                "failed": "FAILED",
                "skipped_or_failed": "NO OUTPUT",
            }.get(status, status.upper()))
            if status in {"failed", "skipped_or_failed"}:
                badge_bg, badge_fg = "#45232b", danger
            elif status == "completed":
                badge_bg, badge_fg = accent_dark, accent
            elif status == "running":
                badge_bg, badge_fg = "#163b49", accent
            else:
                badge_bg, badge_fg = "#1c3450", blue
            card_info["badge"].configure(bg=badge_bg, fg=badge_fg)
            card_info["worker_meta"].configure(
                text=(
                    f"{state.get('worker_id') or card_info['worker_id']}  •  "
                    f"PID {state.get('pid') or '—'}  •  {str(state.get('lane') or 'unknown').upper()} LANE"
                )
            )
            card_info["encoder_meta"].configure(text=f"Encoder: {state.get('encoder') or '—'}")
            card_info["stage_label"].configure(text=str(state.get("stage") or "Working"))
            card_info["detail_label"].configure(text=str(state.get("detail") or "The worker is processing this project."))

            progress_value = state.get("progress")
            current_value = state.get("current")
            total_value = state.get("total")
            if isinstance(progress_value, (int, float)):
                progress_value = max(0.0, min(100.0, float(progress_value)))
                card_info["progress_bar"].configure(value=progress_value)
                if current_value is not None and total_value:
                    card_info["progress_label"].configure(text=f"{progress_value:.1f}% ({current_value}/{total_value})")
                else:
                    card_info["progress_label"].configure(text=f"{progress_value:.1f}%")
            elif status == "completed":
                card_info["progress_bar"].configure(value=100)
                card_info["progress_label"].configure(text="100%")
            else:
                card_info["progress_label"].configure(text="—")

            started_at = state.get("started_at") or state.get("queued_at") or time.time()
            try:
                elapsed = max(0, int(time.time() - float(started_at)))
            except (TypeError, ValueError):
                elapsed = 0
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
            card_info["elapsed_label"].configure(text=f"Elapsed: {elapsed_text}")
            card_info["whisper_label"].configure(
                text=(
                    f"Whisper: {state.get('whisper_device', 'cpu')} / "
                    f"{state.get('whisper_compute_type', 'int8')}"
                )
            )
            append_card_log(card_info, state)
            card_info["terminal_status"] = status if status in terminal_values else None

        for key, value in counts.items():
            stat_labels[key].configure(text=str(value))
        summary_label.configure(
            text=(
                f"{counts['running']} running   •   {counts['queued']} queued   •   "
                f"{counts['completed']} completed   •   {counts['failed']} failed"
            )
        )

        # Keep the requested window title stable for the full run.
        root.title("SceneIQ Video Production")
        root.after(850, refresh_dashboard)

    if not cards:
        tk.Label(
            grid_frame,
            text="No production jobs were found in this dashboard manifest.",
            bg=background,
            fg=muted,
            font=("Segoe UI", 11),
            padx=20,
            pady=20,
        ).pack(anchor="w")
    else:
        refresh_dashboard()

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.after(300, root.lift)
    root.mainloop()

# -----------------------------------------------------------------------------
# Per-worker private workspaces and safe publication to the original project
# -----------------------------------------------------------------------------

def _video_producer_wait_for_stable_file(source_path, timeout_seconds=300, stable_seconds=0.45):
    """Wait until a source file stops changing and can be safely copied."""
    import os
    import time

    deadline = time.monotonic() + max(1.0, float(timeout_seconds))
    previous_signature = None
    stable_since = None
    last_error = None
    while time.monotonic() < deadline:
        try:
            stat = os.stat(source_path)
            signature = (stat.st_size, getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)))
            if stat.st_size > 0 and signature == previous_signature:
                if stable_since is not None and time.monotonic() - stable_since >= stable_seconds:
                    # Confirm that the file can be opened for reading before copy.
                    with open(source_path, "rb") as probe:
                        probe.read(1)
                    return stat
            else:
                previous_signature = signature
                stable_since = time.monotonic()
        except (OSError, PermissionError) as exc:
            last_error = exc
            previous_signature = None
            stable_since = None
        time.sleep(0.20)
    detail = f": {last_error}" if last_error else ""
    raise TimeoutError(f"Timed out waiting for a stable, readable file: {source_path}{detail}")

def _video_producer_copy_file_isolated(source_path, destination_path, timeout_seconds=300):
    """Copy one input into a worker folder, retrying transient Windows locks."""
    import os
    import shutil
    import time
    import uuid

    source_path = os.path.abspath(os.fspath(source_path))
    destination_path = os.path.abspath(os.fspath(destination_path))
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    deadline = time.monotonic() + max(1.0, float(timeout_seconds))
    last_error = None
    while time.monotonic() < deadline:
        temporary_path = destination_path + f".copying_{os.getpid()}_{uuid.uuid4().hex}"
        try:
            before = _video_producer_wait_for_stable_file(
                source_path,
                timeout_seconds=max(1.0, min(30.0, deadline - time.monotonic())),
                stable_seconds=0.25,
            )
            shutil.copy2(source_path, temporary_path)
            after = os.stat(source_path)
            before_signature = (before.st_size, getattr(before, "st_mtime_ns", int(before.st_mtime * 1e9)))
            after_signature = (after.st_size, getattr(after, "st_mtime_ns", int(after.st_mtime * 1e9)))
            if before_signature != after_signature:
                raise OSError("Source changed while it was being copied")
            if os.path.getsize(temporary_path) != after.st_size:
                raise OSError("Copied file size does not match the source")
            os.replace(temporary_path, destination_path)
            return destination_path
        except (OSError, TimeoutError) as exc:
            last_error = exc
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass
            time.sleep(0.35)
    raise TimeoutError(
        f"Could not make a private copy of '{source_path}' after {timeout_seconds}s: {last_error}"
    )

def _video_producer_copy_project_tree_isolated(source_root, destination_root, timeout_seconds=600, progress_callback=None):
    """Copy a project tree while excluding prior renders and disposable caption caches.

    All project JSON, panel/storyboard data, entry images, thumbnail sources, and
    other project assets are copied. Previous rendered videos in edited/ and the
    regenerable temp_captions/ cache are not copied into a fresh worker run.
    """
    import os
    import time

    source_root = os.path.abspath(os.fspath(source_root))
    destination_root = os.path.abspath(os.fspath(destination_root))
    if not os.path.isdir(source_root):
        raise NotADirectoryError(f"Project source folder does not exist: {source_root}")
    os.makedirs(destination_root, exist_ok=True)

    files_to_copy = []
    skipped_outputs = 0
    for current_root, directories, filenames in os.walk(source_root, topdown=True):
        relative_root = os.path.relpath(current_root, source_root)
        relative_parts = [] if relative_root == "." else relative_root.split(os.sep)
        directories[:] = sorted(
            name for name in directories
            if name.casefold() not in {"temp_captions", "__pycache__"}
        )
        if any(part.casefold() == "temp_captions" for part in relative_parts):
            directories[:] = []
            continue
        in_edited_folder = any(part.casefold() == "edited" for part in relative_parts)
        for filename in sorted(filenames):
            lowered = filename.casefold()
            if lowered == ".sceniq_publish.lock" or ".incoming_" in lowered:
                continue
            if lowered.endswith((".tmp", ".part", ".partial", ".copying")):
                continue
            extension = os.path.splitext(filename)[1].casefold()
            if in_edited_folder and extension in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}:
                skipped_outputs += 1
                continue
            source_file = os.path.join(current_root, filename)
            relative_file = os.path.relpath(source_file, source_root)
            files_to_copy.append((source_file, relative_file))

    total_files = len(files_to_copy)
    copied_files = 0
    started = time.monotonic()
    for source_file, relative_file in files_to_copy:
        target_file = os.path.join(destination_root, relative_file)
        remaining = max(1.0, float(timeout_seconds) - (time.monotonic() - started))
        _video_producer_copy_file_isolated(
            source_file,
            target_file,
            timeout_seconds=min(remaining, 300.0),
        )
        copied_files += 1
        if progress_callback:
            try:
                progress_callback(copied_files, max(1, total_files), relative_file)
            except Exception:
                pass
    return {
        "copied_files": copied_files,
        "total_files": total_files,
        "skipped_previous_renders": skipped_outputs,
    }

def _video_producer_resolve_original_project_folder(images_root, project_title, project_category=None):
    """Resolve category/title and legacy flat project paths, with no category required."""
    return _sceneiq_resolve_project_folder_path(
        images_root,
        project_title,
        project_category=project_category,
        create_if_missing=False,
    )

def _video_producer_find_audio_source(project_title):
    """Find the same latest title-matching Downloads audio as the original producer."""
    import os

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads):
        return None
    audio_extensions = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma")
    try:
        matches = [
            os.path.join(downloads, name)
            for name in os.listdir(downloads)
            if name.lower().endswith(audio_extensions)
            and str(project_title).lower() in name.lower()
            and os.path.isfile(os.path.join(downloads, name))
        ]
        return max(matches, key=os.path.getmtime) if matches else None
    except OSError:
        return None

def _video_producer_prepare_worker_workspace(job, workspace_path, status_path=None, base_status=None):
    """Create a complete, independent input workspace for one video worker."""
    import os
    import shutil

    original_ready_script = job.get("ready_script_path")
    original_images_root = job.get("images_path")
    title = job.get("project_title")
    if not original_ready_script or not os.path.isfile(original_ready_script):
        raise FileNotFoundError(f"READY_SCRIPT snapshot is missing: {original_ready_script}")
    if not original_images_root or not os.path.isdir(original_images_root):
        raise NotADirectoryError(f"IMAGES_PATH is missing: {original_images_root}")

    workspace_path = os.path.abspath(workspace_path)
    os.makedirs(workspace_path, exist_ok=True)
    timeout = float(os.environ.get("VIDEO_WORKSPACE_COPY_TIMEOUT_SECONDS", "900"))

    def report_copy_stage(stage, progress, detail):
        if not status_path:
            return
        status_payload = dict(base_status or {})
        status_payload.update({
            "worker_id": job.get("worker_id"),
            "lane": str(job.get("lane", "unknown")).upper(),
            "pid": os.getpid(),
            "project_title": title,
            "status": "running",
            "stage": stage,
            "progress": progress,
            "detail": detail,
            "log_path": job.get("log_path"),
            "status_path": status_path,
        })
        _video_producer_write_worker_status(status_path, status_payload)

    report_copy_stage(
        "Copying private queue JSON",
        2,
        "Creating this worker's own READY_SCRIPT copy",
    )

    private_queue_dir = os.path.join(workspace_path, "queue")
    private_ready_script = os.path.join(private_queue_dir, "ready_script.json")
    _video_producer_copy_file_isolated(original_ready_script, private_ready_script, timeout_seconds=timeout)

    project_category = job.get("project_category")
    original_project_dir = _video_producer_resolve_original_project_folder(
        original_images_root, title, project_category
    )
    if not original_project_dir or not os.path.isdir(original_project_dir):
        return {
            "workspace_path": workspace_path,
            "ready_script_path": private_ready_script,
            "images_path": os.path.join(workspace_path, "projects"),
            "subscribe_stickers_path": None,
            "audio_path": None,
            "skip_reason": (
                f"No project image folder was found for '{title}' under "
                f"{original_images_root}; checked category and legacy flat paths"
            ),
        }

    normalized_title = _video_producer_normalize_title(title)
    safe_title = _sceneiq_safe_path_component(title, "unnamed_project")
    expected_output_paths = [
        os.path.join(original_project_dir, "edited", f"{normalized_title}.mp4"),
        os.path.join(original_images_root, safe_title, "edited", f"{normalized_title}.mp4"),
        os.path.join(original_images_root, normalized_title, "edited", f"{normalized_title}.mp4"),
        os.path.join(original_images_root, "Uncategorized", safe_title, "edited", f"{normalized_title}.mp4"),
        os.path.join(original_images_root, "Uncategorized", normalized_title, "edited", f"{normalized_title}.mp4"),
    ]
    if project_category:
        category_component = _sceneiq_safe_path_component(project_category)
        expected_output_paths.extend([
            os.path.join(original_images_root, category_component, safe_title, "edited", f"{normalized_title}.mp4"),
            os.path.join(original_images_root, category_component, normalized_title, "edited", f"{normalized_title}.mp4"),
        ])
    for existing_output in expected_output_paths:
        try:
            if os.path.isfile(existing_output) and os.path.getsize(existing_output) > 0:
                return {
                    "workspace_path": workspace_path,
                    "already_completed_output": existing_output,
                    "original_project_dir": original_project_dir,
                    "ready_script_path": private_ready_script,
                    "images_path": os.path.join(workspace_path, "projects"),
                    "subscribe_stickers_path": None,
                    "audio_path": None,
                }
        except OSError:
            # If metadata access is temporarily denied, do not assume the output
            # exists; publication will use an explicit lock and retry later.
            continue

    audio_source = _video_producer_find_audio_source(title)
    if not audio_source or not os.path.isfile(audio_source) or os.path.getsize(audio_source) <= 0:
        return {
            "workspace_path": workspace_path,
            "original_project_dir": original_project_dir,
            "ready_script_path": private_ready_script,
            "images_path": os.path.join(workspace_path, "projects"),
            "subscribe_stickers_path": None,
            "audio_path": None,
            "skip_reason": f"No valid narration audio was found for '{title}' in Downloads",
        }

    relative_project_path = os.path.relpath(original_project_dir, original_images_root)
    private_images_root = os.path.join(workspace_path, "projects")
    private_project_dir = os.path.join(private_images_root, relative_project_path)

    report_copy_stage(
        "Copying private project files",
        5,
        "Copying project JSON, storyboard files, images and assets into this worker's folder",
    )
    def project_copy_progress(current, total, relative_file):
        percentage = round((current / max(1, total)) * 100, 1)
        report_copy_stage(
            "Copying private project files",
            percentage,
            f"Copied {current}/{total}: {relative_file}",
        )

    copy_summary = _video_producer_copy_project_tree_isolated(
        original_project_dir,
        private_project_dir,
        timeout_seconds=timeout,
        progress_callback=project_copy_progress,
    )

    private_audio_path = os.path.join(workspace_path, "audio", os.path.basename(audio_source))
    report_copy_stage(
        "Copying private narration audio",
        7,
        f"Copying {os.path.basename(audio_source)}",
    )
    _video_producer_copy_file_isolated(audio_source, private_audio_path, timeout_seconds=timeout)

    private_stickers_path = None
    sticker_source = job.get("subscribe_stickers_path")
    if sticker_source and os.path.isdir(sticker_source):
        private_stickers_path = os.path.join(workspace_path, "subscribe_stickers")
        report_copy_stage(
            "Copying private sticker assets",
            8,
            "Copying animated subscribe sticker library",
        )
        def sticker_copy_progress(current, total, relative_file):
            percentage = round((current / max(1, total)) * 100, 1)
            report_copy_stage(
                "Copying private sticker assets",
                percentage,
                f"Copied sticker asset {current}/{total}: {relative_file}",
            )

        _video_producer_copy_project_tree_isolated(
            sticker_source,
            private_stickers_path,
            timeout_seconds=timeout,
            progress_callback=sticker_copy_progress,
        )

    return {
        "workspace_path": workspace_path,
        "original_project_dir": original_project_dir,
        "private_project_dir": private_project_dir,
        "ready_script_path": private_ready_script,
        "images_path": private_images_root,
        "subscribe_stickers_path": private_stickers_path,
        "audio_path": private_audio_path,
        "copy_summary": copy_summary,
    }

def _video_producer_acquire_project_publish_lock(edited_folder, timeout_seconds=1800):
    """Acquire a cross-process lock for final writes to one original edited folder."""
    import os
    import time

    os.makedirs(edited_folder, exist_ok=True)
    lock_path = os.path.join(edited_folder, ".sceniq_publish.lock")
    handle = open(lock_path, "a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + max(1.0, float(timeout_seconds))
        while time.monotonic() < deadline:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return handle
            except (OSError, BlockingIOError):
                time.sleep(0.35)
        raise TimeoutError(
            f"Timed out waiting for another SceneIQ worker to release the publish lock: {lock_path}"
        )
    except Exception:
        handle.close()
        raise

def _video_producer_release_project_publish_lock(handle):
    """Release a project publication lock without deleting the shared lock file."""
    if handle is None:
        return
    try:
        handle.seek(0)
        if __import__("os").name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        handle.close()
    except OSError:
        pass

def _video_producer_replace_when_ready(source_path, destination_path, deadline):
    """Replace a destination only when Windows releases any external file handle."""
    import os
    import time

    last_error = None
    while time.monotonic() < deadline:
        try:
            os.replace(source_path, destination_path)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.4)
    raise TimeoutError(
        f"Destination is still unavailable; could not publish '{destination_path}': {last_error}"
    )

def _video_producer_publish_worker_outputs(job, workspace_result, render_result):
    """Publish final MP4/thumbnail to the original project after acquiring its lock."""
    import os
    import re
    import shutil
    import time
    import uuid

    original_project_dir = workspace_result.get("original_project_dir")
    if not original_project_dir or not os.path.isdir(original_project_dir):
        raise FileNotFoundError(f"Original project folder is unavailable: {original_project_dir}")

    source_video = render_result.get("output_path")
    if not source_video or not os.path.isfile(source_video) or os.path.getsize(source_video) <= 0:
        raise RuntimeError(f"Private rendered video is missing or empty: {source_video}")

    publish_timeout = float(os.environ.get("VIDEO_PUBLISH_WAIT_TIMEOUT_SECONDS", "1800"))
    deadline = time.monotonic() + max(10.0, publish_timeout)
    edited_folder = os.path.join(original_project_dir, "edited")
    os.makedirs(edited_folder, exist_ok=True)
    lock_handle = _video_producer_acquire_project_publish_lock(
        edited_folder,
        timeout_seconds=max(1.0, deadline - time.monotonic()),
    )

    stage_paths = []
    backup_temp_path = None
    backup_final_path = None
    try:
        filename = os.path.basename(source_video)
        destination_video = os.path.join(edited_folder, filename)
        token = f"{os.getpid()}_{uuid.uuid4().hex}"
        stage_video = os.path.join(edited_folder, f".{filename}.incoming_{token}")
        stage_paths.append(stage_video)

        # Stage a complete copy on the destination volume before touching an
        # existing final file. The original remains intact until os.replace works.
        _video_producer_copy_file_isolated(
            source_video,
            stage_video,
            timeout_seconds=max(1.0, deadline - time.monotonic()),
        )

        if os.path.isfile(destination_video) and os.path.getsize(destination_video) > 0:
            stem, extension = os.path.splitext(filename)
            old_pattern = re.compile(rf"^{re.escape(stem)}_old_(\d+){re.escape(extension)}$", re.IGNORECASE)
            old_numbers = []
            for existing_name in os.listdir(edited_folder):
                match = old_pattern.match(existing_name)
                if match:
                    old_numbers.append(int(match.group(1)))
            next_number = max(old_numbers, default=0) + 1
            backup_final_path = os.path.join(edited_folder, f"{stem}_old_{next_number}{extension}")
            while os.path.exists(backup_final_path):
                next_number += 1
                backup_final_path = os.path.join(edited_folder, f"{stem}_old_{next_number}{extension}")
            backup_temp_path = backup_final_path + f".incoming_{token}"
            stage_paths.append(backup_temp_path)
            _video_producer_copy_file_isolated(
                destination_video,
                backup_temp_path,
                timeout_seconds=max(1.0, deadline - time.monotonic()),
            )

        _video_producer_replace_when_ready(stage_video, destination_video, deadline)
        if backup_temp_path and os.path.isfile(backup_temp_path):
            try:
                _video_producer_replace_when_ready(backup_temp_path, backup_final_path, deadline)
                backup_temp_path = None
            except Exception as backup_exc:
                # The new video is already published and the old file is safely
                # preserved in this pending backup. Do not report the whole job
                # as failed merely because its preferred backup name is busy.
                print(
                    f"⚠️ [PUBLISH] New video is saved, but the preserved old video "
                    f"could not be renamed to its numbered backup path: {backup_exc}"
                )
                backup_final_path = backup_temp_path
                if backup_temp_path in stage_paths:
                    stage_paths.remove(backup_temp_path)
                backup_temp_path = None

        # Publish the thumbnail too, but it is ancillary: a thumbnail lock must
        # not invalidate a correctly rendered and safely published MP4.
        private_thumbnail = render_result.get("thumbnail_path")
        destination_thumbnail = os.path.join(edited_folder, "Thumbnail.png")
        thumbnail_published = None
        if private_thumbnail and os.path.isfile(private_thumbnail) and os.path.getsize(private_thumbnail) > 0:
            stage_thumbnail = os.path.join(edited_folder, f".Thumbnail.png.incoming_{token}")
            stage_paths.append(stage_thumbnail)
            try:
                _video_producer_copy_file_isolated(
                    private_thumbnail,
                    stage_thumbnail,
                    timeout_seconds=max(1.0, deadline - time.monotonic()),
                )
                _video_producer_replace_when_ready(stage_thumbnail, destination_thumbnail, deadline)
                thumbnail_published = destination_thumbnail
            except Exception as thumbnail_exc:
                print(f"⚠️ [PUBLISH] Video published, but thumbnail could not be updated: {thumbnail_exc}")

        final_result = dict(render_result)
        final_result["output_folder"] = edited_folder
        final_result["output_path"] = destination_video
        final_result["thumbnail_path"] = thumbnail_published or (
            destination_thumbnail if os.path.isfile(destination_thumbnail) else None
        )
        final_result["backup_path"] = backup_final_path if backup_final_path and os.path.isfile(backup_final_path) else None
        final_result["private_output_path"] = source_video
        return final_result
    finally:
        for path in stage_paths:
            try:
                if path and os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
        _video_producer_release_project_publish_lock(lock_handle)

def _video_producer_process_worker(job):
    """Run one project entirely in a private workspace, then safely publish it."""
    import contextlib
    import os
    import shutil
    import tempfile
    import traceback
    import time

    title = job["project_title"]
    profile = dict(job.get("profile") or {})
    pid = os.getpid()
    log_path = job["log_path"]
    status_path = job["status_path"]
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    workspace_root = job.get("workspace_root") or os.path.join(os.path.dirname(log_path), "worker_workspaces")
    os.makedirs(workspace_root, exist_ok=True)
    workspace_path = None
    started_at = time.time()

    base_status = {
        "worker_id": job.get("worker_id", "worker"),
        "lane": str(job.get("lane", "unknown")).upper(),
        "pid": pid,
        "project_title": title,
        "status": "running",
        "stage": "Starting isolated worker",
        "progress": 0,
        "current": None,
        "total": None,
        "detail": "Preparing a private copy of all required project files",
        "started_at": started_at,
        "encoder": profile.get("video_encoder", "libx264"),
        "whisper_device": profile.get("whisper_device", "cpu"),
        "whisper_compute_type": profile.get("whisper_compute_type", "int8"),
        "log_path": log_path,
        "status_path": status_path,
    }
    with open(log_path, "a", encoding="utf-8", buffering=1):
        pass
    _video_producer_write_worker_status(status_path, base_status)

    final_status = "failed"
    result = None
    cleanup_workspace = False
    workspace_deleted = False
    try:
        with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
            with contextlib.redirect_stdout(worker_log), contextlib.redirect_stderr(worker_log):
                print("=" * 78)
                print(
                    f"[WORKER START] job={job.get('worker_id')} pid={pid} "
                    f"lane={str(job.get('lane', 'unknown')).upper()} project={title}"
                )
                print(
                    f"[WORKER PROFILE] whisper={profile.get('whisper_device', 'cpu')}/"
                    f"{profile.get('whisper_compute_type', 'int8')} | "
                    f"encoder={profile.get('video_encoder', 'libx264')} | "
                    f"preset={profile.get('encoder_preset')} | "
                    f"threads={profile.get('ffmpeg_threads')}"
                )
                print(f"[WORKER LOG] {log_path}")

                workspace_name = f"{job.get('worker_id', 'worker')}_pid_{pid}_"
                workspace_path = tempfile.mkdtemp(prefix=workspace_name, dir=workspace_root)
                print(f"[WORKSPACE] Private worker folder: {workspace_path}")
                _video_producer_write_worker_status(status_path, {
                    **base_status,
                    "stage": "Preparing private workspace",
                    "progress": 1,
                    "detail": f"Copying files into {workspace_path}",
                })

                workspace = _video_producer_prepare_worker_workspace(
                    job,
                    workspace_path,
                    status_path=status_path,
                    base_status=base_status,
                )
                if workspace.get("skip_reason"):
                    skip_reason = str(workspace.get("skip_reason"))
                    print(f"⏭️ [VIDEO-PREFLIGHT] Skipping '{title}': {skip_reason}")
                    final_status = "skipped"
                    result = {"project_title": title, "skipped": True, "skip_reason": skip_reason}
                    cleanup_workspace = True
                elif workspace.get("already_completed_output"):
                    existing_path = workspace["already_completed_output"]
                    print(f"⏭️ [READY-SCRIPT] Existing final video found; leaving it untouched: {existing_path}")
                    final_status = "completed"
                    result = {
                        "project_title": title,
                        "output_path": existing_path,
                        "already_existed": True,
                    }
                    cleanup_workspace = True
                else:
                    print(f"[WORKSPACE] Project files copied: {workspace.get('copy_summary')}")
                    print(f"[WORKSPACE] Private READY_SCRIPT: {workspace['ready_script_path']}")
                    print(f"[WORKSPACE] Private project root: {workspace['images_path']}")
                    print(f"[WORKSPACE] Private narration: {workspace.get('audio_path') or 'not found'}")
                    print(f"[WORKSPACE] Private stickers: {workspace.get('subscribe_stickers_path') or 'not configured'}")

                    result = process_single_video(
                        target_project_title=title,
                        target_project_category=job.get("project_category"),
                        ready_script_path=workspace["ready_script_path"],
                        images_path=workspace["images_path"],
                        subscribe_stickers_path=workspace.get("subscribe_stickers_path"),
                        whisper_device=profile.get("whisper_device", "cpu"),
                        whisper_compute_type=profile.get("whisper_compute_type", "int8"),
                        video_encoder=profile.get("video_encoder", "libx264"),
                        encoder_preset=profile.get("encoder_preset"),
                        ffmpeg_threads=profile.get("ffmpeg_threads", 2),
                        ffmpeg_binary=profile.get("ffmpeg_binary"),
                        worker_id=job.get("worker_id"),
                        worker_lane=job.get("lane"),
                        worker_status_path=status_path,
                        worker_log_path=log_path,
                        audio_path=workspace.get("audio_path"),
                        private_workspace_mode=True,
                    )

                    if isinstance(result, dict):
                        _video_producer_write_worker_status(status_path, {
                            **base_status,
                            "stage": "Waiting for original destination",
                            "progress": 98,
                            "detail": "Private render completed. Acquiring the original project's publish lock and waiting for the output path.",
                        })
                        print("[PUBLISH] Waiting for exclusive access to the original project's edited folder...")
                        published_result = _video_producer_publish_worker_outputs(job, workspace, result)
                        result = published_result
                        final_status = "completed"
                        cleanup_workspace = True
                        print(f"✅ [PUBLISH] Final video safely saved to: {result['output_path']}")
                        if result.get("backup_path"):
                            print(f"📦 [PUBLISH] Previous output preserved as: {result['backup_path']}")
                        if result.get("thumbnail_path"):
                            print(f"🖼️ [PUBLISH] Thumbnail saved to: {result['thumbnail_path']}")
                    else:
                        final_status = "skipped_or_failed"
                        print("⚠️ [WORKER] No final render was returned. The private workspace is being retained for inspection.")

                _video_producer_write_worker_status(status_path, {
                    **base_status,
                    "status": final_status,
                    "stage": "Completed" if final_status == "completed" else "Skipped / no output",
                    "progress": 100 if final_status == "completed" else None,
                    "current": 1 if final_status == "completed" else None,
                    "total": 1 if final_status == "completed" else None,
                    "detail": (
                        result.get("output_path") if isinstance(result, dict) and result.get("output_path")
                        else result.get("skip_reason") if isinstance(result, dict) and result.get("skip_reason")
                        else f"No output returned. Workspace retained at: {workspace_path}"
                    ),
                    "started_at": started_at,
                    "finished_at": time.time(),
                    "workspace_path": None if cleanup_workspace else workspace_path,
                })
                print(f"[WORKER {final_status.upper()}] {title}")

        if cleanup_workspace and workspace_path and os.path.isdir(workspace_path):
            try:
                shutil.rmtree(workspace_path)
                workspace_deleted = True
                with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
                    worker_log.write(f"[WORKSPACE] Temporary worker folder deleted: {workspace_path}\n")
            except Exception as cleanup_exc:
                # A cleanup failure does not undo the successfully published MP4.
                try:
                    with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
                        worker_log.write(f"\n⚠️ [WORKSPACE] Could not delete temporary folder '{workspace_path}': {cleanup_exc}\n")
                except OSError:
                    pass
                try:
                    current_state = _video_producer_read_worker_status(status_path)
                    _video_producer_write_worker_status(status_path, {
                        **current_state,
                        "workspace_path": workspace_path,
                        "detail": f"{current_state.get('detail', '')} | Temporary workspace could not be deleted: {workspace_path}",
                    })
                except Exception:
                    pass

        return {
            "project_title": title,
            "status": final_status,
            "result": result,
            "pid": pid,
            "lane": job.get("lane"),
            "worker_id": job.get("worker_id"),
            "log_path": log_path,
            "workspace_path": None if workspace_deleted else workspace_path,
        }
    except Exception as exc:
        error_traceback = traceback.format_exc()
        preserved_workspace = workspace_path if workspace_path and os.path.isdir(workspace_path) else None
        try:
            with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
                worker_log.write("\n[WORKER FAILED]\n")
                worker_log.write(error_traceback)
                if preserved_workspace:
                    worker_log.write(f"\n[WORKSPACE PRESERVED FOR RECOVERY] {preserved_workspace}\n")
        except Exception:
            pass
        try:
            _video_producer_write_worker_status(status_path, {
                **base_status,
                "status": "failed",
                "stage": "Failed",
                "detail": f"{exc} | workspace preserved: {preserved_workspace or 'not created'}",
                "started_at": started_at,
                "finished_at": time.time(),
                "workspace_path": preserved_workspace,
            })
        except Exception:
            pass
        return {
            "project_title": title,
            "status": "failed",
            "error": str(exc),
            "traceback": error_traceback,
            "pid": pid,
            "lane": job.get("lane"),
            "worker_id": job.get("worker_id"),
            "log_path": log_path,
            "workspace_path": preserved_workspace,
        }

def video_producer_main(cpu_workers=None, gpu_workers=None, max_projects=None):
    """Run projects concurrently and show all worker activity in one SceneIQ grid.

    Each worker has a private status file and log. A single GUI process reads
    those files and displays every project's progress in its own dashboard card.
    The production console is not used as the progress display.
    """
    import os
    import json
    import time
    import datetime
    import multiprocessing
    import traceback
    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
    from contextlib import ExitStack

    ready_script_path = globals().get("READY_SCRIPT")
    images_path = globals().get("IMAGES_PATH")
    subscribe_stickers_path = globals().get("SUBSCRIBE_STICKERS")
    if not ready_script_path or not images_path:
        raise RuntimeError(
            "video_producer_main requires module-level READY_SCRIPT and IMAGES_PATH."
        )

    ready_script_path = os.path.abspath(os.fspath(ready_script_path))
    images_path = os.path.abspath(os.fspath(images_path))
    subscribe_stickers_path = (
        os.path.abspath(os.fspath(subscribe_stickers_path))
        if subscribe_stickers_path else None
    )
    if not os.path.isfile(ready_script_path):
        raise FileNotFoundError(f"READY_SCRIPT not found: {ready_script_path}")
    if not os.path.isdir(images_path):
        raise NotADirectoryError(f"IMAGES_PATH not found: {images_path}")

    configured_log_root = os.environ.get("VIDEO_PRODUCER_LOG_DIR")
    if configured_log_root:
        log_root = os.path.abspath(os.path.expanduser(configured_log_root))
    else:
        log_root = os.path.join(os.path.dirname(ready_script_path), "video_producer_runs")
    run_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(log_root, f"run_{run_stamp}_parent_{os.getpid()}")
    os.makedirs(run_dir, exist_ok=True)

    # Capture one stable source-JSON snapshot for this run. Every worker then
    # copies this snapshot into its own private folder and reads only that copy.
    source_snapshot_dir = os.path.join(run_dir, "source_snapshot")
    ready_script_snapshot_path = os.path.join(source_snapshot_dir, "ready_script_snapshot.json")
    _video_producer_copy_file_isolated(
        ready_script_path,
        ready_script_snapshot_path,
        timeout_seconds=float(os.environ.get("VIDEO_WORKSPACE_COPY_TIMEOUT_SECONDS", "900")),
    )
    project_records = _video_producer_collect_ready_titles(ready_script_snapshot_path)
    if max_projects is not None:
        project_records = project_records[:max(0, int(max_projects))]
    project_titles = [record["project_title"] for record in project_records]
    project_categories = [
        record.get("project_category") for record in project_records
    ]
    if not project_titles:
        try:
            import shutil
            shutil.rmtree(source_snapshot_dir, ignore_errors=True)
        except Exception:
            pass
        return {
            "total": 0,
            "completed": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
            "log_directory": run_dir,
        }

    gpu_info = _video_producer_detect_gpu()
    cpu_total = max(1, int(os.cpu_count() or 2))
    if cpu_workers is None:
        env_value = os.environ.get("VIDEO_CPU_WORKERS")
        cpu_workers = int(env_value) if env_value else max(1, min(4, cpu_total // 2))
    cpu_workers = max(1, min(int(cpu_workers), len(project_titles)))

    if gpu_workers is None:
        env_value = os.environ.get("VIDEO_GPU_WORKERS")
        gpu_workers = int(env_value) if env_value is not None else (1 if gpu_info["gpu_available"] else 0)
    gpu_workers = max(0, int(gpu_workers))
    if gpu_workers and not gpu_info["gpu_available"]:
        gpu_workers = 0
    gpu_workers = min(gpu_workers, len(project_titles))

    if gpu_workers:
        gpu_whisper_device = "cuda" if gpu_info["cuda_available"] else "cpu"
        gpu_whisper_compute = "float16" if gpu_info["cuda_available"] else "int8"
        gpu_encoder = "h264_nvenc" if gpu_info["nvenc_available"] else "libx264"
        gpu_preset = os.environ.get(
            "VIDEO_GPU_PRESET",
            "p5" if gpu_encoder == "h264_nvenc" else "medium",
        )
        gpu_profile = {
            "whisper_device": gpu_whisper_device,
            "whisper_compute_type": gpu_whisper_compute,
            "video_encoder": gpu_encoder,
            "encoder_preset": gpu_preset,
            "ffmpeg_threads": max(1, min(2, cpu_total // max(1, cpu_workers + gpu_workers))),
            "ffmpeg_binary": gpu_info["ffmpeg_binary"],
        }
    else:
        gpu_profile = None

    cpu_profile = {
        "whisper_device": "cpu",
        "whisper_compute_type": os.environ.get("VIDEO_CPU_WHISPER_COMPUTE", "int8"),
        "video_encoder": "libx264",
        "encoder_preset": os.environ.get("VIDEO_CPU_PRESET", "slow"),
        "ffmpeg_threads": max(1, min(4, cpu_total // max(1, cpu_workers))),
        "ffmpeg_binary": None,
    }

    lane_pattern = (["gpu"] * gpu_workers) + (["cpu"] * cpu_workers)
    cpu_jobs, gpu_jobs, all_jobs = [], [], []
    cpu_index = 0
    gpu_index = 0
    for project_index, title in enumerate(project_titles):
        lane = lane_pattern[len(all_jobs) % len(lane_pattern)]
        if lane == "gpu":
            gpu_index += 1
            lane_job_id = f"GPU-{gpu_index:03d}"
            profile = gpu_profile
        else:
            cpu_index += 1
            lane_job_id = f"CPU-{cpu_index:03d}"
            profile = cpu_profile
        job = {
            "project_title": title,
            "project_category": project_categories[project_index] if project_index < len(project_categories) else None,
            "ready_script_path": ready_script_snapshot_path,
            "images_path": images_path,
            "subscribe_stickers_path": subscribe_stickers_path,
            "workspace_root": os.path.join(run_dir, "worker_workspaces"),
            "profile": dict(profile or {}),
            "lane": lane,
            "worker_id": lane_job_id,
            "queued_at": time.time(),
        }
        (gpu_jobs if lane == "gpu" else cpu_jobs).append(job)
        all_jobs.append(job)

    # Calculate the resource budget from the process count that will actually run.
    effective_cpu_workers = min(cpu_workers, len(cpu_jobs))
    effective_gpu_workers = min(gpu_workers, len(gpu_jobs))
    if cpu_jobs:
        cpu_thread_budget = max(1, min(4, cpu_total // max(1, effective_cpu_workers)))
        for job in cpu_jobs:
            job["profile"]["ffmpeg_threads"] = cpu_thread_budget
    if gpu_jobs:
        gpu_thread_budget = max(1, min(2, cpu_total // max(1, effective_cpu_workers + effective_gpu_workers)))
        for job in gpu_jobs:
            job["profile"]["ffmpeg_threads"] = gpu_thread_budget

    for job in all_jobs:
        safe_title = _video_producer_normalize_title(job["project_title"])
        filename_base = f"{job['worker_id']}_{safe_title[:70]}"
        job["log_path"] = os.path.join(run_dir, filename_base + ".log")
        job["status_path"] = os.path.join(run_dir, filename_base + ".status.json")
        _video_producer_write_worker_status(job["status_path"], {
            "worker_id": job["worker_id"],
            "lane": job["lane"].upper(),
            "pid": None,
            "project_title": job["project_title"],
            "status": "queued",
            "stage": "Waiting for a process slot",
            "progress": None,
            "current": None,
            "total": None,
            "detail": f"Assigned to {job['lane'].upper()} lane; a private worker workspace will be created",
            "queued_at": job["queued_at"],
            "log_path": job["log_path"],
            "status_path": job["status_path"],
            "encoder": job["profile"].get("video_encoder"),
            "whisper_device": job["profile"].get("whisper_device"),
            "whisper_compute_type": job["profile"].get("whisper_compute_type"),
        })

    # One manifest describes the complete run. The single GUI process reads every
    # worker status/log file and renders one grid card per project.
    dashboard_manifest_path = os.path.join(run_dir, "dashboard_manifest.json")
    dashboard_manifest = {
        "window_title": "SceneIQ Video Production",
        "created_at": time.time(),
        "run_directory": run_dir,
        "jobs": [
            {
                "worker_id": job["worker_id"],
                "project_title": job["project_title"],
                "lane": job["lane"],
                "encoder": job["profile"].get("video_encoder"),
                "status_path": job["status_path"],
                "log_path": job["log_path"],
            }
            for job in all_jobs
        ],
    }
    with open(dashboard_manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(dashboard_manifest, manifest_file, ensure_ascii=False, indent=2)

    dashboard_pid = None
    dashboard_launch_error = None
    try:
        dashboard_pid = _video_producer_launch_dashboard_window(dashboard_manifest_path)
    except Exception as dashboard_exc:
        dashboard_launch_error = str(dashboard_exc)
    if dashboard_pid:
        dashboard_manifest["dashboard_pid"] = dashboard_pid
        with open(dashboard_manifest_path, "w", encoding="utf-8") as manifest_file:
            json.dump(dashboard_manifest, manifest_file, ensure_ascii=False, indent=2)
    elif dashboard_launch_error or os.name != "nt":
        # Keep GUI launch diagnostics out of the shared production console.
        diagnostic_path = os.path.join(run_dir, "dashboard-launch-error.log")
        with open(diagnostic_path, "a", encoding="utf-8") as diagnostic_file:
            if dashboard_launch_error:
                diagnostic_file.write(f"Could not launch the single SceneIQ dashboard: {dashboard_launch_error}\n")
            else:
                diagnostic_file.write("The SceneIQ GUI dashboard is configured for Windows only.\n")

    results = []
    process_context = multiprocessing.get_context("spawn")
    with ExitStack() as stack:
        cpu_pool = None
        gpu_pool = None
        if cpu_jobs:
            cpu_pool = stack.enter_context(ProcessPoolExecutor(
                max_workers=effective_cpu_workers,
                mp_context=process_context,
            ))
        if gpu_jobs:
            gpu_pool = stack.enter_context(ProcessPoolExecutor(
                max_workers=effective_gpu_workers,
                mp_context=process_context,
            ))

        future_to_job = {}
        for job in cpu_jobs:
            future_to_job[cpu_pool.submit(_video_producer_process_worker, job)] = job
        for job in gpu_jobs:
            future_to_job[gpu_pool.submit(_video_producer_process_worker, job)] = job

        pending = set(future_to_job)
        while pending:
            done, pending = wait(pending, timeout=1.0, return_when=FIRST_COMPLETED)
            for future in done:
                job = future_to_job[future]
                try:
                    item_result = future.result()
                except Exception as exc:
                    error_traceback = traceback.format_exc()
                    item_result = {
                        "project_title": job["project_title"],
                        "status": "failed",
                        "error": str(exc),
                        "traceback": error_traceback,
                        "lane": job["lane"],
                        "worker_id": job["worker_id"],
                        "log_path": job["log_path"],
                    }
                    try:
                        with open(job["log_path"], "a", encoding="utf-8", buffering=1) as worker_log:
                            worker_log.write("\n[PARENT WORKER FAILURE]\n")
                            worker_log.write(error_traceback)
                    except OSError:
                        pass
                    previous_state = _video_producer_read_worker_status(job["status_path"])
                    _video_producer_write_worker_status(job["status_path"], {
                        **previous_state,
                        "worker_id": job["worker_id"],
                        "lane": job["lane"].upper(),
                        "project_title": job["project_title"],
                        "status": "failed",
                        "stage": "Worker process failed",
                        "progress": None,
                        "detail": str(exc),
                        "log_path": job["log_path"],
                        "status_path": job["status_path"],
                        "finished_at": time.time(),
                    })
                results.append(item_result)

    completed = sum(item.get("status") == "completed" for item in results)
    failed = sum(item.get("status") == "failed" for item in results)
    skipped = len(results) - completed - failed
    try:
        import shutil
        if os.path.isdir(source_snapshot_dir):
            shutil.rmtree(source_snapshot_dir)
    except OSError:
        pass
    return {
        "total": len(project_titles),
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "results": results,
        "log_directory": run_dir,
        "gpu_available": gpu_info["gpu_available"],
        "cuda_available": gpu_info["cuda_available"],
        "nvenc_available": gpu_info["nvenc_available"],
        "cpu_workers": effective_cpu_workers,
        "gpu_workers": effective_gpu_workers,
    }

def video_producer():
    """Backward-compatible entry point; now launches parallel bulk production."""
    return video_producer_main()


def video_producer_service_loop(poll_interval=2.0, retry_interval=60.0):
    """Continuously detect newly ready projects without rebuilding empty batches."""
    poll_interval = max(1.0, float(poll_interval or 2.0))
    retry_interval = max(10.0, float(retry_interval or 60.0))
    last_input_signature = None
    last_batch_at = 0.0
    print("🎞️ [VIDEO-SERVICE] Independent video producer service started.")

    def current_input_signature():
        ready_path = os.path.abspath(os.fspath(READY_SCRIPT))
        try:
            ready_stat = os.stat(ready_path)
            ready_signature = (ready_stat.st_mtime_ns, ready_stat.st_size)
        except OSError:
            ready_signature = (None, None)
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        try:
            downloads_stat = os.stat(downloads_path)
            downloads_signature = (downloads_stat.st_mtime_ns, downloads_stat.st_size)
        except OSError:
            downloads_signature = (None, None)
        # Detect late-arriving entry images inside category/project directories.
        newest_project_directory_mtime = 0
        try:
            if os.path.isdir(IMAGES_PATH):
                for directory, subdirectories, _ in os.walk(IMAGES_PATH):
                    try:
                        newest_project_directory_mtime = max(
                            newest_project_directory_mtime,
                            os.stat(directory).st_mtime_ns,
                        )
                    except OSError:
                        continue
        except OSError:
            pass
        return ready_signature, downloads_signature, newest_project_directory_mtime

    while True:
        try:
            signature = current_input_signature()
            now = time.monotonic()
            inputs_changed = signature != last_input_signature
            retry_due = now - last_batch_at >= retry_interval
            if inputs_changed or retry_due:
                last_input_signature = signature
                last_batch_at = now
                result = video_producer_main()
                if isinstance(result, dict):
                    print(
                        "🎞️ [VIDEO-SERVICE] Batch finished: "
                        f"total={result.get('total', 0)}, completed={result.get('completed', 0)}, "
                        f"skipped={result.get('skipped', 0)}, failed={result.get('failed', 0)}"
                    )
        except KeyboardInterrupt:
            print("🛑 [VIDEO-SERVICE] KeyboardInterrupt received; video service is stopping.")
            raise
        except Exception as video_error:
            # Video failures never stop the image producer or the shared process.
            print(f"❌ [VIDEO-SERVICE] This video batch failed independently: {video_error}")
            traceback.print_exc()
            last_batch_at = time.monotonic()
        time.sleep(poll_interval)


def main():
    """Run only the independent video-producer service in this process."""
    print("\n" + "=" * 72)
    print("🚀 SCENEIQ VIDEO PRODUCER — STANDALONE")
    print("=" * 72)
    print(f"📄 READY_SCRIPT: {READY_SCRIPT}")
    print(f"📁 IMAGES_PATH: {IMAGES_PATH}")
    print("ℹ️ Google Flow image generation is not started or imported by this script.")
    video_producer_service_loop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
