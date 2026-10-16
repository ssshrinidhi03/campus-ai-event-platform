from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.schemas.health import HealthResponse
from app.db.database import get_db
from app.models.registration import EventRegistration
from app.models.saved_event import SavedEvent
from app.models.event import Event
from app.models.enums import EventStatus
from app.core.security import get_current_user
from .events import router as events_router
from .auth import router as auth_router
from .organizer import router as organizer_router
from .ai import router as ai_router
from .search import router as search_router

api_router = APIRouter()

# Health endpoint within API router (/api/v1/health)
@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="API Health Check",
    tags=["Health"]
)
def api_health() -> HealthResponse:
    """
    Check the health of the API router.
    Returns status: 'ok' if service is responsive.
    """
    return HealthResponse(status="ok")


class RegistrationCreate(BaseModel):
    name: str
    email: str
    college: str = ""


@api_router.post(
    "/events/{event_id}/register",
    summary="Register for an Event",
    tags=["Events"]
)
def register_event(event_id: int, req: RegistrationCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if event exists and is approved
    event = db.query(Event).filter(Event.id == event_id, Event.status == EventStatus.APPROVED).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not published")
    
    existing = db.query(EventRegistration).filter(
        EventRegistration.event_id == event_id,
        EventRegistration.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this event")
        
    registration = EventRegistration(
        event_id=event_id,
        user_id=current_user.id,
        status="REGISTERED"
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return {"message": "Registration successful", "registration_id": registration.id}


class SavedEventCreate(BaseModel):
    event_id: int


class SavedEventResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    saved_at: datetime
    event_title: str
    event_category: str
    event_date: str
    event_venue: str
    event_organizer_name: str

    class Config:
        from_attributes = True


@api_router.post(
    "/events/{event_id}/save",
    response_model=SavedEventResponse,
    summary="Save/Bookmark an Event",
    tags=["Events"]
)
def save_event(event_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save/bookmark an event for the current user."""
    # Check if event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if already saved
    existing = db.query(SavedEvent).filter(
        SavedEvent.event_id == event_id,
        SavedEvent.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Event already saved")
    
    saved = SavedEvent(event_id=event_id, user_id=current_user.id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    
    return SavedEventResponse(
        id=saved.id,
        event_id=saved.event_id,
        user_id=saved.user_id,
        saved_at=saved.saved_at,
        event_title=event.title,
        event_category=event.category or "",
        event_date=event.date.isoformat() if event.date else "",
        event_venue=event.venue or "",
        event_organizer_name=event.organizer.name if event.organizer else ""
    )


@api_router.delete(
    "/events/{event_id}/save",
    summary="Remove Saved Event",
    tags=["Events"]
)
def unsave_event(event_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a saved/bookmarked event for the current user."""
    saved = db.query(SavedEvent).filter(
        SavedEvent.event_id == event_id,
        SavedEvent.user_id == current_user.id
    ).first()
    
    if not saved:
        raise HTTPException(status_code=404, detail="Saved event not found")
    
    db.delete(saved)
    db.commit()
    
    return {"message": "Event removed from saved events"}


@api_router.get(
    "/saved-events",
    response_model=List[SavedEventResponse],
    summary="Get Current User's Saved Events",
    tags=["Events"]
)
def list_saved_events(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all saved/bookmarked events for the current user."""
    saved_events = db.query(SavedEvent).filter(
        SavedEvent.user_id == current_user.id
    ).order_by(SavedEvent.saved_at.desc()).all()
    
    result = []
    for saved in saved_events:
        event = db.query(Event).filter(Event.id == saved.event_id).first()
        if event:
            result.append(SavedEventResponse(
                id=saved.id,
                event_id=saved.event_id,
                user_id=saved.user_id,
                saved_at=saved.saved_at,
                event_title=event.title,
                event_category=event.category or "",
                event_date=event.date.isoformat() if event.date else "",
                event_venue=event.venue or "",
                event_organizer_name=event.organizer.name if event.organizer else ""
            ))
    
    return result


api_router.include_router(events_router)

api_router.include_router(auth_router)

api_router.include_router(organizer_router)

api_router.include_router(ai_router)

api_router.include_router(search_router)
