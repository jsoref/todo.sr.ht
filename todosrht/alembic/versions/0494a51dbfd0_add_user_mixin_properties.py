"""Add user mixin properties

Revision ID: 0494a51dbfd0
Revises: ec0b84a86165
Create Date: 2018-12-30 15:47:14.624946

"""

# revision identifiers, used by Alembic.
revision = '0494a51dbfd0'
down_revision = 'ec0b84a86165'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("user", sa.Column("url", sa.String(256)))
    op.add_column("user", sa.Column("location", sa.Unicode(256)))
    op.add_column("user", sa.Column("bio", sa.Unicode(4096)))


def downgrade():
    op.delete_column("user", "url")
    op.delete_column("user", "location")
    op.delete_column("user", "bio")
