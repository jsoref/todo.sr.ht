"""Add events

Revision ID: 132ee194cefe
Revises: 5fb6db84ce55
Create Date: 2017-11-09 09:26:18.763954

"""

# revision identifiers, used by Alembic.
revision = '132ee194cefe'
down_revision = '5fb6db84ce55'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('event',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.DateTime, nullable=False),
        sa.Column('event_type', sa.Integer, nullable=False),
        sa.Column('old_status', sa.Integer, default=0),
        sa.Column('old_resolution', sa.Integer, default=0),
        sa.Column('new_status', sa.Integer, default=0),
        sa.Column('new_resolution', sa.Integer, default=0),
        sa.Column('user_id', sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column('ticket_id', sa.Integer, sa.ForeignKey("ticket.id"), nullable=False),
        sa.Column('comment_id', sa.Integer, sa.ForeignKey("ticket_comment.id"))
    )


def downgrade():
    op.drop_table('event')
