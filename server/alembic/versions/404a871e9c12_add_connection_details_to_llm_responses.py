"""add_connection_details_to_llm_responses

Revision ID: 404a871e9c12
Revises: 3ec491a78c21
Create Date: 2025-05-31 23:54:24.484371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '404a871e9c12'
down_revision: Union[str, None] = '3ec491a78c21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add connection_details JSONB column to llm_responses table
    op.add_column('llm_responses', sa.Column('connection_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove connection_details column from llm_responses table
    op.drop_column('llm_responses', 'connection_details')
