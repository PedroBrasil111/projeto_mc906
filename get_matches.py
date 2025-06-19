import os
import json
from common import load_json
from api import make_request
from extract_features import extract_features
from get_game_data import get_champion_data
import shutil

"""
The AMERICAS routing value serves NA, BR, LAN and LAS. The ASIA routing value serves KR and JP. The EUROPE routing value serves EUNE, EUW, ME1, TR and RU. The SEA routing value serves OCE, SG2, TW2 and VN2.
"""

MACRO_REGION = {"br1": "americas", "na1": "americas", "euw1": "europe", "eun1": "europe", "kr": "asia", "kr1":"asia", "jp1": "asia", "oc1": "americas", "la1": "americas", "la2": "americas", "ru": "europe", "tr1": "europe", "ph2": "asia", "tw2": "asia", "sg2": "asia", "vn2": "asia", "me1": "europe",}
VERSIONS = ["15.10", "15.11", "15.12"]

def get_match_ids(puuid, region, step, count=20):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type=ranked&start={count*step}&count={count}"
    response = make_request(url)
    if response.status_code != 200:
        return None
    return response.json()

def get_match_details(match_id, region):
    if os.path.exists(f"matches/{match_id}_matches.json"):
        return None
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    response = make_request(url)
    if response.status_code != 200:
        print(f"Error fetching match details for {match_id}: {response.status_code} - {response.text}")
        return None
    return response.json()

def get_match_timeline(match_id, region):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    response = make_request(url)
    if response.status_code != 200:
        print(f"Error fetching match timeline for {match_id}: {response.status_code} - {response.text}")
        return None
    return response.json()

def champion_in_match(match_details, champion_id):
    participants = match_details.get("info", {}).get("participants", [])
    for participant in participants:
        if participant.get("championId") == champion_id:
            return True
    return False

def write_matches_anterior(champion, match_details, match_timelines):
    os.makedirs(f"matches/{champion}", exist_ok=True)
    os.makedirs(f"timelines/{champion}", exist_ok=True)
    max_idx = 0
    for filename in os.listdir("matches"):
        if filename.startswith(champion) and filename.endswith("_matches.json"):
            if filename[len(champion):-13].isdigit():
                idx = int(filename[len(champion):-13])
                if idx > max_idx:
                    max_idx = idx
    file_path = f"matches/{champion}{max_idx + 1}_matches.json"
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(match_details, file, ensure_ascii=False, indent=4)

def write_match(champion, match_details, match_timeline):
    os.makedirs(f"matches/{champion}", exist_ok=True)
    os.makedirs(f"timelines/{champion}", exist_ok=True)
    match_id = match_details.get("metadata", {}).get("matchId", "unknown")

    match_file_path = f"matches/{champion}/{match_id}_matches.json"
    timeline_file_path = f"timelines/{champion}/{match_id}_timeline.json"

    with open(match_file_path, 'w', encoding='utf-8') as file:
        json.dump(match_details, file, ensure_ascii=False, indent=4)

    if match_timeline:
        with open(timeline_file_path, 'w', encoding='utf-8') as file:
            json.dump(match_timeline, file, ensure_ascii=False, indent=4)

def delete_files(champion):
    tl_path = os.path.join("timelines", champion)
    pg_path = os.path.join("matches", champion)
    backup = False
    if os.path.exists("backup") and os.path.isdir("backup"):
        os.makedirs(os.path.join("backup", pg_path), exist_ok=True)
        os.makedirs(os.path.join("backup", tl_path), exist_ok=True)
    timelines = [os.path.join(tl_path, fn) for fn in list(os.listdir(tl_path))]
    postgames = [os.path.join(pg_path, fn) for fn in list(os.listdir(pg_path))]
    for fn in timelines + postgames:
        if backup:
            shutil.move(fn, os.path.join("backup", fn))
        else:
            os.remove(fn)

def is_valid_match(match_details):
    info = match_details.get("info", {})
    # A team FF'd before 30 min
    if any([
            participant_info["teamEarlySurrendered"]
            for participant_info in info.get("participants", {})
           ]) and info.get("gameDuration") < 1800:
        print(f"Found a FF<30 match")
        return False
    # Map is not Summoners Rift
    if info.get("mapId", 0) != 11:
        print(f"Found a match not in Summoner's Rift")
        return False
    # Not current version
    if not any([info.get("gameVersion", "").startswith(version) for version in VERSIONS]):
        print(f"Found a match not on patches {VERSIONS}")
        return False
    # Not ranked
    if not info.get("queueId", 0) in [420, 440]:
        print("Found non-ranked game")
        return False
    return True

def main():
    champion_path = get_champion_data(clean=False)
    with open(champion_path, "r", encoding="UTF-8") as fp:
        champions = json.load(fp)
    all_champions = list(champions.keys())

    total_steps = 100
    start_step = 0
    count = 50
    last_time_valid = {}

    for step in range(start_step, total_steps + start_step):
        print(f"Current step: {step}")
        for player_origin in [folder for folder in os.listdir("player_info") if os.path.isdir(os.path.join("player_info", folder))]:
            print(f"Processing: {player_origin}")

            os.makedirs(f"matches/{player_origin}", exist_ok=True)
            os.makedirs(f"timelines/{player_origin}", exist_ok=True)

            with open("features/checked.json", "r") as fp:
                checked = json.load(fp)

            player_info = []
            for player_info_file in os.listdir(os.path.join("player_info", player_origin)):
                fp = os.path.join("player_info", player_origin, player_info_file)
                print(f"Using file {fp}")
                with open(fp, "r", encoding="UTF-8") as fp:
                    players = json.load(fp)
                    for p in players:
                        p["origin"] = f"{player_origin}/{player_info_file}"
                    player_info.extend(players)

            for i, player in enumerate(player_info):
                if player['puuid'] in last_time_valid:
                    if last_time_valid[player['puuid']] == 0:
                        continue

                macro_region = MACRO_REGION[player['region']]
                match_ids = get_match_ids(player['puuid'], macro_region, step, count)
                if not match_ids:
                    print(f"Found no matches for puuid {player['puuid']} in region {player['region']}.")
                    continue

                print(f"Found {len(match_ids)} matches for puuid {player['puuid']} in region {player['region']}, from {str(step*count)} to {str((step+1)*count)}. Fetching details...")
                valid = 0
                for id in match_ids:
                    if (os.path.exists(f"matches/{player_origin}/{id}_matches.json") and \
                            os.path.exists(f"timelines/{player_origin}/{id}_timeline.json")) or \
                            id in checked:
                        valid += 1
                        continue
                    details = get_match_details(id, macro_region)
                    if details and is_valid_match(details):
                        timeline = get_match_timeline(id, macro_region)
                        details["metadata"]["origin"] = p["origin"]
                        timeline["metadata"]["origin"] = p["origin"]
                        write_match(player_origin, details, timeline)
                        valid += 1
                print(f"Found {valid} valid matches for puuid {player['puuid']} in region {player['region']}.")
                last_time_valid[player['puuid']] = valid

                total_matches = len(os.listdir(f"timelines/{player_origin}"))
                print(f"Extracting features for {total_matches} games...")
                checked = extract_features(f"matches/{player_origin}", f"timelines/{player_origin}")
                delete_files(player_origin)

                with open(f"last.txt", "w+") as fp:
                    fp.write(f"{step}, {player['origin']}, {player['puuid']}")

if __name__ == '__main__':
    main()