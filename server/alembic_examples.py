"""
Alembic Migration Examples for DocumentEvaluator

This file contains examples of common database migration operations using Alembic.
These are templates you can copy into your migration files.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ============================================================================
# TABLE OPERATIONS
# ============================================================================

def create_table_example():
    """Example: Creating a new table"""
    op.create_table('new_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

def drop_table_example():
    """Example: Dropping a table"""
    op.drop_table('old_table')

# ============================================================================
# COLUMN OPERATIONS
# ============================================================================

def add_column_example():
    """Example: Adding a new column"""
    op.add_column('table_name', sa.Column('new_column', sa.String(255), nullable=True))

def drop_column_example():
    """Example: Dropping a column"""
    op.drop_column('table_name', 'old_column')

def alter_column_example():
    """Example: Modifying a column"""
    # Change column type
    op.alter_column('table_name', 'column_name',
                   existing_type=sa.VARCHAR(length=100),
                   type_=sa.VARCHAR(length=255),
                   existing_nullable=True)
    
    # Make column not nullable
    op.alter_column('table_name', 'column_name',
                   existing_type=sa.VARCHAR(length=255),
                   nullable=False)
    
    # Rename column
    op.alter_column('table_name', 'old_name', new_column_name='new_name')

# ============================================================================
# INDEX OPERATIONS
# ============================================================================

def create_index_example():
    """Example: Creating indexes"""
    # Simple index
    op.create_index('idx_table_column', 'table_name', ['column_name'])
    
    # Composite index
    op.create_index('idx_table_multi', 'table_name', ['col1', 'col2'])
    
    # Unique index
    op.create_index('idx_table_unique', 'table_name', ['column_name'], unique=True)

def drop_index_example():
    """Example: Dropping an index"""
    op.drop_index('idx_table_column', table_name='table_name')

# ============================================================================
# CONSTRAINT OPERATIONS
# ============================================================================

def add_foreign_key_example():
    """Example: Adding foreign key constraint"""
    op.create_foreign_key('fk_table_ref', 'table_name', 'referenced_table',
                         ['foreign_key_column'], ['id'])

def drop_foreign_key_example():
    """Example: Dropping foreign key constraint"""
    op.drop_constraint('fk_table_ref', 'table_name', type_='foreignkey')

def add_unique_constraint_example():
    """Example: Adding unique constraint"""
    op.create_unique_constraint('uq_table_column', 'table_name', ['column_name'])

def drop_unique_constraint_example():
    """Example: Dropping unique constraint"""
    op.drop_constraint('uq_table_column', 'table_name', type_='unique')

# ============================================================================
# DATA MIGRATION OPERATIONS
# ============================================================================

def data_migration_example():
    """Example: Data migration operations"""
    # Simple data update
    op.execute("UPDATE table_name SET column_name = 'new_value' WHERE condition = 'old_value'")
    
    # Complex data migration
    connection = op.get_bind()
    
    # Fetch data
    result = connection.execute(sa.text("SELECT id, old_column FROM table_name"))
    
    # Process and update data
    for row in result:
        new_value = process_data(row.old_column)  # Your custom logic
        connection.execute(
            sa.text("UPDATE table_name SET new_column = :new_val WHERE id = :id"),
            {"new_val": new_value, "id": row.id}
        )

def bulk_data_migration_example():
    """Example: Bulk data operations"""
    # Bulk insert
    op.bulk_insert(
        sa.table('table_name',
                sa.column('column1'),
                sa.column('column2')),
        [
            {'column1': 'value1', 'column2': 'value2'},
            {'column1': 'value3', 'column2': 'value4'},
        ]
    )

# ============================================================================
# POSTGRESQL SPECIFIC OPERATIONS
# ============================================================================

def postgresql_specific_example():
    """Example: PostgreSQL specific operations"""
    # Create ENUM type
    op.execute("CREATE TYPE status_enum AS ENUM ('active', 'inactive', 'pending')")
    
    # Add column with ENUM type
    op.add_column('table_name', 
                 sa.Column('status', postgresql.ENUM('active', 'inactive', 'pending', 
                                                   name='status_enum'), nullable=True))
    
    # Create partial index
    op.create_index('idx_active_only', 'table_name', ['column_name'], 
                   postgresql_where=sa.text('is_active = true'))
    
    # Add JSONB column
    op.add_column('table_name', 
                 sa.Column('metadata', postgresql.JSONB(), nullable=True))

# ============================================================================
# COMPLETE MIGRATION EXAMPLE
# ============================================================================

def complete_migration_example():
    """
    Complete migration example for DocumentEvaluator:
    Migrating from llm_configurations to connections
    """
    
    # Step 1: Create new connections table (if not exists)
    op.create_table('connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('api_key', sa.String(500), nullable=True),
        sa.Column('port_no', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('connection_config', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['provider_id'], ['llm_providers.id']),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'])
    )
    
    # Step 2: Migrate data from llm_configurations to connections
    op.execute("""
        INSERT INTO connections (name, base_url, api_key, port_no, is_active, provider_id)
        SELECT 
            llm_name as name,
            base_url,
            api_key,
            port_no,
            CASE WHEN active = 1 THEN true ELSE false END as is_active,
            1 as provider_id  -- Default provider, adjust as needed
        FROM llm_configurations
        WHERE active = 1
    """)
    
    # Step 3: Add connection_id to llm_responses if not exists
    op.add_column('llm_responses', sa.Column('connection_id', sa.Integer(), nullable=True))
    
    # Step 4: Migrate llm_responses to use connection_id
    op.execute("""
        UPDATE llm_responses 
        SET connection_id = (
            SELECT c.id 
            FROM connections c 
            JOIN llm_configurations lc ON c.name = lc.llm_name 
            WHERE lc.id = llm_responses.llm_config_id
            LIMIT 1
        )
        WHERE llm_config_id IS NOT NULL
    """)
    
    # Step 5: Add foreign key constraint
    op.create_foreign_key('fk_llm_responses_connection', 'llm_responses', 'connections',
                         ['connection_id'], ['id'])
    
    # Step 6: Remove deprecated columns
    op.drop_column('llm_responses', 'llm_config_id')
    op.drop_column('llm_responses', 'llm_name')
    
    # Step 7: Drop deprecated table
    op.drop_table('llm_configurations')

def process_data(old_value):
    """Helper function for data processing"""
    # Your custom data transformation logic here
    return old_value.upper() if old_value else None
