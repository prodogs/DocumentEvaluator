#!/usr/bin/env python
# Database initialization script

import os
import sys
import sqlite3

def create_schema(db_path):
    """Create database schema if tables don't exist"""
    # Check if database file exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")

    print(f"Initializing database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read schema from schema.sql file
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Schema file not found: {schema_path}")
        return False

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Execute schema creation
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("Database schema created successfully")

        # Read and execute data from data.sql file
        data_path = os.path.join(os.path.dirname(__file__), 'data.sql')
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                data_sql = f.read()
            try:
                cursor.executescript(data_sql)
                conn.commit()
                print("Sample data inserted successfully from data.sql")
            except sqlite3.Error as e:
                print(f"Error inserting sample data: {e}")
        else:
            print(f"Data file not found: {data_path}, skipping sample data insertion.")

        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Tables in database: {', '.join([t[0] for t in tables])}")

        return True
    except sqlite3.Error as e:
        print(f"Error creating schema: {e}")
        return False
    finally:
        conn.close()

def main():
    # Default database path
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'llm_evaluation.db'))

    # Allow overriding the database path from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]

    success = create_schema(db_path)
    if success:
        print(f"Database initialized successfully at: {db_path}")
        return 0
    else:
        print("Failed to initialize database")
        return 1

if __name__ == "__main__":
    sys.exit(main())
