from app.database import engine
from app.models import Base

def init():
    print("Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    print("Database initialized successfully.")

if __name__ == "__main__":
    init()
