"""Add new event fields and migrate data.

Also makes Event.ticket_id and Event.user_id nullable since some these fields
can be empty for mention events.

Revision ID: 75ff2f7624fd
Revises: c7146cb70d6b
Create Date: 2019-03-28 16:26:18.714300

"""

# revision identifiers, used by Alembic.
revision = "75ff2f7624fd"
down_revision = "c7146cb70d6b"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def upgrade():
    op.alter_column("event", "ticket_id", nullable=True)
    op.alter_column("event", "user_id", nullable=True)
    op.add_column("event",
        sa.Column("by_user_id", sa.Integer(), nullable=True))
    op.add_column("event",
        sa.Column("from_ticket_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        constraint_name="event_from_ticket_id_fkey",
        source_table="event",
        referent_table="ticket",
        local_cols=["from_ticket_id"],
        remote_cols=["id"],
        ondelete="CASCADE"
    )

    op.create_foreign_key(
        constraint_name="event_by_user_id_fkey",
        source_table="event",
        referent_table="user",
        local_cols=["by_user_id"],
        remote_cols=["id"]
    )

    session = sessionmaker()(bind=op.get_bind())

    # `assigned_user` & `unassigned_user`
    session.execute("""
        UPDATE event
           SET by_user_id = user_id,
               user_id = assigned_user_id,
               assigned_user_id = NULL
         WHERE event_type IN (32, 64);
    """)

    # `user_mentioned`
    session.execute("""
        UPDATE event
           SET from_ticket_id = ticket_id,
               ticket_id = NULL,
               by_user_id = (
                   SELECT submitter_id
                     FROM ticket_comment
                    WHERE id = event.comment_id
               )
         WHERE event_type = 128;
    """)

    # `ticket_mentioned`
    session.execute("""
        UPDATE event
           SET by_user_id = user_id,
               user_id = NULL,
               from_ticket_id = (
                   SELECT ticket_id
                     FROM ticket_comment
                    WHERE id = event.comment_id
               )
         WHERE event_type = 256;
    """)

    session.commit()

    op.drop_constraint(
        constraint_name='event_assigned_user_id_fkey',
        table_name='event',
        type_='foreignkey'
    )
    op.drop_column('event', 'assigned_user_id')


def downgrade():
    op.add_column('event',
        sa.Column('assigned_user_id', sa.INTEGER(), nullable=True))

    op.create_foreign_key(
        constraint_name="event_assigned_user_id_fkey",
        source_table="event",
        referent_table="user",
        local_cols=["assigned_user_id"],
        remote_cols=["id"],
        ondelete="CASCADE"
    )

    session = sessionmaker()(bind=op.get_bind())

    # `assigned_user` & `unassigned_user`
    session.execute("""
        UPDATE event
           SET assigned_user_id = user_id,
               user_id = by_user_id,
               by_user_id = NULL
         WHERE event_type IN (32, 64);
    """)

    # `user_mentioned`
    session.execute("""
        UPDATE event
           SET ticket_id = from_ticket_id,
               from_ticket_id = NULL,
               by_user_id = NULL
         WHERE event_type = 128;
    """)

    # `ticket_mentioned`
    session.execute("""
        UPDATE event
           SET user_id = by_user_id,
               by_user_id = NULL,
               from_ticket_id = NULL
         WHERE event_type = 256;
    """)

    session.commit()

    op.drop_constraint("event_from_ticket_id_fkey", "event", type_="foreignkey")
    op.drop_constraint("event_by_user_id_fkey", "event", type_="foreignkey")
    op.drop_column("event", "from_ticket_id")
    op.drop_column("event", "by_user_id")
    op.alter_column("event", "ticket_id", nullable=False)
    op.alter_column("event", "user_id", nullable=False)
