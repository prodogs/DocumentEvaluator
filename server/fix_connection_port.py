#!/usr/bin/env python3
"""
Fix Connection Port Issue

This script fixes the existing connection that has the wrong port number.
It updates connections to use the correct port from their provider's default_base_url.
"""

import os
import sys
import logging
from urllib.parse import urlparse

# Add the parent directory to the path so we can import from server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection

logger = logging.getLogger(__name__)

def fix_connection_ports():
    """Fix connection ports to match provider default URLs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get connections with their provider default URLs
        cursor.execute("""
            SELECT c.id, c.name, c.base_url, c.port_no, p.default_base_url, p.name as provider_name
            FROM connections c
            LEFT JOIN llm_providers p ON c.provider_id = p.id
            WHERE p.default_base_url IS NOT NULL
        """)
        
        connections = cursor.fetchall()
        
        if not connections:
            print("No connections found with provider default URLs")
            return True
        
        print(f"Found {len(connections)} connections to check")
        
        for conn_row in connections:
            conn_id, conn_name, base_url, port_no, default_base_url, provider_name = conn_row
            
            print(f"\nChecking connection: {conn_name}")
            print(f"  Current: {base_url}:{port_no}")
            print(f"  Provider default: {default_base_url}")
            
            try:
                # Parse the provider's default URL
                parsed_default = urlparse(default_base_url)
                
                if parsed_default.port:
                    expected_port = parsed_default.port
                    expected_base_url = f"{parsed_default.scheme}://{parsed_default.hostname}"
                    
                    # Check if we need to update
                    needs_update = False
                    updates = {}
                    
                    if base_url != expected_base_url:
                        print(f"  Base URL mismatch: {base_url} -> {expected_base_url}")
                        updates['base_url'] = expected_base_url
                        needs_update = True
                    
                    if port_no != expected_port:
                        print(f"  Port mismatch: {port_no} -> {expected_port}")
                        updates['port_no'] = expected_port
                        needs_update = True
                    
                    if needs_update:
                        # Build update query
                        set_clauses = []
                        params = {'connection_id': conn_id}
                        
                        if 'base_url' in updates:
                            set_clauses.append("base_url = %(base_url)s")
                            params['base_url'] = updates['base_url']
                        
                        if 'port_no' in updates:
                            set_clauses.append("port_no = %(port_no)s")
                            params['port_no'] = updates['port_no']
                        
                        update_query = f"""
                            UPDATE connections 
                            SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                            WHERE id = %(connection_id)s
                        """
                        
                        cursor.execute(update_query, params)
                        print(f"  ✅ Updated connection {conn_name}")
                    else:
                        print(f"  ✅ Connection {conn_name} is already correct")
                else:
                    print(f"  ⚠️ Provider default URL has no port: {default_base_url}")
                    
            except Exception as e:
                print(f"  ❌ Error parsing URL for {conn_name}: {e}")
        
        conn.commit()
        print(f"\n✅ Successfully processed {len(connections)} connections")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing connection ports: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Fixing connection port issues...")
    success = fix_connection_ports()
    if success:
        print("✅ Connection port fix completed successfully")
        sys.exit(0)
    else:
        print("❌ Connection port fix failed")
        sys.exit(1)
