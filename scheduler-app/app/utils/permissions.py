# app/utils/permissions.py
from app.models import User

def has_permission(user: User, permission_key: str) -> bool:
    """
    Check if the given user has a specific permission.
    """
    if not user or not user.role or not user.role.permissions:
        return False
    return any(p.key == permission_key for p in user.role.permissions)
