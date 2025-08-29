from ProcessComboTextFile import write_video_titles, write_video_descriptions, pair_videodata_with_videofiles
from VideoCompilation import generate_compilation_from_videodata, fix_mp4_metadata_in_folder
from YoutubeVideoUpload import get_authenticated_service, scheduled_upload_video, YoutubeArgs, set_thumbnails
import config
import time
import schedule
from pathlib import Path
import os
import importlib
import logging
import sys

EVENTS_BASE_DIR = Path.home() / "project-flippi" / "Event"

# ---- scheduling constants (readability only) ----
ROTATE_TIMES = ["12:00"]
SHORT_SLOTS = {
    "monday":    ["11:00"],
    "wednesday": ["11:00"],  # you noted AM after comp is weaker; kept same as your file
    "thursday":  ["11:00"],
    "friday":    ["11:00"],
    "saturday":  ["11:00"],
    "sunday":    ["11:00"],
}
COMP_SLOTS = {
    "tuesday": ["11:45"],
}

def get_event_list():
    """Get a sorted list of subfolder names inside the event directory."""
    if not EVENTS_BASE_DIR.exists():
        logging.warning("Event directory '%s' does not exist.", EVENTS_BASE_DIR)
        return []
    return sorted([folder.name for folder in EVENTS_BASE_DIR.iterdir() if folder.is_dir()])

# Globals kept to minimize changes; they are initialized in main()
EVENT_LIST = []
CURRENT_EVENT_INDEX = 0
youtube = None
video_args = None

def set_active_event(event_name: str):
    """Set the active event via env and reload config (keeps your current pattern)."""
    config.set_event_name(event_name)
    logging.info("Switched event to: %s", event_name)

def switch_to_next_event():
    """Rotate to the next event based on subfolder names."""
    global CURRENT_EVENT_INDEX, EVENT_LIST

    EVENT_LIST = get_event_list()
    if not EVENT_LIST:
        logging.info("No valid event folders found. Retrying in the next cycle...")
        return

    # If current index is stale, reset
    if CURRENT_EVENT_INDEX >= len(EVENT_LIST):
        CURRENT_EVENT_INDEX = 0

    CURRENT_EVENT_INDEX = (CURRENT_EVENT_INDEX + 1) % len(EVENT_LIST)
    set_active_event(EVENT_LIST[CURRENT_EVENT_INDEX])

def _prep_videos_for_event():
    """Shared pre-upload prep for both short and comp."""
    write_video_titles(config.COMBO_DATA, config.VIDEO_DATA)
    write_video_descriptions(config.VIDEO_DATA)
    pair_videodata_with_videofiles(config.VIDEO_DATA, config.VIDEO_FOLDER)

def process_and_upload_short():
    global youtube, CURRENT_EVENT_INDEX, EVENT_LIST
    EVENT_LIST = get_event_list()
    if not EVENT_LIST:
        logging.info("No events to process for shorts.")
        return

    if CURRENT_EVENT_INDEX >= len(EVENT_LIST):
        CURRENT_EVENT_INDEX = 0

    events_tried = 0
    total_events = len(EVENT_LIST)

    while events_tried < total_events:
        event_name = EVENT_LIST[CURRENT_EVENT_INDEX]
        set_active_event(event_name)
        logging.info("Shorts: processing event %s", config.get_event_name())

        try:
            _prep_videos_for_event()
            video_uploaded = scheduled_upload_video(youtube, config.VIDEO_DATA, config.POSTED_VIDS_FILE, video_args)
        except Exception as e:
            msg = str(e)
            if "invalid_grant" in msg:
                logging.warning("Token expired. Re-authorising...")
                youtube = get_authenticated_service()
                # retry same event on next loop iteration
                continue
            logging.exception("Unexpected error during short upload; skipping this cycle.")
            return

        if video_uploaded:
            logging.info("Short uploaded successfully for %s", config.get_event_name())
            return
        else:
            logging.info("No unposted videos for %s. Switching to next event...", event_name)
            CURRENT_EVENT_INDEX = (CURRENT_EVENT_INDEX + 1) % len(EVENT_LIST)
            events_tried += 1

    logging.info("No videos uploaded across all events. Will try again next scheduled cycle.")

def process_and_upload_comp():
    global youtube, CURRENT_EVENT_INDEX, EVENT_LIST
    EVENT_LIST = get_event_list()
    if not EVENT_LIST:
        logging.info("No events to process for compilations.")
        return

    if CURRENT_EVENT_INDEX >= len(EVENT_LIST):
        CURRENT_EVENT_INDEX = 0

    events_tried = 0
    total_events = len(EVENT_LIST)

    while events_tried < total_events:
        event_name = EVENT_LIST[CURRENT_EVENT_INDEX]
        set_active_event(event_name)
        logging.info("Comps: processing event %s", config.get_event_name())

        try:
            _prep_videos_for_event()
            fix_mp4_metadata_in_folder(config.VIDEO_FOLDER, config.VIDEO_DATA)
            generate_compilation_from_videodata(config.VIDEO_DATA)
            video_uploaded = scheduled_upload_video(youtube, config.COMP_DATA, config.POSTED_VIDS_FILE, video_args)
        except Exception as e:
            msg = str(e)
            if "invalid_grant" in msg:
                logging.warning("Token expired. Re-authorising...")
                youtube = get_authenticated_service()
                continue
            logging.exception("Unexpected error during compilation upload; skipping this cycle.")
            return

        if video_uploaded:
            set_thumbnails(youtube, config.COMP_DATA)
            logging.info("Compilation uploaded successfully for %s", config.get_event_name())
            return
        else:
            logging.info("No unposted compilations for %s. Switching to next event...", event_name)
            CURRENT_EVENT_INDEX = (CURRENT_EVENT_INDEX + 1) % len(EVENT_LIST)
            events_tried += 1

    logging.info("No compilations uploaded across all events. Will try again next scheduled cycle.")

def run_schedule():
    for t in ROTATE_TIMES:
        schedule.every().day.at(t).do(switch_to_next_event)

    # shorts
    for day, times in SHORT_SLOTS.items():
        for t in times:
            getattr(schedule.every(), day).at(t).do(process_and_upload_short)

    # compilations
    for day, times in COMP_SLOTS.items():
        for t in times:
            getattr(schedule.every(), day).at(t).do(process_and_upload_comp)

def main():
    global youtube, video_args, EVENT_LIST, CURRENT_EVENT_INDEX

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    # Initialize runtime state
    EVENT_LIST = get_event_list()
    CURRENT_EVENT_INDEX = 0

    if EVENT_LIST:
        set_active_event(EVENT_LIST[CURRENT_EVENT_INDEX])
    else:
        logging.info("No events found at start; scheduler will retry later.")

    youtube = get_authenticated_service()
    video_args = YoutubeArgs()

    run_schedule()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down.")

if __name__ == "__main__":
    main()