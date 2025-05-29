#!/usr/bin/env python3
"""
Simple PostgreSQL Connection Test

Tests if we can connect to PostgreSQL and run basic queries
"""

import psycopg2
import sys

# PostgreSQL connection parameters
PG_CONFIG = {
    'host': 'tablemini.local',
    'user': 'postgres',
    'password': 'prodogs03',
    'database': 'doc_eval',
    'port': 5432
}

def test_basic_connection():
    """Test basic PostgreSQL connection"""
    print("🔍 Testing basic PostgreSQL connection...")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"📊 PostgreSQL version: {version.split(',')[0]}")
        
        # Test table access
        cursor.execute("SELECT COUNT(*) FROM batches;")
        batch_count = cursor.fetchone()[0]
        print(f"📋 Batches table accessible: {batch_count} records")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection (same as the app uses)"""
    print("\n🔍 Testing SQLAlchemy connection...")
    
    try:
        from sqlalchemy import create_engine, text
        
        # Create engine same as the app
        DATABASE_URL = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}"
        
        engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM batches;"))
            count = result.fetchone()[0]
            print(f"✅ SQLAlchemy connection successful!")
            print(f"📋 Batches count via SQLAlchemy: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False

def test_app_models():
    """Test using the app's models directly"""
    print("\n🔍 Testing app models...")
    
    try:
        import sys
        import os
        sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')
        
        from server.database import Session
        from server.models import Batch
        
        session = Session()
        
        # Test query
        batches = session.query(Batch).all()
        print(f"✅ App models working!")
        print(f"📋 Found {len(batches)} batches via app models")
        
        for batch in batches[:3]:  # Show first 3
            print(f"   Batch #{batch.batch_number}: {batch.batch_name}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ App models failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 PostgreSQL Connection Diagnostic\n")
    
    # Test basic connection
    basic_ok = test_basic_connection()
    
    if not basic_ok:
        print("\n❌ Basic connection failed - cannot proceed")
        return False
    
    # Test SQLAlchemy
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    # Test app models
    models_ok = test_app_models()
    
    print(f"\n📊 Test Results:")
    print(f"   Basic Connection: {'✅' if basic_ok else '❌'}")
    print(f"   SQLAlchemy: {'✅' if sqlalchemy_ok else '❌'}")
    print(f"   App Models: {'✅' if models_ok else '❌'}")
    
    if all([basic_ok, sqlalchemy_ok, models_ok]):
        print(f"\n🎉 All tests passed! PostgreSQL connection is working correctly.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
