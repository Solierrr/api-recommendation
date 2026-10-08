MATCH (profession:Profession {
    source: $source,
    sync_version: $sync_version,
    id: $context_id
})
RETURN profession.id AS id, profession.name AS name
