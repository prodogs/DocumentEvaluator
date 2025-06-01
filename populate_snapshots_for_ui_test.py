#!/usr/bin/env python3
"""
Populate the snapshots table with records for existing snapshot files
This will allow us to test the UI functionality
"""

import sys
import os
from datetime import datetime
import json

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_engine, Session
from models import Snapshot

def get_snapshot_files():
    """Get all snapshot files from the snapshots directory"""
    snapshots_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
    
    if not os.path.exists(snapshots_dir):
        print(f"❌ Snapshots directory not found: {snapshots_dir}")
        return []
    
    snapshot_files = []
    for filename in os.listdir(snapshots_dir):
        if filename.endswith('.sql.gz'):
            file_path = os.path.join(snapshots_dir, filename)
            file_size = os.path.getsize(file_path)
            file_stat = os.stat(file_path)
            created_at = datetime.fromtimestamp(file_stat.st_ctime)
            
            snapshot_files.append({
                'filename': filename,
                'file_path': file_path,
                'file_size': file_size,
                'created_at': created_at
            })
    
    return sorted(snapshot_files, key=lambda x: x['created_at'], reverse=True)

def create_snapshot_records():
    """Create database records for existing snapshot files"""
    try:
        session = Session()
        
        # Get existing snapshot files
        snapshot_files = get_snapshot_files()
        
        if not snapshot_files:
            print("📁 No snapshot files found in snapshots directory")
            return False
        
        print(f"📸 Found {len(snapshot_files)} snapshot files")
        
        # Check which files already have database records
        existing_paths = {s.file_path for s in session.query(Snapshot).all()}
        
        new_records = 0
        for file_info in snapshot_files:
            if file_info['file_path'] not in existing_paths:
                # Extract name from filename (remove timestamp and extension)
                filename = file_info['filename']
                if '_' in filename:
                    name_part = filename.split('_')[0]
                else:
                    name_part = filename.replace('.sql.gz', '')
                
                # Create mock record counts (since we can't easily get real counts from the file)
                record_counts = {
                    'llm_responses': 1250,
                    'documents': 89,
                    'docs': 45,
                    'connections': 3,
                    'models': 12,
                    'providers': 4,
                    'batches': 8,
                    'snapshots': len(snapshot_files)
                }
                
                # Create snapshot record
                snapshot = Snapshot(
                    name=name_part,
                    description=f"Snapshot created from file: {filename}",
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    database_name='doc_eval',
                    snapshot_type='full',
                    compression='gzip',
                    created_at=file_info['created_at'],
                    created_by='file_import',
                    tables_included=['llm_responses', 'documents', 'docs', 'connections', 'models', 'providers', 'batches', 'snapshots'],
                    record_counts=record_counts,
                    database_version='PostgreSQL 17.2',
                    application_version='1.0.0',
                    status='completed'
                )
                
                session.add(snapshot)
                new_records += 1
                
                print(f"  ✅ Added record for: {filename} ({file_info['file_size'] / 1024 / 1024:.1f} MB)")
        
        if new_records > 0:
            session.commit()
            print(f"\n🎉 Created {new_records} new snapshot records in database")
        else:
            print("\n📋 All snapshot files already have database records")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating snapshot records: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def verify_snapshots():
    """Verify the snapshots in the database"""
    try:
        session = Session()
        
        snapshots = session.query(Snapshot).order_by(Snapshot.created_at.desc()).all()
        
        print(f"\n📊 Database contains {len(snapshots)} snapshot records:")
        print("=" * 80)
        
        for i, snapshot in enumerate(snapshots, 1):
            file_exists = "✅" if os.path.exists(snapshot.file_path) else "❌"
            print(f"{i}. {snapshot.name}")
            print(f"   📁 File: {os.path.basename(snapshot.file_path)} {file_exists}")
            print(f"   📊 Size: {snapshot.file_size / 1024 / 1024:.1f} MB")
            print(f"   📅 Created: {snapshot.created_at}")
            print(f"   🔄 Status: {snapshot.status}")
            if snapshot.record_counts:
                total_records = sum(snapshot.record_counts.values())
                print(f"   📈 Records: {total_records:,} total")
            print()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying snapshots: {e}")
        return False

def main():
    """Main function"""
    print("📸 DocumentEvaluator - Populate Snapshots for UI Testing")
    print("=" * 70)
    
    # Create snapshot records
    success = create_snapshot_records()
    
    if success:
        # Verify the results
        verify_snapshots()
        
        print("🎯 Next Steps:")
        print("1. Start the Flask server: cd server && python app.py")
        print("2. Refresh the maintenance tab in your browser")
        print("3. You should now see snapshots with Load/Edit/Delete buttons")
        print("4. Test the snapshot functionality!")
        
        print(f"\n🌐 Frontend: http://localhost:5173")
        print("📋 Navigate to: Maintenance tab → Database Snapshots section")
    else:
        print("\n❌ Failed to populate snapshot records")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
