import os
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, JSON, TIMESTAMP, text
)
from databases import Database

# --- Configuration ---
# Read the database URL from an environment variable.
# For production, ALWAYS set the DATABASE_URL environment variable.
# Example for PostgreSQL: "postgresql://user:password@host:port/dbname"
DATABASE_URL = os.environ.get("DATABASE_URL")

# Handle Railway's postgres:// URL format (SQLAlchemy 2.0+ requires postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fallback to PostgreSQL localhost for development if no DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/assignments"
    print("⚠️ Using default PostgreSQL localhost. Set DATABASE_URL for production.")
else:
    print(f"✅ Using PostgreSQL database")

# SQLAlchemy specific objects
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()

# Define the 'question_assignments' table
question_assignments = Table(
    'question_assignments',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', String(255), nullable=True),  # Will be populated later when we have user system
    Column('question', String, nullable=False),
    Column('marks', Integer, nullable=False),
    Column('topic', JSON, nullable=False),
    Column('evaluation_rubrics', JSON, nullable=False),
    Column('created_at', TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
)

# The 'databases' library allows for async connections
database = Database(DATABASE_URL)
