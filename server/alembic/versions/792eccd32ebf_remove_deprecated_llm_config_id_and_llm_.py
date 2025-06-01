"""Remove deprecated llm_config_id and llm_name from llm_responses

Revision ID: 792eccd32ebf
Revises: 399f595a23fb
Create Date: 2025-05-31 20:56:42.982234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '792eccd32ebf'
down_revision: Union[str, None] = '399f595a23fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # First, ensure all llm_responses have connection_id populated
    # This is a safety check - in production you'd want to ensure data migration is complete
    op.execute("""
        UPDATE llm_responses
        SET connection_id = 1
        WHERE connection_id IS NULL AND llm_config_id IS NOT NULL
    """)

    # Remove the deprecated columns
    op.drop_column('llm_responses', 'llm_config_id')
    op.drop_column('llm_responses', 'llm_name')


def downgrade() -> None:
    """Downgrade schema."""

    # Add back the deprecated columns (for rollback purposes)
    op.add_column('llm_responses', sa.Column('llm_config_id', sa.INTEGER(), nullable=True))
    op.add_column('llm_responses', sa.Column('llm_name', sa.VARCHAR(length=255), nullable=True))

    # Note: Data recovery would need to be handled separately if needed
