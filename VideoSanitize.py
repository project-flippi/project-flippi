import os
import subprocess
import json
import re

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
    update_json_references(videodata_path)
    update_text_file(postedvids_path)

def batch_update_metadata(videodata_path, postedvids_path):
    """
    Runs both update functions to fix metadata references.
    :param videodata_path: Path to videodata.txt.
    :param postedvids_path: Path to postedvids.txt.
    """
    update_json_references(videodata_path)
    update_text_file(postedvids_path)