import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()  # .env

API_KEY = os.getenv("RIOT_API_KEY")

TIME_SINCE_BREAK = time.time()
REQ_SINCE_BREAK = 0
REQ_LIMIT = 100
REQ_TIME_LIMIT = 120

def safe_request(url, headers, max_tries=300):
    tries = 0
    while tries < max_tries:
        try:
            return requests.get(url, headers=headers)
        except KeyboardInterrupt:
            print("Request interrupted by user.")
            raise
        except Exception:
            time.sleep(1)
            tries += 1
    raise Exception(f"Max tries exceeded while fetching request for url {url}")

def make_request(url):
    headers = {"X-Riot-Token": API_KEY}
    response = safe_request(url, headers)
    global TIME_SINCE_BREAK, REQ_SINCE_BREAK
    REQ_SINCE_BREAK += 1
    cond1 = REQ_SINCE_BREAK >= REQ_LIMIT
    cond2 = response.status_code == 429
    if cond1 or cond2:
        elapsed_time = time.time() - TIME_SINCE_BREAK
        if elapsed_time < REQ_TIME_LIMIT:
            sleep_time = REQ_TIME_LIMIT - elapsed_time if cond1 else 10
            print(f"\033[93mRate limit reached ({'stopping before getting denied' if cond1 else 'denied by host'}). Sleeping for {sleep_time:.2f} seconds.\033[0m")
            time.sleep(sleep_time)
            print("We're so back")
        TIME_SINCE_BREAK = time.time()
        REQ_SINCE_BREAK = 0
    if cond2:
        response = make_request(url) # retry the request if rate limit is hit
    return response