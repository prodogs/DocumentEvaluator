#!/usr/bin/env python3
"""
Batch Configuration Snapshot Migration

This script adds the config_snapshot column to the batches table and migrates
existing batches to use the new configuration snapshot system.

The config_snapshot will contain:
- llm_configurations: All active LLM configurations at batch creation time
- prompts: All active prompts at batch creation time  
- folders: All folders included in the batch with their details
- documents: List of documents found in the folders at batch creation time
"""

import sys
import os
import json
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extras import RealDictCursor
from server.database import Session
from server.models import Batch, Folder, LlmConfiguration, Prompt, Document

# Database connection settings
DB_HOST = "tablemini.local"
DB_USER = "postgres"
DB_PASSWORD = "prodogs03"
DB_NAME = "doc_eval"

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursor_factory=RealDictCursor
    )

def add_config_snapshot_column():
    """Add config_snapshot column to batches table"""
    print("📋 Adding config_snapshot column to batches table...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'batches' AND column_name = 'config_snapshot'
        """)
        
        if cursor.fetchone():
            print("ℹ️  config_snapshot column already exists")
            return True
        
        # Add the column
        cursor.execute("""
            ALTER TABLE batches 
            ADD COLUMN config_snapshot JSONB
        """)
        
        conn.commit()
        print("✅ config_snapshot column added successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error adding config_snapshot column: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def create_config_snapshot_for_batch(batch_id: int, folder_ids: list = None) -> dict:
    """Create a configuration snapshot for a batch"""
    session = Session()
    try:
        # Get all active LLM configurations
        llm_configs = session.query(LlmConfiguration).filter_by(active=1).all()
        llm_configs_data = []
        for config in llm_configs:
            llm_configs_data.append({
                'id': config.id,
                'llm_name': config.llm_name,
                'base_url': config.base_url,
                'model_name': config.model_name,
                'api_key': config.api_key,
                'provider_type': config.provider_type,
                'port_no': config.port_no,
                'active': config.active
            })
        
        # Get all active prompts
        prompts = session.query(Prompt).filter_by(active=1).all()
        prompts_data = []
        for prompt in prompts:
            prompts_data.append({
                'id': prompt.id,
                'prompt_text': prompt.prompt_text,
                'description': prompt.description,
                'active': prompt.active
            })
        
        # Get folders data
        folders_data = []
        documents_data = []
        
        if folder_ids:
            folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
            for folder in folders:
                folder_data = {
                    'id': folder.id,
                    'folder_path': folder.folder_path,
                    'folder_name': folder.folder_name,
                    'active': folder.active,
                    'created_at': folder.created_at.isoformat() if folder.created_at else None
                }
                folders_data.append(folder_data)
                
                # Get documents for this folder that belong to this batch
                docs = session.query(Document).filter_by(
                    folder_id=folder.id,
                    batch_id=batch_id
                ).all()
                
                for doc in docs:
                    documents_data.append({
                        'id': doc.id,
                        'filepath': doc.filepath,
                        'filename': doc.filename,
                        'folder_id': doc.folder_id,
                        'batch_id': doc.batch_id,
                        'created_at': doc.created_at.isoformat() if doc.created_at else None,
                        'task_id': doc.task_id
                    })
        
        # Create the complete snapshot
        config_snapshot = {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'llm_configurations': llm_configs_data,
            'prompts': prompts_data,
            'folders': folders_data,
            'documents': documents_data,
            'summary': {
                'total_llm_configs': len(llm_configs_data),
                'total_prompts': len(prompts_data),
                'total_folders': len(folders_data),
                'total_documents': len(documents_data)
            }
        }
        
        return config_snapshot
        
    finally:
        session.close()

def migrate_existing_batches():
    """Migrate existing batches to use config snapshots"""
    print("🔄 Migrating existing batches to use config snapshots...")
    
    session = Session()
    try:
        # Get all batches that don't have config snapshots
        batches = session.query(Batch).filter(Batch.config_snapshot.is_(None)).all()
        
        print(f"Found {len(batches)} batches to migrate")
        
        migrated_count = 0
        failed_count = 0
        
        for batch in batches:
            try:
                print(f"  Migrating batch #{batch.batch_number}: {batch.batch_name}")
                
                # Create config snapshot
                config_snapshot = create_config_snapshot_for_batch(
                    batch.id, 
                    batch.folder_ids if batch.folder_ids else []
                )
                
                # Update the batch
                batch.config_snapshot = config_snapshot
                session.commit()
                
                migrated_count += 1
                print(f"    ✅ Migrated with {config_snapshot['summary']['total_documents']} documents")
                
            except Exception as e:
                print(f"    ❌ Failed to migrate batch {batch.id}: {e}")
                failed_count += 1
                session.rollback()
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Successfully migrated: {migrated_count}")
        print(f"   ❌ Failed: {failed_count}")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"❌ Error during batch migration: {e}")
        return False
    finally:
        session.close()

def verify_migration():
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    session = Session()
    try:
        # Check that all batches have config snapshots
        total_batches = session.query(Batch).count()
        batches_with_snapshots = session.query(Batch).filter(Batch.config_snapshot.isnot(None)).count()
        
        print(f"   Total batches: {total_batches}")
        print(f"   Batches with config snapshots: {batches_with_snapshots}")
        
        if total_batches == batches_with_snapshots:
            print("✅ All batches have config snapshots")
            return True
        else:
            print(f"❌ {total_batches - batches_with_snapshots} batches missing config snapshots")
            return False
            
    finally:
        session.close()

def main():
    """Main migration function"""
    print("🚀 Batch Configuration Snapshot Migration")
    print("=" * 50)
    
    # Step 1: Add the column
    if not add_config_snapshot_column():
        print("❌ Failed to add config_snapshot column")
        return False
    
    # Step 2: Migrate existing batches
    if not migrate_existing_batches():
        print("❌ Failed to migrate existing batches")
        return False
    
    # Step 3: Verify migration
    if not verify_migration():
        print("❌ Migration verification failed")
        return False
    
    print("\n🎉 Migration completed successfully!")
    print("   ✅ config_snapshot column added")
    print("   ✅ Existing batches migrated")
    print("   ✅ All batches now have configuration snapshots")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
