
from typing import Tuple

from ranked.models import Batch, Match, Player
from ranked.models.openskill import OpenSkill


def nearly(a, b, eps=0.0001):
    return abs(a - b) < eps


def check(a, b, eps=0.0001):
    print(a, b)
    return nearly(a, b, eps)


def get_match_batch(ranker) -> Tuple[Player, Batch]:
    p1 = ranker.new_player(1500, 200)
    p2 = ranker.new_player(1400, 30)
    p3 = ranker.new_player(1550, 100)
    p4 = ranker.new_player(1700, 300)

    batch = Batch(
        Match((p1, 1), (p2, 0)),  # p1 won
        Match((p3, 1), (p1, 0)),  # p3 won
        Match((p4, 1), (p1, 0)),  # p4 won
    )

    return p1, batch


def test_openskill():
    ranker = OpenSkill(mu=1500, sigma=173)

    p1, batch = get_match_batch(ranker)

    assert all(
        [ 
            check(ranker.win(batch.matches[0]), 0.500997102292219),   # 0.505756
            check(ranker.win(batch.matches[1]), 0.5004837884531367),  # 0.686300
            check(ranker.win(batch.matches[2]), 0.5008101284707912),  # 0.785026
        ]
    )

    for match in batch:
        ranker.update(match)

    assert nearly(p1.skill(), 1464.1202991405364) 
