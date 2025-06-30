"""add message_metadata column to chat_messages

Revision ID: 0002
Revises: 0001
Create Date: 2025-06-29 02:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add message_metadata column to chat_messages table
    op.add_column('chat_messages', sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'))


def downgrade() -> None:
    # Remove message_metadata column from chat_messages table
    op.drop_column('chat_messages', 'message_metadata') 