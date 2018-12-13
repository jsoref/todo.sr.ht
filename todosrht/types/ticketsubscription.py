import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base
from srht.flagtype import FlagType
from enum import Enum

class TicketSubscription(Base):
    """One of user, email, or webhook will be valid. The rest will be null."""
    __tablename__ = 'ticket_subscription'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    tracker_id = sa.Column(sa.Integer,
            sa.ForeignKey("tracker.id", ondelete="CASCADE"))
    tracker = sa.orm.relationship("Tracker",
            backref=sa.orm.backref("subscriptions",
                cascade="all, delete-orphan"))
    """Used for subscriptions to all tickets on a tracker"""

    ticket_id = sa.Column(sa.Integer,
            sa.ForeignKey("ticket.id", ondelete="CASCADE"))
    ticket = sa.orm.relationship("Ticket",
            backref=sa.orm.backref("subscriptions",
                cascade="all, delete-orphan"))
    """Used for subscriptions to specific tickets"""

    user_id = sa.Column(sa.Integer,
            sa.ForeignKey("user.id"))
    user = sa.orm.relationship("User",
            backref=sa.orm.backref("subscriptions"))

    email = sa.Column(sa.Unicode(512))

    webhook = sa.Column(sa.Unicode(1024))
