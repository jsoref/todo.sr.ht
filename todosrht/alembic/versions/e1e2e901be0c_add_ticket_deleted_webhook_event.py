"""Add TICKET_DELETED webhook event

Revision ID: e1e2e901be0c
Revises: 7c117bc9e99b
Create Date: 2022-05-03 11:47:11.143292

"""

# revision identifiers, used by Alembic.
revision = 'e1e2e901be0c'
down_revision = '7c117bc9e99b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TYPE tracker_webhook_event ADD VALUE 'TICKET_DELETED';
    ALTER TYPE ticket_webhook_event ADD VALUE 'TICKET_DELETED';
    """)


def downgrade():
    op.execute("""
    ALTER TYPE tracker_webhook_event RENAME TO tracker_webhook_event_old;
    CREATE TYPE tracker_webhook_event AS ENUM (
        'TRACKER_UPDATE',
        'TRACKER_DELETED',
        'TICKET_CREATED',
        'TICKET_UPDATE',
        'LABEL_CREATED',
        'LABEL_UPDATE',
        'LABEL_DELETED',
        'EVENT_CREATED'
    );
    ALTER TABLE gql_tracker_wh_sub ALTER COLUMN events TYPE varchar[];
    ALTER TABLE gql_tracker_wh_sub ALTER COLUMN events TYPE tracker_webhook_event[] USING events::tracker_webhook_event[];
    ALTER TABLE gql_tracker_wh_delivery ALTER COLUMN event TYPE varchar;
    ALTER TABLE gql_tracker_wh_delivery ALTER COLUMN event TYPE tracker_webhook_event USING event::tracker_webhook_event;
    DROP TYPE tracker_webhook_event_old;

    ALTER TYPE ticket_webhook_event RENAME TO ticket_webhook_event_old;
    CREATE TYPE ticket_webhook_event AS ENUM (
        'TICKET_UPDATE',
        'EVENT_CREATED'
    );
    ALTER TABLE gql_ticket_wh_sub ALTER COLUMN events TYPE varchar[];
    ALTER TABLE gql_ticket_wh_sub ALTER COLUMN events TYPE ticket_webhook_event[] USING events::ticket_webhook_event[];
    ALTER TABLE gql_ticket_wh_delivery ALTER COLUMN event TYPE varchar;
    ALTER TABLE gql_ticket_wh_delivery ALTER COLUMN event TYPE ticket_webhook_event USING event::ticket_webhook_event;
    DROP TYPE ticket_webhook_event_old;
    """)
