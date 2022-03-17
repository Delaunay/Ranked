import math
from typing import List, Tuple
import json

from scipy.stats import norm, uniform

from ranked.models.interface import Batch, Match, Player, Ranker, Team
from ranked.matchmaker import Matchmaker


class MatchmakerReplaySaver:
    def __init__(self, filename) -> None:
        self.replay = open(filename, 'w')

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.replay.__exit__(*args, **kwargs)

    def save(self, teams):
        if self.replay is None:
            return

        saved = []
        for t in teams:
            players = []

            for p in t:
                players.append(p.pid)

            saved.append(players)

        self.replay.write(json.dumps(saved) + '\n')


class GenPlayer:
    """Simulated player performance"""

    def __init__(self, skill: float, consistency: float) -> None:
        self.skill = skill
        self.consistency = consistency

    def performance(self, model):
        """Sample a performance rating from the player"""
        skill = norm(self.skill, self.consistency).rvs()
        return norm(skill, model.perf_vol).rvs()


class SyntheticPlayerPool:
    """Simulate a pool of players and their performance"""

    def __init__(self, count, smu=25, svol=25 / 3) -> None:
        self.skill_distribution = norm(smu, svol)
        self.consistency_distribution = uniform(smu ** -4, math.sqrt(smu))
        self.perf_vol = svol / 2
        self.player_pool = [self.new_player() for _ in range(count)]

    def performance(self, pid):
        return self.player_pool[pid].performance()

    def new_player(self, skill=None, consistency=None) -> GenPlayer:
        # Sample player skill & consistency
        skill = skill or self.skill_distribution.rvs()
        consistency = consistency or self.consistency_distribution.rvs()
        return GenPlayer(skill, consistency)



def add_player(ranker, model, pool, *args):
     p = model.new_player(*args)
     model.player_pool.append(p)
     pool.append(ranker.new_player())



class SimulateMatch:
    """Simulate the outcome of a given match

    Parameters
    ----------

    ranker:
        System use to rank players

    model:
        Model used to simulate players

    pool:
        List of players

    """
    def __init__(self, ranker: Ranker, model: SyntheticPlayerPool, pool: List[Player]) -> None:
        self.pool = pool
        self.model = model
        self.ranker = ranker

    def simulate(self, teams: List[List[int]]) -> Match:
        """Simulate the outcome of a given match

        Parameters
        ----------
        teams:
            List of teams competing in this match

        Returns
        -------
        a Match object which contains the scoreboard of the simulated match
        it can be passed to a Ranker to update the skill.
        """
        scoreboard: List[Tuple[Team, float]] = []

        for team in teams:
            score = 0
            for player_id in team:
                score += self.model.performance(player_id)

            # Generate a Ranker Team to run our algo
            team = self.ranker.new_team(*[self.pool[player_id] for player_id in team])
            scoreboard.append((team, score))

        return Match(*scoreboard)


class SaveEvolution:
    def __init__(self, fname, pool, ranker) -> None:
        self.fs = open(fname, 'w')
        self.header()
        self.ranker = ranker.__class__.__name__
        self.pool = pool

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.fs.__exit__(*args, **kwargs)

    def save_outcome(self, match, result):
        pass

    def save_model(self, model, player_filter=None):
        rows = []

        players = model.players

        with open('model.csv') as fs:
            fs.write(f"pid,skill,cons\n")

            for i, p in enumerate(players):
                if player_filter and i < player_filter:
                    continue


                cols = [
                    i,
                    p.skill,
                    p.consistency
                ]
                rows.append(', '.join(cols))

        fs.write("\n".join(rows) + "\n")

    def header(self):
        self.fs.write(f"$match,pid,skill,cons,method\n")

    def save(self, iter, method, player_filter=None):
        rows = []
        for p in self.pool:
            if player_filter and p.pid < player_filter:
                continue

            cols = [
                str(iter),
                str(p.pid),
                str(p.skill()),
                str(p.consistency()),
                str(self.ranker),
            ]
            rows.append(", ".join(cols))

        self.fs.write("\n".join(rows) + "\n")


def simulate_new_players(
    center=1500, var=128 * 0.8, beta=128, n_matches=20, n_players=100
):
    """Simulate arrival of new players & focus on its trajectory.

    Notes
    -----

    The goal here is to minimize the number of calibration games necessary for the player
    to reach its skill bracket & avoid too big jumps in rating
    """

    from ranked.models.glicko2 import Glicko2
    from ranked.models.noskill import NoSkill

    ranker = Glicko2(center=center, scale=var * 0.8)
    # ranker = NoSkill(mu=center, sigma=var)

    # Create the initial pool of players and bootstrap it
    model, pool = simulate_bootstrapping(ranker, center, var, beta, n_players)

    # a new players to the pool
    add_player(ranker, model, pool, center + 3 * var, var * 0.5)
    add_player(ranker, model, pool, center - 3 * var, var * 0.5)

    mm = Matchmaker(pool, ranker, 2, 5)
    sim = SimulateMatch(ranker, model, pool)

    with SaveEvolution("evol.csv", pool, ranker) as saver:
        saver.save_model(model)

        # Play 100 matches for each player
        for i in range(n_matches):

            # Group players in teams
            for match in mm.matches():

                # Simulate match outcomes
                result = sim.simulate(match)

                # Update simulated skill
                ranker.update(result)

            saver.save(i)


def simulate_bootstrapping(
    ranker, center=1500, var=128 * 0.8, beta=128, n_players=50, n_matches=100
):
    """Start with a pool of new player.

    Notes
    -----

    The goal here is to see the skill estimate reach its truth level as fast as possible without too much noise.
    So player can start playing in their skill bracket fast & start improving & discorvering new strategies.

    Returns
    -------
    the model and the final skill estimation for each players
    """
    # Generates 10'000 players
    model = SyntheticPlayerPool(n_players, center, beta)

    # Initialize the players
    pool = [ranker.new_player() for _ in range(n_players)]

    # Part of the simulation
    mm = Matchmaker(pool, ranker, 2, 5)
    sim = SimulateMatch(ranker, model, pool)

    with SaveEvolution("evol.csv", pool, ranker) as saver:
        saver.save_model(model)

        # Play 100 matches for each player
        for i in range(n_matches):

            # Group players in teams
            for match in mm.matches():

                # Simulate match outcomes
                result = sim.simulate(match)

                # Update simulated skill
                ranker.update(result)

                saver.save_outcome(match, result)

            saver.save(i)

            if i % 100 == 0:
                print(i)

    return model, pool


def visualize_evolution():
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
    # simulate_bootstrapping()
    simulate_new_players()
    visualize_evolution()
