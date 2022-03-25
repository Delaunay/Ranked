"""Used to query SteamAPI to get dota match information to bootstrap bots"""
import datetime
import gzip
import json
import logging
import os
import time
from tracemalloc import start
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
from typing import List

import requests

from ranked.utils.webapi import LimitExceeded, ServerError, WebAPI

logger = logging.getLogger(__name__)

# Loaded options
_options = {}

# Options that are currently in use
_active_options = {}


def fetch_option(name, default, type=str) -> str:
    """Look for an option locally and using the environment variables
    Environment variables are use as the ultimate overrides
    """
    global _active_options

    env_name = name.upper().replace(".", "_")
    value = os.getenv(f"RANKED_{env_name}", None)

    if value is None:
        value = _options.get(name, default)

    if value is None:
        return value

    return type(value)


def option(name, default, type=str) -> str:
    global _active_options

    value = fetch_option(name, default, type)
    _active_options[name] = value

    return value


# set export RANKED_STEAM_API=XXXX
STEAM_API_KEY = option("steam.api", None)
DOTA_ID = 570
DOTA_PRIVATE_BETA = 816
DOTA_BETA_TEST = 205790


class DOTA_GameMode(IntEnum):
    DOTA_GAMEMODE_NONE = 0
    DOTA_GAMEMODE_AP = 1
    DOTA_GAMEMODE_CM = 2
    DOTA_GAMEMODE_RD = 3
    DOTA_GAMEMODE_SD = 4
    DOTA_GAMEMODE_AR = 5
    DOTA_GAMEMODE_INTRO = 6
    DOTA_GAMEMODE_HW = 7
    DOTA_GAMEMODE_REVERSE_CM = 8
    DOTA_GAMEMODE_XMAS = 9
    DOTA_GAMEMODE_TUTORIAL = 10
    DOTA_GAMEMODE_MO = 11
    DOTA_GAMEMODE_LP = 12
    DOTA_GAMEMODE_POOL1 = 13
    DOTA_GAMEMODE_FH = 14
    DOTA_GAMEMODE_CUSTOM = 15
    DOTA_GAMEMODE_CD = 16
    DOTA_GAMEMODE_BD = 17
    DOTA_GAMEMODE_ABILITY_DRAFT = 18
    DOTA_GAMEMODE_EVENT = 19
    DOTA_GAMEMODE_ARDM = 20
    DOTA_GAMEMODE_1V1MID = 21
    DOTA_GAMEMODE_ALL_DRAFT = 22
    DOTA_GAMEMODE_TURBO = 23
    DOTA_GAMEMODE_MUTATION = 24


@dataclass
class MatchHistory_Match_Player:
    account_id: int
    player_slot: int
    hero_id: int

    def is_dire(self):
        return (self.player_slot & 0b10000000) >> 7

    def position(self):
        return self.player_slot & 0b00000111


@dataclass
class MatchHistory_Match:
    match_id: int
    match_seq_num: int
    start_time: int
    lobby_time: int
    players: List[MatchHistory_Match_Player]


@dataclass
class MatchHistory:
    status: int
    statusDetail: str
    num_results: int
    total_results: int
    results_remaining: int
    matches: List[MatchHistory_Match]


@dataclass
class MatchDetail_Player_Unit:
    unitname: str
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int


@dataclass
class MatchDetail_Player_AbilityUpgrades:
    ability: int
    time: int
    level: int


@dataclass
class MatchDetail_Player:
    account_id: int
    player_slot: int
    hero_id: int
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int
    backpack_0: int
    backpack_1: int
    backpack_2: int
    item_neutral: int
    kills: int
    deaths: int
    assists: int
    leaver_status: int
    last_hits: int
    denies: int
    gold_per_min: float
    xp_per_min: float
    level: int
    hero_damage: int
    tower_damage: int
    hero_healing: int
    gold: int
    gold_spent: int
    scaled_hero_damage: int
    scaled_tower_damage: int
    scaled_hero_healing: int
    ability_upgrades: List[MatchDetail_Player_AbilityUpgrades]
    additional_units: List[MatchDetail_Player_Unit]


@dataclass
class MatchDetail_Picks:
    is_pick: bool
    hero_id: int
    team: int
    order: int


@dataclass
class MatchDetail:
    players: List[MatchDetail_Player]
    season: str
    radiant_win: bool
    duration: int
    pre_game_duration: int
    start_time: int
    match_id: str
    match_seq_num: int
    tower_status_radiant: int
    tower_status_dire: int
    barracks_status_radiant: int
    barracks_status_dire: int
    cluster: str
    first_blood_time: int
    lobby_type: int
    human_players: int
    leagueid: int
    positive_votes: int
    negative_votes: int
    game_mode: int
    picks_bans: List[MatchDetail_Picks]
    flags: str
    engine: int
    radiant_score: int
    dire_score: int


@dataclass
class LeagueListing:
    name: str
    leagueid: int
    description: str
    tournament_url: str


# TODO: add API query limiter
# TODO: add a dynamic dataset builder that save the result of the queries and keep building it up
class SteamAPI(WebAPI):
    """
    References
    ----------
    * https://wiki.teamfortress.com/wiki/WebAPI/GetMatchHistory
    * https://dev.dota2.com/forum/dota-2/spectating/replays/webapi/60177-things-you-should-know-before-starting?t=58317
    """

    URL = "https://api.steampowered.com/IDOTA2Match_{game_id}/{method}/v1"
    URL_STATS = "https://api.steampowered.com/IDOTA2MatchStats_{game_id}/{method}/v1"

    def __init__(self):
        super(SteamAPI, self).__init__("steamapi")

        # 100,000 API calls per day.
        # 1 request per second
        # 60 request per minute
        self.max_api_call_day = 100000
        self.start = None
        # make sure we respect the T&C of valve and do not get banned
        self.wait_time = 1
        self.limiter = True
        self.request_count = 0

    def get_match_history(
        self,
        mode: int = DOTA_GameMode.DOTA_GAMEMODE_AP,
        skill=3,
        min_players=10,
        count=500,
        league_id=None,
        date_min=None,
        start_at_match_id=None,
        account_id=None,
    ) -> MatchHistory:
        # Results are limited 500 per query
        params = {
            "mode": mode,
            "skill": skill,
            "min_players": min_players,
            "matches_requested": count,
            "key": STEAM_API_KEY,
            "league_id": league_id,
            "start_at_match_id": start_at_match_id,
            "account_id": account_id,
            # Docs say `Start searching for matches equal to or older than this match ID.`
            # which does not make sense, I want newer match not older one
            # date_max
            "date_min": date_min,
            # Optionals
            # 'format': 'json',
            # 'language': 'en_US'
        }

        url = SteamAPI.URL.format(game_id=DOTA_ID, method="GetMatchHistory")
        response = requests.get(url, params=params)

        self.handle_errors(response)
        self.limit()
        return response.json().get("result")

    def get_match_detail(self, match_id) -> MatchDetail:
        params = {
            "match_id": match_id,
            "key": STEAM_API_KEY,
        }

        url = SteamAPI.URL.format(game_id=DOTA_ID, method="GetMatchDetails")
        response = requests.get(url, params=params)
        self.handle_errors(response)
        self.limit()
        return response.json().get("result")

    def get_league_listing(self) -> LeagueListing:
        params = {
            "key": STEAM_API_KEY,
        }

        url = SteamAPI.URL.format(game_id=DOTA_ID, method="GetLeagueListing")
        response = requests.get(url, params=params)
        self.handle_errors(response)
        self.limit()
        return response.json().get("result")

    def get_realtime_match_stats(self, match_id) -> MatchDetail:
        params = {
            "match_id": match_id,
            "key": STEAM_API_KEY,
        }

        url = SteamAPI.URL_STATS.format(game_id=DOTA_ID, method="GetRealtimeStats")
        response = requests.get(url, params=params)
        self.handle_errors(response)
        self.limit()
        return response.json().get("result")


class Dota2MatchDumper:
    """Dump match data to a file"""

    def __init__(self, builder, start_match) -> None:
        self.api = SteamAPI()
        self.skill = 3
        self.latest_date = None
        self.start_match_id = start_match
        self.latest_match = None
        self.known_match = defaultdict(int)
        self.counts = defaultdict(int)
        self.matches = 0
        self.running = True
        self.builder = builder

        # Tweak the sleeps to avoid duplicates
        # Sleeps are not there for the lulz or even to be nice to valve
        # matches are kind of slow to appear so to avoid getting tons of duplicates
        # we need to sleep a bit so when all the matches are processed we get a fresh batch
        self.batch_sleep = 5
        self.match_sleep = 3
        self.error_retry = 3
        self.error_sleep = 30

    def status(self):
        api_call_limit = f"API: {self.api.limit_stats() * 100:6.2f}%"
        match = f"Matches: {self.matches} (unique: {len(self.known_match) * 100 / self.matches:6.2f}%)"
        return f"{api_call_limit} {match}"

    def write_match(self, dataset, match_id, data):
        self.counts[DOTA_GameMode(data.get("game_mode", 0)).name] += 1
        self.builder.process_match(match_id, data)
        # dataset.write(json.dumps(dict(id=match_id, match=data)) + "\n")

    def get_match_detail(self, match_id):
        for i in range(self.error_retry):
            try:
                return self.api.get_match_detail(match_id)
            except KeyboardInterrupt:
                raise
            except Exception as err:
                print(f"Error retrying {err}")
                time.sleep(self.error_sleep)

    def brute_search(self, dataset=None):
        """Use a match id and fetch all the matches around it"""
        match_id = self.latest_match
        k = 0
        err = 0

        while True:
            match_id += 1
            self.latest_match = match_id
            k += 1

            details = self.get_match_detail(match_id)

            if details.get("error") is not None:
                logger.debug("%s", details)
                continue

            if details is None:
                time.sleep(self.error_sleep)
                err += 1
                continue

            self.known_match[match_id] += 1
            self.matches += 1

            count = self.known_match[match_id]

            if count == 1:
                logger.debug("Write new match")
                self.write_match(dataset, match_id, details)
            else:
                print("Duplicate")

            if err > 10:
                self.running = False
                break

            k = k % 100
            if k == 0:
                print(
                    f"Latest Match: {self.latest_match} | {self.status()} | err {err}"
                )
                print(json.dumps(self.counts, indent=2))

    def run(self):
        # if os.path.exists(name):
        #    print("Cannot override existing file")
        #    return

        server_error = 0
        self.latest_match = self.start_match_id
        self.running = True
        while self.running:
            try:
                self.brute_search(dataset=None)

                print(f"+> Batch done")
                time.sleep(self.batch_sleep)
                print(f"+> Fetching next 500 matches {self.status()}")
            except KeyboardInterrupt:
                self.running = False

            except ServerError:
                server_error += 1
                print("+> Server error retrying")
                if server_error > 3:
                    self.running = False

            except LimitExceeded:
                self.running = False

            except requests.ConnectionError:
                pass

        print(
            f"> Unique Match processed: {len(self.known_match)} Total match: {self.matches}, lastMatch = {self.latest_match}"
        )


class Dota2MatchQuery(Dota2MatchDumper):
    def __init__(self, builder, start_match=None) -> None:
        super().__init__(builder, start_match)
        self.mode = DOTA_GameMode.DOTA_GAMEMODE_AP
        self.pending_matches = []
        self.skill = 1

    def update_latest_date(self, date):
        if self.latest_date is None:
            self.latest_date = date
        else:
            self.latest_date = max(date, self.latest_date) + 1

    def update_latest_match(self, match):
        if self.latest_match is None:
            self.latest_match = match
        else:
            self.latest_match = max(match, self.latest_match) + 1

    def status(self):
        api_call_limit = f"API: {self.api.limit_stats() * 100:6.2f}%"
        match = f"Matches: {self.matches} (unique: {len(self.known_match) * 100 / self.matches:6.2f}%)"
        return f"{api_call_limit} {match}"

    def get_match_history(self, start_at_match_id):
        for i in range(self.error_retry):
            try:
                return self.api.get_match_history(
                    skill=self.skill,
                    min_players=10,
                    count=500,
                    date_min=self.latest_date,
                    start_at_match_id=start_at_match_id,
                    mode=int(self.mode),
                )
            except KeyboardInterrupt:
                raise
            except Exception as err:
                print(f"Error retrying {err}")
                time.sleep(self.error_sleep)


    def fetch_match_ids(self):
        # date_min does not work, we get a lot of duplicate really fast
        # start_at_match_id does not work at all it does seem that the doc was correct and get older match from that id

        remaining = None
        total = None
        results = None
        start_at_match_id = None

        while remaining is None or remaining > 0:
            result = self.get_match_history(start_at_match_id)

            matches = result["matches"]
            results = result["num_results"]
            total = result["total_results"]
            remaining = result["results_remaining"]

            if len(matches) > 0:
                start_at_match_id = matches[-1]["match_id"] + 1
                self.pending_matches.extend(matches)

        print(f"+-> Found {len(self.pending_matches)} matches")
        print(f"        - Results: {results}")
        print(f"        - Total: {total}")
        print(f"        - Remaining: {remaining}")

    def brute_search(self, dataset=None):
        """Fetch new matches"""
        self.fetch_match_ids()

        while self.pending_matches:
            match = self.pending_matches.pop()
            match_id = match["match_id"]

            self.update_latest_date(match["start_time"])
            self.update_latest_match(match_id)

            # We shouldnt see this error if we do be sure we track it to see
            self.known_match[match_id] += 1
            count = self.known_match[match_id]
            self.matches += 1
            if count != 1:
                print(f"+-+> Match duplicate {count} {self.status()}")
                continue
            # ----
            details = self.get_match_detail(match_id)
            if details is None:
                time.sleep(self.error_sleep)
                continue

            self.write_match(dataset, match_id, details)
            time.sleep(self.match_sleep)


class Dota2MatchDatasetBuilder:
    def __init__(self) -> None:
        self.n = 0
        self.m = 0
        self.q = 0
        self.player_id = dict()

        # nunber of time the player was included
        self.player_included = defaultdict(int)
        self.k = 0
        self.batches = None
        self.open_files()

    def open_files(self):
        self.k = 0
        while os.path.exists(f"batches_{self.k}.json"):
            self.k += 1

        self.batches = open(f"batches_{self.k}.json", "w")

    def save(self):
        with open(f"player_{self.k}.json", "w") as fs:
            fs.write(json.dumps(dict(n=self.n, player_id=self.player_id)))
        print(f"N players {self.n}")

    def is_valid(self, data):
        if data.get("radiant_win") is None:
            print(f"Missing dictionnary key radiant_win {data}")
            return False

        # Sanity check
        for p in data["players"]:
            accid = p.get("account_id")
            slot = p.get("player_slot")

            if accid is None:
                print(f"Missing dictionnary key account_id {data}")
                return False

            if slot is None:
                print(f"Missing dictionnary key player_slot {data}")
                return False

        return True

    def process_match(self, match_id, data):
        if not self.is_valid(data):
            return

        radiant_win = int(data["radiant_win"])

        radiant_players = []
        radiant_pair = [radiant_players, radiant_win]

        dire_players = []
        dire_pair = [dire_players, 1 - radiant_win]

        match = [radiant_pair, dire_pair]
        batch = 0

        # process the match
        for p in data["players"]:
            accid = p.get("account_id")

            batch = max(batch, self.get_player_count(accid) - 1)

            if p["player_slot"] < 5:
                arr = radiant_players
            else:
                arr = dire_players

            newid = self.get_player_id(accid)
            arr.append(newid)

        print(f"Unique players {self.n / self.m * 100:5.2f} (Players: {self.n}) (Queryable: {self.q})")
        self.batches.write(json.dumps(dict(batch=batch, id=match_id, matches=match)) + "\n")

    def get_player_count(self, accid):
        if accid == 4294967295:
            return 1

        self.player_included[accid] += 1
        return self.player_included[accid]

    def get_player_id(self, accid):
        newid = self.player_id.get(accid)

        # if newid is none of account is annonymous
        if accid == 4294967295 or newid is None:
            newid = self.n
            self.n += 1

            # only save players if we can rely on its account id
            if accid != 4294967295:
                self.player_id[accid] = newid
                self.q += 1

        self.m += 1
        return newid



def read_players():
    player_ids = dict()
    n = 0
    k = 0
    while os.path.exists(f"player_{k}.json"):
        with open(f"player_{k}.json", "r") as players:
            ids = json.load(players)['player_id']

            for accid, _ in ids.items():
                if accid in player_ids:
                    print('Player is duplicated', accid)
                    continue

                player_ids[accid] = n
                n += 1
        k += 1
    print(n)
    return list(sorted(list(player_ids.keys())))

class Dota2PlayerMatchHistoryQuery(Dota2MatchQuery):
    def __init__(self, players, builder) -> None:
        super().__init__(builder)
        self.players = players

    def get_match_history_for_player(self, account_id, start_at_match_id):
        for i in range(self.error_retry):
            try:
                return self.api.get_match_history(
                    skill=self.skill,
                    min_players=10,
                    count=500,
                    date_min=self.latest_date,
                    start_at_match_id=start_at_match_id,
                    account_id=account_id,
                    mode=int(self.mode),
                )
            except KeyboardInterrupt:
                raise
            except Exception as err:
                print(f"Error retrying {err}")
                time.sleep(self.error_sleep)

    def fetch_match_ids(self):
        # date_min does not work, we get a lot of duplicate really fast
        # start_at_match_id does not work at all it does seem that the doc was correct and get older match from that id

        if len(self.players) == 0:
            print("Fetched match for all players")
            self.running = False
            return

        pid = None
        while pid is None or pid < '999980646':
            pid = self.players.pop()

        remaining = None
        total = None
        results = None
        start_at_match_id = None

        while remaining is None or remaining > 0:
            print(pid, start_at_match_id)
            result = self.get_match_history_for_player(pid, start_at_match_id)
            print(result)

            if result.get('status') == 15:
                break

            matches = result["matches"]
            results = result["num_results"]
            total = result["total_results"]
            remaining = result["results_remaining"]

            if len(matches) > 0:
                start_at_match_id = matches[-1]["match_id"] + 1
                self.pending_matches.extend(matches)

        print(f"+-> Found {len(self.pending_matches)} matches")
        print(f"        - Results: {results}")
        print(f"        - Total: {total}")
        print(f"        - Remaining: {remaining}")



def listen():
    try:
        builder = Dota2MatchDatasetBuilder()

        # the problem with both approaches is that
        # most players are all unique or Anonymous
        # so it is hard to build a database for it
        Dota2MatchQuery(builder).run()


        # Dota2MatchDumper(builder, 6486086331).run()

    except KeyboardInterrupt:
        pass

    builder.save()
    builder.batches.close()
    print("Writing done")



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    try:
        builder = Dota2MatchDatasetBuilder()

        players = read_players()
        Dota2PlayerMatchHistoryQuery(players, builder).run()

    except KeyboardInterrupt:
        pass

    builder.save()
    builder.batches.close()
    print("Writing done")

