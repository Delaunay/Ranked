import math
from typing import List, Tuple
import json

from scipy.stats import norm, uniform

from ranked.models.interface import Batch, Match, Player, Ranker, Team
from ranked.matchmaker import Matchmaker


class MatchmakerReplaySaver:
    def __init__(self, filename) -> None:
        self.replay = open(filename, "w")

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

        self.replay.write(json.dumps(saved) + "\n")


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

    @property
    def players(self):
        return self.player_pool

    def performance(self, pid):
        return self.player_pool[pid].performance(self)

    def new_player(self, skill=None, consistency=None) -> GenPlayer:
        # Sample player skill & consistency
        skill = skill or self.skill_distribution.rvs()
        consistency = consistency or self.consistency_distribution.rvs()
        return GenPlayer(skill, consistency)


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

    def __init__(
        self, ranker: Ranker, model: SyntheticPlayerPool, pool: List[Player]
    ) -> None:
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
        self.fs = open(fname, "w")
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

        with open("model.csv", "w") as fs:
            fs.write(f"pid,skill,cons\n")

            for i, p in enumerate(players):
                if player_filter and i < player_filter:
                    continue

                cols = [str(i), str(p.skill), str(p.consistency)]
                rows.append(", ".join(cols))

            fs.write("\n".join(rows) + "\n")

    def header(self):
        self.fs.write(f"#match,pid,skill,cons,method\n")

    def save(self, iter, method, player_filter=None):
        rows = []
        for pid, p in enumerate(self.pool):
            if player_filter and pid < player_filter:
                continue

            cols = [
                str(iter),
                str(pid),
                str(p.skill()),
                str(p.consistency()),
                str(self.ranker),
            ]
            rows.append(", ".join(cols))

        self.fs.write("\n".join(rows) + "\n")


class Simulation:
    def __init__(
        self, ranker, center=1500, var=128 * 0.8, beta=128, n_players=100
    ) -> None:
        self.center = center
        self.var = var
        self.beta = beta
        self.n_players = n_players
        self.ranker = ranker
        self.pool = None
        self.model = None

    def add_player(self, *args):
        """Insert new players to the player pool"""
        if self.pool is None:
            raise RuntimeError("No existing player pool, call `bootstrap` first")

        p = self.model.new_player(*args)
        self.model.player_pool.append(p)
        self.pool.append(self.ranker.new_player())

    def bootstrap(self, n_matches, statfs="bootstrap.csv"):
        """Create a new pool of players and simulate n_matches

        Notes
        -----

        The goal here is to see the skill estimate reach its truth level as fast as possible without too much noise.
        So player can start playing in their skill bracket fast & start improving & discorvering new strategies.

        Returns
        -------
        the model and the final skill estimation for each players
        """

        # Generates 10'000 players
        self.model = SyntheticPlayerPool(self.n_players, self.center, self.beta)

        # Initialize the players
        self.pool = [self.ranker.new_player() for _ in range(self.n_players)]

        self.simulate(n_matches, statfs)

    def simulate(self, n_matches, statfs="simulation.csv", filter=None):
        """Simulate n matches"""

        # Part of the simulation
        mm = Matchmaker(self.pool, 2, 5)
        sim = SimulateMatch(self.ranker, self.model, self.pool)

        with SaveEvolution(statfs, self.pool, self.ranker) as saver:
            saver.save_model(self.model)

            # Play 100 matches for each player
            for i in range(n_matches):

                # Group players in teams
                for match in mm.matches():

                    # Simulate match outcomes
                    result = sim.simulate(match)

                    # Update simulated skill
                    self.ranker.update(result)

                    saver.save_outcome(match, result)

                saver.save(i, self.ranker.__class__.__name__, filter)

                if i % 100 == 0:
                    print(i)

    def newplayers(self, n_matches, statfs="newplayers.csv"):
        """Add new players to the current pool of players & simulate

        Notes
        -----

        The goal here is to minimize the number of calibration games necessary for the player
        to reach its skill bracket & avoid too big jumps in rating
        """

        if self.pool is None:
            raise RuntimeError("No existing player pool, call `bootstrap` first")

        # a new players to the pool
        self.add_player(self.center + 3 * self.var, self.var * 0.5)
        self.add_player(self.center - 3 * self.var, self.var * 0.5)

        self.simulate(n_matches, statfs, filter=self.n_players)


def skill_estimate_evolution(dataframe):
    import altair as alt

    highlight = alt.selection(
        type="single", on="mouseover", fields=["pid"], nearest=True
    )

    chart = alt.Chart(dataframe).encode(
        x="#match:Q",
        y=alt.Y("skill:Q", scale=alt.Scale(domain=[1000, 2000])),
        color="pid:N",
        strokeDash="type:N",
    )

    points = (
        chart.mark_circle()
        .encode(opacity=alt.value(0))
        .add_selection(highlight)
        .properties(width=600)
    )

    lines = chart.mark_line().encode(
        size=alt.condition(~highlight, alt.value(1), alt.value(3))
    )

    return points + lines


def skill_distribution(dataframe):
    import altair as alt

    eskill_distribution = (
        alt.Chart(dataframe)
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

    return eskill_distribution


def load_skill_evolution(filename):
    import pandas as pd

    evol = pd.read_csv(filename)
    model = pd.read_csv("model.csv")

    # This creates a new column with the truth
    # data = pd.merge(evol, model, how="left", on=["pid"], suffixes=("", "_truth"))
    n_match = evol["#match"].max()
    n_players = evol["pid"].min()

    evol["type"] = "estimate"
    model["type"] = "truth"
    model["#match"] = 0

    modeln = model.copy()
    modeln["#match"] = n_match

    data = pd.concat([evol, model, modeln], join="inner")
    return data[data["pid"] >= n_players]


if __name__ == "__main__":
    from ranked.models.glicko2 import Glicko2
    from ranked.models.noskill import NoSkill

    center = 1500
    var = 128 * 0.8
    beta = 128
    n_matches = 20
    n_players = 100

    ranker = Glicko2(center, var)

    sim = Simulation(ranker, center, var, beta, n_players)

    # Create the initial pool of players
    print("Bootstrap Player pool")
    sim.bootstrap(n_matches=100)

    # Check how new players are doing
    print("Add New PLayers")
    sim.newplayers(n_matches=20)

    print("Compile data")
    bootstrap = load_skill_evolution("bootstrap.csv")
    newplayers = load_skill_evolution("newplayers.csv")

    boot_chart = skill_estimate_evolution(bootstrap)
    new_chart = skill_estimate_evolution(newplayers)

    (boot_chart & new_chart).save("evol.html")
