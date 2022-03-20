import os

from orion.client import build_experiment

from ranked.datasets.synthetic import SimulationConfig, create_simulated_matchups
from ranked.models.glicko2 import Glicko2
from ranked.models.noskill import NoSkill
from ranked.simulation import Simulation


def optimize(klass, max_trials=1000):
    center = 1500

    try:
        os.remove("orion.pkl")
    except:
        pass

    experiment = build_experiment(
        "mm-calibration",
        space=klass.parameters(center),
        algorithms=None,
        storage={
            "type": "legacy",
            "database": {
                "type": "pickleddb",
                "host": "./orion.pkl",
            },
        },
    )

    experiment.workon(run, center=center, klass=klass, max_trials=max_trials)
    print(experiment.stats)

    experiment.close()


def run(klass, **kwargs):
    ranker = klass(**kwargs)
    objective = synthetic_calibration(ranker)
    print(f"    {objective:6.4f}", kwargs)
    return [dict(name="objective", type="objective", value=-objective)]


def synthetic_calibration(
    ranker, n_matches_bootstrap=100, n_maches_newplayers=20, n_benchmark=100
):
    """Simulates player and their skill estimate"""
    print("Synthetic Benchmark")
    print("===================")

    center = 1500
    var = 64
    beta = 16
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
    sim.simulate(statfs="bootstrap.csv")

    matchup.n_matches = n_benchmark

    # Compute the prediction precision on unseen data
    metrics = sim.benchmark()
    return metrics["ranker_precision"]


if __name__ == "__main__":
    optimize(NoSkill)
