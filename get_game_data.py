import json
import wget
import requests
import os

def get_champion_data(clean=True):
    information_to_keep = ["id", "icon"]
    url = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
    path = os.path.join("game_data", "champions.json")
    if os.path.exists(path):
        if clean:
            os.remove(path)
        else:
            return path
    print(f"\nFetching champions")
    wget.download(url, out=path)
    os.makedirs(os.sep.join(path.split(os.sep)[:-1]), exist_ok=True)
    with open(path, 'r', encoding='utf-8') as fp:
        champ_info = json.load(fp)
        champ_info = {
            key: {
                info: champ_info[key][info]
                for info in information_to_keep
            } for key in champ_info.keys()
        }
    os.remove(path)
    with open(path, 'w+', encoding='utf-8') as fp:
        json.dump(champ_info, fp, ensure_ascii=False, indent=4)
    return path

def get_item_data(clean=True):
    information_to_keep = ["id", "name", "tier", "rank", "buildsFrom", "buildsInto", "icon"]
    url = f"https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/items.json"
    path = os.path.join("game_data", "items.json")
    if os.path.exists(path):
        if clean:
            os.remove(path)
        else:
            return path
    print(f"\nFetching items")
    wget.download(url, out=path)
    os.makedirs(os.sep.join(path.split(os.sep)[:-1]), exist_ok=True)
    with open(path, 'r', encoding='utf-8') as fp:
        item_info = json.load(fp)
        item_info = {
            key: {
                info: item_info[key][info]
                for info in information_to_keep
            } for key in item_info.keys()
        }
    os.remove(path)
    with open(path, 'w+', encoding='utf-8') as fp:
        json.dump(item_info, fp, ensure_ascii=False, indent=4)
    return path

def get_rune_data(clean=True):
    url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/perks.json"
    path = os.path.join("game_data", "perks.json")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    if os.path.exists(path):
        if clean:
            os.remove(path)
        else:
            return path
    print(f"\nFetching perks (runes)")
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    perk_info  = response.json()
    os.makedirs(os.sep.join(path.split(os.sep)[:-1]), exist_ok=True)
    perk_info = {
        info["id"]: {
            "name": info["name"]
        } for info in perk_info
    }
    with open(path, 'w+', encoding='utf-8') as fp:
        json.dump(perk_info, fp, ensure_ascii=False, indent=4)
    return path

def get_champion_icons():
    pass

def get_item_icons():
    pass

if __name__ == "__main__":
    get_rune_data()
    get_champion_data()
    get_item_data()