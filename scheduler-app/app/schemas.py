from pydantic import BaseModel, EmailStr, model_validator
from datetime import datetime
from typing import List, Optional, Dict

# ─────────────── Permission Schema ─────────────── #

class UserPermissions(BaseModel):
    can_create_users: bool = False
    can_create_events: bool = False

    class Config:
        from_attributes = True


# ─────────────── User Schemas ─────────────── #

class UserBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def validate_email_or_mobile(self):
        if not self.email and not self.mobile:
            raise ValueError("Either email or mobile must be provided")
        return self


class RoleOut(BaseModel):
    name: str
    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    name: str
    email: Optional[EmailStr]
    mobile: Optional[str]
    role: str
    permissions: dict

    class Config:
        from_attributes = True


# ─────────────── Token Schemas ─────────────── #

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None 


# ─────────────── Event Schemas ─────────────── #

class EventBase(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True


class EventCreate(EventBase):
    participants: Optional[List[int]] = []


class EventOut(EventBase):
    id: int
    user_id: int
    status: str
    cancellation_reason: Optional[str] = None
    participants: List[UserOut] = []

    class Config:
        from_attributes = True

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
        from_attributes = True

class UserRegister(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    password: str
    token: Optional[str] = None

    @model_validator(mode="after")
    def validate_email_or_mobile(self):
        email = getattr(self, "email", None)
        mobile = getattr(self, "mobile", None)

        if not email and not mobile:
            raise ValueError("Either email or mobile must be provided")

        return self
