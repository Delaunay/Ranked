from typing import Tuple

from ranked.models import Batch, Match, Player, Ranker
from ranked.models.noskill import NoSkill


def nearly(a, b, eps=0.0001):
    return abs(a - b) < eps


def check(a, b, eps=0.0001):
    print(a, b)
    return nearly(a, b, eps)


def get_match_batch(ranker: Ranker, sub=0, div=1) -> Tuple[Player, Batch]:
    p1 = ranker.new_player((1613 - sub) / div)
    p2 = ranker.new_player((1609 - sub) / div)
    p3 = ranker.new_player((1477 - sub) / div)
    p4 = ranker.new_player((1388 - sub) / div)
    p5 = ranker.new_player((1586 - sub) / div)
    p6 = ranker.new_player((1720 - sub) / div)

    batch = Batch(
        Match((p1, 0), (p2, 1)),  # Lose
        Match((p1, 0), (p3, 0)),  # Draw
        Match((p1, 1), (p4, 0)),  # Win
        Match((p1, 1), (p5, 0)),  # Win
        Match((p1, 0), (p6, 1)),  # Lose
    )
    return p1, batch


def test_noskill():
    ranker = NoSkill(1500, 173)

    p1, batch = get_match_batch(ranker)

    assert all(
        [  # Elo Chess
            check(ranker.win(batch.matches[0]), 0.5058336245103013),  # 0.505756
            check(ranker.win(batch.matches[1]), 0.6904726315332785),  # 0.686300
            check(ranker.win(batch.matches[2]), 0.794620239867361),  # 0.785026
            check(ranker.win(batch.matches[3]), 0.5393145178920864),  # 0.538778
            check(ranker.win(batch.matches[4]), 0.3478350817945835),  # 0.350705
        ]
    )

    for match in batch:
        ranker.update(match)

    assert nearly(p1.skill(), 1567.5437809554614)  # 1603.191184


def test_noskill_batch():
    ranker = NoSkill(1500, 173)

    p1, batch = get_match_batch(ranker)

    ranker.update(batch)

    assert nearly(p1.skill(), 1567.5437809554614)  # 1603.191184


def get_team_match_batch(ranker, sub=0, div=1) -> Tuple[Player, Batch]:
    p1 = ranker.new_player((1613 - sub) / div)
    p2 = ranker.new_player((1388 - sub) / div)

    p3 = ranker.new_player((1477 - sub) / div)
    p4 = ranker.new_player((1609 - sub) / div)

    t1 = ranker.new_team(p1, p2)
    t2 = ranker.new_team(p3, p4)

    batch = Batch(
        Match((t1, 0), (t2, 1)),  # Lose
        Match((t1, 0), (t2, 0)),  # Draw
        Match((t1, 1), (t2, 0)),  # Win
        Match((t1, 1), (t2, 0)),  # Win
        Match((t1, 0), (t2, 1)),  # Lose
    )
    return t1, t2, batch


def test_noskill_team():
    ranker = NoSkill(1500, 173)

    t1, t2, results = get_team_match_batch(ranker)

    assert all(
        [
            check(t1.skill(), 3001.0),
            check(t2.skill(), 3086.0),
        ]
    )

    ranker.update(results)

    assert all(
        [
            check(t1.skill(), 3025.302510083812),
            check(t2.skill(), 3061.6974899161874),
        ]
    )
