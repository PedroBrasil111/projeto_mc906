import os
import json
from common import load_json
from api import make_request
from extract_features import extract_features

"""
The AMERICAS routing value serves NA, BR, LAN and LAS. The ASIA routing value serves KR and JP. The EUROPE routing value serves EUNE, EUW, ME1, TR and RU. The SEA routing value serves OCE, SG2, TW2 and VN2.
"""

MACRO_REGION = {"br1": "americas", "na1": "americas", "euw1": "europe", "eun1": "europe", "kr": "asia", "kr1":"asia", "jp1": "asia", "oc1": "americas", "la1": "americas", "la2": "americas", "ru": "europe", "tr1": "europe", "ph2": "asia", "tw2": "asia", "sg2": "asia", "vn2": "asia", "me1": "europe",}

def get_match_ids(puuid, region, step, count=20):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type=ranked&start={count*step}&count={count}"
    print("url is:")
    print(url)
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
    pg_path = os.path.join("matches"  , champion)
    timelines = [os.path.join(tl_path, fn) for fn in list(os.listdir(tl_path))]
    postgames = [os.path.join(pg_path, fn) for fn in list(os.listdir(pg_path))]
    for fn in timelines + postgames:
        os.remove(fn)

def main():
    champion_name = "Kaisa"
    champions = load_json("champions.json")
    champion_id = champions.get(champion_name, {}).get("id")

    if not champion_id:
        print(f"Champion {champion_name} not found in champions.json.")
        exit(1)
    else:
        print(f"Champion ID for {champion_name}: {champion_id}")

    #checked = extract_features(f"matches/{champion_name}", f"timelines/{champion_name}")
    delete_files(champion_name)

    player_info = load_json(f"player_info/{champion_name}_players.json")
    match_info = []
    total_matches = 0

    total_steps = 2
    step = 0
    count = 100 
    #variables used to get matches from player

    for step in range(total_steps):
        print(f"new step {str(step)}")
        for i, player in enumerate(player_info): # 5 APENAS PARA TESTE
            macro_region = MACRO_REGION[player['region']]
            match_ids = get_match_ids(player['puuid'], macro_region, step, count)
            if not match_ids:
                print(f"Found no matches for puuid {player['puuid']} in region {player['region']}.")
                continue

            print(f"Found {len(match_ids)} matches for puuid {player['puuid']} in region {player['region']}, from {str(step*count)} to {str((step+1)*count)}. Fetching details...")
            valid = 0
            for id in match_ids:
                '''
                if (os.path.exists(f"matches/{champion_name}/{id}_matches.json") and \
                        os.path.exists(f"timelines/{champion_name}/{id}_timeline.json")) or \
                        f"{id}_matches.json" in checked:
                    continue'''
                details = get_match_details(id, macro_region)
                if details and champion_in_match(details, champion_id):
                    timeline = get_match_timeline(id, macro_region)
                    write_match(champion_name, details, timeline)
                    valid += 1
            print(f"Found {valid} valid matches for puuid {player['puuid']} in region {player['region']}.")
            total_matches += valid
            if total_matches >= 50:
                print(f"Extracting features for {total_matches} games...")
                checked = extract_features(f"matches/{champion_name}", f"timelines/{champion_name}")
                delete_files(champion_name)
                total_matches = 0

if __name__ == '__main__':
    main()