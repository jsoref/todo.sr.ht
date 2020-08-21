"""Remove self-referencing ticket mention events

Revision ID: 074182407bb2
Revises: 61e241dc978c
Create Date: 2020-08-21 18:25:15.512581

"""

# revision identifiers, used by Alembic.
revision = '074182407bb2'
down_revision = '61e241dc978c'

from alembic import op
from todosrht.types import Event, EventType
from sqlalchemy.orm import sessionmaker


Session = sessionmaker()


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    (session.query(Event)
        .filter(Event.event_type == EventType.ticket_mentioned)
        .filter(Event.from_ticket_id == Event.ticket_id)).delete()


def downgrade():
    pass
