"""
Database configuration for PostgreSQL

Updated to use PostgreSQL server at tablemini.local
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection URL
DATABASE_URL = "postgresql://postgres:prodogs03@tablemini.local:5432/doc_eval"

# Create engine with PostgreSQL-specific settings
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def Session():
    """Create a new database session"""
    return SessionLocal()

def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)

def get_engine():
    """Get the database engine"""
    return engine
