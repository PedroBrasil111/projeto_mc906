import os
import json
import wget
import requests
from argparse import ArgumentParser
from api import make_request

RANKED_QUEUES = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
RANKS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
REGION_MAPPING = {"BR": ["br1"], "NA": ["na1"], "OCE": ["oc1"], "EUNE": ["eun1"], "EUW": ["euw1"], "JP": ["jp1"], "KR": ["kr"], "LAN": ["la1", "la2"], "LAS": ["la1", "la2"], "RU": ["ru"], "TR": ["tr1"], "PH": ["ph2"], "TW": ["tw2"], "SG": ["sg2"], "VN": ["vn2"], "MENA": ["me1"], "TH": ["oc1"], "SEA": ["oc1", "sg2", "tw2", "vn2"]}

def get_champion_html(champion_name):
    filename = os.path.join("champions_html", f"best_{champion_name}.html")
    os.makedirs("champions_html", exist_ok=True)
    if os.path.exists(filename):
        return filename
    url = f'https://www.leagueofgraphs.com/rankings/summoners/{champion_name}'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(filename, "w+", encoding="utf-8") as f:
            f.write(response.text)
        print(f"\nChampion HTML downloaded: {filename}")
    else:
        print(f"\nCouldn't download from {url}")
    return filename

def get_champion_ids():
    if not os.path.exists("champions.json"):
        wget.download("https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json", out="champions.json")
    with open("champions.json", 'r', encoding='utf-8') as file:
        champions = json.load(file)
    champ_ids = {name.lower(): data['id'] for name, data in champions.items()}
    return champ_ids

def get_champion_names():
    if not os.path.exists("champions.json"):
        wget.download("https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json", out="champions.json")
    with open("champions.json", 'r', encoding='utf-8') as file:
        champions = json.load(file)
    champ_names = [name.lower() for name, data in champions.items()]
    return champ_names

def extract_from_html(html_file):
    players = []
    split_str = '<span class="name">'
    region_str = '<i>'
    with open(html_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    for line in lines:
        if split_str in line:
            l = line.strip().split(split_str)[1]
            id_start = 0
            id_end = l.find('<')
            player_info = l[id_start:id_end].split('#')
            if len(player_info) != 2:
                continue
        elif region_str in line:
            l = line.strip().split(region_str)[1]
            region = l[:l.find("</i>")]
            players.append({
                'gameName': player_info[0],
                'tagLine': player_info[1],
                'region': REGION_MAPPING[region],
            })
    print(f"Total players extracted: {len(players)}")
    return players

def puuid_request(gameName, tagLine):
    gameName = requests.utils.quote(gameName, safe='')
    tagLine = requests.utils.quote(tagLine, safe='')
    url = f"https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    response = make_request(url)
    if response.status_code != 200:
        return None
    return response.json()

def get_puuids(players):
    not_found = []
    for i, p in enumerate(players):
        response = puuid_request(p['gameName'], p['tagLine'])
        if response:
            players[i]['puuid'] = response.get('puuid')
        else:
            not_found.append(i)
    for i in reversed(not_found):
        players.pop(i)
    print(f"Total PUUIDS found: {len(players)}")
    return players

def rank_request(puuid, region):
    url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    response = make_request(url)
    if response.status_code != 200:
        return None
    ranked_queues_info = {}
    for entry in response.json():
        queue_type = entry.get('queueType')
        if queue_type in RANKED_QUEUES:
            tier = entry.get('tier')
            rank = entry.get('rank')
            if tier and rank:
                ranked_queues_info[queue_type] = {
                    'tier': tier,
                    'rank': rank,
                }
    if ranked_queues_info:
        for queue in RANKED_QUEUES:
            return ranked_queues_info.get(queue, None)
    return {
        'tier': None,
        'rank': None,
    }

def get_ranked_info(infos: list[dict]):
    not_found = []
    for i, info in enumerate(infos):
        puuid = info.get('puuid')
        regions = info.get('region', [])
        if not regions:
            not_found.append(i)
        for region in regions:
            rank_info = rank_request(puuid, region)
            if rank_info:
                info['region'] = region
                info['tier'] = rank_info.get('tier')
                info['rank'] = rank_info.get('rank')
                break
            else:
                info['region'] = region
                info['tier'] = None
                info['rank'] = None
    for i in reversed(not_found):
        infos.pop(i)
    print(f"Total ranked info found: {len(infos)}")
    return infos

def write_to_json(infos, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(infos, file, ensure_ascii=False, indent=4)
    print(f"Data written to {output_file}")

def main(args):
    champ_names = get_champion_names()
    query_champions = [
                 c.replace("'", "").lower() for c in args.champion
                ] if args.champion else champ_names
    if args.clean:
        print("Cleaning existing player info files...")
        for champion in query_champions:
            file_path = f"player_info/{champion}_players.json"
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed {file_path}")
    for champion in query_champions:
        if os.path.exists(f"player_info/best_{champion}_players.json"):
            print(f"Skipping {champion} (ID: {champion}), already processed.")
            continue
        print(f"Processing champion: {champion}")
        html_file = get_champion_html(champion)
        players = extract_from_html(html_file)
        print(f"Extracting PUUIDs")
        infos = get_puuids(players)
        print(f"Extracting ranked info")
        infos = get_ranked_info(infos)
        write_to_json(infos, f"player_info/best_{champion}_players.json")
        print()
        os.remove(html_file)

if __name__ == "__main__":
    parser = ArgumentParser(description="Get player information for specific champions.")
    parser.add_argument('--champion', type=str, nargs='+', help='List of champion names to process (default: all)')
    parser.add_argument('--clean', action='store_true', help='Make a clean run, removing existing player info files')
    args = parser.parse_args()
    main(args)