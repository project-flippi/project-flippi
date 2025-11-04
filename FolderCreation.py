from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

# --- Constants (repo layout assumptions) ---
REPO_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = REPO_ROOT / "_EventTemplate"
EVENTS_DIR = REPO_ROOT / "Event"
KEYS_DIR = REPO_ROOT / "_keys"

# Template expected structure (self-heal if missing)
TEMPLATE_SUBFOLDERS = [
    "data",
    "videos/clips",
    "videos/compilations",
    "images",
    "slp",
    "thumbnails",
]
TEMPLATE_DATA_FILES = [
    "combodata.jsonl",
    "compdata.jsonl",
    "event_title.txt",
    "postedvids.txt",
    "titlehistory.txt",
    "venue_desc.txt",
    "videodata.jsonl",
]

# Keys expected files (empty placeholders ok)
KEY_FILES = [
    "client_secret.json",
    "credentials.json",
    "open_AI_key.json",
]


def print_header():
    print("=" * 60)
    print("Project Flippi — Event Folder Creator")
    print("=" * 60)


def confirm(prompt: str) -> bool:
    while True:
        ans = input(f"{prompt} (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please type 'y' or 'n'.")


def sanitize_event_folder_name(raw_title: str) -> str:
    """
    Convert a user-entered title to TitleCase-With-Dashes and remove
    filesystem-unsafe characters. Keep letters/numbers; words joined by '-'.
    """
    # Split on any non-alphanumeric character to get "words"
    words = re.split(r"[^A-Za-z0-9]+", raw_title)
    words = [w for w in words if w]  # drop empties
    # TitleCase each word
    titled = [w[:1].upper() + w[1:].lower() if w else "" for w in words]
    # Join with dashes
    joined = "-".join(titled)
    # Remove anything not allowed (keep letters, numbers, dash)
    joined = re.sub(r"[^A-Za-z0-9\-]", "", joined)
    # Collapse multiple dashes
    joined = re.sub(r"-{2,}", "-", joined).strip("-")
    # Fallback if everything got stripped
    return joined or "Event"


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def ensure_file(path: Path):
    if not path.exists():
        path.touch()


def self_heal_template():
    """
    Ensure _EventTemplate exists and has the required structure.
    Does NOT overwrite existing files, only creates missing folders/files.
    """
    ensure_dir(TEMPLATE_DIR)
    for sub in TEMPLATE_SUBFOLDERS:
        ensure_dir(TEMPLATE_DIR / sub)
    data_dir = TEMPLATE_DIR / "data"
    for fname in TEMPLATE_DATA_FILES:
        ensure_file(data_dir / fname)


def ensure_keys_placeholders():
    ensure_dir(KEYS_DIR)
    created = []
    for kf in KEY_FILES:
        path = KEYS_DIR / kf
        if not path.exists():
            path.touch()
            created.append(kf)

    if created:
        print("\n⚠️  The following key files were created as empty placeholders:")
        for f in created:
            print(f"   - {f}")
        print("\n👉 You must populate these files for project-flippi to function:")
        print("   • client_secret.json  → Google API OAuth2 client secret for YouTube uploads")
        print("   • open_AI_key.json    → OpenAI API key for generating titles, descriptions, and thumbnails\n")


def ensure_repo_scaffold():
    """
    Make sure the repo has the expected top-level directories.
    """
    self_heal_template()
    ensure_dir(EVENTS_DIR)
    ensure_keys_placeholders()


def create_event_from_template(event_title_raw: str, venue_desc: str) -> Path | None:
    """
    Copy _EventTemplate to Event/<SanitizedTitle>,
    then fill data/event_title.txt & data/venue_desc.txt with user input.
    Returns the new event path on success, None on failure.
    """
    sanitized = sanitize_event_folder_name(event_title_raw)
    event_dest = EVENTS_DIR / sanitized

    if event_dest.exists():
        print(f"✖ An event folder already exists at: {event_dest}")
        print("   Choose a different title.")
        return None

    try:
        shutil.copytree(TEMPLATE_DIR, event_dest)
    except Exception as e:
        print(f"✖ Failed to copy template: {e}")
        return None

    # Write user-entered metadata verbatim
    try:
        data_dir = event_dest / "data"
        (data_dir / "event_title.txt").write_text(event_title_raw, encoding="utf-8")
        (data_dir / "venue_desc.txt").write_text(venue_desc or "", encoding="utf-8")
    except Exception as e:
        print(f"✖ Failed to write metadata files: {e}")
        return None

    print(f"✔ Created: {event_dest}")
    return event_dest


def main():
    print_header()
    # Ensure scaffold under the cloned repo
    ensure_repo_scaffold()

    if not confirm("Would you like to create a new event now?"):
        print("Okay—nothing to do. Bye!")
        sys.exit(0)

    while True:
        print("\nEnter details for your new event")
        event_title_raw = input("Event Title (as you'd like it displayed): ").strip()
        while not event_title_raw:
            print("Event title cannot be empty.")
            event_title_raw = input("Event Title: ").strip()

        venue_desc = input("Venue Description (will be used to generate thumbnails, don't mention copyrighted content): ").strip()
        while not venue_desc:
            print("Venue Description cannot be empty.")
            venue_desc = input("Venue Description: ").strip()

        created_path = create_event_from_template(event_title_raw, venue_desc)
        if created_path is not None:
            print(f"✅ Event folder ready at:\n   {created_path.resolve()}")

        if not confirm("\nCreate another event?"):
            print("All set. Go play some melee and have fun!")
            break


if __name__ == "__main__":
    main()