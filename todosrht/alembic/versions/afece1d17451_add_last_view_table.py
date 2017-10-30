"""Add last view table

Revision ID: afece1d17451
Revises: 237974dd94c4
Create Date: 2017-10-30 12:38:47.769260

"""

# revision identifiers, used by Alembic.
revision = 'afece1d17451'
down_revision = '237974dd94c4'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'ticket_seen',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
        sa.Column('ticket_id', sa.Integer, sa.ForeignKey('ticket.id'), primary_key=True),
        sa.Column('last_view', sa.DateTime, nullable=False, server_default=sa.sql.func.now())
    )


def downgrade():
    op.drop_table('ticket_seen')
