# app/crud.py
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt
from app.models import User
from app.auth import verify_password

from . import models, schemas
from app.auth import get_password_hash, verify_password
from app.config import SECRET_KEY, ALGORITHM

# =====================================================
# USER UTILITIES
# =====================================================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_identifier(db: Session, identifier: str):
    return db.query(models.User).filter(
        (models.User.email == identifier) | (models.User.phone == identifier)
    ).first()


def authenticate_user(db, identifier: str, password: str):
    user = (
        db.query(User)
        .filter(
            (User.email == identifier) |
            (User.mobile == identifier)
        )
        .first()
    )

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user

def create_user(db: Session, user: schemas.UserCreate):
    role = db.query(models.Role).filter(models.Role.name == user.role).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    db_user = models.User(
        email=user.email,
        name=user.name,
        mobile=user.mobile, 
        hashed_password=get_password_hash(user.password),
        role=role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_invited_user(db: Session, user: schemas.UserInvite):
    role = db.query(models.Role).filter(models.Role.name == user.role).first()
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")

    db_user = models.User(
        email=user.email,
        name=user.email.split("@")[0],
        hashed_password=None,
        role=role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# =====================================================
# EVENT CONFLICT LOGIC (THE IMPORTANT PART)
# =====================================================

def _has_overlap(db: Session, user_id: int, start: datetime, end: datetime) -> bool:
    """
    Checks if THIS USER already has an overlapping event
    either as owner or participant.
    """
    return db.query(models.Event).filter(
        (
            (models.Event.user_id == user_id)
            | (models.Event.participants.any(models.User.id == user_id))
        ),
        models.Event.start_time < end,
        models.Event.end_time > start,
    ).first() is not None


def _is_regular_user(user: models.User) -> bool:
    """
    Only role 'user' participates in conflicts.
    """
    return not user.role or user.role.name == "user"


def create_event(db: Session, event: schemas.EventCreate, owner_id: int):
    """
    RULES:
    - Conflict checks ONLY for role == 'user'
    - Admin & Super Admin are ALWAYS ignored in conflicts
    """

    owner = db.query(models.User).filter(models.User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # 1️⃣ OWNER CONFLICT CHECK (ONLY IF REGULAR USER)
    if _is_regular_user(owner):
        if _has_overlap(db, owner.id, event.start_time, event.end_time):
            raise HTTPException(
                status_code=400,
                detail="Conflict: You already have an event at this time",
            )

    # 2️⃣ CREATE EVENT OBJECT
    db_event = models.Event(
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        user_id=owner.id,
    )

    # 3️⃣ PARTICIPANT CONFLICT CHECK (ONLY REGULAR USERS)
    if event.participants:
        participants = (
            db.query(models.User)
            .filter(models.User.id.in_(event.participants))
            .all()
        )

        for p in participants:
            if _is_regular_user(p):
                if _has_overlap(db, p.id, event.start_time, event.end_time):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Conflict: {p.name} already has an event at this time",
                    )

        db_event.participants.extend(participants)

    # 4️⃣ SAVE
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_event(
    db: Session,
    event_id: int,
    event: schemas.EventCreate,
    current_user: models.User,
):
    db_event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    if db_event.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot edit a cancelled event")

    is_owner = db_event.user_id == current_user.id
    is_admin = current_user.role.name in ["admin", "super_admin"]

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not allowed to edit this event")

    # ---------- CONFLICT CHECK (EXCLUDE SELF) ----------
    def has_overlap_excluding_self(user_id: int):
        return db.query(models.Event).filter(
            models.Event.id != event_id,  # 🔑 THIS IS CRITICAL
            (
                (models.Event.user_id == user_id)
                | (models.Event.participants.any(models.User.id == user_id))
            ),
            models.Event.start_time < event.end_time,
            models.Event.end_time > event.start_time,
            models.Event.status == "active",
        ).first() is not None

    # Owner conflict
    if current_user.role.name == "user":
        if has_overlap_excluding_self(current_user.id):
            raise HTTPException(
                status_code=400,
                detail="Conflict: You already have another event at this time",
            )

    # Participants conflict
    participants = []
    if event.participants:
        participants = (
            db.query(models.User)
            .filter(models.User.id.in_(event.participants))
            .all()
        )

        for p in participants:
            if p.role.name == "user":
                if has_overlap_excluding_self(p.id):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Conflict: {p.name} already has another event at this time",
                    )

    # ---------- UPDATE ----------
    db_event.title = event.title
    db_event.start_time = event.start_time
    db_event.end_time = event.end_time
    db_event.participants = participants

    db.commit()
    db.refresh(db_event)
    return db_event


def get_user_events(db: Session, user_id: int):
    return db.query(models.Event).filter(models.Event.user_id == user_id).all()


def get_other_users(db: Session, exclude_user_id: int):
    return db.query(models.User).filter(models.User.id != exclude_user_id).all()


# =====================================================
# INVITE TOKEN
# =====================================================

def generate_invite_token(email: str, role: str):
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def cancel_event(db, event_id: int, current_user):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status == "cancelled":
        raise HTTPException(status_code=400, detail="Event already cancelled")

    is_owner = event.user_id == current_user.id
    is_admin = current_user.role.name in ["admin", "super_admin"]

    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not allowed to cancel this event")

    event.status = "cancelled"
    event.cancelled_at = datetime.utcnow()
    event.cancelled_by = current_user.id

    db.commit()
    db.refresh(event)

    return event
