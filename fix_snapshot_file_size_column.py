#!/usr/bin/env python3
"""
Fix the file_size column in snapshots table to handle large files
"""

import sys
import os

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_engine
from sqlalchemy import text

def fix_file_size_column():
    """Change file_size column from INTEGER to BIGINT"""
    try:
        engine = get_engine()
        
        print("🔧 Fixing file_size column in snapshots table...")
        
        with engine.connect() as conn:
            # Check current column type
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'snapshots' AND column_name = 'file_size';
            """))
            
            current_type = result.fetchone()
            if current_type:
                print(f"📊 Current file_size column type: {current_type[0]}")
            
            # Change column type to BIGINT
            print("🔄 Changing file_size column to BIGINT...")
            conn.execute(text("""
                ALTER TABLE snapshots 
                ALTER COLUMN file_size TYPE BIGINT;
            """))
            
            conn.commit()
            
            # Verify the change
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'snapshots' AND column_name = 'file_size';
            """))
            
            new_type = result.fetchone()
            if new_type:
                print(f"✅ New file_size column type: {new_type[0]}")
            
        print("🎉 Successfully updated file_size column to BIGINT")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing file_size column: {e}")
        return False

def main():
    """Main function"""
    print("🔧 DocumentEvaluator - Fix Snapshots File Size Column")
    print("=" * 60)
    
    success = fix_file_size_column()
    
    if success:
        print("\n✅ Column fix completed!")
        print("💡 Now you can run populate_snapshots_for_ui_test.py again")
    else:
        print("\n❌ Failed to fix column!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
