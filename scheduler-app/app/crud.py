# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from app.auth import get_password_hash, verify_password
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException
from app.config import SECRET_KEY, ALGORITHM

# ------------------- User Utilities ------------------- #

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        print("[AUTH] User not found:", email)
        return None

    if not verify_password(password, user.hashed_password):
        print("[AUTH] Password mismatch")
        return None

    return user


def create_user(db: Session, user: schemas.UserCreate):
    hashed_pw = get_password_hash(user.password)

    role = db.query(models.Role).filter(models.Role.name == user.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{user.role}' not found")

    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_pw,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_invited_user(db: Session, user: schemas.UserInvite):
    role = db.query(models.Role).filter(models.Role.name == user.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{user.role}' not found")

    db_user = models.User(
        email=user.email,
        name=user.email.split("@")[0],
        hashed_password=None,
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_permissions(db: Session, user_id: int, permissions: schemas.UserPermissionUpdate):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(models.Role).filter(models.Role.name == permissions.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{permissions.role}' not found")

    user.role = role
    db.commit()
    db.refresh(user)
    return user


# ------------------- Event Utilities ------------------- #

def _has_overlap(db: Session, user_id: int, start_time: datetime, end_time: datetime) -> bool:
    """
    Returns True if *this* user already has **any** overlapping event
    (as owner OR as participant).
    """
    return db.query(models.Event).filter(
        # 1. Owner of the event
        (models.Event.user_id == user_id) |
        # 2. Participant in the event
        (models.Event.participants.any(models.User.id == user_id)),
        # Overlap logic
        models.Event.start_time < end_time,
        models.Event.end_time > start_time
    ).first() is not None


def create_event(db: Session, event: schemas.EventCreate, owner_id: int):
    """
    - owner_id → the teacher / session owner
    - participants → list of student IDs
    - Conflict only when **the same user** appears in two overlapping slots.
    """
    # 1. Owner must be free
    if _has_overlap(db, owner_id, event.start_time, event.end_time):
        raise HTTPException(
            status_code=400,
            detail="Conflict: You (the owner) already have an event at this time."
        )

    # 2. Build the event object
    db_event = models.Event(
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        user_id=owner_id
    )

    # 3. Add participants and check each one
    if event.participants:
        participants = db.query(models.User).filter(
            models.User.id.in_(event.participants)
        ).all()

        for p in participants:
            if _has_overlap(db, p.id, event.start_time, event.end_time):
                raise HTTPException(
                    status_code=400,
                    detail=f"Conflict: '{p.name}' is already booked for this time."
                )

        db_event.participants.extend(participants)

    # 4. Persist
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_user_events(db: Session, user_id: int):
    return db.query(models.Event).filter(models.Event.user_id == user_id).all()


def get_other_users(db: Session, exclude_user_id: int):
    return db.query(models.User).filter(models.User.id != exclude_user_id).all()


# ------------------- Invite Token ------------------- #

def generate_invite_token(email: str, role: str):
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)