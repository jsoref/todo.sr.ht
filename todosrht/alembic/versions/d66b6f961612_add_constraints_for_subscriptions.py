"""Add constraints for subscriptions

Revision ID: d66b6f961612
Revises: ef297aab214c
Create Date: 2021-09-28 12:09:04.941316

"""

# revision identifiers, used by Alembic.
revision = 'd66b6f961612'
down_revision = 'ef297aab214c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    ALTER TABLE ticket_subscription
    ADD CONSTRAINT subscription_tracker_participant_uq
        UNIQUE (tracker_id, participant_id),
    ADD CONSTRAINT subscription_ticket_participant_uq
        UNIQUE (ticket_id, participant_id);
    """)


def downgrade():
    op.execute("""
    ALTER TABLE ticket_subscription
    DROP CONSTRAINT subscription_tracker_participant_uq,
    DROP CONSTRAINT subscription_ticket_participant_uq;
    """)
