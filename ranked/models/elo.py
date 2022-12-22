import math

from scipy.stats import norm

from ranked.models import Match, Player, Ranker, Team


class EloPlayer(Player):
    def __init__(self, mu=0, *args) -> None:
        self.mu = mu

    def skill(self) -> float:
        return self.mu


class EloTeam(Team):
    """Combine multiple players and make them look like one to the algorithm"""

    def __init__(self, *players, **config) -> None:
        super().__init__(*players, **config)
        self._mu = None

    def skill(self) -> float:
        return self.mu

    @property
    def mu(self):
        if self._mu is None:
            self._mu = sum([p.skill() for p in self.players])
        return self._mu

    @mu.setter
    def mu(self, value):
        diff = value - self.mu

        for p in self.players:
            print(self, p, diff, p.skill() / self.mu)
            p.mu += diff * (p.skill() / self.mu)

        self._mu = None


class Elo(Ranker):
    """Generic Elo Rating System"""

    def __init__(self, vol, distribution=norm, alpha=1) -> None:
        super().__init__()

        self.dist = distribution
        self.vol = vol
        self.alpha = alpha

    def new_player(self, *args) -> EloPlayer:
        return EloPlayer(*args)

    def new_team(self, *players, **config) -> EloTeam:
        return EloTeam(*players, **config)

    @property
    def k(self):
        return self.alpha * self.vol * math.sqrt(math.pi)

    def win(self, match: Match) -> float:
        if len(match) == 2:
            s1 = match.get_player(0).skill()
            s2 = match.get_player(1).skill()

            n = (s1 - s2) / math.sqrt(2 * self.vol)
            return self.dist.cdf(n)

        raise NotImplementedError()

    def update_match(self, match: Match) -> None:
        p1 = match.get_player(0)
        p2 = match.get_player(1)
        y = match.get_result(p1)

        expectation = self.win(match)

        delta = self.k * ((y + 1) / 2 - expectation)

        p1.mu += delta
        p2.mu -= delta


def make(*args, **kwargs):
    return Elo(*args, **kwargs)
