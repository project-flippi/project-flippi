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
KEY_FILE      = "File Path"
KEY_TITLE     = "Title"
KEY_PROMPT    = "Prompt"
KEY_DESC      = "Descripition"  # keep current spelling for compatibility
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
def _json_dump_atomic(obj: Any, path: str) -> None:
    """Write JSON atomically to avoid partial writes."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4)
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
# Parsers
# ----------------------------

def parse_combos(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse the combo text file and return a list of combo dicts.
    Each block begins after 'Timestamp:' and contains fields parsed via regex.
    """
    if not os.path.exists(file_path):
        logger.warning("Combodata file not found: %s", file_path)
        return []

    with open(file_path, 'r', encoding="utf-8", errors="ignore") as file:
        data = file.read()

    combo_blocks = [block.strip() for block in data.split('Timestamp:') if block.strip()]
    combolist: List[Dict[str, Any]] = []

    for block in combo_blocks:
        # Timestamp (accept either HH-MM-SS or HH:MM:SS in input)
        ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}[-:]\d{2}[-:]\d{2})', block)
        timestamp_raw = ts_match.group(1) if ts_match else None
        ts_dt = _parse_dt_loose(timestamp_raw) if timestamp_raw else None

        # StageID
        stage_match = re.search(r'StageID:\s*(\d+)', block)
        stage_id = int(stage_match.group(1)) if stage_match else None

        # Players (JSON list)
        players_match = re.search(r'Players:\s*(\[[\s\S]*?\])', block)
        try:
            players = json.loads(players_match.group(1)) if players_match else []
        except Exception:
            players = []

        # CatcherIndex
        catcher_match = re.search(r'CatcherIndex:\s*(\d+)', block)
        catcher_index = int(catcher_match.group(1)) if catcher_match else None

        # Start/End percent
        start_match = re.search(r'StartPercent:\s*([\d.]+)', block)
        end_match   = re.search(r'EndPercent:\s*([\d.]+)', block)
        start_percent = float(start_match.group(1)) if start_match else 0.0
        end_percent   = float(end_match.group(1)) if end_match else 0.0

        # DidKill
        did_kill_match = re.search(r'DidKill:\s*(true|false)', block, re.IGNORECASE)
        did_kill = (did_kill_match.group(1).lower() == 'true') if did_kill_match else False

        # Moves (JSON list of objects with moveId, etc.) if present
        moves_match = re.search(r'Moves:\s*(\[[\s\S]*?\])', block)
        try:
            moves = json.loads(moves_match.group(1)) if moves_match else []
        except Exception:
            moves = []

        combo = {
            KEY_TIMESTAMP: timestamp_raw,            # keep original raw string for traceability
            "TimestampDT": ts_dt.isoformat() if ts_dt else None,  # helper for consumers
            "StageID": stage_id,
            "Players": players,
            "CatcherIndex": catcher_index,
            "StartPercent": start_percent,
            "EndPercent": end_percent,
            "DidKill": did_kill,
            "Moves": moves,
        }
        combolist.append(combo)

    logger.info("Parsed combos: count=%d from %s", len(combolist), file_path)
    return combolist

def parse_combos_new(file_path: str) -> List[Dict[str, Any]]:
    """
    Read a .jsonl file (one JSON object per line) and return a list of combo dicts.
    Assumes all keys are already in the expected format.
    """
    combos: List[Dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            combos.append(json.loads(line))
    return combos

def parse_videodata(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse videodata JSON into a list of dicts.
    Missing/empty/invalid files return [] (callers will rewrite as needed).
    """
    if not os.path.exists(file_path):
        logger.warning("Videodata not found: %s (returning empty list)", file_path)
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read().strip()

    if not data:
        logger.warning("Videodata empty: %s (returning empty list)", file_path)
        return []

    try:
        obj = json.loads(data)
        if isinstance(obj, list):
            return obj
        logger.warning("Videodata not a list: %s (returning empty list)", file_path)
        return []
    except json.JSONDecodeError as e:
        logger.warning("Error decoding videodata %s: %s (returning empty list)", file_path, e)
        return []

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
            parts.append(f"Sequence: {', '.join(seq_names)} → {last_move}.")
        else:
            parts.append(f"Finisher: {last_move}.")

        parts.append(f"Did KO: {did_KO}")
        parts.append(f"Trigger: {trigger}")

        return " ".join(parts)
    except Exception as e:
        logger.warning("Failed to build title prompt: %s", e)
        return "Hype Melee combo!"

"""def get_attacker_tag(combo: Dict[str, Any]) -> str:
   
    #get the attacker's name tag if one is being used, returns none if none is being used
    
    try:
        attacker = next((p for p in combo['Players'] if p.get('playerIndex') != combo['CatcherIndex']), None)
        attacker_tag = (attacker or {}).get('nametag') or None
        return attacker_tag
    except Exception as e:
        logger.warning("Failed to retrieve tag or return None")"""

def write_video_titles(combodata_file_path: str, videodata_file_path: str) -> None:
    """
    Generate AI titles for each combo not yet represented in videodata.
    Initialize descriptions as None and store the raw Prompt used.
    New entries will normalize Timestamp to TS_FMT.
    """
    combos = parse_combos(combodata_file_path)
    video = parse_videodata(videodata_file_path)
    newlist = video[:]

    added = 0
    seen_ts = {v.get(KEY_TIMESTAMP) for v in video}

    for c in combos:
        ts_raw = c.get(KEY_TIMESTAMP)
        if ts_raw in seen_ts:
            continue

        # Normalize timestamp for storage in videodata
        ts_dt = _parse_dt_loose(ts_raw) if ts_raw else None
        ts_norm = ts_dt.strftime(TS_FMT) if ts_dt else ts_raw or ""

        prompt = write_title_prompt(c)
        title_resp = provide_AI_title(prompt)
        title = (title_resp or "").strip('"')

        tag = get_attacker_tag(c)

        entry = {
            KEY_TIMESTAMP: ts_norm,
            KEY_FILE: None,
            KEY_TITLE: title,
            KEY_PROMPT: prompt,
            KEY_DESC: None,  # to be filled later
            KEY_TAG: tag,
        }
        newlist.append(entry)
        added += 1

    if newlist != video:
        _json_dump_atomic(newlist, videodata_file_path)
        logger.info("Titles updated: titles_created=%d file=%s", added, videodata_file_path)
    else:
        logger.info("No new titles generated.")

def write_video_descriptions(videodata_file_path: str) -> None:
    """
    Fill in descriptions where KEY_DESC is None using the stored title/prompt.
    """
    video = parse_videodata(videodata_file_path)
    updated = 0

    for v in video:
        if v.get(KEY_DESC) is None:
            title = v.get(KEY_TITLE) or ""
            logger.info("Generating description for: %s", title)
            desc = (provide_AI_desc(title) or "").strip('"')
            prompt = v.get(KEY_PROMPT, "")

            v[KEY_DESC] = (
                "Check out flippi.gg to learn more about this project!"
                "\n\n" + (prompt or "") +
                "\n\n" + desc
            )
            updated += 1

    if updated:
        _json_dump_atomic(video, videodata_file_path)
        logger.info("Descriptions added: descriptions_filled=%d file=%s", updated, videodata_file_path)
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
    video = parse_videodata(videodata_file_path)
    used_files: set = set()

    paired = 0
    unmatched = 0

    for v in video:
        if v.get(KEY_FILE):
            continue

        file_path = find_closest_video_file(v.get(KEY_TIMESTAMP, ""), video_folder_path, used_files, time_threshold=16)
        if file_path:
            v[KEY_FILE] = file_path
            paired += 1
        else:
            unmatched += 1

    if paired > 0:
        _json_dump_atomic(video, videodata_file_path)
        logger.info(
            "Paired video files written: files_paired=%d unmatched=%d file=%s",
            paired, unmatched, videodata_file_path
        )
    else:
        logger.info("No updates to file paths. files_paired=%d unmatched=%d", paired, unmatched)

# ----------------------------
# Maintenance helper (kept)
# ----------------------------
def correct_video_data_structure(videodata_file_path: str) -> None:
    """
    Ensure each entry has a KEY_PROMPT and reset KEY_DESC to None for proper regeneration if needed.
    """
    video = parse_videodata(videodata_file_path)
    changed = 0

    for v in video:
        if KEY_PROMPT not in v:
            v[KEY_PROMPT] = ""
            changed += 1
        # If you intend to force fresh descriptions, uncomment:
        # if KEY_DESC in v:
        #     v[KEY_DESC] = None
        #     changed += 1

    if changed:
        _json_dump_atomic(video, videodata_file_path)
        logger.info("correct_video_data_structure: entries_changed=%d file=%s", changed, videodata_file_path)
    else:
        logger.info("correct_video_data_structure: no changes needed.")

combos = parse_combos_new('C:/Users/15613/Desktop/combodata.jsonl')
combo = combos[0]

print(get_stage_id(combo))

print(write_title_prompt(combo))