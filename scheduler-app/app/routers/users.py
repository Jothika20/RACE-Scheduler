from sqlalchemy.orm import Session, joinedload
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from app import crud, schemas, models, auth
from app.database import SessionLocal
from app.auth import get_current_user
from app.crud import generate_invite_token
from app.utils.email import send_invite_email
from app.config import SECRET_KEY, ALGORITHM
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app import models, schemas, utils, database, auth
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.utils.permissions import has_permission
import secrets

router = APIRouter(tags=["Users"])


def format_user_response(user: models.User):
    """
    Return a plain serializable dict matching schemas.UserOut:
      {
        id, name, email, role (string), permissions (dict[str,bool])
      }
    """
    role_name = user.role.name if user.role else "user"

    # Build a dict of all permissions this role has: { "can_x": True, ... }
    permissions = {perm.key: True for perm in user.role.permissions} if user.role else {}

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role_name,
        "permissions": permissions,
    }


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register_user(
    data: dict,
    db: Session = Depends(get_db)
):
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    token = data.get("token")

    # --- If registering through invite link ---
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            role_name = payload.get("role")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=400, detail="Invite link expired")
        except JWTError:
            raise HTTPException(status_code=400, detail="Invalid invite link")
    else:
        role_name = "user"  # Default for direct registration

    # --- Check if user already exists ---
    existing = db.query(models.User).filter(models.User.email == email).first()

    if existing:
        # If it's an invited user (no password yet), activate them
        if not existing.hashed_password:
            existing.name = name
            existing.hashed_password = auth.get_password_hash(password)
            # Set role relationship properly
            role_obj = db.query(models.Role).filter(models.Role.name == role_name).first()
            existing.role = role_obj
            db.commit()
            db.refresh(existing)
            return {"message": "Registration completed for invited user"}

        # Otherwise, prevent duplicate registration
        raise HTTPException(status_code=400, detail="Email already registered")

    # --- If not existing (normal registration) ---
    hashed_pw = auth.get_password_hash(password)

    # Find role object (important: assign relationship, not string)
    role_obj = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role_obj:
        # fallback to a "user" role if missing
        role_obj = db.query(models.Role).filter(models.Role.name == "user").first()

    new_user = models.User(name=name, email=email, hashed_password=hashed_pw, role=role_obj)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Registration successful"}


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.put("/{user_id}/permissions", response_model=schemas.UserOut)
def update_permissions(
    user_id: int,
    perm_update: schemas.UserPermissionUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not has_permission(current_user, "can_manage_users"):
        raise HTTPException(status_code=403, detail="You lack permission to manage users")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Change role by name -> assign Role object
    role_obj = db.query(models.Role).filter(models.Role.name == perm_update.role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Role '{perm_update.role}' not found")

    user.role = role_obj
    db.commit()
    db.refresh(user)

    return format_user_response(user)


@router.get("/", response_model=List[schemas.UserOut])
def get_other_users(db: Session = Depends(database.get_db)):
    # Eager load role -> permissions to avoid lazy-loading surprises
    users = db.query(models.User).options(
        joinedload(models.User.role).joinedload(models.Role.permissions)
    ).all()

    result = []
    for user in users:
        permissions_dict = {perm.key: True for perm in user.role.permissions} if user.role else {}
        result.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.name if user.role else None,
            "permissions": permissions_dict,
        })
    return result


@router.post("/invite-user", response_model=schemas.UserOut)
def invite_user(
    user_invite: schemas.UserInvite,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    # Only superadmin can invite
    if not current_user.role or current_user.role.name != "super_admin":
        raise HTTPException(status_code=403, detail="Not authorized to invite users")

    existing_user = db.query(models.User).filter(models.User.email == user_invite.email).first()

    # find role object once
    role_obj = db.query(models.Role).filter(models.Role.name == user_invite.role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Role '{user_invite.role}' not found")

    if existing_user:
        # If existing user exists but has no password (i.e., previously invited), we can re-invite:
        if not existing_user.hashed_password:
            # create a temporary password and set hashed_password
            temp_password = secrets.token_urlsafe(8)
            existing_user.hashed_password = auth.get_password_hash(temp_password)
            existing_user.role = role_obj
            db.commit()
            db.refresh(existing_user)

            # create token for this invited user
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token_data = {"sub": existing_user.email, "role": existing_user.role.name, "exp": expire}
            token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

            # print invite (or send email)
            print(f"Re-invite link: https://localhost:3000/register?token={token}")
            print(f"Temporary password: {temp_password} (remove printing in production)")

            return format_user_response(existing_user)

        # If user already fully exists, just update role (same as before)
        existing_user.role = role_obj
        db.commit()
        db.refresh(existing_user)
        return format_user_response(existing_user)

    # New user creation: assign role object (not string).
    # Create a temporary password and store its hash so NOT NULL constraint is satisfied.
    temp_password = secrets.token_urlsafe(8)
    hashed_temp = auth.get_password_hash(temp_password)

    new_user = models.User(
        email=user_invite.email,
        name=user_invite.email.split("@")[0],
        hashed_password=hashed_temp,  # important: store hash, not None
        role=role_obj,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Generate invitation token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": new_user.email, "role": new_user.role.name, "exp": expire}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # Send email logic (optional) - adjust send_invite_email signature if needed.
    # send_invite_email(new_user.email, token, temp_password)
    # For now print for convenience (remove in production)
    print(f"Invite link: https://localhost:3000/register?token={token}")
    print(f"Temporary password: {temp_password} (remove printing in production)")

    return format_user_response(new_user)


@router.post("/register-from-invite", response_model=schemas.UserOut)
def register_from_invite(
    data: dict,
    db: Session = Depends(get_db)
):
    token = data.get("token")
    password = data.get("password")
    name = data.get("name")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role_name = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    db_user = crud.get_user_by_email(db, email)
    if not db_user:
        raise HTTPException(status_code=404, detail="Invite not found or invalid")

    if db_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account already activated")

    # set fields and assign Role object
    db_user.name = name
    db_user.hashed_password = auth.get_password_hash(password)
    role_obj = db.query(models.Role).filter(models.Role.name == role_name).first()
    if role_obj:
        db_user.role = role_obj

    db.commit()
    db.refresh(db_user)
    return format_user_response(db_user)


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    # current_user should already be loaded with role+permissions by auth.get_current_user,
    # but to be safe ensure they are serializable via format_user_response
    return format_user_response(current_user)
