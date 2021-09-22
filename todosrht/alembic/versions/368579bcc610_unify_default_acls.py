"""Unify default ACLs

Revision ID: 368579bcc610
Revises: 9fca56774794
Create Date: 2021-09-22 12:08:54.542597

"""

# revision identifiers, used by Alembic.
revision = '368579bcc610'
down_revision = '9fca56774794'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE tracker
    DROP COLUMN default_user_perms,
    DROP COLUMN default_submitter_perms,
    DROP COLUMN default_committer_perms;

    ALTER TABLE tracker
    RENAME COLUMN default_anonymous_perms TO default_access;

    ALTER TABLE ticket
    DROP COLUMN user_perms,
    DROP COLUMN submitter_perms,
    DROP COLUMN committer_perms,
    DROP COLUMN anonymous_perms;
    """)


def downgrade():
    op.execute("""
    ALTER TABLE tracker
    ADD COLUMN default_user_perms integer,
    ADD COLUMN default_committer_perms integer,
    ADD COLUMN default_submitter_perms integer;

    ALTER TABLE tracker
    RENAME COLUMN default_access TO default_anonymous_perms;

    UPDATE tracker
    SET
        default_user_perms = default_anonymous_perms,
        default_committer_perms = default_anonymous_perms,
        default_submitter_perms = default_anonymous_perms;

    ALTER TABLE tracker
    ALTER COLUMN default_user_perms SET NOT NULL,
    ALTER COLUMN default_committer_perms SET NOT NULL,
    ALTER COLUMN default_submitter_perms SET NOT NULL;

    ALTER TABLE ticket
    ADD COLUMN user_perms integer,
    ADD COLUMN committer_perms integer,
    ADD COLUMN submitter_perms integer,
    ADD COLUMN anonymous_perms integer;
    """)
