"""Add tracker subscriptions

Revision ID: 5fb6db84ce55
Revises: afece1d17451
Create Date: 2017-11-08 21:48:22.522263

"""

# revision identifiers, used by Alembic.
revision = '5fb6db84ce55'
down_revision = 'afece1d17451'

from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as BaseSession, relationship

Session = sessionmaker()
Base = declarative_base()

class Tracker(Base):
    __tablename__ = 'tracker'
    id = sa.Column(sa.Integer, primary_key=True)
    owner_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"), nullable=False)

class User(Base):
    __tablename__ = 'user'
    id = sa.Column(sa.Integer, primary_key=True)

class TicketSubscription(Base):
    __tablename__ = 'ticket_subscription'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)
    tracker_id = sa.Column(sa.Integer, sa.ForeignKey("tracker.id"), nullable=False)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"))

def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    op.alter_column("ticket_subscription", "ticket_id", type_=sa.Integer, nullable=True)
    op.add_column('ticket_subscription', sa.Column('tracker_id', sa.Integer()))
    op.create_foreign_key(None, 'ticket_subscription', 'tracker', ['tracker_id'], ['id'])
    session.commit()
    for tracker in session.query(Tracker).all():
        sub = TicketSubscription()
        sub.created = sub.updated = datetime.utcnow()
        sub.user_id = tracker.owner_id
        sub.tracker_id = tracker.id
        session.add(sub)
    session.commit()

def downgrade():
    op.alter_column("ticket_subscription", "ticket_id", type_=sa.Integer, nullable=False)
    op.drop_constraint(None, 'ticket_subscription', type_='foreignkey')
    op.drop_column('ticket_subscription', 'tracker_id')
