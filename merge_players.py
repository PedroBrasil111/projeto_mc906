import os
import json

def main():
    base_folder = "player_info"
    output_path = os.path.join(base_folder, "all_players.json")
    if os.path.exists(output_path):
        os.remove(output_path)
    all_player_info = []
    for info_folder in os.listdir(base_folder):
        for info_file in os.listdir(os.path.join(base_folder, info_folder)):
            with open(os.path.join(base_folder, info_folder, info_file), "r", encoding="UTF-8") as fp:
                players = json.load(fp)
            for p in players:
                p["origin"] = f"{info_folder}/{info_file.replace('.json', '')}"
            all_player_info.extend(players)
    with open(output_path, "w+", encoding="UTF-8") as fp:
        json.dump(all_player_info, fp, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()