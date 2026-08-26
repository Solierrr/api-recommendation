from neo4j import AsyncSession

from app.repositories.event_repository import EventRepository
from app.schemas.event import EventCreate


class EventService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_event(self, event_data: EventCreate) -> bool:
        return await EventRepository.log_event(
            session=self.session,
            user_id=event_data.user_id,
            candidate_id=event_data.candidate_id,
            event_type=event_data.event_type.value,
        )
