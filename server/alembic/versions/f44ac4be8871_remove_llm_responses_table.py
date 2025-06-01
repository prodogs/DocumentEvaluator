"""remove_llm_responses_table

Revision ID: f44ac4be8871
Revises: fd196deb262e
Create Date: 2025-06-01 16:25:31.651166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f44ac4be8871'
down_revision: Union[str, None] = 'fd196deb262e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove llm_responses table from doc_eval database."""
    # Drop the llm_responses table completely
    op.drop_table('llm_responses')


def downgrade() -> None:
    """Recreate llm_responses table in doc_eval database."""
    # Recreate the llm_responses table structure
    op.create_table('llm_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('connection_details', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('task_id', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), default='N', nullable=True),
        sa.Column('started_processing_at', sa.DateTime(), nullable=True),
        sa.Column('completed_processing_at', sa.DateTime(), nullable=True),
        sa.Column('response_json', sa.Text(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('time_taken_seconds', sa.Float(), nullable=True),
        sa.Column('tokens_per_second', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now())
    )

    # Recreate indexes
    op.create_index('idx_llm_responses_document_id', 'llm_responses', ['document_id'])
    op.create_index('idx_llm_responses_prompt_id', 'llm_responses', ['prompt_id'])
    op.create_index('idx_llm_responses_connection_id', 'llm_responses', ['connection_id'])
    op.create_index('idx_llm_responses_status', 'llm_responses', ['status'])
    op.create_index('idx_llm_responses_task_id', 'llm_responses', ['task_id'])
    op.create_index('idx_llm_responses_timestamp', 'llm_responses', ['timestamp'])
