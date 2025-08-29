import re
import os
import json
import datetime
import logging
from typing import List, Dict, Any, Optional

import config
from resources import stage_dict, character_dict, move_dict, character_movenames_dict
from AI_functions import provide_AI_title, provide_AI_desc

logger = logging.getLogger(__name__)

# ----------------------------
# Field & timestamp constants
# ----------------------------
KEY_TIMESTAMP = "timestamp"
KEY_FILE      = "file path"
KEY_TITLE     = "title"
KEY_PROMPT    = "prompt"
KEY_DESC      = "description"  # keep current spelling for compatibility
KEY_TRIGGER   = "trigger"
KEY_SOURCE    = "source"
KEY_PHASE     = "phase"
KEY_ACTIVE    = "active"
KEY_EVENT     = "event"
KEY_COMBO     = "combo"
KEY_PLAYERS   = "players"
KEY_PLAYER_IN = "playerIndex"
KEY_START_PER = "startPercent"
KEY_CUR_PER   = "currentPercent"
KEY_END_PER   = "endPercent"
KEY_MOVES     = "moves"
KEY_MOVE_ID   = "moveId"
KEY_DID_KILL  = "didKill"
KEY_SETTINGS  = "settings"
KEY_STAGE_ID  = "stageId"
KEY_PORT      = "port"
KEY_CHAR_ID   = "characterId"
KEY_TAG       = "nametag"


# Combo text file timestamps may vary; we normalize new videodata timestamps to this:
TS_FMT = "%Y-%m-%d %H-%M-%S"  # matches "Replay YYYY-MM-DD HH-MM-SS.mp4"

# ----------------------------
# Small utilities
# ----------------------------
def parse_jsonl(path: str) -> List[Dict[str, Any]]:
    """Read a .jsonl file and return a list of dicts. Returns [] if file missing/empty."""
    if not os.path.exists(path):
        return []
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                items.append(json.loads(s))
            except json.JSONDecodeError as e:
                # Log and skip bad lines (don’t crash the whole run)
                print(f"[!] Skipping invalid JSON in {os.path.basename(path)}: {e}")
    return items

def append_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    """Append one JSON object per line to a .jsonl file, creating the file if needed."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def write_jsonl_atomic(path: str, rows: List[Dict[str, Any]]) -> None:
    """Rewrite an entire .jsonl file atomically."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _parse_dt_loose(ts_str: str) -> Optional[datetime.datetime]:
    """
    Parse a timestamp string from combodata blocks. We try common formats seen in the project.
    Returns None if parsing fails.
    """
    candidates = [
        "%Y-%m-%d %H-%M-%S",   # 2025-08-12 21-04-33
        "%Y-%m-%d %H:%M:%S",   # 2025-08-12 21:04:33
        "%Y/%m/%d %H:%M:%S",   # 2025/08/12 21:04:33 (just in case)
    ]
    for fmt in candidates:
        try:
            return datetime.datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue
    return None

def get_timestamp(combo: dict) -> str | None:
    try:
        return combo[KEY_TIMESTAMP]
    except (KeyError, TypeError):
        return None 

def get_trigger(combo: dict) -> str | None:
    try:
        return combo[KEY_TRIGGER]
    except (KeyError, TypeError):
        return None

def get_source(combo: dict) -> str | None:
    try:
        return combo[KEY_SOURCE]
    except (KeyError, TypeError):
        return None

def get_phase(combo: dict) -> str | None:
    try:
        return combo[KEY_PHASE]
    except (KeyError, TypeError):
        return None

def get_combo(combo: dict) -> dict | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO]
    except (KeyError, TypeError):
        return None

def get_start_percent(combo: dict) -> float | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_START_PER]
    except (KeyError, TypeError):
        return None

def get_current_percent(combo: dict) -> float | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_CUR_PER]
    except (KeyError, TypeError):
        return None

def get_end_percent(combo: dict) -> float | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_END_PER]
    except (KeyError, TypeError):
        return None

def get_defender_index(combo: dict) -> int | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_PLAYER_IN]
    except (KeyError, TypeError):
        return None

def get_moves(combo: dict) -> List[Dict[str, Any]] | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_MOVES]
    except (KeyError, TypeError):
        return None

def get_attacker_index(combo: dict) -> int | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_MOVES][0][KEY_PLAYER_IN]
    except (KeyError, TypeError):
        return None

def get_did_kill(combo: dict) -> bool | None:
    try:
        return combo[KEY_EVENT][KEY_COMBO][KEY_DID_KILL]
    except (KeyError, TypeError):
        return None

def get_stage_id(combo: dict) -> int | None:
    try:
        return combo[KEY_EVENT][KEY_SETTINGS][KEY_STAGE_ID]
    except (KeyError, TypeError):
        return None

def get_players(combo: dict) -> dict | None:
    try:
        return combo[KEY_EVENT][KEY_SETTINGS][KEY_PLAYERS]
    except (KeyError, TypeError):
        return None

def _find_player_by_index(players: List[Dict[str, Any]], idx: int) -> Optional[Dict[str, Any]]:
    for p in players or []:
        if p.get(KEY_PLAYER_IN) == idx:
            return p
    return None

def get_defender_char_id(combo: dict) -> int | None:
    try:
        defender_index=get_defender_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, defender_index)
        return p.get(KEY_CHAR_ID)
    except (KeyError, TypeError):
        return None

def get_defender_port(combo: dict) -> int | None:
    try:
        defender_index=get_defender_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, defender_index)
        return p.get(KEY_PORT)
    except (KeyError, TypeError):
        return None

def get_defender_nametag(combo: dict) -> int | None:
    try:
        defender_index=get_defender_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, defender_index)
        return p.get(KEY_TAG)
    except (KeyError, TypeError):
        return None

def get_attacker_char_id(combo: dict) -> int | None:
    try:
        attacker_index=get_attacker_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, attacker_index)
        return p.get(KEY_CHAR_ID)
    except (KeyError, TypeError):
        return None

def get_attacker_port(combo: dict) -> int | None:
    try:
        attacker_index=get_attacker_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, attacker_index)
        return p.get(KEY_PORT)
    except (KeyError, TypeError):
        return None

def get_attacker_nametag(combo: dict) -> int | None:
    try:
        attacker_index=get_attacker_index(combo)
        players=get_players(combo)
        p=_find_player_by_index(players, attacker_index)
        return p.get(KEY_TAG)
    except (KeyError, TypeError):
        return None

def get_character(index: int) -> str | None:
    try:
        return character_dict.get(str(index), {}).get('name', 'Unknown')
    except (KeyError, TypeError):
        return None

def get_stage_name(index: int) -> str | None:
    try:
        return stage_dict.get(str(index), "Unknown Stage")
    except (KeyError, TypeError):
        return None



# ----------------------------
# Prompt & title/desc writers
# ----------------------------
def write_title_prompt(combo: Dict[str, Any]) -> str:
    """
    Build a human-readable prompt from a parsed combo using resources mappings.
    """
    try:
        if get_end_percent(combo) is None:
            percent = get_current_percent(combo)
        else:
            percent = get_end_percent(combo)
        total_percent = int(round(percent - get_start_percent(combo), 0))

        punished_name = get_defender_nametag(combo) or "Player " + str(get_defender_port(combo))
        punished_char_id = get_defender_char_id(combo)
        punished_char = get_character(punished_char_id)

        attacker_name = get_attacker_nametag(combo) or "Player " + str(get_attacker_port(combo))
        attacker_char_id = get_attacker_char_id(combo)
        attacker_char = get_character(attacker_char_id)

        # Stage name
        stage_id = get_stage_id(combo)
        stage_name = get_stage_name(stage_id)

        #Did Ko
        did_KO = get_did_kill(combo)

        #what triggered clip
        trigger = get_trigger(combo)

        # Move sequence
        moves = get_moves(combo) or []
        seq_names = []
        for m in moves[:-1]:
            move_id = str(m.get("moveId"))
            seq_names.append(character_movenames_dict.get(attacker_char, {}).get(move_id, move_dict.get(move_id, "move")))
        last_move_id = str((moves[-1].get("moveId")) if moves else "")
        last_move = character_movenames_dict.get(attacker_char, {}).get(last_move_id, move_dict.get(last_move_id, "finish"))

        parts = [
            f"On {stage_name}, {attacker_name}'s {attacker_char} punished {punished_name}'s {punished_char}.",
            f"Damage dealt: ~{total_percent}%.",
        ]
        if seq_names:
            parts.append(f"Sequence: {', '.join(seq_names)} → Finisher: {last_move}.")
        else:
            parts.append(f"Finisher: {last_move}.")

        parts.append(f"Did KO: {did_KO}")
        parts.append(f"Trigger: {trigger}")

        return " ".join(parts)
    except Exception as e:
        logger.warning("Failed to build title prompt: %s", e)
        return "Hype Melee combo!"

def write_video_titles(combodata_file_path: str, videodata_file_path: str) -> None:
    """
    Generate AI titles for each combo not yet represented in videodata (.jsonl).
    Initializes descriptions as None and stores the raw Prompt used.
    Normalizes timestamp to TS_FMT for storage in videodata.
    """
    # Combos are already JSONL via your new parse_combos
    combos = parse_jsonl(combodata_file_path)

    # Videodata is now JSONL too
    video_rows = parse_jsonl(videodata_file_path)
    seen_ts = {v.get(KEY_TIMESTAMP) for v in video_rows if isinstance(v, dict)}

    new_entries: List[Dict[str, Any]] = []
    added = 0

    for c in combos:
        ts_raw = get_timestamp(c)
        if not ts_raw:
            continue
        if ts_raw in seen_ts:
            continue

        # Normalize timestamp for storage in videodata
        ts_dt = _parse_dt_loose(ts_raw)
        ts_norm = ts_dt.strftime(TS_FMT) if ts_dt else ts_raw

        prompt = write_title_prompt(c)
        title_resp = provide_AI_title(prompt)
        # guard against accidental wrapping quotes / whitespace
        title = (title_resp or "").strip('"')

        entry = {
            KEY_TIMESTAMP: ts_norm,
            KEY_FILE: None,
            KEY_TITLE: title,
            KEY_PROMPT: prompt,
            KEY_DESC: None,      # fill later
            KEY_TAG: get_attacker_nametag(c),
            KEY_STAGE_ID: get_stage_id(c),
            KEY_COMBO: get_combo(c)
        }

        new_entries.append(entry)
        added += 1
        # Prevent duplicates within the same run if multiple combos share ts_raw (unlikely but safe)
        seen_ts.add(ts_raw)

    if new_entries:
        append_jsonl(videodata_file_path, new_entries)
        logger.info("Titles updated: titles_created=%d file=%s", added, videodata_file_path)
    else:
        logger.info("No new titles generated.")

def write_video_descriptions(videodata_file_path: str) -> None:
    """
    Fill in descriptions where KEY_DESC is None (or missing) for a JSONL videodata file.
    Rewrites the JSONL file atomically after updates.
    """
    video_rows = parse_jsonl(videodata_file_path)
    if not video_rows:
        logger.info("No videodata found: %s", videodata_file_path)
        return

    updated = 0

    for v in video_rows:
        if not isinstance(v, dict):
            continue

        # Treat missing KEY_DESC or explicit None as needing a description
        if v.get(KEY_DESC) is None:
            title = (v.get(KEY_TITLE) or "").strip().strip('"')
            if not title:
                # If there's no title, skip generating to avoid junk prompts
                continue

            logger.info("Generating description for: %s", title)
            desc_model = (provide_AI_desc(title) or "").strip().strip('"')
            prompt = v.get(KEY_PROMPT, "") or ""

            v[KEY_DESC] = (
                "Check out flippi.gg to learn more about this project!"
                "\n\n" + prompt +
                ("\n\n" + desc_model if desc_model else "")
            )
            updated += 1

    if updated:
        write_jsonl_atomic(videodata_file_path, video_rows)
        logger.info(
            "Descriptions added: descriptions_filled=%d file=%s",
            updated, videodata_file_path
        )
    else:
        logger.info("No missing descriptions found.")

# ----------------------------
# Pairing logic
# ----------------------------
def find_closest_video_file(timestamp: str, video_folder_path: str, used_files: set, time_threshold: int = 10) -> Optional[str]:
    """
    Find the closest 'Replay YYYY-MM-DD HH-MM-SS.mp4' in video_folder_path within time_threshold seconds
    that has not already been assigned (tracked by used_files).
    """
    ts_dt = _parse_dt_loose(timestamp)
    if not ts_dt:
        logger.warning("Timestamp parse error for pairing: %s", timestamp)
        return None

    closest_file = None
    closest_diff = float('inf')

    try:
        for fname in os.listdir(video_folder_path):
            if not (fname.startswith("Replay") and fname.endswith(".mp4")):
                continue
            if fname in used_files:
                continue

            try:
                # expected exact format in filenames
                ts_str = fname.replace("Replay ", "").replace(".mp4", "")
                f_dt = datetime.datetime.strptime(ts_str, TS_FMT)
            except ValueError:
                # skip unexpected filenames
                continue

            diff = abs((f_dt - ts_dt).total_seconds())
            if diff < closest_diff and diff <= time_threshold:
                closest_diff = diff
                closest_file = fname
    except FileNotFoundError:
        logger.warning("Video folder not found: %s", video_folder_path)
        return None

    if closest_file:
        used_files.add(closest_file)
        full_path = os.path.join(video_folder_path, closest_file).replace("\\", "/")
        logger.info("Paired file %s (Δ=%.0fs)", full_path, closest_diff)
        return full_path

    logger.info("No video file within %ss for timestamp %s", time_threshold, timestamp)
    return None

def pair_videodata_with_videofiles(videodata_file_path: str, video_folder_path: str) -> None:
    """
    Match entries in videodata.jsonl with actual video files in a folder.
    Updates KEY_FILE for entries that don’t yet have a file path.
    Rewrites the JSONL file atomically after updates.
    """
    video_rows = parse_jsonl(videodata_file_path)
    if not video_rows:
        logger.info("No videodata found: %s", videodata_file_path)
        return

    used_files: set = set()
    paired = 0
    unmatched = 0

    for v in video_rows:
        if not isinstance(v, dict):
            continue
        if v.get(KEY_FILE):
            continue

        ts = v.get(KEY_TIMESTAMP, "")
        file_path = find_closest_video_file(ts, video_folder_path, used_files, time_threshold=16)
        if file_path:
            v[KEY_FILE] = file_path
            paired += 1
        else:
            unmatched += 1

    if paired > 0:
        write_jsonl_atomic(videodata_file_path, video_rows)
        logger.info(
            "Paired video files written: files_paired=%d unmatched=%d file=%s",
            paired, unmatched, videodata_file_path
        )
    else:
        logger.info("No updates to file paths. files_paired=%d unmatched=%d", paired, unmatched)