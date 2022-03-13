import math
from itertools import chain

from numpy import mat
from trueskill import TrueSkill

from ranked.interface import Match, Player, Ranker, Team


class NoSkillPlayer(Player):
    def __init__(self, rating) -> None:
        self.rating = rating

    def skill(self) -> float:
        """Returns the estimated skill of this team"""
        return self.rating.mu

    @property
    def mu(self):
        return self.mu

    @property
    def sigma(self):
        return self.sigma


class NoSkillTeam(Team):
    def __init__(self, *players, **config) -> None:
        super().__init__(*players, **config)


class NoSkill(Ranker):
    """NoSkill is a bayesian skill rating system, supports team

    References
    ----------
    .. [1] http://www.moserware.com/assets/computing-your-skill/The%20Math%20Behind%20TrueSkill.pdf
    .. [2] https://www.microsoft.com/en-us/research/publication/trueskilltm-a-bayesian-skill-rating-system/

    """

    def __init__(self) -> None:
        self.model = TrueSkill(backend="scipy")

    def new_player(self, *args, **config) -> Player:
        return NoSkillPlayer(self.model.create_rating(*args))

    def new_team(self, *players, **config) -> Team:
        return NoSkillTeam(*players)

    def win(self, match: Match):
        if len(match) == 2:
            team1 = match.get_player(0)
            team2 = match.get_player(1)

            delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
            sum_sigma = sum(r.sigma ** 2 for r in chain(team1, team2))
            size = len(team1) + len(team2)
            denom = math.sqrt(size * (self.model.beta * self.model.beta) + sum_sigma)

            return self.model.cdf(delta_mu / denom)

        raise NotImplementedError()

    def quality(self, match: Match) -> float:
        return self.model.quality(match.players)

    def update_match(self, match: Match) -> None:
        new_ratings = self.model.rate(match.players, ranks=match.scores)

        for player, (new_rating,) in zip(match.players, new_ratings):
            player.rating = new_rating
