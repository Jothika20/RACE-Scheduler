from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import calendar  # ✅ ADDED THIS
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from app.models import User
from sqlalchemy import func
import secrets

from . import models, schemas
from app.auth import get_password_hash, verify_password
from app.config import SECRET_KEY, ALGORITHM

# =====================================================
# USER UTILITIES
# =====================================================

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# def get_user_by_identifier(db: Session, identifier: str):
#     return db.query(models.User).filter(
#         (models.User.email == identifier) | (models.User.phone == identifier)
#     ).first()


# In crud.py - Update authenticate_user with debug logs
def authenticate_user(db: Session, identifier: str, password: str):
    print(f"Attempting to authenticate user with identifier: {identifier}")
    
    user = (
        db.query(models.User)
        .filter(
            (models.User.email == identifier) |
            (models.User.mobile == identifier)
        )
        .first()
    )

    if not user:
        print(f"No user found with identifier: {identifier}")
        return None

    print(f"User found: {user.email if user.email else 'No email'}, {user.mobile if user.mobile else 'No mobile'}")
    print(f"Has hashed_password: {bool(user.hashed_password)}")

    if not user.hashed_password:
        print("User has no password (invited but not activated)")
        return None  # invited but not activated

    password_valid = verify_password(password, user.hashed_password)
    print(f"Password valid: {password_valid}")

    if not password_valid:
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
# PASSWORD RESET FUNCTIONS
# =====================================================

def generate_password_reset_token(db: Session, identifier: str):
    """Generate a password reset token for user (email or phone)"""
    # Find user by email or phone
    user = db.query(models.User).filter(
        models.User.email == identifier
    ).first()
    
    if not user:
        # Don't reveal if user exists or not for security
        raise HTTPException(status_code=400, detail="If an account exists, a reset link will be sent")
    
    # Generate a unique token (random string)
    reset_token = secrets.token_urlsafe(32)
    
    # Set token expiry to 1 hour from now
    token_expiry = datetime.utcnow() + timedelta(hours=1)
    
    # Store token in database
    user.password_reset_token = reset_token
    user.password_reset_token_expiry = token_expiry
    
    db.commit()
    db.refresh(user)
    
    return user, reset_token


def verify_password_reset_token(db: Session, token: str):
    """Verify password reset token and return user if valid"""
    user = db.query(models.User).filter(
        models.User.password_reset_token == token
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")
    
    # Check if token has expired
    if not user.password_reset_token_expiry or user.password_reset_token_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    return user


def reset_password(db: Session, token: str, new_password: str):
    """Reset user password using valid token"""
    user = verify_password_reset_token(db, token)
    
    # Update password and clear reset token
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_token_expiry = None
    
    db.commit()
    db.refresh(user)
    
    return user


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

# =====================================================
# VALIDATION HELPERS
# =====================================================

def _validate_time_rules(start: datetime, end: datetime, is_edit: bool = False):
    # Convert to UTC and make naive for comparison
    if start.tzinfo is not None:
        # Convert to UTC and then remove timezone
        start = start.astimezone(timezone.utc).replace(tzinfo=None)
    if end.tzinfo is not None:
        end = end.astimezone(timezone.utc).replace(tzinfo=None)
    
    now = datetime.utcnow()

    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Only check for past events when creating new events, not when editing
    if not is_edit and start < now:
        raise HTTPException(status_code=400, detail="Cannot schedule events in the past")

    # 30-minute rule (check UTC times)
    if start.minute not in [0, 30] or end.minute not in [0, 30]:
        raise HTTPException(
            status_code=400,
            detail="Events must start and end at 30-minute intervals"
        )

    duration = (end - start).total_seconds() / 60
    if duration % 30 != 0:
        raise HTTPException(
            status_code=400,
            detail="Event duration must be in 30-minute intervals"
        )

def _is_holiday(db: Session, date: datetime):
    # Convert to naive date if it has timezone
    if date.tzinfo is not None:
        date = date.replace(tzinfo=None)
    
    return db.query(models.Event).filter(
        func.date(models.Event.start_time) == date.date(),
        models.Event.event_type.in_(["holiday", "weekly_off", "announced_holiday"]),
        models.Event.status == "active"
    ).first() is not None

def create_event(db: Session, event: schemas.EventCreate, owner_id: int):
    owner = db.query(models.User).filter(models.User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

     # Convert to naive datetime if they have timezone
    start = event.start_time.replace(tzinfo=None) if event.start_time.tzinfo else event.start_time
    end = event.end_time.replace(tzinfo=None) if event.end_time.tzinfo else event.end_time
    
    # Create a new event object with naive datetimes
    event_with_naive = schemas.EventCreate(
        title=event.title,
        start_time=start,
        end_time=end,
        event_type=event.event_type,
        participants=event.participants
    )

    # ✅ 1. Time validation (is_edit=False for new events)
    _validate_time_rules(event_with_naive.start_time, event_with_naive.end_time, is_edit=False)

    is_global_event = event.event_type in [
        "holiday",
        "weekly_off",
        "announced_holiday"
    ]

    is_combined = event.event_type == "combined"

    # ✅ 2. Holiday restriction
    if not is_global_event and not is_combined:
        if _is_holiday(db, event.start_time):
            raise HTTPException(
                status_code=400,
                detail="Cannot schedule regular events on holidays"
            )

    # ✅ 3. Only admin/super_admin can create global events
    if is_global_event and owner.role.name not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Only admin can create holidays or weekly off"
        )

    # ✅ 4. Conflict checks (ONLY if NOT combined AND NOT admin)
    if not is_combined and owner.role.name == "user":
        if _has_overlap(db, owner.id, event.start_time, event.end_time):
            raise HTTPException(
                status_code=400,
                detail="Conflict: You already have an event at this time",
            )

    db_event = models.Event(
        title=event.title,
        start_time=event.start_time,
        end_time=event.end_time,
        user_id=owner.id,
        event_type=event.event_type,
    )

    # ✅ 5. Participant conflict check
    if event.participants:
        participants = (
            db.query(models.User)
            .filter(models.User.id.in_(event.participants))
            .all()
        )

        if not is_combined:
            for p in participants:
                if p.role.name == "user":
                    if _has_overlap(db, p.id, event.start_time, event.end_time):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Conflict: {p.name} already has an event at this time",
                        )

        db_event.participants.extend(participants)

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

    # Convert to UTC naive datetime for validation
    start = event.start_time
    end = event.end_time
    
    if start.tzinfo is not None:
        start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        start_utc = start
        
    if end.tzinfo is not None:
        end_utc = end.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        end_utc = end

    # ✅ 1. Time validation (use UTC naive times, is_edit=True to allow editing past events)
    _validate_time_rules(start_utc, end_utc, is_edit=True)

    is_global_event = event.event_type in [
        "holiday",
        "weekly_off",
        "announced_holiday"
    ]

    is_combined = event.event_type == "combined"

    # ✅ 2. Holiday restriction (use UTC date)
    if not is_global_event and not is_combined:
        holiday_exists = db.query(models.Event).filter(
            models.Event.id != event_id,
            func.date(models.Event.start_time) == start_utc.date(),
            models.Event.event_type.in_(["holiday", "weekly_off", "announced_holiday"]),
            models.Event.status == "active"
        ).first()

        if holiday_exists:
            raise HTTPException(
                status_code=400,
                detail="Cannot schedule regular events on holidays"
            )

    # ---------- CONFLICT CHECK (EXCLUDE SELF) ----------
    def has_overlap_excluding_self(user_id: int):
        return db.query(models.Event).filter(
            models.Event.id != event_id,
            (
                (models.Event.user_id == user_id)
                | (models.Event.participants.any(models.User.id == user_id))
            ),
            models.Event.start_time < end,  # Store original timezone-aware times
            models.Event.end_time > start,
            models.Event.status == "active",
        ).first() is not None

    # Owner conflict
    current_user_role = current_user.role.name if current_user.role else "user"
    if not is_combined and current_user_role == "user":
        if has_overlap_excluding_self(current_user.id):
            raise HTTPException(
                status_code=400,
                detail="Conflict: You already have another event at this time",
            )

    participants = []
    if event.participants:
        participants = (
            db.query(models.User)
            .filter(models.User.id.in_(event.participants))
            .all()
        )

        if not is_combined:
            for p in participants:
                participant_role = p.role.name if p.role else "user"
                if participant_role == "user":
                    if has_overlap_excluding_self(p.id):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Conflict: {p.name} already has another event at this time",
                        )

    # ---------- UPDATE ----------
    db_event.title = event.title
    db_event.start_time = event.start_time  # Store original timezone-aware
    db_event.end_time = event.end_time      # Store original timezone-aware
    db_event.participants = participants
    db_event.event_type = event.event_type

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


def create_recurring_events(db: Session, event: schemas.EventCreate, owner_id: int):
    # If no recurrence, just create one
    if not event.recurrence_type:
        return create_event(db, event, owner_id)
        
    start_date = event.start_time
    # Ensure naive for calculation to avoid mixing tz-aware and naive
    if start_date.tzinfo:
        start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        
    # Recurrence end date
    recurrence_end = event.recurrence_end_date
    if not recurrence_end:
        # Default to 1 occurrence if missing
        recurrence_end = start_date
    elif recurrence_end.tzinfo:
        recurrence_end = recurrence_end.astimezone(timezone.utc).replace(tzinfo=None)
        
    # Cap recurrence to reasonable limit (e.g. 1 year) to prevent infinite loops
    if (recurrence_end - start_date).days > 365:
         recurrence_end = start_date + timedelta(days=365)

    created_events = []
    
    # Loop day by day
    current_date = start_date
    
    # Calculate duration
    if event.end_time.tzinfo:
        original_end = event.end_time.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        original_end = event.end_time
    
    # Ensure naive
    if original_end.tzinfo:
        original_end = original_end.astimezone(timezone.utc).replace(tzinfo=None)

    duration = original_end - start_date
    
    first_event = None

    while current_date <= recurrence_end:
        should_create = False
        
        # Check day of week (Monday=0, Sunday=6)
        day_index = current_date.weekday()
        day_name = calendar.day_name[day_index] # e.g. "Monday"

        if event.recurrence_type == "daily":
            should_create = True
        elif event.recurrence_type == "weekly":
            if not event.recurrence_days:
                 # If no days specified, repeat on same weekday as start
                 if day_index == start_date.weekday():
                     should_create = True
            elif day_name in event.recurrence_days:
                should_create = True
                
        if should_create:
            # Construct new times
            # preserve time of day (current_date has time of start_date if we increment by days=1)
            # Actually current_date starts as start_date (including time)
            # and we add timedelta(days=1), so time is preserved.
            
            new_start = current_date
            new_end = new_start + duration
            
            # Construct a new EventCreate object
            # Use model_dump or dict depending on pydantic version. Assuming v2 usage in schemas but v1 compat might be needed.
            # schemas.py imports BaseModel from pydantic.
            try:
                event_dict = event.model_dump()
            except AttributeError:
                event_dict = event.dict()

            event_dict.update({
                "start_time": new_start,
                "end_time": new_end,
                "recurrence_type": None, # clear to avoid recursion
                "recurrence_end_date": None,
                "recurrence_days": []
            })
            
            sub_event = schemas.EventCreate(**event_dict)
            
            try:
                ev = create_event(db, sub_event, owner_id)
                if not first_event:
                    first_event = ev
                created_events.append(ev)
            except HTTPException as e:
                # If conflict, we skip or fail. 
                # Let's fail noisy if conflict, so user knows.
                raise e 
        
        current_date += timedelta(days=1)
        
    if not created_events:
         return create_event(db, event, owner_id)
         
    return first_event
