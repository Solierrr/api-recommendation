MATCH (technician:Technician {
    source: $source,
    sync_version: $sync_version
})-[registration:REGISTERED_AS]->(profession:Profession {
    source: $source,
    sync_version: $sync_version
})
WHERE technician.user_active = true
  AND ($profession_id IS NULL OR profession.id = $profession_id)
WITH technician,
     collect(DISTINCT profession.name) AS professions,
     max(registration.valid_certification_count) AS valid_certification_count,
     collect(registration.certification_names) AS certification_lists
RETURN
    technician.id AS technician_id,
    technician.name AS name,
    professions,
    technician.average_rating_global AS average_rating_global,
    technician.review_count_global AS review_count_global,
    technician.completed_service_count_global AS completed_service_count_global,
    technician.assigned_service_count_global AS assigned_service_count_global,
    technician.canceled_service_count_global AS canceled_service_count_global,
    coalesce(valid_certification_count, 0) AS valid_certification_count,
    reduce(
        names = [],
        certifications IN certification_lists |
        names + [certification IN certifications WHERE NOT certification IN names]
    ) AS certification_names
ORDER BY technician.id
LIMIT $fetch_limit
