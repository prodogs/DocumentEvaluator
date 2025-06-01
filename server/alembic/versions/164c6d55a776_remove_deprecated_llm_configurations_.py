"""Remove deprecated llm_configurations table

Revision ID: 164c6d55a776
Revises: 792eccd32ebf
Create Date: 2025-05-31 20:57:44.116101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '164c6d55a776'
down_revision: Union[str, None] = '792eccd32ebf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Remove the deprecated llm_configurations table
    # Note: Ensure all data has been migrated to connections before running this
    op.drop_table('llm_configurations')


def downgrade() -> None:
    """Downgrade schema."""

    # Recreate the llm_configurations table structure (for rollback)
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

    # Note: Data recovery would need to be handled separately if needed
