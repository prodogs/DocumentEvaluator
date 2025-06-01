#!/usr/bin/env python3
"""
Simple test for connection details capture.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Connection
from sqlalchemy import text
import json


def test_simple_query():
    """Test a simple query to see what's in the database."""
    session = Session()
    
    try:
        print("🧪 Testing Simple Database Query")
        print("=" * 50)
        
        # Get first connection
        connection = session.query(Connection).first()
        if not connection:
            print("❌ No connections found")
            return
            
        print(f"✅ Found connection: {connection.name} (ID: {connection.id})")
        print(f"   Provider ID: {connection.provider_id}")
        print(f"   Model ID: {connection.model_id}")
        
        # Test the exact query from our utility
        print(f"\n🔍 Testing connection details query for ID {connection.id}")
        
        result = session.execute(text("""
            SELECT 
                c.id, c.name, c.description, c.base_url, c.port_no,
                c.is_active, c.connection_status, c.created_at,
                p.id as provider_id, p.provider_type, p.name as provider_name,
                m.id as model_id, m.display_name as model_name, m.model_name as model_identifier
            FROM connections c
            LEFT JOIN llm_providers p ON c.provider_id = p.id
            LEFT JOIN models m ON c.model_id = m.id
            WHERE c.id = :connection_id
        """), {"connection_id": connection.id}).fetchone()
        
        if result:
            print("✅ Query successful!")
            print(f"   Connection: {result.name}")
            print(f"   Provider: {result.provider_name} ({result.provider_type})")
            print(f"   Model: {result.model_name}")
            
            # Test building the connection details dict
            connection_details = {
                "connection": {
                    "id": result.id,
                    "name": result.name,
                    "description": result.description,
                    "base_url": result.base_url,
                    "port_no": result.port_no,
                    "is_active": result.is_active,
                    "connection_status": result.connection_status,
                    "created_at": result.created_at.isoformat() if result.created_at else None
                },
                "provider": {
                    "id": result.provider_id,
                    "provider_type": result.provider_type,
                    "provider_name": result.provider_name
                } if result.provider_id else None,
                "model": {
                    "id": result.model_id,
                    "display_name": result.model_name,
                    "model_identifier": result.model_identifier
                } if result.model_id else None,
                "captured_at": "2025-05-31T23:00:00",
                "version": "1.0"
            }
            
            print(f"\n📋 Connection details JSON:")
            print(json.dumps(connection_details, indent=2))
            
        else:
            print("❌ Query returned no results")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_simple_query()
