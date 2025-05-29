#!/usr/bin/env python3
"""
Simple Documents Table Check

Check if documents are being populated correctly in PostgreSQL
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Document, Batch, LlmResponse, Folder
from sqlalchemy import func

def check_documents():
    """Check documents table"""
    
    print("🔍 Documents Table Check")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Total documents
        total_docs = session.query(Document).count()
        print(f"📊 Total Documents: {total_docs}")
        
        if total_docs > 0:
            print("\n📋 Recent Documents:")
            print("-" * 30)
            
            recent_docs = session.query(Document).order_by(Document.id.desc()).limit(5).all()
            
            for doc in recent_docs:
                print(f"  Doc ID: {doc.id}")
                print(f"    File: {doc.filename}")
                print(f"    Batch ID: {doc.batch_id}")
                print(f"    Folder ID: {doc.folder_id}")
                print(f"    Created: {doc.created_at}")
                print()
        
        # Documents by batch
        print("📊 Documents by Batch:")
        print("-" * 25)
        
        batch_docs = session.query(
            Batch.batch_number,
            Batch.batch_name,
            func.count(Document.id).label('doc_count')
        ).outerjoin(Document, Batch.id == Document.batch_id)\
         .group_by(Batch.id, Batch.batch_number, Batch.batch_name)\
         .order_by(Batch.batch_number.desc())\
         .limit(5).all()
        
        for batch_num, batch_name, doc_count in batch_docs:
            print(f"  Batch #{batch_num}: {doc_count} docs")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def check_llm_responses():
    """Check LLM responses"""
    
    print("\n🤖 LLM Responses Check")
    print("=" * 30)
    
    session = Session()
    
    try:
        total_responses = session.query(LlmResponse).count()
        print(f"📊 Total LLM Responses: {total_responses}")
        
        if total_responses > 0:
            # Status breakdown
            status_counts = session.query(
                LlmResponse.status,
                func.count(LlmResponse.id).label('count')
            ).group_by(LlmResponse.status).all()
            
            print("\n📈 Response Status:")
            for status, count in status_counts:
                status_name = {
                    'R': 'Ready',
                    'P': 'Processing', 
                    'S': 'Success',
                    'F': 'Failed'
                }.get(status, status)
                print(f"  {status_name}: {count}")
            
            # Recent responses
            print("\n🔄 Recent Responses:")
            recent = session.query(LlmResponse).order_by(LlmResponse.id.desc()).limit(3).all()
            
            for resp in recent:
                doc = session.query(Document).filter(Document.id == resp.document_id).first()
                doc_name = doc.filename if doc else "Unknown"
                print(f"  Response ID: {resp.id}")
                print(f"    Document: {doc_name}")
                print(f"    Status: {resp.status}")
                print(f"    Task ID: {resp.task_id}")
                print()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def check_folders():
    """Check folder configuration"""
    
    print("\n🗂️  Folders Check")
    print("=" * 20)
    
    session = Session()
    
    try:
        folders = session.query(Folder).all()
        
        print(f"📊 Total Folders: {len(folders)}")
        
        for folder in folders:
            print(f"\n  Folder ID: {folder.id}")
            print(f"    Path: {folder.folder_path}")
            print(f"    Name: {folder.folder_name}")
            print(f"    Active: {folder.active}")
            
            # Count documents in this folder
            doc_count = session.query(Document).filter(Document.folder_id == folder.id).count()
            print(f"    Documents: {doc_count}")
            
            # Check if path exists
            if os.path.exists(folder.folder_path):
                files = [f for f in os.listdir(folder.folder_path) 
                        if f.endswith(('.pdf', '.txt', '.doc', '.docx'))]
                print(f"    Files on disk: {len(files)}")
            else:
                print(f"    ⚠️  Path not found!")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 PostgreSQL Documents Analysis")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Check each component
    docs_ok = check_documents()
    responses_ok = check_llm_responses()
    folders_ok = check_folders()
    
    print("\n" + "=" * 50)
    if all([docs_ok, responses_ok, folders_ok]):
        print("✅ All checks completed successfully!")
        print("💡 PostgreSQL is being updated correctly.")
    else:
        print("⚠️  Some issues detected.")
    
    print("\n🔧 To verify in DataGrip:")
    print("SELECT * FROM documents ORDER BY id DESC LIMIT 10;")
    print("SELECT * FROM llm_responses ORDER BY id DESC LIMIT 10;")
    print("SELECT * FROM batches ORDER BY batch_number DESC LIMIT 10;")

if __name__ == "__main__":
    main()
