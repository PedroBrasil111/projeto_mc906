import json
import os


LANE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

def extract_features(match_details):
    info = match_details.get("info", {})
    participants = info.get("participants", [])
    features = []
    for i, participant in enumerate(participants):
        features.append({
            "championId": participant.get("championId"),
            "teamId": participant.get("teamId"),
            "matchResult": participant.get("win"),
            "kills": participant.get("kills"),
            "deaths": participant.get("deaths"),
            "assists": participant.get("assists"),
            "goldEarned": participant.get("goldEarned"),
            "lane": participant.get("individualPosition"),
            "level": participant.get("champLevel"),
            "items": [
                participant.get(f"item{i}") for i in range(7)
            ],
        })
    features = sorted(features, key=lambda x: LANE_ORDER.index(x['lane']) if x['lane'] in LANE_ORDER else len(LANE_ORDER))
    return features

def main():
    matches_folder = "matches/Kaisa"
    features_path = "features/Kaisa_features.json"
    features = []

    for filename in os.listdir(matches_folder):
        match_file = os.path.join(matches_folder, filename)
        with open(match_file, 'r', encoding='utf-8') as f:
            match_data = json.load(f)
            features.append(extract_features(match_data))

    with open(features_path, 'w', encoding='utf-8') as f:
        json.dump(features, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()