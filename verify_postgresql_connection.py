#!/usr/bin/env python3
"""
Verify PostgreSQL Connection and Show Current Data

This script will:
1. Connect to the exact same PostgreSQL instance as the application
2. Show the current batches in the database
3. Verify the connection details
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session, get_engine
from server.models import Batch
from sqlalchemy import text

def verify_connection():
    """Verify the PostgreSQL connection and show current data"""
    
    print("🔍 PostgreSQL Connection Verification")
    print("=" * 50)
    
    # Get engine info
    engine = get_engine()
    print(f"📍 Database URL: {engine.url}")
    print(f"🏠 Host: {engine.url.host}")
    print(f"🔌 Port: {engine.url.port}")
    print(f"🗄️  Database: {engine.url.database}")
    print(f"👤 User: {engine.url.username}")
    print()
    
    # Test connection
    try:
        session = Session()
        
        # Test basic connection
        result = session.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"📊 PostgreSQL Version: {version.split(',')[0]}")
        print()
        
        # Show current batches
        print("📋 Current Batches in PostgreSQL:")
        print("-" * 40)
        
        batches = session.query(Batch).order_by(Batch.batch_number.desc()).limit(10).all()
        
        if batches:
            for batch in batches:
                print(f"  Batch #{batch.batch_number}: {batch.batch_name}")
                print(f"    ID: {batch.id}")
                print(f"    Status: {batch.status}")
                print(f"    Created: {batch.created_at}")
                print(f"    Total Docs: {batch.total_documents}")
                print()
        else:
            print("  No batches found in database")
        
        # Show total count
        total_batches = session.query(Batch).count()
        print(f"📊 Total Batches in Database: {total_batches}")
        
        # Show most recent batch
        latest_batch = session.query(Batch).order_by(Batch.created_at.desc()).first()
        if latest_batch:
            print(f"🕐 Most Recent Batch: #{latest_batch.batch_number} - {latest_batch.batch_name}")
            print(f"   Created at: {latest_batch.created_at}")
        
        session.close()
        
        print()
        print("✅ Verification Complete!")
        print(f"💡 The application IS writing to PostgreSQL on {engine.url.host}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def show_connection_details():
    """Show exactly where to look in your PostgreSQL client"""
    
    print()
    print("🔧 PostgreSQL Client Connection Details:")
    print("=" * 50)
    print("Host: tablemini.local")
    print("Port: 5432")
    print("Database: doc_eval")
    print("Username: postgres")
    print("Password: prodogs03")
    print()
    print("📋 Tables to check:")
    print("  - batches")
    print("  - documents") 
    print("  - llm_responses")
    print("  - folders")
    print("  - prompts")
    print("  - llm_configurations")
    print()
    print("🔍 SQL to run in your PostgreSQL client:")
    print("  SELECT * FROM batches ORDER BY created_at DESC LIMIT 10;")
    print("  SELECT COUNT(*) FROM batches;")

if __name__ == "__main__":
    success = verify_connection()
    show_connection_details()
    
    if success:
        print("\n🎉 Your application IS connected to PostgreSQL!")
        print("💡 If you don't see updates in your client, try refreshing or reconnecting.")
    else:
        print("\n⚠️  Connection issue detected.")
