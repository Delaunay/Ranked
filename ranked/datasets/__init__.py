from ranked.models import Batch


class Matchup:
    """Returns a batch of matches with their results

    A batch of matches is a list of matches where each player appears only once.

    Because the outcome of the past matches impacts the future matchups
    the batches are ordered by their time of play, but as long as players appears once
    in each batches the time in itself does not matter only the order of the match
    sequence need to be respected.

    If we were to sample random matches the skill estimation would become biased as
    future matches would implicitly provide information about their past matchups.

    i.e a high skill player will play against high skill players by the end of the dataset
    but he might be playing against mid tier player at the beginning.
    By presenting the latest matches first the algorithm will update its skill upwards faster.

    For algorithm benchmarking, you will need to use this logic to make sure
    your are benchmarking the algorithm fairly.

    The validation set needs to always be from the last batches.

    Nevertheless, in the case of resetting or recomputing skills at the start of a season you
    could use the biased version so the estimated skill converges faster.

    Notes
    -----
    In the case of estimating the skill for real match data, you will depend on the game's
    matchmaker, indeed, the matchmaker use its own metric for estimating skills and it might
    not yours closely as such the match you are observing might be suboptimal.
    """

    def __init__(self, ranker) -> None:
        self.ranker = ranker

    def save(self, fname: str):
        """Enable saving of the matchup during a simulation"""
        return

    def matches(self) -> Batch:
        raise NotImplementedError()
