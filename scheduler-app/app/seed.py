from app.database import SessionLocal
from app import models

db = SessionLocal()

def seed_roles_permissions():
    permissions = [
        "invite_user",
        "update_permissions",
        "create_event",
    ]

    perm_objs = {}
    for key in permissions:
        perm = db.query(models.Permission).filter_by(key=key).first()
        if not perm:
            perm = models.Permission(key=key)
            db.add(perm)
        perm_objs[key] = perm

    db.commit()

    roles = {
        "super_admin": permissions,
        "admin": ["invite_user", "create_event"],
        "user": ["create_event"],
    }

    for role_name, perms in roles.items():
        role = db.query(models.Role).filter_by(name=role_name).first()
        if not role:
            role = models.Role(name=role_name)
            db.add(role)

        role.permissions = [perm_objs[p] for p in perms]

    db.commit()
    db.close()
    print("✅ Roles & permissions seeded")
