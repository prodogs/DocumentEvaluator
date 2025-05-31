#!/usr/bin/env python3
"""
Add status column to folders table in PostgreSQL database
"""

import psycopg2
import sys

# PostgreSQL connection configuration
PG_CONFIG = {
    'host': 'studio.local',
    'database': 'doc_eval',
    'user': 'postgres',
    'password': 'prodogs03',
    'port': 5432
}

def add_status_column():
    """Add status column to folders table"""
    try:
        print("🔗 Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        # Check current table structure
        print("📋 Checking current folders table structure...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'folders' 
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        print("Current columns:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        # Check if status column already exists
        status_exists = any(col[0] == 'status' for col in columns)
        
        if status_exists:
            print("✅ Status column already exists!")
        else:
            print("➕ Adding status column...")
            cursor.execute("""
                ALTER TABLE folders 
                ADD COLUMN status TEXT DEFAULT 'NOT_PROCESSED' NOT NULL;
            """)
            print("✅ Status column added successfully!")
        
        # Check if created_at column exists (also needed for folder preprocessing)
        created_at_exists = any(col[0] == 'created_at' for col in columns)
        
        if not created_at_exists:
            print("➕ Adding created_at column...")
            cursor.execute("""
                ALTER TABLE folders 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            print("✅ Created_at column added successfully!")
        
        # Commit changes
        conn.commit()
        
        # Verify final structure
        print("\n📋 Final folders table structure:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'folders' 
            ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        # Show current folder data
        print("\n📁 Current folders in database:")
        cursor.execute("SELECT id, folder_name, folder_path, status, active FROM folders ORDER BY id;")
        folders = cursor.fetchall()
        
        if folders:
            for folder in folders:
                print(f"  ID: {folder[0]}, Name: {folder[1]}, Status: {folder[3]}, Active: {folder[4]}")
        else:
            print("  No folders found")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database migration completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    success = add_status_column()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
