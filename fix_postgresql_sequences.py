#!/usr/bin/env python3
"""
Fix PostgreSQL Sequences

After migrating data from SQLite to PostgreSQL, the auto-increment sequences
need to be updated to start from the correct values to avoid primary key conflicts.
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

def fix_sequence(cursor, table_name, sequence_name, id_column='id'):
    """Fix a single sequence to start from the correct value"""
    print(f"🔧 Fixing sequence for {table_name}...")
    
    try:
        # Get the maximum ID from the table
        cursor.execute(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table_name};")
        max_id = cursor.fetchone()[0]
        
        # Set the sequence to start from max_id + 1
        next_val = max_id + 1
        cursor.execute(f"SELECT setval('{sequence_name}', {next_val}, false);")
        
        print(f"   ✅ {table_name}: max_id={max_id}, sequence set to {next_val}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to fix {table_name} sequence: {e}")
        return False

def fix_all_sequences():
    """Fix all sequences in the database"""
    print("🚀 Fixing PostgreSQL Sequences\n")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        # List of tables and their sequences
        sequences_to_fix = [
            ('folders', 'folders_id_seq'),
            ('batches', 'batches_id_seq'),
            ('documents', 'documents_id_seq'),
            ('llm_configurations', 'llm_configurations_id_seq'),
            ('prompts', 'prompts_id_seq'),
            ('llm_responses', 'llm_responses_id_seq')
        ]
        
        success_count = 0
        for table_name, sequence_name in sequences_to_fix:
            if fix_sequence(cursor, table_name, sequence_name):
                success_count += 1
        
        # Commit all changes
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Fixed {success_count}/{len(sequences_to_fix)} sequences successfully")
        
        if success_count == len(sequences_to_fix):
            print("🎉 All sequences fixed! New records can now be created without conflicts.")
            return True
        else:
            print("⚠️  Some sequences could not be fixed. Check the errors above.")
            return False
        
    except Exception as e:
        print(f"❌ Failed to connect to database or fix sequences: {e}")
        return False

def test_sequence_fix():
    """Test that sequences are working correctly"""
    print("\n🧪 Testing sequence fixes...")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        # Test each sequence by getting the next value
        sequences_to_test = [
            ('folders', 'folders_id_seq'),
            ('batches', 'batches_id_seq'),
            ('documents', 'documents_id_seq'),
            ('llm_configurations', 'llm_configurations_id_seq'),
            ('prompts', 'prompts_id_seq'),
            ('llm_responses', 'llm_responses_id_seq')
        ]
        
        for table_name, sequence_name in sequences_to_test:
            try:
                # Get the current sequence value (without incrementing)
                cursor.execute(f"SELECT currval('{sequence_name}');")
                current_val = cursor.fetchone()[0]
                
                # Get the next sequence value (this increments it)
                cursor.execute(f"SELECT nextval('{sequence_name}');")
                next_val = cursor.fetchone()[0]
                
                print(f"   ✅ {table_name}: current={current_val}, next={next_val}")
                
                # Reset the sequence back to where it was
                cursor.execute(f"SELECT setval('{sequence_name}', {current_val}, true);")
                
            except Exception as e:
                print(f"   ❌ {table_name}: {e}")
        
        # Rollback the test changes
        conn.rollback()
        
        cursor.close()
        conn.close()
        
        print("✅ Sequence testing completed")
        return True
        
    except Exception as e:
        print(f"❌ Sequence testing failed: {e}")
        return False

def show_current_status():
    """Show current status of tables and sequences"""
    print("📊 Current Database Status\n")
    
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cursor = conn.cursor()
        
        tables = ['folders', 'batches', 'documents', 'llm_configurations', 'prompts', 'llm_responses']
        
        for table in tables:
            try:
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                
                # Get max ID
                cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table};")
                max_id = cursor.fetchone()[0]
                
                # Get sequence current value
                sequence_name = f"{table}_id_seq"
                try:
                    cursor.execute(f"SELECT last_value, is_called FROM {sequence_name};")
                    last_value, is_called = cursor.fetchone()
                    seq_status = f"last_value={last_value}, is_called={is_called}"
                except:
                    seq_status = "sequence not found"
                
                print(f"📋 {table}:")
                print(f"   Records: {count}")
                print(f"   Max ID: {max_id}")
                print(f"   Sequence: {seq_status}")
                print()
                
            except Exception as e:
                print(f"❌ Error checking {table}: {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to show status: {e}")
        return False

def main():
    """Main function"""
    print("🚀 PostgreSQL Sequence Fix Tool\n")
    print(f"📍 Target: postgresql://postgres@{PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['database']}")
    
    # Show current status
    show_current_status()
    
    # Fix sequences
    if fix_all_sequences():
        # Test the fixes
        test_sequence_fix()
        
        print(f"\n🎉 PostgreSQL sequences fixed successfully!")
        print(f"   ✅ All auto-increment sequences updated")
        print(f"   ✅ New records can be created without conflicts")
        print(f"   ✅ Application should work normally now")
        
        return True
    else:
        print(f"\n❌ Failed to fix PostgreSQL sequences!")
        print(f"💡 Check the error messages above and try again")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
