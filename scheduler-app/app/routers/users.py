from sqlalchemy.orm import Session, joinedload
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from app import crud, schemas, models, auth
from app.database import SessionLocal
from app.auth import create_access_token
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
from app.authz import require_action

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
        "mobile": user.mobile,
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
    data: schemas.UserRegister,
    db: Session = Depends(get_db)
):
    name = data.name
    email = data.email
    mobile = data.mobile
    password = data.password
    token = data.token
    
    if email:
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

    if mobile:
        if db.query(models.User).filter(models.User.mobile == mobile).first():
            raise HTTPException(status_code=400, detail="Mobile already registered")


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
        
        # Invited user registration - get or create user
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            # Activate the invited user by setting their name and new password
            existing.name = name
            existing.hashed_password = auth.get_password_hash(password)
            role_obj = db.query(models.Role).filter(models.Role.name == role_name).first()
            if role_obj:
                existing.role = role_obj
            db.commit()
            db.refresh(existing)
            return format_user_response(existing)
        else:
            # Shouldn't happen, but create user if missing
            raise HTTPException(status_code=404, detail="Invite not found or invalid")
    else:
        # Direct registration (non-invited)
        role_name = "user"

    # --- If not existing (normal registration) ---
    hashed_pw = auth.get_password_hash(password)

    # Find role object (important: assign relationship, not string)
    role_obj = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role_obj:
        # fallback to a "user" role if missing
        role_obj = db.query(models.Role).filter(models.Role.name == "user").first()

    new_user = models.User(
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        hashed_password=hashed_pw,
        role=role_obj
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Registration successful"}


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.put(
    "/{user_id}/permissions",
    response_model=schemas.UserOut,
    dependencies=[Depends(require_action("update_permissions"))],
)
def update_permissions(
    user_id: int,
    perm_update: schemas.UserPermissionUpdate,
    db: Session = Depends(database.get_db),
):
    """
    Only SUPER ADMIN can update user roles.
    Admin is explicitly blocked by authz.
    """

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_obj = db.query(models.Role).filter(
        models.Role.name == perm_update.role
    ).first()

    if not role_obj:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{perm_update.role}' not found"
        )

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


@router.post(
    "/invite-user",
    response_model=schemas.UserOut,
    dependencies=[Depends(require_action("invite_user"))],
)
def invite_user(
    user_invite: schemas.UserInvite,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    - Super Admin: can invite any role
    - Admin: can invite ONLY 'user'
    """

    # ✅ Admin restriction
    if current_user.role.name == "admin" and user_invite.role != "user":
        raise HTTPException(status_code=403, detail="Admins can only invite normal users")

    # ✅ Validate role
    role_obj = db.query(models.Role).filter(models.Role.name == user_invite.role).first()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Role '{user_invite.role}' not found")

    existing_user = db.query(models.User).filter(models.User.email == user_invite.email).first()

    # ✅ If user already exists, just update role
    if existing_user:
        existing_user.role = role_obj
        db.commit()
        db.refresh(existing_user)

        # ✅ Generate invite token again (re-invite)
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"sub": existing_user.email, "role": existing_user.role.name, "exp": expire}
        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        # ✅ Send email properly (token only)
        send_invite_email(existing_user.email, token)

        return format_user_response(existing_user)

    # ✅ Create new invited user with temporary password
    temp_password = secrets.token_urlsafe(16)
    hashed_temp = auth.get_password_hash(temp_password)

    new_user = models.User(
        email=user_invite.email,
        name=user_invite.email.split("@")[0],
        hashed_password=hashed_temp,  # Temporary password
        role=role_obj,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ✅ Generate invite token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": new_user.email, "role": new_user.role.name, "exp": expire}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    # ✅ Send email properly (token only)
    send_invite_email(new_user.email, token)

    # Debugging prints (optional)
    print(f"✅ Invite sent to: {new_user.email}")
    print(f"🔗 Invite link: http://localhost:3000/register?token={token}")

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
