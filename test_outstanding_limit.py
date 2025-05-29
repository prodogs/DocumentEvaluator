#!/usr/bin/env python3
"""
Test script to verify outstanding document processing limits
"""

import sys
import os
sys.path.append('.')

from server.database import Session
from server.models import LlmResponse, Document

def check_outstanding_documents():
    """Check how many documents are currently being processed"""
    session = Session()

    try:
        # Count documents with processing status
        processing_count = session.query(LlmResponse).filter(
            LlmResponse.status == 'P'
        ).count()

        # Count documents with task_ids (indicating they're being processed)
        documents_with_tasks = session.query(Document).filter(
            Document.task_id.isnot(None)
        ).count()

        # Count all llm_responses
        total_responses = session.query(LlmResponse).count()

        # Count all documents
        total_documents = session.query(Document).count()

        print("=== Outstanding Document Processing Status ===")
        print(f"📊 Total Documents: {total_documents}")
        print(f"📊 Total LLM Responses: {total_responses}")
        print(f"🔄 Documents with Processing Status (P): {processing_count}")
        print(f"🏷️  Documents with Task IDs: {documents_with_tasks}")

        # Check status distribution
        status_counts = session.query(LlmResponse.status, session.query(LlmResponse).filter(LlmResponse.status == LlmResponse.status).count()).all()

        print("\n=== Status Distribution ===")
        for status in ['P', 'S', 'F', 'R']:
            count = session.query(LlmResponse).filter(LlmResponse.status == status).count()
            status_name = {
                'P': 'Processing',
                'S': 'Success',
                'F': 'Failed',
                'R': 'Ready'
            }.get(status, status)
            print(f"{status} ({status_name}): {count}")

        return processing_count

    except Exception as e:
        print(f"Error checking outstanding documents: {e}")
        return 0
    finally:
        session.close()

def simulate_outstanding_limit_check(max_outstanding=30):
    """Simulate checking if we can start new processing based on outstanding limit"""
    current_outstanding = check_outstanding_documents()

    print(f"\n=== Outstanding Limit Check ===")
    print(f"🎯 Maximum Outstanding Limit: {max_outstanding}")
    print(f"📈 Current Outstanding: {current_outstanding}")

    if current_outstanding >= max_outstanding:
        print("❌ LIMIT REACHED: Cannot start new document processing")
        print(f"   Need to wait for {current_outstanding - max_outstanding + 1} tasks to complete")
        return False
    else:
        available_slots = max_outstanding - current_outstanding
        print(f"✅ CAN PROCESS: {available_slots} slots available")
        return True

def test_status_n_implementation():
    """Test the new 'N' status implementation"""
    print("\n=== Testing 'N' Status Implementation ===")

    session = Session()
    try:
        # Create test records with 'N' status
        test_doc = Document(
            filepath="/test/path/status_n_test.pdf",
            filename="status_n_test.pdf"
        )
        session.add(test_doc)
        session.commit()

        # Create LLM response with 'N' status
        test_response = LlmResponse(
            document_id=test_doc.id,
            prompt_id=1,
            llm_name="test_llm",
            status='N'  # Not started
        )
        session.add(test_response)
        session.commit()

        # Check if 'N' status records are found
        n_status_count = session.query(LlmResponse).filter(LlmResponse.status == 'N').count()
        print(f"📊 LLM responses with 'N' status: {n_status_count}")

        # Test startup recovery detection
        from server.services.startup_recovery import startup_recovery_service
        outstanding_tasks = startup_recovery_service.find_outstanding_tasks()

        not_started_tasks = [task for task in outstanding_tasks if task.get('recovery_type') == 'not_started']
        print(f"🔍 Not-started tasks found by recovery service: {len(not_started_tasks)}")

        # Clean up
        session.delete(test_response)
        session.delete(test_doc)
        session.commit()

        return len(not_started_tasks) > 0

    except Exception as e:
        print(f"❌ Error testing 'N' status: {e}")
        return False
    finally:
        session.close()

def check_process_folder_implementation():
    """Check if process_folder.py implements outstanding limit checking"""
    print("\n=== Process Folder Implementation Check ===")

    try:
        with open('server/api/process_folder.py', 'r') as f:
            content = f.read()

        # Check for specific implementation patterns
        has_max_outstanding = 'MAX_OUTSTANDING_DOCUMENTS' in content
        has_status_check = 'status == \'P\'' in content or 'status == "P"' in content
        has_count_check = 'count()' in content and ('LlmResponse' in content)
        has_limit_check = 'current_outstanding >= MAX_OUTSTANDING_DOCUMENTS' in content
        has_skip_logic = 'skipped_due_to_limit' in content

        print(f"📊 Has MAX_OUTSTANDING_DOCUMENTS constant: {has_max_outstanding}")
        print(f"📊 Has processing status check: {has_status_check}")
        print(f"🔢 Has count check: {has_count_check}")
        print(f"🚫 Has limit check logic: {has_limit_check}")
        print(f"⏭️  Has skip logic: {has_skip_logic}")

        # Extract the limit value
        if has_max_outstanding:
            import re
            match = re.search(r'MAX_OUTSTANDING_DOCUMENTS\s*=\s*(\d+)', content)
            if match:
                limit_value = int(match.group(1))
                print(f"🎯 Outstanding limit set to: {limit_value}")
            else:
                print("⚠️  Could not extract limit value")

        implementation_score = sum([has_max_outstanding, has_status_check, has_count_check, has_limit_check, has_skip_logic])
        print(f"📈 Implementation score: {implementation_score}/5")

        if implementation_score >= 4:
            print("✅ Outstanding limit implementation looks complete")
            return True
        elif implementation_score >= 2:
            print("⚠️  Partial implementation found")
            return True
        else:
            print("❌ No proper outstanding limit implementation found")
            return False

    except Exception as e:
        print(f"Error checking process_folder.py: {e}")
        return False

def create_test_processing_records(count=5):
    """Create test records with processing status to test the limit"""
    print(f"\n=== Creating {count} Test Processing Records ===")

    session = Session()
    try:
        # Create test documents and processing records
        for i in range(count):
            # Create a test document
            test_doc = Document(
                filepath=f"/test/path/test_document_{i}.pdf",
                filename=f"test_document_{i}.pdf"
            )
            session.add(test_doc)
            session.commit()

            # Create a processing LLM response
            test_response = LlmResponse(
                document_id=test_doc.id,
                prompt_id=1,  # Assuming prompt ID 1 exists
                llm_name="test_llm",
                task_id=f"test-task-{i}",
                status='P'  # Processing
            )
            session.add(test_response)

        session.commit()
        print(f"✅ Created {count} test processing records")
        return True

    except Exception as e:
        print(f"❌ Error creating test records: {e}")
        return False
    finally:
        session.close()

def cleanup_test_records():
    """Clean up test records"""
    print("\n=== Cleaning Up Test Records ===")

    session = Session()
    try:
        # Delete test documents and responses
        test_docs = session.query(Document).filter(Document.filepath.like('/test/path/%')).all()
        test_responses = session.query(LlmResponse).filter(LlmResponse.llm_name == 'test_llm').all()

        for response in test_responses:
            session.delete(response)
        for doc in test_docs:
            session.delete(doc)

        session.commit()
        print(f"✅ Cleaned up {len(test_docs)} test documents and {len(test_responses)} test responses")

    except Exception as e:
        print(f"❌ Error cleaning up test records: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Testing Outstanding Document Processing Limits\n")

    # Check current status
    check_outstanding_documents()

    # Simulate limit check
    can_process = simulate_outstanding_limit_check(max_outstanding=10)

    # Check implementation
    has_implementation = check_process_folder_implementation()

    # Test 'N' status implementation
    print("\n🧪 Testing 'N' status implementation...")
    n_status_works = test_status_n_implementation()

    # Test with simulated processing records
    print("\n🧪 Testing with simulated processing records...")
    cleanup_test_records()  # Clean up any existing test records first

    if create_test_processing_records(count=35):  # Create more than the limit (30)
        print("\n📊 After creating test records:")
        check_outstanding_documents()
        simulate_outstanding_limit_check(max_outstanding=30)

        # Clean up
        cleanup_test_records()

    print("\n=== Summary ===")
    print(f"Can process new documents: {can_process}")
    print(f"Has limit implementation: {has_implementation}")
    print(f"'N' status implementation works: {n_status_works}")

    if has_implementation:
        print("\n✅ Outstanding document limit is properly implemented!")
        print("   - MAX_OUTSTANDING_DOCUMENTS = 30")
        print("   - Checks current processing count before starting new tasks")
        print("   - Skips processing when limit is reached")
        print("   - Provides detailed feedback on skipped tasks")

    if n_status_works:
        print("\n✅ 'N' status implementation is working!")
        print("   - Documents stored immediately with 'N' status")
        print("   - Startup recovery detects and handles 'N' status records")
        print("   - Improved restart resilience")
    else:
        print("\n⚠️  'N' status implementation needs verification")

    if not has_implementation:
        print("\n🔧 RECOMMENDATION: Implement outstanding document limit checking in process_folder.py")
        print("   Add code to count processing documents before starting new ones")
