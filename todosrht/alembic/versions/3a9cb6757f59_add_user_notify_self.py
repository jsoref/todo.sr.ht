"""Add User.notify_self

Revision ID: 3a9cb6757f59
Revises: 6c714f704591
Create Date: 2020-09-28 19:11:22.221191

"""

# revision identifiers, used by Alembic.
revision = '3a9cb6757f59'
down_revision = '6c714f704591'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('notify_self', sa.Boolean,
        nullable=False, server_default='FALSE'))


def downgrade():
    op.drop_column('user', 'notify_self')
