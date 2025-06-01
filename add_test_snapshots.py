#!/usr/bin/env python3
"""
Add a few test snapshot records to test the UI functionality
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add the server directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_engine, Session
from models import Snapshot

def add_test_snapshots():
    """Add test snapshot records"""
    try:
        session = Session()
        
        # Clear existing snapshots first
        session.query(Snapshot).delete()
        session.commit()
        
        print("🧹 Cleared existing snapshot records")
        
        # Create test snapshots with reasonable file sizes
        test_snapshots = [
            {
                'name': 'production_backup',
                'description': 'Production database backup before major update',
                'file_path': '/Users/frankfilippis/AI/Github/DocumentEvaluator/snapshots/production_backup_20250601_120000.sql.gz',
                'file_size': 156789123,  # ~150 MB
                'created_at': datetime.now() - timedelta(days=2),
                'record_counts': {
                    'llm_responses': 2450,
                    'documents': 156,
                    'docs': 89,
                    'connections': 5,
                    'models': 15,
                    'providers': 6,
                    'batches': 12,
                    'snapshots': 1
                }
            },
            {
                'name': 'weekly_backup',
                'description': 'Weekly automated backup',
                'file_path': '/Users/frankfilippis/AI/Github/DocumentEvaluator/snapshots/weekly_backup_20250601_140000.sql.gz',
                'file_size': 89456789,  # ~85 MB
                'created_at': datetime.now() - timedelta(days=1),
                'record_counts': {
                    'llm_responses': 1890,
                    'documents': 123,
                    'docs': 67,
                    'connections': 4,
                    'models': 12,
                    'providers': 5,
                    'batches': 9,
                    'snapshots': 2
                }
            },
            {
                'name': 'test_snapshot',
                'description': 'Test snapshot for development',
                'file_path': '/Users/frankfilippis/AI/Github/DocumentEvaluator/snapshots/test_snapshot_20250601_150000.sql.gz',
                'file_size': 45123456,  # ~43 MB
                'created_at': datetime.now() - timedelta(hours=2),
                'record_counts': {
                    'llm_responses': 567,
                    'documents': 45,
                    'docs': 23,
                    'connections': 2,
                    'models': 8,
                    'providers': 3,
                    'batches': 4,
                    'snapshots': 3
                }
            }
        ]
        
        for i, snapshot_data in enumerate(test_snapshots, 1):
            snapshot = Snapshot(
                name=snapshot_data['name'],
                description=snapshot_data['description'],
                file_path=snapshot_data['file_path'],
                file_size=snapshot_data['file_size'],
                database_name='doc_eval',
                snapshot_type='full',
                compression='gzip',
                created_at=snapshot_data['created_at'],
                created_by='test_script',
                tables_included=['llm_responses', 'documents', 'docs', 'connections', 'models', 'providers', 'batches', 'snapshots'],
                record_counts=snapshot_data['record_counts'],
                database_version='PostgreSQL 17.2',
                application_version='1.0.0',
                status='completed'
            )
            
            session.add(snapshot)
            print(f"  ✅ Added: {snapshot_data['name']} ({snapshot_data['file_size'] / 1024 / 1024:.1f} MB)")
        
        session.commit()
        print(f"\n🎉 Successfully added {len(test_snapshots)} test snapshots")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding test snapshots: {e}")
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
            print(f"{i}. {snapshot.name}")
            print(f"   📁 File: {os.path.basename(snapshot.file_path)}")
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
    print("📸 DocumentEvaluator - Add Test Snapshots for UI")
    print("=" * 60)
    
    # Add test snapshots
    success = add_test_snapshots()
    
    if success:
        # Verify the results
        verify_snapshots()
        
        print("🎯 Next Steps:")
        print("1. Start the Flask server if not running:")
        print("   cd server && python app.py")
        print("2. Refresh the maintenance tab in your browser")
        print("3. You should now see 3 test snapshots with Load/Edit/Delete buttons")
        print("4. Test the snapshot functionality!")
        
        print(f"\n🌐 Frontend: http://localhost:5173")
        print("📋 Navigate to: Maintenance tab → Database Snapshots section")
    else:
        print("\n❌ Failed to add test snapshots")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
