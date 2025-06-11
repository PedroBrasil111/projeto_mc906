import os
import json
import wget
import requests
import time
from dotenv import load_dotenv
from argparse import ArgumentParser

load_dotenv()  # .env

API_KEY = os.getenv("RIOT_API_KEY")

RANKED_QUEUES = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
RANKS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
REGION_MAPPING = {"BR": ["br1"], "NA": ["na1"], "OCE": ["oc1"], "EUNE": ["eun1"], "EUW": ["euw1"], "JP": ["jp1"], "KR": ["kr"], "LAN": ["la1", "la2"], "LAS": ["la1", "la2"], "RU": ["ru"], "TR": ["tr1"], "PH": ["ph2"], "TW": ["tw2"], "SG": ["sg2"], "VN": ["vn2"], "MENA": ["me1"],}

TIME_SINCE_BREAK = time.time()
REQ_SINCE_BREAK = 0
REQ_LIMIT = 100
REQ_TIME_LIMIT = 120

def make_request(url):
    url += f"?api_key={API_KEY}"
    response = requests.get(url)
    global TIME_SINCE_BREAK, REQ_SINCE_BREAK, REQ_LIMIT, REQ_TIME_LIMIT
    REQ_SINCE_BREAK += 1
    cond1 = REQ_SINCE_BREAK >= REQ_LIMIT
    cond2 = response.status_code == 429
    if cond1 or cond2:
        elapsed_time = time.time() - TIME_SINCE_BREAK
        if elapsed_time < REQ_TIME_LIMIT:
            sleep_time = REQ_TIME_LIMIT - elapsed_time if cond1 else 120
            print(f"\033[93mRate limit reached ({'cond1' if cond1 else 'cond2'}). Sleeping for {sleep_time:.2f} seconds.\033[0m")
            time.sleep(sleep_time)
        TIME_SINCE_BREAK = time.time()
        REQ_SINCE_BREAK = 0
    if cond2:
        response = requests.get(url)  # Retry after waiting
    return response

def get_champion_html(champion_id, name):
    filename = f"champions_html/{name}.html"
    if not os.path.exists("champions_html"):
        os.makedirs("champions_html")
    if os.path.exists(filename):
        return filename
    url = f'https://championmastery.gg/champion?champion={champion_id}'
    filename = wget.download(url, out=filename)
    print(f"\nChampion HTML downloaded: {filename}")
    return filename

def get_champion_ids():
    split_str = 'class=\"champion well\"'
    champions = []
    ret = {}
    if not os.path.exists("champions_html"):
        os.makedirs("champions_html")
    filename = "champions_html/index.html"
    if os.path.exists(filename):
        os.remove(filename)
    index = wget.download('https://championmastery.gg/', out=filename)
    with open(index, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            if not split_str in line:
                continue
            line = line.strip().split(split_str)
            for l in line:
                id = l[l.find('/champion?champion=') + 19:l.find('\" aria-label')]
                try:
                    id = int(id)
                    assert id > 0
                except:
                    continue
                name = l[l.find('aria-label=') + 12:l.find('Highscores') - 1]
                name = name.replace("&#x27;", "'").replace("&amp;", "&").replace("&#x2F;", "/")
                champions.append({
                    'id': id,
                    'name': name
                })
                ret[name] = id
    with open("champions.json", 'w', encoding='utf-8') as file:
        json.dump(champions, file, ensure_ascii=False, indent=4)
    print(f"Total champions found: {len(champions)}")
    return ret

def extract_from_html(html_file):
    players = []
    with open(html_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    for line in lines:
        if 'summoner-lookup' in line:
            line = line.strip().split("region=")
            for l in line:
                region = l[:l.find('\"')]
                id_start = l.find('>') + 1
                id_end = l.find('<')
                player_info = l[id_start:id_end].split('#')
                if len(player_info) != 2:
                    continue
                players.append({
                    'gameName': player_info[0][:-1],
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
    champ_ids = get_champion_ids()
    #champions = list(champ_ids.keys())
    champions = args.champion if args.champion else list(champ_ids.keys())
    if args.clean:
        print("Cleaning existing player info files...")
        for champion in champions:
            file_path = f"player_info/{champion}_players.json"
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Removed {file_path}")
    ids = [champ_ids[champion] for champion in champions]
    for id, champion in zip(ids, champions):
        if os.path.exists(f"player_info/{champion}_players.json"):
            print(f"Skipping {champion} (ID: {id}), already processed.")
            continue
        print(f"Processing champion: {champion} (ID: {id})")
        html_file = get_champion_html(id, champion)
        players = extract_from_html(html_file)
        infos = get_puuids(players)
        infos = get_ranked_info(infos)
        write_to_json(infos, f"player_info/{champion}_players.json")
        print()
        os.remove(html_file)
    os.remove("champions_html/index.html")

if __name__ == "__main__":
    args = ArgumentParser(description="Get player information for specific champions.")
    args.add_argument('--champion', type=str, nargs='+', help='List of champion names to process (default: all)')
    args.add_argument('--clean', action='store_true', help='Make a clean run, removing existing player info files')
    main(args)