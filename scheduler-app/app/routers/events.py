from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from .. import schemas, crud, auth, models
from ..database import SessionLocal
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from app.utils.permissions import has_permission
from typing import List, Dict, Any
from datetime import datetime, timedelta
from jose import jwt

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _serialize_user(user: models.User) -> Dict[str, Any]:
    """Return simple dict for User matching UserOut: role as string and permissions dict."""
    # Handle None role - default to "user"
    role_name = user.role.name if user.role else "user"
    
    # Handle permissions - empty dict if no role
    permissions = {}
    if user.role and user.role.permissions:
        permissions = {perm.key: True for perm in user.role.permissions}
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "mobile": user.mobile,  # This can be None
        "role": role_name,  # Always a string
        "permissions": permissions,
    }


def _serialize_event(e: models.Event) -> Dict[str, Any]:
    participants = [_serialize_user(u) for u in getattr(e, "participants", [])]
    return {
        "id": e.id,
        "title": e.title,
        "start_time": e.start_time,
        "end_time": e.end_time,
        "user_id": e.user_id,
        "status": e.status,
        "event_type": e.event_type,  # ✅ ADDED THIS
        "participants": participants,
    }

@router.post("/", response_model=schemas.EventOut)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # permission check
    if not has_permission(current_user, "can_create_events"):
        raise HTTPException(status_code=403, detail="Not authorized to create events")

    # Use your crud function (it handles recurrence)
    db_event = crud.create_recurring_events(db, event, owner_id=current_user.id)

    # eager-load role permissions for participants might not be loaded here;
    # refresh via query to be safe (load participants -> role -> permissions)
    db_event = (
        db.query(models.Event)
        .options(joinedload(models.Event.participants).joinedload(models.User.role).joinedload(models.Role.permissions))
        .filter(models.Event.id == db_event.id)
        .first()
    )

    serialized = _serialize_event(db_event)
    # EventOut expects datetime objects — returning ISO strings is acceptable if client expects them;
    # if you require actual datetimes, change serialization above to pass datetimes (we used isoformat to be safe).
    return serialized

@router.get("/", response_model=List[schemas.EventOut])
def list_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # Load events where user is owner or participant; eager load role & permissions for participants
    events = (
        db.query(models.Event)
        .options(joinedload(models.Event.participants).joinedload(models.User.role).joinedload(models.Role.permissions))
        .filter(
            (models.Event.user_id == current_user.id)
            | (models.Event.participants.any(models.User.id == current_user.id))
            | (models.Event.event_type.in_(["holiday", "weekly_off", "announced_holiday"]))
        )
        .all()
    )

    result = [_serialize_event(e) for e in events]
    return result

@router.delete("/{event_id}")
def cancel_event_endpoint(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    event = crud.cancel_event(db, event_id, current_user)
    return {"message": "Event cancelled", "event_id": event.id}

@router.put("/{event_id}", response_model=schemas.EventOut)
def update_event_endpoint(
    event_id: int,
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    updated_event = crud.update_event(db, event_id, event, current_user)

    updated_event = (
        db.query(models.Event)
        .options(
            joinedload(models.Event.participants)
            .joinedload(models.User.role)
            .joinedload(models.Role.permissions)
        )
        .filter(models.Event.id == updated_event.id)
        .first()
    )

    return _serialize_event(updated_event)


