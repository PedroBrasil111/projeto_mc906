import os
import json

items = [    
    3042,
    6655,
    4645,
    1043,
    3108,
    3006,
    3340 
]

with open(os.path.join("items", "items.json"), 'r', encoding='utf-8') as file:
    item_list = json.load(file)

for id in items:
    print(f'{id} - {item_list[str(id)]["name"]}')