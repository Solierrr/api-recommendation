MATCH (state:SyncState {source: $source})
WHERE state.active_version IS NOT NULL
RETURN state.active_version AS active_version,
       toInteger(duration.inSeconds(coalesce(state.activated_at, datetime()), datetime()).seconds)
           AS snapshot_age_seconds
