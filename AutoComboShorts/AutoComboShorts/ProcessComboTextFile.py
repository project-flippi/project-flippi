import re
import datetime
import json
import config
import os

from resources import stage_dict, character_dict, move_dict, character_movenames_dict
from AI_functions import provide_AI_title, provide_AI_desc

# Parse combo text file and returns a list of combos. Each combo is a dictionary with relevant information.
def parse_combos(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    combo_blocks = [block.strip() for block in data.split('Timestamp:') if block.strip()]
    combolist = []
    for block in combo_blocks:
        timestamp_match = re.match('(\\d{4}-\\d{2}-\\d{2} \\d{2}-\\d{2}-\\d{2})', block)
        timestamp = timestamp_match.group(1) if timestamp_match else None

        stage_match = re.search('StageID: (\\d+)', block)
        stage_id = json.loads(stage_match.group(1)) if stage_match else None

        players_match = re.search('Players: (\\[.*?\\])', block, re.DOTALL)
        players = json.loads(players_match.group(1)) if players_match else []

        moves_match = re.search('Moves: (\\[.*?\\])', block, re.DOTALL)
        moves = json.loads(moves_match.group(1)) if moves_match else []

        catcher_match = re.search('CatcherIndex: (\\d+)', block)
        catcher_index = int(catcher_match.group(1)) if catcher_match else None

        start_percent_match = re.search('StartPercent: ([\\d.]+)', block)
        start_percent = float(start_percent_match.group(1)) if start_percent_match else None

        end_percent_match = re.search('EndPercent: ([\\d.]+)', block)
        end_percent = float(end_percent_match.group(1)) if end_percent_match else None

        did_kill_match = re.search('DidKill: (true|false)', block, re.IGNORECASE)
        did_kill = did_kill_match.group(1).lower() == 'true' if did_kill_match else False

        combo = {
        'Timestamp': timestamp, 
        'StageID': stage_id, 
        'Players': players, 
        'CatcherIndex': catcher_index, 
        'StartPercent': start_percent, 
        'EndPercent': end_percent, 
        'Moves': moves, 
        'DidKill': did_kill}

        combolist.append(combo)
    return combolist

#Parse the videodata text file so it can be used in other functions. Videodata consists of Timestamp, File Path, Title, and Descripition.
def parse_videodata(file_path):
    """Parses a JSON file and returns a list of dictionaries. 
    If the file is missing, empty, or invalid, returns an empty list.
    """
    if not os.path.exists(file_path):  # Check if file exists
        print(f"Warning: {file_path} not found. Returning an empty list.")
        return []

    with open(file_path, "r", encoding="utf-8") as file:
        data = file.read().strip()  # Remove unnecessary whitespace

    if not data:  # Handle empty file case
        print(f"Warning: {file_path} is empty. Returning an empty list.")
        return []

    try:
        list_of_dicts = json.loads(data)
        if isinstance(list_of_dicts, list):  # Ensure it's a list
            return list_of_dicts
        else:
            print(f"Warning: {file_path} does not contain a valid list. Returning an empty list.")
            return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {file_path}: {e}. Returning an empty list.")
        return []

#Uses the combo data to generate a prompt. This prompt can be used to prompt an AI.
def write_title_prompt(combo):

    total_percent = int(round(combo['EndPercent'] - combo['StartPercent'], 0))
    PunishedPlayerInfo = next((d for d in combo['Players'] if d.get('playerIndex') == combo['CatcherIndex']), None)
    PunishedPlayerNameTag = PunishedPlayerInfo['displayName']
    PunishedPlayerCharacterId = PunishedPlayerInfo['characterId']
    PunishedPlayerCharacter = character_dict[str(PunishedPlayerCharacterId)]['name']
    if PunishedPlayerNameTag == '':
        PunishedPlayerNameTag = 'Player 2'
    AttackingPlayerInfo = next((d for d in combo['Players'] if d.get('playerIndex') != combo['CatcherIndex']), None)
    AttackingPlayerNameTag = AttackingPlayerInfo['displayName']
    AttackingPlayerCharacterId = AttackingPlayerInfo['characterId']
    AttackingPlayerCharacter = character_dict[str(AttackingPlayerCharacterId)]['name']
    move_sequence = ''
    for move in combo['Moves'][:-1]:
        move_sequence = move_sequence + character_movenames_dict[AttackingPlayerCharacter][str(move['moveId'])] + ', '
    LastMoveId = combo['Moves'][-1]['moveId']
    LastMove = character_movenames_dict[AttackingPlayerCharacter][str(LastMoveId)]
    prompt = 'On ' + stage_dict[str(combo['StageID'])] + ', ' + AttackingPlayerNameTag + "'s " + AttackingPlayerCharacter + ' punished ' + PunishedPlayerNameTag + "'s " + PunishedPlayerCharacter + ' for ' + str(total_percent) + '% with ' + move_sequence + 'and ended with a ' + LastMove + ' into the blast zone!'
    return prompt

#Used to find the replay file with the closest timestamp to the combo data for use in pairing
def find_closest_video_file(timestamp, video_folder_path, used_files, time_threshold=10):
    """Finds the closest video file within a given threshold (default: 30 seconds) and ensures it is not reused."""
    try:
        timestamp_dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H-%M-%S")  # Correct format
        
    except ValueError:
        print(f"Error: Timestamp format is incorrect: {timestamp}")
        return None

    closest_file = None
    closest_time_diff = float('inf')


    for filename in os.listdir(video_folder_path):
        if filename.startswith("Replay") and filename.endswith(".mp4") and filename not in used_files:
            try:
                file_timestamp_str = filename.replace("Replay ", "").replace(".mp4", "")
                file_timestamp_dt = datetime.datetime.strptime(file_timestamp_str, "%Y-%m-%d %H-%M-%S")  # Correct format
                time_diff = abs((file_timestamp_dt - timestamp_dt).total_seconds())
                

                if time_diff < closest_time_diff and time_diff <= time_threshold:
                    closest_time_diff = time_diff
                    closest_file = filename
            except ValueError:
                print("ValueError")
                continue  # Skip files that don't match the expected format

    if closest_file:
        used_files.add(closest_file)  # Mark file as used
        full_path = os.path.join(video_folder_path, closest_file)
        return full_path.replace("\\", "/")  # Convert Windows backslashes to forward slashes
    
    return None  # No valid file found

#Used to rename the video file to match the title as Youtube uses the file name in its algorithim 
def rename_video_file(original_file_path, title):
    """
    Renames the file at original_file_path to a new name based on the given title.
    Returns the new file path if successful; otherwise, returns the original file path.
    """
    # Remove any characters that aren't allowed in file names
    title = title.replace("'", "")
    title = title.replace(" ", "_")
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    safe_title = re.sub(r'[^a-zA-Z0-9._-]', '', safe_title)
    # Get the file extension (assuming it's .mp4)
    _, ext = os.path.splitext(original_file_path)
    new_file_name = f"{safe_title}{ext}"
    directory = os.path.dirname(original_file_path)
    new_file_path = os.path.join(directory, new_file_name)
    
    try:
        os.rename(original_file_path, new_file_path)
        print(f"Renamed video file from {original_file_path} to {new_file_path}")
    except Exception as e:
        print(f"Failed to rename file: {e}")
        return original_file_path
    new_file_path = new_file_path.replace("\\", "/")
    return new_file_path

#Function that parses both combo data and video data, updates video data file with any new combos and the data resulting from them (titles, desc, etc.)
def write_video_title_desc(combodata_file_path, videodata_file_path):
    combodatalist = parse_combos(combodata_file_path)
    videodatalist = parse_videodata(videodata_file_path)
    newvideodatalist = videodatalist[:]

    for combodata in combodatalist:
        # Check if there's a match before proceeding to avoid generating video data for combos that already have video data.
        if any(videodata.get('Timestamp') == combodata['Timestamp'] for videodata in videodatalist):
            continue  # Skip if a match is found

        newvideodata = {}
        newvideodata['Timestamp'] = combodata['Timestamp']
        newvideodata['File Path'] = None

        print("\nBananaBot developing a title!")
        prompt = write_title_prompt(combodata)
        response = provide_AI_title(prompt)
        title = response
        print('\n' + title)
        print("\n\nSubscribe for more monke...\n")
        title = title.strip("\"")
        desc = provide_AI_desc(title)
        desc = desc.strip("\"")

        newvideodata['Title'] = title 
        newvideodata['Descripition'] = prompt + '\n\n' + desc
        
        newvideodatalist.append(newvideodata)

    #If the new video data list is the same as the old video data list, that means there are no new combos.
    if newvideodatalist == videodatalist:
        print("No new combos.")
        
    else:
        with open(videodata_file_path, "w") as file:
            json.dump(newvideodatalist, file)

def write_video_titles(combodata_file_path, videodata_file_path):
    """Generates video titles and initializes descriptions as None."""
    combodatalist = parse_combos(combodata_file_path)
    videodatalist = parse_videodata(videodata_file_path)
    newvideodatalist = videodatalist[:]

    for combodata in combodatalist:
        # Skip if a video entry already exists
        if any(videodata.get('Timestamp') == combodata['Timestamp'] for videodata in videodatalist):
            continue

        newvideodata = {}
        newvideodata['Timestamp'] = combodata['Timestamp']
        newvideodata['File Path'] = None

        print("\nBananaBot developing a title!")
        prompt = write_title_prompt(combodata)
        title = provide_AI_title(prompt).strip("\"")
        print('\n' + title)
        print("\n\nSubscribe for more monke...\n")

        newvideodata['Title'] = title
        newvideodata['Prompt'] = prompt
        newvideodata['Descripition'] = None  # Initialize as None

        newvideodatalist.append(newvideodata)

    # Save updated video data
    if newvideodatalist != videodatalist:
        with open(videodata_file_path, "w") as file:
            json.dump(newvideodatalist, file)
        print("Titles updated. Descriptions pending.")
    else:
        print("No new titles generated.")

def write_video_descriptions(videodata_file_path):
    """Fills in descriptions for videos where Descripition is None."""
    videodatalist = parse_videodata(videodata_file_path)
    updated = False

    for videodata in videodatalist:
        if videodata.get('Descripition') is None:
            title = videodata['Title']
            print(f"\nGenerating description for: {title}")

            description = provide_AI_desc(title).strip("\"")

            # Check if 'Prompt' exists, otherwise use a default value
            prompt = videodata.get('Prompt', "")

            videodata['Descripition'] = "Come check out nouns.gg for more cool projects and opportunities!" +"\n\n" + prompt + "\n\n" + description
            updated = True

    # Save updated video data if any descriptions were generated
    if updated:
        with open(videodata_file_path, "w") as file:
            json.dump(videodatalist, file, indent=4)
        print("Descriptions added.")
    else:
        print("No missing descriptions found.")

def correct_video_data_structure(videodata_file_path):
    """
    Corrects the video data file by ensuring each entry has a 'Prompt' key 
    and resets 'Descripition' to None for proper processing in write_video_descriptions.
    """
    videodatalist = parse_videodata(videodata_file_path)
    updated = False

    for videodata in videodatalist:
        # If 'Prompt' is missing, assume existing 'Descripition' was the original prompt
        if 'Prompt' not in videodata:
            videodata['Prompt'] = videodata.get('Descripition', "")  # Preserve original text
            videodata['Descripition'] = None  # Reset description for regeneration
            updated = True

    # Save corrected video data if modifications were made
    if updated:
        with open(videodata_file_path, "w") as file:
            json.dump(videodatalist, file)
        print("Video data structure corrected. Ready for description generation.")
    else:
        print("No corrections needed. File structure is already correct.")            

#Adds the appropriate file path to the correct video data dictionary
def pair_videodata_with_videofiles(videodata_file_path, video_folder_path):
    videodatalist = parse_videodata(videodata_file_path)
    newvideodatalist = videodatalist[:]
    used_files = set() # Keep track of assigned video files

    for videodata in videodatalist:
        if videodata.get('File Path') is not None:
            continue # Skip if a file path is already assigned.

        file_path = find_closest_video_file(videodata['Timestamp'], video_folder_path, used_files, time_threshold=16)


        if file_path:
            # If a title exists, rename the file to match it.
            if videodata.get('Title'):
                file_path = rename_video_file(file_path, videodata['Title'])
            videodata["File Path"] = file_path  # Save the (renamed) file path
            print(f"File path paired to video data: {file_path}")

    # Save the updated videodata list
    with open(videodata_file_path, "w") as file:
        json.dump(newvideodatalist, file)
        print("Updated video file paths in videodata file.")





    

