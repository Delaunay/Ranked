from typing import List, Tuple

import numpy as np

from ranked.models import Batch, Match, Player, Ranker, Team

# List of player matched together
MatchMakerTeam = List[int]
# List of teams of a given match
MatchMakerMatch = List[MatchMakerTeam]


class Matchmaker:
    """Build teams of player based on their estimated skill bracket.
    The goal of the matchmaker is to builds teams of similar strength
    to gives every teams a fair chance of winning.

    Notes
    -----

    * Party support requires its own matchmaker
    """

    def __init__(self, pool: List[Player], n_team: int = 2, n_players: int = 5) -> None:
        # players should never be reordered
        self.players = pool
        self.first_player = self.players[0]

        # players_pid can be shuffled
        self.players_pid = [i for i, _ in enumerate(pool)]

        self.n_team = n_team
        self.n_players = n_players
        self.n_player_match = self.n_team * self.n_players
        self.n_matches = len(self.players) // self.n_player_match
        self.saver = None

    def save_replay(self, saver):
        self.saver = saver

    def matches(self) -> List[MatchMakerMatch]:
        # sort players by their estimated skill
        self.players_pid.sort(key=lambda item: self.players[item].skill())

        s = 0
        e = self.n_player_match
        batch: List[MatchMakerMatch] = []

        for i in range(self.n_matches):
            teams: List[MatchMakerTeam] = [[] for _ in range(self.n_team)]

            # shallow copy
            pool = [p for p in self.players_pid[s:e]]

            # Shuffle; we want the teams to be random
            # if we have a lot of players then the skill between them
            # should be very close
            #
            # if not this is not going to be that good
            np.random.shuffle(pool)

            for j in range(self.n_player_match):
                team = j % self.n_team
                teams[team].append(pool[j])

            batch.append(teams)

            s = e
            e += self.n_player_match

        # players cannot be shuffled
        # we rely on the order to give use the player id
        assert self.first_player is self.players[0]
        return batch
