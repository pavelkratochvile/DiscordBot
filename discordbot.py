from dotenv import load_dotenv
load_dotenv()

import os
import requests
from datetime import *
import time
import dis

game_name = "OPTIM1"
game_tag = "EUNE"


def read_api_key(filename):
    with open(filename, "r") as file:
        data = file.readline()
        return data

def load_webhook_url(filename):
    with open(filename, "r") as file:
        data = file.readline()
        return data.strip()


def read_ascii(filename):
    with open(filename, "r", encoding="utf-8") as file:
        return file.read().rstrip()


api_key = read_api_key("apikey.txt")
api_key = api_key.strip()

class GameAnalyzer:
    def __init__(self, game_name, game_tag):
        self.game_name = game_name
        self.game_tag = game_tag
        self.api_key = api_key
        self.puuid = self.get_summoner_puuid()

    def get_summoner_puuid(self):
        url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{self.game_name}/{self.game_tag}"
        response = requests.get(
            url,
            headers={"X-Riot-Token": self.api_key},
            timeout=15,
        )
        if not response.ok:
            raise RuntimeError(
                f"Riot API vrátil chybu {response.status_code}: {response.text}"
            )
        return response.json()["puuid"]

    def get_summoner_last_match(self):
        url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{self.puuid}/ids?start=0&count=20&api_key={self.api_key}"
        response = requests.get(url)
        return response.json()[0]

    def get_match_details(self, match_id):
        url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={self.api_key}"
        response = requests.get(url)
        return response.json()

    def get_teamates_stats(self, match_details):
        participants = match_details["info"]["participants"]
        teamates_stats = []
        enemy_stats = []
        for participant in participants:
            player_name = (
                participant.get("riotIdGameName")
                or participant.get("summonerName")
                or "Neznámý hráč"
            )
            if participant["teamId"] == 100:
                teamates_stats.append(PlayerStats(player_name,participant["kills"],participant["deaths"],participant["assists"],participant["totalDamageDealtToChampions"],participant["win"],))
            else:
                enemy_stats.append(PlayerStats(player_name,participant["kills"],participant["deaths"],participant["assists"],participant["totalDamageDealtToChampions"],participant["win"],))
        return MatchStats(teamates_stats, enemy_stats, match_details["info"]["teams"][0]["win"])


class PlayerStats:
    def __init__(self, name, kills, deaths, assists, total_damage, doeswin):
        self.name = name
        self.kills = kills
        self.deaths = deaths
        self.assists = assists
        self.total_damage = total_damage
        self.doeswin = doeswin

class MatchStats:
    def __init__(self, players_stats_list, enemy_stats_list, is_win):
        self.players_stats_list = players_stats_list
        self.enemy_stats_list = enemy_stats_list
        self.is_win = is_win

    def format_match_message(self):
        if self.is_win:
            result = "VÍTĚZSTVÍ"
            color = 0x2ECC71
        else:
            result = "PROHRA"
            color = 0xE74C3C

        fields = []

        for i, player_stats in enumerate(self.players_stats_list):
            fields.append({
                "name": f"Hráč {player_stats.name}",
                "value": (
                    f"**K/D/A:** {player_stats.kills}/{player_stats.deaths}/{player_stats.assists}\n"
                    f"**Poškození:** {player_stats.total_damage:,}\n"
                    f"**Výsledek:** {'Výhra' if player_stats.doeswin else 'Prohra'}"
                ).replace(",", " "),
                "inline": True,
            })

        return {
            "embeds": [{
                "title": f"{result} - poslední zápas",
                "description": "Přehled statistik tvého týmu",
                "color": color,
                "fields": fields,
                "footer": {"text": "League of Legends • Match Analyzer"},
            }]
        }

if __name__ == "__main__":
    game_analyzer = GameAnalyzer(game_name, game_tag)
    last_match_id = None

    WEBHOOK_URL = load_webhook_url("webhook_url.txt")

    while True:
        if last_match_id != game_analyzer.get_summoner_last_match():
            new_last_match_id = game_analyzer.get_summoner_last_match()
            last_match_id = new_last_match_id
            match_details = game_analyzer.get_match_details(last_match_id)
            match_stats = game_analyzer.get_teamates_stats(match_details)
            
            
            data = match_stats.format_match_message()
            response = requests.post(WEBHOOK_URL, json=data)

            if response.status_code == 204:
                print("Zpráva byla úspěšně odeslána na Discord.")
            else:
                print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

        time.sleep(60)

