# You cn use the API to access rank estimate
# example: https://api.opendota.com/api/players/104275965

query = """
SELECT
    player_matches.match_id,
    player_matches.account_id,
    player_matches.player_slot,

    matches.radiant_win,
    matches.game_mode,

    public_matches.avg_rank_tier,
    public_matches.num_rank_tier,
    public_matches.avg_mmr,
    public_matches.num_mmr
    -- estimate

    -- solo_competitive_rank,
    -- competitive_rank

FROM player_matches
INNER JOIN matches USING(match_id)
LEFT OUTER JOIN public_matches USING(match_id)

-- error: permission denied for relation rank_tier
-- JOIN rank_tier USING(account_id)

-- error: permission denied for relation solo_competitive_rank
-- JOIN solo_competitive_rank  USING(account_id)

-- error: permission denied for relation mmr_estimates
-- JOIN mmr_estimates  USING(account_id)

-- error: permission denied for relation player_ratings
-- INNER JOIN player_ratings USING(account_id)

WHERE
    -- Not necessary
    -- account_id != 4294967295 AND
    human_players = 10

-- start_time
-- match_id > X

ORDER BY match_id

LIMIT 10
"""
