"""Migrate users to participants

Revision ID: 4631a2317dd0
Revises: d54ed600c4bf
Create Date: 2019-08-21 11:09:46.626025

"""

# revision identifiers, used by Alembic.
revision = '4631a2317dd0'
down_revision = 'd54ed600c4bf'

from alembic import op
from enum import Enum
import sqlalchemy as sa
import sqlalchemy_utils as sau

class ParticipantType(Enum):
    user = "user"
    email = "email"
    external = "external"

def upgrade():
    op.create_table("participant",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime, nullable=False),
        sa.Column("participant_type",
            sau.ChoiceType(ParticipantType, impl=sa.String()),
            nullable=False),
        sa.Column("user_id", sa.Integer,
                sa.ForeignKey("user.id", ondelete="CASCADE"), unique=True),
        sa.Column("email", sa.String, unique=True),
        sa.Column("email_name", sa.String),
        sa.Column("external_id", sa.String, unique=True),
        sa.Column("external_url", sa.String))

    op.execute("""
        ALTER TABLE participant ALTER COLUMN created DROP NOT NULL;
        ALTER TABLE participant ALTER COLUMN participant_type DROP NOT NULL;

        INSERT INTO participant(user_id)
        SELECT submitter_id AS user_id FROM ticket
        UNION SELECT user_id FROM event
        UNION SELECT by_user_id AS user_id FROM event
        UNION SELECT submitter_id AS user_id FROM ticket_comment
        UNION SELECT user_id FROM ticket_subscription;

        UPDATE participant
        SET created = now() at time zone 'utc', participant_type = 'user';

        ALTER TABLE participant ALTER COLUMN created SET NOT NULL;
        ALTER TABLE participant ALTER COLUMN participant_type SET NOT NULL;
    """)

    op.add_column("ticket", sa.Column(
        "participant_id", sa.Integer, sa.ForeignKey("participant.id")))
    op.execute("""
        UPDATE ticket tk
        SET participant_id = p.id
        FROM participant p
        WHERE p.user_id = tk.submitter_id;
    """)
    op.drop_column("ticket", "submitter_id")
    op.alter_column("ticket", "participant_id",
            new_column_name="submitter_id", nullable=False)

    op.add_column("event", sa.Column(
        "participant_id", sa.Integer, sa.ForeignKey("participant.id")))
    op.add_column("event", sa.Column(
        "by_participant_id", sa.Integer, sa.ForeignKey("participant.id")))
    op.execute("""
        UPDATE event ev
        SET participant_id = p.id
        FROM participant p
        WHERE p.user_id = ev.user_id;

        UPDATE event ev
        SET by_participant_id = p.id
        FROM participant p
        WHERE p.user_id = ev.by_user_id;
    """)
    op.drop_column("event", "user_id")
    op.drop_column("event", "by_user_id")

    op.add_column("ticket_comment", sa.Column(
        "participant_id", sa.Integer, sa.ForeignKey("participant.id")))
    op.execute("""
        UPDATE ticket_comment tc
        SET participant_id = p.id
        FROM participant p
        WHERE p.user_id = tc.submitter_id;
    """)
    op.drop_column("ticket_comment", "submitter_id")
    op.alter_column("ticket_comment", "participant_id",
            new_column_name="submitter_id", nullable=False)

    op.add_column("ticket_subscription", sa.Column(
        "participant_id", sa.Integer, sa.ForeignKey("participant.id")))
    op.execute("""
        UPDATE ticket_subscription ts
        SET participant_id = p.id
        FROM participant p
        WHERE p.user_id = ts.user_id;
    """)
    op.drop_column("ticket_subscription", "user_id")
    op.drop_column("ticket_subscription", "email")
    op.drop_column("ticket_subscription", "webhook")


def downgrade():
    op.add_column("ticket", sa.Column(
        "submitter_user_id", sa.Integer, sa.ForeignKey("user.id")))
    op.execute("""
        UPDATE ticket tk
        SET submitter_user_id = p.user_id
        FROM participant p
        WHERE p.id = tk.submitter_id;
    """)
    op.drop_column("ticket", "submitter_id")
    op.alter_column("ticket", "submitter_user_id",
            new_column_name="submitter_id", nullable=False)

    op.add_column("event", sa.Column(
        "user_id", sa.Integer, sa.ForeignKey("user.id")))
    op.add_column("event", sa.Column(
        "by_user_id", sa.Integer, sa.ForeignKey("user.id")))
    op.execute("""
        UPDATE event ev
        SET user_id = p.user_id
        FROM participant p
        WHERE p.id = ev.participant_id;

        UPDATE event ev
        SET by_user_id = p.user_id
        FROM participant p
        WHERE p.user_id = ev.by_participant_id;
    """)
    op.drop_column("event", "participant_id")
    op.drop_column("event", "by_participant_id")

    op.add_column("ticket_comment", sa.Column(
        "user_id", sa.Integer, sa.ForeignKey("user.id")))
    op.execute("""
        UPDATE ticket_comment tc
        SET user_id = p.user_id
        FROM participant p
        WHERE p.id = tc.submitter_id;
    """)
    op.drop_column("ticket_comment", "submitter_id")
    op.alter_column("ticket_comment", "user_id",
            new_column_name="submitter_id", nullable=False)

    op.add_column("ticket_subscription", sa.Column(
        "user_id", sa.Integer, sa.ForeignKey("user.id")))
    op.execute("""
        UPDATE ticket_subscription ts
        SET user_id = p.user_id
        FROM participant p
        WHERE p.id = ts.participant_id;
    """)
    op.drop_column("ticket_subscription", "participant_id")

    op.add_column("ticket_subscription",
            sa.Column("email", sa.Column(sa.Unicode(512))))
    op.add_column("ticket_subscription",
            sa.Column("webhook", sa.Column(sa.Unicode(1024))))

    op.drop_table("participant")

