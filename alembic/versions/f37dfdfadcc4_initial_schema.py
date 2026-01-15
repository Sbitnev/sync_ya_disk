"""initial_schema

Revision ID: f37dfdfadcc4
Revises: 
Create Date: 2026-01-15 13:26:41.541026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f37dfdfadcc4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем таблицу files
    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('modified', sa.Text(), nullable=False),
        sa.Column('md5', sa.Text(), nullable=True),
        sa.Column('last_sync', sa.Text(), nullable=False),
        sa.Column('is_empty', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('markdown_path', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path')
    )

    # Создаем индексы
    op.create_index('idx_files_path', 'files', ['path'])
    op.create_index('idx_files_modified', 'files', ['modified'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index('idx_files_modified', table_name='files')
    op.drop_index('idx_files_path', table_name='files')

    # Удаляем таблицу
    op.drop_table('files')
