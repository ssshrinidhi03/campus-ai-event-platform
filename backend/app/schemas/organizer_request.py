from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.enums import OrganizerRequestStatus


class OrganizerRequestBase(BaseModel):
    reason: Optional[str] = None


class OrganizerRequestCreate(OrganizerRequestBase):
    pass


class OrganizerRequestResponse(OrganizerRequestBase):
    id: int
    user_id: int
    status: OrganizerRequestStatus
    admin_id: Optional[int] = None
    admin_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizerRequestUpdate(BaseModel):
    status: OrganizerRequestStatus
    admin_note: Optional[str] = None
