import pandas as pd
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env

API_KEY = os.getenv("RIOT_API_KEY")  # Certifique-se de ter uma variável de ambiente RIOT_API_KEY configurada
REGIAO = "br1"  # Região para Summoner e League API
MATCH_REGION = "americas"  # Região para Match API (americas cobre BR, NA, etc)
CHAMPION_NAME = "Kai'sa"  # Campeão que queremos analisar

# 1. Buscar jogadores Challenger solo queue
def get_challenger_summoners():
    url = f"https://{REGIAO}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Erro ao buscar Challenger:", response.status_code, response.text)
        return []
    data = response.json()
    return data.get("entries", [])

# 2. Pegar dados do summoner pelo nome para obter puuid
def get_summoner_puuid(summoner_name):
    url = f"https://{REGIAO}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao buscar summoner {summoner_name}:", response.status_code)
        return None
    return response.json().get("puuid")

# 3. Buscar partidas recentes do summoner (limite 20 partidas)
def get_match_ids(puuid, count=20):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao buscar partidas de {puuid}:", response.status_code)
        return []
    return response.json()

# 4. Obter detalhes da partida
def get_match_detail(match_id):
    url = f"https://{MATCH_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao buscar detalhes da partida {match_id}:", response.status_code)
        return None
    return response.json()

# 5. Filtrar e extrair dados das partidas com o campeão desejado
def analyze_builds(puuid, summonerID):
    if puuid is None:
        return []
    match_ids = get_match_ids(puuid)
    builds = []

    for match_id in match_ids:
        match_detail = get_match_detail(match_id)
        if match_detail is None:
            continue

        participants = match_detail["info"]["participants"]
        for p in participants:
            if p["summonerId"].lower() == summonerID.lower() and p["championName"].lower() == CHAMPION_NAME.lower():
                # Extrai dados de build e stats
                build = {
                    "match_id": match_id,
                    "items": [p[f"item{i}"] for i in range(7)],  # itens 0 a 6
                    "kills": p["kills"],
                    "deaths": p["deaths"],
                    "assists": p["assists"],
                    "goldEarned": p["goldEarned"],
                    "totalDamageDealtToChampions": p["totalDamageDealtToChampions"],
                    "win": p["win"],
                    "champLevel": p["champLevel"],
                    "gameDuration": match_detail["info"]["gameDuration"],
                }
                builds.append(build)
                break
        time.sleep(1.3)  # Respeita limite de requests (20 reqs / 1min para API gratuita)
    return builds

def main():
    challenger_summoners = get_challenger_summoners()
    print(f"Encontrados {len(challenger_summoners)} summoners Challenger.")

    all_builds = []
    for entry in challenger_summoners[:10]:  # limita a 10 summoners para exemplo
        puuid = entry["puuid"]
        summonerID = entry["summonerId"]
        print(f"Analisando builds do summoner: {puuid}")
        builds = analyze_builds(puuid, summonerID)
        print(f"  Encontradas {len(builds)} partidas com {CHAMPION_NAME} para {puuid}")
        all_builds.extend(builds)

    print(f"\nTotal de builds coletadas: {len(all_builds)}")
    # Aqui você pode salvar os dados para CSV, JSON, etc.
    # Exemplo: salvar em CSV
    df = pd.DataFrame(all_builds)
    df.to_csv(f"builds_{CHAMPION_NAME}.csv", index=False)
    print(f"Dados salvos em builds_{CHAMPION_NAME}.csv")

if __name__ == "__main__":
    main()
