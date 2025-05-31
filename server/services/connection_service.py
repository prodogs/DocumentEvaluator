"""
Connection Service

This service manages connections - specific instances of providers with actual connection details.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session as SQLSession

from database import Session
from models import Connection, LlmProvider
from services.llm_provider_service import llm_provider_service
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ConnectionService:
    """Service for managing provider connections"""
    
    def __init__(self):
        self.provider_service = llm_provider_service
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get all connections with their provider information"""
        session = Session()
        try:
            # Use direct SQL to avoid relationship loading issues
            result = session.execute(text("""
                SELECT c.*, p.name as provider_name, p.provider_type, m.display_name as model_name, m.common_name as model_common_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
            """))

            connections_data = []
            for row in result:
                connections_data.append(self._row_to_dict(row))

            return connections_data
        finally:
            session.close()
    
    def get_connection_by_id(self, connection_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific connection by ID"""
        session = Session()
        try:
            # Use direct SQL to avoid relationship loading issues
            result = session.execute(text("""
                SELECT c.*, p.name as provider_name, p.provider_type, m.display_name as model_name, m.common_name as model_common_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            session.close()
    
    def get_connections_by_provider(self, provider_id: int) -> List[Dict[str, Any]]:
        """Get all connections for a specific provider"""
        session = Session()
        try:
            # Use direct SQL to avoid relationship loading issues
            result = session.execute(text("""
                SELECT c.*, p.name as provider_name, p.provider_type, m.display_name as model_name, m.common_name as model_common_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.provider_id = :provider_id
            """), {"provider_id": provider_id})

            connections_data = []
            for row in result:
                connections_data.append(self._row_to_dict(row))

            return connections_data
        finally:
            session.close()
    
    def create_connection(self, connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new connection"""
        session = Session()
        try:
            # Get provider information to auto-populate fields
            result = session.execute(text("""
                SELECT id, name, default_base_url, auth_type
                FROM llm_providers
                WHERE id = :provider_id
            """), {"provider_id": connection_data['provider_id']})

            provider_row = result.fetchone()
            if not provider_row:
                raise ValueError(f"Provider with ID {connection_data['provider_id']} not found")

            # Auto-populate base_url and port from provider if not provided
            if not connection_data.get('base_url') and provider_row.default_base_url:
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(provider_row.default_base_url)

                    # Extract base URL without port
                    if parsed_url.port:
                        # Remove port from URL for base_url field
                        connection_data['base_url'] = f"{parsed_url.scheme}://{parsed_url.hostname}"
                        # Set port_no from the parsed URL
                        if not connection_data.get('port_no'):
                            connection_data['port_no'] = parsed_url.port
                    else:
                        # No port in URL, use as-is
                        connection_data['base_url'] = provider_row.default_base_url
                        # Set default ports only if no port specified in URL
                        if not connection_data.get('port_no'):
                            if parsed_url.scheme == 'https':
                                connection_data['port_no'] = 443
                            elif parsed_url.scheme == 'http':
                                connection_data['port_no'] = 80
                except:
                    # If URL parsing fails, use the default_base_url as-is
                    connection_data['base_url'] = provider_row.default_base_url

            # Auto-populate port from base_url if still not provided
            elif not connection_data.get('port_no') and connection_data.get('base_url'):
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(connection_data['base_url'])
                    if parsed_url.port:
                        connection_data['port_no'] = parsed_url.port
                    elif parsed_url.scheme == 'https':
                        connection_data['port_no'] = 443
                    elif parsed_url.scheme == 'http':
                        connection_data['port_no'] = 80
                except:
                    pass  # If URL parsing fails, leave port_no as None
            
            # Insert connection using direct SQL to avoid ORM relationship loading
            result = session.execute(text("""
                INSERT INTO connections (
                    name, description, provider_id, model_id, base_url, api_key, port_no,
                    connection_config, is_active, supports_model_discovery, notes,
                    connection_status, created_at, updated_at
                ) VALUES (
                    :name, :description, :provider_id, :model_id, :base_url, :api_key, :port_no,
                    :connection_config, :is_active, :supports_model_discovery, :notes,
                    'unknown', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """), {
                "name": connection_data['name'],
                "description": connection_data.get('description'),
                "provider_id": connection_data['provider_id'],
                "model_id": connection_data.get('model_id'),
                "base_url": connection_data.get('base_url'),
                "api_key": connection_data.get('api_key'),
                "port_no": connection_data.get('port_no'),
                "connection_config": json.dumps(connection_data.get('connection_config', {})),
                "is_active": connection_data.get('is_active', True),
                "supports_model_discovery": connection_data.get('supports_model_discovery', True),
                "notes": connection_data.get('notes')
            })

            # Get the ID of the created connection
            connection_id = result.lastrowid
            session.commit()

            logger.info(f"Created connection: {connection_data['name']}")

            # Get the created connection with provider info using SQL
            result = session.execute(text("""
                SELECT c.*, p.name as provider_name, p.provider_type, m.display_name as model_name, m.common_name as model_common_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            return self._row_to_dict(row)
        finally:
            session.close()
    
    def update_connection(self, connection_id: int, connection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing connection"""
        session = Session()
        try:
            connection = session.query(Connection).filter(Connection.id == connection_id).first()
            if not connection:
                return None
            
            # Update connection fields using SQL to avoid datetime issues
            update_fields = []
            update_params = {"connection_id": connection_id}

            for field in ['name', 'description', 'model_id', 'base_url', 'api_key', 'port_no', 'is_active',
                         'supports_model_discovery', 'notes']:
                if field in connection_data:
                    update_fields.append(f"{field} = :{field}")
                    update_params[field] = connection_data[field]

            if 'connection_config' in connection_data:
                update_fields.append("connection_config = :connection_config")
                update_params['connection_config'] = json.dumps(connection_data['connection_config'])

            # Always update the updated_at timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            if update_fields:
                session.execute(text(f"""
                    UPDATE connections
                    SET {', '.join(update_fields)}
                    WHERE id = :connection_id
                """), update_params)
                session.commit()

            logger.info(f"Updated connection: {connection.name}")

            # Get the updated connection with provider info using SQL
            result = session.execute(text("""
                SELECT c.*, p.name as provider_name, p.provider_type, m.display_name as model_name, m.common_name as model_common_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            return self._row_to_dict(row)
        finally:
            session.close()
    
    def delete_connection(self, connection_id: int) -> bool:
        """Delete a connection"""
        session = Session()
        try:
            connection = session.query(Connection).filter(Connection.id == connection_id).first()
            if not connection:
                return False
            
            # Check if connection is being used by any LLM configurations
            # Use direct SQL to avoid importing LlmConfiguration model
            result = session.execute(text(
                "SELECT COUNT(*) FROM llm_configurations WHERE connection_id = :connection_id"
            ), {"connection_id": connection_id})
            configs_count = result.scalar()
            
            if configs_count > 0:
                raise ValueError(f"Cannot delete connection: it is used by {configs_count} LLM configurations")
            
            connection_name = connection.name
            session.delete(connection)
            session.commit()
            
            logger.info(f"Deleted connection: {connection_name}")
            return True
        finally:
            session.close()
    
    def test_connection(self, connection_id: int, test_config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Test a connection"""
        session = Session()
        try:
            # Get connection and provider info using SQL to avoid relationship loading
            result = session.execute(text("""
                SELECT c.*, p.provider_type
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            if not row:
                return False, "Connection not found"

            # Build test configuration
            config = {
                'provider_type': row.provider_type,
                'base_url': row.base_url,
                'api_key': row.api_key,
                'port_no': row.port_no
            }
            
            # Override with test config if provided
            if test_config:
                config.update(test_config)
            
            # Use provider service to test connection
            success, message = self.provider_service.test_connection(config)

            # Update connection status using SQL
            session.execute(text("""
                UPDATE connections
                SET connection_status = :status,
                    last_tested = CURRENT_TIMESTAMP,
                    last_test_result = :result
                WHERE id = :connection_id
            """), {
                "status": 'connected' if success else 'failed',
                "result": message,
                "connection_id": connection_id
            })
            session.commit()

            return success, message
        finally:
            session.close()
    
    def sync_models(self, connection_id: int) -> Tuple[bool, str]:
        """Sync models for a connection"""
        session = Session()
        try:
            # Get connection and provider info using SQL to avoid relationship loading
            result = session.execute(text("""
                SELECT c.*, p.provider_type
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            if not row:
                return False, "Connection not found"

            if not row.supports_model_discovery:
                return False, "Connection does not support model discovery"

            # Build configuration for model discovery
            config = {
                'provider_type': row.provider_type,
                'base_url': row.base_url,
                'api_key': row.api_key,
                'port_no': row.port_no
            }

            # Use provider service to discover models
            success, models, error = self.provider_service.discover_models(row.provider_id, config)

            if success:
                # Update available models using SQL
                session.execute(text("""
                    UPDATE connections
                    SET available_models = :models,
                        last_model_sync = CURRENT_TIMESTAMP
                    WHERE id = :connection_id
                """), {
                    "models": json.dumps([model['model_name'] for model in models]),
                    "connection_id": connection_id
                })
                session.commit()
                return True, f"Synced {len(models)} models"
            else:
                return False, error
        finally:
            session.close()
    
    def get_available_models(self, connection_id: int) -> List[str]:
        """Get available models for a connection"""
        session = Session()
        try:
            # Use direct SQL to avoid relationship loading
            result = session.execute(text("""
                SELECT available_models
                FROM connections
                WHERE id = :connection_id
            """), {"connection_id": connection_id})

            row = result.fetchone()
            if not row or not row.available_models:
                return []

            try:
                return json.loads(row.available_models)
            except json.JSONDecodeError:
                return []
        finally:
            session.close()
    
    def _connection_to_dict(self, connection: Connection) -> Dict[str, Any]:
        """Convert connection model to dictionary"""
        config = {}
        if connection.connection_config:
            try:
                config = json.loads(connection.connection_config)
            except json.JSONDecodeError:
                config = {}
        
        available_models = []
        if connection.available_models:
            try:
                available_models = json.loads(connection.available_models)
            except json.JSONDecodeError:
                available_models = []
        
        return {
            'id': connection.id,
            'name': connection.name,
            'description': connection.description,
            'provider_id': connection.provider_id,
            'provider_name': connection.provider.name if connection.provider else None,
            'provider_type': connection.provider.provider_type if connection.provider else None,
            'base_url': connection.base_url,
            'api_key': connection.api_key,
            'port_no': connection.port_no,
            'connection_config': config,
            'is_active': connection.is_active,
            'connection_status': connection.connection_status,
            'last_tested': connection.last_tested.isoformat() if connection.last_tested else None,
            'last_test_result': connection.last_test_result,
            'supports_model_discovery': connection.supports_model_discovery,
            'available_models': available_models,
            'last_model_sync': connection.last_model_sync.isoformat() if connection.last_model_sync else None,
            'notes': connection.notes,
            'created_at': connection.created_at.isoformat() if connection.created_at else None,
            'updated_at': connection.updated_at.isoformat() if connection.updated_at else None
        }

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert SQL result row to dictionary"""
        config = {}
        if row.connection_config:
            try:
                config = json.loads(row.connection_config)
            except json.JSONDecodeError:
                config = {}

        available_models = []
        if row.available_models:
            try:
                available_models = json.loads(row.available_models)
            except json.JSONDecodeError:
                available_models = []

        return {
            'id': row.id,
            'name': row.name,
            'description': row.description,
            'provider_id': row.provider_id,
            'provider_name': row.provider_name,
            'provider_type': row.provider_type,
            'model_id': getattr(row, 'model_id', None),
            'model_name': getattr(row, 'model_name', None),
            'model_common_name': getattr(row, 'model_common_name', None),
            'base_url': row.base_url,
            'api_key': row.api_key,
            'port_no': row.port_no,
            'connection_config': config,
            'is_active': row.is_active,
            'connection_status': row.connection_status,
            'last_tested': row.last_tested if row.last_tested else None,
            'last_test_result': row.last_test_result,
            'supports_model_discovery': row.supports_model_discovery,
            'available_models': available_models,
            'last_model_sync': row.last_model_sync if row.last_model_sync else None,
            'notes': row.notes,
            'created_at': row.created_at if row.created_at else None,
            'updated_at': row.updated_at if row.updated_at else None
        }

# Global service instance
connection_service = ConnectionService()
