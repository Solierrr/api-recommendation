from __future__ import annotations

from neo4j import AsyncSession


class RecommendationRepository:
    SOURCE = "api-core"

    ACTIVE_VERSION = """
        MATCH (state:SyncState {source: $source})
        RETURN state.active_version AS active_version
    """

    PANEL_CONTEXT = """
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
    """

    PANEL_CANDIDATES = """
        MATCH (offer:SolarOffer {
            source: $source,
            sync_version: $sync_version
        })-[:OF_MODEL]->(model:SolarModel {
            source: $source,
            sync_version: $sync_version
        })
        MATCH (offer)-[:FROM_SUPPLIER]->(supplier:Supplier {
            source: $source,
            sync_version: $sync_version
        })
        WHERE model.status = 'APPROVED'
          AND model.power_wp > 0
          AND model.efficiency >= 0
          AND model.efficiency <= 100
          AND model.dimension > 0
          AND model.weight > 0
          AND supplier.status = 'ACTIVE'
          AND supplier.subscription_active = true
          AND offer.unit_price_cents > 0
          AND offer.effective_availability > 0
          AND (offer.expiration_at IS NULL OR offer.expiration_at > datetime())
        RETURN
            model.id AS model_id,
            offer.id AS offer_id,
            supplier.id AS supplier_id,
            model.brand AS brand,
            model.model AS model,
            model.power_wp AS power_wp,
            model.efficiency AS efficiency,
            model.dimension AS dimension,
            model.weight AS weight,
            offer.unit_price_cents AS unit_price_cents,
            offer.effective_availability AS effective_availability,
            offer.accepted_proposal_quantity AS accepted_proposal_quantity,
            supplier.geolocation_count AS supplier_geolocation_count,
            supplier.latitude AS supplier_latitude,
            supplier.longitude AS supplier_longitude
        ORDER BY offer.id
        LIMIT $fetch_limit
    """

    PROFESSION_CONTEXT = """
        MATCH (profession:Profession {
            source: $source,
            sync_version: $sync_version,
            id: $context_id
        })
        RETURN profession.id AS id, profession.name AS name
    """

    PROFESSIONAL_CANDIDATES = """
        MATCH (technician:Technician {
            source: $source,
            sync_version: $sync_version
        })-[registration:REGISTERED_AS]->(profession:Profession {
            source: $source,
            sync_version: $sync_version,
            id: $context_id
        })
        WHERE technician.user_active = true
        RETURN
            technician.id AS technician_id,
            technician.name AS name,
            profession.id AS profession_id,
            technician.average_rating_global AS average_rating_global,
            technician.review_count_global AS review_count_global,
            technician.completed_service_count_global AS completed_service_count_global,
            technician.assigned_service_count_global AS assigned_service_count_global,
            technician.canceled_service_count_global AS canceled_service_count_global,
            registration.valid_certification_count AS valid_certification_count,
            registration.certification_names AS certification_names
        ORDER BY technician.id
        LIMIT $fetch_limit
    """

    TECHNICAL_SERVICE_CONTEXT = """
        MATCH (service:TechnicalService {
            source: $source,
            sync_version: $sync_version,
            id: $context_id
        })
        RETURN
            service.id AS id,
            service.purpose AS purpose,
            service.normalized_purpose AS normalized_purpose,
            service.status AS status,
            service.scheduled_at AS scheduled_at,
            service.geolocation_count AS geolocation_count,
            service.latitude AS latitude,
            service.longitude AS longitude
    """

    TECHNICIAN_CANDIDATES = """
        MATCH (technician:Technician {
            source: $source,
            sync_version: $sync_version
        })-[:HAS_EXPERIENCE]->(experience:ServiceExperience {
            source: $source,
            sync_version: $sync_version,
            normalized_purpose: $normalized_purpose
        })
        MATCH (affiliation:TechnicianAffiliation {
            source: $source,
            sync_version: $sync_version,
            active: true
        })-[:OF_TECHNICIAN]->(technician)
        WHERE NOT EXISTS {
            MATCH (technician)<-[:OF_TECHNICIAN]-(assigned_affiliation:TechnicianAffiliation {
                source: $source,
                sync_version: $sync_version
            })-[:ASSIGNED_TO]->(:TechnicalService {
                source: $source,
                sync_version: $sync_version,
                id: $context_id
            })
        }
        OPTIONAL MATCH (technician)-[:HAS_SHIFT]->(shift:Shift {
            source: $source,
            sync_version: $sync_version
        })
        WITH technician, experience, affiliation,
             [entry IN collect(
                 CASE
                     WHEN shift IS NULL THEN null
                     ELSE {start_at: shift.start_at, end_at: shift.end_at}
                 END
             ) WHERE entry IS NOT NULL] AS shifts
        RETURN
            technician.id AS technician_id,
            affiliation.id AS technician_affiliation_id,
            technician.name AS name,
            affiliation.affiliation_type AS affiliation_type,
            experience.completed_count AS same_purpose_completed_count,
            technician.average_rating_global AS average_rating_global,
            technician.review_count_global AS review_count_global,
            technician.active_workload AS active_workload,
            affiliation.company_geolocation_count AS company_geolocation_count,
            affiliation.company_latitude AS company_latitude,
            affiliation.company_longitude AS company_longitude,
            shifts
        ORDER BY affiliation.id
        LIMIT $fetch_limit
    """

    @classmethod
    async def get_active_version(cls, session: AsyncSession) -> str | None:
        result = await session.run(cls.ACTIVE_VERSION, source=cls.SOURCE)
        record = await result.single()
        return record["active_version"] if record else None

    @staticmethod
    async def _single(session: AsyncSession, query: str, **parameters) -> dict | None:
        result = await session.run(query, **parameters)
        record = await result.single()
        return dict(record) if record else None

    @staticmethod
    async def _many(session: AsyncSession, query: str, **parameters) -> list[dict]:
        result = await session.run(query, **parameters)
        records = await result.data()
        return [
            RecommendationRepository._normalize_temporals(dict(row)) for row in records
        ]

    @staticmethod
    def _normalize_temporals(row: dict) -> dict:
        def native(value):
            return value.to_native() if hasattr(value, "to_native") else value

        for key, value in list(row.items()):
            if isinstance(value, list):
                row[key] = [
                    {
                        nested_key: native(nested_value)
                        for nested_key, nested_value in item.items()
                    }
                    if isinstance(item, dict)
                    else native(item)
                    for item in value
                ]
            else:
                row[key] = native(value)
        return row

    @classmethod
    async def get_panel_context(
        cls, session: AsyncSession, version: str, context_id: str
    ) -> dict | None:
        return await cls._single(
            session,
            cls.PANEL_CONTEXT,
            source=cls.SOURCE,
            sync_version=version,
            context_id=context_id,
        )

    @classmethod
    async def get_panel_candidates(
        cls, session: AsyncSession, version: str, pool_limit: int
    ) -> list[dict]:
        return await cls._many(
            session,
            cls.PANEL_CANDIDATES,
            source=cls.SOURCE,
            sync_version=version,
            fetch_limit=pool_limit + 1,
        )

    @classmethod
    async def get_profession_context(
        cls, session: AsyncSession, version: str, context_id: str
    ) -> dict | None:
        return await cls._single(
            session,
            cls.PROFESSION_CONTEXT,
            source=cls.SOURCE,
            sync_version=version,
            context_id=context_id,
        )

    @classmethod
    async def get_professional_candidates(
        cls,
        session: AsyncSession,
        version: str,
        context_id: str,
        pool_limit: int,
    ) -> list[dict]:
        return await cls._many(
            session,
            cls.PROFESSIONAL_CANDIDATES,
            source=cls.SOURCE,
            sync_version=version,
            context_id=context_id,
            fetch_limit=pool_limit + 1,
        )

    @classmethod
    async def get_technical_service_context(
        cls, session: AsyncSession, version: str, context_id: str
    ) -> dict | None:
        context = await cls._single(
            session,
            cls.TECHNICAL_SERVICE_CONTEXT,
            source=cls.SOURCE,
            sync_version=version,
            context_id=context_id,
        )
        return cls._normalize_temporals(context) if context else None

    @classmethod
    async def get_technician_candidates(
        cls,
        session: AsyncSession,
        version: str,
        context_id: str,
        normalized_purpose: str,
        pool_limit: int,
    ) -> list[dict]:
        return await cls._many(
            session,
            cls.TECHNICIAN_CANDIDATES,
            source=cls.SOURCE,
            sync_version=version,
            context_id=context_id,
            normalized_purpose=normalized_purpose,
            fetch_limit=pool_limit + 1,
        )
