"""Add ticket unique constraint.

Revision ID: c7146cb70d6b
Revises: 0494a51dbfd0
Create Date: 2019-01-09 12:25:27.275257

"""

# revision identifiers, used by Alembic.
revision = 'c7146cb70d6b'
down_revision = '0494a51dbfd0'

from alembic import op


def upgrade():
    op.create_unique_constraint(
        'uq_ticket_tracker_id_scoped_id', 'ticket', ['tracker_id', 'scoped_id'])


def downgrade():
    op.drop_constraint(
        'uq_ticket_tracker_id_scoped_id', 'ticket', type_='unique')
