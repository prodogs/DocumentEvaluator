#!/usr/bin/env python3
"""
Check the docs table schema
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_db_connection

def check_docs_schema():
    """Check the docs table schema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("📋 Docs table schema:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'docs'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        if columns:
            for row in columns:
                print(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        else:
            print("  No columns found - table may not exist")
        
        print()
        print("📋 Documents table schema:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        if columns:
            for row in columns:
                print(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        else:
            print("  No columns found - table may not exist")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_docs_schema()
