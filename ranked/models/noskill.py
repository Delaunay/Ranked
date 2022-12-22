import math
from itertools import chain

from trueskill import TrueSkill

from ranked.models import Match, Player, Ranker, Team


class NoSkillPlayer(Player):
    def __init__(self, rating, *args) -> None:
        self.rating = rating

    def skill(self) -> float:
        """Returns the estimated skill of this team"""
        return self.rating.mu

    def consistency(self) -> float:
        return self.rating.sigma

    @property
    def mu(self):
        return self.rating.mu

    @property
    def sigma(self):
        return self.rating.sigma


class NoSkillTeam(Team):
    def __init__(self, *players, **config) -> None:
        super().__init__(*players, **config)


def to_team(p):
    if isinstance(p, NoSkillPlayer):
        return (p,)

    return p


def ensure_team(players):
    # Make sure our match is composed of teams in the game of 1v1
    return [to_team(p) for p in players]


class NoSkill(Ranker):
    """NoSkill is a bayesian skill rating system, supports team

    References
    ----------
    .. [1] http://www.moserware.com/assets/computing-your-skill/The%20Math%20Behind%20TrueSkill.pdf
    .. [2] https://www.microsoft.com/en-us/research/publication/trueskilltm-a-bayesian-skill-rating-system/

    """

    @staticmethod
    def parameters(self, center=1500):
        sigma = center / 3  # center - 3 * sigma = 0
        sigmav = math.sqrt(sigma)  #
        beta = math.sqrt((sigma / 2) ** 2)
        betav = math.sqrt(beta)
        tau = math.sqrt((sigma / 100) ** 2)
        tauv = math.sqrt(tau)

        return dict(
            sigma=f"normal({sigma}, {sigmav})",
            beta=f"normal({beta}, {betav})",
            tau=f"normal({tau}, {tauv})",
        )

    def __init__(
        self,
        center=35,
        sigma=None,
        beta=None,
        tau=None,
        draw_probability=0.1,
    ) -> None:

        if sigma is None:
            sigma = center / 3

        if beta is None:
            beta = sigma / 2

        if tau is None:
            tau = sigma / 100

        self.starting_mu = center
        self.starting_sigma = sigma

        self.model = TrueSkill(
            mu=center,
            sigma=sigma,
            beta=beta,
            tau=tau,
            draw_probability=draw_probability,
            backend="scipy",
        )

    def new_player(self, a=None, b=None, *args, **config) -> Player:
        return NoSkillPlayer(self.model.create_rating(a, b), *args)

    def new_team(self, *players, **config) -> Team:
        return NoSkillTeam(*players, **config)

    def win(self, match: Match):
        if len(match) == 2:
            team1 = to_team(match.get_player(0))
            team2 = to_team(match.get_player(1))

            delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
            sum_sigma = sum(r.sigma**2 for r in chain(team1, team2))
            size = len(team1) + len(team2)
            denom = math.sqrt(size * (self.model.beta * self.model.beta) + sum_sigma)

            return self.model.cdf(delta_mu / denom)

        raise NotImplementedError()

    def quality(self, match: Match) -> float:
        return self.model.quality(ensure_team(match.players))

    def update_match(self, match: Match) -> None:
        teams = ensure_team(match.players)

        new_ratings = self.model.rate(teams, ranks=[1 / (s + 1) for s in match.scores])

        for (
            team,
            ratings,
        ) in zip(teams, new_ratings):
            for p, rating in zip(team, ratings):
                p.rating = rating


def make(*args, **kwargs):
    return NoSkill(*args, **kwargs)
