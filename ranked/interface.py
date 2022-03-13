import math
from typing import Sequence, Union


class Player:
    def skill(self) -> float:
        """Returns the estimated skill of this player"""
        raise NotImplementedError()


class Team(Player):
    """Combine multiple players and make them look like one to the ranking algorithm.
    It needs to propagate the rating change back to the individual players.
    """

    def __init__(self, *players, **config) -> None:
        self.players = players
        self.config = config

    def skill(self) -> float:
        """Returns the estimated skill of this team"""
        return sum([player.skill() for player in self.players])

    def __len__(self):
        return len(self.players)

    def __getitem__(self):
        return self.players[0]

    def __iter__(self):
        return iter(self.players)


class Match:
    """Represent a single match with N players"""

    def __init__(self, *ranks) -> None:
        self.players = [p for p, _ in ranks]
        self.scores = [r for _, r in ranks]
        self.ranks = ranks

    def get_score(self, index) -> float:
        return self.scores[index]

    def get_enemy(self, player: Player) -> Player:
        """Get the enemy of the given player; only available for 1v1"""
        assert len(self.players) == 2

        if self.players[0] is player:
            return self.players[1]

        return self.players[0]

    def get_result(self, player: Player) -> Player:
        """Convert the score value into a win(1)/draw(0)/loss(-1) number
        Only available for 1v1
        """
        assert len(self.players) == 2

        if self.scores[0] == self.scores[1]:
            return 0

        score = int(self.scores[0] > self.scores[1]) * 2 - 1

        if self.players[0] is player:
            return score

        return -score

    def get_player(self, index) -> Player:
        return self.players[index]

    def __len__(self) -> int:
        return len(self.players)


class Batch:
    """A batch of matches"""

    def __init__(self, *matches) -> None:
        self.matches = matches

    def __iter__(self) -> Sequence[Match]:
        return iter(self.matches)


class Ranker:
    def new_player(self, *args, **config) -> Player:
        """Builds a new player, this enable the Ranker to initialize it if needed"""
        raise NotImplementedError()

    def new_team(self, *players, **config) -> Team:
        """Builds a new team, this enable the Ranker to initialize it if needed"""
        raise NotImplementedError()

    def win(self, match: Match) -> float:
        """Returns the win probability"""
        raise NotImplementedError()

    def update(self, matches: Union[Batch, Match]) -> None:
        """Update rank of each players for a given score

        Parameters
        ----------
        matches: Union[Batch, Match]
            A single match or a batch of matches with results

        """
        if isinstance(matches, Match):
            return self.update_match(matches)
        return self.update_batch(matches)

    def update_match(self, match: Match) -> None:
        """Online version, updates score as the match are happening"""
        raise NotImplementedError()

    def update_batch(self, matches: Batch) -> None:
        """Default implementation calls ``update_match`` sequentially"""
        for match in matches:
            self.update_match(match)
