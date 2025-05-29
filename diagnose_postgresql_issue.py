#!/usr/bin/env python3
"""
PostgreSQL Connection Diagnostic with Timeout Handling

Comprehensive diagnostic tool to identify PostgreSQL connection issues
"""

import socket
import psycopg2
import sys
import time
from contextlib import contextmanager

# PostgreSQL connection parameters
PG_CONFIG = {
    'host': 'tablemini.local',
    'user': 'postgres',
    'password': 'prodogs03',
    'database': 'doc_eval',
    'port': 5432
}

@contextmanager
def timeout_handler(seconds):
    """Context manager for timeout handling"""
    import signal
    
    def timeout_signal(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_signal)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def test_network_connectivity():
    """Test basic network connectivity to PostgreSQL server"""
    print("🌐 Testing network connectivity...")
    
    try:
        # Test DNS resolution
        print(f"   📍 Resolving hostname: {PG_CONFIG['host']}")
        ip_address = socket.gethostbyname(PG_CONFIG['host'])
        print(f"   ✅ Hostname resolved to: {ip_address}")
        
        # Test port connectivity with timeout
        print(f"   🔌 Testing port connectivity: {PG_CONFIG['host']}:{PG_CONFIG['port']}")
        
        with timeout_handler(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((PG_CONFIG['host'], PG_CONFIG['port']))
            sock.close()
            
            if result == 0:
                print(f"   ✅ Port {PG_CONFIG['port']} is accessible")
                return True
            else:
                print(f"   ❌ Port {PG_CONFIG['port']} is not accessible (error code: {result})")
                return False
                
    except socket.gaierror as e:
        print(f"   ❌ DNS resolution failed: {e}")
        return False
    except TimeoutError as e:
        print(f"   ❌ Connection test timed out: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Network test failed: {e}")
        return False

def test_postgresql_connection_with_timeout():
    """Test PostgreSQL connection with timeout"""
    print("\n🔍 Testing PostgreSQL connection with timeout...")
    
    try:
        # Add connection timeout to config
        conn_config = PG_CONFIG.copy()
        conn_config['connect_timeout'] = 10
        
        print(f"   📡 Attempting connection to: {PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
        
        with timeout_handler(15):
            conn = psycopg2.connect(**conn_config)
            cursor = conn.cursor()
            
            print(f"   ✅ Connection established!")
            
            # Test basic query with timeout
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   📊 PostgreSQL version: {version.split(',')[0]}")
            
            # Test table access
            cursor.execute("SELECT COUNT(*) FROM batches;")
            batch_count = cursor.fetchone()[0]
            print(f"   📋 Batches table: {batch_count} records")
            
            cursor.close()
            conn.close()
            
            return True
            
    except psycopg2.OperationalError as e:
        if "timeout" in str(e).lower():
            print(f"   ❌ Connection timed out: {e}")
        elif "password authentication failed" in str(e):
            print(f"   ❌ Authentication failed: {e}")
        elif "could not connect" in str(e):
            print(f"   ❌ Could not connect to server: {e}")
        else:
            print(f"   ❌ PostgreSQL error: {e}")
        return False
    except TimeoutError as e:
        print(f"   ❌ Operation timed out: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_alternative_connection_methods():
    """Test alternative connection methods"""
    print("\n🔧 Testing alternative connection methods...")
    
    # Test with different timeout values
    timeout_values = [5, 15, 30]
    
    for timeout in timeout_values:
        print(f"\n   ⏱️  Testing with {timeout}s timeout...")
        
        try:
            conn_config = PG_CONFIG.copy()
            conn_config['connect_timeout'] = timeout
            
            start_time = time.time()
            conn = psycopg2.connect(**conn_config)
            end_time = time.time()
            
            print(f"   ✅ Connected in {end_time - start_time:.2f}s with {timeout}s timeout")
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            result = cursor.fetchone()[0]
            
            if result == 1:
                print(f"   ✅ Query executed successfully")
                cursor.close()
                conn.close()
                return True
            
        except Exception as e:
            print(f"   ❌ Failed with {timeout}s timeout: {e}")
            continue
    
    return False

def test_connection_to_postgres_db():
    """Test connection to default postgres database"""
    print("\n🔍 Testing connection to default 'postgres' database...")
    
    try:
        conn_config = PG_CONFIG.copy()
        conn_config['database'] = 'postgres'
        conn_config['connect_timeout'] = 10
        
        with timeout_handler(15):
            conn = psycopg2.connect(**conn_config)
            cursor = conn.cursor()
            
            print(f"   ✅ Connected to 'postgres' database!")
            
            # Check if our target database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (PG_CONFIG['database'],))
            exists = cursor.fetchone()
            
            if exists:
                print(f"   ✅ Target database '{PG_CONFIG['database']}' exists")
            else:
                print(f"   ❌ Target database '{PG_CONFIG['database']}' does not exist")
            
            cursor.close()
            conn.close()
            
            return True
            
    except Exception as e:
        print(f"   ❌ Failed to connect to 'postgres' database: {e}")
        return False

def provide_troubleshooting_recommendations():
    """Provide troubleshooting recommendations"""
    print(f"\n🛠️  Troubleshooting Recommendations:")
    print(f"")
    print(f"1. **Check PostgreSQL Server Status** (on tablemini.local):")
    print(f"   sudo systemctl status postgresql")
    print(f"   sudo systemctl restart postgresql")
    print(f"")
    print(f"2. **Check PostgreSQL Logs** (on tablemini.local):")
    print(f"   sudo tail -f /var/log/postgresql/postgresql-*.log")
    print(f"")
    print(f"3. **Check Server Resources** (on tablemini.local):")
    print(f"   top")
    print(f"   free -h")
    print(f"   df -h")
    print(f"")
    print(f"4. **Check PostgreSQL Configuration** (on tablemini.local):")
    print(f"   sudo nano /etc/postgresql/*/main/postgresql.conf")
    print(f"   # Verify: listen_addresses = '*'")
    print(f"   # Verify: port = 5432")
    print(f"")
    print(f"5. **Check Client Authentication** (on tablemini.local):")
    print(f"   sudo nano /etc/postgresql/*/main/pg_hba.conf")
    print(f"   # Ensure client IP is allowed")
    print(f"")
    print(f"6. **Test Local Connection** (on tablemini.local):")
    print(f"   sudo -u postgres psql -c 'SELECT version();'")
    print(f"")
    print(f"7. **Check Firewall** (on tablemini.local):")
    print(f"   sudo ufw status")
    print(f"   sudo iptables -L")

def main():
    """Main diagnostic function"""
    print("🚀 PostgreSQL Connection Diagnostic Tool\n")
    print(f"📍 Target: {PG_CONFIG['user']}@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    print(f"⏰ Using timeouts to prevent hanging\n")
    
    # Test network connectivity first
    network_ok = test_network_connectivity()
    
    if not network_ok:
        print(f"\n❌ Network connectivity failed!")
        print(f"💡 The PostgreSQL server may be down or unreachable.")
        provide_troubleshooting_recommendations()
        return False
    
    # Test PostgreSQL connection
    pg_ok = test_postgresql_connection_with_timeout()
    
    if not pg_ok:
        print(f"\n⚠️  Direct connection to target database failed.")
        print(f"🔄 Trying alternative methods...")
        
        # Test connection to postgres database
        postgres_db_ok = test_connection_to_postgres_db()
        
        if postgres_db_ok:
            print(f"\n✅ Can connect to PostgreSQL server, but not to target database.")
            print(f"💡 The issue may be with the specific database or permissions.")
        else:
            # Test alternative timeouts
            alt_ok = test_alternative_connection_methods()
            
            if not alt_ok:
                print(f"\n❌ All connection methods failed!")
                print(f"💡 The PostgreSQL server appears to be unresponsive.")
    
    # Provide recommendations
    provide_troubleshooting_recommendations()
    
    if pg_ok:
        print(f"\n🎉 PostgreSQL connection is working!")
        return True
    else:
        print(f"\n⚠️  PostgreSQL connection issues detected.")
        print(f"💡 Follow the troubleshooting steps above to resolve.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Diagnostic interrupted by user.")
        print(f"💡 The connection test was taking too long, confirming connectivity issues.")
        sys.exit(1)
