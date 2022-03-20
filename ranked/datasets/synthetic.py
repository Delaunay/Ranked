import json
import math
from dataclasses import dataclass
from typing import List, Tuple

from scipy.stats import norm, uniform

from ranked.datasets import Matchup
from ranked.matchmaker import Matchmaker
from ranked.models import Batch, Match, Player, Ranker, Team


class MatchupReplaySaver:
    """Save simulated matchup so they can be replayed"""

    def __init__(self, filename) -> None:
        self.replay = open(filename, "w")

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.replay.__exit__(*args, **kwargs)

    def save_pool(self, pool):
        self.replay.write(json.dumps([p.to_json() for p in pool]) + "\n")

    def save(self, batch, teams: List[List[int]], match: Match):
        cols = []
        for (team_obj, score), team in zip(match.leaderboard, teams):
            team_info = dict(
                players=team,
                score=score,
                skill=team_obj.skill(),
            )
            cols.append(team_info)

        self.replay.write(json.dumps(dict(batch=batch, teams=cols)) + "\n")

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


class GenPlayer:
    """Simulated player performance"""

    def __init__(self, skill: float, consistency: float) -> None:
        self.skill = skill
        self.consistency = consistency

    def performance(self, model):
        """Sample a performance rating from the player"""
        skill = norm(self.skill, self.consistency).rvs()
        return norm(skill, model.perf_vol).rvs()

    @property
    def args(self):
        return (self.skill, self.consistency)


@dataclass
class SimulationConfig:
    skill_mean: float = 25
    skill_volatility: float = 25 / 3
    consistency_variability_lower: float = 0
    consistency_variability_upper: float = 10
    game_randomness: float = 1


class SyntheticPlayerPool:
    """Simulate a pool of players and their performance"""

    def __init__(self, count, config: SimulationConfig = SimulationConfig()) -> None:
        self.skill_distribution = norm(config.skill_mean, config.skill_volatility)
        self.consistency_distribution = uniform(
            config.consistency_variability_lower,
            config.consistency_variability_upper,
        )
        self.perf_vol = config.game_randomness
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


class SimulatedMatchup(Matchup):
    def __init__(
        self, ranker, pool, model, n_matches, n_team, n_player_per_team
    ) -> None:
        self.model = model
        self._pool = pool
        self.n_team = n_team
        self.mm = None
        self.n_player_per_team = n_player_per_team
        self.sim = SimulateMatch(ranker, model, pool)
        self.saver = None
        self.batch_id = 0
        self.n_matches = n_matches
        self.ranker = ranker
        self.reset()

    def set_estimate_to_truth(self):
        """Update current estimate to match the simulated skill.
        This function is useful to benchmark score evolution in a
        existing pool of players or to benchmark the matchmaker when the skill is known
        """
        for i, truth in enumerate(self.model.players):
            self._pool[i] = self.ranker.new_player(*truth.args)

        # reset the matchmaker so he uses the updated pool
        self.reset()

    def save(self, fname: str):
        """Enable saving of the matchup during a simulation"""
        self.saver = MatchupReplaySaver(fname)
        self.saver.save_model(self.model)
        self.saver.save_pool(self._pool)

    def add_player(self, *args):
        """Insert new players to the player pool"""
        if self.pool is None:
            raise RuntimeError("No existing player pool")

        p = self.model.new_player(*args)
        self.model.player_pool.append(p)
        self._pool.append(self.ranker.new_player())

        # reset the matchmaker so he uses the updated pool
        self.reset()

    def replace_player(self, *args, i=-1):
        """Replace an older player with a new one"""
        if self.pool is None:
            raise RuntimeError("No existing player pool")

        p = self.model.new_player(*args)
        self.model.player_pool[i] = p
        self._pool[i] = self.ranker.new_player()

        # reset the matchmaker so he uses the updated pool
        self.reset()

    def reset(self):
        self.mm = Matchmaker(self._pool, self.n_team, self.n_player_per_team)

    @property
    def pool(self):
        return self._pool

    def matches(self) -> Batch:
        for i in range(self.n_matches):
            batch = []

            # Group players in teams
            for teams in self.mm.matches():

                # Simulate match outcomes
                result: Match = self.sim.simulate(teams)

                if self.saver is not None:
                    self.saver.save(i, teams, result)

                batch.append(result)

            yield Batch(*batch)


def create_simulated_matchups(
    ranker,
    n_players,
    n_matches,
    n_team,
    n_player_per_team,
    config=SimulationConfig(),
    pool=None,
    model=None,
) -> SimulatedMatchup:
    """Generate new players from a model and initialize a SimulatedMatchup dataset"""
    if model is None:
        model = SyntheticPlayerPool(n_players, config)

    if pool is None:
        pool = [ranker.new_player() for _ in range(n_players)]

    return SimulatedMatchup(ranker, pool, model, n_matches, n_team, n_player_per_team)
