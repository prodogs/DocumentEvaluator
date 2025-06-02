#!/usr/bin/env python3

import psycopg2
import base64

def check_all_batch70_docs():
    # Connect to KnowledgeDocuments database
    conn = psycopg2.connect(
        host='studio.local',
        database='KnowledgeDocuments', 
        user='postgres',
        password='prodogs03',
        port=5432
    )
    cursor = conn.cursor()

    try:
        # Find all batch 70 documents
        cursor.execute("SELECT id, document_id, LENGTH(content) FROM docs WHERE document_id LIKE 'batch_70_%' ORDER BY document_id")
        results = cursor.fetchall()
        
        print(f"Found {len(results)} documents for batch 70:")
        
        invalid_docs = []
        
        for doc_id, document_id, content_length in results:
            print(f'\n🔍 Checking {document_id}:')
            print(f'   Length: {content_length}, mod 4: {content_length % 4}')
            
            # Get the actual content
            cursor.execute('SELECT content FROM docs WHERE id = %s', (doc_id,))
            content_raw = cursor.fetchone()[0]
            
            # Convert to string if needed
            if isinstance(content_raw, (bytes, memoryview)):
                content = content_raw.tobytes().decode('utf-8') if hasattr(content_raw, 'tobytes') else content_raw.decode('utf-8')
            else:
                content = str(content_raw)
            
            # Check if base64 is valid
            try:
                decoded = base64.b64decode(content)
                print(f'   ✅ Valid base64, decoded size: {len(decoded)} bytes')
            except Exception as e:
                print(f'   ❌ Invalid base64: {e}')
                invalid_docs.append((doc_id, document_id, content_length, len(content)))
                
                # Try to fix it
                content_fixed = content.strip()
                padding_needed = 4 - (len(content_fixed) % 4)
                if padding_needed != 4:
                    content_fixed += '=' * padding_needed
                    try:
                        decoded = base64.b64decode(content_fixed)
                        print(f'   🔧 Fixed with padding, updating database...')
                        cursor.execute('UPDATE docs SET content = %s WHERE id = %s', (content_fixed, doc_id))
                        conn.commit()
                        print(f'   ✅ Database updated')
                    except Exception as fix_error:
                        print(f'   ❌ Could not fix: {fix_error}')
        
        print(f'\n📊 Summary:')
        print(f'   Total docs: {len(results)}')
        print(f'   Invalid docs: {len(invalid_docs)}')
        
        if invalid_docs:
            print(f'\n❌ Invalid documents:')
            for doc_id, document_id, db_length, actual_length in invalid_docs:
                print(f'   {document_id}: DB length={db_length}, actual length={actual_length}')
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_all_batch70_docs()