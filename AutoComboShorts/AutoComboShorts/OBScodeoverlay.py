#purpose of this script is to use the console log as an OBS overlay
from ProcessComboTextFile import write_video_titles, pair_videodata_with_videofiles
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


import config
import time
import sys
import threading
import os


# Global flag to control animation state
stop_animation = False

class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global stop_animation
        if os.path.abspath(event.src_path) == os.path.abspath(config.COMBO_DATA):
            stop_animation = True  # Stop animation
            print("\rKO detected!              \n", end="", flush=True)  # Overwrite animation
            write_video_titles(config.COMBO_DATA, config.VIDEO_DATA)
            time.sleep(2)
            os.system('cls')
            stop_animation = False  # Resume animation

# Function to animate "Awaiting a Punish..."
def animate_loading():
    loading_states = ["BananaBot awaiting a KO.  ", "BananaBot awaiting a KO.. ", "BananaBot awaiting a KO..."]
    index = 0
    while True:
        if not stop_animation:  # Only update if animation is allowed
            print(f"\r{loading_states[index]}", end="", flush=True)
            index = (index + 1) % len(loading_states)  # Cycle through states
        time.sleep(0.5)  # Adjust speed

# Set up observer
path_to_watch = config.DATA_FOLDER
event_handler = FileChangeHandler()
observer = Observer()
observer.schedule(event_handler, path=path_to_watch, recursive=False)
observer.start()

os.system('cls')

# Start loading animation in a separate thread
animation_thread = threading.Thread(target=animate_loading, daemon=True)
animation_thread.start()

try:
    while True:
        time.sleep(1)  # Keep main thread alive
except KeyboardInterrupt:
    observer.stop()
    print("\nStopping observer...")
observer.join()