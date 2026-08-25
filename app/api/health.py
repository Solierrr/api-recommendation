import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession

from app.database import neo4j_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(session: Annotated[AsyncSession, Depends(neo4j_service.get_session)]):
    try:
        # Envia um comando Cypher super leve só para testar a resposta
        result = await session.run("RETURN 1 AS status")
        record = await result.single()

        if record and record["status"] == 1:
            return {"status": "online", "database": "connected"}

        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Resposta inesperada do banco")
    except HTTPException:
        raise
    except Exception:
        # Nunca expor detalhes internos (stack trace, host, credenciais) na resposta ao cliente.
        logger.exception("Falha no healthcheck de conexão com o Neo4j")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível: falha na conexão com o banco de dados",
        ) from None
