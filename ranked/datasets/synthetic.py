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

    def save(self, iter, fs, method):
        rows = []
        for p in self.players:
            cols = [
                str(iter),
                str(p.pid),
                "truth",
                str(p.truth.skill),
                str(p.truth.consistency),
                str(method),
            ]
            rows.append(", ".join(cols))
            cols = [
                str(iter),
                str(p.pid),
                "estimate",
                str(p.estimation.skill()),
                str(p.estimation.consistency()),
                str(method),
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

    # Reduce variance since our player pool is small
    center = 1500
    var = 128
    beta = 128

    ranker = Glicko2(center=center, scale=var * 0.8)
    # ranker = NoSkill(mu=center, sigma=var * 0.8)

    # Generates 10'000 players
    pool = SyntheticPlayerPool(50, center, beta)

    # Group players in teams
    mm = Matchmaker(pool, pool.player_pool, ranker, 2, 5)

    with open("evol.csv", "w") as evol:
        evol.write(f"#match,pid,type,skill,cons,method\n")

        # Play 100 matches for each player
        for i in range(100):
            ranker.update(mm.matches())
            mm.save(i, evol, ranker.__class__.__name__)

            if i % 100 == 0:
                print(i)

    # Visualize the progress
    import altair as alt
    import pandas as pd

    evol = pd.read_csv("evol.csv")

    highlight = alt.selection(
        type="single", on="mouseover", fields=["pid"], nearest=True
    )

    estimate = alt.Chart(evol).encode(
        x="#match:Q",
        y=alt.Y("skill:Q", scale=alt.Scale(domain=[1000, 2000])),
        color="pid:N",
        strokeDash="type:N",
    )

    points = (
        estimate.mark_circle()
        .encode(opacity=alt.value(0))
        .add_selection(highlight)
        .properties(width=600)
    )

    lines = estimate.mark_line().encode(
        size=alt.condition(~highlight, alt.value(1), alt.value(3))
    )

    (points + lines).save(f"evol.html")

    eskill_distribution = (
        alt.Chart(evol)
        .mark_bar(color="rgba(0, 0, 125, 0.5)")
        .encode(
            alt.X(
                "skill:Q",
                bin=alt.Bin(maxbins=20),
                scale=alt.Scale(domain=[1000, 2000]),
            ),
            y="count()",
            color="type",
        )
    )

    eskill_distribution.save(f"skill_dist.html")


if __name__ == "__main__":
    simulate()
