from moviepy.editor import VideoFileClip, clips_array, concatenate_videoclips
import cv2
import numpy as np
import os
import subprocess
import config
import random
import json

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

#reen_screen_coords = (56, 1050, 964, 726)