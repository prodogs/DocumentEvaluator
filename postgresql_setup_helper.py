#!/usr/bin/env python3
"""
PostgreSQL Setup Helper

Helps diagnose and resolve PostgreSQL connection issues
Provides multiple authentication methods and troubleshooting steps
"""

import psycopg2
import sys
import getpass

def try_connection_variants():
    """Try different connection variants to find working credentials"""
    print("🔍 Trying different connection methods...\n")
    
    host = 'tablemini.local'
    port = 5432
    
    # Different user/password combinations to try
    variants = [
        {'user': 'postgres', 'password': 'prodogs', 'description': 'Original credentials'},
        {'user': 'postgres', 'password': 'postgres', 'description': 'Default postgres password'},
        {'user': 'postgres', 'password': '', 'description': 'No password'},
        {'user': 'admin', 'password': 'prodogs', 'description': 'Admin user'},
        {'user': 'root', 'password': 'prodogs', 'description': 'Root user'},
    ]
    
    for i, variant in enumerate(variants, 1):
        print(f"🧪 Test {i}: {variant['description']}")
        print(f"   User: {variant['user']}, Password: {'***' if variant['password'] else '(empty)'}")
        
        try:
            conn_params = {
                'host': host,
                'port': port,
                'user': variant['user'],
                'password': variant['password'],
                'database': 'postgres'
            }
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Get basic info
            cursor.execute("SELECT current_user, version();")
            user, version = cursor.fetchone()
            
            print(f"   ✅ SUCCESS! Connected as: {user}")
            print(f"   📊 Server version: {version.split(',')[0]}")
            
            # Check if we can create databases
            cursor.execute("SELECT rolcreatedb FROM pg_roles WHERE rolname = current_user;")
            can_create_db = cursor.fetchone()[0]
            print(f"   🔐 Can create databases: {can_create_db}")
            
            cursor.close()
            conn.close()
            
            return variant
            
        except psycopg2.OperationalError as e:
            if "password authentication failed" in str(e):
                print(f"   ❌ Password authentication failed")
            elif "role" in str(e) and "does not exist" in str(e):
                print(f"   ❌ User does not exist")
            else:
                print(f"   ❌ Connection failed: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
        
        print()
    
    return None

def try_manual_credentials():
    """Allow user to manually enter credentials"""
    print("🔧 Manual credential entry:")
    print("Please enter PostgreSQL credentials for tablemini.local")
    
    user = input("Username [postgres]: ").strip() or 'postgres'
    password = getpass.getpass("Password: ")
    
    try:
        conn_params = {
            'host': 'tablemini.local',
            'port': 5432,
            'user': user,
            'password': password,
            'database': 'postgres'
        }
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT current_user, version();")
        current_user, version = cursor.fetchone()
        
        print(f"✅ SUCCESS! Connected as: {current_user}")
        print(f"📊 Server version: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        
        return {'user': user, 'password': password}
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def create_database_with_credentials(credentials):
    """Create the target database using working credentials"""
    print(f"\n🔨 Creating database 'doc_eval'...")
    
    try:
        conn_params = {
            'host': 'tablemini.local',
            'port': 5432,
            'user': credentials['user'],
            'password': credentials['password'],
            'database': 'postgres'
        }
        
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'doc_eval';")
        exists = cursor.fetchone()
        
        if exists:
            print("ℹ️  Database 'doc_eval' already exists")
        else:
            cursor.execute("CREATE DATABASE doc_eval;")
            print("✅ Database 'doc_eval' created successfully")
        
        # Test connection to new database
        cursor.close()
        conn.close()
        
        # Connect to the new database
        conn_params['database'] = 'doc_eval'
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT current_database();")
        db_name = cursor.fetchone()[0]
        print(f"✅ Successfully connected to database: {db_name}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create/access database: {e}")
        return False

def update_migration_script(credentials):
    """Update the migration script with working credentials"""
    print(f"\n⚙️  Updating migration script with working credentials...")
    
    try:
        # Read the current migration script
        with open('migrate_to_postgresql.py', 'r') as f:
            content = f.read()
        
        # Update the PG_CONFIG section
        old_config = """PG_CONFIG = {
    'host': 'tablemini.local',
    'user': 'postgres',
    'password': 'prodogs',
    'database': 'doc_eval',
    'port': 5432
}"""
        
        new_config = f"""PG_CONFIG = {{
    'host': 'tablemini.local',
    'user': '{credentials['user']}',
    'password': '{credentials['password']}',
    'database': 'doc_eval',
    'port': 5432
}}"""
        
        updated_content = content.replace(old_config, new_config)
        
        # Write back the updated script
        with open('migrate_to_postgresql.py', 'w') as f:
            f.write(updated_content)
        
        print("✅ Migration script updated with working credentials")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update migration script: {e}")
        return False

def provide_troubleshooting_tips():
    """Provide troubleshooting tips for common PostgreSQL issues"""
    print(f"\n🛠️  PostgreSQL Troubleshooting Tips:")
    print(f"")
    print(f"If you're still having connection issues, try these steps on the PostgreSQL server (tablemini.local):")
    print(f"")
    print(f"1. Check if PostgreSQL is running:")
    print(f"   sudo systemctl status postgresql")
    print(f"   # or")
    print(f"   ps aux | grep postgres")
    print(f"")
    print(f"2. Check PostgreSQL configuration:")
    print(f"   sudo nano /etc/postgresql/*/main/postgresql.conf")
    print(f"   # Ensure: listen_addresses = '*' or 'localhost,tablemini.local'")
    print(f"")
    print(f"3. Check client authentication:")
    print(f"   sudo nano /etc/postgresql/*/main/pg_hba.conf")
    print(f"   # Add line: host all all 0.0.0.0/0 md5")
    print(f"   # or: host all all your.client.ip.address/32 md5")
    print(f"")
    print(f"4. Restart PostgreSQL after changes:")
    print(f"   sudo systemctl restart postgresql")
    print(f"")
    print(f"5. Create/reset postgres user password:")
    print(f"   sudo -u postgres psql")
    print(f"   ALTER USER postgres PASSWORD 'prodogs';")
    print(f"   \\q")
    print(f"")
    print(f"6. Test local connection on server:")
    print(f"   sudo -u postgres psql -c 'SELECT version();'")

def main():
    """Main setup helper function"""
    print("🚀 PostgreSQL Setup Helper for Document Evaluation System\n")
    print("This tool will help diagnose and resolve PostgreSQL connection issues.\n")
    
    # Try different connection variants
    working_credentials = try_connection_variants()
    
    if not working_credentials:
        print("❌ None of the standard credential combinations worked.")
        print("Let's try manual credential entry...\n")
        
        working_credentials = try_manual_credentials()
        
        if not working_credentials:
            print("\n❌ Manual credential entry also failed.")
            provide_troubleshooting_tips()
            return False
    
    print(f"\n🎉 Found working credentials!")
    print(f"   User: {working_credentials['user']}")
    print(f"   Password: {'***' if working_credentials['password'] else '(empty)'}")
    
    # Create database
    if create_database_with_credentials(working_credentials):
        print(f"\n✅ Database setup successful!")
        
        # Update migration script
        if update_migration_script(working_credentials):
            print(f"\n🎯 Ready for migration!")
            print(f"   Run: python3 migrate_to_postgresql.py")
            return True
    
    return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 PostgreSQL setup completed successfully!")
        print(f"💡 You can now run the migration script")
    else:
        print(f"\n⚠️  PostgreSQL setup failed!")
        print(f"💡 Please resolve the issues above before proceeding")
    
    sys.exit(0 if success else 1)
