from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession

from app.core.event_service import EventService
from app.database import neo4j_service
from app.schemas.event import EventCreate

router = APIRouter(prefix="/events", tags=["Telemetry"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def track_event(
    payload: EventCreate,
    session: Annotated[AsyncSession, Depends(neo4j_service.get_session)],
):
    service = EventService(session)
    success = await service.register_event(payload)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível registrar o evento. Verifique o candidate_id.",
        )
    return {"status": "success", "message": "Evento de telemetria registrado com sucesso"}
