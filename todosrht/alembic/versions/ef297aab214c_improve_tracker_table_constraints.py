"""Improve tracker table constraints

Revision ID: ef297aab214c
Revises: 368579bcc610
Create Date: 2021-09-27 14:51:13.559030

"""

# revision identifiers, used by Alembic.
revision = 'ef297aab214c'
down_revision = 'e3427af07c4e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE tracker
    DROP COLUMN min_desc_length,
    DROP COLUMN enable_ticket_status,
    DROP COLUMN enable_ticket_resolution;

    ALTER TABLE tracker
    ALTER COLUMN next_ticket_id SET DEFAULT 1,
    ALTER COLUMN default_access SET DEFAULT 7,
    ADD CONSTRAINT tracker_owner_id_name_unique UNIQUE (owner_id, name);
    """)


def downgrade():
    op.execute("""
    ALTER TABLE tracker
    ADD COLUMN min_desc_length INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN enable_ticket_status INTEGER NOT NULL DEFAULT 8,
    ADD COLUMN enable_ticket_resolution INTEGER NOT NULL DEFAULT 33;

    ALTER TABLE tracker
    ALTER COLUMN next_ticket_id DROP DEFAULT,
    ALTER COLUMN default_access DROP DEFAULT,
    DROP CONSTRAINT tracker_owner_id_name_unique;
    """)
