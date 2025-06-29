"""add session_type to chat_sessions

Revision ID: 0001
Revises: None
Create Date: 2025-06-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # create the new enum type
    session_type_enum = sa.Enum('TEXT', 'VOICE', name='sessiontype')
    session_type_enum.create(op.get_bind())
    # add the column with a default so existing rows get TEXT
    op.add_column(
        'chat_sessions',
        sa.Column(
            'session_type',
            session_type_enum,
            nullable=False,
            server_default='TEXT'
        )
    )

def downgrade() -> None:
    # drop the column and then drop the enum type
    op.drop_column('chat_sessions', 'session_type')
    sa.Enum(name='sessiontype').drop(op.get_bind())
