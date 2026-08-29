import logging
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from neo4j import AsyncSession

from app.config import settings
from app.core.errors import SyncInProgressError, UnsafeSnapshotError
from app.core.sync_service import SyncService
from app.database import neo4j_service, postgres_service
from app.schemas.responses import SyncResponse

logger = logging.getLogger(__name__)

sync_key_header = APIKeyHeader(
    name="X-Sync-Key",
    scheme_name="SyncApiKey",
    auto_error=False,
)


def require_sync_key(
    provided_key: Annotated[str | None, Security(sync_key_header)] = None,
) -> None:
    configured_key = settings.SYNC_API_KEY
    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sincronização manual não configurada",
        )

    if (
        provided_key is None
        or len(provided_key) > 512
        or not compare_digest(provided_key, configured_key.get_secret_value())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de sincronização inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )


router = APIRouter(
    prefix="/internal/sync",
    tags=["sync"],
    dependencies=[Depends(require_sync_key)],
)


@router.post("/core", response_model=SyncResponse)
async def synchronize_core_data(
    session: Annotated[AsyncSession, Depends(neo4j_service.get_write_session)],
):
    try:
        summary = await SyncService(postgres_service, session).synchronize()
        return {
            "status": "synchronized",
            "sync_version": summary.sync_version,
            "local_units": summary.local_units,
            "panel_models": summary.panel_models,
            "panel_offers": summary.panel_offers,
            "professionals": summary.professionals,
            "professions": summary.professions,
            "services": summary.services,
            "qualifications": summary.qualifications,
            "technician_affiliations": summary.technician_affiliations,
            "technical_services": summary.technical_services,
        }
    except SyncInProgressError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SYNC_IN_PROGRESS", "message": str(error)},
        ) from None
    except UnsafeSnapshotError:
        logger.exception("Snapshot inseguro recusado durante a sincronização")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "UNSAFE_SNAPSHOT",
                "message": "O snapshot não passou pelas validações de segurança.",
            },
        ) from None
    except Exception:
        logger.exception("Falha ao sincronizar o PostgreSQL do api-core com o Neo4j")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao sincronizar os dados do api-core",
        ) from None
