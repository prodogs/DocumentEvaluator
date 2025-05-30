#!/usr/bin/env python3
"""
Database migration to add overall_score column to llm_responses table
"""

import sys
import os

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session, engine
from sqlalchemy import text

def add_overall_score_column():
    """Add overall_score column to llm_responses table"""
    print("🔄 Adding overall_score column to llm_responses table...")

    session = Session()

    try:
        # Check if column already exists (PostgreSQL)
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_name = 'llm_responses'
            AND column_name = 'overall_score'
        """))

        column_exists = result.fetchone()[0] > 0

        if column_exists:
            print("✅ overall_score column already exists")
            return True

        # Add the column
        session.execute(text("""
            ALTER TABLE llm_responses
            ADD COLUMN overall_score REAL
        """))

        session.commit()
        print("✅ Successfully added overall_score column")

        # Verify the column was added (PostgreSQL)
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_name = 'llm_responses'
            AND column_name = 'overall_score'
        """))

        if result.fetchone()[0] > 0:
            print("✅ Column addition verified")
            return True
        else:
            print("❌ Column addition verification failed")
            return False

    except Exception as e:
        print(f"❌ Error adding column: {e}")
        session.rollback()
        return False

    finally:
        session.close()

def show_table_schema():
    """Show the current schema of llm_responses table"""
    print("\n📋 Current llm_responses table schema:")

    session = Session()

    try:
        result = session.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'llm_responses'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()

        for column in columns:
            name, data_type, is_nullable, column_default = column
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            default_info = f" DEFAULT {column_default}" if column_default is not None else ""
            print(f"   {name}: {data_type} {nullable}{default_info}")

    except Exception as e:
        print(f"❌ Error showing schema: {e}")

    finally:
        session.close()

if __name__ == "__main__":
    print("🗄️  LLM Responses Table Migration")
    print("=" * 50)

    # Show current schema
    show_table_schema()

    # Add the column
    success = add_overall_score_column()

    if success:
        # Show updated schema
        show_table_schema()
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
