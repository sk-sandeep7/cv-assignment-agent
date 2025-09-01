import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from Railway environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle Railway's postgres:// URL format (SQLAlchemy 2.0+ requires postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite for local development if no DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./assignments.db"
    print("⚠️ Using SQLite for local development. Set DATABASE_URL for PostgreSQL.")
else:
    print(f"✅ Using PostgreSQL database")

# Create engine with proper configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
