# backend/app/api/events.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.db.database import get_db
from app.models.event import Event
from app.models.user import User
from app.models.enums import EventStatus
from app.schemas.event import EventResponse

router = APIRouter()


def _event_to_response(event: Event, organizer_name: str = None) -> EventResponse:
    """Convert Event model to EventResponse schema."""
    from datetime import datetime, time as dt_time
    event_date = None
    if event.date:
        event_date = datetime.combine(event.date, dt_time.min)
    
    start_time_str = None
    if event.start_time:
        start_time_str = event.start_time.strftime("%H:%M")
    
    end_time_str = None
    if event.end_time:
        end_time_str = event.end_time.strftime("%H:%M")
    
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        category=event.category,
        venue=event.venue,
        eligibility=event.eligibility,
        registration_deadline=event.registration_deadline,
        registration_link=event.registration_link,
        date=event_date,
        start_time=start_time_str,
        end_time=end_time_str,
        tags=event.tags.split(",") if event.tags else [],
        status=event.status.value if hasattr(event.status, 'value') else event.status,
        organizer_id=event.organizer_id,
        organizer_name=organizer_name,
        registration_count=0,  # Could be computed if needed
        created_at=event.created_at,
        updated_at=event.updated_at,
        capacity=event.capacity,
        poster_url=event.poster_url,
        contact_email=event.contact_email,
        online_meeting_url=event.online_meeting_url,
        speaker_info=event.speaker_info,
        additional_instructions=event.additional_instructions,
    )


@router.get(
    "/events",
    response_model=List[EventResponse],
    summary="List published events",
    tags=["Events"]
)
def list_events(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query for title, description, tags, or organizer name"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """Return all events with status APPROVED (published), optionally filtered by search query and category."""
    query = db.query(Event, User.name.label("organizer_name")).join(User, Event.organizer_id == User.id).filter(Event.status == EventStatus.APPROVED)
    
    # Apply search filter
    if q:
        search_term = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                Event.title.ilike(search_term),
                Event.description.ilike(search_term),
                Event.tags.ilike(search_term),
                User.name.ilike(search_term),
            )
        )
    
    # Apply category filter
    if category and category != "All":
        query = query.filter(Event.category == category)
    
    events = query.order_by(Event.date).all()
    return [_event_to_response(e, organizer_name) for e, organizer_name in events]


@router.get(
    "/events/{event_id}",
    response_model=EventResponse,
    summary="Get event details",
    tags=["Events"]
)
def get_event(event_id: int, db: Session = Depends(get_db)):
    result = db.query(Event, User.name.label("organizer_name")).join(User, Event.organizer_id == User.id).filter(Event.id == event_id, Event.status == EventStatus.APPROVED).first()
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    event, organizer_name = result
    return _event_to_response(event, organizer_name)
