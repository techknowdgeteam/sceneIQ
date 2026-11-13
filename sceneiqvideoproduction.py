"""SceneIQ standalone video producer.
sceneiqvideoproduction.py
This single file contains both the video renderer and its isolated dashboard mode.
Google Flow image generation lives in
sceniqimageproduction.py and is not imported or started here.
"""

import os
import re
import time
import traceback
import multiprocessing
import hashlib

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
    control_path=None,
    shutdown_path=None,
    dashboard_heartbeat_path=None,
    checkpoint_dir=None,
    parent_pid=None,
    preview_image_path=None,
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
    checkpoint_dir = _awake_os.path.abspath(checkpoint_dir) if checkpoint_dir else None
    if checkpoint_dir:
        _awake_os.makedirs(checkpoint_dir, exist_ok=True)

    # A per-job JPG is atomically refreshed from frames produced by MoviePy's
    # actual scene renderer. The desktop reads this shared file independently;
    # preview failures are deliberately non-fatal to encoding.
    if preview_image_path:
        preview_image_path = _awake_os.path.abspath(_awake_os.fspath(preview_image_path))
    elif worker_status_path:
        _preview_worker_key = re.sub(r"[^A-Za-z0-9_-]+", "_", str(worker_id or "worker"))
        preview_image_path = _awake_os.path.join(
            _awake_os.path.dirname(_awake_os.path.abspath(worker_status_path)),
            "previews", f"{_preview_worker_key}.jpg",
        )
    else:
        preview_image_path = None

    def _check_worker_control(stage=None, detail=None):
        _video_producer_control_checkpoint(
            control_path=control_path,
            status_path=worker_status_path,
            project_title=target_project_title,
            stage=stage,
            detail=detail,
            shutdown_path=shutdown_path,
            heartbeat_path=dashboard_heartbeat_path,
            parent_pid=parent_pid,
            checkpoint_dir=checkpoint_dir,
        )

    def _set_worker_status(
        stage,
        progress=None,
        current=None,
        total=None,
        detail=None,
        status="running",
    ):
        if status == "running":
            _check_worker_control(stage=stage, detail=detail)
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
            "preview_path": preview_image_path,
        }
        try:
            _video_producer_write_worker_status(worker_status_path, payload)
        except Exception as status_exc:
            # Monitoring must never interrupt video production.
            print(f"⚠️ [WORKER-STATUS] Could not update status file: {status_exc}")
        if checkpoint_dir:
            try:
                progress_snapshot = {
                    key: payload.get(key)
                    for key in (
                        "worker_id", "project_title", "status", "stage", "progress",
                        "current", "total", "detail", "updated_at", "encoder",
                        "whisper_device", "whisper_compute_type",
                    )
                }
                _video_producer_write_json_atomic(
                    _awake_os.path.join(checkpoint_dir, "progress.json"),
                    progress_snapshot,
                )
            except Exception as checkpoint_exc:
                print(f"⚠️ [CHECKPOINT] Could not save progress snapshot: {checkpoint_exc}")

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
    else:
        # Do not let a previous GPU-lane job leak its FFmpeg path into a CPU job.
        _awake_os.environ.pop("FFMPEG_BINARY", None)

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
        # This nested function intentionally reuses and may initialize the
        # checkpoint directory supplied by process_single_video().  Declaring
        # it nonlocal prevents Python from treating it as an uninitialized local
        # when the early checkpoint-cache checks run above the fallback assignment.
        nonlocal checkpoint_dir
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
        # Initialize output dimensions before any checkpoint fingerprint, cache,
        # validation, or render helper can read them. The original solo producer
        # used this exact fixed 16:9 output size; the service wrapper must not
        # change its initialization order.
        video_width, video_height = 1920, 1080
        # Import from MoviePy's public package namespace (MoviePy 2.x).
        try:
            from moviepy import VideoClip, AudioFileClip, VideoFileClip, concatenate_videoclips
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
        _set_worker_status(
            "Reading the story and its scene instructions",
            progress=2,
            detail="Checking the script, scene order, timings, transition directions and caption settings.",
        )
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
            return _video_producer_find_audio_source(title)
        _set_worker_status(
            "Finding the narration audio",
            progress=4,
            detail=f"Looking in Downloads for the narration file matching: {project_title}",
        )
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
        _set_worker_status(
            "Checking the narration audio",
            progress=5,
            detail=f"Opening {os.path.basename(audio_file_path)} and checking its duration and audio stream.",
        )
        print(f"🎵 Found verified narration audio: {os.path.basename(audio_file_path)}")
        render_fingerprint = None
        render_segments_dir = None
        if checkpoint_dir:
            import hashlib
            fingerprint_images = []
            for item in image_files:
                try:
                    stat = os.stat(item["path"])
                    fingerprint_images.append((
                        item["filename"], stat.st_size,
                        getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9)),
                    ))
                except OSError:
                    fingerprint_images.append((item["filename"], -1, -1))
            try:
                audio_stat = os.stat(audio_file_path)
                audio_signature = (
                    os.path.basename(audio_file_path), audio_stat.st_size,
                    getattr(audio_stat, "st_mtime_ns", int(audio_stat.st_mtime * 1e9)),
                )
            except OSError:
                audio_signature = (os.path.basename(audio_file_path), -1, -1)
            fingerprint_payload = {
                "project_title": project_title,
                "project_category": target_project_category,
                "script_entries": selected_script_data,
                "images": fingerprint_images,
                "audio": audio_signature,
                "include_captions": include_captions,
                "include_transitions": include_transitions,
                "encoder": video_encoder,
                "encoder_preset": encoder_preset,
                "video_width": video_width,
                "video_height": video_height,
                "fps": 24,
                "whisper_model": os.environ.get("WHISPER_MODEL", "small"),
            }
            encoded_fingerprint = json.dumps(
                fingerprint_payload, ensure_ascii=False, sort_keys=True, default=str
            ).encode("utf-8")
            render_fingerprint = hashlib.sha256(encoded_fingerprint).hexdigest()
            render_segments_dir = os.path.join(checkpoint_dir, "scene_segments")
            fingerprint_path = os.path.join(checkpoint_dir, "render_fingerprint.json")
            previous_fingerprint = _video_producer_read_json(fingerprint_path, {})
            if not isinstance(previous_fingerprint, dict) or previous_fingerprint.get("fingerprint") != render_fingerprint:
                if os.path.isdir(render_segments_dir):
                    shutil.rmtree(render_segments_dir, ignore_errors=True)
                os.makedirs(render_segments_dir, exist_ok=True)
                _video_producer_write_json_atomic(
                    fingerprint_path,
                    {"fingerprint": render_fingerprint, "updated_at": time.time()},
                )
                print("🧹 [CHECKPOINT] Project inputs changed; old scene segments were invalidated.")
            else:
                os.makedirs(render_segments_dir, exist_ok=True)
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
                detail="Building one-row typewriter captions from narration, matching each word to its spoken time, and preparing any Stage/Step/Level headings.",
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

        cached_audio_words = []
        asr_cache_path = None
        asr_cache_key = None
        if checkpoint_dir and audio_file_path and os.path.isfile(audio_file_path):
            import hashlib
            audio_stat = os.stat(audio_file_path)
            asr_cache_key = hashlib.sha256(
                f"{os.path.basename(audio_file_path)}|{audio_stat.st_size}|{getattr(audio_stat, 'st_mtime_ns', int(audio_stat.st_mtime * 1e9))}|{os.environ.get('WHISPER_MODEL', 'small')}|{os.environ.get('WHISPER_DEVICE', 'cpu')}|{os.environ.get('WHISPER_COMPUTE_TYPE', 'int8')}".encode("utf-8")
            ).hexdigest()
            asr_cache_path = os.path.join(checkpoint_dir, "narration_word_timestamps.json")
            cached_payload = _video_producer_read_json(asr_cache_path, {})
            if isinstance(cached_payload, dict) and cached_payload.get("cache_key") == asr_cache_key:
                cached_audio_words = cached_payload.get("words") or []
                if isinstance(cached_audio_words, list):
                    print(f"♻️ [CHECKPOINT] Reusing {len(cached_audio_words)} saved narration word timestamps.")
                else:
                    cached_audio_words = []
        if include_captions or has_overlay_metadata:
            _set_worker_status(
                "Recognising the narration",
                progress=10 if cached_audio_words else 0,
                detail=(
                    f"Reusing {len(cached_audio_words)} saved speech word timestamps."
                    if cached_audio_words else
                    "Running speech recognition on the narration and recording the exact time of every spoken word."
                ),
            )
            # One ASR pass supplies word-level timing for captions and for dynamic
            # Stage/Step/Level/Example/Chapter overlays. Overlay timing is still available
            # when ordinary captions are switched OFF.
            audio_words = list(cached_audio_words)
            if audio_file_path and os.path.isfile(audio_file_path) and not audio_words:
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
                        _check_worker_control(
                            stage="Recognising the narration",
                            detail="Reading the next portion of speech and saving its word timestamps.",
                        )
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
                    if asr_cache_path and asr_cache_key:
                        _video_producer_write_json_atomic(
                            asr_cache_path,
                            {
                                "cache_key": asr_cache_key,
                                "audio_file": os.path.basename(audio_file_path),
                                "word_count": len(audio_words),
                                "saved_at": time.time(),
                                "words": audio_words,
                            },
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
        # Force the finished video and every scene image to the solo producer's
        # fixed 16:9 frame. The dimensions were initialized at function entry so
        # the earlier render-fingerprint logic can safely use them.
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
            """Normalize whitespace without separating currency or number punctuation."""
            value = re.sub(r"\s+", " ", str(value or "").strip())
            value = re.sub(r"([$£€¥₹])\s+(?=\d)", r"\1", value)
            value = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", value)
            value = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", value)
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

            def _normalize_caption_numeric_spacing(value):
                """Keep currency symbols, thousands separators and decimals contiguous."""
                value = str(value or "").strip()
                value = re.sub(r"([$£€¥₹])\s+(?=\d)", r"\1", value)
                value = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", value)
                value = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", value)
                return value

            def _merge_caption_recognition_tokens(source_tokens):
                """Join ASR-split punctuation/currency fragments without changing speech timing."""
                merged = []
                currency_symbols = {"$", "£", "€", "¥", "₹"}
                numeric_pattern = re.compile(r"^(?:[$£€¥₹])?\d[\d,]*(?:\.\d*)?$")
                for source_index, source_token in enumerate(source_tokens):
                    token = dict(source_token) if isinstance(source_token, dict) else {"word": str(source_token)}
                    word = _normalize_caption_numeric_spacing(token.get("word", ""))
                    if not word:
                        continue
                    if merged:
                        previous = merged[-1]
                        previous_word = str(previous.get("word", ""))
                        previous_numeric = bool(numeric_pattern.fullmatch(previous_word))
                        current_is_punctuation = bool(re.fullmatch(r"[,.;:!?%‰]+", word))
                        current_numeric_fragment = bool(re.match(r"^[,.]\d+", word))
                        previous_has_numeric_tail = bool(re.search(r"\d[,.]?$", previous_word))
                        previous_ends_separator = bool(re.search(r"[,.]$", previous_word))
                        previous_is_currency = previous_word in currency_symbols
                        previous_currency_amount = bool(re.fullmatch(r"[$£€¥₹]\d+", previous_word))
                        current_is_digits = bool(re.fullmatch(r"\d+", word))
                        join_token = False
                        separator_for_split_thousands = False

                        if previous_is_currency and current_is_digits:
                            join_token = True
                        elif current_is_punctuation and previous_word not in currency_symbols:
                            # Attach commas/periods/sentence punctuation to the
                            # preceding word; the next spoken word still receives
                            # its normal inter-word space.
                            join_token = True
                        elif previous_numeric and previous_has_numeric_tail and current_numeric_fragment:
                            join_token = True
                        elif previous_ends_separator and current_is_digits and previous_numeric:
                            join_token = True
                        elif previous_currency_amount and current_is_digits:
                            # Some ASR models split "$1,000" into "$1" + "000"
                            # and omit the comma token entirely. Preserve the
                            # conventional grouped amount when the suffix is 3 digits.
                            previous_digits = re.sub(r"[^0-9]", "", previous_word)
                            if len(previous_digits) in (1, 2, 3) and len(word) == 3:
                                join_token = True
                                separator_for_split_thousands = True

                        if join_token:
                            previous["word"] = _normalize_caption_numeric_spacing(
                                previous_word + (("," if separator_for_split_thousands else "") + word)
                            )
                            try:
                                previous["end"] = max(
                                    float(previous.get("end", previous.get("start", 0.0))),
                                    float(token.get("end", token.get("start", 0.0))),
                                )
                            except (TypeError, ValueError):
                                previous["end"] = token.get("end", previous.get("end"))
                            previous.setdefault("_source_indices", []).append(source_index)
                            continue

                    token["word"] = word
                    token["_source_indices"] = [source_index]
                    merged.append(token)
                return merged

            caption_tokens = _merge_caption_recognition_tokens(recognized_words)
            measure_canvas = Image.new("RGB", (frame_width, 100))
            measure_draw = ImageDraw.Draw(measure_canvas)
            # IMPORTANT: original font-size calculation is unchanged.
            font_size = max(24, min(64, int(frame_width / 35)))
            font = load_font(font_size)
            max_text_width = int(frame_width * 0.84)
            rows = []
            token_total = max(1, len(caption_tokens))
            for token_index, token in enumerate(caption_tokens):
                source_indices = token.get("_source_indices", [token_index])
                # Stage-heading suppression is indexed against the original ASR
                # words. A merged amount/punctuation token is skipped only when
                # every constituent ASR token is suppressed.
                if source_indices and all(index in suppressed_word_indices for index in source_indices):
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
            detail=f"Opening each of the {count} scene images, fitting it to the video frame, and loading its camera-motion and transition instructions.",
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
                detail=f"Prepared scene image {index + 1} of {count}: {image_info['filename']}.",
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

            # Publish occasional final-composited frames into a small preview JPG.
            # The preview comes from the same frame function that MoviePy encodes,
            # so it shows the real camera motion, transitions, captions, stickers
            # and instructional overlays rather than a placeholder source image.
            _preview_publish_state = {"last_saved": 0.0, "scene_number": None, "warned": False}
            _preview_publish_lock = _awake_threading.Lock()

            def _publish_live_scene_preview(frame_image, scene_number):
                if not preview_image_path:
                    return
                now = _worker_time.monotonic()
                with _preview_publish_lock:
                    scene_changed = _preview_publish_state["scene_number"] != int(scene_number)
                    if not scene_changed and now - _preview_publish_state["last_saved"] < 0.85:
                        return
                    temporary_preview = preview_image_path + f".tmp_{_awake_os.getpid()}.jpg"
                    try:
                        _awake_os.makedirs(_awake_os.path.dirname(preview_image_path), exist_ok=True)
                        preview_image = frame_image.convert("RGB")
                        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                        preview_image.thumbnail((640, 360), resampling)
                        preview_image.save(temporary_preview, format="JPEG", quality=78, optimize=False)
                        _awake_os.replace(temporary_preview, preview_image_path)
                        _preview_publish_state["last_saved"] = now
                        _preview_publish_state["scene_number"] = int(scene_number)
                    except Exception as preview_exc:
                        try:
                            if _awake_os.path.isfile(temporary_preview):
                                _awake_os.remove(temporary_preview)
                        except OSError:
                            pass
                        if not _preview_publish_state["warned"]:
                            _preview_publish_state["warned"] = True
                            print(
                                f"⚠️ [LIVE-PREVIEW] Could not refresh the visual preview; "
                                f"video rendering will continue: {type(preview_exc).__name__}: {preview_exc}"
                            )

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
                    detail=f"Creating the animated captions and timed headings from {len(audio_words)} recognised narration words.",
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
                _last_frame_control_check = {"at": 0.0}
                current_scene_number = scene_index + 1
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
                    if _worker_time.monotonic() - _last_frame_control_check["at"] >= 0.75:
                        _check_worker_control(
                            stage=f"Rendering scene {current_scene_number} of {len(prepared)}",
                            detail=f"Rendering camera movement, transition, captions and overlays for scene {current_scene_number}/{len(prepared)}.",
                        )
                        _last_frame_control_check["at"] = _worker_time.monotonic()
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
                    # Capture a sampled, final-composited frame for this video's
                    # dashboard preview. This operation is throttled and cannot
                    # interrupt the actual frame return/encoding path.
                    _publish_live_scene_preview(rendered, current_scene_number)
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
            # Each scene is encoded as its own durable MP4 segment. A completed
            # scene is atomically checkpointed and reused after pause, stop, crash,
            # or machine restart. Only the interrupted scene needs to be rendered again.
            if not checkpoint_dir:
                # Keep a durable location even for callers that invoke this function
                # outside the normal worker scheduler.
                checkpoint_dir = os.path.join(project_folder, ".video_producer_checkpoint")
                os.makedirs(checkpoint_dir, exist_ok=True)
                render_segments_dir = os.path.join(checkpoint_dir, "scene_segments")
            os.makedirs(render_segments_dir, exist_ok=True)

            render_started = time.monotonic()
            if video_encoder == "h264_nvenc":
                active_encoder_preset = encoder_preset or "p5"
                active_ffmpeg_params = [
                    "-rc", "vbr", "-cq:v", "18", "-b:v", "0",
                    "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
                    "-movflags", "+faststart", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709",
                ]
            else:
                active_encoder_preset = encoder_preset or "slow"
                active_ffmpeg_params = [
                    "-crf", "16", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-level", "4.1",
                    "-movflags", "+faststart", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709",
                ]
            active_encoder_threads = ffmpeg_threads or max(1, min(8, os.cpu_count() or 2))
            print(
                f"🎛️ [ENCODER] {video_encoder} | preset={active_encoder_preset} | "
                f"threads={active_encoder_threads}"
            )

            from proglog import ProgressBarLogger

            def segment_is_valid(segment_path):
                if not os.path.isfile(segment_path):
                    return False
                try:
                    if os.path.getsize(segment_path) < 1024:
                        return False
                    probe = VideoFileClip(segment_path, audio=False)
                    try:
                        return bool(probe.duration and probe.duration > 0 and tuple(probe.size or ()) == (video_width, video_height))
                    finally:
                        probe.close()
                except Exception:
                    return False

            completed_segments = []
            scene_count = max(1, len(clips))

            class _SceneSegmentProgressLogger(ProgressBarLogger):
                def __init__(self, scene_number, existing_count, scene_total):
                    super().__init__(logged_bars=[])
                    self.scene_number = scene_number
                    self.existing_count = existing_count
                    self.scene_total = scene_total
                    self._last_emit = 0.0
                    self._last_percent = -1

                def bars_callback(self, bar, attr, value, old_value=None):
                    if attr not in {"index", "total"}:
                        return
                    normalized_bar = str(bar).casefold()
                    if normalized_bar not in {"frame_index", "chunk"}:
                        return
                    _check_worker_control(
                        stage=f"Rendering scene {self.scene_number} of {scene_count}",
                        detail=f"Rendering the movement, transition, captions and overlays for scene {self.scene_number}/{scene_count}.",
                    )
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
                    segment_percent = current_int / total_int
                    overall_percent = ((self.existing_count + segment_percent) / scene_count) * 94.0
                    percent = round(overall_percent, 1)
                    now = _worker_time.monotonic()
                    if percent < self._last_percent + 0.3 and now - self._last_emit < 0.75:
                        return
                    self._last_emit = now
                    self._last_percent = percent
                    _set_worker_status(
                        f"Rendering scene {self.scene_number} of {scene_count}",
                        progress=percent,
                        current=self.scene_number,
                        total=scene_count,
                        detail=(
                            f"Encoding scene {self.scene_number}/{scene_count}: "
                            f"{current_int:,}/{total_int:,} frames. "
                            "This includes camera movement, transitions, captions and visual overlays."
                        ),
                    )

            for scene_index, scene_clip in enumerate(clips):
                scene_number = scene_index + 1
                segment_path = os.path.join(render_segments_dir, f"scene_{scene_number:05d}.mp4")
                temporary_segment = segment_path + f".partial_{os.getpid()}.mp4"
                _check_worker_control(
                    stage=f"Checking saved scene {scene_number} of {scene_count}",
                    detail=f"Checking whether scene {scene_number}/{scene_count} has already been rendered and saved.",
                )
                if segment_is_valid(segment_path):
                    completed_segments.append(segment_path)
                    # Also preview cached scenes so a resumed job does not leave
                    # a stale frame from an earlier scene/run on its card.
                    if preview_image_path:
                        cached_preview_clip = None
                        try:
                            cached_preview_clip = VideoFileClip(segment_path, audio=False)
                            cached_preview_time = min(0.35, max(0.0, float(cached_preview_clip.duration or 0.0) * 0.5))
                            cached_preview_frame = Image.fromarray(
                                np.asarray(cached_preview_clip.get_frame(cached_preview_time), dtype=np.uint8)
                            )
                            _publish_live_scene_preview(cached_preview_frame, scene_number)
                        except Exception as cached_preview_exc:
                            print(f"⚠️ [LIVE-PREVIEW] Could not preview cached scene {scene_number}: {cached_preview_exc}")
                        finally:
                            if cached_preview_clip is not None:
                                try:
                                    cached_preview_clip.close()
                                except Exception:
                                    pass
                    print(f"♻️ [CHECKPOINT] Reusing completed scene {scene_number}/{scene_count}: {segment_path}")
                    _set_worker_status(
                        f"Reusing saved scene {scene_number} of {scene_count}",
                        progress=round((len(completed_segments) / scene_count) * 94.0, 1),
                        current=scene_number,
                        total=scene_count,
                        detail=f"Scene {scene_number}/{scene_count} was already rendered successfully; no need to render it again.",
                    )
                    continue

                for stale_path in (segment_path, temporary_segment):
                    try:
                        if os.path.isfile(stale_path):
                            os.remove(stale_path)
                    except OSError:
                        pass

                _set_worker_status(
                    f"Rendering scene {scene_number} of {scene_count}",
                    progress=round((len(completed_segments) / scene_count) * 94.0, 1),
                    current=scene_number,
                    total=scene_count,
                    detail=(
                        f"Rendering scene {scene_number}/{scene_count}: generating its frames, "
                        "camera movement, transition, timed captions and overlays."
                    ),
                )
                segment_logger = _SceneSegmentProgressLogger(
                    scene_number, len(completed_segments), scene_count
                )
                try:
                    scene_clip.write_videofile(
                        temporary_segment,
                        fps=24,
                        codec=video_encoder,
                        audio=False,
                        preset=active_encoder_preset,
                        ffmpeg_params=active_ffmpeg_params,
                        threads=active_encoder_threads,
                        logger=segment_logger,
                    )
                    if not segment_is_valid(temporary_segment):
                        raise RuntimeError(
                            f"Rendered scene {scene_number} did not produce a valid video segment."
                        )
                    os.replace(temporary_segment, segment_path)
                    completed_segments.append(segment_path)
                    _video_producer_write_json_atomic(
                        os.path.join(checkpoint_dir, "render_checkpoint.json"),
                        {
                            "project_title": project_title,
                            "fingerprint": render_fingerprint,
                            "completed_scene_numbers": list(range(1, scene_number + 1)),
                            "completed_segments": len(completed_segments),
                            "total_segments": scene_count,
                            "updated_at": time.time(),
                        },
                    )
                    print(
                        f"💾 [CHECKPOINT] Scene {scene_number}/{scene_count} safely saved. "
                        f"{len(completed_segments)}/{scene_count} scene videos are reusable."
                    )
                    _set_worker_status(
                        f"Scene {scene_number} saved",
                        progress=round((len(completed_segments) / scene_count) * 94.0, 1),
                        current=scene_number,
                        total=scene_count,
                        detail=f"Scene {scene_number}/{scene_count} is fully encoded and saved. This scene will not need to be rendered again.",
                    )
                finally:
                    try:
                        if os.path.isfile(temporary_segment):
                            os.remove(temporary_segment)
                    except OSError:
                        pass

            if len(completed_segments) != scene_count:
                raise RuntimeError(
                    f"Scene checkpoint mismatch: {len(completed_segments)} of {scene_count} scenes are ready."
                )

            _check_worker_control(
                stage="Combining saved scenes and adding narration",
                detail="All scene videos are saved. Joining them in order and adding the original narration track.",
            )
            _set_worker_status(
                "Combining saved scenes and adding narration",
                progress=95,
                current=scene_count,
                total=scene_count,
                detail="Joining the completed scene videos in the correct order and adding the narration audio.",
            )

            concat_list_path = os.path.join(checkpoint_dir, "scene_concat_list.txt")
            with open(concat_list_path, "w", encoding="utf-8", newline="\n") as concat_handle:
                for segment in completed_segments:
                    escaped = os.path.abspath(segment).replace("\\", "/").replace("'", r"'\''")
                    concat_handle.write(f"file '{escaped}'\n")

            ffmpeg_exe = None
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_exe = shutil.which("ffmpeg")
            if not ffmpeg_exe:
                raise RuntimeError(
                    "FFmpeg executable was not found. Install imageio-ffmpeg or add FFmpeg to PATH."
                )

            temporary_output = output_path[:-4] + f".partial_{os.getpid()}.mp4"
            try:
                if os.path.isfile(temporary_output):
                    os.remove(temporary_output)
            except OSError:
                pass

            ffmpeg_command = [
                ffmpeg_exe,
                "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_list_path,
                "-i", audio_file_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "320k",
                "-t", f"{max(0.1, float(total_duration)):.6f}",
                "-movflags", "+faststart",
                temporary_output,
            ]
            import subprocess
            mux_result = subprocess.run(
                ffmpeg_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                check=False,
            )
            if mux_result.returncode != 0 or not os.path.isfile(temporary_output) or os.path.getsize(temporary_output) <= 0:
                raise RuntimeError(
                    "FFmpeg could not join the saved scenes and narration: "
                    + (mux_result.stderr.strip()[-3000:] or f"exit code {mux_result.returncode}")
                )

            _set_worker_status(
                "Finalizing and checking the finished video",
                progress=98,
                detail="The scene videos and narration have been joined. Checking the MP4 before publishing it.",
            )
            if not segment_is_valid(temporary_output):
                raise RuntimeError("The assembled MP4 failed its final video validation.")

            # Preserve an older final output only after the new MP4 has been
            # completely assembled and validated.
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
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
                backup_path = os.path.join(
                    edited_folder, f"{normalized_project_title}_old_{next_old_number}.mp4"
                )
                while os.path.exists(backup_path):
                    next_old_number += 1
                    backup_path = os.path.join(
                        edited_folder, f"{normalized_project_title}_old_{next_old_number}.mp4"
                    )
                os.replace(output_path, backup_path)
                print(f"📦 Preserved previous output as: {backup_path}")

            os.replace(temporary_output, output_path)
            elapsed_minutes = (time.monotonic() - render_started) / 60.0
            print(f"⏱️ Resumable render elapsed time: {elapsed_minutes:.2f} minutes")
            print(f"✅ Video saved: {output_path}")
            print(f"📊 Size: {os.path.getsize(output_path) / (1024 * 1024):.2f} MB")
            _video_producer_write_json_atomic(
                os.path.join(checkpoint_dir, "render_checkpoint.json"),
                {
                    "project_title": project_title,
                    "fingerprint": render_fingerprint,
                    "completed_scene_numbers": list(range(1, scene_count + 1)),
                    "completed_segments": scene_count,
                    "total_segments": scene_count,
                    "final_video": output_path,
                    "completed": True,
                    "updated_at": time.time(),
                },
            )
            _set_worker_status(
                "Finalizing output",
                progress=99.5,
                detail="The finished MP4 has been created and validated successfully.",
            )
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise RuntimeError("FFmpeg finished without creating a valid output file")
        except _VideoProducerStopRequested:
            raise
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


class _VideoProducerStopRequested(BaseException):
    """Internal signal: stop at a safe checkpoint and preserve resumable work."""


def _video_producer_read_json(path, default=None):
    import json
    if not path:
        return {} if default is None else default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, (dict, list)) else ({} if default is None else default)
    except (OSError, ValueError, TypeError):
        return {} if default is None else default


def _video_producer_write_json_atomic(path, payload):
    """Durably replace one JSON checkpoint/control file."""
    import json
    import os
    import uuid
    if not path:
        return False
    path = os.path.abspath(os.fspath(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + f".tmp_{os.getpid()}_{uuid.uuid4().hex}"
    try:
        with open(temp_path, "w", encoding="utf-8", newline="") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temp_path, path)
        return True
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass


def _video_producer_write_control(control_path, command):
    """Write a control action for one individual project."""
    return _video_producer_write_json_atomic(
        control_path,
        {"command": str(command or "run").strip().casefold(), "updated_at": time.time()},
    )


def _video_producer_dashboard_shutdown_requested(shutdown_path):
    state = _video_producer_read_json(shutdown_path, {})
    return bool(isinstance(state, dict) and state.get("shutdown"))


def _video_producer_control_checkpoint(
    control_path,
    status_path=None,
    project_title=None,
    stage=None,
    detail=None,
    shutdown_path=None,
    heartbeat_path=None,
    parent_pid=None,
    checkpoint_dir=None,
):
    """Cooperatively pause/stop; stop always occurs between safe render units."""
    import os
    import time

    def parent_is_gone():
        try:
            expected_pid = int(parent_pid or 0)
        except (TypeError, ValueError):
            return False
        if expected_pid <= 0 or expected_pid == os.getpid():
            return False
        try:
            import psutil
            return not psutil.pid_exists(expected_pid)
        except Exception:
            pass
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                STILL_ACTIVE = 259
                kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
                kernel32.OpenProcess.restype = ctypes.c_void_p
                kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
                kernel32.GetExitCodeProcess.restype = ctypes.c_int
                kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel32.CloseHandle.restype = ctypes.c_int
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, expected_pid)
                if not handle:
                    return True
                try:
                    exit_code = ctypes.c_ulong()
                    if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                        return False
                    return int(exit_code.value) != STILL_ACTIVE
                finally:
                    kernel32.CloseHandle(handle)
            except Exception:
                return False
        try:
            os.kill(expected_pid, 0)
            return False
        except OSError:
            return True

    def dashboard_is_gone():
        if _video_producer_dashboard_shutdown_requested(shutdown_path) or parent_is_gone():
            return True
        if heartbeat_path and os.path.exists(heartbeat_path):
            try:
                age = time.time() - os.path.getmtime(heartbeat_path)
                return age > float(os.environ.get("VIDEO_DASHBOARD_HEARTBEAT_TIMEOUT", "12"))
            except OSError:
                return False
        return False

    def set_status(new_status, new_stage=None, new_detail=None):
        if not status_path:
            return
        previous = _video_producer_read_worker_status(status_path)
        previous.update({
            "status": new_status,
            "stage": new_stage or previous.get("stage") or stage or "Video production",
            "detail": new_detail or previous.get("detail") or detail or "",
            "project_title": project_title or previous.get("project_title"),
            "updated_at": time.time(),
        })
        try:
            _video_producer_write_worker_status(status_path, previous)
        except Exception:
            pass
        if checkpoint_dir:
            try:
                progress_snapshot = {
                    key: previous.get(key)
                    for key in (
                        "worker_id", "project_title", "status", "stage", "progress",
                        "current", "total", "detail", "updated_at", "encoder",
                        "whisper_device", "whisper_compute_type",
                    )
                }
                progress_snapshot["updated_at"] = time.time()
                _video_producer_write_json_atomic(
                    os.path.join(checkpoint_dir, "progress.json"),
                    progress_snapshot,
                )
            except Exception:
                pass

    while True:
        command_data = _video_producer_read_json(control_path, {}) if control_path else {}
        command = str(command_data.get("command", "run") if isinstance(command_data, dict) else "run").casefold()

        if dashboard_is_gone() or command in {"stop", "shutdown", "close", "cancel"}:
            set_status(
                "stopped",
                "Stopped safely — progress saved",
                "This video stopped at a safe checkpoint. Completed scene renders and narration analysis are saved and will be reused when you press Start or relaunch SceneIQ.",
            )
            raise _VideoProducerStopRequested(
                f"Stop requested for {project_title or 'video production'}"
            )

        if command in {"pause", "paused"}:
            set_status(
                "paused",
                "Paused by you",
                f"Paused safely during: {stage or 'current production stage'}. Press Resume to continue.",
            )
            while True:
                time.sleep(0.4)
                if dashboard_is_gone():
                    set_status(
                        "stopped",
                        "Stopped safely — progress saved",
                        "The dashboard was closed. The current video saved its completed work and stopped safely.",
                    )
                    raise _VideoProducerStopRequested("Dashboard closed while video was paused")
                command_data = _video_producer_read_json(control_path, {}) if control_path else {}
                command = str(command_data.get("command", "pause") if isinstance(command_data, dict) else "pause").casefold()
                if command in {"stop", "shutdown", "close", "cancel"}:
                    set_status(
                        "stopped",
                        "Stopped safely — progress saved",
                        "The video stopped at a safe checkpoint. Previously completed work will be reused when restarted.",
                    )
                    raise _VideoProducerStopRequested("Stop requested while paused")
                if command in {"resume", "start", "run", "continue"}:
                    if control_path:
                        _video_producer_write_control(control_path, "run")
                    set_status(
                        "running",
                        stage or "Resuming video production",
                        f"Resumed. Continuing with: {stage or 'the saved production stage'}.",
                    )
                    break
            continue

        if command in {"start", "resume", "continue"} and control_path:
            _video_producer_write_control(control_path, "run")
        return


def _video_producer_tree_signature(folder):
    """Fast deterministic signature for a project tree, excluding generated output."""
    import os
    import hashlib
    digest = hashlib.sha256()
    if not folder or not os.path.isdir(folder):
        return ""
    for current_root, directories, filenames in os.walk(folder):
        directories[:] = sorted(
            name for name in directories
            if name.casefold() not in {"edited", "temp_captions", "__pycache__"}
        )
        for filename in sorted(filenames):
            path = os.path.join(current_root, filename)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            relative = os.path.relpath(path, folder).replace("\\", "/")
            digest.update(f"{relative}|{stat.st_size}|{getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1e9))}\n".encode("utf-8", errors="replace"))
    return digest.hexdigest()


def _video_producer_file_signature(path):
    import os
    import hashlib
    if not path or not os.path.isfile(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _video_producer_write_dashboard_error(ready_path, error):
    """Persist dashboard startup errors for the parent producer process."""
    import time
    try:
        with open(ready_path + ".error.txt", "a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {error}\n")
    except OSError:
        pass


def _video_producer_dashboard_cli(manifest_path, ready_path):
    """Run the embedded dashboard mode when this same file is spawned."""
    import os
    try:
        _video_producer_dashboard_window(
            os.path.abspath(manifest_path),
            os.path.abspath(ready_path),
        )
        return 0
    except BaseException as exc:
        _video_producer_write_dashboard_error(ready_path, f"Dashboard could not start: {exc!r}")
        return 1


def _video_producer_dashboard_window(manifest_path, ready_path):
    """Standalone GUI. It launches independently and treats every worker status as optional."""
    import json
    import os
    import time
    import tkinter as tk
    from tkinter import ttk

    def read_json(path, default=None):
        if not path:
            return {} if default is None else default
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, (dict, list)) else ({} if default is None else default)
        except Exception:
            return {} if default is None else default

    def safe_write_json(path, payload):
        if not path:
            return False
        try:
            _video_producer_write_json_atomic(path, payload)
            return True
        except Exception:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                temporary = path + f".ui_{os.getpid()}.tmp"
                with open(temporary, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except OSError:
                        pass
                os.replace(temporary, path)
                return True
            except Exception:
                try:
                    with open(path, "w", encoding="utf-8") as handle:
                        json.dump(payload, handle, ensure_ascii=False, indent=2)
                    return True
                except Exception:
                    return False

    def read_manifest():
        value = read_json(manifest_path, {})
        return value if isinstance(value, dict) else {}

    # The GUI's existence is independent of the queue, status files, memory
    # telemetry, renderer imports, and multiprocessing. Start with an empty shell.
    manifest = read_manifest()
    jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []

    root = tk.Tk()
    root.title("SceneIQ Video Production")
    root.geometry("1080x700")
    root.minsize(820, 540)
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
    warning = "#f4d477"

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
    tk.Label(title_area, text="SCENEIQ  /  VIDEO PRODUCTION", bg=background,
             fg=accent, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(title_area, text="Production dashboard", bg=background,
             fg=foreground, font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=(3, 1))
    tk.Label(title_area,
             text="The window runs independently. Queue and worker errors never close this dashboard.",
             bg=background, fg=muted, font=("Segoe UI", 9)).pack(anchor="w")

    message_label = tk.Label(
        outer, text="Dashboard is open — waiting for the production service…",
        bg=panel, fg=foreground, font=("Segoe UI", 9, "bold"),
        justify="left", anchor="w", padx=12, pady=9, wraplength=1300,
    )
    message_label.pack(fill="x", pady=(0, 10))

    stats_row = tk.Frame(outer, bg=background)
    stats_row.pack(fill="x", pady=(0, 10))
    stat_labels = {}
    stat_definitions = (
        ("running", "RUNNING", accent),
        ("paused", "PAUSED", warning),
        ("stopped", "STOPPED", foreground),
        ("queued", "QUEUED", blue),
        ("completed", "COMPLETED", accent),
        ("failed", "FAILED", danger),
        ("total", "TOTAL PROJECTS", foreground),
    )
    for key, caption, value_color in stat_definitions:
        stat = tk.Frame(stats_row, bg=panel, highlightbackground=border,
                        highlightthickness=1, padx=10, pady=7)
        stat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Label(stat, text=caption, bg=panel, fg=muted,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        value = tk.Label(stat, text="0", bg=panel, fg=value_color,
                         font=("Segoe UI", 14, "bold"))
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
    grid_frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    empty_label = tk.Label(
        grid_frame,
        text="The dashboard is ready. It will display each video here as soon as the queue is read.",
        bg=background, fg=muted, font=("Segoe UI", 11), padx=20, pady=24,
    )
    empty_label.pack(anchor="w")

    cards = {}
    latest_manifest = dict(manifest)
    close_requested = {"value": False}

    def send_control(path, command):
        if not path:
            return
        try:
            _video_producer_write_control(path, command)
        except Exception as exc:
            try:
                message_label.configure(text=f"Could not send {command} command: {exc}")
            except Exception:
                pass

    def make_card(job, index):
        worker_id = str(job.get("worker_id") or f"WORKER-{index + 1:03d}")
        card = tk.Frame(grid_frame, bg=panel, highlightbackground=border,
                        highlightthickness=1, padx=12, pady=10)
        card.pack(fill="x", padx=6, pady=6)

        title_row = tk.Frame(card, bg=panel)
        title_row.pack(fill="x")
        title_label = tk.Label(title_row, text=str(job.get("project_title") or "Video production"),
                               bg=panel, fg=foreground, font=("Segoe UI", 10, "bold"),
                               justify="left", anchor="w", wraplength=1000)
        title_label.pack(side="left", fill="x", expand=True)
        badge = tk.Label(title_row, text="QUEUED", bg="#1c3450", fg=blue,
                         font=("Segoe UI", 8, "bold"), padx=9, pady=4)
        badge.pack(side="right", padx=(8, 0))

        meta = tk.Label(card,
                        text=f"{worker_id}  •  {str(job.get('lane') or 'CPU').upper()} lane  •  Encoder: {job.get('encoder') or 'libx264'}",
                        bg=panel, fg=muted, font=("Segoe UI", 8, "bold"), anchor="w")
        meta.pack(fill="x", pady=(5, 6))
        stage_label = tk.Label(card, text="Waiting for the producer", bg=panel,
                               fg=foreground, font=("Segoe UI", 9, "bold"), anchor="w")
        stage_label.pack(fill="x")
        detail_label = tk.Label(card, text="Worker status will appear here.", bg=panel,
                                fg=muted, font=("Segoe UI", 8), anchor="w",
                                justify="left", wraplength=1280)
        detail_label.pack(fill="x", pady=(2, 7))
        progress_row = tk.Frame(card, bg=panel)
        progress_row.pack(fill="x")
        progress_bar = ttk.Progressbar(progress_row, style="SceneIQ.Horizontal.TProgressbar",
                                       orient="horizontal", mode="determinate", maximum=100)
        progress_bar.pack(side="left", fill="x", expand=True)
        progress_label = tk.Label(progress_row, text="—", bg=panel, fg=accent,
                                  font=("Segoe UI", 8, "bold"), width=16, anchor="e")
        progress_label.pack(side="right", padx=(8, 0))

        footer = tk.Frame(card, bg=panel)
        footer.pack(fill="x", pady=(5, 5))
        elapsed_label = tk.Label(footer, text="Elapsed: —", bg=panel, fg=muted,
                                 font=("Segoe UI", 8), anchor="w")
        elapsed_label.pack(side="left")
        whisper_label = tk.Label(footer, text="Speech recognition: —", bg=panel, fg=muted,
                                 font=("Segoe UI", 8), anchor="e")
        whisper_label.pack(side="right")

        actions = tk.Frame(card, bg=panel)
        actions.pack(fill="x", pady=(3, 0))
        buttons = {}
        for key, caption, command, color in (
            ("pause", "Pause", "pause", "#34435a"),
            ("resume", "Resume", "resume", "#164d43"),
            ("stop", "Stop", "stop", "#542a32"),
            ("start", "Start", "start", "#24523d"),
        ):
            button = tk.Button(
                actions, text=caption, bg=color, fg=foreground,
                activebackground=border, activeforeground=foreground,
                relief="flat", padx=11, pady=4,
                font=("Segoe UI", 8, "bold"), cursor="hand2",
                command=lambda p=job.get("control_path"), c=command: send_control(p, c),
            )
            buttons[key] = button

        log_frame = tk.Frame(card, bg="#080e18", highlightbackground=border, highlightthickness=1)
        log_frame.pack(fill="x", pady=(7, 0))
        log_text = tk.Text(log_frame, bg="#080e18", fg="#d7e3f0", relief="flat",
                           borderwidth=0, wrap="word", padx=7, pady=5,
                           font=("Consolas", 8), height=3, state="disabled")
        log_text.pack(fill="x")
        log_text.configure(state="normal")
        log_text.insert("end", "Waiting for worker output…\n")
        log_text.configure(state="disabled")

        return {
            "worker_id": worker_id,
            "job": dict(job),
            "signature": (str(job.get("status_path") or ""), str(job.get("log_path") or "")),
            "card": card,
            "badge": badge,
            "meta": meta,
            "stage": stage_label,
            "detail": detail_label,
            "progress_bar": progress_bar,
            "progress_label": progress_label,
            "elapsed": elapsed_label,
            "whisper": whisper_label,
            "buttons": buttons,
            "log_text": log_text,
            "log_offset": 0,
        }

    def append_log(card_info):
        path = card_info["job"].get("log_path")
        if not path or not os.path.isfile(path):
            return
        try:
            size = os.path.getsize(path)
            if card_info["log_offset"] > size:
                card_info["log_offset"] = 0
            with open(path, "rb") as handle:
                handle.seek(card_info["log_offset"])
                chunk = handle.read(32768)
                card_info["log_offset"] = handle.tell()
        except Exception:
            return
        if not chunk:
            return
        widget = card_info["log_text"]
        try:
            follow = widget.yview()[1] >= 0.985
            widget.configure(state="normal")
            widget.insert("end", chunk.decode("utf-8", errors="replace").replace("\r", "\n"))
            lines = int(widget.index("end-1c").split(".")[0])
            if lines > 45:
                widget.delete("1.0", f"{lines - 32}.0")
            if follow:
                widget.see("end")
            widget.configure(state="disabled")
        except Exception:
            try:
                widget.configure(state="disabled")
            except Exception:
                pass

    def close_dashboard():
        if close_requested["value"]:
            return
        close_requested["value"] = True
        # The close action requests a safe stop for each known video, but it does
        # not depend on status snapshots or dashboard counter state.
        current = read_manifest()
        all_jobs = []
        for source in (current.get("jobs", []), latest_manifest.get("jobs", [])):
            if isinstance(source, list):
                all_jobs.extend(item for item in source if isinstance(item, dict))
        for card_info in list(cards.values()):
            all_jobs.append(card_info.get("job", {}))
        seen_controls = set()
        for job in all_jobs:
            path = job.get("control_path") if isinstance(job, dict) else None
            if path and path not in seen_controls:
                seen_controls.add(path)
                send_control(path, "stop")
        shutdown_path = current.get("shutdown_path") or latest_manifest.get("shutdown_path")
        if shutdown_path:
            safe_write_json(shutdown_path, {
                "shutdown": True,
                "requested_at": time.time(),
                "reason": "dashboard_closed",
            })
        try:
            root.destroy()
        except Exception:
            pass

    def refresh_dashboard():
        nonlocal latest_manifest
        try:
            fresh_manifest = read_manifest()
            if fresh_manifest:
                latest_manifest = fresh_manifest
            job_list = latest_manifest.get("jobs")
            if not isinstance(job_list, list):
                job_list = []

            session_message = str(
                latest_manifest.get("message")
                or latest_manifest.get("service_status")
                or "Dashboard is active. Waiting for production updates."
            )
            try:
                message_label.configure(text=session_message)
            except Exception:
                pass

            active_ids = set()
            for index, job in enumerate(job_list):
                if not isinstance(job, dict):
                    continue
                worker_id = str(job.get("worker_id") or f"WORKER-{index + 1:03d}")
                active_ids.add(worker_id)
                signature = (str(job.get("status_path") or ""), str(job.get("log_path") or ""))
                card_info = cards.get(worker_id)
                if card_info is None or card_info.get("signature") != signature:
                    if card_info is not None:
                        try:
                            card_info["card"].destroy()
                        except Exception:
                            pass
                    card_info = make_card(job, index)
                    cards[worker_id] = card_info
                else:
                    card_info["job"].update(job)
                card_info["job"].update(job)

            if cards:
                try:
                    empty_label.pack_forget()
                except Exception:
                    pass
            else:
                if not empty_label.winfo_manager():
                    empty_label.pack(anchor="w")

            counts = {"running": 0, "paused": 0, "stopped": 0,
                      "queued": 0, "completed": 0, "failed": 0,
                      "total": len(job_list)}
            for worker_id, card_info in list(cards.items()):
                # Old cards are retained for visual history, but current status is
                # read best-effort. A missing/corrupt JSON file never closes the UI.
                try:
                    state = read_json(card_info["job"].get("status_path"), {})
                    if not isinstance(state, dict):
                        state = {}
                except Exception:
                    state = {}
                status = str(state.get("status") or "queued").casefold()
                if status not in counts:
                    status = "queued"
                if worker_id in active_ids:
                    counts[status] += 1
                card_info["badge"].configure(text={
                    "queued": "QUEUED", "running": "PRODUCING", "paused": "PAUSED",
                    "stopped": "STOPPED — SAVED", "completed": "COMPLETED",
                    "failed": "FAILED", "skipped_or_failed": "NO OUTPUT",
                }.get(status, status.upper()))
                if status == "completed":
                    badge_bg, badge_fg = accent_dark, accent
                elif status == "running":
                    badge_bg, badge_fg = "#163b49", accent
                elif status == "paused":
                    badge_bg, badge_fg = "#4c4425", warning
                elif status in {"stopped", "stopping"}:
                    badge_bg, badge_fg = "#3e4655", foreground
                elif status in {"failed", "skipped_or_failed"}:
                    badge_bg, badge_fg = "#45232b", danger
                else:
                    badge_bg, badge_fg = "#1c3450", blue
                card_info["badge"].configure(bg=badge_bg, fg=badge_fg)
                card_info["meta"].configure(
                    text=(
                        f"{state.get('worker_id') or worker_id}  •  PID {state.get('pid') or '—'}  •  "
                        f"{str(state.get('lane') or card_info['job'].get('lane') or 'CPU').upper()} lane  •  "
                        f"Encoder: {state.get('encoder') or card_info['job'].get('encoder') or 'libx264'}"
                    )
                )
                card_info["stage"].configure(text=str(state.get("stage") or "Waiting for production"))
                card_info["detail"].configure(text=str(state.get("detail") or "Detailed production status will appear here."))
                progress_value = state.get("progress")
                if isinstance(progress_value, (int, float)):
                    progress_value = max(0.0, min(100.0, float(progress_value)))
                    card_info["progress_bar"].configure(value=progress_value)
                    card_info["progress_label"].configure(text=f"{progress_value:.1f}%")
                elif status == "completed":
                    card_info["progress_bar"].configure(value=100)
                    card_info["progress_label"].configure(text="100%")
                else:
                    card_info["progress_label"].configure(text="—")
                started_at = state.get("started_at") or state.get("queued_at") or time.time()
                try:
                    elapsed = max(0, int(time.time() - float(started_at)))
                except Exception:
                    elapsed = 0
                hours, remainder = divmod(elapsed, 3600)
                minutes, seconds = divmod(remainder, 60)
                elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
                card_info["elapsed"].configure(text=f"Elapsed: {elapsed_text}")
                card_info["whisper"].configure(
                    text=f"Speech recognition: {state.get('whisper_device', 'cpu')} / {state.get('whisper_compute_type', 'int8')}"
                )

                for button in card_info["buttons"].values():
                    button.pack_forget()
                if status == "running":
                    card_info["buttons"]["pause"].pack(side="left", padx=(0, 6))
                    card_info["buttons"]["stop"].pack(side="left", padx=(0, 6))
                elif status == "paused":
                    card_info["buttons"]["resume"].pack(side="left", padx=(0, 6))
                    card_info["buttons"]["stop"].pack(side="left", padx=(0, 6))
                elif status in {"stopped", "stopping"}:
                    card_info["buttons"]["start"].pack(side="left", padx=(0, 6))
                elif status == "queued":
                    card_info["buttons"]["stop"].pack(side="left", padx=(0, 6))
                append_log(card_info)

            for key, value in counts.items():
                # Keep the UI alive even if a future code path adds a new state.
                label = stat_labels.get(key)
                if label is not None:
                    label.configure(text=str(value))
            summary_label_text = (
                f"{counts['running']} running  •  {counts['paused']} paused  •  "
                f"{counts['stopped']} stopped  •  {counts['queued']} queued  •  "
                f"{counts['completed']} completed  •  {counts['failed']} failed"
            )
            # Reuse the session message panel for summary in the window title tooltip area.
            root.title(f"SceneIQ Video Production — {counts['running']} running / {counts['total']} projects")
            message_label.configure(text=f"{session_message}     |     {summary_label_text}")
        except Exception as ui_exc:
            # Any monitoring, malformed status, missing stat key, or file-lock
            # failure must not terminate Tk's event loop or the visible window.
            try:
                message_label.configure(text=f"Dashboard is still running. Status refresh issue: {ui_exc}")
            except Exception:
                pass
        finally:
            heartbeat_path = latest_manifest.get("heartbeat_path")
            if heartbeat_path:
                safe_write_json(heartbeat_path, {
                    "pid": os.getpid(),
                    "heartbeat_at": time.time(),
                })
            try:
                root.after(900, refresh_dashboard)
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", close_dashboard)
    root.withdraw()

    def announce_ready_minimized():
        """Acknowledge the window independently from project/status operations."""
        try:
            root.deiconify()
            root.update_idletasks()
            root.iconify()
            root.update()
            heartbeat_path = latest_manifest.get("heartbeat_path")
            if heartbeat_path:
                safe_write_json(heartbeat_path, {"pid": os.getpid(), "heartbeat_at": time.time()})
            safe_write_json(ready_path, {
                "ready": True,
                "pid": os.getpid(),
                "window_title": "SceneIQ Video Production",
                "manifest_path": os.path.abspath(manifest_path),
                "window_state": "minimized",
                "ready_at": time.time(),
            })
        except Exception as exc:
            # Write an error only if the OS/Tk itself prevents creating a window.
            error_path = ready_path + ".error.txt"
            try:
                with open(error_path, "a", encoding="utf-8") as handle:
                    handle.write(f"Dashboard window initialization failed: {exc!r}\n")
            except OSError:
                pass

    root.after(250, announce_ready_minimized)
    root.after(400, refresh_dashboard)
    root.mainloop()

def _video_producer_launch_dashboard_window(manifest_path, timeout_seconds=30.0):
    """Launch the embedded GUI worker; status files are not part of startup."""
    import json
    import os
    import shutil
    import subprocess
    import sys
    import time

    script_path = os.path.abspath(os.fspath(globals().get("__file__", "")))
    if not script_path or not os.path.isfile(script_path):
        raise RuntimeError("Cannot locate the single-file SceneIQ video producer script")
    manifest_path = os.path.abspath(os.fspath(manifest_path))
    ready_path = manifest_path + ".ready.json"
    error_path = ready_path + ".error.txt"
    current_python = os.path.abspath(sys.executable)
    pythonw = os.path.join(os.path.dirname(current_python), "pythonw.exe")
    candidates = []
    for candidate in (pythonw, shutil.which("pythonw"), current_python):
        if candidate and os.path.isfile(candidate) and os.path.abspath(candidate).casefold() not in {
            os.path.abspath(item).casefold() for item in candidates
        }:
            candidates.append(os.path.abspath(candidate))

    last_error = None
    for dashboard_python in candidates:
        for stale in (ready_path, error_path):
            try:
                if os.path.exists(stale):
                    os.remove(stale)
            except OSError:
                pass
        is_pythonw = os.path.basename(dashboard_python).casefold().startswith("pythonw")
        creation_flags = 0
        startupinfo = None
        if os.name == "nt" and not is_pythonw:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if hasattr(subprocess, "STARTUPINFO"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0
        command = [dashboard_python, script_path, "--sceneiq-dashboard", manifest_path, ready_path]
        try:
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
        except Exception as exc:
            last_error = f"Could not launch {dashboard_python}: {exc!r}"
            continue

        deadline = time.monotonic() + max(5.0, float(timeout_seconds))
        while time.monotonic() < deadline:
            if os.path.isfile(ready_path):
                try:
                    with open(ready_path, "r", encoding="utf-8") as handle:
                        handshake = json.load(handle)
                    if handshake.get("ready") is True and process.poll() is None:
                        return {
                            "pid": process.pid,
                            "process": process,
                            "ready_path": ready_path,
                            "handshake": handshake,
                        }
                    last_error = f"Invalid dashboard readiness response: {handshake!r}"
                except Exception as exc:
                    last_error = str(exc)
            if process.poll() is not None:
                last_error = f"Dashboard process exited with code {process.returncode}."
                if os.path.isfile(error_path):
                    try:
                        with open(error_path, "r", encoding="utf-8") as handle:
                            last_error += " " + handle.read().strip()[-3000:]
                    except OSError:
                        pass
                break
            time.sleep(0.15)

        if process.poll() is None:
            last_error = f"Dashboard process did not confirm its window within {timeout_seconds}s using {dashboard_python}."
            try:
                process.terminate()
                process.wait(timeout=3.0)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        # Try the next interpreter executable if the first one fails.

    raise RuntimeError(last_error or "No usable Python interpreter was found for the SceneIQ dashboard.")

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

def _video_producer_normalize_audio_match_text(value):
    """Normalize audio/project names: letters and digits only, case-insensitive."""
    import unicodedata
    normalized = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _video_producer_find_audio_source(project_title):
    """Find the newest Downloads audio using punctuation/spacing-insensitive matching."""
    import os

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.isdir(downloads):
        return None
    normalized_title = _video_producer_normalize_audio_match_text(project_title)
    if not normalized_title:
        return None
    audio_extensions = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma")
    try:
        matches = []
        for name in os.listdir(downloads):
            if not name.casefold().endswith(audio_extensions):
                continue
            path = os.path.join(downloads, name)
            if not os.path.isfile(path):
                continue
            try:
                if os.path.getsize(path) <= 0:
                    continue
            except OSError:
                continue
            normalized_audio_name = _video_producer_normalize_audio_match_text(
                os.path.splitext(name)[0]
            )
            if normalized_title in normalized_audio_name:
                matches.append(path)
                print(
                    f"🔎 [AUDIO] Normalized filename match: '{name}' "
                    f"(project key: '{normalized_title}')"
                )
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
    checkpoint_manifest_path = os.path.join(workspace_path, "workspace_manifest.json")
    project_category = job.get("project_category")
    original_project_dir = _video_producer_resolve_original_project_folder(
        original_images_root, title, project_category
    )

    # An already-published final video always wins over a stale saved workspace.
    # Check this BEFORE attempting workspace reuse so a previous successful run
    # is never rendered again merely because its private workspace still exists.
    normalized_title_for_output = _video_producer_normalize_title(title)
    completed_output_candidates = []
    if original_project_dir:
        completed_output_candidates.append(
            os.path.join(original_project_dir, "edited", f"{normalized_title_for_output}.mp4")
        )
    safe_title_for_output = _sceneiq_safe_path_component(title, "unnamed_project")
    completed_output_candidates.extend([
        os.path.join(original_images_root, safe_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
        os.path.join(original_images_root, normalized_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
        os.path.join(original_images_root, "Uncategorized", safe_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
        os.path.join(original_images_root, "Uncategorized", normalized_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
    ])
    if project_category:
        category_component_for_output = _sceneiq_safe_path_component(project_category)
        completed_output_candidates.extend([
            os.path.join(original_images_root, category_component_for_output, safe_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
            os.path.join(original_images_root, category_component_for_output, normalized_title_for_output, "edited", f"{normalized_title_for_output}.mp4"),
        ])
    for completed_output in dict.fromkeys(completed_output_candidates):
        try:
            if os.path.isfile(completed_output) and os.path.getsize(completed_output) > 0:
                print(f"✅ [CHECKPOINT] A finished video already exists; skipping production: {completed_output}")
                return {
                    "workspace_path": workspace_path,
                    "already_completed_output": completed_output,
                    "original_project_dir": original_project_dir,
                    "ready_script_path": None,
                    "images_path": None,
                    "subscribe_stickers_path": None,
                    "audio_path": None,
                }
        except OSError:
            continue

    audio_source = _video_producer_find_audio_source(title)
    source_signature = {
        "queue_sha256": _video_producer_file_signature(original_ready_script),
        "project_tree": _video_producer_tree_signature(original_project_dir),
        "audio": [
            os.path.basename(audio_source),
            os.path.getsize(audio_source),
            getattr(os.stat(audio_source), "st_mtime_ns", int(os.path.getmtime(audio_source) * 1e9)),
        ] if audio_source and os.path.isfile(audio_source) else None,
        "stickers_tree": _video_producer_tree_signature(job.get("subscribe_stickers_path")),
    }
    existing_workspace = _video_producer_read_json(checkpoint_manifest_path, {})
    if (
        isinstance(existing_workspace, dict)
        and existing_workspace.get("source_signature") == source_signature
        and all(os.path.exists(existing_workspace.get(key, "")) for key in (
            "ready_script_path", "private_project_dir", "audio_path"
        ))
    ):
        print(f"♻️ [CHECKPOINT] Reusing saved project workspace for '{title}'.")
        return {
            "workspace_path": workspace_path,
            "original_project_dir": existing_workspace.get("original_project_dir"),
            "private_project_dir": existing_workspace.get("private_project_dir"),
            "ready_script_path": existing_workspace.get("ready_script_path"),
            "images_path": existing_workspace.get("images_path"),
            "subscribe_stickers_path": existing_workspace.get("subscribe_stickers_path"),
            "audio_path": existing_workspace.get("audio_path"),
            "copy_summary": existing_workspace.get("copy_summary"),
            "workspace_reused": True,
        }

    # An incomplete previous copy is discarded; fully copied workspaces are
    # retained across runs and machine restarts.
    import shutil
    if os.path.isdir(workspace_path):
        shutil.rmtree(workspace_path, ignore_errors=True)
    os.makedirs(workspace_path, exist_ok=True)
    timeout = float(os.environ.get("VIDEO_WORKSPACE_COPY_TIMEOUT_SECONDS", "900"))

    def report_copy_stage(stage, progress, detail):
        _video_producer_control_checkpoint(
            job.get("control_path"), status_path, title,
            stage=stage, detail=detail,
            shutdown_path=job.get("shutdown_path"),
            heartbeat_path=job.get("dashboard_heartbeat_path"),
            parent_pid=job.get("parent_pid"),
            checkpoint_dir=job.get("checkpoint_dir"),
        )
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
        checkpoint_dir = job.get("checkpoint_dir")
        if checkpoint_dir:
            try:
                _video_producer_write_json_atomic(
                    os.path.join(checkpoint_dir, "progress.json"),
                    {
                        "worker_id": job.get("worker_id"),
                        "project_title": title,
                        "status": "running",
                        "stage": str(stage),
                        "progress": progress,
                        "current": None,
                        "total": None,
                        "detail": str(detail),
                        "updated_at": time.time(),
                    },
                )
            except Exception as checkpoint_exc:
                print(f"⚠️ [CHECKPOINT] Could not save workspace-preparation progress: {checkpoint_exc}")

    report_copy_stage(
        "Preparing the project instructions",
        2,
        "Reading a safe copy of the ready-script queue so this video can work independently without changing the original file.",
    )

    private_queue_dir = os.path.join(workspace_path, "queue")
    private_ready_script = os.path.join(private_queue_dir, "ready_script.json")
    _video_producer_copy_file_isolated(original_ready_script, private_ready_script, timeout_seconds=timeout)

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
        "Preparing the scene images and project assets",
        5,
        "Making a separate working copy of the scene images, storyboard and supporting files. Your original project files are not modified.",
    )
    def project_copy_progress(current, total, relative_file):
        percentage = round((current / max(1, total)) * 100, 1)
        report_copy_stage(
            "Preparing the scene images and project assets",
            percentage,
            f"Prepared project asset {current}/{total}: {relative_file}. This is a safe working copy of the original file.",
        )

    copy_summary = _video_producer_copy_project_tree_isolated(
        original_project_dir,
        private_project_dir,
        timeout_seconds=timeout,
        progress_callback=project_copy_progress,
    )

    private_audio_path = os.path.join(workspace_path, "audio", os.path.basename(audio_source))
    report_copy_stage(
        "Preparing the narration audio",
        7,
        f"Making a safe working copy of the narration file: {os.path.basename(audio_source)}.",
    )
    _video_producer_copy_file_isolated(audio_source, private_audio_path, timeout_seconds=timeout)

    private_stickers_path = None
    sticker_source = job.get("subscribe_stickers_path")
    if sticker_source and os.path.isdir(sticker_source):
        private_stickers_path = os.path.join(workspace_path, "subscribe_stickers")
        report_copy_stage(
            "Preparing the subscribe animations",
            8,
            "Making a safe working copy of the animated like/subscribe sticker library.",
        )
        def sticker_copy_progress(current, total, relative_file):
            percentage = round((current / max(1, total)) * 100, 1)
            report_copy_stage(
                "Preparing the subscribe animations",
                percentage,
                f"Prepared animation asset {current}/{total}: {relative_file}.",
            )

        _video_producer_copy_project_tree_isolated(
            sticker_source,
            private_stickers_path,
            timeout_seconds=timeout,
            progress_callback=sticker_copy_progress,
        )

    workspace_result = {
        "workspace_path": workspace_path,
        "original_project_dir": original_project_dir,
        "private_project_dir": private_project_dir,
        "ready_script_path": private_ready_script,
        "images_path": private_images_root,
        "subscribe_stickers_path": private_stickers_path,
        "audio_path": private_audio_path,
        "copy_summary": copy_summary,
    }
    _video_producer_write_json_atomic(
        checkpoint_manifest_path,
        {
            **workspace_result,
            "source_signature": source_signature,
            "saved_at": time.time(),
        },
    )
    return workspace_result

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
    issue_path = job.get("issue_path")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    workspace_root = job.get("workspace_root") or os.path.join(os.path.dirname(log_path), "worker_workspaces")
    os.makedirs(workspace_root, exist_ok=True)
    workspace_path = None
    checkpoint_dir = os.path.abspath(job.get("checkpoint_dir") or os.path.join(workspace_root, _video_producer_normalize_title(title)))
    os.makedirs(checkpoint_dir, exist_ok=True)
    workspace_path = os.path.join(checkpoint_dir, "workspace")
    started_at = time.time()

    saved_progress = _video_producer_read_json(
        os.path.join(checkpoint_dir, "progress.json"), {}
    )
    saved_stage = (
        str(saved_progress.get("stage"))
        if isinstance(saved_progress, dict) and saved_progress.get("stage")
        else "No earlier checkpoint"
    )
    saved_detail = (
        str(saved_progress.get("detail"))
        if isinstance(saved_progress, dict) and saved_progress.get("detail")
        else "A new project workspace will be prepared."
    )
    base_status = {
        "worker_id": job.get("worker_id", "worker"),
        "lane": str(job.get("lane", "unknown")).upper(),
        "pid": pid,
        "project_title": title,
        "status": "running",
        "stage": "Opening saved video progress",
        "progress": saved_progress.get("progress") if isinstance(saved_progress, dict) else 0,
        "current": saved_progress.get("current") if isinstance(saved_progress, dict) else None,
        "total": saved_progress.get("total") if isinstance(saved_progress, dict) else None,
        "detail": (
            f"Previous saved stage: {saved_stage}. {saved_detail} "
            "Checking the durable scene-render checkpoints before continuing."
        ),
        "started_at": started_at,
        "encoder": profile.get("video_encoder", "libx264"),
        "whisper_device": profile.get("whisper_device", "cpu"),
        "whisper_compute_type": profile.get("whisper_compute_type", "int8"),
        "log_path": log_path,
        "status_path": status_path,
        "issue_path": issue_path,
    }
    if issue_path:
        try:
            _video_producer_write_json_atomic(issue_path, {
                "project_title": title,
                "worker_id": job.get("worker_id"),
                "status": "running",
                "updated_at": time.time(),
                "message": "This project's new attempt has started. Previous issue details were cleared.",
            })
        except Exception:
            pass
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

                _video_producer_control_checkpoint(
                    job.get("control_path"), status_path, title,
                    stage="Starting video worker",
                    detail="Checking the saved project files and previously rendered scenes.",
                    shutdown_path=job.get("shutdown_path"),
                    heartbeat_path=job.get("dashboard_heartbeat_path"),
                    parent_pid=job.get("parent_pid"),
                    checkpoint_dir=job.get("checkpoint_dir"),
                )
                os.makedirs(workspace_path, exist_ok=True)
                print(f"[WORKSPACE] Persistent project workspace: {workspace_path}")
                _video_producer_write_worker_status(status_path, {
                    **base_status,
                    "stage": "Preparing the project's working files",
                    "progress": 1,
                    "detail": "Checking the project script, original scene images, narration audio and saved work from an earlier run.",
                })

                workspace = _video_producer_prepare_worker_workspace(
                    job,
                    workspace_path,
                    status_path=status_path,
                    base_status=base_status,
                )
                if workspace.get("skip_reason"):
                    skip_reason = str(workspace.get("skip_reason"))
                    print(f"❌ [VIDEO-ISSUE] '{title}' cannot start: {skip_reason}")
                    final_status = "failed"
                    issue_payload = {
                        "project_title": title,
                        "worker_id": job.get("worker_id"),
                        "status": "failed",
                        "error_type": "ProjectPreflightIssue",
                        "error": skip_reason,
                        "issue_summary": skip_reason,
                        "stage": "Project input validation",
                        "traceback": "",
                        "log_path": log_path,
                        "workspace_path": workspace_path,
                        "updated_at": time.time(),
                    }
                    if issue_path:
                        try:
                            _video_producer_write_json_atomic(issue_path, issue_payload)
                        except Exception as issue_write_exc:
                            print(f"[ISSUE REPORT WARNING] Could not write issue report: {issue_write_exc}")
                    result = {"project_title": title, "status": "failed", "error": skip_reason, "issue": issue_payload}
                    cleanup_workspace = False
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

                    normalized_output_name = _video_producer_normalize_title(title) + ".mp4"
                    recovered_private_output = os.path.join(
                        workspace.get("private_project_dir", ""),
                        "edited",
                        normalized_output_name,
                    )
                    if (
                        recovered_private_output
                        and os.path.isfile(recovered_private_output)
                        and os.path.getsize(recovered_private_output) > 0
                    ):
                        print(f"♻️ [CHECKPOINT] Reusing the already completed private MP4: {recovered_private_output}")
                        result = {
                            "project_title": title,
                            "output_path": recovered_private_output,
                            "output_file": normalized_output_name,
                            "thumbnail_path": os.path.join(workspace.get("private_project_dir", ""), "edited", "Thumbnail.png"),
                        }
                    else:
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
                            control_path=job.get("control_path"),
                            shutdown_path=job.get("shutdown_path"),
                            dashboard_heartbeat_path=job.get("dashboard_heartbeat_path"),
                            checkpoint_dir=checkpoint_dir,
                            parent_pid=job.get("parent_pid"),
                            preview_image_path=job.get("preview_path"),
                        )

                    if isinstance(result, dict):
                        _video_producer_control_checkpoint(
                            job.get("control_path"), status_path, title,
                            stage="Saving the finished MP4 to the project",
                            detail="The MP4 render is complete. Preparing to publish the finished video and thumbnail to the original project folder.",
                            shutdown_path=job.get("shutdown_path"),
                            heartbeat_path=job.get("dashboard_heartbeat_path"),
                            parent_pid=job.get("parent_pid"),
                            checkpoint_dir=checkpoint_dir,
                        )
                        _video_producer_write_worker_status(status_path, {
                            **base_status,
                            "stage": "Waiting for original destination",
                            "progress": 98,
                            "detail": "The finished MP4 is ready. Saving it and its thumbnail into the original project edited folder.",
                        })
                        print("[PUBLISH] Waiting for exclusive access to the original project's edited folder...")
                        published_result = _video_producer_publish_worker_outputs(job, workspace, result)
                        result = published_result
                        final_status = "completed"
                        cleanup_workspace = True
                        print(f"✅ [PUBLISH] Final video safely saved to: {result['output_path']}")
                        # A verified/published MP4 no longer needs its scene segments
                        # or ASR cache; interrupted and stopped jobs retain them.
                        try:
                            shutil.rmtree(os.path.join(checkpoint_dir, "scene_segments"), ignore_errors=True)
                            for cache_name in ("narration_word_timestamps.json", "scene_concat_list.txt"):
                                cache_path = os.path.join(checkpoint_dir, cache_name)
                                if os.path.isfile(cache_path):
                                    os.remove(cache_path)
                        except OSError:
                            pass
                        if result.get("backup_path"):
                            print(f"📦 [PUBLISH] Previous output preserved as: {result['backup_path']}")
                        if result.get("thumbnail_path"):
                            print(f"🖼️ [PUBLISH] Thumbnail saved to: {result['thumbnail_path']}")
                    else:
                        final_status = "failed"
                        # process_single_video intentionally returns None for several
                        # input/ASR/assembly validation failures. Preserve the final
                        # renderer log so the GUI can explain the actual failure.
                        try:
                            with open(log_path, "r", encoding="utf-8", errors="replace") as issue_log:
                                log_excerpt = issue_log.read()[-18000:]
                        except Exception:
                            log_excerpt = "The renderer returned no output and its worker log could not be read."
                        useful_lines = [line.strip() for line in log_excerpt.splitlines() if line.strip()]
                        issue_summary = (
                            useful_lines[-1] if useful_lines else
                            "The renderer stopped without producing a final MP4. Open the full worker log for details."
                        )
                        for candidate_line in reversed(useful_lines):
                            if any(token in candidate_line.casefold() for token in (
                                "required narration", "no valid narration", "no scene entries",
                                "missing/invalid", "no usable entry images", "traceback",
                                "error:", "failed:", "could not", "cannot ",
                            )):
                                issue_summary = candidate_line
                                break
                        issue_payload = {
                            "project_title": title,
                            "worker_id": job.get("worker_id"),
                            "status": "failed",
                            "error_type": "RendererReturnedNoOutput",
                            "error": issue_summary,
                            "issue_summary": issue_summary,
                            "stage": "Video rendering",
                            "traceback": log_excerpt,
                            "log_path": log_path,
                            "workspace_path": workspace_path,
                            "updated_at": time.time(),
                        }
                        if issue_path:
                            try:
                                _video_producer_write_json_atomic(issue_path, issue_payload)
                            except Exception as issue_write_exc:
                                print(f"[ISSUE REPORT WARNING] Could not write issue report: {issue_write_exc}")
                        result = {"project_title": title, "status": "failed", "error": issue_summary, "issue": issue_payload}
                        print(f"❌ [VIDEO-ISSUE] {title}: {issue_summary}")

                issue_from_result = result.get("issue") if isinstance(result, dict) else None
                detail_text = (
                    result.get("output_path") if isinstance(result, dict) and result.get("output_path")
                    else result.get("error") if isinstance(result, dict) and result.get("error")
                    else result.get("skip_reason") if isinstance(result, dict) and result.get("skip_reason")
                    else f"No output returned. Workspace retained at: {workspace_path}"
                )
                status_payload = {
                    **base_status,
                    "status": final_status,
                    "stage": "Completed" if final_status == "completed" else ("Issue — requires attention" if final_status == "failed" else "Skipped / no output"),
                    "progress": 100 if final_status == "completed" else None,
                    "current": 1 if final_status == "completed" else None,
                    "total": 1 if final_status == "completed" else None,
                    "detail": str(detail_text),
                    "started_at": started_at,
                    "finished_at": time.time(),
                    "workspace_path": None if cleanup_workspace else workspace_path,
                    "issue_path": issue_path,
                }
                if isinstance(issue_from_result, dict):
                    status_payload.update({
                        "error_type": issue_from_result.get("error_type"),
                        "error": issue_from_result.get("error"),
                        "issue_summary": issue_from_result.get("issue_summary") or issue_from_result.get("error"),
                        "issue_stage": issue_from_result.get("stage"),
                        "traceback": issue_from_result.get("traceback"),
                    })
                _video_producer_write_worker_status(status_path, status_payload)
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
    except _VideoProducerStopRequested as stop_exc:
        try:
            current_state = _video_producer_read_worker_status(status_path)
            current_state = {
                **base_status,
                **current_state,
                "status": "stopped",
                "stage": "Stopped safely — progress saved",
                "detail": "The worker stopped at a safe checkpoint. Completed scene MP4 segments, narration word timings and the prepared project workspace are retained for the next Start/relaunch.",
                "finished_at": time.time(),
                "workspace_path": workspace_path,
            }
            _video_producer_write_worker_status(status_path, current_state)
            _video_producer_write_json_atomic(
                os.path.join(checkpoint_dir, "progress.json"),
                {
                    "worker_id": job.get("worker_id"),
                    "project_title": title,
                    "status": "stopped",
                    "stage": "Stopped safely — progress saved",
                    "progress": current_state.get("progress"),
                    "current": current_state.get("current"),
                    "total": current_state.get("total"),
                    "detail": current_state.get("detail"),
                    "updated_at": time.time(),
                },
            )
        except Exception:
            pass
        try:
            with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
                worker_log.write(f"\n[WORKER STOPPED SAFELY] {stop_exc}\n")
        except OSError:
            pass
        return {
            "project_title": title,
            "status": "stopped",
            "detail": str(stop_exc),
            "pid": pid,
            "lane": job.get("lane"),
            "worker_id": job.get("worker_id"),
            "log_path": log_path,
            "workspace_path": workspace_path,
        }
    except Exception as exc:
        error_traceback = traceback.format_exc()
        preserved_workspace = workspace_path if workspace_path and os.path.isdir(workspace_path) else None
        previous_status = _video_producer_read_worker_status(status_path)
        failed_stage = str(previous_status.get("stage") or "Video production")
        issue_payload = {
            "project_title": title,
            "worker_id": job.get("worker_id"),
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "issue_summary": str(exc),
            "stage": failed_stage,
            "traceback": error_traceback,
            "log_path": log_path,
            "workspace_path": preserved_workspace,
            "updated_at": time.time(),
        }
        try:
            with open(log_path, "a", encoding="utf-8", buffering=1) as worker_log:
                worker_log.write("\n[WORKER FAILED]\n")
                worker_log.write(error_traceback)
                if preserved_workspace:
                    worker_log.write(f"\n[WORKSPACE PRESERVED FOR RECOVERY] {preserved_workspace}\n")
        except Exception:
            pass
        if issue_path:
            try:
                _video_producer_write_json_atomic(issue_path, issue_payload)
            except Exception as issue_write_exc:
                try:
                    with open(log_path, "a", encoding="utf-8") as worker_log:
                        worker_log.write(f"\n[ISSUE REPORT WRITE FAILED] {issue_write_exc}\n")
                except Exception:
                    pass
        try:
            _video_producer_write_worker_status(status_path, {
                **base_status,
                **previous_status,
                "status": "failed",
                "stage": f"Issue during: {failed_stage}",
                "detail": str(exc),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "issue_summary": str(exc),
                "issue_stage": failed_stage,
                "traceback": error_traceback,
                "issue_path": issue_path,
                "started_at": started_at,
                "finished_at": time.time(),
                "workspace_path": preserved_workspace,
            })
        except Exception:
            pass
        print(f"❌ [VIDEO-ISSUE] {title} | {type(exc).__name__}: {exc}")
        return {
            "project_title": title,
            "status": "failed",
            "error": str(exc),
            "error_type": type(exc).__name__,
            "traceback": error_traceback,
            "issue": issue_payload,
            "pid": pid,
            "lane": job.get("lane"),
            "worker_id": job.get("worker_id"),
            "log_path": log_path,
            "issue_path": issue_path,
            "workspace_path": preserved_workspace,
        }

def _video_producer_is_resource_failure(result):
    """Identify failures that are worth retrying with one rendering process."""
    if not isinstance(result, dict) or str(result.get("status", "")).casefold() != "failed":
        return False
    detail = " ".join((
        str(result.get("error") or ""),
        str(result.get("traceback") or ""),
        str(result.get("detail") or ""),
    )).casefold()
    indicators = (
        "memoryerror", "out of memory", "not enough memory", "cannot allocate memory",
        "failed to allocate", "cuda error: out of memory", "cudnn_status_alloc_failed",
        "winerror 8", "winerror 1450", "winerror 1455",
        "resource temporarily unavailable", "brokenprocesspool",
    )
    return any(token in detail for token in indicators)


def _video_producer_write_parent_worker_error(job, stage, error_text):
    """Record a retry state without allowing dashboard/logging errors to stop production."""
    import os
    import time
    try:
        with open(job.get("log_path", os.devnull), "a", encoding="utf-8", buffering=1) as handle:
            handle.write(f"\n[PARENT] {stage}: {error_text}\n")
    except OSError:
        pass
    try:
        previous = _video_producer_read_worker_status(job.get("status_path"))
        _video_producer_write_worker_status(job["status_path"], {
            **previous,
            "worker_id": job.get("worker_id"),
            "lane": str(job.get("lane") or "cpu").upper(),
            "project_title": job.get("project_title"),
            "status": "queued",
            "stage": stage,
            "progress": 0,
            "detail": str(error_text),
            "log_path": job.get("log_path"),
            "status_path": job.get("status_path"),
            "updated_at": time.time(),
        })
    except Exception:
        pass


def _video_producer_execute_jobs_resilient(jobs, worker_count, run_dir):
    """Run with the requested process count, retry with one process, then last-resort inline.

    This is still multiprocessing by default, including a one-worker ProcessPool.
    If Windows cannot create a child process at all, a final inline attempt is made
    so a single video can still render rather than abandoning the whole batch.
    """
    import multiprocessing
    import traceback
    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

    if not jobs:
        return []

    # SceneIQ already isolates the renderer from the GUI with the dedicated
    # --sceneiq-worker service process. When the RAM planner selects one render
    # process (the normal case on low-memory machines), run each project inside
    # that service process instead of spawning a second Python interpreter via a
    # one-worker ProcessPoolExecutor. This restores the working solo producer's
    # memory profile while keeping the desktop responsive and each project fully
    # isolated by its own workspace, status file, log, checkpoint and exception
    # boundary. A project's failure is recorded and the next project still runs.
    if max(1, int(worker_count or 1)) <= 1 or len(jobs) == 1:
        print(
            f"🎞️ [WORKER-ISOLATION] Running {len(jobs)} project(s) sequentially inside "
            "the isolated video-service process. No nested ProcessPool child will be spawned."
        )
        inline_results = []
        for job in jobs:
            try:
                item_result = _video_producer_process_worker(job)
            except Exception as exc:
                import traceback as _inline_traceback
                error_traceback = _inline_traceback.format_exc()
                issue = {
                    "project_title": job.get("project_title"),
                    "worker_id": job.get("worker_id"),
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "stage": "Video worker startup",
                    "traceback": error_traceback,
                    "log_path": job.get("log_path"),
                    "workspace_path": job.get("workspace_path"),
                    "updated_at": time.time(),
                }
                try:
                    if job.get("issue_path"):
                        _video_producer_write_json_atomic(job["issue_path"], issue)
                    previous = _video_producer_read_worker_status(job.get("status_path"))
                    _video_producer_write_worker_status(job["status_path"], {
                        **previous, **issue,
                        "detail": str(exc),
                        "issue_path": job.get("issue_path"),
                        "finished_at": time.time(),
                    })
                except Exception:
                    pass
                item_result = {
                    "project_title": job.get("project_title"),
                    "status": "failed",
                    "error": str(exc),
                    "traceback": error_traceback,
                    "worker_id": job.get("worker_id"),
                    "log_path": job.get("log_path"),
                    "issue_path": job.get("issue_path"),
                }
            inline_results.append(item_result)
        return inline_results

    context = multiprocessing.get_context("spawn")
    results_by_id = {}
    retry_jobs = []
    accounted = set()
    future_to_job = {}
    executor = None

    def key_for(job):
        return str(job.get("worker_id") or job.get("project_title") or id(job))

    def keep_retry(job, stage, error_text):
        job_key = key_for(job)
        if job_key in accounted or any(key_for(existing) == job_key for existing in retry_jobs):
            return
        retry_jobs.append(job)
        _video_producer_write_parent_worker_error(job, stage, error_text)

    def save_result(job, item_result, allow_resource_retry):
        job_key = key_for(job)
        if allow_resource_retry and _video_producer_is_resource_failure(item_result):
            keep_retry(
                job,
                "Retrying with one rendering process",
                "The concurrent worker reported a memory/resource failure; this project will be retried alone.",
            )
            return
        results_by_id[job_key] = item_result
        accounted.add(job_key)

    # First attempt: use the resource-aware worker count. Pool creation, submit,
    # worker crashes, and BrokenProcessPool are all recoverable here.
    try:
        executor = ProcessPoolExecutor(
            max_workers=max(1, int(worker_count or 1)),
            mp_context=context,
        )
        for index, job in enumerate(jobs):
            try:
                future = executor.submit(_video_producer_process_worker, job)
                future_to_job[future] = job
            except Exception as exc:
                keep_retry(
                    job,
                    "Retrying after process startup failure",
                    f"Could not submit worker process: {exc}",
                )
                for remaining_job in jobs[index + 1:]:
                    keep_retry(
                        remaining_job,
                        "Retrying after process startup failure",
                        "The process pool could not accept the remaining jobs; they will run one at a time.",
                    )
                break

        pending = set(future_to_job)
        while pending:
            done, pending = wait(pending, timeout=1.0, return_when=FIRST_COMPLETED)
            for future in done:
                job = future_to_job[future]
                try:
                    item_result = future.result()
                except Exception as exc:
                    error_text = f"{exc}\n{traceback.format_exc()}"
                    keep_retry(job, "Retrying after worker process failure", error_text)
                else:
                    save_result(job, item_result, allow_resource_retry=True)
    except Exception as exc:
        error_text = f"Process-pool failure: {exc}\n{traceback.format_exc()}"
        for job in jobs:
            if key_for(job) not in accounted:
                keep_retry(job, "Retrying with one rendering process", error_text)
    finally:
        if executor is not None:
            try:
                executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass

    # Include anything the pool never returned a result for (for example, a
    # worker process terminated while Windows was under memory pressure).
    for job in jobs:
        job_key = key_for(job)
        if job_key not in accounted and not any(key_for(item) == job_key for item in retry_jobs):
            keep_retry(
                job,
                "Retrying with one rendering process",
                "The initial process pool did not return a result for this job.",
            )

    # Second attempt: exactly one child process at a time. A fresh one-worker
    # pool avoids inheriting a broken executor from the parallel attempt.
    emergency_inline_jobs = []
    single_executor = None
    retry_index = 0
    try:
        if retry_jobs:
            single_executor = ProcessPoolExecutor(max_workers=1, mp_context=context)
            for retry_index, job in enumerate(retry_jobs):
                _video_producer_write_parent_worker_error(
                    job,
                    "Retrying with one rendering process",
                    "A single multiprocessing worker has been allocated for this project.",
                )
                try:
                    item_result = single_executor.submit(
                        _video_producer_process_worker, job
                    ).result()
                except Exception as exc:
                    error_text = f"Single-worker process failed: {exc}\n{traceback.format_exc()}"
                    _video_producer_write_parent_worker_error(
                        job, "Falling back to in-process production", error_text
                    )
                    emergency_inline_jobs.extend(retry_jobs[retry_index:])
                    break
                if _video_producer_is_resource_failure(item_result):
                    _video_producer_write_parent_worker_error(
                        job,
                        "Falling back to in-process production",
                        "The one-worker process also reported a memory/resource failure.",
                    )
                    emergency_inline_jobs.append(job)
                else:
                    results_by_id[key_for(job)] = item_result
                    accounted.add(key_for(job))
    except Exception as exc:
        error_text = f"Could not create a one-worker process pool: {exc}\n{traceback.format_exc()}"
        for job in retry_jobs[retry_index:]:
            _video_producer_write_parent_worker_error(
                job, "Falling back to in-process production", error_text
            )
            emergency_inline_jobs.append(job)
    finally:
        if single_executor is not None:
            try:
                single_executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass

    # Last-resort path: still use the same production worker and private-workspace
    # protection, but execute it in the parent only when spawning is unavailable.
    for job in emergency_inline_jobs:
        try:
            item_result = _video_producer_process_worker(job)
        except Exception as exc:
            error_text = f"Inline fallback failed: {exc}\n{traceback.format_exc()}"
            _video_producer_write_parent_worker_error(job, "Final fallback failed", error_text)
            item_result = {
                "project_title": job.get("project_title"),
                "status": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "lane": job.get("lane"),
                "worker_id": job.get("worker_id"),
                "log_path": job.get("log_path"),
            }
        results_by_id[key_for(job)] = item_result
        accounted.add(key_for(job))

    return [results_by_id[key_for(job)] for job in jobs if key_for(job) in results_by_id]


def _video_producer_get_safe_worker_limit(cpu_total=None):
    """Return a conservative process limit from currently available RAM.

    Low-memory or missing-psutil situations always select one process. The limit
    is intentionally based on AVAILABLE memory rather than installed RAM.
    """
    import os
    cpu_total = max(1, int(cpu_total or os.cpu_count() or 1))
    try:
        import psutil
        available_gb = float(psutil.virtual_memory().available) / (1024 ** 3)
    except Exception:
        return 1, None

    if available_gb < 12:
        limit = 1
    elif available_gb < 20:
        limit = 2
    elif available_gb < 30:
        limit = 3
    else:
        limit = 4
    return max(1, min(limit, cpu_total)), available_gb


_VIDEO_PRODUCER_DASHBOARD_SESSION = None


def _video_producer_start_dashboard_session():
    """Start one persistent GUI before doing any video/queue/resource work."""
    import datetime
    import os
    import time

    global _VIDEO_PRODUCER_DASHBOARD_SESSION
    current = _VIDEO_PRODUCER_DASHBOARD_SESSION
    if isinstance(current, dict):
        # In the Serenum-style architecture the visible Tk window lives in the
        # parent process and this process is only the isolated video service.
        # Never launch a second, detached or minimized dashboard from the worker.
        if current.get("ui_managed"):
            return current
        process = current.get("process")
        if process is not None and process.poll() is None and not _video_producer_dashboard_shutdown_requested(current.get("shutdown_path")):
            return current

    configured_ready = globals().get("READY_SCRIPT")
    base_dir = os.path.dirname(os.path.abspath(os.fspath(configured_ready))) if configured_ready else os.getcwd()
    log_root = os.path.join(base_dir, "video_producer_runs")
    stamp = datetime.datetime.now().strftime("dashboard_%Y%m%d_%H%M%S_%f")
    session_dir = os.path.join(log_root, f"{stamp}_parent_{os.getpid()}")
    os.makedirs(session_dir, exist_ok=True)
    manifest_path = os.path.join(session_dir, "dashboard_manifest.json")
    shutdown_path = os.path.join(session_dir, "dashboard_shutdown.json")
    heartbeat_path = os.path.join(session_dir, "dashboard_heartbeat.json")
    session = {
        "session_dir": session_dir,
        "manifest_path": manifest_path,
        "shutdown_path": shutdown_path,
        "heartbeat_path": heartbeat_path,
        "ready_path": manifest_path + ".ready.json",
        "process": None,
        "pid": None,
        "error": None,
        "created_at": time.time(),
        "manifest_cache": None,
    }
    initial_manifest = {
        "window_title": "SceneIQ Video Production",
        "created_at": time.time(),
        "session_dir": session_dir,
        "service_status": "Starting",
        "message": "The SceneIQ dashboard is starting independently of video production. The queue and worker system will load after the window is ready.",
        "shutdown_path": shutdown_path,
        "heartbeat_path": heartbeat_path,
        "jobs": [],
    }
    try:
        _video_producer_write_json_atomic(manifest_path, initial_manifest)
    except Exception:
        import json
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(initial_manifest, handle, ensure_ascii=False, indent=2)

    # Store the session before launching so even a failed GUI launch is visible
    # in diagnostics and never causes repeated hidden dashboard launches.
    session["manifest_cache"] = dict(initial_manifest)
    _VIDEO_PRODUCER_DASHBOARD_SESSION = session
    try:
        info = _video_producer_launch_dashboard_window(
            manifest_path,
            timeout_seconds=float(os.environ.get("VIDEO_DASHBOARD_START_TIMEOUT", "30")),
        )
        session.update({"process": info["process"], "pid": info["pid"], "ready_path": info["ready_path"]})
        _video_producer_update_dashboard_session(
            message="SceneIQ Video Production window is open (minimized). Checking the video queue…",
            service_status="Checking queue",
        )
        print(f"🖥️ [DASHBOARD] SceneIQ Video Production window launched and confirmed (PID {info['pid']}).")
    except Exception as exc:
        session["error"] = str(exc)
        try:
            _video_producer_write_json_atomic(manifest_path, {
                **initial_manifest,
                "service_status": "Dashboard startup failed",
                "message": f"Dashboard could not start: {exc}. Video production remains independent.",
            })
        except Exception:
            pass
        print(f"❌ [DASHBOARD] Could not create the desktop window: {exc}")
    return session


def _video_producer_update_dashboard_session(message=None, service_status=None, jobs=None):
    """Update the UI's independent manifest; failure never interrupts rendering."""
    session = globals().get("_VIDEO_PRODUCER_DASHBOARD_SESSION")
    if not isinstance(session, dict):
        return False
    path = session.get("manifest_path")
    if not path:
        return False
    manifest = _video_producer_read_json(path, {})
    if not isinstance(manifest, dict) or not manifest:
        cached = session.get("manifest_cache")
        manifest = dict(cached) if isinstance(cached, dict) else {}
    if message is not None:
        manifest["message"] = str(message)
    if service_status is not None:
        manifest["service_status"] = str(service_status)
    if jobs is not None:
        manifest["jobs"] = jobs
    manifest["last_updated_at"] = time.time()
    manifest.setdefault("shutdown_path", session.get("shutdown_path"))
    manifest.setdefault("heartbeat_path", session.get("heartbeat_path"))
    session["manifest_cache"] = dict(manifest)
    try:
        return _video_producer_write_json_atomic(path, manifest)
    except Exception as exc:
        # The GUI remains up even when the manifest/status filesystem is busy.
        print(f"⚠️ [DASHBOARD] Could not update dashboard information: {exc}")
        return False


def _video_producer_dashboard_session_closed(session=None):
    """Detect deliberate window close or a dashboard process that was killed."""
    import os
    import time

    if not isinstance(session, dict):
        session = globals().get("_VIDEO_PRODUCER_DASHBOARD_SESSION")
    if not isinstance(session, dict):
        return False
    if _video_producer_dashboard_shutdown_requested(session.get("shutdown_path")):
        return True
    process = session.get("process")
    if process is not None:
        try:
            if process.poll() is not None:
                return True
        except Exception:
            pass
    # The visible GUI is the parent process in the integrated architecture.
    # Its heartbeat is authoritative when this service process has no GUI handle.
    heartbeat_path = session.get("heartbeat_path")
    if heartbeat_path:
        try:
            age = time.time() - os.path.getmtime(heartbeat_path)
            return age > float(os.environ.get("VIDEO_DASHBOARD_HEARTBEAT_TIMEOUT", "12"))
        except OSError:
            return time.time() - float(session.get("created_at", time.time())) > 15.0
    return False


def video_producer_main(cpu_workers=None, gpu_workers=None, max_projects=None):
    """Run SceneIQ projects under the desktop-owned manifest and safe worker controls.

    The visible Tk window belongs to the parent desktop process. This function
    runs only inside the isolated producer-service child, updates the shared
    manifest, and starts rendering workers within the available RAM budget.
    A one-worker budget runs inline inside this isolated service process to avoid
    a needless nested process. Multi-worker pool failures are retried serially.
    """
    import os
    import json
    import time
    import datetime
    import traceback

    # The desktop application creates the visible window and its session before
    # starting this isolated service process. Do not create or launch another GUI.
    dashboard_session = globals().get("_VIDEO_PRODUCER_DASHBOARD_SESSION")
    if not isinstance(dashboard_session, dict):
        dashboard_session = _video_producer_start_dashboard_session()
    if _video_producer_dashboard_session_closed(dashboard_session):
        return {"total": 0, "completed": 0, "skipped": 0, "failed": 0,
                "results": [], "dashboard_closed": True}
    _video_producer_update_dashboard_session(
        message="The dashboard is open. Reading the production queue and checking project files…",
        service_status="Checking queue",
    )

    ready_script_path = globals().get("READY_SCRIPT")
    images_path = globals().get("IMAGES_PATH")
    subscribe_stickers_path = globals().get("SUBSCRIBE_STICKERS")
    if not ready_script_path or not images_path:
        message = "Video production cannot start: READY_SCRIPT or IMAGES_PATH is not configured. The dashboard remains open."
        _video_producer_update_dashboard_session(message=message, service_status="Configuration error")
        raise RuntimeError("video_producer_main requires module-level READY_SCRIPT and IMAGES_PATH.")

    ready_script_path = os.path.abspath(os.fspath(ready_script_path))
    images_path = os.path.abspath(os.fspath(images_path))
    subscribe_stickers_path = (
        os.path.abspath(os.fspath(subscribe_stickers_path))
        if subscribe_stickers_path else None
    )
    if not os.path.isfile(ready_script_path):
        _video_producer_update_dashboard_session(
            message=f"Video production is waiting because READY_SCRIPT was not found: {ready_script_path}",
            service_status="Waiting for ready_script.json",
        )
        raise FileNotFoundError(f"READY_SCRIPT not found: {ready_script_path}")
    if not os.path.isdir(images_path):
        _video_producer_update_dashboard_session(
            message=f"Video production is waiting because the project images folder was not found: {images_path}",
            service_status="Waiting for project images folder",
        )
        raise NotADirectoryError(f"IMAGES_PATH not found: {images_path}")

    configured_log_root = os.environ.get("VIDEO_PRODUCER_LOG_DIR")
    if configured_log_root:
        log_root = os.path.abspath(os.path.expanduser(configured_log_root))
    else:
        log_root = os.path.join(os.path.dirname(ready_script_path), "video_producer_runs")
    run_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = os.path.join(log_root, f"run_{run_stamp}_parent_{os.getpid()}")
    os.makedirs(run_dir, exist_ok=True)

    # Capture one stable queue snapshot. Every render child then works from this
    # snapshot and its own private project workspace.
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
    project_categories = [record.get("project_category") for record in project_records]

    if not project_titles:
        _video_producer_update_dashboard_session(
            message="The dashboard is ready. No eligible video projects were found yet; it will keep checking for new projects.",
            service_status="Waiting for video projects",
            jobs=[],
        )
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
            "cpu_workers": 0,
            "gpu_workers": 0,
            "available_memory_gb": None,
        }

    gpu_info = _video_producer_detect_gpu()
    cpu_total = max(1, int(os.cpu_count() or 2))
    safe_total_workers, available_memory_gb = _video_producer_get_safe_worker_limit(cpu_total)

    # Stable defaults: no more than two render processes by default, and only
    # one when available RAM is below 12 GiB. Explicit settings are still capped
    # by the live memory budget so an environment variable cannot exhaust RAM.
    def read_worker_count(value, default, minimum):
        try:
            return max(minimum, int(value))
        except (TypeError, ValueError):
            print(f"⚠️ [RESOURCE-BUDGET] Invalid worker count {value!r}; using {default}.")
            return max(minimum, int(default))

    if cpu_workers is None:
        env_cpu = os.environ.get("VIDEO_CPU_WORKERS")
        requested_cpu_workers = (
            read_worker_count(env_cpu, min(2, safe_total_workers), 1)
            if env_cpu not in (None, "") else min(2, safe_total_workers)
        )
    else:
        requested_cpu_workers = read_worker_count(cpu_workers, 1, 1)
    requested_cpu_workers = max(1, requested_cpu_workers)

    if gpu_workers is None:
        env_gpu = os.environ.get("VIDEO_GPU_WORKERS")
        requested_gpu_workers = (
            read_worker_count(env_gpu, 0, 0) if env_gpu not in (None, "") else 0
        )
    else:
        requested_gpu_workers = read_worker_count(gpu_workers, 0, 0)
    requested_gpu_workers = max(0, requested_gpu_workers)
    if requested_gpu_workers and not gpu_info["gpu_available"]:
        print("⚠️ [GPU] GPU worker requested but no usable CUDA/NVENC capability was detected; using CPU workers only.")
        requested_gpu_workers = 0

    requested_total = requested_cpu_workers + requested_gpu_workers
    allowed_total = max(1, min(safe_total_workers, len(project_titles), requested_total))
    effective_cpu_workers = min(requested_cpu_workers, allowed_total)
    effective_gpu_workers = min(
        requested_gpu_workers,
        max(0, allowed_total - effective_cpu_workers),
    )
    if effective_cpu_workers < requested_cpu_workers or effective_gpu_workers < requested_gpu_workers:
        print(
            "🧠 [RESOURCE-BUDGET] Worker count reduced to protect available memory: "
            f"requested CPU/GPU={requested_cpu_workers}/{requested_gpu_workers}, "
            f"allowed CPU/GPU={effective_cpu_workers}/{effective_gpu_workers}, "
            f"available RAM={available_memory_gb:.1f} GiB" if available_memory_gb is not None
            else "🧠 [RESOURCE-BUDGET] Worker count reduced to one because available RAM could not be measured."
        )
    print(
        f"🧠 [RESOURCE-BUDGET] Available RAM: "
        f"{available_memory_gb:.1f} GiB | rendering processes: "
        f"{effective_cpu_workers + effective_gpu_workers} "
        f"(CPU={effective_cpu_workers}, GPU={effective_gpu_workers})"
        if available_memory_gb is not None else
        f"🧠 [RESOURCE-BUDGET] RAM telemetry unavailable; using one safe rendering process. "
        f"(CPU={effective_cpu_workers}, GPU={effective_gpu_workers})"
    )

    gpu_profile = None
    if effective_gpu_workers:
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
            "ffmpeg_threads": max(1, min(2, cpu_total // max(1, effective_gpu_workers))),
            "ffmpeg_binary": gpu_info.get("ffmpeg_binary"),
        }

    cpu_profile = {
        "whisper_device": "cpu",
        "whisper_compute_type": os.environ.get("VIDEO_CPU_WHISPER_COMPUTE", "int8"),
        "video_encoder": "libx264",
        "encoder_preset": os.environ.get("VIDEO_CPU_PRESET", "slow"),
        "ffmpeg_threads": max(1, min(4, cpu_total // max(1, effective_cpu_workers))),
        "ffmpeg_binary": None,
    }

    checkpoint_root = os.path.join(os.path.dirname(ready_script_path), "video_producer_checkpoints")
    os.makedirs(checkpoint_root, exist_ok=True)
    shutdown_path = dashboard_session.get("shutdown_path")
    heartbeat_path = dashboard_session.get("heartbeat_path")

    lane_pattern = (["cpu"] * effective_cpu_workers) + (["gpu"] * effective_gpu_workers)
    all_jobs = []
    cpu_index = 0
    gpu_index = 0
    for project_index, title in enumerate(project_titles):
        lane = lane_pattern[len(all_jobs) % len(lane_pattern)]
        if lane == "gpu":
            gpu_index += 1
            worker_id = f"GPU-{gpu_index:03d}"
            profile = gpu_profile
        else:
            cpu_index += 1
            worker_id = f"CPU-{cpu_index:03d}"
            profile = cpu_profile
        category_value = project_categories[project_index] if project_index < len(project_categories) else None
        checkpoint_key = hashlib.sha256(
            f"{str(category_value or '')}|{title}".casefold().encode("utf-8")
        ).hexdigest()[:20]
        project_checkpoint_dir = os.path.join(checkpoint_root, checkpoint_key)
        os.makedirs(project_checkpoint_dir, exist_ok=True)
        all_jobs.append({
            "project_title": title,
            "project_category": category_value,
            "ready_script_path": ready_script_snapshot_path,
            "images_path": images_path,
            "subscribe_stickers_path": subscribe_stickers_path,
            "workspace_root": os.path.join(project_checkpoint_dir, "worker_workspaces"),
            "workspace_path": os.path.join(project_checkpoint_dir, "workspace"),
            "checkpoint_dir": project_checkpoint_dir,
            "control_path": os.path.join(project_checkpoint_dir, "control.json"),
            "issue_path": os.path.join(project_checkpoint_dir, "issue.json"),
            "shutdown_path": shutdown_path,
            "dashboard_heartbeat_path": heartbeat_path,
            "parent_pid": os.getpid(),
            "profile": dict(profile or {}),
            "lane": lane,
            "worker_id": worker_id,
            "queued_at": time.time(),
        })

    # A worker is never assigned more FFmpeg threads than its lane budget.
    for job in all_jobs:
        if job["lane"] == "cpu":
            job["profile"]["ffmpeg_threads"] = cpu_profile["ffmpeg_threads"]
        else:
            job["profile"]["ffmpeg_threads"] = gpu_profile["ffmpeg_threads"]

    for job in all_jobs:
        try:
            _video_producer_write_control(job["control_path"], "run")
        except Exception as control_exc:
            print(f"⚠️ [CONTROL] Could not initialize {job.get('worker_id')}: {control_exc}")
        saved_progress = _video_producer_read_json(
            os.path.join(job["checkpoint_dir"], "progress.json"), {}
        )
        saved_stage = saved_progress.get("stage") if isinstance(saved_progress, dict) else None
        saved_detail = saved_progress.get("detail") if isinstance(saved_progress, dict) else None
        safe_title = _video_producer_normalize_title(job["project_title"])
        filename_base = f"{job['worker_id']}_{safe_title[:70]}"
        job["log_path"] = os.path.join(run_dir, filename_base + ".log")
        job["status_path"] = os.path.join(run_dir, filename_base + ".status.json")
        job["preview_path"] = os.path.join(run_dir, "previews", filename_base + ".jpg")
        try:
            _video_producer_write_worker_status(job["status_path"], {
                "worker_id": job["worker_id"],
                "lane": job["lane"].upper(),
                "pid": None,
                "project_title": job["project_title"],
                "status": "queued",
                "stage": "Waiting for a rendering process",
                "progress": saved_progress.get("progress") if isinstance(saved_progress, dict) else None,
                "current": saved_progress.get("current") if isinstance(saved_progress, dict) else None,
                "total": saved_progress.get("total") if isinstance(saved_progress, dict) else None,
                "detail": (
                    f"Saved checkpoint found. Last stage: {saved_stage}. {saved_detail or ''} "
                    "Completed work will be reused."
                    if saved_stage else
                    "The project is queued for video production."
                ),
                "queued_at": job["queued_at"],
                "log_path": job["log_path"],
                "status_path": job["status_path"],
                "preview_path": job["preview_path"],
                "control_path": job["control_path"],
                "issue_path": job.get("issue_path"),
                "encoder": job["profile"].get("video_encoder"),
                "whisper_device": job["profile"].get("whisper_device"),
                "whisper_compute_type": job["profile"].get("whisper_compute_type"),
            })
        except Exception as status_exc:
            print(f"⚠️ [WORKER-STATUS] Initial status could not be written for {job['project_title']}: {status_exc}")

    dashboard_manifest_path = dashboard_session.get("manifest_path")
    dashboard_jobs = [
        {
            "worker_id": job["worker_id"],
            "project_title": job["project_title"],
            "lane": job["lane"],
            "encoder": job["profile"].get("video_encoder"),
            "status_path": job["status_path"],
            "log_path": job["log_path"],
            "preview_path": job["preview_path"],
            "control_path": job["control_path"],
            "issue_path": job.get("issue_path"),
            "checkpoint_dir": job["checkpoint_dir"],
        }
        for job in all_jobs
    ]
    _video_producer_update_dashboard_session(
        message=(
            f"Loaded {len(all_jobs)} video project(s). Resource budget: "
            f"{effective_cpu_workers} CPU worker(s), {effective_gpu_workers} GPU worker(s). "
            "Select a video's own Pause, Resume, Stop or Start control."
        ),
        service_status="Producing videos",
        jobs=dashboard_jobs,
    )
    dashboard_info = {
        "pid": dashboard_session.get("pid"),
        "process": dashboard_session.get("process"),
        "ready_path": dashboard_session.get("ready_path"),
    } if dashboard_session.get("pid") else None
    dashboard_launch_error = dashboard_session.get("error")
    print(
        "🖥️ [DASHBOARD] Worker cards and controls were published to the already-running window. "
        "Dashboard refresh errors cannot stop video rendering."
    )

    results = _video_producer_execute_jobs_resilient(
        all_jobs,
        worker_count=max(1, effective_cpu_workers + effective_gpu_workers),
        run_dir=run_dir,
    )

    # Failed/stopped projects remain as individual cards. They are not retried
    # forever in the background. A user can inspect the Issue report, fix the
    # missing asset, then press Start on that card. New source files also release
    # this wait so the service can re-read the queue.
    restartable_by_id = {
        str(item.get("worker_id")): item
        for item in results
        if str(item.get("status", "")).casefold() in {"stopped", "failed"}
    }
    def current_project_input_signature():
        try:
            ready_stat = os.stat(ready_script_path)
            ready_value = (ready_stat.st_mtime_ns, ready_stat.st_size)
        except OSError:
            ready_value = (None, None)
        project_value = _video_producer_tree_signature(images_path)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        try:
            download_stat = os.stat(downloads)
            download_value = (download_stat.st_mtime_ns, download_stat.st_size)
        except OSError:
            download_value = (None, None)
        return ready_value, project_value, download_value

    finished_input_signature = current_project_input_signature()
    while restartable_by_id:
        dashboard_closed = _video_producer_dashboard_session_closed(dashboard_session)
        if dashboard_closed:
            for job in all_jobs:
                try:
                    _video_producer_write_control(job["control_path"], "stop")
                except Exception:
                    pass
            print("🛑 [DASHBOARD] Window closed or terminated. Remaining videos are stopping safely; saved checkpoints are retained.")
            break

        # New ready-script projects, scene images, or narration files should be
        # picked up by the outer service loop without requiring a GUI restart.
        if current_project_input_signature() != finished_input_signature:
            print("🔄 [VIDEO-SERVICE] New project input detected; returning to queue monitoring.")
            break

        restarted_jobs = []
        for job in all_jobs:
            key = str(job.get("worker_id"))
            if key not in restartable_by_id:
                continue
            control_data = _video_producer_read_json(job["control_path"], {})
            if isinstance(control_data, dict) and str(control_data.get("command", "")).casefold() in {"start", "resume"}:
                _video_producer_write_control(job["control_path"], "run")
                previous_state = _video_producer_read_worker_status(job["status_path"])
                _video_producer_write_worker_status(job["status_path"], {
                    **previous_state,
                    "status": "queued",
                    "stage": "Restarting from saved progress",
                    "detail": "Restart requested for this video only. Saved narration timing, prepared project files and completed scene renders will be reused.",
                    "error": None,
                    "error_type": None,
                    "traceback": None,
                    "updated_at": time.time(),
                })
                restarted_jobs.append(job)

        if restarted_jobs:
            retry_results = _video_producer_execute_jobs_resilient(
                restarted_jobs, worker_count=1, run_dir=run_dir
            )
            for retry_result in retry_results:
                key = str(retry_result.get("worker_id"))
                if str(retry_result.get("status", "")).casefold() in {"stopped", "failed"}:
                    restartable_by_id[key] = retry_result
                else:
                    restartable_by_id.pop(key, None)
                    results = [item for item in results if str(item.get("worker_id")) != key]
                    results.append(retry_result)
        else:
            time.sleep(0.5)

    dashboard_closed = _video_producer_dashboard_session_closed(dashboard_session)
    if dashboard_closed:
        for job in all_jobs:
            try:
                _video_producer_write_control(job["control_path"], "stop")
            except Exception:
                pass
        _video_producer_update_dashboard_session(
            message="The dashboard was closed. Active videos are stopping at their next safe checkpoint; saved work is preserved.",
            service_status="Stopping safely",
        )
    else:
        _video_producer_update_dashboard_session(
            message="This batch has finished. The dashboard remains open and the service will continue watching for new projects or individual Start commands.",
            service_status="Waiting for new projects or video controls",
        )

    completed = sum(str(item.get("status", "")).casefold() == "completed" for item in results)
    failed = sum(str(item.get("status", "")).casefold() == "failed" for item in results)
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
        "available_memory_gb": available_memory_gb,
        "dashboard_pid": dashboard_info["pid"] if dashboard_info else None,
        "dashboard_error": dashboard_launch_error,
        "dashboard_ready_path": dashboard_info["ready_path"] if dashboard_info else None,
        "dashboard_closed": bool(dashboard_closed),
    }

def video_producer():
    """Backward-compatible entry point; now launches parallel bulk production."""
    return video_producer_main()


def video_producer_service_loop(poll_interval=2.0, retry_interval=None):
    """Continuously detect newly ready projects without rebuilding empty batches."""
    poll_interval = max(1.0, float(poll_interval or 2.0))
    retry_interval = (
        None if retry_interval is None
        else max(10.0, float(retry_interval))
    )
    last_input_signature = None
    last_batch_at = 0.0
    print("🎞️ [VIDEO-SERVICE] Independent video producer service started.")
    dashboard_session = globals().get("_VIDEO_PRODUCER_DASHBOARD_SESSION")
    if not isinstance(dashboard_session, dict):
        dashboard_session = _video_producer_start_dashboard_session()

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
                generated_directory_names = {
                    "edited", "temp_captions", "video_producer_runs",
                    "video_producer_checkpoints", "worker_workspaces", "__pycache__",
                }
                for directory, subdirectories, _ in os.walk(IMAGES_PATH):
                    subdirectories[:] = [
                        name for name in subdirectories
                        if name.casefold() not in generated_directory_names
                    ]
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
            if _video_producer_dashboard_session_closed(dashboard_session):
                print("🛑 [DASHBOARD] Window closed or its process was terminated. The service is exiting after safe worker checkpoints.")
                return
            signature = current_input_signature()
            now = time.monotonic()
            inputs_changed = signature != last_input_signature
            retry_due = (
                retry_interval is not None
                and now - last_batch_at >= max(1.0, float(retry_interval))
            )
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
                    if result.get("dashboard_closed"):
                        print("🛑 [VIDEO-SERVICE] Dashboard was closed. All active video workers have saved progress; the producer service is exiting.")
                        return
        except KeyboardInterrupt:
            print("🛑 [VIDEO-SERVICE] KeyboardInterrupt received; video service is stopping.")
            raise
        except Exception as video_error:
            # A production exception updates the already-running window; it never
            # tears down or prevents the GUI from existing.
            print(f"❌ [VIDEO-SERVICE] This video batch failed independently: {video_error}")
            try:
                _video_producer_update_dashboard_session(
                    message=f"Video service encountered an issue: {video_error}. The window remains open; the service is waiting for corrected or changed project inputs.",
                    service_status="Production issue — waiting for input changes",
                )
            except Exception:
                pass
            traceback.print_exc()
            last_batch_at = time.monotonic()
        time.sleep(poll_interval)



# -----------------------------------------------------------------------------
# SCENEIQ DESKTOP CONTROL CENTER
# -----------------------------------------------------------------------------
# The visible Tk window is hosted by the main process, exactly like Serenum.
# The video-producer service is launched as a separate child process. This keeps
# the GUI responsive and visible even while MoviePy/Whisper/multiprocessing work
# is running or recovering from a failed video job.

class _SceneIQTextStream:
    """Thread-safe stdout/stderr bridge into the SceneIQ desktop console."""
    def __init__(self, app, fallback):
        self.app = app
        self.fallback = fallback
        self.encoding = getattr(fallback, "encoding", "utf-8")

    def write(self, value):
        if value:
            self.app.enqueue_log(str(value))
        return len(value) if value is not None else 0

    def flush(self):
        return None

    def isatty(self):
        return False

    def writable(self):
        return True


def _sceneiq_apply_dark_titlebar(window, background="#07111F", foreground="#EAF5FF"):
    """Match the native Windows title bar to SCiQ's dark window surface."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        window.update_idletasks()
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        hwnd = wintypes.HWND(window.winfo_id())
        try:
            top = user32.GetAncestor(hwnd, 2)
            if top:
                hwnd = top
        except Exception:
            pass
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        set_attribute = dwmapi.DwmSetWindowAttribute
        set_attribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        set_attribute.restype = ctypes.c_long
        enabled = ctypes.c_int(1)
        dark_enabled = False
        for attribute in (20, 19):
            try:
                if set_attribute(hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)) == 0:
                    dark_enabled = True
                    break
            except Exception:
                continue
        def colorref(value):
            value = str(value).lstrip("#")
            red, green, blue = (int(value[i:i+2], 16) for i in (0, 2, 4))
            return blue << 16 | green << 8 | red
        for attribute, value in ((35, background), (36, foreground), (34, background)):
            try:
                color = wintypes.DWORD(colorref(value))
                set_attribute(hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color))
            except Exception:
                pass
        return dark_enabled
    except Exception:
        return False


_SCENEIQ_SINGLE_INSTANCE_HANDLE = None


def _sceneiq_acquire_single_instance():
    """Prevent duplicate SceneIQ windows/services from being started accidentally."""
    import os
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, "Local\\SceneIQVideoProductionControlCenter")
        if not handle:
            # Failure to create a mutex should not block the desktop from launching.
            return True
        already_exists = int(kernel32.GetLastError()) == 183  # ERROR_ALREADY_EXISTS
        if already_exists:
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "SceneIQ Video Production is already running. Use the existing window instead of opening another copy.",
                    "SceneIQ is already open",
                    0x00000040,
                )
            except Exception:
                pass
            kernel32.CloseHandle(handle)
            return False
        globals()["_SCENEIQ_SINGLE_INSTANCE_HANDLE"] = handle
        return True
    except Exception:
        # The app remains usable on systems where the Windows mutex API is restricted.
        return True


class SceneIQApp:
    """Serenum-style dark desktop control center for SceneIQ video production."""

    BG = "#080D18"
    PANEL = "#101827"
    PANEL_ALT = "#0C1422"
    BORDER = "#23334B"
    TEXT = "#E6F0FF"
    MUTED = "#8CA0BA"
    CYAN = "#27D7F2"
    GREEN = "#38D996"
    AMBER = "#FFBE55"
    RED = "#FF5D75"
    BLUE = "#83B8FF"

    def __init__(self, root):
        import os
        import queue
        import sys
        import time

        self.root = root
        self.events = queue.Queue()
        self.process = None
        self.worker_reader = None
        self.running = False
        self.paused = False
        self.startup_failed = False
        self.started_at = None
        self.run_counter = 0

        # Image Producer has its own worker process, command bridge and console.
        # Sharing this window does not share its engine, keyboard hooks or controls.
        self.image_process = None
        self.image_worker_reader = None
        self.image_run_counter = 0
        self.active_image_run_id = None
        self.image_console_history = []
        self.image_command_path = None
        self.image_script_path = None
        self.image_status = "IMAGE PRODUCER READY"
        self._image_stop_requested = False
        self.active_run_id = None
        self._closing = False
        self._closing_requested = False
        self._close_started_at = None
        self._pending_worker_failure = None
        self.stdout_original = sys.stdout
        self.stderr_original = sys.stderr
        self.total_errors = 0
        self.total_warnings = 0
        self.log_history = []
        self.console_view_active = False
        self._console_timer_id = None
        self._console_deadline = None
        # Console can show either the combined desktop log or one selected
        # video's own worker log. Worker logs are tailed from disk while visible.
        self.console_mode = "session"
        self.console_worker_id = None
        self.console_worker_title = None
        self.console_worker_log_path = None
        self._worker_console_refresh_id = None
        self._worker_console_last_signature = None
        self.job_cards = {}
        self.latest_manifest = {}
        self.latest_jobs = []
        self.latest_statuses = {}
        self._service_starting = False
        self._mousewheel_active = False
        self.session = self._create_desktop_session()
        self.manifest_path = self.session["manifest_path"]
        self.shutdown_path = self.session["shutdown_path"]
        self.heartbeat_path = self.session["heartbeat_path"]

        self.root.title("SCiQ — SceneIQ Image & Video Studio")
        self.root.configure(bg=self.BG)
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SceneIQ.ico")
            if os.path.isfile(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        # Start at a more compact desktop size. The window remains resizable;
        # the user can enlarge it manually after launch.
        self.root.geometry("1080x700")
        self.root.minsize(820, 540)
        self._center_window(1080, 700)
        self._build_interface()
        self.root.after(180, lambda: _sceneiq_apply_dark_titlebar(self.root, self.BG, self.TEXT))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-Return>", lambda _event: self.start_service())
        self.root.bind("<Control-l>", lambda _event: self.show_console())

        sys.stdout = _SceneIQTextStream(self, self.stdout_original)
        sys.stderr = _SceneIQTextStream(self, self.stderr_original)

        self.root.after(80, self._process_events)
        self.root.after(120, self._activate_window)
        self.root.after(350, self.start_service)
        self.root.after(500, self._refresh_dashboard)
        self.log("SceneIQ desktop interface initialized.", "INFO")
        self.log(f"Ready script: {READY_SCRIPT}", "INFO")
        self.log(f"Project images: {IMAGES_PATH}", "INFO")
        self.set_status("STARTING VIDEO PRODUCER", self.CYAN)
        self._set_visual_state(
            "ready", "SCENEIQ IS READY",
            "The desktop control center is open. The video service will start separately and load eligible projects without blocking this window.",
            self.CYAN,
            detail="Window and production service use separate processes.",
        )

    def _create_desktop_session(self):
        """Prepare optional status files without making window creation depend on them."""
        import datetime
        import json
        import os
        import tempfile
        import time

        ready_path = globals().get("READY_SCRIPT")
        primary_base = os.path.dirname(os.path.abspath(os.fspath(ready_path))) if ready_path else os.getcwd()
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        candidate_roots = [
            os.path.join(primary_base, "video_producer_runs"),
            os.path.join(local_app_data, "SceneIQ", "video_producer_runs"),
            os.path.join(tempfile.gettempdir(), "SceneIQ", "video_producer_runs"),
        ]
        now = time.time()
        stamp = datetime.datetime.now().strftime("desktop_%Y%m%d_%H%M%S_%f")
        failures = []
        for candidate_root in candidate_roots:
            session_dir = os.path.join(candidate_root, f"{stamp}_gui_{os.getpid()}")
            manifest_path = os.path.join(session_dir, "dashboard_manifest.json")
            shutdown_path = os.path.join(session_dir, "dashboard_shutdown.json")
            heartbeat_path = os.path.join(session_dir, "dashboard_heartbeat.json")
            manifest = {
                "window_title": "SceneIQ — Video Production Control Center",
                "created_at": now,
                "last_updated_at": now,
                "session_dir": session_dir,
                "service_status": "Starting desktop window",
                "message": "SceneIQ desktop control center is ready. The producer service will start after the window is displayed.",
                "shutdown_path": shutdown_path,
                "heartbeat_path": heartbeat_path,
                "jobs": [],
            }
            try:
                os.makedirs(session_dir, exist_ok=True)
                with open(manifest_path, "w", encoding="utf-8") as handle:
                    json.dump(manifest, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                with open(shutdown_path, "w", encoding="utf-8") as handle:
                    json.dump({"shutdown": False, "updated_at": now}, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                return {
                    "session_dir": session_dir,
                    "manifest_path": manifest_path,
                    "shutdown_path": shutdown_path,
                    "heartbeat_path": heartbeat_path,
                    "created_at": now,
                    "session_error": None,
                }
            except Exception as exc:
                failures.append(f"{candidate_root}: {type(exc).__name__}: {exc}")

        # A desktop window is still useful when every status-file location is
        # unavailable. Keep the GUI alive and report that the producer cannot
        # start instead of letting a status-folder error prevent the window.
        return {
            "session_dir": None,
            "manifest_path": None,
            "shutdown_path": None,
            "heartbeat_path": None,
            "created_at": now,
            "session_error": " | ".join(failures) or "No writable status directory was found.",
        }

    def _center_window(self, width, height):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _activate_window(self):
        """Ensure the normal desktop window is visible and not iconified."""
        if self._closing:
            return
        try:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def _build_interface(self):
        import tkinter as tk
        from tkinter import ttk

        self.ttk = ttk
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "SceneIQ.Horizontal.TProgressbar",
            troughcolor="#1B2A3F", background=self.CYAN,
            bordercolor="#1B2A3F", lightcolor=self.CYAN,
            darkcolor=self.CYAN,
        )
        style.configure(
            "SceneIQ.Vertical.TScrollbar",
            background=self.PANEL_ALT, troughcolor=self.BG,
            bordercolor=self.BG, arrowcolor=self.MUTED,
        )
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.root.option_add("*Button.highlightThickness", 0)
        self.root.option_add("*Button.borderWidth", 0)
        self.root.option_add("*Text.highlightThickness", 0)
        self.root.option_add("*Text.borderWidth", 0)
        self.root.option_add("*Scrollbar.borderWidth", 0)

        # One shared application shell. Both producer pages are constructed once
        # and remain alive for the lifetime of this root window. Navigation only
        # raises the already-built page; it never destroys/recreates page widgets.
        app_shell = tk.Frame(
            self.root, bg=self.BG, bd=0, relief="flat", highlightthickness=0,
        )
        app_shell.pack(fill="both", expand=True, padx=22, pady=14)

        global_header = tk.Frame(app_shell, bg=self.BG, bd=0, highlightthickness=0)
        global_header.pack(fill="x", pady=(0, 10))
        brand = tk.Frame(global_header, bg=self.BG, bd=0, highlightthickness=0)
        brand.pack(side="left", fill="x", expand=True)
        tk.Label(
            brand, text="SCENEIQ", bg=self.BG, fg=self.CYAN,
            font=("Segoe UI", 26, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand, text="IMAGE & VIDEO PRODUCTION STUDIO",
            bg=self.BG, fg=self.MUTED, font=("Consolas", 8, "bold"),
        ).pack(anchor="w", pady=(0, 1))
        self.header_status = tk.Label(
            global_header, text="●  INITIALIZING", bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 9, "bold"), padx=14, pady=9,
            bd=0, relief="flat", highlightthickness=0,
        )
        self.header_status.pack(side="right", padx=(10, 0), pady=5)

        # Flat technical navigation below the company header (no ttk Notebook,
        # native white tab bevels, page rebuild, transition or flashing).
        navigation = tk.Frame(app_shell, bg=self.BG, bd=0, highlightthickness=0)
        navigation.pack(fill="x", pady=(2, 12))
        self.video_tab_button = tk.Button(
            navigation, text="VIDEO PRODUCER", command=lambda: self.show_main_page("video"),
            bg="#15334B", fg=self.CYAN, activebackground="#1A405C",
            activeforeground="#E6F0FF", relief="flat", bd=0, highlightthickness=0,
            padx=20, pady=10, font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self.video_tab_button.pack(side="left", padx=(0, 7))
        self.image_tab_button = tk.Button(
            navigation, text="IMAGE PRODUCER", command=lambda: self.show_main_page("image"),
            bg="#0C1726", fg=self.MUTED, activebackground="#1A405C",
            activeforeground="#E6F0FF", relief="flat", bd=0, highlightthickness=0,
            padx=20, pady=10, font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self.image_tab_button.pack(side="left")

        self.page_host = tk.Frame(
            app_shell, bg=self.BG, bd=0, relief="flat", highlightthickness=0,
        )
        self.page_host.pack(fill="both", expand=True)
        self.video_tab = tk.Frame(
            self.page_host, bg=self.BG, bd=0, relief="flat", highlightthickness=0,
        )
        self.image_tab = tk.Frame(
            self.page_host, bg=self.BG, bd=0, relief="flat", highlightthickness=0,
        )
        for page in (self.video_tab, self.image_tab):
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.current_main_page = "video"
        outer = tk.Frame(self.video_tab, bg=self.BG, bd=0, relief="flat", highlightthickness=0)
        outer.pack(fill="both", expand=True, padx=0, pady=0)

        strip = tk.Frame(
            outer, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        strip.pack(fill="x", pady=(0, 14))
        self.status_value = tk.Label(
            strip, text="STARTING VIDEO PRODUCER", bg=self.PANEL,
            fg=self.TEXT, font=("Segoe UI", 11, "bold"), anchor="w",
        )
        self.status_value.pack(side="left", padx=16, pady=12, fill="x", expand=True)
        self.mode_value = tk.Label(
            strip, text="SERVICE INITIALIZING", bg=self.PANEL, fg=self.MUTED,
            font=("Consolas", 9), padx=16,
        )
        self.mode_value.pack(side="right")

        body = tk.Frame(outer, bg=self.BG)
        body.pack(fill="both", expand=True)

        # Compact fixed command deck. No separate vertical scroll area is needed;
        # controls are sized to fit the regular application window.
        side_shell = tk.Frame(
            body, bg=self.PANEL, width=250, bd=0, relief="flat", highlightthickness=0,
        )
        side_shell.pack(side="left", fill="y", padx=(0, 14))
        side_shell.pack_propagate(False)
        side = tk.Frame(side_shell, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0)
        side.pack(fill="both", expand=True)
        tk.Label(side, text="COMMAND DECK", bg=self.PANEL, fg=self.CYAN,
                 font=("Consolas", 10, "bold")).pack(anchor="w", padx=16, pady=(8, 5))

        # Edit the READY_SCRIPT queue directly in this same desktop window.
        # This button intentionally sits immediately above Start Producer.
        self.configuration_button = self._make_button(
            side, "⚙   CONFIGURATION", self.show_configuration_editor, self.BLUE
        )
        self.configuration_button.pack(fill="x", padx=14, pady=2)

        self.start_button = self._make_button(side, "▶   START PRODUCER", self.start_service, self.GREEN)
        self.start_button.pack(fill="x", padx=14, pady=2)
        self.pause_all_button = self._make_button(side, "Ⅱ   PAUSE ALL VIDEOS", self.pause_all, self.AMBER, state="disabled")
        self.pause_all_button.pack(fill="x", padx=14, pady=2)
        self.resume_all_button = self._make_button(side, "▶   RESUME ALL VIDEOS", self.resume_all, self.GREEN, state="disabled")
        self.resume_all_button.pack(fill="x", padx=14, pady=2)
        self.stop_all_button = self._make_button(side, "■   STOP ALL VIDEOS", self.stop_all, "#C5D0DF", state="disabled")
        self.stop_all_button.pack(fill="x", padx=14, pady=2)

        tk.Frame(side, bg=self.BORDER, height=1).pack(fill="x", padx=14, pady=5)
        self.console_button = self._make_button(side, "▤   SHOW CONSOLE", self.show_console, self.CYAN)
        self.console_button.pack(fill="x", padx=14, pady=2)
        self.refresh_button = self._make_button(side, "↻   REFRESH DASHBOARD", self.refresh_now, self.MUTED)
        self.refresh_button.pack(fill="x", padx=14, pady=2)
        self.clear_button = self._make_button(side, "⌫   CLEAR CONSOLE", self.clear_log, self.MUTED)
        self.clear_button.pack(fill="x", padx=14, pady=2)

        tk.Frame(side, bg=self.BORDER, height=1).pack(fill="x", padx=14, pady=5)
        session_row = tk.Frame(side, bg=self.PANEL, bd=0, highlightthickness=0)
        session_row.pack(fill="x", padx=16, pady=(0, 3))
        tk.Label(session_row, text="SESSION", bg=self.PANEL, fg=self.MUTED,
                 font=("Consolas", 8, "bold")).pack(side="left")
        self.runtime_value = tk.Label(
            session_row, text="00:00:00", bg=self.PANEL, fg=self.TEXT,
            font=("Consolas", 14, "bold"),
        )
        self.runtime_value.pack(side="right")
        metrics_row = tk.Frame(side, bg=self.PANEL, bd=0, highlightthickness=0)
        metrics_row.pack(fill="x", padx=16, pady=(0, 2))
        self.error_value = tk.Label(
            metrics_row, text="ERRORS  0", bg=self.PANEL, fg=self.GREEN,
            font=("Consolas", 8, "bold"),
        )
        self.error_value.pack(side="left")
        self.warning_value = tk.Label(
            metrics_row, text="WARNINGS  0", bg=self.PANEL, fg=self.AMBER,
            font=("Consolas", 8, "bold"),
        )
        self.warning_value.pack(side="right")
        self.progress = ttk.Progressbar(side, mode="indeterminate", style="SceneIQ.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=16, pady=(6, 8))

        workspace = tk.Frame(body, bg=self.BG)
        workspace.pack(side="left", fill="both", expand=True)
        self.workspace = workspace

        self.status_view = tk.Frame(workspace, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0)
        self.status_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        hero_top = tk.Frame(self.status_view, bg=self.PANEL_ALT)
        hero_top.pack(fill="x")
        tk.Label(
            hero_top, text="SCENEIQ  /  LIVE PRODUCTION STATUS", bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 9, "bold"),
        ).pack(side="left", padx=18, pady=13)
        self.hero_state_chip = tk.Label(
            hero_top, text="● READY", bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 9, "bold"),
        )
        self.hero_state_chip.pack(side="right", padx=18)

        hero_content = tk.Frame(self.status_view, bg=self.PANEL)
        hero_content.pack(fill="x", padx=22, pady=(16, 10))
        hero_content.grid_columnconfigure(0, weight=6)
        hero_content.grid_columnconfigure(1, weight=4)
        info = tk.Frame(hero_content, bg=self.PANEL)
        info.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        self.hero_title = tk.Label(
            info, text="READY FOR VIDEO PRODUCTION", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 20, "bold"), anchor="w", justify="left", wraplength=470,
        )
        self.hero_title.pack(fill="x", pady=(0, 7))
        self.hero_description = tk.Label(
            info,
            text="SceneIQ will load the ready-script queue and render videos in an isolated background service. This window stays available for controls and monitoring.",
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9), anchor="w",
            justify="left", wraplength=490,
        )
        self.hero_description.pack(fill="x")

        summary = tk.Frame(hero_content, bg=self.PANEL_ALT, bd=0, relief="flat", highlightthickness=0)
        summary.grid(row=0, column=1, sticky="nsew")
        tk.Label(summary, text="PRODUCTION SNAPSHOT", bg=self.PANEL_ALT, fg=self.CYAN,
                 font=("Consolas", 8, "bold")).pack(anchor="w", padx=14, pady=(11, 5))
        self.hero_queue_value = tk.Label(summary, text="0 PROJECTS", bg=self.PANEL_ALT, fg=self.TEXT,
                                         font=("Segoe UI", 15, "bold"))
        self.hero_queue_value.pack(anchor="w", padx=14)
        self.hero_detail = tk.Label(
            summary, text="Waiting for the service to report its queue.", bg=self.PANEL_ALT, fg=self.MUTED,
            font=("Segoe UI", 8), anchor="w", justify="left", wraplength=270,
        )
        self.hero_detail.pack(fill="x", padx=14, pady=(4, 11))

        queue_header = tk.Frame(self.status_view, bg=self.PANEL)
        queue_header.pack(fill="x", padx=22, pady=(3, 7))
        tk.Label(queue_header, text="VIDEO PROJECTS", bg=self.PANEL, fg=self.CYAN,
                 font=("Consolas", 9, "bold")).pack(side="left")
        self.queue_count_label = tk.Label(queue_header, text="0 PROJECTS", bg=self.PANEL, fg=self.MUTED,
                                          font=("Consolas", 8))
        self.queue_count_label.pack(side="right")

        grid_shell = tk.Frame(self.status_view, bg=self.PANEL)
        grid_shell.pack(fill="both", expand=True, padx=15, pady=(0, 14))
        self.canvas = tk.Canvas(grid_shell, bg=self.PANEL, highlightthickness=0, borderwidth=0)
        vertical_scroll = tk.Scrollbar(
            grid_shell, orient="vertical", command=self.canvas.yview,
            bg="#142238", troughcolor="#091321", activebackground=self.CYAN,
            relief="flat", bd=0, highlightthickness=0, width=10,
        )
        self.canvas.configure(yscrollcommand=vertical_scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.canvas, bg=self.PANEL, bd=0, highlightthickness=0)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.grid_columnconfigure(0, weight=1, uniform="video_card_columns")
        self.grid_frame.grid_columnconfigure(1, weight=1, uniform="video_card_columns")

        def _refresh_video_project_scrollregion(_event=None):
            try:
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                self.canvas.update_idletasks()
                bounds = self.canvas.bbox("all")
                needs_scroll = bool(
                    bounds and len(bounds) == 4
                    and int(bounds[3] - bounds[1]) > int(self.canvas.winfo_height()) + 2
                )
                if needs_scroll:
                    if not vertical_scroll.winfo_ismapped():
                        vertical_scroll.pack(side="right", fill="y")
                else:
                    if vertical_scroll.winfo_ismapped():
                        vertical_scroll.pack_forget()
                    self.canvas.yview_moveto(0)
            except Exception:
                pass

        self.grid_frame.bind("<Configure>", _refresh_video_project_scrollregion, add="+")
        def _resize_video_project_canvas(event):
            try:
                self.canvas.itemconfigure(self.canvas_window, width=event.width)
            except Exception:
                pass
            _refresh_video_project_scrollregion()

        self.canvas.bind("<Configure>", _resize_video_project_canvas, add="+")
        # Keep one global wheel binding for the lifetime of the window. Tk's
        # Frame <Leave> event can fire when the pointer moves onto a child widget;
        # binding/unbinding on Enter/Leave therefore made scrolling intermittent.
        # The handlers below scroll only while the pointer is physically over the
        # project canvas, so the console and other panels keep their own behavior.
        self.root.bind_all("<MouseWheel>", self._on_video_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_video_mousewheel_linux, add="+")
        self.root.bind_all("<Button-5>", self._on_video_mousewheel_linux, add="+")
        self.empty_label = tk.Label(
            self.grid_frame,
            text="The desktop window is active. Video projects will appear here when the producer reads ready_script.json.",
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 10), padx=18, pady=22,
            justify="left", wraplength=730,
        )
        self.empty_label.grid(row=0, column=0, columnspan=2, sticky="nw", padx=8, pady=8)

        self.console_view = tk.Frame(workspace, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0)
        self.console_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        console_header = tk.Frame(self.console_view, bg=self.PANEL_ALT)
        console_header.pack(fill="x")
        self.console_title_label = tk.Label(
            console_header, text="LIVE VIDEO PRODUCTION CONSOLE", bg=self.PANEL_ALT,
            fg=self.CYAN, font=("Consolas", 10, "bold"), anchor="w",
        )
        self.console_title_label.pack(side="left", padx=15, pady=13, fill="x", expand=True)
        self.console_countdown_label = tk.Label(
            console_header, text="SESSION OUTPUT", bg=self.PANEL_ALT,
            fg=self.MUTED, font=("Consolas", 8),
        )
        self.console_countdown_label.pack(side="right", padx=15)
        log_wrap = tk.Frame(self.console_view, bg=self.PANEL)
        log_wrap.pack(fill="both", expand=True, padx=12, pady=12)
        self.log_text = tk.Text(
            log_wrap, bg="#070C15", fg="#C7D6EA", insertbackground=self.CYAN,
            selectbackground="#1A4861", relief="flat", bd=0, highlightthickness=0,
            wrap="word", font=("Consolas", 9), padx=13, pady=12, state="disabled",
        )
        scrollbar = tk.Scrollbar(
            log_wrap, command=self.log_text.yview,
            bg="#142238", troughcolor="#091321", activebackground=self.CYAN,
            relief="flat", bd=0, highlightthickness=0, width=10,
        )
        def _sync_video_console_scrollbar(first, last):
            try:
                scrollbar.set(first, last)
                needs_scroll = float(first) > 0.001 or float(last) < 0.999
                if needs_scroll and not scrollbar.winfo_ismapped():
                    scrollbar.pack(side="right", fill="y")
                elif not needs_scroll and scrollbar.winfo_ismapped():
                    scrollbar.pack_forget()
            except Exception:
                pass

        self.log_text.configure(yscrollcommand=_sync_video_console_scrollbar)
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.tag_configure("INFO", foreground="#C7D6EA")
        self.log_text.tag_configure("SUCCESS", foreground=self.GREEN)
        self.log_text.tag_configure("WARNING", foreground=self.AMBER)
        self.log_text.tag_configure("ERROR", foreground=self.RED)
        self.log_text.tag_configure("TIME", foreground="#647994")
        console_footer = tk.Frame(self.console_view, bg=self.PANEL_ALT)
        console_footer.pack(fill="x")
        self.console_copy_button = tk.Button(
            console_footer, text="COPY ALL CONSOLE RESULTS", command=self.copy_all_results,
            bg="#172E49", fg=self.CYAN, activebackground="#214767",
            relief="flat", bd=0, highlightthickness=0, padx=18, pady=10,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )
        self.console_copy_button.pack(side="left", padx=12, pady=9)
        tk.Button(
            console_footer, text="←  BACK TO VIDEO STATUS", command=self.show_status_view,
            bg="#202C3E", fg=self.TEXT, activebackground="#2B3B52",
            relief="flat", bd=0, highlightthickness=0, padx=18, pady=10,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        ).pack(side="right", padx=12, pady=9)

        # Configuration is another page inside the existing workspace, not a
        # Toplevel/modal. The command deck and main SceneIQ window stay visible.
        self.configuration_view = tk.Frame(
            workspace, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        self.configuration_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.configuration_view.grid_rowconfigure(2, weight=1)
        self.configuration_view.grid_columnconfigure(0, weight=1)

        config_header = tk.Frame(self.configuration_view, bg=self.PANEL_ALT)
        config_header.grid(row=0, column=0, sticky="ew")
        tk.Label(
            config_header, text="SCENEIQ  /  READY SCRIPT CONFIGURATION",
            bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 10, "bold"), anchor="w",
        ).pack(side="left", padx=18, pady=13)
        tk.Label(
            self.configuration_view,
            text=(
                "Edit the complete ready_script.json below. Save writes the JSON "
                "to the existing READY_SCRIPT path. Cancel closes this view "
                "without changing the file."
            ),
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9),
            anchor="w", justify="left", wraplength=850,
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(13, 7))

        config_editor_shell = tk.Frame(
            self.configuration_view, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        config_editor_shell.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        config_editor_shell.grid_rowconfigure(0, weight=1)
        config_editor_shell.grid_columnconfigure(0, weight=1)
        self.configuration_text = tk.Text(
            config_editor_shell, bg="#070C15", fg="#D8E6FA",
            insertbackground=self.CYAN, selectbackground="#1A4861",
            relief="flat", wrap="none", undo=True,
            font=("Consolas", 9), padx=13, pady=12, bd=0,
            highlightthickness=0, tabs=(36,),
        )
        config_y_scroll = tk.Scrollbar(
            config_editor_shell, command=self.configuration_text.yview,
            bg="#142238", troughcolor="#091321",
            activebackground=self.CYAN, relief="flat", bd=0,
            highlightthickness=0, width=10,
        )
        config_x_scroll = tk.Scrollbar(
            config_editor_shell, orient="horizontal",
            command=self.configuration_text.xview,
            bg="#142238", troughcolor="#091321",
            activebackground=self.CYAN, relief="flat", bd=0,
            highlightthickness=0, width=10,
        )
        self.configuration_text.configure(
            yscrollcommand=config_y_scroll.set,
            xscrollcommand=config_x_scroll.set,
        )
        self.configuration_text.grid(row=0, column=0, sticky="nsew")
        config_y_scroll.grid(row=0, column=1, sticky="ns")
        config_x_scroll.grid(row=1, column=0, sticky="ew")

        config_footer = tk.Frame(self.configuration_view, bg=self.PANEL_ALT)
        config_footer.grid(row=3, column=0, sticky="ew")
        self.configuration_feedback = tk.Label(
            config_footer, text="", bg=self.PANEL_ALT, fg=self.MUTED,
            font=("Segoe UI", 8), anchor="w", justify="left",
        )
        self.configuration_feedback.pack(side="left", padx=14, pady=11, fill="x", expand=True)
        config_actions = tk.Frame(config_footer, bg=self.PANEL_ALT)
        config_actions.pack(side="right", padx=10, pady=8)
        self.configuration_cancel_button = self._make_button(
            config_actions, "CANCEL", self.cancel_configuration_editor, self.MUTED
        )
        self.configuration_cancel_button.pack(side="left", padx=(0, 7))
        self.configuration_save_button = self._make_button(
            config_actions, "SAVE", self.save_configuration_editor, self.GREEN
        )
        self.configuration_save_button.pack(side="left")

        footer = tk.Frame(outer, bg=self.BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, text="SCENEIQ  •  VIDEO PRODUCTION CONTROL CENTER", bg=self.BG, fg=self.MUTED,
                 font=("Consolas", 8)).pack(side="left")
        tk.Label(footer, text="VISIBLE WINDOW  /  ISOLATED RENDER SERVICE", bg=self.BG, fg=self.MUTED,
                 font=("Consolas", 8)).pack(side="right")
        self.show_status_view()
        self._build_image_interface(self.image_tab)
        self.show_main_page("video")

    def show_main_page(self, page):
        """Instantly raise a pre-built producer page without rebuilding widgets."""
        if self._closing:
            return
        page_key = "image" if str(page).casefold() in {"image", "images", "image producer"} else "video"
        self.current_main_page = page_key
        target = self.image_tab if page_key == "image" else self.video_tab
        try:
            target.tkraise()
            if page_key == "image":
                self.image_tab_button.configure(bg="#15334B", fg=self.CYAN)
                self.video_tab_button.configure(bg="#0C1726", fg=self.MUTED)
            else:
                self.video_tab_button.configure(bg="#15334B", fg=self.CYAN)
                self.image_tab_button.configure(bg="#0C1726", fg=self.MUTED)
        except Exception:
            # A window closing during a click should not break the worker engines.
            return

    def _build_image_interface(self, parent):
        """Build the Google Flow Image Producer command center and its one console."""
        import tkinter as tk
        from tkinter import ttk

        outer = tk.Frame(parent, bg=self.BG, bd=0, relief="flat", highlightthickness=0)
        outer.pack(fill="both", expand=True, padx=0, pady=0)

        strip = tk.Frame(
            outer, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        strip.pack(fill="x", pady=(0, 12))
        self.image_status_value = tk.Label(
            strip, text="IMAGE PRODUCER READY", bg=self.PANEL, fg=self.TEXT,
            font=("Segoe UI", 10, "bold"), anchor="w",
        )
        self.image_status_value.pack(side="left", padx=15, pady=11, fill="x", expand=True)
        self.image_shortcut_value = tk.Label(
            strip, text="CTRL+SHIFT+F12  RESTART   •   ALT+/  STOP",
            bg=self.PANEL, fg=self.MUTED, font=("Consolas", 8), padx=12,
        )
        self.image_shortcut_value.pack(side="right")
        self.image_header_chip = tk.Label(
            strip, text="●  READY", bg=self.PANEL, fg=self.CYAN,
            font=("Consolas", 8, "bold"), padx=11,
        )
        self.image_header_chip.pack(side="right", padx=(8, 12))

        body = tk.Frame(outer, bg=self.BG, bd=0, relief="flat", highlightthickness=0)
        body.pack(fill="both", expand=True)

        command_panel = tk.Frame(
            body, bg=self.PANEL, width=245, bd=0, relief="flat", highlightthickness=0,
        )
        command_panel.pack(side="left", fill="y", padx=(0, 13))
        command_panel.pack_propagate(False)

        tk.Label(
            command_panel, text="COMMAND CENTER", bg=self.PANEL, fg=self.CYAN,
            font=("Consolas", 9, "bold"),
        ).pack(anchor="w", padx=16, pady=(18, 12))

        self.image_configuration_button = self._make_button(
            command_panel, "⚙   CONFIGURATION", self.show_image_configuration_editor, self.BLUE
        )
        self.image_configuration_button.pack(fill="x", padx=13, pady=4)

        self.image_start_button = self._make_button(
            command_panel, "▶   START IMAGE PRODUCTION", self.start_image_producer, self.GREEN
        )
        self.image_start_button.pack(fill="x", padx=13, pady=4)

        self.image_restart_button = self._make_button(
            command_panel, "↻   RESTART WORKFLOW", self.restart_image_producer,
            self.AMBER, state="disabled",
        )
        self.image_restart_button.pack(fill="x", padx=13, pady=4)

        self.image_stop_button = self._make_button(
            command_panel, "■   STOP IMAGE PRODUCTION", self.stop_image_producer,
            self.RED, state="disabled",
        )
        self.image_stop_button.pack(fill="x", padx=13, pady=4)

        tk.Frame(command_panel, bg=self.BORDER, height=1).pack(fill="x", padx=13, pady=13)
        self.image_console_button = self._make_button(
            command_panel, "▤   SHOW CONSOLE", self.show_image_console, self.CYAN
        )
        self.image_console_button.pack(fill="x", padx=13, pady=4)
        self.image_clear_button = self._make_button(
            command_panel, "⌫   CLEAR CONSOLE", self.clear_image_console, self.MUTED
        )
        self.image_clear_button.pack(fill="x", padx=13, pady=4)

        tk.Frame(command_panel, bg=self.BORDER, height=1).pack(fill="x", padx=13, pady=14)
        tk.Label(
            command_panel, text="IMAGE WORKER", bg=self.PANEL, fg=self.MUTED,
            font=("Consolas", 8, "bold"),
        ).pack(anchor="w", padx=16, pady=(0, 7))
        self.image_worker_value = tk.Label(
            command_panel, text="NOT STARTED", bg=self.PANEL, fg=self.TEXT,
            font=("Consolas", 10, "bold"), anchor="w",
        )
        self.image_worker_value.pack(anchor="w", padx=16)
        tk.Label(
            command_panel,
            text=(
                "This panel controls only Google Flow image production. "
                "The Video Producer has a separate process, configuration, "
                "console and control system."
            ),
            bg=self.PANEL, fg=self.MUTED, justify="left",
            font=("Segoe UI", 8), wraplength=205,
        ).pack(anchor="w", padx=16, pady=(14, 0))

        self.image_workspace = tk.Frame(body, bg=self.BG, bd=0, relief="flat", highlightthickness=0)
        self.image_workspace.pack(side="left", fill="both", expand=True)

        # One console only, always inside the Image Producer tab.
        self.image_console_view = tk.Frame(
            self.image_workspace, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        self.image_console_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        console_header = tk.Frame(self.image_console_view, bg=self.PANEL_ALT)
        console_header.pack(fill="x")
        tk.Label(
            console_header, text="IMAGE PRODUCER  /  LIVE CONSOLE",
            bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 9, "bold"), anchor="w",
        ).pack(side="left", padx=15, pady=12)
        self.image_console_state = tk.Label(
            console_header, text="WAITING FOR START", bg=self.PANEL_ALT,
            fg=self.MUTED, font=("Consolas", 8),
        )
        self.image_console_state.pack(side="right", padx=15)

        log_wrap = tk.Frame(self.image_console_view, bg=self.PANEL)
        log_wrap.pack(fill="both", expand=True, padx=11, pady=11)
        self.image_console_text = tk.Text(
            log_wrap, bg="#070C15", fg="#C7D6EA",
            insertbackground=self.CYAN, selectbackground="#1A4861",
            relief="flat", wrap="word", font=("Consolas", 9),
            padx=12, pady=11, state="disabled",
        )
        image_log_scroll = tk.Scrollbar(
            log_wrap, command=self.image_console_text.yview,
            bg="#142238", troughcolor="#091321",
            activebackground=self.CYAN, relief="flat", bd=0,
            highlightthickness=0, width=10,
        )
        def _sync_image_console_scrollbar(first, last):
            try:
                image_log_scroll.set(first, last)
                needs_scroll = float(first) > 0.001 or float(last) < 0.999
                if needs_scroll and not image_log_scroll.winfo_ismapped():
                    image_log_scroll.pack(side="right", fill="y")
                elif not needs_scroll and image_log_scroll.winfo_ismapped():
                    image_log_scroll.pack_forget()
            except Exception:
                pass

        self.image_console_text.configure(yscrollcommand=_sync_image_console_scrollbar)
        self.image_console_text.pack(side="left", fill="both", expand=True)

        image_console_footer = tk.Frame(self.image_console_view, bg=self.PANEL_ALT)
        image_console_footer.pack(fill="x")
        tk.Button(
            image_console_footer, text="COPY IMAGE CONSOLE",
            command=self.copy_image_console,
            bg="#172E49", fg=self.CYAN, activebackground="#214767",
            relief="flat", bd=0, highlightthickness=0, padx=14, pady=9,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        ).pack(side="left", padx=10, pady=8)
        tk.Label(
            image_console_footer,
            text="Only Image Producer output appears here",
            bg=self.PANEL_ALT, fg=self.MUTED, font=("Consolas", 8),
        ).pack(side="right", padx=12)

        # The image configuration editor replaces the console in this workspace;
        # it does not create a modal or a second top-level window.
        self.image_configuration_view = tk.Frame(
            self.image_workspace, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        self.image_configuration_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.image_configuration_view.grid_rowconfigure(2, weight=1)
        self.image_configuration_view.grid_columnconfigure(0, weight=1)

        image_config_header = tk.Frame(self.image_configuration_view, bg=self.PANEL_ALT)
        image_config_header.grid(row=0, column=0, sticky="ew")
        tk.Label(
            image_config_header, text="IMAGE PRODUCER  /  PANEL.JSON CONFIGURATION",
            bg=self.PANEL_ALT, fg=self.CYAN,
            font=("Consolas", 9, "bold"), anchor="w",
        ).pack(side="left", padx=15, pady=12)
        tk.Label(
            self.image_configuration_view,
            text=(
                "Edit the Image Producer panel.json only. Save validates and writes "
                "the JSON to PANEL_PATH. Cancel returns to the Image Producer console "
                "without changing the file."
            ),
            bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 8),
            anchor="w", justify="left", wraplength=820,
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(12, 7))

        image_editor_shell = tk.Frame(
            self.image_configuration_view, bg=self.PANEL, bd=0, relief="flat", highlightthickness=0,
        )
        image_editor_shell.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 9))
        image_editor_shell.grid_rowconfigure(0, weight=1)
        image_editor_shell.grid_columnconfigure(0, weight=1)
        self.image_configuration_text = tk.Text(
            image_editor_shell, bg="#070C15", fg="#D8E6FA",
            insertbackground=self.CYAN, selectbackground="#1A4861",
            relief="flat", bd=0, highlightthickness=0, wrap="none", undo=True,
            font=("Consolas", 9), padx=12, pady=10,
        )
        image_config_y = tk.Scrollbar(
            image_editor_shell, command=self.image_configuration_text.yview,
            bg="#142238", troughcolor="#091321", relief="flat",
            bd=0, highlightthickness=0, width=10,
        )
        image_config_x = tk.Scrollbar(
            image_editor_shell, orient="horizontal",
            command=self.image_configuration_text.xview,
            bg="#142238", troughcolor="#091321", relief="flat",
            bd=0, highlightthickness=0, width=10,
        )
        self.image_configuration_text.configure(
            yscrollcommand=image_config_y.set, xscrollcommand=image_config_x.set
        )
        self.image_configuration_text.grid(row=0, column=0, sticky="nsew")
        image_config_y.grid(row=0, column=1, sticky="ns")
        image_config_x.grid(row=1, column=0, sticky="ew")

        image_config_footer = tk.Frame(self.image_configuration_view, bg=self.PANEL_ALT)
        image_config_footer.grid(row=3, column=0, sticky="ew")
        self.image_configuration_feedback = tk.Label(
            image_config_footer, text="", bg=self.PANEL_ALT, fg=self.MUTED,
            font=("Segoe UI", 8), anchor="w", justify="left",
        )
        self.image_configuration_feedback.pack(side="left", padx=12, pady=9, fill="x", expand=True)
        image_config_actions = tk.Frame(image_config_footer, bg=self.PANEL_ALT)
        image_config_actions.pack(side="right", padx=9, pady=7)
        self.image_configuration_cancel_button = self._make_button(
            image_config_actions, "CANCEL", self.cancel_image_configuration_editor, self.MUTED
        )
        self.image_configuration_cancel_button.pack(side="left", padx=(0, 6))
        self.image_configuration_save_button = self._make_button(
            image_config_actions, "SAVE", self.save_image_configuration_editor, self.GREEN
        )
        self.image_configuration_save_button.pack(side="left")

        self._append_image_log(
            "SceneIQ Image Producer is ready. Press START IMAGE PRODUCTION to launch the isolated Google Flow worker.\n"
            "Image-only shortcuts: Ctrl+Shift+F12 = restart workflow | Alt+/ = stop image production.\n"
        )
        self.show_image_console()

    def show_image_console(self):
        if hasattr(self, "image_console_view"):
            self.image_console_view.tkraise()

    def show_image_configuration_editor(self):
        import json
        try:
            with open(PANEL_PATH, "r", encoding="utf-8") as handle:
                current_data = json.load(handle)
            formatted = json.dumps(current_data, ensure_ascii=False, indent=2)
            feedback = "Loaded the current Image Producer panel.json."
            color = self.GREEN
        except FileNotFoundError:
            formatted = "{}"
            feedback = "panel.json does not exist yet. A new JSON object is shown."
            color = self.AMBER
        except Exception as exc:
            self._append_image_log(
                f"Could not load Image Producer configuration: {type(exc).__name__}: {exc}\n"
            )
            return

        self.image_configuration_text.delete("1.0", "end")
        self.image_configuration_text.insert("1.0", formatted)
        self.image_configuration_feedback.configure(text=feedback, fg=color)
        self.image_configuration_view.tkraise()

    def save_image_configuration_editor(self):
        import json
        raw = self.image_configuration_text.get("1.0", "end-1c")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.image_configuration_feedback.configure(
                text=f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
                fg=self.RED,
            )
            return

        try:
            if not _video_producer_write_json_atomic(PANEL_PATH, parsed):
                raise IOError("Atomic write returned False.")
            self.image_configuration_feedback.configure(
                text="Saved successfully to the Image Producer panel.json.",
                fg=self.GREEN,
            )
            self._append_image_log("✅ Image Producer panel.json configuration saved.\n")
            self.show_image_console()
        except Exception as exc:
            self.image_configuration_feedback.configure(
                text=f"Could not save panel.json: {type(exc).__name__}: {exc}",
                fg=self.RED,
            )

    def cancel_image_configuration_editor(self):
        self.show_image_console()

    def _append_image_log(self, value):
        if not value or self._closing:
            return
        self.image_console_history.append(str(value))
        if len(self.image_console_history) > 15000:
            self.image_console_history = self.image_console_history[-12000:]
        try:
            if not self.image_console_text.winfo_exists():
                return
            self.image_console_text.configure(state="normal")
            self.image_console_text.insert("end", str(value))
            line_count = int(self.image_console_text.index("end-1c").split(".")[0])
            if line_count > 12000:
                self.image_console_text.delete("1.0", "3001.0")
            self.image_console_text.see("end")
            self.image_console_text.configure(state="disabled")
            lowered = str(value).casefold()
            if any(token in lowered for token in ("❌", "traceback", "exception")):
                self.image_console_state.configure(text="ISSUE REPORTED", fg=self.RED)
            elif any(token in lowered for token in ("✅", "completed", "successfully")):
                self.image_console_state.configure(text="ACTIVITY COMPLETE", fg=self.GREEN)
        except Exception:
            # Console rendering is a monitoring convenience and must never
            # interrupt the image worker or the shared desktop.
            return

    def clear_image_console(self):
        try:
            if self.image_console_text.winfo_exists():
                self.image_console_text.configure(state="normal")
                self.image_console_text.delete("1.0", "end")
                self.image_console_text.configure(state="disabled")
            self.image_console_history.clear()
        except Exception:
            pass

    def copy_image_console(self):
        try:
            content = "".join(self.image_console_history) or "Image Producer console is empty."
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update_idletasks()
            self._append_image_log("✅ Image Producer console copied to clipboard.\n")
        except Exception as exc:
            self._append_image_log(f"⚠️ Could not copy Image Producer console: {exc}\n")

    def _write_image_gui_command(self, command):
        import time
        import os
        if not self.image_command_path:
            raise RuntimeError("Image Producer command bridge is not initialized.")
        payload = {
            "command": str(command or "").strip().casefold(),
            "request_id": str(time.time_ns()),
            "updated_at": time.time(),
        }
        if not _video_producer_write_json_atomic(self.image_command_path, payload):
            raise IOError("Could not write the Image Producer desktop command.")
        return payload

    def start_image_producer(self):
        import os
        import subprocess

        if self._closing or self._closing_requested:
            return
        if self.image_process is not None and self.image_process.poll() is None:
            self.show_main_page("image")
            self._append_image_log("ℹ️ Image Producer is already running.\n")
            self.show_image_console()
            return

        script_directory = os.path.dirname(os.path.abspath(__file__))
        image_candidates = [
            os.path.join(script_directory, "sceniqimageproduction.py"),
            os.path.join(script_directory, "sceneiqimageproduction.py"),
        ]
        image_script = next((path for path in image_candidates if os.path.isfile(path)), None)
        if image_script is None:
            try:
                image_script = next(
                    os.path.join(script_directory, name)
                    for name in os.listdir(script_directory)
                    if name.casefold() in {"sceniqimageproduction.py", "sceneiqimageproduction.py"}
                    and os.path.isfile(os.path.join(script_directory, name))
                )
            except (StopIteration, OSError):
                image_script = None

        if not image_script:
            self._append_image_log(
                "❌ Image Producer script not found beside sceneiqvideoproduction.py. "
                "Expected sceniqimageproduction.py.\n"
            )
            self.image_status_value.configure(text="IMAGE SCRIPT NOT FOUND", fg=self.RED)
            self.image_header_chip.configure(text="●  ERROR", fg=self.RED)
            self.show_image_console()
            return

        import tempfile
        session_root = self.session.get("session_dir") or os.path.join(
            tempfile.gettempdir(), "SceneIQ", "image_producer_session"
        )
        os.makedirs(session_root, exist_ok=True)
        self.image_command_path = os.path.join(session_root, "image_producer_gui_command.json")
        self.image_script_path = os.path.abspath(image_script)
        self.image_run_counter += 1
        run_id = self.image_run_counter
        self.active_image_run_id = run_id
        self._image_stop_requested = False

        try:
            # Clear old one-shot local commands when creating a fresh worker.
            _video_producer_write_json_atomic(
                self.image_command_path,
                {"command": "run", "request_id": str(__import__("time").time_ns())},
            )
            worker_environment = os.environ.copy()
            worker_environment["PYTHONIOENCODING"] = "utf-8"
            worker_environment["PYTHONUNBUFFERED"] = "1"
            worker_environment["SCENEIQ_IMAGE_GUI_COMMAND_PATH"] = self.image_command_path
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            command = [
                self._worker_python_executable(),
                "-u",
                self.image_script_path,
                "--sceneiq-image-worker",
                self.image_command_path,
            ]
            self.image_process = subprocess.Popen(
                command,
                cwd=os.path.dirname(self.image_script_path),
                env=worker_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation_flags,
            )
        except Exception as exc:
            self.image_process = None
            self.active_image_run_id = None
            self.image_status_value.configure(text="IMAGE PRODUCER START FAILED", fg=self.RED)
            self.image_header_chip.configure(text="●  ERROR", fg=self.RED)
            self.image_worker_value.configure(text="START FAILED", fg=self.RED)
            self._append_image_log(
                f"❌ Could not start Image Producer: {type(exc).__name__}: {exc}\n"
            )
            self.show_image_console()
            return

        self.image_status = "IMAGE PRODUCTION RUNNING"
        self.image_status_value.configure(text=self.image_status, fg=self.GREEN)
        self.image_header_chip.configure(text="●  RUNNING", fg=self.GREEN)
        self.image_worker_value.configure(text=f"RUNNING  •  PID {self.image_process.pid}", fg=self.GREEN)
        self.image_console_state.configure(text="IMAGE WORKER RUNNING", fg=self.GREEN)
        self.image_start_button.configure(state="disabled")
        self.image_restart_button.configure(state="normal")
        self.image_stop_button.configure(state="normal")
        self._append_image_log(
            f"\n🚀 Image Producer worker started (PID {self.image_process.pid}).\n"
            f"Configuration source: {PANEL_PATH}\n"
            "The Image Producer console is now active. Video production is unaffected.\n"
        )
        self.show_main_page("image")
        self.show_image_console()

        self.image_worker_reader = __import__("threading").Thread(
            target=self._read_image_worker_output,
            args=(self.image_process, run_id),
            name=f"SceneIQImageWorkerOutput-{run_id}",
            daemon=True,
        )
        self.image_worker_reader.start()

    def restart_image_producer(self):
        if self.image_process is None or self.image_process.poll() is not None:
            self._append_image_log("⚠️ Start Image Production before requesting a workflow restart.\n")
            return
        try:
            self._write_image_gui_command("restart")
            self.image_status_value.configure(text="IMAGE WORKFLOW RESTART REQUESTED", fg=self.AMBER)
            self.image_header_chip.configure(text="●  RESTARTING", fg=self.AMBER)
            self._append_image_log(
                "🔁 Restart requested. The image worker will restart the Google Flow workflow at a safe checkpoint.\n"
            )
            self.show_main_page("image")
            self.show_image_console()
        except Exception as exc:
            self._append_image_log(f"❌ Could not request image workflow restart: {exc}\n")

    def stop_image_producer(self, from_close=False):
        if self.image_process is None or self.image_process.poll() is not None:
            if not from_close:
                self._append_image_log("ℹ️ Image Producer is not running.\n")
            return
        try:
            self._image_stop_requested = True
            self._write_image_gui_command("stop")
            self.image_status_value.configure(text="STOPPING IMAGE PRODUCTION", fg=self.AMBER)
            self.image_header_chip.configure(text="●  STOPPING", fg=self.AMBER)
            self.image_worker_value.configure(text="STOP REQUESTED", fg=self.AMBER)
            self.image_start_button.configure(state="disabled")
            self.image_restart_button.configure(state="disabled")
            self.image_stop_button.configure(state="disabled")
            if not from_close:
                self._append_image_log(
                    "🛑 Stop requested. The image worker will exit at its next safe workflow checkpoint.\n"
                )
                self.show_main_page("image")
                self.show_image_console()
        except Exception as exc:
            self._append_image_log(f"❌ Could not send Image Producer stop command: {exc}\n")

    def _read_image_worker_output(self, process, run_id):
        try:
            stream = process.stdout
            if stream is not None:
                for line in iter(stream.readline, ""):
                    if "SCENEIQ_IMAGE_ALT_SLASH_FOCUS_REQUEST" in line:
                        self.events.put(("image_hotkey_focus", run_id))
                        cleaned = line.replace("SCENEIQ_IMAGE_ALT_SLASH_FOCUS_REQUEST", "").strip()
                        if not cleaned:
                            continue
                        line = cleaned + "\n"
                    self.events.put(("image_log", run_id, line))
                try:
                    stream.close()
                except Exception:
                    pass
            return_code = process.wait()
        except Exception as exc:
            return_code = process.poll()
            if return_code is None:
                return_code = -1
            self.events.put(("image_log", run_id, f"[IMAGE WORKER READER ERROR] {exc}\n"))
        self.events.put(("image_exit", run_id, return_code))

    def _finish_image_worker(self, run_id, return_code):
        if run_id != self.active_image_run_id:
            return
        self.image_process = None
        self.active_image_run_id = None
        self.image_start_button.configure(state="normal")
        self.image_restart_button.configure(state="disabled")
        self.image_stop_button.configure(state="disabled")
        self.image_worker_value.configure(text="NOT RUNNING", fg=self.MUTED)
        if self._closing_requested:
            self.image_status_value.configure(text="IMAGE PRODUCER STOPPED", fg=self.AMBER)
            self.root.after(0, self._poll_close)
            return
        if return_code == 0:
            self.image_status_value.configure(text="IMAGE PRODUCER STOPPED", fg=self.AMBER)
            self.image_header_chip.configure(text="●  STOPPED", fg=self.AMBER)
            self.image_console_state.configure(text="WORKER STOPPED", fg=self.AMBER)
            self._append_image_log("\nℹ️ Image Producer worker exited normally.\n")
        else:
            self.image_status_value.configure(text="IMAGE PRODUCER NEEDS ATTENTION", fg=self.RED)
            self.image_header_chip.configure(text="●  ERROR", fg=self.RED)
            self.image_console_state.configure(text="WORKER EXITED WITH ERROR", fg=self.RED)
            self._append_image_log(
                f"\n❌ Image Producer worker exited with code {return_code}. Review the console output above.\n"
            )

    @staticmethod
    def _pointer_is_over_canvas(event, canvas):
        if canvas is None:
            return False
        try:
            x = int(event.x_root) - int(canvas.winfo_rootx())
            y = int(event.y_root) - int(canvas.winfo_rooty())
            return (
                0 <= x < int(canvas.winfo_width())
                and 0 <= y < int(canvas.winfo_height())
            )
        except Exception:
            return False

    def _scroll_target_under_pointer(self, event):
        # Only the project list needs wheel scrolling. The compact command deck
        # is fixed in place and has no redundant vertical scroll rail.
        if self._pointer_is_over_canvas(event, getattr(self, "canvas", None)):
            return self.canvas
        return None

    def _pointer_is_over_video_canvas(self, event):
        # Backward-compatible helper used by any existing internal callbacks.
        return self._pointer_is_over_canvas(event, getattr(self, "canvas", None))

    def _on_video_mousewheel(self, event):
        target = self._scroll_target_under_pointer(event)
        if target is None:
            return None
        try:
            delta = int(getattr(event, "delta", 0) or 0)
            if not delta:
                return "break"
            # Handle standard 120-unit Windows wheels and high-resolution
            # touchpad deltas without allowing a zero-distance scroll.
            units = int(-delta / 120)
            if units == 0:
                units = -1 if delta > 0 else 1
            target.yview_scroll(units, "units")
        except Exception:
            pass
        return "break"

    def _on_video_mousewheel_linux(self, event):
        target = self._scroll_target_under_pointer(event)
        if target is None:
            return None
        try:
            if getattr(event, "num", None) == 4:
                target.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                target.yview_scroll(1, "units")
        except Exception:
            pass
        return "break"

    def _make_button(self, parent, label, command, color, state="normal"):
        import tkinter as tk
        return tk.Button(
            parent, text=label, command=command, state=state,
            bg="#17243A", fg=color, activebackground="#243852",
            activeforeground=self.TEXT, disabledforeground="#53647A",
            relief="flat", bd=0, highlightthickness=0, padx=10, pady=7,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )

    def enqueue_log(self, value):
        self.events.put(("log", value))

    def log(self, message, level="INFO"):
        self.events.put(("log", f"[{level}] {message}\n"))

    @staticmethod
    def _safe_gui_text(value):
        import re
        text = str(value or "")
        text = re.sub(r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:\\|\\\\)[^\r\n<>|]+", "[details in console]", text)
        text = re.sub(r"(?<![A-Za-z0-9])/(?:[^\s<>|]+/)*[^\s<>|]+", "[details in console]", text)
        return text[:420]

    def set_status(self, message, color=None):
        color = color or self.CYAN
        safe_message = self._safe_gui_text(message)
        self.status_value.configure(text=safe_message, fg=color)
        self.header_status.configure(text=f"●  {safe_message.upper()[:24]}", fg=color)

    def _set_visual_state(self, key, title, description, color=None, detail=None):
        color = color or self.CYAN
        state_names = {
            "ready": "● READY", "running": "● RUNNING", "paused": "Ⅱ PAUSED",
            "stopped": "■ STOPPED", "finished": "✓ COMPLETE", "aborted": "● NEEDS ATTENTION",
        }
        if hasattr(self, "hero_state_chip"):
            self.hero_state_chip.configure(text=state_names.get(key, "● STATUS"), fg=color)
            self.hero_title.configure(
                text=self._safe_gui_text(title),
                fg=color if key in ("paused", "stopped", "aborted") else self.TEXT,
            )
            self.hero_description.configure(text=self._safe_gui_text(description))
            self.hero_detail.configure(text=self._safe_gui_text(detail or description))

    def show_status_view(self):
        """Return to the normal dashboard with cards, stages and progress bars."""
        self._cancel_console_timer()
        self._cancel_worker_console_refresh()
        self.console_view_active = False
        self.console_mode = "session"
        self.console_worker_id = None
        self.console_worker_title = None
        self.console_worker_log_path = None
        self._worker_console_last_signature = None
        if hasattr(self, "status_view"):
            self.status_view.tkraise()

    def show_configuration_editor(self):
        """Display READY_SCRIPT JSON inside the existing SceneIQ workspace."""
        import os

        if self._closing or not hasattr(self, "configuration_view"):
            return

        configured_path = globals().get("READY_SCRIPT")
        if not configured_path:
            configured_path = READY_SCRIPT
        self.configuration_file_path = os.path.abspath(os.fspath(configured_path))

        try:
            with open(self.configuration_file_path, "r", encoding="utf-8") as handle:
                current_json = handle.read()
            feedback = "Loaded the current ready_script.json. Changes are not written until you click SAVE."
            feedback_color = self.CYAN
        except FileNotFoundError:
            current_json = ""
            feedback = (
                "ready_script.json was not found. Paste a complete JSON object or array here; "
                "SAVE will create the file. CANCEL leaves it absent."
            )
            feedback_color = self.AMBER
        except Exception as exc:
            current_json = ""
            feedback = f"Could not read ready_script.json: {type(exc).__name__}: {exc}"
            feedback_color = self.RED

        self.configuration_text.delete("1.0", "end")
        if current_json:
            self.configuration_text.insert("1.0", current_json)
        self.configuration_feedback.configure(text=feedback, fg=feedback_color)
        self.configuration_view.tkraise()
        self.configuration_text.focus_set()
        self.log(f"Opened ready-script configuration editor: {self.configuration_file_path}", "INFO")

    def save_configuration_editor(self):
        """Validate and atomically save the edited READY_SCRIPT JSON."""
        import json
        import os

        raw_json = self.configuration_text.get("1.0", "end-1c")
        try:
            parsed_json = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            message = (
                f"Invalid JSON — line {exc.lineno}, column {exc.colno}: {exc.msg}. "
                "Correct it before saving."
            )
            self.configuration_feedback.configure(text=message, fg=self.RED)
            try:
                self.configuration_text.see(f"{exc.lineno}.0")
                self.configuration_text.mark_set("insert", f"{exc.lineno}.0")
                self.configuration_text.focus_set()
            except Exception:
                pass
            return
        except Exception as exc:
            self.configuration_feedback.configure(
                text=f"Could not validate JSON: {type(exc).__name__}: {exc}",
                fg=self.RED,
            )
            return

        if not isinstance(parsed_json, (dict, list)):
            self.configuration_feedback.configure(
                text="The ready script must have a JSON object or JSON array at its root.",
                fg=self.RED,
            )
            return

        path = getattr(self, "configuration_file_path", None)
        if not path:
            configured_path = globals().get("READY_SCRIPT") or READY_SCRIPT
            path = os.path.abspath(os.fspath(configured_path))
        try:
            saved = _video_producer_write_json_atomic(path, parsed_json)
            if not saved:
                raise OSError("The atomic JSON writer did not confirm the save.")
        except Exception as exc:
            message = f"Could not save ready_script.json: {type(exc).__name__}: {exc}"
            self.configuration_feedback.configure(text=message, fg=self.RED)
            self.log(message, "ERROR")
            return

        self.log(f"Saved ready-script configuration to: {path}", "SUCCESS")
        self.configuration_feedback.configure(
            text="Saved successfully. The ready-script file has been updated.",
            fg=self.GREEN,
        )
        self.set_status("READY SCRIPT CONFIGURATION SAVED", self.GREEN)
        self.show_status_view()

    def cancel_configuration_editor(self):
        """Discard editor contents and return without touching READY_SCRIPT."""
        self.log(
            "Configuration editing cancelled. ready_script.json was left unchanged.",
            "INFO",
        )
        self.show_status_view()

    def show_console(self):
        """Show the combined desktop/service console from the command deck."""
        if not hasattr(self, "console_view"):
            return
        self._cancel_console_timer()
        self._cancel_worker_console_refresh()
        self.console_mode = "session"
        self.console_worker_id = None
        self.console_worker_title = None
        self.console_worker_log_path = None
        self._worker_console_last_signature = None
        self.console_view_active = True
        self.console_title_label.configure(text="LIVE SESSION CONSOLE")
        self.console_countdown_label.configure(text="SESSION OUTPUT • USE BACK TO RETURN")
        self.console_copy_button.configure(text="COPY ALL CONSOLE RESULTS")
        self._replace_console_text("".join(self.log_history) or "SceneIQ console is empty.", follow_end=True)
        self.console_view.tkraise()

    def show_video_console(self, worker_id):
        """Switch to the selected video's live worker log without changing its card."""
        import os

        worker_id = str(worker_id)
        job = next(
            (item for item in self.latest_jobs if str(item.get("worker_id")) == worker_id),
            None,
        )
        status = self.latest_statuses.get(worker_id, {})
        if job is None:
            self.log(f"Could not locate the project card for worker {worker_id}.", "WARNING")
            return

        log_path = job.get("log_path") or status.get("log_path")
        title = str(job.get("project_title") or status.get("project_title") or worker_id)
        self._cancel_console_timer()
        self._cancel_worker_console_refresh()
        self.console_mode = "worker"
        self.console_worker_id = worker_id
        self.console_worker_title = title
        self.console_worker_log_path = os.path.abspath(os.fspath(log_path)) if log_path else None
        self._worker_console_last_signature = None
        self.console_view_active = True
        self.console_title_label.configure(
            text=f"VIDEO CONSOLE  /  {self._safe_gui_text(title)}"
        )
        self.console_countdown_label.configure(text=f"{worker_id} • LIVE WORKER OUTPUT")
        self.console_copy_button.configure(text="COPY THIS VIDEO'S CONSOLE")
        self.console_view.tkraise()
        self._refresh_selected_worker_console()

    def _replace_console_text(self, content, follow_end=None):
        """Replace console contents while preserving a user's scroll position."""
        if not hasattr(self, "log_text"):
            return
        try:
            current_view = self.log_text.yview()
            was_at_bottom = bool(current_view and current_view[1] >= 0.985)
        except Exception:
            was_at_bottom = True
        if follow_end is not None:
            was_at_bottom = bool(follow_end)
        try:
            old_position = current_view[0] if current_view else 0.0
        except Exception:
            old_position = 0.0

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", str(content or ""))
        self.log_text.configure(state="disabled")
        if was_at_bottom:
            self.log_text.see("end")
        else:
            self.log_text.yview_moveto(old_position)

    def _cancel_worker_console_refresh(self):
        callback_id = getattr(self, "_worker_console_refresh_id", None)
        if callback_id is not None:
            try:
                self.root.after_cancel(callback_id)
            except Exception:
                pass
        self._worker_console_refresh_id = None

    def _refresh_selected_worker_console(self):
        """Tail the currently selected worker's log while its console is visible."""
        import os

        if self._closing or not self.console_view_active or self.console_mode != "worker":
            self._worker_console_refresh_id = None
            return

        path = self.console_worker_log_path
        content = None
        signature = None
        if path:
            try:
                stat = os.stat(path)
                signature = (
                    int(stat.st_size),
                    int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
                )
                if signature != self._worker_console_last_signature:
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    # Keep the live text widget responsive for exceptionally long
                    # renders while preserving the complete original file for Copy.
                    if len(content) > 300_000:
                        content = "[Earlier output omitted from live view; use Copy to copy the complete log.]\n\n" + content[-300_000:]
                    self._worker_console_last_signature = signature
            except FileNotFoundError:
                content = (
                    f"Worker: {self.console_worker_id}\n"
                    f"Video: {self.console_worker_title}\n\n"
                    "The worker log has not been created yet. This view will keep checking."
                )
            except Exception as exc:
                content = (
                    f"Worker: {self.console_worker_id}\n"
                    f"Video: {self.console_worker_title}\n\n"
                    f"Could not read this worker's log: {type(exc).__name__}: {exc}"
                )
        else:
            content = (
                f"Worker: {self.console_worker_id}\n"
                f"Video: {self.console_worker_title}\n\n"
                "No worker log path has been published for this video yet."
            )

        if content is not None:
            self._replace_console_text(content)

        if self.console_view_active and self.console_mode == "worker" and not self._closing:
            self._worker_console_refresh_id = self.root.after(
                700, self._refresh_selected_worker_console
            )

    def _update_console_countdown(self):
        # Kept as a no-op compatibility method for older call paths. Console
        # views now remain open until the user explicitly returns to video status.
        return None

    def _cancel_console_timer(self):
        if self._console_timer_id is not None:
            try:
                self.root.after_cancel(self._console_timer_id)
            except Exception:
                pass
        self._console_timer_id = None
        self._console_deadline = None

    def copy_all_results(self):
        """Copy the selected video's complete log, or the combined session log."""
        try:
            if self.console_mode == "worker":
                path = self.console_worker_log_path
                if path and __import__("os").path.isfile(path):
                    with open(path, "r", encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                    label = f"worker {self.console_worker_id}"
                else:
                    content = (
                        f"Worker: {self.console_worker_id}\n"
                        f"Video: {self.console_worker_title}\n\n"
                        "The worker log is not available yet."
                    )
                    label = f"worker {self.console_worker_id}"
            else:
                content = "".join(self.log_history) or "SceneIQ console is empty."
                label = "all SceneIQ console results"
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update_idletasks()
            self.log(f"Copied {label} to the clipboard.", "SUCCESS")
        except Exception as exc:
            self.log(f"Could not copy console results: {type(exc).__name__}: {exc}", "WARNING")

    @staticmethod
    def _tk_widget_exists(widget):
        try:
            return widget is not None and bool(widget.winfo_exists())
        except Exception:
            return False

    def _append_log(self, value):
        """Store video logs and render them only while the Text widget is alive."""
        if not value or self._closing:
            return
        value = str(value)
        lowered = value.casefold()
        tag = "INFO"
        if any(term in lowered for term in ("❌", "fatal error", "traceback", "exception:")):
            tag = "ERROR"
            self.total_errors += 1
        elif any(term in lowered for term in ("⚠️", "warning", "could not", "failed")):
            tag = "WARNING"
            self.total_warnings += 1
        elif any(term in lowered for term in ("✅", "successfully", "completed successfully")):
            tag = "SUCCESS"
        self.log_history.append(value)
        if len(self.log_history) > 15000:
            self.log_history = self.log_history[-12000:]

        try:
            if self._tk_widget_exists(getattr(self, "log_text", None)):
                self.log_text.configure(state="normal")
                self.log_text.insert("end", value, tag)
                line_count = int(self.log_text.index("end-1c").split(".")[0])
                if line_count > 12000:
                    self.log_text.delete("1.0", "4001.0")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            if self._tk_widget_exists(getattr(self, "error_value", None)):
                self.error_value.configure(
                    text=f"ERRORS     {self.total_errors}",
                    fg=self.RED if self.total_errors else self.GREEN,
                )
            if self._tk_widget_exists(getattr(self, "warning_value", None)):
                self.warning_value.configure(text=f"WARNINGS   {self.total_warnings}")
        except Exception:
            # A Tk widget may disappear between winfo_exists() and configure().
            # Never let a closing window crash the worker/event-processing loop.
            return

    def _process_events(self):
        import queue
        import tkinter as tk

        if self._closing:
            return
        try:
            if not self.root.winfo_exists():
                self._closing = True
                return

            while True:
                item = self.events.get_nowait()
                event_type = item[0]
                if event_type == "log":
                    self._append_log(item[1])
                elif event_type == "worker_exit":
                    _kind, run_id, return_code, payload = item
                    if run_id == self.active_run_id:
                        self._finish_worker(return_code, payload or self._pending_worker_failure)
                elif event_type == "worker_fatal":
                    _kind, run_id, payload = item
                    if run_id == self.active_run_id:
                        self._pending_worker_failure = payload
                elif event_type == "image_log":
                    _kind, run_id, line = item
                    if run_id == self.active_image_run_id:
                        self._append_image_log(line)
                elif event_type == "image_hotkey_focus":
                    _kind, run_id = item
                    if run_id == self.active_image_run_id:
                        self._focus_sceneiq_window()
                elif event_type == "image_exit":
                    _kind, run_id, return_code = item
                    self._finish_image_worker(run_id, return_code)
        except queue.Empty:
            pass
        except tk.TclError:
            # The root or one of its child widgets is already being destroyed.
            self._closing = True
            return
        except Exception as exc:
            try:
                self.log(f"Event processing warning: {type(exc).__name__}: {exc}", "WARNING")
            except Exception:
                pass

        if not self._closing:
            try:
                self.root.after(80, self._process_events)
            except tk.TclError:
                self._closing = True

    def clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.log_history.clear()
        self.total_errors = 0
        self.total_warnings = 0
        self.error_value.configure(text="ERRORS     0", fg=self.GREEN)
        self.warning_value.configure(text="WARNINGS   0")

    def _worker_python_executable(self):
        import os
        import sys
        executable = os.path.abspath(sys.executable)
        if os.path.basename(executable).casefold() == "pythonw.exe":
            candidate = os.path.join(os.path.dirname(executable), "python.exe")
            if os.path.isfile(candidate):
                return candidate
        return executable

    def start_service(self):
        import os
        import subprocess
        import sys
        import time
        if self._closing or self._closing_requested:
            return
        if self._service_starting or (self.process is not None and self.process.poll() is None):
            self.log("The video producer service is already running or starting; duplicate launch ignored.", "INFO")
            return
        if not self.manifest_path or not self.shutdown_path or not self.heartbeat_path:
            self.running = False
            self.startup_failed = True
            self.start_button.configure(state="normal")
            self.set_status("STATUS STORAGE UNAVAILABLE", self.RED)
            self._set_visual_state(
                "aborted", "VIDEO SERVICE CANNOT START",
                "The desktop window is open, but SceneIQ could not create its small status/control session files in the project, user-data, or temporary folders. The GUI remains available.",
                self.RED, detail=self.session.get("session_error") or "No writable session folder.",
            )
            self.log(f"Could not prepare the producer session: {self.session.get('session_error')}", "ERROR")
            return
        script_path = os.path.abspath(__file__)
        python_exe = self._worker_python_executable()
        command = [
            python_exe, "-u", script_path, "--sceneiq-worker",
            self.manifest_path, self.shutdown_path, self.heartbeat_path,
        ]
        self._service_starting = True
        self.run_counter += 1
        run_id = self.run_counter
        self.active_run_id = run_id
        self._pending_worker_failure = None
        self.started_at = time.monotonic()
        self.running = True
        self.paused = False
        self.startup_failed = False
        try:
            _video_producer_write_json_atomic(
                self.shutdown_path, {"shutdown": False, "updated_at": time.time()}
            )
            worker_environment = os.environ.copy()
            worker_environment["PYTHONIOENCODING"] = "utf-8"
            worker_environment["PYTHONUNBUFFERED"] = "1"
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            self.process = subprocess.Popen(
                command,
                cwd=os.path.dirname(script_path),
                env=worker_environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation_flags,
            )
        except Exception as exc:
            self._service_starting = False
            self.process = None
            self.running = False
            self.startup_failed = True
            self.active_run_id = None
            self.progress.stop()
            self.start_button.configure(state="normal")
            self.log(f"Could not start the video producer service: {type(exc).__name__}: {exc}", "ERROR")
            self.set_status("PRODUCER START FAILED", self.RED)
            self._set_visual_state(
                "aborted", "VIDEO SERVICE COULD NOT START",
                "The desktop window is still available. Open the console for the process launch error, correct it, then press Start Producer again.",
                self.RED, detail="The GUI and video service are separate; the window remains active.",
            )
            return

        self._service_starting = False
        self.start_button.configure(state="disabled")
        self.pause_all_button.configure(state="normal")
        self.resume_all_button.configure(state="normal")
        self.stop_all_button.configure(state="normal")
        self.progress.start(12)
        self.set_status("VIDEO PRODUCER RUNNING", self.GREEN)
        self._set_visual_state(
            "running", "SCENEIQ IS PRODUCING VIDEOS",
            "The production service is running in the background. This window remains available to monitor every video and control projects individually.",
            self.GREEN,
            detail=f"Isolated service process • PID {self.process.pid} • Per-video controls remain active.",
        )
        self.log(f"Video producer service started (PID {self.process.pid}). The desktop window is independent.", "SUCCESS")
        self.worker_reader = __import__("threading").Thread(
            target=self._read_worker_output,
            args=(self.process, run_id),
            name=f"SceneIQServiceOutput-{run_id}",
            daemon=True,
        )
        self.worker_reader.start()
        self.root.after(350, self._update_runtime)

    def _read_worker_output(self, process, run_id):
        import re
        fatal_payload = None
        output_tail = []
        try:
            stream = process.stdout
            if stream is not None:
                for line in iter(stream.readline, ""):
                    output_tail.append(line)
                    if len(output_tail) > 150:
                        output_tail.pop(0)
                    marker = "SCENEIQ_FATAL_JSON="
                    if marker in line:
                        raw = line.split(marker, 1)[1].strip()
                        try:
                            import json
                            fatal_payload = json.loads(raw)
                            self.events.put(("worker_fatal", run_id, fatal_payload))
                        except Exception:
                            self.events.put(("log", line))
                    else:
                        self.events.put(("log", line))
                try:
                    stream.close()
                except Exception:
                    pass
            return_code = process.wait()
        except Exception as exc:
            return_code = process.poll()
            if return_code is None:
                return_code = -1
            output_tail.append(f"[GUI WORKER READER ERROR] {exc}\n")
            self.events.put(("log", output_tail[-1]))
        if return_code != 0 and fatal_payload is None:
            captured = "".join(output_tail)[-9000:]
            lines = [line.strip() for line in output_tail if line.strip()]
            detected_type = "WorkerProcessExit"
            detected_message = f"The video producer service exited with code {return_code}."
            for candidate in reversed(lines):
                match = re.match(r"^([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Interrupt|Exit)):\s*(.*)$", candidate)
                if match:
                    detected_type = match.group(1).split(".")[-1]
                    detected_message = match.group(2) or candidate
                    break
            fatal_payload = {"error_type": detected_type, "message": detected_message, "traceback": captured}
        self.events.put(("worker_exit", run_id, return_code, fatal_payload))

    def _finish_worker(self, return_code, fatal_payload):
        self.running = False
        self.paused = False
        self.process = None
        self.active_run_id = None
        self.progress.stop()
        self.pause_all_button.configure(state="disabled")
        self.resume_all_button.configure(state="disabled")
        self.stop_all_button.configure(state="disabled")
        self.start_button.configure(state="normal")
        if self._closing_requested:
            self.log("The video producer service has stopped. Checking the Image Producer before closing SceneIQ.", "SUCCESS")
            try:
                self.root.after(0, self._poll_close)
            except Exception:
                pass
            return
        if return_code == 0 and not fatal_payload:
            self.set_status("VIDEO SERVICE STOPPED", self.AMBER)
            self._set_visual_state(
                "stopped", "VIDEO PRODUCER IS STOPPED",
                "The video service has exited, but the desktop control center remains open. Press Start Producer to launch it again.",
                self.AMBER, detail="The window is still active and can restart the service.",
            )
            self.log("Video producer service exited normally.", "INFO")
        else:
            if not fatal_payload:
                fatal_payload = {
                    "error_type": "Unexpected service interruption",
                    "message": f"The video producer service ended with code {return_code}.",
                    "traceback": "The service exited without reporting a normal completion.",
                }
            self.set_status("VIDEO SERVICE NEEDS ATTENTION", self.RED)
            self._set_visual_state(
                "aborted", "VIDEO SERVICE ENCOUNTERED AN ERROR",
                "The video service stopped because of a technical issue. The desktop window remains open; review the console and restart when ready.",
                self.RED, detail=f"{fatal_payload.get('error_type', 'Error')}: {fatal_payload.get('message', '')}",
            )
            self.log(
                f"Video service failure: {fatal_payload.get('error_type', 'UnknownError')}: {fatal_payload.get('message', 'Unknown failure')}\n"
                f"{fatal_payload.get('traceback', '')}\n",
                "ERROR",
            )

    def _update_runtime(self):
        import time
        if not self.running or self.started_at is None or self._closing:
            return
        elapsed = max(0, int(time.monotonic() - self.started_at))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.runtime_value.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.root.after(500, self._update_runtime)

    def _write_job_control(self, job, command):
        control_path = job.get("control_path")
        if not control_path:
            status = self.latest_statuses.get(str(job.get("worker_id")), {})
            control_path = status.get("control_path")
        if not control_path:
            self.log(f"No control file is available for {job.get('project_title', 'this video')}.", "WARNING")
            return False
        try:
            _video_producer_write_control(control_path, command)
            self.log(f"{command.upper()} command sent to {job.get('project_title', job.get('worker_id', 'video'))}.", "INFO")
            return True
        except Exception as exc:
            self.log(f"Could not send {command} command: {type(exc).__name__}: {exc}", "ERROR")
            return False

    def _send_card_control(self, worker_id, command):
        job = next((item for item in self.latest_jobs if str(item.get("worker_id")) == str(worker_id)), None)
        if job:
            self._write_job_control(job, command)

    def pause_all(self):
        changed = 0
        for job in self.latest_jobs:
            status = self.latest_statuses.get(str(job.get("worker_id")), {}).get("status", "").casefold()
            if status == "running":
                changed += bool(self._write_job_control(job, "pause"))
        self.log(f"Pause All sent to {changed} running video(s).", "INFO")

    def resume_all(self):
        changed = 0
        for job in self.latest_jobs:
            status = self.latest_statuses.get(str(job.get("worker_id")), {}).get("status", "").casefold()
            if status == "paused":
                changed += bool(self._write_job_control(job, "resume"))
        for job in self.latest_jobs:
            status = self.latest_statuses.get(str(job.get("worker_id")), {}).get("status", "").casefold()
            if status in {"stopped", "failed"}:
                changed += bool(self._write_job_control(job, "start"))
        self.log(f"Resume All sent to {changed} paused/stopped video(s).", "INFO")

    def stop_all(self):
        changed = 0
        for job in self.latest_jobs:
            status = self.latest_statuses.get(str(job.get("worker_id")), {}).get("status", "").casefold()
            if status in {"running", "paused", "queued", "stopping"}:
                changed += bool(self._write_job_control(job, "stop"))
        self.log(f"Stop All sent to {changed} active/queued video(s). Completed work remains saved.", "WARNING")

    def _make_job_card(self, job, index):
        import tkinter as tk
        card = tk.Frame(self.grid_frame, bg=self.PANEL, highlightbackground=self.BORDER,
                        highlightthickness=1, padx=13, pady=10)
        card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=7, pady=7)
        title_row = tk.Frame(card, bg=self.PANEL)
        title_row.pack(fill="x")
        title_label = tk.Label(
            title_row, text=str(job.get("project_title") or "Video production"),
            bg=self.PANEL, fg=self.TEXT, font=("Segoe UI", 10, "bold"),
            justify="left", anchor="w", wraplength=720,
        )
        title_label.pack(side="left", fill="x", expand=True)
        badge = tk.Label(title_row, text="QUEUED", bg="#1C3450", fg=self.BLUE,
                         font=("Consolas", 8, "bold"), padx=9, pady=4)
        badge.pack(side="right", padx=(8, 0))
        meta = tk.Label(
            card,
            text=f"{job.get('worker_id', f'WORKER-{index + 1:03d}')}  •  {str(job.get('lane') or 'CPU').upper()} LANE  •  Encoder: {job.get('encoder') or 'libx264'}",
            bg=self.PANEL, fg=self.MUTED, font=("Consolas", 8), anchor="w",
        )
        meta.pack(fill="x", pady=(5, 5))

        preview_heading_row = tk.Frame(card, bg=self.PANEL)
        preview_heading_row.pack(fill="x", pady=(0, 3))
        preview_heading = tk.Label(
            preview_heading_row, text="LIVE SCENE PREVIEW", bg=self.PANEL, fg=self.CYAN,
            font=("Consolas", 8, "bold"), anchor="w",
        )
        preview_heading.pack(side="left")
        preview_scene_hint = tk.Label(
            preview_heading_row, text="WAITING FOR RENDER", bg=self.PANEL, fg=self.MUTED,
            font=("Consolas", 7), anchor="e",
        )
        preview_scene_hint.pack(side="right")
        preview_label = tk.Label(
            card, text="The visual preview will appear when the first scene frame is rendered.",
            bg="#050A10", fg="#8297B1", font=("Segoe UI", 8),
            justify="center", anchor="center", height=8,
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        preview_label.pack(fill="x", pady=(0, 8))

        stage_label = tk.Label(card, text="Waiting for a rendering process", bg=self.PANEL,
                               fg=self.TEXT, font=("Segoe UI", 9, "bold"), anchor="w")
        stage_label.pack(fill="x")
        detail_label = tk.Label(card, text="The project is queued for production.", bg=self.PANEL,
                                fg=self.MUTED, font=("Segoe UI", 8), anchor="w",
                                justify="left", wraplength=760)
        detail_label.pack(fill="x", pady=(2, 7))
        progress_row = tk.Frame(card, bg=self.PANEL)
        progress_row.pack(fill="x")
        progress_bar = self.ttk.Progressbar(
            progress_row, style="SceneIQ.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate", maximum=100,
        )
        progress_bar.pack(side="left", fill="x", expand=True)
        progress_label = tk.Label(progress_row, text="—", bg=self.PANEL, fg=self.CYAN,
                                  font=("Consolas", 8, "bold"), width=12, anchor="e")
        progress_label.pack(side="right", padx=(8, 0))
        footer = tk.Frame(card, bg=self.PANEL)
        footer.pack(fill="x", pady=(6, 4))
        elapsed_label = tk.Label(footer, text="Elapsed: —", bg=self.PANEL, fg=self.MUTED,
                                 font=("Segoe UI", 8), anchor="w")
        elapsed_label.pack(side="left")
        whisper_label = tk.Label(footer, text="Speech recognition: —", bg=self.PANEL, fg=self.MUTED,
                                 font=("Segoe UI", 8), anchor="e")
        whisper_label.pack(side="right")
        actions = tk.Frame(card, bg=self.PANEL)
        actions.pack(fill="x", pady=(3, 0))
        buttons = {}
        button_specs = (
            ("pause", "Ⅱ  PAUSE", "#34435A", "pause"),
            ("resume", "▶  RESUME", "#164D43", "resume"),
            ("stop", "■  STOP", "#542A32", "stop"),
            ("start", "▶  START", "#24523D", "start"),
        )
        worker_id = str(job.get("worker_id") or f"WORKER-{index + 1:03d}")
        for key, caption, color, command in button_specs:
            button = tk.Button(
                actions, text=caption, bg=color, fg=self.TEXT,
                activebackground=self.BORDER, activeforeground=self.TEXT,
                relief="flat", padx=11, pady=5,
                font=("Segoe UI", 8, "bold"), cursor="hand2",
                command=lambda wid=worker_id, cmd=command: self._send_card_control(wid, cmd),
            )
            buttons[key] = button
        buttons["console"] = tk.Button(
            actions, text="▤  VIEW CONSOLE", bg="#17364D", fg="#A9EAF7",
            activebackground="#24516B", activeforeground="#FFFFFF",
            relief="flat", padx=9, pady=5, font=("Segoe UI", 8, "bold"),
            cursor="hand2", command=lambda wid=worker_id: self.show_video_console(wid),
        )
        buttons["issue"] = tk.Button(
            actions, text="!  VIEW ISSUE", bg="#642B37", fg="#FFE4E8",
            activebackground="#813647", activeforeground="#FFFFFF",
            relief="flat", padx=9, pady=5, font=("Segoe UI", 8, "bold"),
            cursor="hand2", command=lambda wid=worker_id: self.show_video_issue(wid),
        )

        def resize_card_text(event):
            # Keep title and diagnostics readable when the window is resized or
            # when the fixed two-column grid is shown on a smaller display.
            usable_width = max(180, int(event.width) - 42)
            try:
                title_label.configure(wraplength=usable_width)
                detail_label.configure(wraplength=usable_width)
                preview_label.configure(wraplength=max(160, usable_width - 12))
            except Exception:
                pass

        card.bind("<Configure>", resize_card_text, add="+")
        return {
            "frame": card, "title": title_label, "badge": badge, "meta": meta,
            "preview": preview_label, "preview_heading": preview_heading,
            "preview_scene_hint": preview_scene_hint, "preview_photo": None,
            "preview_signature": None, "stage": stage_label, "detail": detail_label,
            "progress": progress_bar, "progress_text": progress_label,
            "elapsed": elapsed_label, "whisper": whisper_label,
            "actions": actions, "buttons": buttons,
        }

    def _update_job_card(self, card, job, status):
        import time
        title = str(job.get("project_title") or status.get("project_title") or "Video production")
        worker_id = str(job.get("worker_id") or status.get("worker_id") or "WORKER")
        lane = str(job.get("lane") or status.get("lane") or "cpu").upper()
        encoder = job.get("encoder") or status.get("encoder") or "libx264"
        card["title"].configure(text=self._safe_gui_text(title))
        card["meta"].configure(text=f"{worker_id}  •  {lane} LANE  •  Encoder: {encoder}")
        state = str(status.get("status") or "queued").casefold()
        stage = status.get("stage") or ("Waiting for a rendering process" if state == "queued" else "Video production")
        detail = status.get("detail") or "Waiting for the producer to publish the next update."
        card["stage"].configure(text=self._safe_gui_text(stage))
        card["detail"].configure(text=self._safe_gui_text(detail))
        self._update_job_card_preview(card, job, status)
        badge_colors = {
            "running": ("#123D36", self.GREEN), "paused": ("#4B3B1D", self.AMBER),
            "stopped": ("#263348", self.TEXT), "stopping": ("#4B3B1D", self.AMBER),
            "queued": ("#1C3450", self.BLUE), "completed": ("#123D36", self.GREEN),
            "failed": ("#4B202B", self.RED),
        }
        badge_bg, badge_fg = badge_colors.get(state, ("#263348", self.TEXT))
        badge_text = "ISSUE" if state == "failed" else state.replace("_", " ").upper()
        card["badge"].configure(text=badge_text, bg=badge_bg, fg=badge_fg)
        progress = status.get("progress")
        if progress is None:
            try:
                current = float(status.get("current"))
                total = float(status.get("total"))
                progress = (current / total * 100.0) if total > 0 else 0.0
            except (TypeError, ValueError):
                progress = 0.0
        try:
            progress = float(progress)
            progress = max(0.0, min(100.0, progress))
        except (TypeError, ValueError):
            progress = 0.0
        card["progress"]["value"] = progress
        card["progress_text"].configure(text=f"{progress:.0f}%")
        started = status.get("started_at") or status.get("queued_at") or job.get("queued_at")
        elapsed_text = "—"
        try:
            elapsed = max(0, int(time.time() - float(started)))
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            elapsed_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except (TypeError, ValueError):
            pass
        card["elapsed"].configure(text=f"Elapsed: {elapsed_text}")
        device = status.get("whisper_device") or "cpu"
        compute = status.get("whisper_compute_type") or "int8"
        card["whisper"].configure(text=f"Speech recognition: {device} / {compute}")
        for button in card["buttons"].values():
            button.pack_forget()
        if state == "running":
            card["buttons"]["pause"].pack(side="left", padx=(0, 6))
            card["buttons"]["stop"].pack(side="left", padx=(0, 6))
        elif state == "paused":
            card["buttons"]["resume"].pack(side="left", padx=(0, 6))
            card["buttons"]["stop"].pack(side="left", padx=(0, 6))
        elif state in {"stopped", "stopping"}:
            if state == "stopped":
                card["buttons"]["start"].pack(side="left", padx=(0, 6))
        elif state == "failed":
            card["buttons"]["start"].pack(side="left", padx=(0, 6))
            card["buttons"]["issue"].pack(side="left", padx=(0, 6))
        elif state == "queued":
            card["buttons"]["stop"].pack(side="left", padx=(0, 6))
        # Every project has its own live console, whether it is queued, running,
        # paused, stopped, completed or has an issue. It sits alongside that
        # project's own Pause/Resume/Stop/Start actions.
        card["buttons"]["console"].pack(side="left", padx=(0, 6))

    def _update_job_card_preview(self, card, job, status):
        """Display the latest actual frame rendered for this specific video."""
        import os

        preview_path = status.get("preview_path") or job.get("preview_path")
        stage = str(status.get("stage") or "")
        scene_match = re.search(r"rendering scene\s+(\d+)\s+of\s+(\d+)", stage, re.IGNORECASE)
        if scene_match:
            card["preview_scene_hint"].configure(
                text=f"SCENE {scene_match.group(1)} / {scene_match.group(2)}"
            )
        elif str(status.get("status") or "").casefold() == "completed":
            card["preview_scene_hint"].configure(text="RENDER COMPLETE")
        elif str(status.get("status") or "").casefold() == "failed":
            card["preview_scene_hint"].configure(text="ISSUE REPORTED")
        elif stage:
            card["preview_scene_hint"].configure(text="PREPARING SCENE")

        if not preview_path or not os.path.isfile(preview_path):
            return

        try:
            stat = os.stat(preview_path)
            frame_width = max(180, min(640, int(card["frame"].winfo_width()) - 30))
            frame_height = max(102, int(frame_width * 9 / 16))
            signature = (
                int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
                int(stat.st_size), frame_width, frame_height,
            )
            if signature == card.get("preview_signature"):
                return

            from PIL import Image, ImageTk
            with Image.open(preview_path) as source_image:
                source_image = source_image.convert("RGB")
                resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                source_image.thumbnail((frame_width, frame_height), resampling)
                canvas_image = Image.new("RGB", (frame_width, frame_height), (5, 10, 16))
                paste_x = (frame_width - source_image.width) // 2
                paste_y = (frame_height - source_image.height) // 2
                canvas_image.paste(source_image, (paste_x, paste_y))
            photo = ImageTk.PhotoImage(canvas_image)
            card["preview"].configure(image=photo, text="", width=frame_width, height=frame_height)
            card["preview_photo"] = photo
            card["preview_signature"] = signature
        except Exception as preview_ui_exc:
            # Preview UI is supplemental and must never disrupt controls/rendering.
            card["preview_scene_hint"].configure(text="PREVIEW UNAVAILABLE")
            if not card.get("preview_ui_warned"):
                card["preview_ui_warned"] = True
                self.log(
                    f"Could not display the live preview for {job.get('project_title')}: "
                    f"{type(preview_ui_exc).__name__}: {preview_ui_exc}",
                    "WARNING",
                )

    def show_video_issue(self, worker_id):
        """Show one video's compact, borderless failure dialog and copyable result."""
        import os
        import tkinter as tk
        from tkinter import ttk

        job = next((item for item in self.latest_jobs if str(item.get("worker_id")) == str(worker_id)), {})
        status = self.latest_statuses.get(str(worker_id), {})
        issue = {}
        issue_path = job.get("issue_path") or status.get("issue_path")
        if issue_path:
            value = self._read_dashboard_json(issue_path, {})
            if isinstance(value, dict):
                issue = value
        combined = dict(status)
        combined.update({key: value for key, value in issue.items() if value not in (None, "")})
        title = str(job.get("project_title") or status.get("project_title") or "Video production")
        error_type = combined.get("error_type") or "ProductionIssue"
        reason = combined.get("issue_summary") or combined.get("error") or combined.get("detail") or "The producer did not return a completed video."
        stage = combined.get("issue_stage") or combined.get("stage") or "Unknown stage"
        log_path = combined.get("log_path") or job.get("log_path")
        traceback_text = combined.get("traceback") or ""
        log_tail = ""
        if log_path and os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                    log_tail = handle.read()[-24000:]
            except Exception as exc:
                log_tail = f"Could not read worker log: {type(exc).__name__}: {exc}"
        details = (
            f"VIDEO: {title}\n"
            f"WORKER: {worker_id}\n"
            f"FAILED STAGE: {stage}\n"
            f"ERROR TYPE: {error_type}\n\n"
            f"WHAT HAPPENED\n{reason}\n\n"
            f"WORKER LOG: {log_path or 'Not recorded'}\n"
            f"WORKSPACE: {combined.get('workspace_path') or status.get('workspace_path') or 'Not available'}\n\n"
            f"TRACEBACK / DIAGNOSTICS\n{traceback_text or 'No Python traceback was produced for this issue.'}\n\n"
            f"LATEST WORKER LOG\n{log_tail or 'No worker log content is available.'}"
        )

        window = tk.Toplevel(self.root)
        # Remove the operating-system title bar and its X button. Every close
        # action is presented in the dialog footer instead.
        window.overrideredirect(True)
        window.geometry("560x390")
        window.minsize(500, 340)
        window.configure(bg=self.BORDER)
        window.transient(self.root)
        shell = tk.Frame(window, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(shell, bg="#3B1E2A", padx=14, pady=10)
        header.pack(fill="x")
        tk.Label(header, text="VIDEO PRODUCTION ISSUE", bg="#3B1E2A", fg="#FF9AAA",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(header, text=self._safe_gui_text(f"{title}  •  {stage}"), bg="#3B1E2A", fg=self.TEXT,
                 font=("Segoe UI", 9), justify="left", wraplength=510).pack(anchor="w", pady=(3, 0))
        body = tk.Frame(shell, bg=self.BG, padx=10, pady=9)
        body.pack(fill="both", expand=True)
        text = tk.Text(body, bg="#070C15", fg="#DCE7F5", insertbackground=self.CYAN,
                       selectbackground="#1A4861", wrap="word", relief="flat",
                       font=("Segoe UI", 9), padx=9, pady=8)
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.insert("1.0", details)
        text.configure(state="disabled")
        footer = tk.Frame(shell, bg=self.BG, padx=10, pady=9)
        footer.pack(fill="x")
        tk.Button(
            footer, text="COPY ISSUE RESULT", command=lambda: self._copy_text(details),
            bg="#172E49", fg=self.CYAN, activebackground="#214767",
            relief="flat", bd=0, padx=13, pady=8,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        ).pack(side="left")

        def close_issue_dialog():
            try:
                window.grab_release()
            except Exception:
                pass
            try:
                window.destroy()
            except Exception:
                pass

        tk.Button(
            footer, text="CLOSE", command=close_issue_dialog,
            bg="#202C3E", fg=self.TEXT, activebackground="#2B3B52",
            relief="flat", bd=0, padx=18, pady=8,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
        ).pack(side="right")
        window.bind("<Escape>", lambda _event: close_issue_dialog())
        try:
            window.update_idletasks()
            parent_x = self.root.winfo_rootx()
            parent_y = self.root.winfo_rooty()
            parent_w = max(1, self.root.winfo_width())
            parent_h = max(1, self.root.winfo_height())
            dialog_w = max(560, window.winfo_reqwidth())
            dialog_h = max(390, window.winfo_reqheight())
            dialog_x = parent_x + max(0, (parent_w - dialog_w) // 2)
            dialog_y = parent_y + max(0, (parent_h - dialog_h) // 2)
            window.geometry(f"{dialog_w}x{dialog_h}+{dialog_x}+{dialog_y}")
            window.grab_set()
            window.lift()
            window.focus_force()
        except Exception:
            pass

    def _copy_text(self, value):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(value))
            self.log("Issue details copied to the clipboard.", "SUCCESS")
        except Exception as exc:
            self.log(f"Could not copy issue details: {exc}", "WARNING")

    def _read_dashboard_json(self, path, default):
        try:
            value = _video_producer_read_json(path, default)
            return value if isinstance(value, (dict, list)) else default
        except Exception:
            return default

    def _write_heartbeat(self):
        import os
        import time
        try:
            _video_producer_write_json_atomic(self.heartbeat_path, {
                "pid": os.getpid(), "heartbeat_at": time.time(),
            })
        except Exception:
            try:
                import json
                with open(self.heartbeat_path, "w", encoding="utf-8") as handle:
                    json.dump({"pid": os.getpid(), "heartbeat_at": time.time()}, handle)
            except Exception:
                pass

    def _refresh_dashboard(self):
        import time
        if self._closing:
            return
        try:
            manifest = self._read_dashboard_json(self.manifest_path, {})
            if not isinstance(manifest, dict):
                manifest = {}
            self.latest_manifest = manifest
            jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []
            self.latest_jobs = jobs
            message = str(manifest.get("message") or "The SceneIQ video producer window is active.")
            service_status = str(manifest.get("service_status") or ("Running" if self.running else "Ready"))
            self.mode_value.configure(text=self._safe_gui_text(service_status.upper()[:40]))
            self.hero_description.configure(text=self._safe_gui_text(message))
            self.hero_queue_value.configure(text=f"{len(jobs)} PROJECT" if len(jobs) == 1 else f"{len(jobs)} PROJECTS")
            self.queue_count_label.configure(text=f"{len(jobs)} PROJECT(S)")

            active_ids = set()
            counts = {"running": 0, "paused": 0, "stopped": 0, "queued": 0, "completed": 0, "failed": 0}
            statuses = {}
            for index, job in enumerate(jobs):
                worker_id = str(job.get("worker_id") or f"WORKER-{index + 1:03d}")
                active_ids.add(worker_id)
                status = self._read_dashboard_json(job.get("status_path"), {})
                if not isinstance(status, dict):
                    status = {}
                status_state = str(status.get("status") or "queued").casefold()
                statuses[worker_id] = status
                if status_state in {"stopping"}:
                    counts["stopped"] += 1
                elif status_state in counts:
                    counts[status_state] += 1
                else:
                    counts["queued"] += 1
                card = self.job_cards.get(worker_id)
                if card is None:
                    card = self._make_job_card(job, index)
                    self.job_cards[worker_id] = card
                # Two equal columns are always reserved. With one project it stays
                # in the first column rather than expanding across the whole row.
                card["frame"].grid_configure(
                    row=index // 2, column=index % 2, sticky="nsew"
                )
                self._update_job_card(card, job, status)
            for worker_id in list(self.job_cards):
                if worker_id not in active_ids:
                    try:
                        self.job_cards[worker_id]["frame"].destroy()
                    except Exception:
                        pass
                    self.job_cards.pop(worker_id, None)
            self.latest_statuses = statuses
            total = len(jobs)
            running = counts["running"]
            paused = counts["paused"]
            if not jobs:
                if not self.empty_label.winfo_ismapped():
                    self.empty_label.grid(row=0, column=0, columnspan=2, sticky="nw", padx=8, pady=8)
            else:
                if self.empty_label.winfo_ismapped():
                    self.empty_label.grid_remove()
            summary = (
                f"{running} running  •  {paused} paused  •  {counts['stopped']} stopped  •  "
                f"{counts['queued']} queued  •  {counts['completed']} completed  •  {counts['failed']} with issues"
            )
            self.hero_detail.configure(text=self._safe_gui_text(summary))
            if self.running:
                if paused and not running:
                    self.set_status("VIDEO PRODUCTION PAUSED", self.AMBER)
                    self._set_visual_state("paused", "VIDEO PRODUCTION IS PAUSED",
                        "One or more projects are paused. Resume an individual video or use Resume All to continue.",
                        self.AMBER, detail=summary)
                elif running:
                    self.set_status("VIDEO PRODUCTION RUNNING", self.GREEN)
                    self._set_visual_state("running", "SCENEIQ IS PRODUCING VIDEOS",
                        "The video service is processing the queue. Individual video controls remain available below.",
                        self.GREEN, detail=summary)
                else:
                    self.set_status("PRODUCER SERVICE ACTIVE", self.CYAN)
                    self._set_visual_state("ready", "WAITING FOR VIDEO WORK",
                        "The service is active and watching for new projects or individual restart commands.",
                        self.CYAN, detail=summary)
            elif not self._closing_requested and not self.startup_failed:
                self.set_status("VIDEO PRODUCER READY", self.CYAN)
            self.pause_all_button.configure(state="normal" if running else "disabled")
            self.resume_all_button.configure(state="normal" if paused or counts["stopped"] else "disabled")
            self.stop_all_button.configure(state="normal" if (running + paused + counts["queued"]) else "disabled")
        except Exception as exc:
            # Never let optional status parsing or UI refresh errors destroy Tk.
            try:
                self.mode_value.configure(text="STATUS REFRESH RETRYING")
                self.log(f"Dashboard refresh warning: {type(exc).__name__}: {exc}", "WARNING")
            except Exception:
                pass
        finally:
            self._write_heartbeat()
            if not self._closing:
                try:
                    self.root.after(700, self._refresh_dashboard)
                except Exception:
                    pass

    def refresh_now(self):
        self._refresh_dashboard()

    def _write_shutdown_request(self):
        import time
        try:
            _video_producer_write_json_atomic(self.shutdown_path, {
                "shutdown": True, "requested_at": time.time(), "requested_by": "SceneIQ desktop window",
            })
        except Exception as exc:
            self.log(f"Could not write graceful shutdown request: {exc}", "WARNING")

    def _confirm_exit_with_custom_modal(self):
        """Show a centered, movable, borderless exit prompt with only Cancel and Exit."""
        import tkinter as tk

        video_active = self.process is not None and self.process.poll() is None
        image_active = self.image_process is not None and self.image_process.poll() is None
        if video_active and image_active:
            message = (
                "Video Producer and Image Producer are currently active. Exiting SCiQ "
                "will request both isolated workers to stop safely. Completed video "
                "renders, generated images and saved workflow progress will be retained."
            )
        elif video_active:
            message = (
                "Video production is currently active. Exiting SCiQ will request the "
                "Video Producer to stop at its next safe checkpoint. Completed renders "
                "and saved progress will be retained."
            )
        elif image_active:
            message = (
                "Image production is currently active. Exiting SCiQ will request the "
                "Image Producer to stop safely. Generated images and saved workflow "
                "progress will be retained."
            )
        else:
            message = "Are you sure you want to exit SCiQ? No production workers are currently running."

        result = {"confirmed": False}
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.configure(bg=self.BG)
        window.transient(self.root)
        window.resizable(False, False)

        shell = tk.Frame(
            window, bg=self.BG, bd=0, relief="flat",
            highlightthickness=1, highlightbackground="#15577A",
        )
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#0B1C31", bd=0, highlightthickness=0, padx=18, pady=13)
        header.pack(fill="x")
        tk.Label(
            header, text="SCiQ  /  EXIT CONFIRMATION", bg="#0B1C31", fg=self.CYAN,
            font=("Segoe UI", 11, "bold"), anchor="w",
        ).pack(fill="x")

        body = tk.Frame(shell, bg=self.BG, padx=20, pady=18)
        body.pack(fill="both", expand=True)
        tk.Label(
            body, text=message, bg=self.BG, fg=self.TEXT,
            font=("Segoe UI", 9), justify="left", anchor="w", wraplength=500,
        ).pack(fill="both", expand=True)

        footer = tk.Frame(shell, bg=self.BG, padx=18, pady=14)
        footer.pack(fill="x")

        def finish(confirmed=False):
            result["confirmed"] = bool(confirmed)
            try:
                window.grab_release()
            except Exception:
                pass
            try:
                window.destroy()
            except Exception:
                pass

        # Exactly two actions: Cancel at the left edge, Exit at the right edge.
        tk.Button(
            footer, text="CANCEL", command=lambda: finish(False),
            bg="#172A40", fg=self.TEXT, activebackground="#24425F",
            activeforeground=self.TEXT, relief="flat", bd=0,
            padx=25, pady=10, font=("Segoe UI", 9, "bold"), cursor="hand2",
        ).pack(side="left")
        tk.Button(
            footer, text="EXIT SCiQ", command=lambda: finish(True),
            bg="#542A39", fg="#FFE8ED", activebackground="#74384C",
            activeforeground="#FFFFFF", relief="flat", bd=0,
            padx=25, pady=10, font=("Segoe UI", 9, "bold"), cursor="hand2",
        ).pack(side="right")

        # The title strip is the drag handle, keeping this borderless modal portable.
        drag_state = {"x": 0, "y": 0, "left": 0, "top": 0}
        def drag_start(event):
            drag_state["x"] = int(event.x_root)
            drag_state["y"] = int(event.y_root)
            drag_state["left"] = int(window.winfo_x())
            drag_state["top"] = int(window.winfo_y())
        def drag_move(event):
            dx = int(event.x_root) - drag_state["x"]
            dy = int(event.y_root) - drag_state["y"]
            window.geometry(f"+{drag_state['left'] + dx}+{drag_state['top'] + dy}")
        header.bind("<ButtonPress-1>", drag_start)
        header.bind("<B1-Motion>", drag_move)

        window.bind("<Escape>", lambda _event: finish(False))
        window.bind("<Return>", lambda _event: finish(True))
        window.update_idletasks()
        width = max(540, int(window.winfo_reqwidth()))
        height = max(220, int(window.winfo_reqheight()))
        # Center against the physical screen, not the parent window's coordinates.
        screen_width = int(window.winfo_screenwidth())
        screen_height = int(window.winfo_screenheight())
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        try:
            window.grab_set()
            window.lift()
            window.focus_force()
        except Exception:
            pass
        self.root.wait_window(window)
        return result["confirmed"]

    def on_close(self):
        if self._closing or self._closing_requested:
            return

        # SCiQ always uses the same centered custom confirmation dialog.
        if not self._confirm_exit_with_custom_modal():
            return

        video_active = self.process is not None and self.process.poll() is None
        image_active = self.image_process is not None and self.image_process.poll() is None
        if not video_active and not image_active:
            self._close_application()
            return

        self._closing_requested = True
        self._close_started_at = __import__("time").monotonic()

        if video_active:
            self.stop_all()
            self._write_shutdown_request()
            self.set_status("STOPPING VIDEO AND IMAGE PRODUCERS", self.AMBER)
            self._set_visual_state(
                "stopped", "SCiQ IS STOPPING SAFELY",
                "SCiQ is asking both isolated producers to stop at safe checkpoints. Completed video renders and image workflow progress are retained.",
                self.AMBER,
                detail="The shared window will close after both producer processes exit.",
            )

        if image_active:
            self.stop_image_producer(from_close=True)

        try:
            self.root.after(350, self._poll_close)
        except Exception:
            self._poll_close()

    def _focus_sceneiq_window(self):
        """Return foreground focus to SCiQ after the Image Producer Alt+/ shortcut only."""
        if self._closing or self._closing_requested:
            return
        try:
            if not self.root.winfo_exists():
                return
            self.root.deiconify()
            try:
                if str(self.root.state()).casefold() == "iconic":
                    self.root.state("normal")
            except Exception:
                pass
            # Brief topmost promotion asks Windows to put the shared control center
            # above Google Flow and the image-only progress HUD.
            self.root.attributes("-topmost", True)
            self.root.lift()
            self.root.focus_force()
            self.root.after(900, self._release_sceneiq_focus_topmost)
        except Exception:
            pass

    def _release_sceneiq_focus_topmost(self):
        if self._closing:
            return
        try:
            if self.root.winfo_exists():
                self.root.attributes("-topmost", False)
        except Exception:
            pass

    def _poll_close(self):
        import time

        if self._closing:
            return

        video_process = self.process
        image_process = self.image_process
        video_alive = video_process is not None and video_process.poll() is None
        image_alive = image_process is not None and image_process.poll() is None

        if not video_alive and not image_alive:
            self._close_application()
            return

        elapsed = time.monotonic() - (self._close_started_at or time.monotonic())
        if elapsed > 600:
            self.log(
                "Graceful shutdown exceeded 10 minutes. Terminating remaining producer process trees.",
                "WARNING",
            )
            if video_alive:
                self._terminate_worker_tree(video_process.pid)
            if image_alive:
                self._terminate_external_process_tree(image_process.pid)
            self.root.after(1200, self._close_application)
            return

        self.root.after(400, self._poll_close)

    def _terminate_external_process_tree(self, pid):
        import os
        import subprocess
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, timeout=8, check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return
            except Exception:
                pass
        try:
            process = self.image_process
            if process is not None:
                process.terminate()
                process.wait(timeout=2)
        except Exception:
            try:
                if self.image_process is not None:
                    self.image_process.kill()
            except Exception:
                pass

    def _terminate_worker_tree(self, pid):
        import os
        import subprocess
        process = self.process
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=8, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                pass
        if process is not None:
            try:
                process.terminate()
            except Exception:
                pass
            try:
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    def _close_application(self):
        import sys
        if self._closing:
            return
        self._closing = True
        self._cancel_console_timer()
        try:
            sys.stdout = self.stdout_original
            sys.stderr = self.stderr_original
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass



def _sceneiq_worker_entry(manifest_path, shutdown_path, heartbeat_path):
    """CLI entry: run the service in a child process while the parent owns Tk."""
    import os
    import time
    import traceback
    global _VIDEO_PRODUCER_DASHBOARD_SESSION
    manifest = _video_producer_read_json(manifest_path, {})
    if not isinstance(manifest, dict):
        manifest = {}
    _VIDEO_PRODUCER_DASHBOARD_SESSION = {
        "session_dir": manifest.get("session_dir"),
        "manifest_path": os.path.abspath(manifest_path),
        "shutdown_path": os.path.abspath(shutdown_path),
        "heartbeat_path": os.path.abspath(heartbeat_path),
        "ready_path": None,
        "process": None,
        "pid": os.getpid(),
        "error": None,
        "created_at": time.time(),
        "manifest_cache": dict(manifest),
        "ui_managed": True,
    }
    print("\n" + "=" * 72)
    print("SCENEIQ VIDEO PRODUCER SERVICE WORKER")
    print(f"Worker PID: {os.getpid()}")
    print("The desktop GUI is hosted by the parent process.")
    print("=" * 72 + "\n", flush=True)
    try:
        video_producer_service_loop()
        print("SCENEIQ_WORKER_RESULT=SUCCESS", flush=True)
        return 0
    except KeyboardInterrupt:
        print("SceneIQ service worker received an interrupt.", flush=True)
        return 0
    except BaseException as exc:
        payload = {
            "error_type": type(exc).__name__,
            "message": str(exc),
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        }
        try:
            import json
            print("SCENEIQ_FATAL_JSON=" + json.dumps(payload, ensure_ascii=False), flush=True)
        except Exception:
            traceback.print_exc()
        return 1


def main():
    """Create the one visible SceneIQ desktop window and start its isolated service."""
    import tkinter as tk
    import traceback
    try:
        application_root = tk.Tk()
        app = SceneIQApp(application_root)
        application_root.mainloop()
    except Exception as startup_error:
        try:
            import sys
            sys.__stderr__.write(f"SceneIQ desktop window failed to start: {startup_error}\n")
            traceback.print_exc(file=sys.__stderr__)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    multiprocessing.freeze_support()
    import sys
    if len(sys.argv) >= 5 and sys.argv[1] == "--sceneiq-worker":
        raise SystemExit(_sceneiq_worker_entry(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "--sceneiq-dashboard":
        # Detached legacy dashboards are disabled. The only supported visible
        # application is the single parent-owned SceneIQ control-center window.
        raise SystemExit("Detached SceneIQ dashboard mode is disabled; launch the main desktop application.")
    else:
        if _sceneiq_acquire_single_instance():
            main()
            
