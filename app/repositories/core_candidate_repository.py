import json

import asyncpg


class CoreCandidateRepository:
    """Lê candidatos diretamente do schema PostgreSQL mantido pelo api-core."""

    FIND_ALL = """
        WITH review_scores AS (
            SELECT
                fk_professional AS technician_id,
                AVG(rating)::double precision AS average_rating,
                COUNT(*)::integer AS review_count
            FROM professional_review
            WHERE active IS TRUE
            GROUP BY fk_professional
        )
        SELECT
            technician.id::text AS candidate_id,
            person.name AS name,
            profession.id::text AS service_id,
            profession.name AS service,
            COALESCE(review_scores.average_rating, 0.0) AS average_rating,
            COALESCE(review_scores.review_count, 0) AS review_count,
            COALESCE(
                jsonb_agg(
                    DISTINCT jsonb_build_object(
                        'id', certification.id::text,
                        'name', certification.name
                    )
                ) FILTER (
                    WHERE certification.id IS NOT NULL
                      AND certification.name IS NOT NULL
                ),
                '[]'::jsonb
            ) AS qualifications
        FROM technician
        JOIN person
          ON person.id = technician.fk_person
        JOIN users
          ON users.id = person.fk_users
        JOIN professional_registration
          ON professional_registration.fk_technician = technician.id
        JOIN profession
          ON profession.id = professional_registration.fk_profession
        LEFT JOIN certification_record
          ON certification_record.fk_professional_registration = professional_registration.id
        LEFT JOIN certification
          ON certification.id = certification_record.fk_certification
         AND (certification.validity IS NULL OR certification.validity >= CURRENT_TIMESTAMP)
        LEFT JOIN review_scores
          ON review_scores.technician_id = technician.id
        WHERE users.active IS TRUE
          AND profession.name IS NOT NULL
          AND (
              professional_registration.expiration_date IS NULL
              OR professional_registration.expiration_date >= CURRENT_TIMESTAMP
          )
        GROUP BY
            technician.id,
            person.name,
            profession.id,
            profession.name,
            review_scores.average_rating,
            review_scores.review_count
        ORDER BY person.name, profession.name
    """

    @classmethod
    async def find_all(cls, connection: asyncpg.Connection) -> list[dict]:
        rows = await connection.fetch(cls.FIND_ALL)
        candidates: list[dict] = []

        for row in rows:
            raw_qualifications = row["qualifications"]
            if isinstance(raw_qualifications, str):
                qualifications = json.loads(raw_qualifications)
            else:
                qualifications = raw_qualifications or []

            candidates.append(
                {
                    "candidate_id": row["candidate_id"],
                    "name": row["name"],
                    "service_id": row["service_id"],
                    "service": row["service"],
                    "average_rating": float(row["average_rating"]),
                    "review_count": int(row["review_count"]),
                    "qualifications": qualifications,
                }
            )

        return candidates
