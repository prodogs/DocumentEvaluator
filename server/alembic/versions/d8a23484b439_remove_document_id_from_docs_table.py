"""remove_document_id_from_docs_table

Revision ID: d8a23484b439
Revises: 404a871e9c12
Create Date: 2025-06-01 15:54:04.834143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a23484b439'
down_revision: Union[str, None] = '404a871e9c12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove document_id column and related constraints from docs table."""
    # Drop the foreign key constraint first (using actual constraint name)
    op.drop_constraint('docs_document_id_fkey', 'docs', type_='foreignkey')

    # Drop the document_id column (this will also drop any indexes on it)
    op.drop_column('docs', 'document_id')


def downgrade() -> None:
    """Re-add document_id column and related constraints to docs table."""
    # Add the document_id column back
    op.add_column('docs', sa.Column('document_id', sa.Integer(), nullable=True))

    # Re-create the foreign key constraint (using the actual constraint name)
    op.create_foreign_key('docs_document_id_fkey', 'docs', 'documents', ['document_id'], ['id'], ondelete='CASCADE')
