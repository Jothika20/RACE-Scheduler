from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from app import utils

# Association table for many-to-many relation between users and events
event_participants = Table(
    "event_participants",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("event_id", Integer, ForeignKey("events.id"))
)

# Association table between roles and permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="joined"
    )

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role_id = Column(Integer, ForeignKey("roles.id"))

    role = relationship("Role", backref="users", lazy="joined")

    # Events the user owns
    events = relationship("Event", back_populates="owner")

    # Events the user participates in
    participating_events = relationship(
        "Event",
        secondary="event_participants",
        back_populates="participants"
    )

    @property
    def permissions(self):
        """Return a dictionary of permissions for quick frontend access."""
        return {perm.key: True for perm in self.role.permissions}

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="events")

    # Many-to-many (participants)
    participants = relationship(
        "User",
        secondary=event_participants,
        back_populates="participating_events"
    )
