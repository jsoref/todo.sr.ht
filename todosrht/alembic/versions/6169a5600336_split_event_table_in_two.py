"""Split event table in two

Revision ID: 6169a5600336
Revises: 132ee194cefe
Create Date: 2017-11-09 18:45:13.828939

"""

# revision identifiers, used by Alembic.
revision = '6169a5600336'
down_revision = '132ee194cefe'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as BaseSession, relationship

Session = sessionmaker()
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = sa.Column(sa.Integer, primary_key=True)

class Ticket(Base):
    __tablename__ = 'ticket'
    id = sa.Column(sa.Integer, primary_key=True)
    submitter_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)

class TicketComment(Base):
    __tablename__ = 'ticket_comment'
    id = sa.Column(sa.Integer, primary_key=True)
    submitter_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)

class Event(Base):
    __tablename__ = 'event'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)
    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket")
    comment_id = sa.Column(sa.Integer, sa.ForeignKey("ticket_comment.id"))
    comment = sa.orm.relationship("TicketComment")

class EventNotification(Base):
    __tablename__ = 'event_notification'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    event_id = sa.Column(sa.Integer, sa.ForeignKey("event.id"), nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)

def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    op.create_table('event_notification',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.DateTime, nullable=False),
        sa.Column('event_id', sa.Integer, sa.ForeignKey("event.id"), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey("user.id"), nullable=False))
    session.commit()
    # NOTE: This does not clear out duplicate events. ¯\_(ツ)_/¯
    for event in session.query(Event).all():
        notification = EventNotification()
        notification.created = event.created
        notification.event_id = event.id
        notification.user_id = event.user_id
        if event.comment:
            event.user_id = event.comment.submitter_id
        else:
            event.user_id = event.ticket.submitter_id
        session.add(notification)
    session.commit()

def downgrade():
    op.drop_table('event_notifications')
