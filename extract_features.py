import json 
import os

DEBUG = True
ITEM_UPGRADES = {
    3004: 3042, # gota ad
    3003: 3040, # gota ap
    3119: 3121, # gota tank
    3010: 3013, # bota void
    3866: 3867, # item de sup
}
LANE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

def write_to_files(all_timeline_features, all_postgame_features, checked):
    timeline_folder = os.path.join("features", "timeline")
    postgame_folder = os.path.join("features", "postgame")
    checked_folder = os.path.join("features")
    os.makedirs(timeline_folder, exist_ok=True)
    os.makedirs(postgame_folder, exist_ok=True)
    os.makedirs(checked_folder, exist_ok=True)

    ids = [int(fn[fn.find("ID")+2:fn.find(".")]) for fn in os.listdir(timeline_folder) if "features_ID" in fn]
    new_id = max(ids) + 1 if ids else 0

    timeline_filepath = os.path.join(timeline_folder, f"timeline_features_ID{new_id}.json")
    postgame_filepath = os.path.join(postgame_folder, f"postgame_features_ID{new_id}.json")
    checked_filepath  = os.path.join(postgame_folder, "checked.json")

    with open(timeline_filepath, "w+", encoding="utf-8") as fp:
        json.dump(all_timeline_features, fp, ensure_ascii=False, indent=4)
    with open(postgame_filepath, "w+", encoding="utf-8") as fp:
        json.dump(all_postgame_features, fp, ensure_ascii=False, indent=4)

    if os.path.exists(checked_filepath):
        with open(os.path.join(checked_folder, "checked.json"), "r") as fp:
            prev_checked = json.load(fp)
            checked = list(set(checked).union(prev_checked))
    with open("checked.json", "w+") as fp:
        json.dump(checked, fp, ensure_ascii=False, indent=4)
    return checked

def extract_match_features(match_details):
    info = match_details.get("info", {})
    if info["mapId"] != 11: # Not Summoners Rift
        return None
    participants = info.get("participants", [])
    features = []
    for i, participant in enumerate(participants):
        features.append({
            "participantId": participant.get("participantId"),
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

## Funcao gigante pq eu tava com preguica
def extract_features(matches_dir, timelines_dir):
    if os.path.exists("checked.json"):
        with open("checked.json", "r") as fp:
            checked = json.load(fp)
    else:
        checked = []

    with open("items/items.json", "r", encoding="utf-8") as fp:
        info = json.load(fp)
        legendary_items = [
            info[str_id]["id"] for str_id in info.keys()
            if info[str_id]["tier"] >= 3 or (info[str_id]["tier"] == 2 and \
                ("BOOTS" in info[str_id]["rank"] or info[str_id]["id"] in ITEM_UPGRADES))
        ]

    with open("champions.json", "r", encoding="utf-8") as fp:
        info = json.load(fp)
        champion_name_dict = {info[champ]["id"]: champ for champ in info.keys()}

    all_timeline_features = []
    all_postgame_features = []

    for match_json in os.listdir(matches_dir):
        if match_json in checked:
            continue

        timeline = os.path.join(timelines_dir, match_json.replace("_matches", "_timeline"))
        if not os.path.exists(timeline):
            continue
        
        match = os.path.join(matches_dir, match_json)

        with open(timeline, "r", encoding="utf-8") as fp:
            timeline_details = json.load(fp)

        with open(match, "r", encoding="utf-8") as fp:
            match_details = json.load(fp)

        match_features = extract_match_features(match_details)
        all_postgame_features.append(match_features)

        # Add nome do champ nas features
        for participant_info in match_features:
            participant_info["championName"] = champion_name_dict[participant_info["championId"]]
            participant_info["items"] = [item for item in participant_info["items"] if item in legendary_items]

        match_results = {
            participant_info["participantId"]: participant_info
            for participant_info in match_features
        }

        all_ids = [match_dict["participantId"] for match_dict in match_features]
        team_id = {participant_id: match_results[participant_id]["teamId"] for participant_id in all_ids}

        frames = timeline_details.get("info", {}).get("frames", {})
        all_frames = [
            {
                participantId: {
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "items": [],
                    "currentGold": 0,
                    "goldEarned": 0
                }
                for participantId in all_ids
            }
        ]
        keep_frame = [False]

        for i, frame in enumerate(frames):
            frame_features = {
                participantId: {
                    "kills": all_frames[-1][participantId]["kills"],
                    "deaths": all_frames[-1][participantId]["deaths"],
                    "assists": all_frames[-1][participantId]["assists"],
                    "items":  all_frames[-1][participantId]["items"].copy(),
                    "currentGold": all_frames[-1][participantId]["currentGold"],
                    "goldEarned": all_frames[-1][participantId]["goldEarned"],
                    "boughtItem": False
                }
                for participantId in all_ids
            }

            # gold
            participantFrames = frame.get("participantFrames", {})
            for participant_str_id in participantFrames.keys():
                frame_features[int(participant_str_id)]["currentGold"] = \
                    participantFrames[participant_str_id]["currentGold"]
                frame_features[int(participant_str_id)]["goldEarned"] = \
                    participantFrames[participant_str_id]["totalGold"]

            events = frame.get("events", {})
            bought_item = False
            for event in events:
                # item
                if event["type"] in ["ITEM_PURCHASED", "ITEM_SOLD", "ITEM_UNDO", "ITEM_DESTROYED"]:
                    if event["participantId"] not in range(1, 11):
                        continue
                    bought_item = True
                    frame_features[event["participantId"]]["boughItem"] = bought_item

                if event["type"] == "ITEM_PURCHASED" and event["itemId"] in legendary_items:
                    if event["itemId"] not in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].append(event["itemId"])

                if event["type"] == "ITEM_SOLD" and event["itemId"] in legendary_items:
                    if event["itemId"] in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].remove(event["itemId"])

                if event["type"] == "ITEM_UNDO":
                    # Desfez compra
                    if event["beforeId"] in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].remove(event["beforeId"])

                    # Desfez venda
                    if event["afterId"] in legendary_items:  
                        if event["afterId"] not in frame_features[event["participantId"]]["items"]:
                            frame_features[event["participantId"]]["items"].append(event["afterId"])
                        else:
                            frame_features[event["participantId"]]["items"].remove(event["afterId"])

                if event["type"] == "ITEM_DESTROYED" and event["itemId"] in legendary_items:
                    # Remocao
                    if event["itemId"] in frame_features[event["participantId"]]["items"] and \
                            match_results[event["participantId"]]["championName"].lower() not in ["viego"]:
                        frame_features[event["participantId"]]["items"].remove(event["itemId"])

                    # Item com upgrade
                    if event["itemId"] in ITEM_UPGRADES:
                        frame_features[event["participantId"]]["items"].append(ITEM_UPGRADES[event["itemId"]])

                    # Item de suporte
                    if event["itemId"] == 3867:
                        for item in [3869, 3870, 3871, 3876, 3877]:
                            if item in match_results[event["participantId"]]["items"] and \
                                    item not in frame_features[event["participantId"]]["items"]:
                                frame_features[event["participantId"]]["items"].append(item)

                if event["type"] == "CHAMPION_KILL":
                    # kill
                    if event["killerId"] in range(1, 11):
                        frame_features[event["killerId"]]["kills"] += 1

                    # death
                    frame_features[event["victimId"]]["deaths"] += 1

                    # assist
                    if "assistingParticipantIds" in event:
                        for assistant_id in event["assistingParticipantIds"]:
                            frame_features[assistant_id]["assists"] += 1

            all_frames.append(frame_features)

            is_last_frame = True if i == len(frames) - 1 else False
            keep_frame.append(bought_item or is_last_frame)

        for i in range(len(all_frames)-1, -1, -1):
            if not keep_frame[i]:
                all_frames.pop(i)

        last_frame = all_frames[-1]

        features = []
        for feat in last_frame[1].keys():
            if feat in match_results[1]:
                features.append(feat)

        ok = True
        debug_string = ""
        mistakes = 0
        for i, participantId in enumerate(sorted(all_ids, key=lambda x: team_id[x])):
            single_ok = True
            if i == 0 or i == 5:
                debug_string += f"\nTime {i % 2}\n"
            debug_string += f"Participant {participantId} - {match_results[participantId]['championName']}\n"
            for feat in features:
                try:
                    if feat != "items":
                        assert match_results[participantId][feat] == last_frame[participantId][feat]
                    else:
                        if match_results[participantId]["championName"] != "Viego":
                            for item in match_results[participantId][feat]:
                                if item not in last_frame[participantId][feat]:
                                    mistakes += 1
                            for item in last_frame[participantId][feat]:
                                if item not in match_results[participantId][feat]:
                                    mistakes += 1
                        assert mistakes < 3
                except:
                    debug_string += f"Feature: {feat:<20} Match results: {str(match_results[participantId][feat]):<50} Timeline: {str(last_frame[participantId][feat])}\n"
                    ok = single_ok = False
            debug_string += f"{'OK' if single_ok else '** FAILED **'}\n"

        if not ok and DEBUG:
            debug_string += f"Error found in match: {timeline}\n"
            print(debug_string)
            break

        all_timeline_features.append(all_frames)
        checked.append(match_json)

        if len(all_timeline_features) >= 50:
            checked = write_to_files(all_timeline_features, all_postgame_features, checked)
            all_timeline_features = []
            all_postgame_features = []

    if all_timeline_features:
        checked = write_to_files(all_timeline_features, all_postgame_features, checked)
    
    return checked