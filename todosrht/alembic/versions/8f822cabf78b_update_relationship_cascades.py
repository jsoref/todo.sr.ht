"""Update relationship cascades

Revision ID: 8f822cabf78b
Revises: 4c70fa9bc46f
Create Date: 2022-11-01 15:54:11.371274

"""

# revision identifiers, used by Alembic.
revision = '8f822cabf78b'
down_revision = '4c70fa9bc46f'

from alembic import op
import sqlalchemy as sa

cascades = [
    ("tracker", "user", "owner_id", "CASCADE"),
    ("ticket", "participant", "submitter_id", "CASCADE"),
    ("ticket_assignee", "user", "assignee_id", "CASCADE"),
    ("ticket_assignee", "user", "assigner_id", "CASCADE"),
    ("ticket_label", "user", "user_id", "CASCADE"),
    ("ticket_subscription", "participant", "participant_id", "CASCADE"),
    ("event", "participant", "participant_id", "CASCADE"),
    ("event", "participant", "by_participant_id", "CASCADE"),
    ("event_notification", "user", "user_id", "CASCADE"),
    ("gql_user_wh_sub", "user", "user_id", "CASCADE"),
    ("gql_tracker_wh_sub", "user", "user_id", "CASCADE"),
    ("gql_ticket_wh_sub", "user", "user_id", "CASCADE"),
    ("oauthtoken", "user", "user_id", "CASCADE"),
    ("user_webhook_subscription", "user", "user_id", "CASCADE"),
    ("user_webhook_subscription", "oauthtoken", "token_id", "CASCADE"),
    ("user_webhook_delivery", "user_webhook_subscription", "subscription_id", "CASCADE"),
]

def upgrade():
    for (table, relation, col, do) in cascades:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{col}_fkey;
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey
            FOREIGN KEY ({col})
            REFERENCES "{relation}"(id) ON DELETE {do};
        """)


def downgrade():
    for (table, relation, col, do) in tables:
        op.execute(f"""
        ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{col}_fkey;
        ALTER TABLE {table} ADD CONSTRAINT {table}_{col}_fkey FOREIGN KEY ({col}) REFERENCES "{relation}"(id);
        """)
