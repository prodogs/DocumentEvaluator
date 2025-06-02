#!/usr/bin/env python3

import psycopg2
import base64
import json

def test_batch70_processing():
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
        # Get LLM responses for batch 70 to simulate what the processing queue sees
        cursor.execute("""
            SELECT lr.id, lr.document_id, lr.status, d.document_id as kb_document_id, LENGTH(d.content) as content_length
            FROM llm_responses lr
            JOIN docs d ON lr.document_id = d.id
            WHERE lr.batch_id = 70
            ORDER BY lr.id
            LIMIT 5
        """)
        
        responses = cursor.fetchall()
        print(f"Found {len(responses)} LLM responses for batch 70")
        
        for resp_id, doc_id, status, kb_doc_id, content_length in responses:
            print(f"\n🔍 Testing response {resp_id}:")
            print(f"   Doc ID: {doc_id}, KB Doc ID: {kb_doc_id}")
            print(f"   Status: {status}, Content length: {content_length}")
            
            # Get the actual content like the processing queue would
            cursor.execute('SELECT content FROM docs WHERE id = %s', (doc_id,))
            content_raw = cursor.fetchone()[0]
            
            # Convert to string like the processing code does
            if isinstance(content_raw, (bytes, memoryview)):
                content = content_raw.tobytes().decode('utf-8') if hasattr(content_raw, 'tobytes') else content_raw.decode('utf-8')
            else:
                content = str(content_raw)
            
            print(f"   Retrieved content length: {len(content)}")
            print(f"   Content mod 4: {len(content) % 4}")
            
            # Test base64 validation like the processing code does
            try:
                # This is what might be causing the issue - let's see if there are any hidden characters
                content_stripped = content.strip()
                print(f"   After strip: {len(content_stripped)}, mod 4: {len(content_stripped) % 4}")
                
                # Check for any non-base64 characters
                import re
                base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
                if not base64_pattern.match(content_stripped):
                    print("   ❌ Content contains non-base64 characters")
                    # Find the first invalid character
                    for i, char in enumerate(content_stripped):
                        if char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=':
                            print(f"   Invalid char at position {i}: {repr(char)}")
                            break
                else:
                    print("   ✅ Content contains only valid base64 characters")
                
                # Try to decode
                decoded = base64.b64decode(content_stripped)
                print(f"   ✅ Successfully decoded to {len(decoded)} bytes")
                
            except Exception as e:
                print(f"   ❌ Base64 decode failed: {e}")
                
                # If the error mentions the specific number, let's investigate
                error_str = str(e)
                if "1398101" in error_str:
                    print(f"   🎯 Found the 1398101 error! Content length is {len(content)}")
                    print(f"   Last 50 chars: {repr(content[-50:])}")
                    print(f"   First 50 chars: {repr(content[:50])}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_batch70_processing()