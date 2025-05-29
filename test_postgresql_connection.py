#!/usr/bin/env python3
"""
PostgreSQL Connection Test Script

Tests various connection scenarios to help diagnose connection issues
"""

import psycopg2
import sys

# Connection parameters
PG_CONFIG = {
    'host': 'tablemini.local',
    'user': 'postgres',
    'password': 'prodogs',
    'database': 'doc_eval',
    'port': 5432
}

def test_basic_connection():
    """Test basic connection to PostgreSQL server"""
    print("🔍 Testing basic connection to PostgreSQL server...")
    
    # Try connecting to default postgres database first
    test_config = PG_CONFIG.copy()
    test_config['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**test_config)
        print(f"✅ Successfully connected to PostgreSQL server at {PG_CONFIG['host']}")
        
        # Get server version
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"📊 PostgreSQL version: {version}")
        
        # List databases
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
        databases = [row[0] for row in cursor.fetchall()]
        print(f"📋 Available databases: {databases}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        
        if "password authentication failed" in str(e):
            print("💡 Password authentication failed. Possible issues:")
            print("   - Incorrect password")
            print("   - User doesn't exist")
            print("   - pg_hba.conf doesn't allow password authentication")
        elif "could not connect to server" in str(e):
            print("💡 Could not connect to server. Possible issues:")
            print("   - PostgreSQL server is not running")
            print("   - Wrong hostname or port")
            print("   - Firewall blocking connection")
        elif "database" in str(e) and "does not exist" in str(e):
            print("💡 Database doesn't exist (this is expected for initial setup)")
        
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_target_database():
    """Test connection to target database"""
    print(f"\n🎯 Testing connection to target database '{PG_CONFIG['database']}'...")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        print(f"✅ Successfully connected to database '{PG_CONFIG['database']}'")
        
        cursor = conn.cursor()
        cursor.execute("SELECT current_database(), current_user;")
        db_name, user = cursor.fetchone()
        print(f"📊 Connected to database: {db_name} as user: {user}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        if "does not exist" in str(e):
            print(f"ℹ️  Database '{PG_CONFIG['database']}' does not exist - this is expected for initial setup")
            return "needs_creation"
        else:
            print(f"❌ Connection failed: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_create_database():
    """Test creating the target database"""
    print(f"\n🔨 Testing database creation...")
    
    try:
        # Connect to postgres database
        test_config = PG_CONFIG.copy()
        test_config['database'] = 'postgres'
        
        conn = psycopg2.connect(**test_config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database already exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (PG_CONFIG['database'],))
        exists = cursor.fetchone()
        
        if exists:
            print(f"ℹ️  Database '{PG_CONFIG['database']}' already exists")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {PG_CONFIG['database']};")
            print(f"✅ Database '{PG_CONFIG['database']}' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Failed to create database: {e}")
        return False

def test_permissions():
    """Test user permissions"""
    print(f"\n🔐 Testing user permissions...")
    
    try:
        # Connect to postgres database to check permissions
        test_config = PG_CONFIG.copy()
        test_config['database'] = 'postgres'
        
        conn = psycopg2.connect(**test_config)
        cursor = conn.cursor()
        
        # Check user privileges
        cursor.execute("""
            SELECT rolname, rolsuper, rolcreatedb, rolcreaterole 
            FROM pg_roles 
            WHERE rolname = %s;
        """, (PG_CONFIG['user'],))
        
        user_info = cursor.fetchone()
        if user_info:
            rolname, rolsuper, rolcreatedb, rolcreaterole = user_info
            print(f"👤 User: {rolname}")
            print(f"   Superuser: {rolsuper}")
            print(f"   Can create databases: {rolcreatedb}")
            print(f"   Can create roles: {rolcreaterole}")
            
            if rolsuper or rolcreatedb:
                print("✅ User has sufficient privileges to create databases")
            else:
                print("⚠️  User may not have sufficient privileges to create databases")
        else:
            print(f"❌ User '{PG_CONFIG['user']}' not found")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to check permissions: {e}")
        return False

def test_network_connectivity():
    """Test network connectivity to the server"""
    print(f"\n🌐 Testing network connectivity...")
    
    import socket
    
    try:
        # Test if we can reach the host and port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((PG_CONFIG['host'], PG_CONFIG['port']))
        sock.close()
        
        if result == 0:
            print(f"✅ Network connection to {PG_CONFIG['host']}:{PG_CONFIG['port']} successful")
            return True
        else:
            print(f"❌ Cannot reach {PG_CONFIG['host']}:{PG_CONFIG['port']}")
            print("💡 Possible issues:")
            print("   - Server is not running")
            print("   - Wrong hostname or port")
            print("   - Firewall blocking connection")
            return False
            
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def main():
    """Run all connection tests"""
    print("🚀 PostgreSQL Connection Diagnostic Tool\n")
    print(f"📍 Target: {PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}")
    
    # Test network connectivity first
    if not test_network_connectivity():
        print("\n❌ Network connectivity failed - cannot proceed with database tests")
        return False
    
    # Test basic connection
    if not test_basic_connection():
        print("\n❌ Basic connection failed - check credentials and server configuration")
        return False
    
    # Test user permissions
    test_permissions()
    
    # Test target database
    db_result = test_target_database()
    
    if db_result == "needs_creation":
        # Try to create the database
        if test_create_database():
            # Test connection again
            if test_target_database():
                print(f"\n✅ All tests passed! Ready for migration.")
                return True
    elif db_result == True:
        print(f"\n✅ All tests passed! Ready for migration.")
        return True
    
    print(f"\n❌ Some tests failed. Please resolve the issues above before proceeding.")
    return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 Connection tests successful!")
        print(f"💡 You can now run: python3 migrate_to_postgresql.py")
    else:
        print(f"\n⚠️  Connection tests failed!")
        print(f"💡 Please resolve the connection issues before attempting migration")
    
    sys.exit(0 if success else 1)
