"""Add defaults for tickets

Revision ID: ce5b2bdc66fe
Revises: d66b6f961612
Create Date: 2021-10-01 10:46:09.526428

"""

# revision identifiers, used by Alembic.
revision = 'ce5b2bdc66fe'
down_revision = 'd66b6f961612'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE ticket
    ALTER COLUMN status SET DEFAULT 0,
    ALTER COLUMN resolution SET DEFAULT 0,
    ALTER COLUMN comment_count SET DEFAULT 0;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE ticket
    ALTER COLUMN status DROP DEFAULT,
    ALTER COLUMN resolution DROP DEFAULT,
    ALTER COLUMN comment_count DROP DEFAULT;
    """)
