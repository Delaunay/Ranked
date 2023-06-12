from ranked.models import Match


def test_match():
    m = Match(("Player1", 200), ("Player2", 100), ("Player3", 300))

    return m.get_ranks() == [1, 2, 0]
