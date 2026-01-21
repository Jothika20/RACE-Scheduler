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

# Keep decode logic in auth.decode_access_token — reuse it
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    try:
        payload = auth.decode_access_token(token)
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def _serialize_user(user: models.User) -> Dict[str, Any]:
    """Return simple dict for User matching UserOut: role as string and permissions dict."""
    role_name = user.role.name if user.role else None
    # role.permissions should be loaded (use joinedload when querying if needed)
    permissions = {perm.key: True for perm in getattr(user.role, "permissions", [])} if user.role else {}
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role_name,
        "permissions": permissions,
    }

def _serialize_event(e: models.Event) -> Dict[str, Any]:
    participants = [_serialize_user(u) for u in getattr(e, "participants", [])]
    return {
        "id": e.id,
        "title": e.title,
        "start_time": e.start_time.isoformat() if isinstance(e.start_time, datetime) else e.start_time,
        "end_time": e.end_time.isoformat() if isinstance(e.end_time, datetime) else e.end_time,
        "user_id": e.user_id,
        "participants": participants,
    }

@router.post("/", response_model=schemas.EventOut)
def create_event(
    event: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # permission check
    if not has_permission(current_user, "can_create_events"):
        raise HTTPException(status_code=403, detail="Not authorized to create events")

    # Use your crud function (it returns an ORM Event)
    db_event = crud.create_event(db, event, owner_id=current_user.id)

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
    current_user: models.User = Depends(get_current_user),
):
    # Load events where user is owner or participant; eager load role & permissions for participants
    events = (
        db.query(models.Event)
        .options(joinedload(models.Event.participants).joinedload(models.User.role).joinedload(models.Role.permissions))
        .filter(
            (models.Event.user_id == current_user.id)
            | (models.Event.participants.any(models.User.id == current_user.id))
        )
        .all()
    )

    result = [_serialize_event(e) for e in events]
    return result
