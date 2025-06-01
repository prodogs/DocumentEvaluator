"""remove_doc_id_add_file_path_to_docs

Revision ID: fd196deb262e
Revises: d8a23484b439
Create Date: 2025-06-01 16:02:43.731452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd196deb262e'
down_revision: Union[str, None] = 'd8a23484b439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove doc_id from documents and add file_path to docs for natural linking."""

    # Step 1: Add file_path column to docs table
    op.add_column('docs', sa.Column('file_path', sa.Text(), nullable=True))

    # Step 2: Populate file_path in docs table using existing doc_id relationships
    # This preserves the existing data by copying filepath from documents to docs
    op.execute("""
        UPDATE docs
        SET file_path = d.filepath
        FROM documents d
        WHERE docs.id = d.doc_id
    """)

    # Step 3: Delete orphaned docs that have no corresponding documents
    # These are docs that were created but never linked to a document record
    op.execute("""
        DELETE FROM docs
        WHERE file_path IS NULL
    """)

    # Step 4: Make file_path NOT NULL and add unique constraint
    op.alter_column('docs', 'file_path', nullable=False)
    op.create_unique_constraint('uq_docs_file_path', 'docs', ['file_path'])

    # Step 5: Drop the foreign key constraint and doc_id column from documents
    op.drop_constraint('documents_doc_id_fkey', 'documents', type_='foreignkey')
    op.drop_column('documents', 'doc_id')


def downgrade() -> None:
    """Restore doc_id in documents and remove file_path from docs."""

    # Step 1: Add doc_id column back to documents
    op.add_column('documents', sa.Column('doc_id', sa.Integer(), nullable=True))

    # Step 2: Restore the foreign key relationship
    op.create_foreign_key('documents_doc_id_fkey', 'documents', 'docs', ['doc_id'], ['id'])

    # Step 3: Populate doc_id in documents using file_path matching
    op.execute("""
        UPDATE documents
        SET doc_id = docs.id
        FROM docs
        WHERE documents.filepath = docs.file_path
    """)

    # Step 4: Remove file_path from docs
    op.drop_constraint('uq_docs_file_path', 'docs', type_='unique')
    op.drop_column('docs', 'file_path')
