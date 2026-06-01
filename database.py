import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL. Defaults to a local SQLite file (app.db is created
# automatically); can be overridden via the DATABASE_URL env variable
# (e.g. a mounted volume in Docker, or PostgreSQL in production).
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# check_same_thread is a SQLite-only connection argument.
connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)

# The "engine" manages the connection to the database.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

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
