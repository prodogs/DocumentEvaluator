#!/usr/bin/env python3
"""
Create the snapshots table in the PostgreSQL database
"""

import sys
import os

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_engine
from models import Base, Snapshot
from sqlalchemy import text

def create_snapshots_table():
    """Create the snapshots table"""
    try:
        engine = get_engine()
        
        print("🔧 Creating snapshots table...")
        
        # Create the table using SQLAlchemy
        Base.metadata.create_all(engine, tables=[Snapshot.__table__])
        
        print("✅ Snapshots table created successfully!")
        
        # Verify the table was created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'snapshots' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            if columns:
                print("\n📋 Snapshots table structure:")
                for col in columns:
                    nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                    print(f"  {col[0]}: {col[1]} {nullable}")
            else:
                print("⚠️  Could not verify table structure")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating snapshots table: {e}")
        return False

def main():
    """Main function"""
    print("🗄️  DocumentEvaluator - Create Snapshots Table")
    print("=" * 50)
    
    success = create_snapshots_table()
    
    if success:
        print("\n🎉 Snapshots table is ready!")
        print("💡 You can now use the snapshot functionality in the maintenance tab.")
    else:
        print("\n❌ Failed to create snapshots table!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
