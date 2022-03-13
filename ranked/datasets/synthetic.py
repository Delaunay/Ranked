import copy
import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from scipy.stats import norm, uniform

from ranked.models.interface import Batch, Match, Player, Ranker, Team


class GenPlayer:
    def __init__(self, skill: float, consistency: float) -> None:
        self.skill = skill
        self.consistency = consistency

    def performance(self, model):
        """Sample a performance rating from the player"""
        skill = norm(self.skill, self.consistency).rvs()
        return norm(skill, model.perf_vol).rvs()


@dataclass
class MMPlayer:
    pid: int
    truth: GenPlayer
    estimation: Player


def gen_match(model, ranker: Ranker, teams: List[List[MMPlayer]]) -> Match:
    ranks: List[Tuple[Team, float]] = []

    for team in teams:
        score = 0
        for player in team:
            score += player.truth.performance(model)

        # Generate a Ranker Team to run our algo
        team = ranker.new_team(*[p.estimation for p in team])
        ranks.append((team, score))

    return Match(*ranks)


class Matchmaker:
    def __init__(
        self, model, players, ranker: Ranker, n_team: int = 2, n_players: int = 5
    ) -> None:
        self.players = [
            MMPlayer(i, p, ranker.new_player()) for i, p in enumerate(players)
        ]
        self.n_team = n_team
        self.n_players = n_players
        self.n_player_match = self.n_team * self.n_players
        self.n_matches = len(self.players) // self.n_player_match
        self.ranker = ranker
        self.model = model

    def matches(self) -> Batch:
        # sort players by their estimated skill
        self.players.sort(key=lambda item: item.estimation.skill())

        s = 0
        e = self.n_player_match
        batch: List[Match] = []

        for i in range(self.n_matches):
            teams = [[] for _ in range(self.n_team)]

            # shallow copy
            pool = [p for p in self.players[s:e]]

            # Shuffle we want the teams to be random
            # if we have a lot of players then the skill between them
            # should be very close
            np.random.shuffle(pool)

            for j in range(self.n_player_match):
                team = j % self.n_team
                teams[team].append(pool[j])

            # Compute performance and append the match
            batch.append(gen_match(self.model, self.ranker, teams))

            s = e
            e += self.n_player_match

        return Batch(*batch)

    def save(self, iter, fs):
        rows = []
        for p in self.players:
            cols = [
                str(iter),
                str(p.pid),
                str(p.truth.skill),
                str(p.truth.consistency),
                str(p.estimation.skill()),
                str(p.estimation.consistency()),
            ]
            rows.append(", ".join(cols))

        fs.write("\n".join(rows) + "\n")


class SyntheticPlayerPool:
    """Generate Match data from players, players do not improve, the system needs
    to infer their level from the noisy obersavton
    """

    def __init__(self, count, smu=25, svol=25 / 3) -> None:
        self.skill_distribution = norm(smu, svol)
        self.consistency_distribution = uniform(smu ** -4, math.sqrt(smu))
        self.perf_vol = svol / 2
        self.player_pool = [self.new_player() for _ in range(count)]

    def new_player(self) -> GenPlayer:
        # Sample player skill & consistency
        skill = self.skill_distribution.rvs()
        consistency = self.consistency_distribution.rvs()
        return GenPlayer(skill, consistency)


def simulate():
    from ranked.models.glicko2 import Glicko2
    from ranked.models.noskill import NoSkill

    ranker = Glicko2()

    center = 1500
    var = 173

    # Generates 10'000 players
    pool = SyntheticPlayerPool(40, center, var)

    # Group players in teams
    mm = Matchmaker(pool, pool.player_pool, ranker, 2, 5)

    with open("evol.csv", "w") as evol:
        evol.write(f"iter,pid,tskill,tcons,eskill,econs\n")

        # Play 100 matches for each player
        for i in range(100):
            ranker.update(mm.matches())
            mm.save(i, evol)

    # Visualize the progress
    import altair as alt
    import pandas as pd

    evol = pd.read_csv("evol.csv")

    estimate = (
        alt.Chart(evol)
        .mark_line()
        .encode(
            x="iter:Q",
            y=alt.Y("eskill:Q", scale=alt.Scale(domain=[1000, 2000])),
            color="pid:N",
        )
    )

    truth = (
        alt.Chart(evol)
        .mark_line(strokeDash=[1, 1])
        .encode(
            x="iter:Q",
            y=alt.Y("tskill:Q", scale=alt.Scale(domain=[1000, 2000])),
            color="pid:N",
        )
    )

    (estimate + truth).save(f"evol.html")


if __name__ == "__main__":
    simulate()
