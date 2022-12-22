from scipy.stats import norm

from ranked.models import Match, Ranker
from ranked.models.elo import EloPlayer, EloTeam


class ChessElo(Ranker):
    """Chess tweaked their distribution to match their data better of simplify the math"""

    def __init__(self, k: float = 32, vol: float = 400) -> None:
        super().__init__()
        self.k = k
        self.vol = 400

    def new_player(self, *args) -> EloPlayer:
        return EloPlayer(*args)

    def new_team(self, *players, **config) -> EloTeam:
        return EloTeam(*players, **config)

    def win(self, match: Match) -> float:
        if len(match) == 2:
            s1 = match.get_player(0).skill()
            s2 = match.get_player(1).skill()

            return 1 / (1 + 10 ** ((s2 - s1) / self.vol))

        raise NotImplementedError()

    def update_match(self, match: Match) -> None:
        p1 = match.get_player(0)
        p2 = match.get_player(1)
        y = (match.get_result(p1) + 1) / 2

        expectation = self.win(match)

        p1.mu += self.k * (y - expectation)
        p2.mu -= self.k * (y - expectation)


def make(*args, **kwargs):
    return ChessElo(*args, **kwargs)
