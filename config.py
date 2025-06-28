# -*- coding: utf-8 -*-

import os
from pathlib import Path 
import sys

# Get the user's home directory

def get_event_name():
	"""Fetch the latest event name from the environment variable."""
	return os.environ.get("EVENT_NAME", "GoldenCactusWeeklies")  # Default if none is set

def get_event_folder():
    """Return the full event folder path based on the latest EVENT_NAME."""
    return PROJECT_FOLDER / "Event" / EVENT_NAME

HOME_DIR = Path.home()
PROJECT_FOLDER = HOME_DIR / "project-flippi"
EVENT_NAME = get_event_name()
EVENT_FOLDER = get_event_folder()
print(f"Using event folder: {EVENT_FOLDER}")

# Construct paths
EVENT_TITLE = EVENT_FOLDER / "data/event_title.txt"
VENUE_DESC = EVENT_FOLDER / "data/venue_desc.txt"
COMBO_DATA = EVENT_FOLDER / "data/combodata.txt"
DATA_FOLDER = EVENT_FOLDER / "data"
VIDEO_DATA = EVENT_FOLDER / "data/videodata.txt"
COMP_DATA = EVENT_FOLDER / "data/compdata.txt"
VIDEO_FOLDER = EVENT_FOLDER / "clips"
COMPS_FOLDER = EVENT_FOLDER / "compilations"
THUMBNAILS_FOLDER = EVENT_FOLDER / "thumbnails"
POSTED_VIDS_FILE = EVENT_FOLDER / "data/postedvids.txt"
TITLE_HISTORY_FILE = EVENT_FOLDER / "data/titlehistory.txt"
SHORTS_IMAGES_PATH = EVENT_FOLDER / "images"
SHORTS_IMAGES_GEN_PATH = EVENT_FOLDER / "images_gen"


# Constants that don’t change
YOUTUBE_TAGS = ("Super Smash Bros, Super Smash Melee, gaming, Nintendo, eSports, viral, viral shorts, for you")
YOUTUBE_HASHTAGS = (" #gaming #supersmashbros #melee")
OPEN_AI_API_KEY = PROJECT_FOLDER / "_keys" / 'open_AI_key.json'
CLIENT_SECRETS_FILE = PROJECT_FOLDER / "_keys" / 'client_secret.json'
CREDENTIALS_FILE = PROJECT_FOLDER / "_keys" / 'credentials.json'




