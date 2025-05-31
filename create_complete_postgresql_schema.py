#!/usr/bin/env python3
"""
Complete PostgreSQL Schema Creation Script

Creates the most up-to-date schema for the Document Evaluator system including:
- All core tables (folders, batches, documents, docs, llm_configurations, prompts, llm_responses)
- Archive tables (batch_archive)
- All recent columns and features
- Proper indexes and constraints
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
        
        # Get all table names
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        tables = cursor.fetchall()
        
        if tables:
            # Drop all tables with CASCADE to handle foreign keys
            for (table_name,) in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"   Dropped table: {table_name}")
        else:
            print("   No tables found to drop")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ All tables dropped successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        return False

def create_complete_schema():
    """Create the complete PostgreSQL schema"""
    print("📋 Creating complete PostgreSQL schema...")

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
        folder_ids JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        status TEXT DEFAULT 'P' NOT NULL,
        total_documents INTEGER DEFAULT 0,
        processed_documents INTEGER DEFAULT 0
    );

    -- Docs table for encoded document storage
    CREATE TABLE docs (
        id SERIAL PRIMARY KEY,
        content BYTEA NOT NULL,
        content_type TEXT,
        doc_type TEXT,
        file_size INTEGER,
        encoding TEXT NOT NULL DEFAULT 'base64',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Documents table
    CREATE TABLE documents (
        id SERIAL PRIMARY KEY,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        folder_id INTEGER REFERENCES folders(id),
        batch_id INTEGER REFERENCES batches(id),
        doc_id INTEGER REFERENCES docs(id),
        meta_data JSONB DEFAULT '{}',
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

    -- Prompts table
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
        overall_score REAL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        time_taken_seconds REAL,
        tokens_per_second REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Batch Archive table
    CREATE TABLE batch_archive (
        id SERIAL PRIMARY KEY,
        original_batch_id INTEGER NOT NULL,
        batch_number INTEGER NOT NULL,
        batch_name TEXT,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        archived_by TEXT,
        archive_reason TEXT DEFAULT 'Manual deletion',
        batch_data JSONB NOT NULL,
        documents_data JSONB NOT NULL,
        llm_responses_data JSONB NOT NULL,
        archive_metadata JSONB
    );

    -- LLM Providers table
    CREATE TABLE llm_providers (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        provider_type TEXT NOT NULL,
        default_base_url TEXT,
        supports_model_discovery BOOLEAN DEFAULT TRUE NOT NULL,
        auth_type TEXT DEFAULT 'api_key' NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Models table (standardized model definitions)
    CREATE TABLE models (
        id SERIAL PRIMARY KEY,
        common_name TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        notes TEXT,
        model_family TEXT,
        parameter_count TEXT,
        context_length INTEGER,
        capabilities TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Provider Models relationship table
    CREATE TABLE provider_models (
        id SERIAL PRIMARY KEY,
        provider_id INTEGER NOT NULL REFERENCES llm_providers(id) ON DELETE CASCADE,
        model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
        provider_model_name TEXT NOT NULL,
        is_active BOOLEAN DEFAULT FALSE,
        is_available BOOLEAN DEFAULT TRUE,
        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider_id, model_id)
    );

    -- Model Aliases table (for name normalization)
    CREATE TABLE model_aliases (
        id SERIAL PRIMARY KEY,
        model_id INTEGER NOT NULL REFERENCES models(id) ON DELETE CASCADE,
        alias_name TEXT NOT NULL,
        provider_pattern TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(alias_name, provider_pattern)
    );

    -- Connections table (specific connection instances)
    CREATE TABLE connections (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        provider_id INTEGER NOT NULL REFERENCES llm_providers(id),
        base_url TEXT,
        api_key TEXT,
        port_no INTEGER,
        connection_config JSONB,
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        connection_status TEXT DEFAULT 'unknown' NOT NULL,
        last_tested TIMESTAMP,
        last_test_result TEXT,
        supports_model_discovery BOOLEAN DEFAULT TRUE NOT NULL,
        available_models TEXT,
        last_model_sync TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- LLM Models table (legacy compatibility)
    CREATE TABLE llm_models (
        id SERIAL PRIMARY KEY,
        provider_id INTEGER REFERENCES llm_providers(id) ON DELETE CASCADE,
        model_name TEXT NOT NULL,
        model_id TEXT NOT NULL,
        is_active BOOLEAN DEFAULT FALSE NOT NULL,
        capabilities TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX idx_folders_folder_path ON folders(folder_path);
    CREATE INDEX idx_folders_active ON folders(active);

    CREATE INDEX idx_batches_status ON batches(status);
    CREATE INDEX idx_batches_batch_number ON batches(batch_number);
    CREATE INDEX idx_batches_created_at ON batches(created_at);

    CREATE INDEX idx_docs_content_type ON docs(content_type);
    CREATE INDEX idx_docs_doc_type ON docs(doc_type);

    CREATE INDEX idx_documents_filepath ON documents(filepath);
    CREATE INDEX idx_documents_folder_id ON documents(folder_id);
    CREATE INDEX idx_documents_batch_id ON documents(batch_id);
    CREATE INDEX idx_documents_doc_id ON documents(doc_id);
    CREATE INDEX idx_documents_task_id ON documents(task_id);

    CREATE INDEX idx_llm_configurations_active ON llm_configurations(active);
    CREATE INDEX idx_llm_configurations_provider_type ON llm_configurations(provider_type);

    CREATE INDEX idx_prompts_active ON prompts(active);

    CREATE INDEX idx_llm_responses_document_id ON llm_responses(document_id);
    CREATE INDEX idx_llm_responses_prompt_id ON llm_responses(prompt_id);
    CREATE INDEX idx_llm_responses_llm_config_id ON llm_responses(llm_config_id);
    CREATE INDEX idx_llm_responses_status ON llm_responses(status);
    CREATE INDEX idx_llm_responses_task_id ON llm_responses(task_id);
    CREATE INDEX idx_llm_responses_timestamp ON llm_responses(timestamp);

    CREATE INDEX idx_batch_archive_original_batch_id ON batch_archive(original_batch_id);
    CREATE INDEX idx_batch_archive_batch_number ON batch_archive(batch_number);
    CREATE INDEX idx_batch_archive_archived_at ON batch_archive(archived_at);

    -- Indexes for new provider/model architecture
    CREATE INDEX idx_llm_providers_provider_type ON llm_providers(provider_type);
    CREATE INDEX idx_llm_providers_name ON llm_providers(name);

    CREATE INDEX idx_models_common_name ON models(common_name);
    CREATE INDEX idx_models_model_family ON models(model_family);

    CREATE INDEX idx_provider_models_provider_id ON provider_models(provider_id);
    CREATE INDEX idx_provider_models_model_id ON provider_models(model_id);
    CREATE INDEX idx_provider_models_is_active ON provider_models(is_active);

    CREATE INDEX idx_model_aliases_model_id ON model_aliases(model_id);
    CREATE INDEX idx_model_aliases_alias_name ON model_aliases(alias_name);

    CREATE INDEX idx_connections_provider_id ON connections(provider_id);
    CREATE INDEX idx_connections_is_active ON connections(is_active);
    CREATE INDEX idx_connections_connection_status ON connections(connection_status);

    CREATE INDEX idx_llm_models_provider_id ON llm_models(provider_id);
    CREATE INDEX idx_llm_models_is_active ON llm_models(is_active);
    """

    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()

        cursor.execute(schema_sql)
        conn.commit()

        cursor.close()
        conn.close()

        print("✅ Complete PostgreSQL schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create schema: {e}")
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

        expected_tables = [
            'batch_archive', 'batches', 'docs', 'documents',
            'folders', 'llm_configurations', 'llm_responses', 'prompts',
            'llm_providers', 'models', 'provider_models', 'model_aliases',
            'connections', 'llm_models'
        ]

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

        # Check specific table structures
        for table in ['docs', 'batch_archive', 'llm_providers', 'connections', 'models']:
            cursor.execute(f"""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = '{table}' AND table_schema = 'public'
                ORDER BY ordinal_position;
            """)
            columns = [row[0] for row in cursor.fetchall()]
            print(f"📋 {table} columns: {columns}")

        cursor.close()
        conn.close()

        print("✅ Schema verification completed successfully")
        return True

    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Complete PostgreSQL Schema Creation\n")
    print(f"📍 Target: postgresql://postgres@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")

    # Drop all existing tables
    if not drop_all_tables():
        return False

    # Create complete schema
    if not create_complete_schema():
        return False

    # Verify schema
    if not verify_schema():
        return False

    print(f"\n🎉 Complete PostgreSQL Schema Created Successfully!")
    print(f"   ✅ All old tables dropped")
    print(f"   ✅ Complete schema created with all tables and features")
    print(f"   ✅ Schema verified")
    print(f"\n💡 The database is now ready with the most up-to-date schema!")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
