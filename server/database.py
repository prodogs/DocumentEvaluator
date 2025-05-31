"""
Database configuration with PostgreSQL primary and SQLite fallback

Updated to use PostgreSQL server at tablemini.local with SQLite fallback
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
import os
import logging

logger = logging.getLogger(__name__)

# PostgreSQL connection URL
POSTGRESQL_URL = "postgresql://postgres:prodogs03@studio.local:5432/doc_eval"

# SQLite fallback URL (relative to project root)
SQLITE_URL = "sqlite:///llm_evaluation.db"

def create_database_engine():
    """Create database engine with PostgreSQL only - no fallback"""
    try:
        logger.info("Attempting to connect to PostgreSQL database...")
        engine = create_engine(
            POSTGRESQL_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False  # Set to True for SQL debugging
        )

        # Test the connection with proper SQLAlchemy syntax
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Successfully connected to PostgreSQL database")
        return engine

    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        logger.error("No fallback database configured - PostgreSQL connection is required")
        raise Exception(f"Failed to connect to PostgreSQL database: {e}")

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
        return psycopg2.connect(
            host="studio.local",
            database="doc_eval",
            user="postgres",
            password="prodogs03",
            port=5432
        )
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise Exception(f"Failed to get PostgreSQL connection: {e}")
