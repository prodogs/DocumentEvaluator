#!/usr/bin/env python3
"""
Check Documents Table Population

This script will verify if the documents table is being populated correctly
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Document, Batch, LlmResponse
from sqlalchemy import text, func

def check_documents_table():
    """Check the documents table population"""

    print("🔍 Documents Table Analysis")
    print("=" * 50)

    session = Session()

    try:
        # Check total documents
        total_docs = session.query(Document).count()
        print(f"📊 Total Documents: {total_docs}")

        # Check recent documents
        print("\n📋 Recent Documents (last 10):")
        print("-" * 40)

        recent_docs = session.query(Document).order_by(Document.id.desc()).limit(10).all()

        if recent_docs:
            for doc in recent_docs:
                print(f"  Doc ID: {doc.id}")
                print(f"    Filename: {doc.filename}")
                print(f"    Filepath: {doc.filepath}")
                print(f"    Batch ID: {doc.batch_id}")
                print(f"    Folder ID: {doc.folder_id}")
                print(f"    Status: {doc.status}")
                print(f"    Created: {doc.created_at}")
                print()
        else:
            print("  No documents found")

        # Check documents by batch
        print("📊 Documents by Batch:")
        print("-" * 30)

        batch_counts = session.query(
            Batch.batch_number,
            Batch.batch_name,
            func.count(Document.id).label('doc_count')
        ).outerjoin(Document, Batch.id == Document.batch_id)\
         .group_by(Batch.id, Batch.batch_number, Batch.batch_name)\
         .order_by(Batch.batch_number.desc())\
         .limit(10).all()

        for batch_num, batch_name, doc_count in batch_counts:
            print(f"  Batch #{batch_num}: {doc_count} documents")
            print(f"    Name: {batch_name}")

        # Check documents without batch_id
        orphaned_docs = session.query(Document).filter(Document.batch_id.is_(None)).count()
        print(f"\n⚠️  Documents without batch_id: {orphaned_docs}")

        # Check documents by status
        print("\n📈 Documents by Status:")
        print("-" * 25)

        status_counts = session.query(
            Document.status,
            func.count(Document.id).label('count')
        ).group_by(Document.status).all()

        for status, count in status_counts:
            status_name = {
                'N': 'Not Started',
                'P': 'Processing',
                'C': 'Complete',
                'F': 'Failed'
            }.get(status, status)
            print(f"  {status_name} ({status}): {count}")

        # Check LLM responses for documents
        print("\n🤖 LLM Responses:")
        print("-" * 20)

        total_responses = session.query(LlmResponse).count()
        print(f"  Total LLM Responses: {total_responses}")

        response_status_counts = session.query(
            LlmResponse.status,
            func.count(LlmResponse.id).label('count')
        ).group_by(LlmResponse.status).all()

        for status, count in response_status_counts:
            status_name = {
                'N': 'Not Started',
                'P': 'Processing',
                'C': 'Complete',
                'F': 'Failed'
            }.get(status, status)
            print(f"    {status_name} ({status}): {count}")

        # Check recent LLM responses
        print("\n🔄 Recent LLM Responses (last 5):")
        print("-" * 35)

        recent_responses = session.query(LlmResponse).order_by(LlmResponse.id.desc()).limit(5).all()

        for resp in recent_responses:
            doc = session.query(Document).filter(Document.id == resp.document_id).first()
            doc_name = doc.filename if doc else "Unknown"
            print(f"  Response ID: {resp.id}")
            print(f"    Document: {doc_name}")
            print(f"    Status: {resp.status}")
            print(f"    Task ID: {resp.task_id}")
            print(f"    Updated: {resp.updated_at}")
            print()

        session.close()

        print("✅ Documents table analysis complete!")

        # Provide recommendations
        if total_docs == 0:
            print("\n⚠️  No documents found - this might indicate:")
            print("   - Documents are not being created")
            print("   - File processing is failing")
            print("   - Folder paths are incorrect")
        elif orphaned_docs > 0:
            print(f"\n⚠️  {orphaned_docs} documents without batch_id - this might indicate:")
            print("   - Batch assignment is failing")
            print("   - Database transaction issues")

        return True

    except Exception as e:
        print(f"❌ Error checking documents table: {e}")
        session.close()
        return False

def check_folder_configuration():
    """Check folder configuration"""

    print("\n🗂️  Folder Configuration:")
    print("=" * 30)

    session = Session()

    try:
        from server.models import Folder

        folders = session.query(Folder).all()

        if folders:
            for folder in folders:
                print(f"  Folder ID: {folder.id}")
                print(f"    Path: {folder.path}")
                print(f"    Active: {folder.active}")
                print()

                # Check if folder path exists
                import os
                if os.path.exists(folder.path):
                    files = [f for f in os.listdir(folder.path) if f.endswith(('.pdf', '.txt', '.doc', '.docx'))]
                    print(f"    Files found: {len(files)}")
                    if files:
                        print(f"    Sample files: {files[:3]}")
                else:
                    print(f"    ⚠️  Path does not exist!")
                print()
        else:
            print("  No folders configured")

        session.close()

    except Exception as e:
        print(f"❌ Error checking folders: {e}")
        session.close()

if __name__ == "__main__":
    check_documents_table()
    check_folder_configuration()
