from ProcessComboTextFile import parse_videodata, parse_jsonl, write_jsonl_atomic, append_jsonl
import os
import subprocess
import config
import random
import json
import datetime
from AI_functions import provide_AI_comptitle, provide_AI_desc, provide_image
import tempfile
from pathlib import Path
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)
#shared keys
KEY_FILE      = "file path"
KEY_TITLE     = "title"
KEY_DESC      = "description"
KEY_USED  = "used in compilation"
KEY_FIXED = "metadata fixed"
KEY_CLIPTITLES = "clip titles"
KEY_CLIPFILES = "clip files"
KEY_THUMBNAIL = "thumbnail"
KEY_ID        = "videoId"

def update_compilation_data_old(clip_titles, output_path, clip_file_paths: Optional[List[str]] = None):
    """
    Updates the COMP_DATA file with the dictionary for the compilation.
    
    :param clip_titles: List containing the clip titles used in the compilation.
    :param output_path: Path to save the compilation video.
    """
    # Convert any Path objects to strings to ensure they are JSON serializable
    output_path_str = str(output_path)  # Convert WindowsPath to string
    # Convert backslashes to forward slashes for FFmpeg compatibility
    formatted_path = output_path_str.replace("\\", "/")
    # Escape single quotes inside filenames by doubling them
    escaped_path = formatted_path.replace("'", "''")

    # Prepare the dictionary with required keys
    Title = provide_AI_comptitle(clip_titles)
    Desc = provide_AI_desc(Title)
    Title = Title.strip("\"")
    Desc = "Check out flippi.gg to register your tag to be ...and learn more about Project Flippi!" +"\n\n" + Desc.strip("\"")

    
    #Create thumbnail
    thumbnail = provide_image(Title)
    if thumbnail is None:
        logger.warning("Thumbnail generation failed; checking for fallback placeholder.")
        fallback = config.THUMBNAILS_FOLDER / 'image.png'
        if Path(fallback).exists():
            thumbnail = fallback
        else:
            thumbnail = None

    thumbnail_str = None
    if thumbnail is not None:
        thumbnail_str = str(thumbnail).replace("\\", "/").replace("'", "''")
    
    compilation_dict = {
        KEY_FILE: escaped_path,  
        KEY_TITLE: Title,
        KEY_DESC: Desc,
        KEY_CLIPTITLES: clip_titles,
        KEY_CLIPFILES: clip_file_paths if clip_file_paths else []
    }
    if thumbnail_str is not None:
        compilation_dict["Thumbnail"] = thumbnail_str

    
    # Check if the COMP_DATA file exists and is non-empty
    if os.path.exists(config.COMP_DATA):
        try:
            with open(config.COMP_DATA, "r", encoding="utf-8") as file:
                comp_data = json.load(file)  # Try loading existing data
        except json.JSONDecodeError:
            logger.warning("Error reading %s: empty or corrupted; starting fresh.", config.COMP_DATA)
            comp_data = []  # If the file is empty or corrupted, start with an empty list
    else:
        comp_data = []  # If the file doesn't exist, start with an empty list
    
    # Append the new compilation data
    comp_data.append(compilation_dict)
    
    # Write the updated data back to the file
    _json_dump_atomic(comp_data, config.COMP_DATA)
    logger.info("Updated %s with new compilation data.", config.COMP_DATA)

def update_compilation_data(
    clip_titles: List[str],
    output_path,
    clip_file_paths: Optional[List[str]] = None
) -> None:
    """
    Appends a single compilation record to COMP_DATA (.jsonl).
    Each compilation is one JSON object per line.
    """
    # Normalize paths to forward slashes for portability
    output_path_str = str(output_path).replace("\\", "/")

    # Generate title/desc (same behavior you had)
    Title = provide_AI_comptitle(clip_titles)
    Desc  = provide_AI_desc(Title)
    Title = (Title or "").strip().strip('"')
    Desc  = (
        "Check out flippi.gg to register your tag to be ...and learn more about Project Flippi!"
        "\n\n" + (Desc or "").strip().strip('"')
    )

    # Create thumbnail (keep your fallback logic)
    thumbnail = provide_image(Title)
    if thumbnail is None:
        fallback = config.THUMBNAILS_FOLDER / "image.png"
        thumbnail = fallback if Path(fallback).exists() else None

    thumbnail_str = str(thumbnail).replace("\\", "/") if thumbnail is not None else None

    # Normalize clip file paths if provided
    clip_file_paths = clip_file_paths or []
    clip_file_paths = [str(p).replace("\\", "/") for p in clip_file_paths]

    compilation_dict = {
        KEY_FILE:       output_path_str,
        KEY_TITLE:      Title,
        KEY_DESC:       Desc,
        KEY_CLIPTITLES: clip_titles,
        KEY_CLIPFILES:  clip_file_paths,
    }
    if thumbnail_str:
        compilation_dict[KEY_THUMBNAIL] = thumbnail_str

    # Append one JSON object to the JSONL file
    try:
        append_jsonl(config.COMP_DATA, [compilation_dict])
        logger.info("Appended new compilation record to %s", config.COMP_DATA)
    except Exception as e:
        logger.error("Failed to append compilation data: %s", e)

def select_clips_for_compilation_old(video_data, min_length=50, max_length=305):
    """
    Selects video clips sequentially until adding a clip would exceed max_length.
    Stops immediately once an overflow would happen.
    
    :param video_data: List of video metadata dictionaries.
    :param min_length: Minimum total length required for a compilation (seconds).
    :param max_length: Maximum total length allowed for a compilation (seconds).
    :return: A tuple (selected_clips, updated_video_data) or (None, video_data) if not enough.
    """
    # Filter to only unused clips
    unused_clips = [clip for clip in video_data if not clip.get("Used in Compilation", False)]

    if not unused_clips:
        logger.info("No unused clips available.")
        return None, video_data

    # Sort clips by timestamp (oldest first)
    try:
        unused_clips.sort(key=lambda c: c.get("Timestamp", ""))
    except Exception as e:
        logger.warning("Error sorting clips by timestamp: %s", e)

    selected_clips = []
    total_duration = 0.0
    updated_video_data = [dict(clip) for clip in video_data]  # shallow copy of dicts

    for clip in unused_clips:
        file_path = clip.get("File Path")
        if not file_path or not os.path.exists(file_path):
            continue

        # Get clip duration using ffprobe
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
        except Exception:
            logger.info("Skipping %s: Could not determine duration.", file_path)
            continue

        # If adding this clip would exceed max_length, stop immediately
        if total_duration + duration > max_length:
            logger.info("Stopping: adding %s (%.2fs) would exceed max_length.", file_path, duration)
            break

        selected_clips.append((file_path, duration))
        total_duration += duration

        # Mark as used
        for video_entry in updated_video_data:
            if video_entry["File Path"] == file_path:
                video_entry["Used in Compilation"] = True
                break  # Efficient exit

    if total_duration >= min_length:
        return selected_clips, updated_video_data
    else:
        logger.info("Compilation too short: %.2fs (minimum required: %ss).", total_duration, min_length)
        return None, video_data

def select_clips_for_compilation(
    video_rows: List[dict],
    min_length: int = 50,
    max_length: int = 305,
) -> tuple[Optional[List[Tuple[str, float]]], List[dict]]:
    """
    Selects video clips sequentially until adding a clip would exceed max_length.
    Stops immediately once an overflow would happen.

    :param video_rows: List of videodata rows (each a dict) from a .jsonl file.
    :param min_length: Minimum total length required for a compilation (seconds).
    :param max_length: Maximum total length allowed for a compilation (seconds).
    :return: (selected_clips, updated_rows) or (None, original_rows) if not enough.
             selected_clips = [(file_path, duration_sec), ...]
    """
    # Filter to only unused clips
    unused_clips = [clip for clip in video_rows if not clip.get(KEY_USED, False)]

    if not unused_clips:
        logger.info("No unused clips available.")
        return None, video_rows

    # Sort by timestamp (oldest first); fall back to raw string if parse fails
    try:
        unused_clips.sort(
            key=lambda c: (_parse_dt_loose(c.get(KEY_TIMESTAMP, "")) or c.get(KEY_TIMESTAMP, ""))
        )
    except Exception as e:
        logger.warning("Error sorting clips by timestamp: %s", e)

    selected_clips: List[Tuple[str, float]] = []
    total_duration = 0.0
    # Shallow copy so we can mark selections while leaving the original reference intact
    updated_rows = [dict(clip) for clip in video_rows]

    for clip in unused_clips:
        file_path = clip.get(KEY_FILE)
        if not file_path or not os.path.exists(file_path):
            continue

        # Probe duration with ffprobe
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
        except Exception:
            logger.info("Skipping %s: Could not determine duration.", file_path)
            continue

        # If adding this clip would exceed max_length, stop immediately
        if total_duration + duration > max_length:
            logger.info("Stopping: adding %s (%.2fs) would exceed max_length.", file_path, duration)
            break

        selected_clips.append((file_path, duration))
        total_duration += duration

        # Mark as used in the corresponding row of updated_rows
        for row in updated_rows:
            if row.get(KEY_FILE) == file_path:
                row[KEY_USED] = True
                break  # efficient exit

    if total_duration >= min_length and selected_clips:
        return selected_clips, updated_rows
    else:
        logger.info("Compilation too short: %.2fs (minimum required: %ss).", total_duration, min_length)
        return None, video_rows

def create_compilation(selected_clips, output_path):
    """
    Concatenates the selected clips and applies desired processing to produce a final compilation.

    :param selected_clips: List of tuples (file_path, duration).
    :param output_path: Destination for the final video file.
    :return: Path to the final output video, or None if failed.
    """
    if not selected_clips:
        logger.info("No valid clips selected for compilation.")
        return None

    # Create temporary directory for intermediate files
    temp_dir = tempfile.mkdtemp()
    try:
        # Prepare a file list for FFmpeg concat
        list_path = os.path.join(temp_dir, "list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for file_path, _ in selected_clips:
                if not os.path.isfile(file_path):
                    logger.info("Skipping %s: File not found.", file_path)
                    continue
                
                f.write(f"file '{_ffmpeg_escape_path(file_path)}'\n")

        # 1) Concatenate using FFmpeg 
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy",
            os.path.join(temp_dir, "temp_concatenated.mp4")
        ]
        subprocess.run(cmd_concat, check=True, capture_output=True, text=True)
        temp_compilation = os.path.join(temp_dir, "temp_concatenated.mp4")
        logger.info("Concatenated compilation saved at: %s", temp_compilation)

        # 2) Post-process 
        cmd_process = [
            "ffmpeg", "-y",
            "-i", temp_compilation,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "copy",
            str(output_path)
        ]
        subprocess.run(cmd_process, check=True, capture_output=True, text=True)
        logger.info("Final processed compilation saved at: %s", output_path)
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error("Error during processing: %s", e.stderr)
        return None
    finally:
        # Clean up temporary directory
        try:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(temp_dir)
        except Exception:
            pass

def _json_dump_atomic(data, file_path):
    """
    Safely writes JSON data to a file by first writing to a temporary file and then replacing the original.
    
    :param data: The JSON data to write.
    :param file_path: The path to the original file to be replaced.
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    temp_file_path = file_path + ".tmp"

    with open(temp_file_path, "w", encoding="utf-8") as temp_file:
        json.dump(data, temp_file, ensure_ascii=False, indent=2)

    os.replace(temp_file_path, file_path)

def get_clip_titles(video_data):
    """
    Returns the titles of the clips used in the compilation from VIDEO_DATA.
    
    :param video_data: List of video metadata dictionaries.
    :return: List of titles from the video data.
    """
    return [clip["Title"] for clip in video_data]

def get_clip_titles_from_selected(selected_clips, full_video_data):
    titles = []
    for file_path, _ in selected_clips:
        for clip in full_video_data:
            if clip.get(KEY_FILE) == file_path:
                titles.append(clip.get(KEY_TITLE, ""))
                break
    return titles

def _ffmpeg_escape_path(p: str) -> str:
    # ffmpeg concat file format: single quotes around a POSIX-style path; escape internal quotes
    p = str(p).replace("\\", "/")
    return p.replace("'", "''")

def _ffprobe_duration(path: str) -> Optional[float]:
    """
    Get duration in seconds using ffprobe. Returns None on failure.
    """
    try:
        cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", path
            ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        val = result.stdout.strip()
        if not val:
            return None
        return float(val)
    except Exception:
        return None

def generate_compilation_from_videodata(videodata_path):
    """
    Full process to generate a compilation from videodata.txt.
    Updates videodata.txt to mark used clips and skips already used ones.
    
    :param videodata_path: Path to 'videodata.txt'.
    :param output_path: Path to save the final compilation video.
    """
    ct = str(datetime.datetime.now().replace(microsecond=0))
    ct = ct.replace(":", "-")
    filename = ct + ".mp4" 
    output_path = config.COMPS_FOLDER / filename
    video_rows = parse_jsonl(videodata_path)  # Use the provided function
    selected_clips, updated_video_data = select_clips_for_compilation(video_data)

    if selected_clips:
        compilation_path = create_compilation(selected_clips, output_path)
        if compilation_path:
            write_jsonl_atomic(videodata_path, updated_video_data)
            logger.info("Updated videodata.txt to mark used clips.")
            clip_titles = get_clip_titles_from_selected(selected_clips, updated_video_data)
            update_compilation_data(clip_titles, compilation_path, [fp for fp, _ in selected_clips])  # Update the COMP_DATA with compilation info
        return compilation_path
    else:
        logger.info("Not enough valid unused clips to create a compilation.")
        return None

def update_video_data(file_path, updated_data):
    """
    Saves the updated video data back to the videodata.txt file.
    
    :param file_path: Path to 'videodata.txt'.
    :param updated_data: List of updated video metadata dictionaries.
    """
    _json_dump_atomic(updated_data, file_path)
    logger.info("Updated videodata.txt")

def fix_mp4_metadata(input_path, output_path=None):
    """
    Fixes metadata for an MP4 file by re-encoding (lossless) and adding duration info using FFmpeg.

    :param input_path: Path to the original MP4 file.
    :param output_path: (Optional) Path to save the fixed MP4 file. If None, overwrites the input file.
    :return: Path to the fixed MP4 file.
    """
    import shutil

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_temp{ext}"

    try:
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c", "copy",        
            "-movflags", "+faststart",
            "-metadata", "fixed_by=metadata-fix-script",
            output_path,
            "-y"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Replace the original with the fixed version
        if output_path != input_path:
            shutil.move(output_path, input_path)

        print(f"Metadata fully rebuilt and fixed for Explorer: {input_path}")
        return input_path

    except subprocess.CalledProcessError as e:
        print("Error processing file:", e.stderr.decode())
        return None

        
def fix_mp4_metadata_in_folder(folder_path, videodata_path: Optional[str] = None):
    """
    Fix metadata for all MP4 files in a folder using fix_mp4_metadata().
    If videodata_path is provided (JSONL), skip files already marked KEY_FIXED == True,
    and mark entries as fixed immediately after successful processing (no probing).
    """
    folder_path = str(folder_path)

    try:
        mp4_files = [
            os.path.join(folder_path, f).replace("\\", "/")
            for f in os.listdir(folder_path)
            if f.lower().endswith(".mp4")
        ]
    except FileNotFoundError:
        logger.warning("Video folder not found: %s", folder_path)
        return

    # Load videodata (JSONL) if provided
    videodata_rows = None
    path_to_idx: dict[str, int] = {}
    if videodata_path and os.path.exists(videodata_path):
        try:
            videodata_rows = parse_jsonl(videodata_path)  # -> List[dict]
            # Build an index by absolute path (as stored in videodata)
            for i, item in enumerate(videodata_rows):
                if isinstance(item, dict):
                    p = item.get(KEY_FILE)
                    if p:
                        path_to_idx[p] = i
        except Exception as e:
            logger.warning("Unable to read videodata from %s: %s", videodata_path, e)
            videodata_rows = None

    checked = 0
    fixed_count = 0
    skipped_already_fixed = 0
    wrote_videodata = False

    for mp4_file in mp4_files:
        checked += 1

        # If we have videodata, skip files already marked as fixed
        if videodata_rows is not None and path_to_idx:
            idx = path_to_idx.get(mp4_file)
            if idx is not None:
                entry = videodata_rows[idx]
                if isinstance(entry, dict) and entry.get(KEY_FIXED) is True:
                    skipped_already_fixed += 1
                    logger.info("Skipping (already marked fixed): %s", mp4_file)
                    continue

        # Run the fixer (your existing ffmpeg-based function)
        result = fix_mp4_metadata(mp4_file)

        if result:
            fixed_count += 1
            # Immediately mark videodata as fixed (no probing)
            if videodata_rows is not None and path_to_idx:
                idx = path_to_idx.get(mp4_file)
                if idx is not None and isinstance(videodata_rows[idx], dict):
                    videodata_rows[idx][KEY_FIXED] = True
                    wrote_videodata = True
                else:
                    logger.debug("File fixed but not found in videodata: %s", mp4_file)
        else:
            logger.warning("Failed to fix metadata for: %s", mp4_file)

    logger.info(
        "Metadata pass complete: checked=%d, fixed=%d, skipped_already_fixed=%d",
        checked, fixed_count, skipped_already_fixed
    )

    # Persist videodata updates once at the end (rewrite JSONL atomically)
    if videodata_path and videodata_rows is not None and wrote_videodata:
        try:
            write_jsonl_atomic(videodata_path, videodata_rows)
            logger.info("Videodata updated with '%s': true flags.", KEY_FIXED)
        except Exception as e:
            logger.error("Failed to write updated videodata to %s: %s", videodata_path, e)


def fix_mp4_metadata_in_folder_old(folder_path, videodata_path=None):
    """
    Fix metadata for all MP4 files in a folder using fix_mp4_metadata().
    If videodata_path is provided, skip files already marked "Metadata Fixed" == True,
    and mark entries as fixed immediately after successful processing (no probing).
    """
    folder_path = str(folder_path)
    mp4_files = [
    os.path.join(folder_path, f).replace("\\", "/")
    for f in os.listdir(folder_path)
    if f.lower().endswith(".mp4")
    ]

    # Load videodata if provided
    videodata = None
    path_to_entry = {}
    if videodata_path and os.path.exists(videodata_path):
        try:
            videodata = parse_videodata(videodata_path)
            # Build a lookup by absolute path (as stored in videodata)
            path_to_entry = {item.get(KEY_FILE): item for item in videodata if item.get(KEY_FILE)}
            

        except Exception as e:
            logger.warning("Unable to read videodata from %s: %s", videodata_path, e)

    checked = 0
    fixed_count = 0
    skipped_already_fixed = 0
    wrote_videodata = False

    for mp4_file in mp4_files:
        
        checked += 1

        # If we have videodata, skip files already marked as fixed
        if path_to_entry:
            entry = path_to_entry.get(mp4_file)
            if entry and entry.get(KEY_FIXED) is True:
                skipped_already_fixed += 1
                logger.info("Skipping (already marked fixed): %s", mp4_file)
                continue

        # Run the fixer (FFmpeg command remains unchanged inside fix_mp4_metadata)
        result = fix_mp4_metadata(mp4_file)

        if result:
            fixed_count += 1
            # Immediately mark videodata as fixed (no probing)
            if path_to_entry:
                entry = path_to_entry.get(mp4_file)
                if entry is not None:
                    entry[KEY_FIXED] = True
                    wrote_videodata = True
                else:
                    # No existing entry for this file; do nothing (or add if you want)
                    logger.debug("File fixed but not found in videodata: %s", mp4_file)
        else:
            logger.warning("Failed to fix metadata for: %s", mp4_file)

    logger.info(
        "Metadata pass complete: checked=%d, fixed=%d, skipped_already_fixed=%d",
        checked, fixed_count, skipped_already_fixed
    )

    # Persist videodata updates once at the end
    if videodata_path and videodata is not None and wrote_videodata:
        try:
            # Rebuild list to include updated dicts (defensive copy)
            updated_list = []
            for item in videodata:
                p = item.get(KEY_FILE)
                if p in path_to_entry:
                    updated_list.append(path_to_entry[p])
                else:
                    updated_list.append(item)
            _json_dump_atomic(updated_list, videodata_path)
            logger.info("Videodata updated with '%s': true flags.", KEY_FIXED)
        except Exception as e:
            logger.error("Failed to write updated videodata to %s: %s", videodata_path, e)
