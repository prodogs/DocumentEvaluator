#!/usr/bin/env python3
"""
Fix batches that are marked as COMPLETED but have no LLM responses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Batch, LlmResponse, Document
from sqlalchemy import func
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_problematic_batches():
    """Find batches marked as COMPLETED but with no LLM responses"""
    
    session = Session()
    
    try:
        print("🔍 FINDING PROBLEMATIC BATCHES")
        print("=" * 50)
        
        # Find completed batches
        completed_batches = session.query(Batch).filter(Batch.status == 'COMPLETED').all()
        
        problematic_batches = []
        
        for batch in completed_batches:
            # Count LLM responses for this batch
            llm_response_count = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id
            ).count()
            
            if llm_response_count == 0:
                problematic_batches.append(batch)
                print(f"❌ Batch #{batch.batch_number} (ID: {batch.id}) - '{batch.batch_name}'")
                print(f"   Status: {batch.status} (COMPLETED)")
                print(f"   LLM Responses: {llm_response_count}")
                
                # Check if it has documents
                doc_count = session.query(Document).filter(Document.batch_id == batch.id).count()
                print(f"   Documents: {doc_count}")
                
                # Check config snapshot
                if batch.config_snapshot:
                    config = batch.config_snapshot
                    connections = config.get('connections', [])
                    prompts = config.get('prompts', [])
                    print(f"   Config: {len(connections)} connections, {len(prompts)} prompts")
                else:
                    print(f"   Config: No config snapshot")
                
                print()
        
        return problematic_batches
        
    finally:
        session.close()

def fix_problematic_batch(batch_id, action='reset_status'):
    """Fix a problematic batch"""
    
    session = Session()
    
    try:
        batch = session.query(Batch).filter_by(id=batch_id).first()
        if not batch:
            print(f"❌ Batch {batch_id} not found")
            return False
        
        print(f"🔧 FIXING Batch #{batch.batch_number} (ID: {batch_id})")
        
        if action == 'reset_status':
            # Reset status to allow re-staging
            old_status = batch.status
            batch.status = 'SAVED'  # Reset to initial status
            batch.completed_at = None
            
            print(f"   Status changed: {old_status} → {batch.status}")
            print(f"   Completed timestamp cleared")
            
        elif action == 'create_responses':
            # Try to create LLM responses if config exists
            if not batch.config_snapshot:
                print(f"   ❌ Cannot create responses - no config snapshot")
                return False
            
            config = batch.config_snapshot
            connections = config.get('connections', [])
            prompts = config.get('prompts', [])
            
            if not connections or not prompts:
                print(f"   ❌ Cannot create responses - missing connections or prompts")
                return False
            
            # Get documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            
            if not documents:
                print(f"   ❌ Cannot create responses - no documents in batch")
                return False
            
            responses_created = 0
            
            for document in documents:
                for prompt in prompts:
                    for connection in connections:
                        # Check if response already exists
                        existing = session.query(LlmResponse).filter(
                            LlmResponse.document_id == document.id,
                            LlmResponse.prompt_id == prompt['id'],
                            LlmResponse.connection_id == connection['id']
                        ).first()
                        
                        if not existing:
                            llm_response = LlmResponse(
                                document_id=document.id,
                                prompt_id=prompt['id'],
                                connection_id=connection['id'],
                                status='N',  # Not started
                                task_id=None
                            )
                            session.add(llm_response)
                            responses_created += 1
            
            print(f"   Created {responses_created} LLM response records")
            
            # Reset batch status to allow processing
            batch.status = 'STAGED'
            batch.completed_at = None
            
        session.commit()
        print(f"   ✅ Batch fixed successfully")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"   ❌ Error fixing batch: {e}")
        return False
    finally:
        session.close()

def main():
    """Main function"""
    
    print("🚀 BATCH REPAIR TOOL")
    print("=" * 50)
    
    # Find problematic batches
    problematic_batches = find_problematic_batches()
    
    if not problematic_batches:
        print("✅ No problematic batches found!")
        return
    
    print(f"\n📋 Found {len(problematic_batches)} problematic batch(es)")
    print("\nOptions:")
    print("1. Reset status to SAVED (allows re-staging)")
    print("2. Create missing LLM responses and set to STAGED")
    print("3. Exit without changes")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '3':
            print("Exiting without changes")
            return
        
        action = 'reset_status' if choice == '1' else 'create_responses' if choice == '2' else None
        
        if not action:
            print("Invalid choice")
            return
        
        print(f"\n🔧 Applying fix to {len(problematic_batches)} batch(es)...")
        
        fixed_count = 0
        for batch in problematic_batches:
            if fix_problematic_batch(batch.id, action):
                fixed_count += 1
        
        print(f"\n✅ Fixed {fixed_count}/{len(problematic_batches)} batches")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
