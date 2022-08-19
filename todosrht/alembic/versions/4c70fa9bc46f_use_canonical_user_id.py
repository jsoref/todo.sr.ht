"""Use canonical user ID

Revision ID: 4c70fa9bc46f
Revises: b5f503ac3ae9
Create Date: 2022-06-16 11:38:50.325723

"""

# revision identifiers, used by Alembic.
revision = '4c70fa9bc46f'
down_revision = 'b5f503ac3ae9'

from alembic import op
import sqlalchemy as sa


# These tables all have a column referencing "user"(id)
tables = [
    ("event_notification", "user_id"),
    ("gql_ticket_wh_sub", "user_id"),
    ("gql_tracker_wh_sub", "user_id"),
    ("gql_user_wh_sub", "user_id"),
    ("oauthtoken", "user_id"),
    ("participant", "user_id"),
    ("ticket_assignee", "assignee_id"),
    ("ticket_assignee", "assigner_id"),
    ("ticket_label", "user_id"),
    ("ticket_webhook_subscription", "user_id"),
    ("tracker", "owner_id"),
    ("tracker_webhook_subscription", "user_id"),
    ("user_access", "user_id"),
    ("user_webhook_subscription", "user_id"),
]

def upgrade():
    # Drop unique constraints
    op.execute("""
    ALTER TABLE participant DROP CONSTRAINT participant_user_id_key;
    ALTER TABLE tracker DROP CONSTRAINT tracker_owner_id_name_unique;
    """)

    # Drop foreign key constraints and update user IDs
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT {table}_{col}_fkey;
        UPDATE {table} t SET {col} = u.remote_id FROM "user" u WHERE u.id = t.{col};
        """)

    # Update primary key
    op.execute("""
    ALTER TABLE "user" DROP CONSTRAINT user_pkey;
    ALTER TABLE "user" DROP CONSTRAINT user_remote_id_key;
    ALTER TABLE "user" RENAME COLUMN id TO old_id;
    ALTER TABLE "user" RENAME COLUMN remote_id TO id;
    ALTER TABLE "user" ADD PRIMARY KEY (id);
    ALTER TABLE "user" ADD UNIQUE (old_id);
    """)

    # Add foreign key constraints
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey FOREIGN KEY ({col}) REFERENCES "user"(id) ON DELETE CASCADE;
        """)

    # Add unique constraints
    op.execute("""
    ALTER TABLE participant ADD CONSTRAINT participant_user_id_key UNIQUE (user_id);
    ALTER TABLE tracker ADD CONSTRAINT tracker_owner_id_name_unique UNIQUE (owner_id, name);
    """)


def downgrade():
    # Drop unique constraints
    op.execute("""
    ALTER TABLE participant DROP CONSTRAINT participant_user_id_key;
    ALTER TABLE tracker DROP CONSTRAINT tracker_owner_id_name_unique;
    """)

    # Drop foreign key constraints and update user IDs
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT {table}_{col}_fkey;
        UPDATE {table} t SET {col} = u.old_id FROM "user" u WHERE u.id = t.{col};
        """)

    # Update primary key
    op.execute("""
    ALTER TABLE "user" DROP CONSTRAINT user_pkey;
    ALTER TABLE "user" DROP CONSTRAINT user_old_id_key;
    ALTER TABLE "user" RENAME COLUMN id TO remote_id;
    ALTER TABLE "user" RENAME COLUMN old_id TO id;
    ALTER TABLE "user" ADD PRIMARY KEY (id);
    ALTER TABLE "user" ADD UNIQUE (remote_id);
    """)

    # Add foreign key constraints
    for (table, col) in tables:
        op.execute(f"""
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey FOREIGN KEY ({col}) REFERENCES "user"(id) ON DELETE CASCADE;
        """)

    # Add unique constraints
    op.execute("""
    ALTER TABLE participant ADD CONSTRAINT participant_user_id_key UNIQUE (user_id);
    ALTER TABLE tracker ADD CONSTRAINT tracker_owner_id_name_unique UNIQUE (owner_id, name);
    """)
