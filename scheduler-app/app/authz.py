from fastapi import Depends, HTTPException, status
from app.auth import get_current_user
from app import models

def require_action(action: str):
    def checker(current_user: models.User = Depends(get_current_user)):
        role = current_user.role.name if current_user.role else None

        # Super admin bypass
        if role == "super_admin":
            return current_user

        if action == "invite_user":
            if role == "admin":
                return current_user

        if action == "update_permissions":
            raise HTTPException(
                status_code=403,
                detail="Admins cannot update permissions"
            )

        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )
    return checker
