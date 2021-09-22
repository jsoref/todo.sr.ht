"""Add visibility to trackers

Revision ID: 9fca56774794
Revises: 6099fe670392
Create Date: 2021-09-22 11:19:24.886544

"""

# revision identifiers, used by Alembic.
revision = '9fca56774794'
down_revision = '6099fe670392'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE TYPE visibility AS ENUM (
        'PUBLIC', 'UNLISTED', 'PRIVATE'
    );

    ALTER TABLE tracker
    ADD COLUMN visibility visibility;

    UPDATE tracker
    SET visibility =
        CASE WHEN default_anonymous_perms & 1 > 0
            THEN 'PUBLIC'::visibility
            ELSE 'PRIVATE'::visibility
        END;

    ALTER TABLE tracker
    ALTER COLUMN visibility
    SET NOT NULL;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE tracker DROP COLUMN visibility;
    DROP TYPE visibility;
    """)
