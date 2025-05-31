#!/usr/bin/env python3
"""
Check consistency between SQLAlchemy models and actual database schema
"""

from database import get_db_connection
from models import Base

def get_db_schema():
    """Get actual database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        # Get columns for each table
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table,))
        
        columns = []
        for col in cursor.fetchall():
            columns.append({
                'name': col[0],
                'type': col[1],
                'nullable': col[2] == 'YES',
                'default': col[3]
            })
        
        schema[table] = columns
    
    cursor.close()
    conn.close()
    return schema

def get_sqlalchemy_schema():
    """Get SQLAlchemy model schema"""
    schema = {}
    
    for table_name, table in Base.metadata.tables.items():
        columns = []
        for column in table.columns:
            columns.append({
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'default': str(column.default) if column.default else None
            })
        schema[table_name] = columns
    
    return schema

def main():
    """Main consistency check"""
    print("🔍 Checking schema consistency between SQLAlchemy models and database...\n")
    
    try:
        db_schema = get_db_schema()
        model_schema = get_sqlalchemy_schema()
        
        print("📊 Database Tables:")
        for table in sorted(db_schema.keys()):
            print(f"  - {table}")
        
        print("\n📊 SQLAlchemy Model Tables:")
        for table in sorted(model_schema.keys()):
            print(f"  - {table}")
        
        # Check for missing tables
        db_tables = set(db_schema.keys())
        model_tables = set(model_schema.keys())
        
        missing_in_db = model_tables - db_tables
        missing_in_models = db_tables - model_tables
        
        if missing_in_db:
            print("\n❌ Tables in models but missing in database:")
            for table in missing_in_db:
                print(f"  - {table}")
        
        if missing_in_models:
            print("\n❌ Tables in database but missing in models:")
            for table in missing_in_models:
                print(f"  - {table}")
        
        # Check column consistency for common tables
        common_tables = db_tables & model_tables
        
        print(f"\n🔍 Checking column consistency for {len(common_tables)} common tables...\n")
        
        inconsistencies = []
        
        for table in sorted(common_tables):
            print(f"📋 Table: {table}")
            
            db_cols = {col['name']: col for col in db_schema[table]}
            model_cols = {col['name']: col for col in model_schema[table]}
            
            db_col_names = set(db_cols.keys())
            model_col_names = set(model_cols.keys())
            
            # Check for missing columns
            missing_in_db_cols = model_col_names - db_col_names
            missing_in_model_cols = db_col_names - model_col_names
            
            if missing_in_db_cols:
                print(f"  ❌ Columns in model but missing in DB: {missing_in_db_cols}")
                inconsistencies.append(f"{table}: columns {missing_in_db_cols} missing in DB")
            
            if missing_in_model_cols:
                print(f"  ❌ Columns in DB but missing in model: {missing_in_model_cols}")
                inconsistencies.append(f"{table}: columns {missing_in_model_cols} missing in model")
            
            # Check common columns
            common_cols = db_col_names & model_col_names
            for col_name in sorted(common_cols):
                db_col = db_cols[col_name]
                model_col = model_cols[col_name]
                
                # Check nullable consistency
                if db_col['nullable'] != model_col['nullable']:
                    print(f"  ⚠️  Column {col_name}: nullable mismatch (DB: {db_col['nullable']}, Model: {model_col['nullable']})")
                    inconsistencies.append(f"{table}.{col_name}: nullable mismatch")
            
            if not missing_in_db_cols and not missing_in_model_cols:
                nullable_issues = [i for i in inconsistencies if f"{table}." in i and "nullable mismatch" in i]
                if not nullable_issues:
                    print("  ✅ All columns consistent")
            
            print()
        
        # Summary
        print("=" * 80)
        if not inconsistencies and not missing_in_db and not missing_in_models:
            print("🎉 SUCCESS: Database schema and SQLAlchemy models are fully consistent!")
            return True
        else:
            print("❌ INCONSISTENCIES FOUND:")
            if missing_in_db:
                print(f"  - {len(missing_in_db)} tables missing in database")
            if missing_in_models:
                print(f"  - {len(missing_in_models)} tables missing in models")
            if inconsistencies:
                print(f"  - {len(inconsistencies)} column inconsistencies")
                for issue in inconsistencies[:10]:  # Show first 10
                    print(f"    • {issue}")
                if len(inconsistencies) > 10:
                    print(f"    ... and {len(inconsistencies) - 10} more")
            return False
    
    except Exception as e:
        print(f"❌ Error during schema check: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
