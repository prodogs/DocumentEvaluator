#!/usr/bin/env python3
"""
Create a stuck batch for testing recovery functionality
"""

from database import Session
from models import Batch
from datetime import datetime, timedelta
import sys

def create_stuck_batch():
    """Create a batch stuck in ANALYZING status"""
    session = Session()
    
    try:
        # Find a batch to make stuck
        batch = session.query(Batch).filter(
            Batch.status.in_(['COMPLETED', 'STAGED', 'SAVED'])
        ).first()
        
        if not batch:
            print("No suitable batch found to make stuck")
            return False
            
        batch_id = batch.id
        batch_name = batch.batch_name
        previous_status = batch.status
        
        # Set batch to ANALYZING with old timestamp
        batch.status = 'ANALYZING'
        batch.started_at = datetime.now() - timedelta(hours=2)  # Started 2 hours ago
        
        session.commit()
        session.close()
        
        print(f"✓ Set batch {batch_id} '{batch_name}' to ANALYZING status")
        print(f"  Previous status: {previous_status}")
        print(f"  Started at: {batch.started_at}")
        print("\nThis batch should be detected and recovered on next startup")
        
        return True
        
    except Exception as e:
        print(f"Error creating stuck batch: {e}")
        session.rollback()
        session.close()
        return False


def create_stuck_staging_batch():
    """Create a batch stuck in STAGING status"""
    session = Session()
    
    try:
        # Find another batch to make stuck in staging
        batch = session.query(Batch).filter(
            Batch.status.in_(['COMPLETED', 'STAGED', 'SAVED'])
        ).offset(1).first()  # Get second batch
        
        if not batch:
            print("No suitable batch found for STAGING test")
            return False
            
        batch_id = batch.id
        batch_name = batch.batch_name
        previous_status = batch.status
        
        # Set batch to STAGING with old timestamp
        batch.status = 'STAGING'
        batch.started_at = datetime.now() - timedelta(hours=1)  # Started 1 hour ago
        
        session.commit()
        session.close()
        
        print(f"✓ Set batch {batch_id} '{batch_name}' to STAGING status")
        print(f"  Previous status: {previous_status}")
        print(f"  Started at: {batch.started_at}")
        print("\nThis batch should be detected and reset to SAVED on next startup")
        
        return True
        
    except Exception as e:
        print(f"Error creating stuck staging batch: {e}")
        session.rollback()
        session.close()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Creating stuck batches for recovery testing")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--staging":
        create_stuck_staging_batch()
    else:
        create_stuck_batch()
        print("\nTo also create a STAGING stuck batch, run with --staging")
    
    print("\nRestart the server to test recovery functionality")
    print("=" * 60)