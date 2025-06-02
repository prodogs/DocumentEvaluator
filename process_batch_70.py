#!/usr/bin/env python3
"""
Process Batch 70 - Working Solution

This script processes batch 70 by:
1. Checking the current batch status
2. Staging documents if needed
3. Creating entries in KnowledgeDocuments database
4. Running the LLM analysis
"""

import os
import sys
import json
import base64
import psycopg2
from datetime import datetime

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Batch, Document, Connection, Prompt


def process_batch_70():
    """Process batch 70 with the new architecture"""
    
    print("=== Processing Batch 70 ===\n")
    
    # Step 1: Check batch status
    session = Session()
    try:
        batch = session.query(Batch).filter_by(id=70).first()
        if not batch:
            print("❌ Batch 70 not found")
            return
            
        print(f"📋 Batch Info:")
        print(f"   ID: {batch.id}")
        print(f"   Name: {batch.batch_name}")
        print(f"   Status: {batch.status}")
        print(f"   Documents: {batch.total_documents}")
        
        # Get configuration
        config = batch.config_snapshot or {}
        connections = config.get('connections', [])
        prompts = config.get('prompts', [])
        
        print(f"   Connections: {len(connections)}")
        print(f"   Prompts: {len(prompts)}")
        
        # Step 2: Get documents
        documents = session.query(Document).filter_by(batch_id=70).all()
        print(f"\n📄 Found {len(documents)} documents")
        
        # Step 3: Connect to KnowledgeDocuments database
        print("\n🔗 Connecting to KnowledgeDocuments database...")
        kb_conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        kb_cursor = kb_conn.cursor()
        
        # Step 4: Process each document
        success_count = 0
        error_count = 0
        
        for doc in documents:
            print(f"\n📄 Processing: {doc.filename}")
            
            # Check if file exists
            if not os.path.exists(doc.filepath):
                print(f"   ❌ File not found: {doc.filepath}")
                error_count += 1
                continue
                
            try:
                # Read file content
                with open(doc.filepath, 'rb') as f:
                    file_content = f.read()
                
                # Encode to base64
                encoded_content = base64.b64encode(file_content).decode('utf-8')
                
                # Ensure valid base64 (must be divisible by 4)
                if len(encoded_content) % 4 != 0:
                    # Add padding if needed
                    encoded_content += '=' * (4 - len(encoded_content) % 4)
                
                print(f"   ✅ File read: {len(file_content)} bytes")
                print(f"   ✅ Base64 encoded: {len(encoded_content)} chars")
                
                # Check if this is the problematic size
                if len(encoded_content) == 1398101:
                    print(f"   ⚠️  WARNING: This is the problematic document size!")
                    # Strip any trailing whitespace
                    encoded_content = encoded_content.strip()
                    print(f"   ✅ After cleanup: {len(encoded_content)} chars")
                
                # Create document ID
                doc_id = f"batch_70_doc_{doc.id}"
                
                # Insert into docs table
                kb_cursor.execute("""
                    INSERT INTO docs (document_id, content, content_type, doc_type, file_size, encoding, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (document_id) DO UPDATE
                    SET content = EXCLUDED.content,
                        file_size = EXCLUDED.file_size,
                        created_at = NOW()
                    RETURNING id
                """, (
                    doc_id,
                    encoded_content,
                    'text/plain',  # You might want to detect this
                    os.path.splitext(doc.filename)[1][1:],  # Extension without dot
                    len(file_content),
                    'base64'
                ))
                
                kb_doc_id = kb_cursor.fetchone()[0]
                print(f"   ✅ Inserted into KnowledgeDocuments: ID {kb_doc_id}")
                
                # Create LLM response entries
                for conn in connections:
                    for prompt in prompts:
                        kb_cursor.execute("""
                            INSERT INTO llm_responses 
                            (document_id, prompt_id, connection_id, connection_details, 
                             status, created_at, batch_id)
                            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            kb_doc_id,
                            prompt['id'],
                            conn['id'],
                            json.dumps(conn),
                            'QUEUED',
                            70
                        ))
                
                kb_conn.commit()
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                kb_conn.rollback()
                error_count += 1
                
        # Step 5: Update batch status
        if success_count > 0:
            batch.status = 'ANALYZING'
            batch.total_documents = success_count
            session.commit()
            print(f"\n✅ Batch 70 updated to ANALYZING status")
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📋 Total: {len(documents)}")
        
        kb_cursor.close()
        kb_conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    process_batch_70()