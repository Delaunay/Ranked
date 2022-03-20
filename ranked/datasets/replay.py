import json

from ranked.datasets import Matchup
from ranked.models import Batch, Match


class ReplayMatchup(Matchup):
    """Returns a batch of matchups, each batch have each players once.
    The matches are sorted by ascending timestamp.

    This means that the first batch represent the first match for each player.
    second batch second match, etc...


    Parameters
    ----------
    ranker:
        Ranker object used to create teams

    pool:
        Pool of player

    matchupfs:
        Name of the file containing the replay data

    """

    def __init__(self, ranker, pool, matchupfs: str) -> None:
        self.ranker = ranker
        self.matches = []
        self.batches = []
        self.pool = pool
        self.step = 0

        with open(matchupfs, "r") as data:
            for line in data.readline():
                #
                match = json.loads(line)

                batch = match.get("batch")
                teams = match.get("teams")
                leaderboard = []

                for team in teams:
                    players = team["players"]
                    score = team["score"]

                    t1 = self.ranker.new_team(
                        *[self.pool[player_id] for player_id in players]
                    )
                    leaderboard.append((t1, score))

                m = Match(*leaderboard)
                if batch is not None:
                    self.batches.append((batch, m))

                self.matches.append(m)

        self.batches.sort(key=lambda item: item[0])

    def matches(self) -> Batch:
        for b in self.batches:
            yield b
