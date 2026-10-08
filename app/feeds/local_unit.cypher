MATCH (unit:LocalUnit {
    source: $source,
    sync_version: $sync_version,
    id: $context_id
})
RETURN
    unit.id AS id,
    coalesce(unit.geolocation_count, 0) AS geolocation_count,
    unit.latitude AS latitude,
    unit.longitude AS longitude
