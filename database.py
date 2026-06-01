from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database URL.
# The app.db file is created automatically in the project directory.
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# The "engine" manages the connection to the database.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
)

# The "session factory" creates sessions used to talk to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all our models (= tables).
Base = declarative_base()


# Utility dependency for FastAPI:
# opens a session, hands it to the endpoint, then closes it.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
