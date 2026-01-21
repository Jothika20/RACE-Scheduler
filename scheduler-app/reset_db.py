# reset_db.py

from app.database import Base, engine
from app import models

# WARNING: This will drop all tables and recreate them. Only do this in development!
print("🔄 Dropping all tables...")
Base.metadata.drop_all(bind=engine)

print("✅ Creating all tables...")
Base.metadata.create_all(bind=engine)

print("✅ Database schema has been reset.")
