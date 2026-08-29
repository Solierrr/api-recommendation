from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    VIEW = "VIEW"
    CLICK = "CLICK"
    HIRE = "HIRE"


class EventCreate(BaseModel):
    user_id: str = Field(..., min_length=1, examples=["empresa_123"])
    candidate_id: str = Field(..., min_length=1, examples=["prof_1"])
    event_type: EventType = Field(..., examples=["CLICK"])
