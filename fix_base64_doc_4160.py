#!/usr/bin/env python3

import psycopg2
import base64

def fix_base64_document():
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
        # Find the problematic document
        cursor.execute("SELECT id, document_id, LENGTH(content) FROM docs WHERE document_id LIKE 'batch_70_doc_4160'")
        result = cursor.fetchone()
        
        if result:
            doc_id, document_id, content_length = result
            print(f'Found document: {document_id}, length: {content_length}')
            print(f'Length mod 4: {content_length % 4}')
            
            # Get the content and check it
            cursor.execute('SELECT content FROM docs WHERE id = %s', (doc_id,))
            content_raw = cursor.fetchone()[0]
            
            # Convert memoryview/bytes to string if needed
            if isinstance(content_raw, (bytes, memoryview)):
                content = content_raw.tobytes().decode('utf-8') if hasattr(content_raw, 'tobytes') else content_raw.decode('utf-8')
            else:
                content = str(content_raw)
            
            print(f'Actual content length: {len(content)}')
            print(f'Content mod 4: {len(content) % 4}')
            print(f'Last 10 chars: {repr(content[-10:])}')
            
            # Try to fix the base64 padding
            content_fixed = content.strip()
            padding_needed = 4 - (len(content_fixed) % 4)
            if padding_needed != 4:
                content_fixed += '=' * padding_needed
                print(f'Fixed length: {len(content_fixed)}, mod 4: {len(content_fixed) % 4}')
                
                # Test if it's valid base64 now
                try:
                    decoded = base64.b64decode(content_fixed)
                    print('✅ Base64 is now valid')
                    
                    # Update the database
                    cursor.execute('UPDATE docs SET content = %s WHERE id = %s', (content_fixed, doc_id))
                    conn.commit()
                    print('✅ Database updated')
                except Exception as e:
                    print(f'❌ Still invalid: {e}')
            else:
                print('✅ Content length is already valid (divisible by 4)')
                # Still test if it's valid base64
                try:
                    decoded = base64.b64decode(content)
                    print('✅ Base64 is valid')
                except Exception as e:
                    print(f'❌ Base64 is invalid despite correct length: {e}')
        else:
            print('Document not found')
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_base64_document()