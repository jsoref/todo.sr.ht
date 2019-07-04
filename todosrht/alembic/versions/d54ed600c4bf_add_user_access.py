"""Add UserAccess table.

Revision ID: d54ed600c4bf
Revises: 01ed05041614
Create Date: 2019-07-01 12:43:24.129613

"""

# revision identifiers, used by Alembic.
revision = 'd54ed600c4bf'
down_revision = '01ed05041614'

import sqlalchemy as sa
from alembic import op
from enum import IntFlag
from srht.flagtype import FlagType

class TicketAccess(IntFlag):
    none = 0
    browse = 1
    submit = 2
    comment = 4
    edit = 8
    triage = 16
    all = browse | submit | comment | edit | triage


def upgrade():
    op.create_table('user_access',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tracker_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permissions', FlagType(TicketAccess), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tracker_id'], ['tracker.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tracker_id', 'user_id', name='idx_useraccess_tracker_user_unique')
    )


def downgrade():
    op.drop_table('user_access')
