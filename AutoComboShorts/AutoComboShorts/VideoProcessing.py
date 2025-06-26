from moviepy.editor import VideoFileClip, clips_array, concatenate_videoclips
from ProcessComboTextFile import parse_videodata
import cv2
import numpy as np
import os
import subprocess
import config
import random
import json
import re
import datetime
import tempfile

from moviepy.editor import *



def process_video_clip_ffmpeg1(video_path, processed_path, background_image_path=None):
    """
    Processes a portrait video using FFmpeg for speed.
    Assumes preprocessing has already been done.
    """
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", "scale=1920:853",  # Resize
        "-c:v", "libx264",
        "-preset", "fast",  # Use fast encoding for speed
        "-crf", "23",  # Lower is better quality
        "-c:a", "aac",
        "-b:a", "192k",
        processed_path
    ]
    subprocess.run(cmd, check=True)

def process_video_clip_ffmpeg(input_path, output_path):
    """
    Processes a portrait (1080x1920) video by splitting it into two halves,
    placing them side by side, resizing to 1920x853.33, and overlaying it
    onto a blurred 1920x1080 background using FFmpeg for faster processing.

    :param input_path: Path to the input video.
    :param output_path: Path to save the processed video.
    """
    # FFmpeg command for optimized speed and quality
    cmd = [
        "ffmpeg",
        "-i", input_path,  # Input video
        "-filter_complex",
        "[0:v]crop=1080:960:0:0[top];"  # Crop top half
        "[0:v]crop=1080:960:0:960[bottom];"  # Crop bottom half
        "[top][bottom]hstack=inputs=2[stacked];"  # Stack them side by side
        "[stacked]scale=1920:853[scaled];"  # Resize to 1920x853.33
        "[0:v]scale=1920:1080,boxblur=5:5[bg];"  # Create blurred background (lighter blur for speed)
        "[bg][scaled]overlay=(W-w)/2:(H-h)/2[out]",  # Overlay processed video on blurred background
        "-map", "[out]",  # Use the final processed stream
        "-map", "0:a:0",  # Keep original audio stream
        "-c:v", "libx264",  
        "-preset", "fast",  
        "-b:v", "6M",  # Increase bitrate to 6 Mbps for better quality
        "-c:a", "aac",  # Encode audio using AAC
        "-b:a", "192k",  # Set audio bitrate
        output_path  # Output file path
    ]

    subprocess.run(cmd, check=True)
    print(f"Processed video saved at: {output_path}")

def process_video_clip_ffmpeg_horiz(input_path, output_path):
    """
    Processes a portrait (1080x1920) video by splitting it into two halves,
    placing them side by side using FFmpeg. Removes scaling and background blur.

    :param input_path: Path to the input video.
    :param output_path: Path to save the processed video.
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,  # Input video
        "-filter_complex",
        "[0:v]crop=1080:960:0:0[top];"          # Crop top half
        "[0:v]crop=1080:960:0:960[bottom];"     # Crop bottom half
        "[top][bottom]hstack=inputs=2[out]",    # Stack them side by side
        "-map", "[out]",                        # Use the final video stream
        "-map", "0:a:0",                        # Keep original audio stream
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "6M",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"Processed video saved at: {output_path}")

def process_video_clip_ffmpeg_scale(input_path, output_path):
    """
    Rescales a 2160x960 video to 1920x853 using FFmpeg.

    :param input_path: Path to the input video.
    :param output_path: Path to save the processed video.
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "scale=1920:852",  # Rescale to 1920x853
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "6M",
        "-c:a", "aac",
        "-b:a", "192k",
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"Rescaled video saved at: {output_path}")

def process_video_clip_ffmpeg_background(input_path, output_path):
    """
    Pads a 1920x852 video to 1920x1080 with a whiskey barrel brown color.
    """
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-vf", "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#5c3a21",
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "6M",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"Padded video with whiskey barrel color saved at: {output_path}")

def process_video_clip_ffmpeg_combined(input_path, output_path):
    """
    Combines horizontal split, rescaling, and padding into a single function.
    - Input: 1080x1920 portrait video
    - Step 1: Horizontally stack top and bottom halves -> 2160x960
    - Step 2: Scale to 1920x852
    - Step 3: Pad to 1920x1080 with whiskey barrel color

    :param input_path: Path to the original portrait video.
    :param output_path: Final processed video path.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp1, \
         tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp2:
        horiz_path = tmp1.name
        scaled_path = tmp2.name

    try:
        # Step 1: Horizontal split
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter_complex",
            "[0:v]crop=1080:960:0:0[top];"
            "[0:v]crop=1080:960:0:960[bottom];"
            "[top][bottom]hstack=inputs=2[out]",
            "-map", "[out]",
            "-map", "0:a:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", "6M",
            "-c:a", "aac",
            "-b:a", "192k",
            horiz_path
        ], check=True)
        print(f"Step 1: Horizontally stacked video saved at {horiz_path}")

        # Step 2: Scale
        subprocess.run([
            "ffmpeg", "-y",
            "-i", horiz_path,
            "-vf", "scale=1920:852",
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", "6M",
            "-c:a", "aac",
            "-b:a", "192k",
            scaled_path
        ], check=True)
        print(f"Step 2: Scaled video saved at {scaled_path}")

        # Step 3: Pad
        subprocess.run([
            "ffmpeg", "-y",
            "-i", scaled_path,
            "-vf", "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:#5c3a21",
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", "6M",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            output_path
        ], check=True)
        print(f"Step 3: Final padded video saved at {output_path}")

    finally:
        # Clean up intermediate files
        os.remove(horiz_path)
        os.remove(scaled_path)

def compile_shorts_ffmpeg(video_paths, output_file):
    """
    Uses FFmpeg to concatenate preprocessed videos quickly.
    """
    if not video_paths:
        print("No videos to compile.")
        return

    # Create a temporary concat list file for FFmpeg
    concat_file = "concat_list.txt"
    with open(concat_file, "w") as f:
        for video in video_paths:
            f.write(f"file '{video}'\n")

    # Use FFmpeg to concatenate videos
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        output_file
    ]
    
    subprocess.run(cmd, check=True)
    os.remove(concat_file)  # Cleanup

    print(f"Compiled video saved at: {output_file}")

def add_blur_background(clip, background_image_path=None, target_width=1920, target_height=1080):
    """
    Creates a background using a custom image or blurs the first frame of the given clip.
    
    :param clip: The input video clip.
    :param background_image_path: Path to a custom background image (optional).
    :param target_width: Width of the output background.
    :param target_height: Height of the output background.
    :return: A MoviePy ImageSequenceClip of the background.
    """
    if background_image_path:
        try:
            # Load the custom background image
            background = cv2.imread(background_image_path)

            # Resize the image to match the target dimensions
            background = cv2.resize(background, (target_width, target_height))

            # Convert to RGB (cv2 loads in BGR format)
            background = cv2.cvtColor(background, cv2.COLOR_BGR2RGB)
            background = cv2.GaussianBlur(background, (99, 99), 30)

        except Exception as e:
            print(f"Error loading background image: {e}. Falling back to blurred video frame.")
            background_image_path = None  # Fallback to blurred frame

    if not background_image_path:
        # Use a blurred frame from the video if no image is provided
        frame = clip.get_frame(0)
        background = cv2.resize(frame, (target_width, target_height))
        background = cv2.GaussianBlur(background, (99, 99), 30)  # Strong blur effect

    # Convert to a MoviePy ImageClip
    background_clip = ImageClip(background, duration=clip.duration)
    background_clip = background_clip.set_fps(clip.fps)

    return background_clip


def get_shorts(download_folder="C:/Users/15613/Videos/TopShorts"):
    """
    Returns a list of downloaded shorts (video file paths) from the specified folder.
    The list is sorted by modification time in ascending order (oldest first).
    """
    # List all .mp4 files in the download folder
    file_paths = [os.path.join(download_folder, f) 
                  for f in os.listdir(download_folder) 
                  if f.lower().endswith(".mp4")]
    
    # Sort by modification time (oldest first) so that the least-viewed (downloaded earlier) come first.
    file_paths.sort(key=lambda path: os.path.getmtime(path))
    
    return file_paths

def process_video_clip(video_path, background_image_path=None):
    """
    Processes a portrait (1080x1920) video by splitting it into two halves,
    placing them side by side, resizing to 1920x853.33, and overlaying it
    onto a custom background or a blurred 1920x1080 background.
    """
    try:
        clip = VideoFileClip(video_path)
    except Exception as e:
        print(f"Error loading video {video_path}: {e}")
        return None

    # Allow slight variations in resolution due to encoding
    if not (1078 <= clip.w <= 1082 and 1918 <= clip.h <= 1922):
        print(f"Video {video_path} is not within the expected size range (w: {clip.w}, h: {clip.h}).")
        return None

    # Split the video into two horizontal halves (1080x960 each)
    top_half = clip.crop(x1=0, y1=0, width=1080, height=960)
    bottom_half = clip.crop(x1=0, y1=960, width=1080, height=960)

    # Arrange them side by side (Final size: 2160x960)
    side_by_side_clip = clips_array([[top_half, bottom_half]])

    # Resize to 1920x853.33 to maintain aspect ratio
    resized_side_by_side_clip = side_by_side_clip.resize(width=1920, height=853.33)

    # Create the background (either custom image or blurred video frame)
    background_clip = add_blur_background(clip, background_image_path, target_width=1920, target_height=1080)

    # Overlay the resized side-by-side video onto the background, centered
    final_output = CompositeVideoClip([background_clip, resized_side_by_side_clip.set_position(("center", "center"))])

    return final_output



def compile_shorts(video_paths, output_file, background_image_path=None):
    """
    Processes each video in video_paths, concatenates the processed clips into one final video,
    and writes the compiled video to output_file.
    """
    processed_clips = []
    for path in video_paths:
        print(f"Processing video: {path}")
        composite = process_video_clip(path, background_image_path)
        if composite:
            processed_clips.append(composite)
        else:
            print(f"Skipping video due to processing error: {path}")
    
    if not processed_clips:
        print("No videos were processed successfully.")
        return

    # Concatenate the processed clips in order (from least to most views)
    final_clip = concatenate_videoclips(processed_clips, method="compose")
    print(f"Writing compiled video to {output_file}")
    final_clip.write_videofile(output_file, codec="h264_nvenc", threads=8)
    final_clip.close()

def create_image_creation_video(image_path, duration=5, fps=30, steps=50, chunk_direction="vertical"):
    """
    Creates an MP4 video showing the step-by-step creation of an image in chunks.

    :param image_path: Path to the input image
    :param output_video_path: Path to save the output video
    :param duration: Total duration of the video in seconds
    :param fps: Frames per second for the video
    :param steps: Number of steps for the image reveal
    :param chunk_direction: Direction of chunking ("vertical" or "horizontal")
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Extract base name from image path and replace extension with .mp4
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_video_path = os.path.join(config.SHORTS_IMAGES_GEN_PATH, f"{base_name}.mp4")

    height, width, _ = img.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    total_frames = int(duration * fps)  # Ensure video duration matches
    frames_per_step = max(1, total_frames // steps)  # Frames per step
    chunk_size = (width // steps) if chunk_direction == "vertical" else (height // steps)  # Chunk size per step

    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    for i in range(steps + 1):
        frame = np.zeros_like(img)  # Start with a blank image

        if chunk_direction == "horizontal":
            frame[:, :min(i * chunk_size, width)] = img[:, :min(i * chunk_size, width)]  # Reveal left to right
        else:
            frame[:min(i * chunk_size, height), :] = img[:min(i * chunk_size, height), :]  # Reveal top to bottom

        # Write frames gradually to match total duration
        for _ in range(frames_per_step):
            out.write(frame)

    out.release()

def select_clips_for_compilation(video_data, min_length=120, max_length=180):
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


def create_compilation(selected_clips, output_path="compilation.mp4"):
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

def generate_compilation_from_videodata(videodata_path):
    """
    Full process to generate a compilation from videodata.txt.
    Updates videodata.txt to mark used clips and skips already used ones.

    :param videodata_path: Path to 'videodata.txt'.
    :param output_path: Path to save the final compilation video.
    """
    ct=str(datetime.datetime.now().replace(microsecond=0))
    ct=ct.replace(":","-")
    filename = ct + ".mp4" 
    output_path = config.COMPS_FOLDER / filename
    video_data = parse_videodata(videodata_path)  # Use the provided function
    selected_clips, updated_video_data = select_clips_for_compilation(video_data)

    if selected_clips:
        compilation_path = create_compilation(selected_clips, output_path)
        if compilation_path:
            update_video_data(videodata_path, updated_video_data)
            print("Updated videodata.txt to mark used clips.")
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
    Fixes metadata for an MP4 file by adding duration information using FFmpeg.

    :param input_path: Path to the original MP4 file.
    :param output_path: (Optional) Path to save the fixed MP4 file. If None, overwrites the input file.
    :return: Path to the fixed MP4 file.
    """
    
    # If no output path is specified, overwrite the original file
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_fixed{ext}"

    try:
        # FFmpeg command to fix metadata and move moov atom to the beginning
        cmd = [
            "ffmpeg",
            "-i", input_path,  # Input file
            "-c", "copy",  # Copy codec (no re-encoding)
            "-movflags", "+faststart",  # Move moov atom to the beginning
            output_path,
            "-y"  # Overwrite existing file without asking
        ]

        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Metadata fixed! New file saved at: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        print("Error processing the file:", e.stderr.decode())
        return None

def needs_metadata_fix(file_path):
    """
    Checks if an MP4 file is missing readable duration metadata by verifying if Windows Explorer can see it.

    :param file_path: Path to the MP4 file.
    :return: True if metadata needs fixing, False otherwise.
    """
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-select_streams", "v:0", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        duration = result.stdout.strip()
        
        # If duration is missing or zero, the file needs fixing
        if not duration or float(duration) <= 0:
            return True
        
        # Extra check: Use FFmpeg to fully rebuild metadata if Windows Explorer still doesn't read it
        cmd_metadata = [
            "ffmpeg",
            "-i", file_path,
            "-f", "ffmetadata", 
            "-"
        ]
        metadata_result = subprocess.run(cmd_metadata, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # If metadata extraction fails or does not contain duration, assume it needs fixing
        return "duration=" not in metadata_result.stdout.lower()

    except subprocess.CalledProcessError:
        return True  # Assume broken metadata if ffprobe fails

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

def process_green_screen(video_path, new_background_path, green_screen_region, output_path):
    """
    Processes a video clip by replacing a designated green screen region with a new background and saves the output.

    :param video_path: Path to the input video.
    :param new_background_path: Path to the new background image/video.
    :param green_screen_region: Tuple (x, y, width, height) defining the green screen area.
    :param output_path: Path to save the processed video.
    """
    clip = VideoFileClip(video_path)
    new_background = VideoFileClip(new_background_path).resize(clip.size)

    x, y, w, h = green_screen_region  # Extract green screen region dimensions

    # Function to replace green screen on each frame
    def apply_green_screen(frame):
        gs_region = frame[y:y+h, x:x+w]  # Extract green screen region
        hsv = cv2.cvtColor(gs_region, cv2.COLOR_RGB2HSV)

        # Define green screen color range (tweak for lighting conditions)
        lower_green = np.array([35, 80, 80])  
        upper_green = np.array([90, 255, 255])

        # Create mask for the green screen
        mask = cv2.inRange(hsv, lower_green, upper_green)
        mask_inv = cv2.bitwise_not(mask)

        # Extract foreground (non-green parts)
        foreground = cv2.bitwise_and(gs_region, gs_region, mask=mask_inv)

        # Resize background to match green screen region size
        bg_frame = new_background.get_frame(clip.reader.pos / clip.fps)
        bg_frame = cv2.resize(bg_frame, (w, h))

        # Apply mask to background
        new_background_region = cv2.bitwise_and(bg_frame, bg_frame, mask=mask)

        # Merge new background with foreground
        final_region = cv2.add(foreground, new_background_region)

        # Insert processed region back into original frame
        final_frame = frame.copy()
        final_frame[y:y+h, x:x+w] = final_region

        return final_frame

    # Apply frame-by-frame transformation using MoviePy
    processed_clip = clip.fl_image(apply_green_screen)

    # Save the processed video
    processed_clip.write_videofile(output_path, codec="libx264", threads=2)

    print(f"Processed green screen video saved at: {output_path}")

    return output_path

def sanitize_filename(filename):
    """
    Converts a filename into a format safe for FFmpeg.
    
    - Removes apostrophes (')
    - Replaces spaces with underscores (_)
    - Removes special characters except for underscores and dashes
    """
    filename = filename.replace("'", "")  # Remove apostrophes
    filename = filename.replace(" ", "_")  # Replace spaces with underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)  # Remove other special characters
    return filename

def update_json_references(json_file):
    """
    Updates file paths in the JSON-based video metadata file.
    :param json_file: Path to the JSON file (e.g., 'videodata.txt').
    """
    if not os.path.exists(json_file):
        print(f"File not found: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    updated = False
    for entry in data:
        if "File Path" in entry and entry["File Path"]:
            old_path = entry["File Path"]
            directory, filename = os.path.split(old_path)
            new_filename = sanitize_filename(filename)
            new_path = os.path.join(directory, new_filename)

            if old_path != new_path:
                entry["File Path"] = new_path
                updated = True
                print(f"Updated JSON path: {old_path} → {new_path}")

    if updated:
        with open(json_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
        print(f"Updated file paths in {json_file}")

def batch_rename_files(directory):
    """
    Renames all video files in the specified directory to a FFmpeg-safe format.

    :param directory: Path to the directory containing video files.
    :return: Dictionary mapping old filenames to new filenames.
    """
    renamed_files = {}

    for filename in os.listdir(directory):
        old_path = os.path.join(directory, filename)

        # Skip non-video files
        if not os.path.isfile(old_path) or not filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            continue

        new_filename = sanitize_filename(filename)
        new_path = os.path.join(directory, new_filename)

        # Rename the file only if the name changes
        if old_path != new_path:
            os.rename(old_path, new_path)
            renamed_files[old_path] = new_path
            print(f"Renamed: {old_path} -> {new_path}")

    return renamed_files

def update_text_file(text_file):
    """
    Updates file paths in a plain text file (e.g., 'postedvids.txt').
    :param text_file: Path to the text file.
    """
    if not os.path.exists(text_file):
        print(f"File not found: {text_file}")
        return

    with open(text_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    updated_lines = []
    updated = False
    for line in lines:
        old_path = line.strip()
        directory, filename = os.path.split(old_path)
        new_filename = sanitize_filename(filename)
        new_path = os.path.join(directory, new_filename)

        if old_path != new_path:
            updated_lines.append(new_path + "\n")
            updated = True
            print(f"Updated text file path: {old_path} → {new_path}")
        else:
            updated_lines.append(line)

    if updated:
        with open(text_file, "w", encoding="utf-8") as file:
            file.writelines(updated_lines)
        print(f"Updated file paths in {text_file}")

def batch_rename_and_update(directory, videodata_path, postedvids_path):
    """
    Full process:
    - Renames video files in a directory.
    - Updates file paths in 'videodata.txt' and 'postedvids.txt'.

    :param directory: Path to the directory containing video files.
    :param videodata_path: Path to the JSON-based video metadata file.
    :param postedvids_path: Path to the text-based posted videos list.
    """
    renamed_files = batch_rename_files(directory)
    update_json_references(videodata_path, renamed_files)
    update_text_file(postedvids_path, renamed_files)

def batch_update_metadata(videodata_path, postedvids_path):
    """
    Runs both update functions to fix metadata references.
    :param videodata_path: Path to videodata.txt.
    :param postedvids_path: Path to postedvids.txt.
    """
    update_json_references(videodata_path)
    update_text_file(postedvids_path)

def process_video_clip_and_save(video_path, output_path, background_image_path=None):
    """
    Processes a portrait (1080x1920) video by splitting it into two halves,
    placing them side by side, resizing to 1920x853.33, and overlaying it
    onto a custom background or a blurred 1920x1080 background.
    Saves the processed video to the specified output path.
    
    :param video_path: Path to the input video.
    :param output_path: Path to save the processed video.
    :param background_image_path: Path to a background image for overlay (optional).
    """
    try:
        clip = VideoFileClip(video_path)
    except Exception as e:
        print(f"Error loading video {video_path}: {e}")
        return

    # Allow slight variations in resolution due to encoding
    if not (1078 <= clip.w <= 1082 and 1918 <= clip.h <= 1922):
        print(f"Video {video_path} is not within the expected size range (w: {clip.w}, h: {clip.h}).")
        return

    # Split the video into two horizontal halves (1080x960 each)
    top_half = clip.crop(x1=0, y1=0, width=1080, height=960)
    bottom_half = clip.crop(x1=0, y1=960, width=1080, height=960)

    # Arrange them side by side (Final size: 2160x960)
    side_by_side_clip = clips_array([[top_half, bottom_half]])

    # Resize to 1920x853.33 to maintain aspect ratio
    resized_side_by_side_clip = side_by_side_clip.resize(width=1920, height=853.33)

    # Create the background (either custom image or blurred video frame)
    background_clip = add_blur_background(clip, background_image_path, target_width=1920, target_height=1080)

    # Overlay the resized side-by-side video onto the background, centered
    final_output = CompositeVideoClip([background_clip, resized_side_by_side_clip.set_position(("center", "center"))])

    # Save the processed video
    final_output.write_videofile(output_path, codec="h264_nvenc", preset="fast", threads=8, fps=clip.fps)

    print(f"Processed video saved at: {output_path}")

    # Close the clip to free resources
    clip.close()
    final_output.close()

#process_video_clip_ffmpeg_combined("C:/Users/15613/BarrelOfNouns/Event/GoldenCactusWeeklies/compilations/2025-03-27 11-30-00.mp4", "C:/Users/15613/BarrelOfNouns/Event/GoldenCactusWeeklies/compilations/2025-03-27 11-30-00_test4.mp4")

#reen_screen_coords = (56, 1050, 964, 726)
#image_path = "C:/Users/15613/Event/OtterFodder/images/Blast_&_Kick_Combo_Falco_Punishes_DK_on_Final_D!.png"
#video_path = "C:/Users/15613/Event/OtterFodder/clips/Blast & Kick Combo Falco Punishes DK on Final D!.mp4"
  # Could be an image or another video
#output_path = "C:/Users/15613/Event/OtterFodder/clipswithgen/Blast & Kick Combo Falco Punishes DK on Final D!.mp4"

#create_image_creation_video(image_path, duration=10, fps=30, steps=50, chunk_direction="vertical")

#new_background_path = "C:/Users/15613/Event/OtterFodder/images_gen/Blast_&_Kick_Combo_Falco_Punishes_DK_on_Final_D!.mp4"

#process_green_screen(video_path, new_background_path, green_screen_coords, output_path)

#compile_shorts_ffmpeg(get_shorts('C:/Users/15613/Videos/GoldenCactus/ClippiCombos'), 'C:/Users/15613/Videos/GoldenCactus/Compilations/20250303_2.mp4')
#process_video_clip_ffmpeg('C:/Users/15613/Videos/GoldenCactus/Test/test.mp4', 'C:/Users/15613/Videos/GoldenCactus/Test/test3.mp4')
#process_video_clip_and_save('C:/Users/15613/Videos/GoldenCactus/Compilations/20250303.mp4', 'C:/Users/15613/Videos/GoldenCactus/Compilations/20250303_2.mp4')

#generate_compilation_from_videodata(config.VIDEO_DATA)

#batch_update_metadata("C:/Users/15613/Event/GoldenCactusWeeklies/data/videodata.txt", "C:/Users/15613/Event/GoldenCactusWeeklies/data/postedvids.txt")