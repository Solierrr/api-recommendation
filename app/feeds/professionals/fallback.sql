WITH eligible_technician AS (
    SELECT technician.id AS technician_id
    FROM technician
    JOIN person
      ON person.id = technician.person_id
    JOIN user_account
      ON user_account.id = person.user_id
    WHERE user_account.is_active IS TRUE
      AND technician.status = 'APPROVED'
),
registered AS (
    SELECT
        professional_registration.technician_id AS technician_id,
        ARRAY_AGG(DISTINCT profession.name ORDER BY profession.name) AS professions
    FROM professional_registration
    JOIN profession
      ON profession.id = professional_registration.profession_id
    WHERE profession.name IS NOT NULL
      AND BTRIM(profession.name) <> ''
      AND (
          professional_registration.expires_at IS NULL
          OR professional_registration.expires_at >= CURRENT_TIMESTAMP
      )
      AND ($3::uuid IS NULL OR professional_registration.profession_id = $3::uuid)
    GROUP BY professional_registration.technician_id
),
review_scores AS (
    SELECT
        technician_id,
        AVG(rating)::double precision AS average_rating,
        COUNT(*)::integer AS review_count
    FROM professional_review
    WHERE is_active IS TRUE
    GROUP BY technician_id
),
service_metrics AS (
    SELECT
        technician_affiliation.technician_id AS technician_id,
        COUNT(DISTINCT technical_service.id)::integer AS assigned_service_count,
        COUNT(DISTINCT technical_service.id) FILTER (
            WHERE technical_service.status = 'COMPLETED'
        )::integer AS completed_service_count,
        COUNT(DISTINCT technical_service.id) FILTER (
            WHERE technical_service.status = 'CANCELED'
        )::integer AS canceled_service_count
    FROM technician_affiliation
    JOIN service_executor
      ON service_executor.technician_affiliation_id = technician_affiliation.id
    JOIN technical_service
      ON technical_service.id = service_executor.technical_service_id
    GROUP BY technician_affiliation.technician_id
),
valid_certifications AS (
    SELECT
        technician_id,
        COUNT(*)::integer AS valid_certification_count,
        ARRAY_AGG(DISTINCT type ORDER BY type) AS certification_names
    FROM certification
    WHERE valid_until_at IS NULL
       OR valid_until_at >= CURRENT_TIMESTAMP
    GROUP BY technician_id
),
top_rated AS (
    SELECT
        technician.id::text AS technician_id,
        'Profissional ' || LEFT(technician.id::text, 8) AS name,
        registered.professions,
        COALESCE(review_scores.average_rating, 0.0) AS average_rating_global,
        COALESCE(review_scores.review_count, 0) AS review_count_global,
        COALESCE(service_metrics.completed_service_count, 0) AS completed_service_count_global,
        COALESCE(service_metrics.assigned_service_count, 0) AS assigned_service_count_global,
        COALESCE(service_metrics.canceled_service_count, 0) AS canceled_service_count_global,
        COALESCE(valid_certifications.valid_certification_count, 0) AS valid_certification_count,
        COALESCE(valid_certifications.certification_names, ARRAY[]::text[]) AS certification_names
    FROM technician
    JOIN eligible_technician
      ON eligible_technician.technician_id = technician.id
    JOIN registered
      ON registered.technician_id = technician.id
    LEFT JOIN review_scores
      ON review_scores.technician_id = technician.id
    LEFT JOIN service_metrics
      ON service_metrics.technician_id = technician.id
    LEFT JOIN valid_certifications
      ON valid_certifications.technician_id = technician.id
    ORDER BY
        COALESCE(review_scores.average_rating, 0.0) DESC,
        COALESCE(review_scores.review_count, 0) DESC,
        COALESCE(service_metrics.completed_service_count, 0) DESC,
        technician.id
    LIMIT $1
)
SELECT *
FROM top_rated
ORDER BY random()
LIMIT $2
