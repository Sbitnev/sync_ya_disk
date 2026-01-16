"""add_video_transcription_fields

Revision ID: 352d756a674e
Revises: f37dfdfadcc4
Create Date: 2026-01-16 13:38:56.706259

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '352d756a674e'
down_revision: Union[str, Sequence[str], None] = 'f37dfdfadcc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поля для асинхронной транскрибации видео
    op.add_column('files', sa.Column('transcription_status', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('transcription_operation_id', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('transcription_started_at', sa.Text(), nullable=True))
    op.add_column('files', sa.Column('video_metadata', sa.Text(), nullable=True))

    # Создаем индекс для быстрого поиска pending операций
    op.create_index('idx_files_transcription_status', 'files', ['transcription_status'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индекс
    op.drop_index('idx_files_transcription_status', table_name='files')

    # Удаляем добавленные колонки
    op.drop_column('files', 'video_metadata')
    op.drop_column('files', 'transcription_started_at')
    op.drop_column('files', 'transcription_operation_id')
    op.drop_column('files', 'transcription_status')
