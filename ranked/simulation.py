import json
from collections import defaultdict
from nis import match
from typing import List

from ranked.models import Batch, Match, Player, Ranker, Team


class SaveEvolution:
    def __init__(self, fname: str, pool, ranker) -> None:
        self.fs = open(fname, "w")
        self.header()
        self.ranker = ranker.__class__.__name__
        self.pool = pool

        name = fname.rsplit(".", maxsplit=1)[0]
        self.matchup = open(f"{name}_matchup.csv", "w")

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.fs.__exit__(*args, **kwargs)
        self.matchup.__exit__(*args, **kwargs)

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
    """Simulate ranking estimation evolution using simulated matches

    On one side the matchmaker is working torwards making teams of equal strength
    while the Ranker is estimating the skill of each players from which the win
    probability of a given match can be deduced.

    Notes
    -----
    In case of simulated matchup, the matchmaker and the Ranker are both
    working for and against each other, for each other because the estimated
    skills are used by the matchmaker to produce fair matches,
    but also against because good estimates will enable the matchmaker to
    make the fair matches which will be harder to predict by the ranker,
    lowering its overall precision.

    This means while the ranker's precision should be higher than 50%
    it can never reach high precision levels because of the matchmaker.

    When the matchup are not simulated the precision can reach much higher than
    50% since the matchup are fixed while the Ranker is able to update
    its estimate based on the obersation.

    To measure the precision of the Ranker on real-life data you will need to
    split the dataset on 2 with the older matches being used for training on the
    newer matches being used for benchmarking the prediction precision.
    """

    def __init__(
        self,
        ranker,
        matchups,
    ) -> None:
        self.ranker = ranker
        self.matchups = matchups

    def simulate(self, statfs="simulation.csv", filter=None):
        last_print = 0

        with SaveEvolution(statfs, self.matchups.pool, self.ranker) as saver:
            for i, batch in enumerate(self.matchups.matches()):
                # `train`/refine the estimation
                self.ranker.update(batch)

                saver.save(i, self.ranker.__class__.__name__, filter)

                if (i + 1) % 100 == 0:
                    last_print = i
                    print(f"    Simulated {i + 1} matches")

            if i != last_print:
                print(f"    Simulated {i + 1} matches")

    def benchmark(self):
        """Use the latest skill estimate for each player and estimate the win probabilities
        for each matchup, if the Ranker estimated their skill corectly the precision should higher than 50%
        """
        acc = 0
        count = 0
        batch: Batch
        match: Match
        team: Team
        stats = dict()

        team_skill = defaultdict(float)
        diff = 0
        match_count = 0

        for _, batch in enumerate(self.matchups.matches()):

            for match in batch.matches:
                estimated_leaderboard = []
                avg = 0

                for i, team in enumerate(match.teams):
                    # estimated skill of the time
                    tskill = team.skill()

                    # average skill per team
                    team_skill[i] += tskill

                    # average skill per match
                    avg += tskill

                    team_score = tskill
                    estimated_leaderboard.append((team, team_score))

                # average skill diff in this match
                avg = avg / len(match.teams)
                avg_diff = sum([abs(team.skill() - avg) for team in match.teams]) / len(
                    match.teams
                )

                diff += avg_diff
                match_count += 1

                # sort both
                estimated_leaderboard.sort(key=lambda item: item[1])

                leaderboard = list(match.leaderboard)
                leaderboard.sort(key=lambda item: item[1])

                # if teams match then the prediction was correct
                for (t1, _), (t2, _) in zip(estimated_leaderboard, leaderboard):
                    if t1 is t2:
                        acc += 1
                    count += 1

        # how often is the team the highest score wins
        # bigger is better
        stats["ranker_precision"] = acc / count

        # The average score difference between teams
        # smaller is better
        stats["matchmaker_diff"] = diff / match_count

        # Overall skill for every team should be even
        # regardless of their position inside the team array
        avg = sum([v for _, v in team_skill.items()]) / len(team_skill)
        avg_diff = sum([abs(v) - avg for _, v in team_skill.items()]) / len(team_skill)

        # Is the matchmaker biased toward a team
        # should be 0
        stats["matchmaker_team_bias"] = avg_diff

        return stats


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


def synthetic_main(n_matches_bootstrap=100, n_maches_newplayers=100, n_benchmark=100):
    """Simulates player and their skill estimate"""
    print("Synthetic Benchmark")
    print("===================")

    from ranked.datasets.synthetic import SimulationConfig, create_simulated_matchups
    from ranked.models.glicko2 import Glicko2
    from ranked.models.noskill import NoSkill

    center = 1500
    var = 64
    beta = 0
    n_players = 100

    config = SimulationConfig(
        # Distribution of the skills of the entire player pool
        #   How spread the skill is between players
        #   This is a representation on how complex your game is
        skill_mean=center,
        skill_volatility=500 / 3,  # so the results are [1000, 200]
        # Consistency of the players (innate)
        #   The more consistent player are the faster they will
        #   reach their true skill level
        consistency_variability_lower=var / 2,
        consistency_variability_upper=var,
        # How randomness impacts the player' score
        #   More randomness will make it harder for the Ranker
        #   to identify the player's true skill level
        game_randomness=beta,
    )

    # Note that the number representing the skill
    # is totally arbitrary because we are in a simulation
    # we know the real value and we set our ranker
    # to match the simulation to help with interpreting the
    # results but the scale between the two could be different
    ranker = Glicko2(
        # Useless mostly cosmetic
        center,
        # How fast can the score change
        500 / 2,
        # Constrain the volatility change of a player
        # prevent big rating changes from unlikely outcome
        tau=0.2,
    )

    ranker = NoSkill(
        center,
        500 / 3,
        beta,
        tau=0.2,
        draw_probability=0,
    )

    matchup = create_simulated_matchups(
        ranker,
        n_players,
        n_matches=n_matches_bootstrap,
        n_team=2,
        n_player_per_team=5,
        config=config,
    )

    sim = Simulation(ranker, matchup)

    # Create the initial pool of players
    print("1. Bootstrap Player pool")
    sim.simulate(statfs="bootstrap.csv")

    # Benchmark
    print("2. Benchmark")
    matchup.n_matches = n_benchmark
    for k, v in sim.benchmark().items():
        print(f"{k:>30}: {v}")

    # Check how new players are doing
    print("3. Add New Players")

    # Current pool of players have a perfect estimate
    matchup.set_estimate_to_truth()

    # If we add 2 players at the same time they might endup being
    # teamed up together
    matchup.add_player(center + 3 * var, var * 0.5)
    # matchup.add_player(center - 3 * var, var * 0.5)

    # force save the new model with the new players
    matchup.save("matchup.csv")

    matchup.n_matches = n_maches_newplayers
    sim.simulate(statfs="newplayers.csv", filter=n_players)

    # Plot skill estimation trajectories
    print("4. Generate Graphs")
    bootstrap = load_skill_evolution("bootstrap.csv")
    newplayers = load_skill_evolution("newplayers.csv")

    boot_chart = skill_estimate_evolution(bootstrap)
    new_chart = skill_estimate_evolution(newplayers)

    (boot_chart & new_chart).save("evol.html")


if __name__ == "__main__":
    synthetic_main()
