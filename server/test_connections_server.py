#!/usr/bin/env python3
"""
Test Connections Server

A minimal server to test the connection management system without model conflicts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS

# Import only the essential models to avoid conflicts
from database import Session
from models import LlmProvider, Connection

app = Flask(__name__)
CORS(app)

@app.route('/api/test-connections', methods=['GET'])
def test_connections():
    """Test the connections system"""
    try:
        from database import engine
        from sqlalchemy import text

        session = Session()

        # First, check what tables exist
        result = session.execute(text('SELECT name FROM sqlite_master WHERE type="table"'))
        tables = [row[0] for row in result.fetchall()]

        # Check if connections table exists
        if 'connections' not in tables:
            return jsonify({
                'success': False,
                'error': 'connections table not found',
                'available_tables': tables,
                'database_url': str(engine.url),
                'working_directory': os.getcwd()
            }), 500

        # Test basic queries
        providers = session.query(LlmProvider).all()
        connections = session.query(Connection).all()

        result = {
            'success': True,
            'message': 'Connection system working!',
            'providers_count': len(providers),
            'connections_count': len(connections),
            'providers': [{'id': p.id, 'name': p.name, 'type': p.provider_type} for p in providers],
            'connections': [{'id': c.id, 'name': c.name, 'provider_id': c.provider_id, 'status': c.connection_status} for c in connections],
            'database_url': str(engine.url),
            'working_directory': os.getcwd()
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Connection system failed',
            'working_directory': os.getcwd()
        }), 500

@app.route('/api/test-simple', methods=['GET'])
def test_simple():
    """Simple test without database"""
    return jsonify({
        'success': True,
        'message': 'Server is running',
        'timestamp': str(os.popen('date').read().strip())
    }), 200

if __name__ == '__main__':
    print("🧪 Starting Test Connections Server...")

    # Ensure tables are created
    try:
        from database import Base, engine
        print("🔧 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"⚠️  Error creating tables: {e}")

    print("📍 Test endpoints:")
    print("   GET /api/test-simple - Simple test")
    print("   GET /api/test-connections - Test connection system")
    print()

    app.run(host='0.0.0.0', port=5002, debug=True)
