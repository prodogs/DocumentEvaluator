#!/usr/bin/env python3
"""
Reset PostgreSQL Schema

Drops all existing tables and recreates the schema with the correct structure
"""

import psycopg2
import sys

# PostgreSQL connection parameters
PG_CONFIG = {
    'host': 'studio.local',
    'user': 'postgres',
    'password': 'prodogs03',
    'database': 'doc_eval',
    'port': 5432
}

def drop_all_tables():
    """Drop all existing tables"""
    print("🗑️  Dropping all existing tables...")

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        # Get list of all tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)

        tables = [row[0] for row in cursor.fetchall()]

        if tables:
            print(f"📋 Found tables to drop: {tables}")

            # Drop tables in reverse dependency order
            drop_order = ['llm_responses', 'documents', 'prompts', 'llm_configurations', 'batches', 'folders']

            for table in drop_order:
                if table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    print(f"   ✅ Dropped table: {table}")

            # Drop any remaining tables
            for table in tables:
                if table not in drop_order:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    print(f"   ✅ Dropped table: {table}")
        else:
            print("ℹ️  No tables found to drop")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ All tables dropped successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        return False

def create_fresh_schema():
    """Create fresh PostgreSQL schema"""
    print("📋 Creating fresh PostgreSQL schema...")

    schema_sql = """
    -- Folders table
    CREATE TABLE folders (
        id SERIAL PRIMARY KEY,
        folder_path TEXT UNIQUE NOT NULL,
        folder_name TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Batches table
    CREATE TABLE batches (
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
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        folder_id INTEGER REFERENCES folders(id),
        batch_id INTEGER REFERENCES batches(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        task_id TEXT
    );

    -- LLM Configurations table
    CREATE TABLE llm_configurations (
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

    -- Prompts table (with description column)
    CREATE TABLE prompts (
        id SERIAL PRIMARY KEY,
        prompt_text TEXT NOT NULL,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- LLM Responses table
    CREATE TABLE llm_responses (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id),
        prompt_id INTEGER REFERENCES prompts(id),
        llm_config_id INTEGER REFERENCES llm_configurations(id),
        llm_name TEXT,
        task_id TEXT,
        status TEXT DEFAULT 'N',
        started_processing_at TIMESTAMP,
        completed_processing_at TIMESTAMP,
        response_json TEXT,
        response_text TEXT,
        response_time_ms INTEGER,
        error_message TEXT,
        overall_score REAL, -- Suitability score (0-100) for LLM readiness
        -- Token metrics (for analyze_status response compatibility)
        input_tokens INTEGER, -- Number of input tokens sent to the LLM
        output_tokens INTEGER, -- Number of output tokens received from the LLM
        time_taken_seconds REAL, -- Time taken for the LLM call in seconds
        tokens_per_second REAL, -- Rate of tokens per second
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX idx_documents_filepath ON documents(filepath);
    CREATE INDEX idx_documents_folder_id ON documents(folder_id);
    CREATE INDEX idx_documents_batch_id ON documents(batch_id);
    CREATE INDEX idx_llm_responses_document_id ON llm_responses(document_id);
    CREATE INDEX idx_llm_responses_status ON llm_responses(status);
    CREATE INDEX idx_llm_responses_task_id ON llm_responses(task_id);
    CREATE INDEX idx_batches_status ON batches(status);
    CREATE INDEX idx_batches_batch_number ON batches(batch_number);
    """

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        cursor.execute(schema_sql)
        conn.commit()

        cursor.close()
        conn.close()

        print("✅ Fresh PostgreSQL schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create fresh schema: {e}")
        return False

def verify_schema():
    """Verify the schema was created correctly"""
    print("🔍 Verifying schema...")

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['batches', 'documents', 'folders', 'llm_configurations', 'llm_responses', 'prompts']

        print(f"📋 Created tables: {tables}")

        if set(tables) == set(expected_tables):
            print("✅ All expected tables created")
        else:
            missing = set(expected_tables) - set(tables)
            extra = set(tables) - set(expected_tables)
            if missing:
                print(f"❌ Missing tables: {missing}")
            if extra:
                print(f"⚠️  Extra tables: {extra}")

        # Check prompts table has description column
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'prompts' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)

        prompt_columns = [row[0] for row in cursor.fetchall()]
        print(f"📋 Prompts table columns: {prompt_columns}")

        if 'description' in prompt_columns:
            print("✅ Prompts table has description column")
        else:
            print("❌ Prompts table missing description column")
            return False

        cursor.close()
        conn.close()

        print("✅ Schema verification completed successfully")
        return True

    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 PostgreSQL Schema Reset\n")
    print(f"📍 Target: postgresql://postgres@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")

    # Drop all existing tables
    if not drop_all_tables():
        return False

    # Create fresh schema
    if not create_fresh_schema():
        return False

    # Verify schema
    if not verify_schema():
        return False

    print(f"\n🎉 PostgreSQL Schema Reset Completed Successfully!")
    print(f"   ✅ All old tables dropped")
    print(f"   ✅ Fresh schema created with correct structure")
    print(f"   ✅ Schema verified")
    print(f"\n💡 You can now run: python3 migrate_to_postgresql.py")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
