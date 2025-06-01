"""Safe cleanup - backup and remove deprecated fields

Revision ID: 286d0bb51a84
Revises: 164c6d55a776
Create Date: 2025-05-31 20:58:43.324792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '286d0bb51a84'
down_revision: Union[str, None] = '164c6d55a776'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Step 1: Create backup table for llm_configurations
    op.execute("""
        CREATE TABLE llm_configurations_backup AS
        SELECT * FROM llm_configurations
    """)

    # Step 2: Create backup columns for deprecated llm_responses fields
    op.add_column('llm_responses', sa.Column('llm_config_id_backup', sa.INTEGER(), nullable=True))
    op.add_column('llm_responses', sa.Column('llm_name_backup', sa.VARCHAR(length=255), nullable=True))

    # Step 3: Copy data to backup columns
    op.execute("""
        UPDATE llm_responses
        SET llm_config_id_backup = llm_config_id,
            llm_name_backup = llm_name
        WHERE llm_config_id IS NOT NULL OR llm_name IS NOT NULL
    """)

    # Step 4: Verify all llm_responses have connection_id
    op.execute("""
        UPDATE llm_responses
        SET connection_id = 1
        WHERE connection_id IS NULL AND llm_config_id IS NOT NULL
    """)

    # Step 5: Remove deprecated columns (data is backed up)
    op.drop_column('llm_responses', 'llm_config_id')
    op.drop_column('llm_responses', 'llm_name')

    # Step 6: Remove deprecated table (data is backed up)
    op.drop_table('llm_configurations')


def downgrade() -> None:
    """Downgrade schema."""

    # Restore llm_configurations table from backup
    op.execute("""
        CREATE TABLE llm_configurations AS
        SELECT * FROM llm_configurations_backup
    """)

    # Restore deprecated columns
    op.add_column('llm_responses', sa.Column('llm_config_id', sa.INTEGER(), nullable=True))
    op.add_column('llm_responses', sa.Column('llm_name', sa.VARCHAR(length=255), nullable=True))

    # Restore data from backup columns
    op.execute("""
        UPDATE llm_responses
        SET llm_config_id = llm_config_id_backup,
            llm_name = llm_name_backup
        WHERE llm_config_id_backup IS NOT NULL OR llm_name_backup IS NOT NULL
    """)

    # Remove backup columns
    op.drop_column('llm_responses', 'llm_config_id_backup')
    op.drop_column('llm_responses', 'llm_name_backup')

    # Remove backup table
    op.drop_table('llm_configurations_backup')
