"""Add assigned user events

Revision ID: bd06de76eb15
Revises: cd94e721e6b0
Create Date: 2018-12-13 21:24:12.867228

"""

# revision identifiers, used by Alembic.
revision = 'bd06de76eb15'
down_revision = 'cd94e721e6b0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('event', sa.Column('assigned_user_id', sa.Integer))
    op.create_foreign_key('event_assigned_user_id_fkey',
            'event', 'user', ['assigned_user_id'], ['id'])

def downgrade():
    op.drop_constraint('event_assigned_user_id_fkey',
            'event', type_='foreignkey')
    op.drop_column('event', 'assigned_user_id')
