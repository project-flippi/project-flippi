from ProcessComboTextFile import parse_jsonl, write_jsonl_atomic, append_jsonl, _parse_dt_loose
import os
import subprocess
import config
from config import KEY_FILE, KEY_FIXED, KEY_TITLE, KEY_DESC, KEY_USED, KEY_CLIPFILES, KEY_CLIPTITLES, KEY_TIMESTAMP, KEY_THUMBNAIL
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
        "Check out flippi.gg to register your tag and learn more about Project Flippi!"
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
            "-filter_complex",
            "[0:v]crop=1080:960:0:0[top];"
            "[0:v]crop=1080:960:0:960[bottom];"
            "[top][bottom]hstack=inputs=2[stacked];"
            "[stacked]scale=1920:852[scaled];"
            "[scaled]pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#5c3a21[out]",
            "-map", "[out]",
            "-map", "0:a?",
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

def generate_compilation_from_videodata(video_data):
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
    video_rows = parse_jsonl(video_data)  # Use the provided function
    selected_clips, updated_video_data = select_clips_for_compilation(video_rows)

    if selected_clips:
        compilation_path = create_compilation(selected_clips, output_path)
        if compilation_path:
            write_jsonl_atomic(video_data, updated_video_data)
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
