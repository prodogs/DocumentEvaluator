"""
Utility functions for handling connection details and snapshots.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


def capture_connection_details(session: Session, connection_id: int) -> Optional[Dict[str, Any]]:
    """
    Capture a snapshot of connection details for preservation.
    
    This function queries the connection along with its provider and model information
    and returns a JSON-serializable dictionary containing all the essential information
    needed for display purposes. Sensitive information like API keys are excluded.
    
    Args:
        session: SQLAlchemy session
        connection_id: ID of the connection to capture
        
    Returns:
        Dictionary containing connection details or None if connection not found
    """
    try:
        # Query connection with provider and model info
        result = session.execute(text("""
            SELECT
                c.id, c.name, c.description, c.base_url, c.port_no,
                c.is_active, c.connection_status, c.created_at,
                p.id as provider_id, p.provider_type, p.name as provider_name,
                m.id as model_id, m.display_name as model_name, m.common_name as model_identifier
            FROM connections c
            LEFT JOIN llm_providers p ON c.provider_id = p.id
            LEFT JOIN models m ON c.model_id = m.id
            WHERE c.id = :connection_id
        """), {"connection_id": connection_id}).fetchone()
        
        if not result:
            return None
            
        # Build connection details dictionary (excluding sensitive data)
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
            "captured_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        return connection_details
        
    except Exception as e:
        # Log error but don't fail the main operation
        print(f"Warning: Failed to capture connection details for connection {connection_id}: {e}")
        return None


def get_display_info_from_connection_details(connection_details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract display information from stored connection details.
    
    Args:
        connection_details: Stored connection details dictionary
        
    Returns:
        Dictionary with display-friendly connection information
    """
    if not connection_details:
        return {
            "connection_name": "Unknown Connection",
            "provider_type": "unknown",
            "model_name": "Unknown Model",
            "llm_name": "Unknown LLM"  # For backward compatibility
        }
    
    connection = connection_details.get("connection", {})
    provider = connection_details.get("provider", {})
    model = connection_details.get("model", {})
    
    return {
        "connection_id": connection.get("id"),
        "connection_name": connection.get("name", "Unknown Connection"),
        "provider_type": provider.get("provider_type", "unknown") if provider else "unknown",
        "provider_name": provider.get("provider_name", "Unknown Provider") if provider else "Unknown Provider",
        "model_name": model.get("display_name", "Unknown Model") if model else "Unknown Model",
        "model_identifier": model.get("model_identifier") if model else None,
        "llm_name": connection.get("name", "Unknown LLM"),  # For backward compatibility
        "base_url": connection.get("base_url"),
        "port_no": connection.get("port_no"),
        "captured_at": connection_details.get("captured_at")
    }


def format_connection_for_api_response(connection_details: Optional[Dict[str, Any]], 
                                     fallback_connection=None) -> Optional[Dict[str, Any]]:
    """
    Format connection details for API response, with fallback to current connection if available.
    
    Args:
        connection_details: Stored connection details
        fallback_connection: Current connection object (if available)
        
    Returns:
        Formatted connection info for API response
    """
    # Try to use stored connection details first
    if connection_details:
        display_info = get_display_info_from_connection_details(connection_details)
        return {
            "id": display_info["connection_id"],
            "name": display_info["connection_name"],
            "provider_type": display_info["provider_type"],
            "model_name": display_info["model_name"],
            "source": "stored_details"
        }
    
    # Fallback to current connection if available
    if fallback_connection:
        return {
            "id": fallback_connection.id,
            "name": fallback_connection.name,
            "provider_type": fallback_connection.provider.provider_type if fallback_connection.provider else None,
            "model_name": fallback_connection.model.display_name if fallback_connection.model else None,
            "source": "current_connection"
        }
    
    # No connection info available
    return None
