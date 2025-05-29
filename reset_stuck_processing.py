#!/usr/bin/env python3
"""
Reset Stuck Processing Items

Reset items that have been stuck in "Processing" status for too long
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import LlmResponse
from datetime import datetime, timedelta

def reset_stuck_processing():
    """Reset stuck processing items"""
    
    print("🔧 Resetting Stuck Processing Items")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Find items stuck in processing for more than 10 minutes
        stuck_threshold = datetime.now() - timedelta(minutes=10)
        
        stuck_items = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.started_processing_at < stuck_threshold
        ).all()
        
        print(f"📊 Found {len(stuck_items)} items stuck in processing")
        
        if not stuck_items:
            print("✅ No stuck items found!")
            return True
        
        print("\n🔄 Resetting stuck items:")
        
        reset_count = 0
        
        for item in stuck_items:
            print(f"   Response ID {item.id}:")
            print(f"     Started: {item.started_processing_at}")
            print(f"     Task ID: {item.task_id}")
            
            # Reset to "Not Started" status
            item.status = 'N'
            item.started_processing_at = None
            item.task_id = None
            item.updated_at = datetime.now()
            
            reset_count += 1
            print(f"     ✅ Reset to 'N' status")
        
        # Commit changes
        session.commit()
        
        print(f"\n✅ Successfully reset {reset_count} stuck items")
        print(f"💡 These items will now be available for processing")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        session.close()
        return False

def check_processing_status_after_reset():
    """Check processing status after reset"""
    
    print(f"\n📊 Processing Status After Reset")
    print("=" * 35)
    
    session = Session()
    
    try:
        from sqlalchemy import func
        
        # Check status counts
        status_counts = session.query(
            LlmResponse.status,
            func.count(LlmResponse.id).label('count')
        ).group_by(LlmResponse.status).all()
        
        processing_count = 0
        ready_count = 0
        
        for status, count in status_counts:
            status_name = {
                'R': 'Ready',
                'N': 'Not Started', 
                'P': 'Processing',
                'S': 'Success',
                'F': 'Failed'
            }.get(status, status)
            
            print(f"   {status_name} ({status}): {count}")
            
            if status == 'P':
                processing_count = count
            elif status in ['N', 'R']:
                ready_count += count
        
        print(f"\n🎯 Available Processing Slots:")
        print(f"   Currently processing: {processing_count}/30")
        print(f"   Available slots: {30 - processing_count}")
        print(f"   Ready to process: {ready_count}")
        
        if processing_count < 30 and ready_count > 0:
            print(f"   ✅ Processing can now resume!")
        elif processing_count == 0:
            print(f"   🚀 All slots available - processing should start immediately!")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 Stuck Processing Reset")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Reset stuck items
    reset_ok = reset_stuck_processing()
    
    if reset_ok:
        # Check status after reset
        status_ok = check_processing_status_after_reset()
        
        if status_ok:
            print(f"\n✅ Reset complete!")
            print(f"💡 The processing queue should now utilize all 30 slots")
            print(f"🔄 Monitor the application logs to see processing resume")
        else:
            print(f"\n⚠️  Reset completed but status check failed")
    else:
        print(f"\n❌ Reset failed")

if __name__ == "__main__":
    main()
