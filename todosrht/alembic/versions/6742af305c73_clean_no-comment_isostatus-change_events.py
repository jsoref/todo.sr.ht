"""Clean no-comment isostatus-change events

Revision ID: 6742af305c73
Revises: c32f13924e46
Create Date: 2020-08-25 23:50:49.940532

"""

# revision identifiers, used by Alembic.
revision = '6742af305c73'
down_revision = 'c32f13924e46'

from alembic import op
from todosrht.types import Event, EventType
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    (session.query(Event)
        .filter(Event.comment_id == None)
        .filter(Event.event_type == EventType.status_change)
        .filter(Event.old_status == Event.new_status)
        .filter(Event.old_resolution == Event.new_resolution)).delete()


def downgrade():
    pass
