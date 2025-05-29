#!/usr/bin/env python3
"""
Fix Stuck Tasks Script

This script identifies and fixes LLM responses that are stuck in processing state
without proper task IDs or that have been processing for too long.
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy.sql import func

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.database import Session
from server.models import LlmResponse, Document, Batch
from server.services.batch_service import batch_service

def fix_stuck_tasks():
    """Fix stuck LLM response tasks"""
    session = Session()
    try:
        print("🔍 Analyzing stuck tasks...")
        
        # Find processing responses without task IDs
        stuck_responses = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.task_id.is_(None)
        ).all()
        
        print(f"Found {len(stuck_responses)} stuck responses without task IDs")
        
        # Find processing responses that have been processing too long (over 1 hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        old_processing = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.started_processing_at < one_hour_ago
        ).all()
        
        print(f"Found {len(old_processing)} responses processing for over 1 hour")
        
        # Combine and deduplicate
        all_stuck = list(set(stuck_responses + old_processing))
        print(f"Total unique stuck responses: {len(all_stuck)}")
        
        if not all_stuck:
            print("✅ No stuck tasks found!")
            return
        
        # Ask for confirmation
        response = input(f"\n❓ Mark {len(all_stuck)} stuck responses as failed? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            return
        
        # Fix stuck responses
        fixed_count = 0
        batch_ids_to_update = set()
        
        for llm_response in all_stuck:
            try:
                # Mark as failed
                llm_response.status = 'F'
                llm_response.completed_processing_at = func.now()
                llm_response.error_message = 'Task was stuck and automatically marked as failed'
                
                # Calculate processing time if possible
                if llm_response.started_processing_at:
                    processing_time = datetime.now() - llm_response.started_processing_at
                    llm_response.response_time_ms = int(processing_time.total_seconds() * 1000)
                
                # Track which batches need updating
                if llm_response.document_id:
                    document = session.query(Document).filter_by(id=llm_response.document_id).first()
                    if document and document.batch_id:
                        batch_ids_to_update.add(document.batch_id)
                
                fixed_count += 1
                print(f"  ✅ Fixed response ID {llm_response.id}")
                
            except Exception as e:
                print(f"  ❌ Error fixing response ID {llm_response.id}: {e}")
        
        # Commit changes
        session.commit()
        print(f"\n✅ Fixed {fixed_count} stuck responses")
        
        # Update batch progress
        print(f"\n🔄 Updating {len(batch_ids_to_update)} affected batches...")
        for batch_id in batch_ids_to_update:
            try:
                batch_service.update_batch_progress(batch_id)
                print(f"  ✅ Updated batch {batch_id}")
            except Exception as e:
                print(f"  ❌ Error updating batch {batch_id}: {e}")
        
        print("\n🎉 Stuck task recovery completed!")
        
        # Show current status
        print("\n📊 Current Status:")
        processing_count = session.query(LlmResponse).filter_by(status='P').count()
        failed_count = session.query(LlmResponse).filter_by(status='F').count()
        success_count = session.query(LlmResponse).filter_by(status='S').count()
        
        print(f"  Processing: {processing_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Successful: {success_count}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error during recovery: {e}")
        raise
    finally:
        session.close()

def show_stuck_task_details():
    """Show detailed information about stuck tasks"""
    session = Session()
    try:
        print("🔍 Stuck Task Analysis")
        print("=" * 50)
        
        # Processing responses without task IDs
        stuck_no_task = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.task_id.is_(None)
        ).all()
        
        print(f"\n📋 Responses without task IDs: {len(stuck_no_task)}")
        for resp in stuck_no_task:
            document = session.query(Document).filter_by(id=resp.document_id).first()
            batch_info = ""
            if document and document.batch_id:
                batch = session.query(Batch).filter_by(id=document.batch_id).first()
                if batch:
                    batch_info = f" (Batch #{batch.batch_number}: {batch.batch_name})"
            
            print(f"  ID {resp.id}: {document.filename if document else 'Unknown'}{batch_info}")
        
        # Processing responses with task IDs but old
        one_hour_ago = datetime.now() - timedelta(hours=1)
        old_with_task = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.task_id.isnot(None),
            LlmResponse.started_processing_at < one_hour_ago
        ).all()
        
        print(f"\n⏰ Old processing responses (>1 hour): {len(old_with_task)}")
        for resp in old_with_task:
            if resp.started_processing_at:
                elapsed = datetime.now() - resp.started_processing_at
                print(f"  ID {resp.id}: Task {resp.task_id} - {elapsed.total_seconds()/3600:.1f} hours")
        
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--details":
        show_stuck_task_details()
    else:
        fix_stuck_tasks()
