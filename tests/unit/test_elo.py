from typing import Tuple

from ranked.models.elo import ChessElo, Elo
from ranked.models.interface import Batch, Match, Player, Ranker


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


def test_chess_elo():
    ranker = ChessElo()

    p1, batch = get_match_batch(ranker)

    assert nearly(ranker.win(batch.matches[0]), 0.505756)
    assert nearly(ranker.win(batch.matches[1]), 0.686300)
    assert nearly(ranker.win(batch.matches[2]), 0.785026)
    assert nearly(ranker.win(batch.matches[3]), 0.538778)
    assert nearly(ranker.win(batch.matches[4]), 0.350705)

    for match in batch:
        ranker.update(match)

    assert nearly(p1.skill(), 1603.191184)


def test_chess_elo_batch():
    ranker = ChessElo()
    p1, batch = get_match_batch(ranker)
    ranker.update(batch)
    assert nearly(p1.skill(), 1603.191184)


def test_elo_logistic():
    from scipy.stats import logistic

    # pick alpha to make K ~= 32
    ranker = Elo(1, logistic, 0.10435876689)

    p1, batch = get_match_batch(ranker, 1500, 173)

    assert all(
        [
            check(ranker.k * 173, 32, 1),
            # Chess Elo
            check(ranker.win(batch.matches[0]), 0.504087),  # 0.505756
            check(ranker.win(batch.matches[1]), 0.635497),  # 0.686300
            check(ranker.win(batch.matches[2]), 0.714970),  # 0.785026
            check(ranker.win(batch.matches[3]), 0.527561),  # 0.538778
            check(ranker.win(batch.matches[4]), 0.392374),  # 0.350705
        ]
    )

    for match in batch:
        ranker.update(match)

    assert nearly(p1.skill() * 173 + 1500, 1605.426562)  # 1603.191184


def test_elo_logistic_batch():
    from scipy.stats import logistic

    ranker = Elo(64 / 1500, logistic, 0.2831)
    p1, batch = get_match_batch(ranker, 0, 1500)
    ranker.update(batch)
    assert nearly(p1.skill() * 1500, 1608.416031)


def test_elo_norm():
    print("Elo Norm")
    from scipy.stats import norm

    ranker = Elo(1, norm, 0.10435876689)

    p1, batch = get_match_batch(ranker, 1500, 173)

    assert all(
        [
            check(ranker.k * 173, 32, 1),
            # Chess Elo
            check(ranker.win(batch.matches[0]), 0.5065221323696847),  # 0.505756
            check(ranker.win(batch.matches[1]), 0.710852136082442),  # 0.686300
            check(ranker.win(batch.matches[2]), 0.8211215145200301),  # 0.785026
            check(ranker.win(batch.matches[3]), 0.5439371529376492),  # 0.538778
            check(ranker.win(batch.matches[4]), 0.3309311261083969),  # 0.350705
        ]
    )
    for match in batch:
        ranker.update(match)

    assert nearly(p1.skill() * 173 + 1500, 1602.131659)  # 1603.191184


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


def test_elo_team():
    from scipy.stats import norm

    ranker = ChessElo()

    t1, t2, results = get_team_match_batch(ranker)

    assert all(
        [
            check(t1.skill(), 3001.0),
        ]
    )

    assert all(
        [
            check(t2.skill(), 3086.0),
        ]
    )

    ranker.update(results)

    assert all(
        [
            check(t1.skill(), 3017.83171558993),
        ]
    )

    assert all(
        [
            check(t2.skill(), 3069.16828441007),
        ]
    )
