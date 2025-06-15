import os
import json

for match in os.listdir("matches/Kaisa"):
    with open(f"matches/Kaisa/{match}", "r", encoding="utf-8") as f:
        data = json.load(f)
    mapId = data["info"]["mapId"]
    gameMode = data["info"]["gameMode"]
    if mapId != 11:
        print(mapId, gameMode)

exit(0)

items = [    
    223006
]

with open(os.path.join("items", "items.json"), 'r', encoding='utf-8') as file:
    item_list = json.load(file)

for id in items:
    print(f'{id} - {item_list[str(id)]["name"]}')

