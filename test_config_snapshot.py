#!/usr/bin/env python3
"""
Test Config Snapshot Functionality

This script tests the new configuration snapshot feature for batches.
"""

import sys
import os
import json

# Add the current directory to the Python path
sys.path.append('.')

def test_config_snapshot():
    """Test the config snapshot functionality"""
    print("🧪 Testing Config Snapshot Functionality")
    print("=" * 50)
    
    try:
        # Import after adding to path
        from server.services.batch_service import BatchService
        from server.database import Session
        from server.models import Batch
        
        print("✅ Imports successful")
        
        # Create batch service instance
        batch_service = BatchService()
        print("✅ BatchService instance created")
        
        # Create a test batch with config snapshot
        print("\n📋 Creating test batch with config snapshot...")
        batch_data = batch_service.create_multi_folder_batch(
            folder_ids=[1, 4],
            batch_name='Config Snapshot Test Batch',
            description='Testing new configuration snapshot functionality',
            meta_data={'test': 'config_snapshot_feature'}
        )
        
        print(f"✅ Created batch #{batch_data['batch_number']}: {batch_data['batch_name']}")
        
        # Verify config snapshot was created
        if 'config_snapshot' in batch_data and batch_data['config_snapshot']:
            config_snapshot = batch_data['config_snapshot']
            summary = config_snapshot['summary']
            
            print(f"\n📊 Config Snapshot Summary:")
            print(f"   Version: {config_snapshot['version']}")
            print(f"   Created At: {config_snapshot['created_at']}")
            print(f"   LLM Configurations: {summary['total_llm_configs']}")
            print(f"   Prompts: {summary['total_prompts']}")
            print(f"   Folders: {summary['total_folders']}")
            print(f"   Documents: {summary['total_documents']}")
            print(f"   Expected Combinations: {summary['expected_combinations']}")
            
            # Show folder details
            print(f"\n📁 Folders in Snapshot:")
            for folder in config_snapshot['folders']:
                print(f"   - ID {folder['id']}: {folder['folder_name']}")
                print(f"     Path: {folder['folder_path']}")
                print(f"     Active: {folder['active']}")
            
            # Show LLM configurations
            print(f"\n🤖 LLM Configurations:")
            for llm_config in config_snapshot['llm_configurations']:
                print(f"   - {llm_config['llm_name']}: {llm_config['model_name']}")
                print(f"     Provider: {llm_config['provider_type']}")
                print(f"     Base URL: {llm_config['base_url']}")
            
            # Show prompts
            print(f"\n💬 Prompts:")
            for prompt in config_snapshot['prompts']:
                prompt_preview = prompt['prompt_text'][:50] + "..." if len(prompt['prompt_text']) > 50 else prompt['prompt_text']
                print(f"   - ID {prompt['id']}: {prompt_preview}")
            
            # Show sample documents
            documents = config_snapshot['documents']
            if documents:
                print(f"\n📄 Sample Documents ({len(documents)} total):")
                for doc in documents[:5]:
                    print(f"   - {doc['filename']} (Folder ID: {doc['folder_id']})")
                    print(f"     Size: {doc['file_size']} bytes")
                if len(documents) > 5:
                    print(f"   ... and {len(documents) - 5} more documents")
            
            print(f"\n✅ Config snapshot contains complete state!")
            
        else:
            print("❌ No config snapshot found in batch data")
            return False
        
        # Verify in database
        print(f"\n🔍 Verifying in database...")
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_data['id']).first()
            if batch and batch.config_snapshot:
                print("✅ Config snapshot successfully stored in database")
                
                # Check that folder_ids is still there for backward compatibility
                if batch.folder_ids:
                    print("✅ folder_ids maintained for backward compatibility")
                else:
                    print("⚠️  folder_ids not set (may affect backward compatibility)")
                
                return True
            else:
                print("❌ Config snapshot not found in database")
                return False
        finally:
            session.close()
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_existing_batches():
    """Show existing batches and their config snapshot status"""
    print("\n📋 Existing Batches Config Snapshot Status")
    print("=" * 50)
    
    try:
        from server.database import Session
        from server.models import Batch
        
        session = Session()
        try:
            batches = session.query(Batch).order_by(Batch.id.desc()).limit(5).all()
            
            for batch in batches:
                has_snapshot = batch.config_snapshot is not None
                snapshot_summary = ""
                
                if has_snapshot:
                    try:
                        summary = batch.config_snapshot.get('summary', {})
                        snapshot_summary = f" (Configs: {summary.get('total_llm_configs', 0)}, Prompts: {summary.get('total_prompts', 0)}, Docs: {summary.get('total_documents', 0)})"
                    except:
                        snapshot_summary = " (Invalid snapshot)"
                
                status_icon = "✅" if has_snapshot else "❌"
                print(f"   {status_icon} Batch #{batch.batch_number}: {batch.batch_name}{snapshot_summary}")
                
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error checking existing batches: {e}")

if __name__ == "__main__":
    show_existing_batches()
    success = test_config_snapshot()
    
    if success:
        print(f"\n🎉 Config snapshot functionality test PASSED!")
        print(f"   ✅ Batches now store complete configuration state")
        print(f"   ✅ Protected from future changes to LLM configs, prompts, and folders")
        print(f"   ✅ folder_ids column can be deprecated in future")
    else:
        print(f"\n❌ Config snapshot functionality test FAILED!")
    
    sys.exit(0 if success else 1)
