#!/usr/bin/env python3
"""
Migration: Update batch statuses for two-stage processing
- Updates existing batch statuses from old format to new format
- P (Processing) -> PROCESSING
- C (Completed) -> COMPLETED  
- F (Failed) -> FAILED
- New batches will default to PREPARED
"""

import psycopg2
import sys

# Database connection parameters
DB_HOST = "tablemini.local"
DB_NAME = "doc_eval"
DB_USER = "postgres"
DB_PASSWORD = "prodogs03"

def run_migration():
    """Execute the migration"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        print("🔄 Starting migration: Update batch statuses...")
        
        # Check current status distribution
        print("📊 Current batch status distribution:")
        cursor.execute("SELECT status, COUNT(*) FROM batches GROUP BY status ORDER BY status;")
        current_statuses = cursor.fetchall()
        for status, count in current_statuses:
            print(f"   {status}: {count} batches")
        
        # Update old statuses to new format
        print("\n🔄 Updating batch statuses...")
        
        # P -> PROCESSING
        cursor.execute("UPDATE batches SET status = 'PROCESSING' WHERE status = 'P';")
        p_updated = cursor.rowcount
        print(f"   Updated {p_updated} batches from 'P' to 'PROCESSING'")
        
        # C -> COMPLETED
        cursor.execute("UPDATE batches SET status = 'COMPLETED' WHERE status = 'C';")
        c_updated = cursor.rowcount
        print(f"   Updated {c_updated} batches from 'C' to 'COMPLETED'")
        
        # F -> FAILED
        cursor.execute("UPDATE batches SET status = 'FAILED' WHERE status = 'F';")
        f_updated = cursor.rowcount
        print(f"   Updated {f_updated} batches from 'F' to 'FAILED'")
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        print("\n🔍 Updated batch status distribution:")
        cursor.execute("SELECT status, COUNT(*) FROM batches GROUP BY status ORDER BY status;")
        updated_statuses = cursor.fetchall()
        for status, count in updated_statuses:
            print(f"   {status}: {count} batches")
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
