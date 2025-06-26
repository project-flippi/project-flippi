from moviepy.editor import VideoFileClip, clips_array, concatenate_videoclips
from ProcessComboTextFile import parse_videodata
import os
import subprocess
import config
import random
import json
import datetime
from AI_functions import provide_AI_comptitle, provide_AI_desc, provide_image
import tempfile

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
            if clip.get("File Path") == file_path:
                titles.append(clip.get("Title", "Untitled"))
                break
    return titles

def update_compilation_data(clip_titles, output_path):
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
    Desc = "Come check out nouns.gg for more cool projects and opportunities!" +"\n\n" + Desc.strip("\"")

    #Create thumbnail
    thumbnail = provide_image(Title)
    if thumbnail is None:
        print("Thumbnail generation failed, using default placeholder.")
        thumbnail = config.THUMBNAILS_FOLDER / 'image.png'  # optional fallback

    thumbnail = str(thumbnail).replace("\\", "/").replace("'", "''")
    
    compilation_dict = {
        "File Path": escaped_path,  
        "Title": Title,
        "Descripition": Desc,
        "ClipTitles": clip_titles,
        "Thumbnail" : thumbnail
    }
    
    # Check if the COMP_DATA file exists and is non-empty
    if os.path.exists(config.COMP_DATA):
        try:
            with open(config.COMP_DATA, "r", encoding="utf-8") as file:
                comp_data = json.load(file)  # Try loading existing data
        except json.JSONDecodeError:
            print(f"Error reading {config.COMP_DATA}: File is empty or corrupted, starting fresh.")
            comp_data = []  # If the file is empty or corrupted, start with an empty list
    else:
        comp_data = []  # If the file doesn't exist, start with an empty list
    
    # Append the new compilation data
    comp_data.append(compilation_dict)
    
    # Write the updated data back to the file
    with open(config.COMP_DATA, "w", encoding="utf-8") as file:
        json.dump(comp_data, file, indent=4)  # Save with indentation for better readability
    print(f"Updated {config.COMP_DATA} with new compilation data.")

def select_clips_for_compilation(video_data, min_length=50, max_length=305):
    """
    Selects video clips sequentially until adding a clip would exceed max_length.
    Stops immediately once an overflow would happen.
    
    :param video_data: List of video metadata dictionaries.
    :param min_length: Minimum total duration for the compilation (in seconds).
    :param max_length: Maximum total duration for the compilation (in seconds).
    :return: List of selected video file paths and updated video metadata.
    """
    selected_clips = []
    total_duration = 0
    updated_video_data = video_data.copy()

    # Filter out unused clips
    unused_clips = [clip for clip in video_data if not clip.get("Used in Compilation", False) and clip.get("File Path")]

    if not unused_clips:
        print("No unused clips available.")
        return None, video_data

    # Sort clips from oldest to newest
    try:
        unused_clips.sort(key=lambda clip: datetime.datetime.strptime(clip["Timestamp"], "%Y-%m-%d %H-%M-%S"))
    except Exception as e:
        print(f"Error sorting clips by timestamp: {e}")
        return None, video_data

    for clip in unused_clips:
        file_path = clip["File Path"]

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
            print(f"Skipping {file_path}: Could not determine duration.")
            continue

        # If adding this clip would exceed max_length, stop immediately
        if total_duration + duration > max_length:
            print(f"Stopping: adding {file_path} ({duration:.2f}s) would exceed max_length.")
            break

        # Otherwise, add the clip
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
        print(f"Compilation too short: {total_duration:.2f}s (minimum required: {min_length}s).")
        return None, video_data

def select_clips_for_compilation_shuffle(video_data, min_length=300, max_length=330):
    """
    Selects video clips to create a compilation with a total duration between min_length and max_length.

    :param video_data: List of video metadata dictionaries.
    :param min_length: Minimum total duration for the compilation (in seconds).
    :param max_length: Maximum total duration for the compilation (in seconds).
    :return: List of selected video file paths and updated video metadata.
    """
    selected_clips = []
    total_duration = 0
    updated_video_data = video_data.copy()

    # Filter out clips already used in a compilation
    unused_clips = [clip for clip in video_data if not clip.get("Used in Compilation", False)]

    if not unused_clips:
        print("No unused clips available.")
        return None, video_data

    # Shuffle clips for random selection
    random.shuffle(unused_clips)

    for clip in unused_clips:
        file_path = clip["File Path"]

        # Get clip duration using ffprobe
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "format=duration", "-of",
                   "default=noprint_wrappers=1:nokey=1", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
        except Exception:
            print(f"Skipping {file_path}: Could not determine duration.")
            continue

        # Ensure the total compilation length stays within limits
        if total_duration + duration <= max_length:
            selected_clips.append((file_path, duration))
            total_duration += duration

            # Mark this clip as used in compilation
            for video_entry in updated_video_data:
                if video_entry["File Path"] == file_path:
                    video_entry["Used in Compilation"] = True

        if total_duration >= min_length:
            break  # Stop selecting clips if the minimum length is met

    return (selected_clips, updated_video_data) if total_duration >= min_length else (None, video_data)


def create_compilation_old(selected_clips, output_path):
    """
    Creates a video compilation from selected clips, ensuring paths are properly formatted for FFmpeg.

    :param selected_clips: List of (file_path, duration) tuples.
    :param output_path: Path to save the final compilation video.
    """
    if not selected_clips:
        print("No valid clips selected for compilation.")
        return None

    temp_list_file = "file_list.txt"

    with open(temp_list_file, "w", encoding="utf-8") as f:
        for file_path, _ in selected_clips:
            # Ensure file exists before adding it
            if not os.path.exists(file_path):
                print(f"Skipping {file_path}: File not found.")
                continue
            
            # Convert backslashes to forward slashes for FFmpeg compatibility
            formatted_path = file_path.replace("\\", "/")
            # Escape single quotes inside filenames by doubling them
            escaped_path = formatted_path.replace("'", "''")
            # Write to the file list using single quotes (correct format for FFmpeg concat)
            f.write(f"file '{escaped_path}'\n")

    # FFmpeg command to concatenate clips
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", temp_list_file, "-c", "copy", output_path, "-y"
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Compilation created: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating compilation: {e.stderr}")
        return None
    finally:
        os.remove(temp_list_file)  # Clean up temp file

    return output_path

def create_compilation(selected_clips, output_path):
    """
    Concatenates all input clips first (without re-encoding), then applies:
    - Horizontal split (top + bottom)
    - Scale to 1920x852
    - Pad to 1920x1080 with whiskey barrel brown
    """
    if not selected_clips:
        print("No valid clips selected for compilation.")
        return None

    temp_dir = tempfile.mkdtemp()
    temp_concat_list = os.path.join(temp_dir, "file_list.txt")
    temp_compilation = os.path.join(temp_dir, "raw_compilation.mp4")

    try:
        # Step 1: Create concat list
        with open(temp_concat_list, "w", encoding="utf-8") as f:
            for file_path, _ in selected_clips:
                if not os.path.exists(file_path):
                    print(f"Skipping {file_path}: File not found.")
                    continue
                formatted_path = file_path.replace("\\", "/").replace("'", "''")
                f.write(f"file '{formatted_path}'\n")

        # Step 2: Concatenate all raw clips (no re-encode)
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", temp_concat_list,
            "-c", "copy",
            temp_compilation
        ]
        subprocess.run(concat_cmd, check=True)
        print(f"Concatenated compilation saved at: {temp_compilation}")

        # Step 3: Process the single combined video
        process_cmd = [
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
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", "6M",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(process_cmd, check=True)
        print(f"Final processed compilation saved at: {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:
        print(f"Error during processing: {e.stderr}")
        return None

    finally:
        if os.path.exists(temp_concat_list):
            os.remove(temp_concat_list)
        if os.path.exists(temp_compilation):
            os.remove(temp_compilation)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

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
    video_data = parse_videodata(videodata_path)  # Use the provided function
    selected_clips, updated_video_data = select_clips_for_compilation(video_data)

    if selected_clips:
        compilation_path = create_compilation(selected_clips, output_path)
        if compilation_path:
            update_video_data(videodata_path, updated_video_data)
            print("Updated videodata.txt to mark used clips.")
            clip_titles = get_clip_titles_from_selected(selected_clips, updated_video_data)
            update_compilation_data(clip_titles, compilation_path)  # Update the COMP_DATA with compilation info
        return compilation_path
    else:
        print("Not enough valid unused clips to create a compilation.")
        return None

def update_video_data(file_path, updated_data):
    """
    Updates the videodata.txt file with new metadata (e.g., marking clips as used).

    :param file_path: Path to 'videodata.txt'.
    :param updated_data: List of updated video metadata dictionaries.
    """
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(updated_data, file)  # Save the list as a valid JSON array

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

def needs_metadata_fix(file_path):
    """
    Determines if an MP4 file from OBS needs remuxing for Windows Explorer compatibility.
    Skips files already fixed by this script (marked with 'fixed_by' metadata).

    :param file_path: Path to the MP4 file.
    :return: True if the file needs fixing, False otherwise.
    """
    import subprocess
    import re

    try:
        # Extract ffmetadata
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-f", "ffmetadata",
            "-"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        metadata = result.stdout + result.stderr
        print(metadata)
        
        # Skip if already fixed
        if re.search(r"fixed_by\s*=\s*metadata-fix-script", metadata, re.IGNORECASE):
            return False
        # Needs fix if tag not found
        return True
        
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
        return True

def fix_mp4_metadata_in_folder(folder_path):
    """
    Fixes MP4 metadata for all videos in a folder. Skips videos where metadata is already correct.

    :param folder_path: Path to the folder containing MP4 files.
    """
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".mp4"):
            file_path = os.path.join(folder_path, file_name)

            if not needs_metadata_fix(file_path):
                print(f"Skipping {file_name}: Metadata is already fixed.")
                continue

            output_path = fix_mp4_metadata(file_path)

            if output_path and output_path != file_path:
                os.replace(output_path, file_path)
                print(f"Replaced original file with fixed metadata version: {file_name}")



