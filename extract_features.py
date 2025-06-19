import json 
import os
from get_game_data import get_item_data, get_champion_data

DEBUG = True
ITEM_UPGRADES = {
    3004: 3042, # gota ad
    3003: 3040, # gota ap
    3119: 3121, # gota tank
    3010: 3013, # bota void
    3866: 3867, # item de sup
}
LANE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
ELITE_MONSTER_MAPPING = {
    "DRAGON": "dragonKills",
    "BARON_NASHOR": "baronKills",
    "HORDE": "voidgrubKills",
    "RIFTHERALD": "heraldKills",
    "ATAKHAN": "atakhanKills",
}

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
    checked_filepath  = os.path.join(checked_folder, "checked.json")

    with open(timeline_filepath, "w+", encoding="utf-8") as fp:
        json.dump(all_timeline_features, fp, ensure_ascii=False, indent=4)
    with open(postgame_filepath, "w+", encoding="utf-8") as fp:
        json.dump(all_postgame_features, fp, ensure_ascii=False, indent=4)

    if os.path.exists(checked_filepath):
        with open(checked_filepath, "r") as fp:
            prev_checked = json.load(fp)
            checked = list(set(checked).union(prev_checked))
    with open(checked_filepath, "w+") as fp:
        json.dump(checked, fp, ensure_ascii=False, indent=4)
    return checked

def extract_match_features(match_details):
    info = match_details.get("info", {})
    participants = info.get("participants", [])
    features = []
    for i, participant in enumerate(participants):
        features.append({
            "participantId": participant.get("participantId"),
            "puuid": participant.get("puuid"),
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
            "perks": [
                perk_info["perk"]
                for perk_info in participant.get("perks").get("styles")[0].get("selections")
            ] + [
                perk_info["perk"]
                for perk_info in participant.get("perks").get("styles")[1].get("selections")
            ],
            "origin": match_details.get("metadata", {}).get("origin", "")
        })
    features = sorted(features, key=lambda x: LANE_ORDER.index(x['lane']) if x['lane'] in LANE_ORDER else len(LANE_ORDER))
    return features

## Funcao gigante pq eu tava com preguica
def extract_features(matches_dir, timelines_dir):
    checked_path = os.path.join("features", "checked.json")
    if os.path.exists(checked_path):
        with open(checked_path, "r") as fp:
            checked = json.load(fp)
    else:
        checked = []

    item_path = get_item_data(clean=False)
    champion_path = get_champion_data(clean=False)

    with open(item_path, "r", encoding="utf-8") as fp:
        info = json.load(fp)
        analysed_items = [
            info[str_id]["id"] for str_id in info.keys()
            if info[str_id]["tier"] >= 3 or (info[str_id]["tier"] == 2 and \
                ("BOOTS" in info[str_id]["rank"] or info[str_id]["id"] in ITEM_UPGRADES)) or \
                ("STARTER" in info[str_id]["rank"])
        ]

    with open(champion_path, "r", encoding="utf-8") as fp:
        info = json.load(fp)
        champion_name_dict = {info[champ]["id"]: champ for champ in info.keys()}

    all_timeline_features = {}
    all_postgame_features = {}

    for match_json in os.listdir(matches_dir):
        if not os.path.exists(os.path.join(matches_dir, match_json)):
            continue

        match_id = match_json.split("_matches")[0]
        if match_id in checked:
            print(f"Already checked: {match_id}")
            continue

        timeline = os.path.join(timelines_dir, match_json.replace("_matches", "_timeline"))
        if not os.path.exists(timeline):
            continue

        match = os.path.join(matches_dir, match_json)

        with open(timeline, "r", encoding="utf-8") as fp:
            timeline_details = json.load(fp)

        with open(match, "r", encoding="utf-8") as fp:
            match_details = json.load(fp)

        print(match_json)
        match_features = extract_match_features(match_details)

        match_id = match_details["metadata"]["matchId"]

        if not match_features:
            continue

        tier = None
        with open(os.path.join("player_info", "all_players.json"), "r", encoding="UTF-8") as fp:
            all_players = json.load(fp)
            for player in match_features:
                if player["puuid"] in all_players:
                    tier = all_players[player["puuid"]]["tier"]
                    break
        for player in match_features:
            player["tier"] = tier

        all_postgame_features[match_id] = match_features


        # Add nome do champ nas features
        for participant_info in match_features:
            participant_info["championName"] = champion_name_dict[participant_info["championId"]]
            participant_info["items"] = [item for item in participant_info["items"] if item in analysed_items]

        match_results = {
            participant_info["participantId"]: participant_info
            for participant_info in match_features
        }

        additional_features = {
            participant_info["participantId"]: {
                feature: participant_info[feature]
                for feature in [
                    "participantId",
                    "puuid",
                    "championId",
                    "teamId",
                    "lane",
                    "perks",
                    "tier",
                    "championName",
                    "origin",
                ]
            } for participant_info in match_features
        }

        all_ids = [match_dict["participantId"] for match_dict in match_features]
        team_id = {participant_id: match_results[participant_id]["teamId"] for participant_id in all_ids}

        frames = timeline_details.get("info", {}).get("frames", {})
        all_frames = {
            -1: {
                participantId: {
                    "kills": 0,
                    "deaths": 0,
                    "assists": 0,
                    "items": [],
                    "currentGold": 0,
                    "goldEarned": 0,
                    "skills": [0, 0, 0, 0],
                    "level": 0,
                    "minionsKilled": 0,
                    "dragonKills": 0,
                    "voidgrubKills": 0,
                    "heraldKills": 0,
                    "baronKills": 0,
                    "atakhanKills": 0,
                    "structuresKilled": 0,
                    **additional_features[participantId]
                }
                for participantId in all_ids
            }
        }
        marked_for_removal = [-1, ]
        timestamp = -1

        for i, frame in enumerate(frames):

            frame_features = {
                participantId: {
                    "kills": all_frames[timestamp][participantId]["kills"],
                    "deaths": all_frames[timestamp][participantId]["deaths"],
                    "assists": all_frames[timestamp][participantId]["assists"],
                    "items":  all_frames[timestamp][participantId]["items"].copy(),
                    "skills": all_frames[timestamp][participantId]["skills"].copy(),
                    "currentGold": all_frames[timestamp][participantId]["currentGold"],
                    "goldEarned": all_frames[timestamp][participantId]["goldEarned"],
                    "level": all_frames[timestamp][participantId]["level"],
                    "minionsKilled": all_frames[timestamp][participantId]["minionsKilled"],
                    "dragonKills": all_frames[timestamp][participantId]["dragonKills"],
                    "voidgrubKills": all_frames[timestamp][participantId]["voidgrubKills"],
                    "baronKills": all_frames[timestamp][participantId]["baronKills"],
                    "heraldKills": all_frames[timestamp][participantId]["heraldKills"],
                    "atakhanKills": all_frames[timestamp][participantId]["atakhanKills"],
                    "structuresKilled": all_frames[timestamp][participantId]["structuresKilled"],
                    "boughtItem": False,
                    **additional_features[participantId]
                }
                for participantId in all_ids
            }

            participantFrames = frame.get("participantFrames", {})
            # dados sempre presentes
            for participant_str_id in participantFrames.keys():
                frame_features[int(participant_str_id)]["currentGold"] = \
                    participantFrames[participant_str_id]["currentGold"]
                frame_features[int(participant_str_id)]["goldEarned"] = \
                    participantFrames[participant_str_id]["totalGold"]
                frame_features[int(participant_str_id)]["level"] = \
                    participantFrames[participant_str_id]["level"]
                frame_features[int(participant_str_id)]["minionsKilled"] = \
                    participantFrames[participant_str_id]["minionsKilled"] + \
                    participantFrames[participant_str_id]["jungleMinionsKilled"]

            events = frame.get("events", {})
            timestamp = frame.get("timestamp", {})
            must_keep = False
            for event in events:
                bought_item = False
                # item
                if event["type"] in ["ITEM_PURCHASED", "ITEM_SOLD", "ITEM_UNDO", "ITEM_DESTROYED"] and \
                        event.get("participantId", 0) not in range(1, 11):
                    continue

                if event["type"] == "ITEM_PURCHASED" and event["itemId"] in analysed_items:
                    if event["itemId"] not in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].append(event["itemId"])
                        bought_item = True

                elif event["type"] == "ITEM_SOLD" and event["itemId"] in analysed_items:
                    if event["itemId"] in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].remove(event["itemId"])

                elif event["type"] == "ITEM_UNDO":
                    # Desfez compra
                    if event["beforeId"] in frame_features[event["participantId"]]["items"]:
                        frame_features[event["participantId"]]["items"].remove(event["beforeId"])

                    # Desfez venda
                    if event["afterId"] in analysed_items:  
                        if event["afterId"] not in frame_features[event["participantId"]]["items"]:
                            frame_features[event["participantId"]]["items"].append(event["afterId"])
                        else:
                            frame_features[event["participantId"]]["items"].remove(event["afterId"])

                elif event["type"] == "ITEM_DESTROYED" and event["itemId"] in analysed_items:
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
                                bought_item = True

                if bought_item:
                    frame_features[event["participantId"]]["boughtItem"] = bought_item
                    must_keep = True
                    continue

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

                elif event["type"] == "SKILL_LEVEL_UP":
                    # kill
                    frame_features[event["participantId"]]["skills"][event["skillSlot"] - 1] += 1

                elif event["type"] == "ELITE_MONSTER_KILL":
                    for participantId in frame_features.keys():
                        if frame_features[participantId]["teamId"] == event["killerTeamId"]:
                            frame_features[participantId][ELITE_MONSTER_MAPPING[event["monsterType"]]] += 1

                elif event["type"] == "BUILDING_KILL":
                    for participantId in frame_features.keys():
                        if frame_features[participantId]["teamId"] != event["teamId"]:
                            frame_features[participantId]["structuresKilled"] += 1

            all_frames[timestamp] = frame_features

            is_last_frame = True if i == len(frames) - 1 else False
            if not (must_keep or is_last_frame):
                marked_for_removal.append(timestamp)

        for ts in marked_for_removal:
            all_frames.pop(ts)

        last_frame = all_frames[max(all_frames.keys())]

        debug_string = ""

        features = []
        for feat in last_frame[1].keys():
            if feat in match_results[1]:
                features.append(feat)
            else:
                debug_string += f"Feature {feat} not found in postgame results\n"

        ok = True
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

        all_timeline_features[match_id] = all_frames
        checked.append(match_id)

        if len(all_timeline_features) >= 50:
            checked = write_to_files(all_timeline_features, all_postgame_features, checked)
            all_timeline_features = {}
            all_postgame_features = {}

    if all_timeline_features:
        checked = write_to_files(all_timeline_features, all_postgame_features, checked)

    return checked

if __name__ == "__main__":
    for folder in os.listdir("matches"):
        if len(os.listdir(os.path.join("matches", folder))) > 0:
            extract_features(
                os.path.join("matches", folder),
                os.path.join("timelines", folder),
            )