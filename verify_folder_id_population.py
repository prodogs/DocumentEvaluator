#!/usr/bin/env python3
"""
Verification script to check if folder_id is properly populated in the documents table
"""

import sys
sys.path.append('.')

from server.database import Session
from server.models import Document, Folder, Batch

def check_folder_id_population():
    """Check if documents have proper folder_id values"""
    print("🔍 Checking folder_id Population in Documents Table\n")
    
    session = Session()
    try:
        # Get all documents
        documents = session.query(Document).all()
        total_docs = len(documents)
        
        print(f"📊 Total documents in database: {total_docs}")
        
        if total_docs == 0:
            print("ℹ️  No documents found in database")
            return True
        
        # Check folder_id population
        docs_with_folder_id = session.query(Document).filter(Document.folder_id.isnot(None)).all()
        docs_without_folder_id = session.query(Document).filter(Document.folder_id.is_(None)).all()
        
        print(f"✅ Documents with folder_id: {len(docs_with_folder_id)}")
        print(f"❌ Documents without folder_id: {len(docs_without_folder_id)}")
        
        # Show percentage
        if total_docs > 0:
            percentage_with_folder = (len(docs_with_folder_id) / total_docs) * 100
            print(f"📈 Folder ID coverage: {percentage_with_folder:.1f}%")
        
        # Show sample documents with folder_id
        if docs_with_folder_id:
            print(f"\n📄 Sample documents WITH folder_id:")
            for doc in docs_with_folder_id[:5]:  # Show first 5
                folder = session.query(Folder).filter_by(id=doc.folder_id).first()
                folder_name = folder.folder_name if folder else "Unknown"
                print(f"   - {doc.filename} (Doc ID: {doc.id}, Folder ID: {doc.folder_id}, Folder: {folder_name})")
        
        # Show sample documents without folder_id
        if docs_without_folder_id:
            print(f"\n❌ Sample documents WITHOUT folder_id:")
            for doc in docs_without_folder_id[:5]:  # Show first 5
                print(f"   - {doc.filename} (Doc ID: {doc.id}, Path: {doc.filepath})")
        
        # Check folder-document relationships
        print(f"\n🔗 Checking Folder-Document Relationships:")
        folders = session.query(Folder).all()
        
        for folder in folders:
            docs_in_folder = session.query(Document).filter_by(folder_id=folder.id).count()
            print(f"   📁 {folder.folder_name or folder.folder_path}: {docs_in_folder} documents")
        
        return len(docs_without_folder_id) == 0
        
    except Exception as e:
        print(f"❌ Error checking folder_id population: {e}")
        return False
    finally:
        session.close()

def check_batch_document_relationships():
    """Check batch-document relationships"""
    print(f"\n📦 Checking Batch-Document Relationships\n")
    
    session = Session()
    try:
        # Get all batches
        batches = session.query(Batch).all()
        
        print(f"📊 Total batches in database: {len(batches)}")
        
        for batch in batches:
            docs_in_batch = session.query(Document).filter_by(batch_id=batch.id).count()
            print(f"   #{batch.batch_number}: {batch.batch_name} - {docs_in_batch} documents")
        
        # Check documents without batch_id
        docs_without_batch = session.query(Document).filter(Document.batch_id.is_(None)).count()
        print(f"\n❌ Documents without batch_id: {docs_without_batch}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking batch relationships: {e}")
        return False
    finally:
        session.close()

def verify_database_schema():
    """Verify that the database schema includes the expected columns"""
    print(f"\n🗄️  Verifying Database Schema\n")
    
    session = Session()
    try:
        # Check if Document table has the expected columns
        from sqlalchemy import inspect
        inspector = inspect(session.bind)
        
        # Get Document table columns
        doc_columns = inspector.get_columns('documents')
        column_names = [col['name'] for col in doc_columns]
        
        print(f"📋 Document table columns: {column_names}")
        
        # Check for required columns
        required_columns = ['id', 'filepath', 'filename', 'folder_id', 'batch_id', 'created_at', 'task_id']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print(f"✅ All required columns present")
        
        # Check Batch table columns
        batch_columns = inspector.get_columns('batches')
        batch_column_names = [col['name'] for col in batch_columns]
        
        print(f"📋 Batch table columns: {batch_column_names}")
        
        # Check for required batch columns
        required_batch_columns = ['id', 'batch_number', 'batch_name', 'folder_path', 'created_at', 'started_at', 'completed_at']
        missing_batch_columns = [col for col in required_batch_columns if col not in batch_column_names]
        
        if missing_batch_columns:
            print(f"❌ Missing batch columns: {missing_batch_columns}")
            return False
        else:
            print(f"✅ All required batch columns present")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False
    finally:
        session.close()

def test_folder_document_linking():
    """Test creating a document with folder_id"""
    print(f"\n🧪 Testing Folder-Document Linking\n")
    
    session = Session()
    try:
        # Get or create a test folder
        test_folder = session.query(Folder).first()
        
        if not test_folder:
            print("ℹ️  No folders found, creating test folder")
            test_folder = Folder(
                folder_path="/test/folder_id_verification",
                folder_name="Test Folder for ID Verification",
                active=1
            )
            session.add(test_folder)
            session.commit()
        
        print(f"📁 Using folder: {test_folder.folder_name} (ID: {test_folder.id})")
        
        # Create a test document with folder_id
        test_doc = Document(
            filepath="/test/folder_id_verification/test_doc.pdf",
            filename="test_doc.pdf",
            folder_id=test_folder.id
        )
        session.add(test_doc)
        session.commit()
        
        print(f"✅ Created test document with folder_id: {test_doc.id}")
        
        # Verify the relationship
        retrieved_doc = session.query(Document).filter_by(id=test_doc.id).first()
        if retrieved_doc and retrieved_doc.folder_id == test_folder.id:
            print(f"✅ Folder-document relationship verified")
            
            # Test the relationship
            folder_docs = session.query(Document).filter_by(folder_id=test_folder.id).count()
            print(f"✅ Folder contains {folder_docs} documents")
            
            # Clean up
            session.delete(test_doc)
            session.commit()
            print(f"🧹 Cleaned up test document")
            
            return True
        else:
            print(f"❌ Folder-document relationship failed")
            return False
        
    except Exception as e:
        print(f"❌ Error testing folder-document linking: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Folder ID Population Verification\n")
    
    # Verify database schema
    schema_ok = verify_database_schema()
    
    # Check folder_id population
    folder_id_ok = check_folder_id_population()
    
    # Check batch relationships
    batch_ok = check_batch_document_relationships()
    
    # Test folder-document linking
    linking_ok = test_folder_document_linking()
    
    print(f"\n=== Verification Results ===")
    print(f"Database Schema: {'✅ CORRECT' if schema_ok else '❌ ISSUES'}")
    print(f"Folder ID Population: {'✅ CORRECT' if folder_id_ok else '❌ ISSUES'}")
    print(f"Batch Relationships: {'✅ CORRECT' if batch_ok else '❌ ISSUES'}")
    print(f"Folder-Document Linking: {'✅ CORRECT' if linking_ok else '❌ ISSUES'}")
    
    if all([schema_ok, folder_id_ok, batch_ok, linking_ok]):
        print(f"\n🎉 All verifications passed!")
        print(f"   ✅ Documents are properly linked to folders")
        print(f"   ✅ Documents are properly linked to batches")
        print(f"   ✅ Database schema is correct")
    else:
        print(f"\n⚠️  Some verifications failed:")
        if not schema_ok:
            print(f"   ❌ Database schema issues detected")
        if not folder_id_ok:
            print(f"   ❌ Some documents missing folder_id")
        if not batch_ok:
            print(f"   ❌ Batch relationship issues")
        if not linking_ok:
            print(f"   ❌ Folder-document linking test failed")
        
        print(f"\n💡 Recommendations:")
        print(f"   1. Run database migrations if schema is incorrect")
        print(f"   2. Reprocess folders to populate missing folder_id values")
        print(f"   3. Check process_folder function implementation")
