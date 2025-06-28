import os
from pathlib import Path
import shutil

# Define path
HOME_DIR = Path.home()
PROJECT_FOLDER = HOME_DIR / "project-flippi"

template_folder = PROJECT_FOLDER / "_template"
destination_root = PROJECT_FOLDER / "Event"
events_file = PROJECT_FOLDER / "Events.txt"

# Get user input for the new folder name
new_folder_name = input("Enter the new folder name: ").strip()

# Create the new folder path
new_folder_path = destination_root / new_folder_name

# Check if the folder already exists
if new_folder_path.exists():
    print(f"Error: The folder '{new_folder_name}' already exists!")
else:
    try:
        # Copy the entire template directory
        shutil.copytree(template_folder, new_folder_path)

        # Append the new folder name to Events.txt
        events_file.touch(exist_ok=True)  # Ensure Events.txt exists
        with events_file.open("a") as f:
            f.write(new_folder_name + "\n")

        print(f"Successfully created '{new_folder_name}' and added to Events.txt.")
    except Exception as e:
        print(f"Error: {e}")