#!/usr/bin/env python3
"""
Debug script to test processing a single file
"""

import sys
import os
import tempfile

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_db_connection

def test_single_file_insert():
    """Test inserting a single document and doc record"""
    
    # Create a test file
    temp_dir = tempfile.mkdtemp(prefix="debug_")
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("Test content")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, create a test folder
        cursor.execute("""
            INSERT INTO folders (folder_name, folder_path, active, status)
            VALUES (%s, %s, 1, 'PREPROCESSING')
            RETURNING id
        """, ("Debug Folder", temp_dir))
        folder_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Created folder with ID: {folder_id}")
        
        # Try to insert a document
        print("🔄 Inserting document...")
        cursor.execute("""
            INSERT INTO documents (folder_id, filepath, filename, valid)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (folder_id, test_file, "test.txt", 'Y'))
        document_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Created document with ID: {document_id}")
        
        # Try to insert into docs table
        print("🔄 Inserting into docs table...")
        with open(test_file, 'rb') as f:
            content = f.read()
        
        import base64
        encoded_content = base64.b64encode(content).decode('utf-8')
        file_size = len(content)
        
        cursor.execute("""
            INSERT INTO docs (document_id, doc_type, content, file_size)
            VALUES (%s, %s, %s, %s)
        """, (document_id, 'txt', encoded_content.encode('utf-8'), file_size))
        conn.commit()
        print(f"✅ Created docs record")
        
        print("🎉 Single file test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_single_file_insert()
