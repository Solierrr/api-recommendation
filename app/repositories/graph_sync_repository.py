from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping

from neo4j import AsyncSession

from app.core.errors import SyncInProgressError, UnsafeSnapshotError
from app.repositories.core_graph_repository import CoreGraphSnapshot

logger = logging.getLogger(__name__)


class GraphSyncRepository:
    SOURCE = "api-core"
    DEFAULT_BATCH_SIZE = 500
    DEFAULT_LOCK_LEASE_SECONDS = 900
    DEFAULT_MIN_DOMAIN_RETENTION_RATIO = 0.5

    SCHEMA_STATEMENTS = (
        (
            "CREATE CONSTRAINT sync_state_source IF NOT EXISTS "
            "FOR (n:SyncState) REQUIRE n.source IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT local_unit_graph_key IF NOT EXISTS "
            "FOR (n:LocalUnit) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT solar_offer_graph_key IF NOT EXISTS "
            "FOR (n:SolarOffer) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT solar_model_graph_key IF NOT EXISTS "
            "FOR (n:SolarModel) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT supplier_graph_key IF NOT EXISTS "
            "FOR (n:Supplier) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT technician_graph_key IF NOT EXISTS "
            "FOR (n:Technician) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT profession_graph_key IF NOT EXISTS "
            "FOR (n:Profession) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT affiliation_graph_key IF NOT EXISTS "
            "FOR (n:TechnicianAffiliation) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT shift_graph_key IF NOT EXISTS "
            "FOR (n:Shift) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT technical_service_graph_key IF NOT EXISTS "
            "FOR (n:TechnicalService) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE CONSTRAINT service_experience_graph_key IF NOT EXISTS "
            "FOR (n:ServiceExperience) REQUIRE n.graph_key IS UNIQUE"
        ),
        (
            "CREATE INDEX local_unit_lookup IF NOT EXISTS "
            "FOR (n:LocalUnit) ON (n.source, n.sync_version, n.id)"
        ),
        (
            "CREATE INDEX profession_lookup IF NOT EXISTS "
            "FOR (n:Profession) ON (n.source, n.sync_version, n.id)"
        ),
        (
            "CREATE INDEX technical_service_lookup IF NOT EXISTS "
            "FOR (n:TechnicalService) ON (n.source, n.sync_version, n.id)"
        ),
        (
            "CREATE INDEX offer_snapshot_lookup IF NOT EXISTS "
            "FOR (n:SolarOffer) ON (n.source, n.sync_version)"
        ),
        (
            "CREATE INDEX affiliation_snapshot_lookup IF NOT EXISTS "
            "FOR (n:TechnicianAffiliation) ON "
            "(n.source, n.sync_version, n.active)"
        ),
    )

    ACQUIRE_LOCK = """
        MERGE (state:SyncState {source: $source})
        ON CREATE SET state.sync_in_progress = false,
                      state.lock_fence = 0
        SET state.lock_fence = coalesce(state.lock_fence, 0) + 1
        WITH state
        WHERE coalesce(state.sync_in_progress, false) = false
           OR (state.lock_expires_at IS NOT NULL
               AND state.lock_expires_at < datetime())
           OR (state.lock_expires_at IS NULL
               AND (state.locked_at IS NULL
                    OR state.locked_at < datetime() - duration('PT15M')))
        SET state.sync_in_progress = true,
            state.lock_token = $sync_version,
            state.locked_at = datetime(),
            state.lock_expires_at = datetime()
                + duration({seconds: $lease_seconds})
        RETURN state.active_version AS active_version,
               state.lock_fence AS lock_fence
    """

    RENEW_LOCK = """
        MATCH (state:SyncState {
            source: $source,
            lock_token: $sync_version,
            sync_in_progress: true
        })
        SET state.lock_expires_at = datetime()
            + duration({seconds: $lease_seconds})
        RETURN state.lock_token AS lock_token
    """

    RELEASE_LOCK = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        SET state.sync_in_progress = false
        REMOVE state.lock_token, state.locked_at, state.lock_expires_at
    """

    REGISTER_CLEANUP_VERSION = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        WITH state, coalesce(state.pending_cleanup_versions, []) AS pending
        WHERE (state.active_version IS NULL
               OR $cleanup_version <> state.active_version)
          AND (state.previous_version IS NULL
               OR $cleanup_version <> state.previous_version)
        SET state.pending_cleanup_versions = CASE
            WHEN $cleanup_version IN pending THEN pending
            ELSE pending + [$cleanup_version]
        END
        RETURN state.pending_cleanup_versions AS cleanup_versions
    """

    DELETE_SNAPSHOT_VERSIONS = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        WITH state
        MATCH (node)
        WHERE node.source = $source
          AND node.sync_version IN $cleanup_versions
          AND (state.active_version IS NULL
               OR node.sync_version <> state.active_version)
          AND (state.previous_version IS NULL
               OR node.sync_version <> state.previous_version)
        DETACH DELETE node
    """

    CLEAR_CLEANUP_VERSIONS = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        SET state.pending_cleanup_versions = [
            version IN coalesce(state.pending_cleanup_versions, [])
            WHERE NOT version IN $cleanup_versions
        ]
    """

    REGISTER_UNREFERENCED_VERSIONS = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        OPTIONAL MATCH (node)
        WHERE node.source = $source
          AND node.sync_version IS NOT NULL
          AND node.sync_version <> $sync_version
          AND (state.active_version IS NULL
               OR node.sync_version <> state.active_version)
          AND (state.previous_version IS NULL
               OR node.sync_version <> state.previous_version)
        WITH state,
             coalesce(state.pending_cleanup_versions, []) AS pending,
             collect(DISTINCT node.sync_version) AS unreferenced
        SET state.pending_cleanup_versions = pending + [
            version IN unreferenced
            WHERE version IS NOT NULL AND NOT version IN pending
        ]
        RETURN state.pending_cleanup_versions AS cleanup_versions
    """

    UPSERT_LOCAL_UNITS = """
        UNWIND $rows AS row
        MERGE (unit:LocalUnit {
            graph_key: $source + '|' + $sync_version + '|' + row.id
        })
        SET unit.id = row.id,
            unit.location_type = row.location_type,
            unit.complement = row.complement,
            unit.geolocation_count = row.geolocation_count,
            unit.latitude = row.latitude,
            unit.longitude = row.longitude,
            unit.source = $source,
            unit.sync_version = $sync_version
    """

    UPSERT_PANEL_OFFERS = """
        UNWIND $rows AS row
        MERGE (model:SolarModel {
            graph_key: $source + '|' + $sync_version + '|' + row.model_id
        })
        SET model.id = row.model_id,
            model.brand = row.brand,
            model.model = row.model,
            model.power_wp = row.power_wp,
            model.efficiency = row.efficiency,
            model.dimension = row.dimension,
            model.weight = row.weight,
            model.status = row.model_status,
            model.source = $source,
            model.sync_version = $sync_version

        MERGE (supplier:Supplier {
            graph_key: $source + '|' + $sync_version + '|' + row.supplier_id
        })
        SET supplier.id = row.supplier_id,
            supplier.status = row.supplier_status,
            supplier.business_type = row.business_type,
            supplier.company_id = row.company_id,
            supplier.trade_name = row.trade_name,
            supplier.subscription_active = row.subscription_active,
            supplier.geolocation_count = row.supplier_geolocation_count,
            supplier.latitude = row.supplier_latitude,
            supplier.longitude = row.supplier_longitude,
            supplier.source = $source,
            supplier.sync_version = $sync_version

        MERGE (offer:SolarOffer {
            graph_key: $source + '|' + $sync_version + '|' + row.offer_id
        })
        SET offer.id = row.offer_id,
            offer.unit_price_cents = row.unit_price_cents,
            offer.availability = row.availability,
            offer.inventory_quantity = row.inventory_quantity,
            offer.effective_availability = row.effective_availability,
            offer.expiration_at = row.expiration_at,
            offer.accepted_proposal_quantity = row.accepted_proposal_quantity,
            offer.source = $source,
            offer.sync_version = $sync_version

        MERGE (offer)-[model_relation:OF_MODEL]->(model)
        SET model_relation.source = $source,
            model_relation.sync_version = $sync_version
        MERGE (offer)-[supplier_relation:FROM_SUPPLIER]->(supplier)
        SET supplier_relation.source = $source,
            supplier_relation.sync_version = $sync_version
    """

    UPSERT_PROFESSIONS = """
        UNWIND $rows AS row
        MERGE (profession:Profession {
            graph_key: $source + '|' + $sync_version + '|' + row.profession_id
        })
        SET profession.id = row.profession_id,
            profession.name = row.profession_name,
            profession.requires_registration = row.requires_registration,
            profession.accept_emergency_call = row.accept_emergency_call,
            profession.source = $source,
            profession.sync_version = $sync_version
    """

    UPSERT_PROFESSIONALS = """
        UNWIND $rows AS row
        MERGE (technician:Technician {
            graph_key: $source + '|' + $sync_version + '|' + row.technician_id
        })
        SET technician.id = row.technician_id,
            technician.name = row.name,
            technician.crea = row.crea,
            technician.user_active = true,
            technician.average_rating_global = row.average_rating_global,
            technician.review_count_global = row.review_count_global,
            technician.assigned_service_count_global = row.assigned_service_count_global,
            technician.completed_service_count_global = row.completed_service_count_global,
            technician.canceled_service_count_global = row.canceled_service_count_global,
            technician.active_workload = row.active_workload,
            technician.source = $source,
            technician.sync_version = $sync_version

        MATCH (profession:Profession {
            graph_key: $source + '|' + $sync_version + '|' + row.profession_id
        })
        MERGE (technician)-[registration:REGISTERED_AS]->(profession)
        SET registration.valid_certification_count = row.valid_certification_count,
            registration.certification_names = row.certification_names,
            registration.source = $source,
            registration.sync_version = $sync_version
    """

    UPSERT_AFFILIATIONS = """
        UNWIND $rows AS row
        MERGE (technician:Technician {
            graph_key: $source + '|' + $sync_version + '|' + row.technician_id
        })
        SET technician.id = row.technician_id,
            technician.name = row.name,
            technician.crea = row.crea,
            technician.user_active = true,
            technician.average_rating_global = row.average_rating_global,
            technician.review_count_global = row.review_count_global,
            technician.active_workload = row.active_workload,
            technician.source = $source,
            technician.sync_version = $sync_version

        MERGE (affiliation:TechnicianAffiliation {
            graph_key: $source + '|' + $sync_version + '|' + row.affiliation_id
        })
        SET affiliation.id = row.affiliation_id,
            affiliation.affiliation_type = row.affiliation_type,
            affiliation.active = row.active,
            affiliation.company_id = row.company_id,
            affiliation.company_trade_name = row.company_trade_name,
            affiliation.company_geolocation_count = row.company_geolocation_count,
            affiliation.company_latitude = row.company_latitude,
            affiliation.company_longitude = row.company_longitude,
            affiliation.source = $source,
            affiliation.sync_version = $sync_version

        MERGE (affiliation)-[relation:OF_TECHNICIAN]->(technician)
        SET relation.source = $source,
            relation.sync_version = $sync_version
    """

    UPSERT_SHIFTS = """
        UNWIND $rows AS row
        MERGE (technician:Technician {
            graph_key: $source + '|' + $sync_version + '|' + row.technician_id
        })
        ON CREATE SET technician.id = row.technician_id,
                      technician.user_active = true,
                      technician.source = $source,
                      technician.sync_version = $sync_version

        MERGE (shift:Shift {
            graph_key: $source + '|' + $sync_version + '|' + row.shift_id
        })
        SET shift.id = row.shift_id,
            shift.day_week = row.day_week,
            shift.start_at = row.start_at,
            shift.end_at = row.end_at,
            shift.source = $source,
            shift.sync_version = $sync_version

        MERGE (technician)-[relation:HAS_SHIFT]->(shift)
        SET relation.source = $source,
            relation.sync_version = $sync_version
    """

    UPSERT_TECHNICAL_SERVICES = """
        UNWIND $rows AS row
        MERGE (service:TechnicalService {
            graph_key: $source + '|' + $sync_version + '|' + row.service_id
        })
        SET service.id = row.service_id,
            service.purpose = row.purpose,
            service.normalized_purpose = row.normalized_purpose,
            service.status = row.status,
            service.scheduled_at = row.scheduled_at,
            service.created_at = row.created_at,
            service.end_at = row.end_at,
            service.project_id = row.project_id,
            service.local_unit_id = row.local_unit_id,
            service.geolocation_count = row.geolocation_count,
            service.latitude = row.latitude,
            service.longitude = row.longitude,
            service.source = $source,
            service.sync_version = $sync_version
    """

    UPSERT_SERVICE_EXPERIENCES = """
        UNWIND $rows AS row
        MERGE (technician:Technician {
            graph_key: $source + '|' + $sync_version + '|' + row.technician_id
        })
        ON CREATE SET technician.id = row.technician_id,
                      technician.user_active = true,
                      technician.source = $source,
                      technician.sync_version = $sync_version

        MERGE (experience:ServiceExperience {
            graph_key: $source + '|' + $sync_version + '|' +
                       row.technician_id + '|' + row.normalized_purpose
        })
        SET experience.technician_id = row.technician_id,
            experience.normalized_purpose = row.normalized_purpose,
            experience.completed_count = row.completed_count,
            experience.source = $source,
            experience.sync_version = $sync_version

        MERGE (technician)-[relation:HAS_EXPERIENCE]->(experience)
        SET relation.source = $source,
            relation.sync_version = $sync_version
    """

    UPSERT_ASSIGNMENTS = """
        UNWIND $rows AS row
        MATCH (affiliation:TechnicianAffiliation {
            graph_key: $source + '|' + $sync_version + '|' + row.affiliation_id
        })
        MATCH (service:TechnicalService {
            graph_key: $source + '|' + $sync_version + '|' + row.service_id
        })
        MERGE (affiliation)-[assignment:ASSIGNED_TO {
            executor_id: row.executor_id
        }]->(service)
        SET assignment.function = row.function,
            assignment.source = $source,
            assignment.sync_version = $sync_version
    """

    SNAPSHOT_NODE_COUNTS = """
        MATCH (node)
        WHERE node.source = $source
          AND node.sync_version = $sync_version
        RETURN
            count(CASE WHEN node:LocalUnit THEN 1 END) AS local_units,
            count(CASE WHEN node:SolarOffer THEN 1 END) AS solar_offers,
            count(CASE WHEN node:SolarModel THEN 1 END) AS solar_models,
            count(CASE WHEN node:Supplier THEN 1 END) AS suppliers,
            count(CASE WHEN node:Technician THEN 1 END) AS technicians,
            count(CASE WHEN node:Profession THEN 1 END) AS professions,
            count(CASE WHEN node:TechnicianAffiliation THEN 1 END) AS affiliations,
            count(CASE WHEN node:Shift THEN 1 END) AS shifts,
            count(CASE WHEN node:TechnicalService THEN 1 END) AS technical_services,
            count(CASE WHEN node:ServiceExperience THEN 1 END) AS service_experiences
    """

    SNAPSHOT_RELATIONSHIP_COUNTS = """
        MATCH (start)-[relationship]->(end)
        WHERE start.source = $source
          AND start.sync_version = $sync_version
          AND end.source = $source
          AND end.sync_version = $sync_version
        RETURN
            count(CASE WHEN type(relationship) = 'OF_MODEL' THEN 1 END) AS offer_models,
            count(CASE WHEN type(relationship) = 'FROM_SUPPLIER' THEN 1 END) AS offer_suppliers,
            count(CASE WHEN type(relationship) = 'REGISTERED_AS' THEN 1 END) AS registrations,
            count(CASE WHEN type(relationship) = 'OF_TECHNICIAN' THEN 1 END) AS affiliation_technicians,
            count(CASE WHEN type(relationship) = 'HAS_SHIFT' THEN 1 END) AS technician_shifts,
            count(CASE WHEN type(relationship) = 'HAS_EXPERIENCE' THEN 1 END) AS technician_experiences,
            count(CASE WHEN type(relationship) = 'ASSIGNED_TO' THEN 1 END) AS assignments
    """

    ACTIVATE_SNAPSHOT = """
        MATCH (state:SyncState {source: $source, lock_token: $sync_version})
        WITH state,
             state.previous_version AS cleanup_version,
             coalesce(state.pending_cleanup_versions, []) AS pending
        SET state.previous_version = state.active_version,
            state.active_version = $sync_version,
            state.activated_at = datetime(),
            state.pending_cleanup_versions = CASE
                WHEN cleanup_version IS NULL OR cleanup_version IN pending
                    THEN pending
                ELSE pending + [cleanup_version]
            END
        RETURN state.active_version AS active_version,
               state.previous_version AS previous_version,
               state.pending_cleanup_versions AS cleanup_versions
    """

    RECONCILE_ACTIVATION = """
        MATCH (state:SyncState {
            source: $source,
            lock_token: $sync_version,
            active_version: $sync_version
        })
        RETURN state.active_version AS active_version,
               state.previous_version AS previous_version,
               coalesce(state.pending_cleanup_versions, []) AS cleanup_versions
    """

    @staticmethod
    def _chunks(rows: list[dict], batch_size: int) -> Iterable[list[dict]]:
        for index in range(0, len(rows), batch_size):
            yield rows[index : index + batch_size]

    @staticmethod
    async def _consume(session: AsyncSession, query: str, **parameters) -> None:
        result = await session.run(query, **parameters)
        await result.consume()

    @classmethod
    async def ensure_schema(cls, session: AsyncSession) -> None:
        for statement in cls.SCHEMA_STATEMENTS:
            await cls._consume(session, statement)

    @classmethod
    async def begin_sync(
        cls,
        session: AsyncSession,
        sync_version: str,
        lease_seconds: int = DEFAULT_LOCK_LEASE_SECONDS,
    ) -> str | None:
        await cls.ensure_schema(session)
        result = await session.run(
            cls.ACQUIRE_LOCK,
            source=cls.SOURCE,
            sync_version=sync_version,
            lease_seconds=lease_seconds,
        )
        record = await result.single()
        if record is None:
            raise SyncInProgressError("Já existe uma sincronização em andamento.")

        try:
            cleanup_result = await session.run(
                cls.REGISTER_UNREFERENCED_VERSIONS,
                source=cls.SOURCE,
                sync_version=sync_version,
            )
            cleanup_record = await cleanup_result.single()
            cleanup_versions = (
                list(cleanup_record["cleanup_versions"] or []) if cleanup_record else []
            )
            await cls._cleanup_snapshot_versions(
                session,
                sync_version,
                cleanup_versions,
            )
        except Exception:
            logger.exception(
                "Falha ao recuperar versões órfãs; elas permanecerão pendentes"
            )

        return record["active_version"]

    @classmethod
    async def renew_lock(
        cls,
        session: AsyncSession,
        sync_version: str,
        lease_seconds: int = DEFAULT_LOCK_LEASE_SECONDS,
    ) -> None:
        result = await session.run(
            cls.RENEW_LOCK,
            source=cls.SOURCE,
            sync_version=sync_version,
            lease_seconds=lease_seconds,
        )
        if await result.single() is None:
            raise UnsafeSnapshotError(
                "O lock da sincronização foi perdido antes da ativação."
            )

    @classmethod
    async def release_lock(cls, session: AsyncSession, sync_version: str) -> None:
        await cls._consume(
            session,
            cls.RELEASE_LOCK,
            source=cls.SOURCE,
            sync_version=sync_version,
        )

    @classmethod
    async def _cleanup_snapshot_versions(
        cls,
        session: AsyncSession,
        sync_version: str,
        cleanup_versions: Iterable[str],
    ) -> None:
        versions = sorted({version for version in cleanup_versions if version})
        if not versions:
            return
        await cls._consume(
            session,
            cls.DELETE_SNAPSHOT_VERSIONS,
            source=cls.SOURCE,
            sync_version=sync_version,
            cleanup_versions=versions,
        )
        await cls._consume(
            session,
            cls.CLEAR_CLEANUP_VERSIONS,
            source=cls.SOURCE,
            sync_version=sync_version,
            cleanup_versions=versions,
        )

    @classmethod
    async def abort_sync(cls, session: AsyncSession, sync_version: str) -> None:
        registered = False
        try:
            result = await session.run(
                cls.REGISTER_CLEANUP_VERSION,
                source=cls.SOURCE,
                sync_version=sync_version,
                cleanup_version=sync_version,
            )
            registered = await result.single() is not None
            if registered:
                await cls._cleanup_snapshot_versions(
                    session,
                    sync_version,
                    [sync_version],
                )
        except Exception:
            logger.exception(
                "Falha ao registrar ou descartar o staging da sincronização %s",
                sync_version,
            )
        try:
            await cls.release_lock(session, sync_version)
        except Exception:
            logger.exception(
                "Falha ao liberar o lock da sincronização %s", sync_version
            )

    @classmethod
    async def _stage_rows(
        cls,
        session: AsyncSession,
        query: str,
        rows: list[dict],
        sync_version: str,
        batch_size: int,
        lease_seconds: int,
    ) -> None:
        for batch in cls._chunks(rows, batch_size):
            await cls._consume(
                session,
                query,
                source=cls.SOURCE,
                sync_version=sync_version,
                rows=batch,
            )
            await cls.renew_lock(session, sync_version, lease_seconds)

    @classmethod
    async def _snapshot_counts(
        cls,
        session: AsyncSession,
        query: str,
        sync_version: str,
        expected_keys: Iterable[str],
    ) -> dict[str, int]:
        result = await session.run(
            query,
            source=cls.SOURCE,
            sync_version=sync_version,
        )
        record = await result.single()
        if record is None:
            return {key: 0 for key in expected_keys}
        return {key: int(record[key] or 0) for key in expected_keys}

    @staticmethod
    def _validate_exact_counts(
        expected: Mapping[str, int],
        actual: Mapping[str, int],
        entity_type: str,
    ) -> None:
        mismatches = [
            f"{name}: esperado {expected_count}, encontrado {actual.get(name, 0)}"
            for name, expected_count in expected.items()
            if actual.get(name, 0) != expected_count
        ]
        if mismatches:
            raise UnsafeSnapshotError(
                f"Validação de {entity_type} do snapshot falhou: "
                + "; ".join(mismatches)
            )

    @staticmethod
    def _validate_domain_retention(
        active_counts: Mapping[str, int],
        new_counts: Mapping[str, int],
        minimum_ratio: float,
    ) -> None:
        drops = [
            f"{name}: {new_counts.get(name, 0)}/{active_count}"
            for name, active_count in active_counts.items()
            if active_count > 0
            and new_counts.get(name, 0) / active_count < minimum_ratio
        ]
        if drops:
            raise UnsafeSnapshotError(
                "Snapshot recusado por queda anormal de domínio: " + "; ".join(drops)
            )

    @classmethod
    async def complete_sync(
        cls,
        session: AsyncSession,
        snapshot: CoreGraphSnapshot,
        sync_version: str,
        active_version: str | None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        lease_seconds: int = DEFAULT_LOCK_LEASE_SECONDS,
        min_domain_retention_ratio: float = DEFAULT_MIN_DOMAIN_RETENTION_RATIO,
    ) -> None:
        if active_version and snapshot.expected_node_count == 0:
            raise UnsafeSnapshotError(
                "Snapshot vazio recusado porque já existe uma versão ativa."
            )

        if active_version:
            active_counts = await cls._snapshot_counts(
                session,
                cls.SNAPSHOT_NODE_COUNTS,
                active_version,
                snapshot.expected_node_counts,
            )
            cls._validate_domain_retention(
                active_counts,
                snapshot.expected_node_counts,
                min_domain_retention_ratio,
            )
            active_relationship_counts = await cls._snapshot_counts(
                session,
                cls.SNAPSHOT_RELATIONSHIP_COUNTS,
                active_version,
                snapshot.expected_relationship_counts,
            )
            cls._validate_domain_retention(
                active_relationship_counts,
                snapshot.expected_relationship_counts,
                min_domain_retention_ratio,
            )

        await cls.renew_lock(session, sync_version, lease_seconds)
        stages = (
            (cls.UPSERT_LOCAL_UNITS, snapshot.local_units),
            (cls.UPSERT_PANEL_OFFERS, snapshot.panel_offers),
            (cls.UPSERT_PROFESSIONS, snapshot.professions),
            (cls.UPSERT_PROFESSIONALS, snapshot.professionals),
            (cls.UPSERT_AFFILIATIONS, snapshot.affiliations),
            (cls.UPSERT_SHIFTS, snapshot.shifts),
            (cls.UPSERT_TECHNICAL_SERVICES, snapshot.technical_services),
            (cls.UPSERT_SERVICE_EXPERIENCES, snapshot.service_experiences),
            (cls.UPSERT_ASSIGNMENTS, snapshot.assignments),
        )
        for query, rows in stages:
            await cls._stage_rows(
                session,
                query,
                rows,
                sync_version,
                batch_size,
                lease_seconds,
            )

        actual_node_counts = await cls._snapshot_counts(
            session,
            cls.SNAPSHOT_NODE_COUNTS,
            sync_version,
            snapshot.expected_node_counts,
        )
        cls._validate_exact_counts(
            snapshot.expected_node_counts,
            actual_node_counts,
            "nós",
        )
        actual_relationship_counts = await cls._snapshot_counts(
            session,
            cls.SNAPSHOT_RELATIONSHIP_COUNTS,
            sync_version,
            snapshot.expected_relationship_counts,
        )
        cls._validate_exact_counts(
            snapshot.expected_relationship_counts,
            actual_relationship_counts,
            "relações",
        )

        await cls.renew_lock(session, sync_version, lease_seconds)
        activation_failure: Exception | None = None
        record = None
        try:
            result = await session.run(
                cls.ACTIVATE_SNAPSHOT,
                source=cls.SOURCE,
                sync_version=sync_version,
            )
            record = await result.single()
        except Exception as error:
            activation_failure = error

        if record is None:
            reconciliation_result = await session.run(
                cls.RECONCILE_ACTIVATION,
                source=cls.SOURCE,
                sync_version=sync_version,
            )
            record = await reconciliation_result.single()

        if record is None:
            if activation_failure is not None:
                raise activation_failure
            raise UnsafeSnapshotError(
                "O lock da sincronização foi perdido antes da ativação."
            )

        cleanup_versions = list(record["cleanup_versions"] or [])
        if cleanup_versions:
            try:
                await cls._cleanup_snapshot_versions(
                    session,
                    sync_version,
                    cleanup_versions,
                )
            except Exception:
                logger.exception(
                    "Snapshot ativado, mas a limpeza das versões %s falhou; "
                    "elas permanecerão pendentes",
                    cleanup_versions,
                )

    @classmethod
    async def stage_and_activate(
        cls,
        session: AsyncSession,
        snapshot: CoreGraphSnapshot,
        sync_version: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        lease_seconds: int = DEFAULT_LOCK_LEASE_SECONDS,
        min_domain_retention_ratio: float = DEFAULT_MIN_DOMAIN_RETENTION_RATIO,
    ) -> None:
        """Compatibilidade para chamadas que já possuem o snapshot em memória."""
        active_version = await cls.begin_sync(session, sync_version, lease_seconds)
        try:
            await cls.complete_sync(
                session,
                snapshot,
                sync_version,
                active_version,
                batch_size,
                lease_seconds,
                min_domain_retention_ratio,
            )
        except Exception:
            await cls.abort_sync(session, sync_version)
            raise
        else:
            await cls.release_lock(session, sync_version)
