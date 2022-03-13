from typing import Tuple

from ranked.models.glicko2 import Glicko2
from ranked.models.interface import Batch, Match, Player


def nearly(a, b, eps=0.0001):
    return abs(a - b) < eps


def check(a, b, eps=0.0001):
    print(a, b)
    return nearly(a, b, eps)


def get_glicko2_match_batch(ranker) -> Tuple[Player, Batch]:
    p1 = ranker.new_player(1500, 200)
    p2 = ranker.new_player(1400, 30)
    p3 = ranker.new_player(1550, 100)
    p4 = ranker.new_player(1700, 300)

    results = Batch(
        Match((p1, 1), (p2, 0)),  # p1 won
        Match((p3, 1), (p1, 0)),  # p3 won
        Match((p4, 1), (p1, 0)),  # p4 won
    )

    return p1, results


def test_glicko2():
    ranker = Glicko2()

    p1, results = get_glicko2_match_batch(ranker)

    ranker.update(results)

    # Note here that the online version gives something different
    assert nearly(p1.rating, 1463.7883720898253)
    assert nearly(p1.deviation, 151.87321313884027)
    assert nearly(p1.volatility, 0.0599959)


def test_glicko2_sanity():
    ranker = Glicko2()

    p1 = ranker.new_player(1500, 200)
    p2 = ranker.new_player(1400, 30)
    p3 = ranker.new_player(1550, 100)
    p4 = ranker.new_player(1700, 300)

    # Sanity check
    assert nearly(ranker.mu(p2), -0.5756)
    assert nearly(ranker.phi(p2), 0.1727)
    assert nearly(ranker.g(p2), 0.9955)
    assert nearly(ranker.expectation(p1, p2), 0.639, 0.001)

    assert nearly(ranker.mu(p3), 0.2878)
    assert nearly(ranker.phi(p3), 0.5756)
    assert nearly(ranker.g(p3), 0.9531)
    assert nearly(ranker.expectation(p1, p3), 0.432, 0.001)

    assert nearly(ranker.mu(p4), 1.1513)
    assert nearly(ranker.phi(p4), 1.7269)
    assert nearly(ranker.g(p4), 0.7242)
    assert nearly(ranker.expectation(p1, p4), 0.303, 0.001)


def test_glicko2_internal():
    ranker = Glicko2()

    p1, results = get_glicko2_match_batch(ranker)

    # Note: paper has rounding so the values are a bit off
    assert nearly(ranker.estimated_variance(p1, results), 1.778977)
    assert nearly(ranker.delta(p1, results), -0.483933)
    assert nearly(ranker.estimate_volatility(p1, results), 0.05999)

    ranker.update_player(p1, results)

    assert nearly(p1.rating, 1464.0506)
    assert nearly(p1.deviation, 151.5165)
    assert nearly(p1.volatility, 0.0599959)

    for (fun, _), counts in ranker.hits.items():
        print(fun, counts)


def get_match_batch(ranker, sub=0, div=1) -> Tuple[Player, Batch]:
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


def test_glicko2_vs_elo():
    print("Glicko2 - EloCase")
    ranker = Glicko2(tau=0.2)

    p1, results = get_match_batch(ranker)

    ranker.update(results)

    assert nearly(p1.rating, 1573.5748142575442)
    assert nearly(p1.deviation, 194.757411)
    assert nearly(p1.volatility, 0.0599959)


def get_team_match_batch(ranker, sub=0, div=1) -> Tuple[Player, Batch]:
    p1 = ranker.new_player((1613 - sub) / div, 30)
    p2 = ranker.new_player((1388 - sub) / div, 200)

    p3 = ranker.new_player((1477 - sub) / div, 30)
    p4 = ranker.new_player((1609 - sub) / div, 100)

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


def test_glicko2_team():
    ranker = Glicko2(tau=0.2)

    t1, t2, results = get_team_match_batch(ranker)

    assert all(
        [
            check(t1.rating, 3001.0),
            check(t1.deviation, 202.23748416156684),
            check(t1.volatility, 0.08485281374238571),
        ]
    )

    assert all(
        [
            check(t2.rating, 3086.0),
            check(t2.deviation, 104.4030650891055),
            check(t2.volatility, 0.08485281374238571),
        ]
    )

    ranker.update(results)

    assert all(
        [
            check(t1.rating, 3049.789894120224),
            check(t1.deviation, 131.92696272805088),
            check(t1.volatility, 0.08485251939984882),
        ]
    )

    assert all(
        [
            check(t2.rating, 3065.8777508054022),
            check(t2.deviation, 94.75464123536405),
            check(t2.volatility, 0.0848529507874745),
        ]
    )
