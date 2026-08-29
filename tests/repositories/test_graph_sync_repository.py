from dataclasses import replace

import pytest

from app.core.errors import SyncInProgressError, UnsafeSnapshotError
from app.repositories.core_graph_repository import CoreGraphSnapshot
from app.repositories.graph_sync_repository import GraphSyncRepository

NODE_KEYS = (
    "local_units",
    "solar_offers",
    "solar_models",
    "suppliers",
    "technicians",
    "professions",
    "affiliations",
    "shifts",
    "technical_services",
    "service_experiences",
)
RELATIONSHIP_KEYS = (
    "offer_models",
    "offer_suppliers",
    "registrations",
    "affiliation_technicians",
    "technician_shifts",
    "technician_experiences",
    "assignments",
)


class FakeResult:
    def __init__(self, record=None, error=None):
        self.record = record
        self.error = error

    async def single(self):
        if self.error:
            raise self.error
        return self.record

    async def consume(self):
        return None


class FakeSession:
    def __init__(
        self,
        *,
        active_version=None,
        previous_version=None,
        lock_acquired=True,
        renew_succeeds=True,
        node_counts=None,
        active_node_counts=None,
        relationship_counts=None,
        active_relationship_counts=None,
        pending_cleanup_versions=None,
        unreferenced_versions=None,
        activation_ack_lost=False,
        fail_query=None,
    ):
        self.initial_active_version = active_version
        self.active_version = active_version
        self.previous_version = previous_version
        self.lock_acquired = lock_acquired
        self.renew_succeeds = renew_succeeds
        self.node_counts = node_counts or {key: 0 for key in NODE_KEYS}
        self.active_node_counts = active_node_counts or {key: 0 for key in NODE_KEYS}
        self.relationship_counts = relationship_counts or {key: 0 for key in RELATIONSHIP_KEYS}
        self.active_relationship_counts = active_relationship_counts or {key: 0 for key in RELATIONSHIP_KEYS}
        self.pending_cleanup_versions = list(pending_cleanup_versions or [])
        self.unreferenced_versions = list(unreferenced_versions or [])
        self.activation_ack_lost = activation_ack_lost
        self.fail_query = fail_query
        self.lock_token = None
        self.queries = []

    async def run(self, query, **parameters):
        self.queries.append((query, parameters))
        if query == self.fail_query:
            raise RuntimeError("falha simulada")
        if query == GraphSyncRepository.ACQUIRE_LOCK:
            if not self.lock_acquired:
                return FakeResult(None)
            self.lock_token = parameters["sync_version"]
            return FakeResult({"active_version": self.active_version, "lock_fence": 1})
        if query == GraphSyncRepository.RENEW_LOCK:
            succeeds = self.renew_succeeds and self.lock_token == parameters["sync_version"]
            return FakeResult({"lock_token": parameters["sync_version"]} if succeeds else None)
        if query == GraphSyncRepository.RELEASE_LOCK:
            if self.lock_token == parameters["sync_version"]:
                self.lock_token = None
            return FakeResult()
        if query == GraphSyncRepository.SNAPSHOT_NODE_COUNTS:
            counts = (
                self.active_node_counts
                if parameters["sync_version"] == self.initial_active_version
                else self.node_counts
            )
            return FakeResult(counts)
        if query == GraphSyncRepository.SNAPSHOT_RELATIONSHIP_COUNTS:
            counts = (
                self.active_relationship_counts
                if parameters["sync_version"] == self.initial_active_version
                else self.relationship_counts
            )
            return FakeResult(counts)
        if query == GraphSyncRepository.REGISTER_UNREFERENCED_VERSIONS:
            for version in self.unreferenced_versions:
                if version not in self.pending_cleanup_versions:
                    self.pending_cleanup_versions.append(version)
            return FakeResult({"cleanup_versions": self.pending_cleanup_versions.copy()})
        if query == GraphSyncRepository.REGISTER_CLEANUP_VERSION:
            cleanup_version = parameters["cleanup_version"]
            if cleanup_version in {self.active_version, self.previous_version}:
                return FakeResult(None)
            if cleanup_version not in self.pending_cleanup_versions:
                self.pending_cleanup_versions.append(cleanup_version)
            return FakeResult({"cleanup_versions": self.pending_cleanup_versions.copy()})
        if query == GraphSyncRepository.CLEAR_CLEANUP_VERSIONS:
            cleared = set(parameters["cleanup_versions"])
            self.pending_cleanup_versions = [
                version for version in self.pending_cleanup_versions if version not in cleared
            ]
            return FakeResult()
        if query == GraphSyncRepository.ACTIVATE_SNAPSHOT:
            cleanup_version = self.previous_version
            if cleanup_version and cleanup_version not in self.pending_cleanup_versions:
                self.pending_cleanup_versions.append(cleanup_version)
            self.previous_version = self.active_version
            self.active_version = parameters["sync_version"]
            record = {
                "active_version": self.active_version,
                "previous_version": self.previous_version,
                "cleanup_versions": self.pending_cleanup_versions.copy(),
            }
            error = RuntimeError("ack de ativação perdido") if self.activation_ack_lost else None
            return FakeResult(record, error)
        if query == GraphSyncRepository.RECONCILE_ACTIVATION:
            if (
                self.active_version == parameters["sync_version"]
                and self.lock_token == parameters["sync_version"]
            ):
                return FakeResult(
                    {
                        "active_version": self.active_version,
                        "previous_version": self.previous_version,
                        "cleanup_versions": self.pending_cleanup_versions.copy(),
                    }
                )
            return FakeResult(None)
        return FakeResult()


def empty_snapshot() -> CoreGraphSnapshot:
    return CoreGraphSnapshot(
        local_units=[],
        panel_offers=[],
        professions=[],
        professionals=[],
        affiliations=[],
        shifts=[],
        technical_services=[],
        service_experiences=[],
        assignments=[],
    )


def local_unit_snapshot(count: int = 1) -> CoreGraphSnapshot:
    return replace(
        empty_snapshot(),
        local_units=[
            {
                "id": f"unit-{index}",
                "location_type": "HOUSE",
                "complement": None,
                "geolocation_count": 0,
                "latitude": None,
                "longitude": None,
            }
            for index in range(count)
        ],
    )


@pytest.mark.asyncio
async def test_sync_lock_blocks_concurrent_run() -> None:
    session = FakeSession(lock_acquired=False)
    snapshot = empty_snapshot()

    with pytest.raises(SyncInProgressError):
        await GraphSyncRepository.stage_and_activate(session, snapshot, "new-version")


@pytest.mark.asyncio
async def test_empty_snapshot_cannot_replace_active_version() -> None:
    session = FakeSession(active_version="active-version")
    snapshot = empty_snapshot()

    with pytest.raises(UnsafeSnapshotError, match="Snapshot vazio"):
        await GraphSyncRepository.stage_and_activate(session, snapshot, "new-version")

    assert any(query == GraphSyncRepository.REGISTER_CLEANUP_VERSION for query, _ in session.queries)
    assert any(query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS for query, _ in session.queries)
    assert not any(query == GraphSyncRepository.ACTIVATE_SNAPSHOT for query, _ in session.queries)


@pytest.mark.asyncio
async def test_initial_empty_snapshot_is_allowed() -> None:
    session = FakeSession(active_version=None)

    await GraphSyncRepository.stage_and_activate(session, empty_snapshot(), "first-version")

    assert any(query == GraphSyncRepository.ACTIVATE_SNAPSHOT for query, _ in session.queries)


@pytest.mark.asyncio
async def test_mismatched_node_count_prevents_activation_and_discards_staging() -> None:
    session = FakeSession(node_counts={key: 0 for key in NODE_KEYS})
    snapshot = local_unit_snapshot()

    with pytest.raises(UnsafeSnapshotError, match="Validação de nós"):
        await GraphSyncRepository.stage_and_activate(
            session,
            snapshot,
            "new-version",
        )

    assert not any(query == GraphSyncRepository.ACTIVATE_SNAPSHOT for query, _ in session.queries)
    assert any(query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS for query, _ in session.queries)


@pytest.mark.asyncio
async def test_mismatched_relationship_count_prevents_activation() -> None:
    node_counts = {key: 0 for key in NODE_KEYS}
    node_counts["local_units"] = 1
    relationship_counts = {key: 0 for key in RELATIONSHIP_KEYS}
    relationship_counts["assignments"] = 1
    session = FakeSession(
        node_counts=node_counts,
        relationship_counts=relationship_counts,
    )
    snapshot = local_unit_snapshot()

    with pytest.raises(UnsafeSnapshotError, match="Validação de relações"):
        await GraphSyncRepository.stage_and_activate(
            session,
            snapshot,
            "new-version",
        )


@pytest.mark.asyncio
async def test_node_domain_drop_is_rejected_before_staging() -> None:
    active_counts = {key: 0 for key in NODE_KEYS}
    active_counts["local_units"] = 10
    session = FakeSession(
        active_version="active-version",
        active_node_counts=active_counts,
    )
    snapshot = local_unit_snapshot()

    with pytest.raises(UnsafeSnapshotError, match="queda anormal"):
        await GraphSyncRepository.stage_and_activate(
            session,
            snapshot,
            "new-version",
            min_domain_retention_ratio=0.5,
        )

    assert not any(query == GraphSyncRepository.UPSERT_LOCAL_UNITS for query, _ in session.queries)


@pytest.mark.asyncio
async def test_relationship_domain_drop_is_rejected_before_staging() -> None:
    active_node_counts = {key: 0 for key in NODE_KEYS}
    active_node_counts["local_units"] = 1
    active_relationship_counts = {key: 0 for key in RELATIONSHIP_KEYS}
    active_relationship_counts["registrations"] = 10
    session = FakeSession(
        active_version="active-version",
        active_node_counts=active_node_counts,
        active_relationship_counts=active_relationship_counts,
    )
    snapshot = local_unit_snapshot()

    with pytest.raises(UnsafeSnapshotError, match="queda anormal"):
        await GraphSyncRepository.stage_and_activate(
            session,
            snapshot,
            "new-version",
            min_domain_retention_ratio=0.5,
        )


@pytest.mark.asyncio
async def test_lock_is_renewed_and_released_after_pending_cleanup() -> None:
    node_counts = {key: 0 for key in NODE_KEYS}
    node_counts["local_units"] = 2
    session = FakeSession(
        active_version="active-version",
        previous_version="older-version",
        active_node_counts=node_counts.copy(),
        node_counts=node_counts,
    )

    await GraphSyncRepository.stage_and_activate(
        session,
        local_unit_snapshot(2),
        "new-version",
        batch_size=1,
    )

    queries = [query for query, _ in session.queries]
    assert queries.count(GraphSyncRepository.RENEW_LOCK) >= 4
    assert queries.index(GraphSyncRepository.ACTIVATE_SNAPSHOT) < queries.index(
        GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS
    )
    assert queries.index(GraphSyncRepository.CLEAR_CLEANUP_VERSIONS) < queries.index(
        GraphSyncRepository.RELEASE_LOCK
    )
    cleanup_parameters = next(
        parameters
        for query, parameters in session.queries
        if query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS
    )
    assert cleanup_parameters["cleanup_versions"] == ["older-version"]
    assert session.pending_cleanup_versions == []


@pytest.mark.asyncio
async def test_cleanup_failure_stays_registered_for_future_retry() -> None:
    node_counts = {key: 0 for key in NODE_KEYS}
    node_counts["local_units"] = 1
    session = FakeSession(
        active_version="active-version",
        previous_version="older-version",
        active_node_counts=node_counts.copy(),
        node_counts=node_counts,
        fail_query=GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS,
    )

    await GraphSyncRepository.stage_and_activate(
        session,
        local_unit_snapshot(),
        "new-version",
    )

    assert session.pending_cleanup_versions == ["older-version"]
    assert not any(query == GraphSyncRepository.CLEAR_CLEANUP_VERSIONS for query, _ in session.queries)


@pytest.mark.asyncio
async def test_lost_activation_ack_is_reconciled_safely() -> None:
    node_counts = {key: 0 for key in NODE_KEYS}
    node_counts["local_units"] = 1
    session = FakeSession(
        node_counts=node_counts,
        activation_ack_lost=True,
    )

    await GraphSyncRepository.stage_and_activate(
        session,
        local_unit_snapshot(),
        "new-version",
    )

    assert session.active_version == "new-version"
    assert any(query == GraphSyncRepository.RECONCILE_ACTIVATION for query, _ in session.queries)
    assert not any(query == GraphSyncRepository.REGISTER_CLEANUP_VERSION for query, _ in session.queries)


@pytest.mark.asyncio
async def test_abort_never_deletes_active_or_previous_snapshot() -> None:
    session = FakeSession(
        active_version="active-version",
        previous_version="previous-version",
    )
    session.lock_token = "active-version"

    await GraphSyncRepository.abort_sync(session, "active-version")

    assert not any(query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS for query, _ in session.queries)


@pytest.mark.asyncio
async def test_staging_failure_discards_only_own_version() -> None:
    session = FakeSession(fail_query=GraphSyncRepository.UPSERT_LOCAL_UNITS)
    snapshot = local_unit_snapshot()

    with pytest.raises(RuntimeError, match="falha simulada"):
        await GraphSyncRepository.stage_and_activate(
            session,
            snapshot,
            "failed-version",
        )

    discard_parameters = next(
        parameters
        for query, parameters in session.queries
        if query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS
    )
    assert discard_parameters["cleanup_versions"] == ["failed-version"]


def test_lock_query_serializes_check_with_monotonic_fence() -> None:
    query = GraphSyncRepository.ACQUIRE_LOCK

    fence_position = query.index("SET state.lock_fence = coalesce(state.lock_fence, 0) + 1")
    availability_check_position = query.index("WHERE coalesce(state.sync_in_progress, false) = false")
    assert fence_position < availability_check_position


@pytest.mark.asyncio
async def test_new_lock_owner_recovers_unreferenced_staging() -> None:
    session = FakeSession(unreferenced_versions=["lost-staging-version"])

    await GraphSyncRepository.begin_sync(session, "new-owner-version")

    cleanup_parameters = next(
        parameters
        for query, parameters in session.queries
        if query == GraphSyncRepository.DELETE_SNAPSHOT_VERSIONS
    )
    assert cleanup_parameters["cleanup_versions"] == ["lost-staging-version"]
    assert session.pending_cleanup_versions == []
