#!/usr/bin/env python3
"""
Test script to verify the batch tracking system
"""

import sys
import json
from datetime import datetime
sys.path.append('.')

from server.database import Session
from server.models import Batch, Document, LlmResponse
from server.services.batch_service import batch_service

def test_batch_creation():
    """Test creating a new batch"""
    print("🧪 Testing Batch Creation\n")
    
    try:
        # Create a test batch
        test_folder = "/test/batch_system/documents"
        test_batch_name = f"Test Batch - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        batch = batch_service.create_batch(
            folder_path=test_folder,
            batch_name=test_batch_name,
            description="Test batch for verifying batch system functionality"
        )
        
        print(f"✅ Created batch:")
        print(f"   ID: {batch.id}")
        print(f"   Batch Number: #{batch.batch_number}")
        print(f"   Name: {batch.batch_name}")
        print(f"   Folder Path: {batch.folder_path}")
        print(f"   Status: {batch.status}")
        print(f"   Created At: {batch.created_at}")
        print(f"   Started At: {batch.started_at}")
        
        return batch
        
    except Exception as e:
        print(f"❌ Error creating batch: {e}")
        return None

def test_batch_name_update(batch):
    """Test updating batch name"""
    print(f"\n🔧 Testing Batch Name Update\n")
    
    try:
        new_name = f"Updated Test Batch - {datetime.now().strftime('%H:%M:%S')}"
        new_description = "Updated description for testing"
        
        success = batch_service.update_batch_name(
            batch.id,
            new_name,
            new_description
        )
        
        if success:
            print(f"✅ Successfully updated batch name:")
            print(f"   New Name: {new_name}")
            print(f"   New Description: {new_description}")
            
            # Get updated batch info
            batch_info = batch_service.get_batch_info(batch.id)
            print(f"   Verified Name: {batch_info['batch_name']}")
            print(f"   Verified Description: {batch_info['description']}")
            return True
        else:
            print(f"❌ Failed to update batch name")
            return False
            
    except Exception as e:
        print(f"❌ Error updating batch name: {e}")
        return False

def test_batch_document_linking(batch):
    """Test linking documents to batch"""
    print(f"\n📄 Testing Document-Batch Linking\n")
    
    session = Session()
    try:
        # Create test documents linked to the batch
        test_docs = []
        for i in range(3):
            doc = Document(
                filepath=f"/test/batch_system/doc_{i}.pdf",
                filename=f"test_doc_{i}.pdf",
                batch_id=batch.id  # Link to batch
            )
            session.add(doc)
            test_docs.append(doc)
        
        session.commit()
        
        print(f"✅ Created {len(test_docs)} test documents linked to batch #{batch.batch_number}")
        
        # Verify the linking
        linked_docs = session.query(Document).filter_by(batch_id=batch.id).all()
        print(f"✅ Verified {len(linked_docs)} documents linked to batch")
        
        for doc in linked_docs:
            print(f"   - {doc.filename} (ID: {doc.id})")
        
        return test_docs
        
    except Exception as e:
        print(f"❌ Error linking documents to batch: {e}")
        return []
    finally:
        session.close()

def test_batch_progress_tracking(batch, test_docs):
    """Test batch progress tracking"""
    print(f"\n📊 Testing Batch Progress Tracking\n")
    
    session = Session()
    try:
        # Create some LLM responses for the test documents
        for i, doc in enumerate(test_docs):
            # Create responses with different statuses
            statuses = ['N', 'P', 'S']  # Not started, Processing, Success
            status = statuses[i % len(statuses)]
            
            response = LlmResponse(
                document_id=doc.id,
                prompt_id=1,  # Assuming prompt ID 1 exists
                llm_config_id=1,  # Assuming LLM config ID 1 exists
                llm_name="test_llm",
                status=status
            )
            session.add(response)
        
        session.commit()
        print(f"✅ Created test LLM responses with various statuses")
        
        # Update batch progress
        progress = batch_service.update_batch_progress(batch.id)
        
        print(f"✅ Batch progress updated:")
        print(f"   Total Documents: {progress.get('total_documents', 0)}")
        print(f"   Processed Responses: {progress.get('processed_responses', 0)}")
        print(f"   Total Responses: {progress.get('total_responses', 0)}")
        print(f"   Completion %: {progress.get('completion_percentage', 0):.1f}%")
        print(f"   Status: {progress.get('status', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error tracking batch progress: {e}")
        return False
    finally:
        session.close()

def test_batch_listing():
    """Test listing batches"""
    print(f"\n📋 Testing Batch Listing\n")
    
    try:
        batches = batch_service.list_batches(limit=10)
        
        print(f"✅ Retrieved {len(batches)} batches:")
        for batch in batches:
            print(f"   #{batch['batch_number']}: {batch['batch_name']}")
            print(f"      Status: {batch['status']}")
            print(f"      Documents: {batch['total_documents']}")
            print(f"      Completion: {batch['completion_percentage']:.1f}%")
            print(f"      Created: {batch['created_at']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing batches: {e}")
        return False

def test_batch_info_retrieval(batch):
    """Test getting detailed batch information"""
    print(f"\n🔍 Testing Batch Info Retrieval\n")
    
    try:
        batch_info = batch_service.get_batch_info(batch.id)
        
        if batch_info:
            print(f"✅ Retrieved detailed batch information:")
            print(f"   Batch #{batch_info['batch_number']}: {batch_info['batch_name']}")
            print(f"   Folder Path: {batch_info['folder_path']}")
            print(f"   Status: {batch_info['status']}")
            print(f"   Created: {batch_info['created_at']}")
            print(f"   Started: {batch_info['started_at']}")
            print(f"   Completed: {batch_info['completed_at']}")
            print(f"   Duration: {batch_info.get('duration_seconds', 'N/A')} seconds")
            print(f"   Documents: {batch_info['total_documents']}")
            print(f"   Responses: {batch_info['total_responses']}")
            print(f"   Status Counts: {batch_info['status_counts']}")
            print(f"   Completion: {batch_info['completion_percentage']:.1f}%")
            return True
        else:
            print(f"❌ Failed to retrieve batch information")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving batch info: {e}")
        return False

def cleanup_test_data(batch, test_docs):
    """Clean up test data"""
    print(f"\n🧹 Cleaning Up Test Data\n")
    
    session = Session()
    try:
        # Delete test LLM responses
        test_responses = session.query(LlmResponse).filter(
            LlmResponse.llm_name == 'test_llm'
        ).all()
        
        for response in test_responses:
            session.delete(response)
        
        # Delete test documents
        for doc in test_docs:
            session.delete(doc)
        
        # Delete test batch
        session.delete(batch)
        
        session.commit()
        
        print(f"✅ Cleaned up:")
        print(f"   - {len(test_responses)} test LLM responses")
        print(f"   - {len(test_docs)} test documents")
        print(f"   - 1 test batch")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning up test data: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Batch System Test Suite\n")
    
    # Test batch creation
    batch = test_batch_creation()
    if not batch:
        print("❌ Batch creation failed, stopping tests")
        sys.exit(1)
    
    # Test batch name update
    name_update_success = test_batch_name_update(batch)
    
    # Test document linking
    test_docs = test_batch_document_linking(batch)
    
    # Test progress tracking
    progress_success = test_batch_progress_tracking(batch, test_docs)
    
    # Test batch listing
    listing_success = test_batch_listing()
    
    # Test batch info retrieval
    info_success = test_batch_info_retrieval(batch)
    
    # Clean up
    cleanup_success = cleanup_test_data(batch, test_docs)
    
    print(f"\n=== Test Results ===")
    print(f"Batch Creation: {'✅ PASS' if batch else '❌ FAIL'}")
    print(f"Name Update: {'✅ PASS' if name_update_success else '❌ FAIL'}")
    print(f"Document Linking: {'✅ PASS' if test_docs else '❌ FAIL'}")
    print(f"Progress Tracking: {'✅ PASS' if progress_success else '❌ FAIL'}")
    print(f"Batch Listing: {'✅ PASS' if listing_success else '❌ FAIL'}")
    print(f"Info Retrieval: {'✅ PASS' if info_success else '❌ FAIL'}")
    print(f"Cleanup: {'✅ PASS' if cleanup_success else '❌ FAIL'}")
    
    all_passed = all([
        batch, name_update_success, test_docs, progress_success,
        listing_success, info_success, cleanup_success
    ])
    
    if all_passed:
        print(f"\n🎉 All tests passed! Batch system is working correctly.")
        print(f"   ✅ Batches are created with timestamps")
        print(f"   ✅ Documents are linked to batches")
        print(f"   ✅ Progress tracking works")
        print(f"   ✅ Batch names can be updated")
        print(f"   ✅ API endpoints should work correctly")
    else:
        print(f"\n⚠️  Some tests failed. Check the implementation.")
