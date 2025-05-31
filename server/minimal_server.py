#!/usr/bin/env python3
"""
Minimal Server for Connection Management

A clean server that only loads the essential models to avoid SQLAlchemy conflicts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS

# Import only the database and essential models
from database import Session, Base, engine

app = Flask(__name__)
CORS(app)

# Define only the essential models inline to avoid import conflicts
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class LlmProvider(Base):
    __tablename__ = 'llm_providers'
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    provider_type = Column(Text, nullable=False)
    default_base_url = Column(Text)
    auth_type = Column(Text, default='api_key')
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

class Model(Base):
    __tablename__ = 'models'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(Text, nullable=False)
    common_name = Column(Text, nullable=False)
    model_family = Column(Text)
    context_length = Column(Integer)
    parameter_count = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

class ModelProvider(Base):
    __tablename__ = 'model_providers'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())

class Connection(Base):
    __tablename__ = 'connections'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=True)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    base_url = Column(Text)
    api_key = Column(Text)
    port_no = Column(Integer)
    connection_config = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(Text, default='unknown', nullable=False)
    last_tested = Column(DateTime, nullable=True)
    last_test_result = Column(Text)
    supports_model_discovery = Column(Boolean, default=True, nullable=False)
    available_models = Column(Text, nullable=True)
    last_model_sync = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# API Routes
@app.route('/api/connections', methods=['GET'])
def list_connections():
    """List all connections"""
    try:
        session = Session()
        connections = session.query(Connection).all()
        providers = session.query(LlmProvider).all()
        
        # Convert to dictionaries
        connections_data = []
        models = session.query(Model).all()
        for conn in connections:
            provider = next((p for p in providers if p.id == conn.provider_id), None)
            model = next((m for m in models if m.id == conn.model_id), None) if conn.model_id else None
            connections_data.append({
                'id': conn.id,
                'name': conn.name,
                'description': conn.description,
                'model_id': conn.model_id,
                'model_name': model.display_name if model else None,
                'model_common_name': model.common_name if model else None,
                'provider_id': conn.provider_id,
                'provider_name': provider.name if provider else None,
                'provider_type': provider.provider_type if provider else None,
                'base_url': conn.base_url,
                'port_no': conn.port_no,
                'is_active': conn.is_active,
                'connection_status': conn.connection_status,
                'last_tested': conn.last_tested.isoformat() if conn.last_tested else None,
                'supports_model_discovery': conn.supports_model_discovery,
                'notes': conn.notes,
                'created_at': conn.created_at.isoformat() if conn.created_at else None
            })
        
        session.close()
        return jsonify({
            'success': True,
            'connections': connections_data,
            'total': len(connections_data)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/connections', methods=['POST'])
def create_connection():
    """Create a new connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        session = Session()
        
        connection = Connection(
            name=data['name'],
            description=data.get('description'),
            model_id=data.get('model_id'),
            provider_id=data['provider_id'],
            base_url=data.get('base_url'),
            api_key=data.get('api_key'),
            port_no=data.get('port_no'),
            is_active=data.get('is_active', True),
            supports_model_discovery=data.get('supports_model_discovery', True),
            notes=data.get('notes')
        )
        
        session.add(connection)
        session.commit()
        
        result = {
            'id': connection.id,
            'name': connection.name,
            'description': connection.description,
            'provider_id': connection.provider_id,
            'base_url': connection.base_url,
            'port_no': connection.port_no,
            'is_active': connection.is_active,
            'connection_status': connection.connection_status,
            'supports_model_discovery': connection.supports_model_discovery,
            'notes': connection.notes,
            'created_at': connection.created_at.isoformat() if connection.created_at else None
        }
        
        session.close()
        return jsonify({
            'success': True,
            'message': 'Connection created successfully',
            'connection': result
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/connections/<int:connection_id>', methods=['PUT'])
def update_connection(connection_id):
    """Update an existing connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        session = Session()
        connection = session.query(Connection).filter_by(id=connection_id).first()

        if not connection:
            session.close()
            return jsonify({'success': False, 'error': 'Connection not found'}), 404

        # Update fields
        connection.name = data.get('name', connection.name)
        connection.description = data.get('description', connection.description)
        connection.model_id = data.get('model_id', connection.model_id)
        connection.provider_id = data.get('provider_id', connection.provider_id)
        connection.base_url = data.get('base_url', connection.base_url)
        connection.api_key = data.get('api_key', connection.api_key)
        connection.port_no = data.get('port_no', connection.port_no)
        connection.is_active = data.get('is_active', connection.is_active)
        connection.supports_model_discovery = data.get('supports_model_discovery', connection.supports_model_discovery)
        connection.notes = data.get('notes', connection.notes)

        session.commit()

        result = {
            'id': connection.id,
            'name': connection.name,
            'description': connection.description,
            'model_id': connection.model_id,
            'provider_id': connection.provider_id,
            'base_url': connection.base_url,
            'port_no': connection.port_no,
            'is_active': connection.is_active,
            'connection_status': connection.connection_status,
            'supports_model_discovery': connection.supports_model_discovery,
            'notes': connection.notes,
            'updated_at': connection.updated_at.isoformat() if connection.updated_at else None
        }

        session.close()
        return jsonify({
            'success': True,
            'message': 'Connection updated successfully',
            'connection': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/llm-providers', methods=['GET'])
def list_providers():
    """List all providers"""
    try:
        session = Session()
        providers = session.query(LlmProvider).all()
        
        providers_data = []
        for provider in providers:
            providers_data.append({
                'id': provider.id,
                'name': provider.name,
                'provider_type': provider.provider_type,
                'default_base_url': provider.default_base_url,
                'auth_type': provider.auth_type,
                'notes': provider.notes,
                'created_at': provider.created_at.isoformat() if provider.created_at else None
            })
        
        session.close()
        return jsonify({
            'success': True,
            'providers': providers_data,
            'total': len(providers_data)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """List all models"""
    try:
        session = Session()
        models = session.query(Model).all()

        models_data = []
        for model in models:
            models_data.append({
                'id': model.id,
                'display_name': model.display_name,
                'common_name': model.common_name,
                'family': model.model_family,
                'context_length': model.context_length,
                'parameter_count': model.parameter_count,
                'notes': model.notes,
                'created_at': model.created_at.isoformat() if model.created_at else None
            })

        session.close()
        return jsonify({
            'success': True,
            'models': models_data,
            'total': len(models_data)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/models/<int:model_id>/providers', methods=['GET'])
def get_model_providers(model_id):
    """Get providers for a specific model"""
    try:
        session = Session()

        # Get model-provider relationships
        model_providers = session.query(ModelProvider).filter_by(model_id=model_id).all()
        provider_ids = [mp.provider_id for mp in model_providers]

        # Get the actual providers
        providers = session.query(LlmProvider).filter(LlmProvider.id.in_(provider_ids)).all()

        providers_data = []
        for provider in providers:
            providers_data.append({
                'id': provider.id,
                'name': provider.name,
                'provider_type': provider.provider_type,
                'default_base_url': provider.default_base_url,
                'auth_type': provider.auth_type,
                'notes': provider.notes,
                'created_at': provider.created_at.isoformat() if provider.created_at else None
            })

        session.close()
        return jsonify({
            'success': True,
            'providers': providers_data,
            'total': len(providers_data)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test():
    """Simple test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Minimal server is working!',
        'timestamp': str(os.popen('date').read().strip())
    }), 200

if __name__ == '__main__':
    print("🧪 Starting Minimal Connection Server...")
    
    # Create tables
    try:
        print("🔧 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"⚠️  Error creating tables: {e}")
    
    print("📍 Endpoints:")
    print("   GET /api/test - Simple test")
    print("   GET /api/llm-providers - List providers")
    print("   GET /api/connections - List connections")
    print("   POST /api/connections - Create connection")
    print()
    
    app.run(host='0.0.0.0', port=5003, debug=True)
