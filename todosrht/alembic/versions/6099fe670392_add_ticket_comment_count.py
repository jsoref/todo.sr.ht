"""Add ticket comment count

Revision ID: 6099fe670392
Revises: 3a9cb6757f59
Create Date: 2021-09-12 16:48:48.759365

"""

# revision identifiers, used by Alembic.
revision = '6099fe670392'
down_revision = '3a9cb6757f59'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('ticket',
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_ticket_comment_count'), 'ticket', ['comment_count'], unique=False)

    op.execute("""
        UPDATE ticket t
        SET comment_count = (
            SELECT count(*)
            FROM ticket_comment
            WHERE ticket_id = t.id AND superceeded_by_id IS NULL
        )
    """)

def downgrade():
    op.drop_index(op.f('ix_ticket_comment_count'), table_name='ticket')
    op.drop_column('ticket', 'comment_count')
