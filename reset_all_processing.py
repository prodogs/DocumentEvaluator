#!/usr/bin/env python3
"""
Reset ALL Processing Items

Reset all items in "Processing" status to clear the queue
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import LlmResponse
from datetime import datetime

def reset_all_processing():
    """Reset ALL processing items"""
    
    print("🔧 Resetting ALL Processing Items")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Find ALL items in processing status
        processing_items = session.query(LlmResponse).filter(
            LlmResponse.status == 'P'
        ).all()
        
        print(f"📊 Found {len(processing_items)} items in processing status")
        
        if not processing_items:
            print("✅ No processing items found!")
            return True
        
        print("\n🔄 Resetting all processing items:")
        
        reset_count = 0
        
        for item in processing_items:
            print(f"   Response ID {item.id}: {item.status} -> N")
            
            # Reset to "Not Started" status
            item.status = 'N'
            item.started_processing_at = None
            item.task_id = None
            item.updated_at = datetime.now()
            
            reset_count += 1
        
        # Commit changes
        session.commit()
        
        print(f"\n✅ Successfully reset {reset_count} processing items")
        print(f"💡 All 30 slots are now available for processing")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        session.close()
        return False

def check_final_status():
    """Check final processing status"""
    
    print(f"\n📊 Final Processing Status")
    print("=" * 30)
    
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
        total_count = 0
        
        for status, count in status_counts:
            status_name = {
                'R': 'Ready',
                'N': 'Not Started', 
                'P': 'Processing',
                'S': 'Success',
                'F': 'Failed'
            }.get(status, status)
            
            print(f"   {status_name} ({status}): {count}")
            total_count += count
            
            if status == 'P':
                processing_count = count
            elif status in ['N', 'R']:
                ready_count += count
        
        print(f"   Total: {total_count}")
        
        print(f"\n🎯 Processing Queue Status:")
        print(f"   Currently processing: {processing_count}/30")
        print(f"   Available slots: {30 - processing_count}")
        print(f"   Ready to process: {ready_count}")
        
        if processing_count == 0 and ready_count > 0:
            print(f"   🚀 ALL SLOTS AVAILABLE - Processing should start immediately!")
            print(f"   💡 Expected: All 30 slots will be utilized within seconds")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 Reset ALL Processing Items")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    print("⚠️  This will reset ALL items in 'Processing' status")
    print("   to 'Not Started' to clear the queue blockage")
    print()
    
    # Reset all processing items
    reset_ok = reset_all_processing()
    
    if reset_ok:
        # Check final status
        status_ok = check_final_status()
        
        if status_ok:
            print(f"\n🎉 QUEUE CLEARED!")
            print(f"✅ All 30 processing slots are now available")
            print(f"🔄 The dynamic processing queue should immediately")
            print(f"   start utilizing all available slots")
            print(f"💡 Monitor application logs to see 30/30 utilization")
        else:
            print(f"\n⚠️  Reset completed but status check failed")
    else:
        print(f"\n❌ Reset failed")

if __name__ == "__main__":
    main()
