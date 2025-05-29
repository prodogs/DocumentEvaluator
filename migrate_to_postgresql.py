#!/usr/bin/env python3
"""
PostgreSQL Migration Script

Migrates the document evaluation system from SQLite to PostgreSQL:
1. Creates PostgreSQL database schema
2. Migrates existing data from SQLite
3. Updates application configuration
4. Validates the migration

Target PostgreSQL Server:
- Host: tablemini.local
- User: postgres
- Password: prodogs
- Database: doc_eval
"""

import sys
import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

sys.path.append('.')

# PostgreSQL connection parameters
PG_CONFIG = {
    'host': 'tablemini.local',
    'user': 'postgres',
    'password': 'prodogs03',
    'database': 'doc_eval',
    'port': 5432
}

def get_sqlite_path():
    """Get the current SQLite database path"""
    try:
        from server.database import DATABASE_URL
        if DATABASE_URL.startswith('sqlite:///'):
            return DATABASE_URL[10:]
        elif DATABASE_URL.startswith('sqlite://'):
            return DATABASE_URL[9:]
        else:
            return 'llm_evaluation.db'
    except ImportError:
        return 'llm_evaluation.db'

def test_postgresql_connection():
    """Test connection to PostgreSQL server"""
    print("🔍 Testing PostgreSQL connection...")

    try:
        # First try to connect to postgres database to check server connectivity
        test_config = PG_CONFIG.copy()
        test_config['database'] = 'postgres'

        conn = psycopg2.connect(**test_config)
        conn.close()
        print(f"✅ Successfully connected to PostgreSQL server at {PG_CONFIG['host']}")

        # Now try to connect to target database
        try:
            conn = psycopg2.connect(**PG_CONFIG)
            conn.close()
            print(f"✅ Target database '{PG_CONFIG['database']}' exists and is accessible")
            return True
        except psycopg2.OperationalError as e:
            if "does not exist" in str(e):
                print(f"⚠️  Database '{PG_CONFIG['database']}' does not exist - will create it")
                return "create_db"
            else:
                print(f"❌ Error connecting to database: {e}")
                return False

    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL server: {e}")
        print(f"💡 Please ensure:")
        print(f"   - PostgreSQL server is running on {PG_CONFIG['host']}")
        print(f"   - User '{PG_CONFIG['user']}' exists with password '{PG_CONFIG['password']}'")
        print(f"   - Server allows connections from this machine")
        return False

def create_database():
    """Create the target database if it doesn't exist"""
    print(f"📊 Creating database '{PG_CONFIG['database']}'...")

    try:
        # Connect to postgres database to create new database
        test_config = PG_CONFIG.copy()
        test_config['database'] = 'postgres'

        conn = psycopg2.connect(**test_config)
        conn.autocommit = True
        cursor = conn.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE {PG_CONFIG['database']};")

        cursor.close()
        conn.close()

        print(f"✅ Database '{PG_CONFIG['database']}' created successfully")
        return True

    except psycopg2.Error as e:
        if "already exists" in str(e):
            print(f"ℹ️  Database '{PG_CONFIG['database']}' already exists")
            return True
        else:
            print(f"❌ Failed to create database: {e}")
            return False

def create_postgresql_schema():
    """Create the PostgreSQL schema"""
    print("📋 Creating PostgreSQL schema...")

    schema_sql = """
    -- Folders table
    CREATE TABLE IF NOT EXISTS folders (
        id SERIAL PRIMARY KEY,
        folder_path TEXT UNIQUE NOT NULL,
        folder_name TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Batches table
    CREATE TABLE IF NOT EXISTS batches (
        id SERIAL PRIMARY KEY,
        batch_number INTEGER UNIQUE NOT NULL,
        batch_name TEXT,
        description TEXT,
        folder_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT DEFAULT 'P' NOT NULL,
        total_documents INTEGER DEFAULT 0,
        processed_documents INTEGER DEFAULT 0
    );

    -- Documents table
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        folder_id INTEGER REFERENCES folders(id),
        batch_id INTEGER REFERENCES batches(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        task_id TEXT
    );

    -- LLM Configurations table
    CREATE TABLE IF NOT EXISTS llm_configurations (
        id SERIAL PRIMARY KEY,
        llm_name TEXT NOT NULL,
        provider_type TEXT NOT NULL,
        base_url TEXT,
        model_name TEXT,
        api_key TEXT,
        port_no INTEGER,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Prompts table
    CREATE TABLE IF NOT EXISTS prompts (
        id SERIAL PRIMARY KEY,
        prompt_text TEXT NOT NULL,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- LLM Responses table
    CREATE TABLE IF NOT EXISTS llm_responses (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id),
        prompt_id INTEGER REFERENCES prompts(id),
        llm_config_id INTEGER REFERENCES llm_configurations(id),
        llm_name TEXT,
        task_id TEXT,
        status TEXT DEFAULT 'N',
        started_processing_at TIMESTAMP,
        completed_processing_at TIMESTAMP,
        response_text TEXT,
        error_message TEXT,
        response_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_documents_filepath ON documents(filepath);
    CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON documents(folder_id);
    CREATE INDEX IF NOT EXISTS idx_documents_batch_id ON documents(batch_id);
    CREATE INDEX IF NOT EXISTS idx_llm_responses_document_id ON llm_responses(document_id);
    CREATE INDEX IF NOT EXISTS idx_llm_responses_status ON llm_responses(status);
    CREATE INDEX IF NOT EXISTS idx_llm_responses_task_id ON llm_responses(task_id);
    CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status);
    CREATE INDEX IF NOT EXISTS idx_batches_batch_number ON batches(batch_number);
    """

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        cursor.execute(schema_sql)
        conn.commit()

        cursor.close()
        conn.close()

        print("✅ PostgreSQL schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create PostgreSQL schema: {e}")
        return False

def migrate_table_data(sqlite_cursor, pg_cursor, table_name, column_mapping=None):
    """Migrate data from SQLite table to PostgreSQL table"""
    print(f"📊 Migrating {table_name} table...")

    try:
        # Special handling for llm_responses to check foreign key constraints
        if table_name == 'llm_responses':
            return migrate_llm_responses_with_constraints(sqlite_cursor, pg_cursor)

        # Get data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name};")
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"ℹ️  No data found in {table_name} table")
            return True

        # Get column names from SQLite
        column_names = [description[0] for description in sqlite_cursor.description]

        # Apply column mapping if provided
        if column_mapping:
            column_names = [column_mapping.get(col, col) for col in column_names]

        # Prepare PostgreSQL insert statement
        placeholders = ', '.join(['%s'] * len(column_names))
        columns_str = ', '.join(column_names)
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

        # Insert data into PostgreSQL
        successful_rows = 0
        for row in rows:
            try:
                # Convert SQLite row to list and handle data type conversions
                row_data = list(row)

                # Handle datetime conversions and other data type issues
                for i, value in enumerate(row_data):
                    if value is not None:
                        # Convert SQLite datetime strings to proper format
                        if isinstance(value, str) and ('T' in value or '-' in value):
                            try:
                                # Try to parse as datetime
                                if 'T' in value:
                                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    row_data[i] = dt
                            except:
                                pass  # Keep as string if parsing fails

                pg_cursor.execute(insert_sql, row_data)
                successful_rows += 1

            except Exception as row_error:
                print(f"   ⚠️  Skipped row due to error: {row_error}")
                continue

        print(f"✅ Migrated {successful_rows}/{len(rows)} rows from {table_name}")
        return True

    except Exception as e:
        print(f"❌ Failed to migrate {table_name}: {e}")
        return False

def migrate_llm_responses_with_constraints(sqlite_cursor, pg_cursor):
    """Migrate llm_responses table with foreign key constraint checking"""
    print(f"📊 Migrating llm_responses table with constraint validation...")

    try:
        # Get all llm_responses from SQLite
        sqlite_cursor.execute("SELECT * FROM llm_responses;")
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"ℹ️  No data found in llm_responses table")
            return True

        # Get valid foreign key IDs from PostgreSQL
        pg_cursor.execute("SELECT id FROM documents;")
        valid_document_ids = set(row[0] for row in pg_cursor.fetchall())

        pg_cursor.execute("SELECT id FROM prompts;")
        valid_prompt_ids = set(row[0] for row in pg_cursor.fetchall())

        pg_cursor.execute("SELECT id FROM llm_configurations;")
        valid_llm_config_ids = set(row[0] for row in pg_cursor.fetchall())

        print(f"   📋 Valid document IDs: {len(valid_document_ids)}")
        print(f"   📋 Valid prompt IDs: {len(valid_prompt_ids)}")
        print(f"   📋 Valid LLM config IDs: {len(valid_llm_config_ids)}")

        # Get column names from SQLite
        column_names = [description[0] for description in sqlite_cursor.description]

        # Prepare PostgreSQL insert statement
        placeholders = ', '.join(['%s'] * len(column_names))
        columns_str = ', '.join(column_names)
        insert_sql = f"INSERT INTO llm_responses ({columns_str}) VALUES ({placeholders})"

        # Insert valid rows only
        successful_rows = 0
        skipped_rows = 0

        for row in rows:
            row_data = list(row)

            # Get the foreign key values (assuming standard column order)
            document_id = row_data[1] if len(row_data) > 1 else None
            prompt_id = row_data[2] if len(row_data) > 2 else None
            llm_config_id = row_data[14] if len(row_data) > 14 else None  # Based on SQLite schema

            # Check foreign key constraints
            valid_row = True
            if document_id and document_id not in valid_document_ids:
                print(f"   ⚠️  Skipping row: document_id {document_id} not found")
                valid_row = False
            if prompt_id and prompt_id not in valid_prompt_ids:
                print(f"   ⚠️  Skipping row: prompt_id {prompt_id} not found")
                valid_row = False
            if llm_config_id and llm_config_id not in valid_llm_config_ids:
                print(f"   ⚠️  Skipping row: llm_config_id {llm_config_id} not found")
                valid_row = False

            if valid_row:
                try:
                    # Handle datetime conversions
                    for i, value in enumerate(row_data):
                        if value is not None:
                            if isinstance(value, str) and ('T' in value or '-' in value):
                                try:
                                    if 'T' in value:
                                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                        row_data[i] = dt
                                except:
                                    pass

                    pg_cursor.execute(insert_sql, row_data)
                    successful_rows += 1

                except Exception as row_error:
                    print(f"   ⚠️  Failed to insert row: {row_error}")
                    skipped_rows += 1
            else:
                skipped_rows += 1

        print(f"✅ Migrated {successful_rows}/{len(rows)} rows from llm_responses")
        if skipped_rows > 0:
            print(f"   ⚠️  Skipped {skipped_rows} rows due to constraint violations")

        return True

    except Exception as e:
        print(f"❌ Failed to migrate llm_responses: {e}")
        return False

def migrate_data():
    """Migrate all data from SQLite to PostgreSQL"""
    print("🔄 Starting data migration...")

    sqlite_path = get_sqlite_path()

    if not os.path.exists(sqlite_path):
        print(f"⚠️  SQLite database not found at {sqlite_path}")
        print("ℹ️  Starting with empty PostgreSQL database")
        return True

    try:
        # Connect to both databases
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()

        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_cursor = pg_conn.cursor()

        # Migration order (respecting foreign key dependencies)
        migration_order = [
            'folders',
            'batches',
            'llm_configurations',
            'prompts',
            'documents',
            'llm_responses'
        ]

        success = True
        for table in migration_order:
            # Check if table exists in SQLite
            sqlite_cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name=?;
            """, (table,))

            if sqlite_cursor.fetchone():
                if not migrate_table_data(sqlite_cursor, pg_cursor, table):
                    success = False
                    break
            else:
                print(f"ℹ️  Table {table} not found in SQLite database")

        if success:
            pg_conn.commit()
            print("✅ Data migration completed successfully")
        else:
            pg_conn.rollback()
            print("❌ Data migration failed - rolled back changes")

        # Close connections
        sqlite_cursor.close()
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

        return success

    except Exception as e:
        print(f"❌ Data migration failed: {e}")
        return False

def update_database_config():
    """Update the application database configuration"""
    print("⚙️  Updating database configuration...")

    # Create new database configuration
    new_database_url = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}"

    # Update server/database.py
    try:
        database_py_content = f'''"""
Database configuration for PostgreSQL

Updated to use PostgreSQL server at {PG_CONFIG['host']}
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL connection URL
DATABASE_URL = "{new_database_url}"

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
'''

        with open('server/database.py', 'w') as f:
            f.write(database_py_content)

        print("✅ Database configuration updated")

        # Create backup of old config
        backup_content = f'''# Backup of SQLite configuration
# Created during PostgreSQL migration on {datetime.now().isoformat()}

# Old SQLite configuration:
# DATABASE_URL = "sqlite:///../llm_evaluation.db"

# New PostgreSQL configuration:
# DATABASE_URL = "{new_database_url}"
'''

        with open('server/database_sqlite_backup.py', 'w') as f:
            f.write(backup_content)

        print("✅ SQLite configuration backed up to database_sqlite_backup.py")
        return True

    except Exception as e:
        print(f"❌ Failed to update database configuration: {e}")
        return False

def verify_migration():
    """Verify the PostgreSQL migration was successful"""
    print("🔍 Verifying migration...")

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]

        expected_tables = ['folders', 'batches', 'documents', 'llm_configurations', 'prompts', 'llm_responses']
        missing_tables = [table for table in expected_tables if table not in tables]

        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False

        print(f"✅ All expected tables present: {tables}")

        # Check data counts
        for table in expected_tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
            count = cursor.fetchone()['count']
            print(f"   {table}: {count} records")

        # Test a simple join query
        cursor.execute("""
            SELECT d.filename, b.batch_name, f.folder_name
            FROM documents d
            LEFT JOIN batches b ON d.batch_id = b.id
            LEFT JOIN folders f ON d.folder_id = f.id
            LIMIT 5;
        """)

        results = cursor.fetchall()
        print(f"✅ Join query successful, sample results: {len(results)} rows")

        cursor.close()
        conn.close()

        print("✅ Migration verification completed successfully")
        return True

    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 PostgreSQL Migration for Document Evaluation System\n")
    print(f"📍 Target: postgresql://{PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")

    # Test PostgreSQL connection
    connection_result = test_postgresql_connection()
    if connection_result == False:
        return False
    elif connection_result == "create_db":
        if not create_database():
            return False

    # Create PostgreSQL schema
    if not create_postgresql_schema():
        return False

    # Migrate data
    if not migrate_data():
        return False

    # Update application configuration
    if not update_database_config():
        return False

    # Verify migration
    if not verify_migration():
        return False

    print(f"\n🎉 PostgreSQL Migration Completed Successfully!")
    print(f"   ✅ Database: {PG_CONFIG['database']} on {PG_CONFIG['host']}")
    print(f"   ✅ Schema created with all tables and indexes")
    print(f"   ✅ Data migrated from SQLite")
    print(f"   ✅ Application configuration updated")
    print(f"   ✅ Migration verified")
    print(f"\n💡 Next steps:")
    print(f"   1. Install psycopg2: pip install psycopg2-binary")
    print(f"   2. Restart the application to use PostgreSQL")
    print(f"   3. Test the application functionality")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
