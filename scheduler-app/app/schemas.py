from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional, Dict

# ─────────────── Permission Schema ─────────────── #

class UserPermissions(BaseModel):
    can_create_users: bool = False
    can_create_events: bool = False

    class Config:
        orm_mode = True


# ─────────────── User Schemas ─────────────── #

class UserBase(BaseModel):
    email: EmailStr
    name: str

    class Config:
        orm_mode = True


class UserCreate(UserBase):
    password: str
    role: str = "user"
    can_create_events: Optional[bool] = False
    can_create_users: Optional[bool] = False


class RoleOut(BaseModel):
    name: str
    class Config:
        orm_mode = True


class UserOut(UserBase):
    id: int
    role: Optional[str] = None
    permissions: Dict[str, bool] = {}

    class Config:
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        # Convert nested Role object to string safely
        role_name = obj.role.name if hasattr(obj.role, "name") else obj.role
        return cls(
            id=obj.id,
            email=obj.email,
            name=obj.name,
            role=role_name,
            permissions=obj.permissions if hasattr(obj, "permissions") else {}
        )


# ─────────────── Token Schemas ─────────────── #

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ─────────────── Event Schemas ─────────────── #

class EventBase(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime

    class Config:
        orm_mode = True


class EventCreate(EventBase):
    participants: Optional[List[int]] = []


class EventOut(EventBase):
    id: int
    user_id: int
    status: str
    cancellation_reason: Optional[str] = None
    participants: List[UserOut] = []

    class Config:
        orm_mode = True

    @classmethod
    def from_orm(cls, obj):
        participants = []
        for p in getattr(obj, "participants", []):
            participants.append(UserOut.from_orm(p))

        return cls(
            id=obj.id,
            title=obj.title,
            start_time=obj.start_time,
            end_time=obj.end_time,
            user_id=obj.user_id,
            status=obj.status,
            cancellation_reason=obj.cancellation_reason,
            participants=participants
        )


# ─────────────── Update Permission Schema ─────────────── #

class UserPermissionUpdate(BaseModel):
    role: str
    can_create_users: bool
    can_create_events: bool


# ─────────────── Invite User Schema ─────────────── #

class UserInvite(BaseModel):
    email: EmailStr
    role: str
    can_create_events: Optional[bool] = False
    can_create_users: Optional[bool] = False

    class Config:
        orm_mode = True
