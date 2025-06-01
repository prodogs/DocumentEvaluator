"""Remove deprecated fields with proper constraint handling

Revision ID: ac72e9e3f540
Revises: 286d0bb51a84
Create Date: 2025-05-31 21:04:45.395536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac72e9e3f540'
down_revision: Union[str, None] = '286d0bb51a84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Step 1: Ensure all llm_responses have connection_id populated
    op.execute("""
        UPDATE llm_responses
        SET connection_id = 1
        WHERE connection_id IS NULL AND llm_config_id IS NOT NULL
    """)

    # Step 2: Drop foreign key constraint from llm_responses to llm_configurations
    op.drop_constraint('llm_responses_llm_config_id_fkey', 'llm_responses', type_='foreignkey')

    # Step 3: Remove deprecated columns from llm_responses
    op.drop_column('llm_responses', 'llm_config_id')
    op.drop_column('llm_responses', 'llm_name')

    # Step 4: Now we can safely drop the llm_configurations table
    op.drop_table('llm_configurations')


def downgrade() -> None:
    """Downgrade schema."""

    # Step 1: Recreate llm_configurations table
    op.create_table('llm_configurations',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('llm_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('base_url', sa.VARCHAR(length=500), nullable=True),
        sa.Column('model_name', sa.VARCHAR(length=255), nullable=True),
        sa.Column('api_key', sa.VARCHAR(length=500), nullable=True),
        sa.Column('provider_type', sa.VARCHAR(length=100), nullable=True),
        sa.Column('port_no', sa.INTEGER(), nullable=True),
        sa.Column('active', sa.INTEGER(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Step 2: Add back deprecated columns to llm_responses
    op.add_column('llm_responses', sa.Column('llm_config_id', sa.INTEGER(), nullable=True))
    op.add_column('llm_responses', sa.Column('llm_name', sa.VARCHAR(length=255), nullable=True))

    # Step 3: Recreate foreign key constraint
    op.create_foreign_key('llm_responses_llm_config_id_fkey', 'llm_responses', 'llm_configurations',
                         ['llm_config_id'], ['id'])

    # Note: Data recovery would need to be handled separately
