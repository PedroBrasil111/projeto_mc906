import os
import json
import wget
import requests
from argparse import ArgumentParser
from api import make_request
from get_game_data import get_champion_data

RANKED_QUEUES = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
ALL_SERVERS = ["br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "me1", "na1", "oc1", "ru", "sg2", "tr1", "tw2", "vn2"]
SERVER_MAPPING = {"BR": ["br1"], "NA": ["na1"], "OCE": ["oc1"], "EUNE": ["eun1"], "EUW": ["euw1"], "JP": ["jp1"], "KR": ["kr"], "LAN": ["la1", "la2"], "LAS": ["la1", "la2"], "RU": ["ru"], "TR": ["tr1"], "TW": ["tw2"], "SG": ["sg2"], "VN": ["vn2"], "MENA": ["me1"], "TH": ["oc1"], "SEA": ["oc1", "sg2", "tw2", "vn2"], "ME": ["me1"], "PH": ["oc1"]}
FETCHING_MODES = {"mono", "best", "rank"}
ALL_CHAMPIONS = {}
RANKS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]

def get_monochampions_html(champion_id, champion_name):
    os.makedirs("champions_html", exist_ok=True)
    filename = f"champions_html/mono_{champion_name}.html"
    if os.path.exists(filename):
        return filename
    url = f'https://championmastery.gg/champion?champion={champion_id}'
    filename = wget.download(url, out=filename)
    print(f"Champion HTML downloaded: {filename}")
    return filename

def get_best_players_html(champion_name):
    os.makedirs("champions_html", exist_ok=True)
    filepath = os.path.join("champions_html", f"best_{champion_name}.html")
    if os.path.exists(filepath):
        return filepath
    url = f'https://www.leagueofgraphs.com/rankings/summoners/{champion_name.lower()}'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        with open(filepath, "w+", encoding="utf-8") as f:
            f.write(response.text)
        print(f"\nChampion HTML downloaded: {filepath}")
    else:
        print(f"\nCouldn't download from {url}")
    return filepath

def load_champion_data():
    path = get_champion_data(clean=False)
    with open(path, 'r', encoding='utf-8') as file:
        champ_info = json.load(file)
        for champ_name in champ_info:
            ALL_CHAMPIONS[champ_name] = champ_info[champ_name]["id"]

def extract_best_players(html_file):
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
                'region': SERVER_MAPPING[region],
            })
    print(f"Total players extracted: {len(players)}")
    return players

def extract_monochampions(html_file):
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
                    'region': SERVER_MAPPING[region],
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

def get_puuids(name, tag):
    response = puuid_request(name, tag)
    if response:
        return response.get('puuid', None)
    return None

def entry_request(tier, server_region, queue="RANKED_SOLO_5x5", division="II"):
    url = f"https://{server_region}.api.riotgames.com/lol/league-exp/v4/entries/{queue}/{tier}/{division}"
    response = make_request(url)
    if response.status_code != 200:
        return None
    return response.json()

def rank_request(puuid, server_region):
    url = f"https://{server_region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
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
                    'matches': entry.get('wins') + entry.get('losses'),
                    'win_rate': entry.get('wins') / (entry.get('wins') + entry.get('losses')),
                }
    # Tries to return ranked info for SOLO, then FLEX
    if ranked_queues_info:
        for queue in RANKED_QUEUES:
            return ranked_queues_info.get(queue, None)
    return {
        'tier': None,
        'rank': None,
        'matches': 0
    }

def get_ranked_info(player_infos: list[dict], ammount):
    results = []
    for info in player_infos:
        puuid_response = puuid_request(info['gameName'], info['tagLine'])
        if not puuid_response:
            continue
        puuid = puuid_response.get('puuid')
        regions = info.get('region', [])
        for region in regions:
            rank_info = rank_request(puuid, region)
            # Take ranked info based on 1st region
            # Minimum 100 matches and 50% win rate
            if rank_info and rank_info.get('matches') >= 100 \
                    and rank_info.get('win_rate') > 0.5:
                results.append({
                    **rank_info,
                    'region': region,
                    'puuid': puuid
                })
                break # for region
        if len(results) >= ammount:
            break # for player
    print(f"Total ranked info found: {len(results)}")
    return results

def write_to_json(infos, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(infos, file, ensure_ascii=False, indent=4)
    print(f"Data written to {output_file}")

def save_results(results, folder, filename):
    folder_path = os.path.join('player_info', folder)
    os.makedirs(folder_path, exist_ok=True)
    out_path = os.path.join(folder_path, filename)
    write_to_json(results, out_path)

def get_monochampions(champion_name, champion_id, ammount=100):
    if os.path.exists(os.path.join('player_info', champion_name, "mono.json")):
        print(f"Monochampion file for {champion_name} already exists")
        return False
    print(f"Getting monochampions for {champion_name}")
    html_file = get_monochampions_html(champion_id, champion_name)
    players = extract_monochampions(html_file)
    players_ranked_info = get_ranked_info(players, ammount)
    save_results(players_ranked_info, champion_name, "mono.json")
    os.remove(html_file)
    return True

def get_best_players(champion_name, champion_id, ammount=100):
    if os.path.exists(os.path.join('player_info', champion_name, "best.json")):
        print(f"Best players file for {champion_name} already exists")
        return False
    print(f"Getting best players for {champion_name}")
    html_file = get_best_players_html(champion_name)
    players = extract_best_players(html_file)
    players_ranked_info = get_ranked_info(players, ammount)
    save_results(players_ranked_info, champion_name, "best.json")
    os.remove(html_file)
    return True

def get_rank_players(rank, ammount=100):
    if os.path.exists(os.path.join('player_info', rank, "players.json")):
        print(f"Players file for {rank} rank already exists")
        return False
    print(f"Getting players for {rank} rank")
    players = []
    per_server_limit = ammount / len(ALL_SERVERS)
    per_server_limit = per_server_limit if per_server_limit > 1 else 1
    for server in ALL_SERVERS:
        count = 0
        info = entry_request(rank, server)
        if not info:
            continue
        for player in info:
            wins = player.get("wins")
            losses = player.get("losses")
            matches = wins + losses
            if matches >= 100 and wins / matches >= 0.5:
                count += 1
                players.append({
                    "tier": player.get("tier"),
                    "rank": player.get("rank"),
                    "matches": matches,
                    "win_rate": wins / matches,
                    "region": server,
                    "puuid": player.get("puuid")
                })
            if count >= per_server_limit:
                break
    save_results(players, rank, "players.json")
    return True

def main(args):
    mode_functs = {
        "best": get_best_players,
        "mono": get_monochampions,
    }
    for champ_name in args.champions:
        for mode, funct in mode_functs.items():
            if mode not in args.modes:
                continue
            funct_args = {
                "champion_name": champ_name,
                "champion_id": ALL_CHAMPIONS[champ_name],
                "ammount": args.n,
            }
            if funct(**funct_args):
                print("\033[92mDONE\033[0m\n")
    if "rank" in args.modes:
        for rank in args.ranks:
            if get_rank_players(rank, args.n):
                print("\033[92mDONE\033[0m\n")

def handle_args(args):
    if args.modes:
        args.modes = [m.lower() for m in args.modes]
        for m in args.modes:
            if m not in FETCHING_MODES:
                print(f"Invalid mode: {m}")
                exit(1)
    else:
        args.modes = FETCHING_MODES
    if args.champions:
        args.champions = [c.lower().capitalize() for c in args.champions]
        for c in args.champions:
            if c not in ALL_CHAMPIONS:
                print(f"Invalid champion: {c}")
                exit(1)
    else:
        args.champions = list(ALL_CHAMPIONS.keys())
    if args.ranks:
        args.ranks = [r.upper() for r in args.ranks]
        for r in args.ranks:
            if r not in RANKS:
                print(f"Invalid rank: {r}")
    else:
        args.ranks = RANKS
    if not args.n:
        args.n = 100
    if args.clean:
        print(f"Cleaning existing files")
        for mode in args.modes:
            for champ_name in args.champions:
                path = os.path.join('player_info', champ_name, mode + '.json')
                if os.path.exists(path):
                    os.chmod(path, 0o777)
                    os.remove(path)
        if "rank" in args.modes:
            for rank in args.ranks:
                path = os.path.join('player_info', rank, 'players.json')
                if os.path.exists(path):
                    os.chmod(path, 0o777)
                    os.remove(path)

if __name__ == "__main__":
    parser = ArgumentParser(description="Get player information.")
    parser.add_argument('-m', '--modes', type=str, nargs='+', help=f'Fetching modes - one or more of {FETCHING_MODES} (default: all)')
    parser.add_argument('-c', '--champions', type=str, nargs='+', help='List of champion names to process (default: all) - Only for "best" and "mono"')
    parser.add_argument('-r', '--ranks', type=str, nargs='+', help='List of ranks to fetch (default: all) - Only for "rank"')
    parser.add_argument('-n', type=int, help='Maximum ammount of fetched players per type/rank')
    parser.add_argument('--clean', action='store_true', help='Make a clean run, removing existing player info files')
    args = parser.parse_args()

    load_champion_data()

    handle_args(args)

    main(args)