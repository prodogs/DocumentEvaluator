#!/usr/bin/env python3

import psycopg2
import base64
import json

def debug_1398101_issue():
    """Debug the specific 1398101 character base64 issue"""
    
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
        print("🔍 Investigating the 1398101 character base64 issue...")
        
        # Find all batch 70 documents and check their content
        cursor.execute("""
            SELECT lr.id, lr.task_id, lr.status, lr.error_message, 
                   d.id as doc_id, d.document_id, LENGTH(d.content) as content_length,
                   d.content_type, d.encoding
            FROM llm_responses lr
            JOIN docs d ON lr.document_id = d.id
            WHERE lr.batch_id = 70
            ORDER BY lr.id
        """)
        
        responses = cursor.fetchall()
        print(f"Found {len(responses)} LLM responses for batch 70\n")
        
        # Look for patterns that might create 1398101 characters
        for i, (resp_id, task_id, status, error_msg, doc_id, document_id, content_length, content_type, encoding) in enumerate(responses):
            print(f"Response {i+1}: ID={resp_id}")
            print(f"  Task ID: {task_id}")
            print(f"  Status: {status}")
            print(f"  Doc ID: {doc_id} ({document_id})")
            print(f"  Content length: {content_length:,} chars (mod 4: {content_length % 4})")
            
            if error_msg and "1398101" in str(error_msg):
                print(f"  ❌ ERROR: {error_msg}")
                print(f"  🎯 THIS RESPONSE HAS THE 1398101 ERROR!")
                
                # Get the actual content for this document
                cursor.execute("SELECT content FROM docs WHERE id = %s", (doc_id,))
                content_raw = cursor.fetchone()[0]
                
                if isinstance(content_raw, (bytes, memoryview)):
                    content = content_raw.tobytes().decode('utf-8') if hasattr(content_raw, 'tobytes') else content_raw.decode('utf-8')
                else:
                    content = str(content_raw)
                
                print(f"  📊 Actual content analysis:")
                print(f"     Length: {len(content):,}")
                print(f"     Mod 4: {len(content) % 4}")
                print(f"     First 100 chars: {repr(content[:100])}")
                print(f"     Last 100 chars: {repr(content[-100:])}")
                
                # Check if there are any non-base64 characters
                valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
                invalid_chars = set(content) - valid_chars
                if invalid_chars:
                    print(f"     ❌ Invalid characters found: {invalid_chars}")
                else:
                    print(f"     ✅ All characters are valid base64")
                
                # Test different scenarios that might create 1398101
                scenarios = [
                    ("Raw content", content),
                    ("Content + newline", content + "\n"),
                    ("Content + space", content + " "),
                    ("Content + null", content + "\0"),
                    ("Stripped content", content.strip()),
                ]
                
                print(f"  🧪 Testing scenarios that might create 1398101:")
                for name, test_content in scenarios:
                    if len(test_content) == 1398101:
                        print(f"     🎯 FOUND IT! {name} = {len(test_content)} chars")
                        print(f"        Last 20 chars: {repr(test_content[-20:])}")
                        
                        # Try to decode this content
                        try:
                            decoded = base64.b64decode(test_content)
                            print(f"        ✅ Successfully decoded to {len(decoded)} bytes")
                        except Exception as e:
                            print(f"        ❌ Decode failed: {e}")
                            
                            # Try with padding fix
                            padded = test_content.strip()
                            if len(padded) % 4 != 0:
                                padded += '=' * (4 - len(padded) % 4)
                            try:
                                decoded = base64.b64decode(padded)
                                print(f"        ✅ Fixed with padding! Decoded to {len(decoded)} bytes")
                                
                                # Update the database with the fixed content
                                cursor.execute("UPDATE docs SET content = %s WHERE id = %s", (padded, doc_id))
                                conn.commit()
                                print(f"        ✅ Database updated with fixed content")
                            except Exception as e2:
                                print(f"        ❌ Even padding didn't help: {e2}")
                    elif abs(len(test_content) - 1398101) < 5:
                        print(f"     🔍 Close: {name} = {len(test_content)} chars (diff: {len(test_content) - 1398101})")
                
                # Check if external system might be concatenating content with metadata
                print(f"  💡 Checking if 1398101 could be content + metadata:")
                diff = 1398101 - len(content)
                if diff > 0:
                    print(f"     Missing {diff} characters to reach 1398101")
                    print(f"     This could be metadata added by external system")
                
            else:
                print(f"  ✅ No error")
            
            print()
        
        # Summary analysis
        print("📋 SUMMARY:")
        total_errors = sum(1 for _, _, _, error_msg, _, _, _, _, _ in responses if error_msg and "1398101" in str(error_msg))
        print(f"  Total responses with 1398101 error: {total_errors}")
        
        if total_errors == 0:
            print("  🤔 No responses currently have the 1398101 error")
            print("  💡 The error might be happening during external processing")
            print("  💡 External system might be adding metadata to the base64 content")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    debug_1398101_issue()