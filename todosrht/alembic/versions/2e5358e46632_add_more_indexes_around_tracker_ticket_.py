"""Add more indexes around tracker/ticket/event relationships

Revision ID: 2e5358e46632
Revises: c59043a3240b
Create Date: 2022-03-21 11:06:58.633601

"""

# revision identifiers, used by Alembic.
revision = '2e5358e46632'
down_revision = 'c59043a3240b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    CREATE INDEX ticket_tracker_id ON ticket (tracker_id);
    CREATE INDEX ticket_scoped_id ON ticket (scoped_id);
    CREATE INDEX ticket_dupe_of_id ON ticket (dupe_of_id);

    CREATE INDEX event_ticket_id ON event (ticket_id);
    CREATE INDEX event_from_ticket_id ON event (from_ticket_id);
    CREATE INDEX event_label_id ON event (label_id);
    CREATE INDEX event_participant_id ON event (participant_id);
    CREATE INDEX event_comment_id ON event (comment_id);

    CREATE INDEX event_notification_event_id ON event_notification (event_id);

    CREATE INDEX ticket_comment_ticket_id ON ticket_comment (ticket_id);
    CREATE INDEX ticket_comment_submitter_id ON ticket_comment (submitter_id);
    CREATE INDEX ticket_comment_superceeded_by_id ON ticket_comment (superceeded_by_id);

    CREATE INDEX ticket_label_ticket_id ON ticket_label (ticket_id);

    CREATE INDEX ticket_assignee_ticket_id ON ticket_assignee (ticket_id);

    CREATE INDEX ticket_webhook_subscription_ticket_id ON ticket_webhook_subscription (ticket_id);
    """)


def downgrade():
    op.execute("""
    DROP INDEX ticket_tracker_id;
    DROP INDEX ticket_scoped_id;
    DROP INDEX ticket_dupe_of_id;
    DROP INDEX event_ticket_id;
    DROP INDEX event_from_ticket_id;
    DROP INDEX event_label_id;
    DROP INDEX event_participant_id;
    DROP INDEX event_comment_id;
    DROP INDEX event_notification_event_id;
    DROP INDEX ticket_comment_ticket_id;
    DROP INDEX ticket_comment_submitter_id;
    DROP INDEX ticket_comment_superceeded_by_id;
    DROP INDEX ticket_label_ticket_id;
    DROP INDEX ticket_assignee_ticket_id;
    DROP INDEX ticket_webhook_subscription_ticket_id;
    """)
