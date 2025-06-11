import wget
import os
import json
import multiprocessing as mp

def download_item(id):
    if any(os.path.exists(f"items/{tier}/{id}.json") for tier in range(1, 6)):
        return
    url = f"https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/items.json"
    try:
        wget.download(url, f"items/{id}.json")
        with open(f"items/{id}.json", 'r', encoding='utf-8') as file:
            data = json.load(file)
        os.rename(f"items/{id}.json", f"items/{data['tier']}/{id}.json")
    except:
        return

def download_items():
    url = f"https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/items.json"
    wget.download(url, f"items/items.json")

if __name__ == "__main__":
    download_items()

    exit()

    os.makedirs("items", exist_ok=True)
    cpus = mp.cpu_count()
    max_pool_size = cpus if cpus < 4 else 4
    pool = mp.Pool(cpus if cpus < max_pool_size else max_pool_size)
    
    for id in range(1001, 8021):
        pool.apply_async(download_item, args=(id,))

    pool.close()
    pool.join()
    
    print("All items downloaded successfully.")