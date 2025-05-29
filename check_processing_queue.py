#!/usr/bin/env python3
"""
Check Processing Queue Status

Analyze why only 2 of 30 slots are being used
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import LlmResponse, Document
from sqlalchemy import func

def check_processing_status():
    """Check current processing status"""
    
    print("🔍 Processing Queue Analysis")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Check LLM response statuses
        status_counts = session.query(
            LlmResponse.status,
            func.count(LlmResponse.id).label('count')
        ).group_by(LlmResponse.status).all()
        
        print("📊 LLM Response Status Breakdown:")
        total_responses = 0
        processing_count = 0
        
        for status, count in status_counts:
            status_name = {
                'R': 'Ready',
                'N': 'Not Started', 
                'P': 'Processing',
                'S': 'Success',
                'F': 'Failed'
            }.get(status, status)
            
            print(f"   {status_name} ({status}): {count}")
            total_responses += count
            
            if status == 'P':
                processing_count = count
        
        print(f"   Total: {total_responses}")
        print()
        
        # Check processing details
        print(f"🔄 Processing Details:")
        print(f"   Currently processing: {processing_count}/30 slots")
        print(f"   Available slots: {30 - processing_count}")
        
        # Check documents ready for processing
        ready_responses = session.query(LlmResponse).filter(
            LlmResponse.status.in_(['N', 'R'])
        ).count()
        
        print(f"   Ready to process: {ready_responses}")
        
        # Show currently processing items
        if processing_count > 0:
            print(f"\n🔄 Currently Processing:")
            processing_items = session.query(LlmResponse).filter(
                LlmResponse.status == 'P'
            ).limit(10).all()
            
            for item in processing_items:
                doc = session.query(Document).filter(Document.id == item.document_id).first()
                doc_name = doc.filename if doc else "Unknown"
                print(f"   Response ID {item.id}: {doc_name}")
                print(f"     Task ID: {item.task_id}")
                print(f"     Started: {item.started_processing_at}")
                print()
        
        # Check for stuck items
        print(f"\n⏰ Checking for Stuck Items:")
        from datetime import datetime, timedelta
        
        # Items processing for more than 10 minutes might be stuck
        stuck_threshold = datetime.now() - timedelta(minutes=10)
        
        stuck_items = session.query(LlmResponse).filter(
            LlmResponse.status == 'P',
            LlmResponse.started_processing_at < stuck_threshold
        ).all()
        
        if stuck_items:
            print(f"   ⚠️  Found {len(stuck_items)} potentially stuck items:")
            for item in stuck_items:
                doc = session.query(Document).filter(Document.id == item.document_id).first()
                doc_name = doc.filename if doc else "Unknown"
                print(f"     Response ID {item.id}: {doc_name}")
                print(f"       Started: {item.started_processing_at}")
                print(f"       Task ID: {item.task_id}")
        else:
            print(f"   ✅ No stuck items found")
        
        session.close()
        return processing_count, ready_responses
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return 0, 0

def check_queue_configuration():
    """Check the processing queue configuration"""
    
    print(f"\n⚙️  Queue Configuration Check")
    print("=" * 35)
    
    try:
        # Check the configuration in the process_folder file
        with open('/Users/frankfilippis/GitHub/DocumentEvaluator/server/api/process_folder.py', 'r') as f:
            content = f.read()
            
        # Look for MAX_OUTSTANDING_DOCUMENTS
        if 'MAX_OUTSTANDING_DOCUMENTS' in content:
            lines = content.split('\n')
            for line in lines:
                if 'MAX_OUTSTANDING_DOCUMENTS' in line and '=' in line:
                    print(f"   Found: {line.strip()}")
        
        # Check if dynamic processing queue is running
        print(f"\n🔄 Dynamic Processing Queue:")
        print(f"   Should be running and monitoring for ready tasks")
        print(f"   Should automatically start processing when slots are available")
        
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")

def suggest_solutions(processing_count, ready_responses):
    """Suggest solutions based on the analysis"""
    
    print(f"\n💡 Analysis & Recommendations:")
    print("=" * 35)
    
    if processing_count == 0 and ready_responses > 0:
        print(f"🔴 Issue: No items processing but {ready_responses} items ready")
        print(f"   Possible causes:")
        print(f"   - Dynamic processing queue not running")
        print(f"   - Queue not picking up ready items")
        print(f"   - Service connectivity issues")
        print(f"   Solution: Restart the application or check queue service")
        
    elif processing_count < 10 and ready_responses > 0:
        print(f"🟡 Issue: Only {processing_count} items processing, {ready_responses} waiting")
        print(f"   Possible causes:")
        print(f"   - RAG service slow/overloaded")
        print(f"   - Network timeouts")
        print(f"   - Queue not aggressive enough")
        print(f"   Solution: Check RAG service performance")
        
    elif processing_count > 0 and ready_responses == 0:
        print(f"🟢 Status: {processing_count} items processing, none waiting")
        print(f"   This is normal - all available work is being processed")
        
    elif processing_count == 0 and ready_responses == 0:
        print(f"🔵 Status: No items to process")
        print(f"   All work may be complete or no new batches created")
        
    else:
        print(f"📊 Status: {processing_count} processing, {ready_responses} ready")
        print(f"   Queue appears to be working normally")

def main():
    """Main function"""
    
    print("🚀 Processing Queue Diagnostics")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Check processing status
    processing_count, ready_responses = check_processing_status()
    
    # Check configuration
    check_queue_configuration()
    
    # Provide recommendations
    suggest_solutions(processing_count, ready_responses)
    
    print(f"\n🔧 Quick Actions:")
    print(f"   1. Check application logs for queue activity")
    print(f"   2. Verify RAG service on port 7001 is responding")
    print(f"   3. Consider restarting application if queue is stuck")
    print(f"   4. Monitor processing progress over time")

if __name__ == "__main__":
    main()
