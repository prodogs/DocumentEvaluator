"""
Database configuration with PostgreSQL primary and SQLite fallback

Updated to use PostgreSQL server at tablemini.local with SQLite fallback
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
import os
import logging

logger = logging.getLogger(__name__)

# PostgreSQL connection URL
POSTGRESQL_URL = "postgresql://postgres:prodogs03@tablemini.local:5432/doc_eval"

# SQLite fallback URL (relative to project root)
SQLITE_URL = "sqlite:///llm_evaluation.db"

def create_database_engine():
    """Create database engine - using SQLite due to PostgreSQL I/O error"""
    # Temporarily force SQLite usage due to PostgreSQL I/O error
    logger.info("Using SQLite database (PostgreSQL temporarily disabled)...")

    engine = create_engine(
        SQLITE_URL,
        echo=False  # Set to True for SQL debugging
    )

    logger.info("Successfully connected to SQLite database")
    return engine

# Create engine with fallback logic
engine = create_database_engine()

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

def get_db_connection():
    """Get a raw database connection for direct SQL operations"""
    try:
        # Try PostgreSQL first
        return psycopg2.connect(
            host="tablemini.local",
            database="doc_eval",
            user="postgres",
            password="prodogs03",
            port=5432
        )
    except Exception as e:
        logger.warning(f"PostgreSQL connection failed: {e}")
        logger.info("Using SQLite database - raw connections not supported")
        # For SQLite, we'll use the engine instead
        return None
