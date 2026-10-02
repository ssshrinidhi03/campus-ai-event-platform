from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.enums import EventStatus


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    venue: Optional[str] = None
    status: EventStatus = EventStatus.DRAFT


class EventCreate(EventBase):
    organizer_id: int
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class EventResponse(EventBase):
    id: int
    organizer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
