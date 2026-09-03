from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from math import isfinite
from typing import Any

import asyncpg

Heartbeat = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class CoreGraphSnapshot:
    local_units: list[dict]
    panel_offers: list[dict]
    professions: list[dict]
    professionals: list[dict]
    affiliations: list[dict]
    shifts: list[dict]
    technical_services: list[dict]
    service_experiences: list[dict]
    assignments: list[dict]

    @property
    def expected_node_counts(self) -> dict[str, int]:
        technician_ids = {
            row["technician_id"]
            for rows in (
                self.professionals,
                self.affiliations,
                self.shifts,
                self.service_experiences,
            )
            for row in rows
        }
        return {
            "local_units": len({row["id"] for row in self.local_units}),
            "solar_offers": len({row["offer_id"] for row in self.panel_offers}),
            "solar_models": len({row["model_id"] for row in self.panel_offers}),
            "suppliers": len({row["supplier_id"] for row in self.panel_offers}),
            "technicians": len(technician_ids),
            "professions": len({row["profession_id"] for row in self.professions}),
            "affiliations": len({row["affiliation_id"] for row in self.affiliations}),
            "shifts": len({row["shift_id"] for row in self.shifts}),
            "technical_services": len({row["service_id"] for row in self.technical_services}),
            "service_experiences": len(
                {(row["technician_id"], row["normalized_purpose"]) for row in self.service_experiences}
            ),
        }

    @property
    def expected_relationship_counts(self) -> dict[str, int]:
        return {
            "offer_models": len({(row["offer_id"], row["model_id"]) for row in self.panel_offers}),
            "offer_suppliers": len({(row["offer_id"], row["supplier_id"]) for row in self.panel_offers}),
            "registrations": len(
                {(row["technician_id"], row["profession_id"]) for row in self.professionals}
            ),
            "affiliation_technicians": len(
                {(row["affiliation_id"], row["technician_id"]) for row in self.affiliations}
            ),
            "technician_shifts": len({(row["technician_id"], row["shift_id"]) for row in self.shifts}),
            "technician_experiences": len(
                {(row["technician_id"], row["normalized_purpose"]) for row in self.service_experiences}
            ),
            "assignments": len(
                {(row["executor_id"], row["affiliation_id"], row["service_id"]) for row in self.assignments}
            ),
        }

    @property
    def expected_node_count(self) -> int:
        return sum(self.expected_node_counts.values())

    @property
    def counts(self) -> dict[str, int]:
        certification_names = {
            name for professional in self.professionals for name in professional["certification_names"]
        }
        return {
            "local_units": self.expected_node_counts["local_units"],
            "panel_models": self.expected_node_counts["solar_models"],
            "panel_offers": self.expected_node_counts["solar_offers"],
            "professionals": len({row["technician_id"] for row in self.professionals}),
            "professions": self.expected_node_counts["professions"],
            "qualifications": len(certification_names),
            "technician_affiliations": self.expected_node_counts["affiliations"],
            "technical_services": self.expected_node_counts["technical_services"],
        }


class CoreGraphRepository:
    """Constrói um snapshot somente leitura a partir do schema mantido pelo api-core."""

    FIND_LOCAL_UNITS = """
        WITH address_geolocation AS (
            SELECT
                address_id,
                COUNT(*)::integer AS geolocation_count,
                CASE WHEN COUNT(*) = 1
                    THEN MIN(latitude)::double precision
                END AS latitude,
                CASE WHEN COUNT(*) = 1
                    THEN MIN(longitude)::double precision
                END AS longitude
            FROM geolocation
            GROUP BY address_id
        )
        SELECT
            local_unit.id::text AS id,
            local_unit.unit_type AS location_type,
            local_unit.complement,
            COALESCE(address_geolocation.geolocation_count, 0) AS geolocation_count,
            address_geolocation.latitude,
            address_geolocation.longitude
        FROM local_unit
        LEFT JOIN address_geolocation
          ON address_geolocation.address_id = local_unit.address_id
        ORDER BY local_unit.id
    """

    FIND_PANEL_OFFERS = """
        WITH active_subscriptions AS (
            SELECT
                supplier_id,
                BOOL_OR(
                    status = 'PAID'
                    AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP)
                ) AS subscription_active
            FROM subscription
            GROUP BY supplier_id
        ),
        accepted_usage AS (
            SELECT
                proposal_item.offer_id AS offer_id,
                COALESCE(SUM(proposal_item.quantity), 0)::integer
                    AS accepted_proposal_quantity
            FROM proposal_item
            JOIN proposal
              ON proposal.id = proposal_item.proposal_id
            WHERE proposal.status = 'ACCEPTED'
            GROUP BY proposal_item.offer_id
        ),
        company_geolocation AS (
            SELECT
                company.id AS company_id,
                COUNT(geolocation.id)::integer AS geolocation_count,
                CASE WHEN COUNT(geolocation.id) = 1
                    THEN MIN(geolocation.latitude)::double precision
                END AS latitude,
                CASE WHEN COUNT(geolocation.id) = 1
                    THEN MIN(geolocation.longitude)::double precision
                END AS longitude
            FROM company
            LEFT JOIN geolocation
              ON geolocation.address_id = company.address_id
            GROUP BY company.id
        )
        SELECT
            model.id::text AS model_id,
            model.brand,
            model.model_name AS model,
            model.power_wp::double precision AS power_wp,
            model.efficiency::double precision AS efficiency,
            model.dimension::double precision AS dimension,
            model.weight::double precision AS weight,
            model.status AS model_status,
            offer.id::text AS offer_id,
            ROUND(offer.unit_price * 100)::bigint AS unit_price_cents,
            offer.availability,
            offer.expiration_date AS expiration_at,
            stock.quantity AS inventory_quantity,
            LEAST(offer.availability, stock.quantity)::integer
                AS effective_availability,
            supplier.id::text AS supplier_id,
            supplier.status AS supplier_status,
            supplier.business_type,
            company.id::text AS company_id,
            company.trade_name,
            active_subscriptions.subscription_active,
            COALESCE(accepted_usage.accepted_proposal_quantity, 0)
                AS accepted_proposal_quantity,
            COALESCE(company_geolocation.geolocation_count, 0)
                AS supplier_geolocation_count,
            company_geolocation.latitude AS supplier_latitude,
            company_geolocation.longitude AS supplier_longitude
        FROM offer
        JOIN model
          ON model.id = offer.model_id
        JOIN supplier
          ON supplier.id = offer.supplier_id
        JOIN company
          ON company.id = supplier.company_id
        JOIN stock
          ON stock.supplier_id = offer.supplier_id
         AND stock.model_id = offer.model_id
        JOIN active_subscriptions
          ON active_subscriptions.supplier_id = supplier.id
         AND active_subscriptions.subscription_active IS TRUE
        LEFT JOIN accepted_usage
          ON accepted_usage.offer_id = offer.id
        LEFT JOIN company_geolocation
          ON company_geolocation.company_id = company.id
        WHERE model.status = 'APPROVED'
          AND model.power_wp > 0
          AND model.efficiency >= 0
          AND model.efficiency <= 100
          AND model.dimension > 0
          AND model.weight > 0
          AND supplier.status = 'ACTIVE'
          AND offer.unit_price > 0
          AND offer.availability > 0
          AND stock.quantity > 0
          AND (
              offer.expiration_date IS NULL
              OR offer.expiration_date > CURRENT_TIMESTAMP
          )
        ORDER BY offer.id
    """

    FIND_PROFESSIONS = """
        SELECT
            profession.id::text AS profession_id,
            profession.name AS profession_name,
            true AS requires_registration,
            false AS accept_emergency_call
        FROM profession
        WHERE profession.name IS NOT NULL
          AND BTRIM(profession.name) <> ''
        ORDER BY profession.id
    """

    FIND_PROFESSIONALS = """
        WITH review_scores AS (
            SELECT
                professional_id AS technician_id,
                AVG(rating)::double precision AS average_rating,
                COUNT(*)::integer AS review_count
            FROM professional_review
            WHERE active IS TRUE
            GROUP BY professional_id
        ),
        service_metrics AS (
            SELECT
                professional.id AS technician_id,
                COUNT(DISTINCT technical_service.id)::integer
                    AS assigned_service_count,
                COUNT(DISTINCT technical_service.id) FILTER (
                    WHERE technical_service.status = 'COMPLETED'
                )::integer AS completed_service_count,
                COUNT(DISTINCT technical_service.id) FILTER (
                    WHERE technical_service.status = 'CANCELED'
                )::integer AS canceled_service_count,
                COUNT(DISTINCT technical_service.id) FILTER (
                    WHERE technical_service.status IN ('OPEN', 'IN_PROGRESS')
                )::integer AS active_workload
            FROM professional
            LEFT JOIN professional_affiliation
              ON professional_affiliation.professional_id = professional.id
            LEFT JOIN service_executor
              ON service_executor.professional_affiliation_id = professional_affiliation.id
            LEFT JOIN technical_service
              ON technical_service.id = service_executor.service_id
            GROUP BY professional.id
        )
        SELECT
            professional.id::text AS technician_id,
            'Profissional ' || LEFT(professional.id::text, 8) AS name,
            professional_registration.council || ' ' || professional_registration.number AS crea,
            profession.id::text AS profession_id,
            profession.name AS profession_name,
            true AS requires_registration,
            false AS accept_emergency_call,
            COALESCE(review_scores.average_rating, 0.0) AS average_rating_global,
            COALESCE(review_scores.review_count, 0) AS review_count_global,
            COALESCE(service_metrics.assigned_service_count, 0)
                AS assigned_service_count_global,
            COALESCE(service_metrics.completed_service_count, 0)
                AS completed_service_count_global,
            COALESCE(service_metrics.canceled_service_count, 0)
                AS canceled_service_count_global,
            COALESCE(service_metrics.active_workload, 0) AS active_workload,
            COUNT(DISTINCT certification.id) FILTER (
                WHERE certification.id IS NOT NULL
            )::integer AS valid_certification_count,
            COALESCE(
                ARRAY_AGG(DISTINCT certification.type) FILTER (
                    WHERE certification.type IS NOT NULL
                ),
                ARRAY[]::text[]
            ) AS certification_names
        FROM professional
        JOIN users
          ON users.id = professional.user_id
        JOIN professional_registration
          ON professional_registration.professional_id = professional.id
        JOIN profession
          ON profession.id = professional_registration.profession_id
        LEFT JOIN certification
          ON certification.professional_id = professional.id
        LEFT JOIN review_scores
          ON review_scores.technician_id = professional.id
        LEFT JOIN service_metrics
          ON service_metrics.technician_id = professional.id
        WHERE profession.name IS NOT NULL
          AND (
              professional_registration.expiration_date IS NULL
              OR professional_registration.expiration_date >= CURRENT_TIMESTAMP
          )
        GROUP BY
            professional.id,
            professional_registration.council,
            professional_registration.number,
            profession.id,
            profession.name,
            review_scores.average_rating,
            review_scores.review_count,
            service_metrics.assigned_service_count,
            service_metrics.completed_service_count,
            service_metrics.canceled_service_count,
            service_metrics.active_workload
        ORDER BY professional.id, profession.id
    """

    FIND_AFFILIATIONS = """
        WITH review_scores AS (
            SELECT
                professional_id AS technician_id,
                AVG(rating)::double precision AS average_rating,
                COUNT(*)::integer AS review_count
            FROM professional_review
            WHERE active IS TRUE
            GROUP BY professional_id
        ),
        service_metrics AS (
            SELECT
                professional.id AS technician_id,
                COUNT(DISTINCT technical_service.id) FILTER (
                    WHERE technical_service.status IN ('OPEN', 'IN_PROGRESS')
                )::integer AS active_workload
            FROM professional
            LEFT JOIN professional_affiliation AS any_affiliation
              ON any_affiliation.professional_id = professional.id
            LEFT JOIN service_executor
              ON service_executor.professional_affiliation_id = any_affiliation.id
            LEFT JOIN technical_service
              ON technical_service.id = service_executor.service_id
            GROUP BY professional.id
        ),
        company_geolocation AS (
            SELECT
                company.id AS company_id,
                COUNT(geolocation.id)::integer AS geolocation_count,
                CASE WHEN COUNT(geolocation.id) = 1
                    THEN MIN(geolocation.latitude)::double precision
                END AS latitude,
                CASE WHEN COUNT(geolocation.id) = 1
                    THEN MIN(geolocation.longitude)::double precision
                END AS longitude
            FROM company
            LEFT JOIN geolocation
              ON geolocation.address_id = company.address_id
            GROUP BY company.id
        )
        SELECT
            professional_affiliation.id::text AS affiliation_id,
            professional_affiliation.affiliation_type,
            true AS active,
            professional.id::text AS technician_id,
            NULL AS crea,
            'Profissional ' || LEFT(professional.id::text, 8) AS name,
            company.id::text AS company_id,
            company.trade_name AS company_trade_name,
            COALESCE(review_scores.average_rating, 0.0) AS average_rating_global,
            COALESCE(review_scores.review_count, 0) AS review_count_global,
            COALESCE(service_metrics.active_workload, 0) AS active_workload,
            COALESCE(company_geolocation.geolocation_count, 0)
                AS company_geolocation_count,
            company_geolocation.latitude AS company_latitude,
            company_geolocation.longitude AS company_longitude
        FROM professional_affiliation
        JOIN professional
          ON professional.id = professional_affiliation.professional_id
        JOIN users
          ON users.id = professional.user_id
        LEFT JOIN company
          ON company.id = professional_affiliation.company_id
        LEFT JOIN company_geolocation
          ON company_geolocation.company_id = company.id
        LEFT JOIN review_scores
          ON review_scores.technician_id = professional.id
        LEFT JOIN service_metrics
          ON service_metrics.technician_id = professional.id
        ORDER BY professional_affiliation.id
    """

    # O schema atual do api-core não modela turnos de trabalho (não existe
    # tabela "shift"). Por decisão de produto, a disponibilidade por horário
    # não é avaliada: todo técnico é considerado disponível. Esta consulta
    # sempre retorna um conjunto vazio, mantendo o contrato de colunas.
    FIND_SHIFTS = """
        SELECT
            NULL::text AS shift_id,
            NULL::text AS technician_id,
            NULL::text AS day_week,
            NULL::timestamptz AS start_at,
            NULL::timestamptz AS end_at
        WHERE FALSE
    """

    # O schema atual não possui coluna de data agendada em technical_service.
    # Por decisão de produto, created_at é usado como scheduled_at: a data de
    # criação do registro é tratada como o momento em que a tarefa foi aberta.
    FIND_TECHNICAL_SERVICES = """
        WITH address_geolocation AS (
            SELECT
                address_id,
                COUNT(*)::integer AS geolocation_count,
                CASE WHEN COUNT(*) = 1
                    THEN MIN(latitude)::double precision
                END AS latitude,
                CASE WHEN COUNT(*) = 1
                    THEN MIN(longitude)::double precision
                END AS longitude
            FROM geolocation
            GROUP BY address_id
        )
        SELECT
            technical_service.id::text AS service_id,
            technical_service.purpose,
            LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
            technical_service.status,
            technical_service.created_at AS scheduled_at,
            technical_service.created_at,
            technical_service.end_date AS end_at,
            technical_project.id::text AS project_id,
            local_unit.id::text AS local_unit_id,
            COALESCE(address_geolocation.geolocation_count, 0)
                AS geolocation_count,
            address_geolocation.latitude,
            address_geolocation.longitude
        FROM technical_service
        JOIN technical_project
          ON technical_project.id = technical_service.technical_project_id
        LEFT JOIN local_unit
          ON local_unit.id = technical_project.local_unit_id
        LEFT JOIN address_geolocation
          ON address_geolocation.address_id = local_unit.address_id
        ORDER BY technical_service.id
    """

    FIND_SERVICE_EXPERIENCES = """
        SELECT
            professional_affiliation.professional_id::text AS technician_id,
            LOWER(BTRIM(technical_service.purpose)) AS normalized_purpose,
            COUNT(DISTINCT technical_service.id)::integer AS completed_count
        FROM technical_service
        JOIN service_executor
          ON service_executor.service_id = technical_service.id
        JOIN professional_affiliation
          ON professional_affiliation.id = service_executor.professional_affiliation_id
        WHERE technical_service.status = 'COMPLETED'
          AND BTRIM(technical_service.purpose) <> ''
        GROUP BY
            professional_affiliation.professional_id,
            LOWER(BTRIM(technical_service.purpose))
        ORDER BY professional_affiliation.professional_id, normalized_purpose
    """

    FIND_ASSIGNMENTS = """
        SELECT
            service_executor.id::text AS executor_id,
            service_executor.service_id::text AS service_id,
            service_executor.professional_affiliation_id::text AS affiliation_id,
            service_executor.role_function AS function
        FROM service_executor
        JOIN professional_affiliation
          ON professional_affiliation.id = service_executor.professional_affiliation_id
        JOIN professional
          ON professional.id = professional_affiliation.professional_id
        JOIN users
          ON users.id = professional.user_id
        ORDER BY service_executor.id
    """

    @staticmethod
    async def _fetch(
        connection: asyncpg.Connection,
        query: str,
        heartbeat: Heartbeat | None,
    ) -> list[asyncpg.Record]:
        rows = await connection.fetch(query)
        if heartbeat is not None:
            await heartbeat()
        return list(rows)

    @classmethod
    async def load_snapshot(
        cls,
        connection: asyncpg.Connection,
        heartbeat: Heartbeat | None = None,
    ) -> CoreGraphSnapshot:
        local_units = [
            cls._local_unit(row) for row in await cls._fetch(connection, cls.FIND_LOCAL_UNITS, heartbeat)
        ]

        panel_offers: list[dict] = []
        for row in await cls._fetch(connection, cls.FIND_PANEL_OFFERS, heartbeat):
            panel_offer = cls._panel_offer(row)
            if panel_offer is not None:
                panel_offers.append(panel_offer)

        professions = [
            cls._profession(row) for row in await cls._fetch(connection, cls.FIND_PROFESSIONS, heartbeat)
        ]
        professionals = [
            cls._professional(row) for row in await cls._fetch(connection, cls.FIND_PROFESSIONALS, heartbeat)
        ]
        affiliations = [
            cls._affiliation(row) for row in await cls._fetch(connection, cls.FIND_AFFILIATIONS, heartbeat)
        ]
        shifts = [cls._shift(row) for row in await cls._fetch(connection, cls.FIND_SHIFTS, heartbeat)]
        technical_services = [
            cls._technical_service(row)
            for row in await cls._fetch(
                connection,
                cls.FIND_TECHNICAL_SERVICES,
                heartbeat,
            )
        ]
        service_experiences = [
            cls._service_experience(row)
            for row in await cls._fetch(
                connection,
                cls.FIND_SERVICE_EXPERIENCES,
                heartbeat,
            )
        ]
        assignments = [
            cls._assignment(row) for row in await cls._fetch(connection, cls.FIND_ASSIGNMENTS, heartbeat)
        ]
        return CoreGraphSnapshot(
            local_units=local_units,
            panel_offers=panel_offers,
            professions=professions,
            professionals=professionals,
            affiliations=affiliations,
            shifts=shifts,
            technical_services=technical_services,
            service_experiences=service_experiences,
            assignments=assignments,
        )

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        number = float(value)
        return number if isfinite(number) else None

    @classmethod
    def _local_unit(cls, row: asyncpg.Record) -> dict:
        return {
            "id": row["id"],
            "location_type": row["location_type"],
            "complement": row["complement"],
            "geolocation_count": int(row["geolocation_count"]),
            "latitude": cls._optional_float(row["latitude"]),
            "longitude": cls._optional_float(row["longitude"]),
        }

    @classmethod
    def _panel_offer(cls, row: asyncpg.Record) -> dict | None:
        power_wp = cls._optional_float(row["power_wp"])
        efficiency = cls._optional_float(row["efficiency"])
        dimension = cls._optional_float(row["dimension"])
        weight = cls._optional_float(row["weight"])
        if (
            power_wp is None
            or power_wp <= 0
            or efficiency is None
            or not 0 <= efficiency <= 100
            or dimension is None
            or dimension <= 0
            or weight is None
            or weight <= 0
        ):
            return None

        return {
            "model_id": row["model_id"],
            "brand": row["brand"],
            "model": row["model"],
            "power_wp": power_wp,
            "efficiency": efficiency,
            "dimension": dimension,
            "weight": weight,
            "model_status": row["model_status"],
            "offer_id": row["offer_id"],
            "unit_price_cents": int(row["unit_price_cents"]),
            "availability": int(row["availability"]),
            "expiration_at": row["expiration_at"],
            "inventory_quantity": int(row["inventory_quantity"]),
            "effective_availability": int(row["effective_availability"]),
            "supplier_id": row["supplier_id"],
            "supplier_status": row["supplier_status"],
            "business_type": row["business_type"],
            "company_id": row["company_id"],
            "trade_name": row["trade_name"],
            "subscription_active": bool(row["subscription_active"]),
            "accepted_proposal_quantity": int(row["accepted_proposal_quantity"]),
            "supplier_geolocation_count": int(row["supplier_geolocation_count"]),
            "supplier_latitude": cls._optional_float(row["supplier_latitude"]),
            "supplier_longitude": cls._optional_float(row["supplier_longitude"]),
        }

    @staticmethod
    def _profession(row: asyncpg.Record) -> dict:
        return {
            "profession_id": row["profession_id"],
            "profession_name": row["profession_name"],
            "requires_registration": row["requires_registration"],
            "accept_emergency_call": bool(row["accept_emergency_call"]),
        }

    @staticmethod
    def _professional(row: asyncpg.Record) -> dict:
        return {
            "technician_id": row["technician_id"],
            "name": row["name"],
            "crea": row["crea"],
            "profession_id": row["profession_id"],
            "profession_name": row["profession_name"],
            "requires_registration": row["requires_registration"],
            "accept_emergency_call": bool(row["accept_emergency_call"]),
            "average_rating_global": float(row["average_rating_global"]),
            "review_count_global": int(row["review_count_global"]),
            "assigned_service_count_global": int(row["assigned_service_count_global"]),
            "completed_service_count_global": int(row["completed_service_count_global"]),
            "canceled_service_count_global": int(row["canceled_service_count_global"]),
            "active_workload": int(row["active_workload"]),
            "valid_certification_count": int(row["valid_certification_count"]),
            "certification_names": sorted(row["certification_names"] or []),
        }

    @classmethod
    def _affiliation(cls, row: asyncpg.Record) -> dict:
        return {
            "affiliation_id": row["affiliation_id"],
            "affiliation_type": row["affiliation_type"],
            "active": bool(row["active"]),
            "technician_id": row["technician_id"],
            "crea": row["crea"],
            "name": row["name"],
            "company_id": row["company_id"],
            "company_trade_name": row["company_trade_name"],
            "average_rating_global": float(row["average_rating_global"]),
            "review_count_global": int(row["review_count_global"]),
            "active_workload": int(row["active_workload"]),
            "company_geolocation_count": int(row["company_geolocation_count"]),
            "company_latitude": cls._optional_float(row["company_latitude"]),
            "company_longitude": cls._optional_float(row["company_longitude"]),
        }

    @staticmethod
    def _shift(row: asyncpg.Record) -> dict:
        return {
            "shift_id": row["shift_id"],
            "technician_id": row["technician_id"],
            "day_week": row["day_week"],
            "start_at": row["start_at"],
            "end_at": row["end_at"],
        }

    @classmethod
    def _technical_service(cls, row: asyncpg.Record) -> dict:
        return {
            "service_id": row["service_id"],
            "purpose": row["purpose"],
            "normalized_purpose": row["normalized_purpose"],
            "status": row["status"],
            "scheduled_at": row["scheduled_at"],
            "created_at": row["created_at"],
            "end_at": row["end_at"],
            "project_id": row["project_id"],
            "local_unit_id": row["local_unit_id"],
            "geolocation_count": int(row["geolocation_count"]),
            "latitude": cls._optional_float(row["latitude"]),
            "longitude": cls._optional_float(row["longitude"]),
        }

    @staticmethod
    def _service_experience(row: asyncpg.Record) -> dict:
        return {
            "technician_id": row["technician_id"],
            "normalized_purpose": row["normalized_purpose"],
            "completed_count": int(row["completed_count"]),
        }

    @staticmethod
    def _assignment(row: asyncpg.Record) -> dict:
        return {
            "executor_id": row["executor_id"],
            "service_id": row["service_id"],
            "affiliation_id": row["affiliation_id"],
            "function": row["function"],
        }
