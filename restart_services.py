#!/usr/bin/env python3
"""
Service Restart Script

This script restarts the dynamic processing queue and status polling service
to ensure document processing continues properly.
"""

import sys
import os

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

def restart_services():
    """Restart both the dynamic queue and status polling services"""
    
    print("🔄 Service Restart Script")
    print("=" * 40)
    
    try:
        # Import services
        from server.services.dynamic_processing_queue import dynamic_queue
        from server.api.status_polling import polling_service
        
        print("\n📊 Checking current service status...")
        
        # Check dynamic queue status
        queue_running = dynamic_queue.queue_thread and dynamic_queue.queue_thread.is_alive()
        print(f"   Dynamic Queue: {'✅ Running' if queue_running else '❌ Not Running'}")
        
        # Check polling service status
        polling_running = polling_service.polling_thread and polling_service.polling_thread.is_alive()
        print(f"   Status Polling: {'✅ Running' if polling_running else '❌ Not Running'}")
        
        # Get queue status
        try:
            queue_status = dynamic_queue.get_queue_status()
            print(f"\n📋 Queue Status:")
            print(f"   Current Outstanding: {queue_status['current_outstanding']}")
            print(f"   Max Outstanding: {queue_status['max_outstanding']}")
            print(f"   Available Slots: {queue_status['available_slots']}")
            print(f"   Waiting Documents: {queue_status['waiting_documents']}")
        except Exception as e:
            print(f"   Error getting queue status: {e}")
        
        # Restart services if needed
        print(f"\n🔧 Restarting services...")
        
        # Stop and restart dynamic queue
        if queue_running:
            print("   Stopping dynamic queue...")
            dynamic_queue.stop_queue_processing()
        
        print("   Starting dynamic queue...")
        dynamic_queue.start_queue_processing()
        print("   ✅ Dynamic queue started")
        
        # Stop and restart polling service
        if polling_running:
            print("   Stopping status polling...")
            polling_service.stop_polling_service()
        
        print("   Starting status polling...")
        polling_service.start_polling()
        print("   ✅ Status polling started")
        
        # Verify services are running
        print(f"\n✅ Service restart completed!")
        
        # Final status check
        queue_running = dynamic_queue.queue_thread and dynamic_queue.queue_thread.is_alive()
        polling_running = polling_service.polling_thread and polling_service.polling_thread.is_alive()
        
        print(f"\n📊 Final Status:")
        print(f"   Dynamic Queue: {'✅ Running' if queue_running else '❌ Failed to start'}")
        print(f"   Status Polling: {'✅ Running' if polling_running else '❌ Failed to start'}")
        
        if queue_running and polling_running:
            print(f"\n🎉 All services are now running properly!")
            print(f"   Documents should resume processing automatically.")
        else:
            print(f"\n⚠️  Some services failed to start. Check logs for details.")
            
        return queue_running and polling_running
        
    except Exception as e:
        print(f"\n❌ Error restarting services: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = restart_services()
    sys.exit(0 if success else 1)
