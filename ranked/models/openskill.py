from itertools import chain

from openskill import Rating, rate, predict_win
from openskill.models import PlackettLuce

from ranked.models import Match, Player, Ranker, Team


class OpenSkillPlayer(Player):
    def __init__(self, rating, *args) -> None:
        self.rating = rating

    def skill(self) -> float:
        """Returns the estimated skill of this team"""
        return self.rating.mu

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mu={self.skill():4.2f}, sigma={self.sigma:4.2f})"

    def consistency(self) -> float:
        return self.rating.sigma

    @property
    def mu(self):
        return self.rating.mu

    @property
    def sigma(self):
        return self.rating.sigma

    @sigma.setter
    def sigma(self, value):
        self.rating.sigma = value

    @mu.setter
    def mu(self, value):
        self.rating.mu = value
 

class OpenSkillTeam(Team):
    def __init__(self, *players, **config) -> None:
        super().__init__(*players, **config)


def to_team(p):
    if isinstance(p, OpenSkillPlayer):
        return (p,)

    return p


def ensure_team(players):
    # Make sure our match is composed of teams in the game of 1v1
    return [to_team(p) for p in players]


class OpenSkill(Ranker):
    def __init__(self, model=None, mu=None, sigma=None, beta=None, tau=None, initial_sigma=None) -> None:
        if model is None:
            model = PlackettLuce

        self.model = model
        self.default_mu = mu
        self.default_sigma = initial_sigma or sigma

        self.options = dict()

        if mu:
            self.options['mu'] = mu

        if sigma:
            self.options['sigma'] = sigma
    
        if beta:
            self.options['beta'] = beta

        if tau:
            self.options['tau'] = tau

    def new_player(self, a=None, b=None, *args, **config) -> Player:
        return OpenSkillPlayer(Rating(          #
                mu=a or self.default_mu,        #
                sigma=b or self.default_sigma   #
            ),                                  # 
            *args                               #
        )

    def new_team(self, *players, **config) -> Team:
        return OpenSkillTeam(*players, **config)

    def win(self, match: Match):
        if len(match) == 2:
            
            team1 = to_team(match.get_player(0))
            team2 = to_team(match.get_player(1))
            return predict_win([team1, team2], model=self.model, **self.options)[0]

        raise NotImplementedError()

    def update_match(self, match: Match) -> None:
        teams = ensure_team(match.players)

        new_ratings = rate(teams, score=match.scores, model=self.model, **self.options)

        for (
            team,
            ratings,
        ) in zip(teams, new_ratings):
            for p, rating in zip(team, ratings):
                p.rating = rating
