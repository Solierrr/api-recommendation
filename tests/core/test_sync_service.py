from contextlib import asynccontextmanager

import pytest

from app.core.sync_service import SyncService
from app.repositories.core_graph_repository import (
    CoreGraphRepository,
    CoreGraphSnapshot,
)
from app.repositories.graph_sync_repository import GraphSyncRepository


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


class FakePostgres:
    def __init__(self, events):
        self.events = events

    @asynccontextmanager
    async def connection(self):
        self.events.append("postgres_enter")
        try:
            yield object()
        finally:
            self.events.append("postgres_exit")


@pytest.mark.asyncio
async def test_lock_precedes_extraction_and_transaction_closes_before_staging(
    monkeypatch,
) -> None:
    events = []
    snapshot = empty_snapshot()

    async def begin_sync(_cls, _session, _version, _lease):
        events.append("lock")
        return "active-version"

    async def renew_lock(_cls, _session, _version, _lease):
        events.append("heartbeat")

    async def load_snapshot(_cls, _connection, heartbeat):
        events.append("extract")
        await heartbeat()
        return snapshot

    async def complete_sync(
        _cls,
        _session,
        _snapshot,
        _version,
        _active_version,
        **_kwargs,
    ):
        events.append("stage")

    async def release_lock(_cls, _session, _version):
        events.append("release")

    monkeypatch.setattr(GraphSyncRepository, "begin_sync", classmethod(begin_sync))
    monkeypatch.setattr(GraphSyncRepository, "renew_lock", classmethod(renew_lock))
    monkeypatch.setattr(
        GraphSyncRepository,
        "complete_sync",
        classmethod(complete_sync),
    )
    monkeypatch.setattr(
        GraphSyncRepository,
        "release_lock",
        classmethod(release_lock),
    )
    monkeypatch.setattr(
        CoreGraphRepository,
        "load_snapshot",
        classmethod(load_snapshot),
    )

    await SyncService(FakePostgres(events), object()).synchronize()

    assert events.index("lock") < events.index("postgres_enter")
    assert events.index("postgres_exit") < events.index("stage")
    assert events.index("stage") < events.index("release")


@pytest.mark.asyncio
async def test_extraction_failure_aborts_sync(monkeypatch) -> None:
    events = []

    async def begin_sync(_cls, _session, _version, _lease):
        events.append("lock")
        return None

    async def load_snapshot(_cls, _connection, heartbeat):
        del heartbeat
        raise RuntimeError("falha de leitura")

    async def abort_sync(_cls, _session, _version):
        events.append("abort")

    monkeypatch.setattr(GraphSyncRepository, "begin_sync", classmethod(begin_sync))
    monkeypatch.setattr(GraphSyncRepository, "abort_sync", classmethod(abort_sync))
    monkeypatch.setattr(
        CoreGraphRepository,
        "load_snapshot",
        classmethod(load_snapshot),
    )

    with pytest.raises(RuntimeError, match="falha de leitura"):
        await SyncService(FakePostgres(events), object()).synchronize()

    assert events == ["lock", "postgres_enter", "postgres_exit", "abort"]
