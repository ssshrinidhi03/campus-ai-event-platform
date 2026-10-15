from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    organization: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    registration_link: Optional[str] = None
    date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    tags: List[str] = []
    status: str = "DRAFT"
    capacity: Optional[int] = None
    poster_url: Optional[str] = None
    contact_email: Optional[str] = None
    online_meeting_url: Optional[str] = None
    speaker_info: Optional[str] = None
    additional_instructions: Optional[str] = None


class EventCreate(EventBase):
    organizer_id: Optional[int] = 2
    organizer_name: Optional[str] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            # Handle both "HH:MM" and "HH:MM:SS" formats
            parts = v.split(":")
            if len(parts) >= 2:
                return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        return v

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            # Parse date string to datetime at midnight
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime):
            return v
        return v


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    organization: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    registration_link: Optional[str] = None
    date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    capacity: Optional[int] = None
    poster_url: Optional[str] = None
    contact_email: Optional[str] = None
    online_meeting_url: Optional[str] = None
    speaker_info: Optional[str] = None
    additional_instructions: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    organization: Optional[str] = None
    venue: Optional[str] = None
    eligibility: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    registration_link: Optional[str] = None
    date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    tags: List[str] = []
    status: str = "DRAFT"
    organizer_id: int
    organizer_name: Optional[str] = None
    registration_count: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    capacity: Optional[int] = None
    poster_url: Optional[str] = None
    contact_email: Optional[str] = None
    online_meeting_url: Optional[str] = None
    speaker_info: Optional[str] = None
    additional_instructions: Optional[str] = None


class OrganizerDashboardStats(BaseModel):
    total_events: int
    total_registrations: int
    events_by_status: dict
    upcoming_events: int
    past_events: int


class OrganizerDashboardResponse(BaseModel):
    stats: OrganizerDashboardStats
    events: List[EventResponse]

