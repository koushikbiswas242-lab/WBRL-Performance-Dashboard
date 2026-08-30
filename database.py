import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# =========================================================
# DATABASE URL
# =========================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./wbrl_dashboard.db"
)


# =========================================================
# DATABASE CONNECTION SETTINGS
# =========================================================

# SQLite-এর জন্য এই setting দরকার
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False
    }


# =========================================================
# CREATE DATABASE ENGINE
# =========================================================

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True
)


# =========================================================
# DATABASE SESSION
# =========================================================

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# =========================================================
# BASE MODEL
# =========================================================

Base = declarative_base()


# =========================================================
# DATABASE DEPENDENCY
# =========================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
