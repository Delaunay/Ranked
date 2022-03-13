import math
from collections import defaultdict
from typing import Tuple

from ranked.interface import Batch, Match, Player, Ranker, Team


class Glicko2Player(Player):
    def __init__(self, rating=1500, deviation=350, volatility=0.06) -> None:
        self.rating: float = rating
        self.deviation: float = deviation
        self.volatility: float = volatility

    def skill(self) -> float:
        return self.rating

    def interval(self) -> Tuple[float, float]:
        eps = 2 * self.deviation
        return self.rating - eps, self.rating + eps


class Glicko2Team(Team):
    """Combine multiple players and make them look like one to the algorithm"""

    def __init__(self, *players, **config) -> None:
        super().__init__(*players, **config)
        self._rating = None
        self._deviation = None
        self._volatility = None

    def reset(self):
        self._rating = None
        self._deviation = None
        self._volatility = None

    @property
    def rating(self):
        if self._rating is None:
            self._rating = sum([p.rating for p in self.players])
        return self._rating

    @property
    def deviation(self):
        if self._deviation is None:
            self._deviation = math.sqrt(sum([p.deviation ** 2 for p in self.players]))
        return self._deviation

    @property
    def volatility(self):
        if self._volatility is None:
            self._volatility = math.sqrt(sum([p.volatility ** 2 for p in self.players]))
        return self._volatility

    @rating.setter
    def rating(self, value):
        diff = value - self.rating

        for p in self.players:
            p.rating += diff * (p.rating / self.rating)

        self._rating = None

    @deviation.setter
    def deviation(self, value):
        diff = value - self.deviation

        for p in self.players:
            p.deviation += diff * (p.deviation / self.deviation)

        self._deviation = None

    @volatility.setter
    def volatility(self, value):
        diff = value - self.volatility

        for p in self.players:
            p.volatility += diff * (p.volatility / self.volatility)

        self._volatility = None


def cache(func):
    def wrapper(self, *args):
        r = self.cache.get((func, args))

        if r is None:
            r = func(self, *args)
            self.cache[(func, args)] = r

        self.hits[(func, args)] += 1
        return r

    return wrapper


class Glicko2(Ranker):
    """Glicko extend the Elo system to take into account the consistency/reliability of the skill"""

    # System constants
    TAU = (0.3 + 1.2) / 2
    TAU = 0.5
    EPS = 0.000001

    CENTER = 1500
    SCALE = 173.7178

    def __init__(self, tau=None) -> None:
        if tau is not None:
            self.TAU = tau

        self.cache = dict()
        self.hits = defaultdict(int)

    def new_player(self, *args) -> Glicko2Player:
        return Glicko2Player(*args)

    def new_team(self, *players, **config) -> Glicko2Team:
        return Glicko2Team(*players, **config)

    @cache
    def mu(self, player: Glicko2Player) -> float:
        return (player.rating - self.CENTER) / self.SCALE

    @cache
    def phi(self, player: Glicko2Player) -> float:
        return player.deviation / 173.7178

    @cache
    def g(self, player: Glicko2Player) -> float:
        return 1 / math.sqrt(1 + 3 * self.phi(player) ** 2 / math.pi ** 2)

    @cache
    def expectation(self, player: Glicko2Player, enemy: Glicko2Player) -> float:
        """Estimated win probably against a given ennemy"""
        return 1 / (1 + math.exp(-self.g(enemy) * (self.mu(player) - self.mu(enemy))))

    @cache
    def estimated_variance(self, player: Glicko2Player, matches: Batch) -> float:
        """Step 3: Compute the quantity v;
        This is the estimated variance of the team's/players's rating based only on game outcomes

        """
        v = 0

        for match in matches:
            enemy = match.get_enemy(player)

            p = self.expectation(player, enemy)
            v += (self.g(enemy) ** 2) * p * (1 - p)

        return 1 / v

    @cache
    def delta(self, player: Glicko2Player, matches: Batch) -> float:
        """Step 4: Compute the quantity delta; the estimated improvement in rating
        by comparing the pre-period rating to the performance rating based only on game outcomes

        """
        delta = 0
        v = self.estimated_variance(player, matches)

        for match in matches:
            enemy = match.get_enemy(player)
            result = (match.get_result(player) + 1) / 2

            delta += self.g(enemy) * (result - self.expectation(player, enemy))

        return v * delta

    @cache
    def estimate_volatility(self, player: Glicko2Player, matches: Batch) -> float:
        delta = self.delta(player, matches)
        v = self.estimated_variance(player, matches)
        ca = math.log(player.volatility ** 2)

        def f(x):
            top = math.exp(x) * (delta ** 2 - self.phi(player) ** 2 - v - math.exp(x))
            bot = 2 * (self.phi(player) ** 2 + v + math.exp(x)) ** 2

            return top / bot - (x - ca) / self.TAU ** 2

        # Find bounds
        a = math.log(player.volatility ** 2)

        if delta ** 2 > self.phi(player) ** 2 + v:
            b = math.log(delta ** 2 - self.phi(player) ** 2 - v)

        else:
            k = 1
            while f(a - k * self.TAU) < 0:
                k += 1
            b = a - k * self.TAU

        # Iterate to find
        fa = f(a)
        fb = f(b)

        while abs(b - a) > self.EPS:
            c = a + (a - b) * fa / (fb - fa)
            fc = f(c)

            if fc * fb < 0:
                a = b
                fa = fb
            else:
                fa = fa / 2

            b = c
            fb = fc

        return math.exp(a / 2)

    def _update(self, player: Glicko2Player, matches: Batch):
        v = self.estimated_variance(player, matches)
        sp = self.estimate_volatility(player, matches)

        phi_s = math.sqrt(self.phi(player) ** 2 + sp ** 2)
        phi_p = 1 / math.sqrt(1 / phi_s ** 2 + 1 / v)

        score = 0
        for match in matches:
            enemy = match.get_enemy(player)
            s = (match.get_result(player) + 1) / 2

            score += self.g(enemy) * (s - self.expectation(player, enemy))

        mu_p = self.mu(player) + phi_p ** 2 * score

        new_rating = self.SCALE * mu_p + self.CENTER
        new_deviation = self.SCALE * phi_p

        return new_rating, new_deviation, sp

    def update_match(self, match: Match) -> None:
        """Update all the players of a given match"""
        delayed_updates = dict()

        for player in match.players:
            update = self._update(player, Batch(match))
            delayed_updates[player] = update

        for player, (r, d, v) in delayed_updates.items():
            print(player, r - player.rating)
            player.rating = r
            player.deviation = d
            player.volatility = v

            if hasattr(player, "reset"):
                player.reset()

        # Cache is not valid anymore as a players were updated
        self.cache = dict()
        self.hits = defaultdict(int)

    def update_player(self, player, matches: Batch) -> None:
        """Update a single player without touching the others"""
        r, d, v = self._update(player, matches)

        player.rating = r
        player.deviation = d
        player.volatility = v