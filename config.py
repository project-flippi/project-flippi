import os
from pathlib import Path
# import sys  # was unused

# ---- Static roots ----
HOME_DIR = Path.home()
PROJECT_FOLDER = HOME_DIR / "project-flippi"

def get_event_name():
    """Fetch the latest event name from the environment variable."""
    return os.environ.get("EVENT_NAME", "GoldenCactusWeeklies")  # Default if none is set

def _build_event_folder(event_name: str) -> Path:
    """Return the full event folder path based on the event name."""
    return PROJECT_FOLDER / "Event" / event_name

# ---- Module state (initialized once, can be updated via set_event_name) ----
EVENT_NAME = get_event_name()
EVENT_FOLDER = _build_event_folder(EVENT_NAME)

# Construct paths (backward-compatible names)
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

def set_event_name(event_name: str) -> None:
    """
    Re-point all config paths to a new event without reloading the module.
    Keeps backward-compatible module-level names.
    """
    global EVENT_NAME, EVENT_FOLDER
    global EVENT_TITLE, VENUE_DESC, COMBO_DATA, DATA_FOLDER
    global VIDEO_DATA, COMP_DATA, VIDEO_FOLDER, COMPS_FOLDER, THUMBNAILS_FOLDER
    global POSTED_VIDS_FILE, TITLE_HISTORY_FILE, SHORTS_IMAGES_PATH, SHORTS_IMAGES_GEN_PATH

    EVENT_NAME = event_name
    EVENT_FOLDER = _build_event_folder(EVENT_NAME)

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

def ensure_dirs() -> None:
    """Create expected directories if they don't exist (safe to call anytime)."""
    for p in [
        PROJECT_FOLDER, EVENT_FOLDER, DATA_FOLDER, VIDEO_FOLDER, COMPS_FOLDER,
        THUMBNAILS_FOLDER, SHORTS_IMAGES_PATH, SHORTS_IMAGES_GEN_PATH,
    ]:
        p.mkdir(parents=True, exist_ok=True)

def validate():
    """
    Return a list of missing files/dirs that callers may want to create or skip.
    Purely informational—no side effects.
    """
    missing = []
    for p in [
        EVENT_FOLDER, DATA_FOLDER, VIDEO_FOLDER, COMPS_FOLDER, THUMBNAILS_FOLDER,
        SHORTS_IMAGES_PATH, SHORTS_IMAGES_GEN_PATH,
        OPEN_AI_API_KEY, CLIENT_SECRETS_FILE, CREDENTIALS_FILE,
    ]:
        if not p.exists():
            missing.append(str(p))
    return missing