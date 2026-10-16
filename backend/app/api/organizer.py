from datetime import date, datetime, time as dt_time
import asyncio
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.core.security import require_organizer
from app.models.user import User
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.enums import EventStatus
from app.schemas.event import (
    EventResponse,
    EventCreate,
    EventUpdate,
    OrganizerDashboardResponse,
    OrganizerDashboardStats,
)
from app.services.vector_store import SimpleVectorStore

logger = logging.getLogger(__name__)

_vector_store = None

def _get_vector_store() -> SimpleVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = SimpleVectorStore()
    return _vector_store

def _index_event_in_vector_store(event: Event) -> None:
    """Index a published event in the vector store for RAG search."""
    try:
        asyncio.run(_get_vector_store().add_event(event))
    except Exception as e:
        # Vector store indexing must not break event publishing/updating
        logger.warning(f"Failed to index event {event.id} in vector store: {e}")

router = APIRouter(prefix="/organizer", tags=["Organizer Dashboard"])


def _event_to_response(event: Event, organizer_name: str, reg_count: int = 0) -> EventResponse:
    """Convert Event model to EventResponse schema."""
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
        organization=event.organization,
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
        registration_count=reg_count,
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
    "/dashboard",
    response_model=OrganizerDashboardResponse,
    summary="Get organizer dashboard overview",
)
def get_organizer_dashboard(
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Return dashboard statistics and events for the authenticated organizer.
    Includes total events, total registrations, events by status, and upcoming/past events.
    """
    events = (
        db.query(Event)
        .filter(Event.organizer_id == current_user.id)
        .order_by(Event.created_at.desc())
        .all()
    )

    total_events = len(events)

    reg_counts = {}
    if events:
        event_ids = [e.id for e in events]
        reg_results = (
            db.query(EventRegistration.event_id, func.count(EventRegistration.id).label("reg_count"))
            .filter(EventRegistration.event_id.in_(event_ids))
            .group_by(EventRegistration.event_id)
            .all()
        )
        reg_counts = {r.event_id: r.reg_count for r in reg_results}

    total_registrations = sum(reg_counts.values())

    events_by_status = {}
    for status in EventStatus:
        events_by_status[status.value] = sum(1 for e in events if e.status == status)

    today = date.today()
    upcoming_events = sum(
        1
        for e in events
        if e.date and e.date >= today and e.status in [EventStatus.APPROVED, EventStatus.PENDING_APPROVAL]
    )
    past_events = sum(
        1
        for e in events
        if e.date and e.date < today
    )

    event_responses = []
    for event in events:
        reg_count = reg_counts.get(event.id, 0)
        event_responses.append(_event_to_response(event, current_user.name, reg_count))

    stats = OrganizerDashboardStats(
        total_events=total_events,
        total_registrations=total_registrations,
        events_by_status=events_by_status,
        upcoming_events=upcoming_events,
        past_events=past_events,
    )

    return OrganizerDashboardResponse(stats=stats, events=event_responses)


@router.get(
    "/events",
    response_model=List[EventResponse],
    summary="List all events organized by the current organizer",
)
def list_organizer_events(
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Return all events created by the authenticated organizer (all statuses).
    Includes registration count for each event.
    """
    events = (
        db.query(Event)
        .filter(Event.organizer_id == current_user.id)
        .order_by(Event.created_at.desc())
        .all()
    )

    event_ids = [e.id for e in events]
    reg_counts = {}
    if event_ids:
        reg_results = (
            db.query(EventRegistration.event_id, func.count(EventRegistration.id).label("reg_count"))
            .filter(EventRegistration.event_id.in_(event_ids))
            .group_by(EventRegistration.event_id)
            .all()
        )
        reg_counts = {r.event_id: r.reg_count for r in reg_results}

    event_responses = []
    for event in events:
        reg_count = reg_counts.get(event.id, 0)
        event_responses.append(_event_to_response(event, current_user.name, reg_count))

    return event_responses


@router.get(
    "/events/{event_id}",
    summary="Get event details with registrations",
)
def get_organizer_event_with_registrations(
    event_id: int,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Return event details with all registrations for the authenticated organizer.
    Only accessible by the event's organizer or admin.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == current_user.id).first()
    if not event:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found or access denied")

    registrations = (
        db.query(EventRegistration, User)
        .join(User, EventRegistration.user_id == User.id)
        .filter(EventRegistration.event_id == event_id)
        .all()
    )

    reg_responses = [
        {
            "id": reg.id,
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "registered_at": reg.registered_at,
            "status": reg.status,
        }
        for reg, user in registrations
    ]

    reg_count = len(reg_responses)

    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "venue": event.venue,
        "eligibility": event.eligibility,
        "registration_deadline": event.registration_deadline,
        "registration_link": event.registration_link,
        "date": event.date,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "tags": event.tags.split(",") if event.tags else [],
        "status": event.status,
        "organizer_id": event.organizer_id,
        "organizer_name": current_user.name,
        "registration_count": reg_count,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "capacity": event.capacity,
        "poster_url": event.poster_url,
        "contact_email": event.contact_email,
        "online_meeting_url": event.online_meeting_url,
        "speaker_info": event.speaker_info,
        "additional_instructions": event.additional_instructions,
        "registrations": reg_responses,
    }


@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
def create_event(
    event_data: EventCreate,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Create a new event for the authenticated organizer.
    
    The event is created with DRAFT status by default.
    The organizer is derived from the authenticated user.
    """
    # Validate required fields
    if not event_data.title or not event_data.title.strip():
        raise HTTPException(status_code=400, detail="Event title is required")
    
    # Parse date and times
    event_date = None
    start_time = None
    end_time = None
    
    if event_data.date:
        event_date = event_data.date.date()
    
    if event_data.start_time:
        try:
            parts = event_data.start_time.split(":")
            start_time = dt_time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid start_time format. Use HH:MM")
    
    if event_data.end_time:
        try:
            parts = event_data.end_time.split(":")
            end_time = dt_time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid end_time format. Use HH:MM")
    
    # Validate dates
    if event_date and start_time and end_time:
        if end_time <= start_time:
            raise HTTPException(
                status_code=400, 
                detail="End time must be after start time"
            )
    
    # Validate registration deadline
    if event_data.registration_deadline and event_date and start_time:
        event_start = datetime.combine(event_date, start_time)
        if event_data.registration_deadline > event_start:
            raise HTTPException(
                status_code=400,
                detail="Registration deadline must be before event start time"
            )
    
    # Create event with organizer from authenticated user
    event = Event(
        title=event_data.title.strip(),
        description=event_data.description,
        category=event_data.category,
        venue=event_data.venue,
        eligibility=event_data.eligibility,
        registration_deadline=event_data.registration_deadline,
        registration_link=event_data.registration_link,
        date=event_date,
        start_time=start_time,
        end_time=end_time,
        tags=",".join(event_data.tags) if event_data.tags else None,
        capacity=event_data.capacity,
        poster_url=event_data.poster_url,
        contact_email=event_data.contact_email,
        online_meeting_url=event_data.online_meeting_url,
        speaker_info=event_data.speaker_info,
        additional_instructions=event_data.additional_instructions,
        status=EventStatus.DRAFT,
        organizer_id=current_user.id,
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return _event_to_response(event, current_user.name, 0)


@router.put(
    "/events/{event_id}",
    response_model=EventResponse,
    summary="Update an existing event (draft)",
)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Update an existing event for the authenticated organizer.
    Only allows updating events owned by the organizer.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found or access denied")
    
    # Only allow updating drafts
    if event.status != EventStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail="Only draft events can be updated. Current status: " + event.status.value
        )
    
    # Parse date and times if provided
    event_date = None
    start_time = None
    end_time = None
    
    if event_data.date is not None:
        if event_data.date:
            event_date = event_data.date.date()
        else:
            event_date = None
    
    if event_data.start_time is not None:
        if event_data.start_time:
            try:
                parts = event_data.start_time.split(":")
                start_time = dt_time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use HH:MM")
        else:
            start_time = None
    
    if event_data.end_time is not None:
        if event_data.end_time:
            try:
                parts = event_data.end_time.split(":")
                end_time = dt_time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Invalid end_time format. Use HH:MM")
        else:
            end_time = None
    
    # Validate dates if all provided
    if event_date and start_time and end_time:
        if end_time <= start_time:
            raise HTTPException(
                status_code=400, 
                detail="End time must be after start time"
            )
    
    # Validate registration deadline
    if event_data.registration_deadline and event_date and start_time:
        event_start = datetime.combine(event_date, start_time)
        if event_data.registration_deadline > event_start:
            raise HTTPException(
                status_code=400,
                detail="Registration deadline must be before event start time"
            )
    
    # Validate capacity if provided
    if event_data.capacity is not None and event_data.capacity <= 0:
        raise HTTPException(status_code=400, detail="Capacity must be a positive integer")
    
    # Validate contact email if provided
    if event_data.contact_email and "@" not in event_data.contact_email:
        raise HTTPException(status_code=400, detail="Invalid contact email format")
    
    # Validate URLs if provided
    for url_field, field_name in [
        (event_data.poster_url, "poster_url"),
        (event_data.online_meeting_url, "online_meeting_url"),
        (event_data.registration_link, "registration_link"),
    ]:
        if url_field and not (url_field.startswith("http://") or url_field.startswith("https://")):
            raise HTTPException(status_code=400, detail=f"Invalid {field_name} format. Must be a valid URL")
    
    # Update fields
    if event_data.title is not None:
        event.title = event_data.title.strip()
    if event_data.description is not None:
        event.description = event_data.description
    if event_data.category is not None:
        event.category = event_data.category
    if event_data.venue is not None:
        event.venue = event_data.venue
    if event_data.eligibility is not None:
        event.eligibility = event_data.eligibility
    if event_data.registration_deadline is not None:
        event.registration_deadline = event_data.registration_deadline
    if event_data.registration_link is not None:
        event.registration_link = event_data.registration_link
    if event_data.date is not None:
        event.date = event_date
    if event_data.start_time is not None:
        event.start_time = start_time
    if event_data.end_time is not None:
        event.end_time = end_time
    if event_data.tags is not None:
        event.tags = ",".join(event_data.tags) if event_data.tags else None
    if event_data.capacity is not None:
        event.capacity = event_data.capacity
    if event_data.poster_url is not None:
        event.poster_url = event_data.poster_url
    if event_data.contact_email is not None:
        event.contact_email = event_data.contact_email
    if event_data.online_meeting_url is not None:
        event.online_meeting_url = event_data.online_meeting_url
    if event_data.speaker_info is not None:
        event.speaker_info = event_data.speaker_info
    if event_data.additional_instructions is not None:
        event.additional_instructions = event_data.additional_instructions
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Re-index the updated event in the vector store for RAG search
    _index_event_in_vector_store(event)
    
    return _event_to_response(event, current_user.name, 0)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event (draft only)",
)
def delete_event(
    event_id: int,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Delete an event for the authenticated organizer.
    Only allows deleting draft events owned by the organizer.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found or access denied")
    
    # Only allow deleting drafts
    if event.status != EventStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail="Only draft events can be deleted. Current status: " + event.status.value
        )
    
    db.delete(event)
    db.commit()
    
    return None


@router.post(
    "/events/{event_id}/publish",
    response_model=EventResponse,
    summary="Publish event (approved organizers)",
)
def publish_event(
    event_id: int,
    current_user: User = Depends(require_organizer),
    db: Session = Depends(get_db),
):
    """
    Publish a draft event directly (approved organizers only).
    Changes status to APPROVED and makes it visible on public discovery feed.
    Only allows publishing draft events owned by the organizer.
    """
    event = db.query(Event).filter(Event.id == event_id, Event.organizer_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found or access denied")
    
    # Only allow publishing drafts
    if event.status != EventStatus.DRAFT:
        raise HTTPException(
            status_code=400, 
            detail="Only draft events can be published. Current status: " + event.status.value
        )
    
    # Validate required fields before publishing
    if not event.title or not event.title.strip():
        raise HTTPException(status_code=400, detail="Event title is required")
    if not event.category:
        raise HTTPException(status_code=400, detail="Event category is required")
    if not event.venue or not event.venue.strip():
        raise HTTPException(status_code=400, detail="Event venue is required")
    if not event.date:
        raise HTTPException(status_code=400, detail="Event date is required")
    if not event.start_time:
        raise HTTPException(status_code=400, detail="Event start time is required")
    if not event.end_time:
        raise HTTPException(status_code=400, detail="Event end time is required")
    
    # Change status to APPROVED (published directly for authorized organizers)
    event.status = EventStatus.APPROVED
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Index the published event in the vector store for RAG search
    _index_event_in_vector_store(event)
    
    return _event_to_response(event, current_user.name, 0)