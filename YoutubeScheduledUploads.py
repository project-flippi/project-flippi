from ProcessComboTextFile import write_video_titles, write_video_descriptions, pair_videodata_with_videofiles
from VideoCompilation import generate_compilation_from_videodata, fix_mp4_metadata_in_folder
from YoutubeVideoUpload import get_authenticated_service, scheduled_upload_video, YoutubeArgs, set_thumbnails
import config
import time
import schedule
from pathlib import Path
import os
import importlib

EVENTS_BASE_DIR = Path.home() / "project-flippi" / "Event"

def get_event_list():
    """Get a list of subfolder names inside the event directory."""
    if not EVENTS_BASE_DIR.exists():
        print(f"Event directory '{EVENTS_BASE_DIR}' does not exist.")
        return []
    
    return [folder.name for folder in EVENTS_BASE_DIR.iterdir() if folder.is_dir()]

EVENT_LIST = get_event_list()
CURRENT_EVENT_INDEX = 0  # Track which event is active
event_name = EVENT_LIST[CURRENT_EVENT_INDEX]
os.environ["EVENT_NAME"] = event_name

youtube = get_authenticated_service()
video_args = YoutubeArgs()

def switch_to_next_event():
    """Rotate to the next event based on subfolder names."""
    global CURRENT_EVENT_INDEX, EVENT_LIST

    # Refresh the event list in case folders have changed
    EVENT_LIST = get_event_list()
    
    if not EVENT_LIST:
        print("No valid event folders found. Retrying in the next cycle...")
        return
    
    # Move to the next event (loop around if at the end)
    CURRENT_EVENT_INDEX = (CURRENT_EVENT_INDEX + 1) % len(EVENT_LIST)
    event_name = EVENT_LIST[CURRENT_EVENT_INDEX]
    os.environ["EVENT_NAME"] = event_name
    importlib.reload(config)  # Reload config with new event name
    print(f"Switched event to: {event_name}")

    

def process_and_upload_short():
    global youtube
    events_tried = 0
    total_events = len(EVENT_LIST)

    while events_tried < total_events:
        print(f"Processing and uploading short from event: {config.get_event_name()}")
        write_video_titles(config.COMBO_DATA, config.VIDEO_DATA)
        write_video_descriptions(config.VIDEO_DATA)
        pair_videodata_with_videofiles(config.VIDEO_DATA, config.VIDEO_FOLDER)

        try:
            video_uploaded = scheduled_upload_video(youtube, config.VIDEO_DATA, config.POSTED_VIDS_FILE, video_args)
        except Exception as e:
            if "invalid_grant" in str(e):
                print("Token expired. Re-authorising...")
                youtube = get_authenticated_service()
                continue
            else:
                raise

        if video_uploaded:
            return
        else:
            print("No unposted videos found. Switching to next event...")
            switch_to_next_event()
            events_tried += 1
    print("No videos uploaded across all events. Will try again next scheduled cycle.")


def process_and_upload_comp():
    global youtube
    events_tried = 0
    total_events = len(EVENT_LIST)
    while events_tried < total_events:
        print(f"Processing and uploading compilation from event: {config.get_event_name()}")
        write_video_titles(config.COMBO_DATA, config.VIDEO_DATA)
        write_video_descriptions(config.VIDEO_DATA)
        pair_videodata_with_videofiles(config.VIDEO_DATA, config.VIDEO_FOLDER)
        fix_mp4_metadata_in_folder(config.VIDEO_FOLDER)
        generate_compilation_from_videodata(config.VIDEO_DATA)

        try:
            video_uploaded = scheduled_upload_video(youtube, config.COMP_DATA, config.POSTED_VIDS_FILE, video_args)
        except Exception as e:
            if "invalid_grant" in str(e):
                print("Token expired. Re-authorising...")
                youtube = get_authenticated_service()
                continue
            else:
                raise
                
        if video_uploaded:
            set_thumbnails(youtube, config.COMP_DATA)
            return
        else:
            print("No unposted compilations found. Switching to next event...")
            switch_to_next_event()
            events_tried += 1
    print("No compilations uploaded across all events. Will try again next scheduled cycle.")



def run_schedule():
    schedule.every(1).days.at("12:00").do(switch_to_next_event)
    schedule.every(1).days.at("23:59").do(switch_to_next_event)
    schedule.every().monday.at("11:00").do(process_and_upload_short)
    #schedule.every().monday.at("22:00").do(process_and_upload_short)
    schedule.every().tuesday.at("11:00").do(process_and_upload_comp)
    #schedule.every().tuesday.at("22:00").do(process_and_upload_comp) 
    schedule.every().wednesday.at("11:00").do(process_and_upload_short) #noticed that shorts don't do well the morning after a comp post
    #schedule.every().wednesday.at("22:00").do(process_and_upload_short)
    schedule.every().thursday.at("11:00").do(process_and_upload_short)
    #schedule.every().thursday.at("22:00").do(process_and_upload_short)
    schedule.every().friday.at("11:00").do(process_and_upload_short)
    #schedule.every().friday.at("22:00").do(process_and_upload_short)
    schedule.every().saturday.at("11:00").do(process_and_upload_short)
    #schedule.every().saturday.at("22:00").do(process_and_upload_short)
    schedule.every().sunday.at("11:00").do(process_and_upload_short)
   # schedule.every().sunday.at("22:00").do(process_and_upload_short)

run_schedule()


while True:
	schedule.run_pending()
	time.sleep(1)


