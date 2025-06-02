"""
Database Configuration and Session Management

Provides database initialization, session management, and connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.engine = None
        self.session_factory = None
        self.Session = None
        
    def init_engine(self):
        """Initialize the database engine with proper pooling"""
        # Determine pool class based on environment
        if self.config.TESTING:
            # Use NullPool for testing (no connection pooling)
            pool_class = NullPool
        else:
            # Use QueuePool for production/development
            pool_class = QueuePool
        
        # Create engine with configuration
        engine_options = {
            'poolclass': pool_class,
            'echo': getattr(self.config, 'SQLALCHEMY_ECHO', False),
            'future': True,  # Use SQLAlchemy 2.0 style
        }
        
        # Add pool options if using QueuePool
        if pool_class == QueuePool:
            engine_options.update(self.config.SQLALCHEMY_ENGINE_OPTIONS)
        
        self.engine = create_engine(
            self.config.SQLALCHEMY_DATABASE_URI,
            **engine_options
        )
        
        # Set up event listeners
        self._setup_listeners()
        
        return self.engine
    
    def init_session_factory(self):
        """Initialize the session factory"""
        if not self.engine:
            self.init_engine()
        
        # Create session factory
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            future=True  # Use SQLAlchemy 2.0 style
        )
        
        # Create scoped session for thread safety
        self.Session = scoped_session(self.session_factory)
        
        return self.Session
    
    def _setup_listeners(self):
        """Set up SQLAlchemy event listeners"""
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Enable foreign keys for SQLite"""
            if 'sqlite' in self.config.SQLALCHEMY_DATABASE_URI:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(self.engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries in development"""
            if self.config.DEBUG:
                conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time"""
            if self.config.DEBUG:
                total = time.time() - conn.info['query_start_time'].pop(-1)
                if total > 0.5:  # Log queries taking more than 500ms
                    logger.warning(f"Slow query ({total:.2f}s): {statement[:100]}...")
    
    @contextmanager
    def session_scope(self) -> Generator:
        """Provide a transactional scope for database operations"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self):
        """Get a new database session"""
        if not self.Session:
            self.init_session_factory()
        return self.Session()
    
    def close_all_sessions(self):
        """Close all sessions"""
        if self.Session:
            self.Session.remove()
    
    def dispose_engine(self):
        """Dispose of the engine and close all connections"""
        if self.engine:
            self.engine.dispose()
    
    def health_check(self) -> bool:
        """Check if database is accessible"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Convenience functions
def get_db():
    """Get a database session (for use in routes)"""
    return db_manager.get_session()


@contextmanager
def transaction():
    """Context manager for database transactions"""
    with db_manager.session_scope() as session:
        yield session


def init_db(app=None):
    """Initialize database with Flask app"""
    if app:
        # Initialize with app config
        config = get_config(app.config.get('ENV'))
        global db_manager
        db_manager = DatabaseManager(config)
    
    # Initialize engine and session
    db_manager.init_engine()
    db_manager.init_session_factory()
    
    # Import models to ensure they're registered
    from models import Base
    
    # Create tables if they don't exist (development only)
    if db_manager.config.DEBUG:
        Base.metadata.create_all(bind=db_manager.engine)
    
    return db_manager


def close_db(error=None):
    """Close database sessions (for Flask teardown)"""
    db_manager.close_all_sessions()


# Performance monitoring utilities
import time
from functools import wraps


def monitor_query_performance(func):
    """Decorator to monitor database query performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # Log operations taking more than 1 second
                logger.warning(
                    f"Slow database operation '{func.__name__}' took {execution_time:.2f}s"
                )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Database operation '{func.__name__}' failed after {execution_time:.2f}s: {e}"
            )
            raise
    return wrapper


# Connection pool monitoring
def get_pool_status():
    """Get current connection pool status"""
    if not db_manager.engine or not hasattr(db_manager.engine.pool, 'status'):
        return {}
    
    pool = db_manager.engine.pool
    return {
        'size': pool.size(),
        'checked_in': pool.checkedin(),
        'overflow': pool.overflow(),
        'total': pool.size() + pool.overflow()
    }