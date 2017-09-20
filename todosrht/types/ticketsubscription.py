import sqlalchemy as sa
import sqlalchemy_utils as sau
from srht.database import Base
from srht.types import FlagType
from enum import Enum

class TicketSubscription(Base):
    """One of user, email, or webhook will be valid. The rest will be null."""
    __tablename__ = 'ticket_subscription'
    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.DateTime, nullable=False)
    updated = sa.Column(sa.DateTime, nullable=False)

    ticket_id = sa.Column(sa.Integer, sa.ForeignKey("ticket.id"), nullable=False)
    ticket = sa.orm.relationship("Ticket", backref=sa.orm.backref("subscriptions"))

    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"))
    user = sa.orm.relationship("User", backref=sa.orm.backref("subscriptions"))

    email = sa.Column(sa.Unicode(512))

    webhook = sa.Column(sa.Unicode(1024))
