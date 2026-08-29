import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from neo4j import AsyncSession

from app.config import settings
from app.database import PostgresService
from app.repositories.core_graph_repository import CoreGraphRepository
from app.repositories.graph_sync_repository import GraphSyncRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncSummary:
    sync_version: UUID
    local_units: int
    panel_models: int
    panel_offers: int
    professionals: int
    professions: int
    qualifications: int
    technician_affiliations: int
    technical_services: int

    @property
    def services(self) -> int:
        """Alias mantido para logs e consumidores da resposta anterior."""
        return self.professions


class SyncService:
    def __init__(self, postgres: PostgresService, session: AsyncSession):
        self.postgres = postgres
        self.session = session

    async def _renew_lock(self, sync_version: str) -> None:
        await GraphSyncRepository.renew_lock(
            self.session,
            sync_version,
            settings.SYNC_LOCK_LEASE_SECONDS,
        )

    async def synchronize(self) -> SyncSummary:
        sync_version = uuid4()
        version = str(sync_version)
        active_version = await GraphSyncRepository.begin_sync(
            self.session,
            version,
            settings.SYNC_LOCK_LEASE_SECONDS,
        )
        activated = False
        try:
            # A transação repeatable-read existe somente durante a extração. O lock
            # já está adquirido e a transação termina antes do staging no Neo4j.
            async with self.postgres.connection() as connection:
                snapshot = await CoreGraphRepository.load_snapshot(
                    connection,
                    heartbeat=lambda: self._renew_lock(version),
                )

            await GraphSyncRepository.complete_sync(
                self.session,
                snapshot,
                version,
                active_version,
                batch_size=settings.SYNC_BATCH_SIZE,
                lease_seconds=settings.SYNC_LOCK_LEASE_SECONDS,
                min_domain_retention_ratio=(settings.SYNC_MIN_DOMAIN_RETENTION_RATIO),
            )
            activated = True
        finally:
            if activated:
                try:
                    await GraphSyncRepository.release_lock(self.session, version)
                except Exception:
                    logger.exception(
                        "Snapshot %s ativado, mas o lock não pôde ser liberado; "
                        "a lease expirará automaticamente",
                        version,
                    )
            else:
                await GraphSyncRepository.abort_sync(self.session, version)

        return SyncSummary(sync_version=sync_version, **snapshot.counts)
