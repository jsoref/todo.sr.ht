"""Remove TicketSeen

Revision ID: e3427af07c4e
Revises: 368579bcc610
Create Date: 2021-12-18 19:43:57.634789

"""

# revision identifiers, used by Alembic.
revision = 'e3427af07c4e'
down_revision = '368579bcc610'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.drop_table('ticket_seen')



def downgrade():
    op.create_table('ticket_seen',
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('ticket_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('last_view', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['ticket_id'], ['ticket.id'], name='ticket_seen_ticket_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='ticket_seen_user_id_fkey'),
    sa.PrimaryKeyConstraint('user_id', 'ticket_id', name='ticket_seen_pkey')
    )
