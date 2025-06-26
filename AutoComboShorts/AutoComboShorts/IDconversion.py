import os
import json
import csv

# --- Constants ---
BASE_CHARACTER_COUNT = 0x21  # 33
INTERNAL_SPECIAL_CHAR_COUNT = 6
EXTERNAL_SPECIAL_CHAR_COUNT = 7

INTERNAL_TO_EXTERNAL = [
    0x08, 0x02, 0x00, 0x01, 0x04, 0x05, 0x06,
    0x13, 0x0B, 0x0C, 0x0E, 0x20, 0x0D, 0x10,
    0x11, 0x0F, 0x0A, 0x07, 0x09, 0x12, 0x15,
    0x16, 0x14, 0x18, 0x03, 0x19, 0x17, 0x1A,
    0x1E, 0x1B, 0x1C, 0x1D, 0x1F
]

def to_external_id(internal_id, character_count):
    added_chars = character_count - BASE_CHARACTER_COUNT
    is_special = internal_id >= character_count - INTERNAL_SPECIAL_CHAR_COUNT

    if internal_id >= character_count - INTERNAL_SPECIAL_CHAR_COUNT - added_chars and not is_special:
        return (BASE_CHARACTER_COUNT - EXTERNAL_SPECIAL_CHAR_COUNT) + (internal_id - (BASE_CHARACTER_COUNT - INTERNAL_SPECIAL_CHAR_COUNT))

    external_id = internal_id - added_chars if is_special else internal_id

    if external_id < len(INTERNAL_TO_EXTERNAL):
        external_id = INTERNAL_TO_EXTERNAL[external_id]

    if is_special:
        external_id += added_chars

    if internal_id == 11:  # Popo special case
        return character_count - 1

    return external_id

# --- Paths ---
fighters_dir = "C:/Users/15613/Fighters"  # Update this
output_csv = "C:/Users/15613/BarrelOfNouns/fighter_id_mapping.csv"

# --- Load and process ---
fighter_files = [f for f in os.listdir(fighters_dir) if f.endswith(".json") and f[:3].isdigit()]
fighter_files.sort()
character_count = len(fighter_files)
entries = []

for filename in fighter_files:
    internal_id = int(filename[:3])
    with open(os.path.join(fighters_dir, filename), 'r') as file:
        data = json.load(file)
        name = data.get("name", "Unknown")
        external_id = to_external_id(internal_id, character_count)
        entries.append((external_id, internal_id, name))

# --- Sort by external ID ---
entries.sort(key=lambda x: x[0])

# --- Write to CSV ---
with open(output_csv, mode="w", newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["External ID", "Internal ID", "Name"])
    for external_id, internal_id, name in entries:
        writer.writerow([external_id, internal_id, name])

print(f"✅ Saved sorted mapping to {output_csv}")